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
import uuid
import requests
from ..describe import Description, autoDescribeRoute
from ..rest import Resource
from girder.constants import AccessType, SortDir, TokenScope, SPECIAL_SUBJECTS,\
    USER_ROLES
from girder.api import access
from girder.utility import loadJSON
from girder.exceptions import AccessException, ValidationException
from girder.models.applet import Applet as AppletModel, getCanonicalUser, getUserCipher
from girder.models.collection import Collection as CollectionModel
from girder.models.folder import Folder as FolderModel
from girder.models.item import Item as ItemModel
from girder.models.user import User as UserModel
from girder.utility import config, jsonld_expander


class Applet(Resource):

    def __init__(self):
        super(Applet, self).__init__()
        self.resourceName = 'applet'
        self._model = AppletModel()
        # TODO: self.route('PUT', (':id'), self.deactivateActivity)
        # TODO: self.route('PUT', ('version', ':id'), self.deactivateActivity)
        self.route('GET', (), self.getAppletFromURL)
        self.route('GET', (':id',), self.getApplet)
        # TODO: self.route('POST', (), self.createActivity)
        self.route('POST', (':id', 'invite'), self.invite)
        self.route('POST', ('invite',), self.inviteFromURL)
        # TODO: self.route('POST', (':id', 'version'), self.createActivityVersion)
        # TODO: self.route('POST', (':id', 'copy'), self.copyActivity)
        # TODO: self.route('POST', ('version', ':id', 'copy'), self.copyActivityVersion)


    @access.user(scope=TokenScope.DATA_READ)
    @autoDescribeRoute(
        Description('Get an applet by ID.')
        .modelParam('id', model=AppletModel, level=AccessType.READ)
        .errorResponse('Invalid applet ID.')
        .errorResponse('Read access was denied for this applet.', 403)
    )
    def getApplet(self, folder):
        applet = folder
        user = Applet().getCurrentUser()
        return(jsonld_expander.formatLdObject(applet, 'applet', user))


    @access.user(scope=TokenScope.DATA_READ)
    @autoDescribeRoute(
        Description('Get an applet by URL.')
        .param('url', 'URL of Applet.', required=True)
        .errorResponse('Invalid applet URL.')
        .errorResponse('Read access was denied for this applet.', 403)
    )
    def getAppletFromURL(self, url):
        thisUser=self.getCurrentUser()
        return(jsonld_expander.updateFromURL(url, 'applet', thisUser))


    @access.user(scope=TokenScope.DATA_WRITE)
    @autoDescribeRoute(
        Description('Invite a user to a role in an applet.')
        .responseClass('Folder')
        .modelParam('id', model=FolderModel, level=AccessType.READ)
        .param(
            'user',
            'Applet-specific or canonical ID or email address of the user to '
            'invite. The current user is assumed if this parameter is omitted.',
            required=False,
            strip=True
        )
        .param(
            'role',
            'Role to invite this user to. One of ' + str(USER_ROLES),
            default='user',
            required=False,
            strip=True
        )
        .param(
            'rsvp',
            'Can the invited user decline the invitation?',
            default=True,
            required=False
        )
        .param(
            'subject',
            'For \'user\' or \'reviewer\' roles, an applet-specific or '
            'cannonical ID of the subject of that informant or reviewer, an '
            'iterable thereof, or \'ALL\' or \'NONE\'. The current user is '
            'assumed if this parameter is omitted.',
            required=False
        )
        .errorResponse('ID was invalid.')
        .errorResponse('Write access was denied for the folder or its new parent object.', 403)
    )
    def invite(self, folder, user, role, rsvp, subject):
        if role not in USER_ROLES:
            raise ValidationException(
                'Invalid role.',
                'role'
            )
        applets = CollectionModel().createCollection(
            name="Applets",
            public=True,
            reuseExisting=True
        )
        if not str(folder['baseParentId'])==str(applets['_id']):
            raise ValidationException(
                'Invalid applet ID.',
                'applet'
            )
        jsonld_expander.formatLdObject(folder, 'applet', user)
        return(_invite(folder, user, role, rsvp, subject))

    @access.user(scope=TokenScope.DATA_WRITE)
    @autoDescribeRoute(
        Description('Invite a user to a role in an applet by applet URL.')
        #.responseClass('Folder')
        .param(
            'url',
            'URL of applet, eg, '
            '`https://raw.githubusercontent.com/ReproNim/schema-standardization/master/activity-sets/example/nda-phq.jsonld`',
            required=True
        )
        .param(
            'user',
            'Applet-specific or canonical ID or email address of the user to '
            'invite. The current user is assumed if this parameter is omitted.',
            required=False,
            strip=True
        )
        .param(
            'role',
            'Role to invite this user to. One of ' + str(USER_ROLES),
            default='user',
            required=False,
            strip=True
        )
        .param(
            'rsvp',
            'Can the invited user decline the invitation?',
            default=True,
            required=False
        )
        .param(
            'subject',
            'For \'user\' or \'reviewer\' roles, an applet-specific or '
            'cannonical ID of the subject of that informant or reviewer, an '
            'iterable thereof, or \'ALL\' or \'NONE\'. The current user is '
            'assumed if this parameter is omitted.',
            required=False
        )
        .errorResponse('ID was invalid.')
        .errorResponse('Write access was denied for the folder or its new parent object.', 403)
    )
    def inviteFromURL(self, url, user, role, rsvp, subject):
        if role not in USER_ROLES:
            raise ValidationException(
                'Invalid role.',
                'role'
            )
        thisUser = self.getCurrentUser()
        thisApplet = AppletModel().load(
            jsonld_expander.updateFromURL(url, 'applet', thisUser).get(
                'applet',
                {}
            ).get('_id', '').split('applet/')[-1],
            level=AccessType.READ,
            user=thisUser
        )
        return(
            _invite(
                applet=thisApplet,
                user=user,
                role=role,
                rsvp=rsvp,
                subject=subject
            )
        )

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
    thisUser = Applet().getCurrentUser()
    user = user if user else str(thisUser['_id'])
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
