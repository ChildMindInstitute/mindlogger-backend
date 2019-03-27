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
from girder.utility import ziputil
from girder.constants import AccessType, TokenScope
from girder.exceptions import RestException
from girder.api import access
from girder.models.file import File
from girder.models.folder import Folder
from girder.models.item import Item as ItemModel


class Screen(Resource):

    def __init__(self):
        super(Screen, self).__init__()
        self.resourceName = 'screen'
        self._model = ItemModel()

        # TODO: self.route('PUT', (':id',), self.deactivateScreen)
        self.route('GET', (':id',), self.getScreen)
        # TODO: self.route('GET', (':id', 'files'), self.getFiles)
        # TODO: self.route('GET', (':id', 'download'), self.download)
        # TODO: self.route('POST', (), self.createScreen)
        # TODO: self.route('POST', (':id', 'copy'), self.copyScreen)

    @access.public(scope=TokenScope.DATA_READ)
    @autoDescribeRoute(
        Description('Get a screen by ID.')
        .responseClass('Item')
        .modelParam('id', model=ItemModel, level=AccessType.READ)
        .errorResponse('ID was invalid.')
        .errorResponse('Read access was denied for the screen.', 403)
    )
    def getScreen(self, item):
        screen = item
        return (
            screen['meta'] if 'meta' in screen else screen
        )
