from bson.objectid import ObjectId
import csv
import os
from pymongo import DESCENDING, ASCENDING
from datetime import datetime, timedelta

from girderformindlogger.models.account_profile import AccountProfile
from girderformindlogger.models.profile import Profile as ProfileModel
from girderformindlogger.models.user import User as UserModel
from girderformindlogger.models.applet_library import AppletLibrary as AppletLibraryModel
from girderformindlogger.models.applet_basket import AppletBasket as AppletBasketModel
from girderformindlogger.models.folder import Folder as FolderModel
from girderformindlogger.models.token import Token as TokenModel
from girderformindlogger.models.item import Item as ItemModel

accountsBlackList = [ObjectId("5f0c9582773c79301db70b35"), ObjectId("5f0dd1943477de8b4a528d8c"), ObjectId("5f0dd3b23477de8b4a528d9a"), ObjectId("5fcfdb08c47c585b7c7330f0"), ObjectId("60ba3c805fa6a85768b62717"), ObjectId("60cc58985fa6a85768b648d5"), ObjectId("60efe7a589c6d5038b96a759"), ObjectId("60f149da25e2114a3ed9b985"), ObjectId("6149ab8cefa8adf9de386e00"), ObjectId("614c302befa8adf9de386fe5"), ObjectId("61532a2745f52e102d006fad"), ObjectId("61532a4f45f52e102d006faf"), ObjectId("615485ea5b70d65efedaf2ef"), ObjectId("615728055b70d65efedaf8c0"), ObjectId("6177a141572692219407ab0b"), ObjectId("617a61f5a463200ebc8506e2"), ObjectId("617a65d2c8869124a83d3e0e"), ObjectId("619f8be48a45f2bc70b17549"), ObjectId("619f8f658a45f2bc70b1762b"), ObjectId("61c2e4265f996a603975d5d7"), ObjectId("61c2e4685f996a603975d5d9"), ObjectId("61c2e4be5f996a603975d5db"), ObjectId("61c2e53e5f996a603975d5dd"), ObjectId("62336a9b5197b946898249dd"), ObjectId("624462285197b9338bdb09f8"), ObjectId("627a357d0a62aa4796225eb9"), ObjectId("627a3b630a62aa4796225fd0"), ObjectId("6284fb390a62aa479622805e"), ObjectId("62c6934aacd35a1054f0e9b4"), ObjectId("62d91168acd35a44dd03c10c"), ObjectId("62d911a5acd35a44dd03c10e"), ObjectId("62de6464acd35a44dd03cee1"), ObjectId("62de70bdacd35a4bf1195797"), ObjectId("62f63155acd35a39e99b68a0"), ObjectId("62fb8124924264104c28ef3a"), ObjectId("62fb8141924264104c28ef3f"), ObjectId("6307844d924264279508774a"), ObjectId("6315af73b7ee970ffa90010f"), ObjectId("6315ec9db7ee970ffa900116"), ObjectId("6315f706b7ee970ffa900123"), ObjectId("63170911b7ee970ffa90029e"), ObjectId("63172f8eb7ee970ffa900302"), ObjectId("63187250b7ee970ffa9004c2"), ObjectId("6319cd49b7ee970ffa9008ac"), ObjectId("631efe87b7ee970ffa900dd5"), ObjectId("631f7709b7ee970ffa900fa7"), ObjectId("632cb6f3b7ee9765ba542d6c"), ObjectId("633eb731b7ee9765ba5444e2"), ObjectId("633fc37eb7ee9765ba5445c5"), ObjectId("6345966d5cb7004311218cce"), ObjectId("6346619d5cb7004311218d29"), ObjectId("6347daf95cb7004311219d67"), ObjectId("63484d245cb700431121a3c1"), ObjectId("634d51465cb700431121b4e5"), ObjectId("634fcef55cb700431121d0cb"), ObjectId("635547735cb700431121e9a8"), ObjectId("635fe0065cb700431121f9d9"), ObjectId("6374a3f752ea0234e1f4fb19"), ObjectId("6374a68152ea0234e1f4fb1d"), ObjectId("637c8fdd52ea0234e1f5097e"), ObjectId("63c6c3f7b71996780cdf0634"), ObjectId("63c81225b71996780cdf11b7"), ObjectId("63dccc78b7199623ac4fff5c"), ObjectId("63e39f87601cdc0fee1eca84"), ObjectId("63e52298601cdc0fee1edfdd"), ObjectId("63f5edf1601cdc5212d5a4e9"), ObjectId("6400bba9601cdc5212d5e9d8"), ObjectId("640ef74d83718f0fbf0ade58"), ObjectId("6421902b83718f0fbf0b3891"), ObjectId("642d233f83718f0fbf0b7295"), ObjectId("642d564c83718f0fbf0b74dd"), ObjectId("6433e98d25d51a0f8edad7e5"), ObjectId("6433e9d725d51a0f8edad7eb"), ObjectId("64351cdc25d51a0f8edadb20")]

