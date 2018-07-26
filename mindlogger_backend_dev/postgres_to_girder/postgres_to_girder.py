import os
import sys

sys.path.append(
    os.path.abspath(
        os.path.join(
            __file__,
            os.pardir,
            os.pardir,
            os.pardir
        )
    )
)
__package__ = ".".join([
    "mindlogger_backend_dev",
    "postgres_to_girder",
    "postgres_to_girder"
])
import girder_client as gc
import json
import numpy as np
import pandas as pd
import psycopg2
import re
import urllib
from datetime import date
from ...girder_connections import *
from ...object_manipulation import *
from ...update_schema import *
from ...update_schema import _delete_collections, _delete_users


def assingments_from_postgres(
    girder_connection,
    postgres_tables,
    context={},
    timings={
        "1d": "Daily",
        "1": "Once",
        "8h": "3×Daily",
        "12h": "2×Daily"
    }
):
    """
    Function to build user activity schedules.

    Parameters
    ----------
    girder_connection: GirderClient

    postgres_tables: DataFrame

    context: dictionary, optional

    timings: dictionary, optional

    Returns
    -------
    schedules: set
        set of Girder Item _ids
    """
    schedules = set()
    assignments = pd.merge(
        pd.merge(
            postgres_tables["user_acts"].drop(
                "id",
                axis=1
            ),
            postgres_tables["users"][
                [
                    "id",
                    "email"
                ]
            ],
            how='left',
            left_on='user_id',
            right_on='id'
        ).drop(
            "id",
            axis=1
        ),
        postgres_tables["acts"].drop(
            "user_id",
            axis=1
        ),
        how="left",
        left_on="act_id",
        right_on="id",
        suffixes=(
            "_assignment",
            "_activity"
        )
    ).drop(
        "id",
        axis=1
    ).dropna(
        axis=0,
        subset=["title"]
    )
    assignments["frequency"] = assignments.act_data.apply(
        lambda x: json.loads(x)["frequency"]
    )
    assignments = assignments.sort_values(
        [
            "email",
            "frequency"
        ]
    ).set_index(
        [
            "email",
            "frequency",
            "title"
        ]
    )
    users = set(
        assignments.index.get_level_values(
            "email"
        )
    )
    users = {
        u: get_user_id_by_email(
            girder_connection,
            u
        ) for u in users
    }
    frequencies = set(
        assignments.index.get_level_values(
            "frequency"
        )
    )
    for s in {
        (u, f) for u in users for f in frequencies
    }:
        try:
            sched_df = assignments.loc[s,]
        except KeyError:
            continue
        schedule_folder_id = girder_connection.createFolder(
            name="Schedules",
            parentId=users[s[0]],
            parentType="user",
            public=False,
            reuseExisting=True
        )["_id"]
        schedule_item_id = girder_connection.createItem(
            name=" ".join([
                "Version 0 ",
                timings[s[1]]
            ]),
            parentFolderId=schedule_folder_id,
            reuseExisting=True
        )["_id"]
        l = assignments.loc[s,]
        for title in l.index.get_level_values("title"):
            activity_name, abbreviation = get_abbreviation(
                title
            )
            add_to_schedule(
                girder_connection=girder_connection,
                frequency=s[1],
                schedules_id=None,
                context=context,
                activity_item_id=get_girder_id_by_name(
                    girder_connection,
                    "item",
                    parent=(
                        "folder",
                        get_girder_id_by_name(
                            girder_connection,
                            "folder",
                            name=get_postgres_item_version(
                                activity_name,
                                abbreviation=abbreviation
                            ),
                            parent=(
                                "collection",
                                get_girder_id_by_name(
                                    entity="collection",
                                    name="Activities",
                                    girder_connection=girder_connection
                                )
                            )
                        )
                    ),
                    name=get_postgres_item_version(
                        activity_name,
                        abbreviation=abbreviation,
                        activity_source="Version 0",
                        respondent=l.loc[
                            title,
                            "respondent"
                        ],
                        version=date.strftime(
                            l.loc[
                                title,
                                "updated_at_activity"
                            ],
                            "%F"
                        )
                    )
                ),
                schedule_folder_id=schedule_folder_id,
                schedule_item_id=schedule_item_id
            )
            schedules.add(schedule_item_id)
    return(schedules)


def connect_to_postgres(postgres_config):
    """
    Function to connect to a Girder DB.

    Parameters
    ----------
    postgres_config: dictionary
        "dbname": string
            Postgres DB name
        "user": string
            Postgres username
        "host": string
            active Postgres IP (no protocol, ie, without "https://")
        "password": string
            password for Postgres user

    Returns
    -------
    postgres_connection: connection
        http://initd.org/psycopg/docs/connection.html#connection

    Examples
    --------
    >>> config_file = os.path.join(
    ...    os.path.dirname(__file__),
    ...    os.pardir,
    ...    "config.json.template"
    ... )
    >>> connect_to_postgres(
    ...     configuration(
    ...         config_file=config_file
    ...     )[0]["postgres"]
    ... )
    I am unable to connect to the Postgres database 🐘
    """
    try:
        postgres_connection = psycopg2.connect(
            " ".join(
                [
                    "=".join([
                        key,
                        postgres_config[
                            key
                        ]
                    ]) for key in postgres_config
                ]
            )
        )
        print("Connected to the Postgres database 🐘") # pragma: no cover
        return(postgres_connection) # pragma: no cover
    except (
        psycopg2.OperationalError,
        psycopg2.DatabaseError
    ):
        print(
            "I am unable to connect to the "
            "Postgres database 🐘"
        )
        return(None)


def get_abbreviation(activity):
    """
    Function to extract abbreviation from
    activity name if one is present

    Parameters
    ----------
    activity: string

    Returns
    -------
    activity_name: string

    abbreviation: string

    Examples
    --------
    >>> get_abbreviation(
    ...     "Corresponding parts of congruent "
    ...     "triangles are congruent (CPCTC)"
    ... )[1]
    'CPCTC'
    """
    abbreviation = None
    if "(" in activity:
        anames = [
            a.strip(
                ")"
            ).strip() for a in activity.split(
                "("
            )
        ]
        if (
            len(anames)==2
        ):
            if (
                len(anames[0])>len(anames[1])
            ):
                abbreviation = anames[1]
                activity_name = anames[0]
            else:
                abbreviation = anames[0]
                activity_name = anames[1]
        else: # pragma: no cover
            print(anames) # pragma: no cover
    activity_name = activity if not abbreviation else activity_name
    return(
        activity_name,
        abbreviation
    )


