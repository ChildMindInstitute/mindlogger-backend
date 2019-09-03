# -*- coding: utf-8 -*-
from girderformindlogger.api import access
from girderformindlogger.api.describe import Description, autoDescribeRoute
from girderformindlogger.api.rest import boundHandler
from girderformindlogger.models.setting import Setting

from .settings import PluginSettings


@access.user
@boundHandler
@autoDescribeRoute(
    Description('Get list of item licenses.')
    .param('default', 'Whether to return the default list of item licenses.',
           required=False, dataType='boolean', default=False)
)
def getLicenses(self, default):
    if default:
        licenses = Setting().getDefault(PluginSettings.LICENSES)
    else:
        licenses = Setting().get(PluginSettings.LICENSES)

    return licenses