def accounts_sheet():
    rows = []
    ids = get_admins_groupped_by_user_id()
    accounts = AccountProfile().find(query={'$expr': {'$eq': ['$accountId', '$_id']}, 'userId': {'$in': ids}, '_id': {'$nin': accountsBlackList}})
    print('accounts: ', accounts.count())
    for idx, account in enumerate(accounts, start=1):
        row = accounts_sheet_row(account, ids)
        if not row:
            continue
        rows.append(row)
        if idx % 1000 == 0: print(idx)
        elif idx % 100 == 0: print('.', end='')

    to_csv(rows, os.getcwd() + '/accounts.csv')

def users_sheet():
    rows = []
    ids = get_admins_groupped_by_user_id()
    users = list(UserModel().find(query={}, fields={"_id": 1}))
    print('users: ', len(users))
    for idx, user in enumerate(users, start=1):
        row = users_sheet_row(user, ids)
        if not row:
            continue
        rows.append(row)
        if idx % 1000 == 0: print(idx)
        elif idx % 100 == 0: print('.', end='')

    to_csv(rows, os.getcwd() + '/users.csv')


def applets_sheet():
    rows = []
    applets = FolderModel().find(query={'meta.applet': {'$exists': True}, 'meta.applet.deleted': {'$ne': True}, 'accountId': {'$nin': accountsBlackList}}, fields={"_id": 1, "name": 1, "meta": 1, "created": 1, "creatorId": 1})
    print('applets: ', applets.count())
    for idx, applet in enumerate(applets, start=1):
        rows.append(applets_sheet_row(applet))
        if idx % 1000 == 0: print(idx)
        elif idx % 100 == 0: print('.', end='')

    to_csv(rows, os.getcwd() + '/applets.csv')

def library_sheet():
    applets = FolderModel().find(query={'meta.applet': {'$exists': True}, 'meta.applet.deleted': {'$ne': True}, 'accountId': {'$nin': accountsBlackList}}, fields={"_id": 1})
    appletsIds = [applet['_id'] for applet in applets]
    libraryApplets = AppletLibraryModel().find(query={'appletId': {'$in': appletsIds}}, fields={"_id": 1, "name": 1, "created": 1, "appletId": 1, "activities": 1})
    rows = []
    print('applets: ', libraryApplets.count())
    for idx, libraryApplet in enumerate(libraryApplets, start=1):
        rows.append(library_sheet_row(libraryApplet))
        if idx % 1000 == 0: print(idx)
        elif idx % 100 == 0: print('.', end='')

    to_csv(rows, os.getcwd() + '/library.csv')


