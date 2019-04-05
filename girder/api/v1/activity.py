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
from girder.constants import AccessType, SortDir, TokenScope
from girder.api import access
from girder.models.folder import Folder as FolderModel
from girder.models.item import Item as ItemModel


class Activity(Resource):

    def __init__(self):
        super(Activity, self).__init__()
        self.resourceName = 'activity'
        self._model = FolderModel()
        # TODO: self.route('PUT', (':id'), self.deactivateActivity)
        # TODO: self.route('PUT', ('version', ':id'), self.deactivateActivity)
        self.route('GET', (':id',), self.getActivity)
        self.route('GET', ('version', ':id'), self.getActivityVersion)
        # TODO: self.route('POST', (), self.createActivity)
        # TODO: self.route('POST', (':id', 'version'), self.createActivityVersion)
        # TODO: self.route('POST', (':id', 'copy'), self.copyActivity)
        # TODO: self.route('POST', ('version', ':id', 'copy'), self.copyActivityVersion)

    @access.public(scope=TokenScope.DATA_READ)
    @autoDescribeRoute(
        Description('Get a screen by ID.')
        .responseClass('Folder')
        .modelParam('id', model=FolderModel, level=AccessType.READ)
        .errorResponse('ID was invalid.')
        .errorResponse('Read access was denied for the activity.', 403)
    )
    def getActivity(self, folder):
        user = self.getCurrentUser()
        activity = folder
        activityVersion = self._model.childFolders(
            parentType='folder',
            parent=activity,
            user=user,
            sort=[('created', SortDir.DESCENDING)],
            limit=1
        )[0] # get latest version
        return (activityVersion.get('meta', activityVersion))

    @access.public(scope=TokenScope.DATA_READ)
    @autoDescribeRoute(
        Description('Get a screen by ID.')
        .responseClass('Folder')
        .modelParam('id', model=FolderModel, level=AccessType.READ)
        .errorResponse('ID was invalid.')
        .errorResponse('Read access was denied for the activity.', 403)
    )
    def getActivityVersion(self, folder):
        activityVersion = folder
        return (activityVersion.get('meta', activityVersion))