def get_postgres_item_version(
    activity_name,
    abbreviation=None,
    activity_source=None,
    respondent=None,
    version=None
):
    """
    Function to create an item version in `Mindlogger Item <https://github.com/ChildMindInstitute/mindlogger-app-backend/wiki/Data-Dictionary#activitiesfolderitem>`_ format:
    `[Source] — [Activity] — [Respondent] Report ([Version])`.

    Parameters
    ----------
    activity_name: string

    abbreviation: string

    activity_source: string

    respondent: string

    version: string

    Returns
    -------
    item_version: string

    Examples
    --------
    >>> activity_name, abbreviation = get_abbreviation(
    ...     "EHQ (Edinburgh Handedness Questionnaire)"
    ... )
    >>> get_postgres_item_version(
    ...     activity_name=activity_name,
    ...     abbreviation=abbreviation,
    ...     activity_source="MATTER Lab",
    ...     respondent="Coworker",
    ...     version="v0.1"
    ... )
    'MATTER Lab ― Edinburgh Handedness Questionnaire (EHQ) ― Coworker Report (v0.1)'
    """
    return(
        "{0}{1}{2}".format(
            "".join([
                activity_source,
                " ― "
            ]) if activity_source else "", # {0}
            "{0}{1}{2}".format(
                activity_name,
                " ({0})".format(
                    abbreviation
                ) if abbreviation else "",
                " ― {0} Report".format(
                        respondent
                    ) if respondent else ""
            ).strip(" "), # {1}
            " ({0})".format(
                version
            ) if version else "" #{2}
        )
    )


def postgres_activities_to_girder_activities(
    acts,
    gc,
    users,
    users_by_email,
    context
):
    """
    Function to transfer users from Postgres table to
    Girder collection.

    Parameters
    ----------
    acts: DataFrame
        activities table from Postgres DB

    gc: GirderClient
        active GirderClient in which to add the users

    users: DataFrame
        users table from Postgres DB

    users_by_email: dictionary
        key: string
            email address
        value: string
            Girder User_id

    context: dictionary
        JSON-LD context

    Returns
    -------
    activities: DataFrame
    """
    activities = {} # pragma: no cover
    activities_id = get_girder_id_by_name(
        entity="collection",
        name="Activities",
        girder_connection=gc
    )
    schedules_id = get_girder_id_by_name(
        entity="collection",
        name="Schedules",
        girder_connection=gc
    )
    for i in range(acts.shape[0]):
        activity = acts.loc[i, "title"]
        activity_name, abbreviation = get_abbreviation(
            activity
        )
        respondent = acts.loc[i ,"respondent"]
        item_version = get_postgres_item_version(
            activity_name,
            abbreviation,
            activity_source="Version 0",
            respondent=respondent,
            version=date.strftime(
                acts.loc[
                    i,
                    "updated_at"
                ],
                "%F"
            )
        )
        user = {
            "@id": "".join([
                "user/",
                users_by_email[
                    users[
                        users["id"]==acts.loc[
                            i,
                            "user_id"
                        ]
                    ]["email"].values[0]
                ]
            ])
        }
        act_data = json.loads(
            acts.loc[
                i,
                "act_data"
            ]
        )

        # Create or locate top-level folder and return _id
        activity_folder_id = gc.createFolder(
            name=get_postgres_item_version(
                activity_name,
                abbreviation=abbreviation
            ),
            parentId=activities_id,
            parentType="collection",
            public=False,
            reuseExisting=True
        )["_id"]
        # Define metadata
        metadata = {
            **context,
            "schema:name": {
                "@value": activity_name,
                "@language": "en-US"
            },
            "abbreviation": abbreviation if abbreviation else None,
            "status": acts.loc[
                i,
                "status"
            ],
            "accordion": act_data["accordion"] if (
                "accordion" in act_data and
                act_data["accordion"]==True
            ) else False,
            "pav:lastUpdatedOn": acts.loc[
                i,
                "updated_at"
            ].isoformat(),
            **{
                prop: act_data[prop] for prop in
                act_data if prop not in [
                    "questions",
                    "instruction",
                    "image_url",
                    "frequency",
                    "mode",
                    "type",
                    "answers"
                ]
            },
            "oslc:modifiedBy": [
                user
            ],
            "pav:createdBy": user,
            "respondent": respondent if respondent else None,
            "screens": [
                    {
                        "@id": "item/{0}".format(
                            screen
                        )
                    } for screen in postgres_questions_to_girder_screens(
                        gc,
                        act_data["questions"],
                        abbreviation if abbreviation else activity_name,
                        " ".join([
                            word for word in [
                                acts.loc[
                                    i,
                                    "type"
                                ],
                                act_data[
                                    "mode"
                                ] if "mode" in act_data else None
                            ] if word is not None
                        ]),
                        item_version,
                        context
                    )
                ] if "questions" in act_data else [
                    {
                        "@id": "item/{0}".format(
                            screen
                        )
                    } for screen in postgres_questions_to_girder_screens(
                            gc,
                            [{
                                **act_data,
                                "type": acts.loc[
                                    i,
                                    "type"
                                ] if "type" in list(acts.loc[i].index) else acts.loc[
                                    i,
                                    "mode"
                                ]
                            }],
                            abbreviation if abbreviation else activity_name,
                            " ".join([
                                word for word in [
                                    acts.loc[
                                        i,
                                        "type"
                                    ],
                                    act_data[
                                        "mode"
                                    ] if "mode" in act_data else None
                                ] if word is not None
                            ]),
                            item_version,
                            context
                        )
                ]
        }

        # Create or locate Item
        activity_item_id = gc.createItem(
            name=item_version,
            parentFolderId=activity_folder_id,
            reuseExisting=True,
            metadata=drop_empty_keys(
                metadata
            )
        )["_id"]

        ids = upload_applicable_files(
            gc,
            act_data,
            activity_item_id,
            activity_name
        )

        activities[
            activity_item_id
        ] = {
            "name": activity_name,
            "abbreviation": abbreviation if (
                abbreviation
            ) else None,
            "files": ids,
            "metadata": drop_empty_keys(
                metadata
            )
        }

        # Add to Schedule
        add_to_schedule(
            gc,
            act_data["frequency"],
            schedules_id,
            activity_item_id,
            context
        )
    return(pd.DataFrame(activities).T)


