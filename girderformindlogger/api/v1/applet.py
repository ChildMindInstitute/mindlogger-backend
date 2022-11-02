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

import datetime
import json
import os
import threading
import time
import uuid

from bson import json_util
from bson.objectid import ObjectId
from pymongo import DESCENDING

from girderformindlogger.api import access
from girderformindlogger.constants import AccessType, TokenScope, \
    DEFINED_INFORMANTS, SPECIAL_SUBJECTS, USER_ROLES, MAX_PULL_SIZE
from girderformindlogger.exceptions import AccessException, ValidationException
from girderformindlogger.i18n import t
from girderformindlogger.models.account_profile import AccountProfile
from girderformindlogger.models.activity import Activity as ActivityModel
from girderformindlogger.models.applet import Applet as AppletModel
from girderformindlogger.models.applet_library import AppletLibrary
from girderformindlogger.models.collection import Collection as CollectionModel
from girderformindlogger.models.events import Events as EventsModel
from girderformindlogger.models.folder import Folder as FolderModel
from girderformindlogger.models.group import Group as GroupModel
from girderformindlogger.models.invitation import Invitation as InvitationModel
from girderformindlogger.models.item import Item as ItemModel
from girderformindlogger.models.profile import Profile as ProfileModel
from girderformindlogger.models.protocol import Protocol as ProtocolModel
from girderformindlogger.models.response_alerts import ResponseAlerts
from girderformindlogger.models.roles import getCanonicalUser, getUserCipher
from girderformindlogger.models.user import User as UserModel
from girderformindlogger.utility import jsonld_expander, mail_utils
from girderformindlogger.utility.validate import validator, email_validator, symbol_validator
from ..describe import Description, autoDescribeRoute
from ..rest import Resource
from girderformindlogger.utility.redis import cache

USER_ROLE_KEYS = USER_ROLES.keys()


