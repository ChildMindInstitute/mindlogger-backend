# -*- coding: utf-8 -*-
import datetime

import pymongo
from girderformindlogger.models.setting import Setting
from girderformindlogger.models.model_base import Model


class Shield(Model):
    def initialize(self):
        self.name = 'shield'

    def set_default(self, user, ctx):
        self.save({
                "user": user.get('_id'),
                "source": ctx,
                "date": datetime.datetime.now(),
                "blocked": False,
                "count": 1,
                "date_blocked": None
            }, validate=False)