def postgres_answers_to_girder_answers(
    girder_connection,
    postgres_tables,
    context
):
    """
    Function to port User responses from Postgres
    to Girder

    Parameters
    ----------
    girder_connection: GirderClient

    postgres_tables: DataFrame

    context: dictionary

    Returns
    -------
    response_folder_ids: set
    """
    answers = pd.merge(
        pd.merge(
            postgres_tables["answers"].drop(
                "id",
                axis=1
            ),
            postgres_tables["users"],
            how="left",
            left_on="user_id",
            right_on="id",
            suffixes=(
                "_answers",
                "_user"
            )
        ).drop(
            "id",
            axis=1
        ),
        postgres_tables["acts"].drop(
            [
                "act_data",
                "user_id",
                "status",
                "organization_id"
            ],
            axis=1
        ),
        how="left",
        left_on="act_id",
        right_on="id",
        suffixes=(
            "_answers",
            "_activity"
        )
    )
    answers = answers.sort_values(
        [
            "email",
            "title",
            "created_at_answers"
        ]
    ).reset_index(
        drop=True
    )
    answers = answers.set_index(
        [
            "email",
            "title",
            "updated_at",
            "created_at_answers"
        ]
    )
    users = set(
        answers.index.get_level_values(
            "email"
        )
    )
    users = {
        u: get_user_id_by_email(
            girder_connection,
            u
        ) for u in users
    }
    activities = set(
        answers.index.get_level_values(
            "title"
        )
    )
    response_folder_ids = set()
    for s in {
        (u, a) for u in users for a in activities
    }:
        activity_name, abbreviation = get_abbreviation(
            s[1]
        )
        try:
            activity_df = answers.loc[s,]
        except KeyError:
            continue
        respondent = list(
            activity_df[
                "respondent"
            ]
        )[0]
        version = activity_df.index.get_level_values("updated_at")[0]
        response_folder_id = girder_connection.createFolder(
            name="Responses",
            parentId=users[s[0]],
            parentType="user",
            public=False,
            reuseExisting=True
        )["_id"]
        activity_folder_id = girder_connection.createFolder(
            name=activity_name,
            parentId=response_folder_id,
            parentType="folder",
            public=False,
            reuseExisting=True
        )["_id"]
        for version in set(
            activity_df.index.get_level_values(
                "updated_at"
            )
        ):
            activity_version_folder_id = girder_connection.createFolder(
                name=get_postgres_item_version(
                    activity_name,
                    abbreviation=abbreviation,
                    activity_source="Version 0",
                    respondent=list(
                        activity_df[
                            "respondent"
                        ]
                    )[0],
                    version=date.strftime(
                        version,
                        "%F"
                    )
                ),
                parentId=activity_folder_id,
                parentType="folder",
                public=False,
                reuseExisting=True
            )["_id"]
            for response in activity_df.loc[
                version,
            ].index.get_level_values(
                "created_at_answers"
            ):
                response_item_id = girder_connection.createItem(
                    name=date.strftime(
                        response,
                        "%F-%R%z"
                    ),
                    parentFolderId=activity_version_folder_id,
                    reuseExisting=True
                )["_id"]
                user_responses = json.loads(
                    activity_df[
                        "answer_data"
                    ].values[0]
                )
                user_responses = user_responses["answers"] if (
                    "answers" in user_responses
                ) else user_responses["lines"] if (
                    "lines" in user_responses
                ) else [user_responses]
                screens = girder_connection.getItem(
                    _lookup_postgres_activity_in_girder(
                        girder_connection,
                        activity_name,
                        abbreviation,
                        respondent,
                        version
                    )
                )["meta"]["screens"]
                screens = [
                    girder_connection.getItem(
                        screen["@id"][5:]
                    )["meta"] for screen in screens
                ]
                answer_data = {
                    "responses": [
                        {
                            **{
                                resp: user_responses[
                                    i
                                ][resp] for resp in user_responses[
                                    i
                                ] if resp!="result"
                            },
                            "prompt": screens[i][
                                "question_text"
                            ] if (
                                "question_text" in screens[i]
                            ) else None,
                            "schema:name": screens[i][
                                "schema:name"
                            ] if (
                                "schema:name" in screens[i]
                            ) else None,
                            "choice": [
                                screens[
                                    i
                                ][
                                    "options"
                                ][
                                    selection
                                ] for selection in (
                                    answer[
                                        "result"
                                    ] if type(
                                        answer[
                                            "result"
                                        ]
                                    )==list else [
                                        answer[
                                            "result"
                                        ]
                                    ]
                                )
                            ] if (
                                (
                                    "response_type" in screens[i]
                                ) and (
                                    "sel" in screens[i]["response_type"]
                                ) and (
                                    "table" not in screens[i]["response_type"]
                                )
                            ) else None
                        } if (
                            answer is not None
                        ) else None for i, answer in enumerate(
                            user_responses
                        )
                    ] if (
                        len(
                            user_responses
                        ) and len(
                            screens
                        )
                    ) else None,
                #     "prompt": prompts[
                #         "instruction"
                #     ] if (
                #         "instruction" in prompts
                #     ) else None,
                    "devices:os": "devices:iOS" if activity_df.loc[
                        (
                            version,
                            response
                        )
                    ]["platform"] == "ios" else "devices:{0}".format(
                        activity_df.loc[
                            (
                                version,
                                response
                            )
                        ]["platform"]
                    )
                }
                girder_connection.addMetadataToItem(
                    response_item_id,
                    drop_empty_keys(
                        answer_data
                    )
                )
        response_folder_ids.add(response_folder_id)
    return(response_folder_ids)


