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
from girderformindlogger.models.account_profile import AccountProfile
from girderformindlogger.utility import jsonld_expander, response
from bson.objectid import ObjectId
from girderformindlogger.i18n import t


class Invitation(Resource):
    """API Endpoint for invitations."""

    def __init__(self):
        super(Invitation, self).__init__()
        self.resourceName = 'invitation'
        self.route('GET', (':id',), self.getInvitation)
        self.route('GET', (':id', ':lang', 'accept'), self.acceptInvitationByToken)
        self.route('POST', (':id', 'accept'), self.acceptInvitation)
        self.route('GET', (':id', 'qr'), self.getQR)
        self.route('DELETE', (':id',), self.declineInvitation)

    @access.public(scope=TokenScope.USER_INFO_READ)
    @autoDescribeRoute(
        Description('Get an invitation by ID.')
        .notes(
            'This endpoint is used to get invitation from id. <br>'
            '(Used in the website to get invitation-html from id)'
        )
        .param(
            'id',
            'ID of invitation',
            required=True
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
    def getInvitation(self, id, fullHTML=False, includeLink=True):
        """
        Get an invitation as a string.
        """

        from girderformindlogger.models.profile import Profile

        currentUser = self.getCurrentUser()

        if not currentUser:
            raise AccessException(
                "You must be logged in to get invitation."
            )

        htmlInvitation = InvitationModel().htmlInvitation(
            id,
            currentUser,
            fullDoc=fullHTML,
            includeLink=includeLink if includeLink is not None else True
        )
        return htmlInvitation

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
        .notes(
            'This endpoint is used for logged in user to accept invitation.'
        )
        .param(
            'id',
            'ID of invitation',
            required=True
        )
        .param(
            'email',
            'email for invited user',
            default='',
            required=False
        )
        .errorResponse()
    )
    def acceptInvitation(self, id, email):
        """
        Accept an invitation.
        """
        currentUser = self.getCurrentUser()
        if currentUser is None or not email:
            raise AccessException(
                "You must be logged in to accept an invitation."
            )

        email = email.lower().strip()

        invitation = InvitationModel().findOne({ '_id': ObjectId(id) })

        if not invitation:
            return InvitationModel().getMessageForAlreadyAcceptedInvitation(
                id,
                currentUser.get("lang", "en")
            )

        if invitation.get('role', 'user') == 'owner':
            profile = AppletModel().receiveOwnerShip(AppletModel().load(invitation['appletId'], force=True), currentUser, email)
        else:
            profile = InvitationModel().acceptInvitation(invitation, currentUser, email)

            if invitation.get('role', 'user') == 'editor' or invitation.get('role', 'user') == 'manager':
                InvitationModel().accessToDuplicatedApplets(invitation, currentUser, email)

        InvitationModel().remove(invitation)

        return {
            'lang': invitation.get('lang', 'en'),
            'body': t('invitationAccepted', invitation.get('lang', 'en'))
        }


    @access.public(scope=TokenScope.USER_INFO_READ)
    @autoDescribeRoute(
        Description('Accept an invitation by token.')
        .param(
            'id',
            'ID of invitation',
            required=True
        )
        .param(
            'email',
            'email for invited user',
            default='',
            required=False
        )
        .param(
            'token',
            'Authentication token to link user to invitation.',
            required=True
        )
        .errorResponse()
    )
    def acceptInvitationByToken(self, id, lang, email, token):
        """
        Accept an invitation.
        """
        currentUser = Token().load(
            token,
            force=True,
            objectId=False,
            exc=False
        ).get('userId', None)
        if currentUser is not None:
            currentUser = UserModel().load(currentUser, force=True)
        if currentUser is None:
            raise AccessException(
                "Invalid token."
            )

        invitation = InvitationModel().findOne({ '_id': ObjectId(id) })

        if not invitation:
            return InvitationModel().getMessageForAlreadyAcceptedInvitation(
                id,
                currentUser.get("lang", "en")
            )

        if invitation.get('role', 'user') == 'owner':
            AppletModel().receiveOwnerShip(AppletModel().load(invitation['appletId'], force=True), currentUser, email)
        else:
            profile = InvitationModel().acceptInvitation(invitation, currentUser, email)

            # editors should be able to access duplicated applets
            if invitation.get('role','user') == 'editor' or invitation.get('role', 'user') == 'manager':
                InvitationModel().accessToDuplicatedApplets(invitation, currentUser, email)

        InvitationModel().remove(invitation)
        return profile

    @access.public(scope=TokenScope.USER_INFO_READ)
    @autoDescribeRoute(
        Description('Decline an invitation from id.')
        .param(
            'id',
            'ID of invitation',
            required=True
        )
        .errorResponse()
    )
    def declineInvitation(self, id):
        """
        Decline an invitation.
        """
        currentUser = self.getCurrentUser()

        invitation = InvitationModel().findOne({ '_id': ObjectId(id) })

        if not invitation:
            return InvitationModel().getMessageForAlreadyAcceptedInvitation(
                id,
                currentUser.get("lang", "en")
            )

        InvitationModel().remove(invitation)
        return {
            'lang': invitation.get('lang', 'en'),
            'body': t('invitationRemoved', invitation.get('lang', 'en'))
        }
