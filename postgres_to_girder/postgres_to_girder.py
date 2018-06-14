import girder_client as gc
import json
import os
import pandas as pd
import psycopg2
import urllib
from datetime import date


def config(
    config_file=None,
    context_file=None
):
    """
    Function to set configuration variables.
    
    Parameters
    ----------
    config_file: string, optional
        path to configuration file
        default = "config.json"
        
    context_file: string, optional
        path to context file
        default = "context.json"
        
    Returns
    -------
    config: dictionary
    
    context: dictionary
    
    api_url: string
    
    Example
    -------
    >>> import json
    >>> config, context, api_url = config(
    ...     config_file=os.path.join(
    ...         os.path.dirname(__file__),
    ...         "config.json.template"
    ...     )
    ... )
    >>> config["girder"]["user"]
    'wong'
    """
    if config_file is None:
        config_file = os.path.join(
            os.path.dirname(__file__),
            "config.json"
        )
    if context_file is None:
        context_file = os.path.join(
            os.path.dirname(__file__),
            "config.json"
        )
    with open (config_file, "r") as j:
        config = json.load(j)
    with open (context_file, "r") as j:
        context = json.load(j)
    api_url = "".join([
        "http://",
        config["girder"]["host"],
        "/api/v1"
    ])
    return(config, context, api_url)
  
  
