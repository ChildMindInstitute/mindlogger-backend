import json
import os
import pandas as pd
import sys
__package__ = "mindlogger_backend_dev.update_schema"
from ..object_manipulation import *


def add_to_schedule(
    girder_connection,
    frequency,
    schedules_id,
    activity_item_id,
    context={},
    timings={
        "1d": "Daily",
        "1": "Once",
        "8h": "3×Daily",
        "12h": "2×Daily"
    },
    schedule_folder_id=None,
    schedule_item_id=None
):
    """
    Function to add Activities to a Schedule

    Parameters
    ----------
    girder_connection: GirderClient

    frequency: string

    schedules_id: string

    activity_item_id: string

    context: dictionary, optional
        default: {}

    timings: dictionary, optional
        key: string
            frequency
        value: string
            schedule name
        default: {
            "1d": "Daily",
            "1": "Once",
            "8h": "3×Daily",
            "12h": "2×Daily"
        }

    schedule_folder_id: string, optional
        default: _id for public schedules

    schedule_item_id: string, optional
        default: _id for "Version 0 [Frequency]"

    Returns
    -------
    schedule_item_id: string
    """
    schedule_folder_id = girder_connection.createFolder(
        name=timings[frequency],
        parentId=schedules_id,
        parentType="collection",
        public=False,
        reuseExisting=True
    )[
        "_id"
    ] if not schedule_folder_id else schedule_folder_id # pragma: no cover
    schedule_item_id = girder_connection.createItem(
        name=" ".join([
            "Version 0",
            timings[frequency]
        ]),
        parentFolderId=schedule_folder_id,
        reuseExisting=True
    )[
        "_id"
    ] if not schedule_item_id else schedule_item_id # pragma: no cover
    schedule_item = girder_connection.get(
        "".join([
            "item/",
            schedule_item_id
        ])
    ) # pragma: no cover
    schedule_metadata = schedule_item[
        "meta"
    ] if "meta" in schedule_item else {} # pragma: no cover
    schedule_metadata[
        "@context"
    ] = context if "@context" not in \
    schedule_metadata else schedule_metadata[
        "@context"
    ] # pragma: no cover
    schedule_metadata["activities"] = [] if (
        "activities" not in schedule_metadata
    ) else schedule_metadata["activities"] # pragma: no cover
    schedule_metadata["activities"].append(
        {
            "@id": "".join([
                "item/",
                activity_item_id
            ]),
            "name": girder_connection.get(
                "item/{0}".format(
                    activity_item_id
                )
            )["name"]
        }
    ) # pragma: no cover
    girder_connection.addMetadataToItem(
        schedule_item_id,
        drop_empty_keys(
            schedule_metadata
        )
    ) # pragma: no cover
    return(schedule_item_id) # pragma: no cover


def find_or_create(x, parent, girder_connection):
    """
    Function to find or create a Girder Folder or Item
    under a specific parent.
    
    Parameters
    ----------
    x: 2-tuple
        x[0]: string
            "Folder", "Item", etc.
        x[1]: string
            entity name
    
    parent: 2-tuple
        parent[0]: string
            "Collection", "Folder", etc.
        parent[1]: string
            Girder_id
    
    girder_connection: GirderClient
        active GirderClient
        
    Returns
    -------
    _id: string
        Girder_id of found or created entity
    """
    api_query = "".join([
        x[0].lower(),
        "?folderId=",
        parent[1],
        "&name=",
        x[1],
        "&reuseExisting=true"
    ]) if (
        x[0].lower()=="item" and
        y[0].lower()=="folder"
    ) else "".join([
        x[0].lower(),
        "?parentType=",
        parent[0].lower(),
        "&parentId=",
        parent[1],
        "&name=",
        x[1],
        "&reuseExisting=true"
    ])
    return(
        girder_connection.post(
            api_query
        )["_id"]
    )


