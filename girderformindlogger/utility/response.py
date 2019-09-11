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
    startDate = datetime.fromisoformat(startDate.isoformat(
    )).astimezone(utc) if startDate is not None else None
    endDate = datetime.fromisoformat((
        thisResponseTime if endDate is None else endDate
    ).isoformat()).astimezone(utc)
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
    startDate = min([
        response.created for response in definedRange
    ]) if (
        startDate is None and len(definedRange)
    ) else startDate
    # TODO: Fix duration
    duration = endDate - startDate if startDate is not None else 0
    responseIRIs = list(set(itertools.chain.from_iterable([list(
        response.get('meta', {}).get('responses').keys()
    ) for response in definedRange])))
    aggregated = {
        "schema:startDate": startDate,
        "schema:endDate": endDate,
        "schema:duration": 0,
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
        }
    } if getAll else {}
    # TODO: save the real data format (https://github.com/ChildMindInstitute/MATTER-spec-docs/blob/response-format/active/MindLogger/MindLogger-app-backend/response_format.md)
    # aggregated = {
    #     "schema:startDate": startDate if startDate else min([
    #         response.get("created") for response in definedRange
    #     ]),
    #     "schema:endDate": endDate,
    #     "schema:duration": endDate - startDate,
    #     "responses": listResponseValues(definedRange)
    #   } if getAll else {
    #     "schema:startDate": startDate if startDate else min([
    #         response.get("created") for response in definedRange
    #     ]),
    #     "schema:endDate": endDate,
    #     "schema:duration": endDate - startDate,
    #     "responses": countResponseValues(definedRange)
    #   }
    return(aggregated)

def completedDate(response):
    completed = response.get("meta", {}).get("responseCompleted")
    return (
        datetime.fromisoformat(datetime.fromtimestamp(
            (completed/1000 if completed else response.get("created"))
        ).isoformat())
    )

def countResponseValues(definedRange):
    # TODO write this fxn, return `allToDate` format (https://github.com/ChildMindInstitute/MATTER-spec-docs/blob/response-format/active/MindLogger/MindLogger-app-backend/response_format.md)
    counts = {}
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
    return(counts)

def listResponseValues(definedRange):
    # TODO: clean up this fxn, return `last7Days` format (https://github.com/ChildMindInstitute/MATTER-spec-docs/blob/response-format/active/MindLogger/MindLogger-app-backend/response_format.md)
    df = pd.DataFrame(definedRange)
    df = pd.concat([df.meta.apply(pd.Series), df.drop('meta', axis=1)], axis=1)
    responses = pd.concat([df['responses'].apply(pd.Series), df['created']], axis=1)
    print(responses.head())
    df = pd.concat([responses, df.drop('responses', axis=1)], axis=1)
    pd.set_option('display.max_colwidth', -1)
    pd.set_option('display.max_columns', None)
    print(df.head())
    return(df)
    # return(listedResponseValues)


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
    last7Days = aggregate(
        metadata,
        informant,
        startDate=((datetime.fromtimestamp(
            metadata["responseCompleted"]/1000
        ) if "responseCompleted" in metadata else datetime.now(
            tzlocal.get_localzone()
        )) - timedelta(days=7)),
        getAll=True
    )
    metadata["last7Days"] = last7Days
    # save
    if metadata:
        item = ResponseItem().setMetadata(item, metadata)
    # ResponseItem().setMetadata(newItem, metadata)
    # allTime
    # save again
    return()
