import girderformindlogger
import itertools
import numpy as np
import pandas as pd
import simplejson
import time
import tzlocal
from bson.objectid import ObjectId
from datetime import datetime
from girderformindlogger.constants import AccessType
from girderformindlogger.models.activity import Activity as ActivityModel
from girderformindlogger.models.activitySet import ActivitySet as \
    ActivitySetModel
from girderformindlogger.models.applet import Applet as AppletModel
from girderformindlogger.models.folder import Folder
from girderformindlogger.models.group import Group
from girderformindlogger.models.response_folder import ResponseFolder as \
    ResponseFolderModel, ResponseItem as ResponseItemModel
from girderformindlogger.models.user import User as UserModel
from girderformindlogger.utility import jsonld_expander
from girderformindlogger.utility.response import formatResponse, last7Days
from girderformindlogger.utility.resource import listFromString
from girder_client import HttpError
from pymongo import DESCENDING

girder = {} # TODO: Delete once all in Python

def testCreateUser(email=None, admin=False):
    """
    Create a test user

    inputs
    ------

    email: String (optional)

    returns
    -------

    a user object from the server
    """
    randomUser = np.random.randint(1000000)
    displayName = 'test'
    # NOTE: girder makes login and email lowercase!!!
    login = 'testuser{}'.format(randomUser)
    if not email:
        email = 'testemail{}@testemail.com'.format(randomUser)
    password = 'password'
    createUser = UserModel().createUser(
        login=login,
        password=password,
        displayName=displayName,
        email=email
    )
    # assert 'authToken' in createUser.keys(), 'user has no token, {}'.format(createUser)
    assert createUser['email'] == email, 'email does not match, {} {}'.format(createUser['email'], email)
    assert createUser['displayName'] == displayName, 'displayName does not match'
    assert createUser['login'] == login, 'login does not match, {} {}'.format(createUser['login'], login)
    assert createUser['admin'] == admin, 'user\'s admin property does not match'
    assert createUser.get('public', False) == False, 'user is public!'

    return createUser

def authenticate(user, password="password"):
    """
    authenticate a user

    inputs
    ------
    user: a user object
    password: (optional) defaults to 'password'

    """
    return(
        UserModel().authenticate(
            login=user['login'] if isinstance(user, dict) else user,
            password=password
        )
    )


def getAppletById(user, ar):
    """
    make sure the user has exactly one expected applet in its list

    inputs
    ------
    user: a user object
    ar: an applet response object
    """
    currentUser = authenticate(user=user['login'], password='password')
    res = AppletModel().getAppletsForUser(role='user', user=currentUser)
    assert str(res[0]['_id']) == str(ar['_id']), 'applet ids are not the same'
    return 1


def addApplet(new_user, activitySetUrl):
    """
    adds an applet for the user, where the user becomes a manager for it.

    inputs
    ------

    new_user: a user oject (from testCreateUser)
    activitySetURL: String, a valid URL to an activity set.

    returns
    -------
    applet response object

    """
    currentUser = authenticate(new_user)

    # TODO: create an activity-set that JUST for testing.
    # make sure it has all the weird qualities that can break


    # for now, lets do the mindlogger demo
    activitySet = {}
    activitySet.update(ActivitySetModel().getFromUrl(
        activitySetUrl,
        'activitySet',
        currentUser
    ))
    randomAS = np.random.randint(1000000)
    ar = AppletModel().createApplet(
        name="testActivitySet{}".format(randomAS),
        activitySet={
            '_id': 'activitySet/{}'.format(activitySet.get('_id')),
            'url': activitySet.get(
                'meta',
                {}
            ).get(
                'activitySet',
                {}
            ).get('url', activitySetUrl)
        },
        user=currentUser
    )

    assert ar['_id'], 'there is no ID!'
    assert ar['meta']['activitySet']['url'] == activitySetUrl, \
        'the URLS do not match! {} {}'.format(
            ar['meta']['activitySet']['url'],
            activitySetUrl
        )

    assert getAppletById(
        new_user,
        ar
    ) == 1, 'something wrong with getAppletById'
    return ar


