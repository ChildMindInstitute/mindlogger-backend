# -*- coding: utf-8 -*-
import datetime
import json
import os

from bson.objectid import ObjectId
from girderformindlogger.constants import AccessType, DEFINED_RELATIONS, PROFILE_FIELDS
from girderformindlogger.exceptions import ValidationException, AccessException
from girderformindlogger.models.aes_encrypt import AESEncryption, AccessControlledModel
from girderformindlogger.utility.progress import noProgress
from girderformindlogger.constants import USER_ROLES


class Profile(AESEncryption, dict):
    """
    Profiles store customizable information specific to both users and applets.
    These data can be sensitive and are access controlled.
    """

    def initialize(self):
        self.name = 'appletProfile'
        self.ensureIndices(
            (
                'appletId',
                'userId',
                'individual_events',
                'completed_activities',
                'reviewers',
                'MRN',
                'updated',
                ([
                    ('appletId', 1),
                    ('roles', 1),
                    ('MRN', 1),
                ], {})
            )
        )

        self.exposeFields(level=AccessType.READ, fields=(
            '_id', 'created', 'updated', 'meta', 'appletId',
            'parentCollection', 'creatorId', 'baseParentType', 'baseParentId'
        ))

        self.initAES([
            ('firstName', 64),
            ('lastName', 64),
            ('userDefined.displayName', 64),
            ('coordinatorDefined.displayName', 64),
            ('cachedDisplay.manager.displayName', 64)
        ])

    def display(self, p, role):
        """
        :param p: Profile
        :type p: dict
        :param role: role
        :type role: string
        :returns: dict
        """
        prof = {
            k: v for k, v in p.get("coordinatorDefined", {}).items() if (
                v is not None and (
                    role is not 'user' or k is not 'email'
                )
            )
        }
        prof.update({
            k: v for k, v in p.get("userDefined", {}).items() if (
                v is not None and (
                    role is not 'user' or k is not 'email'
                )
            )
        })
        return(prof)

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
            'appletId',
            'userId'
        }
        loadFields = self._supplementFields(fields, extraFields)

        doc = super(Profile, self).load(
            id=id, level=level, user=user, objectId=objectId, force=force,
            fields=loadFields, exc=exc
        )

        if doc is not None:
            for key in ["coordinatorDefined", "userDefined"]:
                if key not in doc:
                    doc[key] = {}
                    self.update({'_id': doc['_id']}, {'$set': {
                        key: {}
                    }})

            self._removeSupplementalFields(doc, fields)

        return doc

    def coordinatorProfile(self, appletId, coordinator):
        from girderformindlogger.models.applet import Applet

        if isinstance(coordinator, dict) and "userId" not in coordinator:
            coordinator = self.createProfile(
                appletId,
                coordinator,
                "coordinator"
            )
        return(self.cycleDefinitions(
            coordinator,
            showEmail=True
        ) if Applet().isCoordinator(
            appletId,
            coordinator
        ) else {})

    def _canonicalUser(self, appletId, user):
        from girderformindlogger.models.user import User

        if isinstance(user, dict):
            userId = str(user['_id'])
            user = User().load(userId, force=True)
            profile = self.load(userId, force=True)
            return(user if user is not None else (
                User().load(
                    str(profile['userId']),
                    force=True
                ) if (isinstance(profile, dict) and 'userId' in profile) else {}
            ))
        if isinstance(user, str):
            try:
                return(
                    self._canonicalUser(
                        appletId,
                        User().load(user, force=True)
                    )
                )
            except:
                return(
                    self._canonicalUser(
                        appletId,
                        self.load(user, force=True)
                    )
                )

    def cycleDefinitions(self, userProfile, showEmail=False, showIDCode=False):
        """
        :param userProfile: Profile or Invitation
        :type userProfile: dict
        :param showEmail: Show email in profile?
        :type showEmail: bool
        :returns dict: display profile
        """
        profileFields = PROFILE_FIELDS

        if showEmail and not userProfile.get('email_encrypted', False):
            profileFields.append('email')

        displayProfile = userProfile.get("coordinatorDefined", {})
        displayProfile.update(userProfile.get("userDefined", {}))

        displayProfile.update({
            k: v for k, v in userProfile.items(
            ) if k in profileFields
        })

        if showIDCode:
            from girderformindlogger.models.ID_code import IDCode

            profileFields.append('idCodes')
            profileFields.append('idCode')
            if userProfile.get('profile', False):
                displayProfile.update({
                    "idCodes": IDCode().findIdCodes(
                        userProfile['_id']
                    )
                })
            if userProfile.get('code', False):
                displayProfile.update({
                    "idCode": userProfile.get('code')
                })

        return({
            k: v if v!="" else None for k, v in displayProfile.items(
            ) if k in profileFields and v is not None
        })

    def profileAsUser(self, profile, requester):
        from girderformindlogger.models.applet import Applet as AppletModel
        return(self.cycleDefinitions(
            profile,
            showEmail=any([
                AppletModel().isCoordinator(profile['appletId'], requester),
                str(requester['_id'])==str(profile.get('userId'))
            ]),
            showIDCode=any([
                AppletModel().isCoordinator(profile['appletId'], requester),
                AppletModel()._hasRole(
                    profile['appletId'],
                    requester,
                    'reviewer'
                )
            ])
        ))

    def displayProfileFields(
        self,
        profile,
        user=None,
        forceManager=False,
        forceReviewer=False
    ):
        """
        :param profile: Profile or Invitation
        :type profile: dict
        :param user: user requesting profile
        :type user: dict
        :returns dict: display profile
        """
        import threading

        loadingMessage = '{loading}…'
        if 'cachedDisplay' in profile:
            if forceManager:
                if 'manager' in profile['cachedDisplay']:
                    return(profile['cachedDisplay']['manager'])
            if forceReviewer:
                if 'reviewer' in profile['cachedDisplay']:
                    return(profile['cachedDisplay']['reviewer'])
        else:
            profile['cachedDisplay'] = {}

        thread = threading.Thread(
            target=self._cacheProfileDisplay,
            args=(profile, user, forceManager, forceReviewer)
        )
        thread.start()
        return({
            '_id': profile['_id'],
            'displayName': loadingMessage,
            'email': None,
            'idCodes': [loadingMessage]
        })


    def _cacheProfileDisplay(
        self,
        profile,
        user,
        forceManager=False,
        forceReviewer=False
    ):
        from girderformindlogger.models.applet import Applet
        profileDefinitions = self.cycleDefinitions(
            profile,
            showEmail=forceManager if forceManager else Applet(
            ).isCoordinator(profile['appletId'], user),
            showIDCode=forceReviewer if forceReviewer else Applet(
            ).isCoordinator(profile['appletId'], user)
        )

        if 'invitedBy' in profile:
            profileDefinitions['invitedBy'] = self.cycleDefinitions(
                profile['invitedBy'],
                showEmail=False
            )

        if forceManager and not forceReviewer:
            profile['cachedDisplay']['manager'] = profileDefinitions
            self.save(profile, validate=False)
        elif forceReviewer:
            profile['cachedDisplay']['reviewer'] = profileDefinitions
            self.save(profile, validate=False)
        print(profileDefinitions)
        return(profileDefinitions)

    def getProfile(self, id, user):
        from girderformindlogger.models.applet import Applet as AppletModel
        from girderformindlogger.models.ID_code import IDCode
        from bson.errors import InvalidId

        if not isinstance(id, ObjectId):
            try:
                id = ObjectId(id)
            except InvalidId:
                p = None
        if isinstance(id, ObjectId):
            p = self.findOne({'_id': id})
        if p is None:
            ps = IDCode().findProfile(id)
            if ps is not None:
                ps = [
                    self.profileAsUser(p, user) for p in ps if p is not None
                ]
                return(ps[0] if len(ps)==1 and ps[0] is not None else ps)
            else:
                from girderformindlogger.models.invitation import Invitation
                from girderformindlogger.utility.jsonld_expander import        \
                    oidIffHex
                inv = Invitation().findOne({'$or': [
                    {'_id': {'$in': oidIffHex(id)}},
                    {'idCode': id}
                ]})
                return(
                    self.profileAsUser(
                        inv,
                        user
                    ) if isinstance(inv, dict) else {}
                )
        return(self.profileAsUser(self.load(p['_id'], force=True), user))

    def getSubjectProfile(self, id, displayName, user):
        from girderformindlogger.models.applet import Applet as AppletModel
        from girderformindlogger.models.ID_code import IDCode

        p = None
        ps = IDCode().findProfile(id)
        if ps is not None:
            ps = [self.profileAsUser(p, user) for p in ps if p is not None]
            ps = [p for p in ps if p is not None and p.get(
                'displayName'
            )==displayName]
            if len(ps):
                return(ps[0])
        else:
            try:
                id = ObjectId(id)
                p = self.profileAsUser(
                    self.findOne({
                        '_id': id,
                        '$or': [
                            {'coordinatorDefined.displayName': displayName},
                            {'userDefined.displayName': displayName}
                        ]
                    }),
                    user
                )
            except:
                p = None
        return(p)

    def updateProfile(self, profileId, user, profileUpdate):
        from copy import deepcopy
        from girderformindlogger.models.applet import Applet
        profile = self.load(profileId, force=True)
        if str(user["_id"]==profile["userId"]):
            update = deepcopy(profile.get("userDefined", {}))
            update.update(profileUpdate)
            profile["userDefined"] = update
        elif Applet().isCoordinator(
            profile["appletId"],
            user
        ):
            update = deepcopy(profile.get("coordinatorDefined", {}))
            update.update(profileUpdate)
            profile["coordinatorDefined"] = update
        else:
            raise AccessException(
                "You do not have adequate permissions to update this profile."
            )
        return self.save(profile, validate=False)

    def updateProfiles(self, user, data):
        data = {'$set': data}
        try:
            self.update(query={
                'userId': {
                    '$in': [user['_id']]
                },
                'profile': True
            }, update=data, multi=True)
        except ValueError as e:
            print("Error  while updating Profile")

    def updateProfileBadgets(self, profiles):
        self.increment(query={
            '_id': {
                '$in': [profile['_id'] for profile in profiles]
            }
        }, field='badge', amount=1)

    def updateRelations(self, profileId):
        relations = list(self.find({
            '$or': [{
                'schema:knows.{}'.format(rel): profileId
            } for rel in DEFINED_RELATIONS.keys()]
        }))

    def _updateDescendants(self, folderId, updateQuery):
        """
        This helper is used to update all items and folders underneath a
        profile. This is expensive, so think carefully before using it.

        :param folderId: The _id of the profile at the root of the subtree.
        :param updateQuery: The mongo query to apply to all of the children of
        the profile.
        :type updateQuery: dict
        """
        from girderformindlogger.models.item import Item

        self.update(query={
            'appletId': folderId,
            'parentCollection': 'profile'
        }, update=updateQuery, multi=True)
        Item().update(query={
            'folderId': folderId,
        }, update=updateQuery, multi=True)

        q = {
            'appletId': folderId,
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

        descendant = self.load(descendant['appletId'], force=True)

        if descendant is None:
            return False

        return self._isAncestor(ancestor, descendant)

    def remove(self, folder, progress=None, **kwargs):
        """
        Delete a profile recursively.

        :param profile: The profile document to delete.
        :type folder: dict
        :param progress: A progress context to record progress on.
        :type progress: girderformindlogger.utility.progress.ProgressContext or
            None.
        """
        # Remove the contents underneath this folder recursively.
        from girderformindlogger.models.upload import Upload

        # self.clean(folder, progress, **kwargs)

        # Delete pending uploads into this folder
        uploadModel = Upload()
        uploads = uploadModel.find({
            'appletId': folder['_id'],
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
        from girderformindlogger.models.item import Item

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

        parentType = self._verify_parentType(parentType)

        q = {
            'appletId': parent['_id'],
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
                     public=None, creator=None, allowRename=False,
                     reuseExisting=False):
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
                'appletId': parent['_id'],
                'name': name,
                'parentCollection': parentType
            })

            if existing:
                return existing

        parentType = self._verify_parentType(parentType)

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
            'appletId': ObjectId(parent['_id']),
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

    def getProfileData(self, profile, viewer):
        isUser = len(profile.get('roles', [])) <= 1

        if viewer['appletId'] != profile['appletId']:
            return None

        if not isUser:
            fields = ['_id', 'updated', 'roles', 'firstName', 'lastName', 'email']
        else:
            fields = ['_id', 'updated', 'roles', 'MRN']

        data = {
            field: profile.get(field, '') for field in fields
        }

        data['pinned'] = viewer['_id'] in profile.get('pinnedBy', [])
        if profile.get('deactivated', False):
            return None

        # these are temporary
        if 'email' in fields and not data['email']:
            data['email'] = profile.get('userDefined', {}).get('email', '')

        if 'firstName' in fields and not data['firstName']:
            data['firstName'] = profile.get('userDefined', {}).get('displayName', '')

        # reviewers don't need to view user's roles
        if 'coordinator' not in viewer['roles'] and 'manager' not in viewer['roles']:
            if viewer['_id'] not in profile.get('reviewers', []):
                return None

            data.pop('roles')

        if 'coordinator' in viewer['roles']:
            data['hasIndividualEvent'] = (profile.get('individual_events', 0) > 0)

        data['viewable'] = False
        if viewer['_id'] in profile.get('reviewers', []) or viewer['_id'] == profile['_id']:
            data['refreshRequest'] = profile.get('refreshRequest', None)
            data['viewable'] = True

        data['updated'] = None
        for userActivityUpdate in profile.get('completed_activities', []):
            if userActivityUpdate['completed_time'] and (not data['updated'] or data['updated'] < userActivityUpdate['completed_time']):
                data['updated'] = userActivityUpdate['completed_time']

        if 'roles' in data and 'manager' in data['roles']:
            if 'owner' in data['roles']:
                data['roles'] = ['owner']
            elif 'manager' in data['roles']:
                data['roles'] = ['manager']

        return data

    def generateMissing(self, applet):
        """
        Helper function to generate profiles for users that predate this class.
        To be threaded unless no users with profiles exist.

        :param applet: Applet to get users for.
        :type applet: dict
        :returns: list of dicts
        """
        from girderformindlogger.models.applet import Applet
        from girderformindlogger.models.user import User as UserModel

        # get groups for applet
        appletGroups = Applet().getAppletGroups(applet)

        userList = {
            role: {
                groupId: {
                    'active': list(UserModel().find(
                        query={"groups": {
                            "$in": [
                                ObjectId(
                                    groupId
                                )
                            ]
                        }},
                        fields=['_id']
                    ))
                } for groupId in appletGroups[role].keys()
            } for role in appletGroups.keys()
        }

        # restructure dictionary & return
        userList = {
            str(ulu["user"]["_id"]): {k: v for k, v in {
                "displayName": ulu["user"].get(
                    "coordinatorDefined",
                    {}
                ).get("displayName", ulu["user"].get(
                    "userDefined",
                    {}
                ).get("displayName", ulu["user"].get("displayName"))),
                "groups": ulu.get("groups")
            }.items() if v is not None} for ulu in [{
                "user": self.createProfile(
                    applet,
                    UserModel().load(user, AccessType.READ, force=True)
                ),
                "groups": [{
                        "_id": groupId,
                        "name": appletGroups[role][groupId],
                        "status": status,
                        "role": role
                } for role in userList for groupId in userList[
                    role
                ] for status in userList[role][groupId]]
            } for user in set([
                ui.get('_id') for u in (
                    userList[role][groupId][
                        status
                    ] for role in userList for groupId in userList[
                        role
                    ] for status in userList[role][groupId]
                ) for ui in u
            ])]
        }
        return(userList)

    def updateOwnerProfile(self, applet):
        from girderformindlogger.models.account_profile import AccountProfile

        accountId = applet.get('accountId', None)
        if not accountId:
            return
        owner = AccountProfile().getOwner(accountId)

        appletProfile = self.findOne({'userId': owner['userId'], 'appletId': applet['_id']})
        appletProfile['roles'] = list(USER_ROLES.keys())
        appletProfile['roles'].append('owner')

        return self.save(appletProfile, validate=False)

    # isMRNList - if true, content of users array is mrn list
    def updateReviewerList(self, reviewer, users=None, operation='replace', isMRNList=False):
        profiles = self.find({'appletId': reviewer['appletId']})

        if isMRNList and users:
            MrnToProfileId = {}
            for profile in profiles:
                if 'MRN' in profile:
                    MrnToProfileId[profile['MRN']] = profile['_id']

            users = [
                MrnToProfileId[MRN] for MRN in users if MRN in MrnToProfileId
            ]

        for profile in profiles:
            if reviewer['_id'] == profile['_id']:
                continue

            if operation == 'delete': # delete
                if users and profile['_id'] in users and reviewer['_id'] in profile['reviewers']:
                    profile['reviewers'].remove(reviewer['_id'])
                    self.update({
                        '_id': profile['_id']
                    }, {
                        '$set': {
                            'reviewers': profile['reviewers']
                        }
                    })

            else:   # add/replace
                if reviewer['_id'] not in profile.get('reviewers', []):
                    if users is None or profile['_id'] in users and operation:
                        self.update({
                            '_id': profile['_id']
                        }, {
                            '$push': {
                                'reviewers': reviewer['_id']
                            }
                        }, multi=False)

                elif operation == 'replace':
                    if users is not None and profile['_id'] not in users:
                        profile['reviewers'].remove(reviewer['_id'])
                        self.update({
                            '_id': profile['_id']
                        }, {
                            '$set': {
                                'reviewers': profile['reviewers']
                            }
                        })

    def getReviewerListForUser(self, appletId, userProfile, user):
        reviewers = []
        for reviewer in userProfile['reviewers']:
            reviewers.append(self.displayProfileFields(self.findOne({'_id': reviewer}), user, forceManager=True))

        return reviewers

    def createProfile(self, applet, user, role="user"):
        """
        Create a new profile to store information specific to a given (applet ∩
            user)

        :param applet: The applet for which this profile exists
        :type applet: dict
        :param user: The user for which this profile exists
        :type user: dict
        :returns: The profile document that was created.
        """
        from girderformindlogger.models.applet import Applet
        from girderformindlogger.models.group import Group

        if not isinstance(applet, dict):
            applet = Applet().load(applet, force=True)
        user = self._canonicalUser(applet["_id"], user)
        returnFields=["_id", "appletId", "coordinatorDefined", "userDefined"]
        existing = self.findOne(
            {
                'appletId': applet['_id'],
                'userId': user['_id'],
                'profile': True
            },
            fields=[
                *returnFields, "deactivated"
            ]
        )

        if applet['_id'] not in [
            a.get('_id') for a in Applet().getAppletsForUser(role, user)
        ]:
            appletGroups=Applet().getAppletGroups(applet)

            roles = ['user', 'editor', 'reviewer', 'coordinator', 'manager'] if role == 'manager' else [role]
            if 'user' not in roles:
                roles.append('user')

            for role in roles:
                groups = appletGroups.get(role)
                if bool(groups):
                    group = Group().load(
                        ObjectId(list(groups.keys())[0]),
                        force=True
                    )

                    if group['_id'] not in user.get('groups', []):
                        Group().inviteUser(group, user, level=AccessType.READ)
                        Group().joinGroup(group, user)
                else:
                    raise ValidationException(
                        "User does not have role \"{}\" in this \"{}\" applet "
                        "({})".format(
                            role,
                            Applet().preferredName(applet),
                            str(applet['_id'])
                        )
                    )

        if existing and not existing.get('deactivated', False):
            if "deactivated" in existing:
                existing.pop("deactivated")

            return existing

        now = datetime.datetime.utcnow()

        managers = list(self.find(query={'appletId': applet['_id'], 'roles': 'manager'}, fields=['_id']))
        profile = {
            k: v for k, v in {
                'appletId': ObjectId(applet['_id']),
                'userId': ObjectId(user['_id']),
                'profile': True,
                'badge': 0,
                'created': now,
                'updated': now,
                'deviceId': user['deviceId'],
                'timezone': user['timezone'],
                'individual_events': 0,
                'completed_activities': [
                    {
                        'activity_id': activity_id, 'completed_time': None
                    } for activity_id in applet.get('meta', {}).get('protocol', {}).get('activities', [])
                ],
                'accountId': applet.get('accountId', None),
                'size': 0,
                'coordinatorDefined': {},
                'userDefined': {
                    'displayName': user.get(
                        'displayName',
                        user.get('firstName')
                    ),
                    'email': user.get('email') if not user.get('email_encrypted', None) else ''
                },
                'reviewers': [
                    manager['_id'] for manager in managers
                ],
                'firstName': user['firstName'],
                'lastName': user['lastName']
            }.items() if v is not None
        }

        if role != 'user' and not user.get('email_encrypted', True):
            profile['email'] = user['email']

        if existing:
            profile['_id'] = existing['_id']

        self.setPublic(profile, False, save=False)

        # Save the profile.
        self.save(profile, validate=False)
        return({
            k: v for k, v in profile.items(
            ) if k in returnFields
        })

    def createPassiveProfile(self, appletId, code, displayName, coordinator):
        """
        Create a new profile to store information specific to a given (applet ∩
            passive individual)

        :param applet: The applet for which this profile exists
        :type applet: dict
        :param code: A data ID code for the passive individual
        :type code: str
        :param displaName: The display name for the passive individual
        :type displayName: str
        :returns: The profile document that was created.
        """
        from girderformindlogger.models.ID_code import IDCode
        returnFields=["_id", "appletId", "coordinatorDefined", "userDefined"]

        now = datetime.datetime.utcnow()
        appletId = ObjectId(appletId)
        profile = {
            k: v for k, v in {
                'appletId': appletId,
                'userId': now,
                'profile': True,
                'created': now,
                'updated': now,
                'size': 0,
                'coordinatorDefined': {
                    'displayName': displayName
                },
                'createdBy': self.coordinatorProfile(
                    appletId,
                    coordinator
                )
            }.items() if v is not None
        }

        self.setPublic(profile, False, save=False)

        # Save the profile.
        self.save(profile, validate=False)

        IDCode().createIdCode(profile, code)

        return({
            k: v for k, v in self.load(profile['_id'], force=True).items(
            ) if k in returnFields
        })

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
            'appletId': folder['_id'],
            'parentCollection': 'profile'
        }, fields=fields, user=user, level=level)

        return len(folders)

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
            'appletId': folder['_id'],
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
        from girderformindlogger.models.item import Item

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
                'appletId': doc['_id'],
                'parentCollection': 'profile'
            }, user=user, level=AccessType.ADMIN)

            for folder in subfolders:
                self.setAccessList(
                    folder, access, save=True, recurse=True, user=user,
                    progress=progress, setPublic=setPublic, publicFlags=publicFlags, force=force)

        return doc

    def deactivateProfile(self, applet_id, user_id):
        """
        deactivate profile from applet_id, user_id
        at the moment, this is used in deactivateApplet
        """
        if not applet_id and not user_id:
            return

        query = {}
        if applet_id:
            query['appletId'] = ObjectId(applet_id)
        if user_id:
            query['userId'] = ObjectId(user_id)

        self.update(query, {'$set': {'deactivated': True}})

    def get_profiles_by_applet_id(self, applet_id):
        return list(self.find(
            query={
                'appletId': ObjectId(applet_id),
                'userId': {
                    '$exists': True
                },
                'profile': True
            }
        ))

    def get_profiles_by_ids(self, profile_ids):
        return self.find(
            query={
                '_id': {
                    '$in': profile_ids
                },
                'userId': {
                    '$exists': True
                },
                'profile': True
            }
        )

    def get_profiles_by_user_ids(self, user_ids):
        return self.find(
            query={
                'userId': {
                    '$in': user_ids
                },
                'profile': True
            }
        )

    def update_profile_activities_by_applet_id(self, applet, activities):
        self.update({
            'appletId': ObjectId(applet['_id'])
        }, {
            '$set': {
                'completed_activities': [
                    {
                        'activity_id': activity_id,
                        'completed_time': None
                    } for activity_id in activities
                ]
            }
        })
