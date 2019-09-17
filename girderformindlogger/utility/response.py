import isodate
import itertools
import pandas as pd
import tzlocal
from backports.datetime_fromisoformat import MonkeyPatch
from bson.codec_options import CodecOptions
# from bson.objectid import ObjectId
from datetime import date, datetime, timedelta
from girderformindlogger.models.response_folder import ResponseItem
from pandas.api.types import is_numeric_dtype
from pymongo import ASCENDING, DESCENDING
from pytz import utc
MonkeyPatch.patch_fromisoformat()


def aggregate(metadata, informant, startDate=None, endDate=None, getAll=False):
    """
    Function to calculate aggregates
    """
    responses = metadata.get("responses")
    startDate = delocalize(startDate) if startDate is not None else None
    endDate = delocalize(datetime.fromtimestamp(
        metadata["responseCompleted"]/1000
    ) if "responseCompleted" in metadata else datetime.now(
        tzlocal.get_localzone()
    ) if endDate is None else endDate)
    # print({
    #     "baseParentType": 'user',
    #     "baseParentId": informant.get("_id"),
    #     "created": {
    #         "$gte": startDate,
    #         "$lt": endDate
    #     } if startDate else {
    #         "$lt": endDate
    #     },
    #     "meta.applet.@id": metadata.get("applet", {}).get("@id"),
    #     "meta.activity.@id": metadata.get("activity", {}).get("@id"),
    #     "meta.subject.@id": metadata.get("subject", {}).get("@id")
    # })
    definedRange = list(ResponseItem().find(
        query={
            "baseParentType": 'user',
            "baseParentId": informant.get("_id"),
            "created": {
                "$gte": startDate,
                "$lt": endDate
            } if startDate else {
                "$lt": endDate
            },
            "meta.applet.@id": metadata.get("applet", {}).get("@id"),
            "meta.activity.@id": metadata.get("activity", {}).get("@id"),
            "meta.subject.@id": metadata.get("subject", {}).get("@id")
        },
        force=True,
        sort=[("created", ASCENDING)],
        options=CodecOptions(tz_aware=True)
    ))
    startDate = delocalize(min([
        response.get('created') for response in definedRange
    ])) if (
        startDate is None and len(definedRange)
    ) else startDate
    duration = isodate.duration_isoformat(
        endDate - startDate if startDate is not None else 0
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
                    "date": completedDate(response)
                } for response in definedRange if itemIRI in response.get(
                    'meta',
                    {}
                ).get('responses', {})
            ] for itemIRI in responseIRIs
        } if getAll else countResponseValues(definedRange, responseIRIs)
    }
    return(aggregated)


def completedDate(response):
    completed = response.get("meta", {}).get("responseCompleted")
    return (
        datetime.fromisoformat(datetime.fromtimestamp(
            (completed/1000 if completed else response.get("created"))
        ).isoformat())
    )


def _responseIRIs(definedRange):
    return(list(set(itertools.chain.from_iterable([list(
        response.get('meta', {}).get('responses').keys()
    ) for response in definedRange]))))


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


def countResponseValues(definedRange, responseIRIs=None):
    responseIRIs = _responseIRIs(
        definedRange
    ) if responseIRIs is None else responseIRIs
    pd.set_option('display.max_colwidth', -1)
    pd.set_option('display.max_columns', None)
    df = pd.DataFrame(definedRange)
    df = _flattenDF(df, ['meta', 'applet', 'activity', 'responses'])
    counts = {
        responseIRI: (
            df[responseIRI].astype(str) if not(is_numeric_dtype(
                df[responseIRI]
            )) else df[responseIRI]
        ).value_counts().to_dict() for responseIRI in responseIRIs
    }
    return(
        {
            responseIRI: [
                {
                    "value": value,
                    "count": counts[responseIRI][value]
                } for value in counts[responseIRI]
            ] for responseIRI in counts
        }
    )


def delocalize(dt):
    try:
        return(datetime.fromisoformat(dt.isoformat()).astimezone(utc).replace(
            tzinfo=None
        ))
    except:
        print(dt)
        print(type(dt))
        raise ValueError(dt)
        return(None)


def aggregateAndSave(item, informant):
    print(item)
    metadata = item.get("meta", {})
    # Save 1 (of 3)
    if metadata:
        item = ResponseItem().setMetadata(item, metadata)
    # sevenDay ...
    endDate = datetime.fromtimestamp(
        metadata["responseCompleted"]/1000
    ) if "responseCompleted" in metadata else datetime.now()
    startDate = endDate - timedelta(days=7)
    print("From {} to {}".format(
        startDate.strftime("%c"),
        endDate.strftime("%c")
    ))
    metadata["last7Days"] = aggregate(
        metadata,
        informant,
        startDate=startDate,
        endDate=endDate,
        getAll=True
    )
    # save (2 of 3)
    if metadata:
        item = ResponseItem().setMetadata(item, metadata)
    # allTime
    metadata["allTime"] = aggregate(
        metadata,
        informant,
        endDate=endDate,
        getAll=False
    )
    # save (3 of 3)
    if metadata:
        item = ResponseItem().setMetadata(item, metadata)
    return(item)


def last7Days(applet, reviewer, referenceDate=None):
    # TODO: Refactor to allow reviewer and informant to be different
    referenceDate = delocalize(
        datetime.now() if referenceDate is None else referenceDate # TODO allow timeless dates
    )
    print(referenceDate)
    latestResponse = list(ResponseItem().find(
        query={
            "baseParentType": 'user',
            "baseParentId": reviewer.get('_id'),
            "created": {
                "$lte": referenceDate
            },
            "meta.applet.@id": applet.get('_id')
        },
        sort=[("created", DESCENDING)]
    ))[0]
    metadata = latestResponse.get('meta', {})
    print(latestResponse)
    print(metadata)
    if "last7Days" not in metadata or "allTime" not in metadata:
        latestResponse = aggregateAndSave(latestResponse, reviewer)
    l7d = latestResponse.get('meta', {}).get('last7Days')
    l7d["responses"] = _oneResponsePerDate(l7d.get("responses", {}))
    return(l7d)


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


def responseDateList(appletId, userId, reviewer):
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


def _oneResponsePerDate(responses):
    newResponses = {}
    for response in responses:
        df = pd.DataFrame(responses[response])
        df["datetime"] = df.date
        df["date"] = df.date.apply(determine_date)
        df.sort_values(by=['datetime'], ascending=False, inplace=True)
        df = df.groupby('date').first()
        df.drop('datetime', axis=1, inplace=True)
        df['date'] = df.index
        newResponses[response] = df.to_dict(orient="records")
    return(newResponses)