def getAppletsUser(user, n=1):
    """
    count applets for the user, and assert the length is a given amount.

    inputs
    ------
    user: a user object
    """
    currentUser = authenticate(user)
    appletList = AppletModel().getAppletsForUser(role='user', user=currentUser)
    assert len(
        appletList
    ) == n, 'this user should have {} applets. we get {}'.format(
        str(n),
        str(len(appletList))
    )
    return appletList



def getExpandedApplets(user):
    """
    get the fully expanded applet for a user

    inputs
    ------
    user: a user object
    """
    currentUser = authenticate(user)
    applets = AppletModel().getAppletsForUser(
        role='user',
        user=currentUser
    )
    expandedApplets = [
        jsonld_expander.formatLdObject(
            applet,
            'applet',
            currentUser
        ) for applet in applets
    ]
    # TODO: add some checks to the structure of expandedApplets to make sure
    # the mobile app can parse it.
    return expandedApplets


# def refreshApplet(user, appletObject):
#     """
#     refresh an applet
#
#     inputs
#     ------
#     user: a user object
#     appletObject: appletObject.
#     """
#     currentUser = authenticate(user)
#     appletId = appletObject['_id']
#     refreshResp = {} #girder.get('applet/{}?refreshCache=true'.format(appletId))
#     # TODO: somehow check that the refresh actually worked?
#     return refreshResp


def addSchedule(user, appletObject):
    """
    add a schedule to an applet

    inputs
    ------

    user: a user object
    appletObject: appletObject.
    """

    scheduleString = """{"type":2,"size":1,"fill":true,"minimumSize":0,"repeatCovers":true,"listTimes":false,"eventsOutside":false,"updateRows":false,"updateColumns":false,"around":1567321200000,"events":[{"data":{"title":"EMA: Morning","description":"","location":"","color":"#673AB7","forecolor":"#ffffff","calendar":"","busy":true,"icon":"","URI":"http://repronim.org/schema-standardization/activity-sets/mindlogger-demo/mindlogger-demo_schema","notifications":[{"start":"09:00","end":null,"random":false,"notifyIfIncomplete":false}],"useNotifications":true},"schedule":{}}]}"""
    schedule = simplejson.loads(scheduleString)
    authenticate(user)
    appletId = appletObject['_id']
    putResp = girder.put('applet/{}/constraints/'.format(appletId),
        data=dict(schedule=simplejson.dumps(schedule)))
    assert putResp['applet']['schedule'] == schedule


def inviteUserToApplet(user, appletObject, userB):
    """
    invite a user to an applet

    inputs
    ------
    user: a user object
    appletObject:
    userB: a user object of a user you want to invite. If they aren't
    defined yet, it should be a dict(email="emailaddress")
    """
    groupId = appletObject['roles']['user']['groups'][0]['id']
    currentUser = authenticate(user)
    group = Group().load(id=ObjectId(groupID), force=True)
    return Group().addUser(group, userB, level=AccessType.READ)
    # inviteResp = girder.post('group/{}/invitation'.format(groupId), {
    #     "email": userB['email']
    # })
    # assert inviteResp['public'] == False, 'invite is public!'
    # assert len(inviteResp['access']['users']), 'ths user was not added'
    # return inviteResp


def checkInvitesForUser(user, appletObject, userB):
    """
    check that a user's list of invites has our applet
    from the perspective of the manager

    inputs
    ------
    user: admin user object
    appletObject: appletObject
    userB: user who you want to check you invited
    """
    currentUser = authenticate(user)
    groupId = appletObject['roles']['user']['groups'][0]['id']
    pendingInvites = girder.get('group/{}/invitation'.format(groupId))
    value = False
    for invite in pendingInvites:
        if invite['email'] == userB['email']:
            value = True
            break
    assert value, "email not in list of pending invites, {}".format(pendingInvites)
    return 1


