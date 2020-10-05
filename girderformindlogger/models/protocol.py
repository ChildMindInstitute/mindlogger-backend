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
import itertools
import json
import os
import six

from bson.objectid import ObjectId
from girderformindlogger import events
from girderformindlogger.api.rest import getCurrentUser
from girderformindlogger.constants import AccessType, SortDir
from girderformindlogger.exceptions import ValidationException, GirderException
from girderformindlogger.models.folder import Folder as FolderModel
from girderformindlogger.models.user import User as UserModel
from girderformindlogger.utility.progress import noProgress, setResponseTimeLimit

class Protocol(FolderModel):
    def importUrl(self, url, user=None, refreshCache=False):
        """
        Gets an activity set from a given URL, checks against the database,
        stores and returns that activity set.
        """
        return(
            self.getFromUrl(url, 'protocol', user, refreshCache, thread=False)[
                0
            ]
        )

    def getCache(self, id):
        protocol = self.findOne({'_id': ObjectId(id)}, ['cached'])
        cached = protocol.get('cached')
        if protocol and cached:
            return cached
        return None

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
        doc = super(FolderModel, self).load(
            id=id, level=level, user=user, objectId=objectId, force=force,
            fields=loadFields, exc=exc)
        if doc is not None:
            pathFromRoot = FolderModel().parentsToRoot(doc, user=user, force=True)
            if 'baseParentType' not in doc:
                baseParent = pathFromRoot[0]
                doc['baseParentId'] = baseParent['object']['_id']
                doc['baseParentType'] = baseParent['type']
                self.update({'_id': doc['_id']}, {'$set': {
                    'baseParentId': doc['baseParentId'],
                    'baseParentType': doc['baseParentType']
                }})
            if 'lowerName' not in doc:
                doc['lowerName'] = doc['name'].lower()
                self.update(
                    {'_id': doc['_id']},
                    {'$set': {
                        'lowerName': doc['lowerName']
                    }}
                )
            if '_modelType' not in doc:
                doc['_modelType'] = 'folder'
            self._removeSupplementalFields(doc, fields)
            try:
                parent = pathFromRoot[-1]['object']
                if (
                    parent['name'] in {"Activitysets", "Protocols"} and
                    doc['baseParentType'] in {'collection', 'user'}
                ):
                    """
                    Check if parent is "Protocols" collection or user
                    folder, ie, if this is a Protocol. If so, return
                    Protocol.
                    """
                    return(doc)
            except:
                raise ValidationException(
                    "Invalid Protocol ID."
                )

    def createProtocol(self, document, user, editExisting=False):
        from girderformindlogger.utility import jsonld_expander

        return jsonld_expander.loadFromSingleFile(document, user, editExisting)

    def duplicateProtocol(self, protocolId, editor):
        from girderformindlogger.models.screen import Screen
        from girderformindlogger.utility import jsonld_expander

        formatted = jsonld_expander.formatLdObject(self.load(protocolId, force=True), 'protocol', editor)

        for key in ['url', 'schema:url']:
            if key in formatted['protocol']:
                formatted['protocol'].pop(key)

        formatted['protocol'].pop('_id')
        protocol = {
            'protocol': {
                formatted['protocol']['@id']: {
                    'expanded': jsonld_expander.fixUpOrderList(formatted['protocol'], 'screen'),
                    'ref2Document': {
                        'duplicateOf': protocolId
                    }
                }
            },
            'activity': {},
            'screen': {}
        }

        activityId2Key = {}

        for activityKey in formatted['activities']:
            activity = formatted['activities'][activityKey]
            activityId = activity.pop('_id').split('/')[-1]

            for key in ['url', 'schema:url']:
                if key in activity:
                    activity.pop(key)
            protocol['activity'][activityKey] = {
                'parentKey': 'protocol',
                'parentId': formatted['protocol']['@id'],
                'expanded': jsonld_expander.fixUpOrderList(activity, 'activity'),
                'ref2Document': {
                    'duplicateOf': activityId
                }
            }
            activityId2Key[activityId] = activityKey

        itemId2ActivityId = {}
        
        items = list(Screen().find({'meta.protocolId': protocolId}))
        for item in items:
            itemId2ActivityId[str(item['_id'])] = str(item['meta'].get('activityId', None))

        for itemKey in formatted['items']:
            item = formatted['items'][itemKey]
            itemId = item.pop('_id').split('/')[-1]

            for key in ['url', 'schema:url']:
                if key in item:
                    item.pop(key)

            protocol['screen'][itemKey] = {
                'parentKey': 'activity',
                'parentId': activityId2Key[itemId2ActivityId[itemId]],
                'expanded': item,
                'ref2Document': {
                    'duplicateOf': itemId
                }
            }

        protocolId = jsonld_expander.createProtocolFromExpandedDocument(protocol, editor)

        return jsonld_expander.formatLdObject(
            self.load(protocolId, force=True),
            mesoPrefix='protocol',
            user=editor,
            refreshCache=True
        )

    def createHistoryFolders(
        self,
        protocolId,
        user
    ):
        protocol = self.load(protocolId, force=True)
        updated = False

        if not protocol['meta'].get('historyId', None):
            historyFolder = FolderModel().createFolder(
                name='history of ' + protocol['name'],
                parent=protocol,
                parentType='folder',
                public=False,
                creator=user,
                allowRename=True,
                reuseExisting=False
            )

            protocol['meta']['historyId'] = historyFolder['_id']
            updated = True
        else:
            historyFolder = FolderModel().load(protocol['meta']['historyId'], force=True)
        
        if not historyFolder.get('meta', {}).get('referenceId', None):
            referencesFolder = FolderModel().createFolder(
                name='reference of history data for ' + protocol['name'],
                parent=historyFolder,
                parentType='folder',
                public=False,
                creator=user,
                allowRename=True,
                reuseExisting=False,
            )

            FolderModel().setMetadata(historyFolder, {
                'referenceId': referencesFolder['_id']
            })


        # add folder to save contents
        if not protocol['meta'].get('contentId', None):
            contentFolder = FolderModel().createFolder(
                name='content of ' + protocol['name'],
                parent=protocol,
                parentType='folder',
                public=False,
                creator=user,
                allowRename=True,
                reuseExisting=False
            )

            protocol['meta']['contentId'] = contentFolder['_id']
            updated = True

        if updated:
            protocol = self.setMetadata(protocol, protocol['meta'])

        return protocol
