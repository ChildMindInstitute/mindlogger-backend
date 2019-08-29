from girderformindlogger.models.file import File
from girderformindlogger.models.folder import Folder
from girderformindlogger.models.upload import Upload
from six import BytesIO


def testEmptyUploadFromFile(admin, fsAssetstore):
    dest = Folder().childFolders(admin, parentType='user')[0]
    file = Upload().uploadFromFile(BytesIO(b''), size=0, name='empty', parent=dest, user=admin)
    assert File().load(file['_id'], force=True) is not None
    assert file['assetstoreId'] == fsAssetstore['_id']
