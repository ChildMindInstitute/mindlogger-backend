from bson import json_util
from copy import deepcopy
from datetime import datetime
from girderformindlogger.constants import AccessType, DEFINED_RELATIONS,       \
    HIERARCHY, KEYS_TO_DELANGUAGETAG, KEYS_TO_DEREFERENCE, KEYS_TO_EXPAND,     \
    MODELS, NONES, REPROLIB_CANONICAL, REPROLIB_PREFIXES
from girderformindlogger.exceptions import AccessException,                    \
    ResourcePathNotFound, ValidationException
from girderformindlogger.models.activity import Activity as ActivityModel
from girderformindlogger.models.applet import Applet as AppletModel
from girderformindlogger.models.collection import Collection as CollectionModel
from girderformindlogger.models.folder import Folder as FolderModel
from girderformindlogger.models.item import Item as ItemModel
from girderformindlogger.models.protocol import Protocol as ProtocolModel
from girderformindlogger.models.screen import Screen as ScreenModel
from girderformindlogger.models.user import User as UserModel
from girderformindlogger.utility.response import responseDateList
from pyld import jsonld


def getModelCollection(modelType):
    """
    Returns the Collection named for the given modelType, creating if not
    already extant.

    :param modelType: 'activity', 'screen', etc.
    :type modelType: str
    :returns: dict
    """
    from girderformindlogger.models import pluralize
    name = pluralize(modelType).title()
    collection = CollectionModel().findOne(
        {'name': name}
    )
    if not collection:
        collection = CollectionModel().createCollection(
            name=name,
            public=True,
            reuseExisting=True
        )
    return(collection)


def importAndCompareModelType(model, url, user):
    import threading
    from girderformindlogger.utility import firstLower

    if model is None:
        return(None, None)
    atType = model.get('@type', '').split('/')[-1].split(':')[-1]
    modelType = firstLower(atType) if len(atType) else modelType
    modelType = 'screen' if modelType.lower(
    )=='field' else 'protocol' if modelType.lower(
    )=='activityset' else modelType
    changedModel = (atType != modelType and len(atType))
    modelType = firstLower(atType) if changedModel else modelType
    modelType = 'screen' if modelType.lower(
    )=='field' else 'protocol' if modelType.lower(
    )=='activityset' else modelType
    modelClass = MODELS()[modelType]()
    prefName = modelClass.preferredName(model)
    cachedDocObj = {}
    print("Loaded {}".format(": ".join([modelType, prefName])))
    docCollection=getModelCollection(modelType)
    if modelClass.name in ['folder', 'item']:
        docFolder = FolderModel().createFolder(
            name=prefName,
            parent=docCollection,
            parentType='collection',
            public=True,
            creator=user,
            allowRename=True,
            reuseExisting=(modelType!='applet')
        )
        if modelClass.name=='folder':
            newModel = modelClass.setMetadata(
                docFolder,
                {
                    modelType: {
                        **model,
                        'schema:url': url,
                        'url': url
                    }
                }
            )
        elif modelClass.name=='item':
            newModel = modelClass.setMetadata(
                modelClass.createItem(
                    name=prefName if prefName else str(len(list(
                        FolderModel().childItems(
                            FolderModel().load(
                                docFolder,
                                level=None,
                                user=user,
                                force=True
                            )
                        )
                    )) + 1),
                    creator=user,
                    folder=docFolder,
                    reuseExisting=True
                ),
                {
                    modelType: {
                        **model,
                        'url': url
                    }
                }
            )
    formatted = _fixUpFormat(formatLdObject(
        newModel,
        mesoPrefix=modelType,
        user=user,
    ))
    thread = threading.Thread(
        target=createCache,
        args=(newModel, formatted, modelType, user)
    )
    thread.start()
    return(formatted, modelType)