def get_files_in_item(
    girder_connection,
    item_id,
    sort="created",
    sortdir=-1
):
    """
    Function to get a dictionary of Files in an Item in
    a Girder database.

    Parameters
    ----------
    girder_connection: GirderClient
        an active `GirderClient <http://girder.readthedocs.io/en/latest/python-client.html#girder_client.GirderClient>`_

    item_id: string
        Girder _id of Item.

    sort: string, optional
        Field to sort the result set by.
        default = "created"

    sortdir: int, optional
        Sort order: 1 for ascending, -1 for descending.
        default = -1

    Returns
    -------
    files: dictionary or None
        metadata of files in Girder Item

    Examples
    --------
    >>> import girder_client as gc
    >>> get_files_in_item(
    ...     girder_connection=gc.GirderClient(
    ...         apiUrl="https://data.kitware.com/api/v1/"
    ...     ),
    ...     item_id="58a372f38d777f0721a64df3"
    ... )[0]["name"]
    'Normal001-T1-Flash.mha'
    """
    return(
      girder_connection.get(
        "".join([
          "item/",
          item_id,
          "/files?",
          "sort=",
          sort,
          "&sortdir=",
          str(sortdir)
        ])
      )
    )


def get_girder_id_by_name(
    girder_connection,
    entity,
    name,
    parent=None,
    limit=1,
    sortdir=-1,
    index=0
):
    """
    Function to get the `_id` of a single entity in a Girder database.

    Parameters
    ----------
    girder_connection: GirderClient
        an active `GirderClient <http://girder.readthedocs.io/en/latest/python-client.html#girder_client.GirderClient>`_

    entity: string
        "collection", "folder", "item", "file", "user"

    name: string
        name of entity

    parent: 2-tuple, optional, default=None
        (parentType, parent_id)
        parentType: string
            "Collection", "Folder", or "User"
        parendId: string
            Girder _id for parent

    limit: int, optional, default=1
        maximum number of query results

    sortdir: int, optional, default=-1
        Sort order: 1 for ascending, -1 for descending.

    index: int, default=0
        0-indexed index of named entity in given sort order.

    Returns
    -------
    _id: string
        Girder _id of requested entity

    Examples
    --------
    >>> import girder_client as gc
    >>> get_girder_id_by_name(
    ...     girder_connection=gc.GirderClient(
    ...         apiUrl="https://data.kitware.com/api/v1/"
    ...     ),
    ...     entity="collection",
    ...     name="Cinema",
    ...     parent=None,
    ...     sortdir=1
    ... )
    '55706aa58d777f649a9ba164'
    """
    entity = entity.title()
    query = "".join([
        entity.lower(),
        "?text=" if entity in {
            "Collection",
            "Group"
        } else "?name=",
        name,
        "&parentType={0}&parentId={1}".format(
            parent[0].lower(),
            parent[1]
        ) if (
            parent and entity!="Item"
        ) else "&folderId={0}".format(
            parent[1]
        ) if parent else "",
        "&limit=",
        str(limit),
        "&sortdir=",
        str(sortdir)
    ])
    j = json.loads(
        girder_connection.get(
            query,
            jsonResp=False
        ).content.decode(
            "UTF8"
        )
    )
    return(
        j[0]["_id"] if len(
            j
        ) else girder_connection.createCollection(
            name=name,
            public=False
        )["_id"] if entity=="Collection" else None
    )


def get_group_ids(
    girder_connection,
    groups={
        "Editors",
        "Managers",
        "Users",
        "Viewers"
    },
    create_missing=False
):
    """
    Function to collect Girder _ids,
    optionally creating any missing groups.

    Parameters
    ----------
    girder_connection: GirderClient
        active Girder Client

    groups: set
        set of Group names for which to get
        Girder _ids
        item: string
            Group name
        default: {
            "Editors",
            "Managers",
            "Users",
            "Viewers"
        }

    create_missing: boolean
        create Group if none with that name
        exists?
        default: False

    Returns
    -------
    groups: dictionary
        key: string
            name from original set
        value: string
            Girder Group _id

    Examples
    --------
    >>> import girder_client as gc
    >>> get_group_ids(
    ...     girder_connection=gc.GirderClient(
    ...         apiUrl="https://data.kitware.com/api/v1/"
    ...     ),
    ...     groups={"VIGILANT"}
    ... )
    {'VIGILANT': '58a354fe8d777f0721a6106a'}
    """
    groups = {
        group: get_girder_id_by_name(
          girder_connection,
          "group",
          group
          ) for group in groups
    }
    if create_missing: # pragma: no cover
        for group in groups: # pragma: no cover
            if groups[group] is None: # pragma: no cover
                groups[group] = girder_connection.post(
                    "".join([
                        "group?name=",
                        group,
                        "&public=false"
                    ])
                )["_id"] # pragma: no cover
    return(groups)


