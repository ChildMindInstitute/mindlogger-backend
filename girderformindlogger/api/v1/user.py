# -*- coding: utf-8 -*-
import base64
import cherrypy
import datetime
import itertools

from ..describe import Description, autoDescribeRoute
from girderformindlogger.api import access
from girderformindlogger.api.rest import Resource, filtermodel, setCurrentUser
from girderformindlogger.constants import AccessType, SortDir, TokenScope,     \
    USER_ROLES
from girderformindlogger.exceptions import RestException, AccessException
from girderformindlogger.models.applet import Applet as AppletModel
from girderformindlogger.models.collection import Collection as CollectionModel
from girderformindlogger.models.folder import Folder as FolderModel
from girderformindlogger.models.group import Group as GroupModel
from girderformindlogger.models.ID_code import IDCode
from girderformindlogger.models.profile import Profile as ProfileModel
from girderformindlogger.models.setting import Setting
from girderformindlogger.models.token import Token
from girderformindlogger.models.user import User as UserModel
from girderformindlogger.settings import SettingKey
from girderformindlogger.utility import jsonld_expander, mail_utils
from sys import exc_info


class User(Resource):
    """API Endpoint for users in the system."""

    def __init__(self):
        super(User, self).__init__()
        self.resourceName = 'user'
        self._model = UserModel()

        self.route('DELETE', ('authentication',), self.logout)
        self.route('DELETE', (':id',), self.deleteUser)
        self.route('GET', ('me',), self.getMe)
        self.route('GET', ('authentication',), self.login)
        self.route('PUT', ('applet', ':id', 'schedule'), self.setSchedule)
        self.route(
            'PUT',
            (':uid', 'applet', ':aid', 'schedule'),
            self.setOtherSchedule
        )
        self.route('GET', (':id',), self.getUserByID)
        self.route('PUT', (':id', 'code'), self.updateIDCode)
        self.route('DELETE', (':id', 'code'), self.removeIDCode)
        self.route('GET', ('applets',), self.getOwnApplets)
        self.route('PUT', (':id', 'knows'), self.setUserRelationship)
        self.route('GET', ('details',), self.getUsersDetails)
        self.route('POST', (), self.createUser)
        self.route('PUT', ('password',), self.changePassword)
        self.route('PUT', (':id', 'password'), self.changeUserPassword)
        self.route('GET', ('password', 'temporary', ':id'),
                   self.checkTemporaryPassword)
        self.route('PUT', ('password', 'temporary'),
                   self.generateTemporaryPassword)
        self.route('POST', (':id', 'otp'), self.initializeOtp)
        self.route('PUT', (':id', 'otp'), self.finalizeOtp)
        self.route('DELETE', (':id', 'otp'), self.removeOtp)
        self.route('PUT', ('profile',), self.updateProfile)
        self.route('PUT', (':id', 'verification'), self.verifyEmail)
        self.route('POST', ('verification',), self.sendVerificationEmail)

    @access.public(scope=TokenScope.USER_INFO_READ)
    @autoDescribeRoute(
        Description('Get a user by ID.')
        .param('id', 'Profile ID or ID code', required=True)
        .errorResponse('ID was invalid.')
        .errorResponse('You do not have permission to see this user.', 403)
    )
    def getUserByID(self, id):
        from bson.objectid import ObjectId
        user = self.getCurrentUser()
        return(ProfileModel().getProfile(id, user))

    @access.user(scope=TokenScope.DATA_WRITE)
    @autoDescribeRoute(
        Description('Set or update your own custom schedule information for an applet.')
        .modelParam(
            'id',
            model=AppletModel,
            level=AccessType.READ,
            destName='applet'
        )
        .jsonParam(
            'schedule',
            'A JSON object containing schedule information for an activity',
            paramType='form',
            required=False
        )
        .errorResponse('Invalid applet ID.')
        .errorResponse('Read access was denied for this applet.', 403)
    )
    def setSchedule(self, applet, schedule, **kwargs):
        import threading

        thisUser = self.getCurrentUser()
        if not AppletModel()._hasRole(applet['_id'], thisUser, 'user'):
            raise AccessException(
                "You aren't a user of this applet."
            )
        profile = ProfileModel().findOne(
            {
                'appletId': applet['_id'],
                'userId': thisUser['_id'],
                'profile': True
            }
        )
        if not profile:
            raise AccessException(
                "You aren't a user of this applet."
            )
        ud = profile["userDefined"] if "userDefined" in profile else {}
        ud["schedule"] = schedule
        profile["userDefined"] = ud
        ProfileModel().save(profile, validate=False)

        thread = threading.Thread(
            target=AppletModel().updateUserCacheAllUsersAllRoles,
            args=(applet, thisUser)
        )
        thread.start()
        return(profile["userDefined"])

    @access.user(scope=TokenScope.DATA_WRITE)
    @autoDescribeRoute(
        Description('Set or update custom schedule information for a user of an applet you manage or coordinate.')
        .modelParam(
            'uid',
            model=ProfileModel,
            force=True,
            destName='profile',
            description='The ID of the user\'s profile for this applet.'
        )
        .modelParam(
            'aid',
            model=AppletModel,
            level=AccessType.READ,
            destName='applet',
            description="The ID of the applet."
        )
        .jsonParam(
            'schedule',
            'A JSON object containing schedule information for an activity',
            paramType='form',
            required=False
        )
        .errorResponse('Invalid ID.')
        .errorResponse('Read access was denied.', 403)
    )
    def setOtherSchedule(self, profile, applet, schedule, **kwargs):
        import threading

        thisUser = self.getCurrentUser()
        if not AppletModel().isCoordinator(applet['_id'], thisUser):
            raise AccessException(
                "You aren't a coordinator or manager of this applet."
            )
        if profile["appletId"] not in [applet['_id'], str(applet['_id'])]:
            raise AccessException(
                "That profile is not a user of this applet."
            )
        ud = profile[
            "coordinatorDefined"
        ] if "coordinatorDefined" in profile else {}
        ud["schedule"] = schedule
        profile["coordinatorDefined"] = ud
        ProfileModel().save(profile, validate=False)

        thread = threading.Thread(
            target=AppletModel().updateUserCacheAllUsersAllRoles,
            args=(applet, thisUser)
        )
        thread.start()
        return(profile["coordinatorDefined"])

    @access.public(scope=TokenScope.USER_INFO_READ)
    @autoDescribeRoute(
        Description('Add a relationship between users.')
        .param(
            'id',
            'ID or ID code of user to add relationship to',
            required=True
        )
        .param('rel', 'Relationship to add', required=True)
        .param('otherId', 'ID or ID code of related individual.', required=True)
        .param(
            'otherName',
            'Name to display for related individual',
            required=True
        )
        .errorResponse('ID was invalid.')
        .errorResponse('You do not have permission to see this user.', 403)
    )
    def setUserRelationship(self, id, rel, otherId, otherName):
        from girderformindlogger.models.invitation import Invitation
        from girderformindlogger.utility.jsonld_expander import                \
            inferRelationships, oidIffHex

        user = self.getCurrentUser()
        grammaticalSubject = ProfileModel().getProfile(id, user)
        gsp = ProfileModel().load(
            grammaticalSubject['_id'],
            force=True
        )
        grammaticalSubject = Invitation().load(
            grammaticalSubject['_id'],
            force=True
        ) if gsp is None else gsp
        print(grammaticalSubject)
        if grammaticalSubject is None or not AppletModel().isCoordinator(
            grammaticalSubject['appletId'], user
        ):
            raise AccessException(
                'You do not have permission to update this user.'
            )

        appletId = grammaticalSubject['appletId']
        grammaticalObject = ProfileModel().getSubjectProfile(
            otherId,
            otherName,
            user
        )
        if grammaticalObject is None:
            grammaticalObject = ProfileModel().getProfile(
                ProfileModel().createPassiveProfile(
                    appletId,
                    otherId,
                    otherName,
                    user
                )['_id'],
                grammaticalSubject
            )
        if 'schema:knows' in grammaticalSubject:
            if rel in grammaticalSubject['schema:knows'] and grammaticalObject[
                '_id'
            ] not in grammaticalSubject['schema:knows'][rel]:
                grammaticalSubject['schema:knows'][rel].append(
                    grammaticalObject['_id']
                )
            else:
                grammaticalSubject['schema:knows'][rel] = [
                    grammaticalObject['_id']
                ]
        else:
            grammaticalSubject['schema:knows'] = {
                rel: [grammaticalObject['_id']]
            }
        ProfileModel().save(grammaticalSubject, validate=False)
        inferRelationships(grammaticalSubject)
        return(ProfileModel().getProfile(id, user))

    @access.public(scope=TokenScope.USER_INFO_READ)
    @autoDescribeRoute(
        Description('Update a user\'s ID Code.')
        .param('id', 'Profile ID', required=True)
        .param('code', 'ID code to add to profile', required=True)
        .errorResponse('ID was invalid.')
        .errorResponse('You do not have permission to see this user.', 403)
    )
    def updateIDCode(self, id, code):
        from bson.objectid import ObjectId
        user = self.getCurrentUser()
        try:
            p = ProfileModel().findOne({'_id': ObjectId(id)})
        except:
            p = None
        if p is None or not AppletModel().isCoordinator(p['appletId'], user):
            raise AccessException(
                'You do not have permission to update this user\'s ID code.'
            )
        else:
            IDCode().createIdCode(p, code)
        return(
            ProfileModel().profileAsUser(
                ProfileModel().load(p['_id'], force=True),
                user
            )
        )

    @access.public(scope=TokenScope.USER_INFO_READ)
    @autoDescribeRoute(
        Description('Remove an ID Code from a user.')
        .param('id', 'Profile ID', required=True)
        .param(
            'code',
            'ID code to remove from profile. If the ID code to remove is the '
            'only ID code for that profile, a new one will be auto-generated.',
            required=True
        )
        .errorResponse('ID was invalid.')
        .errorResponse('You do not have permission to see this user.', 403)
    )
    def removeIDCode(self, id, code):
        from bson.objectid import ObjectId
        user = self.getCurrentUser()
        try:
            p = ProfileModel().findOne({'_id': ObjectId(id)})
        except:
            p = None
        if p is None or not AppletModel().isCoordinator(p['appletId'], user):
            raise AccessException(
                'You do not have permission to update this user\'s ID code.'
            )
        else:
            IDCode().removeCode(p['_id'], code)
        return(
            ProfileModel().profileAsUser(
                ProfileModel().load(p['_id'], force=True),
                user
            )
        )

    @access.public(scope=TokenScope.DATA_READ)
    @autoDescribeRoute(
        Description('Get all your applets by role.')
        .param(
            'role',
            'One of ' + str(USER_ROLES.keys()),
            required=False,
            default='user'
        )
        .param(
            'ids_only',
            'If true, only returns an Array of the IDs of assigned applets. '
            'Otherwise, returns an Array of Objects keyed with "applet" '
            '"protocol", "activities" and "items" with expanded JSON-LD as '
            'values. This parameter takes precedence over `unexpanded`.',
            required=False,
            dataType='boolean'
        )
        .param(
            'unexpanded',
            'If true, only returns an Array of assigned applets, but only the '
            'applet-level information. Otherwise, returns an Array of Objects '
            'keyed with "applet", "protocol", "activities" and "items" with '
            'expanded JSON-LD as values.',
            required=False,
            dataType='boolean'
        )
        .param(
            'refreshCache',
            'If true, refresh user cache.',
            required=False,
            dataType='boolean'
        )
        .errorResponse('ID was invalid.')
        .errorResponse(
            'You do not have permission to see any of this user\'s applets.',
            403
        )
    )
    def getOwnApplets(
        self,
        role,
        ids_only=False,
        unexpanded=False,
        refreshCache=False
    ):
        import threading
        from bson import json_util
        from bson.objectid import ObjectId

        reviewer = self.getCurrentUser()
        if reviewer is None:
            raise AccessException("You must be logged in to get user applets.")
        role = role.lower()
        if role not in USER_ROLES.keys():
            raise RestException(
                'Invalid user role.',
                'role'
            )
        if ids_only or unexpanded:
            applets = AppletModel().getAppletsForUser(
                role,
                reviewer,
                active=True
            )
            if len(applets)==0:
                return([])
            if ids_only==True:
                return([applet.get('_id') for applet in applets])
            elif unexpanded==True:
                return([{
                    'applet': AppletModel().unexpanded(applet)
                } for applet in applets])
        if refreshCache:
            thread = threading.Thread(
                target=AppletModel().updateUserCache,
                args=(role, reviewer),
                kwargs={"active": True, "refreshCache": refreshCache}
            )
            thread.start()
            return({
                "message": "The user cache is being updated. Please check back "
                           "in several mintutes to see it."
            })
        try:
            if 'cached' in reviewer:
                reviewer['cached'] = json_util.loads(
                    reviewer['cached']
                ) if isinstance(reviewer['cached'], str) else reviewer['cached']
            else:
                reviewer['cached'] = {}
            if 'applets' in reviewer[
                'cached'
            ] and role in reviewer['cached']['applets'] and isinstance(
                reviewer['cached']['applets'][role],
                list
            ) and len(reviewer['cached']['applets'][role]):
                applets = reviewer['cached']['applets'][role]
                thread = threading.Thread(
                    target=AppletModel().updateUserCache,
                    args=(role, reviewer),
                    kwargs={"active": True, "refreshCache": refreshCache}
                )
                thread.start()
            else:
                applets = AppletModel().updateUserCache(
                    role,
                    reviewer,
                    active=True,
                    refreshCache=refreshCache
                )
            for applet in applets:
                try:
                    applet["applet"]["responseDates"] = responseDateList(
                        applet['applet'].get(
                            '_id',
                            ''
                        ).split('applet/')[-1],
                        user.get('_id'),
                        user
                    )
                except:
                    applet["applet"]["responseDates"] = []

            return(applets)
        except Exception as e:
            import sys, traceback
            print(sys.exc_info())
            return([])


    @access.public(scope=TokenScope.USER_INFO_READ)
    @filtermodel(model=UserModel)
    @autoDescribeRoute(
        Description('Retrieve the currently logged-in user information.')
        .responseClass('User')
    )
    def getMe(self):
        return self.getCurrentUser()

    @access.public
    @autoDescribeRoute(
        Description('Log in to the system.')
        .notes('Pass your username and password using HTTP Basic Auth. Sends'
               ' a cookie that should be passed back in future requests.')
        .param('Girder-OTP', 'A one-time password for this user',
               paramType='header', required=False)
        .errorResponse('Missing Authorization header.', 401)
        .errorResponse('Invalid login or password.', 403)
    )
    def login(self):
        import threading
        from girderformindlogger.utility.mail_utils import validateEmailAddress

        if not Setting().get(SettingKey.ENABLE_PASSWORD_LOGIN):
            raise RestException('Password login is disabled on this instance.')

        user, token = self.getCurrentUser(returnToken=True)


        # Only create and send new cookie if user isn't already sending a valid
        # one.
        if not user:
            authHeader = cherrypy.request.headers.get('Authorization')

            if not authHeader:
                authHeader = cherrypy.request.headers.get(
                    'Girder-Authorization'
                )

            if not authHeader or not authHeader[0:6] == 'Basic ':
                raise RestException('Use HTTP Basic Authentication', 401)

            try:
                credentials = base64.b64decode(authHeader[6:]).decode('utf8')
                if ':' not in credentials:
                    raise TypeError
            except Exception:
                raise RestException('Invalid HTTP Authorization header', 401)

            login, password = credentials.split(':', 1)
            if validateEmailAddress(login):
                raise AccessException(
                    "Please log in with a username, not an email address."
                )
            otpToken = cherrypy.request.headers.get('Girder-OTP')
            try:
                user = self._model.authenticate(login, password, otpToken)
            except:
                raise AccessException(
                    "Incorrect password for {} if that user exists".format(
                        login
                    )
                )

            thread = threading.Thread(
                target=AppletModel().updateUserCacheAllRoles,
                args=(user,)
            )

            setCurrentUser(user)
            token = self.sendAuthTokenCookie(user)

        return {
            'user': self._model.filter(user, user),
            'authToken': {
                'token': token['_id'],
                'expires': token['expires'],
                'scope': token['scope']
            },
            'message': 'Login succeeded.'
        }

    @access.public
    @autoDescribeRoute(
        Description('Log out of the system.')
        .responseClass('Token')
        .notes('Attempts to delete your authentication cookie.')
    )
    def logout(self):
        token = self.getCurrentToken()
        if token:
            Token().remove(token)
        self.deleteAuthTokenCookie()
        return {'message': 'Logged out.'}

    @access.public
    @filtermodel(model=UserModel, addFields={'authToken'})
    @autoDescribeRoute(
        Description('Create a new user.')
        .responseClass('User')
        .param('login', "The user's requested login.")
        .param('password', "The user's requested password")
        .param(
            'displayName',
            "The user's display name, usually just their first name.",
            default="",
            required=False
        )
        .param('email', "The user's email address.", required=False)
        .param('admin', 'Whether this user should be a site administrator.',
               required=False, dataType='boolean', default=False)
        .param(
            'lastName',
            'Deprecated. Do not use.',
            required=False
        )
        .param(
            'firstName',
            'Deprecated. Do not use.',
            required=False
        )
        .errorResponse('A parameter was invalid, or the specified login or'
                       ' email already exists in the system.')
    )
    def createUser(
        self,
        login,
        password,
        displayName="",
        email="",
        admin=False,
        lastName=None,
        firstName=None
    ): # 🔥 delete lastName once fully deprecated
        currentUser = self.getCurrentUser()

        regPolicy = Setting().get(SettingKey.REGISTRATION_POLICY)

        if not currentUser or not currentUser['admin']:
            admin = False
            if regPolicy == 'closed':
                raise RestException(
                    'Registration on this instance is closed. Contact an '
                    'administrator to create an account for you.')

        user = self._model.createUser(
            login=login, password=password, email=email,
            firstName=displayName if len(
                displayName
            ) else firstName if firstName is not None else "",
            lastName=lastName, admin=admin, currentUser=currentUser) # 🔥 delete firstName and lastName once fully deprecated

        if not currentUser and self._model.canLogin(user):
            setCurrentUser(user)
            token = self.sendAuthTokenCookie(user)
            user['authToken'] = {
                'token': token['_id'],
                'expires': token['expires']
            }

        # Assign all new users to a "New Users" Group
        newUserGroup = GroupModel().findOne({'name': 'New Users'})
        newUserGroup = newUserGroup if (
            newUserGroup is not None and bool(newUserGroup)
        ) else GroupModel(
        ).createGroup(
            name="New Users",
            creator=UserModel().findOne(
                query={'admin': True},
                sort=[('created', SortDir.ASCENDING)]
            ),
            public=False
        )
        group = GroupModel().addUser(
            newUserGroup,
            user,
            level=AccessType.READ
        )
        group['access'] = GroupModel().getFullAccessList(group)
        group['requests'] = list(GroupModel().getFullRequestList(group))

        return(user)

    @access.user
    @autoDescribeRoute(
        Description('Delete a user by ID.')
        .modelParam('id', model=UserModel, level=AccessType.ADMIN)
        .errorResponse('ID was invalid.')
        .errorResponse('You do not have permission to delete this user.', 403)
    )
    def deleteUser(self, user):
        self._model.remove(user)
        return {'message': 'Deleted user %s.' % user['login']}

    @access.user
    @autoDescribeRoute(
        Description('Get detailed information of accessible users.')
    )
    def getUsersDetails(self):
        nUsers = self._model.findWithPermissions(user=self.getCurrentUser(
        )).count()
        return {'nUsers': nUsers}


    @access.user
    @autoDescribeRoute(
        Description("Update a user's information.")
        .modelParam('id', model=UserModel, level=AccessType.WRITE)
        .param(
            'displayName',
            'Display name of the user, usually just their first name.',
            default="",
            required=False
        )
        .param('admin', 'Is the user a site admin (admin access required)',
               required=False, dataType='boolean')
        .param('status', 'The account status (admin access required)',
               required=False, enum=('pending', 'enabled', 'disabled'))
        .param(
             'email',
             'Deprecated. Do not use.',
             required=False,
             dataType='string'
        )
        .param(
            'firstName',
            'Deprecated. Do not use.',
            deprecated=True,
            required=False
        )
        .param(
            'lastName',
            'Deprecated. Do not use.',
            deprecated=True,
            required=False
        )
        .errorResponse()
        .errorResponse(('You do not have write access for this user.',
                        'Must be an admin to create an admin.'), 403)
    )
    def updateUser(
        self,
        user,
        displayName="",
        email="",
        admin=False,
        status=None,
        firstName=None,
        lastName=None
    ):
        # 🔥 delete firstName and lastName once fully deprecated
        user['firstName'] = displayName if len(
            displayName
        ) else firstName if firstName is not None else ""
        user['email'] = email

        # Only admins can change admin state
        if admin is not None:
            if self.getCurrentUser()['admin']:
                user['admin'] = admin
            elif user['admin'] is not admin:
                raise AccessException('Only admins may change admin status.')

            # Only admins can change status
            if status is not None and status != user.get('status', 'enabled'):
                if not self.getCurrentUser()['admin']:
                    raise AccessException('Only admins may change status.')
                if user['status'] == 'pending' and status == 'enabled':
                    # Send email on the 'pending' -> 'enabled' transition
                    self._model._sendApprovedEmail(user)
                user['status'] = status

        try:
            self._model.save(user)
        except:
            raise RestException(
                'Update failed, and `PUT /user/{:id}` is deprecated.'
            )

        return(
            {'message': 'Update saved, but `PUT /user/{:id}` is deprecated.'}
        )

    @access.admin
    @autoDescribeRoute(
        Description("Change a user's password.")
        .notes('Only administrators may use this endpoint.')
        .modelParam('id', model=UserModel, level=AccessType.ADMIN)
        .param('password', "The user's new password.")
        .errorResponse('You are not an administrator.', 403)
        .errorResponse('The new password is invalid.')
    )
    def changeUserPassword(self, user, password):
        self._model.setPassword(user, password)
        return {'message': 'Password changed.'}

    @access.user
    @autoDescribeRoute(
        Description('Change your password.')
        .param('old', 'Your current password or a temporary access token.')
        .param('new', 'Your new password.')
        .errorResponse(('You are not logged in.',
                        'Your old password is incorrect.'), 401)
        .errorResponse('Your new password is invalid.')
    )
    def changePassword(self, old, new):
        user = self.getCurrentUser()
        token = None

        if not old:
            raise RestException('Old password must not be empty.')

        if (not self._model.hasPassword(user)
                or not self._model._cryptContext.verify(old, user['salt'])):
            # If not the user's actual password, check for temp access token
            token = Token().load(old, force=True, objectId=False, exc=False)
            if (not token or not token.get('userId')
                    or token['userId'] != user['_id']
                    or not Token().hasScope(token, TokenScope.TEMPORARY_USER_AUTH)):
                raise AccessException('Old password is incorrect.')

        self._model.setPassword(user, new)

        if token:
            # Remove the temporary access token if one was used
            Token().remove(token)

        return {'message': 'Password changed.'}

    @access.public
    @autoDescribeRoute(
        Description("Create a temporary access token for a user.  The user's "
                    'password is not changed.')
        .param('email', 'Your email address.', strip=True)
        .errorResponse('That email does not exist in the system.')
    ) ## TODO: recreate by login
    def generateTemporaryPassword(self, email):
        user = self._model.findOne({'email': email.lower()})

        if not user:
            raise RestException('That email is not registered.')

        token = Token().createToken(user, days=1, scope=TokenScope.TEMPORARY_USER_AUTH)

        url = '%s#useraccount/%s/token/%s' % (
            mail_utils.getEmailUrlPrefix(), str(user['_id']), str(token['_id']))

        html = mail_utils.renderTemplate('temporaryAccess.mako', {
            'url': url,
            'token': str(token['_id'])
        })
        mail_utils.sendMail(
            '%s: Temporary access' % Setting().get(SettingKey.BRAND_NAME),
            html,
            [email]
        )
        return {'message': 'Sent temporary access email.'}

    @access.public
    @autoDescribeRoute(
        Description('Check if a specified token is a temporary access token '
                    'for the specified user.  If the token is valid, returns '
                    'information on the token and user.')
        .modelParam('id', 'The user ID to check.', model=UserModel, force=True)
        .param('token', 'The token to check.')
        .errorResponse('The token does not grant temporary access to the specified user.', 401)
    )
    def checkTemporaryPassword(self, user, token):
        token = Token().load(
            token, user=user, level=AccessType.ADMIN, objectId=False, exc=True)
        delta = (token['expires'] - datetime.datetime.utcnow()).total_seconds()
        hasScope = Token().hasScope(token, TokenScope.TEMPORARY_USER_AUTH)

        if token.get('userId') != user['_id'] or delta <= 0 or not hasScope:
            raise AccessException('The token does not grant temporary access to this user.')

        # Temp auth is verified, send an actual auth token now. We keep the
        # temp token around since it can still be used on a subsequent request
        # to change the password
        authToken = self.sendAuthTokenCookie(user)

        return {
            'user': self._model.filter(user, user),
            'authToken': {
                'token': authToken['_id'],
                'expires': authToken['expires'],
                'temporary': True
            },
            'message': 'Temporary access token is valid.'
        }

    @access.user
    @autoDescribeRoute(
        Description('Initiate the enablement of one-time passwords for this user.')
        .modelParam('id', model=UserModel, level=AccessType.ADMIN)
        .errorResponse()
        .errorResponse('Admin access was denied on the user.', 403)
    )
    def initializeOtp(self, user):
        if self._model.hasOtpEnabled(user):
            raise RestException('The user has already enabled one-time passwords.')

        otpUris = self._model.initializeOtp(user)
        self._model.save(user)

        return otpUris

    @access.user
    @autoDescribeRoute(
        Description('Finalize the enablement of one-time passwords for this user.')
        .modelParam('id', model=UserModel, level=AccessType.ADMIN)
        .param('Girder-OTP', 'A one-time password for this user', paramType='header')
        .errorResponse()
        .errorResponse('Admin access was denied on the user.', 403)
    )
    def finalizeOtp(self, user):
        otpToken = cherrypy.request.headers.get('Girder-OTP')
        if not otpToken:
            raise RestException('The "Girder-OTP" header must be provided.')

        if 'otp' not in user:
            raise RestException('The user has not initialized one-time passwords.')
        if self._model.hasOtpEnabled(user):
            raise RestException('The user has already enabled one-time passwords.')

        user['otp']['enabled'] = True
        # This will raise an exception if the verification fails, so the user will not be saved
        self._model.verifyOtp(user, otpToken)

        self._model.save(user)

    @access.user
    @autoDescribeRoute(
        Description('Disable one-time passwords for this user.')
        .modelParam('id', model=UserModel, level=AccessType.ADMIN)
        .errorResponse()
        .errorResponse('Admin access was denied on the user.', 403)
    )
    def removeOtp(self, user):
        if not self._model.hasOtpEnabled(user):
            raise RestException('The user has not enabled one-time passwords.')

        del user['otp']
        self._model.save(user)

    @access.public
    @autoDescribeRoute(
        Description(
            'Update a user profile. Requires either profile ID __OR__ applet '
            'ID and ID code.'
        )
        .jsonParam(
            'update',
            'A JSON Object with values to update, overriding existing values.',
            required=True
        )
        .param('id', 'Profile ID.', required=False)
        .param('applet', 'Applet ID.', required=False)
        .param('idCode', 'ID code.', required=False)
    )
    def updateProfile(self, update={}, id=None, applet=None, idCode=None):
        if (id is not None) and (applet is not None or idCode is not None):
            raise RestException(
                'Pass __either__ profile ID __OR__ (applet ID and ID code), '
                'not both.'
            )
        elif (id is None) and (applet is None or idCode is None):
            raise RestException(
                'Either profile ID __OR__ (applet ID and ID code) required.'
            )
        else:
            currentUser = self.getCurrentUser()
            id = id if id is not None else Profile().getProfile(
                applet=AppletModel().load(applet, force=True),
                idCode=idCode,
                user=currentUser
            )
        return(ProfileModel().updateProfile(id, currentUser, update))

    @access.public
    @autoDescribeRoute(
        Description('Verify an email address using a token.')
        .modelParam('id', 'The user ID to check.', model=UserModel, force=True)
        .param('token', 'The token to check.')
        .errorResponse('The token is invalid or expired.', 401)
    )
    def verifyEmail(self, user, token):
        token = Token().load(
            token, user=user, level=AccessType.ADMIN, objectId=False, exc=True)
        delta = (token['expires'] - datetime.datetime.utcnow()).total_seconds()
        hasScope = Token().hasScope(token, TokenScope.EMAIL_VERIFICATION)

        if token.get('userId') != user['_id'] or delta <= 0 or not hasScope:
            raise AccessException('The token is invalid or expired.')

        user['emailVerified'] = True
        Token().remove(token)
        user = self._model.save(user)

        if self._model.canLogin(user):
            setCurrentUser(user)
            authToken = self.sendAuthTokenCookie(user)
            return {
                'user': self._model.filter(user, user),
                'authToken': {
                    'token': authToken['_id'],
                    'expires': authToken['expires'],
                    'scope': authToken['scope']
                },
                'message': 'Email verification succeeded.'
            }
        else:
            return {
                'user': self._model.filter(user, user),
                'message': 'Email verification succeeded.'
            }

    @access.public
    @autoDescribeRoute(
        Description('Send verification email.')
        .param('login', 'Your login.', strip=True)
        .errorResponse('That login is not registered.', 401)
    )
    def sendVerificationEmail(self, login):
        loginField = 'email' if '@' in login else 'login'
        user = self._model.findOne({loginField: login.lower()})

        if not user:
            raise RestException('That login is not registered.', 401)

        self._model._sendVerificationEmail(user)
        return {'message': 'Sent verification email.'}
