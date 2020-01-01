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
from ..rest import Resource, filtermodel, setResponseHeader, setContentDisposition
from girderformindlogger.utility import ziputil
from girderformindlogger.constants import AccessType, TokenScope
from girderformindlogger.exceptions import RestException
from girderformindlogger.api import access
from girderformindlogger.models.activity import Activity as ActivityModel
from girderformindlogger.models.file import File as FileModel
from girderformindlogger.models.folder import Folder as FolderModel
from girderformindlogger.models.item import Item as ItemModel
from girderformindlogger.models.screen import Screen as ScreenModel
from girderformindlogger.utility import jsonld_expander


class Screen(Resource):

    def __init__(self):
        super(Screen, self).__init__()
        self.resourceName = 'screen'
        self._model = ItemModel()

        # TODO: self.route('PUT', (':id',), self.deactivateScreen)
        self.route('GET', (':id',), self.getScreen)
        # TODO: self.route('GET', (':id', 'files'), self.getFiles)
        # TODO: self.route('GET', (':id', 'download'), self.download)
        self.route('GET', (), self.getScreenByURL)
        self.route('POST', (), self.createScreen)
        # TODO: self.route('POST', (':id', 'copy'), self.copyScreen)

    @access.public(scope=TokenScope.DATA_WRITE)
    @autoDescribeRoute(
        Description('Create a new screen.')
        .param(
            'activity',
            'ID of the parent Activity or Activity version',
            required=True
        )
        .param('screenName', 'Name for the new screen.', required=False)
        .errorResponse('ID was invalid.')
        .errorResponse('Read access was denied for the screen.', 403)
    )
    def createScreen(self, activity, screenName=None):
        thisUser = self.getCurrentUser()
        activity = ActivityModel().load(
            activity,
            level=AccessType.WRITE,
            user=thisUser
        )
        screen = ScreenModel().createScreen(
            name=screenName if screenName is not None else str(len(
                list(FolderModel().childItems(activity))
            ) + 1),
            creator=thisUser,
            folder=activity,
            reuseExisting=False
        )
        return(jsonld_expander._fixUpFormat(
            jsonld_expander.formatLdObject(screen, 'screen', thisUser)
        ))

    @access.public(scope=TokenScope.DATA_READ)
    @autoDescribeRoute(
        Description('Get a screen by ID.')
        .modelParam('id', model=ScreenModel, level=AccessType.READ)
        .errorResponse('ID was invalid.')
        .errorResponse('Read access was denied for the screen.', 403)
    )
    def getScreen(self, item):
        screen = item
        user = self.getCurrentUser()
        return (jsonld_expander._fixUpFormat(
            jsonld_expander.formatLdObject(screen, 'screen', user)
        ))


    @access.public(scope=TokenScope.DATA_READ)
    @autoDescribeRoute(
        Description(
            'Get a screen by URL.'
        )
        .responseClass('Item')
        .param('url', 'URL of Screen.', required=True)
    )
    def getScreenByURL(self, url):
        thisUser = self.getCurrentUser()
        return(jsonld_expander._fixUpFormat(
            jsonld_expander.formatLdObject(
                ScreenModel().importUrl(url=url, user=thisUser),
                'screen',
                thisUser
            )
        ))
