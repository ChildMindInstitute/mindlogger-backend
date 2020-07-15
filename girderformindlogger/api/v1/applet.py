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

import itertools
import os
import re
import threading
import uuid
from datetime import datetime
from ..describe import Description, autoDescribeRoute
from ..rest import Resource, rawResponse
from bson.objectid import ObjectId
from girderformindlogger.constants import AccessType, SortDir, TokenScope,     \
    DEFINED_INFORMANTS, REPROLIB_CANONICAL, SPECIAL_SUBJECTS, USER_ROLES
from girderformindlogger.api import access
from girderformindlogger.exceptions import AccessException, ValidationException
from girderformindlogger.models.activity import Activity as ActivityModel
from girderformindlogger.models.applet import Applet as AppletModel
from girderformindlogger.models.collection import Collection as CollectionModel
from girderformindlogger.models.folder import Folder as FolderModel
from girderformindlogger.models.group import Group as GroupModel
from girderformindlogger.models.item import Item as ItemModel
from girderformindlogger.models.protocol import Protocol as ProtocolModel
from girderformindlogger.models.roles import getCanonicalUser, getUserCipher
from girderformindlogger.models.user import User as UserModel
from girderformindlogger.models.events import Events as EventsModel
from girderformindlogger.utility import config, jsonld_expander, mail_utils
from girderformindlogger.models.setting import Setting
from girderformindlogger.settings import SettingKey
from girderformindlogger.models.profile import Profile as ProfileModel
from girderformindlogger.models.account_profile import AccountProfile
from bson import json_util
from pyld import jsonld

USER_ROLE_KEYS = USER_ROLES.keys()


