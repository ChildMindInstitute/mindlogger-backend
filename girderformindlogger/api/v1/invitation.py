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
from girderformindlogger.models.applet import Applet as AppletModel
from girderformindlogger.models.invitation import Invitation as InvitationModel
from girderformindlogger.utility import jsonld_expander, response


class Invitation(Resource):
    """API Endpoint for schedules."""

    def __init__(self):
        super(Resource, self).__init__()
        self.resourceName = 'invitation'
        self.route('GET', (':id',), self.getInvitation)

    @access.public(scope=TokenScope.DATA_READ)
    @autoDescribeRoute(
        Description('Get schedule Array for the logged-in user.')
        .modelParam(
            'id',
            model=InvitationModel,
            level=AccessType.READ,
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
