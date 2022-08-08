# convert linked activities to activity flow

from girderformindlogger.models.applet import Applet
from girderformindlogger.models.profile import Profile
from girderformindlogger.models.folder import Folder as FolderModel
from girderformindlogger.models.activity import Activity
from girderformindlogger.utility import jsonld_expander
from bson.objectid import ObjectId

# '_id': ObjectId('5f0e35523477de8b4a528dd0'),
applets = Applet().find(query={ 'meta.applet': { '$exists': True } }, fields= {"_id": 1})
appletsCount = applets.count()
print('total', appletsCount)
skipUntil = None
for index, appletId in enumerate(applets, start=1):
    if skipUntil == appletId['_id']:
        skipUntil = None
    if skipUntil is not None:
        continue

    applet = Applet().findOne(appletId)

    # optional filters
    # if applet['accountId'] != ObjectId("5f175a27cf47283a93eaf7cc") :
    #     continue
    # if applet['_id'] != ObjectId("5f175a27cf47283a93eaf7cc"):
    #     continue


    formatted = jsonld_expander.formatLdObject(applet, 'applet', None, refreshCache=False, reimportFromUrl=False)
    if formatted is None or formatted == {}:
        continue

    print('processing', applet['_id'], index, '/', appletsCount)

    activityList = []
    activityIndexes = {}

    combineReports = formatted['applet'].get('reprolib:terms/combineReports', [])
    combineReports = combineReports[0]['@value'] if len(combineReports) > 0 else False

    g = []
    activityIRIs = dict.keys(formatted['activities'].copy())
    for activityIRI in activityIRIs:
        activity = Activity().findOne({
            '_id': ObjectId(formatted['activities'][activityIRI])
        })

        if not activity:
            formatted['activities'].pop(activityIRI)

        formattedActivity = jsonld_expander.formatLdObject(activity, 'activity', None, refreshCache=False, reimportFromUrl=False)
        if formattedActivity is None or formattedActivity == {}:
            continue

        content = formattedActivity['activity']
        messages = content.get('reprolib:terms/messages', [])

        activityIndexes[content['@id']] = len(activityList)
        activityList.append({
            'id': activity['_id'],
            'name': content['@id']
        })

        nextActivities = []
        for message in messages:
            nextActivity = message.get('reprolib:terms/nextActivity', [])

            recommended = message.get('reprolib:terms/isRecommended', [])
            isRecommended = False
            if len(recommended) and recommended[0]['@value']:
                isRecommended = True

            if len(nextActivity):
                value = nextActivity[0]['@value']
                updated = False

                for activity in nextActivities:
                    if activity['index'] == value:
                        activity['badge'] = activity['badge'] or isRecommended
                        updated = True

                if not updated:
                    nextActivities.append({
                        'index': nextActivity[0]['@value'],
                        'badge': isRecommended
                    })

        g.append(nextActivities)

    markedCount = 0
    marked = []

    for edges in g:
        marked.append(False)

        for edge in edges:
            if not edge['index'] in activityIndexes:
                del edge['index']
                continue
            edge['index'] = activityIndexes[edge['index']]

    flowIndex = 0
    protocolId = formatted['protocol'].get('_id').split('/').pop()

    flowOrder = []
    flowProperties = []
    def createActivityFlow(path, badge):
        global flowIndex, protocolId, flowOrder, flowProperties

        flowIndex = flowIndex + 1
        name = f'flow{flowIndex}'
        data = {
            "@context": [
                "https://raw.githubusercontent.com/jj105/reproschema-context/master/context.json"
            ],
            "@id": name,
            "@type": "reproschema:ActivityFlow",
            "name": name,
            "description": name,
            "combineReports": combineReports,
            "showBadge": badge,
            "order": [
                activityList[index]['name'] for index in path
            ],
            "isVis": True,
        }

        expanded = jsonld_expander.expandObj({
            "https://raw.githubusercontent.com/jj105/reproschema-context/master/context.json": {
                "@version": 1.1,
                "pav": "http://purl.org/pav/",
                "prov": "http://www.w3.org/ns/prov#",
                "nidm": "http://purl.org/nidash/nidm#",
                "xsd": "http://www.w3.org/2001/XMLSchema#",
                "skos": "http://www.w3.org/2004/02/skos/core#",
                "reproterms": "https://raw.githubusercontent.com/ReproNim/reproschema/master/terms/",
                "reproschema": "https://raw.githubusercontent.com/ReproNim/reproschema/master/schemas/",
                "schema": "http://schema.org/",
                "@language": "en",
                "schema:description": {
                    "@container": "@language"
                },
                "description": {
                    "@id": "schema:description",
                    "@container": "@language"
                },
                "name": {
                    "@id": "schema:name",
                    "@container": "@language"
                },
                "value": {
                    "@id": "schema:value",
                    "@container": "@language"
                },
                "score": {
                    "@id": "schema:score",
                    "@container": "@language"
                },
                "header": {
                    "@id": "schema:header",
                    "@container": "@language"
                },
                "section": {
                    "@id": "schema:section",
                    "@container": "@language"
                },
                "schema:rate": {
                    "@container": "@language"
                },
                "schema:startTime": {
                    "@container": "@language"
                },
                "schema:endTime": {
                    "@container": "@language"
                },
                "schema:name": {
                    "@container": "@language"
                },
                "schema:color": {
                    "@type": "schema:String"
                },
                "schema:value": {
                    "@container": "@language"
                },
                "schema:score": {
                    "@container": "@language"
                },
                "schema:alert": {
                    "@container": "@language"
                },
                "schema:image": {
                    "@type": "@vocab"
                },
                "schema:watermark": {
                    "@type": "@vocab"
                },
                "schema:citation": {
                    "@container": "@language"
                },
                "schema:version": {
                    "@container": "@language"
                },
                "schema:schemaVersion": {
                    "@container": "@language"
                },
                "skos:prefLabel": {
                    "@container": "@language"
                },
                "skos:altLabel": {
                    "@container": "@language"
                },
                "prefLabel": {
                    "@id": "skos:prefLabel",
                    "@container": "@language"
                },
                "altLabel": {
                    "@id": "skos:altLabel",
                    "@container": "@language"
                },
                "preamble": {
                    "@id": "reproterms:preamble",
                    "@container": "@language"
                },
                "maxLength": {
                    "@id": "reproterms:maxLength",
                    "@type": "schema:Number"
                },
                "isReviewerActivity": {
                    "@id": "reproterms:isReviewerActivity",
                    "@type": "schema:Boolean"
                },
                "isOnePageAssessment": {
                    "@id": "reproterms:isOnePageAssessment",
                    "@type": "schema:Boolean"
                },
                "streamEnabled": {
                    "@id": "reproterms:streamEnabled",
                    "@type": "schema:Boolean"
                },
                "combineReports": {
                    "@id": "reproterms:combineReports",
                    "@type": "schema:Boolean"
                },
                "showBadge": {
                    "@id": "reproterms:showBadge",
                    "@type": "schema:Boolean"
                },
                "valueType": {
                    "@id": "reproterms:valueType",
                    "@type": "@vocab"
                },
                "landingPage": {
                    "@id": "reproterms:landingPage",
                    "@container": "@language"
                },
                "landingPageContent": {
                    "@id": "reproterms:landingPageContent",
                    "@container": "@language"
                },
                "landingPageType": {
                    "@id": "reproterms:landingPageType",
                    "@type": "xsd:string"
                },
                "activityType": {
                    "@id": "reproterms:activityType",
                    "@type": "xsd:string"
                },
                "correctAnswer": {
                    "@id": "schema:correctAnswer"
                },
                "question": {
                    "@id": "schema:question",
                    "@container": "@language"
                },
                "choices": {
                    "@id": "schema:itemListElement"
                },
                "choiceUrl": {
                    "@id": "schema:DigitalDocument",
                    "@type": "@id"
                },
                "timeScreen": {
                    "@id": "reproterms:timeScreen",
                    "@type": "schema:String"
                },
                "requiredValue": {
                    "@id": "reproterms:requiredValue",
                    "@type": "schema:Boolean"
                },
                "colorPalette": {
                    "@id": "reproterms:colorPalette",
                    "@type": "schema:Boolean"
                },
                "multipleChoice": {
                    "@id": "reproterms:multipleChoice",
                    "@type": "schema:Boolean"
                },
                "scoring": {
                    "@id": "reproterms:scoring",
                    "@type": "schema:Boolean"
                },
                "randomizeOptions": {
                    "@id": "reproterms:randomizeOptions",
                    "@type": "schema:Boolean"
                },
                "topNavigationOption": {
                    "@id": "reproterms:topNavigationOption",
                    "@type": "schema:Boolean"
                },
                "removeBackOption": {
                    "@id": "reproterms:removeBackOption",
                    "@type": "schema:Boolean"
                },
                "removeUndoOption": {
                    "@id": "reproterms:removeUndoOption",
                    "@type": "schema:Boolean"
                },
                "showTickMarks": {
                    "@id": "reproterms:showTickMarks",
                    "@type": "schema:Boolean"
                },
                "continousSlider": {
                    "@id": "reproterms:continousSlider",
                    "@type": "schema:Boolean"
                },
                "tickMark": {
                    "@id": "reproterms:tickMark",
                    "@type": "schema:Boolean"
                },
                "tickLabel": {
                    "@id": "reproterms:tickLabel",
                    "@type": "schema:Boolean"
                },
                "textAnchors": {
                    "@id": "reproterms:textAnchors",
                    "@type": "schema:Boolean"
                },
                "responseAlert": {
                    "@id": "reproterms:responseAlert",
                    "@type": "schema:Boolean"
                },
                "responseOptions": {
                    "@id": "reproterms:responseOptions",
                    "@type": "@vocab"
                },
                "sliderOptions": {
                    "@id": "reproterms:sliderOptions"
                },
                "positiveBehaviors": {
                    "@id": "reproterms:positiveBehaviors"
                },
                "negativeBehaviors": {
                    "@id": "reproterms:negativeBehaviors"
                },
                "options": {
                    "@id": "reproterms:options"
                },
                "itemList": {
                    "@id": "reproterms:itemList"
                },
                "scores": {
                    "@id": "reproterms:scores"
                },
                "itemOptions": {
                    "@id": "reproterms:itemOptions"
                },
                "dataType": {
                    "@id": "schema:DataType",
                    "@type": "@id"
                },
                "responseAlertMessage": {
                    "@id": "schema:responseAlertMessage"
                },
                "timeDuration": {
                    "@id": "schema:timeDuration"
                },
                "minAge": {
                    "@id": "schema:minAge"
                },
                "maxAge": {
                    "@id": "schema:maxAge"
                },
                "minValue": {
                    "@id": "schema:minValue"
                },
                "maxValue": {
                    "@id": "schema:maxValue"
                },
                "minAlertValue": {
                    "@id": "schema:minAlertValue"
                },
                "maxAlertValue": {
                    "@id": "schema:maxAlertValue"
                },
                "activityFlows": "@nest",
                "activityFlowOrder": {
                    "@id": "reproterms:activityFlowOrder",
                    "@container": "@list",
                    "@type": "@vocab",
                    "@nest": "activityFlows"
                },
                "activityFlowProperties": {
                    "@id": "reproterms:activityFlowProperties",
                    "@container": "@index",
                    "@nest": "activityFlows"
                },
                "ui": "@nest",
                "order": {
                    "@id": "reproterms:order",
                    "@container": "@list",
                    "@type": "@vocab",
                    "@nest": "ui"
                },
                "addProperties": {
                    "@id": "reproterms:addProperties",
                    "@container": "@index",
                    "@nest": "ui"
                },
                "printItems": {
                    "@id": "reproterms:printItems",
                    "@container": "@list"
                },
                "conditionals": {
                    "@id": "reproterms:conditionals",
                    "@container": "@list"
                },
                "reports": {
                    "@id": "reproterms:reports",
                    "@container": "@list"
                },
                "reportConfigs": {
                    "@id": "reproterms:reportConfigs",
                    "@container": "@list"
                },
                "reportIncludeItem": {
                    "@id": "reproterms:reportIncludeItem"
                },
                "shuffle": {
                    "@id": "reproterms:shuffle",
                    "@type": "schema:Boolean",
                    "@nest": "ui"
                },
                "activity_display_name": {
                    "@id": "reproterms:activity_display_name",
                    "@type": "schema:alternateName",
                    "@nest": "ui"
                },
                "displayNameMap": {
                    "@id": "reproterms:displayNameMap",
                    "@type": "schema:alternateName",
                    "@nest": "ui"
                },
                "inputOptions": {
                    "@id": "reproterms:inputs",
                    "@container": "@index",
                    "@nest": "ui"
                },
                "inputType": {
                    "@id": "reproterms:inputType",
                    "@type": "xsd:string",
                    "@nest": "ui"
                },
                "readOnly": {
                    "@id": "reproterms:readOnly",
                    "@type": "xsd:boolean",
                    "@nest": "ui"
                },
                "headerLevel": {
                    "@id": "reproterms:headerLevel",
                    "@type": "xsd:int",
                    "@nest": "ui"
                },
                "headers": {
                    "@id": "reproterms:tableheaders",
                    "@container": "@list",
                    "@nest": "ui"
                },
                "rows": {
                    "@id": "reproterms:tablerows",
                    "@container": "@list",
                    "@type": "@vocab",
                    "@nest": "ui"
                },
                "scoringLogic": {
                    "@id": "reproterms:scoringLogic",
                    "@container": "@index"
                },
                "scoring_logic": {
                    "@id": "reproterms:scoring_logic",
                    "@container": "@index"
                },
                "outputType": {
                    "@id": "reproterms:outputType",
                    "@container": "@language"
                },
                "subScales": {
                    "@id": "reproterms:subScales",
                    "@container": "@index"
                },
                "finalSubScale": {
                    "@id": "reproterms:finalSubScale",
                    "@container": "@index"
                },
                "isAverageScore": {
                    "@id": "reproterms:isAverageScore",
                    "@type": "schema:Boolean"
                },
                "isRecommended": {
                    "@id": "reproterms:isRecommended",
                    "@type": "schema:Boolean"
                },
                "lookupTable": {
                    "@id": "reproterms:lookupTable",
                    "@container": "@index"
                },
                "tScore": "reproterms:tScore",
                "rawScore": "reproterms:rawScore",
                "age": "reproterms:age",
                "sex": "reproterms:sex",
                "outputText": "reproterms:outputText",
                "allowEdit": {
                    "@id": "reproterms:allowEdit",
                    "@type": "schema:Boolean"
                },
                "isResponseIdentifier": {
                    "@id": "reproterms:isResponseIdentifier",
                    "@type": "schema:Boolean"
                },
                "hasResponseIdentifier": {
                    "@id": "reproterms:hasResponseIdentifier",
                    "@type": "schema:Boolean"
                },
                "compute": {
                    "@id": "reproterms:compute",
                    "@container": "@index"
                },
                "messages": {
                    "@id": "reproterms:messages",
                    "@container": "@index"
                },
                "message": {
                    "@id": "reproterms:message"
                },
                "jsExpression": {
                    "@id": "reproterms:jsExpression"
                },
                "scoreOverview": {
                    "@id": "reproterms:scoreOverview",
                    "@container": "@language"
                },
                "direction": {
                    "@id": "reproterms:direction",
                    "@type": "schema:Boolean"
                },
                "visibility": {
                    "@id": "reproterms:visibility",
                    "@container": "@index",
                    "@nest": "ui"
                },
                "vis": {
                    "@id": "reproterms:vis",
                    "@container": "@index",
                    "@nest": "ui"
                },
                "isVis": {
                    "@id": "reproterms:isVis"
                },
                "required": {
                    "@id": "reproterms:required",
                    "@container": "@index",
                    "@nest": "ui"
                },
                "variableMap": {
                    "@id": "reproterms:variableMap",
                    "@container": "@index"
                },
                "variableName": "reproterms:variableName",
                "alternateName": {
                    "@id": "schema:alternateName",
                    "@container": "@language"
                },
                "isAbout": {
                    "@id": "reproterms:isAbout",
                    "@type": "@vocab"
                },
                "allow": {
                    "@id": "reproterms:allow",
                    "@container": "@list",
                    "@type": "@vocab",
                    "@nest": "ui"
                },
                "addAllow": {
                    "@id": "reproterms:addAllow",
                    "@container": "@index",
                    "@nest": "ui"
                },
                "skipped": "reproterms:refused_to_answer",
                "dontKnow": "reproterms:dont_know_answer",
                "timedOut": "reproterms:timed_out",
                "fullScreen": "reproterms:full_screen",
                "autoAdvance": "reproterms:auto_advance",
                "disableBack": "reproterms:disable_back",
                "disableSummary": "reproterms:disable_summary",
                "allowExport": "reproterms:allow_export",
                "media": "reproterms:media",
                "timer": {
                    "@id": "reproterms:timer",
                    "@type": "@id",
                    "@nest": "ui"
                },
                "delay": {
                    "@id": "reproterms:delay",
                    "@type": "@id",
                    "@nest": "ui"
                },
                "method": "schema:httpMethod",
                "url": "schema:url",
                "payload": "reproterms:payload",
                "importedFrom": {
                    "@id": "pav:importedFrom",
                    "@type": "@id"
                },
                "importedBy": {
                    "@id": "pav:importedBy",
                    "@type": "@id"
                },
                "createdWith": {
                    "@id": "pav:createdWith",
                    "@type": "@id"
                },
                "createdBy": {
                    "@id": "pav:createdBy",
                    "@type": "@id"
                },
                "createdOn": {
                    "@id": "pav:createdOn",
                    "@type": "@id"
                },
                "previousVersion": {
                    "@id": "pav:previousVersion",
                    "@type": "@id"
                },
                "lastUpdateOn": {
                    "@id": "pav:lastUpdateOn",
                    "@type": "@id"
                },
                "derivedFrom": {
                    "@id": "pav:derivedFrom",
                    "@type": "@id"
                },
                "price": {
                    "@id": "schema:price",
                    "@container": "@language"
                },
                "schema:price": {
                    "@container": "@language"
                },
                "flagScore": {
                    "@id": "reproterms:flagScore",
                    "@type": "schema:Boolean"
                },
                "isPrize": {
                    "@id": "reproterms:isPrize",
                    "@type": "schema:Boolean"
                },
                "enableNegativeTokens": {
                    "@id": "reproterms:enableNegativeTokens",
                    "@type": "schema:Boolean"
                },
                "isOptionalText": {
                    "@id": "reproterms:isOptionalText",
                    "@type": "schema:Boolean"
                },
                "isOptionalTextRequired": {
                    "@id": "reproterms:isOptionalTextRequired",
                    "@type": "schema:Boolean"
                },
                "baseAppletId": {
                    "@id": "reproterms:baseAppletId",
                    "@type": "@id"
                },
                "baseActivityId": {
                    "@id": "reproterms:baseActivityId",
                    "@type": "@id"
                },
                "baseItemId": {
                    "@id": "reproterms:baseItemId",
                    "@type": "@id"
                },
                "nextActivity": {
                    "@id": "reproterms:nextActivity"
                },
                "hideActivity": {
                    "@id": "reproterms:hideActivity",
                    "@type": "schema:Boolean"
                }
            }
        }, data)

        prefName = FolderModel().preferredName(expanded)
        docCollection = jsonld_expander.getModelCollection('activityFlow')
        docFolder = FolderModel().createFolder(
            name=prefName,
            parent=docCollection,
            parentType='collection',
            public=True,
            creator=None,
            allowRename=True,
            reuseExisting=False
        )

        newModel = FolderModel().setMetadata(
            docFolder,
            {
                **docFolder.get('meta', {}),
                'modelType': 'activityFlow',
                'identifier': docFolder['_id'],
                'protocolId': ObjectId(protocolId),
                'schema': '1.0.1',
                'activityFlow': expanded
            }
        )

        flowOrder.append({
            '@id': newModel['_id']
        })
        flowProperties.append({
            'reprolib:terms/isVis': [ { '@value': True }],
            'reprolib:terms/variablename': [ { '@value': name, '@language': 'en' } ],
            'http://www.w3.org/2004/02/skos/core#prefLabel': [ { '@value': name, '@language': 'en' } ]
        })

    def getFlows(path, current, badge):
        hasNext = False
        for edge in g[current]:
            if (not 'index' in edge) or edge['index'] in path:
                continue

            hasNext = True

            path.append(edge['index'])
            getFlows(path, edge['index'], badge or edge['badge'])
            path.pop()

            marked[edge['index']] = True

        if not hasNext and len(path) > 1:
            createActivityFlow(path, badge)

    for i in range(0, len(g)):
        if not marked[i]:
            getFlows([i], i, False)
            marked[i] = True

    protocol = FolderModel().findOne({ '_id': ObjectId(protocolId) })
    protocol['meta']['protocol']['reprolib:terms/activityFlowOrder'] = [ {'@list': [
        {'@id': str(order['@id'])} for order in flowOrder
    ]}]

    protocol['meta']['protocol']['reprolib:terms/activityFlowProperties'] = flowProperties
    FolderModel().setMetadata(protocol, protocol['meta'])

    applet['meta']['protocol']['activityFlows'] = [ order['@id'] for order in flowOrder ]
    FolderModel().setMetadata(applet, applet['meta'])

    profileModel = Profile()
    profiles = profileModel.find({ 'appletId': applet['_id'], 'profile': True })
    for profile in profiles:
        profile['activity_flows'] = [
            {
                'activity_flow_id': order['@id'],
                'completed_time': None,
                'last_activity': None
            } for order in flowOrder
        ]

        profileModel.update(query={
            '_id': profile['_id']
        }, update={
            '$set': {
                'activity_flows': profile['activity_flows']
            }
        })

    jsonld_expander.formatLdObject(applet, 'applet', None, refreshCache=True, reimportFromUrl=False)
    print('completed', applet['_id'])
