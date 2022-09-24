# Add missing properties to flanker items: blocks, buttons, fixationDuration, fixationScreen, blockType

from girderformindlogger.models.item import Item
from girderformindlogger.models.activity import Activity
from girderformindlogger.utility import jsonld_expander
from bson.objectid import ObjectId


def inputExists(name, inputs):
    return any(i['schema:name'][0]['@value'] == name for i in inputs)

def findInput(name, inputs):
    return next((i for i in inputs if i['schema:name'][0]['@value'] == name), None)

items = Item().find(query={'meta.activityId': ObjectId('628e3d6be50eef3353e63813'), 'meta.screen.reprolib:terms/inputType.0.@value': 'visual-stimulus-response'}, fields= {"_id": 1})
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
    itemChanged = False
    activityId = item['meta']['activityId']
    print('processing', item['_id'], index, '/', itemsCount)
    inputs = item['meta']['screen']['reprolib:terms/inputs']
    if (findInput('fixationScreen', inputs) is None):
        print('adding fixationScreen')
        inputs.append({"@type":["http://schema.org/Text"],"schema:image":"","schema:name":[{"@language":"en","@value":"fixationScreen"}],"schema:value":[{"@language":"en","@value":""}]})
        itemChanged = True

    if (findInput('fixationDuration', inputs) is None):
        print('adding fixationDuration')
        inputs.append({"@type":["http://schema.org/Number"],"schema:name":[{"@language":"en","@value":"fixationDuration"}],"schema:value":[{"@value":0}]})
        itemChanged = True

    if (findInput('buttons', inputs) is None):
        print('adding buttons')
        inputs.append({"schema:itemListElement":[{"schema:image":"","schema:name":[{"@language":"en","@value":"left"}],"schema:value":[{"@value":0}]},{"schema:image":"","schema:name":[{"@language":"en","@value":"right"}],"schema:value":[{"@value":0}]}],"schema:name":[{"@language":"en","@value":"buttons"}]})
        itemChanged = True

    if (findInput('blocks', inputs) is None):
        print('adding blocks')
        inputs.append({"@type":["http://schema.org/ItemList"],"schema:itemListElement":[],"schema:name":[{"@language":"en","@value":"blocks"}]})
        itemChanged = True

    if (findInput('blockType', inputs) is None):
        value = 'test' if 'test' in item['name'].casefold() else 'practice'
        print('adding blockType', value)
        inputs.append({"@type":["http://schema.org/Text"],"schema:name":[{"@language":"en","@value":"blockType"}],"schema:value":[{"@language":"en","@value":value}]})
        itemChanged = True

    if itemChanged:
        Item().setMetadata(item, item['meta'], validate=False)
        affectedActivityIds.append(activityId)


affectedActivityIds = list(set(affectedActivityIds))

if (len(affectedActivityIds)):
    print('Affected activities:', ','.join('"'+str(activityId)+'"' for activityId in affectedActivityIds))

# refresh cache for the affected activities
for activityId in affectedActivityIds:
    print('Refreshing affected activity id=' + str(activityId))
    activity = Activity().findOne({'_id': activityId})
    jsonld_expander.formatLdObject(activity, 'activity', None, refreshCache=True, reimportFromUrl=False)
