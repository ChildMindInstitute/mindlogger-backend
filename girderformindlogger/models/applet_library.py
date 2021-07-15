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
from girderformindlogger.utility.model_importer import ModelImporter
from girderformindlogger.models.applet_categories import AppletCategory
from girderformindlogger.constants import USER_ROLES
from bson import json_util

class AppletLibrary(AccessControlledModel):
    """
    collection for managing account profiles
    """

    def initialize(self):
        self.name = 'appletLibrary'
        self.metaFields = [
            'name', 'appletId', 'accountId', 'description', 'image',
            'categoryId', 'subCategoryId', 'keywords'
        ]
        self.ensureIndices(
            (
                'name',
                'appletId',
                'accountId',
                'keywords'
            )
        )

    def validate(self, document):
        if not document.get('name', ''):
            raise ValidationException('name not defined.', 'name')

        return document

    def addAppletToLibrary(self, applet):
        from girderformindlogger.models.applet import Applet

        libraryApplet = self.findOne({
            'appletId': applet['_id']
        }, fields=self.metaFields)

        if libraryApplet:
            return libraryApplet

        libraryApplet = {
            'name': applet.get('meta', {}).get('applet', {}).get('displayName', ''),
            'appletId': applet['_id'],
            'accountId': applet['accountId'],
            'categoryId': None,
            'subCategoryId': None,
            'keywords': [],
            **Applet().getAppletMeta(applet)
        }

        if 'editing' in libraryApplet:
            libraryApplet.pop('editing')

        libraryApplet['activities'] = self.getActivitySearchInfo(applet)

        libraryApplet = self.save(libraryApplet)
        return libraryApplet

    def getActivitySearchInfo(self, applet):
        from girderformindlogger.utility import jsonld_expander
        from girderformindlogger.models.activity import Activity

        formattedApplet = jsonld_expander.formatLdObject(
            applet,
            'applet'
        )

        activityModel = Activity()
        activities = []
        for activityIRI in formattedApplet['activities']:
            activity = activityModel.findOne({
                '_id': ObjectId(formattedApplet['activities'][activityIRI])
            })

            formattedActivity = jsonld_expander.formatLdObject(
                activity,
                'activity'
            )

            activitySearch = {
                'activityId': ObjectId(formattedApplet['activities'][activityIRI]),
                'name': formattedActivity['activity'].get('@id', ''),
                'items': []
            }

            for itemIRI in formattedActivity['items']:
                item = formattedActivity['items'][itemIRI]
                activitySearch['items'].append({
                    'itemId': ObjectId(item['_id'].split('/')[-1]),
                    'name': item.get('schema:question', [{}])[0].get('@value') or item.get('@id', '')
                })

            activities.append(activitySearch)

        return activities

    def deleteAppletFromLibrary(self, applet):
        from girderformindlogger.models.applet_basket import AppletBasket

        self.removeWithQuery({
            'appletId': applet['_id']
        })

        AppletBasket().removeWithQuery({
            'appletId': applet['_id']
        })

    def updateAppletSearch(self, appletId, categoryName, subCategoryName, keywords):
        appletCategory = AppletCategory()
        category = appletCategory.findOne({
            'name': categoryName
        })

        subCategory = None

        if category:
            subCategory = appletCategory.findOne({
                'name': subCategoryName,
                'parentId': category['_id']
            })

        updates = {
            'categoryId': category['_id'] if category else None,
            'subCategoryId': subCategory['_id'] if subCategory else None,
            'keywords': keywords
        }

        self.update({
            'appletId': ObjectId(appletId)
        }, {
            '$set': updates
        })

    def appletContentUpdate(self, applet):
        from girderformindlogger.models.applet import Applet

        libraryApplet = self.findOne({
            'appletId': applet['_id']
        })

        libraryApplet.update(Applet().getAppletMeta(applet))

        if 'editing' in libraryApplet:
            libraryApplet.pop('editing')

        libraryApplet['activities'] = self.getActivitySearchInfo(applet)

        self.save(libraryApplet)
