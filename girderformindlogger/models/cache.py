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
from bson import json_util
import decimal

class Cache(Model):
    """
    Cache collection is used to save cache .
    """

    def initialize(self):
        self.name = 'cache'
        self.ensureIndices(
            (
                'source_id',
                'updated'
            )
        )

    def validate(self, document):
        return document

    def insertCache(self, collection_name, source_id, model_type, cachedData):
        def decimal_default(obj):
            if isinstance(obj, decimal.Decimal):
                return float(obj)
            raise TypeError

        newCache = {
            'collection_name': collection_name,
            'source_id': source_id,
            'model_type': model_type,
            'updated': datetime.datetime.utcnow(),
            'cache_data': json_util.dumps(cachedData, default=decimal_default)
        }
        return self.save(newCache)

    def updateCache(self, original_id, collection_name, source_id, model_type, cachedData):
        return self.save({
            '_id': ObjectId(original_id),
            'collection_name': collection_name,
            'source_id': source_id,
            'model_type': model_type,
            'updated': datetime.datetime.utcnow(),
            'cache_data': json_util.dumps(cachedData)
        })

    def getCacheData(self, _id):
        document = self.findOne(query={'_id': ObjectId(_id)})
        if document.get('cache_data'):
            return json_util.loads(document.get('cache_data'))
        return None

    def getFromSourceID(self, collection_name, source_id):
        document = self.findOne(query={'collection_name': collection_name, 'source_id': source_id})
        if document.get('cache_data'):
            return json_util.loads(document.get('cache_data'))
        return None

