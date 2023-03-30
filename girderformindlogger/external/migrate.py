from girderformindlogger.models.account_profile import AccountProfile
from girderformindlogger.models.profile import Profile
from girderformindlogger.models.user import User as UserModel
from girderformindlogger.models.applet_library import AppletLibrary as AppletLibraryModel
from girderformindlogger.models.applet_basket import AppletBasket as AppletBasketModel
from girderformindlogger.models.invitation import Invitation as InvitationModel
from girderformindlogger.models.note import Note as NoteModel
from girderformindlogger.models.notification import Notification as NotificationModel
from girderformindlogger.models.events import Events as EventsModel
from girderformindlogger.models.ID_code import IDCode as IDCodeModel
from girderformindlogger.models.api_key import ApiKey as ApiKeyModel
from girderformindlogger.models.response_alerts import ResponseAlerts as ResponseAlertsModel
from girderformindlogger.models.setting import Setting as SettingModel
from girderformindlogger.models.shield import Shield as ShieldModel
from girderformindlogger.models.collection import Collection as CollectionModel
from girderformindlogger.models.cache import Cache as CacheModel
from girderformindlogger.models.group import Group as GroupModel
from girderformindlogger.models.folder import Folder as FolderModel
from girderformindlogger.models.response_tokens import ResponseTokens as ResponseTokensModel
from girderformindlogger.models.item import Item as ItemModel
from girderformindlogger.utility import jsonld_expander

from bson import json_util
from bson.objectid import ObjectId
import traceback

source_db_uri = 'mongodb://localhost:27017/source'
target_db_uri = 'mongodb://localhost:27017/target'

migrated = {}

def start(email, account_name, applet_id = None):
    global migrated

    migrate_settings()

    main_user = find_user(email)
    main_ap = find_main_account_profile(main_user['_id'], account_name)


    # print applets in account
    # for _applet_id in get_applets_in_profile(main_ap):
    #     if applet_id is not None and _applet_id != applet_id:
    #         continue
    #     applet = FolderModel().findOne(query={'_id': _applet_id})
    #     print('applet', applet['_id'], applet['name'])
    #     for activity in find_activities_by_applet(applet):
    #         print('activity', activity['_id'], activity['name'])
    #         for item in find_items(activity['_id']):
    #             print('item', item['_id'], item['name'])
    # exit(0)


    migrate_collection_types()

    # migrate main user
    if applet_id is not None:
        remove_not_allowed_applets_from_ap(main_ap, applet_id)
    migrate(AccountProfile(), main_ap)
    migrate(UserModel(), main_user)
    migrate_responses(main_user['_id'], applet_id)
    migrate_api_keys(main_user['_id'])
    migrate_notifications(main_user['_id'])
    migrate_shields(main_user['_id'])

    # migrate other users in main account
    for account in find_other_users_accounts_profiles(main_ap['_id']):
        if applet_id is not None:
            remove_not_allowed_applets_from_ap(account, applet_id)
        migrate(AccountProfile(), account)
        user = UserModel().load(account['userId'], force=True)
        migrate(UserModel(), user)
        migrate_responses(account['userId'], applet_id)
        migrate_api_keys(account['userId'])
        migrate_notifications(account['userId'])
        migrate_shields(account['userId'])

    # migrate applets
    for _applet_id in get_applets_in_profile(main_ap):
        if applet_id is not None and _applet_id != applet_id:
            continue
        migrated = {}
        migrate_applets(_applet_id)
        migrate_applet_basket(applet_id)
        migrate_invitations(applet_id)
        migrate_notes(applet_id)
        migrate_response_alerts(applet_id)
        migrate_events(applet_id)
        for profile in get_applet_profiles(_applet_id, main_ap['_id']):
            migrate(Profile(), profile)
            migrate_id_codes(profile['_id'])
    migrate_applet_library(main_ap['accountId'], applet_id)

    migrated = {}
    migrate_response_folders_recursively(main_user['_id'], 'user')
    for account in find_other_users_accounts_profiles(main_ap['_id']):
        migrate_response_folders_recursively(account['userId'], 'user')

