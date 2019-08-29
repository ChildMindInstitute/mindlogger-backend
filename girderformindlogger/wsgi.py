# -*- coding: utf-8 -*-
import cherrypy
import girderformindlogger
from girderformindlogger.utility import server

cherrypy.config.update({'engine.autoreload.on': False,
                        'environment': 'embedded'})
cherrypy.config['server'].update({'disable_event_daemon': True})

# TODO The below line can be removed if we do away with girderformindlogger.logprint
girderformindlogger._quiet = True  # This means we won't duplicate messages to stdout/stderr
_formatter = girderformindlogger.LogFormatter('[%(asctime)s] %(levelname)s: %(message)s')
_handler = cherrypy._cplogging.WSGIErrorHandler()
_handler.setFormatter(_formatter)
girderformindlogger.logger.addHandler(_handler)

# 'application' is the default callable object for WSGI implementations, see PEP 3333 for more.
server.setup()
application = cherrypy.tree

cherrypy.server.unsubscribe()
cherrypy.engine.start()
