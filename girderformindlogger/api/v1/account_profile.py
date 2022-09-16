# -*- coding: utf-8 -*-
from ..rest import Resource
from ..describe import Description, autoDescribeRoute
from girderformindlogger.api import access
from girderformindlogger.models.account_profile import AccountProfile as AccountProfileModel
from girderformindlogger.constants import AccessType, SortDir, TokenScope,     \
    DEFINED_INFORMANTS, REPROLIB_CANONICAL, SPECIAL_SUBJECTS, USER_ROLES
from girderformindlogger.models.profile import Profile as ProfileModel
from girderformindlogger.models.response_alerts import ResponseAlerts
from pymongo import DESCENDING, ASCENDING
from bson.objectid import ObjectId

USER_ROLE_KEYS = USER_ROLES.keys()

class AccountProfile(Resource):
    """API Endpoint for managing account data in the system."""

    def __init__(self):
        super(AccountProfile, self).__init__()
        self.resourceName = 'account'
        self._model = AccountProfileModel()

        self.route('GET', ('users',), self.getUsers)
        self.route('GET', ('permissions', ), self.getPermissions)
        self.route('PUT', (':id',), self.updateAccountDB)
        self.route('PUT', ('manage', 'pin', ), self.updatePin)
        self.route('PUT', ('updateAlertStatus', ':id', ), self.updateAlertStatus)

    @access.user(scope=TokenScope.DATA_OWN)
    @autoDescribeRoute(
        Description('Update view status for alerts.')
        .notes(
            'This endpoint is used for reviewer/manager to update view status for notifications. <br>'
        )
        .param(
            'id',
            'id of alert to update status',
            required=True
        )
    )
    def updateAlertStatus(self, id):
        accountProfile = self.getAccountProfile()

        ResponseAlerts().update({
            'reviewerId': accountProfile['userId'],
            'accountId': accountProfile['accountId'],
            '_id': ObjectId(id)
        }, {
            '$set': {
                'viewed': True
            }
        })

    @access.user(scope=TokenScope.DATA_OWN)
    @autoDescribeRoute(
        Description('Get permission on account')
        .notes(
            'This endpoint is used for getting permissions of a user on account'
        )
        .param(
            'accountId',
            'id of account',
            required=True
        )
        .param(
            'appletId',
            'id of applet',
            required=False
        )
    )
    def getPermissions(self, accountId, appletId):
        viewer = self.getCurrentUser()
        accountProfile = self.getAccountProfile()

        if accountProfile['accountId'] != ObjectId(accountId):
            return []

        permissions = []
        if appletId:
            profile = ProfileModel().findOne({
                'userId': viewer['_id'],
                'appletId': ObjectId(appletId)
            })

            if not profile:
                return []

            permissions = profile['roles']
        else:
            for permission in ['user', 'coordinator', 'editor', 'manager', 'owner']:
                if len(accountProfile['applets'].get(permission, [])) > 0:
                    permissions.append(permission)

        return permissions

    @access.user(scope=TokenScope.DATA_OWN)
    @autoDescribeRoute(
        Description('Update pin status.')
        .notes(
            'this endpoint is used for reviewer/manager/coordinators to update pin status. <br>'
        )
        .param(
            'profileId',
            'user profile id to update pin status',
            required=True,
            strip=True
        )
        .param(
            'newState',
            'if true, pin user',
            required=True,
            default=True,
            dataType='boolean'
        )
    )
    def updatePin(self, profileId, newState):
        viewer = self.getCurrentUser()
        accountProfile = self.getAccountProfile()

        profile = ProfileModel().findOne({
            '_id': ObjectId(profileId)
        })

        userProfiles = list(ProfileModel().find({
            'userId': profile['userId'],
            'accountId': accountProfile['accountId'],
            'deactivated': {'$ne': True}
        }))

        for profile in userProfiles:
            viewerProfile = ProfileModel().findOne({
                'appletId': profile['appletId'],
                'userId': viewer['_id'],
                'deactivated': {'$ne': True},
            })

            if not viewerProfile:
                continue

            viewerRoles = viewerProfile.get('roles', [])
            if 'coordinator' in viewerRoles or 'manager' in viewerRoles or 'reviewer' in viewerRoles and viewerProfile['_id'] in profile.get('reviewers', []):
                if 'pinnedBy' not in profile:
                    profile['pinnedBy'] = []

                if newState and viewerProfile['_id'] not in profile['pinnedBy']:
                    profile['pinnedBy'].append(viewerProfile['_id'])

                if not newState and viewerProfile['_id'] in profile['pinnedBy']:
                    profile['pinnedBy'].remove(viewerProfile['_id'])

                ProfileModel().update({
                    '_id': profile['_id']
                }, {
                    '$set': {
                        'pinnedBy': profile['pinnedBy']
                    }
                })

    @access.user(scope=TokenScope.DATA_OWN)
    @autoDescribeRoute(
        Description('Get userlist.')
        .notes(
            'this endpoint is used to get user-list for an account. <br>'
        )
        .param(
            'appletId',
            'if set, get result for only specified applet',
            default=None,
            required=False,
        )
        .param(
            'role',
            'One of ' + str(USER_ROLE_KEYS),
            default='user',
            required=False,
            strip=True
        )
        .param(
            'MRN',
            'string to be used as a filter for MRN',
            default='',
            required=False,
            strip=True
        )
        .jsonParam(
            'sort',
            'field to be used for sorting users: sortBy, sortDesc fields are available',
            required=False,
        )
        .jsonParam(
            'pagination',
            'pagination info - allow, pageIndex, recordsPerPage fields are available',
            required=False
        )
    )
    def getUsers(self, appletId, role='user', MRN='', sort=None, pagination=None):
        accountProfile = self.getAccountProfile()

        applets = [ObjectId(appletId)] if appletId else accountProfile['applets'].get('user', [])

        # prepare profiles for reviewer to use for checking permission
        viewerProfileByApplet = {}
        viewerProfiles = list(ProfileModel().find({
            'accountId': accountProfile['accountId'],
            'appletId': {
                '$in': applets
            },
            'userId': accountProfile['userId']
        }))

        for profile in viewerProfiles:
            if 'reviewer' in profile['roles'] or 'coordinator' in profile['roles'] or 'manager' in profile['roles']:
                viewerProfileByApplet[str(profile['appletId'])] = profile

        # define sort rule
        sortRule = []
        if sort and sort.get('allow', True):
            sortRule.append((sort.get('sortBy', 'updated'), DESCENDING if sort.get('sortDesc', True) else ASCENDING))

        if not len(sortRule):
            sortRule = [('updated', DESCENDING)]

        userProfiles = []

        # get user profiles
        for pinStatus in ['pinned', 'unpinned']:
            for appletId in viewerProfileByApplet:
                if role != 'user' and 'manager' not in viewerProfileByApplet[appletId].get('roles', []):
                    continue

                query = {
                    'accountId': accountProfile['accountId'],
                    'appletId': ObjectId(appletId),
                    'roles': role
                }

                if role == 'user' and MRN:
                    if MRN == 'None' or MRN == 'none':
                        query['MRN'] = {
                            '$exists': False
                        }
                    else:
                        query['$or'] = [ {
                                'MRN': {
                                    '$regex': f'{MRN}',
                                    '$options' :'i'
                                },
                            }, {
                                'identifiers': {
                                    '$regex': f'{MRN}',
                                    '$options' :'i'
                                }
                            }
                        ]

                if pinStatus == 'pinned':
                    query['pinnedBy'] = viewerProfileByApplet[appletId]['_id']

                userProfiles = userProfiles + list(ProfileModel().find(
                    query,
                    sort=sortRule,
                    hint={
                        'appletId': 1,
                        'roles': 1,
                        'MRN': 1
                    }
                ))

        userIndex = {}
        users = []

        # format and group profiles
        for profile in userProfiles:
            userId = str(profile['userId'])
            appletId = str(profile['appletId'])
            viewer = viewerProfileByApplet[appletId]

            if role == 'user' and len(profile.get('roles', [])) > 1:
                continue

            if 'manager' in profile['roles'] and role != 'manager':
                continue

            data = ProfileModel().getProfileData(profile, viewer)

            if not data:
                continue

            # user might use several applets in one account
            if userId not in userIndex:
                userIndex[userId] = len(users)

                users.append({
                    appletId: data
                })
            else:
                users[userIndex[userId]][appletId] = data

        skip = 0
        limit = len(users)

        if pagination and pagination.get('allow', False) and 'pageIndex' in pagination and 'recordsPerPage' in pagination:
            if pagination['recordsPerPage'] > 0:
                skip = pagination['pageIndex'] * pagination['recordsPerPage']
                limit = pagination['recordsPerPage']

        return {
            'items': users[skip: skip + limit],
            'total': len(users)
        }

    @access.user(scope=TokenScope.DATA_WRITE)
    @autoDescribeRoute(
        Description('Update profile personal db uri')
        .param('id', 'account id', required=True)
        .param('dbURL', 'db uri for store the user responses', default=False, required=True)
        .jsonParam('data', 'A JSON object containing the arbitrary bucket information to add', paramType='body', requireObject=True)
    )
    def updateAccountDB(self, id, dbURL, data):
        account = self._model.findOne({"accountId": ObjectId(id)})
        self._model.validateDBURL(dbURL)
        accessKeyId = None
        bucketType = None
        s3Bucket = None
        secretAccessKey = None

        if (data.get('bucket_type').lower() == 'azure'):
            bucketType = data.get('bucket_type').lower()
            s3Bucket = data.get('storage_account_name')
            secretAccessKey = data.get('connection_string')

        elif (data.get('bucket_type').lower() == 'gcp'):
            bucketType = data.get('bucket_type').lower()
            s3Bucket = data.get('bucket_name')
            accessKeyId = data.get('access_key')
            secretAccessKey = data.get('secret_access_key')

        else:
            s3Bucket = data.get('bucket_name')
            accessKeyId = data.get('access_key')
            secretAccessKey = data.get('secret_access_key')

        account.update({
           'db': dbURL,
           's3Bucket': s3Bucket,
           'accessKeyId': accessKeyId,
           'secretAccessKey': secretAccessKey,
           'bucketType': bucketType
        })
        self._model.save(account, validate=False)
        return 'Information has been saved successfully.'