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
from girderformindlogger.api import access
from girderformindlogger.api.v1.protocol import Protocol
from girderformindlogger.constants import AccessType, TokenScope
from girderformindlogger.models.protocol import Protocol as ProtocolModel

class ActivitySet(Protocol):

    def __init__(self):
        super(ActivitySet, self).__init__()
        self.resourceName = 'activity_set'
        self._model = ProtocolModel()
        self.route('GET', (), self.getActivitySetFromURL)
        self.route('GET', (':id',), self.getActivitySet)


    @access.user(scope=TokenScope.DATA_READ)
    @autoDescribeRoute(
        Description(
            '~~Get a protocol by ID.~~ Deprecated. Use '
            '[`GET /protocol/{id}`](#!/protocol/protocol_getProtocol) instead.'
        )
        .modelParam('id', model=ProtocolModel, level=AccessType.READ)
        .errorResponse('Invalid protocol ID.')
        .errorResponse('Read access was denied for this protocol.', 403)
        .deprecated()
    )
    def getActivitySet(self, folder):
        return(Protocol().getProtocol(folder))


    @access.user(scope=TokenScope.DATA_READ)
    @autoDescribeRoute(
        Description(
            '~~Get a protocol by URL.~~ Deprecated. Use '
            '[`GET /protocol`](#!/protocol/protocol_getProtocolFromURL) '
            'instead.'
        )
        .param('url', 'URL of protocol.', required=True)
        .errorResponse('Invalid protocol URL.')
        .errorResponse('Read access was denied for this protocol.', 403)
        .deprecated()
    )
    def getActivitySetFromURL(self, url):
        return(Protocol().getProtocolFromURL(url))
