# -*- coding: utf-8 -*-
import datetime
import json
import os

from bson.objectid import ObjectId
from girderformindlogger.constants import AccessType, DEFINED_RELATIONS, PROFILE_FIELDS
from girderformindlogger.exceptions import ValidationException, AccessException
from girderformindlogger.models.aes_encrypt import AESEncryption, AccessControlledModel
from girderformindlogger.utility.progress import noProgress
from girderformindlogger.models.profile import Profile

class Note(AESEncryption, dict):
    def initialize(self):
        self.name = 'notes'
        self.ensureIndices(
            (
                'appletId',
                'reviewerId',
                'note',
                'updated',
                'created',
                'userProfileId',
                'responseId'
            )
        )

        self.initAES([
            ('note', 256),
        ])

    def validate(self, document):
        if not document.get('appletId', '') or not document.get('reviewerId', ''):
            raise ValidationException('document is invalid.')

        return document

    def addNote(self, appletId, responseId, userProfileId, note, reviewer):
        document = {
            'appletId': ObjectId(appletId),
            'responseId': ObjectId(responseId),
            'userProfileId': ObjectId(userProfileId),
            'note': note,
            'reviewerId': reviewer['_id'],
            'created': datetime.datetime.utcnow(),
            'updated': datetime.datetime.utcnow()
        }

        document = self.save(document)
        document['reviewer'] = {
            'firstName': reviewer['firstName'],
            'lastName': reviewer['lastName']
        }
        document['my_note'] = True

        return document

    def updateNote(self, noteId, note, reviewer):
        document = self.findOne({
            '_id': ObjectId(noteId)
        })

        if document:
            if document['reviewerId'] != reviewer['_id']:
                raise AccessException('permission denied')

            document.update({
                'note': note,
                'updated': datetime.datetime.utcnow()
            })

            document = self.save(document)

            document['reviewer'] = {
                'firstName': reviewer['firstName'],
                'lastName': reviewer['lastName']
            }
            document['my_note'] = True

            return document

        return None

    def deleteNote(self, noteId):
        self.removeWithQuery({
            '_id': ObjectId(noteId)
        })

    def getNotes(self, responseId, reviewer):
        notes = list(self.find({
            'responseId': ObjectId(responseId)
        }))

        profiles = Profile().find({
            '_id': {
                '$in': [note['reviewerId'] for note in notes]
            }
        })

        # reviewer names
        names = {}
        for profile in profiles:
            names[str(profile['_id'])] = {
                'firstName': profile['firstName'],
                'lastName': profile['lastName']
            }


        for note in notes:
            note['reviewer'] = names[str(note['reviewerId'])]
            note['my_note'] = reviewer['_id'] == note['reviewerId']

        return notes