class Applet(Resource):

    def __init__(self):
        super(Applet, self).__init__()
        self.resourceName = 'applet'
        self._model = AppletModel()
        self.route('GET', (':id',), self.getApplet)
        self.route('GET', ('check_state', ':request_id',), self.check_state)
        self.route('GET', (':id', 'data'), self.getAppletData)
        self.route('GET', (':id', 'groups'), self.getAppletGroups)
        self.route('POST', (), self.createApplet)
        self.route('POST', (':id', 'setRetention'), self.setRetentionSettings)
        self.route('PUT', (':id', 'encryption'), self.setAppletEncryption)
        self.route('PUT', (':id', 'informant'), self.updateInformant)
        self.route('PUT', (':id', 'assign'), self.assignGroup)
        self.route('PUT', (':id', 'constraints'), self.setConstraints)
        self.route('PUT', (':id', 'setSchedule'), self.setSchedule)
        self.route('PUT', (':id', 'getSchedule'), self.getSchedule)
        self.route('PUT', (':id', 'refresh'), self.refresh)
        self.route('POST', (':id', 'invite'), self.invite)
        self.route('POST', (':id', 'inviteUser'), self.inviteUser)
        self.route('POST', (':id', 'publicLink'), self.createPublicLink)
        self.route('GET', (':id', 'publicLink'), self.getPublicLink)
        self.route('GET', ('public', ':publicId', 'data'), self.getAppletFromPublicLink)
        self.route('PUT', (':id', 'publicLink'), self.replacePublicLink)
        self.route('DELETE', (':id', 'publicLink'), self.deletePublicLink)

        self.route('GET', ('invitelink', ':inviteLinkId', 'info'), self.viewInviteLinkInfo)
        self.route('POST', ('invitelink', ':inviteLinkId', 'accept'), self.acceptOpenInviteLink)
        self.route('PUT', (':id', 'updateRoles'), self.updateRoles)
        self.route('PUT', (':id', 'updateProfile'), self.updateProfile)

        self.route('PUT', (':id', 'reviewer', 'userList'), self.updateUserListForReviewer)
        self.route('GET', (':id', 'reviewer', 'userList'), self.getUserListForReviewer)
        self.route('GET', (':id', 'reviewerList'), self.getReviewerListForUser)

        self.route('GET', (':id', 'roles'), self.getAppletRoles)
        self.route('GET', (':id', 'users'), self.getAppletUsers)
        self.route('GET', (':id', 'invitations'), self.getAppletInvitations)
        self.route('DELETE', (':id',), self.deactivateApplet)
        self.route('POST', ('fromJSON', ), self.createAppletFromProtocolData)
        self.route('PUT', (':id', 'fromJSON'), self.updateAppletFromProtocolData)
        self.route('PUT', (':id', 'activities', 'visibility'), self.updateActivityVisibility)
        self.route('GET', (':id', 'protocolData'), self.getProtocolData)
        self.route('GET', (':id', 'versions'), self.getProtocolVersions)
        self.route('PUT', (':id', 'prepare',), self.prepareAppletForEdit)
        self.route('POST', (':id', 'duplicate', ), self.duplicateApplet)
        self.route('POST', ('setBadge',), self.setBadgeCount)
        self.route('PUT', (':id', 'transferOwnerShip', ), self.transferOwnerShip)
        self.route('DELETE', (':id', 'deleteUser', ), self.deleteUserFromApplet)
        self.route('GET', ('validateName',), self.validateAppletName)
        self.route('PUT', (':id', 'name', ), self.renameApplet)
        self.route('PUT', (':id', 'status'), self.updateAppletPublishStatus)
        self.route('PUT', (':id', 'welcomeApplet'), self.updateWelcomeAppletStatus)
        self.route('PUT', (':id', 'searchTerms'), self.updateAppletSearch)
        self.route('GET', (':id', 'searchTerms'), self.getAppletSearch)
        self.route('GET', (':id', 'libraryUrl'), self.getAppletLibraryUrl)
        self.route('POST', (':id', 'setTheme', ), self.setAppletTheme)

    @access.user(scope=TokenScope.DATA_WRITE)
    @autoDescribeRoute(
        Description('Retentions settings for particular applet.')
        .modelParam(
            'id',
            model=AppletModel,
            level=AccessType.ADMIN,
            destName='applet'
        )
        .param(
            'period',
            'Set period days/weeks/months/years how long user data will be stored',
            dataType='integer',
            default=5,
            required=True
        )
        .param(
            'retention',
            'Retention parameter inslude only day/week/month/year',
            default='year',
            required=True,
            enum=['day', 'week', 'month', 'year', 'indefinitely']
        )
        .param(
            'enabled',
            'set if you want to enable or disable retention settings',
            default=True,
            required=False
        )
    )
    def setRetentionSettings(self, applet, period, retention, enabled):
        thisUser = self.getCurrentUser()
        if not self._model.isManager(applet['_id'], thisUser):
            raise AccessException('only manager/owners can change applet retention setting')
        self.requireParams('period', {'period': period})
        self.requireParams('retention', {'retention': retention})

        applet['meta']['retentionSettings'] = {
            'period': period,
            'retention': retention,
            'enabled': enabled
        }
        self._model.setMetadata(applet, applet['meta'])

        jsonld_expander.clearCache(applet, 'applet')
        return {'message': 'successed'}

    @access.user(scope=TokenScope.DATA_WRITE)
    @autoDescribeRoute(
        Description('Reset badge parameter')
            .notes(
            'this endpoint is used to reset badge parameter in profile collection. <br>'
            'users who are associated with that group will be able to connect to this endpoint.'
        )
        .param(
            'badge',
            'set badge status',
            default=0,
            required=False,
        )
    )
    def setBadgeCount(self, badge):
        thisUser = self.getCurrentUser()
        ProfileModel().updateProfiles(thisUser, {"badge": int(badge)})
        return({"message": "Badge was successfully reseted"})

    @access.user(scope=TokenScope.DATA_OWN)
    @autoDescribeRoute(
        Description('update encryption info for applet.')
        .modelParam(
            'id',
            model=AppletModel,
            level=AccessType.ADMIN,
            destName='applet'
        )
        .jsonParam(
            'encryption',
            'encryption info which public key and prime for applet',
            paramType='form',
            required=True
        )
    )
    def setAppletEncryption(self, applet, encryption):
        thisUser = self.getCurrentUser()
        if not self._model.isManager(applet['_id'], thisUser):
            raise AccessException('only manager/owners can change applet encryption info')

        applet['meta']['encryption'] = encryption
        applet['updated'] = datetime.datetime.utcnow()

        applet = self._model.setMetadata(applet, applet['meta'])

        jsonld_expander.clearCache(applet, 'applet')
        return { 'message': 'successed' }

    @access.user(scope=TokenScope.DATA_OWN)
    @autoDescribeRoute(
        Description('update role from employer of applet.')
        .modelParam(
            'id',
            model=AppletModel,
            level=AccessType.ADMIN,
            destName='applet'
        )
        .param(
            'userId',
            'id for applet user',
            required=True,
            default=None
        )
        .jsonParam(
            'roleInfo',
            'role info which contains information for grant/revoke roles',
            paramType='form',
            required=True
        )
    )
    def updateRoles(self, applet, userId, roleInfo):
        userProfile = ProfileModel().findOne({'_id': ObjectId(userId)})

        if not userProfile or userProfile['appletId'] != applet['_id']:
            raise ValidationException('unable to find user with specified id')

        accountProfile = self.getAccountProfile()
        thisUser = self.getCurrentUser()

        isCoordinator = self._model.isCoordinator(applet['_id'], thisUser)
        isManager = self._model.isManager(applet['_id'], thisUser)

        if not accountProfile or 'manager' in userProfile.get('roles') and applet.get('accountId', None) != thisUser['accountId'] or not isCoordinator:
            raise AccessException('You don\'t have enough permission to update role from this user.')

        if 'user' in userProfile['roles'] and len(userProfile['roles']) == 1:
            raise AccessException('You can update roles only from employers.')

        for role in roleInfo:
            if role in USER_ROLE_KEYS:
                if role != 'reviewer' and not isManager or role == 'user':
                    continue

                if roleInfo[role] != 0:
                    userProfile = self._model.grantRole(
                        applet,
                        userProfile,
                        role,
                        roleInfo[role] if role == 'reviewer' and isinstance(roleInfo[role], list) else []
                    )
                else:
                    userProfile = self._model.revokeRole(applet, userProfile, role)

        return ({
            'roles': userProfile.get('roles', [])
        })

    @access.user(scope=TokenScope.DATA_OWN)
    @autoDescribeRoute(
        Description('update profile of user of applet')
        .modelParam(
            'id',
            model=AppletModel,
            level=AccessType.ADMIN,
            destName='applet'
        )
        .param(
            'userId',
            'id for applet user',
            required=True,
            default=None
        )
        .param(
            'firstName',
            'first name of the user',
            default=None,
            required=False
        )
        .param(
            'lastName',
            'last name of the user',
            default=None,
            required=False
        )
        .param(
            'MRN',
            'MRN of the user',
            default=None,
            required=False
        )
        .param(
            'nickName',
            'nickName of the user',
            default=None,
            required=False
        )
    )
    def updateProfile(self, applet, userId, firstName=None, lastName=None, MRN=None, nickName=None):
        userProfile = ProfileModel().findOne({'_id': ObjectId(userId)})

        if not userProfile or userProfile['appletId'] != applet['_id']:
            raise ValidationException('unable to find user with specified id')

        accountProfile = self.getAccountProfile()
        thisUser = self.getCurrentUser()

        isCoordinator = self._model.isCoordinator(applet['_id'], thisUser)
        if not accountProfile or 'manager' in userProfile.get('roles') and applet.get('accountId', None) != thisUser['accountId'] or not isCoordinator:
            raise AccessException('permission denied')

        updates = {
            'firstName': firstName,
            'lastName': lastName,
            'MRN': MRN,
            'nickName': nickName
        }

        for key in updates:
            if updates[key] is not None:
                userProfile[key] = updates[key]

        userProfile = ProfileModel().save(userProfile, validate=False)

        return ProfileModel().getProfileData(
            userProfile,
            ProfileModel().findOne({'appletId': applet['_id'], 'userId': thisUser['_id']})
        )

    @access.user(scope=TokenScope.DATA_OWN)
    @autoDescribeRoute(
        Description('Update user list that reviewer can view.')
        .notes(
            'this endpoint will be used to update user list that reviewer can view.'
        )
        .modelParam(
            'id',
            model=AppletModel,
            level=AccessType.ADMIN,
            destName='applet'
        )
        .param(
            'reviewerId',
            'id of reviewer',
            required=True,
            default=None
        )
        .jsonParam(
            'users',
            'user list that reviewer can view',
            paramType='form',
            required=False,
            default=[]
        )
        .param(
            'operation',
            'one of ["replace", "add", "delete"]',
            required=False,
            default='replace'
        )
    )
    def updateUserListForReviewer(self, applet, reviewerId, users, operation):
        if operation not in ['replace', 'add', 'delete']:
            raise ValidationException('invalid operation type')

        reviewerProfile = ProfileModel().findOne({'_id': ObjectId(reviewerId)})

        accountProfile = self.getAccountProfile()

        if not accountProfile or applet['_id'] not in accountProfile.get('applets', {}).get('manager', []) or \
            (reviewerProfile and 'manager' in reviewerProfile.get('roles', []) and applet['_id'] not in accountProfile.get('applets', {}).get('owner', [])):
            raise AccessException('You don\'t have enough permission to update user list for this reviewer.')

        if not reviewerProfile or 'reviewer' not in reviewerProfile.get('roles', []) or applet['_id'] != reviewerProfile['appletId']:
            raise AccessException('unable to find reviewer with specified id')

        ProfileModel().updateReviewerList(reviewerProfile, [ObjectId(userId) for userId in users], operation)

        return "success"

    @access.user(scope=TokenScope.DATA_READ)
    @autoDescribeRoute(
        Description('GET user list that reviewer can view.')
        .notes(
            'this endpoint will be used for managers/reviewers to view users that reviewer can access.'
        )
        .modelParam(
            'id',
            model=AppletModel,
            level=AccessType.READ,
            destName='applet'
        )
        .param(
            'reviewerId',
            'id of reviewer, we do not need to set this value when reviewer want to see his user list',
            required=False,
            default=None
        )
    )
    def getUserListForReviewer(self, applet, reviewerId):
        accountProfile = self.getAccountProfile()
        thisUser = self.getCurrentUser()

        if not accountProfile or reviewerId and applet['_id'] not in accountProfile.get('applets', {}).get('manager', []) or \
            not reviewerId and applet['_id'] not in accountProfile.get('applets', {}).get('reviewer', []):
            raise AccessException('You don\'t have enough permission to get list of users that specified reviewer can view.')

        profileModel = ProfileModel()
        reviewerProfile = profileModel.findOne({'_id': ObjectId(reviewerId)}) if reviewerId else profileModel.findOne({
            'appletId': applet['_id'],
            'userId': accountProfile['userId']
        })
        if not reviewerProfile or 'reviewer' not in reviewerProfile.get('roles', []) or applet['_id'] != reviewerProfile['appletId']:
            raise AccessException('unable to find reviewer with specified id')

        users = [
            profileModel.displayProfileFields(
                p,
                thisUser,
                forceManager=True
            )
            for p in list(
                profileModel.find({'appletId': applet['_id'], 'reviewers': reviewerProfile['_id']})
            )
        ]
        return users

    @access.user(scope=TokenScope.DATA_READ)
    @autoDescribeRoute(
        Description('GET reviewer list for user.')
        .notes(
            'this endpoint will be used for users to retrieve reviewer list that review his response.'
        )
        .modelParam(
            'id',
            model=AppletModel,
            level=AccessType.READ,
            destName='applet'
        )
        .param(
            'userId',
            'id of user to see reviewer list, we do not need to set this field if user want to see his reviewers',
            required=False,
            default=None
        )
    )
    def getReviewerListForUser(self, applet, userId):
        accountProfile = self.getAccountProfile()
        thisUser = self.getCurrentUser()
        if not accountProfile or userId and applet['_id'] not in accountProfile.get('applets', {}).get('manager', {}):
            raise AccessException('You do not have enough permission to get reviewer list')

        userProfile = ProfileModel().findOne({'_id': ObjectId(userId)}) if userId else ProfileModel().findOne({
            'appletId': applet['_id'],
            'userId': accountProfile['userId']
        })

        if not userProfile or 'user' not in userProfile.get('roles', []) or applet['_id'] != userProfile['appletId']:
            raise AccessException('unable to find user with specified id')

        return ProfileModel().getReviewerListForUser(applet['_id'], userProfile, thisUser)


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
            level=AccessType.READ,
            destName='applet'
        )
        .param(
            'retrieveRoles',
            'True if retrieve roles for each user. only owner/managers/coordinators can use this field.',
            dataType='boolean',
            required=False,
            default=False
        )
    )
    def getAppletUsers(self, applet, retrieveRoles=False):
        user = self.getCurrentUser()
        is_reviewer = AppletModel()._hasRole(applet['_id'], user, 'reviewer')
        is_coordinator = AppletModel().isCoordinator(applet['_id'], user)

        if not (is_coordinator or is_reviewer):
            raise AccessException("Only coordinators, managers and reviewers can see user lists.")

        profile = ProfileModel().findOne({'appletId': applet['_id'],
                                          'userId': user['_id']})

        if (not is_coordinator) and is_reviewer:
            # Only include the users this reviewer has access to.
            users = ProfileModel().find(query={'appletId': applet['_id'],
                                               'userId': {'$exists': True},
                                               'profile': True,
                                               'deactivated': {'$ne': True},
                                               'reviewers': profile['_id']})
            return {'active': [
                ProfileModel().displayProfileFields(p, user, forceManager=True)
                for p in list(users)
            ]}

        return AppletModel().getAppletUsers(applet, user, force=True, retrieveRoles=retrieveRoles, retrieveRequests=AppletModel().isManager(applet['_id'], user))

    @access.user(scope=TokenScope.DATA_OWN)
    @autoDescribeRoute(
        Description('Get invitations for applet.')
        .notes(
            'this endpoint is used to getting invitations for an applet. <br>'
            'coordinator/managers can make request to this endpoint.'
        )
        .modelParam(
            'id',
            model=FolderModel,
            level=AccessType.READ,
            destName='applet'
        )
    )
    def getAppletInvitations(self, applet):
        user = self.getCurrentUser()
        is_coordinator = self._model.isCoordinator(applet['_id'], user)

        if not is_coordinator:
            raise AccessException("Only coordinators, managers and reviewers can view invitations.")

        return self._model.getAppletInvitations(applet)

    @access.user(scope=TokenScope.DATA_READ)
    @autoDescribeRoute(
        Description('Get content of protocol by applet id.')
        .modelParam('id', model=AppletModel, level=AccessType.READ, destName='applet')
        .param(
            'versions',
            'version of protocol data to retrieve',
            dataType='array',
            required=True,
            default=[]
        )
        .errorResponse('Invalid applet ID.')
        .errorResponse('Read access was denied for this applet.', 403)
    )
    def getProtocolData(self, applet, versions=[]):
        versions = json_util.loads(versions)

        thisUser = self.getCurrentUser()

        if not self._model._hasRole(applet['_id'], thisUser, 'editor'):
            raise AccessException('You don\'t have enough permission to get content of this protocol')

        protocol = ProtocolModel().load(applet.get('meta', {}).get('protocol', {}).get('_id', '').split('/')[-1], force=True)

        items = list(ItemModel().find({
            'folderId': protocol['meta'].get('contentId', None),
            'version': {
                '$in': versions
            }
        }, sort=[("created", DESCENDING)]))

        contents = []

        cacheIDToActivity = {}
        for item in items:
            content = json_util.loads(item['content'])
            activities = content['protocol'].get('activities', {})

            for activityIRI in dict.keys(activities):
                activity = activities[activityIRI]

                if type(activity) == str:
                    cacheId = activities[activityIRI].split('/')[-1]

                    if cacheId not in cacheIDToActivity:
                        activity = jsonld_expander.loadCache(cacheId)
                        cacheIDToActivity[cacheId] = activity

                    activities[activityIRI] = cacheIDToActivity[cacheId]

            contents.append({
                'version': item['version'],
                'content': content
            })

        return contents

    @access.user(scope=TokenScope.DATA_READ)
    @autoDescribeRoute(
        Description('Get content of protocol by applet id.')
        .modelParam('id', model=AppletModel, level=AccessType.READ, destName='applet')
        .param(
            'retrieveDate',
            'true if retrieve date for each version',
            dataType='boolean',
            required=True,
            default=False,
        )
        .errorResponse('Invalid applet ID.')
        .errorResponse('Read access was denied for this applet.', 403)
    )
    def getProtocolVersions(self, applet, retrieveDate=False):
        thisUser = self.getCurrentUser()

        if not applet['meta'].get('welcomeApplet') and not self._model._hasRole(applet['_id'], thisUser, 'editor') and not self._model._hasRole(applet['_id'], thisUser, 'reviewer'):
            raise AccessException('You don\'t have enough permission to get content of this protocol')

        protocol = ProtocolModel().load(applet.get('meta', {}).get('protocol', {}).get('_id', '').split('/')[-1], force=True)

        items = list(ItemModel().find({
            'folderId': protocol['meta'].get('contentId', None),
        }, fields=['version', 'created'], sort=[("created", DESCENDING)])) if 'contentId' in protocol['meta'] else []

        if retrieveDate:
            return [
                {
                    'version': item['version'],
                    'updated': item['created']
                } for item in items
            ]

        return [
            item['version'] for item in items
        ]

    @access.user(scope=TokenScope.DATA_WRITE)
    @autoDescribeRoute(
        Description('delete user from applet.')
        .notes(
            'this endpoint is used for deleting user\'s access to applet. <br>'
        )
        .modelParam(
            'id',
            model=AppletModel,
            description='ID of the applet',
            destName='applet',
            level=AccessType.WRITE
        )
        .param(
            'profileId',
            'id of profile to be deleted',
            required=True,
            default=None
        )
        .param(
            'deleteResponse',
            'true if delete response',
            dataType='boolean',
            required=True,
            default=True,
        )
        .errorResponse('Invalid applet ID.')
        .errorResponse('Write access was denied for this applet.', 403)
    )
    def deleteUserFromApplet(self, applet, profileId, deleteResponse=True):
        thisUser = self.getCurrentUser()
        accountProfile = self.getAccountProfile()

        profile = None
        if profileId:
            profile = ProfileModel().findOne({'_id': ObjectId(profileId)})
        if not profile:
            raise AccessException('unable to find user')

        if 'manager' in profile.get('roles', []) and applet.get('accountId', None) != thisUser['accountId'] or \
            (deleteResponse or len(profile.get('roles')) > 1) and applet['_id'] not in accountProfile.get('applets', {}).get('manager', []) or \
            applet['_id'] not in accountProfile.get('applets', {}).get('coordinator', []):
            raise AccessException('You don\'t have enough permission to perform this action')

        for role in USER_ROLE_KEYS:
            if role != 'user':
                profile = self._model.revokeRole(applet, profile, role)

        profile = self._model.revokeRole(applet, profile, 'user')

        ResponseAlerts().deleteResponseAlerts(profile['_id'])

        if deleteResponse:
            ProfileModel().remove(profile)
        else:
            profile['reviewers'] = []
            profile['deactivated'] = True

            ProfileModel().save(profile, validate=False)

        if deleteResponse:
            from girderformindlogger.models.response_folder import ResponseItem

            ResponseItem().removeWithQuery(
                query={
                    "baseParentType": 'user',
                    "baseParentId": profile['userId'],
                    "meta.applet.@id": applet['_id']
                }
            )

        return ({
            'message': 'successfully removed user from applet'
        })

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
        .param(
            'lang',
            'Language of mail template and web link',
            default='en',
            required=True
        )
        .jsonParam(
            'encryption',
            'encryption info',
            paramType='form',
            required=False
        )
        .errorResponse('Write access was denied for this applet.', 403)
    )
    def createApplet(self, protocolUrl=None, email='', name=None, informant=None, encryption={},
                     lang='en'):
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
                'email': email.lower().strip(),
                'constraints': {
                    'informantRelationship': informant
                } if informant is not None else None,
                'appletRole': appletRole,
                'accountId': profile['accountId'],
                'encryption': encryption
            }
        )
        thread.start()
        return {"message": t('applet_is_building', lang)}

    @access.user(scope=TokenScope.DATA_OWN)
    @autoDescribeRoute(
        Description('Change name of an applet.')
        .notes(
            'Use this endpoint to change name of applet. <br>'
        )
        .modelParam(
            'id',
            model=AppletModel,
            description='ID of the applet',
            destName='applet',
            level=AccessType.WRITE
        )
        .param(
            'name',
            'name of applet',
            required=True,
        )
        .errorResponse('Write access was denied for this applet.', 403)
    )
    def renameApplet(self, applet, name):
        editor = self.getCurrentUser()

        profile = ProfileModel().findOne({
            'appletId': applet['_id'],
            'userId': editor['_id']
        })

        if 'editor' not in profile.get('roles', []) and 'manager' not in profile.get('roles', []):
            raise AccessException("You don't have enough permission to update this applet.")

        self._model.renameApplet(applet, name, editor)

        return {
            'message': 'success'
        }

    @access.user(scope=TokenScope.DATA_OWN)
    @autoDescribeRoute(
        Description('Set Publish Status for an applet.')
        .notes(
            'Use this endpoint to publish an applet in the library. <br>'
        )
        .modelParam(
            'id',
            model=AppletModel,
            description='ID of the applet',
            destName='applet',
            level=AccessType.ADMIN
        )
        .param(
            'publish',
            'true if publishing applet',
            default=True,
            required=True,
            dataType='boolean'
        )
        .errorResponse('Write access was denied for this applet.', 403)
    )
    def updateAppletPublishStatus(self, applet, publish=True):
        thisUser = self.getCurrentUser()

        profile = ProfileModel().findOne({
            'appletId': applet['_id'],
            'userId': thisUser['_id']
        })

        if 'manager' not in profile.get('roles', []):
            raise AccessException("You don't have enough permission to update this applet.")

        ownerAccount = AccountProfile().findOne({'_id': applet['accountId']})

        applet['meta']['published'] = publish
        applet = self._model.setMetadata(applet, applet['meta'])

        if publish:
            AppletLibrary().addAppletToLibrary(applet)
        else:
            AppletLibrary().deleteAppletFromLibrary(applet)

        return { 'message': 'success' }

    @access.user(scope=TokenScope.DATA_OWN)
    @autoDescribeRoute(
        Description('Set Publish Status for an applet.')
        .notes(
            'Use this endpoint to make applet to available for all users. <br>'
        )
        .modelParam(
            'id',
            model=AppletModel,
            description='ID of the applet',
            destName='applet',
            level=AccessType.ADMIN
        )
        .param(
            'status',
            'true if publishing applet',
            default=True,
            required=True,
            dataType='boolean'
        )
        .errorResponse('Write access was denied for this applet.', 403)
    )
    def updateWelcomeAppletStatus(self, applet, status=True):
        thisUser = self.getCurrentUser()

        profile = ProfileModel().findOne({
            'appletId': applet['_id'],
            'userId': thisUser['_id']
        })

        if 'owner' not in profile.get('roles', []) or not thisUser.get('admin'):
            raise AccessException("You don't have enough permission to update this applet.")

        applet['meta']['welcomeApplet'] = status
        applet = self._model.setMetadata(applet, applet['meta'])

        return { 'message': 'success' }

    @access.user(scope=TokenScope.DATA_OWN)
    @autoDescribeRoute(
        Description('Set category and keywords of applet in the library.')
        .notes(
            'Use this endpoint to publish an applet in the library. <br>'
        )
        .modelParam(
            'id',
            model=AppletModel,
            description='ID of the applet',
            destName='applet',
            level=AccessType.ADMIN
        )
        .param(
            'category',
            'name of category',
            required=False,
            default=''
        )
        .param(
            'subCategory',
            'name of sub category',
            required=False,
            default=''
        )
        .jsonParam(
            'keywords',
            'list of keyword',
            required=False,
            dataType='array',
        )
        .errorResponse('Write access was denied for this applet.', 403)
    )
    def updateAppletSearch(self, applet, category='', subCategory='', keywords=[]):
        thisUser = self.getCurrentUser()

        profile = ProfileModel().findOne({
            'appletId': applet['_id'],
            'userId': thisUser['_id']
        })

        if 'manager' not in profile.get('roles', []):
            raise AccessException("You don't have enough permission to update this applet.")

        AppletLibrary().updateAppletSearch(
            applet['_id'],
            category,
            subCategory,
            keywords
        )

        return {
            'message': 'success'
        }

    @access.user(scope=TokenScope.DATA_OWN)
    @autoDescribeRoute(
        Description('Get category and keywords for an applet.')
        .notes(
            'Get category and keywords of applet in the library.'
        )
        .modelParam(
            'id',
            model=AppletModel,
            description='ID of the applet',
            destName='applet',
            level=AccessType.ADMIN
        )
    )
    def getAppletLibraryUrl(self, applet):
        thisUser = self.getCurrentUser()

        profile = ProfileModel().findOne({
            'appletId': applet['_id'],
            'userId': thisUser['_id']
        })

        if 'manager' not in profile.get('roles', []):
            raise AccessException("You don't have enough permission to view this resource.")

        libraryApplet = AppletLibrary().findOne({
            'appletId': applet['_id']
        }, fields=["_id"])

        if not libraryApplet:
            raise ValidationException('invalid applet')

        library_url = os.getenv('LIBRARY_URI') or 'localhost:8081'
        url = f'{library_url}/#/applets/{str(libraryApplet["_id"])}'
        return url

    @access.user(scope=TokenScope.DATA_OWN)
    @autoDescribeRoute(
        Description('Get  for an applet.')
        .notes(
            'Get category and keywords of applet in the library.'
        )
        .modelParam(
            'id',
            model=AppletModel,
            description='ID of the applet',
            destName='applet',
            level=AccessType.ADMIN
        )
    )
    def getAppletSearch(self, applet):
        thisUser = self.getCurrentUser()

        profile = ProfileModel().findOne({
            'appletId': applet['_id'],
            'userId': thisUser['_id']
        })

        if 'manager' not in profile.get('roles', []):
            raise AccessException("You don't have enough permission to view this resource.")

        libraryApplet = AppletLibrary().findOne({
            'appletId': applet['_id']
        }, fields=['categoryId', 'subCategoryId', 'keywords'])

        if not libraryApplet:
            raise ValidationException('invalid applet')

        return {
            'categoryId': libraryApplet['categoryId'],
            'subCategoryId': libraryApplet['subCategoryId'],
            'keywords': libraryApplet['keywords']
        }

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
        .param(
            'lang',
            'Language of response message',
            default='en',
            required=True
        )
        .jsonParam(
            'encryption',
            'encryption info',
            paramType='form',
            required=False
        )
        .errorResponse('Write access was denied for this applet.', 403)
    )
    def duplicateApplet(self, applet, name, lang='en', encryption=None):
        thisUser = self.getCurrentUser()
        accountProfile = self.getAccountProfile()

        if not accountProfile or applet['_id'] not in accountProfile.get('applets', {}).get('editor') and applet['_id'] not in accountProfile.get('applets', {}).get('manager'):
            raise AccessException(
                "Only managers and editors are able to duplicate applet."
            )

        thread = threading.Thread(
            target=AppletModel().duplicateApplet,
            kwargs={
                'applet': applet,
                'name': name,
                'editor': thisUser,
                'encryption': encryption
            }
        )
        thread.start()

        return({
            "message": t('applet_is_duplicated', lang)
        })

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
        .jsonParam(
            'encryption',
            'encryption info',
            paramType='form',
            required=False
        )
        .param(
            'themeId',
            'id of the theme to apply to this applet. Sets a logo, background image and main colors',
            paramType='string',
            default=None,
            required=False
        )
        .errorResponse('Write access was denied for this applet.', 403)
    )
    def createAppletFromProtocolData(self, protocol, email='', name=None, informant=None, encryption={}, themeId=None):
        request_guid = str(uuid.uuid4())
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
                'email': email.lower().strip(),
                'constraints': {
                    'informantRelationship': informant
                } if informant is not None else None,
                'appletRole': appletRole,
                'accountId': profile['accountId'],
                'encryption': encryption,
                'themeId': str(themeId),
                'request_guid': request_guid
            }
        )
        thread.start()
        return({
            "message": "The applet is building. We will send you an email in 10 min or less when it has been successfully created or failed.",
            "request_guid": request_guid
        })

    @access.user(scope=TokenScope.DATA_WRITE)
    @autoDescribeRoute(
        Description('Validate applet name')
        .notes(
            'This endpoint is used for validating applet name. <br>'
        )
        .param(
            'name',
            'name for new of applet which needs validation',
            default='',
            required=True
        )
    )
    def validateAppletName(self, name):
        accountProfile = AccountProfile()

        thisUser = self.getCurrentUser()
        profile = self.getAccountProfile()

        appletRole = None
        for role in ['manager', 'editor']:
            if accountProfile.hasPermission(profile, role):
                appletRole = role
                break

        if appletRole is None:
            raise AccessException("only editor/manager can use the endpoint to create new applet or edit existing applet.")

        return self._model.validateAppletName(name, CollectionModel().findOne({"name": "Applets"}), profile['accountId'])

    @access.user(scope=TokenScope.DATA_WRITE)
    @autoDescribeRoute(
        Description('Update an applet')
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
        .param(
            'themeId',
            'id of the theme to apply to this applet. Sets a logo, background image and main colors',
            paramType='string',
            default=None,
            required=False
        )
        .errorResponse('Write access was denied for this applet.', 403)
    )
    def updateAppletFromProtocolData(self, applet, name, protocol, themeId=None):
        thisUser = self.getCurrentUser()
        profile = ProfileModel().findOne({
            'appletId': applet['_id'],
            'userId': thisUser['_id']
        })

        if profile == None:
            raise ValidationException("no applet found for this combination of user and applet id")

        if 'editor' not in profile.get('roles', []) and 'manager' not in profile.get('roles', []):
            raise AccessException("You don't have enough permission to update this applet.")

        if protocol:
            AppletModel().updateAppletFromProtocolData(
                applet=applet,
                name=name,
                content=protocol,
                user=thisUser,
                accountId=applet['accountId']
            )

        # update theme
        if themeId:
            applet = AppletModel().findOne({"_id":applet['_id']})
            AppletModel().setAppletTheme(applet, themeId)

        return {
            'message': 'success'
        }

    @access.user(scope=TokenScope.DATA_WRITE)
    @autoDescribeRoute(
        Description('Update an applet')
        .notes(
            'This endpoint is used to updating visibility of activity flow. <br>'
        )
        .modelParam(
            'id',
            model=AppletModel,
            level=AccessType.READ,
            destName='applet'
        )
        .jsonParam(
            'activityFlowIds',
            'list of activity flow ids to change visibility',
            required=False,
            dataType='array',
            default=[]
        )
        .jsonParam(
            'activityIds',
            'list of activity flow ids to change visibility',
            required=False,
            dataType='array',
            default=[]
        )
        .param(
            'status',
            'show or hide activity flow',
            dataType='boolean',
            required=True,
            default=True
        )
    )
    def updateActivityVisibility(self, applet, activityFlowIds, activityIds, status):
        profile = self.getAccountProfile()

        appletRole = None
        for role in ['manager', 'coordinator', 'editor']:
            if AccountProfile().hasPermission(profile, role):
                appletRole = role
                break

        if appletRole is None:
            raise AccessException("only editor/coordinator/manager can use the endpoint to edit visibility status of activity flow.")

        self._model.updateActivityVisibility(applet, activityFlowIds, activityIds, status)

    @access.user(scope=TokenScope.DATA_WRITE)
    @autoDescribeRoute(
        Description('Create an applet.')
        .notes(
            'This endpoint is used to update applet to be edited'
        )
        .modelParam(
            'id',
            model=AppletModel,
            level=AccessType.READ,
            destName='applet'
        )
        .param(
            'thread',
            'if true, use thread for editing applet',
            required=False,
            default=True,
            dataType='boolean'
        )
        .errorResponse('Write access was denied for this applet.', 403)
    )
    def prepareAppletForEdit(self, applet, thread, params):
        thisUser = self.getCurrentUser()
        profile = ProfileModel().findOne({
            'appletId': applet['_id'],
            'userId': thisUser['_id']
        })

        if 'editor' not in profile.get('roles', []) and 'manager' not in profile.get('roles', []):
            raise AccessException("You don't have enough permission to update this applet.")

        if applet['meta']['applet'].get('editing'):
            raise AccessException("applet is being edited")

        if not thread and applet['meta']['applet'].get('largeApplet', False):
            raise ValidationException('unable to edit this applet without thread')

        applet['meta']['applet']['editing'] = True
        self._model.setMetadata(applet, applet['meta'])

        if thread:
            task = threading.Thread(
                target=AppletModel().prepareAppletForEdit,
                kwargs={
                    'applet': applet,
                    'protocol': params['protocol'].file,
                    'user': thisUser,
                    'accountId': applet['accountId'],
                    'thread': True
                }
            )
            task.start()

            return({
                "message": "The applet is building. We will send you an email in 10 min or less when it has been successfully created or failed."
            })

        AppletModel().prepareAppletForEdit(
            applet=applet,
            protocol=params['protocol'].file,
            user=thisUser,
            accountId=applet['accountId'],
            thread=False
        )

        return({
            "message": "success"
        })

    @access.user(scope=TokenScope.DATA_WRITE)
    @autoDescribeRoute(
        Description('Get all data you are authorized to see for an applet.')
        .notes(
            'This endpoint returns user\'s response data for your applet by json/csv format. <br>'
            'You\'ll need to access this endpoint only if you are owner/manager of this applet.'
        )
        .param(
            'id',
            'ID of the applet for which to fetch data',
            required=True
        )
        .param(
            'users',
            'Only retrieves responses from the given users',
            required=False,
            dataType='array',
            default=''
        )
        .jsonParam(
            'pagination',
            'pagination info - allow, pageIndex fields are available',
            required=False,
            default={}
        )
        .errorResponse('Write access was denied for this applet.', 403)
    )
    def getAppletData(self, id, users, pagination):
        from datetime import datetime
        from ..rest import setContentDisposition, setRawResponse, setResponseHeader

        thisUser = self.getCurrentUser()

        if users and isinstance(users, str):
            users = users.replace(' ', '').split(",")

        users = users if users else []
        data = AppletModel().getResponseData(id, thisUser, users, pagination)

        setContentDisposition("{}-{}.{}".format(
            str(id),
            datetime.now().isoformat(),
            'json'
        ))

        return(data)

    @access.public
    @autoDescribeRoute(
        Description('Get applet data from public id.')
        .notes(
            'This endpoint returns applet data from public id.'
        )
        .param(
            'publicId',
            'public id of applet',
            required=True
        )
        .param(
            'nextActivity',
            'id of next activity',
            default=None,
            required=False,
        )
    )
    def getAppletFromPublicLink(self, publicId, nextActivity):
        applet = self._model.findOne({
            'publicLink.id': publicId,
            'publicLink.requireLogin': False
        })

        if not applet:
            raise AccessException('unable to find applet with specified public id')

        formatted = jsonld_expander.formatLdObject(applet, 'applet', None, refreshCache=False)

        (nextIRI, data, remaining) = self._model.getNextAppletData(formatted['activities'], nextActivity, MAX_PULL_SIZE)

        if nextActivity:
            return {
                'nextActivity': nextIRI,
                **data
            }

        formatted['updated'] = applet['updated']
        formatted['accountId'] = applet['accountId']
        formatted['nextActivity'] = nextIRI

        formatted.update(data)
        return formatted

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
        Description('Request id')
        .param(
            'request_id',
            'Request id for applet creation',
            required=True
        )
    )
    def check_state(self, request_id):
        cache.create()
        value = cache.get(request_id)
        cache.stop()
        if value is None:
            return dict()
        return json.loads(value)

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
            'retrieveSchedule',
            'true if retrieve schedule info in applet metadata',
            default=False,
            required=False,
            dataType='boolean'
        )
        .param(
            'retrieveAllEvents',
            'true if retrieve all events in applet metadata',
            default=False,
            required=False,
            dataType='boolean'
        )
        .param(
            'nextActivity',
            'id of next activity',
            default=None,
            required=False,
        )
        .errorResponse('Invalid applet ID.')
        .errorResponse('Read access was denied for this applet.', 403)
    )
    def getApplet(self, applet, retrieveSchedule=False, retrieveAllEvents=False, nextActivity=None):
        user = self.getCurrentUser()
        profile = ProfileModel().findOne({
            'userId': user['_id'],
            'appletId': applet['_id']
        })

        if not applet['meta'].get('welcomeApplet') and not self._model._hasRole(applet['_id'], user, 'user'):
            raise AccessException('You don\'t have enough permission to get content of this protocol')

        formatted = jsonld_expander.formatLdObject(
            applet,
            'applet',
            user,
            refreshCache=False
        )

        (nextIRI, data, remaining) = self._model.getNextAppletData(formatted['activities'], nextActivity, MAX_PULL_SIZE)

        if nextActivity:
            return {
                'nextActivity': nextIRI,
                **data
            }

        if retrieveSchedule:
            formatted['schedule'] = self._model.getSchedule(applet, user, retrieveAllEvents)

        formatted['updated'] = applet['updated']
        formatted['accountId'] = applet['accountId']
        formatted['nextActivity'] = nextIRI
        formatted['applet']['themeId'] = applet['meta']['applet'].get('themeId')
        formatted['user'] = {
            'id': profile['_id'],
            'MRN': profile.get('MRN', ''),
            'email': profile.get('email', ''),
            'nickName': profile.get('nickName', ''),
            'firstName': profile.get('firstName', ''),
            'lastName': profile.get('lastName', ''),
            'timezone': profile.get('timezone', '')
        }
        if 'publicLink' in applet:
            formatted['applet']['publicLink'] = applet['publicLink'].get('id')
        formatted.update(data)

        return formatted

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
        .param(
            'lang',
            'Language of response message',
            default='en',
            required=True
        )
        .errorResponse('Invalid applet ID.')
        .errorResponse('Write access was denied for this applet.', 403)
    )
    def refresh(self, applet, lang='en'):
        user = self.getCurrentUser()

        if not self._model._hasRole(applet['_id'], user, 'editor'):
            raise AccessException(
                "Only editors and managers can update applet."
            )

        thread = threading.Thread(
            target=AppletModel().reloadAndUpdateCache,
            args=(applet, user)
        )

        thread.start()

        return({
            "message": t('applet_is_refreshed', lang)
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
            'nickName',
            'nickName for user',
            required=False
        )
        .param(
            'MRN',
            'MRN for user',
            default='',
            required=False
        )
        .param(
            'lang',
            'Language of mail template and web link',
            default='en',
            required=True
        )
        .jsonParam(
            'users',
            'list of user_id that reviewer can review. <br>'
            'this field will be used only if manager invites reviewer.',
            paramType='form',
            default=[],
            required=False
        )
        .errorResponse('Write access was denied for the folder or its new parent object.', 403)
    )
    @validator(schema={
        'applet': {'required': True},
        'role': {'type': 'string', 'allowed': ['user', 'coordinator', 'manager', 'editor', 'reviewer']},
        'email': {'type': 'string', 'check_with': email_validator},
        'firstName': {'type': 'string', 'check_with': symbol_validator},
        'lastName': {'type': 'string', 'check_with': symbol_validator},
        'nickName': {'type': 'string', 'check_with': symbol_validator},
        'MRN': {'type': 'string', 'check_with': symbol_validator},
        'lang': {'type': 'string', 'allowed': ['en', 'fr']},
        'users': {'type': 'list'}
    })
    def inviteUser(self, applet, role="user", email='', firstName='', lastName='', nickName='', MRN='', lang='en',users=[]):
        self.shield("inviteUser")
        from girderformindlogger.models.invitation import Invitation
        from girderformindlogger.models.profile import Profile

        email = email.lower().strip()
        if not mail_utils.validateEmailAddress(email):
            raise ValidationException(
                'invalid email', 'email'
            )
        thisUser = self.getCurrentUser()

        appletProfile = ProfileModel().findOne({'appletId': applet['_id'], 'userId': thisUser['_id']})

        if not appletProfile or ('coordinator' not in appletProfile.get('roles', []) and 'manager' not in appletProfile.get('roles', [])) or \
                (role != 'user' and role !='reviewer' and 'manager' not in appletProfile.get('roles', [])):
            raise AccessException('You don\'t have enough permission to invite other user to specified role')

        encryptedEmail = UserModel().hash(email)
        invitedUser = UserModel().findOne({'email': encryptedEmail, 'email_encrypted': True})

        if not invitedUser:
            invitedUser = UserModel().findOne({'email': email, 'email_encrypted': {'$ne': True}})

        inviterProfile = Profile().findOne({
            'appletId': applet['_id'],
            'userId': thisUser['_id'],
            'deactivated': {'$ne': True}
        })

        if role not in USER_ROLE_KEYS:
            raise ValidationException(
                'Invalid role.',
                'role'
            )

        if role == 'user':
            invitation = InvitationModel().findOne({
                'appletId': applet['_id'],
                'MRN': MRN
            })
            if invitation:
                raise ValidationException(t('mrn_is_duplicated', lang))

            invitedAccount = ProfileModel().findOne({
                'accountId': thisUser['accountId'],
                'appletId': applet['_id'],
                'roles': role,
                'MRN': MRN
            })
            if invitedAccount:
                raise ValidationException(t('mrn_is_duplicated', lang))

        invitation = Invitation().createInvitationForSpecifiedUser(
            applet=applet,
            coordinator=thisUser,
            role=role,
            user=invitedUser,
            firstName=firstName,
            lastName=lastName,
            nickName=nickName,
            lang=lang,
            MRN=MRN,
            userEmail=encryptedEmail,
            accessibleUsers=users,
        )

        web_url = os.getenv('WEB_URI') or 'localhost:8081'
        url = f'https://{web_url}/invitation/{str(invitation["_id"])}?lang={lang}'

        managers = mail_utils.htmlUserList(
            AppletModel().listUsers(applet, 'manager', force=True)
        )
        coordinators = mail_utils.htmlUserList(
            AppletModel().listUsers(applet, 'coordinator', force=True)
        )
        reviewers = mail_utils.htmlUserList(
            AppletModel().listUsers(applet, 'reviewer', force=True)
        )

        try:
            appletName = applet['meta']['applet'].get('displayName', applet.get('displayName', 'applet'))
            html = mail_utils.renderTemplate(f'userInvite.{lang}.mako', {
                'url': url,
                'userName': firstName + " " + lastName,
                'coordinatorName': thisUser['firstName'],
                'appletName': appletName,
                'MRN': MRN,
                'managers': managers,
                'coordinators': coordinators,
                'reviewers': reviewers,
                'role': role,
                'newUser': bool(invitedUser)
            })
        except KeyError:
            raise ValidationException(
                'Invalid lang parameter.',
                'lang'
            )

        mail_utils.sendMail(
            appletName + ' ' + t('invite_email_subject', lang),
            html,
            [email]
        )

        return 'sent invitation mail to {}'.format(email)


    @access.user(scope=TokenScope.DATA_WRITE)
    @autoDescribeRoute(
        Description('creates a url that users can use to add themselves directly to an applet')
        .notes(
            'creates an invite url that users can open in the browser to add themselves (i.e. create a profile) to an applet'
        )
        .modelParam(
            'id',
            model=AppletModel,
            level=AccessType.ADMIN,
            destName='applet'
        )
        .param(
            'requireLogin',
            'if true, require user to create account to take assessment',
            required=True,
            dataType='boolean',
        )
        .errorResponse('invite link already exists for this applet', 403)
    )
    def createPublicLink(self, applet, requireLogin):
        self.shield("inviteUser")

        thisUser = self.getCurrentUser()
        appletProfile = ProfileModel().findOne({'appletId': applet['_id'], 'userId': thisUser['_id']})

        if not appletProfile or ('coordinator' not in appletProfile.get('roles', []) and 'manager' not in appletProfile.get('roles', [])):
            raise AccessException('You don\'t have enough permission to create an open invitation to this applet')

        #check if a link already exists
        if 'publicLink' in applet:
            if 'id' in applet['publicLink']:
                raise ValidationException('public link already exists for this applet')

        inviteLink = self._model.createPublicLink(applet['_id'], thisUser, requireLogin)

        return {
            'inviteId': inviteLink['id'],
            'requireLogin': inviteLink.get('requireLogin', True)
        }


    @access.user(scope=TokenScope.DATA_READ)
    @autoDescribeRoute(
        Description('get an existing url that users can use to add themselves to an applet')
        .notes(
            'get the open invite url that users can open in the browser to add themselves (i.e. create a profile) to an applet'
        )
        .modelParam(
            'id',
            model=AppletModel,
            level=AccessType.ADMIN,
            destName='applet'
        )
    )
    def getPublicLink(
        self,
        applet,
    ):
        self.shield('inviteUser')

        thisUser = self.getCurrentUser()
        appletProfile = ProfileModel().findOne({'appletId': applet['_id'], 'userId': thisUser['_id']})

        if not appletProfile or ('coordinator' not in appletProfile.get('roles', []) and 'manager' not in appletProfile.get('roles', [])):
            raise AccessException('You don\'t have enough permission to view the open invitation for this applet')

        if 'publicLink' in applet:
            return {
                'inviteId': applet['publicLink']['id'],
                'requireLogin': applet['publicLink'].get('requireLogin', True)
            }

        else:
            return {}

    @access.user(scope=TokenScope.DATA_WRITE)
    @autoDescribeRoute(
        Description('replace an invite url with a new id')
        .modelParam(
            'id',
            model=AppletModel,
            level=AccessType.ADMIN,
            destName='applet'
        )
        .errorResponse('invite link already exists for this applet', 403)
    )
    def replacePublicLink(self, applet):

        self.shield("inviteUser")

        thisUser = self.getCurrentUser()
        appletProfile = ProfileModel().findOne({'appletId': applet['_id'], 'userId': thisUser['_id']})

        if not appletProfile or ('coordinator' not in appletProfile.get('roles', []) and 'manager' not in appletProfile.get('roles', [])):
            raise AccessException('You don\'t have enough permission to replace the open invitation url for this applet')

        #check if a link already exists
        if 'publicLink' not in applet:
            raise ValidationException('invite link does not exist for this applet')

        inviteLink = self._model.createPublicLink(applet['_id'], thisUser)

        return {
            'inviteId':inviteLink['id'],
            'requireLogin': applet['publicLink'].get('requireLogin', True)
        }

    @access.user(scope=TokenScope.DATA_WRITE)
    @autoDescribeRoute(
        Description('delete the open invite url for an applet')
        .modelParam(
            'id',
            model=AppletModel,
            level=AccessType.ADMIN,
            destName='applet'
        )
    )
    def deletePublicLink(self, applet):

        self.shield("inviteUser")

        thisUser = self.getCurrentUser()
        appletProfile = ProfileModel().findOne({'appletId': applet['_id'], 'userId': thisUser['_id']})

        if not appletProfile or ('coordinator' not in appletProfile.get('roles', []) and 'manager' not in appletProfile.get('roles', [])):
            raise AccessException('You don\'t have enough permission to delete the open invitation url for this applet')

        #check if a link already exists
        if 'publicLink' not in applet:
            raise ValidationException('invite link does not exist for this applet')

        response = self._model.deletePublicLink(applet['_id'], thisUser)

        return 'open invite url deleted for this applet'


    @access.user(scope=TokenScope.DATA_READ)
    @autoDescribeRoute(
        Description('allow a logged in user to add themselves to an applet via this link id')
    )
    def acceptOpenInviteLink(self, inviteLinkId):

        user = self.getCurrentUser()
        userEmail = user.get('email')

        # find applet using invite id
        applet = AppletModel().findOne({
            'publicLink.id':inviteLinkId,
            'publicLink.requireLogin': True
        })

        if not applet:
            raise ValidationException('invalid invite link')

        # check for existing profile
        existing = ProfileModel().findOne(
            {
                'appletId': applet['_id'],
                'userId': user['_id'],
                'profile': True
            },)

        if existing:

            return {}

        profile = ProfileModel().createProfile(
            applet,
            user,
            role='user')

        # append role of user to profile
        profile = ProfileModel().load(profile['_id'], force=True)
        if profile.get('roles', False):
            profile['roles'].append('user')
        else:
            profile['roles'] = ['user',]

        #randomly assign an MRN
        profile['MRN'] = uuid.uuid4()
        ProfileModel().save(profile, validate=False)
        AccountProfile().appendApplet(AccountProfile().createAccountProfile(applet['accountId'], user['_id']), applet['_id'], profile['roles'])

        return {}

    @access.public(scope=TokenScope.DATA_READ)
    @autoDescribeRoute(
        Description('use an inviteLinkId to look up and return an applets metadata')
    )
    def viewInviteLinkInfo(self, inviteLinkId):

        # find applet from invite id
        applet = AppletModel().findOne({
            'publicLink.id': inviteLinkId,
            'publicLink.requireLogin': True
        })
        if applet:
            resp = applet['meta']['applet']
        else:
            resp = {}
            raise ValidationException('invalid inviteLink id')

        # look up who created invitelink, return empty string if not found
        resp['inviter'] = ''

        try:
            creator_id = applet['publicLink']['createdBy']['_id']
        except:
            creator_id = None

        if creator_id:

            qry = {
                '_id': creator_id,
                'appletId': applet['_id']
                }
            inviter = ProfileModel().findOne(qry)

            if inviter:
                resp['inviter'] = ProfileModel().display(inviter, 'coordinator')

        # look up who has access to applet data and settings'
        admin_roles = ['manager', 'coordinator', 'reviewer']
        for role in admin_roles:

            admin_role_dict = AppletModel().listUsers(applet, role, force=True)
            resp[role] = list(admin_role_dict.values())

        return resp


    @access.user(scope=TokenScope.DATA_WRITE)
    @autoDescribeRoute(
        Description('Invite a user to a role in an applet.')
        .notes(
            'this endpoint will be used for owners to transfer ownership for an applet to another owner'
        )
        .modelParam(
            'id',
            model=AppletModel,
            level=AccessType.ADMIN,
            destName='applet'
        )
        .param(
            'email',
            'email of user who will get ownership',
            required=True
        )
    )
    def transferOwnerShip(self, applet, email):
        from girderformindlogger.models.invitation import Invitation

        accountProfile = self.getAccountProfile()
        thisUser = self.getCurrentUser()

        if applet['_id'] not in accountProfile.get('applets', {}).get('owner', []):
            raise AccessException('only owners can transfer ownership')

        if not mail_utils.validateEmailAddress(email):
            raise ValidationException(
                'invalid email', 'email'
            )

        encryptedEmail = UserModel().hash(email)
        invitedUser = UserModel().findOne({'email': encryptedEmail, 'email_encrypted': True})

        if not invitedUser:
            invitedUser = UserModel().findOne({'email': email, 'email_encrypted': {'$ne': True}})

        invitation = Invitation().createInvitationForSpecifiedUser(
            applet,
            thisUser,
            'owner',
            invitedUser,
            firstName=invitedUser['firstName'] if invitedUser else '',
            lastName=invitedUser['lastName'] if invitedUser else '',
            nickName='',
            lang='en',
            MRN='',
            userEmail=email
        )

        web_url = os.getenv('WEB_URI') or 'localhost:8082'
        url = f'https://{web_url}/invitation/{str(invitation["_id"])}'

        if invitedUser:
            html = mail_utils.renderTemplate('transferOwnerShip.mako', {
                'url': url,
                'userName': invitedUser['firstName'],
                'ownerName': thisUser['firstName'],
                'appletName': applet['meta'].get('applet', {}).get('displayName', applet.get('displayName', 'applet')),
            })
        else:
            html = mail_utils.renderTemplate('transferOwnerShipToNewUser.mako', {
                'url': url,
                'ownerName': thisUser['firstName'],
                'appletName': applet['meta'].get('applet', {}).get('displayName', applet.get('displayName', 'applet')),
            })

        mail_utils.sendMail(
            'Transfer ownership of an applet',
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
            default=False,
            dataType='boolean'
        )
        .param(
            'numberOfDays',
            'true only if get today\'s event, valid only if getAllEvents is set to false',
            required=False,
            default=0,
            dataType='integer'
        )
        .jsonParam(
            'localEvents',
            'events that user cached on local device',
            paramType='form',
            required=False,
            default=None
        )
        .errorResponse('Invalid applet ID.')
        .errorResponse('Read access was denied for this applet.', 403)
    )
    def getSchedule(self, applet, getAllEvents = False, numberOfDays = 0, localEvents=None):
        user = self.getCurrentUser()

        currentUserDate = datetime.datetime.utcnow() + datetime.timedelta(hours=int(user['timezone']))

        return self._model.getSchedule(
            applet,
            user,
            getAllEvents,
            (currentUserDate.replace(hour=0, minute=0, second=0, microsecond=0), numberOfDays) if numberOfDays and not getAllEvents else None,
            localEvents or []
        )

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

        events = schedule.get('events', [])
        assigned = {}

        for event in events:
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

        return schedule if rewrite else EventsModel().getSchedule(applet['_id'])


    # @access.user(scope=TokenScope.DATA_WRITE)
    @autoDescribeRoute(
        Description('Set or update the id of the theme to style the applet with')
        .notes(
            'this endpoint is used for setting a theme for styling an applet, usually an institutions logo and color pallete <br>'
            'only coordinator/managers are able to make request to this endpoint. <br>'
        )
        .modelParam(
            'id',
            model=AppletModel,
            level=AccessType.READ,
            destName='applet'
        )
        .param(
            'themeId',
            'objectId for the theme to assign',
            dataType='string',
            required=True
        )
        .errorResponse('Invalid applet ID.')
        .errorResponse('Read access was denied for this applet.', 403)
    )
    def setAppletTheme(self, applet, themeId):
        thisUser = self.getCurrentUser()
        #### TO DO -> if not AppletModel().isCoordinator(applet['_id'], thisUser):
        #     raise AccessException(
        #         "Only coordinators and managers can update applet themes."
        #     )

        AppletModel().setAppletTheme(applet, themeId)

        return


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
