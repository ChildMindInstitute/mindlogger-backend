# -*- coding: utf-8 -*-
import copy
import json
import os
import re

import six

from bson.objectid import ObjectId
import pytz
from girderformindlogger import events
from girderformindlogger.constants import AccessType
from girderformindlogger.exceptions import ValidationException, GirderException
from girderformindlogger.models.model_base import AccessControlledModel, Model
from girderformindlogger.models.aes_encrypt import AESEncryption
from girderformindlogger.utility.model_importer import ModelImporter
from girderformindlogger.utility.progress import noProgress, setResponseTimeLimit
from datetime import date, datetime, timedelta, timezone
from girderformindlogger.constants import USER_ROLES
from pymongo import ASCENDING, DESCENDING
from bson import json_util

class ResponseTokens(AESEncryption, dict):
    """
    collection for managing user's token balance
    """

    def initialize(self):
        self.name = 'responseTokens'
        self.ensureIndices(
            (
                'userId',
                'appletId',
                ([
                    ('userId', 1),
                    ('appletId', 1),
                    ('isCumulative', 1),
                    ('created', 1)
                ], {})
            )
        )

        self.initAES([
            ('data', 256),
        ])

    def validate(self, document):
        return document

    def encodeDocument(self, document):
        if isinstance(document.get('data', ''), dict):
            document['data'] = json_util.dumps(document['data'])

    def decodeDocument(self, document):
        try:
            document['data'] = json_util.loads(document['data'])
        except:
            pass

    def saveResponseToken(
        self,
        profile,
        data,
        userPublicKey,
        isCumulative=False,
        isToken=False,
        isTracker=False,
        trackerAggregation=False,
        version=None,
        tokenId=None,
        date=None
    ):
        now = datetime.utcnow()

        tokenInfo = {}

        if isCumulative:
            tokenInfo = self.findOne({
                'userId': profile['userId'],
                'appletId': profile['appletId'],
                'isCumulative': isCumulative
            }) or {}

        if tokenId:
            tokenInfo = self.findOne({'_id': ObjectId(tokenId)})

        tokenInfo.update({
            'userId': profile['userId'],
            'appletId': profile['appletId'],
            'accountId': profile['accountId'],
            'data': data,
            'isCumulative': isCumulative,
            'isToken': isToken,
            'isTracker': isTracker,
            'trackerAggregation': trackerAggregation,
            'userPublicKey': userPublicKey,
        })

        if date:
            tokenInfo['date'] = date

        if version:
            tokenInfo['version'] = version

        if not tokenInfo.get('created', None):
            tokenInfo['created'] = now

        if isCumulative:
            tokenInfo['updated'] = now

        self.save(tokenInfo)

    def getResponseTokens(self, profile, startDate=None, retrieveUserKeys=True):
        cumulativeToken = self.findOne({
            'userId': profile['userId'],
            'appletId': profile['appletId'],
            'isCumulative': True
        }, fields=['data'])

        query = {
            'userId': profile['userId'],
            'appletId': profile['appletId'],
            'isToken': True,
        }

        if startDate:
            query["created"] = {
                "$gte": startDate,
            }

        def convertTimeZone(tokens, profile):
            for token in tokens:
                if 'created' in token:
                    token["created"] = token["created"].replace(tzinfo=pytz.timezone("UTC")).astimezone(
                        timezone(
                            timedelta(
                                hours=profile.get('timezone', 0)
                            )
                        )
                    ).isoformat()

                token['id'] = token.pop('_id')

        tokens = list(self.find(
            query,
            fields=['created', 'data', 'date', 'userPublicKey'] if retrieveUserKeys else ['data', 'date'],
            sort=[("created", ASCENDING)]
        ))
        convertTimeZone(tokens, profile)

        query['isTracker'] = query.pop('isToken')
        trackers = list(self.find(
            query,
            fields=['created', 'data', 'userPublicKey'] if retrieveUserKeys else ['created', 'data']
        ))
        convertTimeZone(trackers, profile)

        query['trackerAggregation'] = query.pop('isTracker')
        trackerAggregation = list(self.find(
            query,
            fields=['created', 'data', 'userPublicKey', 'date'] if retrieveUserKeys else ['created', 'data', 'date']
        ))
        convertTimeZone(trackerAggregation, profile)

        return {
            'cumulative': cumulativeToken['data'] if cumulativeToken else 0,
            'tokenTimes': profile.get('tokenTimes', []),
            'lastRewardTime': profile.get('lastRewardTime', None),
            'tokens': tokens,
            'trackers': trackers,
            'trackerAggregation': trackerAggregation
        }
