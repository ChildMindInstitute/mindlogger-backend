__package__ = "mindlogger_backend_dev.create_scorekeys"
from .. import object_manipulation


score_key_comparison_operators = {
    "=": (
        "==",
        "=="
    ),
    "==": (
        "==",
        "=="
    ),
    "<": (
        "<",
        ">"
    ),
    ">": (
        ">",
        "<"
    ),
    "<=": (
        "<=",
        ">="
    ),
    "≤": (
        "<=",
        ">="
    ),
    "≥": (
        ">=",
        "<="
    ),   
    ">=": (
        ">=",
        "<="
    )
}


def columns_to_score_key_labels(columns):
    """
    Function to convert 2-column table to score key labels dictionary
    
    Parameters
    ----------
    columns: DataFrame
        2-column table with ranges in the first column and values in the second
        
    Returns
    -------
    score_key_labels: dictionary
        key: string
            range (from first column)
        value: dictionary
            key: tuple
                [0]: "==", "<", ">", "<=", ">="
                [1]: comparator
            value: anything
                label
                
    Example
    -------
    >>> import pandas as pd
    >>> columns_to_score_key_labels(pd.DataFrame(
    ...     {
    ...         'range': {
    ...             17: 'LI=-100',
    ...             18: '−100 ≤ LI < −92',
    ...             19: '−92 ≤ LI < −90',
    ...             20: '−90 ≤ LI < −87',
    ...             21: '−87 ≤ LI < −83',
    ...             22: '−83 ≤ LI < −76',
    ...             23: '−76 ≤ LI < −66',
    ...             24: '−66 ≤ LI < −54',
    ...             25: '−54 ≤ LI < −42',
    ...             26: '−42 ≤ LI < −28',
    ...             27: '−28 ≤ LI < 48',
    ...             28: '48 ≤ LI < 60',
    ...             29: '60 ≤ LI < 68',
    ...             30: '68 ≤ LI < 74',
    ...             31: '74 ≤ LI < 80',
    ...             32: '80 ≤ LI < 84',
    ...             33: '84 ≤ LI < 88',
    ...             34: '88 ≤ LI < 92',
    ...             35: '92 ≤ LI < 95',
    ...             36: '95 ≤ LI < 100',
    ...             37: 'LI = 100'
    ...         },
    ...         'value': {
    ...             17: '10th left',
    ...             18: '9th left',
    ...             19: '8th left',
    ...             20: '7th left',
    ...             21: '6th left',
    ...             22: '5th left',
    ...             23: '4th left',
    ...             24: '3d left',
    ...             25: '2d left',
    ...             26: '1st left',
    ...             27: 'Middle',
    ...             28: '1st right',
    ...             29: '2d right',
    ...             30: '3d right',
    ...             31: '4th right',
    ...             32: '5th right',
    ...             33: '6th right',
    ...             34: '7th right',
    ...             35: '8th right',
    ...             36: '9th right',
    ...             37: '10th right'
    ...         }
    ...     }
    ... ))[('>=', -28), ('<', 48)]
    'Middle'
    """
    initial_dict = {
        a[1][
            columns.columns[0]
        ].replace("−", "-"): a[1][
            columns.columns[1]
        ] for a in columns.iterrows()
    }
    score_key_labels = {
            tuple([
                    *[(
                    score_key_comparison_operators[
                        operator
                    ][1],
                    object_manipulation.numeric(
                        key.split(
                            operator
                        )[0].strip()
                    )
                ) for operator in score_key_comparison_operators if (
                    (
                        operator in key
                    ) and (
                        (
                            key.split(
                                operator
                            )[0].strip().isnumeric()
                        ) or (
                            (
                                key.split(
                                    operator
                                )[0].strip().startswith("-")
                            ) and (
                                key.split(
                                    operator
                                )[0].strip()[1:].isnumeric()
                            )
                        )
                    )
                )],
                *[(
                    score_key_comparison_operators[
                        operator
                    ][0],
                    object_manipulation.numeric(
                        key.split(
                            operator
                        )[1].strip()
                    )
                ) for operator in score_key_comparison_operators if (
                    (
                        operator in key
                    ) and (
                        (
                            key.split(
                                operator
                            )[1].strip().isnumeric()
                        ) or (
                            (
                                key.split(
                                    operator
                                )[1].strip().startswith("-")
                            ) and (
                                key.split(
                                    operator
                                )[1].strip()[1:].isnumeric()
                            )
                        )
                    )
                )]
            ]): initial_dict[key] for key in initial_dict
    }
    return(score_key_labels)