class Applet(Resource):

    def __init__(self):
        super(Applet, self).__init__()
        self.resourceName = 'applet'
        self._model = AppletModel()
        self.route('GET', (':id',), self.getApplet)
        self.route('GET', (':id', 'data'), self.getAppletData)
        self.route('GET', (':id', 'groups'), self.getAppletGroups)
        self.route('POST', (), self.createApplet)
        self.route('PUT', (':id', 'informant'), self.updateInformant)
        self.route('PUT', (':id', 'assign'), self.assignGroup)
        self.route('PUT', (':id', 'constraints'), self.setConstraints)
        self.route('PUT', (':id', 'schedule'), self.setSchedule)
        self.route('PUT', (':id', 'refresh'), self.refresh)
        self.route('GET', (':id', 'schedule'), self.getSchedule)
        self.route('POST', (':id', 'invite'), self.invite)
        self.route('POST', (':id', 'inviteUser'), self.inviteUser)
        self.route('GET', (':id', 'roles'), self.getAppletRoles)
        self.route('GET', (':id', 'users'), self.getAppletUsers)
        self.route('DELETE', (':id',), self.deactivateApplet)
        self.route('POST', ('fromJSON', ), self.createAppletFromProtocolData)
        self.route('GET', (':id', 'protocolData'), self.getProtocolData)
        self.route('PUT', (':id', 'fromJSON'), self.updateAppletFromProtocolData)
        self.route('POST', (':id', 'duplicate', ), self.duplicateApplet)
        self.route('POST', ('resetBadge',), self.resetBadgeCount)

    @access.user(scope=TokenScope.DATA_WRITE)
    @autoDescribeRoute(
        Description('Reset badge parameter')
            .notes(
            'this endpoint is used to reset badge parameter in profile collection. <br>'
            'users who are associated with that group will be able to connect to this endpoint.'
        )
    )
    def resetBadgeCount(self):
        thisUser = self.getCurrentUser()
        ProfileModel().updateProfiles(thisUser, {"badge": 0})
        return({"message": "Badge was successfully reseted"})

    @access.user(scope=TokenScope.DATA_OWN)
    @autoDescribeRoute(
        Description('Get userlist, groups & statuses.')
        .notes(
            'this endpoint is used to get user-list for an applet. <br>'
            'coordinator/managers can make request to this endpoint.'
        )
        .modelParam(
            'id',
            model=FolderModel,
            level=AccessType.ADMIN,
            destName='applet'
        )
    )
    def getAppletUsers(self, applet):
        thisUser=self.getCurrentUser()
        if AppletModel().isCoordinator(applet['_id'], thisUser):
            appletUsers = AppletModel().getAppletUsers(applet, thisUser, force=True)
            return appletUsers
        else:
            raise AccessException(
                "Only coordinators and managers can see user lists."
            )

    @access.user(scope=TokenScope.DATA_READ)
    @autoDescribeRoute(
        Description('Get content of protocol by applet id.')
        .modelParam('id', model=AppletModel, level=AccessType.READ, destName='applet')
        .errorResponse('Invalid applet ID.')
        .errorResponse('Read access was denied for this applet.', 403)
    )
    def getProtocolData(self, applet):
        profile = self.getAccountProfile()
        if not AccountProfile().hasPermission(profile, 'manager') and not AccountProfile().hasPermission(profile, 'editor'):
            raise AccessException('You don\'t have enough permission to get content of this protocol')

        protocol = ProtocolModel().load(applet.get('meta', {}).get('protocol', {}).get('_id', '').split('/')[-1], force=True)
        protocolContent = FolderModel().load(protocol['content_id'], force=True)

        return None if not protocolContent['content'] else json_util.loads(protocolContent['content'])

    @access.user(scope=TokenScope.DATA_WRITE)
    @autoDescribeRoute(
        Description('Assign a group to a role in an applet.')
        .notes(
            'this endpoint is used to assign group role for an applet. <br>'
            'users who are associated with that group will be able to connect to this applet.'
        )
        .deprecated()
        .responseClass('Folder')
        .modelParam('id', model=FolderModel, level=AccessType.READ)
        .param(
            'group',
            'ID of the group to assign.',
            required=True,
            strip=True
        )
        .param(
            'role',
            'Role to invite this user to. One of ' + str(USER_ROLE_KEYS),
            default='user',
            required=False,
            strip=True
        )
        .jsonParam(
            'subject',
            'Requires a JSON Object in the form \n```'
            '{'
            '  "groups": {'
            '    "«relationship»": []'
            '  },'
            '  "users": {'
            '    "«relationship»": []'
            '  }'
            '}'
            '``` \n For \'user\' or \'reviewer\' assignments, specify '
            'group-level relationships, filling in \'«relationship»\' with a '
            'JSON-ld key semantically defined in in your context, and IDs in '
            'the value Arrays (either applet-specific or canonical IDs in the '
            'case of users; applet-specific IDs will be stored either way).',
            paramType='form',
            required=False,
            requireObject=True
        )
        .errorResponse('ID was invalid.')
        .errorResponse('Write access was denied for the folder or its new parent object.', 403)
    )
    def assignGroup(self, folder, group, role, subject):
        applet = folder
        if role not in USER_ROLE_KEYS:
            raise ValidationException(
                'Invalid role.',
                'role'
            )
        thisUser=self.getCurrentUser()
        group=GroupModel().load(group, level=AccessType.WRITE, user=thisUser)
        return(
            AppletModel().setGroupRole(
                applet,
                group,
                role,
                currentUser=thisUser,
                force=False,
                subject=subject
            )
        )

    @access.user(scope=TokenScope.DATA_WRITE)
    @autoDescribeRoute(
        Description('Create an applet.')
        .notes(
            'Use this endpoint to create a new applet from protocol-url. <br>'
            'You will need to wait for several minutes (5-10 mins) to see a new applet. <br>'
            'When it\'s created you will be able to get applet using GET^user/applets endpoint. <br>'
            'You will have all roles(manager, coordinator, editor, reviewer, user) for applets which you created.'
        )
        .param(
            'protocolUrl',
            'URL of Activity Set from which to create applet',
            required=False
        )
        .param(
            'email',
            'email for creator of applet',
            default='',
            required=False
        )
        .param(
            'name',
            'Name to give the applet. The Protocol\'s name will be used if '
            'this parameter is not provided.',
            required=False
        )
        .param(
            'informant',
            ' '.join([
                'Relationship from informant to individual of interest.',
                'Currently handled informant relationships are',
                str([r for r in DEFINED_INFORMANTS.keys()])
            ]),
            required=False
        )
        .errorResponse('Write access was denied for this applet.', 403)
    )
    def createApplet(self, protocolUrl=None, email='', name=None, informant=None):
        accountProfile = AccountProfile()

        thisUser = self.getCurrentUser()
        profile = self.getAccountProfile()

        appletRole = None
        for role in ['manager', 'editor']:
            if accountProfile.hasPermission(profile, role):
                appletRole = role
                break

        if appletRole is None:
            raise AccessException("You don't have enough permission to create applet on this account.")

        thread = threading.Thread(
            target=AppletModel().createAppletFromUrl,
            kwargs={
                'name': name,
                'protocolUrl': protocolUrl,
                'user': thisUser,
                'email': email,
                'constraints': {
                    'informantRelationship': informant
                } if informant is not None else None,
                'appletRole': appletRole,
                'accountId': profile['accountId']
            }
        )
        thread.start()
        return({
            "message": "The applet is being created. Please check back in "
                       "several mintutes to see it."
        })

    @access.user(scope=TokenScope.DATA_WRITE)
    @autoDescribeRoute(
        Description('Create an applet.')
        .notes(
            'This endpoint is used to create applet from existing one. <br>'
            'Only managers/editors of applets are able to access to this endpoint.'
        )
        .modelParam(
            'id',
            model=AppletModel,
            level=AccessType.READ,
            destName='applet'
        )
        .param(
            'name',
            'Name to give the applet.',
            required=True
        )
        .errorResponse('Write access was denied for this applet.', 403)
    )
    def duplicateApplet(self, applet, name):
        thisUser = self.getCurrentUser()
        accountProfile = self.getAccountProfile()

        if not accountProfile or applet['_id'] not in accountProfile.get('applets', {}).get('editor') and applet['_id'] not in accountProfile.get('applets', {}).get('manager'):
            raise AccessException(
                "Only managers and editors are able to duplicate applet."
            )
        AppletModel().duplicateApplet(applet, name, thisUser)

        return "duplicate successed"

    @access.user(scope=TokenScope.DATA_WRITE)
    @autoDescribeRoute(
        Description('Create an applet.')
        .notes(
            'This endpoint is used to create a new applet using protocol with single-file format. <br>'
            'This endpoint will be widely used in the near future.'
            '(it\'ll take seconds if we create a new applet using this endpoint.)'
        )
        .jsonParam(
            'protocol',
            'A JSON object containing protocol information for an applet',
            paramType='form',
            required=False
        )
        .param(
            'email',
            'email for creator of applet',
            default='',
            required=False
        )
        .param(
            'name',
            'Name to give the applet. The Protocol\'s name will be used if '
            'this parameter is not provided.',
            required=False
        )
        .param(
            'informant',
            ' '.join([
                'Relationship from informant to individual of interest.',
                'Currently handled informant relationships are',
                str([r for r in DEFINED_INFORMANTS.keys()])
            ]),
            required=False
        )
        .errorResponse('Write access was denied for this applet.', 403)
    )
    def createAppletFromProtocolData(self, protocol, email='', name=None, informant=None):
        accountProfile = AccountProfile()

        thisUser = self.getCurrentUser()
        profile = self.getAccountProfile()

        appletRole = None
        for role in ['manager', 'editor']:
            if accountProfile.hasPermission(profile, role):
                appletRole = role
                break

        if appletRole is None:
            raise AccessException("You don't have enough permission to create applet on this account.")

        thread = threading.Thread(
            target=AppletModel().createAppletFromProtocolData,
            kwargs={
                'name': name,
                'protocol': protocol,
                'user': thisUser,
                'email': email,
                'constraints': {
                    'informantRelationship': informant
                } if informant is not None else None,
                'appletRole': appletRole,
                'accountId': profile['accountId']
            }
        )
        thread.start()
        return({
            "message": "The applet is being created. Please check back in "
                       "several seconds to see it."
        })


    @access.user(scope=TokenScope.DATA_WRITE)
    @autoDescribeRoute(
        Description('Create an applet.')
        .notes(
            'This endpoint is used to update existing applet. <br>'
            '(updating applet will take few seconds.)'
        )
        .param(
            'name',
            'Name to give the applet. The Protocol\'s name will be used if '
            'this parameter is not provided.',
            required=False
        )
        .modelParam(
            'id',
            model=AppletModel,
            level=AccessType.READ,
            destName='applet'
        )
        .jsonParam(
            'protocol',
            'A JSON object containing protocol information for an applet',
            paramType='form',
            required=False
        )
        .errorResponse('Write access was denied for this applet.', 403)
    )
    def updateAppletFromProtocolData(self, applet, name, protocol):
        accountProfile = AccountProfile()

        thisUser = self.getCurrentUser()
        profile = self.getAccountProfile()

        appletRole = None
        for role in ['manager', 'editor']:
            if accountProfile.hasPermission(profile, role):
                appletRole = role
                break

        if appletRole is None:
            raise AccessException("You don't have enough permission to create applet on this account.")

        thread = threading.Thread(
            target=AppletModel().updateAppletFromProtocolData,
            kwargs={
                'applet': applet,
                'name': name,
                'protocol': protocol,
                'user': thisUser,
                'accountId': profile['accountId']
            }
        )
        thread.start()
        return({
            "message": "The applet is being updated. Please check back in "
                       "several seconds to see it."
        })

    @access.user(scope=TokenScope.DATA_WRITE)
    @autoDescribeRoute(
        Description('Get all data you are authorized to see for an applet.')
        .notes(
            'This endpoint returns user\'s response data for your applet by json/csv format. <br>'
            'You\'ll need to access this endpoint only if you are manager/reviewer of this applet.'
        )
        .param(
            'id',
            'ID of the applet for which to fetch data',
            required=True
        )
        .param(
            'format',
            'JSON or CSV (json by default)',
            required=False
        )
        .errorResponse('Write access was denied for this applet.', 403)
    )
    def getAppletData(self, id, format='json'):
        import pandas as pd
        from datetime import datetime
        from ..rest import setContentDisposition, setRawResponse, setResponseHeader

        format = ('json' if format is None else format).lower()
        thisUser = self.getCurrentUser()
        data = AppletModel().getResponseData(id, thisUser)

        setContentDisposition("{}-{}.{}".format(
            str(id),
            datetime.now().isoformat(),
            format
        ))
        if format=='csv':
            setRawResponse()
            setResponseHeader('Content-Type', 'text/{}'.format(format))
            csv = pd.DataFrame(data).to_csv(index=False)
            return(csv)
        setResponseHeader('Content-Type', 'application/{}'.format(format))
        return(data)


    @access.user(scope=TokenScope.DATA_WRITE)
    @autoDescribeRoute(
        Description('(managers only) Update the informant of an applet.')
        .notes(
            'managers can use this endpoint to update informant relationship for an applet.'
        )
        .modelParam(
            'id',
            model=AppletModel,
            description='ID of the applet to update',
            destName='applet',
            force=True,
            required=True
        )
        .param(
            'informant',
            ' '.join([
                'Relationship from informant to individual of interest.',
                'Currently handled informant relationships are',
                str([r for r in DEFINED_INFORMANTS.keys()])
            ]),
            required=True
        )
        .errorResponse('Write access was denied for this applet.', 403)
    )
    def updateInformant(self, applet, informant):
        user = self.getCurrentUser()
        if not AppletModel().isManager(applet['_id'], user):
            raise AccessException(
                "Only managers can update informant relationship"
            )
        AppletModel().updateRelationship(applet, informant)
        return(
            jsonld_expander.formatLdObject(
                applet,
                'applet',
                user,
                refreshCache=False
            )
        )

    @access.user(scope=TokenScope.DATA_WRITE)
    @autoDescribeRoute(
        Description('Deactivate an applet by ID.')
        .notes(
            'this endpoint is used for deactivating an applet. <br>'
            'we don\'t completely remove applet from database and we can revert it when it\'s needed.'
        )
        .modelParam(
            'id',
            model=AppletModel,
            description='ID of the applet to update',
            destName='applet',
            level=AccessType.WRITE
        )
        .errorResponse('Invalid applet ID.')
        .errorResponse('Write access was denied for this applet.', 403)
    )
    def deactivateApplet(self, applet):
        from girderformindlogger.models.profile import Profile

        user = self.getCurrentUser()
        if applet.get('meta', {}).get('applet', {}).get('deleted'):
            raise AccessException('this applet is already removed')

        if not AppletModel().isManager(applet['_id'], user):
            raise AccessException('only managers can remove applet')

        successed = AppletModel().deactivateApplet(applet)
        if successed:
            message = 'Successfully deactivated applet {} ({}).'.format(
                AppletModel().preferredName(applet),
                applet.get('_id')
            )
            EventsModel().deleteEventsByAppletId(applet.get('_id'))
        else:
            message = 'Could not deactivate applet {} ({}).'.format(
                AppletModel().preferredName(applet),
                applet.get('_id')
            )
            Description().errorResponse(message, 403)

        return message

    @access.user(scope=TokenScope.DATA_READ)
    @autoDescribeRoute(
        Description('Get an applet by ID.')
        .notes(
            'use this api to get applet info (protocol, activity, item) from applet_id. <br>'
            'refreshCache parameter in this endpoint is deprecated and you don\'t need to set it.'
        )
        .modelParam(
            'id',
            model=AppletModel,
            level=AccessType.READ,
            destName='applet'
        )
        .param(
            'refreshCache',
            'Reparse JSON-LD',
            required=False,
            dataType='boolean'
        )
        .errorResponse('Invalid applet ID.')
        .errorResponse('Read access was denied for this applet.', 403)
    )
    def getApplet(self, applet, refreshCache=False):
        user = self.getCurrentUser()

        # we don't need to refreshCache here (cached data is automatically updated whenever original data changes).
        refreshCache = False

        if refreshCache:
            thread = threading.Thread(
                target=jsonld_expander.formatLdObject,
                args=(applet, 'applet', user),
                kwargs={'refreshCache': refreshCache}
            )
            thread.start()
            return({
                "message": "The applet is being refreshed. Please check back "
                           "in several mintutes to see it."
            })
        return(
            jsonld_expander.formatLdObject(
                applet,
                'applet',
                user,
                refreshCache=refreshCache
            )
        )

    @access.user(scope=TokenScope.DATA_WRITE)
    @autoDescribeRoute(
        Description('reload protocol into database and refresh cache.')
        .notes(
            'this api is used for reloading applet. <br>'
            'manager/editors will need to make request to this endpoint when they update version of protocol.'
        )
        .modelParam(
            'id',
            model=AppletModel,
            level=AccessType.READ,
            destName='applet'
        )
        .errorResponse('Invalid applet ID.')
        .errorResponse('Write access was denied for this applet.', 403)
    )
    def refresh(self, applet):
        user = self.getCurrentUser()

        if not AppletModel().isCoordinator(applet['_id'], user):
            raise AccessException(
                "Only coordinators and managers can update applet."
            )

        thread = threading.Thread(
            target=AppletModel().reloadAndUpdateCache,
            args=(applet, user)
        )

        thread.start()

        return({
            "message": "The protocol is being reloaded and cached data is being updated. Please check back "
                        "in several mintutes to see it."
        })


    @access.user(scope=TokenScope.DATA_READ)
    @autoDescribeRoute(
        Description('Get associated groups for a given role and applet ID.')
        .notes(
            'Use this endpoint to get associated groups for an applet. <br>'
            'users who are associated with one of group for an applet will be able to connect this applet.'
        )
        .modelParam('id', 'ID of the Applet.', model=AppletModel, level=AccessType.READ)
        .param(
            'role',
            'One of ' + str(set(USER_ROLE_KEYS)),
            default='user',
            required=False,
            strip=True
        )
        .errorResponse('Invalid applet ID.')
        .errorResponse('Read access was denied for this applet.', 403)
    )
    def getAppletGroups(self, folder, role):
        applet = folder
        user = self.getCurrentUser()
        groups = [
            group for group in AppletModel(
            ).getAppletGroups(applet).get(role) if ObjectId(group) in [
                *user.get('groups', []),
                *user.get('formerGroups', []),
                *[invite['groupId'] for invite in [
                    *user.get('groupInvites', []),
                    *user.get('declinedInvites', [])
                ]]
            ]
        ]
        return(
            groups
        )

    @access.user(scope=TokenScope.DATA_WRITE)
    @autoDescribeRoute(
        Description('Get roles for an applet by ID.')
        .modelParam(
            'id',
            model=AppletModel,
            level=AccessType.WRITE,
            description='ID of the Applet.'
        )
        .errorResponse('Invalid applet ID.')
        .errorResponse('Write access was denied for this applet.', 403)
        .notes('Only users with write access can see roles.')
    )
    def getAppletRoles(self, folder):
        applet = folder
        user = Applet().getCurrentUser()
        return(AppletModel().getFullRolesList(applet))

    @access.user(scope=TokenScope.DATA_WRITE)
    @autoDescribeRoute(
        Description('Invite a user to a role in an applet.')
        .notes(
            'coordinator/managers can use this endpoint to create a new invitation url. <br>'
            'This endpoint is deprecated. (you\'ll need to use POST^applet/[id]/inviteUser instead of this endpoint.)'
        )
        .modelParam(
            'id',
            model=AppletModel,
            level=AccessType.READ,
            destName='applet'
        )
        .param(
            'role',
            'Role to invite this user to. One of ' + str(set(USER_ROLE_KEYS)),
            default='user',
            required=False,
            strip=True
        )
        .param(
            'idCode',
            'ID code for data reporting. One will be generated if none is '
            'provided.',
            required=False,
            strip=True
        )
        .jsonParam(
            'profile',
            'Optional, coordinator-defined user profile information, eg, '
            '`displayName`, `email`',
            required=False,
            paramType='form'
        )
        .errorResponse('ID was invalid.')
        .errorResponse('Write access was denied for the folder or its new parent object.', 403)
    )
    def invite(self, applet, role="user", idCode=None, profile=None):
        from girderformindlogger.models.invitation import Invitation
        from girderformindlogger.models.profile import Profile

        user = self.getCurrentUser()
        try:
            if role not in USER_ROLE_KEYS:
                raise ValidationException(
                    'Invalid role.',
                    'role'
                )

            invitation = Invitation().createInvitation(
                applet=applet,
                coordinator=user,
                role=role,
                profile=profile,
                idCode=idCode
            )

            return(Profile().displayProfileFields(invitation, user, forceManager=True))
        except:
            import sys, traceback
            print(sys.exc_info())

    @access.user(scope=TokenScope.DATA_WRITE)
    @autoDescribeRoute(
        Description('Invite a user to a role in an applet.')
        .notes(
            'coordinator/manager can use this endpoint to invite a user for his applet. <br>'
            'user who is invited will get invitation link via email so that they can accept/decline invitation there.'
        )
        .modelParam(
            'id',
            model=AppletModel,
            level=AccessType.READ,
            destName='applet'
        )
        .param(
            'role',
            'Role to invite this user to. One of ' + str(set(USER_ROLE_KEYS)),
            default='user',
            required=False
        )
        .param(
            'email',
            'required, email of user',
            required=True,
        )
        .param(
            'firstName',
            'firstName for user',
            required=True
        )
        .param(
            'lastName',
            'lastName for user',
            required=True
        )
        .param(
            'MRN',
            'MRN for user',
            default='',
            required=False
        )
        .errorResponse('Write access was denied for the folder or its new parent object.', 403)
    )
    def inviteUser(self, applet, role="user", email='', firstName='', lastName='', MRN=''):
        from girderformindlogger.models.invitation import Invitation
        from girderformindlogger.models.profile import Profile

        if not mail_utils.validateEmailAddress(email):
            raise ValidationException(
                'invalid email', 'email'
            )

        thisUser = self.getCurrentUser()

        encryptedEmail = UserModel().hash(email)
        invitedUser = UserModel().findOne({'email': encryptedEmail, 'email_encrypted': True})

        if not invitedUser:
            invitedUser = UserModel().findOne({'email': email, 'email_encrypted': {'$ne': True}})

        if not AppletModel().isCoordinator(applet['_id'], thisUser):
            raise AccessException(
                "Only coordinators and managers can invite users."
            )

        if role not in USER_ROLE_KEYS:
            raise ValidationException(
                'Invalid role.',
                'role'
            )

        invitation = Invitation().createInvitationForSpecifiedUser(
            applet=applet,
            coordinator=thisUser,
            role=role,
            user=invitedUser,
            firstName=firstName,
            lastName=lastName,
            MRN=MRN,
            userEmail=encryptedEmail
        )

        web_url = os.getenv('WEB_URI') or 'localhost:8082'
        url = f'{web_url}/#/invitation/{str(invitation["_id"])}'

        managers = mail_utils.htmlUserList(
            AppletModel().listUsers(applet, 'manager', force=True)
        )
        coordinators = mail_utils.htmlUserList(
            AppletModel().listUsers(applet, 'coordinator', force=True)
        )
        reviewers = mail_utils.htmlUserList(
            AppletModel().listUsers(applet, 'reviewer', force=True)
        )

        html = mail_utils.renderTemplate('inviteUserWithoutAccount.mako' if not invitedUser else 'userInvite.mako' if role == 'user' else 'inviteEmployee.mako', {
            'url': url,
            'userName': firstName,
            'coordinatorName': thisUser['firstName'],
            'appletName': applet['displayName'],
            'MRN': MRN,
            'managers': managers,
            'coordinators': coordinators,
            'reviewers': reviewers,
            'role': role
        })

        mail_utils.sendMail(
            'invitation for an applet',
            html,
            [email]
        )

        return 'sent invitation mail to {}'.format(email)

    @access.user(scope=TokenScope.DATA_WRITE)
    @autoDescribeRoute(
        Description('Deprecated. Do not use')
        .modelParam('id', model=AppletModel, level=AccessType.READ)
        .param(
            'activity',
            'Deprecated. Do not use.'
            'schedule.',
            required=False
        )
        .jsonParam(
            'schedule',
            'Deprecated. Do not use.',
            paramType='form',
            required=False
        )
        .errorResponse('Invalid applet ID.')
        .errorResponse('Read access was denied for this applet.', 403)
        .deprecated()
    )
    def setConstraints(self, folder, activity, schedule, **kwargs):
        thisUser = self.getCurrentUser()
        applet = jsonld_expander.formatLdObject(
            _setConstraints(folder, activity, schedule, thisUser),
            'applet',
            thisUser,
            refreshCache=True
        )
        jsonld_expander.createCache(folder, applet, 'applet')

        return(applet)

    @access.user(scope=TokenScope.DATA_READ)
    @autoDescribeRoute(
        Description('Get schedule information for an applet.')
        .notes(
            'This endpoint is used to get schedule data for an applet. <br>'
            'This endpoint returns schedule info for logged in user unless getAllEvents parameter is set to true. <br>'
            '* only coordinator/managers are able to set getAllEvents to true when they are making request to this endpoint'
        )
        .modelParam(
            'id',
            model=AppletModel,
            level=AccessType.READ,
            destName='applet'
        )
        .param(
            'getAllEvents',
            'return all events for an applet if true',
            required=False,
            dataType='boolean'
        )
        .param(
            'refreshCache',
            'Reparse JSON-LD',
            required=False,
            dataType='boolean'
        )
        .errorResponse('Invalid applet ID.')
        .errorResponse('Read access was denied for this applet.', 403)
    )
    def getSchedule(self, applet, getAllEvents = False, refreshCache=False):
        user = self.getCurrentUser()

        if not getAllEvents:
            schedule = EventsModel().getScheduleForUser(applet['_id'], user['_id'], AppletModel().isCoordinator(applet['_id'], user))
        else:
            if not AppletModel().isCoordinator(applet['_id'], user):
                raise AccessException(
                    "Only coordinators and managers can get all events."
                )
            schedule = EventsModel().getSchedule(applet['_id'])

        return schedule

    @access.user(scope=TokenScope.DATA_WRITE)
    @autoDescribeRoute(
        Description('Set or update schedule information for an applet.')
        .notes(
            'this endpoint is used for setting schedule for an applet. <br>'
            'only coordinator/managers are able to make request to this endpoint. <br>'
        )
        .modelParam(
            'id',
            model=AppletModel,
            level=AccessType.READ,
            destName='applet'
        )
        .param(
            'rewrite',
            'True if delete original events and insert all of them again.',
            default=True,
            dataType='boolean',
            required=False
        )
        .jsonParam(
            'deleted',
            'id array of events specifying removed events',
            paramType='form',
            default=[],
            required=False
        )
        .jsonParam(
            'schedule',
            'A JSON object containing schedule information for an applet',
            paramType='form',
            required=False
        )
        .errorResponse('Invalid applet ID.')
        .errorResponse('Read access was denied for this applet.', 403)
    )
    def setSchedule(self, applet, rewrite, deleted, schedule, **kwargs):
        thisUser = self.getCurrentUser()
        if not AppletModel().isCoordinator(applet['_id'], thisUser):
            raise AccessException(
                "Only coordinators and managers can update applet schedules."
            )

        assigned = {}
        if 'events' in schedule:
            for event in schedule['events']:
                if 'id' in event:
                    event['id'] = ObjectId(event['id'])
                    assigned[event['id']] = True

        if rewrite:
            original = EventsModel().getSchedule(applet['_id'])

            if 'events' in original:
                for event in original['events']:
                    original_id = event.get('id')
                    if original_id not in assigned:
                        EventsModel().deleteEvent(ObjectId(original_id))
        else:
            if isinstance(deleted, list):
                for event_id in deleted:
                    EventsModel().deleteEvent(ObjectId(event_id))

        if 'events' in schedule:
            # insert and update events/notifications
            for event in schedule['events']:
                savedEvent = EventsModel().upsertEvent(event, applet, event.get('id', None))
                event['id'] = savedEvent['_id']

        return {
            "applet": {
                "schedule": schedule if rewrite else EventsModel().getSchedule(applet['_id'])
            }
        }


