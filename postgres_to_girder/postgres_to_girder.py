import requests
import urllib
reusable_entities = {"folder"}

def create_girder_entity(
    entity,
    name,
    host,
    parent=None,
    secure=False,
    description=None,
    public=False,
    metadata=None
):
    """
    Function to add an entity to a Girder database.
    
    Parameters
    ----------
    entity: string
        "collection", "folder", "item", "file", "user"
    
    name: string
        name of entity
       
    host: string
        host name or IP address (without protocol prefix)
        
    parent: 2-tuple, optional, default=None
        (parentType, parent_id)
        parentType: string
            "collection", "folder", or "user"
        parendId: string
            Girder _id for parent
        
    secure: Boolean, optional, default=False
        https?
        
    description: string, optional, default=None
        Entity description.
    
    public: Boolean, optional, default=False
        Whether the entity should be publicly visible.
        
    metadata: JSON object, optional, default=None
        JSON to include in entity's "metadata" object.
        
    Returns
    -------
    j: JSON object
        JSON response from Girder server
        
    Example
    -------
    >>> create_girder_entity(
    ...     entity="collection",
    ...     name="Test post",
    ...     host="data.kitware.com",
    ...     secure=True
    ... )["message"]
    'You must be logged in.'
    """
    r = requests.post(
        "".join([
            "http",
            "s" if secure else "",
            "://",
            host,
            "/api/v1/",
            entity,
            "?text=" if entity=="collection" else "?name=",
            urllib.parse.quote(name),
            "&parentType={0}&parentId={1}".format(
                *parent
            ) if parent else "",
            "&description={0}&".format(
              description
            ) if isinstance(
              description,
              str
            ) else "",
            "&public=",
            str(public),
            "&metadata={0}".format(
                url.parse.quote(metadata)
            ) if metadata else "",
            "&reuseexsiting=True" if entity in reusable_entities else ""
        ])
    )
    return(
        r.json()
    )

def get_girder_id_by_name(
    entity,
    name,
    host,
    secure=False,
    parent=None,
    limit=1,
    sortdir=-1,
    index=0
):
    """
    Function to get the `_id` of a single entity in a Girder database.
    
    Parameters
    ----------
    entity: string
        "collection", "folder", "item", "file", "user"
    
    name: string
        name of entity
       
    host: string
        host name or IP address (without protocol prefix)
        
    secure: Boolean, optional, default=False
        https?
        
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
    >>> get_girder_id_by_name(
    ...     entity="collection",
    ...     name="Cinema",
    ...     host="data.kitware.com",
    ...     secure=True,
    ...     parent=None,
    ...     sortdir=1
    ... )
    '57b5c9e58d777f126827f5a1'
    """
    r = requests.get(
        "".join([
            "http",
            "s" if secure else "",
            "://",
            host,
            "/api/v1/",
            entity,
            "?text=" if entity=="collection" else "?name=",
            urllib.parse.quote(name),
            "&parentType={0}&parentId={1}".format(
                *parent
            ) if parent else "",
            "&limit=",
            str(limit),
            "&sort=created&",
            "sortdir=",
            str(sortdir)
        ])
    )
    j = r.json()
    return(
        j[index]["_id"] if len(
            j
        ) else None
    )
  
def girder_login(username, password, host, secure=False):
    """
    Function to get the `_id` of a single entity in a Girder database.
    
    Parameters
    ----------
    username: string
        Girder DB username
    
    password: string
        name of entity
       
    host: string
        host name or IP address (without protocol prefix)
        
    secure: Boolean, optional, default=False
        https?
        
    Returns
    -------
    message: string
        "Login succeeded.", "Login failed.", or "Connection failed."
        
    Examples
    --------
    >>> girder_login(
    ...     username="Loki",
    ...     password="TheAllfather",
    ...     host="data.kitware.com",
    ...     secure=True
    ... )
    'Login failed.'
    >>> girder_login(
    ...     username="Loki",
    ...     password="TheAllfather",
    ...     host="data.kitware.asgard",
    ...     secure=True
    ... )
    'Connection failed.'
    """
    try:
        r = requests.get(
            "".join([
                "http",
                "s" if secure else "",
                "://",
                "{0}:{1}@".format(
                    username,
                    password
                ),
                host,
                "/api/v1/",
                "user/authentication"
            ])
        )
        return(
            r.json()["message"]
        )
    except:
        return("Connection failed.")