# -*- coding: utf-8 -*-
import copy
import datetime
import json
import os
import six

from bson.objectid import ObjectId
from girderformindlogger import events
from girderformindlogger.constants import AccessType
from girderformindlogger.exceptions import ValidationException, GirderException
from girderformindlogger.models.model_base import AccessControlledModel, Model
from girderformindlogger.utility.model_importer import ModelImporter
from girderformindlogger.utility.progress import noProgress, setResponseTimeLimit
from girderformindlogger.constants import USER_ROLES
from bson import json_util

class AccountProfile(AccessControlledModel):
    """
    collection for manage schedule and notification.
    """

    def initialize(self):
        self.name = 'accountProfile'
        self.ensureIndices(
            (
                'userId',
                'accountId',
                'accountName'
            )
        )

    def validate(self, document):
        return document

    def createOwner(self, user):
        account = {
            'userId': user['_id'],
            'accountName': user['firstName'],
            'applets': {}
        }
        account = self.save(account)
        account['accountId'] = account['_id']

        return self.save(account)

    def updateAccountName(self, accountId, accountName):
        self.update({
            'accountId': ObjectId(accountId)
        }, {'$set': {
            'accountName': accountName
        }})

    def hasPermission(self, profile, role):
        if profile and profile['_id'] == profile['accountId'] or len(profile.get('applets', {}).get(role, [])):
            return True

        return False

    def getManagers(self, accountId):
        profiles = list(self.find({'accountId': ObjectId(accountId), 'applets.manager': {'$size': {'$gte': 1}}}))
        return [
            profile.get('userId') for profile in profiles
        ]

    def getAccounts(self, userId):
        accounts = list(self.find({'userId': userId}))
        return accounts

    def createAccountProfile(self, accountId, userId):
        existingProfile = self.findOne({'accountId': ObjectId(accountId), 'userId': userId})

        if existingProfile:
            return existingProfile

        ownerAccount = self.load(accountId, force=True)
        accountProfile = {
            'userId': user['_id'],
            'accountName': ownerAccount['accountName'],
            'accountId': accountId,
            'applets': {}
        }
        account = self.save(account)
        return accountProfile

    def appendApplet(self, profile, appletId, roles):
        for role in roles:
            profile['applets'][role] = profile['applets'].get('role', [])
            profile['applets'][role].append(ObjectId(appletId))

        return self.save(profile)

    def removeApplet(self, profile, appletId):
        if not profile.get('applets'):
            profile['applets'] = {}
            for role in USER_ROLES.keys():
                profile['applets'][role] = []

        appletId = ObjectId(appletId)

        for role in USER_ROLES.keys():
            if appletId in profile['applets'][role]:
                profile['applets'][role].remove(appletId)

        return self.save(profile)
