#!/usr/bin/env python
# -*- coding: utf-8 -*-

###############################################################################
#  Copyright 2019 Child Mind Institute MATTER Lab
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
from datetime import datetime
from girder.utility import ziputil
from girder.constants import AccessType, TokenScope
from girder.exceptions import RestException
from girder.api import access
from girder.models.folder import Folder
from girder.models.item import Item as ItemModel
import tzlocal


class ResponseItem(Resource):

    def __init__(self):
        super(ResponseItem, self).__init__()
        self.resourceName = 'response'
        self._model = ItemModel()
        self.route('POST', (), self.createResponseItem)


    @access.user(scope=TokenScope.DATA_WRITE)
    @filtermodel(model=ItemModel)
    @autoDescribeRoute(
        Description('Create a new user response item.')
        .responseClass('Item')
        .jsonParam('metadata',
                   'A JSON object containing the metadata keys to add. Requires'
                   ' the following keys: ["applet", "activity"], each of which'
                   ' takes an Object for its value.',
                   paramType='form', requireObject=True, required=True)
        .param('subject_id', 'The ID of the user that is the subject.',
               required=False, default=None)
        .errorResponse()
        .errorResponse('Write access was denied on the parent folder.', 403)
    )
    def createResponseItem(self, subject_id, metadata):
        informant = self.getCurrentUser()
        subject_id = subject_id if subject_id is not None else str(
            informant["_id"]
        )
        now = datetime.now(tzlocal.get_localzone())
        UserResponsesFolder = Folder().createFolder(
            parent=informant, parentType='user', name='Responses',
            reuseExisting=True, public=False)
        UserAppletResponsesFolder = Folder().createFolder(
            parent=UserResponsesFolder, parentType='folder',
            name=metadata["applet"]["@id"] if (
                "applet" in metadata and "@id" in metadata["applet"]
            ) else metadata["applet"]["name"] if (
                "applet" in metadata and "skos:prefLabel" in metadata["applet"]
            ) else metadata["applet"]["skos:prefLabel"] if (
                "applet" in metadata and "name" in metadata["applet"]
            ) else metadata["applet"] if (
                "applet" in metadata and type(
                    metadata["applet"]
                ) == str
            ) else "[Unknown Applet]",
            reuseExisting=True, public=False)
        AppletSubjectResponsesFolder = Folder().createFolder(
            parent=UserAppletResponsesFolder, parentType='folder',
            name=subject_id, reuseExisting=True, public=False)
        newItem = self._model.createItem(
            folder=AppletSubjectResponsesFolder,
            name=now.strftime("%Y-%m-%d-%H-%M-%S-%Z"), creator=informant,
            description="{} response on {} at {}".format(
                (
                    metadata["activity"]["@id"] if (
                        "activity" in metadata and "@id" in metadata["activity"]
                    ) else metadata["activity"]["name"] if (
                        "activity" in metadata and "skos:prefLabel" in metadata[
                            "activity"
                        ]
                    ) else metadata["activity"]["skos:prefLabel"] if (
                        "activity" in metadata and "name" in metadata["activity"]
                    ) else metadata["activity"] if (
                        "activity" in metadata and type(
                            metadata["activity"]
                        ) == str
                    ) else "[Unknown Activity]"
                ),
                now.strftime("%Y-%m-%d"),
                now.strftime("%H:%M:%S %Z")
            ), reuseExisting=False)
        if metadata:
            newItem = self._model.setMetadata(newItem, metadata)
        return newItem
