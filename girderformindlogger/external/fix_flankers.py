# Add missing properties to flanker items: blocks, buttons, fixationDuration, fixationScreen, blockType

from girderformindlogger.models.item import Item
from girderformindlogger.models.activity import Activity
from girderformindlogger.models.folder import Folder
from girderformindlogger.models.user import User
from girderformindlogger.utility import jsonld_expander
from bson.objectid import ObjectId


items = Item().find(query={'meta.activityId': ObjectId('62837282e50eef7782f6c41c'), 'meta.screen.@type.0': 'reprolib:schemas/Field'}, fields= {"_id": 1})
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

activityUrl = 'https://raw.githubusercontent.com/ChildMindInstitute/mindlogger-flanker-applet/master/activities/Flanker/Flanker_schema'

# refresh cache for the affected activities
for activityId in affectedActivityIds:
    print('Refreshing affected activity id=' + str(activityId))
    activity = Folder().findOne(query={'_id': activityId})
    activity['meta']['activity']['url'] = activityUrl
    activity['meta']['activity']['_id'] = "activity/{}".format(str(activityId)) #after import

    Folder().setMetadata(folder=activity, metadata=activity['meta'])

    user = User().findOne({'_id': activity['creatorId']})
    searchCriteria = {'identifier': activity['meta']['identifier'], 'protocolId': activity['meta']['protocolId']}
    res = Activity().getFromUrl(activityUrl, 'activity', user, refreshCache=True, thread=False, meta=searchCriteria) # comment out after first run

    jsonld_expander.formatLdObject(activity, 'activity', None, refreshCache=True, reimportFromUrl=False)

exit(0)


