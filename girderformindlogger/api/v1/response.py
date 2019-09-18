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
from girderformindlogger.utility import ziputil
from girderformindlogger.constants import AccessType, TokenScope
from girderformindlogger.exceptions import AccessException, RestException, ValidationException
from girderformindlogger.api import access
from girderformindlogger.models.activity import Activity as ActivityModel
from girderformindlogger.models.applet import Applet as AppletModel
from girderformindlogger.models.assignment import Assignment as AssignmentModel
from girderformindlogger.models.folder import Folder
from girderformindlogger.models.response_folder import ResponseFolder as ResponseFolderModel, ResponseItem as ResponseItemModel
from girderformindlogger.models.roles import getCanonicalUser, getUserCipher
from girderformindlogger.models.user import User as UserModel
from girderformindlogger.models.upload import Upload as UploadModel
from girderformindlogger.utility.resource import listFromString
import itertools
import tzlocal


class ResponseItem(Resource):

    def __init__(self):
        super(ResponseItem, self).__init__()
        self.resourceName = 'response'
        self._model = ResponseItemModel()
        self.route('GET', (), self.getResponses)
        self.route('GET', ('last7Days', ':applet'), self.getLast7Days)
        self.route('POST', (':applet', ':activity'), self.createResponseItem)

    """
    TODO 🚧:
        '…, applet, and/or activity. '
        'Parameters act as cumulative filters, so mutually '
        'exclusive combinations will return an empty Array; called without '
        'any parameters returns all responses to which the logged-in user '
        'has access.'
        .param(
            'subject',
            'The ID (canonical or applet-specific) of the subject about whom '
            'to get responses or an Array thereof.',
            required=False
        )
        .param(
            'activity',
            'The ID of the activity for which to get responses or an Array '
            'thereof.',
            required=False
        )
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
            'Get all responses for a given user.'
        )
        .param(
            'informant',
            'The ID (canonical or applet-specific) of the informant for whom '
            'to get responses or an Array thereof.',
            required=False
        )
        .param(
            'applet',
            'The ID of the applet for which to get responses or an Array '
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
        informant=[],
        subject=[],
        applet=[],
        activity=[],
        screen=[]
    ):
        reviewer = self.getCurrentUser()
        allResponses = []
        try:
            informant = listFromString(informant)
            informants = list(set([cu for cu in
                [
                    getCanonicalUser(u) for u in informant
                ] if cu is not None
            ]))
            informants = informants if len(informants) else [
                u['_id'] for u in list(UserModel().search(user=reviewer))
            ]
        except:
            raise ValidationException(
                'Invalid parameter',
                'informant'
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
                'Invalid parameter',
                'subject'
            )
        try:
            applets = [
                str(a['_id']) for a in [
                    AppletModel().load(
                        id=a,
                        force=True
                    ) for a in listFromString(applet)
                ] if a.get('_id')
            ]
        except:
            raise ValidationException(
                'Invalid parameter',
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
                'Invalid parameter',
                'activity'
            )
        try:
            screens = listFromString(screen)
        except:
            raise ValidationException(
                'Invalid parameter',
                'screen'
            )
        del informant, subject, applet, activity, screen
        for informant in informants:
            allResponses += _getUserResponses(
                reviewer=reviewer,
                informant=informant
            )
        allResponses = [
            r for r in allResponses if isinstance(r, dict) and any(
                [
                    str(r.get(
                        'meta',
                        {}
                    ).get(
                        'applet',
                        {}
                    ).get('@id') if isinstance(
                        r.get(
                            'meta',
                            {}
                        ).get(
                            'applet',
                            {}
                        ),
                        dict
                    ) else r.get(
                        'meta',
                        {}
                    ).get(
                        'applet',
                        {}
                    ) if isinstance(
                        r.get(
                            'meta',
                            {}
                        ),
                        dict
                    ) else r.get('meta'))==str(applet) for applet in applets
                ]
            )
        ] if len(applets) else allResponses
        return(allResponses)

    @access.public(scope=TokenScope.DATA_READ)
    @autoDescribeRoute(
        Description(
            'Get the last 7 days\' responses for the current user.'
        )
        .param(
            'applet',
            'The ID of the Applet this response is to.'
        )
        .param(
            'subject',
            'The ID of the Subject this response is about.',
            required=False
        )
        .param(
            'referenceDate',
            'Final date of 7 day range. (Not plugged in yet).',
            required=False
        )
        .errorResponse('ID was invalid.')
        .errorResponse(
            'Read access was denied for this applet for this user.',
            403
        )
    )
    def getLast7Days(
        self,
        applet,
        subject=None,
        referenceDate=None
    ):
        from girderformindlogger.utility.response import last7Days
        user = self.getCurrentUser()
        return(last7Days(applet, user.get('_id'), user, referenceDate))



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
        .param(
            'pending',
            'Boolean, is this response in-progress rather than complete. '
            '(_not yet implemented_)',
            required=False, default=False)
        .jsonParam('metadata',
                   'A JSON object containing the metadata keys to add.',
                   paramType='form', requireObject=True, required=True)
        .errorResponse()
        .errorResponse('Write access was denied on the parent folder.', 403)
    )
    def createResponseItem(self, applet, activity, metadata, subject_id, pending, params):
        import threading
        from girderformindlogger.utility.response import aggregateAndSave
        # TODO: pending
        metadata['applet'] = {
            "@id": applet.get('_id'),
            "name": AppletModel().preferredName(applet),
            "url": applet.get(
                'url',
                applet.get('meta', {}).get('applet', {}).get('url')
            )
        }
        metadata['activity'] = {
            "@id": activity.get('_id'),
            "name": ActivityModel().preferredName(activity),
            "url": activity.get(
                'url',
                activity.get('meta', {}).get('activity', {}).get('url')
            )
        }
        informant = self.getCurrentUser()
        subject_id = subject_id if subject_id else str(
            informant['_id']
        )

        # subject_id = [
        #     getUserCipher(
        #         appletAssignment=assignment,
        #         user=subject_id
        #     ) for assignment in appletAssignments
        # ][0]
        try:
            subject_info = Folder().load(
                id=subject_id,
                user=informant,
                level=AccessType.READ
            )
        except AccessException:
            subject_info = {}
        metadata['subject'] = subject_info.get('meta', {}) if isinstance(
            subject_info,
            dict
        ) else {}
        metadata['subject']['@id'] = subject_id
        now = datetime.now(tzlocal.get_localzone())
        appletName=AppletModel().preferredName(applet)
        UserResponsesFolder = ResponseFolderModel().load(
            user=informant,
            reviewer=informant,
            force=True
        )
        UserAppletResponsesFolder = Folder().createFolder(
            parent=UserResponsesFolder, parentType='folder',
            name=appletName, reuseExisting=True, public=False)
        AppletSubjectResponsesFolder = Folder().createFolder(
            parent=UserAppletResponsesFolder, parentType='folder',
            name=subject_id, reuseExisting=True, public=False)
        try:
            newItem = self._model.createResponseItem(
                folder=AppletSubjectResponsesFolder,
                name=now.strftime("%Y-%m-%d-%H-%M-%S-%Z"), creator=informant,
                description="{} response on {} at {}".format(
                    Folder().preferredName(activity),
                    now.strftime("%Y-%m-%d"),
                    now.strftime("%H:%M:%S %Z")
                ), reuseExisting=False)
        except:
            raise ValidationException(
                "Couldn't find activity name for this response"
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

        if not pending:
            # create a Thread to calculate and save aggregates
            agg = threading.Thread(target=aggregateAndSave, args=(newItem, informant))
            agg.start()
            newItem['readOnly'] = True
        return(newItem)

def save():
    return(lambda x: x)


def _getUserResponses(
    reviewer,
    informant
):
    """
    Gets a list of a given User's `Responses/{Applet}/{subject}` Folders if the
    logged-in user has access to that folder, else returns an empty list.

    Parameters
    ----------
    reviewer: UserModel
        the logged-in user

    informant: str
        canonical user ID

    Returns
    -------
    allResponses: list of Items or empty list
    """
    try:
        informant = UserModel().load(
            informant,
            level=AccessType.NONE,
            user=reviewer
        )
    except:
        return([])
    allResponses = []
    try:
        UserResponsesFolder = ResponseFolderModel().load(
            user=informant,
            level=AccessType.READ,
            reviewer=reviewer
        )
    except AccessException:
        UserResponsesFolder = []
    if type(UserResponsesFolder)!=list:
        UserAppletResponsesFolders = Folder().childFolders(
            parent=UserResponsesFolder, parentType='folder',
            user=reviewer)
        for appletResponsesFolder in UserAppletResponsesFolders:
            folder = Folder().load(
                id=appletResponsesFolder["_id"], user=reviewer,
                level=AccessType.READ, exc=True
            )
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
            for subjectFolder in subjectFolders:
                allResponses += list(Folder().childItems(
                    folder=subjectFolders[subjectFolder], user=reviewer
                ))

        return(allResponses)
    else:
        return([])
