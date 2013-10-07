import sys
sys.path.append('../multisock')

import multisock
import threading
import subprocess
import os
import random
import socket
import fcntl
import select
import struct
import time

PORT_START = 20000
PORT_END = 40000
DISPATCHER = 'tcp:localhost:7002'
INIT_SERVERS = 10

FCBASE = '../freeciv/freeciv'
SERVER = FCBASE + '/server/freeciv-web'
DATADIR = FCBASE + '/data'

class Client(object):
    def __init__(self, thread):
        self.sock = thread.connect(DISPATCHER)
        self.main = self.sock.get_main_channel()
        self.main.recv.bind(self.recv)
        self.servers_left = 0
        self.init()

    def init(self):
        self.main.send_async(str(INIT_SERVERS))

    def recv(self, line):
        cmd, arg = line.split()
        arg = int(arg)
        if cmd == 'allocate':
            print 'starting server at channel %d' % arg
            channel = self.sock.get_channel(arg)
            self.start_server(channel)

    def start_server(self, channel):
        threading.Thread(target=self.run_server, args=[channel]).start()

    def run_server(self, channel):
        setup_globals()
        port = choose_port()
        print 'starting server at port', port
        proc = subprocess.Popen([SERVER,
                                 '--exit-on-end',
                                 '--port', '%s' % port],
                                env=dict(os.environ, FREECIV_DATA_PATH=DATADIR),
                                stdin=open('/dev/null'))

        def copier():
            try:
                while True:
                    data = channel.recv()
                    print 'recieved', repr(data)
                    header = struct.pack('<HH', len(data), 0)
                    serv.sendall(header + data)
            except multisock.SocketClosedError:
                pass

        serv = socket.socket()
        retry_connect(serv, ('localhost', port), count=5)
        threading.Thread(target=copier).start()
        print 'connected'
        while True:
            r, w, x = select.select([serv], [], [])
            data = serv.read(10000)
            print 'read server data', repr(data)
            channel.send_async(data)

def retry_connect(serv, addr, count):
    for i in xrange(count):
        try:
            serv.connect(addr)
        except socket.error:
            time.sleep(1)
        else:
            return

    serv.connect(addr)

def setup_globals():
    if not os.path.exists(DATADIR + '/fcweb'):
        os.symlink('classic', DATADIR + '/fcweb')

def is_port_free(port):
    s = socket.socket()
    try:
        s.connect(('localhost', port))
    except socket.error:
        return True
    else:
        return False

def choose_port():
    # not entirely thread safe
    for i in xrange(1000):
        port = random.randrange(PORT_START, PORT_END)
        if is_port_free(port):
            return port
    raise Exception('failed to find free port')

if __name__ == '__main__':
    thread = multisock.SocketThread()
    Client(thread)
    thread.loop()
