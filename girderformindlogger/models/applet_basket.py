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

    def updateSelection(self, userId, appletId, activityId, items):
        libraryApplet = AppletLibrary().findOne({'appletId': appletId})

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

        updated = False

        for activitySelection in document.get('selection', []):
            if activitySelection['activityId'] == ObjectId(activityId):
                updated = True

                activitySelection['items'] = [
                    ObjectId(itemId) for itemId in items
                ] if items is not None else None

        if not updated:
            document['selection'] = document.get('selection', [])

            document['selection'].append({
                'activityId': ObjectId(activityId),
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
                'selection': []
            }
            try:
                document['appletId'] = ObjectId(appletId)

                for activitySelection in selection[appletId]:
                    try:
                        activityId = activitySelection['activityId']
                        items = activitySelection.get('items', None)

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
            appletId = str(applet['_id'])

            basket[appletId] = applet['selection']

        return basket