def start_responses_migration(email, account_name):
    global migrated

    migrate_settings()

    main_user = find_user(email)
    main_ap = find_main_account_profile(main_user['_id'], account_name)

    migrate_responses(main_user['_id'], None)
    # migrate other users in main account
    for account in find_other_users_accounts_profiles(main_ap['_id']):
        migrate_responses(account['userId'], None)


def migrate_api_keys(userId):
    for key in ApiKeyModel().find(query={'userId': userId}):
        migrate(ApiKeyModel(), key)


def migrate_applet_basket(appletId):
    for item in AppletBasketModel().find(query={'appletId': appletId}):
        migrate(AppletBasketModel(), item)


def migrate_invitations(appletId):
    for item in InvitationModel().find(query={'appletId': appletId}):
        migrate(InvitationModel(), item)


def migrate_notes(appletId):
    for item in NoteModel().find(query={'appletId': appletId}):
        migrate(NoteModel(), item)


def migrate_response_alerts(appletId):
    for item in ResponseAlertsModel().find(query={'appletId': appletId}):
        migrate(ResponseAlertsModel(), item)


def migrate_notifications(userId):
    for item in NotificationModel().find(query={'userId': userId}):
        migrate(NotificationModel(), item)


def migrate_shields(userId):
    for item in ShieldModel().find(query={'user': userId}):
        migrate(ShieldModel(), item)


def migrate_events(appletId):
    for item in EventsModel().find(query={'applet_id': appletId}):
        migrate(EventsModel(), item)


def migrate_id_codes(profileId):
    for item in IDCodeModel().find(query={'profileId': profileId}):
        migrate(IDCodeModel(), item)


def migrate_settings():
    for item in SettingModel().find(query={}):
        migrate(SettingModel(), item)


def migrate_responses(userId, appletId):
    query = {'creatorId': userId}
    if appletId is not None:
        query['meta.applet.@id'] = appletId
    responses = ItemModel().find(query=query)
    for response in responses:
        migrate(ItemModel(), response)

    for rt in ResponseTokensModel().find(query={'userId': userId}):
        migrate(ResponseTokensModel(), rt)



def migrate_response_folders_recursively(id, parentCollection):
    for folderChild in FolderModel().find(query={'parentId': ObjectId(id), 'parentCollection': parentCollection}):
        migrate(FolderModel(), folderChild)
        # if 'parentId' in folderChild:
        migrate_response_folders_recursively(folderChild['_id'], 'folder')

        # if ObjectId.is_valid(folderChild['name']): # appletProfile.id
        #     for item in ItemModel().find(query={'folderId': folderChild['_id']}):
        #         migrate(ItemModel(), item)


def get_applet_profiles(applet_id, account_id):
    return Profile().find(query={'appletId': applet_id, 'accountId': account_id})


def migrate_collection_types():
    for type in CollectionModel().find():
        migrate(CollectionModel(), type)


def remove_not_allowed_applets_from_ap(account_profile, allowed_applet_id):
    for role in account_profile['applets']:
        account_profile['applets'][role] = list(
            filter(lambda id: id == allowed_applet_id, account_profile['applets'][role]))


def migrate_applets(appletId):
    applet = FolderModel().findOne(query={'_id': appletId})
    migrateFolder(FolderModel(),applet)

    protocol = get_protocol(applet)
    migrateFolder(FolderModel(),protocol)

    for group in GroupModel().find(query={'name': {'$regex': str(appletId)}}):
        migrate(GroupModel(), group)

    for af in find_flows_by_applet(applet):
        migrateFolder(FolderModel(),af)

    for activity in find_activities_by_applet(applet):
        migrateFolder(FolderModel(),activity)
        for h_activity in find_h_activities(activity['_id']):
            migrateFolder(FolderModel(),h_activity)
        for item in find_items(activity['_id']):
            migrateFolder(ItemModel(), item)
        for h_item in find_h_items(activity['_id']):
            migrateFolder(FolderModel(),h_item)


