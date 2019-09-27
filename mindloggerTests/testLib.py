import girderformindlogger
import girder_client as gc
import pandas as pd
import numpy as np
import simplejson


def createGirder(host, port):
    """
    creates a girder client. this is the first argument to
    the subsequent functions below

    inputs
    ------
    host: string ('localhost' or 'dev.mindlogger.org')
    port: integer (443 if https, 8080 if local)
    """
    return gc.GirderClient(host=host, port=port)


def testCreateUser(girder, email=None):
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
    assert len(expandedApplet) == 1, "can't find the applet you want"

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
    girder.post('group/{}/invitation'.format(reviewerGroupId),
    {'email': userB['email']})


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
    girder.delete('applet/{}'.format(appletObject['_id']))
    assert getAppletsUser(user, 0), "user still has the applet that should be deleted."


def testDeleteUser(girder, user):

    authenticate(girder, user)

    deleteUser = girder.delete('user/{}'.format(user['_id']))

    assert deleteUser['message'] == 'Deleted user {}.'.format(user['login']), "{} does not equal {}".format(deleteUser['message'],
                                                             'Deleted user {}'.format(user['login']))
    
    return 1