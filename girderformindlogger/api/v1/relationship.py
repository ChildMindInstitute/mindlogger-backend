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
from girderformindlogger.constants import AccessType, DEFINED_INFORMANTS,         \
    DEFINED_RELATIONS, TokenScope
from girderformindlogger.exceptions import AccessException

class Relationship(Resource):
    """API Endpoint for relationships."""

    def __init__(self):
        super(Relationship, self).__init__()
        self.resourceName = 'relationship'
        self.route('GET', (), self.getDefinedRelations)
        self.route('GET', ('informant',), self.getDefinedReports)

    @access.public(scope=TokenScope.USER_INFO_READ)
    @autoDescribeRoute(
        Description('Get all currently-defined relationships.')
        .errorResponse()
    )
    def getDefinedRelations(self):
        """
        Get all currently-defined relationships.
        """
        return(DEFINED_RELATIONS)

    @access.public(scope=TokenScope.USER_INFO_READ)
    @autoDescribeRoute(
        Description('Get all currently-defined relationships.')
        .errorResponse()
    )
    def getDefinedReports(self):
        """
        Get all currently-defined informant-subject reporting relationships.
        """
        return(["{}-report".format(r) for r in DEFINED_INFORMANTS.keys()])
