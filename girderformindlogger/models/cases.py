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
from girderformindlogger.models.caseUsers import CaseUser
from girderformindlogger.models.entries import EntryModel
from girderformindlogger.exceptions import AccessException, ValidationException
from girderformindlogger.utility.model_importer import ModelImporter
from girderformindlogger.constants import USER_ROLES
from bson import json_util
from pymongo import ASCENDING, DESCENDING

class CaseModel(AccessControlledModel):
    """
    collection for managing account profiles
    """

    def initialize(self):
        self.name = 'cases'
        self.ensureIndices(
            (
                'name',
                'accountId',
            )
        )

    def validate(self, document):
        if not document.get('name'):
            raise ValidationException('name is not defined', 'name')
        return document

    def addCase(self, accountId, caseId, password, creatorId, applets):
        now = datetime.datetime.utcnow()

        case = self.findOne({ 'name': caseId, 'accountId': accountId })
        if not case:
            case = {
                'created': now,
                'accountId': ObjectId(accountId),
            }
        elif case.get('active'):
            raise ValidationException('case already exists')

        case.update({
            'name': caseId,
            'updated': now,
            'creatorId': ObjectId(creatorId),
            'applets': [
                ObjectId(appletId) for appletId in applets
            ],
            'active': True,
            'password': password
        })

        return self.save(case)

    def deleteCase(self, id, deleteResponse):
        if deleteResponse: # permanent delete
            self.removeWithQuery({ '_id': ObjectId(id) })

            CaseUser().removeWithQuery({ 'caseId': ObjectId(id) })
            Entry().removeWithQuery({ 'caseId': ObjectId(id) })
        else:
            self.update({
                '_id': ObjectId(id)
            }, {
                '$set': {
                    'active': False,
                    'deleted': datetime.datetime.now()
                }
            })

            CaseUser().update({
                'caseId': ObjectId(id)
            }, {
                '$set': {
                    'active': False,
                    'deleted': datetime.datetime.now()
                }
            })

            Entry().update({
                'caseId': ObjectId(id)
            }, {
                '$set': {
                    'active': False,
                    'deleted': datetime.datetime.now()
                }
            })


    def getCaseData(self, model):
        return {
            '_id': model['_id'],
            'caseId': model['name'],
            'updated': model['updated'],
            'applets': model['applets'],
            'password': model['password']
        }

    def addAppletsToCase(self, applets, id, password):
        case = self.findOne({'_id': ObjectId(id)})

        for appletId in applets:
            if ObjectId(appletId) not in case['applets']:
                case['applets'].append(ObjectId(appletId))

        case['password'] = password

        case['updated'] = datetime.datetime.utcnow()
        return self.save(case)


    def getCasesForAccount(self, accountId):
        cases = list(self.find({
            'accountId': ObjectId(accountId),
            'active': True
        }, sort=[("created", ASCENDING)]))

        return [
            self.getCaseData(case) for case in cases
        ]
