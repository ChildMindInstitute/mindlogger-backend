# -*- coding: utf-8 -*-
import copy
import datetime
import json
import os
import re

import six

from bson.objectid import ObjectId
from girderformindlogger import events
from girderformindlogger.constants import AccessType
from girderformindlogger.exceptions import ValidationException, GirderException
from girderformindlogger.models.model_base import AccessControlledModel, Model
from girderformindlogger.models.applet_library import AppletLibrary
from girderformindlogger.models.profile import Profile as AppletProfile
from girderformindlogger.models.response_folder import ResponseItem
from girderformindlogger.exceptions import AccessException, ValidationException
from girderformindlogger.utility.model_importer import ModelImporter
from girderformindlogger.constants import USER_ROLES
from bson import json_util
from pymongo import ASCENDING, DESCENDING

class EntryModel(AccessControlledModel):
    """
    collection for managing account profiles
    """

    def initialize(self):
        self.name = 'entries'
        self.ensureIndices(
            (
                'appletId',
                'userId',
                'profileId',
                'caseUserId',
                'caseId'
            )
        )

    def validate(self, document):
        if not document.get('caseId'):
            raise ValidationException('caseId is not defined', 'caseId')
        return document

    def addEntry(self, applet, userId, entryType, caseId, caseUserId, responder):
        profile = AppletProfile().findOne({ 'appletId': applet['_id'], 'userId': ObjectId(userId) })

        activities = applet['meta']['protocol'].get('activities')

        entry = self.findOne({
            'caseId': ObjectId(caseId),
            'appletId': applet['_id'],
            'userId': ObjectId(userId),
            'entryType': entryType
        })

        if not entry:
            entry = {}
        elif entry.get('active'):
            raise ValidationException('entry already exists')

        entry.update({
            'caseId': ObjectId(caseId),
            'appletId': applet['_id'],
            'userId': userId,
            'profileId': profile['_id'] if profile else None,
            'entryType': entryType,
            'completed_activities': [
                {
                    'activity_id': activityId,
                    'completed_time': None
                } for activityId in activities
            ],
            'created': datetime.datetime.now(),
            'caseUserId': ObjectId(caseUserId),
            'responder': responder,
            'active': True
        })

        return self.save(entry)

    def deleteEntry(self, entry, deleteResponse):
        if deleteResponse:
            self.removeWithQuery({
                '_id': entry['_id']
            })

            # delete responses associated with entry
            ResponseItem().removeWithQuery(
                query={
                    "baseParentType": 'user',
                    "baseParentId": entry['userId'],
                    "meta.applet.@id": entry['appletId'],
                    "meta.case.entryId": entry['_id'],
                }
            )
        else:
            self.update({
                '_id': entry['_id']
            }, {
                '$set': {
                    'active': False,
                    'deleted': datetime.datetime.now()
                }
            })

    def getEntryData(self, entry):
        lastUpdated = None

        count = 0
        for activity in entry['completed_activities']:
            if activity['completed_time']:
                count = count + 1

                if not lastUpdated or lastUpdated < activity['completed_time']:
                    lastUpdated = activity['completed_time']

        status = 'not_started'

        if count == len(entry['completed_activities']):
            status = 'completed'
        elif count > 0:
            status = 'in_progress'

        return {
            '_id': entry['_id'],
            'profileId': entry['profileId'],
            'caseUserId': entry['caseUserId'],
            'appletId': entry['appletId'],
            'entryType': entry['entryType'],
            'responder': entry['responder'],
            'status': status,
            'lastUpdated': lastUpdated
        }

    def getEntries(self, caseId, applets):
        entries = self.find({
            'caseId': ObjectId(caseId),
            'appletId': {
                '$in': applets
            },
            'active': True
        })

        result = []

        for entry in entries:
            result.append(self.getEntryData(entry))

        return result
