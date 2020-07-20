# -*- coding: utf-8 -*-
import datetime
import os
import re
from passlib.context import CryptContext
from passlib.totp import TOTP, TokenError
import six
import hashlib

from girderformindlogger import events
from girderformindlogger.constants import AccessType, CoreEventHandler, TokenScope
from girderformindlogger.exceptions import AccessException, ValidationException
from girderformindlogger.models.model_base import AccessControlledModel
from girderformindlogger.models.setting import Setting
from girderformindlogger.models.user import User
from girderformindlogger.settings import SettingKey
from girderformindlogger.utility import config, mail_utils
from girderformindlogger.utility._cache import rateLimitBuffer


class ProtoUser(User):
    """
    This model represents the users who have been invited to the system but not
    yet created an account.
    """

    def initialize(self):
        self.name = 'protoUser'
        self.ensureIndices(['email', 'groupInvites.groupId'])
        self.prefixSearchFields = ('email')
        self.ensureTextIndex({
            'email': 1,
        }, language='none')
        self.exposeFields(level=AccessType.READ, fields=(
            '_id', 'public', 'email',  'created'))
        self.exposeFields(level=AccessType.ADMIN, fields=(
            'groupInvites', 'status'))

        # To ensure compatibility with authenticator apps, other defaults shouldn't be changed
        self._TotpFactory = TOTP.using(
            # An application secret could be set here, if it existed
            wallet=None
        )

        self._cryptContext = CryptContext(
            schemes=['bcrypt']
        )

        # events.bind('model.user.save.created',
        #             CoreEventHandler.USER_SELF_ACCESS, self._grantSelfAccess)
        # events.bind('model.user.save.created',
        #             CoreEventHandler.USER_DEFAULT_FOLDERS,
        #             self._addDefaultFolders)

    def validate(self, doc):
        """
        Validate the user every time it is stored in the database.
        """
        doc['email'] = doc.get('email', '').lower().strip()

        # if 'salt' not in doc:
        #     # Internal error, this should not happen
        #     raise Exception('Tried to save user document with no salt.')
        #
        # if 'hashAlg' in doc:
        #     # This is a legacy field; hash algorithms are now inline with the password hash
        #     del doc['hashAlg']

        if not doc.get('email_encrypted', None) and not mail_utils.validateEmailAddress(doc['email']):
            raise ValidationException('Invalid email address.', 'email')

        # Ensure unique emails # TO DO: use existing user if email exists
        q = {'email': doc['email']}
        if '_id' in doc:
            q['_id'] = {'$ne': doc['_id']}
        existing = self.findOne(q)
        if existing is not None:
            raise ValidationException(''.join([
                                      'That email is already registered:',
                                      str(existing["_id"])]),
                                      'email')

        return doc

    def createProtoUser(self, email):
        """
        Create a new protoUser with the given information.

        :returns: The user document that was created.
        """
        from girderformindlogger.models.group import Group
        from girderformindlogger.models.setting import Setting

        encryptedEmail = hashlib.sha224(email.encode('utf-8')).hexdigest()
        protoUser = self.findOne(query={"email": encryptedEmail}, force=True)
        if protoUser:
            protoUser['groupInvites'] = [
                {
                    "groupId": gi.get('_id'),
                    "level": 0
                } for gi in list(Group().find(query={"queue": encryptedEmail}))
            ]
            self.save(protoUser)
            return(protoUser)
        protoUser = {
            'email': encryptedEmail,
            'created': datetime.datetime.utcnow(),
            'groupInvites': [
                {
                    "groupId": gi.get('_id'),
                    "level": 0
                } for gi in list(Group().find(query={"queue": encryptedEmail}))
            ],
            'email_encrypted': True
        }
        protoUser = self.save(protoUser)
        self._sendCreateAccountEmail(protoUser, email)
        return(protoUser)

    def _sendCreateAccountEmail(self, user, email):
        # from girderformindlogger.models.token import Token
        #
        # token = Token().createToken(
        #     user, days=1, scope=TokenScope.EMAIL_VERIFICATION)
        web_url = os.getenv('WEB_URI') or 'localhost:8082'
        url = f'https://{web_url}/#/signup?email={email}'
        text = mail_utils.renderTemplate('emailCreateAccount.mako', {
            'url': url
        })
        mail_utils.sendMail(
            to=email,
            subject='MindLogger: Invitation',
            text=text)

    def remove(self, protoUser, progress=None, **kwargs):
        """
        Delete a protoUser, and all references to it in the database.

        :param protoUser: The protoUser document to delete.
        :type protoUser: dict
        :param progress: A progress context to record progress on.
        :type progress: girderformindlogger.utility.progress.ProgressContext or None.
        """
        from girderformindlogger.models.folder import Folder
        from girderformindlogger.models.group import Group
        from girderformindlogger.models.token import Token

        # Delete all authentication tokens owned by this user
        # Token().removeWithQuery({'userId': user['_id']})

        # Delete all pending group invites for this user
        # Group().update(
        #     {'requests': user['_id']},
        #     {'$pull': {'requests': user['_id']}}
        # )

        # Delete all of the folders under this user
        # folderModel = Folder()
        # folders = folderModel.find({
        #     'parentId': user['_id'],
        #     'parentCollection': 'user'
        # })
        # for folder in folders:
        #     folderModel.remove(folder, progress=progress, **kwargs)

        # Finally, delete the user document itself
        AccessControlledModel.remove(self, protoUser)
        if progress:
            progress.update(
                increment=1,
                message='Deleted protoUser ' + protoUser['_id']
            )
