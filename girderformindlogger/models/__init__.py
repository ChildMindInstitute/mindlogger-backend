# -*- coding: utf-8 -*-
import pymongo
import six
from six.moves import urllib

from girderformindlogger import logger, logprint
from girderformindlogger.external.mongodb_proxy import MongoProxy
from girderformindlogger.utility import config
from bson.objectid import ObjectId

_dbClients = {}


def getDbConfig():
    """Get the database configuration values from the cherrypy config."""
    cfg = config.getConfig()
    if 'database' in cfg:
        return cfg['database']
    else:
        return {}

_redisClient = None
def getRedisConnection():
    global _redisClient

    from redis import Redis, ConnectionPool

    if _redisClient:
        return _redisClient

    cfg = config.getConfig()
    pool = ConnectionPool(**cfg['redis'])
    _redisClient = Redis(connection_pool=pool)
    return _redisClient

def getDbConnection(uri=None, replicaSet=None, autoRetry=True, quiet=False, **kwargs):
    """
    Get a MongoClient object that is connected to the configured database.
    We lazy-instantiate a module-level singleton, the MongoClient objects
    manage their own connection pools internally. Any extra kwargs you pass to
    this method will be passed through to the MongoClient.

    :param uri: if specified, connect to this mongo db rather than the one in
                the config.
    :param replicaSet: if uri is specified, use this replica set.
    :param autoRetry: if this connection should automatically retry operations
        in the event of an AutoReconnect exception. If you're testing the
        connection, set this to False. If disabled, this also will not cache
        the mongo client, so make sure to only disable if you're testing a
        connection.
    :type autoRetry: bool
    :param quiet: if true, don't logprint warnings and success.
    :type quiet: bool
    """
    global _dbClients

    origKey = (uri, replicaSet)
    if origKey in _dbClients:
        return _dbClients[origKey]

    dbConf = getDbConfig()

    if uri is None or uri == '':
        uri = dbConf.get('uri')
        replicaSet = dbConf.get('replica_set')

    clientOptions = {
        # This is the maximum time between when we fetch data from a cursor.
        # If it times out, the cursor is lost and we can't reconnect.  If it
        # isn't set, we have issues with replica sets when the primary goes
        # down.  This value can be overridden in the mongodb uri connection
        # string with the socketTimeoutMS.
        'socketTimeoutMS': 60000,
        'connectTimeoutMS': 20000,
        'serverSelectionTimeoutMS': 20000,
        'readPreference': 'secondaryPreferred',
        'replicaSet': replicaSet,
        'w': 'majority'
    }

    # All other options in the [database] section will be passed directly as
    # options to the mongo client
    for opt, val in six.viewitems(dict(dbConf)):
        if opt not in {'uri', 'replica_set'}:
            clientOptions[opt] = val

    # Finally, kwargs take precedence
    clientOptions.update(kwargs)
    # if the connection URI overrides any option, honor it above our own
    # settings.
    uriParams = urllib.parse.parse_qs(urllib.parse.urlparse(uri).query)
    for key in uriParams:
        if key in clientOptions:
            del clientOptions[key]

    if uri is None:
        dbUriRedacted = 'mongodb://localhost:27017/girderformindlogger'
        if not quiet:
            logprint.warning('WARNING: No MongoDB URI specified, using '
                             'the default value')

        client = pymongo.MongoClient(dbUriRedacted, **clientOptions)
    else:
        parts = uri.split('@')
        if len(parts) == 2:
            dbUriRedacted = 'mongodb://' + parts[1]
        else:
            dbUriRedacted = uri

        client = pymongo.MongoClient(uri, **clientOptions)

    if not quiet:
        desc = ''
        if replicaSet:
            desc += ', replica set: %s' % replicaSet
        logprint.info('Connecting to MongoDB: %s%s' % (dbUriRedacted, desc))

    # Make sure we can connect to the mongo server at startup
    client.server_info()

    if autoRetry:
        client = MongoProxy(client, logger=logger)
        _dbClients[origKey] = _dbClients[(uri, replicaSet)] = client

    return client


def pluralize(modelType):
    return('{}s'.format(
        modelType[:-1] if modelType.endswith(
            's'
        ) else "{}ie".format(modelType[:-1]) if modelType.endswith(
            'y'
        ) else modelType
    ))


def cycleModels(IRIset, modelType=None, meta={}):
    from girderformindlogger.constants import REPROLIB_TYPES
    from girderformindlogger.models.folder import Folder as FolderModel
    from girderformindlogger.models.item import Item as ItemModel

    cachedDoc = None

    if not modelType:
        if 'appletId' in meta:
            modelType = 'protocol'
        elif 'activityId' in meta:
            modelType = 'screen'
        elif 'protocolId' in meta:
            modelType = 'activity'
        else:
            return (None, None)
    else:
        if isinstance(modelType, list):
            modelType = modelType[0]

    reprolibType = REPROLIB_TYPES[modelType]

    query = {
        'meta.{}.@type'.format(modelType): reprolibType,
        'meta.{}.url'.format(modelType): {
            '$in': list(IRIset)
        }
    }

    for key in meta:
        query['meta.{}'.format(key)] = meta[key]

    cachedDoc = ItemModel().findOne(query) if modelType == 'screen' else FolderModel().findOne(query)

    if cachedDoc is None:
        return(None, None)

    modelType = [
        rt for rt in list(
            REPROLIB_TYPES.keys()
        ) if '@type' in cachedDoc.get('meta', {}).get(rt, {})
    ]
    modelType = modelType[0] if len(modelType) else None

    print("Found {}/{}".format(modelType, str(cachedDoc['_id'])))
    return(modelType, cachedDoc)


def smartImport(IRI, user=None, refreshCache=False, modelType=None, meta={}):
    from girderformindlogger.constants import MODELS
    from girderformindlogger.utility.jsonld_expander import loadCache,         \
        reprolibCanonize

    MODELS = MODELS()
    mt1 = "screen" if modelType in [
        None,
        "external JSON-LD document"
    ] else modelType
    model, modelType = MODELS[mt1]().getFromUrl(
        IRI,
        user=user,
        refreshCache=refreshCache,
        thread=False,
        meta=meta
    )
    return((
        modelType,
        loadCache(model.get('cached')) if model.get('cached') else model,
        reprolibCanonize(IRI)
    ))
