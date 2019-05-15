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
from ast import literal_eval
from girder.api import access
from girder.constants import TokenScope
from girder.exceptions import ValidationException
from girder.models.collection import Collection as CollectionModel
from girder.models.folder import Folder as FolderModel
import itertools


class Context(Resource):
    """API Endpoint for folders."""

    def __init__(self):
        super(Context, self).__init__()
        self.resourceName = 'context'
        self._model = FolderModel()
        self.route('GET', (), self.getContext)

    @access.public(scope=TokenScope.DATA_READ)
    @autoDescribeRoute(
        Description('Get JSON-LD Context for this Mindlogger Database.')
        .errorResponse()
    )
    def getContext(self):
        """
        Get a list of folders with given search parameters. Currently accepted
        search modes are:

        1. Searching by parentId and parentType, with optional additional
           filtering by the name field (exact match) or using full text search
           within a single parent folder. Pass a "name" parameter or "text"
           parameter to invoke these additional filters.
        2. Searching with full text search across all folders in the system.
           Simply pass a "text" parameter for this mode.
        """
        user = self.getCurrentUser()
        collections = CollectionModel().find()
        contextFolder = list(itertools.chain.from_iterable([
            [
                folder for folder in FolderModel().childFolders(
                    parentType='collection',
                    parent=collection,
                    user=user,
                    name="JSON-LD"
                )
            ] for collection in [
                collection for collection in collections if collection[
                    'name'
                ] == "Context"
            ]
        ]))
        return (
            contextFolder[0]['meta'] if (
                len(contextFolder) and 'meta' in contextFolder[0]
            ) else contextFolder
        )