def _createContextForStr(s):
    sp = s.split('/')
    k = '_'.join(
        sp[:-1] if '.' not in sp[-1] else sp
    ).replace('.','').replace(':','')
    return(
        (
            {k: '{}/'.format('/'.join(sp[:-1]))},
            "{}:{}".format(k, sp[-1])
        ) if '.' not in sp[-1] else (
            {k: s},
            k
        )
    )


def contextualize(ldObj):
    newObj = {}
    context = ldObj.get('@context', [])
    if isinstance(context, list):
        context.append(
            {
                "reprolib": REPROLIB_CANONICAL
            }
        )
    elif isinstance(context, dict):
        context["reprolib"] = REPROLIB_CANONICAL
    for k in ldObj.keys():
        if isinstance(ldObj[k], dict):
            context, newObj[k] = _deeperContextualize(
                ldObj[k],
                context
            )
        else:
            newObj[k] = ldObj[k]
    newObj['@context'] = reprolibCanonize(context)
    return(newObj)


def _deeperContextualize(ldObj, context):
    newObj = {}
    for k in ldObj.keys():
        if isinstance(ldObj[k], dict) and '.' in k:
                (c, o) = _createContextForStr(k)
                newObj[o] = ldObj[k]
                if c not in context:
                    context.append(c)
        else:
            newObj[k] = reprolibPrefix(ldObj[k])
    return(context, newObj)


def inferRelationships(person):
    from girderformindlogger.models.invitation import Invitation
    from girderformindlogger.models.profile import Profile

    if "schema:knows" not in person:
        return(person)
    start = deepcopy(person)
    for rel in list(person['schema:knows'].keys()):
        if rel in DEFINED_RELATIONS.keys():
            if "owl:equivalentProperty" in DEFINED_RELATIONS[rel]:
                for ep in DEFINED_RELATIONS[rel]["owl:equivalentProperty"]:
                    if ep not in person['schema:knows']:
                        person['schema:knows'][ep] = []
                    for related in person['schema:knows'][rel]:
                        if related not in person['schema:knows'][ep]:
                            person['schema:knows'][ep].append(related)
    if any([
        bool(
            rp not in start.get('schema:knows', {}).get(rel, [])
        ) for rp in person['schema:knows'][rel] for rel in list(
            person['schema:knows'].keys()
        )
    ]):
        newPerson = Profile().load(person['_id'], force=True)
        if 'schema:knows' in newPerson:
            newPerson['schema:knows'].update(person['schema:knows'])
        else:
            newPerson['schema:knows'] = person['schema:knows']
        Profile().save(
            newPerson,
            validate=False
        ) if 'userId' in newPerson else Invitation().save(
            newPerson,
            validate=False
        )
    return(person)


def oidIffHex(s):
    """
    Function to return a list of the passed string and its ObjectId if the
    passed string is a valid hexidecimal string, or a list of just the passed
    string otherwise.

    :param s: string to check and potentially convert
    :type s: str
    :returns: list of strings, 1≤len≤2
    """
    from bson.objectid import ObjectId
    from bson.errors import InvalidId

    try:
        ObjectId(s)
        return([ObjectId(s), s])
    except InvalidId:
        return([s])


def reprolibPrefix(s):
    """
    Function to check if a string is a reprolib URL, and, if so, compact it to
    the prefix "reprolib:"

    :type s: str
    :returns: str
    """
    if isinstance(s, str):
        for prefix in REPROLIB_PREFIXES:
            if s.startswith(prefix) and s!=prefix:
                return(s.replace(prefix, 'reprolib:'))
    elif isinstance(s, dict):
        for k in s.keys():
            s[k] = reprolibPrefix(
                s[k]
            ) if k not in KEYS_TO_DEREFERENCE else dereference(s[k])
    elif isinstance(s, list):
        s = [reprolibPrefix(li) for li in s]
    return(s)


