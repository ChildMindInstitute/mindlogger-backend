#!/usr/bin/env python
# -*- coding: utf-8 -*-

###############################################################################
#  Copyright 2014 Kitware Inc.
#
#  Licensed under the Apache License, Version 2.0 ( the "License" );
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
###############################################################################

import boto3
import botocore
import cherrypy
import json
import re
import requests
import six
import uuid

from girder import logger, events
from girder.models.model_base import GirderException, ValidationException
from .abstract_assetstore_adapter import AbstractAssetstoreAdapter

BUF_LEN = 65536  # Buffer size for download stream


class S3AssetstoreAdapter(AbstractAssetstoreAdapter):
    """
    This assetstore type stores files on S3. It is responsible for generating
    HMAC-signed messages that authorize the client to communicate directly with
    the S3 server where the files are stored.
    """

    CHUNK_LEN = 1024 * 1024 * 32  # Chunk size for uploading
    HMAC_TTL = 120  # Number of seconds each signed message is valid

    @staticmethod
    def validateInfo(doc):
        """
        Makes sure the root field is a valid absolute path and is writeable.
        """
        if 'prefix' not in doc:
            doc['prefix'] = ''
        # remove slashes from front and back of the prefix
        doc['prefix'] = doc['prefix'].strip('/')
        if not doc.get('bucket'):
            raise ValidationException('Bucket must not be empty.', 'bucket')

        # construct a set of connection parameters based on the keys and the service
        if 'service' not in doc:
            doc['service'] = ''
        if doc['service'] != '':
            if not re.match('^((https?)://)?([^:/]+)(:([0-9]+))?$', doc['service']):
                raise ValidationException(
                    'The service must of the form [http[s]://](host domain)[:(port)].', 'service')
        params = makeBotoConnectParams(doc['accessKeyId'], doc['secret'], doc['service'])
        client = _botoS3(params)
        if doc.get('readOnly'):
            try:
                client.head_bucket(Bucket=doc['bucket'])
            except Exception:
                logger.exception('S3 assetstore validation exception')
                raise ValidationException(
                    'Unable to connect to bucket "%s".' % doc['bucket'], 'bucket')
        else:
            # Make sure we can write into the given bucket using boto
            try:
                key = '/'.join(filter(None, (doc['prefix'], 'girder_test')))
                client.put_object(Bucket=doc['bucket'], Key=key, Body=b'')
                client.delete_object(Bucket=doc['bucket'], Key=key)
            except Exception:
                logger.exception('S3 assetstore validation exception')
                raise ValidationException(
                    'Unable to write into bucket "%s".' % doc['bucket'], 'bucket')

        return doc

    def __init__(self, assetstore):
        super(S3AssetstoreAdapter, self).__init__(assetstore)
        if all(k in self.assetstore for k in ('accessKeyId', 'secret', 'service')):
            self.connectParams = makeBotoConnectParams(
                self.assetstore['accessKeyId'], self.assetstore['secret'],
                self.assetstore['service'])

    def _getRequestHeaders(self, upload):
        return {
            'Content-Disposition': 'attachment; filename="%s"' % upload['name'],
            'Content-Type': upload.get('mimeType', ''),
            'x-amz-acl': 'private',
            'x-amz-meta-uploader-id': str(upload['userId']),
            'x-amz-meta-uploader-ip': str(cherrypy.request.remote.ip)
        }

    def initUpload(self, upload):
        """
        Build the request required to initiate an authorized upload to S3.
        """
        if upload['size'] <= 0:
            return upload

        uid = uuid.uuid4().hex
        key = '/'.join(filter(
            None, (self.assetstore.get('prefix', ''), uid[:2], uid[2:4], uid)))
        path = '/%s/%s' % (self.assetstore['bucket'], key)
        chunked = upload['size'] > self.CHUNK_LEN
        client = _botoS3(self.connectParams)
        headers = self._getRequestHeaders(upload)
        params = {
            'Bucket': self.assetstore['bucket'],
            'Key': key,
            'ACL': headers['x-amz-acl'],
            'ContentDisposition': headers['Content-Disposition'],
            'ContentType': headers['Content-Type'],
            'Metadata': {
                'uploader-id': headers['x-amz-meta-uploader-id'],
                'uploader-ip': headers['x-amz-meta-uploader-ip']
            }
        }
        requestInfo = {
            'headers': headers,
            'method': 'PUT'
        }
        upload['behavior'] = 's3'
        upload['s3'] = {
            'chunked': chunked,
            'chunkLength': self.CHUNK_LEN,
            'relpath': path,
            'key': key,
            'request': requestInfo
        }

        if chunked:
            method = 'create_multipart_upload'
            requestInfo['method'] = 'POST'
        else:
            method = 'put_object'
            params['ContentLength'] = upload['size']

        requestInfo['url'] = client.generate_presigned_url(ClientMethod=method, Params=params)
        return upload

    def uploadChunk(self, upload, chunk):
        """
        Rather than processing actual bytes of the chunk, this will generate
        the signature required to upload the chunk. Clients that do not support
        direct-to-S3 upload can pass the chunk via the request body as with
        other assetstores, and Girder will proxy the data through to S3.

        :param chunk: This should be a JSON string containing the chunk number
            and S3 upload ID. If a normal chunk file-like object is passed,
            we will send the data to S3.
        """
        if isinstance(chunk, six.string_types):
            return self._clientUploadChunk(upload, chunk)
        else:
            return self._proxiedUploadChunk(upload, chunk)

    def _clientUploadChunk(self, upload, chunk):
        """
        Clients that support direct-to-S3 upload behavior will go through this
        method by sending a normally-encoded form string as the chunk parameter,
        containing the required JSON info for uploading. This generates the
        signed URL that the client should use to upload the chunk to S3.
        """
        info = json.loads(chunk)
        index = int(info['partNumber']) - 1
        length = min(self.CHUNK_LEN, upload['size'] - index * self.CHUNK_LEN)

        if 'contentLength' in info and int(info['contentLength']) != length:
            raise ValidationException('Expected chunk size %d, but got %d.' % (
                length, info['contentLength']))

        if length <= 0:
            raise ValidationException('Invalid chunk length %d.' % length)

        client = _botoS3(self.connectParams)
        url = client.generate_presigned_url(ClientMethod='upload_part', Params={
            'Bucket': self.assetstore['bucket'],
            'Key': upload['s3']['key'],
            'ContentLength': length,
            'UploadId': info['s3UploadId'],
            'PartNumber': info['partNumber']
        })

        upload['s3']['uploadId'] = info['s3UploadId']
        upload['s3']['partNumber'] = info['partNumber']
        upload['s3']['request'] = {
            'method': 'PUT',
            'url': url
        }

        return upload

    def _proxiedUploadChunk(self, upload, chunk):
        """
        Clients that do not support direct-to-S3 upload behavior will go through
        this method by sending the chunk data as they normally would for other
        assetstore types. Girder will send the data to S3 on behalf of the client.
        """
        client = _botoS3(self.connectParams)

        if upload['s3']['chunked']:
            if 'uploadId' not in upload['s3']:
                # Initiate a new multipart upload if this is the first chunk
                disp = 'attachment; filename="%s"' % upload['name']
                mime = upload.get('mimeType', '')
                mp = client.create_multipart_upload(
                    Bucket=self.assetstore['bucket'], Key=upload['s3']['key'],
                    ACL='private', ContentDisposition=disp, ContentType=mime,
                    Metadata={
                        'uploader-id': str(upload['userId']),
                        'uploader-ip': str(cherrypy.request.remote.ip)
                    })
                upload['s3']['uploadId'] = mp['UploadId']
                upload['s3']['keyName'] = mp['Key']
                upload['s3']['partNumber'] = 0

            upload['s3']['partNumber'] += 1
            size = chunk.getSize()
            headers = {
                'Content-Length': str(size)
            }

            # We can't just call upload_part directly because they require a
            # seekable file object, and ours isn't.
            url = client.generate_presigned_url(ClientMethod='upload_part', Params={
                'Bucket': self.assetstore['bucket'],
                'Key': upload['s3']['key'],
                'ContentLength': size,
                'UploadId': upload['s3']['uploadId'],
                'PartNumber': upload['s3']['partNumber']
            })

            resp = requests.request(method='PUT', url=url, data=chunk, headers=headers)
            if resp.status_code not in (200, 201):
                logger.error('S3 multipart upload failure %d (uploadId=%s):\n%s' % (
                    resp.status_code, upload['_id'], resp.text))
                raise GirderException('Upload failed (bad gateway)')

            upload['received'] += size
        else:
            size = chunk.getSize()
            if size < upload['size']:
                raise ValidationException('Uploads of this length must be sent in a single chunk.')

            reqInfo = upload['s3']['request']
            resp = requests.request(
                method=reqInfo['method'], url=reqInfo['url'], data=chunk,
                headers=dict(reqInfo['headers'], **{'Content-Length': str(size)}))
            if resp.status_code not in (200, 201):
                logger.error('S3 upload failure %d (uploadId=%s):\n%s' % (
                    resp.status_code, upload['_id'], resp.text))
                raise GirderException('Upload failed (bad gateway)')

            upload['received'] = size

        return upload

    def requestOffset(self, upload):
        if upload['received'] > 0:
            # This is only set when we are proxying the data to S3
            return upload['received']

        if upload['s3']['chunked']:
            raise ValidationException(
                'You should not call requestOffset on a chunked direct-to-S3 upload.')

        headers = self._getRequestHeaders(upload)
        client = _botoS3(self.connectParams)
        url = client.generate_presigned_url(ClientMethod='put_object', Params={
            'Bucket': self.assetstore['bucket'],
            'Key': upload['s3']['key'],
            'ACL': headers['x-amz-acl'],
            'ContentDisposition': headers['Content-Disposition'],
            'ContentLength': upload['size'],
            'ContentType': headers['Content-Type'],
            'Metadata': {
                'uploader-id': headers['x-amz-meta-uploader-id'],
                'uploader-ip': headers['x-amz-meta-uploader-ip']
            }
        })

        return {
            'method': 'PUT',
            'url': url,
            'headers': headers,
            'offset': 0
        }

    def finalizeUpload(self, upload, file):
        if upload['size'] <= 0:
            return file

        file['relpath'] = upload['s3']['relpath']
        file['s3Key'] = upload['s3']['key']

        if upload['s3']['chunked']:
            client = _botoS3(self.connectParams)

            if upload['received'] > 0:
                # We proxied the data to S3
                parts = client.list_parts(
                    Bucket=self.assetstore['bucket'], Key=file['s3Key'],
                    UploadId=upload['s3']['uploadId'])
                parts = [{
                    'ETag': part['ETag'],
                    'PartNumber': part['PartNumber']
                } for part in parts.get('Parts', [])]
                client.complete_multipart_upload(
                    Bucket=self.assetstore['bucket'], Key=file['s3Key'],
                    UploadId=upload['s3']['uploadId'], MultipartUpload={'Parts': parts})
            else:
                url = client.generate_presigned_url(
                    ClientMethod='complete_multipart_upload', Params={
                        'Bucket': self.assetstore['bucket'],
                        'Key': upload['s3']['key'],
                        'UploadId': upload['s3']['uploadId']
                    })
                file['s3FinalizeRequest'] = {
                    'method': 'POST',
                    'url': url,
                    'headers': {'Content-Type': 'text/plain;charset=UTF-8'}
                }
                file['additionalFinalizeKeys'] = ('s3FinalizeRequest',)
        return file

    def downloadFile(self, file, offset=0, headers=True, endByte=None,
                     contentDisposition=None, extraParameters=None, **kwargs):
        """
        When downloading a single file with HTTP, we redirect to S3. Otherwise,
        e.g. when downloading as part of a zip stream, we connect to S3 and
        pipe the bytes from S3 through the server to the user agent.
        """
        if file['size'] <= 0:
            if headers:
                self.setContentHeaders(file, 0, 0)

            def stream():
                yield ''
            return stream

        params = {
            'Bucket': self.assetstore['bucket'],
            'Key': file['s3Key']
        }

        if contentDisposition == 'inline' and not file.get('imported'):
            params['ResponseContentDisposition'] = 'inline; filename="%s"' % file['name']

        url = _botoS3(self.connectParams).generate_presigned_url(
            ClientMethod='get_object', Params=params)

        if headers:
            raise cherrypy.HTTPRedirect(url)
        else:
            def stream():
                pipe = requests.get(url, stream=True)
                for chunk in pipe.iter_content(chunk_size=BUF_LEN):
                    if chunk:
                        yield chunk
            return stream

    def importData(self, parent, parentType, params, progress, user, client=None, **kwargs):
        importPath = params.get('importPath', '').strip().lstrip('/')

        if importPath and not importPath.endswith('/'):
            importPath += '/'

        client = client or _botoS3(self.connectParams)
        bucket = self.assetstore['bucket']
        resp = client.list_objects(Bucket=bucket, Prefix=importPath, Delimiter='/')

        # Start with objects
        for obj in resp.get('Contents', []):
            if progress:
                progress.update(message=obj['Key'])

            name = obj['Key'].rsplit('/', 1)[-1]
            if not name:
                continue

            if parentType != 'folder':
                raise ValidationException(
                    'Keys cannot be imported directly underneath a %s.' % parentType)

            if self.shouldImportFile(obj['Key'], params):
                item = self.model('item').createItem(
                    name=name, creator=user, folder=parent, reuseExisting=True)
                file = self.model('file').createFile(
                    name=name, creator=user, item=item, reuseExisting=True,
                    assetstore=self.assetstore, mimeType=None, size=obj['Size'])
                file['s3Key'] = obj['Key']
                file['imported'] = True
                self.model('file').save(file)

        # Now recurse into subdirectories
        for obj in resp.get('CommonPrefixes', []):
            if progress:
                progress.update(message=obj['Prefix'])

            name = obj['Prefix'].rstrip('/').rsplit('/', 1)[-1]

            folder = self.model('folder').createFolder(
                parent=parent, name=name, parentType=parentType, creator=user,
                reuseExisting=True)
            self.importData(parent=folder, parentType='folder', params={
                'importPath': obj['Prefix']
            }, progress=progress, user=user, client=client, **kwargs)

    def deleteFile(self, file):
        """
        We want to queue up files to be deleted asynchronously since it requires
        an external HTTP request per file in order to delete them, and we don't
        want to wait on that.

        Files that were imported as pre-existing data will not actually be
        deleted from S3, only their references in Girder will be deleted.
        """
        if file['size'] > 0 and 'relpath' in file:
            q = {
                'relpath': file['relpath'],
                'assetstoreId': self.assetstore['_id']
            }
            matching = self.model('file').find(q, limit=2, fields=[])
            if matching.count(True) == 1:
                events.daemon.trigger('_s3_assetstore_delete_file', {
                    'connectParams': self.connectParams,
                    'bucket': self.assetstore['bucket'],
                    'key': file['s3Key']
                })

    def fileUpdated(self, file):
        """
        On file update, if the name or the MIME type changed, we must update
        them accordingly on the S3 key so that the file downloads with the
        correct name and content type.
        """
        if file.get('imported'):
            return

        client = _botoS3(self.connectParams)
        bucket = self.assetstore['bucket']
        try:
            key = client.head_object(Bucket=bucket, Key=file['s3Key'])
        except botocore.exceptions.ClientError:
            return

        disp = 'attachment; filename="%s"' % file['name']
        mime = file.get('mimeType') or ''

        if key['ContentType'] != mime or key['ContentDisposition'] != disp:
            client.copy_object(
                Bucket=bucket, Key=file['s3Key'], Metadata=key['Metadata'],
                CopySource={'Bucket': bucket, 'Key': file['s3Key']}, ContentDisposition=disp,
                ContentType=mime, MetadataDirective='REPLACE')

    def cancelUpload(self, upload):
        """
        Delete the temporary files associated with a given upload.
        """
        if 'key' not in upload.get('s3', {}):
            return
        bucket = self.assetstore['bucket']
        key = upload['s3']['key']

        client = _botoS3(self.connectParams)
        client.delete_object(Bucket=bucket, Key=key)

        # check if this is an abandoned multipart upload
        if 'uploadId' in upload['s3']:
            try:
                client.abort_multipart_upload(
                    Bucket=bucket, Key=key, UploadId=upload['s3']['uploadId'])
            except botocore.exceptions.ClientError:
                pass

    def untrackedUploads(self, knownUploads=None, delete=False):
        """
        List and optionally discard uploads that are in the assetstore but not
        in the known list.

        :param knownUploads: a list of upload dictionaries of all known incomplete uploads.
        :type knownUploads: list
        :param delete: if True, delete any unknown uploads.
        :type delete: bool
        :returns: a list of unknown uploads.
        """
        if self.assetstore.get('readOnly'):
            return []

        untrackedList = []
        prefix = self.assetstore.get('prefix', '')
        if prefix:
            prefix += '/'

        if knownUploads is None:
            knownUploads = []

        bucket = self.assetstore['bucket']
        getParams = {'Bucket': bucket}
        client = _botoS3(self.connectParams)

        while True:
            multipartUploads = client.list_multipart_uploads(**getParams)
            if not multipartUploads.get('Uploads'):
                break
            for upload in multipartUploads['Uploads']:
                if self._uploadIsKnown(upload, knownUploads):
                    continue
                # don't include uploads with a different prefix; this allows a
                # single bucket to handle multiple assetstores and us to only
                # clean up the one we are in.  We could further validate that
                # the key name was of the format /(prefix)/../../(id)
                if not upload['Key'].startswith(prefix):
                    continue
                untrackedList.append({
                    's3': {
                        'uploadId': upload['UploadId'],
                        'key': upload['Key'],
                        'created': upload['Initiated']
                    }
                })
                if delete:
                    client.abort_multipart_upload(
                        Bucket=bucket, Key=upload['Key'], UploadId=upload['UploadId'])
            if not multipartUploads['IsTruncated']:
                break
            getParams['KeyMarker'] = multipartUploads['NextKeyMarker']
            getParams['UploadIdMarker'] = multipartUploads['NextUploadIdMarker']
        return untrackedList

    def _uploadIsKnown(self, multipartUpload, knownUploads):
        """
        Check if a multipartUpload as returned by boto is in our list of known uploads.

        :param multipartUpload: an upload entry from get_all_multipart_uploads.
        :param knownUploads: a list of our known uploads.
        :results: Whether the upload is known
        """
        for upload in knownUploads:
            if ('s3' in upload and 'uploadId' in upload['s3'] and
                    'key' in upload['s3']):
                if (multipartUpload['UploadId'] == upload['s3']['uploadId'] and
                        multipartUpload['Key'] == upload['s3']['key']):
                    return True
        return False


