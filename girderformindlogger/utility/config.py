# -*- coding: utf-8 -*-
import cherrypy
import os
import six

import girderformindlogger
from girderformindlogger.constants import PACKAGE_DIR


def _mergeConfig(filename):
    """
    Load `filename` into the cherrypy config.
    Also, handle global options by putting them in the root.
    """
    cherrypy._cpconfig.merge(cherrypy.config, filename)
    # When in Sphinx, cherrypy may be mocked and returning None
    global_config = cherrypy.config.pop('global', {}) or {}

    for option, value in six.viewitems(global_config):
        cherrypy.config[option] = value


def _loadConfigsByPrecedent():
    """
    Load configuration in reverse order of precedent.
    """
    # TODO: Deprecated, remove in a later version
    def _printConfigurationWarning():
        girderformindlogger.logprint.warning(
            'Detected girderformindlogger.local.cfg, this location is no longer supported.\n'
            'For supported locations, see '
            'https://girderformindlogger.readthedocs.io/en/stable/configuration.html#configuration')

    if os.path.exists(os.path.join(PACKAGE_DIR, 'conf', 'girderformindlogger.local.cfg')):
        # This can't use logprint since configuration is loaded before initialization.
        # Note this also won't be displayed when starting other services that don't start a CherryPy
        # server such as girderformindlogger mount or girderformindlogger sftpd.
        cherrypy.engine.subscribe('start', _printConfigurationWarning)

    configPaths = [os.path.join(PACKAGE_DIR, 'conf', 'girder.dist.cfg'),
                   os.path.join('/etc', 'girder.cfg'),
                   os.path.join(os.path.expanduser('~'), '.girderformindlogger', 'girder.cfg')]

    if 'GIRDER_CONFIG' in os.environ:
        configPaths.append(os.environ['GIRDER_CONFIG'])

    for curConfigPath in configPaths:
        if os.path.exists(curConfigPath):
            _mergeConfig(curConfigPath)


def loadConfig():

    _loadConfigsByPrecedent()

    if 'GIRDER_PORT' in os.environ:
        port = int(os.environ['GIRDER_PORT'])
        cherrypy.config['server.socket_port'] = port

    if 'database' not in cherrypy.config:
        cherrypy.config['database'] = {}

    if 'GIRDER_MONGO_URI' in os.environ:
        cherrypy.config['database']['uri'] = os.getenv('GIRDER_MONGO_URI')

    if 'GIRDER_TEST_DB' in os.environ:
        cherrypy.config['database']['uri'] =\
            os.environ['GIRDER_TEST_DB'].replace('.', '_')

    if 'AES_KEY' in os.environ:
        cherrypy.config['aes_key'] = bytes(os.getenv('AES_KEY'), 'utf8')

    cherrypy.config['redis_uri'] = os.getenv('REDIS_URI', 'redis://localhost/0')

def getConfig():
    if 'database' not in cherrypy.config:
        loadConfig()
    # When in Sphinx, cherrypy may be mocked and returning None\
    return cherrypy.config or {}


def getServerMode():
    return getConfig()['server']['mode']