def reprolibCanonize(s):
    """
    Function to check if a string is a prfixed reprolib URL, and, if so,
    expand it to the current canonical prefix

    :type s: str
    :returns: str
    """
    if isinstance(s, str):
        s = reprolibPrefix(s).replace('reprolib:', REPROLIB_CANONICAL)
        if checkURL(s):
            return(s)
        else:
            return(None)
    elif isinstance(s, list):
        return([reprolibCanonize(ls) for ls in s])
    elif isinstance(s, dict):
        return({
            reprolibCanonize(
                k
            ) if reprolibCanonize(
                k
            ) is not None else k: reprolibCanonize(v) for k, v in s.items()
        })
    return(s)


def delanguageTag(obj):
    """
    Function to take a language-tagged list of dicts and return an untagged
    string.

    :param obj: list of language-tagged dict
    :type obj: list
    :returns: string
    """
    if not isinstance(obj, list):
        return(obj)
    return((obj if len(obj) else [{}])[-1].get("@value", ""))


def expandOneLevel(obj):
    if obj==None:
        return(obj)
    try:
        newObj = jsonld.expand(obj)
    except jsonld.JsonLdError as e: # 👮 Catch illegal JSON-LD
        if e.type == "jsonld.InvalidUrl":
            try:
                newObj = jsonld.expand(reprolibCanonize(obj))
            except:
                print("Invalid URL: {}".format(e.details.get("url")))
                print(obj)
        elif e.cause.type == "jsonld.ContextUrlError":
            invalidContext = e.cause.details.get("url")
            print("Invalid context: {}".format(invalidContext))
            if invalidContext in obj.get("@context", []):
                obj["@context"] = obj["@context"].remove(invalidContext)
                obj["@context"].append(reprolibCanonize(invalidContext))
                if obj["@context"] is None:
                    obj["@context"] = []
            else:
                if isinstance(obj, dict):
                    for k in obj.keys():
                        if invalidContext in obj[k].get("@context", []):
                            obj[k]["@context"] = obj[k]["@context"].remove(
                                invalidContext
                            )
                            if obj[k]["@context"] is None:
                                obj[k]["@context"] = []
                            obj[k]["@context"].append(reprolibCanonize(
                                invalidContext
                            ))
            return(expandOneLevel(obj))
        return(obj)
    newObj = newObj[0] if (
        isinstance(newObj, list) and len(newObj)==1
    ) else newObj
    if isinstance(
        newObj,
        dict
    ):
        if not isinstance(obj, dict):
            obj={}
        for k, v in deepcopy(newObj).items():
            if not bool(v):
                newObj.pop(k)
            else:
                prefix_key = reprolibPrefix(k)
                if prefix_key != k:
                    newObj.pop(k)
                newObj[prefix_key] = reprolibPrefix(
                    v
                ) if prefix_key not in KEYS_TO_DEREFERENCE else dereference(v)
        for k in KEYS_TO_DELANGUAGETAG:
            if k in newObj.keys(
            ) and isinstance(newObj[k], list):
                newObj[k] = delanguageTag(newObj[k])
        newObj.update({
            k: reprolibPrefix(obj.get(k)) for k in obj.keys() if (
                bool(obj.get(k)) and k not in keyExpansion(
                    list(newObj.keys())
                )
            )
        })
        newObj.update({
            k: dereference(newObj[k]) for k in newObj.keys(
            ) if k in KEYS_TO_DEREFERENCE
        })
    return(newObj)


def dereference(prefixed):
    """
    Function to dereference values in given JSON.

    :param prefixed: JSON to dereference
    :type prefixed: dict, list, str, or None
    :returns: dereferenced same-type
    """
    if isinstance(prefixed, str):
        d = reprolibCanonize(prefixed)
        return(d if d is not None else prefixed)
    elif isinstance(prefixed, dict):
        return({
            k: dereference(v) for k, v in prefixed.items()
        })
    elif isinstance(prefixed, list):
        return([dereference(li) for li in prefixed])
    else: # bool, int, float, None
        return(prefixed)