# def inputExists(name, inputs):
#     return any(i['schema:name'][0]['@value'] == name for i in inputs)
#
# def findInput(name, inputs):
#     return next((i for i in inputs if i['schema:name'][0]['@value'] == name), None)
#
# items = Item().find(query={'meta.activityId': ObjectId('628e3d6be50eef3353e63813'), 'meta.screen.reprolib:terms/inputType.0.@value': 'visual-stimulus-response'}, fields= {"_id": 1})
# itemsCount = items.count()
# print('total', itemsCount)
# skipUntil = None
# affectedActivityIds = []
# for index, itemId in enumerate(items, start=1):
#     if skipUntil == itemId['_id']:
#         skipUntil = None
#     if skipUntil is not None:
#         continue
#
#     item = Item().findOne(itemId)
#     itemChanged = False
#     activityId = item['meta']['activityId']
#     print('processing', item['_id'], index, '/', itemsCount)
#     inputs = item['meta']['screen']['reprolib:terms/inputs']
#
#
#     itemChanged = True
#
#     trials = findInput('trials', inputs)
#     trialsIdx = inputs.index(trials)
#     inputs[trialsIdx] = {"@type":["http://schema.org/ItemList"],"schema:itemListElement":[{"@id":"left-con","@type":["http://schema.org/Property"],"schema:image":"","schema:name":[{"@language":"en","@value":"<<<<<"}],"schema:value":[{"@value":0}]},{"@id":"right-inc","@type":["http://schema.org/Property"],"schema:image":"","schema:name":[{"@language":"en","@value":"<<><<"}],"schema:value":[{"@value":1}]},{"@id":"left-inc","@type":["http://schema.org/Property"],"schema:image":"","schema:name":[{"@language":"en","@value":">><>>"}],"schema:value":[{"@value":0}]},{"@id":"right-con","@type":["http://schema.org/Property"],"schema:image":"","schema:name":[{"@language":"en","@value":">>>>>"}],"schema:value":[{"@value":1}]},{"@id":"left-neut","@type":["http://schema.org/Property"],"schema:image":"","schema:name":[{"@language":"en","@value":"--<--"}],"schema:value":[{"@value":0}]},{"@id":"right-neut","@type":["http://schema.org/Property"],"schema:image":"","schema:name":[{"@language":"en","@value":"-->--"}],"schema:value":[{"@value":1}]}],"schema:name":[{"@language":"en","@value":"trials"}],"schema:numberOfItems":[{"@value":6}]}
#
#
#     blockType = 'test' if 'test' in item['meta']['screen']['@id'].casefold() else 'practice'
#
#     blocks = findInput('blocks', inputs)
#     blocksIdx = inputs.index(blocks)
#     if (blockType == 'test'):
#         inputs[blocksIdx] = {"@type":["http://schema.org/ItemList"],"schema:itemListElement":[{"reprolib:terms/order":[{"@list":[{"@id":"left-con"},{"@id":"right-con"},{"@id":"left-inc"},{"@id":"right-inc"},{"@id":"left-neut"},{"@id":"right-neut"}]}],"schema:name":[{"@language":"en","@value":"Block 1"}],"schema:value":[{"@value":0}]},{"reprolib:terms/order":[{"@list":[{"@id":"left-con"},{"@id":"right-con"},{"@id":"left-inc"},{"@id":"right-inc"},{"@id":"left-neut"},{"@id":"right-neut"}]}],"schema:name":[{"@language":"en","@value":"Block 2"}],"schema:value":[{"@value":1}]},{"reprolib:terms/order":[{"@list":[{"@id":"left-con"},{"@id":"right-con"},{"@id":"left-inc"},{"@id":"right-inc"},{"@id":"left-neut"},{"@id":"right-neut"}]}],"schema:name":[{"@language":"en","@value":"Block 3"}],"schema:value":[{"@value":2}]},{"reprolib:terms/order":[{"@list":[{"@id":"left-con"},{"@id":"right-con"},{"@id":"left-inc"},{"@id":"right-inc"},{"@id":"left-neut"},{"@id":"right-neut"}]}],"schema:name":[{"@language":"en","@value":"Block 4"}],"schema:value":[{"@value":3}]},{"reprolib:terms/order":[{"@list":[{"@id":"left-con"},{"@id":"right-con"},{"@id":"left-inc"},{"@id":"right-inc"},{"@id":"left-neut"},{"@id":"right-neut"}]}],"schema:name":[{"@language":"en","@value":"Block 5"}],"schema:value":[{"@value":4}]},{"reprolib:terms/order":[{"@list":[{"@id":"left-con"},{"@id":"right-con"},{"@id":"left-inc"},{"@id":"right-inc"},{"@id":"left-neut"},{"@id":"right-neut"}]}],"schema:name":[{"@language":"en","@value":"Block 6"}],"schema:value":[{"@value":5}]},{"reprolib:terms/order":[{"@list":[{"@id":"left-con"},{"@id":"right-con"},{"@id":"left-inc"},{"@id":"right-inc"},{"@id":"left-neut"},{"@id":"right-neut"}]}],"schema:name":[{"@language":"en","@value":"Block 7"}],"schema:value":[{"@value":6}]},{"reprolib:terms/order":[{"@list":[{"@id":"left-con"},{"@id":"right-con"},{"@id":"left-inc"},{"@id":"right-inc"},{"@id":"left-neut"},{"@id":"right-neut"}]}],"schema:name":[{"@language":"en","@value":"Block 8"}],"schema:value":[{"@value":7}]},{"reprolib:terms/order":[{"@list":[{"@id":"left-con"},{"@id":"right-con"},{"@id":"left-inc"},{"@id":"right-inc"},{"@id":"left-neut"},{"@id":"right-neut"}]}],"schema:name":[{"@language":"en","@value":"Block 9"}],"schema:value":[{"@value":8}]},{"reprolib:terms/order":[{"@list":[{"@id":"left-con"},{"@id":"right-con"},{"@id":"left-inc"},{"@id":"right-inc"},{"@id":"left-neut"},{"@id":"right-neut"}]}],"schema:name":[{"@language":"en","@value":"Block 10"}],"schema:value":[{"@value":9}]},{"reprolib:terms/order":[{"@list":[{"@id":"left-con"},{"@id":"right-con"},{"@id":"left-inc"},{"@id":"right-inc"},{"@id":"left-neut"},{"@id":"right-neut"}]}],"schema:name":[{"@language":"en","@value":"Block 11"}],"schema:value":[{"@value":10}]},{"reprolib:terms/order":[{"@list":[{"@id":"left-con"},{"@id":"right-con"},{"@id":"left-inc"},{"@id":"right-inc"},{"@id":"left-neut"},{"@id":"right-neut"}]}],"schema:name":[{"@language":"en","@value":"Block 12"}],"schema:value":[{"@value":11}]},{"reprolib:terms/order":[{"@list":[{"@id":"left-con"},{"@id":"right-con"},{"@id":"left-inc"},{"@id":"right-inc"},{"@id":"left-neut"},{"@id":"right-neut"}]}],"schema:name":[{"@language":"en","@value":"Block 13"}],"schema:value":[{"@value":12}]},{"reprolib:terms/order":[{"@list":[{"@id":"left-con"},{"@id":"right-con"},{"@id":"left-inc"},{"@id":"right-inc"},{"@id":"left-neut"},{"@id":"right-neut"}]}],"schema:name":[{"@language":"en","@value":"Block 14"}],"schema:value":[{"@value":13}]},{"reprolib:terms/order":[{"@list":[{"@id":"left-con"},{"@id":"right-con"},{"@id":"left-inc"},{"@id":"right-inc"},{"@id":"left-neut"},{"@id":"right-neut"}]}],"schema:name":[{"@language":"en","@value":"Block 15"}],"schema:value":[{"@value":14}]},{"reprolib:terms/order":[{"@list":[{"@id":"left-con"},{"@id":"right-con"},{"@id":"left-inc"},{"@id":"right-inc"},{"@id":"left-neut"},{"@id":"right-neut"}]}],"schema:name":[{"@language":"en","@value":"Block 16"}],"schema:value":[{"@value":15}]},{"reprolib:terms/order":[{"@list":[{"@id":"left-con"},{"@id":"right-con"},{"@id":"left-inc"},{"@id":"right-inc"},{"@id":"left-neut"},{"@id":"right-neut"}]}],"schema:name":[{"@language":"en","@value":"Block 17"}],"schema:value":[{"@value":16}]},{"reprolib:terms/order":[{"@list":[{"@id":"left-con"},{"@id":"right-con"},{"@id":"left-inc"},{"@id":"right-inc"},{"@id":"left-neut"},{"@id":"right-neut"}]}],"schema:name":[{"@language":"en","@value":"Block 18"}],"schema:value":[{"@value":17}]},{"reprolib:terms/order":[{"@list":[{"@id":"left-con"},{"@id":"right-con"},{"@id":"left-inc"},{"@id":"right-inc"},{"@id":"left-neut"},{"@id":"right-neut"}]}],"schema:name":[{"@language":"en","@value":"Block 19"}],"schema:value":[{"@value":18}]},{"reprolib:terms/order":[{"@list":[{"@id":"left-con"},{"@id":"right-con"},{"@id":"left-inc"},{"@id":"right-inc"},{"@id":"left-neut"},{"@id":"right-neut"}]}],"schema:name":[{"@language":"en","@value":"Block 20"}],"schema:value":[{"@value":19}]}],"schema:name":[{"@language":"en","@value":"blocks"}],"schema:numberOfItems":[{"@value":20}]}
#     else:
#         inputs[blocksIdx] = {"@type":["http://schema.org/ItemList"],"schema:itemListElement":[{"reprolib:terms/order":[{"@list":[{"@id":"left-con"},{"@id":"right-con"},{"@id":"left-inc"},{"@id":"right-inc"},{"@id":"left-neut"},{"@id":"right-neut"}]}],"schema:name":[{"@language":"en","@value":"Block 1"}],"schema:value":[{"@value":0}]},{"reprolib:terms/order":[{"@list":[{"@id":"left-con"},{"@id":"right-con"},{"@id":"left-inc"},{"@id":"right-inc"},{"@id":"left-neut"},{"@id":"right-neut"}]}],"schema:name":[{"@language":"en","@value":"Block 2"}],"schema:value":[{"@value":1}]},{"reprolib:terms/order":[{"@list":[{"@id":"left-con"},{"@id":"right-con"},{"@id":"left-inc"},{"@id":"right-inc"},{"@id":"left-neut"},{"@id":"right-neut"}]}],"schema:name":[{"@language":"en","@value":"Block 3"}],"schema:value":[{"@value":2}]},{"reprolib:terms/order":[{"@list":[{"@id":"left-con"},{"@id":"right-con"},{"@id":"left-inc"},{"@id":"right-inc"},{"@id":"left-neut"},{"@id":"right-neut"}]}],"schema:name":[{"@language":"en","@value":"Block 4"}],"schema:value":[{"@value":3}]},{"reprolib:terms/order":[{"@list":[{"@id":"left-con"},{"@id":"right-con"},{"@id":"left-inc"},{"@id":"right-inc"},{"@id":"left-neut"},{"@id":"right-neut"}]}],"schema:name":[{"@language":"en","@value":"Block 5"}],"schema:value":[{"@value":4}]}],"schema:name":[{"@language":"en","@value":"blocks"}],"schema:numberOfItems":[{"@value":5}]}
#
#
#     if (findInput('fixationScreen', inputs) is None):
#         print('adding fixationScreen')
#         inputs.append({"@type":["http://schema.org/Text"],"schema:image":"","schema:name":[{"@language":"en","@value":"fixationScreen"}],"schema:value":[{"@language":"en","@value":"-----"}]})
#         itemChanged = True
#
#     if (findInput('fixationDuration', inputs) is None):
#         print('adding fixationDuration')
#         inputs.append({"@type":["http://schema.org/Number"],"schema:name":[{"@language":"en","@value":"fixationDuration"}],"schema:value":[{"@value":500}]})
#         itemChanged = True
#
#     if (findInput('buttons', inputs) is None):
#         print('adding buttons')
#         inputs.append({"schema:itemListElement":[{"schema:image":"","schema:name":[{"@language":"en","@value":"<"}],"schema:value":[{"@value":0}]},{"schema:image":"","schema:name":[{"@language":"en","@value":">"}],"schema:value":[{"@value":0}]}],"schema:name":[{"@language":"en","@value":"buttons"}]})
#         itemChanged = True
#
#     if (findInput('blocks', inputs) is None):
#         print('adding blocks')
#         inputs.append({"@type":["http://schema.org/ItemList"],"schema:itemListElement":[{"reprolib:terms/order":[{"@list":[{"@id":"left-con"},{"@id":"right-con"},{"@id":"left-inc"},{"@id":"right-inc"},{"@id":"left-neut"},{"@id":"right-neut"}]}],"schema:name":[{"@language":"en","@value":"Block 1"}],"schema:value":[{"@value":0}]},{"reprolib:terms/order":[{"@list":[{"@id":"left-con"},{"@id":"right-con"},{"@id":"left-inc"},{"@id":"right-inc"},{"@id":"left-neut"},{"@id":"right-neut"}]}],"schema:name":[{"@language":"en","@value":"Block 2"}],"schema:value":[{"@value":1}]},{"reprolib:terms/order":[{"@list":[{"@id":"left-con"},{"@id":"right-con"},{"@id":"left-inc"},{"@id":"right-inc"},{"@id":"left-neut"},{"@id":"right-neut"}]}],"schema:name":[{"@language":"en","@value":"Block 3"}],"schema:value":[{"@value":2}]},{"reprolib:terms/order":[{"@list":[{"@id":"left-con"},{"@id":"right-con"},{"@id":"left-inc"},{"@id":"right-inc"},{"@id":"left-neut"},{"@id":"right-neut"}]}],"schema:name":[{"@language":"en","@value":"Block 4"}],"schema:value":[{"@value":3}]},{"reprolib:terms/order":[{"@list":[{"@id":"left-con"},{"@id":"right-con"},{"@id":"left-inc"},{"@id":"right-inc"},{"@id":"left-neut"},{"@id":"right-neut"}]}],"schema:name":[{"@language":"en","@value":"Block 5"}],"schema:value":[{"@value":4}]},{"reprolib:terms/order":[{"@list":[{"@id":"left-con"},{"@id":"right-con"},{"@id":"left-inc"},{"@id":"right-inc"},{"@id":"left-neut"},{"@id":"right-neut"}]}],"schema:name":[{"@language":"en","@value":"Block 6"}],"schema:value":[{"@value":5}]},{"reprolib:terms/order":[{"@list":[{"@id":"left-con"},{"@id":"right-con"},{"@id":"left-inc"},{"@id":"right-inc"},{"@id":"left-neut"},{"@id":"right-neut"}]}],"schema:name":[{"@language":"en","@value":"Block 7"}],"schema:value":[{"@value":6}]},{"reprolib:terms/order":[{"@list":[{"@id":"left-con"},{"@id":"right-con"},{"@id":"left-inc"},{"@id":"right-inc"},{"@id":"left-neut"},{"@id":"right-neut"}]}],"schema:name":[{"@language":"en","@value":"Block 8"}],"schema:value":[{"@value":7}]},{"reprolib:terms/order":[{"@list":[{"@id":"left-con"},{"@id":"right-con"},{"@id":"left-inc"},{"@id":"right-inc"},{"@id":"left-neut"},{"@id":"right-neut"}]}],"schema:name":[{"@language":"en","@value":"Block 9"}],"schema:value":[{"@value":8}]},{"reprolib:terms/order":[{"@list":[{"@id":"left-con"},{"@id":"right-con"},{"@id":"left-inc"},{"@id":"right-inc"},{"@id":"left-neut"},{"@id":"right-neut"}]}],"schema:name":[{"@language":"en","@value":"Block 10"}],"schema:value":[{"@value":9}]},{"reprolib:terms/order":[{"@list":[{"@id":"left-con"},{"@id":"right-con"},{"@id":"left-inc"},{"@id":"right-inc"},{"@id":"left-neut"},{"@id":"right-neut"}]}],"schema:name":[{"@language":"en","@value":"Block 11"}],"schema:value":[{"@value":10}]},{"reprolib:terms/order":[{"@list":[{"@id":"left-con"},{"@id":"right-con"},{"@id":"left-inc"},{"@id":"right-inc"},{"@id":"left-neut"},{"@id":"right-neut"}]}],"schema:name":[{"@language":"en","@value":"Block 12"}],"schema:value":[{"@value":11}]},{"reprolib:terms/order":[{"@list":[{"@id":"left-con"},{"@id":"right-con"},{"@id":"left-inc"},{"@id":"right-inc"},{"@id":"left-neut"},{"@id":"right-neut"}]}],"schema:name":[{"@language":"en","@value":"Block 13"}],"schema:value":[{"@value":12}]},{"reprolib:terms/order":[{"@list":[{"@id":"left-con"},{"@id":"right-con"},{"@id":"left-inc"},{"@id":"right-inc"},{"@id":"left-neut"},{"@id":"right-neut"}]}],"schema:name":[{"@language":"en","@value":"Block 14"}],"schema:value":[{"@value":13}]},{"reprolib:terms/order":[{"@list":[{"@id":"left-con"},{"@id":"right-con"},{"@id":"left-inc"},{"@id":"right-inc"},{"@id":"left-neut"},{"@id":"right-neut"}]}],"schema:name":[{"@language":"en","@value":"Block 15"}],"schema:value":[{"@value":14}]},{"reprolib:terms/order":[{"@list":[{"@id":"left-con"},{"@id":"right-con"},{"@id":"left-inc"},{"@id":"right-inc"},{"@id":"left-neut"},{"@id":"right-neut"}]}],"schema:name":[{"@language":"en","@value":"Block 16"}],"schema:value":[{"@value":15}]},{"reprolib:terms/order":[{"@list":[{"@id":"left-con"},{"@id":"right-con"},{"@id":"left-inc"},{"@id":"right-inc"},{"@id":"left-neut"},{"@id":"right-neut"}]}],"schema:name":[{"@language":"en","@value":"Block 17"}],"schema:value":[{"@value":16}]},{"reprolib:terms/order":[{"@list":[{"@id":"left-con"},{"@id":"right-con"},{"@id":"left-inc"},{"@id":"right-inc"},{"@id":"left-neut"},{"@id":"right-neut"}]}],"schema:name":[{"@language":"en","@value":"Block 18"}],"schema:value":[{"@value":17}]},{"reprolib:terms/order":[{"@list":[{"@id":"left-con"},{"@id":"right-con"},{"@id":"left-inc"},{"@id":"right-inc"},{"@id":"left-neut"},{"@id":"right-neut"}]}],"schema:name":[{"@language":"en","@value":"Block 19"}],"schema:value":[{"@value":18}]},{"reprolib:terms/order":[{"@list":[{"@id":"left-con"},{"@id":"right-con"},{"@id":"left-inc"},{"@id":"right-inc"},{"@id":"left-neut"},{"@id":"right-neut"}]}],"schema:name":[{"@language":"en","@value":"Block 20"}],"schema:value":[{"@value":19}]}],"schema:name":[{"@language":"en","@value":"blocks"}],"schema:numberOfItems":[{"@value":20}]})
#         itemChanged = True
#
#     if (findInput('blockType', inputs) is None):
#         value = 'test' if 'test' in item['meta']['screen']['@id'].casefold() else 'practice'
#         print('adding blockType', value)
#         inputs.append({"@type":["http://schema.org/Text"],"schema:name":[{"@language":"en","@value":"blockType"}],"schema:value":[{"@language":"en","@value":value}]})
#         itemChanged = True
#
#     if itemChanged:
#         Item().setMetadata(item, item['meta'], validate=False)
#         affectedActivityIds.append(activityId)
#
#
# affectedActivityIds = list(set(affectedActivityIds))
#
# if (len(affectedActivityIds)):
#     print('Affected activities:', ','.join('"'+str(activityId)+'"' for activityId in affectedActivityIds))
#
# # refresh cache for the affected activities
# for activityId in affectedActivityIds:
#     print('Refreshing affected activity id=' + str(activityId))
#     activity = Activity().findOne({'_id': activityId})
#     jsonld_expander.formatLdObject(activity, 'activity', None, refreshCache=True, reimportFromUrl=False)



# old: https://raw.githubusercontent.com/mtg137/Flanker_applet/master/protocols/flanker/flanker_schema
# old: https://raw.githubusercontent.com/mtg137/Flanker_applet/staging/protocols/flanker/flanker_schema
# TODO: file names are renamed. how about responses?
