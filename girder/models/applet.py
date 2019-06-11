#!/usr/bin/env python
# -*- coding: utf-8 -*-

###############################################################################
#  Copyright 2013 Kitware Inc.
#
#  Licensed under the Apache License, Version 2.0 ( the "License" );
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
###############################################################################

import copy
import datetime
import itertools
import json
import os
import six

from bson.objectid import ObjectId
from .folder import Folder
from girder import events
from girder.api.rest import getCurrentUser
from girder.constants import AccessType, SortDir, USER_ROLES
from girder.exceptions import AccessException, GirderException, \
    ValidationException
from girder.models.collection import Collection as CollectionModel
from girder.models.folder import Folder as FolderModel
from girder.models.group import Group as GroupModel
from girder.models.user import User as UserModel
from girder.utility.progress import noProgress, setResponseTimeLimit


class Applet(Folder):
    """
    Applets are access-controlled Folders, each of which links to an
    ActivitySet and contains any relevant constraints.
    """
    def createApplet(
        self,
        name,
        activitySet={},
        user=None,
        roles=None,
        constraints=None
    ):
        """
        Function to create an Applet.

        :param name: Name for the Applet
        :type name: str
        :param activitySet: ActivitySet to link to this Applet, with one or both
            keys: {`_id`, `url`}
        :type activitySet: dict
        :param user: User creating Applet
        :type user: dict
        :param roles: Roles to set to this Applet
        :type roles: dict or None
        :param constraints: Constraints to set to this Applet
        :type constraints: dict or None
        """
        if user==None:
            raise AccessException("You must be logged in to create an applet.")
        if constraints is not None and isinstance(constraints, dict):
            activitySet.update(constraints)

        applet = FolderModel().setMetadata(
            folder=FolderModel().createFolder(
                parent=CollectionModel().findOne({"name": "Applets"}),
                name=name,
                parentType='collection',
                public=True,
                creator=user,
                allowRename=True
            ),
            metadata={'activitySet': activitySet}
        )
        appletGroupName = "Default {} ({})".format(
            name,
            str(applet.get('_id', ''))
        )
        for role in USER_ROLES.keys():
            try:
                group = GroupModel().createGroup(
                    name="{} {}s".format(appletGroupName, role.title()),
                    creator=user,
                    public=False if role=='user' else True
                )
            except ValidationException:
                numero = 0
                numberedName = appletGroupName
                while GroupModel().findOne(query={'name': numberedName}):
                    numero += 1
                    numberedName = "{} {} {}s".format(
                        appletGroupName,
                        str(numero),
                        role.title()
                    )
                group = GroupModel().createGroup(
                    name=numberedName,
                    creator=user,
                    public=False if role=='user' else True
                )
            self.setGroupRole(
                doc=applet,
                group=group,
                role=role,
                currentUser=user,
                force=False
            )
        return(applet)


    def importUrl(self, url, user=None):
        """
        Gets an applet from a given URL, checks against the database, stores
        and returns that applet.

        Deprecated.
        """
        return(self.getFromUrl(url, 'applet', user))

    def load(self, id, level=AccessType.ADMIN, user=None, objectId=True,
             force=False, fields=None, exc=False):
        """
        We override load in order to ensure the folder has certain fields
        within it, and if not, we add them lazily at read time. Also, this
        method will return a specific version of an Activity if given an
        Activity version ID or the latest version of an Activity if given an
        Activity ID.

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
        extraFields = {'baseParentId', 'baseParentType', 'parentId',
                       'parentCollection', 'name', 'lowerName'}
        loadFields = self._supplementFields(fields, extraFields)
        doc = super(Folder, self).load(
            id=id, level=level, user=user, objectId=objectId, force=force,
            fields=loadFields, exc=exc)
        if doc is not None:
            pathFromRoot = Folder().parentsToRoot(doc, user=user, force=True)
            if 'baseParentType' not in doc:
                baseParent = pathFromRoot[0]
                doc['baseParentId'] = baseParent['object']['_id']
                doc['baseParentType'] = baseParent['type']
                self.update({'_id': doc['_id']}, {'$set': {
                    'baseParentId': doc['baseParentId'],
                    'baseParentType': doc['baseParentType']
                }})
            if 'lowerName' not in doc:
                doc['lowerName'] = doc['name'].lower()
                self.update(
                    {'_id': doc['_id']},
                    {'$set': {
                        'lowerName': doc['lowerName']
                    }}
                )
            if '_modelType' not in doc:
                doc['_modelType'] = 'folder'
            self._removeSupplementalFields(doc, fields)
            try:
                parent = pathFromRoot[-1]['object']
                if (
                    parent['name'] == "Applets" and
                    doc['baseParentType'] in {'collection', 'user'}
                ):
                    """
                    Check if parent is "Applets" collection or user
                    folder, ie, if this is an Applet. If so, return Applet.
                    """
                    return(doc)
            except:
                raise ValidationException(
                    "Invalid Applet ID."
                )



def canonicalUser(user):
    thisUser = getCurrentUser()
    try:
        userId = UserModel().load(
            user,
            level=AccessType.NONE,
            user=thisUser
        )
    except:
        return(None)
    try:
        return(str(userId['_id']) if '_id' in userId else None)
    except:
        return(None)


def createCipher(applet, appletAssignments, user):
    thisUser = getCurrentUser()
    cUser = None
    try:
        cUser = UserModel().load(
            user,
            level=AccessType.NONE,
            user=thisUser
        )
    except:
        cur_config = config.getConfig()
        if not re.match(cur_config['users']['email_regex'], user):
            raise ValidationException('Invalid email address.', 'user')
    newCipher = FolderModel().createFolder(
        parent=applet,
        name=nextCipher(appletAssignments),
        parentType='folder',
        public=False,
        creator=thisUser,
        reuseExisting=True
    )
    if cUser is None:
        try:
            appletName = FolderModel().preferredName(
                FolderModel().load(
                    applet['meta']['applet']['@id'],
                    level=AccessType.NONE,
                    user=thisUser
                )['name']
            )
        except:
            raise ValidationException('Invalid assignment folder.', 'applet')
        try:
            cUser = UserModel().createUser(
                login="-".join([
                    appletName.replace(' ', ''),
                    str(newCipher['name'])
                ]),
                password=str(uuid.uuid4()),
                firstName=appletName,
                lastName=newCipher['name'],
                email=user,
                admin=False,
                public=False,
                currentUser=thisUser
            )
        except:
            cUser = UserModel().createUser(
                login="-".join([
                    appletName.replace(' ', ''),
                    str(applet['meta']['applet']['@id']),
                    str(FolderModel().preferredName(newCipher))
                ]),
                password=str(uuid.uuid4()),
                firstName=appletName,
                lastName=FolderModel().preferredName(newCipher),
                email=user,
                admin=False,
                public=False,
                currentUser=thisUser
            )
    newSecretCipher = FolderModel().setMetadata(
        FolderModel().createFolder(
            parent=newCipher,
            name='userID',
            parentType='folder',
            public=False,
            creator=thisUser,
            reuseExisting=True
        ),
        {
            'user': {
                '@id': str(cUser['_id'])
            }
        }
    )
    for u in [thisUser, cUser]:
        FolderModel().setUserAccess(
            doc=newSecretCipher,
            user=u,
            level=None,
            save=True,
            currentUser=thisUser,
            force=True
        )
    for u in [thisUser, cUser]:
        FolderModel().setUserAccess(
            doc=newSecretCipher,
            user=u,
            level=AccessType.READ,
            save=True,
            currentUser=thisUser,
            force=True
        )
    return(newCipher)


def decipherUser(appletSpecificId):
    thisUser = getCurrentUser()
    try:
        ciphered = FolderModel().load(
            appletSpecificId,
            level=AccessType.NONE,
            user=thisUser
        )
        userId = list(FolderModel().find(
            query={
                'parentId': ciphered['_id'],
                'parentCollection': 'folder',
                'name': 'userID'
            }
        ))
    except:
        return(None)
    try:
        cUser = str(
            userId[0]['meta']['user']['@id']
        ) if len(userId) and type(
            userId[0]
        ) == dict and userId[0].get('meta').get('user').get('@id') else None
        FolderModel().setUserAccess(
            doc=ciphered,
            user=UserModel().load(id=cUser, user=cUser),
            level=AccessType.READ,
            save=True,
            currentUser=thisUser,
            force=True
        )
        return(cUser)
    except:
        return(None)


def getCanonicalUser(user):
    try:
        cUser = [
            u for u in [
                decipherUser(user),
                userByEmail(user),
                canonicalUser(user)
            ] if u is not None
        ]
        return(cUser[0] if len(cUser) else None)
    except:
        return(None)


def getUserCipher(appletAssignment, user):
    """
    Returns an applet-specific user ID.

    Parameters
    ----------
    appletAssignment: Mongo Folder cursor
        Applet folder in Assignments collection

    user: string or list
        applet-specific ID, canonical ID or email address

    Returns
    -------
    user: string
        applet-specific ID
    """
    if not isinstance(user, str):
        return([getUserCipher(appletAssignment, u) for u in list(user)])
    thisUser = getCurrentUser()
    appletAssignments = list(FolderModel().childFolders(
        parent=appletAssignment,
        parentType='folder',
        user=thisUser
    ))
    allCiphers = list(itertools.chain.from_iterable([
        list(FolderModel().find(
            query={
                'parentId': assignment['_id'],
                'parentCollection': 'folder',
                'name': 'userID'
            }
        )) for assignment in appletAssignments
    ])) if len(appletAssignments) else []
    cUser = getCanonicalUser(user)
    aUser = [
        cipher['parentId'] for cipher in allCiphers if (
            cipher['meta']['user']['@id'] == cUser
        ) if cipher.get('meta') and cipher['meta'].get('user') and cipher[
            'meta'
        ]['user'].get('@id') and cipher.get('parentId')
    ] if cUser and len(allCiphers) else []
    aUser = aUser[0] if len(aUser) else createCipher(
        appletAssignment,
        appletAssignments,
        cUser if cUser is not None else user
    )['_id']
    return(str(aUser))


def nextCipher(currentCiphers):
    if not len(currentCiphers):
        return("1")
    nCipher = []
    for c in [
        cipher.get('name') for cipher in currentCiphers if cipher.get(
            'name'
        ) is not None
    ]:
        try:
            nCipher.append(int(c))
        except:
            nCipher.append(0)
    return(str(max(nCipher)+1))


def userByEmail(email):
    try:
        userId = list(UserModel().find(
            query={
                'email': email
            }
        ))
    except:
        return(None)
    try:
        return(
            str(
                userId[0]['_id']
            ) if len(userId) and '_id' in userId[0] else None
        )
    except:
        return(None)
