import backports
import isodate
import itertools
import pandas as pd
import pytz
import tzlocal
from backports.datetime_fromisoformat import MonkeyPatch
from bson.codec_options import CodecOptions
from bson.objectid import ObjectId
from datetime import date, datetime, timedelta
from girderformindlogger.models.applet import Applet as AppletModel
from girderformindlogger.models.user import User as UserModel
from girderformindlogger.models.response_folder import ResponseItem
from girderformindlogger.models.response_tokens import ResponseTokens
from girderformindlogger.models.account_profile import AccountProfile
from girderformindlogger.utility import clean_empty
from pandas.api.types import is_numeric_dtype
from pymongo import ASCENDING, DESCENDING
from bson import json_util
from girderformindlogger.utility import jsonld_expander
from girderformindlogger.models.protocol import Protocol

MonkeyPatch.patch_fromisoformat()

def getSchedule(currentUser, timezone=None):
    from girderformindlogger.models.profile import Profile

    schedule = {}

    accounts = AccountProfile().getAccounts(currentUser['_id'])
    applets = []

    for account in accounts:
        for applet in account.get('applets', {}).get('user', []):
            applets.append(applet)

    for appletId in applets:
        profile = Profile().findOne({'appletId': appletId, 'userId': currentUser['_id']})
        activities = profile['completed_activities']

        appletSchedule = {}
        for activity in activities:
            appletSchedule['activity/{}'.format(activity['activity_id'])] = {
                'lastResponse': None if not activity['completed_time'] else activity['completed_time'].astimezone(pytz.timezone(timezone)).isoformat() if (
                        isinstance(timezone, str) and timezone in pytz.all_timezones
                    ) else activity['completed_time'].isoformat() #,
                # 'nextScheduled': None,
                # 'lastScheduled': None
            }
        schedule['applet/{}'.format(appletId)] = appletSchedule

    return schedule

def getLatestResponse(informantId, appletId, activityID):
    from .jsonld_expander import reprolibCanonize, reprolibPrefix
    responses = list(ResponseItem().find(
        query={
            "baseParentType": 'user',
            "baseParentId": informantId if isinstance(
                informantId,
                ObjectId
            ) else ObjectId(informantId),
            "meta.applet.@id": {
                "$in": [
                    appletId,
                    ObjectId(appletId)
                ]
            },
            "meta.activity.@id": {
                "$in": [
                    activityID,
                    ObjectId(activityID)
                ]
            }
        },
        force=True,
        sort=[("created", DESCENDING)]
    ))
    if len(responses):
        return(responses[0])
    return(None)


def getLatestResponseTime(informantId, appletId, activityID, tz=None):
    latestResponse = getLatestResponse(informantId, appletId, activityID)
    try:
        latestResponse['created'].isoformat(
        ) if tz is None else latestResponse['created'].astimezone(pytz.timezone(
            tz
        )).isoformat()
    except TypeError:
        pass
    except:
        import sys, traceback
        print(sys.exc_info())
        print(traceback.print_tb(sys.exc_info()[2]))
    return(
        (
            latestResponse['created'].astimezone(pytz.timezone(
                tz
            )).isoformat() if (
                isinstance(tz, str) and tz in pytz.all_timezones
            ) else latestResponse['created'].isoformat()
        ) if (
            isinstance(latestResponse, dict) and isinstance(
                latestResponse.get('created'),
                datetime
            )
        ) else None
    )


