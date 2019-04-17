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
from girder.api.v1.applet import getCanonicalUser, getUserCipher
from girder.api.v1.context import listFromString
from girder.models.activity import Activity as ActivityModel
from girder.models.applet import Applet as AppletModel
from girder.models.assignment import Assignment as AssignmentModel
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
        self.route('POST', (':applet', ':activity'), self.createResponseItem)

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
            respondents = respondents if len(respondents) else [
                u['_id'] for u in list(UserModel().search(user=reviewer))
            ]
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
        for respondent in respondents:
            allResponses += _getUserResponses(
                reviewer=reviewer,
                respondent=respondent,
                subjects=subjects,
                applets=applets,
                activities=activities,
                screens=screens
            )
        return(allResponses)


    @access.user(scope=TokenScope.DATA_WRITE)
    @autoDescribeRoute(
        Description('Create a new user response item.')
        #.responseClass('Item')
        .modelParam(
            'applet',
            model=AppletModel,
            level=AccessType.READ,
            destName='applet',
            description='The ID of the Applet this response is to.'
        )
        .modelParam(
            'activity',
            model=ActivityModel,
            level=AccessType.READ,
            destName='activity',
            description='The ID of the Activity this response is to.'
        )
        .param('subject_id', 'The ID (canonical or applet-specific) of the '
               'user that is the subject.',
               required=False, default=None)
        .jsonParam('metadata',
                   'A JSON object containing the metadata keys to add.',
                   paramType='form', requireObject=True, required=True)
        .errorResponse()
        .errorResponse('Write access was denied on the parent folder.', 403)
    )
    def createResponseItem(self, applet, activity, metadata, subject_id, params):
        informant = self.getCurrentUser()
        subject_id = subject_id if subject_id else str(
            informant['_id']
        )
        return(AssignmentModel().findAssignments(applet['_id']))
        return(AssignmentModel().load(
            id=applet['_id'],
            user=informant,
            level=AccessType.READ
        ))
        subject_id = getUserCipher(
            applet=AssignmentModel().load(
                id=applet['_id'],
                user=informant,
                level=AccessType.READ
            ),
            user=subject_id
        )
        return(subject_id)
        now = datetime.now(tzlocal.get_localzone())

        UserResponsesFolder = Folder().createFolder(
            parent=informant, parentType='user', name='Responses',
            creator=informant, reuseExisting=True, public=False)

        UserAppletResponsesFolder = Folder().createFolder(
            parent=UserResponsesFolder, parentType='folder',
            name=appletName,
            reuseExisting=True, public=False)

        AppletSubjectResponsesFolder = Folder().createFolder(
            parent=UserAppletResponsesFolder, parentType='folder',
            name=subject_id, reuseExisting=True, public=False)
        try:
            newItem = self._model.createItem(
                folder=AppletSubjectResponsesFolder,
                name=now.strftime("%Y-%m-%d-%H-%M-%S-%Z"), creator=informant,
                description="{} response on {} at {}".format(
                    Folder().preferredName(activity),
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
            filename = "{}.{}".format(
                key,
                metadata['responses'][key]['type'].split('/')[-1]
            )
            newUpload = um.uploadFromFile(
                value.file,
                metadata['responses'][key]['size'],
                filename,
                'item',
                newItem,
                informant,
                metadata['responses'][key]['type']
            )
            # now, replace the metadata key with a link to this upload
            metadata['responses'][key] = "file::{}".format(newUpload['_id'])

        if metadata:
            newItem = self._model.setMetadata(newItem, metadata)
        return newItem


def _getUserResponsesFolder(reviewer, user):
    """
    Gets a given User's `Responses` folder if the logged-in user has access
    to that folder, else returns None.

    Parameters
    ----------
    reviewer: UserModel
        the logged-in user

    user: string
        canonical ID

    Returns
    -------
    UserResponsesFolder: Folder or None
    """
    try:
        user = UserModel().load(
            id=user, user=reviewer, level=AccessType.NONE, exc=True
        )
        if reviewer['_id']==user['_id']:
            UserResponsesFolder = Folder().createFolder(
                parent=user, parentType='user', name='Responses',
                creator=user, reuseExisting=True, public=False)
        else:
            UserResponsesFolder = Folder().load(
                id=Folder().findOne({
                    parent: user,
                    parentType: 'user',
                    name: 'Responses'
                }).get('_id'),
                user=reviewer,
                level=AccessType.READ
            )
        return(UserResponsesFolder)
    except:
        return(None)


def _getUserResponses(
    reviewer,
    respondent,
    subjects=[],
    applets=[],
    activities=[],
    screens=[]
):
    """
    Gets a given User's `Responses` folder if the logged-in user has access
    to that folder, else returns None.

    Parameters
    ----------
    reviewer: UserModel
        the logged-in user

    respondent: str
        canonical user ID

    subjects: list
        list of strings, canonical user IDs

    applets: list
        list of strings, applet IDs

    activities: list
        list of strings, activity IDs

    screens: list
        list of strings, screen IDs

    Returns
    -------
    allResponses: list of Items or empty list
    """
    UserResponsesFolder = _getUserResponsesFolder(reviewer, respondent)
    if UserResponsesFolder is not None:
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
    else:
        return([])


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
