# -*- coding: utf-8 -*-
import copy
import datetime
import json
import os
import six
import cherrypy

from bson.objectid import ObjectId
from girderformindlogger.constants import AccessType
from girderformindlogger.exceptions import ValidationException, GirderException
from girderformindlogger.models.model_base import AccessControlledModel, Model
from girderformindlogger.utility.model_importer import ModelImporter
from girderformindlogger.utility.progress import noProgress, setResponseTimeLimit
from girderformindlogger import events
from bson import json_util

from Cryptodome.Cipher import AES

import random
import string

class AESEncryption(AccessControlledModel):
    """
    This model is used for encrypting fields using AES
    """
    def __init__(self):
        self.fields = []
        super(AESEncryption, self).__init__()

    def initAES(self, fields=[], maxCount=4):
        self.baseKey = cherrypy.config['aes_key'] if 'aes_key' in cherrypy.config else b'a!z%C*f4JanU5kap2te45v9y/A?D(G+K'

        self.AES_KEY = self.baseKey
        self.fields = fields
        self.maxCount = maxCount

    # basic function for aes-encryption
    def encrypt(self, data, maxLength):
        length = len(data)
        if length < maxLength:
            # insert other characters at the end of text so that length of text won't be detected
            data = data + random.choice(string.ascii_letters+string.digits) * (maxLength - len(data))
        data = data + '%0{}d'.format(self.maxCount) % length

        cipher = AES.new(self.AES_KEY, AES.MODE_EAX)
        ciphertext, tag = cipher.encrypt_and_digest(data.encode("utf-8"))
        return ciphertext + cipher.nonce + tag

    # basic function for aes-decryption
    def decrypt(self, data):
        try:
            cipher = AES.new(self.AES_KEY, AES.MODE_EAX, nonce=data[-32:-16])
            plaintext = cipher.decrypt(data[:-32])
            cipher.verify(data[-16:])

            txt = plaintext.decode('utf-8')
            length = int(txt[-self.maxCount: ])

            return ('ok', txt[:length])
        except:
            return ('error', None)

    def navigate(self, document, path):
        current = document
        for node in path:
            if node not in current or not isinstance(current[node], dict):
                return None
            current = current[node]
        return current

    # encrypt selected fields using AES
    def encryptFields(self, document, fields):
        if not document:
            return document

        updateAESKey = getattr(self, 'updateAESKey', None)

        if callable(updateAESKey):
            updateAESKey(document, self.baseKey)

        encodeDocument = getattr(self, 'encodeDocument', None)
        if callable(encodeDocument):
            encodeDocument(document)

        for field in fields:
            path = field[0].split('.')

            key = path.pop()
            data = self.navigate(document, path)

            if data and data.get(key, None) and isinstance(data[key], str):
                encrypted = self.encrypt(data[key], field[1])
                data[key] = encrypted

        self.AES_KEY = self.baseKey
        return document

    # decrypt selected fields using AES
    def decryptFields(self, document, fields):
        if not document:
            return document

        updateAESKey = getattr(self, 'updateAESKey', None)
        if callable(updateAESKey):
            updateAESKey(document, self.baseKey)

        for field in fields:
            path = field[0].split('.')

            key = path.pop()
            data = self.navigate(document, path)

            if data and data.get(key, None) and isinstance(data[key], bytes):
                status, decrypted = self.decrypt(data[key])
                if status == 'ok':
                    data[key] = decrypted

        decodeDocument = getattr(self, 'decodeDocument', None)
        if callable(decodeDocument):
            decodeDocument(document)

        self.AES_KEY = self.baseKey
        return document

    # overwrite functions which save data in mongodb
    def save(self, document, validate=True, triggerEvents=True):
        if validate and triggerEvents:
            event = events.trigger('.'.join(('model', self.name, 'validate')), document)
            if event.defaultPrevented:
                validate = False

        if validate:
            document = self.validate(document)

        self.encryptFields(document, self.fields)
        return self.decryptFields(super().save(document, False, triggerEvents), self.fields)

    def find(self, *args, **kwargs):
        documents = list(super().find(*args, **kwargs))
        for document in documents:
            self.decryptFields(document, self.fields)

        return documents

    def findOne(self, *args, **kwargs):
        document = super().findOne(*args, **kwargs)

        self.decryptFields(document, self.fields)
        return document
