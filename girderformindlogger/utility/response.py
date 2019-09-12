import isodate
import itertools
import pandas as pd
import tzlocal
from backports.datetime_fromisoformat import MonkeyPatch
from bson.codec_options import CodecOptions
# from bson.objectid import ObjectId
from datetime import datetime, timedelta
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
    thisResponseTime = datetime.fromtimestamp(
        metadata["responseCompleted"]/1000
    ) if "responseCompleted" in metadata else datetime.now(
        tzlocal.get_localzone()
    )
    print(thisResponseTime)
    startDate = delocalize(startDate) if startDate is not None else None
    endDate = delocalize(thisResponseTime if endDate is None else endDate)
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
        fields=["baseParentId", "created", "meta"],
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
    # TODO write this fxn, return `allToDate` format (https://github.com/ChildMindInstitute/MATTER-spec-docs/blob/response-format/active/MindLogger/MindLogger-app-backend/response_format.md)
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
    # df = df[responseIRIs].melt()
    # df['value'] = df['value'].astype(str)
    # print(df.groupby(['variable', 'value']).count())
    # return({
    #     "value": ,
    #     "count":
    # })
    #
    # print(df.head())
    # print(df.groupBy(''))
    # return(df)
    # counts = {}
    # for responseItem in definedRange:
    #     for responseIRI in definedRange:
    #         pass
    #     responseIRI: [
    #         {
    #             "value": definedRange[i].get("responses")[responseIRI],
    #             "count":
    #         } for i in len(definedRange)
    #     ] for responseIRI in definedRange[0].get("responses").keys()
    # }
    # return(counts)


def delocalize(dt):
    try:
        return(datetime.fromisoformat((dt).isoformat()).astimezone(utc))
    except:
        print(dt)
        print(type(dt))
        raise ValueError(dt)
        return(None)


def aggregateAndSave(item, informant):
    # TODO: finish this fxn. 0: save; 1: calculate `last7Days`; 2: save; 3: calculate `allToDate`; 4: save. (https://github.com/ChildMindInstitute/MATTER-spec-docs/blob/response-format/active/MindLogger/MindLogger-app-backend/response_format.md)
    metadata = item.get("meta", {})
    # Save 1 (of 3)
    if metadata:
        item = ResponseItem().setMetadata(item, metadata)
    # sevenDay ...
    print("From {} to {}".format(
        ((datetime.fromtimestamp(
            metadata["responseCompleted"]/1000
        ) if "responseCompleted" in metadata else datetime.now(
            tzlocal.get_localzone()
        )) - timedelta(days=7)).strftime("%c"),
        datetime.now(
            tzlocal.get_localzone()
        ).strftime("%c")
    ))
    metadata["last7Days"] = aggregate(
        metadata,
        informant,
        startDate=((datetime.fromtimestamp(
            metadata["responseCompleted"]/1000
        ) if "responseCompleted" in metadata else datetime.now(
            tzlocal.get_localzone()
        )) - timedelta(days=7)),
        getAll=True
    )
    # save
    if metadata:
        item = ResponseItem().setMetadata(item, metadata)
    # allTime
    metadata["allTime"] = aggregate(
        metadata,
        informant,
        getAll=False
    )
    # save again
    if metadata:
        item = ResponseItem().setMetadata(item, metadata)
    return(item)
