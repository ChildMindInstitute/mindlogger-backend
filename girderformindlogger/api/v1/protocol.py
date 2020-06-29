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
from girderformindlogger.constants import AccessType, SortDir, TokenScope,     \
    SPECIAL_SUBJECTS
from girderformindlogger.api import access
from girderformindlogger.exceptions import AccessException, ValidationException
from girderformindlogger.models.protocol import Protocol as ProtocolModel
from girderformindlogger.models.applet import Applet as AppletModel
from girderformindlogger.models.collection import Collection as CollectionModel
from girderformindlogger.models.folder import Folder as FolderModel
from girderformindlogger.models.item import Item as ItemModel
from girderformindlogger.models.roles import getCanonicalUser, getUserCipher
from girderformindlogger.models.user import User as UserModel
from girderformindlogger.models.account_profile import AccountProfile
from girderformindlogger.utility import config, jsonld_expander
from bson import json_util


class Protocol(Resource):

    def __init__(self):
        super(Protocol, self).__init__()
        self.resourceName = 'protocol'
        self._model = ProtocolModel()
        self.route('GET', (), self.getProtocolFromURL)
        self.route('GET', (':id',), self.getProtocol)

    @access.user(scope=TokenScope.DATA_READ)
    @autoDescribeRoute(
        Description('Get a protocol by ID.')
        .modelParam('id', model=ProtocolModel, level=AccessType.READ)
        .errorResponse('Invalid protocol ID.')
        .errorResponse('Read access was denied for this protocol.', 403)
    )
    def getProtocol(self, folder):
        try:
            protocol = folder
            user = self.getCurrentUser()
            return(
                jsonld_expander.formatLdObject(
                    protocol,
                    'protocol',
                    user
                )
            )
        except:
            import sys, traceback
            print(sys.exc_info())
            return({traceback.print_tb(sys.exc_info()[2])})


    @access.user(scope=TokenScope.DATA_READ)
    @autoDescribeRoute(
        Description('Get a protocol by URL.')
        .param('url', 'URL of protocol.', required=True)
        .errorResponse('Invalid protocol URL.')
        .errorResponse('Read access was denied for this protocol.', 403)
    )
    def getProtocolFromURL(self, url):
        try:
            thisUser=self.getCurrentUser()
            return(jsonld_expander.formatLdObject(
                ProtocolModel().importUrl(url, thisUser),
                'protocol',
                thisUser
            ))
        except:
            import sys, traceback
            print(sys.exc_info())
            return({traceback.print_tb(sys.exc_info()[2])})