def expand(obj, keepUndefined=False):
    """
    Function to take an unexpanded JSON-LD Object and return it expandeds.

    :param obj: unexpanded JSON-LD Object
    :type obj: dict
    :param keepUndefined: keep undefined-in-context terms?
    :param keepUndefined: bool
    :returns: list, expanded JSON-LD Array or Object
    """
    if obj==None:
        return(obj)
    newObj = expandOneLevel(obj)
    if isinstance(newObj, dict):
        for k in KEYS_TO_EXPAND:
            if k in newObj.keys():
                if isinstance(newObj.get(k), list):
                    v = [
                        expand(lv.get('@id')) for lv in newObj.get(k)
                    ]
                    v = v if v!=[None] else None
                else:
                    v = expand(newObj[k])
                if bool(v):
                    newObj[k] = delanguageTag(
                        v
                    ) if k in KEYS_TO_DELANGUAGETAG else dereference(
                        v
                    ) if k in KEYS_TO_DEREFERENCE else reprolibPrefix(v)
        if k in KEYS_TO_DELANGUAGETAG:
            if k in newObj:
                newObj[k] = reprolibCanonize(
                    delanguageTag(newObj[k])
                )
        if k in KEYS_TO_DEREFERENCE:
            if k in newObj:
                newObj[k] = dereference(newObj[k])
        return(_fixUpFormat(newObj) if bool(newObj) else None)
    else:
        expanded = [expand(n, keepUndefined) for n in newObj]
        return(_fixUpFormat(expanded) if bool(expanded) else None)


def fileObjectToStr(obj):
    """
    Function to load a linked file in a JSON-LD object and return a string.

    :param obj: Object
    :type obj: dict
    :returns: String from loaded file
    """
    import requests
    from requests.exceptions import ConnectionError, MissingSchema
    try:
        r = requests.get(obj.get('@id'))
    except (AttributeError, ConnectionError, MissingSchema):
        r = obj.get("@id") if isinstance(obj, dict) else ""
        raise ResourcePathNotFound("Could not load {}".format(r))
    return(r.text)


def checkURL(s):
    """
    Function to check if a URL is dereferenceable

    :param s: URL
    :type s: string
    :returns: bool
    """
    import requests
    try:
        if (requests.get(s).status_code==404):
            return(False)
        else:
            return(True)
    except:
        return(False)


def compactKeys(obj):
    context = obj.get('@context', [])
    if not isinstance(context, list):
        context = [context]
    newObj = {}
    for k in list(obj.keys()):
        if "." in k:
            c, nk = _createContext(k)
            if c not in context:
                context.append(c)
            nc, newObj[nk] = _deepCompactKeys(obj[k])
            for c in nc:
                if c not in context:
                    context.append(c)
        else:
            nc, newObj[k] = _deepCompactKeys(obj[k])
            for c in nc:
                if c not in context:
                    context.append(c)
    newObj['@context'] = context
    return(newObj)


def _deepCompactKeys(obj):
    context = []
    if not isinstance(obj, dict):
        return(context, obj)
    newObj = {}
    for k in list(obj.keys()):
        if "." in k:
            c, nk = _createContext(k)
            if c not in context:
                context.append(c)
            nc, newObj[nk] = _deepCompactKeys(obj[k])
            for c in nc:
                if c not in context:
                    context.append(c)
        else:
            nc, newObj[k] = _deepCompactKeys(obj[k])
            for c in nc:
                if c not in context:
                    context.append(c)
    return(context, newObj)


def _createContext(key):
    s = key.split('/')
    k = s[-1]
    key = '{}/'.format('/'.join(s[0:-1]))
    return({key.split('://')[-1].replace('.', '_dot_'): key}, k)


def createCache(obj, formatted, modelType, user):
    print(modelType)
    print(MODELS()[modelType])
    obj = MODELS()[modelType]().load(obj['_id'], force=True)
    if "cached" in obj:
        obj["oldCache"] = obj.get("oldCache", []).append(obj["cached"])
    if modelType in NONES:
        print(obj)
    obj["cached"] = json_util.dumps({
        **formatted,
        "prov:generatedAtTime": xsdNow()
    })
    return(MODELS()[modelType]().save(obj, validate=False))