def authorizeReviewer(applet, reviewer, user):
    thisUser = Applet().getCurrentUser()
    user = UserModel().load(
        user,
        level=AccessType.NONE,
        user=thisUser
    )
    try:
        applet = FolderModel().load(
            applet,
            level=AccessType.READ,
            user=thisUser
        )
        responsesCollection = FolderModel().createFolder(
            parent=user,
            name='Responses',
            parentType='user',
            public=False,
            creator=thisUser,
            reuseExisting=True
        )
        thisApplet = list(FolderModel().childFolders(
            parent=responsesCollection,
            parentType='folder',
            user=thisUser,
            filters={
                'meta.applet.@id': str(applet['_id'])
            }
        ))
        thisApplet = thisApplet[0] if len(
            thisApplet
        ) else FolderModel().setMetadata(
            FolderModel().createFolder(
                parent=responsesCollection,
                name=FolderModel().preferredName(applet),
                parentType='folder',
                public=False,
                creator=thisUser,
                allowRename=True,
                reuseExisting=False
            ),
            {
                'applet': {
                    '@id': str(applet['_id'])
                }
            }
        )
        accessList = thisApplet['access']
        accessList['users'].append({
            "id": reviewer,
            "level": AccessType.READ
        })
        thisApplet = FolderModel().setAccessList(
            thisApplet,
            accessList,
            save=True,
            recurse=True,
            user=thisUser
        )
    except:
        thisApplet = None
    return(thisApplet)


