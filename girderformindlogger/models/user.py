# -*- coding: utf-8 -*-
import datetime
import os
import re
from passlib.context import CryptContext
from passlib.totp import TOTP, TokenError
import hashlib

import six

from girderformindlogger import events
from girderformindlogger.constants import AccessType, CoreEventHandler, TokenScope, USER_ROLES, ServerMode
from girderformindlogger.exceptions import AccessException, ValidationException
from girderformindlogger.models.aes_encrypt import AESEncryption, AccessControlledModel
from girderformindlogger.models.setting import Setting
from girderformindlogger.settings import SettingKey
from girderformindlogger.utility import config, mail_utils
from girderformindlogger.utility._cache import rateLimitBuffer
from bson import ObjectId


class User(AESEncryption):
    """
    This model represents the users of the system.
    """

    def initialize(self):
        self.name = 'user'
        self.ensureIndices(['login', 'email', 'groupInvites.groupId', 'size',
                            'created', 'deviceId', 'timezone', 'accountId'])
        self.prefixSearchFields = (
            'login', ('firstName', 'i'), ('displayName', 'i'), 'email')
        self.ensureTextIndex({
            'login': 1,
            'displayName': 1,
            'email': 1,
        }, language='none')
        self.exposeFields(level=AccessType.READ, fields=(
            '_id', 'login', 'public', 'displayName', 'firstName', 'lastName',
            'admin', 'email', 'created'))
        self.exposeFields(level=AccessType.ADMIN, fields=(
            'size', 'status', 'emailVerified', 'creatorId'))

        # To ensure compatibility with authenticator apps, other defaults shouldn't be changed
        self._TotpFactory = TOTP.using(
            # An application secret could be set here, if it existed
            wallet=None
        )

        self._cryptContext = CryptContext(
            schemes=['bcrypt']
        )

        self.initAES([
            ('firstName', 64),
            ('lastName', 64),
            ('displayName', 64)
        ])

        events.bind('model.user.save.created',
                    CoreEventHandler.USER_SELF_ACCESS, self._grantSelfAccess)
        # events.bind('model.user.save.created',
        #             CoreEventHandler.USER_DEFAULT_FOLDERS,
        #             self._addDefaultFolders)

    def validate(self, doc):
        """
        Validate the user every time it is stored in the database.
        """
        for s in ['email', 'displayName', 'firstName']:
            if s in doc and doc[s] is None:
                doc[s] = ''
        doc['login'] = doc.get('login', '').lower().strip()
        if not doc['email_encrypted']:
            doc['email'] = doc.get('email', '').lower().strip()
        doc['displayName'] = doc.get(
            'displayName',
            doc.get('firstName', '')
        ).strip()
        doc['firstName'] = doc.get('firstName', '').strip()
        doc['status'] = doc.get('status', 'enabled')
        doc['deviceId'] = doc.get('deviceId', '')
        doc['timezone'] = doc.get('timezone', 0)

        if 'salt' not in doc:
            # Internal error, this should not happen
            raise Exception('Tried to save user document with no salt.')

        if not doc['displayName']:
            raise ValidationException('Display name must not be empty.',
                                      'displayName')

        if doc['status'] not in ('pending', 'enabled', 'disabled'):
            raise ValidationException(
                'Status must be pending, enabled, or disabled.', 'status')

        if 'hashAlg' in doc:
            # This is a legacy field; hash algorithms are now inline with the password hash
            del doc['hashAlg']

        if not doc['email_encrypted'] and len(doc['email']) and not mail_utils.validateEmailAddress(
            doc['email']
        ):
            raise ValidationException('Invalid email address.', 'email')

        if len(doc['email']):
            q = {'email': doc['email']}
            if '_id' in doc:
                q['_id'] = {'$ne': doc['_id']}
            existing = self.findOne(q)
            if existing is not None:
                raise ValidationException('That email is already registered in the system.', )

        # Ensure unique logins
        if len(doc['login']):
            self._validateLogin(doc['login'])

            q = {'login': doc['login']}
            if '_id' in doc:
                q['_id'] = {'$ne': doc['_id']}
            existing = self.findOne(q)
            if existing is not None:
                raise ValidationException('That login is already registered.',
                                        'login')

        # If this is the first user being created, make it an admin
        existing = self.findOne({})
        if existing is None and config.getServerMode() == ServerMode.DEVELOPMENT:
            doc['admin'] = True
            # Ensure settings don't stop this user from logging in
            doc['emailVerified'] = True
            doc['status'] = 'enabled'

        return doc

    def _validateLogin(self, login):
        if '@' in login:
            # Hard-code this constraint so we can always easily distinguish
            # an email address from a login
            raise ValidationException('Login may not contain "@".', 'login')

        if not re.match(r'^[a-z][\da-z\-\.]{3,}$', login):
            raise ValidationException(
                'Login must be at least 4 characters, start with a letter, and may only contain '
                'letters, numbers, dashes, and dots.', 'login')

    def filter(self, doc, user, additionalKeys=None):
        filteredDoc = super(User, self).filter(doc, user, additionalKeys)

        level = self.getAccessLevel(doc, user)
        if level >= AccessType.ADMIN:
            filteredDoc['otp'] = doc.get('otp', {})
            filteredDoc['otp'] = filteredDoc['otp'].get(
                'enabled',
                False
            ) if isinstance(filteredDoc['otp'], dict) else False

        return filteredDoc

    def hash(self, data):
        x = hashlib.sha224(data.encode('utf-8')).hexdigest()
        return x

    def authenticate(self, login, password, otpToken=None, deviceId=None, timezone=0, loginAsEmail = False):
        """
        Validate a user login via username and password. If authentication
        fails, an ``AccessException`` is raised.

        :param login: The user's login or email.
        :type login: str
        :param password: The user's password.
        :type password: str
        :param otpToken: A one-time password for the user. If "True", then the
                         one-time password (if required) is assumed to be
                         concatenated to the password.
        :type otpToken: str or bool or None
        :returns: The corresponding user if the login was successful.
        :rtype: dict
        """
        user = None
        event = events.trigger('model.user.authenticate', {
            'login': login,
            'password': password
        })

        if event.defaultPrevented and len(event.responses):
            return event.responses[-1]

        login = login.lower().strip()
        loginField = 'email' if loginAsEmail else 'login'

        user = self.findOne({loginField: self.hash(login), 'email_encrypted': True})

        if user is None and loginField == 'email':
            user = self.findOne({loginField: login, 'email_encrypted': {'$ne': True}})

        if user is None:
            raise AccessException('Login failed. User not found.')

        # Handle users with no password
        if not self.hasPassword(user):
            e = events.trigger('no_password_login_attempt', {
                'user': user,
                'password': password
            })

            if len(e.responses):
                return e.responses[-1]

            raise ValidationException(
                'This user does not have a password. You must log in with an '
                'external service, or reset your password.')

        # Handle OTP token concatenation
        if otpToken is True and self.hasOtpEnabled(user):
            # Assume the last (typically 6) characters are the OTP, so split at
            # that point
            otpTokenLength = self._TotpFactory.digits
            otpToken = password[-otpTokenLength:]
            password = password[:-otpTokenLength]

        self._verify_password(password, user)

        # Verify OTP
        if self.hasOtpEnabled(user):
            if otpToken is None:
                raise AccessException(
                    'User authentication must include a one-time password '
                    '(typically in the "Girder-OTP" header).')
            self.verifyOtp(user, otpToken)
        elif isinstance(otpToken, six.string_types):
            raise AccessException(
                'The user has not enabled one-time passwords.'
            )

        # This has the same behavior as User.canLogin, but returns more
        # detailed error messages
        if user.get('status', 'enabled') == 'disabled':
            return { 'exception' : 'Account is disabled.' }

        if self.emailVerificationRequired(user):
            return { 'exception' : 'Email verification is required.' }

        if self.adminApprovalRequired(user):
            return { 'exception' : 'Admin approval required' }

        return user

    def remove(self, user, progress=None, **kwargs):
        """
        Delete a user, and all references to it in the database.

        :param user: The user document to delete.
        :type user: dict
        :param progress: A progress context to record progress on.
        :type progress: girderformindlogger.utility.progress.ProgressContext or None.
        """
        from girderformindlogger.models.folder import Folder
        from girderformindlogger.models.group import Group
        from girderformindlogger.models.token import Token

        # Delete all authentication tokens owned by this user
        Token().removeWithQuery({'userId': user['_id']})

        # Delete all pending group invites for this user
        Group().update(
            {'requests': user['_id']},
            {'$pull': {'requests': user['_id']}}
        )

        # Delete all of the folders under this user
        folderModel = Folder()
        folders = folderModel.find({
            'parentId': user['_id'],
            'parentCollection': 'user'
        })
        for folder in folders:
            folderModel.remove(folder, progress=progress, **kwargs)

        # Finally, delete the user document itself
        AccessControlledModel.remove(self, user)
        if progress:
            progress.update(increment=1, message='Deleted user ' + user['login'])

    def getAdmins(self):
        """
        Helper to return a cursor of all site-admin users. The number of site
        admins is assumed to be small enough that we will not need to page the
        results for now.
        """
        return self.find({'admin': True})

    def search(self, text=None, user=None, limit=0, offset=0, sort=None):
        """
        List all users. Since users are access-controlled, this will filter
        them by access policy.

        :param text: Pass this to perform a full-text search for users.
        :param user: The user running the query. Only returns users that this
                     user can see.
        :param limit: Result limit.
        :param offset: Result offset.
        :param sort: The sort structure to pass to pymongo.
        :returns: Iterable of users.
        """
        # Perform the find; we'll do access-based filtering of the result set
        # afterward.
        if text is not None:
            cursor = self.textSearch(text, sort=sort)
        else:
            cursor = self.find({}, sort=sort)

        return self.filterResultsByPermission(
            cursor=cursor, user=user, level=AccessType.READ, limit=limit,
            offset=offset)

    def setUserName(self, user, userName, save=True):
        """
        Change a user's username

        :param user: The user whose username to change.
        :param userName: the new userName to be stored
        """

        oldUserName = user['login']

        if len(userName) > 0:
            user['login'] = userName
        else:
            raise Exception('username can\'t be empty')
        self.save(user)

        return oldUserName


    def hasPassword(self, user):
        """
        Returns whether or not the given user has a password stored in the
        database. If not, it is expected that the user will be authenticated by
        an external service.

        :param user: The user to test.
        :type user: dict
        :returns: bool
        """
        return user['salt'] is not None

    def setPassword(self, user, password, save=True):
        """
        Change a user's password.

        :param user: The user whose password to change.
        :param password: The new password. If set to None, no password will
                         be stored for this user. This should be done in cases
                         where an external system is responsible for
                         authenticating the user.
        """
        if password is None:
            user['salt'] = None
        else:
            cur_config = config.getConfig()

            # Normally this would go in validate() but password is a special case.
            if not re.match(cur_config['users']['password_regex'], password):
                raise ValidationException(cur_config['users']['password_description'], 'password')

            user['salt'] = self._cryptContext.hash(password)

        if save:
            self.save(user)

    def initializeOtp(self, user):
        """
        Initialize the use of one-time passwords with this user.

        This does not save the modified user model.

        :param user: The user to modify.
        :return: The new OTP keys, each in KeyUriFormat.
        :rtype: dict
        """
        totp = self._TotpFactory.new()

        user['otp'] = {
            'enabled': False,
            'totp': totp.to_dict()
        }

        # Use the brand name as the OTP issuer if it's non-default (since that's prettier and more
        # meaningful for users), but fallback to the site hostname if the brand name isn't set
        # (to disambiguate otherwise identical "Girder" issuers)
        # Prevent circular import
        from girderformindlogger.api.rest import getUrlParts
        brandName = Setting().get(SettingKey.BRAND_NAME)
        defaultBrandName = Setting().getDefault(SettingKey.BRAND_NAME)
        # OTP URIs ( https://github.com/google/google-authenticator/wiki/Key-Uri-Format ) do not
        # allow colons, so use only the hostname component
        serverHostname = getUrlParts().netloc.partition(':')[0]
        # Normally, the issuer would be set when "self._TotpFactory" is instantiated, but that
        # happens during model initialization, when there's no current request, so the server
        # hostname is not known then
        otpIssuer = brandName if brandName != defaultBrandName else serverHostname

        return {
            'totpUri': totp.to_uri(label=user['login'], issuer=otpIssuer)
        }

    def hasOtpEnabled(self, user):
        return 'otp' in user and user['otp']['enabled']

    def verifyOtp(self, user, otpToken):
        lastCounterKey = 'girderformindlogger.models.user.%s.otp.totp.counter' % user['_id']

        # The last successfully-authenticated key (which is blacklisted from reuse)
        lastCounter = rateLimitBuffer.get(lastCounterKey) or None

        try:
            totpMatch = self._TotpFactory.verify(
                otpToken, user['otp']['totp'], last_counter=lastCounter)
        except TokenError as e:
            raise AccessException('One-time password validation failed: %s' % e)

        # The totpMatch.cache_seconds tells us prospectively how long the counter needs to be cached
        # for, but dogpile.cache expiration times work retrospectively (on "get"), so there's no
        # point to using it (over-caching just wastes cache resources, but does not impact
        # "totp.verify" security)
        rateLimitBuffer.set(lastCounterKey, totpMatch.counter)

    def createUser(self, login, password, displayName="", email="",
                   admin=False, public=False, currentUser=None,
                   firstName="", lastName="", encryptEmail=False):
        """
        Create a new user with the given information.

        :param admin: Whether user is global administrator.
        :type admin: bool
        :param public: Whether user is publicly visible.
        :type public: bool
        :returns: The user document that was created.
        """
        from girderformindlogger.models.group import Group
        from girderformindlogger.models.setting import Setting
        from girderformindlogger.models.account_profile import AccountProfile
        requireApproval = Setting(
        ).get(SettingKey.REGISTRATION_POLICY) == 'approve'
        email = "" if not email else email

        login = login.lower().strip()
        email = email.lower().strip()

        if self.findOne({'email': email, 'email_encrypted': {'$ne': True}}) or self.findOne({'email': self.hash(email), 'email_encrypted': True}):
            raise ValidationException('That email is already registered in the system.', )

        if admin:
            requireApproval = False
            encryptEmail = False
        user = {
            'login': login,
            'email': email,
            'displayName': displayName if len(
                displayName
            ) else firstName if firstName is not None else "",
            'firstName': firstName,
            'lastName': lastName,
            'created': datetime.datetime.utcnow(),
            'emailVerified': False,
            'status': 'pending' if requireApproval else 'enabled',
            'admin': admin,
            'size': 0,
            'deviceId': '',
            'timezone': 0,
            'groups': [],
            'groupInvites': [
                {
                    "groupId": gi.get('_id'),
                    "level": 0
                } for gi in list(Group().find(query={"queue": email}))
            ] if len(email) else [],
            'email_encrypted': encryptEmail,
            'accountName': ''
        }
        if encryptEmail:
            if len(email) == 0 or not mail_utils.validateEmailAddress(email):
                raise ValidationException('Invalid email address.', 'email')

            user['email'] = self.hash(user['email'])

        self.setPassword(user, password, save=False)
        self.setPublic(user, public, save=False)

        if currentUser:
            self.setUserAccess(
                user, user=currentUser, level=AccessType.WRITE, save=False
            )
            user['creatorId'] = currentUser['_id']

        user = self.save(user)

        if currentUser:
            User().setUserAccess(
                doc=currentUser, user=user, level=AccessType.READ, save=True
            )
        else:
            user['creatorId'] = user['_id']
            user = self.save(user)

        verifyEmail = Setting().get(SettingKey.EMAIL_VERIFICATION) != 'disabled'
        if verifyEmail:
            self._sendVerificationEmail(user, email)

        if requireApproval:
            self._sendApprovalEmail(user)
        Group().update(
            query={"queue": user['email']},
            update={"$pull": {"queue": user['email']}},
            multi=True
        )

        account = AccountProfile().createOwner(user)
        user['accountId'] = account['_id']
        self.update({'_id': user['_id']}, {'$set': {'accountId': user['accountId']}})

        # self.createTemplatesFolder(user)

        user = self._getGroupInvitesFromProtoUser(user)
        self._deleteProtoUser(user)
        return(user)

    def createTemplatesFolder(self, user):
        from girderformindlogger.models.folder import Folder

        existing = Folder().findOne({
            'accountId': user['accountId'],
            'meta.contentType': 'templates'
        })
        if existing:
            return existing

        templatesFolder = Folder().createFolder(
            parent=user,
            parentType='user',
            name='templates folder for {} account'.format(user['firstName']),
            creator=user,
            reuseExisting=True,
            allowRename=True,
            public=False,
            accountId=user['accountId']
        )

        return Folder().setMetadata(templatesFolder, {
            'contentType': 'templates'
        })

    def canLogin(self, user):
        """
        Returns True if the user is allowed to login, e.g. email verification
        is not needed and admin approval is not needed.
        """
        if user.get('status', 'enabled') == 'disabled':
            return False
        if self.emailVerificationRequired(user):
            return False
        if self.adminApprovalRequired(user):
            return False
        return True

    def emailVerificationRequired(self, user):
        """
        Returns True if email verification is required and this user has not
        yet verified their email address.
        """
        from girderformindlogger.models.setting import Setting
        return (not user['emailVerified']) and \
            (Setting().get(SettingKey.EMAIL_VERIFICATION) == 'required' or Setting().get(SettingKey.EMAIL_VERIFICATION) == 'enabled')

    def adminApprovalRequired(self, user):
        """
        Returns True if the registration policy requires admin approval and
        this user is pending approval.
        """
        from girderformindlogger.models.setting import Setting
        return user.get('status', 'enabled') == 'pending' and \
            Setting().get(SettingKey.REGISTRATION_POLICY) == 'approve'

    def _sendApprovalEmail(self, user):
        url = '%s#user/%s' % (
            mail_utils.getEmailUrlPrefix(), str(user['_id']))
        text = mail_utils.renderTemplate('accountApproval.mako', {
            'user': user,
            'url': url
        })
        mail_utils.sendMailToAdmins(
            'Girder: Account pending approval',
            text)

    def _sendApprovedEmail(self, user, email):
        text = mail_utils.renderTemplate('accountApproved.mako', {
            'user': user,
            'url': mail_utils.getEmailUrlPrefix()
        })
        mail_utils.sendMail(
            'Girder: Account approved',
            text,
            [email])

    def _sendVerificationEmail(self, user, email):
        from girderformindlogger.models.token import Token

        token = Token().createToken(
            user, days=1, scope=TokenScope.EMAIL_VERIFICATION)
        url = '%s#useraccount/%s/verification/%s' % (
            mail_utils.getEmailUrlPrefix(), str(user['_id']), str(token['_id']))
        text = mail_utils.renderTemplate('emailVerification.mako', {
            'url': url
        })
        mail_utils.sendMail(
            'Girder: Email verification',
            text,
            [email])

    def _grantSelfAccess(self, event):
        """
        This callback grants a user admin access to itself.

        This generally should not be called or overridden directly, but it may
        be unregistered from the `model.user.save.created` event.
        """
        user = event.info

        self.setUserAccess(user, user, level=AccessType.ADMIN, save=True)

    def _addDefaultFolders(self, event):
        """
        This callback creates "Public" and "Private" folders on a user, after
        it is first created.

        This generally should not be called or overridden directly, but it may
        be unregistered from the `model.user.save.created` event.
        """
        from girderformindlogger.models.folder import Folder
        from girderformindlogger.models.setting import Setting

        if Setting().get(SettingKey.USER_DEFAULT_FOLDERS) == 'public_private':
            user = event.info

            publicFolder = Folder().createFolder(
                user, 'Public', parentType='user', public=True, creator=user)
            privateFolder = Folder().createFolder(
                user, 'Private', parentType='user', public=False, creator=user)
            # Give the user admin access to their own folders
            Folder().setUserAccess(publicFolder, user, AccessType.ADMIN, save=True)
            Folder().setUserAccess(privateFolder, user, AccessType.ADMIN, save=True)

    def fileList(self, doc, user=None, path='', includeMetadata=False, subpath=True, data=True):
        """
        This function generates a list of 2-tuples whose first element is the
        relative path to the file from the user's folders root and whose second
        element depends on the value of the `data` flag. If `data=True`, the
        second element will be a generator that will generate the bytes of the
        file data as stored in the assetstore. If `data=False`, the second
        element is the file document itself.

        :param doc: the user to list.
        :param user: a user used to validate data that is returned.
        :param path: a path prefix to add to the results.
        :param includeMetadata: if True and there is any metadata, include a
                                result which is the JSON string of the
                                metadata.  This is given a name of
                                metadata[-(number).json that is distinct from
                                any file within the item.
        :param subpath: if True, add the user's name to the path.
        :param data: If True return raw content of each file as stored in the
            assetstore, otherwise return file document.
        :type data: bool
        """
        from girderformindlogger.models.folder import Folder

        if subpath:
            path = os.path.join(path, doc['login'])
        folderModel = Folder()
        # Eagerly evaluate this list, as the MongoDB cursor can time out on long requests
        childFolders = list(folderModel.childFolders(
            parentType='user', parent=doc, user=user,
            fields=['name'] + (['meta'] if includeMetadata else [])
        ))
        for folder in childFolders:
            for (filepath, file) in folderModel.fileList(
                    folder, user, path, includeMetadata, subpath=True, data=data):
                yield (filepath, file)

    def subtreeCount(self, doc, includeItems=True, user=None, level=None):
        """
        Return the size of the user's folders.  The user is counted as well.

        :param doc: The user.
        :param includeItems: Whether to include items in the subtree count, or
            just folders.
        :type includeItems: bool
        :param user: If filtering by permission, the user to filter against.
        :param level: If filtering by permission, the required permission level.
        :type level: AccessLevel
        """
        from girderformindlogger.models.folder import Folder

        count = 1
        folderModel = Folder()
        folders = folderModel.findWithPermissions({
            'parentId': doc['_id'],
            'parentCollection': 'user'
        }, fields='access', user=user, level=level)

        count += sum(folderModel.subtreeCount(
            folder, includeItems=includeItems, user=user, level=level)
            for folder in folders)
        return count

    def countFolders(self, user, filterUser=None, level=None):
        """
        Returns the number of top level folders under this user. Access
        checking is optional; to circumvent access checks, pass ``level=None``.

        :param user: The user whose top level folders to count.
        :type collection: dict
        :param filterUser: If performing access checks, the user to check
            against.
        :type filterUser: dict or None
        :param level: The required access level, or None to return the raw
            top-level folder count.
        """
        from girderformindlogger.models.folder import Folder

        fields = () if level is None else ('access', 'public')

        folderModel = Folder()
        folders = folderModel.findWithPermissions({
            'parentId': user['_id'],
            'parentCollection': 'user'
        }, fields=fields, user=filterUser, level=level)

        return folders.count()

    def updateSize(self, doc):
        """
        Recursively recomputes the size of this user and its underlying
        folders and fixes the sizes as needed.

        :param doc: The user.
        :type doc: dict
        """
        from girderformindlogger.models.folder import Folder

        size = 0
        fixes = 0
        folderModel = Folder()
        folders = folderModel.find({
            'parentId': doc['_id'],
            'parentCollection': 'user'
        })
        for folder in folders:
            # fix folder size if needed
            _, f = folderModel.updateSize(folder)
            fixes += f
            # get total recursive folder size
            folder = folderModel.load(folder['_id'], force=True)
            size += folderModel.getSizeRecursive(folder)
        # fix value if incorrect
        if size != doc.get('size'):
            self.update({'_id': doc['_id']}, update={'$set': {'size': size}})
            fixes += 1
        return size, fixes

    def _getGroupInvitesFromProtoUser(self, doc):
        """

        """
        from girderformindlogger.models.protoUser import ProtoUser

        # Ensure unique emails
        q = {'email': doc['email']}
        if '_id' in doc:
            q['_id'] = {'$ne': doc['_id']}
        existing = ProtoUser().findOne(q)
        if existing is not None:
            doc['groupInvites'] = existing['groupInvites']
        return(doc)

    def _deleteProtoUser(self, doc):
        """

        """
        from girderformindlogger.models.protoUser import ProtoUser

        # Ensure unique emails
        q = {'email': doc['email']}
        if '_id' in doc:
            q['_id'] = {'$ne': doc['_id']}
        existing = ProtoUser().findOne(q)
        if existing is not None:
            ProtoUser().remove(existing)

    def _verify_password(self, password, user):
        # Verify password
        if not self._cryptContext.verify(password, user['salt']):
            raise AccessException('Login failed.')
        else:
            return(True)

    def get_users_by_ids(self, user_ids):
        return self.find(
            query={
                '_id': {
                    '$in': user_ids
                }
            },
            fields=[
                'timezone', 'deviceId'
            ]
        )
