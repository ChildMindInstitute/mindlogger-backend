# -*- coding: utf-8 -*-
import copy
import datetime
import json
import os
import six
import math

from bson.objectid import ObjectId
from pyfcm import FCMNotification

from girderformindlogger import events
from girderformindlogger.constants import AccessType
from girderformindlogger.exceptions import ValidationException, GirderException
from girderformindlogger.models.model_base import AccessControlledModel, Model
from girderformindlogger.models.push_notification import PushNotification as PushNotificationModel
from girderformindlogger.models.profile import Profile
from girderformindlogger.utility.model_importer import ModelImporter
from girderformindlogger.utility.progress import noProgress, setResponseTimeLimit
from bson import json_util


class Events(Model):
    """
    collection for manage schedule and notification.
    """

    def initialize(self):
        self.name = 'events'
        self.ensureIndices(
            (
                'applet_id',
                'individualized',
                'data.users'
            )
        )

    def validate(self, document):
        return document

    def deleteEvent(self, event_id):
        self.removeWithQuery({'_id': ObjectId(event_id)})

    def upsertEvent(self, event, applet_id, event_id = None):
        newEvent = {
            'applet_id': applet_id,
            'individualized': False,
            'schedulers': [],
            'sendTime': [],
            'completed_activities': []
        }

        existed_event = self.findOne({'_id': ObjectId(event_id)}, fields=['_id', 'schedulers'])

        if event_id and existed_event:
            newEvent['_id'] = ObjectId(event_id)
            newEvent['schedulers'] = existed_event['schedulers']

        if 'data' in event:
            newEvent['data'] = event['data']
            if 'users' in event['data']:
                newEvent['individualized'] = True
        if 'schedule' in event:
            newEvent['schedule'] = event['schedule']

        newEvent = self.save(newEvent)

        self.setSchedule(newEvent)

        return self.save(newEvent)

    def rescheduleRandomNotifications(self, event):
        if 'data' in event and 'useNotifications' in event['data'] and event['data'][
            'useNotifications']:
            push_notification = PushNotificationModel(event=event, callback=send_push_notification)
            push_notification.random_reschedule()
            self.save(event)

    def hasIndividual(self, applet_id, profileId):
        return (self.findOne({'applet_id': ObjectId(applet_id), 'data.users': profileId}) is not None)

    def getEvents(self, applet_id, individualized):
        events = list(self.find({'applet_id': ObjectId(applet_id), 'individualized': individualized}, fields=['data', 'schedule']))
        for event in events:
            if 'data' in event and 'users' in event['data']:
                event['data'].pop('users')

        return events

    def setSchedule(self, event):
        if 'data' in event and 'useNotifications' in event['data'] and event['data'][
            'useNotifications']:
            if 'notifications' in event['data'] and event['data']['notifications'][0]['start']:
                push_notification = PushNotificationModel(event=event, callback=send_push_notification)
                push_notification.set_schedules()

    def cancelSchedules(self, event):
        pass
        # if 'schedulers' in event and len(event['schedulers']):


    def getSchedule(self, applet_id):
        events = list(self.find({'applet_id': ObjectId(applet_id)}, fields=['data', 'schedule']))

        for event in events:
            event['id'] = event['_id']
            event.pop('_id')

        return {
            "type": 2,
            "size": 1,
            "fill": True,
            "minimumSize": 0,
            "repeatCovers": True,
            "listTimes": False,
            "eventsOutside": True,
            "updateRows": True,
            "updateColumns": False,
            "around": 1585724400000,
            'events': events
        }

    def getScheduleForUser(self, applet_id, user_id, is_coordinator):
        if is_coordinator:
            individualized = False
        else:
            profile = Profile().findOne({'appletId': ObjectId(applet_id), 'userId': ObjectId(user_id)})
            individualized = self.hasIndividual(applet_id, profile['_id'])

        events = self.getEvents(applet_id, individualized)
        for event in events:
            event['id'] = event['_id']
            event.pop('_id')

        return {
            "type": 2,
            "size": 1,
            "fill": True,
            "minimumSize": 0,
            "repeatCovers": True,
            "listTimes": False,
            "eventsOutside": True,
            "updateRows": True,
            "updateColumns": False,
            "around": 1585724400000,
            'events': events
        }


push_service = FCMNotification(
    api_key='AAAAJOyOEz4:APA91bFudM5Cc1Qynqy7QGxDBa-2zrttoRw6ZdvE9PQbfIuAB9SFvPje7DcFMmPuX1IizR1NAa7eHC3qXmE6nmOpgQxXbZ0sNO_n1NITc1sE5NH3d8W9ld-cfN7sXNr6IAOuodtEwQy-',
    proxy_dict={})


def send_push_notification(applet_id, event_id):
    now = datetime.datetime.utcnow()
    now = datetime.datetime.strptime(now.strftime('%Y/%m/%d %H:%M'), '%Y/%m/%d %H:%M')

    event = Events().findOne({'_id': event_id})

    if event:
        event_time = datetime.datetime.strptime(
            f"{now.year}/{now.month}/{now.day} {event['sendTime']}", '%Y/%m/%d %H:%M')

        timezone = (event_time - now).total_seconds() / 3600

        query = {
            'appletId': applet_id,
            'timezone': round(timezone, 2),
            'profile': True
        }

        if event['data']['notifications'][0]['notifyIfIncomplete']:
            query['completed_activities'] = {
                '$elemMatch': {
                    "completed_time": ""
                }
            }

        profiles = list(Profile().find(query=query, fields=['deviceId']))

        device_ids = [profile['deviceId'] for profile in profiles]

        message_title = event['data']['title']
        message_body = event['data']['description']
        push_service.notify_multiple_devices(registration_ids=device_ids,
                                             message_title=message_title,
                                             message_body=message_body)

        if event['data']['notifications'][0]['random']:
            Events().rescheduleRandomNotifications(event)