def authorizeReviewers(assignment):
    assignment = assignment.get('meta', assignment)
    thisUser = Applet().getCurrentUser()
    allUsers = []
    reviewAll = []
    members = assignment.get('members', [])
    applet = assignment.get('applet').get('@id')
    for member in [member for member in members if 'roles' in member]:
        try:
            if member['roles']['user']:
                allUsers.append(getCanonicalUser(member.get("@id")))
        except:
            pass
        if 'reviewer' in member['roles']:
            if "ALL" in member['roles']['reviewer']:
                reviewAll.append(getCanonicalUser(member.get("@id")))
            for user in [
                user for user in member['roles'][
                    'reviewer'
                ] if user not in SPECIAL_SUBJECTS
            ]:
                authorizeReviewer(
                    assignment.get('applet').get('@id'),
                    getCanonicalUser(member.get('@id')),
                    getCanonicalUser(user)
                )
    for reviewer in reviewAll:
        [authorizeReviewer(
            assignment.get('applet').get('@id'),
            reviewer,
            user
        ) for user in allUsers]
    return(None)


def _invite(applet, user, role, rsvp, subject):
    """
    Helper function to invite a user to an applet.

    :param applet: Applet to invite user to
    :type applet: AppletModel
    :param user: ID (canonical or applet-specific) or email address of user to
                 invite
    :type user: string
    :param role: Role to invite user to
    :type role: string
    :param rsvp: Require user acceptance?
    :type rsvp: boolean
    :param subject: Subject about 'user' role can inform or about which
                    'reviewer' role can review
    :type subject: string or literal
    :returns: New assignment (dictionary)
    """
    if role not in USER_ROLE_KEYS:
        raise ValidationException(
            'Invalid role.',
            'role'
        )
    thisUser = Applet().getCurrentUser()
    user = user if user else str(thisUser['_id'])

    if mail_utils.validateEmailAddress(user):
        user = UserModel().hash(user)

    if bool(rsvp):
        groupName = {
            'title': '{} {}s'.format(
                str(applet.get('_id')),
                role
            )
        }
        groupName['lower'] = groupName.get('title', '').lower()
        group = GroupModel().findOne(query={'lowerName': groupName['lower']})
        if not group or group is None:
            group = GroupModel().createGroup(
                name=groupName['title'],
                creator=thisUser,
                public=bool(role in ['manager', 'reviewer'])
            )
    try:
        assignments = CollectionModel().createCollection(
            name="Assignments",
            public=True,
            reuseExisting=True
        )
        assignmentType = 'collection'
    except AccessException:
        assignments, assignmentType = selfAssignment()
    appletAssignment = list(FolderModel().childFolders(
        parent=assignments,
        parentType=assignmentType,
        user=thisUser,
        filters={
            'meta.applet.@id': str(applet['_id']) if '_id' in applet else None
        }
    ))
    appletAssignment = appletAssignment[0] if len(
        appletAssignment
    ) else FolderModel().setMetadata(
        FolderModel().createFolder(
            parent=assignments,
            name=FolderModel().preferredName(applet),
            parentType=assignmentType,
            public=False,
            creator=thisUser,
            allowRename=True,
            reuseExisting=False
        ),
        {
            'applet': {
                '@id': str(applet['_id']) if '_id' in applet else None
            }
        }
    )
    meta = appletAssignment.get('meta', {})
    members = meta.get('members', []) if meta.get(
        'members'
    ) is not None else []
    cUser = getUserCipher(appletAssignment, user)
    subject = subject.upper() if subject is not None and subject.upper(
    ) in SPECIAL_SUBJECTS else getUserCipher(
        appletAssignment,
        str(thisUser['_id']) if subject is None else subject
    )
    thisAppletAssignment = {
        '@id': str(cUser),
        'roles': {
            role: True if role not in [
                'reviewer',
                'user'
            ] else [
                subject
            ]
        }
    }
    for i, u in enumerate(members):
        if '@id' in u and u["@id"]==str(cUser):
            thisAppletAssignment = members.pop(i)
            if 'roles' not in thisAppletAssignment:
                thisAppletAssignment['roles'] = {}
            thisAppletAssignment['roles'][
                role
            ] = True if role not in [
                'reviewer',
                'user'
            ] else [
                subject
            ] if (
                subject in SPECIAL_SUBJECTS
            ) or (
                'reviewer' not in thisAppletAssignment[
                    'roles'
                ]
            ) else list(set(
                thisAppletAssignment['roles']['reviewer'] + [subject]
            ).difference(set(
                SPECIAL_SUBJECTS
            ))) if "ALL" not in thisAppletAssignment['roles'][
                'reviewer'
            ] else ["ALL"]
    members.append(thisAppletAssignment)
    meta['members'] = members
    appletAssignment = FolderModel().setMetadata(appletAssignment, meta)
    authorizeReviewers(appletAssignment)
    return(appletAssignment)