def loadCache(obj):
    if isinstance(obj, dict):
        return(obj)
    else:
        return(json_util.loads(obj))


def _fixUpFormat(obj):
    if isinstance(obj, dict):
        newObj = {}
        for k in obj.keys():
            if k in KEYS_TO_DELANGUAGETAG:
                newObj[reprolibPrefix(k)] = reprolibCanonize(
                    delanguageTag(obj[k])
                )
            elif k in KEYS_TO_DEREFERENCE:
                newObj[reprolibPrefix(k)] = dereference(obj[k])
            elif isinstance(obj[k], list):
                newObj[reprolibPrefix(k)] = [_fixUpFormat(li) for li in obj[k]]
            elif isinstance(obj[k], dict):
                newObj[reprolibPrefix(k)] = _fixUpFormat(obj[k])
            else: # bool, int, float
                newObj[reprolibPrefix(k)] = obj[k]
            if isinstance(obj[k], str) and k not in KEYS_TO_DEREFERENCE:
                c = reprolibPrefix(obj[k])
                newObj[
                    reprolibPrefix(k)
                ] = c if c is not None else obj[k]
        if "@context" in newObj:
            newObj["@context"] = reprolibCanonize(newObj["@context"])
        for k in ["schema:url", "http://schema.org/url"]:
            if k in newObj:
                newObj["url"] = newObj[k]
        return(newObj)
    elif isinstance(obj, str):
        return(reprolibPrefix(obj))
    else:
        return(obj)