def aggregate(metadata, informant, startDate=None, endDate=None):
    """
    Function to calculate aggregates
    """
    query = {
            "baseParentType": 'user',
            "baseParentId": informant.get("_id") if isinstance(
                informant,
                dict
            ) else informant,
            "created": {
                "$gt": startDate,
            } if startDate else {
            },
            "meta.applet.@id": metadata["applet_id"],
            "meta.subject.@id": metadata["subject_id"]
        }

    definedRange = list(ResponseItem().find(
        query=query,
        force=True,
        sort=[("created", ASCENDING)]
    ))

    if not len(definedRange):
        print('\n\n defined range returns an empty list.')
        return {}

    startDate = min([response.get(
        'created',
    ) for response in definedRange])

    endDate = max([response.get(
        'created'
    ) for response in definedRange])

    duration = isodate.duration_isoformat(
        delocalize(endDate) - delocalize(startDate)
    )

    responseIRIs = _responseIRIs(definedRange)

    aggregated = {
        "schema:startDate": startDate,
        "schema:endDate": endDate,
        "schema:duration": duration,
        "responses": {
            itemIRI: [
                {
                    "value": response.get('meta', {}).get('responses', {}).get(
                        itemIRI
                    ),
                    "date": completedDate(response),
                    "version": response.get('meta', {}).get('applet', {}).get('version', '0.0.0')
                } for response in definedRange if itemIRI in response.get(
                    'meta',
                    {}
                ).get('responses', {})
            ] for itemIRI in responseIRIs
        }
    }

    aggregated['dataSources'] = {}
    for response in definedRange:
        if 'dataSource' in response.get('meta', {}):
            aggregated['dataSources'][str(response['_id'])] = response['meta']['dataSource']

    return(aggregated)


def completedDate(response):
    completed = response.get("created", {})
    return completed


def formatResponse(response):
    try:
        metadata = response.get('meta', response)

        thisResponse = {
            "thisResponse": {
                "schema:startDate": isodatetime(
                    metadata.get(
                        'responseStarted',
                        response.get(
                            'created',
                            datetime.now()
                        )
                    )
                ),
                "schema:endDate": isodatetime(
                    metadata.get(
                        'responseCompleted',
                        response.get(
                            'created',
                            datetime.now()
                        )
                    )
                ),
                "responses": {
                    itemURI: metadata['responses'][
                        itemURI
                    ] for itemURI in metadata.get('responses', {})
                }
            },
        } if isinstance(metadata, dict) and all([
            key in metadata.keys() for key in [
                'responses',
                'applet',
                'activity',
                'subject'
            ]
        ]) else {}
    except Exception as e:
        import sys, traceback
        print(sys.exc_info())
        print(traceback.print_tb(sys.exc_info()[2]))
        thisResponse = None
    return(clean_empty(thisResponse))


def string_or_ObjectID(s):
    return([str(s), ObjectId(s)])


def _responseIRIs(definedRange):
    return(list(set(itertools.chain.from_iterable([list(
        response.get('meta', {}).get('responses', {}).keys()
    ) for response in definedRange if isinstance(response, dict)]))))


def _flattenDF(df, columnName):
    if isinstance(columnName, list):
        for c in columnName:
            df = _flattenDF(df, c)
        return(df)
    prefix = columnName if columnName not in ['meta', 'responses'] else ""
    newDf = pd.concat(
        [
            df[columnName].apply(
                pd.Series
            ),
            df.drop(columnName, axis=1)
        ],
        axis=1
    )
    return(
        (
            newDf.rename(
                {
                    col: "{}-{}".format(
                        prefix,
                        col
                    ) for col in list(
                        df[columnName][0].keys()
                    )
                },
                axis='columns'
            ) if len(prefix) else newDf
        ).dropna('columns', 'all')
    )


def delocalize(dt):
    print("delocalizing {} ({}; {})".format(
        dt,
        type(dt),
        dt.tzinfo if isinstance(dt, datetime) else ""
    ))
    if isinstance(dt, datetime):
        if dt.tzinfo is None:
            return(dt)
        print(dt.astimezone(pytz.utc).replace(
            tzinfo=None
        ))
        return(dt.astimezone(pytz.utc).replace(
            tzinfo=None
        ))
    elif isinstance(dt, str):
        return(datetime.fromisoformat(dt).astimezone(pytz.utc).replace(
            tzinfo=None
        ))
    print("Here's the problem: {}".format(dt))
    raise TypeError

