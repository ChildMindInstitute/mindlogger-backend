import girderformindlogger
import girder_client
import pandas as pd
import numpy as np
import simplejson
from girder_client import HttpError
import time


def createGirder(host, port):
    """
    creates a girder client. this is the first argument to
    the subsequent functions below

    inputs
    ------
    host: string ('localhost' or 'dev.mindlogger.org')
    port: integer (443 if https, 8080 if local)
    """
    return girder_client.GirderClient(host=host, port=port)


def testCreateUser(girder, email=None, admin=False):
    """
    Create a test user

    inputs
    ------
    girder: a GirderClient object
    email: String (optional)

    returns
    -------

    a user object from the server
    """
    randomUser = np.random.randint(1000000)
    firstName = 'test'
    lastName = 'user'
    # NOTE: girder makes login and email lowercase!!!
    login = 'testuser{}'.format(randomUser)
    if not email:
        email = 'testemail{}@testemail.com'.format(randomUser)
    password = 'password'
    createUser = girder.post('user', parameters=dict(firstName=firstName,
                                        lastName=lastName,
                                        login=login,
                                        email=email,
                                        password=password
                                       )
               )
    # assert 'authToken' in createUser.keys(), 'user has no token, {}'.format(createUser)
    assert createUser['email'] == email, 'email does not match, {} {}'.format(createUser['email'], email)
    assert createUser['firstName'] == firstName, 'firstName does not match'
    assert createUser['lastName'] == lastName, 'lastName does not match'
    assert createUser['login'] == login, 'login does not match, {} {}'.format(createUser['login'], login)
    if not admin:
        assert createUser['admin'] == False, 'user is an admin'
    assert createUser['_modelType'] == 'user', 'model is not user'
    assert createUser['public'] == False, 'user is public!'

    return createUser

def authenticate(girder, user, password="password"):
    """
    authenticate a user

    inputs
    ------

    girder: a Girder Client object
    user: a user object
    password: (optional) defaults to 'password'

    """
    girder.authenticate(username=user['login'], password='password')


def getAppletById(girder, user, ar):
    """
    make sure the user has an applet in its list

    inputs
    ------
    girder: GirderClient
    user: a user object
    ar: an applet response object
    """
    girder.authenticate(username=user['login'],
        password='password')
    res = girder.get('applet/{}'.format(ar['_id']))
    assert res['applet']['_id'].split('applet/')[1] == ar['_id'], 'applet ids are not the same'
    return 1


def addApplet(girder, new_user, activitySetUrl):
    """
    adds an applet for the user, where the user becomes a manager for it.

    inputs
    ------
    girder: a GirderClient object
    new_user: a user oject (from testCreateUser)
    activitySetURL: String, a valid URL to an activity set.

    returns
    -------
    applet response object

    """
    authenticate(girder, new_user)

    # TODO: create an activity-set that JUST for testing.
    # make sure it has all the weird qualities that can break


    # for now, lets do the mindlogger demo
    activitySetUrl = activitySetUrl
    randomAS = np.random.randint(1000000)
    ar = girder.post('applet', parameters=dict(activitySetUrl = activitySetUrl, name='testActivitySet{}'.format(randomAS)))

    assert ar['_id'], 'there is no ID!'
    assert ar['meta']['activitySet']['url'] == activitySetUrl, 'the URLS do not match! {} {}'.format(ar['meta']['activitySet']['url'], activitySetUrl)

    assert getAppletById(girder, new_user, ar) == 1, 'something wrong with getAppletById'
    return ar


def getAppletsUser(girder, user, n=1):
    """
    count applets for the user, and assert the length is a given amount.

    inputs
    ------

    girder: a GirderClient object
    user: a user object
    """
    authenticate(girder, user)
    appletList = girder.get('user/applets')
    assert len(appletList) == n, 'this user should have {} applets. we get {}'.format(n, len(appletList))
    return appletList



def getExpandedApplets(girder, user):
    """
    get the fully expanded applet for a user

    inputs
    ------

    girder: a GirderClient object
    user: a user object
    """
    authenticate(girder, user)
    expandedApplets = girder.get('user/applets')
    # TODO: add some checks to the structure of expandedApplets to make sure
    # the mobile app can parse it.
    return expandedApplets


def refreshApplet(girder, user, appletObject):
    """
    refresh an applet

    inputs
    ------

    girder: girderClient object
    user: a user object
    appletObject: appletObject.
    """
    authenticate(girder, user)
    appletId = appletObject['_id']
    refreshResp = girder.get('applet/{}?refreshCache=true'.format(appletId))
    # TODO: somehow check that the refresh actually worked?
    return refreshResp