def postgres_question_to_girder_question(
    q,
    question_text,
    variable_name,
    context,
    language="en-US"
):
    metadata={
        **context,
        "schema:name": {
            "@value": variable_name,
            "@language": language
        },
        "question_text": {
            "@value": question_text,
            "@language": language
        },
        "response_type": q["type"]
    } if context else {
        "schema:name": {
            "@value": variable_name,
            "@language": language
        },
        "question_text": {
            "@value": question_text,
            "@language": language
        },
        "response_type": q["type"]
    }
    return(metadata)


def postgres_questions_to_girder_screens(
    girder_connection,
    questions,
    short_name,
    screen_type,
    activity_version,
    context,
    language="en-US"
):
    """
    Function to convert Postgres questions
    to Girder screens

    Parameters
    ----------
    girder_connection: GirderClient

    questions: list of dictionaries

    short_name: string

    screen_type: string

    activity_version: string

    Returns
    -------
    screens: list
        list of Girder screen _ids

    Examples
    --------
    """
    screens_collection = get_girder_id_by_name(
        entity="collection",
        name="Screens",
        girder_connection=girder_connection
    )
    screens_folder_id = girder_connection.createFolder(
        name=activity_version,
        parentId=screens_collection,
        parentType="collection",
        public=False,
        reuseExisting=True
    )["_id"]
    screens = []
    screen_type, screen_mode = screen_type.split(
        " "
    ) if " " in screen_type else [
        screen_type,
        "table" if "table" in screen_type else None
    ]
    for i, q in enumerate(questions):
        question_text = q["title"] if "title" in q else q[
            "text"
        ] if "text" in q else q["instruction"] if "instruction" in q else None
        variable_name = q[
            "variable_name"
        ] if "variable_name" in q else "_".join([
            short_name,
            str(i + 1)
        ])
        metadata = postgres_question_to_girder_question(
            q,
            question_text,
            variable_name,
            context,
            language="en-US"
        )
        l = True
        while l:
            try:
                screen = girder_connection.createItem(
                    name=": ".join([
                        variable_name,
                        question_text if question_text else str(i)
                    ]),
                    parentFolderId=screens_folder_id,
                    reuseExisting=True,
                    metadata=drop_empty_keys(
                        metadata
                    )
                )["_id"]
                l = False
            except:
                continue
        if screen_mode=="table":
            table = table_cells_from_postgres(
                rows=q["rows"],
                columns=q["cols"],
                response_type=q["type"]
            )
            options = [
                postgres_options_to_JSONLD_options(
                    girder_connection,
                    row,
                    screen
                ) for row in [
                    {
                        "type": q["type"],
                        "title": table[(row,0)],
                        "rows": [
                            table[
                                (
                                    row if q[
                                        "type"
                                    ] in {
                                        "image_sel"
                                    } else 0,
                                    col
                                )
                            ] for col in {
                                cell[1] for cell in table
                            } if col > 0
                        ]
                    } for row in {
                        cell[0] for cell in table
                    } if row > 0
                ]
            ]
            rows = [
                {
                    "index": \
                    postgres_question_to_girder_question(
                        {
                            "type": "_".join([
                                q[
                                    "type"
                                ],
                                "tableRow"
                            ])
                        },
                        table[
                            (
                                i+1,
                                0
                            )
                        ]["text"],
                        "{0}_row_{1}".format(
                            variable_name,
                            str(i+1)
                        ),
                        context=None,
                        language=language
                    ),
                    "options": options[i] if "sel" in q[
                        "type"
                    ] else None,
                    "columns": [
                        {
                            "header": \
                            postgres_question_to_girder_question(
                                {
                                    "type": q[
                                        "type"
                                    ]
                                },
                                options[i][j]["option_text"],
                                "{0}_row_{1}_col_{2}".format(
                                    variable_name,
                                    str(i+1),
                                    str(j+1)
                                ),
                                context=None,
                                language=language
                            )
                        } for j, column in enumerate(
                            options[i]
                        )
                    ] if "sel" not in q[
                        "type"
                    ] else None
                } for i in range(len(options))
            ]
            girder_connection.addMetadataToItem(
                    screen,
                    {
                        **{
                            key: "_".join([
                                metadata[
                                    key
                                ],
                                "table"
                            ]) if (
                                (
                                    key=="response_type"
                                ) and (
                                    "table" not in metadata[
                                        key
                                    ]
                                )
                            ) else metadata[
                                key
                            ] for key in metadata if metadata[
                                key
                            ] is not None
                        },
                        "table": {
                            str(
                                coords
                            ): postgres_options_to_JSONLD_options(
                                girder_connection,
                                {
                                    "type": q["type"],
                                    "rows": [table[coords]]
                                },
                                screen
                            ) for coords in table
                        },
                        "rows": [
                            {
                                key: item[
                                    key
                                ] for key in item if item[
                                    key
                                ] is not None
                            } for item in rows
                        ]
                    }
                )
        elif q["type"] not in {
            "camera",
            "drawing",
            "number",
            "text"
        }:
            girder_connection.addMetadataToItem(
                screen,
                {
                    **{
                        key: metadata[
                            key
                        ] for key in metadata if metadata[
                            key
                        ] is not None
                    },
                    "options": \
                    postgres_options_to_JSONLD_options(
                        girder_connection,
                        q,
                        screen
                    )
                }
            )
        if "image_url" in q:
            continue
            girder_connection.addMetadataToItem(
                screen,
                {
                    **{
                        key: metadata[
                            key
                        ] for key in metadata if metadata[
                            key
                        ] is not None
                    },
                    "question_image": list(
                        upload_applicable_files(
                            girder_connection,
                            {
                                **q,
                                "filetype": "image_url"
                            },
                            screen,
                            q["title"] if "title" in q else q[
                                "instruction"
                            ] if "instruction" in q else str(i)
                        ).values()
                    )[0] if "image_url" in q else None
                }
            )
        screens.append(screen)
    return(screens)


