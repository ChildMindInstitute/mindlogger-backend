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

import tzlocal
import pytz
from datetime import timedelta, timezone

from ..describe import Description, autoDescribeRoute
from ..rest import Resource
from datetime import datetime
from girderformindlogger.constants import AccessType, TokenScope
from girderformindlogger.exceptions import AccessException, ValidationException
from girderformindlogger.api import access
from girderformindlogger.models.activity import Activity as ActivityModel
from girderformindlogger.models.applet import Applet as AppletModel
from girderformindlogger.models.folder import Folder
from girderformindlogger.models.response_folder import ResponseFolder as \
    ResponseFolderModel, ResponseItem as ResponseItemModel
from girderformindlogger.models.response_tokens import ResponseTokens
from girderformindlogger.models.item import Item as ItemModel
from girderformindlogger.models.response_alerts import ResponseAlerts
from girderformindlogger.models.upload import Upload as UploadModel
from girderformindlogger.models.note import Note as NoteModel
from bson import json_util
from pymongo import DESCENDING
from bson import ObjectId
import boto3
import os
import string
import random
import base64
import io

DEFAULT_REGION = 'us-east-1'

class ResponseItem(Resource):

    def __init__(self):
        super(ResponseItem, self).__init__()
        self.resourceName = 'response'
        self.s3_client = boto3.client('s3', region_name=DEFAULT_REGION, aws_access_key_id=os.environ['ACCESS_KEY_ID'],
                                 aws_secret_access_key=os.environ['SECRET_ACCESS_KEY'])
        self._model = ResponseItemModel()
        self.route('GET', (':applet',), self.getResponsesForApplet)
        self.route('GET', ('last7Days', ':applet'), self.getLast7Days)
        self.route('POST', (':applet', ':activity'), self.createResponseItem)
        self.route('POST', (':applet', 'updateResponseToken'), self.updateResponseToken)
        self.route('PUT', (':applet',), self.updateReponseHistory)

        self.route('POST', (':applet', 'note'), self.addNote)
        self.route('PUT', (':applet', 'note'), self.updateNote)
        self.route('GET', (':applet', 'notes'), self.getNotes)
        self.route('DELETE', (':applet', 'note'), self.deleteNote)

    @access.public(scope=TokenScope.DATA_READ)
    @autoDescribeRoute(
        Description(
            'Add note for user\'s response.'
        )
        .modelParam(
            'applet',
            model=AppletModel,
            level=AccessType.READ,
            destName='applet',
            description='The ID of applet.'
        )
        .param(
            'noteId',
            'id of note to delete',
            required=True
        )
    )
    def deleteNote(self, applet, noteId):
        from girderformindlogger.models.profile import Profile
        thisUser = self.getCurrentUser()

        if not thisUser:
            raise AccessException('permission denied')

        reviewerProfile = Profile().findOne({
            'appletId': ObjectId(applet['_id']),
            'userId': thisUser['_id'],
            'roles': {
                '$in': ['reviewer', 'manager']
            },
            'deactivated': {'$ne': True}
        })

        if not reviewerProfile:
            raise AccessException('permission denied')

        NoteModel().deleteNote(noteId)

    @access.public(scope=TokenScope.DATA_READ)
    @autoDescribeRoute(
        Description(
            'Add note for user\'s response.'
        )
        .modelParam(
            'applet',
            model=AppletModel,
            level=AccessType.READ,
            destName='applet',
            description='The ID of applet.'
        )
        .param(
            'responseId',
            'Only retrieves responses for the given activities',
            required=True
        )
        .param(
            'note',
            'content of note',
            required=False
        )
    )
    def addNote(self, applet, responseId, note):
        from girderformindlogger.models.profile import Profile

        thisUser = self.getCurrentUser()

        reviewerProfile = Profile().findOne({
            'appletId': ObjectId(applet['_id']),
            'userId': thisUser['_id'],
            'roles': {
                '$in': ['reviewer', 'manager']
            },
            'deactivated': {'$ne': True}
        })

        if not reviewerProfile:
            raise AccessException('permission denied')

        responseItem = self._model.findOne({'_id': ObjectId(responseId)})

        if not responseItem:
            raise AccessException('unable to find response with specified id')

        return NoteModel().addNote(
            appletId=applet['_id'],
            responseId=responseId,
            userProfileId=responseItem['meta'].get('subject', {}).get('@id'),
            note=note,
            reviewer=reviewerProfile
        )

    @access.public(scope=TokenScope.DATA_READ)
    @autoDescribeRoute(
        Description(
            'Update note for user\'s response.'
        )
        .modelParam(
            'applet',
            model=AppletModel,
            level=AccessType.READ,
            destName='applet',
            description='The ID of applet.'
        )
        .param(
            'noteId',
            'id of note that user have written in the past',
            required=True
        )
        .param(
            'note',
            'updated content of note',
            required=True
        )
    )
    def updateNote(self, applet, noteId, note):
        from girderformindlogger.models.profile import Profile
        thisUser = self.getCurrentUser()

        reviewerProfile = Profile().findOne({
            'appletId': ObjectId(applet['_id']),
            'userId': thisUser['_id'],
            'roles': {
                '$in': ['reviewer', 'manager']
            },
            'deactivated': {'$ne': True}
        })

        if not reviewerProfile:
            raise AccessException('permission denied')

        return NoteModel().updateNote(
            noteId=noteId,
            note=note,
            reviewer=reviewerProfile
        )

    @access.public(scope=TokenScope.DATA_READ)
    @autoDescribeRoute(
        Description(
            'Update note for user\'s response.'
        )
        .modelParam(
            'applet',
            model=AppletModel,
            level=AccessType.READ,
            destName='applet',
            description='The ID of applet.'
        )
        .param(
            'responseId',
            'id of response',
            required=True
        )
    )
    def getNotes(self, applet, responseId):
        from girderformindlogger.models.profile import Profile

        thisUser = self.getCurrentUser()

        if not thisUser:
            raise AccessException('permission denied')

        reviewerProfile = Profile().findOne({
            'appletId': ObjectId(applet['_id']),
            'userId': thisUser['_id'],
            'roles': {
                '$in': ['reviewer', 'manager']
            },
            'deactivated': {'$ne': True}
        })

        if not reviewerProfile:
            raise AccessException('permission denied')

        notes = NoteModel().getNotes(
            responseId=responseId,
            reviewer=reviewerProfile
        )

        return notes


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
        from girderformindlogger.models.account_profile import AccountProfile
        from girderformindlogger.utility.response import (
            delocalize, add_latest_daily_response, getOldVersions)

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
            'items': {},
            'subScaleSources': {},
            'subScales': {},
            'tokens': {
                'cumulativeToken': [],
                'tokenUpdates': [],
            },
        }

        # Get the responses for each users and generate the group responses data.
        owner_account = AccountProfile().findOne({
            'applets.owner': applet.get('_id')
        })
        if owner_account and owner_account.get('db', None):
            self._model.reconnectToDb(db_uri=owner_account.get('db', None))

        for user in users:
            responses = self._model.find(
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
                            hours=user["timezone"] if 'timezone' not in response['meta']['subject'] else response['meta']['subject']['timezone']
                        )
                    )
                )

            tokens = ResponseTokens().getResponseTokens(user, retrieveUserKeys=True)

            add_latest_daily_response(data, responses, tokens)

        self._model.reconnectToDb()

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
            'startDate',
            'start date for response data.',
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
        .jsonParam(
            'localItems',
            'item id array which represents historical items that user has on local device.',
            required=False,
            default=[]
        )
        .jsonParam(
            'localActivities',
            'activity id array which represents historical activities that user has on local device.',
            required=False,
            default=[]
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
        startDate=None,
        includeOldItems=True,
        groupByDateActivity=True,
        localItems=[],
        localActivities=[]
    ):
        from girderformindlogger.utility.response import last7Days
        from bson.objectid import ObjectId

        try:
            appletInfo = AppletModel().findOne({'_id': ObjectId(applet)})
            user = self.getCurrentUser()

            return(last7Days(
                applet,
                appletInfo,
                user.get('_id'),
                user,
                startDate=startDate,
                includeOldItems=includeOldItems,
                groupByDateActivity=groupByDateActivity,
                localItems=localItems,
                localActivities=localActivities
            ))
        except:
            import sys, traceback
            print(sys.exc_info())
            print(traceback.print_tb(sys.exc_info()[2]))
            return({})

    @access.public(scope=TokenScope.DATA_WRITE)
    @autoDescribeRoute(
        Description('Use Response token.')
        .notes(
            'This endpoint is used when a user selects token-prize on mobile app.'
        )
        .modelParam(
            'applet',
            model=AppletModel,
            level=AccessType.READ,
            destName='applet',
            description='The ID of the Applet this response is to.'
        )
        .jsonParam('updateInfo',
                   'A JSON object containing the token update and cumulative.',
                   paramType='form', requireObject=True, required=True)
    )
    def updateResponseToken(
        self,
        applet,
        updateInfo
    ):
        from girderformindlogger.models.profile import Profile
        user = self.getCurrentUser()

        profile = Profile().findOne({
            'appletId': applet['_id'],
            'userId': user['_id']
        })

        if updateInfo.get('tokenUpdate', None):
            ResponseTokens().saveResponseToken(
                profile,
                updateInfo['tokenUpdate'],
                False,
                updateInfo.get('userPublicKey', None),
                updateInfo.get('version', None)
            )

        if updateInfo.get('cumulative', None):
            ResponseTokens().saveResponseToken(
                profile,
                updateInfo['cumulative'],
                True,
                updateInfo.get('userPublicKey', None)
            )

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
        from girderformindlogger.models.account_profile import AccountProfile
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

            owner_account = AccountProfile().findOne({
                'applets.owner': applet.get('_id')
            })

            if owner_account and owner_account.get('db', None):
                self._model.reconnectToDb(db_uri=owner_account.get('db', None))

            try:
                newItem = self._model.createResponseItem(
                    folder=AppletSubjectResponsesFolder,
                    name=now.strftime("%Y-%m-%d-%H-%M-%S-%Z"),
                    creator=informant,
                    description="{} response on {} at {}".format(
                        Folder().preferredName(activity),
                        now.strftime("%Y-%m-%d"),
                        now.strftime("%H:%M:%S %Z")
                    ), reuseExisting=False
                )
            except:
                raise ValidationException(
                    "Couldn't find activity name for this response"
                )

            # for each blob in the parameter, upload it to a File under the item.
            for key, value in params.items():
                # upload the value (a blob)
                um = UploadModel()
                filename = "{}.{}".format(
                    ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(10)),
                    metadata['responses'][key]['type'].split('/')[-1]
                )
                _file_obj_key=f"{ObjectId(profile['_id'])}/{ObjectId(applet['_id'])}/{ObjectId(activity['_id'])}/{filename}"

                file_data=base64.b64decode(value)

                self.s3_client.upload_fileobj(io.BytesIO(file_data),os.environ['S3_MEDIA_BUCKET'],_file_obj_key)

                # newUpload = um.uploadFromFile(
                #     value.file,
                #     metadata['responses'][key]['size'],
                #     filename,
                #     'item',
                #     newItem,
                #     informant,
                #     metadata['responses'][key]['type'],
                # )
                value={}
                value['filename']=filename
                value['fromLibrary']=False
                value['size']=metadata['responses'][key]['size']
                value['type']=metadata['responses'][key]['type']
                value['uri']="s3://{}/{}".format(os.environ['S3_MEDIA_BUCKET'],_file_obj_key)
                # now, replace the metadata key with a link to this upload
                metadata['responses'][key]['value'] = value
                del metadata['responses'][key]['size']
                del metadata['responses'][key]['type']

            if metadata:
                if metadata.get('dataSource', None):
                    for item in metadata.get('responses', {}):
                        metadata['responses'][item] = {
                            'src': newItem['_id'],
                            'ptr': metadata['responses'][item]
                        }

                if metadata.get('subScaleSource', None):
                    for subScale in metadata.get('subScales', {}):
                        metadata['subScales'][subScale] = {
                            'src': newItem['_id'],
                            'ptr': metadata['subScales'][subScale]
                        }

                if metadata.get('tokenCumulation', None):
                    ResponseTokens().saveResponseToken(profile, metadata['tokenCumulation'], True, metadata.get('userPublicKey', None))

                if metadata.get('alerts', []):
                    alerts = metadata.get('alerts', [])

                    for alert in alerts:
                        ResponseAlerts().addResponseAlerts(
                            profile,
                            alert['id'],
                            alert['schema'],
                            alert['message']
                        )

                newItem = self._model.setMetadata(newItem, metadata)

            if not pending:
                newItem['readOnly'] = True
            #self._model.reconnectToDb()

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

            data['updated'] = now
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
        .param(
            'user',
            'profile id for user',
            required=False,
            default=None
        )
        .jsonParam('responses',
                   'A JSON object containing the new response data and public key.',
                   paramType='form', requireObject=True, required=True)
        .errorResponse()
        .errorResponse('Write access was denied on the parent folder.', 403)
    )
    def updateReponseHistory(self, applet, user, responses):
        from girderformindlogger.models.profile import Profile
        from girderformindlogger.models.account_profile import AccountProfile

        if not user:
            user = self.getCurrentUser()
            profile = Profile().findOne({
                'appletId': applet['_id'],
                'userId': user['_id']
            })
        else:
            profile = Profile().findOne({
                '_id': ObjectId(user),
                'appletId': applet['_id']
            })

        if not profile:
            raise ValidationException('unable to find user with specified id')

        is_manager = 'manager' in profile.get('roles', [])

        now = datetime.utcnow()

        owner_account = AccountProfile().findOne({
            'applets.owner': applet.get('_id')
        })

        if owner_account and owner_account.get('db', None):
            self._model.reconnectToDb(db_uri=owner_account.get('db', None))

        for responseId in responses['dataSources']:
            query = {
                "meta.applet.@id": applet['_id'],
                "_id": ObjectId(responseId)
            }
            if not is_manager:
                query["meta.subject.@id"] = profile['_id']

            self._model.update(
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

        responseTokenModel = ResponseTokens()

        for tokenUpdateId in responses['tokenUpdates']:
            query = {
                'appletId': applet['_id'],
                '_id': ObjectId(tokenUpdateId),
                'userId': profile['userId']
            }

            tokenUpdate = responseTokenModel.findOne(query)
            tokenUpdate.update({
                'data': responses['tokenUpdates'][tokenUpdateId],
                'userPublicKey': responses['userPublicKey'],
                'updated': now
            })

            responseTokenModel.save(tokenUpdate)

        self._model.reconnectToDb()

        if profile.get('refreshRequest', None):
            profile.pop('refreshRequest')
            Profile().save(profile, validate=False)

        return ({
            "message": "responses are updated successfully."
        })

def save():
    return(lambda x: x)
