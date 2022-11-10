# -*- coding: utf-8 -*-
import cherrypy_cors
import cherrypy
import click
import six

from girderformindlogger import _attachFileLogHandlers
from girderformindlogger.utility import server
from girderformindlogger.constants import ServerMode


@click.command(name='serve', short_help='Run the Girder server.', help='Run the Girder server.')
@click.option('--dev', default=False, is_flag=True, help='Alias for --mode=development')
@click.option('--mode', type=click.Choice([
    ServerMode.PRODUCTION,
    ServerMode.DEVELOPMENT,
    ServerMode.TESTING
    ]), default=None, show_default=True, help='Specify the server mode')
@click.option('-d', '--database', default=cherrypy.config['database']['uri'],
              show_default=True, help='The database URI to connect to')
@click.option('-H', '--host', default=cherrypy.config['server.socket_host'],
              show_default=True, help='The interface to bind to')
@click.option('-p', '--port', type=int, default=cherrypy.config['server.socket_port'],
              show_default=True, help='The port to bind to')
def main(dev, mode, database, host, port):
    if dev and mode:
        raise click.ClickException('Conflict between --dev and --mode')
    if dev:
        mode = ServerMode.DEVELOPMENT

    # If the user provides no options, the existing config values get re-set through click
    cherrypy.config['database']['uri'] = database
    if six.PY2:
        # On Python 2, click returns the value as unicode and CherryPy expects a str
        # Keep this conversion explicitly for Python 2 only, so it can be removed when Python 2
        # support is dropped
        host = str(host)
    cherrypy_cors.install()
    cherrypy.config['server.socket_host'] = host
    cherrypy.config['server.socket_port'] = port
    cherrypy.config['cors.expose.on'] = True

    _attachFileLogHandlers()
    server.setup(mode)

    cherrypy.engine.start()
    cherrypy.engine.block()