def migrate_item_cache(item):
    if 'content' in item:
        content = json_util.loads(item['content'])
        if 'protocol' in content and 'activities' in content['protocol']:
            activities = content['protocol'].get('activities', {})
            for activityIRI in dict.keys(activities):
                activity = activities[activityIRI]
                if type(activity) == str:
                    cacheId = activities[activityIRI].split('/')[-1]
                    cache = CacheModel().load(cacheId)
                    migrate(CacheModel(), cache)

def get_protocol(applet):
    protocolId = ObjectId(applet['meta']['protocol'].get('_id').split('/').pop())
    return FolderModel().findOne(query={'_id': protocolId})


def find_items(activityId):
    return ItemModel().find(query={'meta.activityId': activityId, 'meta.screen': {'$exists': True}})


def find_h_items(activityId):
    return FolderModel().find(query={'name': {'$regex': str(activityId)}})


def find_h_activities(activityId):
    return FolderModel().find(query={'meta.originalId': activityId, 'meta.activity': {'$exists': True}})


def find_activities_by_applet(applet):
    ids = []

    protocolId = applet['meta']['protocol'].get('_id').split('/').pop()
    docCollection = jsonld_expander.getModelCollection('activity')
    activities = FolderModel().find({'meta.protocolId': ObjectId(protocolId), 'parentId': docCollection['_id']}, fields={"_id": 1})
    for activity in activities:
        ids.append(activity['_id'])

    if 'protocol' in applet['meta'] and 'activities' in applet['meta']['protocol']:
        for id in applet['meta']['protocol']['activities']:
            ids.append(id)

    profiles = Profile().find(query={'appletId': applet['_id'], 'completed_activities': {'$exists': True}})
    for profile in profiles:
        for ca in profile['completed_activities']:
            ids.append(ca['activity_id'])

    ids = list(set(ids))
    return FolderModel().find({'_id': {'$in': ids}, 'parentId': docCollection['_id']})


def find_flows_by_applet(applet):
    flowIds = []

    protocolId = applet['meta']['protocol'].get('_id').split('/').pop()
    docCollection = jsonld_expander.getModelCollection('activityFlow')
    activityFlows = FolderModel().find({'meta.protocolId': ObjectId(protocolId), 'parentId': docCollection['_id']}, fields={"_id": 1})
    for af in activityFlows:
        flowIds.append(af['_id'])

    if 'protocol' in applet['meta'] and 'activityFlows' in applet['meta']['protocol']:
        for flowId in applet['meta']['protocol']['activityFlows']:
            flowIds.append(flowId)

    profiles = Profile().find(query={'appletId': applet['_id'], 'activity_flows': {'$exists': True}})
    for profile in profiles:
        for af in profile['activity_flows']:
            flowIds.append(af['activity_flow_id'])

    flowIds = list(set(flowIds))
    return FolderModel().find({'_id': {'$in': flowIds}, 'parentId': docCollection['_id']})

def migrate_applet_library(account_id, applet_id = None):
    query = {'accountId': account_id}
    if applet_id is not None:
        query['appletId'] = applet_id
    items = AppletLibraryModel().find(query=query)
    for item in items:
        migrate(AppletLibraryModel(), item)


def get_applets_in_profile(profile):
    array = profile['applets'].values()
    return list({x for l in array for x in l})


def find_user(email):
    user = UserModel().findOne({'email': UserModel().hash(email), 'email_encrypted': True})
    if user is None:
        user = UserModel().findOne({'email': email, 'email_encrypted': {'$ne': True}})
    print('user', user['email'], user['_id'])
    return user


def find_main_account_profile(user_id, account_name):
    user_ap = AccountProfile().findOne(query={'userId': user_id, 'accountName': account_name})
    if user_ap is None:
        raise Exception('Unable to find user account %s' % account_name)
    main_ap = AccountProfile().findOne(query={'_id': user_ap['accountId'], 'accountName': account_name})
    if main_ap is None:
        raise Exception('Unable to find main account %s' % account_name)
    return main_ap


def find_other_users_accounts_profiles(account_id):
    return AccountProfile().find(query={'accountId': account_id, '_id': {'$ne': account_id } })