def checkForInvite(user, appletObject):
    """
    check that a user has an invite, from the perspective of the user

    inputs
    ------
    user: admin user object
    appletObject: appletObject

    """
    currentUser = authenticate(user)
    pendingInvitesForUser = girder.get('user/invites')
    groupId = appletObject['roles']['user']['groups'][0]['id']
    assert len(pendingInvitesForUser), "this user has no invites"
    assert pendingInvitesForUser[0]['_id'] == groupId, "this user doesn't have the invite you expect"
    return groupId


def acceptAppletInvite(user, appletObject):
    """
    accept an applet invite

    inputs
    ------
    user: admin user object
    appletObject: appletObject
    """
    groupId = checkForInvite(user, appletObject)
    currentUser = authenticate(user)
    resp = girder.post('group/{}/member'.format(groupId))
    assert resp['_modelType'] == 'group', "something weird about response, {}".format(resp)
    return 1


def getUserTable(user, appletObject):
    """
    returns a table of users/reviewers/managers for an applet
    for a user that's a manager

    inputs
    ------
    user: admin user object
    appletObject: appletObject
    """
    currentUser = authenticate(user)
    appletUsers = girder.get('applet/{}/users'.format(appletObject['_id']))
    return appletUsers


def checkAppletUserTableForUser(user, appletObject, userB):
    """
    check the user table for a user (as a manager)

    inputs
    ------
    user: admin user object
    appletObject: appletObject
    userB: user to check
    """
    ut = getUserTable(user, appletObject)
    assert len(list(filter(lambda x: x['login'] == userB['login'], ut))) == 1
    return ut


def postResponse(user, actURI, itemURI, appletObject, password="password"):
    """

    post a response as a user

    inputs
    ------
    user: user object
    actURI: activity uri
    itemURI: item URI
    appletObject: appletObject
    password (optional): defaults to password
    """
    currentUser = authenticate(user, password)
    appletId = appletObject['_id']

    expandedApplet = jsonld_expander.formatLdObject(
        appletObject,
        'applet',
        currentUser
    )

    a = expandedApplet['activities'][actURI]
    activityId = a['_id'].split('/')[1]

    response = {}
    response[itemURI] = np.random.randint(2)
    metadata = {
        'responses': response,
        'subject': {
            '@id': currentUser.get('_id')
        }
    }
    applet = appletObject
    activity = ActivityModel().load(
        activityId,
        user=currentUser,
        level=AccessType.READ
    )
    metadata['applet'] = {
        "@id": applet.get('_id'),
        "name": AppletModel().preferredName(applet),
        "url": applet.get(
            'url',
            applet.get('meta', {}).get('applet', {}).get('url')
        )
    }
    metadata['activity'] = {
        "@id": activity.get('_id'),
        "name": ActivityModel().preferredName(activity),
        "url": activity.get(
            'url',
            activity.get('meta', {}).get('activity', {}).get('url')
        )
    }
    now = datetime.now(tzlocal.get_localzone())
    appletName=metadata['applet']['name']
    UserResponsesFolder = ResponseFolderModel().load(
        user=currentUser,
        reviewer=currentUser,
        force=True
    )
    UserAppletResponsesFolder = Folder().createFolder(
        parent=UserResponsesFolder, parentType='folder',
        name=appletName, reuseExisting=True, public=False)
    AppletSubjectResponsesFolder = Folder().createFolder(
        parent=UserAppletResponsesFolder, parentType='folder',
        name=str(currentUser['_id']), reuseExisting=True, public=False)
    resp = ResponseItemModel().createResponseItem(
        folder=AppletSubjectResponsesFolder,
        name=now.strftime("%Y-%m-%d-%H-%M-%S-%Z"), creator=currentUser,
        description="{} response on {} at {}".format(
            metadata['activity']['name'],
            now.strftime("%Y-%m-%d"),
            now.strftime("%H:%M:%S %Z")
        ),
        reuseExisting=False
    )
    resp = ResponseItemModel().setMetadata(resp, metadata)
    assert resp['_id'], 'response is weird and does not have an id'
    assert 'activity' in resp['meta'].keys(), 'response does not have an activity'
    assert 'applet' in resp['meta'].keys(), 'response does not have an applet'
    assert 'responses' in resp['meta'].keys(), 'response does not have an response'
    return resp