def create_scorekey(activity_version_id, formula, girder_connection):
    """
    Function to create a scorekey in Girder.
    
    Parameters
    ----------
    activity_version_id: string
        Girder _id of Activity Version
        
    formula: dictionary
        key: string
            score name
        value: list
            sequence of constants, operators, and variable names, eg,
            `["(", 1, "+", "variable1", ")", "*", "variable2"]`
            
    girder_connection: GirderClient
        active GirderClient
    
    Returns
    -------
    None
    
    Examples
    -------
    pass
    """
    pass
    

def get_variables(activity_version_id, girder_connection):
    """
    Function to collect variable names and Girder _ids for screens in an activity version.
    
    Parameters
    ----------
    activity_version_id: string
        Girder _id of Activity Version
    
    
    girder_connection: GirderClient
        active GirderClient
        
    Returns
    -------
    variables: dictionary
        key: string
            variable name
        value: string
            Girder _id
            
    Examples
    --------
    >>> from .. import girder_connections, update_schema
    >>> from urllib.parse import quote
    >>> import json, os
    >>> config_file = os.path.join(
    ...    os.path.dirname(__file__),
    ...    "config.json.template"
    ... )
    >>> config, context, api_url = girder_connections.configuration(
    ...     config_file=config_file
    ... )
    >>> girder_connection = girder_connections.connect_to_girder(
    ...     api_url=api_url,
    ...     authentication=(
    ...         config["girder-dev"]["user"],
    ...         config["girder-dev"]["password"]
    ...     )
    ... )
    Connected to the Girder database 🏗🍃 and authenticated.
    >>> book = girder_connection.get(
    ...     "folder/{}".format(update_schema.find_or_create(
    ...         ("Folder", "Book of Cagliostro"),
    ...         ("Collection", update_schema.get_girder_id_by_name(
    ...             girder_connection,
    ...             "Collection",
    ...             "Ancient One"
    ...         )
    ...     ),
    ...     girder_connection
    ... )))
    >>> book['name']
    'Book of Cagliostro'
    >>> incantation = girder_connection.get("item/{}".format(update_schema.find_or_create(
    ...     ("Item", "draw energy from the Dark Dimension"),
    ...     ("Folder", book["_id"]),
    ...     girder_connection
    ... )))
    >>> incantation = girder_connection.put("item/{}?metadata={}".format(
    ...     incantation["_id"],
    ...     quote(json.dumps({"schema:name":{"@value": "Dark"}}))
    ... ))["_id"]
    >>> list(get_variables(book["_id"], girder_connection))[0]
    'Dark'
    """
    screens = girder_connection.get(
        "item?folderId={}".format(activity_version_id)
    )
    return(
        {
            screen["meta"]["schema:name"]["@value"]: screen[
                "_id"
            ] for screen in screens if (
                "meta" in screen
            ) and (
                "schema:name" in screen["meta"]
            )
        }
    )


def score(responses, scorekey):
    """
    Function to calculate a participants' scores.
    
    Parameters
    ----------
    responses: list of dictionaries
        []
            'choice': list of dictionaries
                []
                    'option_text': dictionary
                        '@language': string
                            eg, 'en-US'
                        '@value': string
                            option text
                    'value': anything
                        scoring value
            'prompt': dictionary
                '@language': string
                    eg, 'en-US'
                '@value': string
                    prompt text
            'schema:name': dictionary
                '@language': string
                    eg, 'en-US'
                '@value': string
                    name of item/question/prompt/screen
            'time': int
                POSIX×1,000 timestamp
    
    scorekey: dictionary
        key: string
            score name
        value: dictionary
            formula: list
                sequence of constants, operators, and variable names, eg,
                `["(", 1, "+", "variable1", ")", "*", "variable2"]`
            lookup: dictionary
                key: anything
                value: anything
    
    Returns
    -------
    scores: dictionary
        key: string
            score name
        value: anything
            score
    
    Examples
    --------
    """
    response_values = {
        response["schema:name"]["@value"]: [
            choice['value'] for choice in response[
                "choice"
            ]
        ] for response in responses
    }
    response_values = {
        prompt_name: response_values[prompt_name][0] if (
            len(response_values[prompt_name])==1
        ) else response_values[
            prompt_name
        ] for prompt_name in response_values
    }
    scores = {
        score: eval(
            "".join(
                [
                    response_values[
                        step
                    ] if step in response_values else step for step in scorekey[
                        score
                    ]["formula"]
                ]
            ).replace(
                "+-",
                "-"
            ).replace(
                "--",
                "+"
            )
        ) for score in scorekey
    }
    return(scores)