def get_user_id_by_email(girder_connection, email):
    """
    Function to get the `_id` of a single User in a Girder database.

    Parameters
    ----------
    girder_connection: GirderClient
        an active `GirderClient <http://girder.readthedocs.io/en/latest/python-client.html#girder_client.GirderClient>`_

    email: string
        email address

    Returns
    -------
    _id: string or None
        Girder _id of requested User, or None if not found

    Examples
    --------
    >>> import girder_client as gc
    >>> get_user_id_by_email(
    ...     girder_connection=gc.GirderClient(
    ...         apiUrl="https://data.kitware.com/api/v1/"
    ...     ),
    ...     email="test@example.com"
    ... )
    """
    email = email.lower()
    user_ids = [
      user["_id"] for user in girder_connection.get(
            "".join([
                "user?text=",
                email
            ])
        ) if (
            (
                 "email" in user
            ) and (
                 user["email"]==email
            )
        ) or (
            (
                 "login" in user
            ) and (
                 user["login"]==email
            )
        )
    ]
    return(
        user_ids[0] if len(user_ids) else None
    )


def ls_x_in_y(x_type, y, girder_connection):
    """
    Function to list **x** in **y**.
    
    Parameters
    ----------
    x_type: string
        "Folder", "Item", etc.
        
    y: 2-tuple
        y[0]: string
            "Collection", "Folder", etc.
        
        y[1]: string
            Girder_id
        
    girder_connection: GirderClient
        active GirderClient
    
    Returns
    -------
    x: list of dictionaries
        ≅ JSON array of objects
        
    Examples
    --------
    >>> import girder_client as gc
    >>> ls_x_in_y(
    ...     "Folder",
    ...     ("Collection", "58b5d21a8d777f0aef5d04b1"),
    ...     girder_connection=gc.GirderClient(
    ...         apiUrl="https://data.kitware.com/api/v1/"
    ...     )
    ... )
    [{'_accessLevel': 0, '_id': '58b5d86c8d777f0aef5d04b4', '_modelType': 'folder', 'baseParentId': '58b5d21a8d777f0aef5d04b1', 'baseParentType': 'collection', 'created': '2017-02-28T20:07:08.074000+00:00', 'creatorId': '55a413168d777f649a9ba343', 'description': '', 'name': 'TestData', 'parentCollection': 'collection', 'parentId': '58b5d21a8d777f0aef5d04b1', 'public': True, 'publicFlags': [], 'size': 41319999, 'updated': '2017-02-28T20:07:08.074000+00:00'}, {'_accessLevel': 0, '_id': '58cb12048d777f0aef5d79fc', '_modelType': 'folder', 'baseParentId': '58b5d21a8d777f0aef5d04b1', 'baseParentType': 'collection', 'created': '2017-03-16T22:30:28.994000+00:00', 'creatorId': '55a413168d777f649a9ba343', 'description': '', 'name': 'TomvizData', 'parentCollection': 'collection', 'parentId': '58b5d21a8d777f0aef5d04b1', 'public': True, 'size': 0, 'updated': '2017-03-24T18:30:21.117000+00:00'}]
    """
    api_query = "".join([
        x_type.lower(),
        "?folderId=",
        y[1]
    ]) if (
        x_type.lower()=="item" and
        y[0].lower()=="folder"
    ) else "".join([
        x_type.lower(),
        "?parentType=",
        y[0].lower(),
        "&parentId=",
        y[1]
    ])
    return(
        girder_connection.get(
            api_query
        )
    )


