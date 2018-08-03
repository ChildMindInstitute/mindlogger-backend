__package__ = "mindlogger_backend_dev.create_scorekeys"
import json
from .. import object_manipulation
import os
import pandas as pd
from urllib.parse import quote


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
        key: tuple of tuples
            [i][0]: "==", "<", ">", "<=", ">="
            [i][1]: comparator
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


def scorekey_to_girder(activity_version_id, scorekey, girder_connection):
    """
    Function to create a scorekey in Girder.
    
    Parameters
    ----------
    activity_version_id: string
        Girder _id of Activity Version
        
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
        value: tuple
            [0]: anything
                score value
            [1]: anything
                score label
    
    Examples
    --------
    >>> responses = [
    ...     {
    ...         'choice': [
    ...             {
    ...                 'option_text': {
    ...                     '@language': 'en-US',
    ...                     '@value': 'Right hand, sometimes uses other hand'
    ...                 },
    ...                 'value': '0.5'
    ...             }
    ...         ],
    ...         'prompt': {
    ...             '@language': 'en-US',
    ...             '@value': 'Writing'
    ...         },
    ...         'schema:name': {
    ...             '@language': 'en-US',
    ...             '@value': 'EHQ_01'
    ...         },
    ...         'time': 1519226389593
    ...     },
    ...     {
    ...         'choice': [
    ...             {
    ...                 'option_text': {
    ...                     '@language': 'en-US',
    ...                     '@value': 'No preference'
    ...                 },
    ...                 'value': '0'
    ...             }
    ...         ],
    ...         'prompt': {
    ...             '@language': 'en-US',
    ...             '@value': 'Drawing'
    ...         },
    ...         'schema:name': {
    ...             '@language': 'en-US',
    ...             '@value': 'EHQ_02'
    ...         },
    ...         'time': 1519226395777
    ...     },
    ...     {
    ...         'choice': [
    ...             {
    ...                 'option_text': {
    ...                     '@language': 'en-US',
    ...                     '@value': 'Right hand, sometimes uses other hand'
    ...                 },
    ...                 'value': '0.5'
    ...             }
    ...         ],
    ...         'prompt': {
    ...             '@language': 'en-US',
    ...             '@value': 'Throwing'
    ...         },
    ...         'schema:name': {
    ...             '@language': 'en-US',
    ...             '@value': 'EHQ_03'
    ...         },
    ...         'time': 1519226398015
    ...     },
    ...     {
    ...         'choice': [
    ...             {
    ...                 'option_text': {
    ...                     '@language': 'en-US',
    ...                     '@value': 'Left hand, sometimes other hand'
    ...                 },
    ...                 'value': '-0.5'
    ...             }
    ...         ],
    ...         'prompt': {
    ...             '@language': 'en-US',
    ...             '@value': 'Using Scissors'
    ...         },
    ...         'schema:name': {
    ...             '@language': 'en-US',
    ...             '@value': 'EHQ_04'
    ...         },
    ...         'time': 1519226402229
    ...     },
    ...     {
    ...         'choice': [
    ...             {
    ...                 'option_text': {
    ...                     '@language': 'en-US',
    ...                     '@value': 'No preference'
    ...                 },
    ...                 'value': '0'
    ...             }
    ...         ],
    ...         'prompt': {
    ...             '@language': 'en-US',
    ...             '@value': 'Using a Toothbrush'
    ...         },
    ...         'schema:name': {
    ...             '@language': 'en-US',
    ...             '@value': 'EHQ_05'
    ...         },
    ...         'time': 1519226404429
    ...     },
    ...     {
    ...         'choice': [
    ...             {
    ...                 'option_text': {
    ...                     '@language': 'en-US',
    ...                     '@value': 'No preference'
    ...                 },
    ...                 'value': '0'
    ...             }
    ...         ],
    ...         'prompt': {
    ...             '@language': 'en-US',
    ...             '@value': 'Using a Knife (without a fork)'
    ...         },
    ...         'schema:name': {
    ...             '@language': 'en-US',
    ...             '@value': 'EHQ_06'
    ...         },
    ...         'time': 1519226412079
    ...     },
    ...     {
    ...         'choice': [
    ...             {
    ...                 'option_text': {
    ...                     '@language': 'en-US',
    ...                     '@value': 'No preference'
    ...                 },
    ...                 'value': '0'
    ...             }
    ...         ],
    ...         'prompt': {
    ...             '@language': 'en-US',
    ...             '@value': 'Using a Spoon'
    ...         },
    ...         'schema:name': {
    ...             '@language': 'en-US',
    ...             '@value': 'EHQ_07'
    ...         },
    ...         'time': 1519226416146
    ...     },
    ...     {
    ...         'choice': [
    ...             {
    ...                 'option_text': {
    ...                     '@language': 'en-US',
    ...                     '@value': 'No preference'
    ...                 },
    ...                 'value': '0'
    ...             }
    ...         ],
    ...         'prompt': {
    ...             '@language': 'en-US',
    ...             '@value': 'Using a Broom (upper hand)'
    ...         },
    ...         'schema:name': {
    ...             '@language': 'en-US',
    ...             '@value': 'EHQ_08'
    ...         },
    ...         'time': 1519226420380
    ...     },
    ...     {
    ...         'choice': [
    ...             {
    ...                 'option_text': {
    ...                     '@language': 'en-US',
    ...                     '@value': 'No preference'
    ...                 },
    ...                 'value': '0'
    ...             }
    ...         ],
    ...         'prompt': {
    ...             '@language': 'en-US',
    ...             '@value': 'Striking a Match'
    ...         },
    ...         'schema:name': {
    ...             '@language': 'en-US',
    ...             '@value': 'EHQ_09'
    ...         },
    ...         'time': 1519226423028
    ...     },
    ...     {
    ...         'choice': [
    ...             {
    ...                 'option_text': {
    ...                     '@language': 'en-US',
    ...                     '@value': 'No preference'
    ...                 },
    ...                 'value': '0'
    ...             }
    ...         ],
    ...         'prompt': {
    ...             '@language': 'en-US',
    ...             '@value': 'Opening a Box (holding the lid)'
    ...         },
    ...         'schema:name': {
    ...             '@language': 'en-US',
    ...             '@value': 'EHQ_10'
    ...         },
    ...         'time': 1519226425111
    ...     },
    ...     {
    ...         'choice': [
    ...             {
    ...                 'option_text': {
    ...                     '@language': 'en-US',
    ...                     '@value': 'Left hand, sometimes other hand'
    ...                 },
    ...                 'value': '-0.67'
    ...             }
    ...         ],
    ...         'prompt': {
    ...             '@language': 'en-US',
    ...             '@value': 'Holding a Computer Mouse'
    ...         },
    ...         'schema:name': {
    ...             '@language': 'en-US',
    ...             '@value': 'EHQ_11'
    ...         },
    ...         'time': 1519226428676
    ...     },
    ...     {
    ...         'choice': [
    ...             {
    ...                 'option_text': {
    ...                     '@language': 'en-US',
    ...                     '@value': 'No preference'
    ...                 },
    ...                 'value': '0'
    ...             }
    ...         ],
    ...         'prompt': {
    ...             '@language': 'en-US',
    ...             '@value': 'Using a Key to Unlock a Door'
    ...         },
    ...         'schema:name': {
    ...             '@language': 'en-US',
    ...             '@value': 'EHQ_12'
    ...         },
    ...         'time': 1519226431664
    ...     },
    ...     {
    ...         'choice': [
    ...             {
    ...                 'option_text': {
    ...                     '@language': 'en-US',
    ...                     '@value': 'No preference'
    ...                 },
    ...                 'value': '0'
    ...             }
    ...         ],
    ...         'prompt': {
    ...             '@language': 'en-US',
    ...             '@value': 'Holding a Hammer'
    ...         },
    ...         'schema:name': {
    ...             '@language': 'en-US',
    ...             '@value': 'EHQ_13'
    ...         },
    ...         'time': 1519226434345
    ...     },
    ...     {
    ...         'choice': [
    ...             {
    ...                 'option_text': {
    ...                     '@language': 'en-US',
    ...                     '@value': 'Left hand, sometimes other hand'
    ...                 },
    ...                 'value': '-0.67'
    ...             }
    ...         ],
    ...         'prompt': {
    ...             '@language': 'en-US',
    ...             '@value': 'Holding a Brush or Comb'
    ...         },
    ...         'schema:name': {
    ...             '@language': 'en-US',
    ...             '@value': 'EHQ_14'
    ...         },
    ...         'time': 1519226438862
    ...     },
    ...     {
    ...         'choice': [
    ...             {
    ...                 'option_text': {
    ...                     '@language': 'en-US',
    ...                     '@value': 'No preference'
    ...                 },
    ...                 'value': '0'
    ...             }
    ...         ],
    ...         'prompt': {
    ...             '@language': 'en-US',
    ...             '@value': 'Holding a Cup While Drinking'
    ...         },
    ...         'schema:name': {
    ...             '@language': 'en-US',
    ...             '@value': 'EHQ_15'
    ...         },
    ...         'time': 1519226441115
    ...     }
    ... ]
    >>> scorekey = {
    ...     'Laterality Index': {
    ...         'formula': [
    ...             'EHQ_01',
    ...             '+',
    ...             'EHQ_02',
    ...             '+',
    ...             'EHQ_03',
    ...             '+',
    ...             'EHQ_04',
    ...             '+',
    ...             'EHQ_05',
    ...             '+',
    ...             'EHQ_06',
    ...             '+',
    ...             'EHQ_07',
    ...             '+',
    ...             'EHQ_08',
    ...             '+',
    ...             'EHQ_09',
    ...             '+',
    ...             'EHQ_10',
    ...             '+',
    ...             'EHQ_11',
    ...             '+',
    ...             'EHQ_12',
    ...             '+',
    ...             'EHQ_13',
    ...             '+',
    ...             'EHQ_14',
    ...             '+',
    ...             'EHQ_15'
    ...         ],
    ...         'lookup': {
    ...             (('==', -100),): '10th left',
    ...             (('>=', -100), ('<', -92)): '9th left',
    ...             (('>=', -92), ('<', -90)): '8th left',
    ...             (('>=', -90), ('<', -87)): '7th left',
    ...             (('>=', -87), ('<', -83)): '6th left',
    ...             (('>=', -83), ('<', -76)): '5th left',
    ...             (('>=', -76), ('<', -66)): '4th left',
    ...             (('>=', -66), ('<', -54)): '3d left',
    ...             (('>=', -54), ('<', -42)): '2d left',
    ...             (('>=', -42), ('<', -28)): '1st left',
    ...             (('>=', -28), ('<', 48)): 'Middle',
    ...             (('>=', 48), ('<', 60)): '1st right',
    ...             (('>=', 60), ('<', 68)): '2d right',
    ...             (('>=', 68), ('<', 74)): '3d right',
    ...             (('>=', 74), ('<', 80)): '4th right',
    ...             (('>=', 80), ('<', 84)): '5th right',
    ...             (('>=', 84), ('<', 88)): '6th right',
    ...             (('>=', 88), ('<', 92)): '7th right',
    ...             (('>=', 92), ('<', 95)): '8th right',
    ...             (('>=', 95), ('<', 100)): '9th right',
    ...             (('==', 100),): '10th right'
    ...         }
    ...     }
    ... }
    >>> score(responses, scorekey)['Laterality Index'][1]
    'Middle'
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
    scores = {
        score: (
            scores[score],
            score_label_lookup(
                scores[score],
                scorekey[score]["lookup"]
            )
        ) for score in scores
    }
    return(scores)


def score_label_lookup(score_value, score_key_labels):
    """
    Function to lookup labels / text values for scores.
    
    Parameters
    ----------
    score_value: numeric
        score to lookup
    
    score_key_labels: dictionary
        key: string
            value or range of values
        value: anything
            labels / text values
    
    Returns
    -------
    score_label: anything
        label / text value of score_value
        
    Examples
    --------
    >>> labels = {
    ...     (('==', -100),): '10th left',
    ...     (('>=', -100), ('<', -92)): '9th left',
    ...     (('>=', -92), ('<', -90)): '8th left',
    ...     (('>=', -90), ('<', -87)): '7th left',
    ...     (('>=', -87), ('<', -83)): '6th left',
    ...     (('>=', -83), ('<', -76)): '5th left',
    ...     (('>=', -76), ('<', -66)): '4th left',
    ...     (('>=', -66), ('<', -54)): '3d left',
    ...     (('>=', -54), ('<', -42)): '2d left',
    ...     (('>=', -42), ('<', -28)): '1st left',
    ...     (('>=', -28), ('<', 48)): 'Middle',
    ...     (('>=', 48), ('<', 60)): '1st right',
    ...     (('>=', 60), ('<', 68)): '2d right',
    ...     (('>=', 68), ('<', 74)): '3d right',
    ...     (('>=', 74), ('<', 80)): '4th right',
    ...     (('>=', 80), ('<', 84)): '5th right',
    ...     (('>=', 84), ('<', 88)): '6th right',
    ...     (('>=', 88), ('<', 92)): '7th right',
    ...     (('>=', 92), ('<', 95)): '8th right',
    ...     (('>=', 95), ('<', 100)): '9th right',
    ...     (('==', 100),): '10th right'
    ... }
    >>> score_label_lookup(-80, labels)
    '5th left'
    >>> score_label_lookup(101, labels)
    """
    try:
        return(
            pd.Series(
                score_key_labels
            ).loc[
                pd.Series([
                    all([
                        eval(
                            "".join([
                                str(score_value),
                                *[str(o) for o in t]
                            ])
                        ) for t in k
                    ]) for k in score_key_labels
                ]).values
            ].values[0]
        )
    except:
        return(None)
    
    
def scorekey_to_girder(activity_version_id, scorekey, girder_connection):
    """
    Function to create a scorekey in Girder.
    
    Parameters
    ----------
    activity_version_id: string
        Girder _id of Activity Version
        
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
            
    girder_connection: GirderClient
        active GirderClient
    
    Returns
    -------
    activity_version: dictionary
        updated activity version
    
    Examples
    -------
    >>> from .. import girder_connections, update_schema
    >>> import os
    >>> which_girder = "dev"
    >>> config, context, api_url = girder_connections.configuration(
    ...     config_file=os.path.join(
    ...         os.path.dirname(__file__),
    ...         "config.json.template"
    ...     ),
    ...     context_file=os.path.join(
    ...         os.path.dirname(__file__),
    ...         "context.json"
    ...     ),
    ...     which_girder=which_girder
    ... )
    >>> which_girder = "girder-{}".format(which_girder)
    >>> girder_connection = girder_connections.connect_to_girder(
    ...     api_url=api_url,
    ...     authentication=(
    ...         config[which_girder]["user"],
    ...         config[which_girder]["password"],
    ...         config[which_girder]["APIkey"]
    ...     ) if "APIkey" in config[which_girder] else (
    ...         config[which_girder]["user"],
    ...         config[which_girder]["password"]
    ...     )
    ... )
    Connected to the Girder database 🏗🍃 and authenticated.
    >>> book = update_schema.find_or_create(
    ...     ("Folder", "Book of Cagliostro"),
    ...     ("Collection", update_schema.get_girder_id_by_name(
    ...         girder_connection,
    ...         "Collection",
    ...         "Ancient One"
    ...     )),
    ...     girder_connection
    ... )
    >>> scorekey={
    ...     'Ring': {
    ...         'formula': [
    ...             1,
    ...             '+',
    ...             2
    ...         ],
    ...         'lookup': {
    ...             "(('==', 3),)": 'Gollum'
    ...         }
    ...     }
    ... }
    >>> scorekey_to_girder(
    ...     book, scorekey, girder_connection
    ... )["meta"]["scorekey"]["Ring"]["lookup"]
    {"(('==', 3),)": 'Gollum'}
    """
    activity_version = girder_connection.get("folder/{}".format(activity_version_id))
    meta = activity_version["meta"] if "meta" in activity_version else {}
    scorekey = {
        key: {
            "formula": scorekey[key][
                "formula"
            ] if "formula" in scorekey[key] else None,
            "lookup": {
                str(comparisons): scorekey[key]["lookup"][comparisons]
                for comparisons in scorekey[key]["lookup"]
            } if "lookup" in scorekey[key] else None
        } for key in scorekey
    }
    meta["scorekey"] = {
        **meta["scorekey"],
        **scorekey
    } if "scorekey" in meta else scorekey
    return(
        girder_connection.put(
            "?".join([
                "folder/{}".format(activity_version_id),
                "metadata={}".format(
                    quote(
                        json.dumps(meta)
                    )
                )
            ])
        )
    )