def formatLdObject(
    obj,
    mesoPrefix='folder',
    user=None,
    keepUndefined=False,
    dropErrors=False,
    refreshCache=False,
    responseDates=False
):
    """
    Function to take a compacted JSON-LD Object within a Girder for Mindlogger
    database and return an exapanded JSON-LD Object including an _id.

    :param obj: Compacted JSON-LD Object
    :type obj: dict or list
    :param mesoPrefix: Girder for Mindlogger entity type, defaults to 'folder'
                       if not provided
    :type mesoPrefix: str
    :param user: User making the call
    :type user: User
    :param keepUndefined: Keep undefined properties
    :type keepUndefined: bool
    :param dropErrors: Return `None` instead of raising an error for illegal
        JSON-LD definitions.
    :type dropErrors: bool
    :param refreshCache: Refresh from Dereferencing URLs?
    :type refreshCache: bool
    :param responseDates: Include list of ISO date strings of responses
    :type responseDates: bool
    :returns: Expanded JSON-LD Object (dict or list)
    """
    from girderformindlogger.models import pluralize

    try:
        if obj is None:
            return(None)
        if isinstance(obj, dict):
            oc = obj.get("cached")
            if all([
                not refreshCache,
                oc is not None
            ]):
                returnObj = loadCache(oc)
            if 'meta' not in obj.keys():
                return(_fixUpFormat(obj))
        mesoPrefix = camelCase(mesoPrefix)
        if type(obj)==list:
            return(_fixUpFormat([
                formatLdObject(
                    o,
                    mesoPrefix,
                    user=user
                ) for o in obj if o is not None
            ]))
        if not type(obj)==dict and not dropErrors:
            raise TypeError("JSON-LD must be an Object or Array.")
        newObj = obj.get('meta', obj)
        newObj = newObj.get(mesoPrefix, newObj)
        newObj = expand(newObj, keepUndefined=keepUndefined)
        if type(newObj)==list and len(newObj)==1:
            try:
                newObj = newObj[0]
            except:
                raise ValidationException(str(newObj))
        if type(newObj)!=dict:
            newObj = {}
        objID = str(obj.get('_id', 'undefined'))
        if objID=='undefined':
            raise ResourcePathNotFound()
        newObj['_id'] = "/".join([snake_case(mesoPrefix), objID])
        if mesoPrefix=='applet':
            protocolUrl = obj.get('meta', {}).get('protocol', obj).get(
                'http://schema.org/url',
                obj.get('meta', {}).get('protocol', obj).get('url')
            )
            protocol = ProtocolModel().getFromUrl(
                protocolUrl,
                'protocol',
                user,
                thread=False
            )[0] if protocolUrl is not None else {}
            protocol = formatLdObject(protocol, 'protocol', user)
            applet = {}
            applet['activities'] = protocol.pop('activities', {})
            applet['items'] = protocol.pop('items', {})
            applet['protocol'] = {
                key: protocol.get(
                    'protocol',
                    protocol.get(
                        'activitySet',
                        {}
                    )
                ).pop(
                    key
                ) for key in [
                    '@type',
                    '_id',
                    'http://schema.org/url',
                    'url'
                ] if key in list(protocol.get('protocol', {}).keys())
            }
            applet['applet'] = {
                **protocol.pop('protocol', {}),
                **obj.get('meta', {}).get(mesoPrefix, {}),
                '_id': "/".join([snake_case(mesoPrefix), objID]),
                'url': "#".join([
                    obj.get('meta', {}).get('protocol', {}).get("url", "")
                ])
            }
            return(applet)
        elif mesoPrefix=='protocol':
            protocol = {
                'protocol': newObj,
                'activities': {},
                "items": {}
            }
            activitiesNow = set()
            itemsNow = set()
            try:
                protocol = componentImport(
                    newObj,
                    deepcopy(protocol),
                    user,
                    refreshCache=refreshCache
                )
            except:
                print("636")
                protocol = componentImport(
                    newObj,
                    deepcopy(protocol),
                    user,
                    refreshCache=True
                )
            newActivities = [
                a for a in protocol.get('activities', {}).keys(
                ) if a not in activitiesNow
            ]
            newItems = [
                i for i in protocol.get('items', {}).keys(
                ) if i not in itemsNow
            ]
            while(any([len(newActivities), len(newItems)])):
                activitiesNow = set(
                    protocol.get('activities', {}).keys()
                )
                itemsNow = set(protocol.get('items', {}).keys())
                for activityURL in newActivities:
                    activity = protocol['activities'][activityURL]
                    activity = activity.get(
                        'meta',
                        {}
                    ).get('activity', activity)
                    try:
                        protocol = componentImport(
                            deepcopy(activity),
                            deepcopy(protocol),
                            user,
                            refreshCache=refreshCache
                        )
                    except:
                        print("670")
                        protocol = componentImport(
                            deepcopy(activity),
                            deepcopy(protocol),
                            user,
                            refreshCache=True
                        )
                for itemURL in newItems:
                    activity = protocol['items'][itemURL]
                    activity = activity.get(
                        'meta',
                        {}
                    ).get('screen', activity)
                    try:
                        protocol = componentImport(
                            deepcopy(activity),
                            deepcopy(protocol),
                            user,
                            refreshCache=refreshCache
                        )
                    except:
                        print("691")
                        protocol = componentImport(
                            deepcopy(activity),
                            deepcopy(protocol),
                            user,
                            refreshCache=True
                        )
                newActivities = list(
                    set(
                        protocol.get('activities', {}).keys()
                    ) - activitiesNow
                )
                newItems = list(
                    set(
                        protocol.get('items', {}).keys()
                    ) - itemsNow
                )
            return(_fixUpFormat(protocol))
        else:
            return(_fixUpFormat(newObj))
        # if responseDates and mesoPrefix=="applet":
        #     try:
        #         returnObj["applet"]["responseDates"] = responseDateList(
        #             obj.get('_id'),
        #             user.get('_id'),
        #             user
        #         )
        #     except:
        #         returnObj["applet"]["responseDates"] = []
        # return(_fixUpFormat(returnObj))
    except:
        if refreshCache==False:
            return(_fixUpFormat(formatLdObject(
                obj,
                mesoPrefix,
                user,
                keepUndefined,
                dropErrors,
                refreshCache=False,
                responseDates=responseDates
            )))
        import sys, traceback
        print(sys.exc_info())
        print(traceback.print_tb(sys.exc_info()[2]))


