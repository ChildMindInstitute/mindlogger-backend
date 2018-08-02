__package__ = "mindlogger_backend_dev.create_scorekeys"


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


def score(responses, scorekey, girder_connection):
    """
    Function to calculate a participants' scores.
    
    """
    pass