#!/usr/bin/env python
# -*- coding: utf-8 -*-
from bson import ObjectId

from ..describe import autoDescribeRoute, Description
from girderformindlogger.api import access
from girderformindlogger.constants import TokenScope
from girderformindlogger.models.account_profile import AccountProfile

from ..rest import Resource


class Account(Resource):
    def __init__(self):
        super(Account, self).__init__()
        self.resourceName = 'account'
        self._model = AccountProfile()
        self.route('PUT', (':id',), self.updateAccountDB)

    @access.user(scope=TokenScope.DATA_WRITE)
    @autoDescribeRoute(
        Description('Update profile personal db uri')
        .param('id', 'account id', required=True, dataType='string')
        .param('dbURL', 'db uri for store the user responses',
               required=True, default=False, dataType='string')
    )
    def updateAccountDB(self, id, dbURL):
        account = self._model.findOne({"accountId": ObjectId(id)})
        self._model.validateDBURL(dbURL)
        account.update({
           'db': dbURL
        })
        self._model.save(account, validate=False)
        return 'DB was saved'
