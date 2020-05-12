from girderformindlogger.api.rest import getCurrentUser
from girderformindlogger.constants import AccessType
from girderformindlogger.exceptions import AccessException, ValidationException
from girderformindlogger.models.folder import Folder as FolderModel
from girderformindlogger.models.user import User as UserModel
from girderformindlogger.utility import config
import itertools


def canonicalUser(user):
    thisUser = getCurrentUser()
    try:
        userId = UserModel().load(
            user,
            level=AccessType.NONE,
            user=thisUser
        )
    except:
        return(None)
    try:
        return(str(userId['_id']) if '_id' in userId else None)
    except:
        return(None)


def checkRole(doc, role, user):
    if not isinstance(
        doc,
        dict
    ) or not isinstance(user, dict) or 'roles' not in doc or '_id' not in user:
        return(False)
    if role not in doc['roles']:
        return(False)
    userRole = [
        str(userId['_id']) for userId in doc['roles'][role].get('users', [])
    ]
    cipher = getUserCipher(doc, user['_id'])
    if str(user['_id']) in userRole or (
        cipher is not None and str(cipher) in userRole
    ):
        return(True)
    for group in user.get('groups', []):
        if group in doc.get('roles', {}).get(role, {}).get('groups', []):
            return(True)
    return(False)


def createCipher(applet, appletAssignments, user):
    thisUser = getCurrentUser()
    cUser = None
    try:
        cUser = UserModel().load(
            user,
            level=AccessType.NONE,
            user=thisUser
        )
    except:
        cur_config = config.getConfig()
        if not re.match(cur_config['users']['email_regex'], user):
            raise ValidationException('Invalid email address.', 'user')
    newCipher = FolderModel().createFolder(
        parent=applet,
        name=nextCipher(appletAssignments),
        parentType='folder',
        public=False,
        creator=thisUser,
        reuseExisting=True
    )
    if cUser is None:
        try:
            appletName = FolderModel().preferredName(
                FolderModel().load(
                    applet['meta']['applet']['@id'],
                    level=AccessType.NONE,
                    user=thisUser
                )['name']
            )
        except:
            raise ValidationException('Invalid assignment folder.', 'applet')
        try:
            cUser = UserModel().createUser(
                login="-".join([
                    appletName.replace(' ', ''),
                    str(newCipher['name'])
                ]),
                password=str(uuid.uuid4()),
                firstName=appletName,
                email=user,
                admin=False,
                public=False,
                currentUser=thisUser,
                encryptEmail=True
            )
        except:
            cUser = UserModel().createUser(
                login="-".join([
                    appletName.replace(' ', ''),
                    str(applet['meta']['applet']['@id']),
                    str(FolderModel().preferredName(newCipher))
                ]),
                password=str(uuid.uuid4()),
                firstName=appletName,
                email=user,
                admin=False,
                public=False,
                currentUser=thisUser,
                encryptEmail=True
            )
    newSecretCipher = FolderModel().setMetadata(
        FolderModel().createFolder(
            parent=newCipher,
            name='userID',
            parentType='folder',
            public=False,
            creator=thisUser,
            reuseExisting=True
        ),
        {
            'user': {
                '@id': str(cUser['_id'])
            }
        }
    )
    FolderModel().setAccessList(
        doc=newSecretCipher,
        access={'users': [], 'groups': []},
        save=True,
        user=thisUser,
        force=True
    )
    for u in [thisUser, cUser]:
        FolderModel().setUserAccess(
            doc=newSecretCipher,
            user=u,
            level=None,
            save=True,
            currentUser=thisUser,
            force=True
        )
    for u in [thisUser, cUser]:
        FolderModel().setUserAccess(
            doc=newSecretCipher,
            user=u,
            level=AccessType.READ,
            save=True,
            currentUser=thisUser,
            force=True
        )
    return(newCipher)


def decipherUser(appletSpecificId):
    thisUser = getCurrentUser()
    try:
        ciphered = FolderModel().load(
            appletSpecificId,
            level=AccessType.NONE,
            user=thisUser
        )
        userId = list(FolderModel().find(
            query={
                'parentId': ciphered['_id'],
                'parentCollection': 'folder',
                'name': 'userID'
            }
        ))
    except:
        return(None)
    try:
        cUser = str(
            userId[0]['meta']['user']['@id']
        ) if len(userId) and type(
            userId[0]
        ) == dict and userId[0].get('meta').get('user').get('@id') else None
        FolderModel().setUserAccess(
            doc=ciphered,
            user=UserModel().load(id=cUser, user=cUser),
            level=AccessType.READ,
            save=True,
            currentUser=thisUser,
            force=True
        )
        return(cUser)
    except:
        return(None)


def getCanonicalUser(user):
    try:
        cUser = [
            u for u in [
                decipherUser(user),
                userByEmail(user),
                canonicalUser(user)
            ] if u is not None
        ]
        return(cUser[0] if len(cUser) else None)
    except:
        return(None)


def getUserCipher(appletAssignment, user):
    """
    Returns an applet-specific user ID.

    Parameters
    ----------
    appletAssignment: Mongo Folder cursor
        Applet folder in Assignments collection

    user: string or list
        applet-specific ID, canonical ID or email address

    Returns
    -------
    user: string
        applet-specific ID
    """
    if not isinstance(user, str):
        return([getUserCipher(appletAssignment, u) for u in list(user)])
    thisUser = getCurrentUser()
    appletAssignments = list(FolderModel().childFolders(
        parent=appletAssignment,
        parentType='folder',
        user=thisUser
    ))
    allCiphers = list(itertools.chain.from_iterable([
        list(FolderModel().find(
            query={
                'parentId': assignment.get('_id'),
                'parentCollection': 'folder',
                'name': 'userID'
            }
        )) for assignment in appletAssignments
    ])) if len(appletAssignments) else []
    cUser = getCanonicalUser(user)
    aUser = [
        cipher['parentId'] for cipher in allCiphers if (
            cipher['meta']['user']['@id'] == cUser
        ) if cipher.get('meta') and cipher['meta'].get('user') and cipher[
            'meta'
        ]['user'].get('@id') and cipher.get('parentId')
    ] if cUser and len(allCiphers) else []
    aUser = aUser[0] if len(aUser) else createCipher(
        appletAssignment,
        appletAssignments,
        cUser if cUser is not None else user
    )['_id']
    return(str(aUser))


def nextCipher(currentCiphers):
    if not len(currentCiphers):
        return("1")
    nCipher = []
    for c in [
        cipher.get('name') for cipher in currentCiphers if cipher.get(
            'name'
        ) is not None
    ]:
        try:
            nCipher.append(int(c))
        except:
            nCipher.append(0)
    return(str(max(nCipher)+1))


def userByEmail(email):
    try:
        user = UserModel().findOne({'email': UserModel().hash(email), 'email_encrypted': True})
        if not user:
            user = UserModel().findOne({'email': UserModel().hash(email), 'email_encrypted': {'$ne': True}})
    except:
        return(None)
    try:
        return str(user['_id']) if user else None
    except:
        return(None)
