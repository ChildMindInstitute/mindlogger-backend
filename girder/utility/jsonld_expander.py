from copy import deepcopy
from girder.models.activity import Activity as ActivityModel
from girder.models.collection import Collection as CollectionModel
from girder.models.folder import Folder as FolderModel
from girder.models.screen import Screen as ScreenModel
from pyld import jsonld
import json


def check_for_unexpanded_value_constraints(item_exp):
    vc = item_exp[0]
    if 'https://schema.repronim.org/valueconstraints' in vc.keys():
        vc = vc['https://schema.repronim.org/valueconstraints'][0]
        if isinstance(vc, dict):
            if "@id" in vc.keys():
                return(True)

    return(False)


def expand_value_constraints(original_items_expanded):
    items_expanded = deepcopy(original_items_expanded)
    for item, item_exp in original_items_expanded.items():
        # check if we need to expand valueConstraints
        vc = item_exp[0]
        if 'https://schema.repronim.org/valueconstraints' in vc.keys():
            if check_for_unexpanded_value_constraints(item_exp):
                vc = jsonld.expand(
                    item_exp[0][
                        'https://schema.repronim.org/valueconstraints'
                    ][0]['@id']
                )
                items_expanded[item][0][
                    'https://schema.repronim.org/valueconstraints'
                ][0] = vc
        else:
            multipart_activities = get_activities(item_exp)
            items_expanded.update(multipart_activities)
    return(items_expanded)


def formatLdObject(obj, mesoPrefix='folder', user=None):
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
    :returns: Expanded JSON-LD Object (dict or list)
    """
    if obj is None:
        return(None)
    if type(obj)==list:
        return([formatLdObject(obj, mesoPrefix) for o in obj])
    if not type(obj)==dict:
        raise TypeError("JSON-LD must be an Object or Array.")
    newObj = obj.get('meta', obj)
    newObj = newObj.get(mesoPrefix, newObj)
    newObj = jsonld.expand(newObj)
    if type(newObj)==list and len(newObj)==1:
        newObj = newObj[0]
    if type(newObj)==dict:
        newObj['_id'] = "/".join([mesoPrefix, str(obj.get('_id', 'undefined'))])
    if mesoPrefix=='applet':
        applet = {'applet': newObj}
        applet['activities'] = {
            activity.get(
                'url',
                activity.get('@id')
            ): formatLdObject(
                ActivityModel().load(
                    activity.get('_id')
                ) if '_id' in activity else ActivityModel().importActivity(
                        url=activity.get(
                            'url',
                            activity.get('@id')
                        ),
                        applet=newObj.get(
                            '_id'
                        ).split('/')[1] if newObj.get(
                            '_id',
                            ''
                        ).startswith('applet') else None,
                        user=user
                ),
                'activity',
                user
            ) for order in newObj[
                "https://schema.repronim.org/order"
            ] for activity in order.get("@list", [])
        }
        applet['items'] = {
            screen.get(
                'url',
                screen.get('@id')
            ): formatLdObject(
                ScreenModel().load(
                    screen.get('_id'),
                    level=AccessType.READ,
                    user=user,
                    force=True
                ) if '_id' in screen else ScreenModel().importScreen(
                    url=screen.get(
                        'url',
                        screen.get('@id')
                    ),
                    activity=activity.get('_id').split(
                        '/'
                    )[1] if activity.get('_id').startswith(
                        'activity'
                    ) else ActivityModel().importActivity(
                        activity.get(
                            'url',
                            activity.get('@id')
                        ),
                        applet=applet.get('_id'),
                        user=user
                    ),
                    user=user
                ),
                'screen',
                user
            ) for activityURL, activity in applet.get(
                'activities',
                {}
            ).items() for order in activity.get(
                "https://schema.repronim.org/order",
                []
            ) for screen in order.get("@list", order.get("@set", []))
        }
        return(applet)
    if mesoPrefix=='activity':
        activity = newObj
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
            val = [
                o for o in object if o.get('@language').lower() in tags
            ]
            if not len(val):
                val = [
                    o for o in object if o.get('@language').lower()==(
                        tag.lower().split("-") if "-" in tag else [""]
                    )[0]
                ]
            if not len(val):
                val = [
                    o for o in object if (
                        '-' in o.get('@language') and o.get('@language').lower(
                        ).split('-')[0] in tags
                    )
                ]
            if not len(val):
                val = [{}]
            return(val[0].get('@value', val[0]))
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
