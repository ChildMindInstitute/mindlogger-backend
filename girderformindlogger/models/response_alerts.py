# -*- coding: utf-8 -*-
import copy
import json
import os
import re

import six

from bson.objectid import ObjectId
from girderformindlogger import events
from girderformindlogger.constants import AccessType
from girderformindlogger.exceptions import ValidationException, GirderException
from girderformindlogger.models.model_base import AccessControlledModel, Model
from girderformindlogger.models.profile import Profile
from girderformindlogger.models.user import User
from girderformindlogger.utility.model_importer import ModelImporter
from girderformindlogger.utility.progress import noProgress, setResponseTimeLimit
from girderformindlogger.constants import USER_ROLES
from datetime import date, datetime, timedelta
from girderformindlogger.utility import mail_utils
from bson import json_util
from pymongo import DESCENDING, ASCENDING

class ResponseAlerts(AccessControlledModel):
    """
    collection for manage schedule and notification.
    """

    def initialize(self):
        self.name = 'responseAlerts'
        self.ensureIndices(
            (
                'created',
                ([
                    ('reviewerId', 1),
                    ('accountId', 1),
                    ('created', 1),
                ], {})
            )
        )

    def addResponseAlerts(self, userProfile, itemId, itemSchema, alertMessage):
        now = datetime.utcnow()

        reviewers = list(userProfile.get('reviewers', []))

        if 'reviewer' in userProfile['roles'] or 'manager' in userProfile['roles'] and userProfile['_id'] not in reviewers:
            reviewers.append(userProfile['_id'])

        for reviewerId in reviewers:
            reviewer = Profile().findOne({ '_id': ObjectId(reviewerId) })

            alert = {
                'reviewerId': reviewer['userId'],
                'accountId': userProfile['accountId'],
                'itemId': ObjectId(itemId),
                'itemSchema': itemSchema,
                'alertMessage': alertMessage,
                'appletId': userProfile['appletId'],
                'profileId': userProfile['_id'],
                'created': now,
                'viewed': False
            }

            self.save(alert)

            reviewerEmail = reviewer.get('email', '') or reviewer.get('userDefined', {}).get('email', '')

            if reviewerEmail and userProfile['_id'] != reviewer['_id']:
                reviewerInfo = User().findOne({
                    '_id': reviewer['userId']
                }, fields=['lang'])

                admin_url = os.getenv('ADMIN_URI') or 'localhost:8082'
                url = f'https://{admin_url}/'

                html = mail_utils.renderTemplate(f'responseAlert.{reviewerInfo.get("lang", "") or "en"}.mako', {
                    'url': url
                })

                mail_utils.sendMail(
                    'Response Alert',
                    html,
                    reviewerEmail
                )

    def getResponseAlerts(self, reviewerId, accountId):
        alerts = list(
            self.find({
                'reviewerId': ObjectId(reviewerId),
                'accountId': ObjectId(accountId),
                "created": {
                  "$gte": (datetime.utcnow() - timedelta(days=30)),
                }
            }, fields=[
                'itemId',
                'itemSchema',
                'alertMessage',
                'appletId',
                'profileId',
                'created',
                'viewed'
            ], sort=[('created', DESCENDING)])
        )

        userProfiles = {}
        viewerProfiles = {}
        for alert in alerts:
            alert.pop('_id')

            if str(alert['profileId']) not in userProfiles:
                profile = Profile().findOne({
                    '_id': alert['profileId']
                })

                appletId = str(profile['appletId'])
                if appletId not in viewerProfiles:
                    viewerProfile = Profile().findOne({
                        'appletId': alert['appletId'],
                        'userId': ObjectId(reviewerId)
                    })
                    viewerProfiles[appletId] = viewerProfile
                else:
                    viewerProfile = viewerProfiles[appletId]

                data = Profile().getProfileData(profile, viewerProfile)

                if data:
                    userProfiles[str(alert['profileId'])] = data
        return {
            'profiles': userProfiles,
            'list': alerts
        }



        return alerts
    def validate(self, document):
        return document
