# -*- coding: latin-1 -*-

u'''
 Freeciv - Copyright (C) 2009-2013 - Andreas R�sdal   andrearo@pvv.ntnu.no
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
from threading import Thread
import logging
import time

HOST = u'127.0.0.1'
logger = logging.getLogger(u"freeciv-proxy")

# The CivCom handles communication between freeciv-proxy and the Freeciv C
# server.


class CivCom(Thread):

    def __init__(self, username, civserverport, civwebserver):
        Thread.__init__(self)
        self.socket = None
        self.username = username
        self.civserverport = civserverport
        self.key = username + unicode(civserverport)
        self.send_buffer = []
        self.connect_time = time.time()
        self.civserver_messages = []
        self.stopped = False
        self.packet_size = -1
        self.net_buf = bytearray(0)
        self.header_buf = bytearray(0)
        self.daemon = True
        self.civwebserver = civwebserver

    def run(self):
        # setup connection to civserver
        if (logger.isEnabledFor(logging.INFO)):
            logger.info(u"Start connection to civserver for " + self.username
                        + u" from IP " + self.civwebserver.ip)
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setblocking(True)
        self.socket.settimeout(2)
        try:
            self.socket.connect((HOST, self.civserverport))
            self.socket.settimeout(0.01)
        except socket.error, reason:
            self.send_error_to_client(
                u"Proxy unable to connect to civserver. Error: %s" % (reason))
            return

        # send initial login packet to civserver
        self.civserver_messages = [self.civwebserver.loginpacket]
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
        if (logger.isEnabledFor(logging.INFO)):
            logger.info(
                u"Server connection closed. Removing civcom thread for " + self.username)

        if (hasattr(self.civwebserver, u"civcoms") and self.key in list(self.civwebserver.civcoms.keys())):
            del self.civwebserver.civcoms[self.key]

        if (self.socket != None):
            self.socket.close()
            self.socket = None

        self.stopped = True

    # queue messages to be sent to client.
    def send_buffer_append(self, data):
        try:
            self.send_buffer.append(
                data.decode(encoding=u"utf-8", errors=u"ignore"))
        except UnicodeDecodeError:
            if (logger.isEnabledFor(logging.ERROR)):
                logger.error(
                    u"Unable to decode string from civcom socket, for user: " + self.username)
            return

    # sends packets to client (WebSockets client / browser)
    def send_packets_to_client(self):
        packet = self.get_client_result_string()
        if (packet != None and self.civwebserver != None):
            self.civwebserver.write_message(packet)

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
        if (logger.isEnabledFor(logging.ERROR)):
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
