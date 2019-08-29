# -*- coding: utf-8 -*-
import sentry_sdk
from girderformindlogger.plugin import GirderPlugin
from girderformindlogger.models.setting import Setting

from . import rest
from .settings import PluginSettings


class SentryPlugin(GirderPlugin):
    DISPLAY_NAME = 'Sentry'
    CLIENT_SOURCE_PATH = 'web_client'

    def load(self, info):
        info['apiRoot'].sentry = rest.Sentry()

        sentry_sdk.init(dsn=Setting().get(PluginSettings.BACKEND_DSN))
