# fix broken links in protocol.activityFlowOrder

from girderformindlogger.models.applet import Applet
from girderformindlogger.models.folder import Folder as FolderModel
from girderformindlogger.utility import jsonld_expander
from bson.objectid import ObjectId


def findFlowsStringIds(applet):
    flowIds = []

    protocolId = applet['meta']['protocol'].get('_id').split('/').pop()
    activityFlows = FolderModel().find({'meta.protocolId': ObjectId(protocolId), 'meta.activityFlow': {'$exists': True} }, fields={"_id": 1})
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

        # find and attach orphan flows
        for afId in applet['meta']['protocol']['activityFlows']:
            if str(afId) in existingFlowsIds:
                continue # exclude that already refer to us
            if FolderModel().find(query={'meta.protocol.activityFlows': afId, '_id': {'$ne': appletId['_id']}}).count() > 0:
                continue # if no other protocols refer to this flow
            flow = FolderModel().findOne(query={'_id': afId})
            if flow is None:
                continue
            print('attaching orphan flow '+str(afId)+' to applet ' + str(applet['_id']))
            flow['meta']['protocolId'] = protocolId
            FolderModel().setMetadata(flow, flow['meta'])
            existingFlowsIds.append(str(afId))


        flowOrder = protocol['meta']['protocol']['reprolib:terms/activityFlowOrder'][0]['@list'] if 'reprolib:terms/activityFlowOrder' in protocol['meta']['protocol'] else []
        flowOrderIdsMap = [fo['@id'] for fo in flowOrder]
        for afId in existingFlowsIds:
            if not str(afId) in flowOrderIdsMap:
                flowOrder.append({'@id': str(afId)})

        filteredFlowOrder = [fo for fo in flowOrder if fo['@id'] in existingFlowsIds]
        flowOrderChanged = flowOrder != filteredFlowOrder or len(flowOrder) != len(flowOrderIdsMap)
        if flowOrderChanged:
            print('fixing activityFlowOrder for applet ' + str(applet['_id']))
            protocol['meta']['protocol']['reprolib:terms/activityFlowOrder'][0]['@list'] = filteredFlowOrder
            FolderModel().setMetadata(protocol, protocol['meta'])
            jsonld_expander.formatLdObject(applet, 'applet', None, refreshCache=True, reimportFromUrl=False)


if __name__ == '__main__':
    applets = Applet().find(query={'_id': ObjectId('633e855131f2c2777e5e1bb6')}, fields={"_id": 1})
    main(applets)