def accounts_sheet_row(main_account, admins_ids):
    accounts = AccountProfile().find(query={'accountId': main_account['_id']})
    usersAmount = 0
    loggedLast6 = 0
    loggedLast12 = 0
    emails = []
    for account in accounts:
        if not ('manager' in account['applets'] or 'owner' in account['applets'] or 'editor' in account['applets'] or account['_id'] == account['accountId']):
            continue
        usersAmount = usersAmount + 1
        user = UserModel().load(account['userId'], force=True)
        if user_email_valid(user):
            emails.append(user['email'])
        tokens = TokenModel().find(query={'accountId': main_account['_id'], 'userId': account['userId']}, limit=1, fields=['created'], sort=[("created", DESCENDING)])
        if tokens.count() > 0:
            diff_months = diff_month(datetime.now(), tokens[0]['created'])
            if diff_months <= 6:
                loggedLast6 = loggedLast6 + 1
            if diff_months <= 12:
                loggedLast12 = loggedLast12 + 1

    owner = UserModel().load(main_account['userId'], force=True)
    if not owner and len(emails) == 0:
        return None

    allApplets = get_applets_in_profile(main_account)
    appletsAmount = len(allApplets)
    responsesAmount = 0
    appletsLast6 = 0
    appletsLast12 = 0
    appletsLast24 = 0
    responsesWithinAccount = 0
    lastResponseDateWithinAccount = None
    for _applet_id in allApplets:
        responses = ItemModel().find(query={'meta.applet.@id': _applet_id}, limit=1, fields=['created'], sort=[("created", DESCENDING)])
        responsesAmount = responsesAmount + responses.count()
        if responses.count() > 0:
            diff_months = diff_month(datetime.now(), responses[0]['created'])
            if diff_months <= 6:
                appletsLast6 = appletsLast6 + 1
            if diff_months <= 12:
                appletsLast12 = appletsLast12 + 1
            if diff_months <= 24:
                appletsLast24 = appletsLast24 + 1

            responsesWithinAccount = responsesWithinAccount + responses.count()
            if lastResponseDateWithinAccount is None or lastResponseDateWithinAccount < responses[0]['created']:
                lastResponseDateWithinAccount = responses[0]['created']

    diff_weeks = diff_week(datetime.now(), owner['created'])
    if diff_weeks < 1:
        diff_weeks = 1
    responsesPerWeekAvg = responsesWithinAccount/diff_weeks

    respondentsProfiles = ProfileModel().find(query={'accountId': main_account['_id'], 'profile': True, '$and': [ {'roles': {'$in': ["user"]}}, {'roles': {'$size': 1}} ], '_id': {'$nin': admins_ids}}, fields=['_id', 'userId'])
    respondents = []
    for profile in respondentsProfiles:
        respondents.append(profile['userId'])
    respondents = list(set(respondents))
    respondentsAmount = len(respondents)


    return {
        'id': main_account['_id'],
        # 'owner email': owner['email'] if user_email_valid(owner) else '-',
        # 'admin emails': ', '.join(emails) if len(emails) > 0 else '-',
        'account': escape_for_excel(main_account['accountName']),
        'admins amount': usersAmount,
        'admins logged in within 6 months': loggedLast6,
        'admins logged in within 12 months': loggedLast12,
        'responses amount': responsesAmount,
        'respondents amount': respondentsAmount,
        'applets amount': appletsAmount,
        'applets responded within 6 months': appletsLast6,
        'applets responded within 12 months': appletsLast12,
        'applets responded within 24 months': appletsLast24,
        'responses per week avg': "{:.2f}".format(responsesPerWeekAvg),
        'last response date': lastResponseDateWithinAccount.strftime("%Y-%m-%d") if lastResponseDateWithinAccount is not None else '-',
    }


def users_sheet_row(user, admins_ids):
    user = UserModel().load(user['_id'], force=True)
    is_admin = user['_id'] in admins_ids

    responses_sizes = list(ItemModel().aggregate([
        {
            "$match": {
                "creatorId": user['_id'],
                "meta.dataSource": {"$exists": True, "$type": "string"},
                "meta.events": {"$exists": True, "$type": "string"},
            }
        },
        {
            "$project": {
                "dataSource_size_bytes": {"$strLenCP": "$meta.dataSource"},
                "events_size_bytes": {"$strLenCP": "$meta.events"},
            }
        }
    ]))
    responses_size_bytes = 0
    for a in responses_sizes:
        responses_size_bytes = responses_size_bytes + a['dataSource_size_bytes'] + a['events_size_bytes']

    accounts = list(AccountProfile().find(query={'userId': user['_id']}))
    account_names = ", ".join([acc['accountName'] for acc in accounts])

    return {
        'id': user['_id'],
        'admin': 'yes' if is_admin else 'no',
        'displayName': user['displayName'],
        'firstName': user['firstName'],
        'lastName': user['lastName'],
        'created': user['created'],
        'account_names': account_names,
        'responses size in bytes': responses_size_bytes,
    }


def user_email_valid(user):
    return user and not user['email_encrypted'] and user['email']


def applets_sheet_row(applet):
    responses = ItemModel().find(query={'meta.applet.@id': applet['_id']}, fields=['created'], sort=[("created", DESCENDING)])
    lastResponseDate = responses[0]['created'].strftime("%Y-%m-%d") if responses.count() > 0 else None
    responsesAmount = responses.count()


    admins = []
    adminProfiles = ProfileModel().find(query={'appletId': applet['_id'], 'profile': True, 'roles': {'$in': ["editor"]}}, fields=['_id', 'userId'])
    for profile in adminProfiles:
        admins.append(profile['userId'])
    admins = list(set(admins))
    adminsAmount = len(admins)

    respondentsProfiles = ProfileModel().find(query={'appletId': applet['_id'], 'profile': True, '$and': [ {'roles': {'$in': ["user"]}}, {'roles': {'$size': 1}} ], '_id': {'$nin': admins}}, fields=['_id', 'userId'])
    respondents = []
    for profile in respondentsProfiles:
        respondents.append(profile['userId'])
    respondents = list(set(respondents))
    respondentsAmount = len(respondents)

    protocolId = ObjectId(applet['meta']['protocol'].get('_id').split('/').pop())
    activities = FolderModel().find(query={'meta.protocolId': protocolId, '$or': [ {'meta.activity.reprolib:terms/baseAppletId.0.@id': {'$exists': True}}, {'meta.activity.reprolib:terms/baseActivityId.0.@id': {'$exists': True}} ]}, fields=['_id'])

    try:
        owner = UserModel().load(applet['creatorId'], force=True)
    except:
        owner = None

    return {
        'id': str(applet['_id']),
        # 'owner email': owner['email'] if user_email_valid(owner) else '-',
        'name': escape_for_excel(applet['name']),
        'creation date': applet['created'].strftime("%Y-%m-%d"),
        'amount of admins': adminsAmount,
        'amount of respondents': respondentsAmount,
        'amount of responses': responsesAmount,
        'last response date': lastResponseDate,
        'imported from the library': activities.count() > 0,
    }


