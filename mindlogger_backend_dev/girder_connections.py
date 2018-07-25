import girder_client as gc
import json
import os
from contextlib import suppress


def configuration(
    config_file=None,
    context_file=None,
    which_girder="dev"
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

    which_girder: string, optional
        "dev" or "production"
        default = "dev"

    Returns
    -------
    config: dictionary

    context: dictionary

    api_url: string

    Example
    -------
    >>> config_file = os.path.join(
    ...    os.path.dirname(__file__),
    ...    "config.json.template"
    ... )
    >>> config, context, api_url = configuration(
    ...     config_file=config_file
    ... )
    >>> config["girder-dev"]["user"]
    'wongwongwong'
    >>> try:
    ...     girder_connection = configuration()
    ... except FileNotFoundError:
    ...     pass
    """
    if config_file is None:
        config_file = os.path.join(
            os.path.dirname(__file__),
            "config.json"
        )
    if context_file is None:
        context_file = os.path.join(
            os.path.dirname(__file__),
            "context.json"
        )
    with open (config_file, "r") as j:
        config = json.load(j)
    with open (context_file, "r") as j:
        context = json.load(j)
    api_url = "".join([
        "http://",
        config["girder-{}".format(
            which_girder
        )]["host"],
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
    Connected to the Girder database 🏗🍃 but could not authenticate without \
username and password.
    >>> g.getItem(
    ...     "58cb124c8d777f0aef5d79ff"
    ... )["name"]
    'LARGE_PtCu_NanoParticles-stride-5.html'
    >>> g = connect_to_girder(authentication=("a", "b"))
    Connected to the Girder database 🏗🍃 but could not authenticate.
    >>> g = connect_to_girder(authentication="ab")
    Connected to the Girder database 🏗🍃 but could not authenticate.
    >>> import os
    >>> config_file = os.path.join(
    ...    os.path.dirname(__file__),
    ...    "config.json.template"
    ... )
    >>> config, context, api_url = configuration(
    ...     config_file=config_file
    ... )
    >>> girder_connection = connect_to_girder(
    ...     api_url=api_url,
    ...     authentication=(
    ...         config["girder-dev"]["user"],
    ...         config["girder-dev"]["password"]
    ...     )
    ... )
    Connected to the Girder database 🏗🍃 and authenticated.
    >>> connect_to_girder(
    ...     api_url=config["girder-dev"]["password"],
    ...     authentication=(
    ...         config["girder-dev"]["user"],
    ...         config["girder-dev"]["password"]
    ...     )
    ... )
    I am unable to connect to the Girder database 🏗🍃
    """
    girder_connection = gc.GirderClient(
        apiUrl=api_url
    )
    if (
        not authentication or
        isinstance(
            authentication,
            type(None)
        )
    ):
        print(
            "Connected to the Girder database 🏗🍃 but "
            "could not authenticate without username and password."
        )
    else:
        try:
            girder_connection.authenticate(
                *authentication
            ) if len(
                authentication
            )==2 else girder_connection.authenticate(
                authentication[0],
                authentication[1],
                apiKey=authentication[2]
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
