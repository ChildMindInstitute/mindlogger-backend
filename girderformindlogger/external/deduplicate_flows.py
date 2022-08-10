# remove duplicated activity flows

from girderformindlogger.models.applet import Applet
from girderformindlogger.models.profile import Profile
from girderformindlogger.models.folder import Folder as FolderModel
from girderformindlogger.models.response_folder import ResponseItem as ResponseItemModel
from girderformindlogger.models.cache import Cache as CacheModel
from girderformindlogger.utility import jsonld_expander
from bson.objectid import ObjectId
import re


def findFlowsByAppletId(appletId):
    flowIds = []

    applet = FolderModel().findOne(query={'_id': appletId})

    protocolId = applet['meta']['protocol'].get('_id').split('/').pop()
    docCollection = jsonld_expander.getModelCollection('activityFlow')
    activityFlows = FolderModel().find({'meta.protocolId': ObjectId(protocolId), 'parentId': docCollection['_id']}, fields={"_id": 1})
    for af in activityFlows:
        flowIds.append(af['_id'])

    if 'protocol' in applet['meta'] and 'activityFlows' in applet['meta']['protocol']:
        for flowId in applet['meta']['protocol']['activityFlows']:
            flowIds.append(flowId)

    profiles = Profile().find(query={'appletId': appletId, 'activity_flows': {'$exists': True}})
    for profile in profiles:
        for af in profile['activity_flows']:
            flowIds.append(af['activity_flow_id'])

    flowIds = list(set(flowIds))
    return FolderModel().find({'_id': {'$in': flowIds}, 'parentId': docCollection['_id']}, fields={"_id": 1})


def namesEqualWithoutParenthesis(name1, name2):
    p = re.compile("\(.*?\)")
    return re.sub(p, '', name1) == re.sub(p, '', name2)


def findAlternativeFlowId(appletId, ignoredFlowId):
    ignoredFlow = FolderModel().findOne({'_id': ignoredFlowId}, fields={"name": 1})
    applet = FolderModel().findOne(query={'_id': appletId})
    if 'protocol' in applet['meta'] and 'activityFlows' in applet['meta']['protocol']:
        flowIds = [_flowId for _flowId in applet['meta']['protocol']['activityFlows'] if _flowId != ignoredFlowId]
        for _flow in FolderModel().find({'_id': {'$in': flowIds}}, fields={"name": 1}):
            if namesEqualWithoutParenthesis(_flow['name'], ignoredFlow['name']):
                return _flow['_id']

    return None


def validateAllResponsesCanBeMovedToAlternativeFlow(flowId):
    for item in ResponseItemModel().find({'meta.activityFlow.@id': flowId}):
        altFlowId = None
        if 'applet' in item['meta']:
            altFlowId = findAlternativeFlowId(item['meta']['applet']['@id'], flowId)
        if altFlowId is None:
            return False
    return True


def removeDuplicatedActivityFlows(activityFlows=None):
    activityFlowCol = jsonld_expander.getModelCollection('activityFlow')
    protocolsCol = jsonld_expander.getModelCollection('protocols')
    if activityFlows is None:
        # activityFlows = FolderModel().find({'meta.protocolId': ObjectId('623302c1139e407e3e51410c'), 'parentId': activityFlowCol['_id']}, fields={"_id": 1})
        activityFlows = FolderModel().find({'parentId': activityFlowCol['_id']}, fields={"_id": 1})
    print('total', activityFlows.count())
    for index, activityFlowId in enumerate(activityFlows, start=1):
        activityFlow = FolderModel().findOne(activityFlowId)
        flowId = str(activityFlow['_id'])
        protocols = FolderModel().find({'meta.protocol.reprolib:terms/activityFlowOrder.0.@list': {'@id': flowId}})
        countProtocols = protocols.count()
        if (countProtocols == 0):
            if not validateAllResponsesCanBeMovedToAlternativeFlow(activityFlow['_id']):
                print('Flow id=' + flowId + ' is orphan but unable to find alternative flow, manual review required!')
                if 'protocolId' in activityFlow['meta']:
                    applets = FolderModel().find({'meta.protocol._id': 'protocol/' + str(activityFlow['meta']['protocolId']), 'parentId': protocolsCol['_id']})
                    for applet in applets:
                        print('applet id='+str(applet['_id']))
                continue

            print('Flow id=' + flowId + ' is orphan, removing')

            affectedAppletIds = []

            if 'protocolId' in activityFlow['meta']:
                applets = FolderModel().find({'meta.protocol._id': 'protocol/'+str(activityFlow['meta']['protocolId']), 'parentId': protocolsCol['_id']})
                for applet in applets:
                    affectedAppletIds.append(applet['_id'])

            if isinstance(activityFlow['cached'], ObjectId):
                CacheModel().removeWithQuery({ '_id': ObjectId(activityFlow['cached']) })

            # re-assign response to alternative flow
            for item in ResponseItemModel().find({'meta.activityFlow.@id': activityFlow['_id']}):
                altFlowId = None
                if 'applet' in item['meta']:
                    altFlowId = findAlternativeFlowId(item['meta']['applet']['@id'], activityFlow['_id'])
                    affectedAppletIds.append(item['meta']['applet']['@id'])
                if altFlowId:
                    item['meta']['activityFlow']['@id'] = altFlowId
                    ResponseItemModel().setMetadata(item, item['meta'])

            # remove references from appletProfile.activity_flows
            for profile in Profile().find(query={'activity_flows': {'$elemMatch': {'activity_flow_id': activityFlow['_id']}}}):
                profile['activity_flows'] = [_flow for _flow in profile['activity_flows'] if _flow['activity_flow_id'] != activityFlow['_id']]
                Profile().save(profile, validate=False)
                if 'appletId' in profile:
                    affectedAppletIds.append(profile['appletId'])

            FolderModel().remove(activityFlow)

            # refresh cache for the affected applets
            for appletId in list(set(affectedAppletIds)):
                print('Refreshing affected applet id='+str(appletId))
                applet = Applet().findOne(appletId)
                jsonld_expander.formatLdObject(applet, 'applet', None, refreshCache=True, reimportFromUrl=False)

            continue
        if (countProtocols > 1):
            print('Flow id=' + flowId + ' is referenced times: ' + str(countProtocols))
            continue
        if protocols[0]['_id'] != activityFlow['meta']['protocolId']:
            print('Flow id=' + flowId + ' protocolId mismatch!!!')
            continue


# flows = findFlowsByAppletId(ObjectId('62101e54b0b0a55f680ddd00'))
flows = None
removeDuplicatedActivityFlows(flows)
