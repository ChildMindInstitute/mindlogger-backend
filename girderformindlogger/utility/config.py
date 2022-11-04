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

    if 'GIRDER_HOST' in os.environ:
        host = os.environ['GIRDER_HOST']
        cherrypy.config['server.socket_host'] = host

    cherrypy.config['database'] = _get_database()

    if 'GIRDER_TEST_DB' in os.environ:
        cherrypy.config['database']['uri'] = \
            os.environ['GIRDER_TEST_DB'].replace('.', '_')

    cherrypy.config['sentry']['backend_dsn'] = os.environ.get('SENTRY_DNS', None)
    cherrypy.config['firebase_key'] = os.environ.get('FIREBASE_KEY', None)

    if 'AES_KEY' in os.environ:
        cherrypy.config['aes_key'] = bytes(os.getenv('AES_KEY'), 'utf8')

    cherrypy.config['redis'] = _get_redis()


def getConfig():
    if 'database' not in cherrypy.config:
        loadConfig()
    # When in Sphinx, cherrypy may be mocked and returning None\
    return cherrypy.config or {}


def getServerMode():
    return getConfig()['server']['mode']


def _get_database():
    host = os.environ.get('MONGO_HOST', '')
    port = os.environ.get('MONGO_PORT', '')
    name = os.environ.get('MONGO_DB_NAME', '')
    uri = f"{host}:{port}/{name}"
    if uri != '':
        return dict(uri=f'mongodb://{uri}')
    return dict()


def _get_redis():
    return dict(
        host=os.environ.get('REDIS_HOST', 'localhost'),
        port=os.environ.get('REDIS_PORT', 6379),
        password=os.environ.get('REDIS_PASSWORD', '')
    )
