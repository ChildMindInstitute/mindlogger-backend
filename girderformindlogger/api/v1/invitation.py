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
from ..rest import Resource, rawResponse
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
        self.route('GET', (':id', 'qr'), self.getQR)
        self.route('DELETE', (':id',), self.declineInvitation)

    @access.public(scope=TokenScope.USER_INFO_READ)
    @autoDescribeRoute(
        Description('Get an invitation by ID.')
        .modelParam(
            'id',
            model=InvitationModel,
            force=True,
            destName='invitation'
        )
        .param(
            'fullHTML',
            'Return a full HTML document rather than just the body?',
            required=False,
            dataType='boolean'
        )
        .param(
            'includeLink',
            'Include a link to the invitation on MindLogger web?',
            required=False,
            dataType='boolean'
        )
        .errorResponse()
    )
    @rawResponse
    def getInvitation(self, invitation, fullHTML=False, includeLink=True):
        """
        Get an invitation as a string.
        """
        currentUser = self.getCurrentUser()
        return(InvitationModel().htmlInvitation(
            invitation,
            currentUser,
            fullDoc=fullHTML,
            includeLink=includeLink if includeLink is not None else True
        ))

    @access.public(scope=TokenScope.USER_INFO_READ)
    @autoDescribeRoute(
        Description('Get a link to an invitation by QR code.')
        .modelParam(
            'id',
            model=InvitationModel,
            force=True,
            destName='invitation'
        )
        .errorResponse()
    )
    def getQR(self, invitation):
        """
        Get a link to an invitation, either as a url string or as a QR code.
        """
        import qrcode
        from girderformindlogger.api.rest import getApiUrl

        try:
            apiUrl = getApiUrl()
        except GirderException:
            import cherrypy
            from girderformindlogger.utiltiy import config

            apiUrl = "/".join([
                cherrypy.url(),
                config.getConfig()['server']['api_root']
            ])

        apiUrl = "?".join([
            "/".join([
                apiUrl,
                'invitation',
                str(invitation['_id'])
            ]),
            'fullHTML=true'
        ])

        img = qrcode.make(apiUrl)
        return(img.show(title=apiUrl))

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
        return(InvitationModel().acceptInvitation(invitation, currentUser))

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
            force=True,
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
        InvitationModel().remove(invitation)
        return("Successfully deleted invitation.")
