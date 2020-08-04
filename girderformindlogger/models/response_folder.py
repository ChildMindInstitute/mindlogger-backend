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
from girderformindlogger.constants import AccessType
from girderformindlogger.exceptions import ValidationException, GirderException
from girderformindlogger.models.applet import Applet
from girderformindlogger.models.assignment import Assignment
from girderformindlogger.models.folder import Folder
from girderformindlogger.models.item import Item
from girderformindlogger.models.model_base import AccessControlledModel
from girderformindlogger.models.roles import getUserCipher
from girderformindlogger.utility.progress import noProgress, setResponseTimeLimit
from girderformindlogger.models.aes_encrypt import AESEncryption
from bson import json_util

class ResponseItem(AESEncryption, Item):
    def initialize(self):
        self.name = 'item'
        self.ensureIndices(('folderId', 'name', 'lowerName',
                            ([('folderId', 1), ('name', 1)], {})))
        self.ensureTextIndex({
            'name': 1,
            'description': 1
        })
        self.resourceColl = 'folder'
        self.resourceParent = 'folderId'

        self.exposeFields(level=AccessType.READ, fields=(
            '_id', 'size', 'updated', 'description', 'created', 'meta',
            'creatorId', 'folderId', 'name', 'baseParentType', 'baseParentId',
            'copyOfItem'))

        self.initAES([
            ('meta.responses', 1024),
            ('meta.last7Days.responses', 1024),
        ])

    def encodeDocument(self, document):
        metadata = document.get('meta', None)
        if metadata:
            if 'responses' in metadata:
                metadata['items'] = list(dict.keys(metadata['responses']))

                for i in range(0, len(metadata['items'])):
                    metadata['responses'][str(i)] = metadata['responses'].pop(metadata['items'][i])
                metadata['responses'] = json_util.dumps(metadata['responses'])

            last7Days = metadata.get('last7Days', {}).get('responses')
            if last7Days:
                if 'items' not in metadata:
                    metadata['items'] = list(dict.keys(last7Days))

                for i in range(0, len(metadata['items'])):
                    last7Days[str(i)] = last7Days.pop(metadata['items'][i])

                metadata['last7Days']['responses'] = json_util.dumps(last7Days)

        return document

    def decodeDocument(self, document):
        metadata = document.get('meta', None)
        if metadata:
            if 'responses' in metadata and isinstance(metadata['responses'], str):
                metadata['responses'] = json_util.loads(metadata['responses'])

                for i in range(0, len(metadata.get('items', []))):
                    metadata['responses'][metadata['items'][i]] = metadata['responses'].pop(str(i))

            last7Days = metadata.get('last7Days', {}).get('responses')
            if last7Days and isinstance(last7Days, str):
                last7Days = metadata['last7Days']['responses'] = json_util.loads(last7Days)

                for i in range(0, len(metadata.get('items', []))):
                    last7Days[str(i)][0]['date'] = last7Days[str(i)][0]['date'].replace(tzinfo=None)
                    last7Days[metadata['items'][i]] = last7Days.pop(str(i))

            metadata.pop('items')

        return document

    def updateAESKey(self, document, baseKey):
        responseStartTime = document.get('meta', {}).get('responseStarted', None)
        if responseStartTime:
            timestamp = datetime.datetime.fromtimestamp(responseStartTime//1000).isoformat()[-32:].encode('utf-8')
            length = len(timestamp)
            self.AES_KEY = bytes( (baseKey[i] ^ timestamp[i%length] ^ 0x34) for i in range(0, 32))

    def createResponseItem(self, name, creator, folder, description='',
                   reuseExisting=False, readOnly=False):
        """
        Create a new response item. The creator will be given admin access to it.

        :param name: The name of the item.
        :type name: str
        :param description: Description for the item.
        :type description: str
        :param folder: The parent folder of the item.
        :param creator: User document representing the creator of the item.
        :type creator: dict
        :param reuseExisting: If an item with the given name already exists
            under the given folder, return that item rather than creating a
            new one.
        :type reuseExisting: bool
        :returns: The item document that was created.
        """
        if reuseExisting:
            existing = self.findOne({
                'folderId': folder['_id'],
                'name': name
            })
            if existing:
                return existing

        now = datetime.datetime.utcnow()

        if not isinstance(creator, dict) or '_id' not in creator:
            # Internal error -- this shouldn't be called without a user.
            raise GirderException('Creator must be a user.',
                                  'girderformindlogger.models.item.creator-not-user')

        if 'baseParentType' not in folder:
            pathFromRoot = self.parentsToRoot({'folderId': folder['_id']},
                                              creator, force=True)
            folder['baseParentType'] = pathFromRoot[0]['type']
            folder['baseParentId'] = pathFromRoot[0]['object']['_id']

        return self.save({
            'name': self._validateString(name),
            'description': self._validateString(description),
            'folderId': ObjectId(folder['_id']),
            'creatorId': creator['_id'],
            'baseParentType': folder['baseParentType'],
            'baseParentId': folder['baseParentId'],
            'created': now,
            'updated': now,
            'size': 0,
            'readOnly': readOnly
        })


class ResponseFolder(Folder):
    """
    Users own their own ResponseFolders.
    """

    def load(self, user, level=AccessType.ADMIN, reviewer=None, force=False,
    applet=None, subject=None):
        """
        We override load in order to ensure the folder has certain fields
        within it, and if not, we add them lazily at read time.

        :param user: The user for whom to get the ResponseFolder.
        :type id: dict
        :param reviewer: The user to check access against.
        :type user: dict or None
        :param level: The required access type for the object.
        :type level: AccessType
        :param reviewer: The user trying to see the data.
        :type reviewer: dict
        :param applet: ID of Applet to which we are loading responses.
                       "Responses" Folder containing all such Folders if None.
        :type applet: str or None
        :param subject: Applet-specific ID for response subject if getting
                        responses about a specific subject.
        :type subject: str or None
        :returns: Folder or list of Folders
        """
        responseFolder = Folder().load(
            id=Folder().createFolder(
                parent=user, parentType='user', name='Responses',
                creator=user, reuseExisting=True, public=False
            ).get('_id'),
            user=reviewer,
            level=AccessType.READ
        )
        accessList = Folder().getFullAccessList(responseFolder)
        accessList = {
            k: [
                {
                    "id": i.get('id'),
                    "level": AccessType.ADMIN if i.get('id')==str(
                        user.get('_id')
                    ) else i.get('level')
                } for i in accessList[k]
            ] for k in accessList
        }
        if str(user.get('_id')) not in [
            u.get('id') for u in accessList.get('users', [])
        ]:
            accessList.get('users', {}).append(
                {
                    "id": str(user.get('_id')),
                    "level": AccessType.ADMIN
                }
            )
        Folder().setAccessList(responseFolder, accessList)
        if applet:
            responseFolders = []
            allResponseFolders = list(Folder().childFolders(
                parent=responseFolder,
                parentType='folder',
                user=reviewer
            ))
            subjectResponseFolders = list(itertools.chain.from_iterable([
                list(Folder().childFolders(
                    parent=appletResponsesFolder,
                    parentType='folder',
                    user=reviewer
                )) for appletResponsesFolder in allResponseFolders
            ]))
            if subject:
                assignments = Assignment().findAssignments(applet.get('_id'))
                subjectFilter = [
                    getUserCipher(
                        appletAssignment,
                        subject
                    ) for appletAssignment in assignments
                ]
                subjectResponseFolders = [
                    sRF for sRF in subjectResponseFolders if sRF.get(
                        'name'
                    ) in subjectFilter or srf.get(
                        'subject',
                        {}
                    ).get('@id') in subjectFilter
                ]
            responseFolders += list(Folder().find(
                {   '$and': [
                        {'$or': [
                            {'meta.applet.@id': str(applet)},
                            {'meta.applet.url': str(applet)}
                        ]},
                        {'$or': [
                            {
                                'parentId': parent['_id']
                            } for parent in subjectResponseFolders
                        ]}
                    ]
                }
            ))
            if len(responseFolders)==1:
                return(responseFolders[0])
            else:
                return(responseFolders)
        return(responseFolder)