def connect_to_girder(
    api_url="https://data.kitware.com/api/v1/",
    authentication=None
):
    """
    Function to connect to a Girder DB.
    
    Parameters
    ----------
    api_url: string, optional
        path to running Girder DB API endpoint.
        Default is Kitware Data API
        
    authentication: tuple or string, optional
        (username, password) or APIkey
        (
            username: string
            password: string
        )
        default=None
        
        APIkey: string
            default=None
        
        
    Returns
    -------
    girder_connection: GirderClient
    
    Examples
    --------
    >>> import girder_client as gc
    >>> g = connect_to_girder()
    >>> g.getItem(
    ...     "58cb124c8d777f0aef5d79ff"
    ... )["name"]
    'LARGE_PtCu_NanoParticles-stride-5.html'
    >>> g =connect_to_girder(authentication=("a", "b"))
    Connected to the Girder database 🏗🍃 but could not authenticate.
    >>> g =connect_to_girder(authentication="ab")
    Connected to the Girder database 🏗🍃 but could not authenticate.
    """
    try:
        girder_connection = gc.GirderClient(
            apiUrl=api_url
        ) 
        if authentication:
            if isinstance(
                authentication,
                tuple
            ):
                girder_connection.authenticate(
                    *authentication
                )
            else:
                girder_connection.authenticate(
                    apiKey=authentication
                )
            print(
              "Connected to the Girder database 🏗🍃 and "
              "authenticated."
            )
    except (gc.AuthenticationError, gc.HttpError) as AuthError:
        print(
            "Connected to the Girder database 🏗🍃 but "
            "could not authenticate."
        )
    except:
        print(
            "I am unable to connect to the "
            "Girder database 🏗🍃"
        )
        return(None)
    return(girder_connection)
  
  
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
    >>> connect_to_postgres(
    ...     config(
    ...         config_file=os.path.join(
    ...             os.path.dirname(__file__),
    ...             "config.json.template"
    ...         )
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
        print("Connected to the Postgres database 🐘")
        return(postgres_connection)
    except (
        psycopg2.OperationalError,
        psycopg2.DatabaseError
    ):
        print(
            "I am unable to connect to the "            "Postgres database 🐘"
        )
        return(None)


def get_girder_id_by_name(
    girder_connection,
    entity,
    name,
    parent=None,
    limit=1,
    sortdir=-1,
    index=0
):
    """
    Function to get the `_id` of a single entity in a Girder database.
    
    Parameters
    ----------
    girder_connection: GirderClient
        an active `GirderClient <http://girder.readthedocs.io/en/latest/python-client.html#girder_client.GirderClient>`_
    
    entity: string
        "collection", "folder", "item", "file", "user"
    
    name: string
        name of entity
        
    parent: 2-tuple, optional, default=None
        (parentType, parent_id)
        parentType: string
            "collection", "folder", or "user"
        parendId: string
            Girder _id for parent
        
    limit: int, optional, default=1
        maximum number of query results
        
    sortdir: int, optional, default=-1
        Sort order: 1 for ascending, -1 for descending.
        
    index: int, default=0
        0-indexed index of named entity in given sort order.
        
    Returns
    -------
    _id: string
        Girder _id of requested entity
        
    Example
    -------
    >>> import girder_client as gc
    >>> get_girder_id_by_name(
    ...     girder_connection=gc.GirderClient(
    ...         apiUrl="https://data.kitware.com/api/v1/"
    ...     ),
    ...     entity="collection",
    ...     name="Cinema",
    ...     parent=None,
    ...     sortdir=1
    ... )
    '55706aa58d777f649a9ba164'
    """
    query = "".join([
        entity,
        "?text=" if entity=="collection" else "?name=",
        name,
        "&parentType={0}&parentId={1}".format(
            *parent
        ) if parent else "",
        "&limit=",
        str(limit),
        "&sortdir=",
        str(sortdir)
    ])
    j = json.loads(
        girder_connection.get(
            query,
            jsonResp=False
        ).content.decode(
            "UTF8"
        )
    )
    return(
        j[0]["_id"] if len(
            j
        ) else None
    )

  
def get_files_in_item(
    girder_connection,
    item_id,
    sort="created",
    sortdir=-1
):
    """
    Function to get a dictionary of Files in an Item in
    a Girder database.
    
    Parameters
    ----------
    girder_connection: GirderClient
        an active `GirderClient <http://girder.readthedocs.io/en/latest/python-client.html#girder_client.GirderClient>`_
    
    item_id: string
        Girder _id of Item.
        
    sort: string, optional
        Field to sort the result set by.
        default = "created"
    
    sortdir: int, optional
        Sort order: 1 for ascending, -1 for descending.
        default = -1
    
    Returns
    -------
    files: dictionary or None
        metadata of files in Girder Item
        
    Example
    -------
    >>> import girder_client as gc
    >>> get_files_in_item(
    ...     girder_connection=gc.GirderClient(
    ...         apiUrl="https://data.kitware.com/api/v1/"
    ...     ),
    ...     item_id="58a372f38d777f0721a64df3"
    ... )[0]["name"]
    'Normal001-T1-Flash.mha'
    """
    return(
      girder_connection.get(
        "".join([
          "item/",
          item_id,
          "/files?",
          "sort=",
          sort,
          "&sortdir=",
          str(sortdir)
        ])
      )
    )


def get_user_id_by_email(girder_connection, email):
    """
    Function to get the `_id` of a single User in a Girder database.
    
    Parameters
    ----------
    girder_connection: GirderClient
        an active `GirderClient <http://girder.readthedocs.io/en/latest/python-client.html#girder_client.GirderClient>`_
    
    email: string
        email address
        
    Returns
    -------
    _id: string or None
        Girder _id of requested User, or None if not found
        
    Example
    -------
    >>> import girder_client as gc
    >>> get_user_id_by_email(
    ...     girder_connection=gc.GirderClient(
    ...         apiUrl="https://data.kitware.com/api/v1/"
    ...     ),
    ...     email="test@example.com"
    ... )
    """
    email = email.lower()
    user_ids = [user["_id"] for user in girder_connection.get(
        "".join([
            "user?text=",
            email
        ])
    ) if "email" in user and user["email"]==email]
    return(
        user_ids[0] if len(user_ids) else None
    )
  

def _main():
    """
    Function to execute from commandline to transfer a running
    Postgres DB to a running Girder DB.
    
    "config.json" needs to have its values filled in first.
    """
    # Load configuration
    config, context, api_url = _config() # pragma: no cover
    
    # Connect to Girder
    girder_connection=_connect_to_girder(
        api_url=api_url,
        authentication=(
            config["girder"]["user"],
            config["girder"]["password"]
        )
    ) # pragma: no cover
    
    # Connect to Postgres
    postgres_connection=_connect_to_postgres(
        config["postgres"]
    ) # pragma: no cover
        
    # Get or create activities Collection
    activities_id = postgres_to_girder.get_girder_id_by_name(
        entity="collection",
        name="activities",
        girder_connection=girder_connection
    )
    activities_id = gc.createCollection(
        name="activities",
        public=True
    ) if not activities_id else activities_id
    
    # Get activities and users from Postgres
    acts = pd.io.sql.read_sql_query(
        "SELECT * FROM acts;",
        conn
    )
    users = pd.io.sql.read_sql_query(
        "SELECT * FROM users;",
        conn
    )
    
    # Load users into Girder
    for i in range(users.shape[0]):
        user_id = get_user_id_by_email(
            gc,
            users.loc[i,"email"]
        )
        if user_id:
            print(user_id)
        else:
            gc.post(
                "".join([
                    "user?login=",
                    users.loc[i,"email"].replace(
                        "@",
                        "at"
                    ),
                    "&firstName=",
                    config["missing_persons"]["first_name"] if not users.loc[
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
                    ] else config[
                        "missing_persons"
                    ][
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
                    "true" if "admin" in str(users.loc[
                        i,
                        "role"
                    ]) else "false",
                    "&email=",
                    users.loc[
                        i,
                        "email"
                    ]
                ])
            )
    
    # Pull respondents out of titles in DataFrame from Postgres
    acts["Respondent"] = acts["title"].apply(
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