def mv(
    x,
    new_parent,
    girder_connection
):
    """
    Function to move a Girder entity to a new_parent.
    
    Parameters
    ----------
    x: 2-tuple
        x[0]: string
            "Folder", "Item", etc.
        x[1]: string
            Girder_id
    
    new_parent: 2-tuple
        new_parent[0]: string
            "Collection", "Folder", etc.
        new_parent[1]: string
            Girder_id
    
    girder_connection: GirderClient
        active GirderClient
        
    Returns
    -------
    x_object: dictionary
        ≅JSON representation of entity in new location
    """
    api_query = "".join([
        x[0].lower(),
        "/",
        x[1],
        "?folderId=",
        new_parent[1]
    ]) if (
        x[0].lower()=="item" and
        y[0].lower()=="folder"
    ) else "".join([
        x[0].lower(),
        "/",
        x[1],
        "?parentId=",
        new_parent[1],
        "&parentType=",
        new_parent[0].lower()
    ])
    return(
        girder_connection.put(
            api_query
        )
    )


def rename(
    x,
    new_name,
    girder_connection
):
    """
    Function to rename a Girder entity.
    
    Parameters
    ----------
    x: 2-tuple
        x[0]: string
            "Folder", "Item", etc.
        x[1]: string
            Girder_id
    
    new_name: string
        new name for entity
    
    girder_connection: GirderClient
        active GirderClient
        
    Returns
    -------
    x_object: dictionary
        ≅JSON representation of entity in new location
    """
    api_query = "".join([
        x[0].lower(),
        "/",
        x[1],
        "?name=",
        new_name
    ])
    return(
        girder_connection.put(
            api_query
        )
    )
    

def _delete_collections(girder_connection, except_collection_ids):
    """
    Function to delete all collections
    except those collection_ids specified
    as exceptions.

    Parameters
    ----------
    gc: GirderClient

    except_collection_ids: iterable
        list, set, or tuple of collection_ids to
        keep. Can be empty.

    Returns
    -------
    collections_kept_and_deleted: DataFrame
        DataFrame of Collections kept and deleted
    """
    except_collection_ids = except_collection_ids if isiterable(
        except_collection_ids
    ) else {}
    kept = pd.DataFrame(
      [
        {
            **girder_connection.getCollection(
                i["_id"]
            ),
            "deleted": False
        } for i in girder_connection.listCollection(
        ) if i["_id"] in except_collection_ids
      ]
    ) # pragma: no cover
    deleted = pd.DataFrame(
      [
        {
            **girder_connection.getCollection(
                i["_id"]
            ),
            "deleted": True
        } for i in girder_connection.listCollection(
        ) if i["_id"] not in except_collection_ids
      ]
    ) # pragma: no cover
    collections_kept_and_deleted = pd.concat(
        [
            kept,
            deleted
        ],
        ignore_index = True
    ) # pragma: no cover
    for u in collections_kept_and_deleted[
        collections_kept_and_deleted[
            "deleted"
        ]==True
    ]["_id"]:
        girder_connection.delete(
            "collection/{0}".format(
                u
            )
        )
    return(
        collections_kept_and_deleted
    )


def _delete_users(girder_connection, except_user_ids):
    """
    Function to delete all users
    except those user_ids specified
    as exceptions.

    Parameters
    ----------
    girder_connection: GirderClient

    except_user_ids: iterable
        list, set, or tuple of user_ids to
        keep. Can be empty.

    Returns
    -------
    users_kept_and_deleted: DataFrame
        DataFrame of Users kept and deleted
    """
    except_user_ids = except_user_ids if isiterable(
        except_user_ids
    ) else {}
    kept = pd.DataFrame(
        [
           {
                **girder_connection.getUser(
                    i["_id"]
                ),
                "deleted": False
            } for i in girder_connection.listUser(
            ) if i["_id"] in except_user_ids
        ]
    ) # pragma: no cover
    deleted = pd.DataFrame(
        [
            {
                **girder_connection.getUser(
                    i["_id"]
                ),
                "deleted": True
            } for i in girder_connection.listUser(
            ) if i["_id"] not in except_user_ids
        ]
    ) # pragma: no cover
    users_kept_and_deleted = pd.concat(
        [
            kept,
            deleted
        ],
        ignore_index = True
    ) # pragma: no cover
    for u in users_kept_and_deleted[
        users_kept_and_deleted[
            "deleted"
        ]==True
    ]["_id"]: # pragma: no cover
        girder_connection.delete(
            "user/{0}".format(
                u
            )
        ) # pragma: no cover
    return(
        users_kept_and_deleted
    ) # pragma: no cover
