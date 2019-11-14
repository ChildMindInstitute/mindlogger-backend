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
from girderformindlogger import events
from girderformindlogger.api.rest import getCurrentUser
from girderformindlogger.constants import AccessType, SortDir, USER_ROLES
from girderformindlogger.exceptions import AccessException, GirderException, \
    ValidationException
from girderformindlogger.models.collection import Collection as CollectionModel
from girderformindlogger.models.folder import Folder as FolderModel
from girderformindlogger.models.group import Group as GroupModel
from girderformindlogger.models.protoUser import ProtoUser as ProtoUserModel
from girderformindlogger.models.user import User as UserModel
from girderformindlogger.utility.progress import noProgress, setResponseTimeLimit


class Applet(Folder):
    """
    Applets are access-controlled Folders, each of which links to an
    Protocol and contains any relevant constraints.
    """
    def createApplet(
        self,
        name,
        protocol={},
        user=None,
        roles=None,
        constraints=None
    ):
        """
        Method to create an Applet.

        :param name: Name for the Applet
        :type name: str
        :param protocol: Protocol to link to this Applet, with one or both
            keys: {`_id`, `url`}
        :type protocol: dict
        :param user: User creating Applet
        :type user: dict
        :param roles: Roles to set to this Applet
        :type roles: dict or None
        :param constraints: Constraints to set to this Applet
        :type constraints: dict or None
        """
        from girderformindlogger.utility import jsonld_expander

        if user==None:
            raise AccessException("You must be logged in to create an applet.")
        appletsCollection = CollectionModel().findOne({"name": "Applets"})

        # create the Applets collection if it isn't there!
        if not appletsCollection:
            CollectionModel().createCollection('Applets')
            appletsCollection = CollectionModel().findOne({"name": "Applets"})

        # create new applet
        applet = self.setMetadata(
            folder=self.createFolder(
                parent=appletsCollection,
                name=name,
                parentType='collection',
                public=True,
                creator=user,
                allowRename=True
            ),
            metadata={
                'protocol': protocol,
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

        print("Name: {}".format(appletGroupName))
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

        return(jsonld_expander.formatLdObject(
            applet,
            'applet',
            user
        ))
        return(self.formatThenUpdate(
            applet,
            user
        ))
        return({
            "_id": applet.get("_id"),
            "applet": {
                **self.unexpanded(applet),
                "name": self.preferredName(applet),
                "note - loading": "Your applet is being expanded on the "
                "server. Check back in a few minutes to see the full content."
                },
            "protocol": protocol
        })

    def formatThenUpdate(self, applet, user):
        from girderformindlogger.utility import jsonld_expander
        jsonld_expander.formatLdObject(
            applet,
            'applet',
            user
        )
        self.updateUserCacheAllRoles(user)

    def unexpanded(self, applet):
        return({
            **(
                applet.get(
                    'cached',
                    {}
                ).get('applet') if isinstance(
                    applet,
                    dict
                ) and 'cached' in applet else {
                    '_id': "applet/{}".format(
                        str(applet.get('_id'))
                    ),
                    **applet.get('meta', {}).get('applet', {})
                }
            )
        })

    def getAppletGroups(self, applet, arrayOfObjects=False):
        # get role list for applet
        roleList = self.getFullRolesList(applet)
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
                    "name": role,
                    "openRegistration": GroupModel().load(
                        groupId,
                        force=True
                    ).get('openRegistration', False)
                } if role=='user' else {
                    "id": groupId,
                    "name": role
                } for role in appletGroups for groupId in appletGroups[
                    role
                ].keys()
            ] if arrayOfObjects else appletGroups
        )

    def isManager(self, appletId, user):
        return(bool(
            str(appletId) in [
                str(applet.get('_id')) for applet in self.getAppletsForUser(
                    'manager',
                    user
                ) if applet.get('_id') is not None
            ]
        ))

    def getAppletsForGroup(self, role, groupId, active=True):
        """
        Method get Applets for a Group.

        :param role: Role to find
        :type name: str
        :param groupId: _id of group
        :type protocol: str
        :param active: Only return active Applets?
        :type active: bool
        :returns: list of dicts
        """
        applets = list(self.find(
            {
                'roles.' + role + '.groups.id': groupId,
                'meta.applet.deleted': {'$ne': active}
            }
        ))
        return(applets if isinstance(applets, list) else [applets])

    def updateUserCacheAllUsersAllRoles(self, applet, coordinator):
        [self.updateUserCacheAllRoles(user) for user in self.getAppletUsers(
            applet,
            coordinator
        )]

    def updateUserCacheAllRoles(self, user):
        [self.updateUserCache(role, user) for role in list(USER_ROLES.keys())]

    def updateUserCache(self, role, user, active=True):
        from girderformindlogger.utility import jsonld_expander

        applets=self.getAppletsForUser(role, user, active)
        user['cached'] = user.get('cached', {})
        user['cached']['applets'] = user['cached'].get('applets', {})
        user['cached']['applets'][role] = user['cached']['applets'].get(
            role,
            {}
        )
        formatted = [
            {
                **jsonld_expander.formatLdObject(
                    applet,
                    'applet',
                    user,
                    refreshCache=False,
                    responseDates=False
                ),
                "users": self.getAppletUsers(applet, user),
                "groups": self.getAppletGroups(
                    applet,
                    arrayOfObjects=True
                )
            } if role in ["coordinator", "manager"] else {
                **jsonld_expander.formatLdObject(
                    applet,
                    'applet',
                    user,
                    dropErrors=True,
                    responseDates=True if role=="user" else False
                ),
                "groups": [
                    group for group in self.getAppletGroups(applet).get(
                        role
                    ) if ObjectId(
                        group
                    ) in [
                        *user.get('groups', []),
                        *user.get('formerGroups', []),
                        *[invite['groupId'] for invite in [
                            *user.get('groupInvites', []),
                            *user.get('declinedInvites', [])
                        ]]
                    ]
                ]
            } for applet in applets if (
                applet is not None and not applet.get(
                    'meta',
                    {}
                ).get(
                    'applet',
                    {}
                ).get('deleted')
            )
        ]
        user['cached']['applets'].update({role: formatted})
        UserModel().save(user)
        return(formatted)

    def getAppletsForUser(self, role, user, active=True):
        """
        Method get Applets for a User.

        :param role: Role to find
        :type name: str
        :param user: User to find
        :type user: dict
        :param active: Only return active Applets?
        :type active: bool
        :returns: list of dicts
        """
        applets = list(self.find(
            {
                'roles.' + role + '.groups.id': {'$in': user.get('groups', [])},
                'meta.applet.deleted': {'$ne': active}
            }
        ))
        return(applets if isinstance(applets, list) else [applets])

    def getAppletUsers(self, applet, user=None):
        # get groups for applet
        appletGroups = self.getAppletGroups(applet)
        if not self.isManager(applet.get('_id', applet), user):
            return([])

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
                "email": user.get("email", ""),
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
        return(self.getFromUrl(url, 'applet', user, refreshCache)[0])

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
