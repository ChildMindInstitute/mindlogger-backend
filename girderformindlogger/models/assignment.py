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
from girderformindlogger import events
from girderformindlogger.constants import AccessType, SortDir
from girderformindlogger.exceptions import ValidationException, GirderException
from girderformindlogger.models.applet import Applet
from girderformindlogger.models.collection import Collection
from girderformindlogger.models.folder import Folder
from girderformindlogger.utility.progress import noProgress, setResponseTimeLimit


class Assignment(Folder):
    """
    Assignments are access-controlled Folders, each of which contains
    managerially-controlled Applet Folders.
    """
    def create(self, applet, user):
        """
        Create an Assignment for a given Applet, returning an existing
        Assignment if one or more exists.

        :param applet: The ID of the Applet for which to find Assignments.
        :type applet: str
        :param user: User
        :type user: User
        :returns: New Assignments
        """
        # validate Applet ID
        try:
            applet = Applet().load(id=applet, force=True)
        except:
            raise ValidationException(
                message='Invalid Applet ID',
                field='applet'
            )
        assignmentsCollection = Collection().findOne({'name': 'Assignments'})
        # for some reason below didn't work/help.. so I added Assignments manually.
        if not assignmentsCollection:
            Collection().createCollection('Assignments')
        try:
            assignment = Folder().createFolder(
                parent=assignmentsCollection, parentType='collection',
                name=Applet().preferredName(applet), creator=user,
                reuseExisting=True, public=False)
        except:
            assignmentsCollection = Folder().createFolder(
                parent=user, parentType='user', name='Assignments',
                creator=user, reuseExisting=True, public=False)
            assignment = Folder().createFolder(
                parent=assignmentsCollection, parentType='folder',
                name=Applet().preferredName(applet), creator=user,
                reuseExisting=True, public=False)
        return(assignment)

    def findAssignments(self, applet):
        """
        Find all Assignments for a given Applet.

        :param applet: The ID of the Applet for which to find Assignments.
        :type applet: str
        :returns: list of Assignments
        """
        # validate Applet ID
        try:
            Applet().load(id=applet, force=True)
        except:
            raise ValidationException(
                message='Invalid Applet ID',
                field='applet'
            )
        allAssignments = [
            {
                '_id': a['_id'],
                '_modelType': 'collection'
            } for a in Collection().find({'name': 'Assignments'})
        ] + [
            {
                '_id': a['_id'],
                '_modelType': 'folder'
            } for a in Folder().find({'name': 'Assignments'})
        ]
        foundAssignments = Folder().find(
            {   '$and': [
                    {'$or': [
                        {'meta.applet.@id': str(applet)},
                        {'meta.applet.url': str(applet)}
                    ]},
                    {'$or': [
                        {'parentId': parent['_id']} for parent in allAssignments
                    ]}
                ]
            }
        )
        return(list(foundAssignments))


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
                self.update({'_id': doc['_id']}, {'$set': {
                    'lowerName': doc['lowerName']
                }})
            if '_modelType' not in doc:
                doc['_modelType'] = 'folder'
            self._removeSupplementalFields(doc, fields)
            try:
                parent = pathFromRoot[-1]['object']
                if (
                    parent['name']=="Assigments" and
                    doc['baseParentType'] in {'collection', 'user'}
                ):
                    """
                    Check if parent is "Assignments" collection or user
                    folder, ie, if this is an Assignment. If so, return
                    Assignment.
                    """
                    appletAssignment = list(FolderModel().childFolders(
                        parent=doc,
                        parentType=doc['baseParentType'],
                        user=user,
                        filters={
                            'meta.applet.@id': str(
                                doc['_id']
                            ) if '_id' in doc else None
                        }
                    ))
                    appletAssignment = appletAssignment[0] if len(
                        appletAssignment
                    ) else FolderModel().setMetadata(
                        FolderModel().createFolder(
                            parent=doc,
                            name=FolderModel().preferredName(doc),
                            parentType=doc['baseParentType'],
                            public=False,
                            creator=user,
                            allowRename=True,
                            reuseExisting=False
                        ),
                        {
                            'applet': {
                                '@id': str(
                                    doc['_id']
                                ) if '_id' in doc else None
                            }
                        }
                    )
            except:
                raise ValidationException(
                    "Invalid Assignment Applet ID."
                )