def _botoS3(connectParams):
    """
    Get a connection to the S3 server using the given connection params.

    :param connectParams: Kwargs to pass to the client constructor.
    :type connectParams: dict
    """
    try:
        return boto3.client('s3', **connectParams)
    except Exception:
        logger.exception('S3 assetstore validation exception')
        raise ValidationException('Unable to connect to S3 assetstore')


def makeBotoConnectParams(accessKeyId, secret, service=None):
    """
    Create a dictionary of values to pass to the boto connect_s3 function.

    :param accessKeyId: the S3 access key ID
    :param secret: the S3 secret key
    :param service: alternate service URL
    :returns: boto connection parameter dictionary.
    """
    if accessKeyId and secret:
        params = {
            'aws_access_key_id': accessKeyId,
            'aws_secret_access_key': secret,
            'config': botocore.client.Config(signature_version='s3v4')
        }
    else:
        params = {
            'config': botocore.client.Config(signature_version=botocore.UNSIGNED)
        }

    if service:
        serviceRe = re.match('^((https?)://)?([^:/]+)(:([0-9]+))?$', service)
        if serviceRe.groups()[1] == 'http':
            params['use_ssl'] = False
        params['endpoint_url'] = service

    # TODO(zach) region parameter? Might not be necessary
    return params


def _deleteFileImpl(event):
    _botoS3(event.info['connectParams']).delete_object(
        Bucket=event.info['bucket'], Key=event.info['key'])


events.bind('_s3_assetstore_delete_file', '_s3_assetstore_delete_file', _deleteFileImpl)