def getLast7Days(user, appletObject):
    currentUser = authenticate(user)
    appletId = appletObject['_id']
    appletInfo = AppletModel().findOne({'_id': ObjectId(appletId)})
    return(last7Days(appletId, appletInfo, currentUser.get('_id'), currentUser))


def getDataForApplet(user, appletObject):
    """
    get the data for an applet (as a manager or reviewer)

    inputs
    ------
    user: admin user object
    appletObject: appletObject
    """
    currentUser = authenticate(user)
    appletId = appletObject['_id']
    appletInfo = AppletModel().findOne({'_id': appletId})
    reviewerGroupOfApplet = appletInfo['roles']['reviewer']['groups']
    assert len(reviewerGroupOfApplet) == 1, \
    'there should be only 1 group for an applet, for now.'
    reviewerGroupOfApplet = reviewerGroupOfApplet[0]['id']
    isAReviewer = list(filter(
        lambda x: x == reviewerGroupOfApplet, currentUser['groups']
    ))
    assert len(isAReviewer) == 1, 'the current user is not a reviewer'
    props = {
        "applet": [
            list(itertools.chain.from_iterable(
                [string_or_ObjectID(s) for s in listFromString(appletId)]
            )),
            "meta.applet.@id"
        ]
    }
    q = {
        props[prop][1]: {
            "$in": props[prop][0]
        } for prop in props if len(
            props[prop][0]
        )
    }
    allResponses = list(ResponseItemModel().find(
        query=q,
        user=currentUser,
        sort=[("created", DESCENDING)]
    ))
    outputResponse = [
        formatResponse(response)['thisResponse'] for response in allResponses
    ]
    formattedOutputResponse = []

    for response in outputResponse:
        tmp = {
            'schema:startDate': response['schema:startDate'],
            'schema:endDate': response['schema:endDate'],
            'userId': response['userId'],
        }
        for key, value in response['responses'].items():
            tmp['itemURI'] = key
            tmp['value'] = value
            formattedOutputResponse.append(tmp)

    return formattedOutputResponse


def makeAReviewer(user, appletObject, userB):
    """
    give a user reviewer priveleges

    inputs
    ------
    user: admin user object
    appletObject: appletObject
    userB: user to make a reviewer
    """
    currentUser = authenticate(user)
    reviewerGroupId = appletObject['roles']['reviewer']['groups'][0]['id']
    group = Group().load(id=ObjectId(reviewerGroupId), force=True)
    return Group().addUser(group, currentUser, level=AccessType.READ)

def acceptReviewerInvite(user, appletObject):
    """
    accept a reviewer invite for an applet

    inputs
    ------
    user: non-manager, non-reviewer user object
    appletObject: appletObject
    """
    currentUser = authenticate(user)
    reviewerGroupId = appletObject['roles']['reviewer']['groups'][0]['id']
    userCReviewerInvite = girder.post('group/{}/member'.format(reviewerGroupId))
    return userCReviewerInvite


def testPrivacyCheck(user, appletObject):
    """
    make sure the user cannot see private information

    inputs
    ------
    user: non-manager, non-reviewer user object
    appletObject: appletObject
    """
    try:
        getDataForApplet(user, appletObject)
        raise ValueError('User can see private data!!')
    except HttpError:
        return 1