def addSchedule(girder, user, appletObject):
    """
    add a schedule to an applet

    inputs
    ------

    girder: girderClient object
    user: a user object
    appletObject: appletObject.
    """

    scheduleString = """{"type":2,"size":1,"fill":true,"minimumSize":0,"repeatCovers":true,"listTimes":false,"eventsOutside":false,"updateRows":false,"updateColumns":false,"around":1567321200000,"events":[{"data":{"title":"EMA: Morning","description":"","location":"","color":"#673AB7","forecolor":"#ffffff","calendar":"","busy":true,"icon":"","URI":"http://repronim.org/schema-standardization/activity-sets/mindlogger-demo/mindlogger-demo_schema","notifications":[{"start":"09:00","end":null,"random":false,"notifyIfIncomplete":false}],"useNotifications":true},"schedule":{}}]}"""
    schedule = simplejson.loads(scheduleString)
    authenticate(girder, user)
    appletId = appletObject['_id']
    putResp = girder.put('applet/{}/constraints/'.format(appletId),
        data=dict(schedule=simplejson.dumps(schedule)))
    assert putResp['applet']['schedule'] == schedule


def inviteUserToApplet(girder, user, appletObject, userB):
    """
    invite a user to an applet

    inputs
    ------

    girder: a GirderClient object
    user: a user object
    appletObject:
    userB: a user object of a user you want to invite. If they aren't
    defined yet, it should be a dict(email="emailaddress")
    """
    groupId = appletObject['roles']['user']['groups'][0]['id']
    authenticate(girder, user)
    inviteResp = girder.post('group/{}/invitation'.format(groupId), {
        "email": userB['email']
    })
    assert inviteResp['public'] == False, 'invite is public!'
    assert len(inviteResp['access']['users']), 'ths user was not added'
    return inviteResp


def checkInvitesForUser(girder, user, appletObject, userB):
    """
    check that a user's list of invites has our applet
    from the perspective of the manager

    inputs
    ------

    girder: GirderClient
    user: admin user object
    appletObject: appletObject
    userB: user who you want to check you invited
    """
    authenticate(girder, user)
    groupId = appletObject['roles']['user']['groups'][0]['id']
    pendingInvites = girder.get('group/{}/invitation'.format(groupId))
    value = False
    for invite in pendingInvites:
        if invite['email'] == userB['email']:
            value = True
            break
    assert value, "email not in list of pending invites, {}".format(pendingInvites)
    return 1


def checkForInvite(girder, user, appletObject):
    """
    check that a user has an invite, from the perspective of the user

    inputs
    ------

    girder: GirderClient
    user: admin user object
    appletObject: appletObject

    """
    authenticate(girder, user)
    pendingInvitesForUser = girder.get('user/invites')
    groupId = appletObject['roles']['user']['groups'][0]['id']
    assert len(pendingInvitesForUser), "this user has no invites"
    assert pendingInvitesForUser[0]['_id'] == groupId, "this user doesn't have the invite you expect"
    return groupId


def acceptAppletInvite(girder, user, appletObject):
    """
    accept an applet invite

    inputs
    ------

    girder: GirderClient
    user: admin user object
    appletObject: appletObject
    """
    groupId = checkForInvite(girder, user, appletObject)
    authenticate(girder, user)
    resp = girder.post('group/{}/member'.format(groupId))
    assert resp['_modelType'] == 'group', "something weird about response, {}".format(resp)
    return 1


def getUserTable(girder, user, appletObject):
    """
    returns a table of users/reviewers/managers for an applet
    for a user that's a manager

    inputs
    ------

    girder: GirderClient
    user: admin user object
    appletObject: appletObject
    """
    authenticate(girder, user)
    appletUsers = girder.get('applet/{}/users'.format(appletObject['_id']))
    return appletUsers


def checkAppletUserTableForUser(girder, user, appletObject, userB):
    """
    check the user table for a user (as a manager)

    inputs
    ------

    girder: GirderClient
    user: admin user object
    appletObject: appletObject
    userB: user to check
    """
    ut = getUserTable(girder, user, appletObject)
    assert len(list(filter(lambda x: x['email'] == userB['email'], ut))) == 1
    return ut


