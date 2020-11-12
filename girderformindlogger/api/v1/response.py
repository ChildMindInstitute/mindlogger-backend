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

import itertools
import tzlocal
import pytz
from datetime import date, datetime, timedelta, timezone
from bson.objectid import ObjectId

from ..describe import Description, autoDescribeRoute
from ..rest import Resource, filtermodel, setResponseHeader, \
    setContentDisposition
from datetime import datetime
from girderformindlogger.utility import ziputil
from girderformindlogger.constants import AccessType, TokenScope
from girderformindlogger.exceptions import AccessException, RestException, \
    ValidationException
from girderformindlogger.api import access
from girderformindlogger.models.activity import Activity as ActivityModel
from girderformindlogger.models.applet import Applet as AppletModel
from girderformindlogger.models.assignment import Assignment as AssignmentModel
from girderformindlogger.models.folder import Folder
from girderformindlogger.models.response_folder import ResponseFolder as \
    ResponseFolderModel, ResponseItem as ResponseItemModel
from girderformindlogger.models.roles import getCanonicalUser, getUserCipher
from girderformindlogger.models.user import User as UserModel
from girderformindlogger.models.upload import Upload as UploadModel
from girderformindlogger.utility.response import formatResponse, \
    string_or_ObjectID
from girderformindlogger.utility.resource import listFromString
from pymongo import ASCENDING, DESCENDING
from bson import ObjectId
import hashlib



