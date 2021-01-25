# -*- coding: utf-8 -*-
import copy
import datetime
import json
import os
import six

from bson.objectid import ObjectId
from girderformindlogger import events
from girderformindlogger.constants import AccessType
from girderformindlogger.exceptions import ValidationException, GirderException
from girderformindlogger.models.model_base import AccessControlledModel, Model
from girderformindlogger.models.push_notification import PushNotification as PushNotificationModel
from girderformindlogger.models.profile import Profile
from girderformindlogger.models.folder import Folder
from girderformindlogger.utility.model_importer import ModelImporter
from girderformindlogger.utility.progress import noProgress, setResponseTimeLimit
from bson import json_util
from girderformindlogger.models.profile import Profile as ProfileModel
from dateutil.relativedelta import relativedelta

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
                'data.users',
                'data.activity_id'
            )
        )

    def validate(self, document):
        return document
    
    def updateScheduleUpdateTime(self, event):
        if event['individualized']:
            ProfileModel().update(query={
                    "_id": {
                        "$in": event['data']['users']
                    }
                }, 
                update={
                    '$set': {
                        'scheduleUpdateTime': now
                    }
                }
            )
        else:
            ProfileModel().update(
                query={
                    "_id": {
                        "$in": event['applet_id']
                    },
                },
                update={
                    '$set': {
                        'scheduleUpdateTime': now
                    }
                }
            )

    def deleteEvent(self, event_id):
        event = self.findOne({'_id': ObjectId(event_id)})

        if event:
            self.updateScheduleUpdateTime(event)

            if event['individualized']:
                ProfileModel().update(query={
                    "_id": {
                        "$in": event['data']['users']
                    }
                    }, update={'$inc': {
                        'individual_events': -1
                    }
                })

            push_notification = PushNotificationModel(event=event)
            push_notification.remove_schedules()
            self.removeWithQuery({'_id': ObjectId(event_id)})

    def deleteEventsByAppletId(self, applet_id):
        events = self.find({'applet_id': ObjectId(applet_id)})

        for event in events:
            self.deleteEvent(event.get('_id'))

    def deleteEventsByActivityId(self, applet_id, activity_id):
        events = self.find({'applet_id': ObjectId(applet_id), 'data.activity_id': ObjectId(activity_id)})

        for event in events:
            self.deleteEvent(event.get('_id'))

    def upsertEvent(self, event, applet, event_id=None):
        newEvent = {
            'applet_id': applet['_id'],
            'individualized': False,
            'schedulers': [],
            'sendTime': [],
            'data': {}
        }
        existed_event = self.findOne({'_id': ObjectId(event_id)}, fields=['_id', 'schedulers', 'data'])

        if event_id and existed_event:
            newEvent['_id'] = ObjectId(event_id)
            newEvent['schedulers'] = existed_event.get('schedulers', [])

        if 'data' in event:
            newEvent['data'] = event['data']

            if 'activity_id' in newEvent['data']:
                newEvent['data']['activity_id'] = ObjectId(newEvent['data']['activity_id'])

            if 'users' in event['data'] and isinstance(event['data']['users'], list):
                newEvent['individualized'] = True
                event['data']['users'] = [ObjectId(profile_id) for profile_id in event['data']['users']]

                self.updateIndividualSchedulesParameter(newEvent, existed_event)

        if 'schedule' in event:
            newEvent['schedule'] = event['schedule']

        newEvent = self.save(newEvent)
        self.setSchedule(newEvent)

        newEvent = self.save(newEvent)

        self.updateScheduleUpdateTime(newEvent)
        return newEvent

    def updateIndividualSchedulesParameter(self, newEvent, oldEvent):
        new = newEvent['data']['users'] if 'users' in newEvent['data'] else []
        old = newEvent['data']['users'] if oldEvent else []

        dicrementedUsers = list(set(old).difference(set(new)))
        incrementedUsers = list(set(new).difference(set(old)))

        if len(dicrementedUsers):
            Profile().update(query={
                "_id": {
                    "$in": dicrementedUsers
                }
            }, update={'$inc': {
                    'individual_events': -1
                }
            })

        if len(incrementedUsers):
            Profile().update(query={
                "_id": {
                    "$in": incrementedUsers
                }
            }, update={'$inc': {
                    'individual_events': 1
                }
            })

    def rescheduleRandomNotifications(self, event):
        if 'data' in event and 'useNotifications' in event['data'] and event['data'][
            'useNotifications']:
            push_notification = PushNotificationModel(event=event)
            push_notification.random_reschedule()
            self.save(event)


    def getEvents(self, applet_id, individualized, profile_id = None):
        if not individualized or not profile_id:
            events = list(self.find({'applet_id': ObjectId(applet_id), 'individualized': individualized}, fields=['data', 'schedule']))
        else:
            events = list(self.find({'applet_id': ObjectId(applet_id), 'individualized': individualized, 'data.users': profile_id}, fields=['data', 'schedule']))

        for event in events:
            if 'data' in event and 'users' in event['data']:
                event['data'].pop('users')

        return events

    def setSchedule(self, event):
        push_notification = PushNotificationModel(event=event)
        push_notification.remove_schedules()
        useNotifications = event.get('data', {}).get('useNotifications', False)
        notifications = event.get('data', {}).get('notifications', [])
        hasNotifications = len(notifications) > 0

        if hasNotifications and useNotifications and notifications[0]['start']:
            push_notification.set_schedules()

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

    def dateMatch(self, event, date): # filter only active events on specified date
        eventTimeout = event['data'].get('timeout', None)
        eventTime = event['schedule']['times'][0] if 'times' in event['schedule'] else '00:00'
        if ':' not in eventTime:
            eventTime = f'{eventTime}:00'

        timeDelta = datetime.timedelta(hours=int(eventTime[:2]), minutes=int(eventTime[-2:]))

        timeout = datetime.timedelta(days=0)

        if eventTimeout and eventTimeout.get('allow', False) and event['data'].get('completion', False) and not event['data'].get('onlyScheduledDay', False):
            timeout = datetime.timedelta(
                days=eventTimeout.get('day', 0),
                hours=eventTimeout.get('hour', 0),
                minutes=eventTimeout.get('minute', 0)
            )

        if event['data'].get('extendedTime', {}).get('allow', False) and not event['data'].get('onlyScheduledDay', False):
            timeout = timeout + datetime.timedelta(
                days=event['data']['extendedTime'].get('days', 0)
            )

        if not event['data'].get('eventType', None) or event['data']['eventType'] == 'onetime': # one time schedule
            if not len(event['schedule'].get('dayOfMonth', [])) \
                or not len(event['schedule'].get('month', [])) \
                or not len(event['schedule'].get('year', [])):

                return (False, None)

            launchDate = datetime.datetime.strptime(
                f'{event["schedule"]["year"][0]}/{event["schedule"]["month"][0]+1}/{event["schedule"]["dayOfMonth"][0]}',
                '%Y/%m/%d'
            ) + timeDelta

            lastAvailableTime = launchDate + timeout

            if lastAvailableTime.date() >= date.date():
                return (launchDate.date() <= date.date(), None)

            return (False, lastAvailableTime)

        else:
            start = event['schedule'].get('start', None)
            end = event['schedule'].get('end', None)

            startDate = datetime.datetime.fromtimestamp(start/1000) + timeDelta if start else None
            endDate = datetime.datetime.fromtimestamp(end/1000) + timeDelta if end else None

            if startDate and startDate.date() > date.date():
                return (False, None)

            if event['data'].get('eventType', None) == 'Weekly': # weekly schedule
                if len(event['schedule']['dayOfWeek']) and event['schedule']['dayOfWeek'][0] == (date.weekday() + 1) % 7:
                    return (True, None)

                if endDate and endDate < date:
                    latestScheduledDay = endDate - datetime.timedelta(
                        days=(endDate.weekday()+1 - event['schedule']['dayOfWeek'][0] + 7) % 7,
                    )
                else:
                    latestScheduledDay = date - datetime.timedelta(
                        days=(date.weekday()+1 - event['schedule']['dayOfWeek'][0] + 7) % 7
                    )

                if (not startDate or startDate.date() <= latestScheduledDay.date()):
                    lastAvailableTime = latestScheduledDay + timeDelta + timeout
                    return ( lastAvailableTime >= date, lastAvailableTime )

                return (False, None)

            elif event['data'].get('eventType', None) == 'Monthly': # monthly schedule
                if len(event['schedule']['dayOfMonth']) and event['schedule']['dayOfMonth'][0] == date.day:
                    return (True, None)

                if endDate and endDate < date:
                    latestScheduledDay = datetime.datetime(endDate.year, endDate.month, event['schedule']['dayOfMonth'][0])

                    if endDate.day < event['schedule']['dayOfMonth'][0]:
                        latestScheduledDay = latestScheduledDay - relativedelta(months=1)
                else:
                    latestScheduledDay = datetime.datetime(date.year, date.month, event['schedule']['dayOfMonth'][0])

                    if date.day < event['schedule']['dayOfMonth'][0]:
                        latestScheduledDay = latestScheduledDay - relativedelta(months=1)

                if (not startDate or startDate.date() <= latestScheduledDay.date()):
                    lastAvailableTime = latestScheduledDay + timeDelta + timeout
                    return ( lastAvailableTime >= date, lastAvailableTime )

                return (False, None)

            # daily schedule
            lastAvailableTime = endDate + timeDelta + timeout if endDate else None
            return ( (not endDate or lastAvailableTime >= date), lastAvailableTime )

    def getScheduleForUser(self, applet_id, user_id, eventFilter=None):
        profile = Profile().findOne({'appletId': ObjectId(applet_id), 'userId': ObjectId(user_id)})
        if not profile:
            return {}

        individualized = profile['individual_events'] > 0
        events = self.getEvents(applet_id, individualized, profile['_id'])

        result = {}

        for event in events:
            event['id'] = event['_id']
            event.pop('_id')

        if eventFilter:
            dayFilter = eventFilter[0]

            result["events"] = {}
            result["data"] = {}

            usedEventCards = {}

            for i in range(0, eventFilter[1]):
                lastEvent = {}
                onlyScheduledDay = {}

                for event in events:
                    event['valid'], lastAvailableTime = self.dateMatch(event, dayFilter)

                    activityId = event.get('data', {}).get('activity_id', None)

                    if not activityId:
                        event['valid'] = False
                        continue

                    if not event['valid']:
                        if lastAvailableTime:
                            if activityId not in lastEvent or (lastEvent[activityId] and lastAvailableTime > lastEvent[activityId][0]):
                                lastEvent[activityId] = (lastAvailableTime, event)
                    else:
                        lastEvent[activityId] = None

                    if event['data'].get('onlyScheduledDay', False):
                        onlyScheduledDay[activityId] = event

                data = []
                for event in events:
                    if event['valid']:
                        data.append(event)

                for value in lastEvent.values():
                    if value and (value[1]['data'].get('completion', False) or value[1]['data'].get('activity_id', None) in onlyScheduledDay):
                        data.append(value[1])

                for event in data:
                    if event['data'].get('activity_id', None) in onlyScheduledDay:
                        onlyScheduledDay.pop(event['data']['activity_id'])

                for activityId in onlyScheduledDay:
                    data.append(onlyScheduledDay[activityId])

                for card in data:
                    usedEventCards[str(card['id'])] = True

                result['data'][dayFilter.strftime('%Y/%m/%d')] = [
                    {
                        'id': str(card['id']),
                        'valid': card['valid']
                    } for card in data
                ]

                dayFilter = dayFilter + relativedelta(days=1)

            for event in events:
                event.pop('valid')

                if usedEventCards.get(str(event["id"]), False):
                    result["events"][str(event["id"])] = event

        else:
            result['events'] = events

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
            **result
        }
