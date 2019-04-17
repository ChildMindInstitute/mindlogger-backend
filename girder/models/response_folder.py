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

import copy
import datetime
import json
import os
import six

from bson.objectid import ObjectId
from .folder import Folder
from .model_base import AccessControlledModel
from girder import events
from girder.constants import AccessType
from girder.exceptions import ValidationException, GirderException
from girder.utility.progress import noProgress, setResponseTimeLimit


class ResponseFolder(Folder):
    """
    Users own their own ResponseFolders.
    """

    def load(self, user, level=AccessType.ADMIN, reviewer=None, force=False):
        """
        We override load in order to ensure the folder has certain fields
        within it, and if not, we add them lazily at read time.

        :param user: The user for whom to get the ResponseFolder.
        :type id: dict
        :param reviewer: The user to check access against.
        :type user: dict or None
        :param level: The required access type for the object.
        :type level: AccessType
        :param force: If you explicitly want to circumvent access
                      checking on this resource, set this to True.
        :type force: bool
        """
        responseFolder = Folder().createFolder(
            parent=user, parentType='user', name='Responses',
            creator=reviewer, reuseExisting=True, public=False
        )
        accessList = Folder().getFullAccessList(responseFolder)
        accessList = {
            k: [
                {
                    "id": i.get('id'),
                    "level": AccessType.ADMIN if i.get('id')==str(
                        user.get('_id')
                    ) else i.get('level')
                } for i in accessList[k]
            ] for k in accessList
        }
        if str(user.get('_id')) not in [
            u.get('id') for u in accessList.get('users', [])
        ]:
            accessList.get('users').append(
                {
                    "id": str(user.get('_id')),
                    "level": AccessType.ADMIN
                }
            )
        Folder().setAccessList(responseFolder, accessList)
        return(responseFolder)
