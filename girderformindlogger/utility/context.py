from girderformindlogger.models.collection import Collection as CollectionModel
from girderformindlogger.models.folder import Folder as FolderModel
from . import jsonld_expander

def getSkin(lang="en-US"):
    """
    Function to return the context for the current instance.

    :param language: ISO language string, optional
    :type language: None
    :returns: context dict
    """
    contextCollection = CollectionModel().findOne({
        'name': 'Context'
    })
    skinFolder = FolderModel().findOne({
        'name': 'Skin',
        'parentCollection': 'collection',
        'parentId': contextCollection.get('_id')
    }) if contextCollection else None
    defaultSkin = {
        'name': '',
        'colors': {
            'primary': '#000000',
            'secondary': '#FFFFFF'
        },
        'about': ''
    }
    skin = skinFolder.get(
        'meta',
        defaultSkin
    ) if skinFolder is not None else defaultSkin
    for s in ['name', 'about']:
        lookup = jsonld_expander.getByLanguage(
            skin.get(s, ""),
            lang if lang and lang not in [
                "@context.@language",
                ""
            ] else None
        )
        skin[s] = lookup if lookup and lookup not in [
            None,
            [{}],
        ] else jsonld_expander.getByLanguage(
            skin[s],
            None
        )
        skin[s] = jsonld_expander.fileObjectToStr(skin[s][0]) if isinstance(
            skin[s],
            list
        ) and len(skin[s]) else skin[s]
    return (skin)
