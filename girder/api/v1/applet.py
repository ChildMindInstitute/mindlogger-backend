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
from ..describe import Description, autoDescribeRoute
from ..rest import Resource
from girder.constants import AccessType, SortDir, TokenScope
from girder.api import access
from girder.exceptions import ValidationException
from girder.models.collection import Collection as CollectionModel
from girder.models.folder import Folder as FolderModel
from girder.models.item import Item as ItemModel
from girder.models.user import User as UserModel
from girder.utility import config


class Applet(Resource):

    def __init__(self):
        super(Applet, self).__init__()
        self.resourceName = 'applet'
        self._model = FolderModel()
        # TODO: self.route('PUT', (':id'), self.deactivateActivity)
        # TODO: self.route('PUT', ('version', ':id'), self.deactivateActivity)
        # TODO: self.route('GET', (':id',), self.getApplet)
        # TODO: self.route('POST', (), self.createActivity)
        self.route('POST', (':id', 'invite'), self.invite)
        # TODO: self.route('POST', (':id', 'version'), self.createActivityVersion)
        # TODO: self.route('POST', (':id', 'copy'), self.copyActivity)
        # TODO: self.route('POST', ('version', ':id', 'copy'), self.copyActivityVersion)

    @access.user(scope=TokenScope.DATA_WRITE)
    @autoDescribeRoute(
        Description('Invite a user to a role in an applet.')
        .responseClass('Folder')
        .modelParam('id', model=FolderModel, level=AccessType.WRITE)
        .param(
            'user',
            'Applet-specific or canonical ID or email address of the user to '
            'invite. The current user is assumed if this parameter is omitted.',
            required=False,
            strip=True
        )
        .param(
            'role',
            'Role to invite this user to. One of {\'user\', \'editor\', '
            '\'manager\', \'reviewer\'}',
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
        applets = CollectionModel().createCollection(
            name="Applets",
            public=True,
            reuseExisting=True
        )
        if not str(folder['baseParentId'])==str(applets['_id']):
            raise ValidationException(
                'Invalid applet ID.'
            )
        thisUser = self.getCurrentUser()
        user = user if user else str(thisUser['_id'])
        assignments = CollectionModel().createCollection(
            name="Assignments",
            public=True,
            reuseExisting=True
        )
        appletAssignment = list(FolderModel().childFolders(
            parent=assignments,
            parentType='collection',
            user=thisUser,
            filters={
                'meta.applet.@id': str(folder['_id'])
            }
        ))
        appletAssignment = appletAssignment[0] if len(
            appletAssignment
        ) else FolderModel().setMetadata(
            FolderModel().createFolder(
                parent=assignments,
                name=str(folder['name']),
                parentType='collection',
                public=False,
                creator=thisUser,
                allowRename=True,
                reuseExisting=False
            ),
            {
                'applet': {
                    '@id': str(folder['_id'])
                }
            }
        )
        # TODO: manager, editor, viewer
        members = appletAssignment['meta'][
            'members'
        ] if 'meta' in appletAssignment and 'members' in appletAssignment[
            'meta'
        ] else {}
        return(getUserCipher(appletAssignment, user))


def canonicalUser(user):
    thisUser = Applet().getCurrentUser()
    try:
        userId = UserModel().load(
            user,
            level=AccessType.NONE,
            user=thisUser
        )
    except:
        return(None)
    try:
        return(str(userId['_id']) if '_id' in userId else None)
    except:
        return(None)


def createCipher(applet, appletAssignments, user):
    thisUser = Applet().getCurrentUser()
    cUser = None
    try:
        cUser = UserModel().load(
            user,
            level=AccessType.NONE,
            user=thisUser
        )['_id']
    except:
        cur_config = config.getConfig()
        if not re.match(cur_config['users']['email_regex'], user):
            raise ValidationException('Invalid email address.', 'user')

    newCipher = FolderModel().createFolder(
        parent=applet,
        name=nextCipher(appletAssignments),
        parentType='folder',
        public=False,
        creator=thisUser
    )
    if cUser is None:
        try:
            appletName = FolderModel().load(
                applet['meta']['applet']['@id'],
                level=AccessType.NONE,
                user=thisUser
            )['name']
        except:
            raise ValidationException('Invalid assignment folder.', 'applet')
        cUser = UserModel().createUser(
            login=appletName.replace(' ', '') + str(newCipher['name']),
            password=str(uuid.uuid4()),
            firstName=appletName,
            lastName=newCipher['name'],
            email=user,
            admin=False,
            public=False,
            currentUser=thisUser
        )['_id']
    return(cUser)
    newSecretCipher = FolderModel().setMetadata(
        FolderModel().createFolder(
            parent=newCipher,
            name='userID',
            parentType='folder',
            public=False,
            creator=cUser
        ),
        {
            'user': {
                '@id': cUser
            }
        }
    )
    return(newCipher['_id'])


def getUserCipher(applet, user):
    """
    Returns an applet-specific user ID.

    Parameters
    ----------
    applet: Mongo Folder cursor
        Applet folder in Assignments collection

    user: string
        applet-specific ID, canonical ID or email address

    Returns
    -------
    user: string
        applet-specific ID
    """
    thisUser = Applet().getCurrentUser()
    appletAssignments = list(FolderModel().childFolders(
        parent=applet,
        parentType='folder',
        user=thisUser
    ))
    allCiphers = list(itertools.chain.from_iterable([
        list(FolderModel().find(
            query={
                'parentId': assignment['_id'],
                'parentCollection': 'folder',
                'name': 'userID'
            }
        )) for assignment in appletAssignments
    ]))
    cUser = [
        u for u in [
            decipherUser(user),
            userByEmail(user),
            canonicalUser(user)
        ] if u is not None
    ]
    aUser = [
        cipher['parentId'] for cipher in allCiphers if (
            cipher['meta']['user']['@id']==cUser[0]
        )
    ] if len(cUser) else []
    aUser = aUser[0] if len(aUser) else createCipher(
        applet,
        appletAssignments,
        cUser[0] if len(cUser) else user
    )
    return(aUser)


def decipherUser(appletSpecificId):
    thisUser = Applet().getCurrentUser()
    try:
        ciphered = FolderModel().load(
            appletSpecificId,
            level=AccessType.NONE,
            user=thisUser
        )
        userId = list(FolderModel().find(
            query={
                'parentId': ciphered['_id'],
                'parentCollection': 'folder',
                'name': 'userID'
            }
        ))
    except:
        return(None)
    try:
        return(
            str(
                userId[0]['meta']['user']['@id']
            ) if len(userId) and 'meta' in userId[0] and 'user' in userId[0][
                'meta'
            ] and '@id' in userId[0]['meta']['user'] else None
        )
    except:
        return(None)


def nextCipher(currentCiphers):
    nCipher = []
    for c in [
        cipher['name'] for cipher in currentCiphers
    ]:
        try:
            nCipher.append(int(c))
        except:
            nCipher.append(0)
    return(str(max(nCipher)+1))


def userByEmail(email):
    try:
        userId = list(UserModel().find(
            query={
                'email': email
            }
        ))
    except:
        return(None)
    try:
        return(
            str(
                userId[0]['_id']
            ) if len(userId) and '_id' in userId[0] else None
        )
    except:
        return(None)