def last7Days(
    appletId,
    appletInfo,
    informantId,
    reviewer,
    subject=None,
    startDate=None,
    includeOldItems=True,
    groupByDateActivity=True,
    localItems=[],
    localActivities=[]
):
    from girderformindlogger.models.profile import Profile

    referenceDate = datetime.combine(
        datetime.utcnow().date() + timedelta(days=1), datetime.min.time()
    )

    try:
        startDate = datetime.fromisoformat(startDate)
    except:
        startDate = None

    if startDate:
        startDate = delocalize(startDate)

    weekBefore = delocalize(referenceDate - timedelta(days=8))

    startDate = weekBefore if not startDate or startDate < weekBefore else startDate

    profile = Profile().findOne({'userId': ObjectId(informantId), 'appletId': ObjectId(appletId)})

    responses = aggregate({
        'applet_id': profile['appletId'],
        'subject_id': profile['_id']
    }, informantId, startDate, referenceDate)

    # destructure the responses
    # TODO: we are assuming here that activities don't share items.
    # might not be the case later on, so watch out.

    outputResponses = responses.get('responses', {})
    dataSources = responses.get('dataSources', {})

    for item in outputResponses:
        for resp in outputResponses[item]:
            resp['date'] = delocalize(resp['date'])
            if not groupByDateActivity:
                resp['date'] = determine_date(resp['date'] + timedelta(hours=profile['timezone']))

    l7d = {}
    l7d['tokens'] = ResponseTokens().getResponseTokens(profile, startDate, False)
    l7d["responses"] = _oneResponsePerDatePerVersion(outputResponses, profile['timezone']) if groupByDateActivity else outputResponses

    l7d["schema:endDate"] = responses.get("schema:endDate", datetime.utcnow()).isoformat()
    l7d["schema:startDate"] = startDate.isoformat()
    l7d["schema:duration"] = responses.get("schema:duration", isodate.duration_isoformat(
        referenceDate - startDate
    ))

    l7d['dataSources'] = {}
    for itemResponses in dict.values(l7d["responses"]):
        for response in itemResponses:
            sourceId = str(response['value']['src']) if isinstance(response['value'], dict) and 'src' in response['value'] else None
            if sourceId and sourceId not in l7d['dataSources']:
                l7d['dataSources'][sourceId] = dataSources[sourceId]

    l7d.update(getOldVersions(l7d['responses'], appletInfo))

    for itemId in list(l7d.get('items', {}).keys()):
        if itemId in localItems:
            l7d['items'].pop(itemId)

    for activityId in list(l7d.get('activities', {}).keys()):
        if activityId in localActivities:
            l7d['activities'].pop(activityId)

    return l7d

def getOldVersions(responses, applet):
    IRIs = {}
    insertedIRI = {}
    for IRI in responses:
        IRIs[IRI] = []
        for response in responses[IRI]:
            if 'version' not in response:
                continue

            identifier = '{}/{}'.format(IRI, response['version'])
            if identifier not in insertedIRI:
                IRIs[IRI].append(response['version'])
                insertedIRI[identifier] = True

    return Protocol().getHistoryDataFromItemIRIs(applet.get('meta', {}).get('protocol', {}).get('_id', '').split('/')[-1], IRIs)

def determine_date(d):
    if isinstance(d, int):
        while (d > 10000000000):
            d = d/10
        d = datetime.fromtimestamp(d)
    return((
        datetime.fromisoformat(
            d
        ) if isinstance(d, str) else d
    ).date())

def convertToComparableVersion(version):
    values = version.split('.')
    for i in range(0, len(values)):
        values[i] = '0' * (20 - len(values[i])) + values[i]

    return '.'.join(values)

def isodatetime(d):
    if isinstance(d, int):
        while (d > 10000000000):
            d = d/10
        d = datetime.fromtimestamp(d)
    return((
        datetime.fromisoformat(
            d
        ) if isinstance(d, str) else d
    ).isoformat())


