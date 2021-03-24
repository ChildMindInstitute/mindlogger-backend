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
from girderformindlogger.constants import AccessType, SortDir, MODELS
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

    def getImageAndDescription(self, protocol):
        description = protocol.get('schema:description', [])
        image = protocol.get('schema:image', '')

        return {
            'description': description[0]['@value'] if description else '',
            'image': image
        }

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

    def duplicateProtocol(self, protocolId, editor, prefLabel=None):
        from girderformindlogger.models.screen import Screen
        from girderformindlogger.utility import jsonld_expander

        formatted = jsonld_expander.formatLdObject(self.load(protocolId, force=True), 'protocol', editor)

        for key in ['url', 'schema:url']:
            if key in formatted['protocol']:
                formatted['protocol'].pop(key)

        if prefLabel:
            for key in formatted['protocol']:
                if key.endswith('prefLabel') and isinstance(formatted['protocol'][key], list):
                    formatted['protocol'][key][0]['@value'] = prefLabel

        formatted['protocol'].pop('_id')
        protocol = {
            'protocol': {
                formatted['protocol']['@id']: {
                    'expanded': formatted['protocol'],
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
                'expanded': activity,
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

        # add folder to save historical data
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

            historyFolder = FolderModel().setMetadata(historyFolder, {
                'referenceId': referencesFolder['_id']
            })
        else:
            referencesFolder = FolderModel().load(historyFolder['meta']['referenceId'], force=True)

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

        if not protocol['meta'].get('contributionId'):
            contributionFolder = FolderModel().createFolder(
                name='contribution of ' + protocol['name'],
                parent=protocol,
                parentType='folder',
                public=False,
                creator=user,
                allowRename=True,
                reuseExisting=True
            )

            protocol['meta']['contributionId'] = contributionFolder['_id']
            updated = True

        if updated:
            protocol = self.setMetadata(protocol, protocol['meta'])

        return (historyFolder, referencesFolder)

    def initHistoryData(self, historyFolder, referencesFolder, protocolId, user, activityIDRef = {}, itemIDRef = {}):
        from girderformindlogger.utility import jsonld_expander
        from girderformindlogger.models.item import Item as ItemModel

        activities = list(FolderModel().find({ 'meta.protocolId': ObjectId(protocolId) }))
        items = list(ItemModel().find({ 'meta.protocolId': ObjectId(protocolId) }))

        protocol = self.load(protocolId, force=True)
        schemaVersion = protocol['meta'].get('protocol', {}).get('schema:version', None)

        currentVersion = schemaVersion[0].get('@value', '0.0.0') if schemaVersion else '0.0.0'

        activityIdToHistoryObj = {}
        for activity in activities:
            identifier = activity['meta'].get('activity', {}).get('url', None)
            if identifier:
                activityId = str(activity['_id'])
                if activityId in activityIDRef:
                    activity['_id'] = activityIDRef[activityId]
                    activityId = str(activityIDRef[activityId])

                activityIdToHistoryObj[activityId] = jsonld_expander.insertHistoryData(activity, identifier, 'activity', currentVersion, historyFolder, referencesFolder, user)

        for item in items:
            identifier = item['meta'].get('screen', {}).get('url', None)
            if identifier:
                if str(item['_id']) in itemIDRef:
                    item['_id'] = itemIDRef[str(item['_id'])]

                if str(item['meta']['activityId']) in activityIDRef:
                    item['meta']['activityId'] = activityIDRef[str(item['meta']['activityId'])]

                activityHistoryObj = activityIdToHistoryObj[str(item['meta']['activityId'])]

                item['meta'].update({
                    'originalActivityId': item['meta']['activityId'],
                    'activityId': activityHistoryObj['_id']
                })

                jsonld_expander.insertHistoryData(item, identifier, 'screen', currentVersion, historyFolder, referencesFolder, user)

    def compareVersions(self, version1, version2):
        vs1 = version1.split('.')
        vs2 = version2.split('.')

        for i in range(0, len(vs1)):
            if vs1[i] < vs2[i]:
                return -1
            if vs1[i] > vs2[i]:
                return 1

        return 0

    def getHistoryDataFromItemIRIs(self, protocolId, IRIGroup):
        from girderformindlogger.models.item import Item as ItemModel
        from girderformindlogger.utility import jsonld_expander

        protocol = self.load(protocolId, force=True)

        items = {}
        activities = {}
        itemReferences = {}
        result = {
            'items': items,
            'activities': activities,
            'itemReferences': itemReferences
        }

        if 'historyId' not in protocol.get('meta', {}):
            return result

        historyFolder = FolderModel().load(protocol['meta']['historyId'], force=True)
        if 'referenceId' not in historyFolder.get('meta', {}):
            return result

        referencesFolder = FolderModel().load(historyFolder['meta']['referenceId'], force=True)
        itemModel = ItemModel()

        for IRI in IRIGroup:
            reference = itemModel.findOne({ 'folderId': referencesFolder['_id'], 'meta.identifier': IRI })
            if not reference:
                continue

            history = reference['meta']['history']

            for version in IRIGroup[IRI]:
                if version not in itemReferences:
                    itemReferences[version] = {}

                inserted = False
                for i in range(0, len(history)):
                    if self.compareVersions(version, history[i]['version']) <= 0:
                        if not history[i].get('reference', None):
                            continue

                        if history[i]['reference'] not in items:
                            (modelType, referenceId) = history[i]['reference'].split('/')
                            model = MODELS()[modelType]().findOne({
                                '_id': ObjectId(referenceId)
                            })
                            items[history[i]['reference']] = jsonld_expander.loadCache(model['cached'])

                            activityId = str(model['meta']['activityId'])

                            if activityId not in activities:
                                activities[activityId] = jsonld_expander.loadCache(
                                    FolderModel().load(activityId, force=True)['cached']
                                )
                        if history[i]['reference']:
                            itemReferences[version][IRI] = history[i]['reference']
                        inserted = True

                        break

                if not inserted:
                    itemReferences[version][IRI] = None # this is same as latest version

        return result

    def getProtocolChanges(self, protocolId, localVersion, localUpdateTime):
        from girderformindlogger.models.item import Item as ItemModel

        changeInfo = { 'screen': {}, 'activity': {} }
        hasUrl = False

        protocol = Protocol().load(protocolId, force=True)

        schemaVersion = protocol.get('meta', {}).get('protocol', {}).get('schema:schemaVersion', None)

        currentVersion = schemaVersion[0].get('@value', '0.0.0') if schemaVersion else '0.0.0'

        if 'historyId' not in protocol.get('meta', {}):
            return None

        historyFolder = FolderModel().load(protocol['meta']['historyId'], force=True)

        if 'referenceId' not in historyFolder.get('meta', {}):
            return None

        referencesFolder = FolderModel().load(historyFolder['meta']['referenceId'], force=True)

        itemModel = ItemModel()

        references = list(itemModel.find({
            'folderId': referencesFolder['_id'],
            'meta.lastVersion': localVersion
        }))

        updates = itemModel.find({ 
            'folderId': referencesFolder['_id'], 
            'updated': {
                '$gt': datetime.datetime.fromisoformat(localUpdateTime)
            }
        })

        for reference in updates:
            if reference['meta'].get('lastVersion', None) != localVersion:
                references.append(reference)

        for reference in references:
            history = reference['meta'].get('history')

            if reference['meta'].get('identifier', '') and len(history):
                modelType = reference['meta'].get('modelType', '')

                if str(reference['meta']['identifier']).startswith('https://'):
                    hasUrl = True

                # to handle old data without modelType in the schema
                if not modelType:
                    lastReference = history[len(history)-1]['reference']
                    if lastReference:
                        modelType = lastReference.split('/')[0]
                    else:
                        modelType = 'screen' if '/' in str(reference['meta']['identifier']) else 'activity'

                if self.compareVersions(history[0]['version'], localVersion) < 0:
                    changeInfo[modelType][str(reference['meta']['identifier'])] = 'updated'
                else:
                    changeInfo[modelType][str(reference['meta']['identifier'])] = 'created'

        return (hasUrl, changeInfo)

    def getContributions(self, protocolId):
        from girderformindlogger.utility import jsonld_expander
        from girderformindlogger.models.item import Item as ItemModel

        protocol = self.load(protocolId, force=True)

        if not protocol.get('meta', {}).get('contributionId', None):
            return {}

        contributions = list(ItemModel().find({
            'folderId': protocol['meta']['contributionId']
        }))

        result = {}
        for item in contributions:
            formattedItem = jsonld_expander.loadCache(item['cached'])

            result[str(item['meta']['itemId'])] = formattedItem

        return result
