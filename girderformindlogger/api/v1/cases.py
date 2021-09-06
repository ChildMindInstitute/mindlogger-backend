#!/usr/bin/env python
# -*- coding: utf-8 -*-

from ..rest import Resource
from ..describe import Description, autoDescribeRoute
from girderformindlogger.api import access
from girderformindlogger.models.account_profile import AccountProfile as AccountProfileModel
from girderformindlogger.constants import AccessType, SortDir, TokenScope,     \
    DEFINED_INFORMANTS, REPROLIB_CANONICAL, SPECIAL_SUBJECTS, USER_ROLES
from girderformindlogger.models.profile import Profile as ProfileModel
from girderformindlogger.models.cases import CaseModel
from girderformindlogger.models.caseUsers import CaseUser
from girderformindlogger.models.entries import EntryModel
from girderformindlogger.models.user import User
from girderformindlogger.models.applet import Applet as AppletModel
from girderformindlogger.exceptions import AccessException, ValidationException
from pymongo import DESCENDING, ASCENDING
from bson.objectid import ObjectId

from pyld import jsonld
from girderformindlogger.utility.validate import validator, email_validator, symbol_validator

USER_ROLE_KEYS = USER_ROLES.keys()


class Cases(Resource):

    def __init__(self):
        super(Cases, self).__init__()
        self.resourceName = 'cases'
        self._model = CaseModel()

        self.route('GET', ('list',), self.getCases)
        self.route('POST', (), self.createCase)
        self.route('GET', (':id', ), self.getCase)
        self.route('PUT', (':id', 'applets', 'add'), self.addApplets)
        self.route('DELETE', (':id', ), self.deleteCase)
        self.route('GET', (':id', 'users', 'list'), self.getLinkedUsers)
        self.route('POST', (':id', 'users', 'add'), self.linkUser)
        self.route('PUT', (':id', 'users', 'update'), self.updateLinkedUser)
        self.route('DELETE', (':id', 'users', 'delete'), self.unlinkUser)
        self.route('GET', (':id', 'entries', 'list'), self.getEntries)
        self.route('POST', (':id', 'entries', 'add'), self.addEntry)
        self.route('DELETE', (':id', 'entries', 'delete'), self.deleteEntry)

    @access.user(scope=TokenScope.DATA_WRITE)
    @autoDescribeRoute(
        Description('Get a case with specified id.')
        .param(
            'id',
            'id of case',
            required=True
        )
    )
    def getCase(self, id):
        user = self.getCurrentUser()
        accountProfile = self.getAccountProfile()

        accountApplets = accountProfile.get('applets', {})

        document = self._model.findOne({'_id': ObjectId(id)})

        if not document:
            raise ValidationException('unable to find a case with specified id')

        applets = []
        for role in ['manager', 'coordinator', 'reviewer']:
            for appletId in accountApplets.get(role, []):
                if appletId not in applets:
                    applets.append(appletId)

        hasPermission = True if len(document['applets']) else False
        for appletId in document['applets']:
            if appletId in applets:
                hasPermission = True

        if not hasPermission:
            raise AccessException('permission denied')

        entries = EntryModel().getEntries(id, applets)
        users = CaseUser().getLinkedUsers(id)

        result = self._model.getCaseData(document)
        result['entries'] = entries
        result['users'] = users

        return result

    @access.user(scope=TokenScope.DATA_WRITE)
    @autoDescribeRoute(
        Description('Get cases in current account.')
    )
    def getCases(self):
        account = self.getAccountProfile()

        cases = CaseModel().getCasesForAccount(account['accountId'])

        result = []

        for case in cases:
            hasPermission = False

            if case['applets']:
                for appletId in case['applets']:
                    if appletId in account['applets'].get('coordinator', []) or appletId in account['applets'].get('manager', []) or appletId in account['applets'].get('reviewer', []):
                        hasPermission = True
                        break
            else:
                hasPermission = True

            if hasPermission:
                result.append(case)

        return result

    @access.user(scope=TokenScope.DATA_WRITE)
    @autoDescribeRoute(
        Description('Create case in current account.')
        .param(
            'caseId',
            'id of case',
            required=True
        )
        .jsonParam(
            'applets',
            'array of applet id to link',
            dataType='array',
            required=True
        )
        .jsonParam(
            'password',
            'A JSON object containing information for password of case',
            paramType='form',
            required=False
        )
    )
    def createCase(self, caseId, applets, password):
        user = self.getCurrentUser()
        accountProfile = self.getAccountProfile()

        accountApplets = accountProfile.get('applets', {})

        if not len(accountApplets.get('coordinator', [])) and not len(accountApplets.get('manager', [])):
            raise AccessException('permission denied')

        for appletId in applets:
            if ObjectId(appletId) not in accountApplets.get('coordinator') and ObjectId(appletId) not in accountApplets.get('manager'):
                raise AccessException('permission denied')

        document = self._model.addCase(accountProfile['accountId'], caseId, password, user['_id'], applets)

        return self._model.getCaseData(document)

    @access.user(scope=TokenScope.DATA_WRITE)
    @autoDescribeRoute(
        Description('Create case in current account.')
        .param(
            'id',
            'id of case',
            required=True
        )
        .jsonParam(
            'applets',
            'array of applet id to link',
            dataType='array',
            required=True
        )
        .jsonParam(
            'password',
            'A JSON object containing information for password of case',
            paramType='form',
            required=False
        )
    )
    def addApplets(self, id, applets, password):
        user = self.getCurrentUser()
        accountProfile = self.getAccountProfile()

        accountApplets = accountProfile.get('applets', {})

        case = self._model.findOne({'_id': ObjectId(id)})
        if not case:
            raise ValidationException('unable to find case with specified id')

        for appletId in applets:
            if ObjectId(appletId) not in accountApplets.get('coordinator') and ObjectId(appletId) not in accountApplets.get('manager'):
                raise AccessException('permission denied')

        document = self._model.addAppletsToCase(applets, id, password)
        return self._model.getCaseData(document)

    @access.user(scope=TokenScope.DATA_WRITE)
    @autoDescribeRoute(
        Description('Delete case in an account.')
        .param(
            'id',
            'id of case',
            required=True
        )
        .param(
            'deleteResponse',
            'if true, delete responses for cases',
            dataType='boolean',
            required=False,
            default=False
        )
    )
    def deleteCase(self, id, deleteResponse):
        user = self.getCurrentUser()
        accountProfile = self.getAccountProfile()

        applets = accountProfile.get('applets', {})

        if not len(applets.get('manager', [])):
            raise AccessException('permission denied')

        self._model.deleteCase(id, deleteResponse)

        return {
            'message': 'success'
        }

    @access.user(scope=TokenScope.DATA_WRITE)
    @autoDescribeRoute(
        Description('Get list of linked users for a case.')
        .param(
            'id',
            'id of case',
            required=True
        )
    )
    def getLinkedUsers(self, id):
        user = self.getCurrentUser()
        accountProfile = self.getAccountProfile()

        applets = accountProfile.get('applets', {})
        if not len(applets.get('manager', [])) and not len(applets.get('coordinator', [])):
            raise AccessException('permission denied')

        return CaseUser().getLinkedUsers(id)

    @access.user(scope=TokenScope.DATA_WRITE)
    @autoDescribeRoute(
        Description('Get list of entries for a case.')
        .param(
            'id',
            'id of case',
            required=True
        )
    )
    def getEntries(self, id):
        user = self.getCurrentUser()
        accountProfile = self.getAccountProfile()

        accountApplets = accountProfile.get('applets', {})

        applets = []
        for role in ['manager', 'coordinator', 'reviewer']:
            for appletId in accountApplets[role]:
                if appletId not in applets:
                    applets.append(appletId)

        entries = EntryModel().getEntries(id, applets)

        return entries

    @access.user(scope=TokenScope.DATA_WRITE)
    @autoDescribeRoute(
        Description('Link users to specified case.')
        .param(
            'id',
            'id of case',
            required=True
        )
        .param(
            'profileId',
            'id of user profile',
            required=True
        )
        .jsonParam(
            'applets',
            'array of applet id to link',
            required=True
        )
        .param(
            'MRN',
            'mrn of user',
            required=True
        )
    )
    def linkUser(self, id, profileId, applets, MRN):
        user = self.getCurrentUser()
        accountProfile = self.getAccountProfile()

        accountApplets = accountProfile.get('applets', {})

        case = self._model.findOne({'_id': ObjectId(id)})
        if not case:
            raise ValidationException('unable to find case with specified id')

        for appletId in applets:
            if ObjectId(appletId) not in accountApplets.get('coordinator') and ObjectId(appletId) not in accountApplets.get('manager'):
                raise AccessException('permission denied')

        userModel = User()
        appletModel = AppletModel()
        profileModel = ProfileModel()

        userProfile = profileModel.findOne({ '_id': ObjectId(profileId) })

        profiles = []
        for appletId in applets:
            profile = profileModel.findOne({
                'userId': userProfile['userId'],
                'appletId': ObjectId(appletId),
            })

            if not profile or profile.get('deactivated'):
                # add user to applet
                appletModel.grantAccessToApplet(
                    userModel.findOne({ '_id': ObjectId(userProfile['userId']) }),
                    appletModel.load(appletId, user=user),
                    'user',
                    user,
                    validateEmail=False,
                    MRN=MRN
                )

                profile = profileModel.findOne({
                    'userId': userProfile['userId'],
                    'appletId': ObjectId(appletId),
                })

            profiles.append(profile)

        caseUser = CaseUser().addCaseUser(
            caseId=case['_id'],
            profiles=profiles,
            accountId=userProfile['accountId'],
            userId=userProfile['userId'],
            MRN=MRN
        )

        return CaseUser().getData(caseUser)

    @access.user(scope=TokenScope.DATA_WRITE)
    @autoDescribeRoute(
        Description('Link users to specified case.')
        .param(
            'id',
            'id of case',
            required=True
        )
        .param(
            'userId',
            'id of user profile',
            required=True
        )
        .jsonParam(
            'applets',
            'array of applet id to link',
            required=True
        )
    )
    def updateLinkedUser(self, id, userId, applets):
        user = self.getCurrentUser()
        accountProfile = self.getAccountProfile()
        accountApplets = accountProfile.get('applets', {})

        caseUser = CaseUser().findOne({
            'caseId': ObjectId(id),
            '_id': ObjectId(userId)
        })

        if not caseUser:
            raise ValidationException('unable to find user with specified id')

        oldApplets = [applet['appletId'] for applet in caseUser['applets']]
        newApplets = [ObjectId(appletId) for appletId in applets]

        # check permission for new applets being added
        for appletId in newApplets:
            if appletId not in oldApplets:
                if appletId not in accountApplets.get('coordinator') and appletId not in accountApplets.get('manager'):
                    raise AccessException('permission denied')

        # check permission for old applets being removed
        for appletId in oldApplets:
            if appletId not in newApplets:
                if appletId not in accountApplets.get('coordinator') and appletId not in accountApplets.get('manager'):
                    raise AccessException('permission denied')

        userModel = User()
        appletModel = AppletModel()
        profileModel = ProfileModel()

        profiles = []
        for appletId in newApplets:
            profile = profileModel.findOne({
                'userId': caseUser['userId'],
                'appletId': appletId,
            })

            if not profile or profile.get('deactivated'):
                # add user to applet
                appletModel.grantAccessToApplet(
                    userModel.findOne({ '_id': ObjectId(caseUser['userId']) }),
                    appletModel.load(appletId, user=user),
                    'user',
                    user,
                    validateEmail=False,
                    MRN=caseUser['MRN']
                )

                profile = profileModel.findOne({
                    'userId': caseUser['userId'],
                    'appletId': ObjectId(appletId),
                })

            profiles.append(profile)

        for obj in caseUser['applets']:
            if obj['appletId'] not in newApplets:
                applet = appletModel.findOne({'_id': obj['appletId'] })
                profile = profileModel.findOne({'_id': obj['profileId']})

                appletModel.deleteUserFromApplet(
                    applet,
                    profile
                )

                entries = EntryModel().find({ 'profileId': profile['_id'] })

                for entry in entries:
                    EntryModel().deleteEntry(entry)

        caseUser = CaseUser().addCaseUser(
            caseId=id,
            profiles=profiles,
            accountId=caseUser['accountId'],
            userId=caseUser['userId'],
            MRN=caseUser['MRN']
        )

        return CaseUser().getData(caseUser)

    @access.user(scope=TokenScope.DATA_WRITE)
    @autoDescribeRoute(
        Description('Delete user from case.')
        .param(
            'id',
            'id of case',
            required=True
        )
        .param(
            'userId',
            'id of case user',
            required=True
        )
        .param(
            'deleteResponse',
            'if true, delete response of case user',
            dataType='boolean',
            required=False,
            default=False
        )
    )
    def unlinkUser(self, id, userId, deleteResponse):
        user = self.getCurrentUser()
        accountProfile = self.getAccountProfile()

        applets = accountProfile.get('applets', {})

        if not len(applets.get('coordinator', [])) and not len(applets.get('manager', [])):
            raise AccessException('permission denied')

        caseUser = CaseUser().findOne({
            'caseId': ObjectId(id),
            '_id': ObjectId(userId)
        })

        if not caseUser:
            raise ValidationException('unable to find user with specified id')

        appletModel = AppletModel()
        profileModel = ProfileModel()

        for obj in caseUser['applets']:
            applet = appletModel.findOne({'_id': obj['appletId'] })
            appletModel.deleteUserFromApplet(
                applet,
                profileModel.findOne({'_id': obj['profileId']})
            )

        CaseUser().deleteCaseUser(caseUser, deleteResponse)

    @access.user(scope=TokenScope.DATA_WRITE)
    @autoDescribeRoute(
        Description('Add entry to case.')
        .param(
            'id',
            'id of case',
            required=True
        )
        .param(
            'profileId',
            'id of user profile',
            required=False,
            default=None
        )
        .param(
            'appletId',
            'id of applet',
        )
        .param(
            'entryType',
            'type of entry, one of one_time_report, self_report, user_report',
            required=True
        )
    )
    def addEntry(self, id, profileId, appletId, entryType):
        user = self.getCurrentUser()
        accountProfile = self.getAccountProfile()

        applets = accountProfile.get('applets', {})

        if entryType == 'user_report':
            profile = ProfileModel().findOne({
                '_id': ObjectId(profileId)
            })
        elif entryType == 'self_report':
            profile = ProfileModel().findOne({
                'userId': user['_id'],
                'appletId': ObjectId(appletId)
            })
        else:
            profile = None

        if not profile and entryType != 'one_time_report':
            raise ValidationException('unable to find user with specified id')

        if ObjectId(appletId) not in applets.get('coordinator', []) and ObjectId(appletId) not in applets.get('manager', []):
            raise AccessException('permission denied')

        case = self._model.findOne({ '_id': ObjectId(id) })

        if entryType != 'user_report':
            caseUser = None
        else:
            caseUser = CaseUser().findOne({
                'userId': profile['userId'],
                'caseId': case['_id']
            })

            if not caseUser:
                raise ValidationException('unable to find user linked to case')

        applet = AppletModel().load(appletId, user=user)

        responder = None
        if entryType == 'self_report':
            responder = user.get('email')
        elif entryType != 'one_time_report':
            responder = caseUser.get('MRN')

        entry = EntryModel().addEntry(
            applet,
            profile['userId'] if profile else None,
            entryType,
            case['_id'],
            caseUser['_id'] if caseUser else None,
            responder
        )

        return EntryModel().getEntryData(entry)

    @access.user(scope=TokenScope.DATA_WRITE)
    @autoDescribeRoute(
        Description('Delete entry in a case.')
        .param(
            'id',
            'id of case',
            required=True
        )
        .param(
            'entryId',
            'id of entry',
            required=True
        )
        .param(
            'deleteResponse',
            'if true, delete response of case user',
            dataType='boolean',
            required=False,
            default=False
        )
    )
    def deleteEntry(self, id, entryId, deleteResponse):
        user = self.getCurrentUser()
        accountProfile = self.getAccountProfile()

        applets = accountProfile.get('applets', {})

        entry = EntryModel().findOne({
            '_id': ObjectId(entryId),
            'caseId': ObjectId(id)
        })

        if not entry:
            raise ValidationException('unable to find an entry with specified id')

        if entry['appletId'] not in applets.get('coordinator', []) and entry['appletId'] not in applets.get('manager', []):
            raise AccessException('permission denied')

        EntryModel().deleteEntry(entry, deleteResponse)
