import datetime

from bson import ObjectId
from girderformindlogger.models.item import Item
from girderformindlogger.models.applet import Applet
from girderformindlogger.models.account_profile import AccountProfile


RETENTION_SET = {
    'day': 1,
    'week': 7,
    'month': 30,
    'year': 365,
    'indefinitely': 0
}


applets = Applet().find(query={
    'meta.retentionSettings': {
        '$exists': True
    }
})

for applet in applets:

    owner_account = AccountProfile().findOne({
        'applets.owner': applet.get('_id')
    })

    _item = Item()

    if owner_account and not owner_account.get('db', None):
        _item.reconnectToDb(db_uri=owner_account.get('db', None))

    retentionSettings = applet['meta'].get('retentionSettings', None)

    retention = retentionSettings.get('retention', 'year')
    period = retentionSettings.get('period', 5)

    if retention == 'indefinitely':
        continue

    timedelta_in_days = int(period) * int(RETENTION_SET[retention])

    items = _item.find(query={
        'baseParentType': 'user',
        'meta.applet.@id': ObjectId(applet['_id']),
        'created': {
            '$lte': datetime.datetime.now() - datetime.timedelta(days=timedelta_in_days)
        }
    })

    if items:
        _item.remove({'_id': {
            '$in': [ObjectId(item['_id']) for item in items]
        }})

    print(f'Responses were removed for applet id - {applet.get("_id")}')