class ResponseItem(Resource):

    def __init__(self):
        super(ResponseItem, self).__init__()
        self.resourceName = 'response'
        self._model = ResponseItemModel()
        self.route('GET', (':applet',), self.getResponsesForApplet)
        self.route('GET', ('last7Days', ':applet'), self.getLast7Days)
        self.route('POST', (':applet', ':activity'), self.createResponseItem)
        self.route('PUT', (':applet',), self.updateReponseItems)

    @access.user(scope=TokenScope.DATA_READ)
    @autoDescribeRoute(
        Description(
            'Get all responses for a given applet.'
        )
        .modelParam(
            'applet',
            model=AppletModel,
            level=AccessType.READ,
            destName='applet',
            description='The ID of the applet'
        )
        .jsonParam(
            'users',
            'List of profile IDs. If given, it only retrieves responses from the given users',
            required=False,
            dataType='array',
        )
        .param(
            'activities',
            'Only retrieves responses for the given activities',
            required=False
        )
        .param(
            'fromDate',
            'Date for the oldest entry to retrieve',
            required=False,
            dataType='dateTime',
        )
        .param(
            'toDate',
            'Date for the newest entry to retrieve',
            required=False,
            dataType='dateTime',
        )
        .param(
            'includeOldItems',
            'true if retrieve old items in the response data',
            dataType='boolean',
            required=False,
            default=True
        )
        .errorResponse('ID was invalid.')
        .errorResponse(
            'Read access was denied for this applet for this user.',
            403
        )
    )
    def getResponsesForApplet(
        self,
        applet=None,
        users=[],
        activities=[],
        fromDate=None,
        toDate=None,
        includeOldItems=True,
    ):
        from girderformindlogger.models.profile import Profile
        from girderformindlogger.utility.response import (
            delocalize, add_missing_dates, add_latest_daily_response, getOldVersions)

        user = self.getCurrentUser()
        profile = Profile().findOne({'appletId': applet['_id'],
                                     'userId': user['_id']})
        is_reviewer = AppletModel()._hasRole(applet['_id'], user, 'reviewer')
        is_manager = AppletModel()._hasRole(applet['_id'], user, 'manager')
        is_owner = applet['creatorId'] == user['_id']

        assert is_reviewer or is_manager or is_owner,  'you don\'t have access to the requested resource'

        if toDate is None:
            # Default toTime is today.
            toDate = delocalize(datetime.now(tzlocal.get_localzone()))
        else:
            # Make sure the last day is included.
            toDate = toDate + timedelta(days=1)

        if fromDate is None:
            # Default fromTime is one month ago.
            fromDate = delocalize(toDate - timedelta(days=30))

        if not users:
            # Retrieve responses for the logged user.
            users = [profile]
        else:
            profile_ids = list(map(lambda x: ObjectId(x), users))
            users = list(Profile().find({'_id': { '$in': profile_ids }, 'reviewers': profile['_id'], 'appletId': applet['_id']}))

            if profile['_id'] in profile_ids and profile['_id'] not in profile['reviewers']:
                users.append(profile)

        # If not speciied, retrieve responses for all activities.
        if not activities:
            activities = applet['meta']['protocol']['activities']
        else:
            activities = list(map(lambda s: ObjectId(s), activities))

        data = {
            'responses': {},
            'dataSources': {},
            'keys': [],
            'items': {}
        }

        # Get the responses for each users and generate the group responses data.
        for user in users:
            responses = ResponseItemModel().find(
                query={"created": { "$lte": toDate, "$gt": fromDate },
                       "meta.applet.@id": ObjectId(applet['_id']),
                       "meta.activity.@id": { "$in": activities },
                       "meta.subject.@id": user['_id']},
                force=True,
                sort=[("created", DESCENDING)])

            # we need this to handle old responses
            for response in responses:
                response['meta']['subject']['userTime'] = response["created"].replace(tzinfo=pytz.timezone("UTC")).astimezone(
                    timezone(
                        timedelta(
                            hours=profile["timezone"] if 'timezone' not in response['meta']['subject'] else response['meta']['subject']['timezone']
                        )
                    )
                )

            add_latest_daily_response(data, responses)
        add_missing_dates(data, fromDate, toDate)

        data.update(getOldVersions(data['responses'], applet))

        return data

    @access.public(scope=TokenScope.DATA_READ)
    @autoDescribeRoute(
        Description(
            'Get the last 7 days\' responses for the current user.'
        )
        .param(
            'applet',
            description='The ID of the Applet this response is to.'
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
        .param(
            'includeOldItems',
            'true if retrieve old items in the response data',
            dataType='boolean',
            required=False,
            default=True
        )
        .param(
            'groupByDateActivity',
            'if true, group by date/activity',
            dataType='boolean',
            required=False,
            default=True
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
        referenceDate=None,
        includeOldItems=True,
        groupByDateActivity=True,
    ):
        from girderformindlogger.utility.response import last7Days
        from bson.objectid import ObjectId
        try:
            appletInfo = AppletModel().findOne({'_id': ObjectId(applet)})
            user = self.getCurrentUser()

            return(last7Days(applet, appletInfo, user.get('_id'), user, referenceDate=referenceDate, includeOldItems=includeOldItems, groupByDateActivity=groupByDateActivity))
        except:
            import sys, traceback
            print(sys.exc_info())
            print(traceback.print_tb(sys.exc_info()[2]))
            return({})



    @access.user(scope=TokenScope.DATA_WRITE)
    @autoDescribeRoute(
        Description('Create a new user response item.')
        .notes(
            'This endpoint is used when a user finishs one activity on mobile app.'
        )
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
    def createResponseItem(
        self,
        applet,
        activity,
        metadata,
        subject_id,
        pending,
        params
    ):
        from girderformindlogger.models.profile import Profile
        try:
            # TODO: pending
            metadata['applet'] = {
                "@id": applet.get('_id'),
                "name": AppletModel().preferredName(applet),
                "url": applet.get(
                    'url',
                    applet.get('meta', {}).get('applet', {}).get('url')
                ),
                "version": metadata['applet']['schemaVersion']
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

            profile = Profile().findOne({
                'appletId': applet['_id'],
                'userId': ObjectId(subject_id)
            })
            subject_id = profile.get('_id')

            print(subject_id)

            if isinstance(metadata.get('subject'), dict):
                metadata['subject']['@id'] = subject_id
            else:
                metadata['subject'] = {'@id': subject_id}

            metadata['subject']['timezone'] = profile.get('timezone', 0)

            now = datetime.now(tz=pytz.timezone("UTC"))

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
                name=str(subject_id), reuseExisting=True, public=False)

            try:
                newItem = self._model.createResponseItem(
                    folder=AppletSubjectResponsesFolder,
                    name=now.strftime("%Y-%m-%d-%H-%M-%S-%Z"),
                    creator=informant,
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
                if metadata.get('dataSource', None):
                    for item in metadata.get('responses', {}):
                        metadata['responses'][item] = {
                            'src': newItem['_id'],
                            'ptr': metadata['responses'][item]
                        }

                newItem = self._model.setMetadata(newItem, metadata)

            if not pending:
                newItem['readOnly'] = True
            print(newItem)

            # update profile activity
            profile = Profile()
            data = profile.findOne(query={
                "_id": subject_id
            })

            updated = False
            for activity in data['completed_activities']:
                if activity["activity_id"] == metadata['activity']['@id']:
                    activity["completed_time"] = now
                    updated = True

            if updated == False:
                data['completed_activities'].append({
                    "activity_id": metadata['activity']['@id'],
                    "completed_time": now
                })

            profile.save(data, validate=False)

            return(newItem)
        except:
            import sys, traceback
            print(sys.exc_info())
            print(traceback.print_tb(sys.exc_info()[2]))
            return(str(traceback.print_tb(sys.exc_info()[2])))

    @access.user(scope=TokenScope.DATA_WRITE)
    @autoDescribeRoute(
        Description('update user response items.')
        .notes(
            'This endpoint is used when user wants to update previous responses.'
        )
        .modelParam(
            'applet',
            model=AppletModel,
            level=AccessType.READ,
            destName='applet',
            description='The ID of the Applet this response is to.'
        )
        .jsonParam('responses',
                   'A JSON object containing the new response data and public key.',
                   paramType='form', requireObject=True, required=True)
        .errorResponse()
        .errorResponse('Write access was denied on the parent folder.', 403)
    )
    def updateReponseItems(self, applet, responses):
        from girderformindlogger.models.profile import Profile

        user = self.getCurrentUser()
        profile = Profile().findOne({
            'appletId': applet['_id'],
            'userId': user['_id']
        })

        is_manager = 'manager' in profile.get('roles', [])

        now = datetime.utcnow()

        for responseId in responses['dataSources']:
            query = {
                "meta.applet.@id": applet['_id'], 
                "_id": ObjectId(responseId)
            }
            if not is_manager:
                query["meta.subject.@id"] = profile['_id']

            ResponseItemModel().update(
                query,
                {
                    '$set': {
                        'meta.dataSource': responses['dataSources'][responseId],
                        'meta.userPublicKey': responses['userPublicKey'],
                        'updated': now
                    }
                }, 
                multi=False
            )

        if profile.get('refreshRequest', None):
            profile.pop('refreshRequest')
            Profile().save(profile, validate=False)

        return ({
            "message": "responses are updated successfully."
        })

def save():
    return(lambda x: x)