def postResponse(girder, user, actURI, itemURI, appletObject, password="password"):
    """

    post a response as a user

    inputs
    ------

    girder: GirderClient
    user: user object
    actURI: activity uri
    itemURI: item URI
    appletObject: appletObject
    password (optional): defaults to password
    """

    authenticate(girder, user, password)
    appletId = appletObject['_id']

    expandedApplets = getExpandedApplets(girder, user)
    expandedApplet = list(filter(lambda x: x['applet']['_id'].split('/')[1] == appletId, expandedApplets))
    assert len(expandedApplet) == 1, "can't find the applet you want when posting a response!"

    expandedApplet = expandedApplet[0]

    a = expandedApplet['activities'][actURI]
    activityId = a['_id'].split('/')[1]

    response = {}
    response[itemURI] = np.random.randint(2)

    resp = girder.post('response/{}/{}'.format(appletId, activityId),
                       data={'metadata': simplejson.dumps(
                       {
                           'activity': activityId,
                           'applet': appletId,
                           'responses': response
                       }
                       )})
    assert resp['_id'], 'response is weird and does not have an id'
    assert 'activity' in resp['meta'].keys(), 'response does not have an activity'
    assert 'applet' in resp['meta'].keys(), 'response does not have an applet'
    assert 'responses' in resp['meta'].keys(), 'response does not have an response'
    return resp


def getLast7Days(girder, user, appletObject):
    authenticate(girder, user)
    appletId = appletObject['_id']
    last7 = girder.get('response/last7Days/{}'.format(appletId))
    return last7


def getDataForApplet(girder, user, appletObject):
    """
    get the data for an applet (as a manager or reviewer)

    inputs
    ------

    girder: GirderClient
    user: admin user object
    appletObject: appletObject
    """
    authenticate(girder, user)
    appletId = appletObject['_id']
    resp = girder.get('response', parameters={
        'applet': appletId
    })
    return resp


def makeAReviewer(girder, user, appletObject, userB):
    """
    give a user reviewer priveleges

    inputs
    ------

    girder: GirderClient
    user: admin user object
    appletObject: appletObject
    userB: user to make a reviewer
    """
    authenticate(girder, user)
    reviewerGroupId = appletObject['roles']['reviewer']['groups'][0]['id']
    return girder.post('group/{}/invitation'.format(reviewerGroupId),
    {'email': userB['email']})


def acceptReviewerInvite(girder, user, appletObject):
    """
    accept a reviewer invite for an applet

    inputs
    ------

    girder: GirderClient
    user: non-manager, non-reviewer user object
    appletObject: appletObject
    """
    authenticate(girder, user)
    reviewerGroupId = appletObject['roles']['reviewer']['groups'][0]['id']
    userCReviewerInvite = girder.post('group/{}/member'.format(reviewerGroupId))
    return userCReviewerInvite


def testPrivacyCheck(girder, user, appletObject):
    """
    make sure the user cannot see private information

    inputs
    ------

    girder: GirderClient
    user: non-manager, non-reviewer user object
    appletObject: appletObject
    """
    try:
        getDataForApplet(girder, user, appletObject)
        raise ValueError('User can see private data!!')
    except HttpError:
        return 1

def removeApplet(girder, user, appletObject):
    """
    remove an applet from a user without deleting their data

    inputs
    ------

    girder: GirderClient
    user: admin user object
    appletObject: appletObject
    """
    authenticate(girder, user)
    groupId = appletObject['roles']['user']['groups'][0]['id']
    girder.delete('group/{}/member?delete=false'.format(groupId))


def deleteApplet(girder, user, appletObject):
    """
    remove an applet from a user and also delete the user's data.

    inputs
    ------

    girder: GirderClient
    user: admin user object
    appletObject: appletObject
    """
    authenticate(girder, user)
    groupId = appletObject['roles']['user']['groups'][0]['id']
    girder.delete('group/{}/member?delete=true'.format(groupId))


def deactivateApplet(girder, user, appletObject):
    """

    inputs
    ------

    girder: GirderClient
    user: admin user object
    appletObject: appletObject
    """
    authenticate(girder, user)
    return girder.delete('applet/{}'.format(appletObject['_id']))


def testDeleteUser(girder, user):

    authenticate(girder, user)

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


