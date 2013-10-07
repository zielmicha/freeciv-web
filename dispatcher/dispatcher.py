import sys
sys.path.append('../multisock')

import multisock
import json
import time
import threading
import collections

DISPATCHER_ADDR = 'tcp:localhost:7001'
CLIENT_ADDR = 'tcp:localhost:7002'

MAX_INACTIVITY_TIME = 120

ERROR_MSG = [{'pid': 5}] # Join reply message

def main():
    global pool
    pool = ConnectionPool()
    thread = multisock.SocketThread()
    thread.listen(DISPATCHER_ADDR).accept.bind(DispatcherHandler)
    thread.listen(CLIENT_ADDR).accept.bind(Connection)
    thread.loop()

class DispatcherHandler(object):
    def __init__(self, sock):
        self.channel = sock.get_main_channel()
        self.channel.recv.bind(self.recv)
        self.sid = None

    def recv(self, data):
        message = json.loads(data)
        print 'recv', repr(message)
        if not self.sid:
            self.sid = message['session_id']

        try:
            connection = pool.get_connection(self.sid)
        except NoFreeConnections:
            self.channel.send_async(json.dumps(ERROR_MSG))
            return

        connection.recv.bind(self.send)

        pool.refresh(self.sid)
        connection.send_async(json.dumps(message))

    def send(self, data):
        self.channel.send_async(data)

class ConnectionPool(object):
    '''
    Pool of connection to Freeciv servers.
    '''
    def __init__(self):
        self.connections = {}
        self.active_time = {}
        self.free_connections = collections.deque()
        self.lock = threading.RLock()

    def get_connection(self, sid):
        with self.lock:
            if sid not in self.connections:
                self.connections[sid] = self._allocate()

            return self.connections[sid]


    def refresh(self, sid):
        self.active_time[sid] = time.time()

    def gc(self):
        with self.lock:
            for sid, active_time in self.active_time.items():
                if active_time + MAX_INACTIVITY_TIME < time.time():
                    self.kill_connection(sid)

    def kill_connection(self, sid):
        with self.lock:
            self.connections[sid].kill()
            self.free_connections.appendleft(self.connections[sid])
            self.connections[sid] = None

    def _allocate(self):
        if not self.free_connections:
            raise NoFreeConnections()
        else:
            conn = self.free_connections.pop()
            return conn.allocate()

class Connection(object):
    def __init__(self, sock):
        self.sock = sock
        self.main = self.sock.get_main_channel()
        self.main.recv.bind(self._recv)

    def _recv(self, msg):
        count = int(msg)
        with pool.lock:
            print self.sock._socket.getpeername(), 'offered', count, 'servers'
            for i in xrange(count):
                pool.free_connections.appendleft(self)

    def allocate(self):
        current = self.sock.new_channel()
        self.main.send_async('allocate %d' % current.id)
        return current

    def kill(self, channel):
        self.main.send_async('kill %D' % self.channel.id)
        self.current = None

class NoFreeConnections(Exception): pass

if __name__ == '__main__':
    main()
