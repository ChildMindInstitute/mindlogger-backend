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
import re
import pytz

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
from girderformindlogger.models.account_profile import AccountProfile
from girderformindlogger.models.profile import Profile
from girderformindlogger.models.events import Events as EventsModel
from girderformindlogger.models.item import Item as ItemModel
from girderformindlogger.external.notification import send_applet_update_notification
from bson import json_util
from girderformindlogger.utility import mail_utils
from girderformindlogger.i18n import t
from datetime import datetime as dt

RETENTION_SET = {
    'day': 1,
    'week': 7,
    'month': 30,
    'year': 365
}

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
        appletRole='editor',
        accountId=None,
        encryption={}
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
        from girderformindlogger.models.protocol import Protocol

        if user==None:
            raise AccessException("You must be logged in to create an applet.")
        appletsCollection = CollectionModel().findOne({"name": "Applets"})

        # create the Applets collection if it isn't there!
        if not appletsCollection:
            CollectionModel().createCollection('Applets')
            appletsCollection = CollectionModel().findOne({"name": "Applets"})

        name = self.validateAppletName('%s (0)' % (name), appletsCollection, accountId)

        # create new applet
        metadata = {
            'protocol': protocol,
            'applet': constraints if constraints is not None and isinstance(
                constraints,
                dict
            ) else {},
            'encryption': encryption,
            'retentionSettings': {
                'period': 5,
                'retention': 'year',
                'enabled': True
            }
        }
        metadata['applet']['displayName'] = name

        applet = self.setMetadata(
            folder=self.createFolder(
                parent=appletsCollection,
                name=name,
                parentType='collection',
                public=True,
                creator=user,
                allowRename=True,
                accountId=accountId
            ),
            metadata=metadata
        )

        FolderModel().update({
            '_id': ObjectId(protocol['_id'].split('/')[-1])
        }, {
            '$set': {
                'meta.appletId': applet['_id']
            }
        })

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

        Protocol().createHistoryFolders(protocol.get('_id', '').split('/')[-1], user)

        formatted = jsonld_expander.formatLdObject(
            applet,
            'applet',
            user,
            refreshCache=False
        )

        if 'activities' in formatted:
            self.updateActivities(applet, formatted)

        # give all roles to creator of an applet
        applet = self.load(applet['_id'], force=True)
        profile = Profile().createProfile(applet, user, appletRole)
        profile = Profile().load(profile['_id'], force=True)

        profile['roles'] = ['editor', 'user'] if appletRole == 'editor' else list(USER_ROLES.keys())
        Profile().save(profile, False)

        AccountProfile().appendApplet(AccountProfile().findOne({'accountId': accountId, 'userId': user['_id']}), applet['_id'], profile['roles'])

        owner = AccountProfile().getOwner(accountId)
        inviter = UserModel().load(user['_id'], force=True)

        self.grantAccessToApplet(UserModel().load(owner['userId'], force=True), applet, 'manager', inviter)
        Profile().updateOwnerProfile(applet)

        return formatted

    def getSchedule(self, applet, user, getAllEvents, eventFilter=None, localEvents=[]):
        if not getAllEvents:
            schedule = EventsModel().getScheduleForUser(applet['_id'], user['_id'], eventFilter)
            events = schedule.get('events', {})

            for localEvent in localEvents:
                eventId = localEvent.get('id', None)
                updated = localEvent.get('updated', None)

                if eventId in events and events[eventId].get('updated', None) == updated:
                    events.pop(eventId)
        else:
            if not self.isCoordinator(applet['_id'], user):
                raise AccessException(
                    "Only coordinators and managers can get all events."
                )
            schedule = EventsModel().getSchedule(applet['_id'])

        return schedule

    def grantRole(self, applet, userProfile, newRole, users):
        if newRole != 'reviewer' and newRole in userProfile.get('roles', []):
            return userProfile

        profile = Profile()

        user = UserModel().load(userProfile['userId'], force=True)
        appletGroups = self.getAppletGroups(applet)

        for role in USER_ROLES.keys():
            if role not in userProfile['roles']:
                if newRole == 'manager' or newRole == role:
                    userProfile['roles'].append(role)

                    group = GroupModel().load(
                        ObjectId(list(appletGroups.get(newRole).keys())[0]),
                        force=True
                    )

                    if group['_id'] not in user.get('groups', []):
                        GroupModel().inviteUser(group, user, level=AccessType.READ)
                        GroupModel().joinGroup(group, user)

        profile.save(userProfile, validate=False)

        if newRole == 'reviewer':
            profile.updateReviewerList(userProfile, users, isMRNList=True)
        elif newRole == 'manager':
            profile.updateReviewerList(userProfile)

        AccountProfile().appendApplet(
            AccountProfile().findOne({
                'accountId': applet['accountId'],
                'userId': userProfile['userId']
            }),
            applet['_id'],
            userProfile['roles']
        )

        return userProfile

    def revokeRole(self, applet, userProfile, role):
        if role not in userProfile.get('roles', []):
            return userProfile

        if role == 'reviewer':
            Profile().updateReviewerList(userProfile, [])

        group = self.getAppletGroups(applet).get(role)
        GroupModel().removeUser(GroupModel().load(
            ObjectId(list(group.keys())[0]),
            force=True
        ), UserModel().load(userProfile['userId'], force=True))

        userProfile['roles'].remove(role)

        AccountProfile().removeApplet(
            AccountProfile().findOne({
                'accountId': applet['accountId'],
                'userId': userProfile['userId']
            }),
            applet['_id'],
            [role]
        )

        Profile().save(userProfile, validate=False)

        return userProfile

    # users won't use this function, so all emails are plain text (this endpoint is used for owners/managers to get access to new applet automatically)
    def grantAccessToApplet(self, user, applet, role, inviter):
        from girderformindlogger.models.invitation import Invitation

        appletProfile = Profile().findOne({'appletId': applet['_id'], 'userId': user['_id']})
        if not appletProfile or role not in appletProfile.get('roles', []):
            accountId = applet.get('accountId', None)
            if not accountId:
                return

            newInvitation = Invitation().createInvitationForSpecifiedUser(
                applet=applet,
                coordinator=inviter,
                role=role,
                user=user,
                firstName=user['firstName'],
                lastName=user['lastName'],
                lang='en',
                MRN='',
                userEmail=user['email']
            )

            appletProfile = Invitation().acceptInvitation(Invitation().load(newInvitation['_id'], force=True), user, user['email'])
            Invitation().remove(newInvitation)

        if role == 'manager':
            Profile().updateReviewerList(Profile().load(appletProfile['_id'], force=True))

    def duplicateApplet(
        self,
        applet,
        name,
        editor
    ):
        from girderformindlogger.utility import jsonld_expander
        from girderformindlogger.models.protocol import Protocol

        appletsCollection = CollectionModel().findOne({"name": "Applets"})
        appletName = self.validateAppletName(name, appletsCollection, applet['accountId'])
        prefLabel = appletName

        suffix = re.findall('^(.*?)\s*\((\d+)\)$', appletName)
        if len(suffix):
            if suffix[0][0] == applet['meta']['applet']['displayName']:
                prefLabel = suffix[0][0]

        protocolId = applet.get('meta', {}).get('protocol', {}).get('_id', None)
        if not protocolId:
            raise ValidationException('this applet does not have protocol id')

        protocol = Protocol().duplicateProtocol(ObjectId(protocolId.split("/")[1]), editor, prefLabel)

        # create new applet
        metadata = {
            **applet.get('meta', {}),
            'protocol': {
                '_id': protocol['protocol']['_id'],
                'activities': [
                    ObjectId(protocol['activities'][activity]['_id'].split('/')[-1]) for activity in protocol['activities']
                ],
                'name': prefLabel
            }
        }
        metadata['applet']['displayName'] = appletName

        newApplet = self.setMetadata(
            folder=self.createFolder(
                parent=appletsCollection,
                name=appletName,
                parentType='collection',
                public=True,
                creator=editor,
                allowRename=True,
                accountId=applet['accountId']
            ),
            metadata=metadata
        )

        appletGroupName = "Default {} ({})".format(
            name,
            str(newApplet.get('_id', ''))
        )

        print("Name: {}".format(appletGroupName))
        # Create user groups
        role2AccessLevel = { 'user': AccessType.READ, 'coordinator': AccessType.ADMIN, 'manager': AccessType.ADMIN, 'editor': AccessType.WRITE, 'reviewer': AccessType.READ }
        accessList = newApplet.get('access', {})
        accessList['groups'] = []

        for role in USER_ROLES.keys():
            try:
                group = GroupModel().createGroup(
                    name="{} {}s".format(appletGroupName, role.title()),
                    creator=editor,
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
                    creator=editor,
                    public=False if role=='user' else True
                )
            self.setGroupRole(
                doc=newApplet,
                group=group,
                role=role,
                currentUser=editor,
                force=False
            )

        newApplet['duplicateOf'] = applet['duplicateOf'] if applet.get('duplicateOf', None) else applet['_id']
        self.setAccessList(newApplet, accessList)
        self.save(newApplet)

        # copy editor and manager list from original applet
        profiles = Profile().find({
            'appletId': applet['_id'],
            'roles': 'editor',
            'userId': {
                '$exists': True
            },
            'profile': True
        })

        inviter = UserModel().load(editor['_id'], force=True)
        for profile in profiles:
            role = 'manager' if 'manager' in profile.get('roles', []) else 'editor'
            self.grantAccessToApplet(UserModel().load(profile['userId'], force=True), newApplet, role, inviter)


        Profile().updateOwnerProfile(newApplet)

        Protocol().createHistoryFolders(protocol['protocol']['_id'].split('/')[-1], editor)

        formatted = jsonld_expander.formatLdObject(
            newApplet,
            'applet',
            editor,
            refreshCache=False
        )

        emailMessage = "Hi, {}. <br>" \
                "Your applet ({}) was successfully created. <br>".format(
                    editor['firstName'],
                    appletName
                )
        subject = 'applet duplicate success!'

        if 'email' in editor and not editor.get('email_encrypted', True):
            from girderformindlogger.utility.mail_utils import sendMail
            sendMail(
                subject=subject,
                text=emailMessage,
                to=[editor['email']]
            )

        return formatted

    def deactivateApplet(self, applet):
        applet['meta']['applet']['deleted'] = True
        applet = self.setMetadata(applet, applet.get('meta'))

        successed = True
        # profiles = []

        if applet.get('meta', {}).get('applet', {}).get('deleted')==True:

            accountProfiles = list(AccountProfile().find({'accountId': applet['accountId'], 'applets.user': applet['_id'] }))
            # profiles = list(Profile().find({
            #     'appletId': applet['_id'],
            #     'deactivated': {'$ne': True}
            # }))

            Profile().deactivateProfile(applet['_id'], None)

            for accountProfile in accountProfiles:
                AccountProfile().removeApplet(accountProfile, applet['_id'])
        else:
            successed = False

        # thread = threading.Thread(
        #    target=send_applet_update_notification,
        #    args=(applet,True, profiles)
        # )
        # thread.start()

        return successed

    def receiveOwnerShip(self, applet, thisUser, email):
        from girderformindlogger.utility import mail_utils, jsonld_expander
        from girderformindlogger.models.group import Group
        from girderformindlogger.models.response_folder import ResponseItem
        from girderformindlogger.models.invitation import Invitation
        from girderformindlogger.utility import jsonld_expander

        if not mail_utils.validateEmailAddress(email):
            raise ValidationException(
                'Invalid email address.',
                'email'
            )

        if thisUser.get('email_encrypted', False):
            if UserModel().hash(email) != thisUser['email']:
                raise ValidationException(
                    'Invalid email address.',
                    'email'
                )
            thisUser['email'] = email
            thisUser['email_encrypted'] = False

            UserModel().save(thisUser)

        Invitation().removeWithQuery({
            'appletId': applet['_id']
        })

        accountId = thisUser['accountId']

        appletUsers = list(Profile().find({'appletId': applet['_id']}))

        appletGroups=self.getAppletGroups(applet)
        groups = []
        for role in list(USER_ROLES.keys()):
            group = appletGroups.get(role)
            if bool(group):
                groups.append(Group().load(
                    ObjectId(list(group.keys())[0]),
                    force=True
                ))

        for user in appletUsers:
            appletUser = UserModel().load(user['userId'], force=True)
            for group in groups:
                Group().removeUser(group, appletUser)

            Profile().remove(user)

        ResponseItem().removeWithQuery(
            query={
                "baseParentType": 'user',
                "meta.applet.@id": applet['_id']
            }
        )

        accountProfiles = list(AccountProfile().find({'accountId': applet['accountId'], 'applets.user': applet['_id'] }))

        for accountProfile in accountProfiles:
            AccountProfile().removeApplet(accountProfile, applet['_id'])

        applet['accountId'] = accountId

        if 'encryption' in applet['meta']:
            applet['meta'].pop('encryption')

        self.save(applet)
        self.grantAccessToApplet(thisUser, applet, 'manager', thisUser)

        jsonld_expander.clearCache(applet, 'applet')

        return Profile().displayProfileFields(Profile().updateOwnerProfile(applet), thisUser, forceManager=True)

    def validateAppletName(self, appletName, appletsCollection, accountId = None, currentApplet = None):
        appletName = appletName.strip()

        suffix = re.findall('^(.*?)\s*\((\d+)\)$', appletName)

        if len(suffix):
            name = appletName
            appletName = suffix[0][0]
            n = int(suffix[0][1])
        else:
            n = 0

        if not n:
            name = appletName

        query = {
            'parentId': appletsCollection['_id'],
            'meta.applet.displayName': name,
            'parentCollection': 'collection'
        }

        if accountId:
            query['accountId'] = ObjectId(accountId)
        if currentApplet and '_id' in currentApplet:
            query['_id'] = {
                '$ne': currentApplet['_id']
            }

        existing = self.findOne(query)
        while existing:
            n = n + 1
            name = '%s (%d)' % (appletName, n)
            query['meta.applet.displayName'] = name

            existing = self.findOne(query)

        return name

    def createAppletFromUrl(
        self,
        name,
        protocolUrl,
        user=None,
        roles=None,
        constraints=None,
        email='',
        sendEmail=True,
        appletRole='editor',
        accountId=None,
        encryption={}
    ):
        from girderformindlogger.models.protocol import Protocol
        from girderformindlogger.utility import mail_utils

        subject = 'applet upload success!'
        try:
            # we have cases to show manager's email to users
            if mail_utils.validateEmailAddress(email) and \
                'email' in user and (user['email'] == email and not user['email_encrypted'] or user['email'] == UserModel().hash(email) and user['email_encrypted']):

                user['email'] = email
                user['email_encrypted'] = False
                UserModel().save(user)
            else:
                raise ValidationException('email is not valid')
            # get a protocol from a URL
            protocol = Protocol().getFromUrl(
                protocolUrl,
                'protocol',
                user,
                thread=False,
                refreshCache=True,
                meta={ 'appletId': None },
                isReloading=False
            )

            protocol = protocol[0].get('protocol', protocol[0])

            displayName = ''
            for candidate in ['prefLabel', 'altLabel']:
                for key in protocol:
                    if not len(displayName) and key.endswith(candidate) and isinstance(protocol[key], list):
                        displayName = protocol[key][0]['@value']

            name = name if name is not None and len(name) else displayName

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
                    ).get('url', protocolUrl),
                    'name': displayName.strip()
                },
                user=user,
                roles=roles,
                constraints=constraints,
                appletRole=appletRole,
                accountId=accountId,
                encryption=encryption
            )

            html = mail_utils.renderTemplate(f'appletUploadSuccess.{user.get("lang", "en")}.mako', {
                'userName': user['firstName'],
                'appletName': name
            })
            subject = t('applet_upload_sucess', user.get('lang', 'en'))

        except Exception as e:
            html = mail_utils.renderTemplate(f'appletUploadFailed.{user.get("lang", "en")}.mako', {
                'userName': user['firstName'],
                'appletName': name
            })
            subject = t('applet_upload_failed', user.get('lang', 'en'))

        if 'email' in user and not user.get('email_encrypted', True):
            mail_utils.sendMail(
                subject,
                html,
                [user['email']]
            )

    def createAppletFromProtocolData(
        self,
        name,
        protocol,
        user=None,
        roles=None,
        constraints=None,
        email='',
        sendEmail=True,
        appletRole='editor',
        accountId=None,
        encryption={}
    ):
        from girderformindlogger.models.protocol import Protocol
        from girderformindlogger.utility import mail_utils

        subject = 'applet upload success!'
        try:
            # we have cases to show manager's email to users
            if mail_utils.validateEmailAddress(email) and \
                'email' in user and (user['email'] == email and not user['email_encrypted'] or user['email'] == UserModel().hash(email) and user['email_encrypted']):
                user['email'] = email
                user['email_encrypted'] = False
                UserModel().save(user)

            # get a protocol from single json file
            protocol = Protocol().createProtocol(
                protocol,
                user
            )

            protocol = protocol.get('protocol', protocol)

            displayName = ''
            for candidate in ['prefLabel', 'altLabel']:
                for key in protocol:
                    if not len(displayName) and key.endswith(candidate) and isinstance(protocol[key], list):
                        displayName = protocol[key][0]['@value']

            name = name if name is not None and len(name) else displayName

            applet = self.createApplet(
                name=name,
                protocol={
                    '_id': 'protocol/{}'.format(
                        str(protocol.get('_id')).split('/')[-1]
                    ),
                    'name': name.strip()
                },
                user=user,
                roles=roles,
                constraints=constraints,
                appletRole=appletRole,
                accountId=accountId,
                encryption=encryption
            )

            html = mail_utils.renderTemplate(f'appletUploadSuccess.{user.get("lang", "en")}.mako', {
                'userName': user['firstName'],
                'appletName': name
            })

            subject = t('applet_upload_sucess', user.get('lang', 'en'))

        except Exception as e:
            html = mail_utils.renderTemplate(f'appletUploadFailed.{user.get("lang", "en")}.mako', {
                'userName': user['firstName'],
                'appletName': name
            })
            subject = t('applet_upload_failed', user.get('lang', 'en'))

        if 'email' in user and not user.get('email_encrypted', True):
            from girderformindlogger.utility.mail_utils import sendMail
            sendMail(
                subject,
                html,
                to=[user['email']]
            )

    def updateAppletFromProtocolData(
        self,
        name,
        applet,
        protocol,
        user,
        accountId
    ):
        from girderformindlogger.models.protocol import Protocol
        from girderformindlogger.utility import jsonld_expander

        # get a protocol from single json file
        now = datetime.datetime.utcnow()
        displayName = protocol['protocol']['data'].get('skos:prefLabel', protocol['protocol']['data'].get('skos:altLabel', '')).strip()

        suffix = re.findall('^(.*?)\s*\((\d+)\)$', displayName)
        if len(suffix) and applet.get('meta', {}).get('protocol', {}).get('name', '') == suffix[0][0]:
            protocol['protocol']['data']['skos:prefLabel'] = suffix[0][0]
        else:
            applet['meta']['protocol']['name'] = displayName
            displayName = '%s (0)' % (displayName)

        protocol = Protocol().createProtocol(
            protocol,
            user,
            True
        )

        protocol = protocol.get('protocol', protocol)

        applet['meta']['applet']['displayName'] = self.validateAppletName(
            displayName,
            CollectionModel().findOne({"name": "Applets"}),
            accountId,
            currentApplet = applet
        )
        applet['meta']['applet']['version'] = protocol['schema:schemaVersion'][0].get('@value', '0.0.0') if 'schema:schemaVersion' in protocol else '0.0.0'

        applet['updated'] = now
        applet = self.setMetadata(folder=applet, metadata=applet['meta'])

        # update appletProfile according to updated applet
        jsonld_expander.clearCache(applet, 'applet')

        formatted = jsonld_expander.formatLdObject(
            applet,
            'applet',
            user
        )

        activities = []
        if 'activities' in formatted:
            for activity in formatted['activities']:
                activityId = ObjectId(formatted['activities'][activity]['_id'].split('/')[-1])
                activities.append(activityId)

                EventsModel().update({
                    'data.activity_id': activityId
                }, {
                    '$set': {
                        'data.title': self.preferredName(formatted['activities'][activity]),
                        # 'updated': datetime.datetime.utcnow()
                    },
                })

            self.update({'_id': ObjectId(applet['_id'])}, {'$set': {'meta.protocol.activities': activities}})

        removedActivities = protocol.get('removed', {}).get('activities', [])

        for activityId in removedActivities:
            EventsModel().deleteEventsByActivityId(applet['_id'], activityId)

        appletProfiles = Profile().get_profiles_by_applet_id(applet['_id'])

        # update applet profiles
        for profile in appletProfiles:
            originalActivities = profile.get('completed_activities', [])
            profile['completed_activities'] = []

            activityUpdated = False
            for activityId in activities:
                activityData = None

                for originalActivity in originalActivities:
                    if originalActivity['activity_id'] == activityId:
                        activityData = originalActivity

                if not activityData:
                    activityUpdated = True

                profile['completed_activities'].append(activityData if activityData else {'activity_id': activityId, 'completed_time': None})

            if activityUpdated:
                Profile().save(profile, validate=False)

        # thread = threading.Thread(
        #     target=send_applet_update_notification,
        #     args=(applet,)
        # )

        # thread.start()

        return formatted

    def prepareAppletForEdit(
        self,
        applet,
        protocol,
        user,
        accountId
    ):
        from girderformindlogger.models.protocol import Protocol
        from girderformindlogger.models.screen import Screen
        from girderformindlogger.models.activity import Activity
        from girderformindlogger.models.response_folder import ResponseItem
        from girderformindlogger.utility import jsonld_expander

        metadata = applet.get('meta', {})
        protocolId = metadata.get('protocol', {}).get('_id', '/').split('/')[-1]

        if metadata.get('protocol', {}).get('url', None):
            if not protocolId:
                raise ValidationException('this applet does not have protocol id')

            ActivityModel = Activity()
            ItemModel = Screen()

            protocolFolder = FolderModel().load(protocolId, force=True)

            if not protocolFolder.get('meta', {}).get('appletId', None): # old schema ( we'll not need this in the future )
                duplicated = Protocol().duplicateProtocol(ObjectId(protocolId), user)
                protocolId = duplicated['protocol']['_id'].split('/')[-1]

                (historyFolder, referencesFolder) = Protocol().createHistoryFolders(protocolId, user)

                # replace with duplicated content
                activities = list(ActivityModel.find({ 'meta.protocolId': ObjectId(protocolId) }))
                items = list(ItemModel.find({ 'meta.protocolId': ObjectId(protocolId) }))

                activityIDRef = {}
                itemIDRef = {}
                for activity in activities:
                    activityIDRef[str(activity['duplicateOf'])] = activity['_id']

                    ResponseItem().update({
                        'meta.activity.@id': activity['duplicateOf'],
                        'meta.applet.@id': applet['_id']
                    }, {
                        '$set': {
                            'meta.activity.@id': activity['_id'],
                        }
                    })

                    EventsModel().update({
                        'data.activity_id': activity['duplicateOf']
                    }, {
                        '$set': {
                            'data.activity_id': activity['_id'],
                            'updated': datetime.datetime.utcnow()
                        }
                    })

                    ActivityModel.update({
                        'duplicateOf': activity['duplicateOf']
                    }, {
                        '$set': {
                            'duplicateOf': activity['_id']
                        }
                    })

                    ActivityModel.update({
                        'meta.historyId': historyFolder['_id'],
                        'meta.originalId': activity['duplicateOf']
                    }, {
                        '$set': {
                            'meta.originalId': activity['_id']
                        }
                    })

                    ItemModel.update({
                        'meta.historyId': historyFolder['_id'],
                        'meta.activityId': activity['duplicateOf']
                    }, {
                        '$set': {
                            'meta.activityId': activity['_id']
                        }
                    })

                    activity.pop('duplicateOf')

                    ActivityModel.update({
                        '_id': activity['_id']
                    }, {
                        '$unset': {
                            'duplicateOf': ''
                        }
                    })

                for item in items:
                    itemIDRef[str(item['duplicateOf'])] = item['_id']
                    ItemModel.update({
                        'duplicateOf': item['duplicateOf']
                    }, {
                        '$set': {
                            'duplicateOf': item['_id']
                        }
                    })

                    ItemModel.update({
                        'meta.historyId': historyFolder['_id'],
                        'meta.originalId': item['duplicateOf']
                    }, {
                        '$set': {
                            'meta.originalId': item['_id']
                        }
                    })

                    item.pop('duplicateOf')

                    ItemModel.update({
                        '_id': item['_id']
                    }, {
                        '$unset': {
                            'duplicateOf': ''
                        }
                    })

                Protocol().initHistoryData(historyFolder, referencesFolder, metadata['protocol']['_id'].split('/')[-1], user, activityIDRef, itemIDRef)

                # update profiles
                appletProfiles = Profile().get_profiles_by_applet_id(applet['_id'])

                for profile in appletProfiles:
                    for activity in profile.get('completed_activities', []):
                        activity['activity_id'] = activityIDRef[str(activity['activity_id'])]

                    Profile().save(profile, validate=False)

                metadata['protocol'] = {
                    '_id': duplicated['protocol']['_id'],
                    'activities': [activity['activity_id'] for activity in profile.get('completed_activities', [])]
                }
                self.setMetadata(applet, metadata)

                protocolFolder = FolderModel().load(protocolId, force=True)
            else:
                (historyFolder, referencesFolder) = Protocol().createHistoryFolders(protocolId, user)
                Protocol().initHistoryData(historyFolder, referencesFolder, protocolId, user)

            activities = list(ActivityModel.find({ 'meta.protocolId': ObjectId(protocolId) }))
            items = list(ItemModel.find({ 'meta.protocolId': ObjectId(protocolId) }))
            activityIdToData = {
                str(activity['_id']): activity for activity in activities
            }

            for item in items:
                activity = activityIdToData[str(item['meta']['activityId'])]
                jsonld_expander.convertObjectToSingleFileFormat(item, 'screen', user, '{}/{}'.format(str(activity['_id']), str(item['_id'])), True)

            for activity in activities:
                ResponseItem().update({
                    'meta.activity.@id': activity['_id'],
                    'meta.applet.@id': applet['_id']
                }, {
                    '$unset': {
                        'meta.activity.url': ''
                    }
                })

                EventsModel().update({
                    'data.activity_id': activity['_id']
                }, {
                    '$set': {
                        'data.URI': self.preferredName(activity),
                        'updated': datetime.datetime.utcnow()
                    }
                })

                jsonld_expander.convertObjectToSingleFileFormat(activity, 'activity', user, str(activity['_id']))

            for key in ['schema:version', 'schema:schemaVersion']:
                schemaVersion = protocolFolder['meta']['protocol'][key]
                schemaVersion[0]['@value'] = protocol['protocol'].get('data', {}).get(key, '0.0.0')

            jsonld_expander.convertObjectToSingleFileFormat(protocolFolder, 'protocol', user)

            if 'url' in metadata['protocol']:
                metadata['protocol'].pop('url')
                applet = self.setMetadata(applet, metadata)

            jsonld_expander.formatLdObject(protocolFolder, 'protocol', user, refreshCache=True)
        else:
            Protocol().createHistoryFolders(protocolId, user)

        jsonld_expander.cacheProtocolContent(Protocol().load(protocolId, force=True), protocol, user)

        jsonld_expander.clearCache(applet, 'applet')
        return jsonld_expander.formatLdObject(
            applet,
            'applet',
            user,
            refreshCache=False
        )

    def formatThenUpdate(self, applet, user):
        from girderformindlogger.utility import jsonld_expander
        jsonld_expander.formatLdObject(
            applet,
            'applet',
            user,
            refreshCache=True
        )

    def getResponseData(self, appletId, reviewer, users):
        """
        Function to collect response data available to given reviewer.

        :param appletId: ID of applet for which to get response data
        :type appletId: ObjectId or str
        :param reviewer: Reviewer making request
        :type reviewer: dict
        :reutrns: TBD
        """
        from girderformindlogger.models.ID_code import IDCode
        from girderformindlogger.models.response_folder import ResponseItem
        from girderformindlogger.models.user import User
        from girderformindlogger.models.protocol import Protocol
        from pymongo import DESCENDING

        if not any([
            self.isReviewer(appletId, reviewer),
            self.isManager(appletId, reviewer)]):
            raise AccessException("You are not a owner or manager for this applet.")

        applet = self.load(appletId, level=AccessType.READ, user=reviewer)

        retentionSettings = applet['meta'].get('retentionSettings', None)

        if retentionSettings != None:
            retention = retentionSettings.get('retention', 'year')
            period = retentionSettings.get('period', 5)

            timedelta_in_days = int(period) * int(RETENTION_SET[retention])

        query = {
            "baseParentType": "user",
            "meta.applet.@id": ObjectId(appletId)
        }

        reviewerProfile = Profile().findOne(query={
            'appletId': ObjectId(appletId),
            'userId': reviewer['_id']
        })
        if len(users):
            profiles = list(Profile().find(query={
                "_id": {
                    "$in": [ObjectId(user) for user in users]
                },
                "profile": True,
                "reviewers": reviewerProfile["_id"]
            }))
        else:
            profiles = list(Profile().find(query={
                "reviewers": reviewerProfile["_id"],
                "profile": True,
            }))

        if reviewerProfile['_id'] not in reviewerProfile['reviewers'] and (str(reviewerProfile['_id']) in users or not users):
            profiles.append(reviewerProfile)

        query["creatorId"] = {
            "$in": [profile['userId'] for profile in profiles]
        }

        if retentionSettings != None:
            query['created'] = {
                '$gte': datetime.datetime.now() - datetime.timedelta(days=timedelta_in_days)
            }
        else:
            query['created'] = {
                '$gte': applet['created']
            }

        responses = list(ResponseItem().find(
            query=query,
            user=reviewer,
            sort=[("created", DESCENDING)]
        ))

        user=getCurrentUser()

        schedule = EventsModel().getScheduleForUser(applet['_id'], user['_id'])

        data = {
            'dataSources': {},
            'subScaleSources': {},
            'keys': [],
            'responses': []
        }

        userKeys = {}
        profileIDToData = {}
        for profile in profiles:
            profileIDToData[str(profile['_id'])] = profile

        IRIs = {}
        # IRIs refers to available versions for specified IRI
        # IRI is github url for items created by url, and pair of activity id and item id for items created by applet-builder
        # ex: IRIS = {
        #                'https://raw.githubusercontent.com/ChildMindInstitute/TokenLogger_applet/master/activities/TokenActivity/items/token_screen': ['0.0.1'],
        #                 '5f87e250c3942f7d5df7b7ca/5f87e25ac3942f7d5df7b7ce': ['0.0.2', '0.0.3']
        #            }

        insertedIRI = {}

        for response in responses:
            meta = response.get('meta', {})

            profile = profileIDToData.get(str(meta.get('subject', {}).get('@id', None)), None)

            if not profile:
                continue

            MRN = profile['MRN'] if profile.get('MRN', '') else f"None ({profile.get('userDefined', {}).get('email', '')})"

            times = {
                'responseStarted': '',
                'responseCompleted': '',
                'scheduledTime': ''
            }

            for key in times:
                ts = meta.get(key, 0)
                if not ts:
                    continue

                secs, millis = divmod(ts, 1000)
                date_time = dt.utcfromtimestamp(secs).replace(microsecond=millis * 1000)
                times[key] = date_time.strftime("%Y-%m-%d %H:%M:%S")

            data['responses'].append({
                '_id': response['_id'],
                'activity': meta.get('activity', {}),
                'userId': str(profile['_id']),
                'MRN': MRN,
                'data': meta.get('responses', {}),
                'subScales': meta.get('subScales', {}),
                'created': response.get('created', None),
                'responseStarted':times['responseStarted'],
                'responseCompleted':times['responseCompleted'],
                'responseScheduled':times['scheduledTime'],
                'timeout': meta.get('timeout', 0),
                'version': meta['applet'].get('version', '0.0.0')
            })

            for IRI in meta.get('responses', {}):
                if IRI not in IRIs:
                    IRIs[IRI] = []

                identifier = '{}/{}'.format(IRI, meta['applet'].get('version', '0.0.0'))

                if identifier not in insertedIRI:
                    IRIs[IRI].append(meta['applet'].get('version', '0.0.0'))
                    insertedIRI[identifier] = True

            if 'userPublicKey' in meta:
                keyDump = json_util.dumps(meta['userPublicKey'])
                if keyDump not in userKeys:
                    userKeys[keyDump] = len(data['keys'])
                    data['keys'].append(meta['userPublicKey'])

                data['dataSources'][str(response['_id'])] = {
                    'key': userKeys[keyDump],
                    'data': meta['dataSource']
                }

                if 'subScaleSource' in meta:
                    data['subScaleSources'][str(response['_id'])] = {
                        'key': userKeys[keyDump],
                        'data': meta['subScaleSource']
                    }

        data.update(
            Protocol().getHistoryDataFromItemIRIs(
                applet.get('meta', {}).get('protocol', {}).get('_id', '').split('/')[-1],
                IRIs
            )
        )

        return data

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

        try:
            user = Profile()._canonicalUser(appletId, user)
            return(any([
                self._hasRole(appletId, user, 'coordinator'),
                self.isManager(appletId, user)
            ]))
        except:
            return(False)

    def isManager(self, appletId, user):
        return self._hasRole(appletId, user, 'manager')

    def isReviewer(self, appletId, user):
        return self._hasRole(appletId, user, 'reviewer')

    def _hasRole(self, appletId, user, role):

        user = Profile()._canonicalUser(appletId, user)
        profile = Profile().findOne({'appletId': ObjectId(appletId), 'userId': user['_id']})

        return (profile and not profile.get('deactivated', False) and role in profile.get('roles', []))

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

        if protocolUrl is None:
            raise AccessException('this applet is not uploaded from url')

        protocol = Protocol().findOne({
            '_id': ObjectId(applet.get('meta', {}).get('protocol', {}).get('_id' , '').split('/')[-1])
        })

        if 'appletId' not in protocol.get('meta', {}):
            protocol['meta']['appletId'] = 'None'
            Protocol().setMetadata(protocol, protocol['meta'])

        protocol = Protocol().getFromUrl(
            protocolUrl,
            'protocol',
            editor,
            thread=False,
            refreshCache=True,
            meta={'appletId': protocol['meta']['appletId']},
        )

        protocol = protocol[0].get('protocol', protocol[0])
        if protocol.get('_id'):
            self.update({'_id': ObjectId(applet['_id'])}, {'$set': {'meta.protocol._id': protocol['_id']}})
            if 'meta' in applet and 'protocol' in applet['meta']:
                applet['meta']['protocol']['_id'] = protocol['_id']

            displayName = ''
            for candidate in ['prefLabel', 'altLabel']:
                for key in protocol:
                    if not len(displayName) and key.endswith(candidate) and isinstance(protocol[key], list):
                        displayName = protocol[key][0]['@value']

            suffix = re.findall('^(.*?)\s*\((\d+)\)$', applet.get('meta', {}).get('applet', {}).get('displayName', {}))
            if len(suffix):
                displayName = '%s (%s)' % (displayName, suffix[0][1])

            applet['meta']['applet']['displayName'] = self.validateAppletName(
                displayName,
                CollectionModel().findOne({"name": "Applets"}),
                accountId = applet['accountId'],
                currentApplet = applet
            )

        self.save(applet)

        from girderformindlogger.utility import jsonld_expander

        jsonld_expander.clearCache(applet, 'applet')

        formatted = jsonld_expander.formatLdObject(
            applet,
            'applet',
            editor,
            refreshCache=False,
            responseDates=False
        )

        if 'activities' in formatted:
            activities = self.updateActivities(applet, formatted)
            Profile().update_profile_activities_by_applet_id(applet, activities)

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

        query = {
            'userId': user['_id'],
            'profile': True,
            'roles': role
        }

        if active:
            query['deactivated'] = {
                '$ne': True
            }

        profiles = list(Profile().find(query))

        applets = []
        for profile in profiles:
            applets.append(self.findOne({
                '_id': profile['appletId']
            }, fields = ['_id'] if idOnly else None))

        return(applets)

    def listUsers(self, applet, role, user=None, force=False):
        if not force:
            if not any([
                self.isCoordinator(applet['_id'], user),
                self._hasRole(applet['_id'], user, 'reviewer')
            ]):
                return([])
        userlist = {
            p['_id']: Profile().display(p, role) for p in list(Profile().find({
                'appletId': applet['_id'],
                'roles': role,
                'deactivated': {'$ne': True}
            }))
        }
        return(userlist)

    def appletFormatted(
        self,
        applet,
        reviewer,
        role='user',
        retrieveSchedule=True,
        retrieveAllEvents=True,
        eventFilter=None,
        retrieveResponses=False,
        groupByDateActivity=True,
        startDate=None,
        retrieveLastResponseTime=False,
        localInfo={}
    ):
        from girderformindlogger.utility import jsonld_expander
        from girderformindlogger.utility.response import responseDateList, last7Days
        from girderformindlogger.models.protocol import Protocol

        formatted = {}

        if not localInfo.get('contentUpdateTime', None) or applet['updated'].isoformat() != localInfo['contentUpdateTime']:
            localVersion = localInfo.get('appletVersion', None)
            updates = None

            if localVersion:
                (isInitialVersion, updates) = Protocol().getProtocolChanges(
                    applet.get('meta', {}).get('protocol', {}).get('_id', '').split('/')[-1],
                    localVersion,
                    localInfo['contentUpdateTime']
                )

            formatted = {
                **jsonld_expander.formatLdObject(
                    applet,
                    'applet',
                    reviewer,
                    refreshCache=False,
                    responseDates=False
                ),
                "users": self.getAppletUsers(applet, reviewer),
                "groups": self.getAppletGroups(
                    applet,
                    arrayOfObjects=True
                )
            } if role in ["coordinator", "manager"] else {
                **jsonld_expander.formatLdObject(
                    applet,
                    'applet',
                    reviewer,
                    refreshCache=False,
                    responseDates=(role == "user")
                ),
                "groups": [
                    group for group in self.getAppletGroups(applet).get(
                        role
                    ) if ObjectId(
                        group
                    ) in [
                            *reviewer.get('groups', []),
                            *reviewer.get('formerGroups', []),
                            *[invite['groupId'] for invite in [
                                *reviewer.get('groupInvites', []),
                                *reviewer.get('declinedInvites', [])
                            ]]
                        ]
                ]
            }

            formatted['removedActivities'] = []
            formatted['removedItems'] = []

            if localVersion and updates:
                for itemId in list(formatted['items'].keys()):
                    if itemId not in updates['screen'] and not isInitialVersion:
                        formatted['items'].pop(itemId)

                for itemId in updates['screen']:
                    if itemId not in formatted['items'] and (updates['screen'][itemId] == 'updated' or isInitialVersion):
                        formatted['removedItems'].append(itemId)

                for activityId in list(formatted['activities'].keys()):
                    if activityId not in updates['activity'] and not isInitialVersion:
                        formatted['activities'].pop(activityId)

                for activityId in updates['activity']:
                    if activityId not in formatted['activities'] and (updates['activity'][activityId] == 'updated' or isInitialVersion):
                        formatted['removedActivities'].append(activityId)

        if retrieveSchedule:
            schedule = self.getSchedule(
                applet,
                reviewer,
                retrieveAllEvents,
                eventFilter if not retrieveAllEvents else None,
                localInfo.get('localEvents', [])
            )

            if schedule:
                formatted["schedule"] = schedule

        if retrieveResponses:
            formatted["responses"] = last7Days(
                applet['_id'],
                applet,
                reviewer.get('_id'),
                reviewer,
                None,
                localInfo.get('startDate', None),
                True,
                groupByDateActivity,
                localInfo.get('localItems', []),
                localInfo.get('localActivities', [])
            )

        if retrieveLastResponseTime:
            profile = Profile().findOne({'appletId': applet['_id'], 'userId': reviewer['_id']})
            activities = profile['completed_activities']

            formatted['lastResponses'] = {}

            for activity in activities:
                completed_time = activity['completed_time']
                timezone = str(profile.get('timezone', 0))
                if completed_time:
                    if isinstance(timezone, str) and timezone in pytz.all_timezones:
                        completed_time = activity['completed_time'].astimezone(pytz.timezone(timezone)).isoformat()
                    else:
                        completed_time = activity['completed_time'].isoformat()

                formatted['lastResponses'][str(activity['activity_id'])] = completed_time

        formatted["updated"] = applet['updated'].isoformat()
        formatted["id"] = applet['_id']

        return formatted

    def getAppletUsers(self, applet, user=None, force=False, retrieveRoles=False, retrieveRequests=False):
        """
        Function to return a list of Applet Users

        :param applet: Applet to get users for.
        :type applet: dict
        :param user: User making request
        :type user: dict
        :returns: list of dicts
        """
        from girderformindlogger.models.invitation import Invitation

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
                'active': [],
                'pending': []
            }

            for p in list(profileModel.find(query={'appletId': applet['_id'], 'userId': {'$exists': True}, 'profile': True, 'deactivated': {'$ne': True}})):
                    profile = profileModel.displayProfileFields(
                        p,
                        user,
                        forceManager=True
                    )

                    if retrieveRoles:
                        profile['roles'] = p['roles']
                    if 'refreshRequest' in p and retrieveRequests:
                        profile['refreshRequest'] = p['refreshRequest']

                    userDict['active'].append(profile)

            for p in list(Invitation().find(query={'appletId': applet['_id']})):
                fields = ['_id', 'firstName', 'lastName', 'role', 'MRN', 'created', 'lang']
                if p['role'] != 'owner':
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

    def getAppletInvitations(self, applet):
        from girderformindlogger.models.invitation import Invitation

        invitations = []
        for p in list(Invitation().find(query={'appletId': applet['_id']})):
            fields = ['_id', 'firstName', 'lastName', 'role', 'MRN', 'created', 'lang']
            if p['role'] != 'owner':
                invitations.append({
                    key: p[key] for key in fields if p.get(key, None)
                })

        return invitations

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
                    doc['baseParentType'] in {'collection', 'user', 'folder'}
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

    def updateActivities(self, applet, obj):
        activities = [ObjectId(obj['activities'][activity]['_id'].split('/')[-1])
                      for activity in obj.get('activities', [])]

        self.update({'_id': ObjectId(applet['_id'])},
                    {'$set': {'meta.protocol.activities': activities}})

        return activities
