# -*- coding: utf-8 -*-
import copy
import datetime
import json
import os
import six

from bson.objectid import ObjectId
from .folder import Folder
from .model_base import AccessControlledModel
from girderformindlogger import events
from girderformindlogger.constants import AccessType
from girderformindlogger.exceptions import ValidationException, GirderException
from girderformindlogger.utility.model_importer import ModelImporter
from girderformindlogger.utility.progress import noProgress, \
    setResponseTimeLimit


class Profile(Folder):
    """
    Profiles store customizable information specific to both users and applets.
    These data can be sensitive and are access controlled.
    """

    def initialize(self):
        self.name = 'profile'
        self.ensureIndices(('parentId', ([('parentId', 1))))

        self.exposeFields(level=AccessType.READ, fields=(
            '_id', 'created', 'updated', 'meta', 'parentId',
            'parentCollection', 'creatorId', 'baseParentType', 'baseParentId'
        ))


    def load(self, id, level=AccessType.ADMIN, user=None, objectId=True,
             force=False, fields=None, exc=False):
        """
        We override load in order to ensure the folder has certain fields
        within it, and if not, we add them lazily at read time.

        :param id: The id of the resource.
        :type id: string or ObjectId
        :param user: The user to check access against.
        :type user: dict or None
        :param level: The required access type for the object.
        :type level: AccessType
        :param force: If you explicitly want to circumvent access
                      checking on this resource, set this to True.
        :type force: bool
        """
        # Ensure we include extra fields to do the migration below
        extraFields = {
            'baseParentId',
            'baseParentType',
            'parentId',
            'userId'
        }
        loadFields = self._supplementFields(fields, extraFields)

        doc = super(Profile, self).load(
            id=id, level=level, user=user, objectId=objectId, force=force,
            fields=loadFields, exc=exc
        )

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
            if 'meta' not in doc:
                doc['meta'] = {}
                self.update({'_id': doc['_id']}, {'$set': {
                    'meta': {}
                }})

            self._removeSupplementalFields(doc, fields)

        return doc

    def _updateDescendants(self, folderId, updateQuery):
        """
        This helper is used to update all items and folders underneath a
        profile. This is expensive, so think carefully before using it.

        :param folderId: The _id of the profile at the root of the subtree.
        :param updateQuery: The mongo query to apply to all of the children of
        the profile.
        :type updateQuery: dict
        """
        from .item import Item

        self.update(query={
            'parentId': folderId,
            'parentCollection': 'profile'
        }, update=updateQuery, multi=True)
        Item().update(query={
            'folderId': folderId,
        }, update=updateQuery, multi=True)

        q = {
            'parentId': folderId,
            'parentCollection': 'profile'
        }
        for child in self.find(q):
            self._updateDescendants(child['_id'], updateQuery)

    def _isAncestor(self, ancestor, descendant):
        """
        Returns whether profile "ancestor" is an ancestor of profile "descendant",
        or if they are the same profile.

        :param ancestor: The profile to test as an ancestor.
        :type ancestor: profile
        :param descendant: The profile to test as a descendant.
        :type descendant: profile
        """
        if ancestor['_id'] == descendant['_id']:
            return True

        if descendant['parentCollection'] != 'profile':
            return False

        descendant = self.load(descendant['parentId'], force=True)

        if descendant is None:
            return False

        return self._isAncestor(ancestor, descendant)


    def remove(self, folder, progress=None, **kwargs):
        """
        Delete a profile recursively.

        :param profile: The profile document to delete.
        :type folder: dict
        :param progress: A progress context to record progress on.
        :type progress: girderformindlogger.utility.progress.ProgressContext or None.
        """
        # Remove the contents underneath this folder recursively.
        from .upload import Upload

        self.clean(folder, progress, **kwargs)

        # Delete pending uploads into this folder
        uploadModel = Upload()
        uploads = uploadModel.find({
            'parentId': folder['_id'],
            'parentType': 'profile'
        })
        for upload in uploads:
            uploadModel.remove(upload, progress=progress, **kwargs)
        uploads.close()

        # Delete this folder
        AccessControlledModel.remove(self, folder, progress=progress, **kwargs)
        if progress:
            progress.update(increment=1, message='Deleted profile %s' %
                            folder['name'])

    def childItems(self, folder, limit=0, offset=0, sort=None, filters=None,
                   **kwargs):
        """
        Generator function that yields child items in a profile.  Passes any
        kwargs to the find function.

        :param folder: The parent profile.
        :param limit: Result limit.
        :param offset: Result offset.
        :param sort: The sort structure to pass to pymongo.
        :param filters: Additional query operators.
        """
        from .item import Item

        q = {
            'folderId': folder['_id']
        }
        q.update(filters or {})

        return Item().find(q, limit=limit, offset=offset, sort=sort, **kwargs)

    def childFolders(self, parent, parentType, user=None, limit=0, offset=0,
                     sort=None, filters=None, force=False, **kwargs):
        """
        This generator will yield child folders of a user, collection, or
        folder, with access policy filtering.  Passes any kwargs to the find
        function.

        :param parent: The parent object.
        :type parentType: Type of the parent object.
        :param parentType: The parent type.
        :type parentType: 'user', 'folder', or 'collection'
        :param user: The user running the query. Only returns folders that this
                     user can see.
        :param limit: Result limit.
        :param offset: Result offset.
        :param sort: The sort structure to pass to pymongo.
        :param filters: Additional query operators.
        :param force: Ignore permissions
        :type force: bool
        """
        if not filters:
            filters = {}

        parentType = _verify_parentType(parentType)

        q = {
            'parentId': parent['_id'],
            'parentCollection': parentType
        }
        q.update(filters)

        cursor = self.findWithPermissions(
            q,
            sort=sort,
            user=user,
            level=None if force else AccessType.READ,
            limit=limit,
            offset=offset,
            **kwargs
        )

        return iter(cursor)

    def _verify_parentType(self, parentType):
        parentType = parentType.lower()
        if parentType not in ('folder', 'user', 'collection', 'profile'):
            raise ValidationException(
                'The parentType must be folder, collection, user, or profile.'
            )
        return(parentType)

    def createFolder(self, parent, name, description='', parentType='profile',
                     public=None, creator=None, allowRename=False, reuseExisting=False):
        """
        Create a new folder under the given parent.

        :param parent: The parent document. Should be a folder, user, or
                       collection.
        :type parent: dict
        :param name: The name of the folder.
        :type name: str
        :param description: Description for the folder.
        :type description: str
        :param parentType: What type the parent is:
                           ('folder' | 'user' | 'collection')
        :type parentType: str
        :param public: Public read access flag.
        :type public: bool or None to inherit from parent
        :param creator: User document representing the creator of this folder.
        :type creator: dict
        :param allowRename: if True and a folder or item of this name exists,
                            automatically rename the folder.
        :type allowRename: bool
        :param reuseExisting: If a folder with the given name already exists
            under the given parent, return that folder rather than creating a
            new one.
        :type reuseExisting: bool
        :returns: The folder document that was created.
        """
        if reuseExisting:
            existing = self.findOne({
                'parentId': parent['_id'],
                'name': name,
                'parentCollection': parentType
            })

            if existing:
                return existing

        parentType = _verify_parentType(parentType)

        if parentType == 'folder':
            if 'baseParentId' not in parent:
                pathFromRoot = self.parentsToRoot(
                    parent, user=creator, force=True)
                parent['baseParentId'] = pathFromRoot[0]['object']['_id']
                parent['baseParentType'] = pathFromRoot[0]['type']
        else:
            parent['baseParentId'] = parent['_id']
            parent['baseParentType'] = parentType

        now = datetime.datetime.utcnow()

        if creator is None:
            creatorId = None
        else:
            creatorId = creator.get('_id', None)

        folder = {
            'name': name,
            'description': description,
            'parentCollection': parentType,
            'baseParentId': parent['baseParentId'],
            'baseParentType': parent['baseParentType'],
            'parentId': ObjectId(parent['_id']),
            'creatorId': creatorId,
            'created': now,
            'updated': now,
            'size': 0,
            'meta': {}
        }

        if parentType in ('folder', 'collection') and (
            parent.get('name') not in [
                "Activities", "Volumes", "Activitysets", "Applets", "Screens"
            ]
        ):
            self.copyAccessPolicies(src=parent, dest=folder, save=False)

        if creator is not None:
            self.setUserAccess(folder, user=creator, level=AccessType.ADMIN,
                               save=False)

        # Allow explicit public flag override if it's set.
        if public is not None and isinstance(public, bool):
            self.setPublic(folder, public, save=False)

        if allowRename:
            self.validate(folder, allowRename=True)

        # Now validate and save the folder.
        return self.save(folder)

    def createProfile(self, applet, user, role="user"):
        """
        Create a new profile to store information specific to a given (applet ∩
            user)

        :param applet: The applet for which this profile exists
        :type parent: dict
        :param user: The user for which this profile exists
        :type user: dict
        :returns: The profile document that was created.
        """
        from girderformindlogger.models.applet import Applet, getAppletsForUser

        if applet['_id'] not in [
            a.get('_id') for a in getAppletsForUser(role, user)
        ]:
            raise ValidationException(
                "User does not have role \"{}\" in this \"{}\" applet "
                "({})".format(
                    role,
                    Applet().preferredName(applet),
                    str(applet['_id'])
                )
            )

        existing = self.findOne({
            'parentId': parent['_id'],
            'userId': user['_id'],
            'parentCollection': 'folder'
        })

        if existing:
            return existing

        now = datetime.datetime.utcnow()

        profile = {
            'parentId': ObjectId(applet['_id']),
            'userId': ObjectId(user['_id']),
            'created': now,
            'updated': now,
            'size': 0,
            'meta': {}
        }

        self.setPublic(profile, False, save=False)

        # Now validate and save the profile.
        return self.save(profile)

    def countFolders(self, folder, user=None, level=None):
        """
        Returns the number of subfolders within the given profile. Access
        checking is optional; to circumvent access checks, pass ``level=None``.

        :param folder: The parent profile.
        :type folder: dict
        :param user: If performing access checks, the user to check against.
        :type user: dict or None
        :param level: The required access level, or None to return the raw
            subfolder count.
        """
        fields = () if level is None else ('access', 'public')

        folders = self.findWithPermissions({
            'parentId': folder['_id'],
            'parentCollection': 'profile'
        }, fields=fields, user=user, level=level)

        return folders.count()

    def subtreeCount(self, folder, includeItems=True, user=None, level=None):
        """
        Return the size of the subtree rooted at the given profile. Includes
        the root profile in the count.

        :param folder: The root of the subtree.
        :type folder: dict
        :param includeItems: Whether to include items in the subtree count, or
            just folders.
        :type includeItems: bool
        :param user: If filtering by permission, the user to filter against.
        :param level: If filtering by permission, the required permission level.
        :type level: AccessLevel
        """
        count = 1

        if includeItems:
            count += self.countItems(folder)

        folders = self.findWithPermissions({
            'parentId': folder['_id'],
            'parentCollection': 'profile'
        }, fields='access', user=user, level=level)

        count += sum(self.subtreeCount(subfolder, includeItems=includeItems,
                                       user=user, level=level)
                     for subfolder in folders)

        return count

    def fileList(self, doc, user=None, path='', includeMetadata=False,
                 subpath=True, mimeFilter=None, data=True):
        """
        This function generates a list of 2-tuples whose first element is the
        relative path to the file from the profile's root and whose second
        element depends on the value of the `data` flag. If `data=True`, the
        second element will be a generator that will generate the bytes of the
        file data as stored in the assetstore. If `data=False`, the second
        element is the file document itself.

        :param doc: The folder to list.
        :param user: The user used for access.
        :param path: A path prefix to add to the results.
        :type path: str
        :param includeMetadata: if True and there is any metadata, include a
                                result which is the JSON string of the
                                metadata.  This is given a name of
                                metadata[-(number).json that is distinct from
                                any file within the folder.
        :type includeMetadata: bool
        :param subpath: if True, add the folder's name to the path.
        :type subpath: bool
        :param mimeFilter: Optional list of MIME types to filter by. Set to
            None to include all files.
        :type mimeFilter: `list or tuple`
        :param data: If True return raw content of each file as stored in the
            assetstore, otherwise return file document.
        :type data: bool
        :returns: Iterable over files in this folder, where each element is a
                  tuple of (path name of the file, stream function with file
                  data or file object).
        :rtype: generator(str, func)
        """
        from .item import Item

        itemModel = Item()
        if subpath:
            path = os.path.join(path, doc['name'])
        metadataFile = 'girder-folder-metadata.json'

        # Eagerly evaluate this list, as the MongoDB cursor can time out on long requests
        childFolders = list(self.childFolders(
            parentType='profile', parent=doc, user=user,
            fields=['name'] + (['meta'] if includeMetadata else [])
        ))
        for sub in childFolders:
            if sub['name'] == metadataFile:
                metadataFile = None
            for (filepath, file) in self.fileList(
                    sub, user, path, includeMetadata, subpath=True,
                    mimeFilter=mimeFilter, data=data):
                yield (filepath, file)

        # Eagerly evaluate this list, as the MongoDB cursor can time out on long requests
        childItems = list(self.childItems(
            folder=doc, fields=['name'] + (['meta'] if includeMetadata else [])
        ))
        for item in childItems:
            if item['name'] == metadataFile:
                metadataFile = None
            for (filepath, file) in itemModel.fileList(
                    item, user, path, includeMetadata, mimeFilter=mimeFilter, data=data):
                yield (filepath, file)

        if includeMetadata and metadataFile and doc.get('meta', {}):
            def stream():
                yield json.dumps(doc['meta'], default=str)
            yield (os.path.join(path, metadataFile), stream)

    def setAccessList(self, doc, access, save=False, recurse=False, user=None,
                      progress=noProgress, setPublic=None, publicFlags=None, force=False):
        """
        Overrides AccessControlledModel.setAccessList to add a recursive
        option. When `recurse=True`, this will set the access list on all
        subfolders to which the given user has ADMIN access level. Any
        subfolders that the given user does not have ADMIN access on will be
        skipped.

        :param doc: The folder to set access settings on.
        :type doc: girderformindlogger.models.folder
        :param access: The access control list.
        :type access: dict
        :param save: Whether the changes should be saved to the database.
        :type save: bool
        :param recurse: Whether this access list should be propagated to all
            subfolders underneath this folder.
        :type recurse: bool
        :param user: The current user (for recursive mode filtering).
        :param progress: Progress context to update.
        :type progress: :py:class:`girderformindlogger.utility.progress.ProgressContext`
        :param setPublic: Pass this if you wish to set the public flag on the
            resources being updated.
        :type setPublic: bool or None
        :param publicFlags: Pass this if you wish to set the public flag list on
            resources being updated.
        :type publicFlags: flag identifier str, or list/set/tuple of them, or None
        :param force: Set this to True to set the flags regardless of the passed in
            user's permissions.
        :type force: bool
        """
        progress.update(increment=1, message='Updating ' + doc['name'])
        if setPublic is not None:
            self.setPublic(doc, setPublic, save=False)

        if publicFlags is not None:
            doc = self.setPublicFlags(doc, publicFlags, user=user, save=False, force=force)

        doc = AccessControlledModel.setAccessList(
            self, doc, access, user=user, save=save, force=force)

        if recurse:
            subfolders = self.findWithPermissions({
                'parentId': doc['_id'],
                'parentCollection': 'profile'
            }, user=user, level=AccessType.ADMIN)

            for folder in subfolders:
                self.setAccessList(
                    folder, access, save=True, recurse=True, user=user,
                    progress=progress, setPublic=setPublic, publicFlags=publicFlags, force=force)

        return doc
