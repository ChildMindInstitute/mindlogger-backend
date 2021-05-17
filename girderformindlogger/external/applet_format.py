from girderformindlogger.utility import jsonld_expander
from girderformindlogger.models.applet import Applet
from girderformindlogger.models.profile import Profile

profiles = Profile().find({
    'deactivated': {
        '$ne': True
    }
})

appletIds = []

usedIds = {}
for profile in profiles:
    if str(profile['appletId']) not in usedIds:
        appletIds.append(profile['appletId'])
    usedIds[str(profile['appletId'])] = True


appletModel = Applet()
print('total', len(appletIds))

for appletId in appletIds:
    applet = appletModel.findOne({
        '_id': appletId
    })

    if applet.get('meta', {}).get('schema', '') != '1.0.1' and not applet.get('meta', {}).get('applet', {}).get('deleted', False):
        print('appletId', appletId)

        jsonld_expander.formatLdObject(
            applet,
            'applet',
            updateSchema=True
        )
