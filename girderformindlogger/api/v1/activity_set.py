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
from girderformindlogger.constants import AccessType, SortDir, TokenScope, SPECIAL_SUBJECTS
from girderformindlogger.api import access
from girderformindlogger.exceptions import AccessException, ValidationException
from girderformindlogger.models.activitySet import ActivitySet as ActivitySetModel
from girderformindlogger.models.applet import Applet as AppletModel
from girderformindlogger.models.collection import Collection as CollectionModel
from girderformindlogger.models.folder import Folder as FolderModel
from girderformindlogger.models.item import Item as ItemModel
from girderformindlogger.models.roles import getCanonicalUser, getUserCipher
from girderformindlogger.models.user import User as UserModel
from girderformindlogger.utility import config, jsonld_expander


class ActivitySet(Resource):

    def __init__(self):
        super(ActivitySet, self).__init__()
        self.resourceName = 'activity_set'
        self._model = ActivitySetModel()
        self.route('GET', (), self.getActivitySetFromURL)
        self.route('GET', (':id',), self.getActivitySet)


    @access.user(scope=TokenScope.DATA_READ)
    @autoDescribeRoute(
        Description('Get an activity set by ID.')
        .modelParam('id', model=ActivitySetModel, level=AccessType.READ)
        .errorResponse('Invalid activity set ID.')
        .errorResponse('Read access was denied for this activity set.', 403)
    )
    def getActivitySet(self, folder):
        activitySet = folder
        user = ActivitySet().getCurrentUser()
        return(
            jsonld_expander.formatLdObject(
                activitySet,
                'activitySet',
                user
            )
        )


    @access.user(scope=TokenScope.DATA_READ)
    @autoDescribeRoute(
        Description('Get an activitty set by URL.')
        .param('url', 'URL of activity set.', required=True)
        .errorResponse('Invalid activity set URL.')
        .errorResponse('Read access was denied for this activity set.', 403)
    )
    def getActivitySetFromURL(self, url):
        thisUser=self.getCurrentUser()
        return(jsonld_expander.formatLdObject(
            ActivitySetModel().importUrl(url, thisUser),
            'activitySet',
            thisUser
        ))
