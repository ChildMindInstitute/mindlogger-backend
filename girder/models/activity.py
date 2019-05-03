#!/usr/bin/env python
# -*- coding: utf-8 -*-

###############################################################################
#  Copyright 2013 Kitware Inc.
#
#  Licensed under the Apache License, Version 2.0 ( the "License" );
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
###############################################################################

import copy
import datetime
import json
import os
import six

from bson.objectid import ObjectId
from .folder import Folder
from girder import events
from girder.constants import AccessType, SortDir
from girder.exceptions import ValidationException, GirderException
from girder.models.applet import Applet as AppletModel
from girder.models.collection import Collection as CollectionModel
from girder.utility.progress import noProgress, setResponseTimeLimit
from girder.utility.resource import loadJSON
from pyld import jsonld


class Activity(Folder):
    """
    Activities are access-controlled Folders stored in Applets, each of which
    contains versions which are also Folders.
    """
    def importActivity(self, url, applet=None, user=None, dynamic=False):
        """
        Looks for a given activity in Girder for MindLogger. If none is found,
        adds that activity.

        :param url: The URL of an accessible Activity in [ReproNim/schema-standardization](https://github.com/ReproNim/schema-standardization)
                    format.
        :type url: str
        :param applet: The ID of the Activity's parent Applet, if any.
        :type applet: str or None
        :param user: The user importing the activity
        :type user: dict
        :param dynamic: Does the URL point to a version that might change, ie,
                        `latest`?
        :param dynamic: false
        :returns: Activity, loaded into Girder for MindLogger
        """
        activity = self.findOne({
            'meta.activity.url': url
        })
        if not activity:
            activity = loadJSON(url, 'activity')
            prefName=self.preferredName(activity)
            try:
                applet = AppletModel().load(
                    id=applet,
                    level=AccessType.WRITE,
                    user=user
                )
            except:
                applet=None
            try:
                parent = self.createFolder(
                    parent=applet,
                    name=prefName,
                    parentType='folder',
                    public=True,
                    creator=user,
                    reuseExisting=True
                )
            except:
                parent = self.createFolder(
                    parent=CollectionModel().createCollection(
                        name="Activities",
                        public=True,
                        reuseExisting=True
                    ),
                    name=prefName,
                    parentType='collection',
                    public=True,
                    creator=user,
                    reuseExisting=True
                )
            activity = self.setMetadata(
                self.createFolder(
                    parent=parent,
                    name=prefName,
                    parentType='folder',
                    public=True,
                    creator=user,
                    allowRename=True,
                    reuseExisting=False
                ),
                {
                    'activity': {
                        **activity,
                        'url': url
                    }
                }
            )
        _id = activity.get('_id')
        activity = activity.get('meta', {}).get('activity')
        activity['_id'] = _id
        return(activity)


    def listVersionId(self, id, level=AccessType.ADMIN, user=None,
                      objectId=True, force=False, fields=None, exc=False):
        """
        Returns a list of activity version IDs for an Activity or a list
        containing only the given activty version IDs if an activity version ID
        is passed in.

        :param id: The id of the resource.
        :type id: string or ObjectId
        :param user: The user to check access against.
        :type user: dict or None
        :param level: The required access type for the object.
        :type level: AccessType
        :param force: If you explicitly want to circumvent access
                      checking on this resource, set this to True.
        :type force: bool
        """
        # Ensure we include extra fields to do the migration below
        extraFields = {'baseParentId', 'baseParentType', 'parentId',
                       'parentCollection', 'name', 'lowerName'}
        loadFields = self._supplementFields(fields, extraFields)
        doc = super(Folder, self).load(
            id=id, level=level, user=user, objectId=objectId, force=force,
            fields=loadFields, exc=exc)
        if doc is not None:
            pathFromRoot = Folder().parentsToRoot(doc, user=user, force=True)
            baseParent = pathFromRoot[0]
            if 'baseParentType' not in doc:
                doc['baseParentId'] = baseParent['object']['_id']
                doc['baseParentType'] = baseParent['type']
                self.update({'_id': doc['_id']}, {'$set': {
                    'baseParentId': doc['baseParentId'],
                    'baseParentType': doc['baseParentType']
                }})
            if 'lowerName' not in doc:
                doc['lowerName'] = doc['name'].lower()
                self.update({'_id': doc['_id']}, {'$set': {
                    'lowerName': doc['lowerName']
                }})
            if '_modelType' not in doc:
                doc['_modelType'] = 'folder'
            self._removeSupplementalFields(doc, fields)
            try:
                if(
                    baseParent['object']['name'].lower()=='activities' and
                    doc['baseParentType']=='collection'
                ):
                    return([str(doc['_id']) if '_id' in doc else str(id)])
                parent = pathFromRoot[-1]['object']
                grandparent = pathFromRoot[-2]['object']
                if (
                    grandparent['lowerName']=="applets" and
                    parent['baseParentType'] in {'collection', 'user'}
                ):
                    """
                    Check if grandparent is "Applets" collection or user
                    folder, ie, if this is an Activity. If so, return latest
                    version.
                    """
                    latest = Folder().childFolders(
                        parentType='folder',
                        parent=doc,
                        user=user,
                        sort=[('created', SortDir.DESCENDING)]
                    )
                    return([str(actVer['_id']) for actVer in list(latest)])
                greatgrandparent = pathFromRoot[-3]['object']
                if (
                    greatgrandparent['lowerName']=="applets" and
                    parent['baseParentType'] in {'collection', 'user'}
                ):
                    """
                    Check if greatgrandparent is "Applets" collection or user
                    folder, ie, if this is an Activity version. If so, return
                    this version.
                    """
                    return([str(doc['_id']) if '_id' in doc else str(id)])
            except:
                raise ValidationException(
                    "Invalid Activity ID."
                )


    def load(self, id, level=AccessType.ADMIN, user=None, objectId=True,
             force=False, fields=None, exc=False):
        """
        We override load in order to ensure the folder has certain fields
        within it, and if not, we add them lazily at read time. Also, this
        method will return a specific version of an Activity if given an
        Activity version ID or the latest version of an Activity if given an
        Activity ID.

        :param id: The id of the resource.
        :type id: string or ObjectId
        :param user: The user to check access against.
        :type user: dict or None
        :param level: The required access type for the object.
        :type level: AccessType
        :param force: If you explicitly want to circumvent access
                      checking on this resource, set this to True.
        :type force: bool
        """
        # Ensure we include extra fields to do the migration below
        extraFields = {'baseParentId', 'baseParentType', 'parentId',
                       'parentCollection', 'name', 'lowerName'}
        loadFields = self._supplementFields(fields, extraFields)
        doc = super(Folder, self).load(
            id=id, level=level, user=user, objectId=objectId, force=force,
            fields=loadFields, exc=exc)
        if doc is not None:
            pathFromRoot = Folder().parentsToRoot(doc, user=user, force=True)
            baseParent = pathFromRoot[0]
            if 'baseParentType' not in doc:
                doc['baseParentId'] = baseParent['object']['_id']
                doc['baseParentType'] = baseParent['type']
                self.update({'_id': doc['_id']}, {'$set': {
                    'baseParentId': doc['baseParentId'],
                    'baseParentType': doc['baseParentType']
                }})
            if 'lowerName' not in doc:
                doc['lowerName'] = doc['name'].lower()
                self.update({'_id': doc['_id']}, {'$set': {
                    'lowerName': doc['lowerName']
                }})
            if '_modelType' not in doc:
                doc['_modelType'] = 'folder'
            self._removeSupplementalFields(doc, fields)
            try:
                if(
                    baseParent['object']['name'].lower()=='activities' and
                    doc['baseParentType']=='collection'
                ):
                    return(doc)
                parent = pathFromRoot[-1]['object']
                grandparent = pathFromRoot[-2]['object']
                if (
                    grandparent['lowerName']=="applets" and
                    parent['baseParentType'] in {'collection', 'user'}
                ):
                    """
                    Check if grandparent is "Applets" collection or user
                    folder, ie, if this is an Activity. If so, return latest
                    version.
                    """
                    latest = Folder().childFolders(
                        parentType='folder',
                        parent=doc,
                        user=user,
                        sort=[('created', SortDir.DESCENDING)],
                        limit=1
                    )
                    return(latest[0])
                greatgrandparent = pathFromRoot[-3]['object']
                if (
                    greatgrandparent['lowerName']=="applets" and
                    parent['baseParentType'] in {'collection', 'user'}
                ):
                    """
                    Check if greatgrandparent is "Applets" collection or user
                    folder, ie, if this is an Activity version. If so, return
                    this version.
                    """
                    return(doc)
            except:
                raise ValidationException(
                    "Invalid Activity ID."
                )