def componentImport(
    obj,
    protocol,
    user=None,
    refreshCache=False,
    modelType=['activity', 'item']
):
    """
    :param modelType: model or models to search
    :type modelType: str or iterable
    :returns: protocol (updated)
    """
    import itertools
    from girderformindlogger.models import pluralize, smartImport
    from girderformindlogger.utility import firstLower

    updatedProtocol = deepcopy(protocol)
    obj2 = {k: v for k, v in expand(obj.copy()).items() if v is not None}
    try:
        for order in obj2.get(
            "reprolib:terms/order",
            {}
        ):
            for activity in order.get("@list", []):
                IRI = activity.get(
                    'url',
                    activity.get('@id')
                )
                if reprolibPrefix(IRI) not in list(
                    itertools.chain.from_iterable([
                        protocol.get(mt, {}).keys() for mt in [
                            "activities",
                            "items"
                        ]
                    ])
                ):
                    activityComponent, activityContent, canonicalIRI =         \
                        smartImport(
                            IRI,
                            user=user,
                            refreshCache=refreshCache
                        ) if IRI is not None else (None, None, None)
                    if IRI != canonicalIRI:
                        activity["url"] = activity["schema:url"] = canonicalIRI
                    activityComponent = pluralize(firstLower(
                        activityContent.get(
                            '@type',
                            ['']
                        )[0].split('/')[-1].split(':')[-1]
                    )) if (activityComponent is None and isinstance(
                        activityContent,
                        dict
                    )) else activityComponent
                    if activityComponent is not None:
                        activityComponents = (
                            pluralize(
                                activityComponent
                            ) if activityComponent != 'screen' else 'items'
                        )
                        updatedProtocol[activityComponents][
                            canonicalIRI
                        ] = formatLdObject(
                            activityContent,
                            activityComponent,
                            user,
                            refreshCache=refreshCache
                        ).copy()
        return(updatedProtocol.get(
            'meta',
            updatedProtocol
        ).get(modelType if isinstance(
            modelType,
            str
        ) else modelType[0], updatedProtocol))
    except:
        import sys, traceback
        print("error!")
        print(sys.exc_info())
        print(traceback.print_tb(sys.exc_info()[2]))


def getByLanguage(object, tag=None):
    """
    Function to get a value or IRI by a language tag following
    https://tools.ietf.org/html/bcp47.

    :param object: The JSON-LD Object to language-parse
    :type object: dict or list
    :param tag: The language tag to use.
    :type tag: str
    :returns: str, either a literal or an IRI.
    """
    if not tag:
        from girderformindlogger.api.v1.context import Context
        tag = FolderModel().findOne({
            'name': 'JSON-LD',
            'parentCollection': 'collection',
            'parentId': CollectionModel().findOne({
                'name': 'Context'
            }).get('_id')
        })
        tag = tag.get('meta', {}).get('@context', {}).get(
            '@language'
        ) if tag else None
    if isinstance(tag, str):
        tags = getMoreGeneric(tag)
        tags = tags + ["@{}".format(t) for t in tags]
        tags.sort(key=len, reverse=True)
        if isinstance(object, dict):
            return(
                getFromLongestMatchingKey(object, tags, caseInsensitive=True)
            )
        if isinstance(object, list):
            return([getFromLongestMatchingValue(
                objectList=object,
                listOfValues=tags,
                keyToMatch='@language',
                caseInsensitive=True
            )])
    if isinstance(object, str):
        return(object)