def fullTest(server, port, activitySetUrl, act1, act2, act1Item, act2Item):

    # Create a girder client and a new user

    def step01():
        gc = createGirder(server, port)
        admin = testCreateUser(gc, admin=True) # First user will be admin on a new image
        user = testCreateUser(gc)
        authenticate(gc, user)
        return gc, user

    gc, user = tryExceptTester(step01,
        [],
        'Create a girder client and a new user',
        2)

    # make sure the user has 0 applets
    def step02(gc, user):
        no_applets = getAppletsUser(gc, user, 0)
        return no_applets

    no_applets = tryExceptTester(step02,
                                 [gc, user],
                                 'Make sure the user has 0 applets')

    # add an applet and make sure it was added
    def step03(gc, user, activitySetUrl):
        appletObject = addApplet(gc, user, activitySetUrl)
        appletList = getAppletsUser(gc, user, 1)
        checkItWasAdded = getAppletById(gc, user, appletObject)
        return appletObject, appletList, checkItWasAdded

    appletObject, appletList, checkItWasAdded = tryExceptTester(step03,
                                                                [gc, user, activitySetUrl],
                                                                'add an applet and make sure it was added',
                                                                3)

    # expand and refresh the applet
    # print('\033[1;37;40m expand and refresh the applet')
    def step04(gc, user, appletObject):
        appletsExpanded = getExpandedApplets(gc, user)
        assert len(appletsExpanded) == 1, 'we get no expanded applets.'
        appletRefreshed = refreshApplet(gc, user, appletObject)
        return appletsExpanded, appletRefreshed

    appletsExpanded, appletRefreshed = tryExceptTester(
        step04,
        [gc, user, appletObject],
        'expand and refresh the applet',
        2
    )

    # add a schedule to the applet
    # print('add a schedule to the applet')

    def step05(gc, user, appletObject):
        addSchedule(gc, user, appletObject)

    tryExceptTester(
        step05,
        [gc, user, appletObject],
        'add a schedule to the applet'
    )

    # create a new user and invite them to the applet
    # print('create a new user and invite them to the applet')
    def step06(gc, user, appletObject):
        userB = testCreateUser(gc)
        userBInvite = inviteUserToApplet(gc, user, appletObject, userB)
        return userB, userBInvite

    userB, userBInvite = tryExceptTester(
        step06,
        [gc, user, appletObject],
        'create a new user and invite them to the applet',
        2
    )

    # check that the manager invited the user
    # print('check that the manager invited the user')
    def step07(gc, user, appletObject, userB):
        checkInvitesForUser(gc, user, appletObject, userB)

    tryExceptTester(
        step07,
        [gc, user, appletObject, userB],
        'check that the manager invited the user'
    )

    # accept the applet invite
    # print('accept the applet invite')
    def step08(gc, userB, appletObject):
        acceptAppletInvite(gc, userB, appletObject)

    tryExceptTester(step08, [gc, userB, appletObject], 'accept the applet invite')

    # invite someone that doesn't have an account yet
    # print('\033[0;37;40m invite someone that doesn\'t have an account yet')

    def step09(gc, user, appletObject):
        userCemail = 'randomuserc{}@test.com'.format(np.random.randint(1000000))
        inviteC = inviteUserToApplet(gc, user, appletObject,
                                        {'email': userCemail})
        appletUserTable = checkAppletUserTableForUser(gc, user,
                                                    appletObject,
                                                    {'email': userCemail})
        return userCemail, inviteC, appletUserTable

    userCemail, inviteC, appletUserTable = tryExceptTester(
        step09,
        [gc, user, appletObject],
        'invite someone that doesn\'t have an account yet',
        3
    )


    # create that person's account, check that they have an invite, and
    # accept the invite

    def step10(gc, userCemail):
        userC = testCreateUser(gc, userCemail)
        userCApplets = getAppletsUser(gc, userC, 0)
        return userC, userCApplets

    userC, userCApplets = tryExceptTester(
        step10,
        [gc, userCemail],
        'create that person\'s account, check that they have an invite',
        2
    )

    # check from perspective of admin and user, if the invite exists.
    # print('check from perspective of admin and user, if the invite exists.')
    def step11(gc, user, appletObject, userC):
        checkInvitesForUser(gc, user, appletObject, userC)
        checkForInvite(gc, userC, appletObject)

    tryExceptTester(
        step11,
        [gc, user, appletObject, userC],
        'check from perspective of admin and user, if the invite exists.'
    )

    # accept user c's invitation
    def step12(gc, userC, appletObject):
        acceptAppletInvite(gc, userC, appletObject)
        userCApplets = getAppletsUser(gc, userC, 1)
        return userCApplets

    userCApplets = tryExceptTester(
        step12,
        [gc, userC, appletObject],
        'accept user C\'s invitation'
    )

    # post a response
    # each user posts a response for a single item in each activity.
    def step13(gc, user, userB, userC, act1, act1Item, act2, act2Item):
        for u in [user, userB, userC]:
            for i in range(2):
                postResponse(gc, u, act1, act1Item, appletObject)
                time.sleep(1)
                postResponse(gc, u, act2, act2Item, appletObject)
                time.sleep(1)
            time.sleep(1)

    tryExceptTester(
        step13,
        [gc, user, userB, userC, act1, act1Item, act2, act2Item],
        'posted responses for all 3 users'
    )


    # get the last 7 days
    #print('get the last 7 days of data')

    def step14(gc, user, userB, userC, appletObject):
        last7user = getLast7Days(gc, user, appletObject)
        last7userB = getLast7Days(gc, userB, appletObject)
        last7userC = getLast7Days(gc, userC, appletObject)

        assert len(last7user['responses']) == 2, 'there should only be 2 responses'
        assert len(last7userB['responses']) == 2, 'there should only be 2 responses'
        assert len(last7userC['responses']) == 2, 'there should only be 2 responses'
        return last7user, last7userB, last7userC

    last7user, last7userB, last7userC = tryExceptTester(
        step14,
        [gc, user, userB, userC, appletObject],
        'get the last 7 days of data for each user',
        3
    )

    # as a manager, see the data. make sure you see emails
    def step15(gc, user, appletObject):
        appletData = getDataForApplet(gc, user, appletObject)
        assert '@' in appletData[0]['userId'], 'manager cannot see emails'
        return appletData

    appletData = tryExceptTester(
        step15,
        [gc, user, appletObject],
        'as a manager, see the data. make sure you see emails'
    )

    # add user as a reviewer
    # print('add user as a reviewer')
    def step16(gc, user, appletObject, userC):
        userCReviewer = makeAReviewer(gc, user, appletObject, userC)
        userCAcceptReviewer = acceptReviewerInvite(gc, userC, appletObject)
        return userCReviewer, userCAcceptReviewer

    userCReviewer, userCAcceptReviewer = tryExceptTester(
        step16,
        [gc, user, appletObject, userC],
        'add user as a reviewer',
        2
    )

    # as a reviewer, see the data and make sure you don't see emails
    # print('as a reviewer, see the data and make sure you don\'t see emails')
    def step17(gc, userC, appletObject):
        appletData = getDataForApplet(gc, userC, appletObject)
        assert '@' not in appletData[0]['userId'], 'reviewer can see emails'
        return appletData

    appletData = tryExceptTester(
        step17,
        [gc, userC, appletObject],
        'as a reviewer, see the data and make sure you don\'t see emails'
    )

    # make sure we don't see any data as a non-manager and non-reviewer
    # print('make sure we don\'t see any data as a non-manager and non-reviewer')
    def step18(gc, userB, appletObject):
        testPrivacyCheck(gc, userB, appletObject)

    tryExceptTester(
        step18,
        [gc, userB, appletObject],
        'make sure we don\'t see any data as a non-manager and non-reviewer'
    )

    # remove an applet without deleting data

    def step19(gc, userC, appletObject):
        removeApplet(gc, userC, appletObject)
        userCApplets = getAppletsUser(gc, userC, 0)
        appletData = getDataForApplet(gc, user, appletObject)

        userCData = list(filter(lambda x: x['userId'] == userC['email'],
                            appletData))
        assert len(userCData), "the user does not have data, but we expect it"

    tryExceptTester(
        step19,
        [gc, userC, appletObject],
        'remove an applet without deleting data'
    )

    # remove an applet and delete data

    def step20(gc, userB, appletObject):
        deleteApplet(gc, userB, appletObject)
        userBApplets = getAppletsUser(gc, userB, 0)
        appletData = getDataForApplet(gc, user, appletObject)

        userBData = list(filter(lambda x: x['userId'] == userB['email'],
                                appletData))
        assert len(userBData) == 0, "the user still has data, but they should not"

    tryExceptTester(
        step20,
        [gc, userB, appletObject],
        'remove an applet and delete data'
    )

    # deactivate an applet
    def step21(gc, user, appletObject):
        appletDeactivated = deactivateApplet(gc, user, appletObject)
        return appletDeactivated

    appletDeactivated = tryExceptTester(
        step21,
        [gc, user, appletObject],
        'deactivate an applet'
    )

    # remove all users
    def step22(gc, user, userB, userC):
        testDeleteUser(gc, user)
        testDeleteUser(gc, userB)
        testDeleteUser(gc, userC)

    tryExceptTester(
        step22,
        [gc, user, userB, userC],
        'remove all users'
    )

    return 1
