import girder_client as gc
import json

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
