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
import threading

from bson.objectid import ObjectId
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
from girderformindlogger.utility.progress import noProgress,                   \
    setResponseTimeLimit


class Applet(FolderModel):
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
        constraints=None,
        appletName=None
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

        appletName = self.validateAppletName(appletName, appletsCollection, user)

        # create new applet
        applet = self.setMetadata(
            folder=self.createFolder(
                parent=appletsCollection,
                name=name,
                parentType='collection',
                public=True,
                creator=user,
                allowRename=True,
                appletName=appletName
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
        role2AccessLevel = { 'user': AccessType.READ, 'coordinator': AccessType.ADMIN, 'manager': AccessType.ADMIN, 'editor': AccessType.WRITE, 'reviewer': AccessType.READ }
        accessList = applet.get('access', {})
        accessList['groups'] = []

        for role in USER_ROLES.keys():
            try:
                group = GroupModel().createGroup(
                    name="{} {}s".format(appletGroupName, role.title()),
                    creator=user,
                    public=False if role=='user' else True
                )
                accessList['groups'].append({ 'id': ObjectId(group['_id']), 'level': role2AccessLevel[role] })

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

        self.setAccessList(applet, accessList)
        self.update({'_id': ObjectId(applet['_id'])}, {'$set': {'access': applet.get('access', {})}})

        from girderformindlogger.models.profile import Profile

        # give all roles to creator of an applet
        profile = Profile().createProfile(applet, user, 'manager')
        profile = Profile().load(profile['_id'], force=True)

        profile['roles'] = list(USER_ROLES.keys())
        Profile().save(profile, False)

        UserModel().appendApplet(UserModel().load(user['_id'], force=True), applet['_id'], USER_ROLES.keys())

        return(jsonld_expander.formatLdObject(
            applet,
            'applet',
            user,
            refreshCache=False
        ))

    def validateAppletName(self, appletName, appletsCollection, user):
        name = appletName
        found = False
        n = 0
        while found == False:
            found = True
            existing = self.findOne({
                'parentId': appletsCollection['_id'],
                'appletName': name,
                'parentCollection': 'collection',
                'creatorId': user['_id']
            })
            if existing:
                found = False
                n = n + 1
                name = '%s(%d)' % (appletName, n)

        return name

    def createAppletFromUrl(
        self,
        name,
        protocolUrl,
        user=None,
        roles=None,
        constraints=None,
        email='',
        sendEmail=True
    ):
        from girderformindlogger.models.protocol import Protocol
        from girderformindlogger.utility import mail_utils

        # we have cases to show manager's email to users
        if mail_utils.validateEmailAddress(email):
            user['email'] = email
            user['email_encrypted'] = False
            UserModel().save(user)

        # get a protocol from a URL
        protocol = Protocol().getFromUrl(
            protocolUrl,
            'protocol',
            user,
            thread=False,
            refreshCache=True
        )

        protocol = protocol[0].get('protocol', protocol[0])

        displayName = Protocol(
        ).preferredName(
            protocol
        )

        name = name if name is not None and len(name) else displayName

        appletName = '{}/'.format(protocolUrl)

        applet = self.createApplet(
            name=name,
            protocol={
                '_id': 'protocol/{}'.format(
                    str(protocol.get('_id')).split('/')[-1]
                ),
                'url': protocol.get(
                    'meta',
                    {}
                ).get(
                    'protocol',
                    {}
                ).get('url', protocolUrl)
            },
            user=user,
            roles=roles,
            constraints=constraints,
            appletName=appletName
        )

    def createAppletFromProtocolData(
        self,
        name,
        protocol,
        user=None,
        roles=None,
        constraints=None,
        email='',
        sendEmail=True
    ):
        from girderformindlogger.models.protocol import Protocol
        from girderformindlogger.utility import mail_utils

        # we have cases to show manager's email to users
        if mail_utils.validateEmailAddress(email):
            user['email'] = email
            user['email_encrypted'] = False
            UserModel().save(user)

        # get a protocol from single json file
        protocol = Protocol().createProtocol(
            protocol,
            user
        )

        protocol = protocol.get('protocol', protocol)

        displayName = Protocol(
        ).preferredName(
            protocol
        )

        name = name if name is not None and len(name) else displayName

        appletName = '{}/'.format(protocol.get('@id'))

        applet = self.createApplet(
            name=name,
            protocol={
                '_id': 'protocol/{}'.format(
                    str(protocol.get('_id')).split('/')[-1]
                )
            },
            user=user,
            roles=roles,
            constraints=constraints,
            appletName=appletName
        )

    def formatThenUpdate(self, applet, user):
        from girderformindlogger.utility import jsonld_expander
        jsonld_expander.formatLdObject(
            applet,
            'applet',
            user,
            refreshCache=True
        )

    def getResponseData(self, appletId, reviewer, filter={}):
        """
        Function to collect response data available to given reviewer.

        :param appletId: ID of applet for which to get response data
        :type appletId: ObjectId or str
        :param reviewer: Reviewer making request
        :type reviewer: dict
        :param filter: reduction criteria (not yet implemented)
        :type filter: dict
        :reutrns: TBD
        """
        from girderformindlogger.models.ID_code import IDCode
        from girderformindlogger.models.profile import Profile
        from girderformindlogger.models.response_folder import ResponseItem
        from girderformindlogger.models.user import User
        from pymongo import DESCENDING

        if not self._hasRole(appletId, reviewer, 'reviewer'):
            raise AccessException("You are not a reviewer for this applet.")
        query = {
            "baseParentType": "user",
            "meta.applet.@id": ObjectId(appletId)
        }
        responses = list(ResponseItem().find(
            query=query,
            user=reviewer,
            sort=[("created", DESCENDING)]
        ))
        respondents = {
            str(response['baseParentId']): IDCode().findIdCodes(
                Profile().createProfile(
                    appletId,
                    User().load(response['baseParentId'], force=True),
                    'user'
                )['_id']
            ) for response in responses if 'baseParentId' in response
        }
        return([
            {
                "respondent": code,
                **response.get('meta', {})
            } for response in responses for code in respondents[
                str(response['baseParentId'])
            ]
        ])

    def updateRelationship(self, applet, relationship):
        """
        :param applet: Applet to update
        :type applet: dict
        :param relationship: Relationship to apply
        :type relationship: str
        :returns: updated Applet
        """

        if not isinstance(relationship, str):
            raise TypeError("Applet relationship must be defined as a string.")
        if 'meta' not in applet:
            applet['meta'] = {'applet': {}}
        if 'applet' not in applet['meta']:
            applet['meta']['applet'] = {}
        applet['meta']['applet']['informantRelationship'] = relationship

        return self.save(applet, validate=False)

    def unexpanded(self, applet):
        from girderformindlogger.utility.jsonld_expander import loadCache
        return({
            **(
                loadCache(applet.get(
                    'cached',
                    {}
                )).get('applet') if isinstance(
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

    def isCoordinator(self, appletId, user):
        from girderformindlogger.models.profile import Profile

        try:
            user = Profile()._canonicalUser(appletId, user)
            return(any([
                self._hasRole(appletId, user, 'coordinator'),
                self.isManager(appletId, user)
            ]))
        except:
            return(False)

    def isManager(self, appletId, user):
        return(self._hasRole(appletId, user, 'manager'))

    def _hasRole(self, appletId, user, role):
        from girderformindlogger.models.profile import Profile

        user = Profile()._canonicalUser(appletId, user)
        return(bool(
            str(appletId) in [
                str(applet.get('_id')) for applet in self.getAppletsForUser(
                    role,
                    user,
                    idOnly=True
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

    def reloadAndUpdateCache(self, applet, editor):
        from girderformindlogger.models.protocol import Protocol

        protocolUrl = applet.get('meta', {}).get('protocol', applet).get(
            'http://schema.org/url',
            applet.get('meta', {}).get('protocol', applet).get('url')
        )

        if protocolUrl is not None:
            protocol = Protocol().getFromUrl(
                protocolUrl,
                'protocol',
                editor,
                thread=False,
                refreshCache=True
            )

            protocol = protocol[0].get('protocol', protocol[0])
            if protocol.get('_id'):
                self.update({'_id': ObjectId(applet['_id'])}, {'$set': {'meta.protocol._id': protocol['_id']}})
                if 'meta' in applet and 'protocol' in applet['meta']:
                    applet['meta']['protocol']['_id'] = protocol['_id']

            from girderformindlogger.utility import jsonld_expander

            jsonld_expander.formatLdObject(
                applet,
                'applet',
                editor,
                refreshCache=False,
                responseDates=False
            )

    def getAppletsForUser(self, role, user, active=True, idOnly = False):
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
        user = UserModel().load(
            id=ObjectId(user["userId"]),
            force=True
        ) if "userId" in user else UserModel().load(
            id=ObjectId(user["_id"]),
            force=True
        ) if "_id" in user else user
        applets = [
            *list(self.find(
                {
                    'roles.' + role + '.groups.id': {'$in': user.get(
                        'groups',
                        []
                    )},
                    'meta.applet.deleted': {'$ne': active}
                }, fields = ['_id'] if idOnly else None
            )),
            *list(self.find(
                {
                    'roles.manager.groups.id': {'$in': user.get('groups', [])},
                    'meta.applet.deleted': {'$ne': active}
                }, fields = ['_id'] if idOnly else None
            ))
        ] if role=="coordinator" else list(self.find(
            {
                'roles.' + role + '.groups.id': {'$in': user.get('groups', [])},
                'meta.applet.deleted': {'$ne': active}
            }, fields = ['_id'] if idOnly else None
        )) if active else [
            *list(self.find(
                {
                    'roles.' + role + '.groups.id': {'$in': user.get(
                        'groups',
                        []
                    )}
                }, fields = ['_id'] if idOnly else None
            )),
            *list(self.find(
                {
                    'roles.manager.groups.id': {'$in': user.get('groups', [])}
                }, fields = ['_id'] if idOnly else None
            ))
        ] if role=="coordinator" else list(self.find(
            {
                'roles.' + role + '.groups.id': {'$in': user.get('groups', [])}
            }, fields = ['_id'] if idOnly else None
        ))

        # filter out duplicates for coordinators
        temp = set()
        applets = [
            k for k in applets if '_id' in k and k[
                '_id'
            ] not in temp and not temp.add(k['_id'])
        ] if isinstance(applets, list) else [applets]

        return(applets)

    def listUsers(self, applet, role, user=None, force=False):
        from girderformindlogger.models.profile import Profile
        if not force:
            if not any([
                self.isCoordinator(applet['_id'], user),
                self._hasRole(applet['_id'], user, 'reviewer')
            ]):
                return([])
        userlist = {
            p['_id']: Profile().display(p, role) for p in list(Profile().find({
                'appletId': applet['_id'],
                'userId': {
                    '$in': [
                        user['_id'] for user in list(UserModel().find({
                            'groups': {
                                '$in': [
                                    ObjectId(
                                        group
                                    ) for group in self.getAppletGroups(
                                        applet
                                    ).get(role, {}).keys()
                                ]
                            }
                        }))
                    ]
                }
            }))
        }
        return(userlist)

    def getAppletUsers(self, applet, user=None, force=False):
        """
        Function to return a list of Applet Users

        :param applet: Applet to get users for.
        :type applet: dict
        :param user: User making request
        :type user: dict
        :returns: list of dicts
        """
        from girderformindlogger.models.invitation import Invitation
        from girderformindlogger.models.profile import Profile

        profileFields = ["_id", "coordinatorDefined", "userDefined"]

        try:

            if not isinstance(user, dict):
                user = UserModel().load(
                    id=user,
                    level=AccessType.READ,
                    force=True
                ) if isinstance(user, str) else {}

            if not force:
                if not self.isCoordinator(applet.get('_id', applet), user):
                    return([])

            profileModel = Profile()
            userDict = {
                'active': [
                    profileModel.displayProfileFields(
                        p,
                        user,
                        forceManager=True
                    )
                    for p in list(
                        profileModel.find(
                            query={'appletId': applet['_id'], 'userId': {'$exists': True}, 'profile': True, 'deactivated': {'$ne': True}}
                        )
                    )
                ],
                'pending': [

                ]
            }

            for p in list(Invitation().find(query={'appletId': applet['_id']})):
                fields = ['_id', 'firstName', 'lastName', 'role', 'MRN', 'created']
                userDict['pending'].append({
                    key: p[key] for key in fields if p.get(key, None)
                })


            missing = threading.Thread(
                target=profileModel.generateMissing,
                args=(applet,)
            )
            missing.start()

            if len(userDict['active']):
                return(userDict)

            else:
                return({
                    **userDict,
                    "message": "cache updating"
                })
        except:
            import sys, traceback
            print(sys.exc_info())
            return({traceback.print_tb(sys.exc_info()[2])})

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