def getFromLongestMatchingKey(object, listOfKeys, caseInsensitive=True):
    """
    Function to take an object and a list of keys and return the value of the
    longest matching key or None if no key matches.

    :param object: The object with the keys.
    :type object: dict
    :param listOfKeys: A list of keys to try to match
    :type listOfKeys: list of string keys
    :param caseInsensitive: Case insensitive key matching?
    :type caseInsensitive: boolean
    :returns: value of longest matching key in object
    """
    listOfKeys = listOfKeys.copy()
    if caseInsensitive:
        object = {k.lower():v for k,v in object.items()}
        listOfKeys = [k.lower() for k in listOfKeys]
    key = max(
        [str(k) for k in listOfKeys],
        key=len
    ) if len(listOfKeys) else None
    if key and key in listOfKeys:
        listOfKeys.remove(key)
    return(
        object.get(
            key,
            getFromLongestMatchingKey(object, listOfKeys)
        ) if key else None
    )


def getFromLongestMatchingValue(
    objectList,
    listOfValues,
    keyToMatch,
    caseInsensitive=True
):
    """
    Function to take a list of objects, a list of values and a key to match and
    return the object with the longest matching value for that key or None if
    no value matches for that that key.

    :param objectList: The list of objects.
    :type objectList: list of dicts
    :param listOfValues: A list of values to try to match
    :type listOfValues: list of string values
    :param keyToMatch: key in which to match the value
    :type keyToMatch: str
    :param caseInsensitive: Case insensitive value matching?
    :type caseInsensitive: boolean
    :returns: dict with longest matching value for specified key in object
    """
    objectList = objectList.copy()
    if caseInsensitive:
        listOfValues = [k.lower() for k in listOfValues]
    value = max(
        [str(k) for k in listOfValues],
        key=len
    ) if len(listOfValues) else None
    if value and value in listOfValues:
        listOfValues.remove(value)
    for object in sorted(
        objectList,
        key=lambda i: len(i.get(keyToMatch, "")),
        reverse=True
    ):
        if (
            object.get(keyToMatch, '').lower(
            ) if caseInsensitive else object.get(keyToMatch, '')
        )==value:
            return(object)
    if len(listOfValues)>=1:
        return(getFromLongestMatchingValue(
            objectList,
            listOfValues,
            keyToMatch,
            caseInsensitive
        ))
    for object in sorted(
        objectList,
        key=lambda i: len(i.get(keyToMatch, "")),
        reverse=False
    ):
        generic = object.get(keyToMatch, '').lower(
        ) if caseInsensitive else object.get(keyToMatch, '')
        generic = generic.split('-')[0] if '-' in generic else generic
        if generic==value:
            return(object)
    return({})


def getMoreGeneric(langTag):
    """
    Function to return a list of decreasingly specific language tags, given a
    language tag.

    :param langTag: a language tag following https://tools.ietf.org/html/bcp47
    :type langTag: str
    :returns: list
    """
    langTags = [langTag]
    while '-' in langTag:
        langTag = langTag[::-1].split('-', 1)[1][::-1]
        langTags.append(langTag)
    return(langTags)


def keyExpansion(keys):
    return(list(set([
        k.split(delimiter)[-1] for k in keys for delimiter in [
            ':',
            '/'
        ] if delimiter in k
    ] + [
        k for k in keys if (':' not in k and '/' not in k)
    ])))


def camelCase(snake_case):
    """
    Function to convert a snake_case_string to a camelCaseString

    :param snake_case: snake_case_string
    :type snake_case: str
    :returns: camelCaseString
    """
    words = snake_case.split('_')
    return('{}{}'.format(
        words[0],
        ''.join([
            word.title() for word in words[1:]
        ])
    ))

def snake_case(camelCase):
    """
    Function to convert a camelCaseString to a snake_case_string

    :param camelCase: camelCaseString
    :type camelCase: str
    :returns: snake_case_string
    """
    import re
    first_cap_re = re.compile('(.)([A-Z][a-z]+)')
    all_cap_re = re.compile('([a-z0-9])([A-Z])')
    return(
        all_cap_re.sub(
            r'\1_\2',
            first_cap_re.sub(
                r'\1_\2',
                camelCase
            )
        ).lower()
    )

def xsdNow():
    """
    Function to return an XSD formatted datetime string for the current
    datetime.now()
    """
    return(datetime.now(datetime.utcnow().astimezone().tzinfo).isoformat())
