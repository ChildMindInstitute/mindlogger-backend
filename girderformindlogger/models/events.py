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


class Events(Model):
    """
    collection for manage schedule and notification.
    """

    def initialize(self):
        self.name = 'events'
        self.ensureIndices(
            (
                'applet_id',
                'individualized'
            )
        )

    def validate(self, document):
        return document

    def upsertEvent(self, event, applet_id, event_id = None):
        newEvent = { 'applet_id': applet_id, 'individualized': False }

        if event_id and self.findOne({'_id': ObjectId(event_id)}, fields=['_id']):
            newEvent['_id'] = ObjectId(event_id)

        if 'data' in event:
            newEvent['data'] = event['data']
            if 'users' in event['data']:
                newEvent['individualized'] = True
        if 'schedule' in event:
            newEvent['schedule'] = event['schedule']

        self.save(newEvent)

    def getEvents(self, applet_id, individualized):
        events = list(self.find({'applet_id': applet_id, 'individualized': individualized}))
        for event in events:
            if 'data' in event and 'users' in event['data']:
                event['data'].pop('users')

        return events
