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
from girder.exceptions import AccessException, RestException, ValidationException
from girder.api import access
from girder.api.v1.applet import getCanonicalUser
from girder.api.v1.context import listFromString
from girder.models.activity import Activity as ActivityModel
from girder.models.folder import Folder
from girder.models.item import Item as ItemModel
from girder.models.user import User as UserModel
from girder.models.upload import Upload as UploadModel
import itertools
import tzlocal


class ResponseItem(Resource):

    def __init__(self):
        super(ResponseItem, self).__init__()
        self.resourceName = 'response'
        self._model = ItemModel()
        self.route('GET', (), self.getResponses)
        self.route('POST', (), self.createResponseItem)

    """
    TODO 🚧:
        .param(
            'screen',
            'The ID of the screen for which to get responses or an Array '
            'thereof.',
            required=False
        )
    """
    @access.public(scope=TokenScope.DATA_READ)
    @autoDescribeRoute(
        Description(
            'Get all responses for a given user, applet, and/or activity. '
            'Parameters act as cumulative filters, so mutually '
            'exclusive combinations will return an empty Array.'
        )
        .param(
            'respondent',
            'The ID (canonical or applet-specific) of the respondent for whom '
            'to get responses or an Array thereof.',
            required=False
        )
        .param(
            'subject',
            'The ID (canonical or applet-specific) of the subject about whom '
            'to get responses or an Array thereof.',
            required=False
        )
        .param(
            'applet',
            'The ID of the applet for which to get responses or an Array '
            'thereof.',
            required=False
        )
        .param(
            'activity',
            'The ID of the activity for which to get responses or an Array '
            'thereof.',
            required=False
        )
        .errorResponse('ID was invalid.')
        .errorResponse(
            'Read access was denied for this applet for this user.',
            403
        )
    )
    def getResponses(
        self,
        respondent=[],
        subject=[],
        applet=[],
        activity=[],
        screen=[]
    ):
        reviewer = self.getCurrentUser()
        allResponses = []
        try:
            respondent = listFromString(respondent)
            respondents = list(set([cu for cu in
                [
                    getCanonicalUser(u) for u in respondent
                ] if cu is not None
            ]))
        except:
            raise ValidationException(
                'Invalid parameter.',
                'respondent'
            )
        try:
            subject = listFromString(subject)
            subjects = list(set([cu for cu in
                [
                    getCanonicalUser(u) for u in subject
                ] if cu is not None
            ]))
        except:
            raise ValidationException(
                'Invalid parameter.',
                'subject'
            )
        try:
            applets = listFromString(applet)
            # TODO: validate applet ID and/or URL
        except:
            raise ValidationException(
                'Invalid parameter.',
                'applet'
            )
        try:
            activities = listFromString(activity)
            activities = [
                *list(itertools.chain.from_iterable(
                    ActivityModel().listVersionId(
                        id=activity,
                        user=reviewer
                    ) for activity in activities
                ))
            ]
        except:
            raise ValidationException(
                'Invalid parameter.',
                'activity'
            )
        try:
            screens = listFromString(screen)
        except:
            raise ValidationException(
                'Invalid parameter.',
                'screen'
            )
        del respondent, subject, applet, activity, screen
        return(", ".join([str(respondents), str(subjects), str(applets), str(activities), str(screens)]))
        ## 🚧 continue from here
        for respondent in respondents:
            allResponses.append(
                *this._getUserResponses(
                    respondent=respondent,
                    subjects=subjects,
                    applets=applets,
                    activities=activities,
                    screens=screens
                )
            )
        return(allResponses)

    def _getUserResponsesFolder(self, user):
        user = UserModel().load(
            id=user, user=reviewer, level=AccessType.NONE, exc=True
        )
        UserResponsesFolder = Folder().createFolder(
            parent=user, parentType='user', name='Responses', creator=user,
            reuseExisting=True, public=False)
        return(UserResponsesFolder)


    def _getUserResponses(
        self,
        respondent,
        subjects=[],
        applets=[],
        activities=[],
        screens=[]
    ):
        UserResponsesFolder = this._getUserResponsesFolder(respondent)
        UserAppletResponsesFolders = Folder().childFolders(
            parent=UserResponsesFolder, parentType='folder',
            user=reviewer)
        allResponses = []
        for appletResponsesFolder in UserAppletResponsesFolders:
            folder = Folder().load(
                id=appletResponsesFolder["_id"], user=reviewer,
                level=AccessType.READ, exc=True
            )
            if len(subjects):
                subjectFolders = {}
                for subject in subjects:
                    subjectFolders[subject] = Folder().childFolders(
                        parent=folder, parentType='folder', user=reviewer,
                        filters={'name': str(subject)}
                    )
            else:
                subjectFolders = {
                    responseFolder[
                        'name'
                    ]: responseFolder for responseFolder in Folder(
                    ).childFolders(
                        parent=folder,
                        parentType='folder',
                        user=reviewer
                    )
                }
        if not len(applets): # don't filter by applet
            for subjectFolder in subjectFolders:
                allResponses += list(Folder().childItems(
                    folder=subjectFolders[subjectFolder], user=reviewer
                ))
        else:
            for applet in applets: # filter by applet
                try:
                    for subjectFolder in subjectFolders:
                        allResponses += list(Folder().childItems(
                            folder=subjectFolders[subjectFolder],
                            user=reviewer,
                            filters={
                                '$or': [
                                    {'meta.applet.@id': str(applet)},
                                    {'meta.applet.url': str(applet)}
                                ]
                            }
                        ))
                except:
                    pass
        for activity in activities:
            allResponses = [
                response for response in allResponses if ((
                    response.get('activity')==str(activity)
                ) or (
                    response.get('activity').get('@id')==str(activity)
                ) or (
                    response.get('activity').get('url')==str(activity)
                ))
            ]
        return(allResponses)


        folder = Folder().load(
            id=appletId, user=user, level=AccessType.NONE, exc=True
        )
        allResponses = {}
        for appletResponsesFolder in UserAppletResponsesFolders:
            if (
                (
                    'meta' in appletResponsesFolder
                ) and 'applet' in appletResponsesFolder[
                    'meta'
                ] and appletResponsesFolder[
                    'meta'
                ]['applet']['@id']==appletId
            ):
                allResponses[appletId] = []
                folder = Folder().load(
                    id=appletResponsesFolder["_id"], user=reviewer,
                    level=AccessType.READ, exc=True
                )
                subjectFolders = Folder().childFolders(
                    parent=folder, parentType='folder', user=reviewer
                )
                for subjectFolder in subjectFolders:
                    allResponses[appletId] += list(Folder().childItems(
                        folder=subjectFolder, user=reviewer
                    ))


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
    def createResponseItem(self, subject_id, metadata, params):
        informant = self.getCurrentUser()
        if 'applet' in metadata:
            applet = metadata['applet']
            appletName = Folder().preferredName(applet)
        else:
            raise ValidationException('Response to unknown applet.')
        subject_id = subject_id if subject_id is not None else str(
            informant["_id"]
        )

        now = datetime.now(tzlocal.get_localzone())

        UserResponsesFolder = Folder().createFolder(
            parent=informant, parentType='user', name='Responses',
            creator=informant, reuseExisting=True, public=False)

        UserAppletResponsesFolder = Folder().createFolder(
            parent=UserResponsesFolder, parentType='folder',
            name=appletName,
            reuseExisting=True, public=False)
        # TODO: fix above [Unknown Applet]. Let's pass an appletName
        # parameter instead.

        AppletSubjectResponsesFolder = Folder().createFolder(
            parent=UserAppletResponsesFolder, parentType='folder',
            name=subject_id, reuseExisting=True, public=False)
        try:
            newItem = self._model.createItem(
                folder=AppletSubjectResponsesFolder,
                name=now.strftime("%Y-%m-%d-%H-%M-%S-%Z"), creator=informant,
                description="{} response on {} at {}".format(
                    Folder().preferredName(metadata.get('activity')),
                    now.strftime("%Y-%m-%d"),
                    now.strftime("%H:%M:%S %Z")
                ), reuseExisting=False)
        except:
            raise ValidationException(
                "Couldn't find activity name for this response."
            )
        # for each blob in the parameter, upload it to a File under the item.
        for key, value in params.items():
            # upload the value (a blob)
            um = UploadModel()
            filename = "{}.{}".format(key, metadata['responses'][key]['type'].split('/')[-1])
            newUpload = um.uploadFromFile(value.file, metadata['responses'][key]['size'],
                                          filename, 'item', newItem, informant,
                                          metadata['responses'][key]['type'])

            # now, replace the metadata key with a link to this upload
            metadata['responses'][key] = "file::{}".format(newUpload['_id'])


        if metadata:
            newItem = self._model.setMetadata(newItem, metadata)
        return newItem
