from girderformindlogger.models.folder import Folder
from girderformindlogger.models.account_profile import AccountProfile
from girderformindlogger.models.profile import Profile
from girderformindlogger.models.user import User as UserModel
from girderformindlogger.models.group import Group as GroupModel
from girderformindlogger.models.applet import Applet
from girderformindlogger.constants import AccessType, USER_ROLES
from girderformindlogger.exceptions import ValidationException
# from girderformindlogger.models.applet_library import AppletLibrary

from bson.objectid import ObjectId

def undelete(appletId):
    applet = Folder().findOne(query={'_id': appletId})
    applet['meta']['applet'].pop('deleted', None)
    applet['meta']['applet']['published'] = True
    Folder().setMetadata(folder=applet, metadata=applet['meta'])

    appletProfiles = list(Profile().find(query={'appletId': appletId, 'deactivated': True}))
    for appletProfile in appletProfiles:
        appletProfile.pop('deactivated', None)
        Profile().save(appletProfile)

    accountProfiles = list(AccountProfile().find({'accountId': applet['accountId'], 'userId': applet['creatorId']}))
    for accountProfile in accountProfiles:
        AccountProfile().appendApplet(accountProfile, appletId, ['user'])

    # AppletLibrary().addAppletToLibrary(applet)

def get_roles_in_applet(applet, user):
    roles = []
    appletGroups = Applet().getAppletGroups(applet)
    for role in list(USER_ROLES.keys()):
        groups = appletGroups.get(role)
        for groupId in list(groups.keys()):
            group = GroupModel().load(groupId, force=True)
            for userAccess in group['access']['users']:
                if (user['_id'] == userAccess['id']):
                    roles.append(role)
    return roles

def create_default_groups(applet, user):
    appletGroupName = "Default {} ({})".format(
        applet['name'],
        str(applet.get('_id', ''))
    )
    role2AccessLevel = {'user': AccessType.READ, 'coordinator': AccessType.ADMIN,
                        'manager': AccessType.ADMIN, 'editor': AccessType.WRITE,
                        'reviewer': AccessType.READ}
    accessList = applet.get('access', {})

    appletGroups = Applet().getAppletGroups(applet)
    for role in USER_ROLES.keys():
        exists = role in appletGroups and appletGroups[role] != {}
        if not exists:
            try:
                group = GroupModel().createGroup(
                    name="{} {}s".format(appletGroupName, role.title()),
                    creator=user,
                    public=False if role=='user' else True
                )
                accessList['groups'].append({ 'id': ObjectId(group['_id']), 'level': role2AccessLevel[role] })

            except ValidationException:
                numero = 0
                numberedName = appletGroupName
                while GroupModel().findOne(query={'name': numberedName}):
                    numero += 1
                    numberedName = "{} {} {}s".format(
                        appletGroupName,
                        str(numero),
                        role.title()
                    )
                group = GroupModel().createGroup(
                    name=numberedName,
                    creator=user,
                    public=False if role=='user' else True
                )
            Applet().setGroupRole(
                doc=applet,
                group=group,
                role=role,
                currentUser=user,
                force=False
            )
    Applet().setAccessList(applet, accessList)
    Applet().update({'_id': ObjectId(applet['_id'])}, {'$set': {'access': applet.get('access', {})}})

def restore_profile(appletId, email):
    applet = Folder().findOne(query={'_id': appletId})
    print('applet', applet['name'], applet['_id'])

    user = UserModel().findOne({'email': UserModel().hash(email), 'email_encrypted': True})
    if user is None:
        user = UserModel().findOne({'email': email, 'email_encrypted': {'$ne': True}})
    print('user', user['email'], user['_id'])

    print('Creating default groups....')
    create_default_groups(applet, user)

    appletProfile = Profile().findOne(query={'appletId': appletId, 'userId': user['_id']})
    if appletProfile is None:
        print('Creating profile....')
        appletProfile = Profile().createProfile(applet, user, 'user')
        appletProfile = Profile().findOne(query={'_id': appletProfile['_id']})
        appletProfile['roles'] = get_roles_in_applet(applet, user)
        Profile().save(appletProfile)

    print('applet profile', appletProfile['_id'])
    print('roles in applet before', appletProfile['roles'])
    print('Creating account profile....')
    accountProfile = AccountProfile().createAccountProfile(applet['accountId'], user['_id'])
    print('account profile', accountProfile['accountName'], accountProfile['_id'])

    print('Granting access....')
    Applet().grantRole(applet, appletProfile, 'manager', [user])
    print('roles in applet after', appletProfile['roles'])


if __name__ == '__main__':
    undelete(ObjectId('63e63462ed51ea5e266d12a0'))
    restore_profile(ObjectId('63e63462ed51ea5e266d12a0'), 'test_account2@ml.com')