def selfAssignment():
    thisUser = Applet().getCurrentUser()
    assignmentsFolder = FolderModel().createFolder(
        parent=thisUser,
        parentType='user',
        name='Assignments',
        creator=thisUser,
        public=False,
        reuseExisting=True
    )
    return((
        assignmentsFolder,
        'folder'
    ))


def _setConstraints(applet, activity, schedule, user, refreshCache=False):
    """
    Helper function for method recursion.

    :param applet: applet Object
    :type applet: dict
    :param activity: Activity ID
    :type activity: str, list, or None
    :param schedule: schedule data
    :type schedule: dict, list, or None
    :param user: user making the call
    :type user: dict
    :returns: updated applet Object
    """
    if activity is None:
        if schedule is not None:
            appletMeta = applet.get('meta', {})
            appletMeta['applet']['schedule'] = schedule
            applet = AppletModel().setMetadata(applet, appletMeta)
        return(applet)
    if isinstance(activity, str) and activity.startswith('['):
        try:
            activity = [
                activity_.replace(
                    "'",
                    ""
                ).replace(
                    '"',
                    ''
                ).strip() for activity_ in activity[1:-1].split(',')
            ]
        except (TypeError, AttributeError) as e:
            print(e)
    if isinstance(activity, list):
        for activity_ in activity:
            applet = _setConstraints(
                applet,
                activity_,
                schedule,
                user
            )
        return(applet)
    try:
        activityLoaded = ActivityModel().getFromUrl(
            activity,
            'activity',
            thisUser,
            refreshCache
        )[0]
    except:
        activityLoaded = ActivityModel().load(
            activity,
            AccessType.WRITE,
            user
        )
    try:
        activityMeta = activityLoaded['meta'].get('activity')
    except AttributeError:
        raise ValidationException(
            'Invalid activity.',
            'activity'
        )
    activityKey = activityMeta.get(
        'url',
        activityMeta.get(
            '@id',
            activityLoaded.get(
                '_id'
            )
        )
    )
    if activityKey is None:
        raise ValidationException(
            'Invalid activity.',
            'activity'
        )
    else:
        activityKey = jsonld_expander.reprolibPrefix(activityKey)
    protocolExpanded = jsonld_expander.formatLdObject(
        applet,
        'applet',
        user
    ).get('applet', {})
    protocolOrder = protocolExpanded.get('ui', {}).get('order', [])
    framedActivityKeys = [
        protocolOrder[i] for i, v in enumerate(
            protocolExpanded.get(
                "reprolib:terms/order"
            )[0].get(
                "@list"
            )
        ) if jsonld_expander.reprolibPrefix(v.get("@id"))==activityKey
    ]
    if schedule is not None:
        appletMeta = applet.get('meta', {})
        scheduleInApplet = appletMeta.get('applet', {}).get('schedule', {})
        for k in framedActivityKeys:
            scheduleInApplet[k] = schedule
        appletMeta['applet']['schedule'] = scheduleInApplet
        applet = AppletModel().setMetadata(applet, appletMeta)
    return(applet)
