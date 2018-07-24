import os
import sys
sys.path.append(
    os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            os.pardir
        )
    )
)
from mindlogger_backend_dev import girder_connections
import json

config_path = os.path.join(
    os.path.dirname(__file__),
    os.pardir,
    "mindlogger_backend_dev",
    "config.json"
)
if os.path.exists(config_path):
    config, context, api_url = girder_connections.configuration(
        config_file=config_path,
        which_girder="dev"
    )
    which_girder = "girder-dev"
    girder_connection = girder_connections.connect_to_girder(
        api_url="http://{}/api/v1/".format(config[which_girder]["host"]),
        authentication=(
            config[which_girder]["user"],
            config[which_girder]["password"]
        )
    )

    from mindlogger_backend_dev import update_girder

    config, context, api_url = girder_connections.configuration(
        config_file="{}.template".format(config_path),
        which_girder="dev"
    )

    
