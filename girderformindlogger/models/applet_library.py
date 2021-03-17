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
        libraryApplet = {
            'name': applet.get('meta', {}).get('applet', {}).get('displayName', ''),
            'appletId': applet['_id'],
            'accountId': applet['accountId'],
            'categoryId': None,
            'subCategoryId': None,
            'keywords': []
        }

        libraryApplet = self.save(libraryApplet)

        return libraryApplet

    def deleteAppletFromLibrary(self, applet):
        self.removeWithQuery({
            'appletId': applet['_id']
        })

    def updateAppletSearch(self, appletId, categoryName, subCategoryName, keywords):
        libraryApplet = self.findOne({
            'appletId': ObjectId(appletId)
        })

        if not libraryApplet:
            raise ValidationException('invalid applet')

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

        libraryApplet.update({
            'categoryId': category['_id'] if category else None,
            'subCategoryId': subCategory['_id'] if subCategory else None,
            'keywords': keywords
        })

        return libraryApplet.save()