def removeApplet(user, appletObject):
    """
    remove an applet from a user without deleting their data

    inputs
    ------
    user: admin user object
    appletObject: appletObject
    """
    currentUser = authenticate(user)
    groupId = appletObject['roles']['user']['groups'][0]['id']
    Group().removeUser(Group().load(id=groupId, force=True), user=currentUser)


def deleteApplet(user, appletObject):
    """
    remove an applet from a user and also delete the user's data.

    inputs
    ------
    user: admin user object
    appletObject: appletObject
    """
    currentUser = authenticate(user)
    groupId = appletObject['roles']['user']['groups'][0]['id']
    Group().removeUser(
        Group().load(id=groupId, force=True),
        user=currentUser,
        delete=True
    )


def deactivateApplet(user, appletObject):
    """

    inputs
    ------
    user: admin user object
    appletObject: appletObject
    """
    currentUser = authenticate(user)
    return girder.delete('applet/{}'.format(appletObject['_id']))


def testDeleteUser(user):
    currentUser = authenticate(user)

    deleteUser = girder.delete('user/{}'.format(user['_id']))

    assert deleteUser['message'] == 'Deleted user {}.'.format(user['login']), "{} does not equal {}".format(deleteUser['message'],
                                                             'Deleted user {}'.format(user['login']))

    return 1

def tryExceptTester(func, args, message, nreturn = 1):
    """
    a wrapper function to run a function and print a message in green if it succeeds
    or red if it fails.

    inputs::
    func: a function
    args: a list of args to the function
    message: a string, what to print about the function
    nreturn: (default 1), number of expected return params.
    """
    try:
        output = func(*args)
        print("\033[1;32;40m {}".format(message))
        print("\033[0;37;40m ")
        return output
    except Exception as e:
        import sys, traceback
        print("\033[1;31;40m {}".format(message))
        print("\033[1;31;40m {}  \n".format(e))
        print("\033[0;37;40m ")
        print(sys.exc_info())
        print(traceback.print_tb(sys.exc_info()[2]))
        raise(e)
        return [None] * nreturn


