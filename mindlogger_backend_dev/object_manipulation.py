def drop_empty_keys(d):
    """
    Function to iteratively drop empty keys
    from a given dictionary
    
    Parameters
    ----------
    d: dictionary
    
    Returns
    -------
    d: dictionary
    
    Examples
    --------
    >>> drop_empty_keys(
    ...     {
    ...         "a": None,
    ...         "b": {
    ...             "a": None,
    ...             "b": {}
    ...         },
    ...         "c": [
    ...             "a",
    ...             None,
    ...             {"b": None},
    ...             (
    ...                 "a",
    ...                 {"b": None},
    ...                 "c"
    ...              ),
    ...              ("a", None, "c")
    ...          ]
    ...      }
    ... )
    {'b': {'b': {}}, 'c': ['a', None, {}, ('a', {}, 'c'), ('a', None, 'c')]}
    """
    return(
        {
            k:(
                drop_empty_keys(
                    d[k]
                ) if isinstance(
                    d[k],
                    dict
                ) else type(d[k])(
                    drop_empty_keys(
                        d[k]
                    ) 
                ) if isiterable(d[k]) else d[k]
            ) for k in d if d[
                k
            ] is not None
        } if isinstance (
            d,
            dict
        ) else [
            drop_empty_keys(
                item
            ) for item in d
        ] if isinstance(
            d,
            list
        ) else {
            drop_empty_keys(
                item
            ) for item in d
        } if isinstance(
            d,
            set
        ) else tuple([
            drop_empty_keys(
                item
            ) for item in d
        ]) if isinstance(
            d,
            tuple
        ) else d
    )


def isiterable(item):
    """
    Function to test if an item is an Iterable, ie
    a non-string object that can be iterated over
    
    Parameters
    ----------
    item: anything
    
    Returns
    -------
    isterable: boolean
        Is item iterable?
        
    Examples
    --------
    >>> isiterable(set())
    True
    >>> isiterable(bool())
    False
    """
    try:
        iterator = iter(item)
        return(True)
    except TypeError:
        return(False)