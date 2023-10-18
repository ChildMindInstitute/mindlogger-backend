# -*- coding: utf-8 -*-
from ..rest import Resource
from ..describe import Description, autoDescribeRoute
from girderformindlogger.api import access
from girderformindlogger.constants import TokenScope
from girderformindlogger.models.token import Token as TokenModel
from girderformindlogger.models.user import User as UserModel
from girderformindlogger.models.profile import Profile as ProfileModel
from bson.objectid import ObjectId
from girderformindlogger.exceptions import RestException
import datetime
from pymongo import DESCENDING


class Token(Resource):
    """API Endpoint for non-user tokens in the system."""

    def __init__(self):
        super(Token, self).__init__()
        self.resourceName = 'token'
        self._model = TokenModel()

        self.route('DELETE', ('session',), self.deleteSession)
        self.route('GET', ('session',), self.getSession)
        self.route('GET', ('session_for_user', ':profileId'), self.getSessionForUser)
        self.route('GET', ('current',), self.currentSession)
        self.route('GET', ('scopes',), self.listScopes)

    @access.public
    @autoDescribeRoute(
        Description('Retrieve the current session information.')
        .responseClass('Token')
    )
    def currentSession(self):
        return self.getCurrentToken()

    @access.public
    @autoDescribeRoute(
        Description('Get an anonymous session token for the system.')
        .notes('If you are logged in, this will return a token associated with that login.')
        .responseClass('Token')
    )
    def getSession(self):
        token = self.getCurrentToken()

        # Only create and send new cookie if token isn't valid or will expire soon
        if not token:
            token = self.sendAuthTokenCookie(None, scope=TokenScope.ANONYMOUS_SESSION)

        return {
            'token': token['_id'],
            'expires': token['expires']
        }

    @access.user(scope=TokenScope.DATA_READ)
    @autoDescribeRoute(
        Description('Get a token for user')
        .responseClass('Token')
    )
    def getSessionForUser(self, profileId):
        profile = ProfileModel().load(ObjectId(profileId), force=True)
        if not profile:
            raise RestException('profile not found', 404)

        userId = profile['userId']
        accountId = profile['accountId']

        user = UserModel().findOne({'_id': ObjectId(userId)}, force=True)
        if not user:
            raise RestException('User not found', 404)

        tokens = TokenModel().find(
            query={
                'userId': ObjectId(userId),
                'accountId': ObjectId(accountId),
                'scope': {'$in': ['core.user_auth']},
                'expires': {'$gt': datetime.datetime.utcnow()}
            },
            sort=[("created", DESCENDING)],
            limit=1
        )
        token = tokens[0] if tokens.count() > 0 else None
        if not token:
            user = UserModel().load(ObjectId(userId), force=True)
            token = TokenModel().createToken(user, days=1, scope=[TokenScope.USER_AUTH], accountId=accountId)

        return {
            'token': token['_id'],
            'expires': token['expires']
        }

    @access.token
    @autoDescribeRoute(
        Description('Remove a session from the system.')
        .responseClass('Token')
        .notes('Attempts to delete your authentication cookie.')
    )
    def deleteSession(self):
        token = self.getCurrentToken()
        if token:
            self._model.remove(token)
        self.deleteAuthTokenCookie()
        return {'message': 'Session deleted.'}

    @access.public
    @autoDescribeRoute(
        Description('List all token scopes available in the system.')
    )
    def listScopes(self):
        return TokenScope.listScopes()