def fullTest(activitySetUrl, act1, act2, act1Item, act2Item):

    # Create a new user

    def step01():
        existingUser = UserModel().findOne({})
        if existingUser is None:
            # First user will be admin on a new image
            admin = testCreateUser(admin=True)
        user = testCreateUser()
        currentUser = authenticate(user)
        return user

    user = tryExceptTester(step01,
        [],
        'Create a new user',
        2)

    # make sure the user has 0 applets
    def step02(user):
        no_applets = getAppletsUser(user, 0)
        return no_applets

    no_applets = tryExceptTester(step02,
                                 [user],
                                 'Make sure the user has 0 applets')

    # add an applet and make sure it was added
    def step03(user, activitySetUrl):
        appletObject = addApplet(user, activitySetUrl)
        appletList = getAppletsUser(user, 1)
        checkItWasAdded = getAppletById(user, appletObject)
        return appletObject, appletList, checkItWasAdded

    appletObject, appletList, checkItWasAdded = tryExceptTester(
        step03,
        [user, activitySetUrl],
        'add an applet and make sure it was added',
        3
    )

    # expand and refresh the applet
    # print('\033[1;37;40m expand and refresh the applet')
    def step04(user, appletObject):
        appletsExpanded = getExpandedApplets(user)
        assert len(appletsExpanded) == 1, 'we get no expanded applets.'
        appletRefreshed = appletsExpanded # refreshApplet(user, appletObject)
        return appletsExpanded, appletRefreshed

    appletsExpanded, appletRefreshed = tryExceptTester(
        step04,
        [user, appletObject],
        'expand and refresh the applet',
        2
    )

    # add a schedule to the applet
    # print('add a schedule to the applet')

    # def step05(user, appletObject):
    #     addSchedule(user, appletObject)
    #
    # tryExceptTester(
    #     step05,
    #     [user, appletObject],
    #     'add a schedule to the applet'
    # )

    # create a new user and invite them to the applet
    # print('create a new user and invite them to the applet')
    def step06(user, appletObject):
        userB = testCreateUser()
        userBInvite = {} #inviteUserToApplet(user, appletObject, userB)
        return userB, userBInvite

    userB, userBInvite = tryExceptTester(
        step06,
        [user, appletObject],
        'create a new user and invite them to the applet',
        2
    )

    userC, userCInvite = tryExceptTester(
        step06,
        [user, appletObject],
        'create a new user and invite them to the applet',
        2
    )
    #
    # # check that the manager invited the user
    # # print('check that the manager invited the user')
    # def step07(user, appletObject, userB):
    #     checkInvitesForUser(user, appletObject, userB)
    #
    # tryExceptTester(
    #     step07,
    #     [user, appletObject, userB],
    #     'check that the manager invited the user'
    # )
    #
    # # accept the applet invite
    # # print('accept the applet invite')
    # def step08(userB, appletObject):
    #     acceptAppletInvite(userB, appletObject)
    #
    # tryExceptTester(step08, [userB, appletObject], 'accept the applet invite')
    #
    # # invite someone that doesn't have an account yet
    # # print('\033[0;37;40m invite someone that doesn\'t have an account yet')
    #
    # def step09(user, appletObject):
    #     userCemail = 'randomuserc{}@test.com'.format(np.random.randint(1000000))
    #     inviteC = {} # inviteUserToApplet(user, appletObject, {'email': userCemail})
    #     appletUserTable = {} #checkAppletUserTableForUser(user, appletObject, {'email': userCemail})
    #     return userCemail, inviteC, appletUserTable
    #
    # userCemail, inviteC, appletUserTable = tryExceptTester(
    #     step09,
    #     [user, appletObject],
    #     'invite someone that doesn\'t have an account yet',
    #     3
    # )
    #
    #
    # # create that person's account, check that they have an invite, and
    # # accept the invite
    #
    # def step10(userCemail):
    #     userC = testCreateUser(userCemail)
    #     userCApplets = getAppletsUser(userC, 0)
    #     return userC, userCApplets
    #
    # userC, userCApplets = tryExceptTester(
    #     step10,
    #     [userCemail],
    #     'create that person\'s account, check that they have an invite',
    #     2
    # )
    #
    # # check from perspective of admin and user, if the invite exists.
    # # print('check from perspective of admin and user, if the invite exists.')
    # def step11(user, appletObject, userC):
    #     checkInvitesForUser(user, appletObject, userC)
    #     checkForInvite(userC, appletObject)
    #
    # tryExceptTester(
    #     step11,
    #     [user, appletObject, userC],
    #     'check from perspective of admin and user, if the invite exists.'
    # )
    #
    # # accept user c's invitation
    # def step12(userC, appletObject):
    #     acceptAppletInvite(userC, appletObject)
    #     userCApplets = getAppletsUser(userC, 1)
    #     return userCApplets
    #
    # userCApplets = tryExceptTester(
    #     step12,
    #     [userC, appletObject],
    #     'accept user C\'s invitation'
    # )

    # post a response
    # each user posts a response for a single item in each activity.
    def step13(user, userB, userC, act1, act1Item, act2, act2Item):
        for u in [user, userB]:
            for i in range(2):
                postResponse(u, act1, act1Item, appletObject)
                time.sleep(1)
                postResponse(u, act2, act2Item, appletObject)
                time.sleep(1)
            time.sleep(1)

    tryExceptTester(
        step13,
        [user, userB, userC, act1, act1Item, act2, act2Item],
        'posted responses for all 3 users'
    )


    # get the last 7 days
    #print('get the last 7 days of data')

    def step14(user, userB, userC, appletObject):
        last7user = getLast7Days(user, appletObject)
        last7userB = getLast7Days(userB, appletObject)
        last7userC = {} # getLast7Days(userC, appletObject)

        assert len(last7user['responses']) == 2, 'there should only be 2 responses'
        assert len(last7userB['responses']) == 2, 'there should only be 2 responses'
        # assert len(last7userC['responses']) == 2, 'there should only be 2 responses'
        return last7user, last7userB, last7userC

    last7user, last7userB, last7userC = tryExceptTester(
        step14,
        [user, userB, userC, appletObject],
        'get the last 7 days of data for each user',
        3
    )

    # # as a manager, see the data. make sure you see emails
    # def step15(user, appletObject):
    #     appletData = getDataForApplet(user, appletObject)
    #     assert '@' in appletData[0]['userId'], 'manager cannot see emails'
    #     return appletData
    #
    # appletData = tryExceptTester(
    #     step15,
    #     [user, appletObject],
    #     'as a manager, see the data. make sure you see emails'
    # )

    # add user as a reviewer
    print('add user as a reviewer')
    def step16(user, appletObject, userC):
        userCReviewer = makeAReviewer(user, appletObject, userC)
        userCAcceptReviewer = {} # acceptReviewerInvite(userC, appletObject)
        return userCReviewer, userCAcceptReviewer

    userCReviewer, userCAcceptReviewer = tryExceptTester(
        step16,
        [user, appletObject, userC],
        'add user as a reviewer',
        2
    )

    # as a reviewer, see the data and make sure you don't see emails
    # print('as a reviewer, see the data and make sure you don\'t see emails')
    # def step17(userC, appletObject):
    #     appletData = getDataForApplet(userC, appletObject)
    #     assert '@' not in appletData[0]['userId'], 'reviewer can see emails'
    #     return appletData
    #
    # appletData = tryExceptTester(
    #     step17,
    #     [userC, appletObject],
    #     'as a reviewer, see the data and make sure you don\'t see emails'
    # )

    # make sure we don't see any data as a non-manager and non-reviewer
    # print('make sure we don\'t see any data as a non-manager and non-reviewer')
    def step18(userB, appletObject):
        try:
            testPrivacyCheck(userB, appletObject)
        except AssertionError:
            return 0

    tryExceptTester(
        step18,
        [userB, appletObject],
        'make sure we don\'t see any data as a non-manager and non-reviewer'
    )

    # # remove an applet without deleting data
    #
    # def step19(userC, appletObject):
    #     removeApplet(userC, appletObject)
    #     userCApplets = getAppletsUser(userC, 0)
    #     appletData = getDataForApplet(user, appletObject)
    #
    #     userCData = list(filter(lambda x: x['userId'] == userC['login'],
    #                         appletData))
    #     assert len(userCData), "the user does not have data, but we expect it"
    #
    # tryExceptTester(
    #     step19,
    #     [userB, appletObject],
    #     'remove an applet without deleting data'
    # )
    #
    # # remove an applet and delete data
    #
    # def step20(userB, appletObject):
    #     deleteApplet(userB, appletObject)
    #     userBApplets = getAppletsUser(userB, 0)
    #     appletData = getDataForApplet(user, appletObject)
    #
    #     userBData = list(filter(lambda x: x['userId'] == userB['login'],
    #                             appletData))
    #     assert len(userBData) == 0, "the user still has data, but they should not"
    #
    # tryExceptTester(
    #     step20,
    #     [userB, appletObject],
    #     'remove an applet and delete data'
    # )
    #
    # # deactivate an applet
    # def step21(user, appletObject):
    #     appletDeactivated = deactivateApplet(user, appletObject)
    #     return appletDeactivated
    #
    # appletDeactivated = tryExceptTester(
    #     step21,
    #     [user, appletObject],
    #     'deactivate an applet'
    # )
    #
    # # remove all users
    # def step22(user, userB, userC):
    #     testDeleteUser(user)
    #     testDeleteUser(userB)
    #     # testDeleteUser(userC)
    #
    # tryExceptTester(
    #     step22,
    #     [user, userB, userC],
    #     'remove all users'
    # )
    #
    # return 1
