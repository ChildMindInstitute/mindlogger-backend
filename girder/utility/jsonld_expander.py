import json
from copy import deepcopy
from girder.constants import AccessType
from girder.exceptions import AccessException, ResourcePathNotFound, \
    ValidationException
from girder.models.activity import Activity as ActivityModel
from girder.models.activitySet import ActivitySet as ActivitySetModel
from girder.models.applet import Applet as AppletModel
from girder.models.collection import Collection as CollectionModel
from girder.models.folder import Folder as FolderModel
from girder.models.item import Item as ItemModel
from girder.models.screen import Screen as ScreenModel
from girder.models.user import User as UserModel
from pyld import jsonld

KEYS_TO_EXPAND = [
    "responseOptions",
    "https://schema.repronim.org/valueconstraints"
]

MODELS = {
    'activity': ActivityModel(),
    'activitySet': ActivitySetModel(),
    'applet': AppletModel(),
    'collection': CollectionModel(),
    'folder': FolderModel(),
    'item': ItemModel(),
    'screen': ScreenModel(),
    'user': UserModel()
}


def expand(obj, keepUndefined=False):
    """
    Function to take an unexpanded JSON-LD Object and return it expandedself.

    :param obj: unexpanded JSON-LD Object
    :type obj: dict
    :param keepUndefined: keep undefined-in-context terms?
    :param keepUndefined: bool
    :returns: list, expanded JSON-LD Array or Object
    """
    if obj==None:
        return(obj)
    try:
        newObj = jsonld.expand(obj)
    except jsonld.JsonLdError as e: # 👮 Catch illegal JSON-LD
        print(e)
        print(obj)
        return(None)
    newObj = newObj[0] if (
        isinstance(newObj, list) and len(newObj)==1
    ) else newObj
    if isinstance(
        newObj,
        dict
    ):
        if not isinstance(obj, dict):
            obj={}
        for k, v in newObj.copy().items():
            if not bool(v):
                newObj.pop(k)
        newObj.update({
            k: obj.get(k) for k in obj.keys() if (
                bool(obj.get(k)) and k not in keyExpansion(
                    list(newObj.keys())
                )
            )
        })
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
                    newObj[k] = v
        return(newObj if bool(newObj) else None)
    else:
        expanded = [expand(n, keepUndefined) for n in newObj]
        return(expanded if bool(expanded) else None)


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
        print("Warning: Could not load {}".format(r))
    return(r.text)


def formatLdObject(
    obj,
    mesoPrefix='folder',
    user=None,
    keepUndefined=False,
    dropErrors=False):
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
    :returns: Expanded JSON-LD Object (dict or list)
    """
    mesoPrefix = camelCase(mesoPrefix)
    if obj is None:
        return(None)
    if type(obj)==list:
        return([formatLdObject(o, mesoPrefix) for o in obj if o is not None])
    if not type(obj)==dict and not dropErrors:
        raise TypeError("JSON-LD must be an Object or Array.")
    newObj = obj.get('meta', obj)
    newObj = newObj.get(mesoPrefix, newObj)
    newObj = expand(newObj, keepUndefined=keepUndefined)
    if type(newObj)==list and len(newObj)==1:
        newObj = newObj[0]
    if type(newObj)!=dict:
        newObj = {}
    objID = str(obj.get('_id', 'undefined'))
    if objID=='undefined':
        raise ResourcePathNotFound()
    newObj['_id'] = "/".join([snake_case(mesoPrefix), objID])
    if mesoPrefix=='applet':
        activitySet = formatLdObject(
            ActivitySetModel().load(
                obj['meta']['activitySet'].get(
                    '_id',
                    ''
                ).split('activity_set/')[1],
                level=AccessType.READ,
                user=user
            ) if '_id' in obj['meta']['activitySet'] else ActivitySetModel(
            ).importUrl(
                obj['meta']['activitySet'].get(
                    'url',
                    ''
                ),
                user
            ) if 'url' in obj['meta']['activitySet'] else {},
            'activitySet',
            user,
            keepUndefined,
            dropErrors
        ) if 'activitySet' in obj.get('meta', {}) and isinstance(
            obj['meta']['activitySet'],
            dict
        ) else {}
        applet = {
            'activities': activitySet.pop('activities', {}),
            'items': activitySet.pop('items', {}),
            'activitySet': {
                key: activitySet.get('activitySet', {}).pop(
                    key,
                    None
                ) for key in [
                    '_id',
                    '@type',
                    'http://schema.org/url'
                ]
            },
            'applet': {
                **activitySet.pop('activitySet', {}),
                **newObj
            }
        }
        return(applet)
    if mesoPrefix=='activitySet':
        activitySet = {
            'activitySet': newObj
        }
        if not dropErrors:
            activitySet['activities'] = {
                activity.get(
                    'url',
                    activity.get('@id')
                ): formatLdObject(
                    ActivityModel().load(
                        activity.get('_id')
                    ) if '_id' in activity else ActivityModel().importUrl(
                            url=activity.get(
                                'url',
                                activity.get('@id')
                            ),
                            user=user
                    ),
                    'activity',
                    user
                ) for order in newObj[
                    "https://schema.repronim.org/order"
                ] for activity in order.get("@list", [])
            }
            activitySet['items'] = {
                screen.get(
                    'url',
                    screen.get('@id')
                ): formatLdObject(
                    ScreenModel().load(
                        screen.get('_id'),
                        level=AccessType.READ,
                        user=user,
                        force=True
                    ) if '_id' in screen else ScreenModel().importUrl(
                        url=screen.get(
                            'url',
                            screen.get('@id')
                        ),
                        user=user
                    ),
                    'screen',
                    user
                ) for activityURL, activity in activitySet.get(
                    'activities',
                    {}
                ).items() for order in activity.get(
                    "https://schema.repronim.org/order",
                    []
                ) for screen in order.get("@list", order.get("@set", []))
            }
            return(activitySet)
        else:
            activitySet['activities'] = {}
            for order in newObj["https://schema.repronim.org/order"]:
                for activity in order.get("@list", []):
                    try:
                        activitySet['activities'][activity.get(
                            'url',
                            activity.get('@id')
                        )] = formatLdObject(
                            ActivityModel().load(
                                activity.get('_id')
                            ) if '_id' in activity else ActivityModel(
                            ).importUrl(
                                    url=activity.get(
                                        'url',
                                        activity.get('@id')
                                    ),
                                    user=user
                            ),
                            'activity',
                            user
                        )
                    except ValidationException as e:
                        print(e)
            activitySet['items'] = {}
            for activityURL, activity in activitySet.get(
                'activities',
                {}
            ).items():
                for order in activity.get(
                    "https://schema.repronim.org/order",
                    []
                ):
                    for screen in order.get("@list", order.get("@set", [])):
                        try:
                            activitySet['items'][screen.get(
                                'url',
                                screen.get('@id')
                            )] = formatLdObject(
                                ScreenModel().load(
                                    screen.get('_id'),
                                    level=AccessType.READ,
                                    user=user,
                                    force=True
                                ) if '_id' in screen else ScreenModel(
                                ).importUrl(
                                    url=screen.get(
                                        'url',
                                        screen.get('@id')
                                    ),
                                    user=user
                                ),
                                'screen',
                                user
                            )
                        except ValidationException as e:
                            print(e)
            return(activitySet)
    return(newObj)


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
        from girder.api.v1.context import Context
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
