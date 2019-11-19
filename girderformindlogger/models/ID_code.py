# -*- coding: utf-8 -*-
import copy
import datetime
import json
import os
import six

from bson.objectid import ObjectId
from .model_base import Model
from girderformindlogger import events
from girderformindlogger import logger
from girderformindlogger.constants import AccessType
from girderformindlogger.exceptions import ValidationException, GirderException
from girderformindlogger.models.item import Item
from girderformindlogger.utility import acl_mixin
from girderformindlogger.utility.model_importer import ModelImporter


class IDCode(acl_mixin.AccessControlMixin, Model):
    """
    IDCodes are special Items that contain a string identifier for
    pseudoanonymized data.
    """

    def initialize(self):
        self.name = 'idCode'
        self.ensureIndices(('folderId'))
        self.ensureTextIndex({'code': 10})
        self.resourceColl = 'folder'
        self.resourceParent = 'folderId'

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
        h = hashlib.new('shake_256')
        h.update(b"{}{}".format(
            profile.get('folderId', ''),
            profile.get('userId', '')
        ))
        return(h.hexdigest(9))

    def load(self, id, level=AccessType.ADMIN, user=None, objectId=True,
             force=False, fields=None, exc=False):
        """
        Calls AccessControlMixin.load while doing some auto-correction.

        Takes the same parameters as
        :py:func:`girderformindlogger.models.model_base.AccessControlMixin.load`
        """
        from .profile import Profile

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
        existing = self.findOne({
            'folderId': profile['_id']
        })
        if existing:
            raise ValidationException(
                "An applet ∩ user can only have one ID code. One already "
                "exists here."
            )

        now = datetime.datetime.utcnow()

        if 'baseParentType' not in folder:
            pathFromRoot = self.parentsToRoot({'folderId': folder['_id']},
                                              creator, force=True)
            folder['baseParentType'] = pathFromRoot[0]['type']
            folder['baseParentId'] = pathFromRoot[0]['object']['_id']

        return self.save({
            'code': idCode if idCode is not None else self.generateCode(
                profile
            ),
            'folderId': ObjectId(folder['_id']),
            'baseParentType': folder['baseParentType'],
            'baseParentId': folder['baseParentId'],
            'created': now,
            'updated': now,
            'size': 0
        })

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
        from .folder import Folder

        folderModel = Folder()
        curFolder = folderModel.load(
            item['folderId'], user=user, level=AccessType.READ, force=force)
        folderIdsToRoot = folderModel.parentsToRoot(
            curFolder, user=user, level=AccessType.READ, force=force)

        if force:
            folderIdsToRoot.append({'type': 'folder', 'object': curFolder})
        else:
            filteredFolder = folderModel.filter(curFolder, user)
            folderIdsToRoot.append({'type': 'folder', 'object': filteredFolder})

        return folderIdsToRoot

    def isOrphan(self, item):
        """
        Returns True if this item is orphaned (its folder is missing).

        :param item: The item to check.
        :type item: dict
        """
        from .folder import Folder
        return not Folder().load(item.get('folderId'), force=True)
