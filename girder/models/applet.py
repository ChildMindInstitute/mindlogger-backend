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
from .folder import Folder
from girder import events
from girder.api.rest import getCurrentUser
from girder.constants import AccessType, SortDir, USER_ROLES
from girder.exceptions import AccessException, GirderException, \
    ValidationException
from girder.models.collection import Collection as CollectionModel
from girder.models.folder import Folder as FolderModel
from girder.models.group import Group as GroupModel
from girder.models.protoUser import ProtoUser as ProtoUserModel
from girder.models.user import User as UserModel
from girder.utility.progress import noProgress, setResponseTimeLimit


class Applet(Folder):
    """
    Applets are access-controlled Folders, each of which links to an
    ActivitySet and contains any relevant constraints.
    """
    def createApplet(
        self,
        name,
        activitySet={},
        user=None,
        roles=None,
        constraints=None
    ):
        """
        Function to create an Applet.

        :param name: Name for the Applet
        :type name: str
        :param activitySet: ActivitySet to link to this Applet, with one or both
            keys: {`_id`, `url`}
        :type activitySet: dict
        :param user: User creating Applet
        :type user: dict
        :param roles: Roles to set to this Applet
        :type roles: dict or None
        :param constraints: Constraints to set to this Applet
        :type constraints: dict or None
        """
        if user==None:
            raise AccessException("You must be logged in to create an applet.")
        appletsCollection = CollectionModel().findOne({"name": "Applets"})
        # # check if applet exists with creator as a manager
        applets = list(FolderModel().find({
            "meta.actvitySet.url": activitySet.get('url'),
            "parentId": appletsCollection.get('_id')
        }))

        # managed = [applet for applet in applets if applet.get('_id') in [
        #     a.get('_id') for a in list(itertools.chain.from_iterable([
        #         list(AppletModel().find(
        #             {
        #                 'roles.' + role + '.groups.id': groupId,
        #                 'meta.applet.deleted': {'$ne': True}
        #             }
        #         )) for groupId in user.get('groups', [])
        #     ]))
        # ]]
        #
        # if len(managed):
        #     return(managed)

        # check if applet needs updated

        # create new applet

        applet = FolderModel().setMetadata(
            folder=FolderModel().createFolder(
                parent=appletsCollection,
                name=name,
                parentType='collection',
                public=True,
                creator=user,
                allowRename=True
            ),
            metadata={
                'activitySet': activitySet,
                'applet': constraints if constraints is not None and isinstance(
                    constraints,
                    dict
                ) else {}
            }
        )
        appletGroupName = "Default {} ({})".format(
            name,
            str(applet.get('_id', ''))
        )
        # Create user groups
        for role in USER_ROLES.keys():
            try:
                group = GroupModel().createGroup(
                    name="{} {}s".format(appletGroupName, role.title()),
                    creator=user,
                    public=False if role=='user' else True
                )
            except ValidationException:
                numero = 0
                numberedName = appletGroupName
                while GroupModel().findOne(query={'name': numberedName}):
                    numero += 1
                    numberedName = "{} {} {}s".format(
                        appletGroupName,
                        str(numero),
                        role.title()
                    )
                group = GroupModel().createGroup(
                    name=numberedName,
                    creator=user,
                    public=False if role=='user' else True
                )
            self.setGroupRole(
                doc=applet,
                group=group,
                role=role,
                currentUser=user,
                force=False
            )
        return(applet)

    def getAppletGroups(self, appletId, arrayOfObjects=False):
        # get role list for applet
        roleList = self.getFullRolesList(appletId)
        # query groups from role list`& return
        appletGroups = {
            role: {
                g.get("_id"): g.get("name") for g in roleList[role]['groups']
            } for role in roleList
        }
        return(
            [
                {
                    "id": groupId,
                    "name": role
                } for role in appletGroups for groupId in appletGroups[
                    role
                ].keys()
            ] if arrayOfObjects else appletGroups
        )

    def getAppletUsers(self, appletId):
        # get groups for applet
        appletGroups = self.getAppletGroups(appletId)
        # query users for groups by status
        userList = {
            role: {
                groupId: {
                    "pending": [
                        *list(UserModel().find(
                            query={
                                "groupInvites.groupId": {"$in": [
                                    ObjectId(groupId)
                                ]}
                            },
                            fields=['_id', 'email']
                        )),
                        *list(ProtoUserModel().find(
                            query={
                                "groupInvites.groupId": {"$in": [
                                    ObjectId(groupId)
                                ]}
                            }
                        ))
                    ],
                    "active": list(UserModel().find(
                        query={"groups": {"$in": [ObjectId(groupId)]}},
                        fields=['_id', 'email']
                    ))
                } for groupId in appletGroups[role]
            } for role in appletGroups
        }
        # restructure dictionary & return
        return([
            {
                "_id": user.get("_id"),
                "email": user.get("email"),
                "groups": [{
                        "_id": groupId,
                        "name": appletGroups[role][groupId],
                        "status": status,
                        "role": role
                }]
            } for role in userList for groupId in userList[
                role
            ] for status in userList[role][groupId] for user in userList[
                role
            ][groupId][status]
        ])


    def importUrl(self, url, user=None, refreshCache=False):
        """
        Gets an applet from a given URL, checks against the database, stores
        and returns that applet.

        Deprecated.
        """
        return(self.getFromUrl(url, 'applet', user, refreshCache))

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
                    parent['name'] == "Applets" and
                    doc['baseParentType'] in {'collection', 'user'}
                ):
                    """
                    Check if parent is "Applets" collection or user
                    folder, ie, if this is an Applet. If so, return Applet.
                    """
                    return(doc)
            except:
                raise ValidationException(
                    "Invalid Applet ID."
                )