def postgres_options_to_JSONLD_options(
    gc,
    q,
    item_id,
    language="en-US"
):
    """
    Function to convert Postgres question
    options to JSON-LD options

    Parameters
    ----------
    gc: GirderClient

    q: dictionary

    item_id: string

    language: string, default en-US

    Returns
    -------
    j_options: list of dictionaries

    Examples
    --------
    """
    j_options = [
        {
            "option_image": list(
                upload_applicable_files(
                    gc,
                    {
                        **option,
                        "filetype": "image_url"
                    },
                    item_id,
                    option[
                        "name"
                    ] if "name" in option else option[
                        "text"
                    ] if "text" in option else ""
                ).values()
            )[0] if "image_url" in option else None,
            "option_text": {
                "@value": option[
                    "text"
                ] if "text" in option else option[
                    "name"
                ] if "name" in option else None,
                "@language": language
            } if (
                "text" in option and option["text"] and len(option["text"])
            ) else None,
            "value": (
                option[
                    "value"
                ] if "value" in option else option[
                    "key"
                ] if "key" in option else option[
                    "name"
                ] if "name" in option else option[
                    "text"
                ] if "text" in option else None
            ) if q["type"] not in {
                "text"
            } else None
        } for option in [
            *(
                q[
                    "images"
                ] if "images" in q else []
            ),
            *(
                q[
                    "rows"
                ] if "rows" in q else []
            )
        ]
    ]
    j_options = [
        {
            key: item[
                key
            ] for key in item if item[
                key
            ] is not None
        } for item in j_options
    ]
    return(j_options)


def postgres_user_assign_to_girder_groups(
    postgres_user,
    girder_user,
    girder_connection
):
    """
    Function to assign User to appropriate
    Girder Groups per permissions in PostgresDB.

    Parameters
    ----------
    postgres_user: Series
        row from users DataFrame

    girder_user: string
        Girder User "_id"

    girder_connection: GirderClient
        active GirderClient

    Returns
    -------
    groups: dictionary
        key: string
            Group_id
        value: string
            permissions level
        groups and permissions levels assigned
    """
    roles = {
        "user": {
            "Users": 0
        },
        "admin": {
            "Managers": 0,
            "Editors": 1,
            "Users": 1,
            "Viewers": 1
        },
        "super_admin": {
            "Managers": 2,
            "Editors": 2,
            "Users": 2,
            "Viewers": 2
        },
        "viewer": {
            "Viewers": 0
        },
        None: {
            "Editors": 0
        }
    }

    groups = {}
    group_ids = get_group_ids(
        girder_connection
    )

    for role in roles[
        postgres_user["role"]
    ]:
        girder_connection.post(
            "".join([
                "group/",
                group_ids[
                    role
                ],
                "/invitation?userId=",
                girder_user,
                "&level=",
                str(
                    roles[
                        postgres_user[
                            "role"
                        ]
                    ][
                        role
                    ]
                ),
                "&",
                "quiet=true&",
                "force=true"
            ])
        ) if group_ids[
            role
        ] is not None else None
        groups[
            group_ids[
                role
            ]
        ] = "Member" if roles[
            postgres_user[
                "role"
            ]
        ][
            role
        ]==0 else "Moderator" if roles[
            postgres_user[
                "role"
            ]
        ][
            role
        ]==1 else "Administrator" if roles[
            postgres_user[
                "role"
            ]
        ][
            role
        ]==2 else None
    return(groups)


def postgres_users_to_girder_users(
    users,
    girder_connection,
    unknown_person={
        "first_name": "[Notname]",
        "last_name": "[Anonymous]"
    }
):
    """
    Function to transfer users from Postgres table to
    Girder collection.

    Parameters
    ----------
    users: DataFrame
        users table from Postgres DB

    girder_connection: GirderClient
        active GirderClient in which to add the users

    unknown_person: dictionary
        unknown_person["first_name"]: string
        unknown_person["last_name"]: string

    Returns
    -------
    users_by_email: dictionary
        key: string
            email address
        value: string
            Girder User_id
    """
    users_by_email = {}
    for i in range(users.shape[0]):
        user_id = get_user_id_by_email(
            girder_connection,
            users.loc[i,"email"]
        )
        if user_id:
            users_by_email[
                users.loc[i,"email"]
            ] = user_id
        else: # pragma: no cover
            original_login = users.loc[i,"email"].replace(
                "@",
                "at"
            )
            login = original_login
            while True: # pragma: no cover
                try: # pragma: no cover
                    user_id = girder_connection.post(
                        "".join([
                            "user?login=",
                            login,
                            "&firstName=",
                            unknown_person[
                                "first_name"
                            ] if not users.loc[
                                i,
                                "first_name"
                            ] else users.loc[
                                i,
                                "first_name"
                            ] if not " " in users.loc[
                                i,
                                "first_name"
                            ] else users.loc[
                                i,
                                "first_name"
                            ].split(" ")[0],
                            "&lastName=",
                            users.loc[
                                i,
                                "last_name"
                            ] if users.loc[
                                i,
                                "last_name"
                            ] else unknown_person[
                                "last_name"
                            ] if not users.loc[
                                i,
                                "first_name"
                            ] else users.loc[
                                i,
                                "first_name"
                            ].split(" ")[1] if " " in users.loc[
                                i,
                                "first_name"
                            ] else users.loc[
                                i,
                                "first_name"
                            ],
                            "&password=",
                            users.loc[i,"password"],
                            "&admin=",
                            "true" if str(
                                users.loc[
                                    i,
                                    "role"
                                ]
                            )=="super_admin" else "false",
                            "&email=",
                            users.loc[
                                i,
                                "email"
                            ],
                            "&public=false"
                        ])
                    )["_id"] # pragma: no cover
                    users_by_email[
                        users.loc[i,"email"]
                    ] = user_id # pragma: no cover
                    break # pragma: no cover
                except: # pragma: no cover
                    username_i = 1 # pragma: no cover
                    login = "{0}{1}".format(
                        original_login,
                        str(username_i)
                    ) # pragma: no cover
        postgres_user_assign_to_girder_groups(
            users.iloc[i],
            user_id,
            girder_connection
        ) # pragma: no cover
    return(users_by_email)


