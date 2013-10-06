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

import time
from tornado import web, websocket, ioloop, httpserver
import logging
import json
import pprint

from debugging import *
from civcom import *

PROXY_PORT = 8002

civcoms = {}

class IndexHandler(web.RequestHandler):
    """
    Serves the Freeciv-proxy index page
    """

    def get(self):
        self.write(
            u"Freeciv-web websocket proxy, port: " + unicode(PROXY_PORT))


class StatusHandler(web.RequestHandler):
    """
    Serves the Freeciv-proxy status page, on the url:  /status
    """

    def get(self):
        self.write(get_debug_info(civcoms))


class WSHandler(websocket.WebSocketHandler):
    clients = []
    logger = logging.getLogger('freeciv-proxy')
    logger.setLevel(logging.DEBUG)

    def open(self):
        self.clients.append(self)
        self.is_ready = False
        self.set_nodelay(True)

    def on_message(self, message):
        self.logger.debug('ws message %s', pprint.pformat(json.loads(message)))
        if not self.is_ready:
            # called the first time the user connects.
            login_message = json.loads(message)
            self.username = login_message[u'username']
            self.civserverport = login_message[u'port']
            self.ip = self.request.headers.get(u"X-Real-IP", u"missing")
            self.loginpacket = message
            self.is_ready = True
            self.civcom = self.get_civcom(
                self.username, self.civserverport, self)
            return

        # get the civcom instance which corresponds to this user.
        self.civcom = self.get_civcom(self.username, self.civserverport, self)

        if self.civcom == None:
            self.write_message(u"Error: Could not authenticate user.")
            return

        # send JSON request to civserver.
        self.civcom.queue_to_civserver(message)

    def on_close(self):
        self.clients.remove(self)
        if hasattr(self, u'civcom') and self.civcom != None:
            self.civcom.stopped = True
            self.civcom.close_connection()
            if self.civcom.key in list(civcoms.keys()):
                del civcoms[self.civcom.key]

    # get the civcom instance which corresponds to the requested user.
    def get_civcom(self, username, civserverport, ws_connection):
        key = username + unicode(civserverport)
        if key not in list(civcoms.keys()):
            if (int(civserverport) < 5500):
                return None
            civcom = CivCom(username, int(civserverport), self)
            civcom.start()
            civcoms[key] = civcom

            time.sleep(0.4)
            return civcom
        else:
            usrcivcom = civcoms[key]
            return usrcivcom


if __name__ == u"__main__":
    try:
        print u'Started Freeciv-proxy. Use Control-C to exit'

        if len(sys.argv) == 2:
            PROXY_PORT = int(sys.argv[1])
        print (u'port: ' + unicode(PROXY_PORT))

        LOG_FILENAME = u'/tmp/logging' + unicode(PROXY_PORT) + u'.out'
        # logging.basicConfig(filename=LOG_FILENAME,level=logging.INFO)
        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger(u"freeciv-proxy")

        application = web.Application([
            (ur'/civsocket', WSHandler),
            (ur"/", IndexHandler),
            (ur"/status", StatusHandler),
        ])

        http_server = httpserver.HTTPServer(application)
        http_server.listen(PROXY_PORT)
        ioloop.IOLoop.instance().start()

    except KeyboardInterrupt:
        print u'Exiting...'
