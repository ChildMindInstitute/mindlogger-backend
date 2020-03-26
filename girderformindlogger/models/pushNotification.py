# -*- coding: utf-8 -*-
import datetime
import six
import time
import bson

from girderformindlogger.models.model_base import Model


class ProgressState(object):
    """
    Enum of possible progress states for progress records.
    """

    ACTIVE = 'active'
    SUCCESS = 'success'
    ERROR = 'error'
    EMPTY = 'empty'

    @classmethod
    def isComplete(cls, state):
        return state == cls.SUCCESS or state == cls.ERROR


class PushNotification(Model):
    """
    This model is used to represent a notification that should be streamed
    to a specific user in some way. Each notification contains a
    type field indicating what kind of notification it is, a userId field
    indicating which user the notification should be sent to, a data field
    representing the payload of the notification, a time field indicating the
    time at which the event happened, and an optional expires field indicating
    at what time the notification should be deleted from the database.
    """

    def initialize(self):
        self.name = 'pushNotification'
        self.ensureIndices(('assetId', 'notification_type', 'head', 'content',
                            'sendTime', 'creator_id', 'created', 'updated', 'progress', 'timezone', 'attempts'))

    def validate(self, doc):
        return doc

    def replaceNotification(self, applet, event, creator_id, original = None):
        """
        Create a generic notification.

        :param type: The notification type.
        :type type: str
        :param data: The notification payload.
        :param user: User to send the notification to.
        :type user: dict
        :param expires: Expiration date (for transient notifications).
        :type expires: datetime.datetime
        :param token: Set this if the notification should correspond to a token
            instead of a user.
        :type token: dict
        """
        current_time = time.time()
        notification_type = 1
        start_time = event['data']['notifications'][0]['start']
        end_time = None

        schedule = {}

        users = []
        if 'users' in event['data']:
            users = [bson.ObjectId(oid=user) for user in event['data']['users'] if user]

        if 'schedule' in event:
            if 'start' in event['schedule'] and 'end' in event['schedule']:
                if 'dayOfWeek' in event['schedule']:
                    """
                    Weekly configuration in case of weekly event
                    """
                    notification_type = 3
                    schedule['start'] = datetime.datetime.fromtimestamp(
                        float(event['schedule']['start']) / 1000).strftime('%Y/%m/%d')
                    schedule['end'] = datetime.datetime.fromtimestamp(
                        float(event['schedule']['end']) / 1000).strftime('%Y/%m/%d')
                    schedule['dayOfWeek'] = event['schedule']['dayOfWeek'][0]
                else:
                    """
                    Daily configuration in case of daily event
                    """
                    notification_type = 2
                    schedule['start'] = datetime.datetime.fromtimestamp(
                        float(event['schedule']['start']) / 1000).strftime('%Y/%m/%d')
                    schedule['end'] = datetime.datetime.fromtimestamp(
                        float(event['schedule']['end']) / 1000).strftime('%Y/%m/%d')
            else:
                if 'dayOfMonth' in event['schedule']:
                    """
                    Does not repeat configuration in case of sigle event with exact year, month, day
                    """
                    print('day of month')
                    if event['data'].get('notifications', None) and \
                        event['data']['notifications'][0][
                            'random']:
                        end_time = event['data']['notifications'][0]['end']
                    if 'year' in event['schedule'] and 'month' in event[
                        'schedule'] and 'dayOfMonth' in \
                        event['schedule']:
                        start_time = str(str(event['schedule']['year'][0]) + '/' +
                                         ('0' + str(event['schedule']['month'][0] + 1))[-2:] + '/' +
                                         ('0' + str(event['schedule']['dayOfMonth'][0]))[
                                         -2:] + ' ' +
                                         start_time)

                        if event['data']['notifications'] and event['data']['notifications'][0][
                            'random']:
                            end_time = str(str(event['schedule']['year'][0]) + '/' +
                                           ('0' + str(event['schedule']['month'][0] + 1))[
                                           -2:] + '/' +
                                           ('0' + str(event['schedule']['dayOfMonth'][0]))[
                                           -2:] + ' ' +
                                           end_time)

            push_notification = {
                'applet': applet,
                'notification_type': notification_type,
                'head': event['data']['title'],
                'content': event['data']['description'],
                'users': users,
                'schedule': schedule,
                'startTime': start_time,
                'endTime': end_time,
                'lastRandomTime': None,
                'dateSend': None,
                'creator_id': creator_id,
                'created': current_time,
                'updated': current_time,
                'progress': ProgressState.ACTIVE,
                'attempts': 0,
                'event_id': event['data'].get('id')
            }

            if original:
                push_notification.update({
                    '_id': original.get('_id'),
                    'progress': original.get('progress'),
                    'attempts': original.get('attempts'),
                })
                
                if start_time > datetime.datetime.utcnow().strftime('%Y/%m/%d %H:%M'):
                    push_notification.update({
                        'progress': ProgressState.ACTIVE
                    })

            return self.save(push_notification)
        return None

    def delete_notification(self, applet, creator_id, event_id):
        self.removeWithQuery(query={'applet': applet,
                                   'creator_id': creator_id,
                                   'event_id': event_id
                                   })

    def updateProgress(self, record, save=True, **kwargs):
        """
        Update an existing progress record.

        :param record: The existing progress record to update.
        :type record: dict
        :param total: Some numeric value representing the total task length. By
            convention, setting this <= 0 means progress on this task is
            indeterminate. Generally this shouldn't change except in cases where
            progress on a task switches between indeterminate and determinate
            state.
        :type total: int, long, or float
        :param state: Represents the state of the underlying task execution.
        :type state: ProgressState enum value.
        :param current: Some numeric value representing the current progress
            of the task (relative to total).
        :type current: int, long, or float
        :param increment: Amount to increment the progress by. Don't pass both
            current and increment together, as that behavior is undefined.
        :type increment: int, long, or float
        :param message: Message corresponding to the current state of the task.
        :type message: str
        :param expires: Set a custom (UTC) expiration time on the record.
            Default is one hour from the current time.
        :type expires: datetime
        :param save: Whether to save the record to the database.
        :type save: bool
        """
        if 'increment' in kwargs:
            record['data']['current'] += kwargs['increment']

        for field, value in six.viewitems(kwargs):
            if field in ('total', 'current', 'state', 'message'):
                record['data'][field] = value

        now = datetime.datetime.utcnow()

        if 'expires' in kwargs:
            expires = kwargs['expires']
        else:
            expires = now + datetime.timedelta(hours=1)

        record['updated'] = now
        record['expires'] = expires
        record['updatedTime'] = time.time()
        if save:
            # Only update the time estimate if we are also saving
            if (record['updatedTime'] > record['startTime']
                    and record['data']['estimateTime']):
                if 'estimatedTotalTime' in record:
                    del record['estimatedTotalTime']
                try:
                    total = float(record['data']['total'])
                    current = float(record['data']['current'])
                    if total >= current and total > 0 and current > 0:
                        record['estimatedTotalTime'] = \
                            total * (record['updatedTime'] - record['startTime']) / current
                except ValueError:
                    pass
            return self.save(record)
        else:
            return record

    def get(self, user, since=None, token=None, sort=None):
        """
        Get outstanding notifications for the given user.

        :param user: The user requesting updates.  None to use the token
            instead.
        :param since: Limit results to entities that have been updated
            since a certain timestamp.
        :type since: datetime
        :param token: if the user is None, the token requesting updated.
        :param sort: Sort field for the database query.
        """
        q = {}
        if user:
            q['userId'] = user['_id']
        else:
            q['tokenId'] = token['_id']

        if since is not None:
            q['updated'] = {'$gt': since}

        return self.find(q, sort=sort)