def table_cells_from_postgres(
    rows,
    columns,
    response_type
):
    """
    Function to convert Postgres table options
    encoded as rows and columns to dictionaries
    with (row, column) keys where 0 represents a
    header in either dimension and internal cells
    are 1-indexed.

    Parameters
    ----------
    rows: list
        rows[]: dictionary
            key: string
                "text" or "img_url"
            value: string
                row header

    columns: list
        columns[] dictionary
            key: string
                "text" or "img_url"
            value: string
                internal cell option or column header

    response_type: string

    Returns
    -------
    table: dictionary
        key: 2-tuple
            (row_number, column_number)
            row_number: int
                0 == header
            column_number: int
                0 == header
        value: dictionary
            key: string
                "text" or "img_url"
            value: string
                internal cell option or column header

    Examples
    --------
    >>> [
    ...     key for key in table_cells_from_postgres(
    ...         rows=[
    ...             {'text': 'Good question'},
    ...             {'text': 'Bad'}
    ...         ],
    ...         columns=[
    ...             {'text': '1'},
    ...             {'text': '2'}
    ...         ],
    ...         response_type="image_sel"
    ...     )
    ... ]
    [(1, 0), (2, 0), (1, 1), (1, 2), (2, 1), (2, 2)]
    >>> [
    ...     key for key in table_cells_from_postgres(
    ...         rows=[
    ...             {'text': 'Good question'},
    ...             {'text': 'Bad'}
    ...         ],
    ...         columns=[
    ...             {'text': '1'},
    ...             {'text': '2'}
    ...         ],
    ...         response_type="single_sel"
    ...     )
    ... ]
    [(1, 0), (2, 0), (0, 1), (0, 2)]
    """
    return(
        {
            **{
                (i+1,0): rows[i] for i in range(
                    len(rows)
                )
            },
            **{
                (
                    i+1 if response_type in {
                        "image_sel"
                    } else 0,
                    j+1
                ): columns[j] for i in range(
                    len(rows)
                ) for j in range(
                    len(columns)
                )
            },
            **({
                (i,j): {"value": 0} for i in range(
                    1, len(rows)+1
                ) for j in range(
                    1, len(columns)+1
                )
            } if response_type=="number" else {})
        }
    )


def upload_applicable_files(
    gc,
    act_data,
    item_id,
    item_name
):
    """
    Function to find a File in a Girder Item if
    such File exists, otherwise to upload said
    File from Postgres pointer.

    Parameters
    ----------
    gc: GirderClient
        active girder client

    act_data: dictionary
        from JSON in Postgres

    item_id: string
        Girder _id for Item

    item_name: string
        name of Item

    Returns
    -------
    file_ids: dictionary
        key: string
            filename
        value: dictionary
            "@id": string
                "file/[Girder _id of File]"

    Examples
    --------
    >>> import girder_client
    >>> upload_applicable_files(
    ...     gc=girder_client.GirderClient(
    ...         apiUrl="https://data.kitware.com/api/v1/"
    ...     ),
    ...     act_data = {
    ...         "image_url": "https://data.kitware.com/api/"
    ...         "v1/file/596f64838d777f16d01e9c28/download/"
    ...         "ensembl_vega_mart_88_drerio_gene_vega__"
    ...         "gene__main.sql.gz"
    ...     },
    ...     item_id="596f64838d777f16d01e9c27",
    ...     item_name="ensembl_vega_mart_88_drerio_gene_"
    ...     "vega__gene__main.sql"
    ... )[
    ...     "ensembl_vega_mart_88_drerio_gene_"
    ...     "vega__gene__main.sql.gz"
    ... ]["@id"]
    'file/596f64838d777f16d01e9c28'
    """
    file_ids = {}
    for filetype in [
        # TODO: "audio_path",
        "image_url"
    ]:
        # Upload applicable file(s)
        img = urllib.request.urlopen(
            act_data[filetype]
        ) if filetype in act_data else None
        if img:
            item_files = get_files_in_item(
                gc,
                item_id
            )
            suffix = act_data[
                "image_url"
            ].split("?")[0].split(".")[-1]
            alpha_num_un = re.sub(
                pattern="[^A-Za-z0-9_\.]+",
                repl="",
                string=item_name
            )
            img_name = ".".join([
                alpha_num_un,
                suffix
            ]) if not item_name.endswith(
                suffix
            ) else alpha_num_un
            if img_name in [
                file[
                    "name"
                ] for file in item_files
            ]:
                img_id = item_files[0]["_id"]
            else:
                img_id = gc.uploadFile(
                    parentId=item_id,
                    stream=img,
                    name=img_name,
                    size=int(
                        img.info()["Content-Length"]
                    )
                )["_id"] # pragma: no cover
            file_ids[
                img_name
            ] = {
                "@id": "file/{0}".format(
                    img_id
                )
            }
    return(file_ids)


def _lookup_postgres_activity_in_girder(
    girder_connection,
    activity_name,
    abbreviation,
    respondent,
    version
):
    """
    Function to find an already-ported-from-Postgres
    Activity in Girder

    Parameters
    ----------
    girder_connection: GirderClient

    activity_name: string

    abbreviation: string

    respondent: string

    version: Timestamp

    Returns
    -------
    item_id: string
        Girder _id
    """
    return(
        get_girder_id_by_name(
            girder_connection,
            entity="Item",
            name=get_postgres_item_version(
                activity_name,
                abbreviation=abbreviation,
                activity_source="Version 0",
                respondent=respondent,
                version=date.strftime(
                    version,
                    "%F"
                )
            ),
            parent=(
                "Folder",
                get_girder_id_by_name(
                    girder_connection,
                    entity="Folder",
                    name=get_postgres_item_version(
                        activity_name,
                        abbreviation=abbreviation
                    ),
                    parent=(
                        "collection",
                        get_girder_id_by_name(
                            girder_connection,
                            entity="Collection",
                            name="Activities",
                        )
                    )
                )
            )
        )
    ) # pragma: no cover


