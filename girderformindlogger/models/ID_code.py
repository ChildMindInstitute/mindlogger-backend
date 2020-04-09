# -*- coding: utf-8 -*-
import copy
import datetime
import json
import os
import six

from bson.objectid import ObjectId
from girderformindlogger import events
from girderformindlogger import logger
from girderformindlogger.constants import AccessType
from girderformindlogger.exceptions import ValidationException, GirderException
from girderformindlogger.models.item import Item
from girderformindlogger.models.model_base import Model
from girderformindlogger.utility import acl_mixin
from girderformindlogger.utility.model_importer import ModelImporter


class IDCode(acl_mixin.AccessControlMixin, Model):
    """
    IDCodes are special Items that contain a string identifier for
    pseudoanonymized data.
    """

    def initialize(self):
        self.name = 'idCode'
        self.ensureIndices(('profileId'))
        self.ensureTextIndex({'code': 10})
        # self.resourceColl = 'folder'
        self.resourceParent = 'profileId'

        self.exposeFields(level=AccessType.READ, fields=('code'))

    def _validateString(self, value):
        """
        Make sure a value is a string and is stripped of whitespace.

        :param value: the value to coerce into a string if it isn't already.
        :returns: the string version of the value.
        """
        if value is None:
            value = ''
        if not isinstance(value, six.string_types):
            value = str(value)
        return value.strip()

    def generateCode(self, profile):
        """
        Autogenerate an ID code string for a given profile,

        :param profile: Profile for which to generate the ID code
        :type profile: dict
        :returns: string
        """
        import hashlib
        from datetime import datetime

        h = hashlib.new('shake_256')
        h.update("{}{}{}".format(
            profile.get('profileId', ''),
            profile.get('_id', str(profile['_id'])),
            datetime.now().isoformat()
        ).encode())
        return(h.hexdigest(9))

    def load(self, id, level=AccessType.ADMIN, user=None, objectId=True,
             force=False, fields=None, exc=False):
        """
        Calls AccessControlMixin.load while doing some auto-correction.

        Takes the same parameters as
        :py:func:`girderformindlogger.models.model_base.AccessControlMixin.load`
        """
        from girderformindlogger.models.profile import Profile

        # Ensure we include extra fields to do the migration below
        extraFields = {'baseParentId', 'baseParentType', 'parentId',
                       'parentCollection', 'code'}
        loadFields = self._supplementFields(fields, extraFields)

        doc = super(IDCode, self).load(
            id=id, level=level, user=user, objectId=objectId, force=force,
            fields=loadFields, exc=exc)

        if doc is not None:
            if 'baseParentType' not in doc:
                pathFromRoot = self.parentsToRoot(doc, user=user, force=True)
                baseParent = pathFromRoot[0]
                doc['baseParentId'] = baseParent['object']['_id']
                doc['baseParentType'] = baseParent['type']
                self.update({'_id': doc['_id']}, {'$set': {
                    'baseParentId': doc['baseParentId'],
                    'baseParentType': doc['baseParentType']
                }})
            if 'code' not in doc:
                doc['code'] = self.generateCode(
                    Profile().load(doc["parentId"], force=True)
                )
                self.update({'_id': doc['_id']}, {'$set': {
                    'code': doc['code']
                }})
            self._removeSupplementalFields(doc, fields)

        return doc

    def findIdCodes(self, profileId):
        from girderformindlogger.models.profile import Profile

        idCodes = [
            i['code'] for i in list(self.find({'profileId': {'$in': [
                str(profileId),
                ObjectId(profileId)
            ]}})) if isinstance(i, dict) and 'code' in i
        ]

        if not len(idCodes):
            self.createIdCode(Profile().load(profileId, force=True))
            return(self.findIdCodes(profileId))

        return(idCodes)

    def removeCode(self, profileId, code):
        from girderformindlogger.models.profile import Profile
        idCode = self.findOne({
            'profileId': ObjectId(profileId),
            'code': code
        })
        if idCode is not None:
            self.remove(idCode)
        if not len(self.findIdCodes(profileId)):
            self.createIdCode(Profile().load(profileId, force=True))
        return(Profile().load(profileId, force=True))

    def remove(self, item, **kwargs):
        """
        Delete an item, and all references to it in the database.

        :param item: The item document to delete.
        :type item: dict
        """

        # Delete the item itself
        Model.remove(self, item)

    def createIdCode(self, profile, idCode=None):
        """
        Create a new ID code.

        :param profile: The profile for which to create the ID code.
        :type name: dict
        :param idCode: ID Code string
        :type idCode: str or None
        :returns: The ID code document that was created.
        """
        now = datetime.datetime.utcnow()

        try:
            self.save(
                {
                    'code': idCode if idCode is not None else self.generateCode(
                        profile
                    ),
                    'profileId': ObjectId(profile['_id']),
                    'created': now,
                    'updated': now,
                    'size': 0
                },
                validate=False
            )
            return(True)
        except Exception as e:
            import sys, traceback
            raise e
            print(sys.exc_info())

    def findProfile(self, idCode):
        """
        Find a list of profiles for a given ID code.
        """
        existing = list(self.find({
            'code': idCode
        }))
        if len(existing):
            from girderformindlogger.models.profile import Profile
            ps = [
                Profile().load(
                    exist['profileId'],
                    force=True
                ) for exist in existing
            ]
            if len(ps):
                return(ps)
        else:
            from girderformindlogger.models.invitation import Invitation
            existing = list(self.find({
                'idCode': idCode
            }))
            ps = [
                Invitation().load(
                    exist['_id'],
                    force=True
                ) for exist in existing
            ]
            if len(ps):
                return(ps)
        return(None)

    def updateIdCode(self, item):
        """
        Updates an item.

        :param item: The item document to update
        :type item: dict
        :returns: The item document that was edited.
        """
        item['updated'] = datetime.datetime.utcnow()

        # Save the item
        return self.save(item, validate=False)

    def parentsToRoot(self, item, user=None, force=False):
        """
        Get the path to traverse to a root of the hierarchy.

        :param item: The item whose root to find
        :type item: dict
        :param user: The user making the request (not required if force=True).
        :type user: dict or None
        :param force: Set to True to skip permission checking. If False, the
            returned models will be filtered.
        :type force: bool
        :returns: an ordered list of dictionaries from root to the current item
        """
        from girderformindlogger.models.folder import Folder

        folderModel = Folder()
        curFolder = folderModel.load(
            item['profileId'], user=user, level=AccessType.READ, force=force)
        profileIdsToRoot = folderModel.parentsToRoot(
            curFolder, user=user, level=AccessType.READ, force=force)

        if force:
            profileIdsToRoot.append({'type': 'folder', 'object': curFolder})
        else:
            filteredFolder = folderModel.filter(curFolder, user)
            profileIdsToRoot.append({'type': 'folder', 'object': filteredFolder})

        return profileIdsToRoot

    def isOrphan(self, item):
        """
        Returns True if this item is orphaned (its folder is missing).

        :param item: The item to check.
        :type item: dict
        """
        from girderformindlogger.models.folder import Folder
        return not Folder().load(item.get('profileId'), force=True)