def library_sheet_row(libraryApplet):
    appletId = str(libraryApplet['appletId'])
    activitiesIds = list(map(lambda x: str(x['activityId']), libraryApplet['activities']))
    activities = FolderModel().find(query={'meta.protocolId': {'$exists': True}, '$or': [  {'meta.activity.reprolib:terms/baseAppletId.0.@id': appletId}, {'meta.activity.reprolib:terms/baseActivityId.0.@id': {'$in': activitiesIds}}  ]}, fields=['_id', 'name', 'created', 'meta'], sort=[("created", DESCENDING)])
    activities = list(activities)
    protocolsIds = list(map(lambda x: str(x['meta']['protocolId']), activities))
    protocolsIds = list(set(protocolsIds))

    applet = FolderModel().load(ObjectId(libraryApplet['appletId']), force=True)
    creator = UserModel().load(applet['creatorId'], force=True)

    appletsInBasket = AppletBasketModel().find(query={'appletId': ObjectId(libraryApplet['appletId'])})

    return {
        'id': str(libraryApplet['_id']),
        'name': escape_for_excel(libraryApplet['name']),
        'creator': creator['email'],
        'last imported': activities[0]['created'].strftime("%Y-%m-%d") if len(activities) > 0 else None,
        'amount of imports': len(protocolsIds),
        'amount in basket': appletsInBasket.count(),
    }


def escape_for_excel(string):
    if string.startswith('+'):
        return "'"+string
    return string


def get_applets_in_profile(profile):
    array = profile['applets'].values()
    ids = list({x for l in array for x in l})
    # filter out not deleted
    applets = FolderModel().find(query={'_id': {'$in': ids}, 'meta.applet.deleted': {'$ne': True}}, fields={"_id": 1})
    ids = [applet['_id'] for applet in applets]
    return ids


def diff_month(d1, d2):
    return (d1.year - d2.year) * 12 + d1.month - d2.month

def diff_week(d1, d2):
    monday1 = (d1 - timedelta(days=d1.weekday()))
    monday2 = (d2 - timedelta(days=d2.weekday()))
    return (monday1 - monday2).days / 7


def to_csv(to_csv, path):
    keys = to_csv[0].keys()
    with open(path, 'w', newline='') as output_file:
        dict_writer = csv.DictWriter(output_file, keys)
        dict_writer.writeheader()
        dict_writer.writerows(to_csv)


def growth_line(year):
    before = datetime(year+1, 1, 1, 0, 0, 0)

    # 'meta.applet.deleted': {'$ne': True}
    applets = FolderModel().find(query={'created': {'$lt': before}, 'meta.applet': {'$exists': True}, 'accountId': {'$nin': accountsBlackList}}, fields={"_id": 1})
    blAppletsIds = get_blacklisted_applets_ids()

    appletsAmount = applets.count()

    admins = []
    adminProfiles = ProfileModel().find(query={'created': {'$lt': before}, 'profile': True, 'roles': {'$in': ["editor"]}, 'appletId': {'$nin': blAppletsIds}}, fields=['_id', 'userId'])
    for profile in adminProfiles:
        admins.append(profile['userId'])
    admins = list(set(admins))
    adminsAmount = len(admins)

    respondentsProfiles = ProfileModel().find(query={'created': {'$lt': before}, 'profile': True, '$and': [ {'roles': {'$in': ["user"]}, 'appletId': {'$nin': blAppletsIds}}, {'roles': {'$size': 1}} ], '_id': {'$nin': admins}}, fields=['_id', 'userId'])
    respondents = []
    for profile in respondentsProfiles:
        respondents.append(profile['userId'])
    respondents = list(set(respondents))
    respondentsAmount = len(respondents)

    print('year', year, 'Administrators', adminsAmount, 'Respondents', respondentsAmount, 'Applets', appletsAmount)


