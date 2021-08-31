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
from girderformindlogger.models.entries import EntryModel
from girderformindlogger.models.response_folder import ResponseItem
from girderformindlogger.exceptions import AccessException, ValidationException
from girderformindlogger.utility.model_importer import ModelImporter
from girderformindlogger.constants import USER_ROLES
from bson import json_util
from pymongo import ASCENDING, DESCENDING

class CaseUser(AccessControlledModel):
    """
    collection for managing account profiles
    """

    def initialize(self):
        self.name = 'caseUsers'
        self.ensureIndices(
            (
                'caseId',
                'accountId',
                'userId',
                'applets',
                'profileId'
            )
        )

    def validate(self, document):
        if not document.get('caseId'):
            raise ValidationException('caseId is not defined', 'caseId')
        return document

    def addCaseUser(self, caseId, profiles, accountId, userId, MRN):
        caseUser = self.findOne({
            'userId': ObjectId(userId),
            'caseId': ObjectId(caseId)
        })

        if not caseUser:
            caseUser = {
                'caseId': ObjectId(caseId),
                'userId': ObjectId(userId),
            }

        caseUser.update({
            'applets': [],
            'accountId': accountId,
            'MRN': MRN,
            'created': datetime.datetime.now(),
            'active': True
        })

        for profile in profiles:
            caseUser['applets'].append({
                'appletId': profile['appletId'],
                'profileId': profile['_id']
            })

        return self.save(caseUser)

    def deleteCaseUser(self, caseUser, deleteResponse):
        if deleteResponse:
            self.removeWithQuery({
                '_id': caseUser['_id'],
                'caseId': caseUser['caseId'],
            })

            Entry().removeWithQuery({
                'caseUserId': caseUser['_id']
            })

            # delete response associated with case
            ResponseItem().removeWithQuery(
                query={
                    "baseParentType": 'user',
                    "baseParentId": caseUser['userId'],
                    "meta.case.caseId": caseUser['caseId']
                }
            )
        else:
            self.update({
                '_id': caseUser['_id'],
                'caseId': caseUser['caseId']
            }, {
                '$set': {
                    'active': False,
                    'deleted': datetime.datetime.now()
                }
            })

            Entry().update({
                'caseUserId': caseUser['_id']
            }, {
                '$set': {
                    'active': True,
                    'deleted': datetime.datetime.now()
                }
            })

