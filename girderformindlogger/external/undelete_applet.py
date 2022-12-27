from girderformindlogger.models.folder import Folder
from girderformindlogger.models.account_profile import AccountProfile
from girderformindlogger.models.profile import Profile
from girderformindlogger.models.applet_library import AppletLibrary
from bson.objectid import ObjectId



def undelete(appletId):
    applet = Folder().findOne(query={'_id': appletId})
    applet['meta']['applet'].pop('deleted', None)
    applet['meta']['applet']['published'] = True
    Folder().setMetadata(folder=applet, metadata=applet['meta'])

    appletProfile = Profile().findOne(query={'appletId': appletId})
    appletProfile.pop('deactivated', None)
    Profile().save(appletProfile)

    accountProfiles = list(AccountProfile().find({'accountId': applet['accountId'], 'userId': applet['creatorId']}))
    for accountProfile in accountProfiles:
        AccountProfile().appendApplet(accountProfile, appletId, ['user'])

    # AppletLibrary().addAppletToLibrary(applet)

if __name__ == '__main__':
    undelete(ObjectId('<applet-id>'))