def responseDateList(appletId, userId, reviewer):
    from girderformindlogger.models.profile import Profile
    userId = ProfileModel().getProfile(userId, reviewer)
    if not isinstance(userId, dict):
        return([])
    userId = userId.get('userId')
    rdl = list(set([
        determine_date(
            response.get("meta", {}).get(
                "responseCompleted",
                response.get("created")
            )
        ).isoformat() for response in list(ResponseItem().find(
            query={
                "baseParentType": 'user',
                "baseParentId": userId,
                "meta.applet.@id": appletId
            },
            sort=[("created", DESCENDING)]
        ))
    ]))
    rdl.sort(reverse=True)
    return(rdl)

def add_latest_daily_response(data, responses, tokens):
    user_keys = {}

    for response in responses:
        activity_id = str(response['meta']['activity']['@id'])

        date = response['meta'].get('subject', {}).get('userTime').isoformat()
        version = response['meta'].get('applet', {}).get('version', '0.0.0')
        key_dump = json_util.dumps(response['meta']['userPublicKey'])

        for item in response['meta']['responses']:
            if item not in data['responses']:
                data['responses'][item] = []

            data['responses'][item].append({
                "date": date,
                "value": response['meta']['responses'][item],
                "version": version,
            })

            if str(response['_id']) not in data['dataSources'] and 'dataSource' in response['meta']:
                if key_dump not in user_keys:
                    user_keys[key_dump] = len(data['keys'])
                    data['keys'].append(response['meta']['userPublicKey'])

                data['dataSources'][str(response['_id'])] = {
                    'key': user_keys[key_dump],
                    'data': response['meta']['dataSource']
                }

        activityId = response['meta'].get('activity', {}).get('@id', None)

        if not activityId:
            continue
        activityId = str(activityId)

        if 'subScales' not in response['meta']:
            continue

        for subScale in response['meta']['subScales']:
            if activityId not in data['subScales']:
                data['subScales'][activityId] = {}

            if subScale not in data['subScales'][activityId]:
                data['subScales'][activityId][subScale] = []

            data['subScales'][activityId][subScale].append({
                "date": date,
                "value": response['meta']['subScales'][subScale],
                "version": version,
            })

            if str(response['_id']) not in data['subScaleSources'] and 'subScaleSource' in response['meta']:
                data['subScaleSources'][str(response['_id'])] = {
                    'key': user_keys[key_dump],
                    'data': response['meta']['subScaleSource']
                }

    for tokenField in ['cumulativeToken', 'tokenUpdates']:
        if isinstance(tokens[tokenField], dict):
            tokens[tokenField] = [tokens[tokenField]]

        if not tokens[tokenField]:
            continue

        for value in tokens[tokenField]:
            key_dump = json_util.dumps(value['userPublicKey'])

            if key_dump not in user_keys:
                user_keys[key_dump] = len(data['keys'])
                data['keys'].append(value['userPublicKey'])

            value['key'] = user_keys[key_dump]
            value.pop('userPublicKey')

            data['tokens'][tokenField].append(value)


def _oneResponsePerDatePerVersion(responses, offset):
    newResponses = {}
    for response in responses:
   
        df = pd.DataFrame(responses[response])

        df["datetime"] = df.date
    
        df["date"] = df.date + timedelta(hours=offset)
        df["date"] = df.date.apply(determine_date)
        df["versionValue"] = df.version.apply(convertToComparableVersion)

        df.sort_values(by=['datetime', 'versionValue'], ascending=False, inplace=True)
        df = df.groupby(['date', 'versionValue']).first()

        df.drop('datetime', axis=1, inplace=True)

        df['date'] = df.index
        df['date'] = df.date.apply(lambda data: data[0])

        newResponses[response] = df.to_dict(orient="records")

    return(newResponses)
