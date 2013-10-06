# -*- coding: latin-1 -*-

u'''
 Freeciv - Copyright (C) 2009-2013 - Andreas Røsdal   andrearo@pvv.ntnu.no
   This program is free software; you can redistribute it and/or modify
   it under the terms of the GNU General Public License as published by
   the Free Software Foundation; either version 2, or (at your option)
   any later version.

   This program is distributed in the hope that it will be useful,
   but WITHOUT ANY WARRANTY; without even the implied warranty of
   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
   GNU General Public License for more details.
'''

import socket
import select
from struct import *
import threading
import logging
import time


DISPATCHER_ADDR = ('localhost', 8003)

logger = logging.getLogger(u"freeciv-proxy")
civcoms = {}

def get_civcom(username, session_id, login_packet):
    if session_id not in civcoms:
        civcom = CivCom(username, session_id, login_packet)
        civcom.start()
        civcoms[session_id] = civcom

        time.sleep(0.4)

    return civcoms[session_id]

class CivCom(object):
    def __init__(self, username, session_id, login_packet):
        self.socket = None
        self.username = username
        self.session_id = session_id
        self.packet_callback = None

        self.connect_time = time.time()
        self.civserver_messages = [login_packet]
        self.stopped = False

        self.packet_size = -1
        self.net_buf = bytearray(0)
        self.header_buf = bytearray(0)
        self.send_buffer = []

    def start(self):
        t = threading.Thread(target=self.run)
        t.daemon = True
        t.start()

    def run(self):
        self.connect_socket()

        # send initial login packet to civserver
        self.send_packets_to_civserver()

        # receive packets from server
        while 1:
            packet = self.read_from_connection()

            if (self.stopped):
                return

            if (packet != None):
                self.net_buf += packet

                if (len(self.net_buf) == self.packet_size and self.net_buf[-1] == 0):
                    # valid packet received from freeciv server, send it to
                    # client.
                    self.send_buffer_append(self.net_buf[:-1])
                    self.packet_size = -1
                    self.net_buf = bytearray(0)
                    continue

            time.sleep(0.01)
            # prevent max CPU usage in case of error

    def connect_socket(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect(DISPATCHER_ADDR)
        f = self.socket.makefile('r+', 0)
        f.write(json.dumps({'session_id': self.session_id}))
        response = json.loads(f.readline())
        if response.get('error'):
            raise CivComError(response['error'])

    def read_from_connection(self):
        try:
            if (self.socket != None and not self.stopped):
                if (self.packet_size == -1):
                    self.header_buf += self.socket.recv(
                        4 - len(self.header_buf))
                    if (len(self.header_buf) == 0):
                        self.close_connection()
                        return None
                    if (len(self.header_buf) == 4):
                        header_pck = unpack(u'>HH', self.header_buf)
                        self.header_buf = bytearray(0)
                        self.packet_size = header_pck[0] - 4
                        if (self.packet_size <= 0 or self.packet_size > 32767):
                            logger.error(u"Invalid packet size.")
                    else:
                        # complete header not read yet. return now, and read
                        # the rest next time.
                        return None

            if (self.socket != None and self.net_buf != None and self.packet_size > 0):
                data = self.socket.recv(self.packet_size - len(self.net_buf))
                if (len(data) == 0):
                    self.close_connection()
                    return None

                return data
        except socket.timeout:
            self.send_packets_to_client()
            self.send_packets_to_civserver()
            return None
        except OSError:
            return None

    def close_connection(self):
        logger.info(
            u"Server connection closed. Removing civcom thread for " + self.username)

        try:
            del civcoms[self.session_id]
        except KeyError:
            pass

        if self.socket is not None:
            self.socket.close()
            self.socket = None

        self.stopped = True

    # queue messages to be sent to client.
    def send_buffer_append(self, data):
        try:
            self.send_buffer.append(
                data.decode(encoding=u"utf-8", errors=u"ignore"))
        except UnicodeDecodeError:
            logger.error(
                "Unable to decode string from civcom socket, for user: " + self.username)
            return

    # sends packets to client (WebSockets client / browser)
    def send_packets_to_client(self):
        packet = self.get_client_result_string()
        if packet is not None and self.packet_callback:
            self.packet_callback(packet)

    def get_client_result_string(self):
        result = u""
        try:
            if len(self.send_buffer) > 0:
                result = u"[" + u",".join(self.send_buffer) + u"]"
            else:
                result = None
        finally:
            del self.send_buffer[:]
        return result

    def send_error_to_client(self, message):
        logger.error(message)
        self.send_buffer_append(
            (u"{\"pid\":18,\"message\":\"" + message + u"\"}").encode(u"utf-8"))

    # Send packets from freeciv-proxy to civserver
    def send_packets_to_civserver(self):
        if (self.civserver_messages is None or self.socket is None):
            return

        try:
            for net_message in self.civserver_messages:
                header = pack(u'>HH', len(net_message), 0)
                self.socket.sendall(
                    header + net_message.encode(u'utf-8') + '\0')
        except:
            self.send_error_to_client(u"Proxy unable to communicate with civserver on port "
                                      + unicode(self.civserverport))
        finally:
            self.civserver_messages = []

    # queue message for the civserver
    def queue_to_civserver(self, message):
        self.civserver_messages.append(message)

class CivComError(Exception):
    pass
