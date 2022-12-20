# Update flanker activities from old to new protocol
# Old: https://raw.githubusercontent.com/mtg137/Flanker_applet/master/protocols/flanker/flanker_schema
# New: https://raw.githubusercontent.com/ChildMindInstitute/mindlogger-flanker-applet/master/protocols/flanker/flanker_schema

from girderformindlogger.models.item import Item
from girderformindlogger.models.activity import Activity
from girderformindlogger.models.folder import Folder
from girderformindlogger.models.user import User
from girderformindlogger.models.applet import Applet
from girderformindlogger.models.account_profile import AccountProfile
from girderformindlogger.models.cache import Cache
from girderformindlogger.utility import jsonld_expander
from bson.objectid import ObjectId


def prepare_items(activityId):
    items = Item().find(query={'meta.activityId': activityId, 'meta.screen.@type.0': 'reprolib:schemas/Field'}, fields= {"_id": 1})
    itemsCount = items.count()
    print('total', itemsCount)
    affectedActivityIds = []
    for index, itemId in enumerate(items, start=1):
        item = Item().findOne(itemId)
        print('processing', item['_id'], index, '/', itemsCount)
        affectedActivityIds.append(item['meta']['activityId'])

        item['meta']['screen']['url'] = 'https://raw.githubusercontent.com/ChildMindInstitute/mindlogger-flanker-applet/master/activities/Flanker/items/{}'.format(item['meta']['screen']['@id'])
        item['meta']['identifier'] = '{}/{}'.format(str(item['meta']['activityId']), str(itemId['_id'])) #after import
        Item().setMetadata(item, item['meta'])

    affectedActivityIds = list(set(affectedActivityIds))

    if (len(affectedActivityIds)):
        print('Affected activities:', ','.join('"'+str(activityId)+'"' for activityId in affectedActivityIds))

    return affectedActivityIds


def findInput(name, inputs):
    return next((i for i in inputs if i['schema:name'][0]['@value'] == name), None)

def fix_q1_issue_in_json(id, model):
    if not 'reprolib:terms/inputs' in model:
        return False
    inputs = model['reprolib:terms/inputs']
    trials = findInput('trials', inputs)
    if trials is None or not 'schema:itemListElement' in trials:
        return False
    print('processing item:', id, model['@id'])
    itemChanged = False
    for trial in trials['schema:itemListElement']:
        if 'q1' == trial['schema:name'][0]['@value']:
            trial['schema:name'][0]['@value'] = trial['schema:image']
            trial['schema:image'] = ''
            itemChanged = True

    return itemChanged

def fix_q1_issue(activityId):
    activityChanged = False
    items = Item().find(query={'meta.activityId': activityId, 'meta.screen': {'$exists': True}})
    for item in items:
        if fix_q1_issue_in_json(item['_id'], item['meta']['screen']):
            Item().setMetadata(item, item['meta'], validate=False)
            activityChanged = True

        if 'cached' in item:
            cache = Cache().getFromSourceID('item', item['_id'])
            if cache is not None and fix_q1_issue_in_json(item['_id'], cache):
                Cache().updateCache(item['cached'], 'item', item['_id'], 'screen', cache)

    return activityChanged


def fix_q1_issue_in_versions(activityId):
    print('fix_q1_issue_in_versions')
    hActivities = Folder().find(query={'meta.originalId': activityId, 'meta.activity': {'$exists': True}})
    hCount = hActivities.count()
    if hCount == 0:
        return
    print('Fixing ' + str(hCount) + ' historical version(s) of the activity id=' + str(activityId))
    for hActivity in hActivities:
        print('processing activity: ', hActivity['_id'])
        fix_q1_issue(hActivity['_id'])


def fix_flankers(activityId, reImport = True):
    activityUrl = 'https://raw.githubusercontent.com/ChildMindInstitute/mindlogger-flanker-applet/master/activities/Flanker/Flanker_schema'
    print('Refreshing affected activity id=' + str(activityId))
    activity = Folder().findOne(query={'_id': activityId})
    activity['meta']['activity']['url'] = activityUrl
    activity['meta']['activity']['_id'] = "activity/{}".format(str(activityId)) #after import
    if not 'identifier' in activity['meta']:
        activity['meta']['identifier'] = str(activityId)

    Folder().setMetadata(folder=activity, metadata=activity['meta'])

    user = User().findOne({'_id': activity['creatorId']})
    searchCriteria = {'identifier': activity['meta']['identifier'], 'protocolId': activity['meta']['protocolId']}
    if reImport:
        res = Activity().getFromUrl(activityUrl, 'activity', user, refreshCache=True, thread=False, meta=searchCriteria) # comment out after first run
    # refresh cache for the affected activities
    jsonld_expander.formatLdObject(activity, 'activity', None, refreshCache=True, reimportFromUrl=False)



def main(activityId):
    affectedActivityIds = prepare_items(activityId)

    for activityId in affectedActivityIds:
        fix_q1_issue_in_versions(activityId)

    for activityId in affectedActivityIds:
        fix_flankers(activityId, True)

    # fix some fields after import
    affectedActivityIds = prepare_items(ObjectId('6290ed45e50eef5716db579c'))
    for activityId in affectedActivityIds:
        fix_flankers(activityId, False)

def get_activities_for_account(email):
    print('get_activities_for_account for', email)
    user = User().findOne({'email': User().hash(email), 'email_encrypted': True})

    if user is None:
        user = User().findOne({'email': email, 'email_encrypted': {'$ne': True}})

    if user is None:
        raise AccessException('user not found')

    activities = []
    applets = Applet().getAppletsForUser('manager', user, active=True)
    for applet in applets:
        for activityId in applet['meta']['protocol']['activities']:
            activity = Activity().findOne({'_id': activityId})
            if activity is None or not '@id' in activity['meta']['activity']:
                continue
            if activity['meta']['activity']['@id'] == 'Flanker_360':
                print('applet', applet['name'], applet['_id'], 'activity', activity['name'], activity['_id'])
                activities.append(activity)
    print('activities to process', len(activities))
    return activities


if __name__ == '__main__':
    activities = get_activities_for_account('jeligi9407@zneep.com')
    for activity in activities:
        main(activity['_id'])
    # activityId = ObjectId('6290ed45e50eef5716db579c')
    # main(activityId)
