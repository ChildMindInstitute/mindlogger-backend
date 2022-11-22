# update the owner account with arbitrary server credentials

from girderformindlogger.models.user import User as UserModel
from girderformindlogger.models.account_profile import AccountProfile


def updateAccount(email, db, type, bucket, accessKeyId, secretAccessKey):
    user = UserModel().findOne({'email': UserModel().hash(email), 'email_encrypted': True})

    if user is None:
        user = UserModel().findOne({'email': email, 'email_encrypted': {'$ne': True}})

    if user is None:
        raise AccessException('user not found')

    owner_account = AccountProfile().findOne({
        'userId': user.get('_id'),
        'accountId': user.get('accountId'),
    })

    if owner_account is None:
        raise AccessException('owner_account not found')

    owner_account['db'] = db
    owner_account['bucketType'] = type
    owner_account['s3Bucket'] = bucket
    owner_account['accessKeyId'] = accessKeyId
    owner_account['secretAccessKey'] = secretAccessKey
    AccountProfile().save(owner_account)


if __name__ == '__main__':
    # Azure
    # updateAccount('email@example.com', 'mongodb://mindlogger:xxxxxx@127.0.0.1:27017/mindlogger', 'azure', 'xxxx', 'no', 'DefaultEndpointsProtocol=https;AccountName=xxxx;AccountKey=xxxxx;EndpointSuffix=core.windows.net')
    # S3
    # updateAccount('email@example.com', 'mongodb://mindlogger:xxxxxx@127.0.0.1:27017/mindlogger', 's3', 'mindlogger-bucket', 'AKIAXXXXXXX', 'XXXXXXXXXXXXXXXXXXXXX')
    # clear
    # updateAccount('email@example.com', None, None, None, None, None)
