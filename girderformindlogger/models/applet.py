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
        displayName=None
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

        if displayName == None:
            displayName = 'applet'

        displayName = self.validateAppletDisplayName(displayName, appletsCollection)

        # create new applet
        applet = self.setMetadata(
            folder=self.createFolder(
                parent=appletsCollection,
                name=name,
                parentType='collection',
                public=True,
                creator=user,
                allowRename=True,
                displayName=displayName
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
            user,
            refreshCache=True
        ))

    def validateAppletDisplayName(self, displayName, appletsCollection):
        name = displayName
        found = False
        n = 0
        while found == False:
            found = True
            existing = self.findOne({
                'parentId': appletsCollection['_id'],
                'displayName': name,
                'parentCollection': 'collection'
            })
            if existing:
                found = False
                n = n + 1
                name = '%s (%d)' % (displayName, n)

        return name

    def createAppletFromUrl(
        self,
        name,
        protocolUrl,
        user=None,
        roles=None,
        constraints=None,
        sendEmail=True
    ):
        from girderformindlogger.models.protocol import Protocol
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
        if len(displayName) == 0:
            displayName = name if len(name) else "activity"

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
            displayName=displayName
        )
        emailMessage = "Your applet, {}, has been successfully created. The "  \
            "applet's ID is {}".format(
                name,
                str(applet.get('applet', applet).get('_id')
            )
        )
        if sendEmail and 'email' in user:
            from girderformindlogger.utility.mail_utils import sendMail
            sendMail(
                subject=name,
                text=emailMessage,
                to=[user['email']]
            )
        print(emailMessage)

    def formatThenUpdate(self, applet, user):
        from girderformindlogger.utility import jsonld_expander
        jsonld_expander.formatLdObject(
            applet,
            'applet',
            user,
            refreshCache=True
        )
        self.updateUserCacheAllRoles(user)

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
        from bson.json_util import dumps
        from girderformindlogger.utility.jsonld_expander import loadCache

        if not isinstance(relationship, str):
            raise TypeError("Applet relationship must be defined as a string.")
        if 'meta' not in applet:
            applet['meta'] = {'applet': {}}
        if 'applet' not in applet['meta']:
            applet['meta']['applet'] = {}
        applet['meta']['applet']['informantRelationship'] = relationship
        if 'cached' in applet:
            applet['cached'] = loadCache(applet['cached'])
        if 'applet' in applet['cached']:
            applet['cached']['applet']['informantRelationship'] = relationship
        applet['cached'] = dumps(applet['cached'])
        return(self.save(applet, validate=False))

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
        from girderformindlogger.models.profile import Profile as ProfileModel

        active_user_applets = self.getAppletUsers(
            applet,
            coordinator
        )

        if active_user_applets:
            for user in active_user_applets.get('active', []):
                self.updateUserCacheAllRoles(
                    UserModel().load(
                        id=ProfileModel().load(
                            user['_id'],
                            force=True
                        ).get('userId'),
                        force=True
                    )
                )

    def updateUserCacheAllRoles(self, user):
        [self.updateUserCache(role, user) for role in list(USER_ROLES.keys())]

    def updateUserCache(self, role, user, active=True, refreshCache=True):
        import threading
        from bson import json_util
        from girderformindlogger.models.profile import Profile
        from girderformindlogger.utility import jsonld_expander

        applets=self.getAppletsForUser(role, user, active)
        user['cached'] = user.get('cached', {})
        user['cached'] = json_util.loads(user['cached']) if isinstance(
            user['cached'], str
        ) else user['cached']
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
                    refreshCache=refreshCache,
                    responseDates=False
                ),
                "users": self.getAppletUsers(applet, user),
                "groups": self.getAppletGroups(
                    applet,
                    arrayOfObjects=True
                ),
                "appletId": applet['_id']
            } if role in ["coordinator", "manager"] else {
                **jsonld_expander.formatLdObject(
                    applet,
                    'applet',
                    user,
                    refreshCache=refreshCache,
                    responseDates=(role=="user")
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
                ],
                "appletId": applet['_id']
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

        profilesCache = {}
        for applet in formatted:
            if 'schedule' in applet['applet']:
                filterRequired = (role == 'user') if not self.isCoordinator(applet['appletId'], user) else False
                schedule = self.filterScheduleEvents(applet['applet']['schedule'], user, filterRequired, profilesCache)
                if 'events' in schedule:
                    applet['applet']['schedule'] = schedule
                else:
                    del applet['applet']['schedule']
            del applet['appletId']

        postformatted = []
        for applet in formatted:
            if applet['applet'].get('informantRelationship')=='parent':
                [
                    postformatted.append(
                        a
                    ) for a in jsonld_expander.childByParent(
                        user,
                        applet
                    )
                ]
            else:
                postformatted.append(applet)
        user['cached']['applets'].update({role: postformatted})
        thread = threading.Thread(
            target=UserModel().save,
            args=(user,)
        )
        thread.start()
        return(formatted)


    def filterScheduleEvents(self, schedule, user, filterRequired, profilesCache = {}):
        from girderformindlogger.models.profile import Profile

        if filterRequired and 'events' in schedule:
            events = []

            for event in schedule['events']:
                notForCurrentUser = 'users' in event

                if 'users' in event:
                    for appletUser in event['users']:
                        if appletUser not in profilesCache:
                            userData = Profile().findOne(query={'_id': ObjectId(appletUser)}, fields=['userId'])

                            if userData and 'userId' in userData:
                                profilesCache[appletUser] = userData['userId']
                        if profilesCache.get(appletUser, '') == user['_id']:
                            notForCurrentUser = False
                            break
                if not notForCurrentUser:
                    events.append(event)

            if len(events):
                newSchedule = schedule.copy()
                newSchedule['events'] = events
                return newSchedule
            else:
                return {}
        return schedule

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
                }
            )),
            *list(self.find(
                {
                    'roles.manager.groups.id': {'$in': user.get('groups', [])},
                    'meta.applet.deleted': {'$ne': active}
                }
            ))
        ] if role=="coordinator" else list(self.find(
            {
                'roles.' + role + '.groups.id': {'$in': user.get('groups', [])},
                'meta.applet.deleted': {'$ne': active}
            }
        )) if active else [
            *list(self.find(
                {
                    'roles.' + role + '.groups.id': {'$in': user.get(
                        'groups',
                        []
                    )}
                }
            )),
            *list(self.find(
                {
                    'roles.manager.groups.id': {'$in': user.get('groups', [])}
                }
            ))
        ] if role=="coordinator" else list(self.find(
            {
                'roles.' + role + '.groups.id': {'$in': user.get('groups', [])}
            }
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
                    ) for p in list(
                        profileModel.find(
                            query={'appletId': applet['_id'], 'userId': {'$exists': True}, 'profile': True}
                        )
                    )
                ],
                'pending': [

                ]
            }

            for p in list(Invitation().find(query={'appletId': applet['_id']})):
                profile = profileModel.findOne(query={'_id': p['_id']})
                userDict['pending'].append(
                    profileModel.displayProfileFields(
                        profile,
                        user,
                        forceManager=True
                    ) if profile else {
                        "_id": p["_id"],
                        "invitedBy": p["invitedBy"]
                    }
                )


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
