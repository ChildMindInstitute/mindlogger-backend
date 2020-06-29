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
        if not document.get('accountName', ''):
            raise ValidationException('accountName not defined.', 'accountName')

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
        if profile and (profile['_id'] == profile['accountId'] or len(profile.get('applets', {}).get(role, []))):
            return True

        return False

    def getManagers(self, accountId):
        profiles = list(self.find({'accountId': ObjectId(accountId), 'applets.manager': {'$exists': True }}))
        return [
            profile.get('userId') for profile in profiles if len(profile.get('applets', {}).get('manager', []))
        ]

    def getOwner(self, accountId):
        return self.findOne({'_id': ObjectId(accountId)})

    def getAccounts(self, userId):
        accounts = list(self.find({'userId': userId}))
        return accounts

    def createAccountProfile(self, accountId, userId):
        existingProfile = self.findOne({'accountId': ObjectId(accountId), 'userId': userId})

        if existingProfile:
            return existingProfile

        ownerAccount = self.load(accountId, force=True)
        accountProfile = {
            'userId': userId,
            'accountName': ownerAccount['accountName'],
            'accountId': accountId,
            'applets': {}
        }
        return self.save(accountProfile)

    def appendApplet(self, profile, appletId, roles):
        appletId = ObjectId(appletId)

        if profile['accountId'] == profile['_id']:
            roles = list(USER_ROLES.keys())
            roles.append('owner')

        for role in roles:
            profile['applets'][role] = profile['applets'].get(role, [])
            if appletId not in profile['applets'][role]:
                profile['applets'][role].append(appletId)

        return self.save(profile)

    def removeApplet(self, profile, appletId):
        roles = list(USER_ROLES.keys())
        roles.append('owner')

        if not profile.get('applets'):
            profile['applets'] = {}

        appletId = ObjectId(appletId)

        for role in roles:
            if appletId in profile['applets'].get(role, []):
                profile['applets'][role].remove(appletId)

        if profile['_id'] != profile['accountId'] and not len(profile.get('applets', {}).get('user', [])):
            self.remove(profile)
        else:
            self.save(profile)

