import threading
import subprocess
import os
import random
import socket
import select
import struct
import time
import logging
import json

import redis

PORT_START = 20000
PORT_END = 40000
DISPATCHER = 'tcp:localhost:7002'
INIT_SERVERS = 10

FCBASE = '../freeciv/freeciv'
SERVER = FCBASE + '/server/freeciv-web'
DATADIR = FCBASE + '/data'

logger = logging.getLogger('client')
logger.setLevel(logging.INFO)

serv_logger = logging.getLogger('server')
serv_logger.setLevel(logging.DEBUG)

class Client(object):
    def __init__(self):
        self.redis = redis.Redis()

    def main(self):
        while True:
            val = self.redis.blpop(['fcmaster'], timeout=10)

            if val:
                channel, session_id = val
                #self.redis.hset('fcrunning', session_id, 'true')
                self.start_server(session_id)

    def start_server(self, channel):
        async(lambda: self.run_server(channel))

    def run_server(self, session_id):
        setup_globals()
        port = choose_port()
        logging.info('starting server at port %d', port)
        proc = subprocess.Popen([SERVER,
                                 '--exit-on-end',
                                 '--port', '%s' % port,
                                 '--debug', '2'],
                                env=dict(os.environ, FREECIV_DATA_PATH=DATADIR),
                                stdin=open('/dev/null'),
                                stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT)

        def server_log():
            for line in iter(proc.stdout.readline, ''):
                serv_logger.debug(line.strip())

        async(server_log)

        def copier():
            saw_login = False
            while True:
                channel, data = self.redis.blpop(['fcsess_write_' + session_id])
                packet = json.loads(data)
                if not saw_login and 'capability' not in packet:
                    # skip possibly stale packet
                    continue
                else:
                    # force compatibility
                    packet['minor_version'] = 5
                    packet['capability'] = '+Freeciv.Web.Devel-2.6-2013.May.25'
                    saw_login = True
                logger.info('remote: %r', packet)
                data = json.dumps(packet)
                header = struct.pack('>HH', len(data), 0)
                serv.sendall(header + data + '\0')

        serv = socket.socket()
        retry_connect(serv, ('localhost', port), count=5)
        async(copier)
        logging.info('connected')
        while True:
            r, w, x = select.select([serv], [], [])
            header = serv.recv(4)
            if not header:
                break
            length, _ = struct.unpack('>HH', header)

            data = serv.makefile('r+').read(length - 4)
            data = data.rstrip('\0')
            logger.debug('server: %r', data)

            self.redis.rpush('fcsess_read_' + session_id, data)

        logger.info('server connection closed')

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

def async(func):
    t = threading.Thread(target=func)
    t.daemon = True
    t.start()

if __name__ == '__main__':
    Client().main()
