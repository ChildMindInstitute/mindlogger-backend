# remove duplicated activity flows

from girderformindlogger.models.applet import Applet
from girderformindlogger.models.profile import Profile
from girderformindlogger.models.folder import Folder as FolderModel
from girderformindlogger.models.response_folder import ResponseItem as ResponseItemModel
from girderformindlogger.models.cache import Cache as CacheModel
from girderformindlogger.utility import jsonld_expander
from bson.objectid import ObjectId



def findAlternativeFlowId(appletId, ignoredFlowId):
    applet = FolderModel().findOne(query={'_id': appletId})
    if 'protocol' in applet['meta'] and 'activityFlows' in applet['meta']['protocol']:
        flows = [_flowId for _flowId in applet['meta']['protocol']['activityFlows'] if _flowId != ignoredFlowId]
        if len(flows) == 1:
            return flows[0]
    return None


def removeDuplicatedActivityFlows():
    docCollection = jsonld_expander.getModelCollection('activityFlow')
    activityFlows = FolderModel().find({'meta.protocolId': ObjectId('623302c1139e407e3e51410c'), 'parentId': docCollection['_id']}, fields={"_id": 1})
    # activityFlows = FolderModel().find({'parentId': docCollection['_id'], 'parentCollection': 'collection', 'baseParentId': docCollection['_id'], 'baseParentType': 'collection'}, fields={"_id": 1})
    print('total', activityFlows.count())
    for index, activityFlowId in enumerate(activityFlows, start=1):
        activityFlow = FolderModel().findOne(activityFlowId)
        flowId = str(activityFlow['_id'])
        protocols = FolderModel().find({'meta.protocol.reprolib:terms/activityFlowOrder.0.@list': {'@id': flowId}})
        countProtocols = protocols.count()
        if (countProtocols == 0):
            print('Flow id=' + flowId + ' is orphan, removing')
            if isinstance(activityFlow['cached'], ObjectId):
                CacheModel().removeWithQuery({ '_id': ObjectId(activityFlow['cached']) })

            affectedApplets = []

            # re-assign response to alternative flow
            for item in ResponseItemModel().find({'meta.activityFlow.@id': activityFlow['_id']}):
                flowId = None
                if 'applet' in item['meta']:
                    flowId = findAlternativeFlowId(item['meta']['applet']['@id'], activityFlow['_id'])
                    affectedApplets.append(item['meta']['applet']['@id'])
                if flowId:
                    item['meta']['activityFlow']['@id'] = flowId
                    ResponseItemModel().setMetadata(item, item['meta'])
                else:
                    print('Flow id=' + flowId + ' unable to find alternative flow for response item id='+str(item['_id']))

            # remove references from appletProfile.activity_flows
            for profile in Profile().find(query={'activity_flows': {'$elemMatch': {'activity_flow_id': activityFlow['_id']}}}):
                profile['activity_flows'] = [_flow for _flow in profile['activity_flows'] if _flow['activity_flow_id'] != activityFlow['_id']]
                Profile().save(profile, validate=False)
                if 'appletId' in profile:
                    affectedApplets.append(profile['appletId'])

            FolderModel().remove(activityFlow)

            # refresh cache for the affected applets 623302c3139e407e3e51412a
            for appletId in list(set(affectedApplets)):
                applet = Applet().findOne(ObjectId(appletId))
                jsonld_expander.formatLdObject(applet, 'applet', None, refreshCache=True, reimportFromUrl=False)

            continue
        if (countProtocols > 1):
            print('Flow id=' + flowId + ' is referenced times: ' + str(countProtocols))
            continue
        if protocols[0]['_id'] != activityFlow['meta']['protocolId']:
            print('Flow id=' + flowId + ' protocolId mismatch!!!')
            continue


removeDuplicatedActivityFlows()