def _main(
    delete_first=False,
    keep_collections=None,
    keep_users=None,
    which_girder="dev"
):
    """
    Function to execute from commandline to transfer a running
    Postgres DB to a running Girder DB.

    "config.json" needs to have its values filled in first.

    Parameters
    ----------
    delete_first: boolean
        delete Users and Collections before building?

    keep_collections: Iterable or None

    keep_users: Iterable or None

    which_girder: string
        "dev" or "production"

    Returns
    -------
    activities_id: string

    activities: DataFrame

    config: dictionary

    context: dictionary

    girder_connection: GirderClient

    postgres_connection: connection

    groups: dictionary

    postgres_tables: dictionary

    users: dictionary
    """
    # Load configuration
    config, context, api_url = configuration(which_girder=which_girder) # pragma: no cover

    # Connect to Girder
    girder_connection = connect_to_girder(
        api_url=api_url,
        authentication=(
            config["girder-{}".format(
                which_girder
            )]["user"],
            config["girder-{}".format(
                which_girder
            )]["password"],
            config["girder-{}".format(
                which_girder
            )]["APIkey"]
        ) if "APIkey" in config["girder-{}".format(
                which_girder
            )] else (
            config["girder-{}".format(
                which_girder
            )]["user"],
            config["girder-{}".format(
                which_girder
            )]["password"]
        )
    ) # pragma: no cover

    # Connect to Postgres
    postgres_connection = connect_to_postgres(
        config["postgres"]
    ) # pragma: no cover

    if delete_first:
        delete_confirmed = ''
        while len(delete_confirmed) < 1:
            delete_confirmed = input("Really delete all Collections and Users?")
        if delete_confirmed[0].lower()=="y":
            _delete_collections(
                girder_connection,
                keep_collections
            )
            _delete_users(
                girder_connection,
                keep_users
            )

    # Get or create user Groups
    groups = get_group_ids(
        girder_connection,
        create_missing=True
    ) # pragma: no cover

    # Get or create activities Collection
    activities_id = get_girder_id_by_name(
        entity="collection",
        name="Activities",
        girder_connection=girder_connection
    ) # pragma: no cover

    # Get tables from Postgres
    postgres_tables = {
        table: pd.io.sql.read_sql_query(
            "SELECT * FROM {0};".format(
                table
            ),
            postgres_connection
        ) for table in {
            "acts",
            "users",
            "user_acts",
            "organizations",
            "answers"
        }
    } # pragma: no cover

    # Load users into Girder
    users = postgres_users_to_girder_users(
        postgres_tables["users"],
        girder_connection,
        config["missing_persons"]
    ) # pragma: no cover

    # Pull respondents out of titles in DataFrame from Postgres
    postgres_tables["acts"] = _respondents(
        postgres_tables["acts"]
    ) # pragma: no cover

    # Port activities from Postgres to Girder
    activities = \
    postgres_activities_to_girder_activities(
        acts=postgres_tables["acts"],
        gc=girder_connection,
        users=postgres_tables["users"],
        users_by_email=users,
        context=context
    ) # pragma: no cover

    # Port individual User Schedules from Postgres to Girder
    assignments = assingments_from_postgres(
        girder_connection,
        postgres_tables,
        context
    ) # pragma: no cover

    # Port individual User Responses from Postgres to Girder
    postgres_answers_to_girder_answers(
        girder_connection,
        postgres_tables,
        context
    ) # pragma: no cover

    # Collect new pointers
    activities_id = get_girder_id_by_name(
        girder_connection,
        "Collection",
        "Activities"
    ) # pragma: no cover
    screens_id = get_girder_id_by_name(
        girder_connection,
        "Collection",
        "Screens"
    ) # pragma: no cover
    schedules_id = get_girder_id_by_name(
        girder_connection,
        "Collection",
        "Schedules"
    ) # pragma: no cover
    users_ids = [
        user["_id"] for user in girder_connection.get("user")
    ] # pragma: no cover
    volumes_id = get_girder_id_by_name(
        girder_connection,
        "Collection",
        "Volumes"
    ) # pragma: no cover

    # Move Schedules and Activities into Volume

    for schedule in ls_x_in_y(
        "Folder",
        ("Collection", schedules_id),
        girder_connection
    ): # pragma: no cover
        versions = ls_x_in_y(
            "Item",
            ("Folder", schedule['_id']),
            girder_connection
        )  # pragma: no cover
        for version in versions:  # pragma: no cover
            volume = version['name'].split(
                schedule['name']
            )[0].strip()  # pragma: no cover
            volume_id = find_or_create(
                ('Folder', volume),
                ('Collection', volumes_id),
                girder_connection
            )  # pragma: no cover
            volume_schedules_folder = find_or_create(
                ('Folder', "Schedules"),
                ('Folder', volume_id),
                girder_connection
            )  # pragma: no cover
            mv(
                ('Folder', schedule['_id']),
                ('Folder', volume_schedules_folder),
                girder_connection
            )  # pragma: no cover
    girder_connection.delete(
        "collection/{}".format(schedules_id)
    )  # pragma: no cover

    for activity in ls_x_in_y(
        "Folder",
        ("Collection", activities_id),
        girder_connection
    ): # pragma: no cover
        versions = ls_x_in_y(
            "Item",
            ("Folder", activity['_id']),
            girder_connection
        ) # pragma: no cover
        for version in versions: # pragma: no cover
            volume = version['name'].split(
                activity['name']
            )[0].strip(" ―") # pragma: no cover
            volume_id = find_or_create(
                ('Folder', volume),
                ('Collection', volumes_id),
                girder_connection
            ) # pragma: no cover
            rename(
                ("Item", version["_id"]),
                version['name'].split(
                    volume,
                    maxsplit=1
                )[1].strip("― "),
                girder_connection
            ) # pragma: no cover
            volume_activities_folder = find_or_create(
                ('Folder', "Activities"),
                ('Folder', volume_id),
                girder_connection
            ) # pragma: no cover
            mv(
                ('Folder', activity['_id']),
                ('Folder', volume_activities_folder),
                girder_connection
            ) # pragma: no cover
    girder_connection.delete(
        "collection/{}".format(activities_id)
    ) # pragma: no cover

    # Update Activities (Item to Folder) in "Volume 0"

    volume_name = "Volume 0" # pragma: no cover
    activities_id = girder_connection.get(
        "&".join([
            "folder?parentType=folder",
            "parentId={}".format(
                girder_connection.get(
                    "&".join([
                        "folder?parentType=collection",
                        "parentId={}".format(volumes_id),
                        "text={}".format(volume_name)
                    ])
                )[0]["_id"]
            ),
            "name={}".format(
                "Activities"
            )
        ])
    )[0]["_id"] # get "Activities" _id within Volume # pragma: no cover

    activity_ids = [
        a["_id"] for a in girder_connection.get(
            "&".join([
                "folder?parentType=folder",
                "parentId={}".format(
                    activities_id
                )
            ])
        )
    ] # get _ids of each Activity # pragma: no cover

    for activity in activity_ids: # pragma: no cover
        [
            move_item_to_folder(
                version["_id"],
                girder_connection
            ) for version in girder_connection.get(
                "&".join([
                    "item?folderId={}".format(activity),
                ])
            )
        ] # pragma: no cover

    # Move Volumes to top of Users

    for user in users_ids: # pragma: no cover
        for user_folder in ls_x_in_y(
            "Folder",
            ("User", user),
            girder_connection
        ): # pragma: no cover
            for item in ls_x_in_y(
                "Item",
                ("Folder", user_folder["_id"]),
                girder_connection
            ): # pragma: no cover
                volume = item['name'][:9] # pragma: no cover
                volume_id = find_or_create(
                    ('Folder', volume),
                    ('User', user),
                    girder_connection
                ) # pragma: no cover
                rename(
                    ("Item", item["_id"]),
                    item['name'].split(volume)[1].strip(),
                    girder_connection
                ) # pragma: no cover
                mv(
                    ("Folder", user_folder["_id"]),
                    ("Folder", volume_id),
                    girder_connection
                ) # pragma: no cover
            for internal_folder in ls_x_in_y(
                "Folder",
                ("Folder", user_folder["_id"]),
                girder_connection
            ): # pragma: no cover
                for version in ls_x_in_y(
                    "Folder",
                    ("Folder", internal_folder["_id"]),
                    girder_connection
                ): # pragma: no cover
                    volume = version['name'].split(
                        internal_folder['name']
                    )[0].strip(" ―") # pragma: no cover
                    volume_id = find_or_create(
                        ('Folder', volume),
                        ('User', user),
                        girder_connection
                    ) # pragma: no cover
                    rename(
                        ("Folder", version["_id"]),
                        version['name'].split(volume)[1].strip("― "),
                        girder_connection
                    ) # pragma: no cover
                    try: # pragma: no cover
                        mv(
                            ("Folder", user_folder["_id"]),
                            ("Folder", volume_id),
                            girder_connection
                        ) # pragma: no cover
                    except: # pragma: no cover
                        pass # if this function persists, add code to copy relevant Folders # pragma: no cover

    # Move Screens into Activity versions

    for screens in ls_x_in_y(
        "Folder",
        ("Collection", screens_id),
        girder_connection
    ):  # pragma: no cover
        volume = screens['name'].split("―")[0].strip(" ―") # pragma: no cover
        volume_id = find_or_create(
            ('Folder', volume),
            ('Collection', volumes_id),
            girder_connection
        ) # pragma: no cover
        screenset = [1] # pragma: no cover
        while len(screenset): # iterate for n(screens) > 50 # pragma: no cover
            screenset = girder_connection.get(
                "item?folderId={}".format(screens["_id"])
            ) # pragma: no cover
            for screen in screenset: # pragma: no cover
                vers = girder_connection.get(
                    "folder/{}".format(screen["folderId"])
                )['name'].split(volume)[1].strip("― ") # pragma: no cover
                act = vers.split(
                    "―"
                )[0].strip() if "―" in vers else vers.rsplit(
                    "(",
                    maxsplit=1
                )[0].strip() # pragma: no cover
                mv(
                    (
                        "Item",
                        screen["_id"]
                    ),
                    (
                        "Folder",
                        girder_connection.get(
                            "&".join([
                                "folder?parentId={}".format(
                                    girder_connection.get(
                                        "&".join([
                                            "folder?parentId={}".format(volume_activities_folder),
                                            "parentType=folder",
                                            "name={}".format(act)
                                        ])
                                    )[0]["_id"]
                                ),
                                "parentType=folder",
                                "name={}".format(vers)
                            ])
                        )[0]["_id"]
                    ),
                    girder_connection
                ) # pragma: no cover

    girder_connection.delete(
        "collection/{}".format(screens_id)
    ) # pragma: no cover

    return(
        (
            activities_id,
            activities,
            config,
            context,
            girder_connection,
            postgres_connection,
            groups,
            postgres_tables,
            users
        )
    ) # pragma: no cover