def get_stack():
    stack = traceback.format_stack()
    stack = list(filter(lambda x: 'migrate.py' in x, stack))
    stack = list(map(lambda x: x.splitlines().pop().strip(), stack))
    stack = list(map(lambda x: x.split('(', 1)[0], stack))
    stack = list(filter(lambda x: len(x) < 50 and '.' not in x and 'get_stack' not in x, stack))
    stack = ' / '.join(stack)

    return stack


def migrate(model, dict):
    global migrated
    if dict['_id'] in migrated:
        return False
    stack = get_stack()
    print(stack, '(', type(model).__name__, dict['_id'], ')')
    try:
        reconnect(model, target_db_uri)
        model.save(dict, validate=False, triggerEvents=False)
        migrated[dict['_id']] = True
        return True
    finally:
        reconnect(model, source_db_uri)


def change_user_password_in_target(user, password):
    global migrated
    model = UserModel()
    try:
        reconnect(model, target_db_uri)
        model.save(user, validate=False, triggerEvents=False)
        model.setPassword(user, password)
        migrated[user['_id']] = True
        return True
    finally:
        reconnect(model, source_db_uri)


def reconnect_all(db_uri):
    reconnect(AppletLibraryModel(), db_uri)
    reconnect(AccountProfile(), db_uri)
    reconnect(Profile(), db_uri)
    reconnect(UserModel(), db_uri)
    reconnect(CollectionModel(), db_uri)
    reconnect(CacheModel(), db_uri)
    reconnect(GroupModel(), db_uri)
    reconnect(FolderModel(), db_uri)
    reconnect(ResponseTokensModel(), db_uri)
    reconnect(ItemModel(), db_uri)
    reconnect(AppletBasketModel(), db_uri)
    reconnect(InvitationModel(), db_uri)
    reconnect(NoteModel(), db_uri)
    reconnect(NotificationModel(), db_uri)
    reconnect(EventsModel(), db_uri)
    reconnect(IDCodeModel(), db_uri)
    reconnect(ApiKeyModel(), db_uri)
    reconnect(ResponseAlertsModel(), db_uri)
    reconnect(SettingModel(), db_uri)
    reconnect(ShieldModel(), db_uri)


def reconnect(model, db_uri):
    model.db_uri = db_uri
    model.reconnect()


def migrateFolder(model, dict):
    if not migrate(model, dict):
        return

    if 'meta' in dict and 'historyId' in dict['meta']: # folder,item
        history = FolderModel().load(dict['meta']['historyId'], force=True)
        if history is not None:
            migrateFolder(FolderModel(), history)

    if 'cached' in dict:  # folder,item
        cache = CacheModel().load(dict['cached'])
        if cache is not None:
            migrate(CacheModel(), cache)


    if type(model) == FolderModel:
        if 'meta' in dict and 'contentId' in dict['meta']:  # folder/protocol
            content = FolderModel().load(dict['meta']['contentId'], force=True)
            if content is not None:
                migrateFolder(FolderModel(), content)

        if 'meta' in dict and 'contributionId' in dict['meta']:  # folder/protocol
            contribution = FolderModel().load(dict['meta']['contributionId'], force=True)
            if contribution is not None:
                migrateFolder(FolderModel(), contribution)

        if 'meta' in dict and 'referenceId' in dict['meta']:  # history items of folder/protocol
            ref = FolderModel().load(dict['meta']['referenceId'], force=True)
            if ref is not None:
                migrateFolder(FolderModel(), ref)

        for child in ItemModel().find(query={'folderId': dict['_id']}):
            migrateFolder(ItemModel(), child)

    if type(model) == ItemModel and 'content' in dict:
        migrate_item_cache(dict)


if __name__ == '__main__':
    reconnect_all(source_db_uri)
    user = find_user('test_account@ml.com')
    change_user_password_in_target(user, '12345678')
    start('test_account@ml.com', 'Test Account', ObjectId('6411d05deddaf60f21c3a0c5')) # RUMC test
    # start('test_account@ml.com', 'Test Account') # all applets
    # start_responses_migration('test_account@ml.com', 'Test Account')  # all
