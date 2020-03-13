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
import re
import threading
import uuid
import requests
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
from girderformindlogger.models.pushNotification import PushNotification as PushNotificationModel
from girderformindlogger.utility import config, jsonld_expander
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
        self.route('GET', (':id', 'schedule'), self.getSchedule)
        self.route('POST', (':id', 'invite'), self.invite)
        self.route('GET', (':id', 'roles'), self.getAppletRoles)
        self.route('GET', (':id', 'users'), self.getAppletUsers)
        self.route('DELETE', (':id',), self.deactivateApplet)

    @access.user(scope=TokenScope.DATA_OWN)
    @autoDescribeRoute(
        Description('Get userlist, groups & statuses.')
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
            return(AppletModel().getAppletUsers(applet, thisUser, force=True))
        else:
            raise AccessException(
                "Only coordinators and managers can see user lists."
            )

    @access.user(scope=TokenScope.DATA_WRITE)
    @autoDescribeRoute(
        Description('Assign a group to a role in an applet.')
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
        .param(
            'protocolUrl',
            'URL of Activity Set from which to create applet',
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
    def createApplet(self, protocolUrl=None, name=None, informant=None):
        thisUser = self.getCurrentUser()
        thread = threading.Thread(
            target=AppletModel().createAppletFromUrl,
            kwargs={
                'name': name,
                'protocolUrl': protocolUrl,
                'user': thisUser,
                'constraints': {
                    'informantRelationship': informant
                } if informant is not None else None
            }
        )
        thread.start()
        return({
            "message": "The applet is being created. Please check back in "
                       "several mintutes to see it. If you have an email "
                       "address associated with your account, you will receive "
                       "an email when your applet is ready."
        })

    @access.user(scope=TokenScope.DATA_WRITE)
    @autoDescribeRoute(
        Description('Get all data you are authorized to see for an applet.')
        .param(
            'id',
            'ID of the applet for which to fetch data',
            required=True
        )
        .param(
            'format',
            'JSON or CSV',
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
        .modelParam('id', model=AppletModel, level=AccessType.WRITE)
        .errorResponse('Invalid applet ID.')
        .errorResponse('Write access was denied for this applet.', 403)
    )
    def deactivateApplet(self, folder):
        applet = folder
        user = Applet().getCurrentUser()
        applet['meta']['applet']['deleted'] = True
        applet = AppletModel().setMetadata(applet, applet.get('meta'), user)
        if applet.get('meta', {}).get('applet', {}).get('deleted')==True:
            message = 'Successfully deactivated applet {} ({}).'.format(
                AppletModel().preferredName(applet),
                applet.get('_id')
            )
            thread = threading.Thread(
                target=AppletModel().updateAllUserCaches(applet, user)
            )
        else:
            message = 'Could not deactivate applet {} ({}).'.format(
                AppletModel().preferredName(applet),
                applet.get('_id')
            )
            Description().errorResponse(message, 403)
        return(message)

    @access.user(scope=TokenScope.DATA_READ)
    @autoDescribeRoute(
        Description('Get an applet by ID.')
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

    @access.user(scope=TokenScope.DATA_READ)
    @autoDescribeRoute(
        Description('Get associated groups for a given role and applet ID.')
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
        thread = threading.Thread(
            target=AppletModel().updateUserCacheAllUsersAllRoles,
            args=(applet, thisUser)
        )
        thread.start()
        return(applet)

    @access.user(scope=TokenScope.DATA_READ)
    @autoDescribeRoute(
        Description('Get schedule information for an applet.')
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
    def getSchedule(self, applet, refreshCache=False):
        user = self.getCurrentUser()
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

        model = AppletModel()
        filterRequired = model._hasRole(applet['_id'], user, 'user') if not model.isCoordinator(applet['_id'], user) else False
        schedule = model.filterScheduleEvents(
            applet.get('meta', {}).get('applet', {}).get('schedule', {}),
            user,
            filterRequired
        )

        return schedule

    @access.user(scope=TokenScope.DATA_WRITE)
    @autoDescribeRoute(
        Description('Set or update schedule information for an applet.')
        .modelParam(
            'id',
            model=AppletModel,
            level=AccessType.READ,
            destName='applet'
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
    def setSchedule(self, applet, schedule, **kwargs):
        thisUser = self.getCurrentUser()
        if not AppletModel().isCoordinator(applet['_id'], thisUser):
            raise AccessException(
                "Only coordinators and managers can update applet schedules."
            )
        if 'events' in schedule:
            for event in schedule['events']:
                if 'data' in event and 'useNotifications' in event['data'] and event['data'].get('useNotifications', None):
                    sendTime = '09:00'
                    if event['data'].get('notifications', None) and event['data']['notifications'][0]['start']:
                        sendTime = event['data']['notifications'][0]['start']

                    # in case of sigle event with exact year, month, day
                    if 'year' in event['schedule'] and 'month' in event['schedule'] and 'dayOfMonth' in event['schedule']:
                        sendTime = (str(event['schedule']['year'][0]) + '/' +
                                    ('0' + str(event['schedule']['month'][0] + 1))[-2:] + '/' +
                                    ('0' + str(event['schedule']['dayOfMonth'][0]))[-2:] + ' ' +
                                    sendTime)
                        existNotification = PushNotificationModel().findOne(query={'applet':applet['_id'],
                                                                                    'creator_id':thisUser['_id'],
                                                                                    'sendTime':str(sendTime)})
                        if not existNotification:
                            PushNotificationModel().createNotification( applet['_id'], 1,
                                                                        event['data']['title'], event['data']['description'],
                                                                        str(sendTime), thisUser['_id'])

                    # in case of daily event

        appletMeta = applet['meta'] if 'meta' in applet else {'applet': {}}
        if 'applet' not in appletMeta:
            appletMeta['applet'] = {}
        appletMeta['applet']['schedule'] = schedule
        AppletModel().setMetadata(applet, appletMeta)
        thread = threading.Thread(
            target=AppletModel().updateUserCacheAllUsersAllRoles,
            args=(applet, thisUser)
        )
        thread.start()
        return(appletMeta)


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