def cohort_sheet():
    rows = []
    ids = get_admins_groupped_by_user_id()
    now = datetime.utcnow()
    cohortDate = UserModel().find(query={'_id': {'$in': ids}}, limit=1, fields=['created'], sort=[("created", ASCENDING)])[0]['created']
    while now > cohortDate:
        # endDate = cohortDate + timedelta(days=7)
        endDate = (cohortDate.replace(day=1, hour=0, minute=0, second=0, microsecond=0) + timedelta(days=32)).replace(day=1)

        cohortUsers = UserModel().find(query={'_id': {'$in': ids}, 'created': {'$gte': cohortDate, '$lt': endDate}}, fields=['_id'])
        cohortUsersIds = list(map(lambda x: x['_id'], cohortUsers))
        print(cohortDate.strftime('%Y-%m-%d'), len(cohortUsersIds), 'users')
        rows.append(cohort_row(cohortUsersIds, cohortDate, endDate, now))
        cohortDate = endDate

    # rows.reverse()
    to_csv(rows, os.getcwd() + '/cohort.csv')


def last_day_of_month(any_day):
    # The day 28 exists in every month. 4 days later, it's always next month
    next_month = any_day.replace(day=28) + timedelta(days=4)
    # subtracting the number of the current day brings us back one month
    return next_month - timedelta(days=next_month.day)


def cohort_row(cohortUsersIds, cohortDate, cohortEndDate, now):
    allUsersCount = len(cohortUsersIds)
    row = {
        # 'COHORT': cohortDate.strftime('%Y-%m-%d')+' - '+cohortEndDate.strftime('%Y-%m-%d'),
        'COHORT': cohortDate.strftime('%B / %Y'),
        'NEW ADMINS': allUsersCount,
    }
    periods = [1, 3, 6, 12, 18, 24, 36, 48]
    periodsDelta = {1: 1, 3: 2, 6: 3, 12: 6, 18: 6, 24: 6, 36: 12, 48: 12}
    periodStart = cohortDate
    for p in periods:
        if periodStart >= now:
            row[str(p) + 'm'] = ''
            break
        periodEnd = periodStart + timedelta(days=periodsDelta[p]*30)
        if periodEnd >= now:
            periodEnd = now
        activeUsers = get_active_users_between(cohortUsersIds, periodStart, periodEnd)
        print(str(p)+'m', periodStart.strftime('%Y-%m-%d'), periodEnd.strftime('%Y-%m-%d'), len(activeUsers), 'users')
        row[str(p)+'m'] = len(activeUsers) / allUsersCount if allUsersCount > 0 else 0
        periodStart = periodEnd

    return row


def get_active_users_between(cohortUsersIds, periodStart, periodEnd):
    activeUsersIds = []

    tokens = list(TokenModel().find(query={'userId': {'$in': cohortUsersIds}, 'created': {'$gte': periodStart, '$lt': periodEnd}}, fields=['userId']))
    for token in tokens:
        activeUsersIds.append(token['userId'])

    applets = list(FolderModel().find(query={'creatorId': {'$in': cohortUsersIds}, 'created': {'$gte': periodStart, '$lt': periodEnd}}, fields=['creatorId']))
    for applet in applets:
        activeUsersIds.append(applet['creatorId'])

    items = list(ItemModel().find(query={'creatorId': {'$in': cohortUsersIds}, 'created': {'$gte': periodStart, '$lt': periodEnd}}, fields=['creatorId']))
    for item in items:
        activeUsersIds.append(item['creatorId'])

    activeUsersIds = list(set(activeUsersIds))

    return activeUsersIds


def get_blacklisted_applets_ids():
    applets = FolderModel().find(query={'meta.applet': {'$exists': True}, 'accountId': {'$in': accountsBlackList}}, fields={"_id": 1})
    return [applet['_id'] for applet in applets]


def get_admins_groupped_by_user_id():
    blAppletsIds = get_blacklisted_applets_ids()
    admins = []
    adminProfiles = ProfileModel().find(query={'profile': True, 'roles': {'$in': ["editor"]}, 'appletId': {'$nin': blAppletsIds}}, fields=['_id', 'userId'])
    for profile in adminProfiles:
        if profile and 'userId' in profile:
            admins.append(profile['userId'])
    admins = list(set(admins))
    return admins


if __name__ == '__main__':
    # accounts_sheet()
    # applets_sheet()
    # library_sheet()
    # growth_line(2020)
    # growth_line(2021)
    # growth_line(2022)
    # growth_line(2023)
    # cohort_sheet()
    users_sheet()
