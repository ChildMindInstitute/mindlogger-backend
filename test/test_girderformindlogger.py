# -*- coding: utf-8 -*-
import pytest
import girderformindlogger
import girder_client as gc
import pandas as pd
import numpy as np
from bson import json_util

girder = gc.GirderClient(host="localhost", port=8080)

def testCreateUser(email=None):
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

def authenticate(user):
    girder.authenticate(username=user['login'], password='password')

userA = testCreateUser()
userB = testCreateUser()

def getAppletsNewUser(new_user):
    girder.authenticate(username=new_user['login'], password='password')
    appletList = girder.get('user/applets')
    assert len(appletList) == 0, 'a new user should have an empty list of applets. we get {}'.format(appletList)
    return 1

getAppletsNewUser(userA)

def getAppletById(user, ar):
    girder.authenticate(username=user['login'], password='password')
    res = girder.get('applet/{}'.format(ar['_id']))
    assert res['applet']['_id'].split('applet/')[1] == ar['_id'], 'applet ids are not the same'
    return 1

activitySetUrl = 'https://raw.githubusercontent.com/ReproNim/schema-standardization/master/activity-sets/ema-hbn/ema-hbn_schema'

act1 = 'https://raw.githubusercontent.com/ReproNim/schema-standardization/master/activities/EmaHBNEvening/ema_evening_schema'
act2 = 'https://raw.githubusercontent.com/ReproNim/schema-standardization/master/activities/EmaHBNMorning/ema_morning_schema'

act1Item = 'https://raw.githubusercontent.com/ReproNim/schema-standardization/master/activities/EmaHBNEvening/items/good_bad_day'
act2Item = 'https://raw.githubusercontent.com/ReproNim/schema-standardization/master/activities/EmaHBNMorning/items/sleeping_aids'


nestedActivitySet = 'https://raw.githubusercontent.com/ReproNim/schema-standardization/master/activity-sets/pediatric-screener/pediatric-screener_schema'

nact1 = 'https://raw.githubusercontent.com/ReproNim/schema-standardization/master/activities/PediatricScreener-Parent/pediatric_screener_parent_schema'
nact2 = 'https://raw.githubusercontent.com/ReproNim/schema-standardization/master/activities/PediatricScreener-SelfReport/pediatric_screener_selfreport_schema'

nact1Item = 'https://raw.githubusercontent.com/ReproNim/schema-standardization/master/activities/PediatricScreener-Parent/items/fidgety'
nact2Item = 'https://raw.githubusercontent.com/ReproNim/schema-standardization/master/activities/PediatricScreener-SelfReport/items/having_less_fun'


def addApplet(new_user, activitySetUrl):
    girder.authenticate(username=new_user['login'], password='password')

    # TODO: create an activity-set that JUST for testing.
    # make sure it has all the weird qualities that can break


    # for now, lets do the mindlogger demo
    activitySetUrl = activitySetUrl
    randomAS = np.random.randint(1000000)
    ar = girder.post('applet', parameters=dict(activitySetUrl = activitySetUrl, name='testActivitySet{}'.format(randomAS)))

    assert ar['_id'], 'there is no ID!'
    assert ar['meta']['activitySet']['url'] == activitySetUrl, 'the URLS do not match! {} {}'.format(ar['meta']['activitySet']['url'], activitySetUrl)

    assert getAppletById(new_user, ar) == 1, 'something wrong with getAppletById'
    return ar

userA_applets = addApplet(userA, nestedActivitySet)

def getAppletsUser(user, n=1):
    girder.authenticate(username=user['login'], password='password')
    appletList = girder.get('user/applets')
    assert len(appletList) == n, 'a new user should have {} applets. we get {}'.format(n, len(appletList))
    return 1

getAppletsUser(userA, 1)

# TODO: continue
