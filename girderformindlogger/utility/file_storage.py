import os
import boto3
from botocore.errorfactory import ClientError
from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient

DEFAULT_REGION = 'us-east-1'
DEFAULT_CONTAINER_NAME = 'mindlogger'

class S3Storage():
    def __init__(self, s3_client):
        self.s3_client = s3_client

    def checkPathExists(self, uri):
        if '/' not in uri:
            return False
        [bucket, path] = uri.split('://').pop().split('/', 1)
        try:
            self.s3_client.head_object(Bucket=bucket, Key=path)
            return True
        except ClientError as e:
            return False

class AzureStorage():
    def __init__(self, container_client):
        self.container_client = container_client

    def checkPathExists(self, uri):
        if '/' not in uri:
            return False
        # TODO: implement
        # [bucket, path] = uri.split('://').pop().split('/', 1)
        return True


def resolve_from_account(owner_account):
    bucketType = owner_account.get('bucketType', None)
    if bucketType and 'gcp' in bucketType.lower():
        s3_client = boto3.client(
            's3',
            region_name=DEFAULT_REGION,
            endpoint_url="https://storage.googleapis.com",
            aws_access_key_id=owner_account.get('accessKeyId', None),
            aws_secret_access_key=owner_account.get('secretAccessKey', None)
        )
        return S3Storage(s3_client)
    elif bucketType and 'azure' in bucketType.lower():
        blob_service_client = BlobServiceClient.from_connection_string(
            owner_account.get('secretAccessKey', None))
        try:
            container_client = blob_service_client.create_container(DEFAULT_CONTAINER_NAME)
            return AzureStorage(container_client)
        except Exception as ex:
            print('Azure CON Exception:')
            print(ex)
    else:
        s3_client = boto3.client(
            's3',
            region_name=DEFAULT_REGION,
            aws_access_key_id=owner_account.get('accessKeyId', None),
            aws_secret_access_key=owner_account.get('secretAccessKey', None)
        )
        return S3Storage(s3_client)

def resolve_default():
    s3_client = boto3.client('s3', region_name=DEFAULT_REGION,
          aws_access_key_id=os.environ['ACCESS_KEY_ID'],
          aws_secret_access_key=os.environ['SECRET_ACCESS_KEY'])

    return S3Storage(s3_client)
