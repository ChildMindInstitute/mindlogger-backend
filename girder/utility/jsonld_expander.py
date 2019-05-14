import json
from copy import deepcopy
from dictdiffer import diff
from girder.api.rest import getApiUrl
from girder.constants import AccessType
from girder.exceptions import AccessException
from girder.models.activity import Activity as ActivityModel
from girder.models.collection import Collection as CollectionModel
from girder.models.folder import Folder as FolderModel
from girder.models.item import Item as ItemModel
from girder.models.screen import Screen as ScreenModel
from girder.models.user import User as UserModel
from .resource import loadJSON
from pyld import jsonld

MODELS = {
    'collection': CollectionModel(),
    'folder': FolderModel(),
    'item': ItemModel(),
    'user': UserModel()
}

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


def updateFromURL(url, docType, user):
    """
    Function to update a document in the database from a URL.

    :param url: URL to load
    :type url: str
    :param docType: {"applet", "activity", "screen", …}
    :type docType: str
    :param user: User making the call
    :type user: User
    :returns: Expanded JSON-LD Object (dict or list)
    """
    folderModels = ['applet', 'activity']
    docType = docType.lower()
    fm = docType in folderModels
    model = FolderModel() if fm else ItemModel()
    cached = list(model.find(
        query={'.'.join(['meta', docType, 'url']): url},
        sort=[("created", -1)]
    ))
    cachedDoc = cached[0] if len(cached) else None
    if cachedDoc:
        cachedId = str(cachedDoc.get('_id'))
        docParent = {
            'type': cachedDoc.get('parentCollection'),
            'id': cachedDoc.get('parentId')
        } if fm else {
            'type': 'folder',
            'id': cachedDoc.get('folderId')
        }
        cachedDocObj = cachedDoc.get('meta', {}).get(docType, {})
        cachedDocObj.pop('url', None)
        cachedDocObj.pop('schema:isBasedOn', None)
    else:
        cachedId = None
        cachedDocObj = {}
    doc = loadJSON(url, docType)
    if not cachedDocObj or len(list(diff(cachedDocObj, doc))):
        if cachedId:
            doc['schema:isBasedOn'] = {
                '@id': '/'.join([
                    getApiUrl(),
                    docType,
                    cachedId
                ])
            }
        else:
            docParent={
                'type': 'collection',
                'id': CollectionModel().createCollection(
                    name="{}s".format(docType.title()),
                    creator=user,
                    public=True,
                    reuseExisting=True
                ).get('_id')
            }
        docName = model.preferredName(doc)
        try:
            parent = MODELS[docParent['type']].load(
                docParent['id'],
                level=AccessType.WRITE,
                user=user
            )
        except AccessException:
            parent = CollectionModel().createCollection(
                name="{}s".format(docType.title()),
                creator=user,
                public=True,
                reuseExisting=True
            ) if fm else FolderModel().createFolder(
                parent=CollectionModel().createCollection(
                    name='Screens',
                    creator=user,
                    public=True,
                    reuseExisting=True
                ),
                parentType='collection',
                name='Screens',
                creator=user,
                allowRename=True,
                reuseExisting=True
            )
        doc = model.setMetadata(
            model.createFolder(
                name=docName,
                parent=parent,
                parentType=docParent['type'],
                public=True,
                creator=user,
                allowRename=True,
                reuseExisting=False
            ),
            {
                docType: {
                    **doc,
                    'url': url
                }
            }
        ) if fm else model.setMetadata(
            model.createItem(
                name=docName if docName else str(len(list(
                    FolderModel().childItems(
                        FolderModel().load(
                            parent,
                            level=AccessType.NONE,
                            user=user,
                            force=True
                        )
                    )
                )) + 1),
                creator=user,
                folder=parent['id'],
                reuseExisting=False
            ),
            {
                docType: {
                    **doc,
                    'url': url
                }
            }
        )
        return(formatLdObject(doc, docType, user))
    return(formatLdObject(cachedDoc, docType, user))
