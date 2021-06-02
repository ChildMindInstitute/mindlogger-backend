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
from girderformindlogger.exceptions import AccessException, ValidationException
from girderformindlogger.utility.model_importer import ModelImporter
from girderformindlogger.constants import USER_ROLES
from bson import json_util

class AppletBasket(AccessControlledModel):
    """
    collection for managing account profiles
    """

    def initialize(self):
        self.name = 'appletBasket'
        self.ensureIndices(
            (
                'userId',
                'appletId'
            )
        )

    def validate(self, document):
        return document

    def updateSelection(self, userId, appletId, selection):
        libraryApplet = AppletLibrary().findOne({'appletId': appletId}, fields=['_id'])

        if not libraryApplet:
            raise AccessException("Unable to find published applet with specified id.")


        document = self.findOne({
            'userId': ObjectId(userId),
            'appletId': ObjectId(appletId)
        })

        if not document:
            document = {
                'userId': ObjectId(userId),
                'appletId': ObjectId(appletId)
            }

        if not selection:
            document['selection'] = None
        else:
            document['selection'] = []

            for activitySelection in selection:
                activityId = ObjectId(activitySelection['activityId'])
                items = activitySelection.get('items', None)

                updated = False

                document['selection'].append({
                    'activityId': activityId,
                    'items': [
                        ObjectId(itemId) for itemId in items
                    ] if items is not None else None
                })

        self.save(document)

    def deleteSelection(self, userId, appletId):
        self.removeWithQuery({
            'userId': ObjectId(userId),
            'appletId': ObjectId(appletId)
        })

    def setSelection(self, userId, selection):
        self.removeWithQuery({
            'userId': ObjectId(userId)
        })

        for appletId in selection:
            document = {
                'userId': userId,
                'appletId': ObjectId(appletId)
            }
            try:
                for activitySelection in selection[appletId]:
                    try:
                        activityId = activitySelection['activityId']
                        items = activitySelection.get('items', None)

                        if not document.get('selection', []):
                            document['selection'] = []

                        document['selection'].append({
                            'activityId': ObjectId(activityId),
                            'items': [
                                ObjectId(itemId) for itemId in items
                            ] if items is not None else None
                        })
                    except:
                        pass

                self.save(document)
            except:
                pass

    def getBasket(self, userId):
        applets = list(self.find({
            'userId': userId
        }))

        basket = {}
        for applet in applets:
            appletId = str(applet['appletId'])

            basket[appletId] = applet['selection']

        return basket
