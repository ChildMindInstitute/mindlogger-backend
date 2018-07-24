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

email="wong@wong.wong"
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

    config, context, api_url = girder_connections.configuration(
        config_file="{}.template".format(config_path),
        which_girder="dev"
    )

    from mindlogger_backend_dev import update_schema

    user_id = update_schema.get_user_id_by_email(
        girder_connection,
        email
    )

    if not user_id:
        user_id = girder_connection.post(
            "&".join([
                "user?login={}".format(config[which_girder]["user"]),
                "firstName=Wong",
                "lastName=Wong",
                "password={}".format(config[which_girder]["password"]),
                "admin=true",
                "email={}".format(email),
                "public=false"
            ])
        )
