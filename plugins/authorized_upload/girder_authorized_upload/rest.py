# -*- coding: utf-8 -*-
from girderformindlogger.api import access
from girderformindlogger.api.describe import describeRoute, Description
from girderformindlogger.api.rest import loadmodel, Resource
from girderformindlogger.constants import AccessType, TokenScope
from girderformindlogger.exceptions import ValidationException
from girderformindlogger.models.setting import Setting
from girderformindlogger.models.token import Token
from girderformindlogger.settings import SettingKey
from girderformindlogger.utility import mail_utils

from .constants import TOKEN_SCOPE_AUTHORIZED_UPLOAD


class AuthorizedUpload(Resource):
    def __init__(self):
        super(AuthorizedUpload, self).__init__()
        self.resourceName = 'authorized_upload'

        self.route('POST', (), self.createAuthorizedUpload)

    @access.user(scope=TokenScope.DATA_WRITE)
    @loadmodel(map={'folderId': 'folder'}, model='folder', level=AccessType.WRITE)
    @describeRoute(
        Description('Create an authorized upload URL.')
        .param('folderId', 'Destination folder ID for the upload.')
        .param('duration', 'How many days the token should last.', required=False, dataType='int')
    )
    def createAuthorizedUpload(self, folder, params):
        try:
            if params.get('duration'):
                days = int(params.get('duration'))
            else:
                days = Setting().get(SettingKey.COOKIE_LIFETIME)
        except ValueError:
            raise ValidationException('Token duration must be an integer, or leave it empty.')

        token = Token().createToken(days=days, user=self.getCurrentUser(), scope=(
            TOKEN_SCOPE_AUTHORIZED_UPLOAD, 'authorized_upload_folder_%s' % folder['_id']))

        url = '%s#authorized_upload/%s/%s' % (
            mail_utils.getEmailUrlPrefix(), folder['_id'], token['_id'])

        return {'url': url}
