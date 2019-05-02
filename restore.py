import girder_client as gc
import json

# Get credentials
with open("config.json", "r") as fp:
    config=json.load(fp)
    
# Connect to Girder
girder_connection = gc.GirderClient(
    apiUrl="{}/api/v1/".format(
        config["girder-production"]["host"]
    )
)
# Log in
girder_connection.authenticate(
    username=config["girder-production"][
        "user"
    ],
    password=config["girder-production"][
        "password"
    ]
)
# Get EMA: Parent
emaParentMeta = girder_connection.getFolder(
    '5bd87caa336da80de9145af2'
)['meta']
# Add/restore all users
emaParentMeta['members']['users'] = [
    u['_id'] for u in girder_connection.get(
        'user'
    )
]
# Make sure Tabinda's a manager
emaParentMeta['members']['managers'] = list({
    *emaParentMeta['members']['managers'],
    '5c92a7868990750e252b5f72'
})
# Let Anisha see everyone's data
emaParentMeta['members']['viewers'][
    '5bdb6a97336da80de9145e35'
] = emaParentMeta['members']['users']
# Push to server, return True on success
girder_connection.put(
    'folder/'
    '5bd87caa336da80de9145af2/'
    'metadata',
    data={
        'metadata': json.dumps(
            emaParentMeta
        )
    }
)['_id'] == '5bd87caa336da80de9145af2'