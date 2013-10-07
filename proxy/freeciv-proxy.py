#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Copyright (C) 2011-2013 - Andreas Rasdal <andrearo@pvv.ntnu.no>
Copyright (C) 2013 - Michał Zieliński <michal@zielinscy.org.pl>

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2, or (at your option)
any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.
'''
from tornado import web, websocket, ioloop, httpserver

import time
import logging
import json
import pprint
import traceback
import threading

import redis

PROXY_PORT = 8002

class WSHandler(websocket.WebSocketHandler):
    clients = []
    logger = logging.getLogger('freeciv-proxy')
    logger.setLevel(logging.DEBUG)

    def open(self):
        self.clients.append(self)
        self.channel = None
        self.set_nodelay(True)
        self.session_id = None
        self.stop = False

    def on_message(self, message):
        message = json.loads(message)
        self.logger.debug('ws message %s', pprint.pformat(message))
        if not self.session_id:
            self.session_id = message['session_id']
            if not redis_instance.hget('fcrunning', self.session_id):
                redis_instance.rpush('fcmaster', self.session_id)
            else:
                print 'fcmaster %r already running' % self.session_id
            t = threading.Thread(target=self.ws_writer)
            t.daemon = True
            t.start()

        self.relay_message(message)

    def relay_message(self, message):
        data = json.dumps(message)
        redis_instance.rpush('fcsess_write_' + self.session_id, data)

    def write_to_ws(self, data):
        ioloop.IOLoop.instance().add_callback(self.write_message, data)

    def ws_writer(self):
        while not self.stop:
            val = redis_instance.blpop(['fcsess_read_' + self.session_id], timeout=10)
            if val:
                channel, data = val
                self.logger.debug('server message %r', data)
                self.write_to_ws(data)

    def on_close(self):
        self.stop = True

def message_recv(data):
    try:
        message = json.loads(data)
        ws_handlers[message['session_id']].write_to_ws(message['message'])
    except:
        traceback.print_exc()

if __name__ == u"__main__":
    application = web.Application([
        (r'/civsocket', WSHandler),
    ])

    redis_instance = redis.Redis()

    http_server = httpserver.HTTPServer(application)
    http_server.listen(PROXY_PORT)
    ioloop.IOLoop.instance().start()
