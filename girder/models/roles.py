from girder.models.applet import getUserCipher

def checkRole(doc, role, user):
    if not isinstance(
        doc,
        dict
    ) or not isinstance(user, dict) 'roles' not in doc or '_id' not in user:
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
        if group in doc['roles'][role]['groups']:
            return(True)
    return(False)
