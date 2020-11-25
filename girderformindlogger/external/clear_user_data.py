import datetime

from bson import ObjectId
from girderformindlogger.models.item import Item
from girderformindlogger.models.applet import Applet


RETENTION_SET = {
    'day': 1,
    'week': 7,
    'month': 30,
    'year': 365
}


applets = Applet().find(query={
    'meta.retentionSettings': {
        '$exists': True
    }
})

for applet in applets:
    retentionSettings = applet['meta'].get('retentionSettings', None)

    retention = retentionSettings.get('retention', 'year')
    period = retentionSettings.get('period', 5)

    timedelta_in_days = int(period) * int(RETENTION_SET[retention])

    items = Item().find(query={
        'baseParentType': 'user',
        'meta.applet.@id': ObjectId(applet['_id']),
        'created': {
            '$lte': datetime.datetime.now() - datetime.timedelta(days=timedelta_in_days)
        }
    })

    if items:
        Item().remove({'_id': {
            '$in': [ObjectId(item['_id']) for item in items]
        }})

    print(f'Responses were removed - {len(items)}')
