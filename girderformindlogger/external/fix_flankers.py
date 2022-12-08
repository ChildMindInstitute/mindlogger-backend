# Update flanker activities from old to new protocol
# Old: https://raw.githubusercontent.com/mtg137/Flanker_applet/master/protocols/flanker/flanker_schema
# New: https://raw.githubusercontent.com/ChildMindInstitute/mindlogger-flanker-applet/master/protocols/flanker/flanker_schema

from girderformindlogger.models.item import Item
from girderformindlogger.models.activity import Activity
from girderformindlogger.models.folder import Folder
from girderformindlogger.models.user import User
from girderformindlogger.utility import jsonld_expander
from bson.objectid import ObjectId


def prepare_items(activityId):
    items = Item().find(query={'meta.activityId': activityId, 'meta.screen.@type.0': 'reprolib:schemas/Field'}, fields= {"_id": 1})
    itemsCount = items.count()
    print('total', itemsCount)
    skipUntil = None
    affectedActivityIds = []
    for index, itemId in enumerate(items, start=1):
        if skipUntil == itemId['_id']:
            skipUntil = None
        if skipUntil is not None:
            continue

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


def fix_q1_issue(activityId):
    activityChanged = False
    items = Item().find(query={'meta.activityId': activityId, 'meta.screen': {'$exists': True}})
    for item in items:
        if not 'reprolib:terms/inputs' in item['meta']['screen']:
            continue
        inputs = item['meta']['screen']['reprolib:terms/inputs']
        trials = findInput('trials', inputs)
        if trials is None or not 'schema:itemListElement' in trials:
            continue
        print('processing item:', item['_id'], item['meta']['screen']['@id'])
        # trialsIdx = inputs.index(trials)
        itemChanged = False
        for trial in trials['schema:itemListElement']:
            if 'q1' == trial['schema:name'][0]['@value']:
                trial['schema:name'][0]['@value'] = trial['schema:image']
                trial['schema:image'] = ''
                itemChanged = True
                activityChanged = True
        if itemChanged:
            Item().setMetadata(item, item['meta'], validate=False)
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
        if fix_q1_issue(hActivity['_id']):
            print('refreshig activity: ', hActivity['_id'])
            jsonld_expander.formatLdObject(hActivity, 'activity', None, refreshCache=True, reimportFromUrl=False)


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

if __name__ == '__main__':
    activityId = ObjectId('6290ed45e50eef5716db579c')
    main(activityId)
