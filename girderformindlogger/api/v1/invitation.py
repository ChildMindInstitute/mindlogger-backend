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

from ..describe import Description, autoDescribeRoute
from ..rest import Resource
from girderformindlogger.api import access
from girderformindlogger.constants import AccessType, TokenScope
from girderformindlogger.exceptions import AccessException
from girderformindlogger.models.applet import Applet as AppletModel
from girderformindlogger.models.invitation import Invitation as InvitationModel
from girderformindlogger.models.token import Token
from girderformindlogger.models.user import User as UserModel
from girderformindlogger.utility import jsonld_expander, response


class Invitation(Resource):
    """API Endpoint for schedules."""

    def __init__(self):
        super(Resource, self).__init__()
        self.resourceName = 'invitation'
        self.route('GET', (':id',), self.getInvitation)
        self.route('GET', (':id', 'accept'), self.acceptInvitationByToken)
        self.route('POST', (':id', 'accept'), self.acceptInvitation)
        self.route('DELETE', (':id', 'remove'), self.declineInvitation)

    @access.public(scope=TokenScope.USER_INFO_READ)
    @autoDescribeRoute(
        Description('Get an invitation by ID.')
        .modelParam(
            'id',
            model=InvitationModel,
            force=True,
            destName='invitation'
        )
        .errorResponse()
    )
    def getInvitation(self, invitation):
        """
        Get a link to an invitation, either as a url string or as a QR code.
        """
        currentUser = self.getCurrentUser()
        return(InvitationModel().htmlInvitation(invitation, currentUser))

    @access.public(scope=TokenScope.USER_INFO_READ)
    @autoDescribeRoute(
        Description('Accept an invitation.')
        .modelParam(
            'id',
            model=InvitationModel,
            force=True,
            destName='invitation'
        )
        .errorResponse()
    )
    def acceptInvitation(self, invitation):
        """
        Accept an invitation.
        """
        currentUser = self.getCurrentUser()
        if currentUser is None:
            raise AccessException(
                "You must be logged in to accept an invitation."
            )
        Invitation().acceptInvitation(invitation, currentUser)
        return(InvitationModel().htmlInvitation(invitation, currentUser))

    @access.public(scope=TokenScope.USER_INFO_READ)
    @autoDescribeRoute(
        Description('Accept an invitation by token.')
        .modelParam(
            'id',
            model=InvitationModel,
            force=True,
            destName='invitation'
        )
        .param(
            'token',
            'Authentication token to link user to invitation.',
            required=True
        )
        .errorResponse()
    )
    def acceptInvitationByToken(self, invitation, token):
        """
        Accept an invitation.
        """
        currentUser = Token().load(
            token,
            force=True,
            objectId=False,
            exc=False
        ).get('userId')
        if currentUser is not None:
            currentUser = UserModel().load(currentUser, force=True)
        if currentUser is None:
            raise AccessException(
                "You must be logged in to accept an invitation."
            )
        return(InvitationModel().acceptInvitation(invitation, currentUser))


    @access.public(scope=TokenScope.USER_INFO_READ)
    @autoDescribeRoute(
        Description('Decline an invitation.')
        .modelParam(
            'id',
            model=InvitationModel,
            level=AccessType.WRITE,
            destName='invitation'
        )
        .errorResponse()
    )
    def declineInvitation(self, invitation):
        """
        Decline an invitation.
        """
        currentUser = self.getCurrentUser()
        if currentUser is None:
            raise AccessException(
                "You must be logged in to accept an invitation."
            )
        if not any([
            AppletModel().isCoordinator(invitation['appletId'], currentUser)
        ]):
            pass
        return(InvitationModel().htmlInvitation(invitation, currentUser))
