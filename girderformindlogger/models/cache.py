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
from girderformindlogger.models.model_base import AccessControlledModel
from girderformindlogger.utility.model_importer import ModelImporter
from girderformindlogger.utility.progress import noProgress, setResponseTimeLimit


class Cache(AccessControlledModel):
    """
    Cache collection is used to save cache .
    """

    def initialize(self):
        self.name = 'cache'
        self.ensureIndices(
            (
                [
                    ('collection_name', 1),
                    ('source_id', 1)                    
                ],
                'updated'
            )
        )

        self.exposeFields(level=AccessType.READ, fields=(
            'collection_name', 'source_id'))

    def insert(self, collection_name, source_id, model_type, cachedData):
        return self.save({
            'collection_name': collection_name,
            'source_id': source_id,
            'model_type': model_type,
            'updated': datetime.datetime.utcnow(),
            'cache_data': cachedData
        })
    
    def update(self, original_id, collection_name, source_id, model_type, cachedData):
        return super().update(query={'_id': ObjectId(original_id)}, {
            'collection_name': collection_name,
            'source_id': source_id,
            'model_type': model_type,
            'updated': datetime.datetime.utcnow(),
            'cache_data': cachedData
        }, False)
    
    def getCacheData(self, _id):
        document = self.findOne(query={'_id': ObjectId(_id)})
        if document:
            return document.get('cache_data')

        return None

    def loadFromSourceID(self, collection_name, source_id):
        return self.findOne(query={'collection_name': collection_name, 'source_id': source_id})