def _respondents(acts):
    """
    Function to extract respondents from
    activity titles in Postgres table and
    update relevat columns

    Parameters
    ----------
    acts: DataFrame

    Returns
    -------
    acts: DataFrame

    Examples
    --------
    >>> import pandas as pd
    >>> _respondents(
    ...     pd.DataFrame(
    ...         {
    ...             "title": [
    ...                 "Test - Self Report",
    ...                 "Test - Parent Report"
    ...             ]
    ...         }
    ...     )
    ... ).loc[0, "respondent"]
    'Self'
    """
    acts["respondent"] = acts["title"].apply(
        lambda x: x.split(
            " - "
        )[
            1
        ].split(
            " "
        )[
            0
        ] if " - " in x else x.split(
            " – "
        )[
            1
        ].split(
            " "
        )[
            0
        ] if " – " in x else x.split(
            "-"
        )[
            1
        ].split(
            " "
        )[
            0
        ] if "Scale-" in x else x.split(
            " ― "
        )[
            1
        ].split(
            "-"
        )[
            0
        ] if "―" in x else x.split(
            "-"
        )[
            1
        ].split(
            ")"
        )[
            0
        ] if "Index-" in x else "Self" if (
            (
                "_SR" in x
            ) or (
                "-SR" in x
            )
        ) else "Parent" if (
            "_P" in x
        ) else ""
    )
    acts["title"] = acts["title"].apply(
        lambda x: x.split(
            " - "
        )[
            0
        ] if " - " in x else x.split(
            " – "
        )[
            0
        ] if " – " in x else x.split(
            "-"
        )[
            0
        ] if "Scale-" in x else x.split(
            " ― "
        )[
            0
        ] if "―" in x else x.split(
            "-"
        )[
            0
        ] if "Index-" in x else x.replace(
            " Self Report",
            ""
        ).replace(
            " Parent Report",
            ""
        )
    ).apply(
        lambda x: "{0})".format(
            x
        ) if (
            "(" in x
        ) and (
            ")"
        ) not in x else x
    )
    return(acts)
