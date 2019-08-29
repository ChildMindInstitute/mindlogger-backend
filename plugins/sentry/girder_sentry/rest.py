# -*- coding: utf-8 -*-
from girderformindlogger.api import access
from girderformindlogger.api.describe import Description, describeRoute
from girderformindlogger.api.rest import Resource
from girderformindlogger.models.setting import Setting

from .settings import PluginSettings


class Sentry(Resource):
    def __init__(self):
        super(Sentry, self).__init__()
        self.resourceName = 'sentry'
        self.route('GET', ('dsn',), self._getDsn)

    @access.public
    @describeRoute(
        Description('Public URL for getting the Sentry DSN.')
    )
    def _getDsn(self, params):
        dsn = Setting().get(PluginSettings.FRONTEND_DSN)
        return {'sentry_dsn': dsn}
