# fix broken links in protocol.activityFlowOrder

from girderformindlogger.models.applet import Applet
from girderformindlogger.models.folder import Folder as FolderModel
from girderformindlogger.utility import jsonld_expander
from bson.objectid import ObjectId


def findFlowsStringIds(applet):
    flowIds = []

    protocolId = applet['meta']['protocol'].get('_id').split('/').pop()
    docCollection = jsonld_expander.getModelCollection('activityFlow')
    activityFlows = FolderModel().find({'meta.protocolId': ObjectId(protocolId), 'parentId': docCollection['_id']}, fields={"_id": 1})
    for af in activityFlows:
        flowIds.append(str(af['_id']))

    return flowIds


def main(applets):
    appletsCount = applets.count()
    print('total', appletsCount)
    skipUntil = None # ObjectId('60a398c9acd96cf825f7679d')
    for index, appletId in enumerate(applets, start=1):
        if skipUntil == appletId['_id']:
            skipUntil = None
        if skipUntil is not None:
            continue

        applet = Applet().findOne(appletId)
        protocolId = ObjectId(applet['meta']['protocol'].get('_id').split('/').pop())
        protocol = FolderModel().findOne(query={'_id': protocolId})

        existingFlowsIds = findFlowsStringIds(applet)
        flowOrder = protocol['meta']['protocol']['reprolib:terms/activityFlowOrder'][0]['@list'] if 'reprolib:terms/activityFlowOrder' in protocol['meta']['protocol'] else []
        filteredFlowOrder = [fo for fo in flowOrder if fo['@id'] in existingFlowsIds]
        if flowOrder != filteredFlowOrder:
            print('fixing applet id=' + str(applet['_id']))
            protocol['meta']['protocol']['reprolib:terms/activityFlowOrder'][0]['@list'] = filteredFlowOrder
            FolderModel().setMetadata(protocol, protocol['meta'])
            jsonld_expander.formatLdObject(applet, 'applet', None, refreshCache=True, reimportFromUrl=False)


if __name__ == '__main__':
    applets = Applet().find(query={'_id': ObjectId('634fad045cb700431121d0ad')}, fields={"_id": 1})
    main(applets)
