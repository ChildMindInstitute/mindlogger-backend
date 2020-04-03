# -*- coding: utf-8 -*-
import random

import cherrypy
import json
import time

from pyfcm import FCMNotification
import datetime

from ..describe import Description, autoDescribeRoute
from ..rest import Resource, disableAuditLog, setResponseHeader
from girderformindlogger.models.applet import Applet as AppletModel
from girderformindlogger.constants import SortDir
from girderformindlogger.exceptions import RestException
from girderformindlogger.models.notification import Notification as NotificationModel
from girderformindlogger.models.user import User as UserModel
from girderformindlogger.models.profile import Profile as ProfileModel
from girderformindlogger.models.pushNotification import PushNotification as PushNotificationModel, \
    ProgressState
from girderformindlogger.models.setting import Setting
from girderformindlogger.settings import SettingKey
from girderformindlogger.utility import JsonEncoder
from girderformindlogger.api import access

# If no timeout param is passed to stream, we default to this value
DEFAULT_STREAM_TIMEOUT = 300
# When new events are seen, we will poll at the minimum interval
MIN_POLL_INTERVAL = 0.5
# The interval increases when no new events are seen, capping at this value
MAX_POLL_INTERVAL = 2


def sseMessage(event):
    """
    Serializes an event into the server-sent events protocol.
    """
    # Inject the current time on the server into the event so that
    # the client doesn't need to worry about clock synchronization
    # issues when restarting the event stream.
    event['_girderTime'] = int(time.time())
    return 'data: %s\n\n' % json.dumps(event, sort_keys=True, allow_nan=False, cls=JsonEncoder)


class Notification(Resource):
    api_key = 'AAAAJOyOEz4:APA91bFudM5Cc1Qynqy7QGxDBa-2zrttoRw6ZdvE9PQbfIuAB9SFvPje7DcFMmPuX1IizR1NAa7eHC3qXmE6nmOpgQxXbZ0sNO_n1NITc1sE5NH3d8W9ld-cfN7sXNr6IAOuodtEwQy-'
    push_service = FCMNotification(api_key=api_key, proxy_dict={})
    user_timezone_time = None
    success = 0
    error = 0

    def __init__(self):
        super(Notification, self).__init__()
        self.resourceName = 'notification'
        self.route('GET', ('stream',), self.stream)
        self.route('GET', ('send-push-notifications',), self.sendPushNotifications)
        self.route('GET', (), self.listNotifications)

    @disableAuditLog
    @access.token(cookie=True)
    @autoDescribeRoute(
        Description('Stream notifications for a given user via the SSE protocol.')
            .notes('This uses long-polling to keep the connection open for '
                   'several minutes at a time (or longer) and should be requested '
                   'with an EventSource object or other SSE-capable client. '
                   '<p>Notifications are returned within a few seconds of when '
                   'they occur.  When no notification occurs for the timeout '
                   'duration, the stream is closed. '
                   '<p>This connection can stay open indefinitely long.')
            .param('timeout', 'The duration without a notification before the stream is closed.',
                   dataType='integer', required=False, default=DEFAULT_STREAM_TIMEOUT)
            .param('since', 'Filter out events before this time stamp.',
                   dataType='integer', required=False)
            .produces('text/event-stream')
            .errorResponse()
            .errorResponse('You are not logged in.', 403)
            .errorResponse('The notification stream is not enabled.', 503)
    )
    def stream(self, timeout, params):
        if not Setting().get(SettingKey.ENABLE_NOTIFICATION_STREAM):
            raise RestException('The notification stream is not enabled.', code=503)

        user, token = self.getCurrentUser(returnToken=True)

        setResponseHeader('Content-Type', 'text/event-stream')
        setResponseHeader('Cache-Control', 'no-cache')
        since = params.get('since')
        if since is not None:
            since = datetime.datetime.utcfromtimestamp(since)

        def streamGen():
            lastUpdate = since
            start = time.time()
            wait = MIN_POLL_INTERVAL
            while cherrypy.engine.state == cherrypy.engine.states.STARTED:
                wait = min(wait + MIN_POLL_INTERVAL, MAX_POLL_INTERVAL)
                for event in NotificationModel().get(user, lastUpdate, token=token):
                    if lastUpdate is None or event['updated'] > lastUpdate:
                        lastUpdate = event['updated']
                    wait = MIN_POLL_INTERVAL
                    start = time.time()
                    yield sseMessage(event)
                if time.time() - start > timeout:
                    break

                time.sleep(wait)

        return streamGen

    @disableAuditLog
    @access.token(cookie=True)
    @autoDescribeRoute(
        Description('List notification events')
            .notes('This endpoint can be used for manual long-polling when '
                   'SSE support is disabled or otherwise unavailable. The events are always '
                   'returned in chronological order.')
            .param('since', 'Filter out events before this date.', required=False,
                   dataType='dateTime')
            .errorResponse()
            .errorResponse('You are not logged in.', 403)
    )
    def listNotifications(self, since):
        user, token = self.getCurrentUser(returnToken=True)
        return list(NotificationModel().get(
            user, since, token=token, sort=[('updated', SortDir.ASCENDING)]))

    @disableAuditLog
    @access.public
    @autoDescribeRoute(
        Description('Send push notifications')
            .errorResponse()
            .errorResponse('You are not logged in.', 403)
    )
    def sendPushNotifications(self):
        now = datetime.datetime.utcnow().strftime('%Y/%m/%d %H:%M')

        users = list(UserModel().find({
                    'timezone': {
                        '$exists': True
                    }}))

        # filter for users
        users = [dict(user) for user in users if user]

        for user in users:
            self.user_timezone_time = datetime.datetime.strptime(now, '%Y/%m/%d %H:%M') \
                                      + datetime.timedelta(hours=int(user['timezone']))

            notifications = list(PushNotificationModel().find(
                query={
                    'progress': ProgressState.ACTIVE,
                    'notification_type': 1,
                    'schedule.start': self.user_timezone_time.strftime('%Y/%m/%d'),
                    'schedule.end': self.user_timezone_time.strftime('%Y/%m/%d'),
                    'startTime': {
                        '$lte': self.user_timezone_time.strftime('%H:%M')
                    }
                }))

            self.__send_random_notifications(notifications, user)

            notifications = [notification for notification in notifications if
                             not notification['endTime']]

            for notification in notifications:
                user_data_send = self.user_timezone_time.strftime('%Y/%m/%d')
                notification_date_send = notification['dateSend']
                device_ids = self.get_user_device_id(notification)

                if len(device_ids):
                    to_send = not notification_date_send or user_data_send > notification_date_send
                    if to_send:
                        self.__send_notification(notification, device_ids)

            self.__send_daily_notifications(user)
            self.__send_weekly_notifications(user)

        result = {'successed': self.success, 'errors': self.error}

        self.success = 0
        self.error = 0

        return result

    def __send_weekly_notifications(self, user):
        """
        Weekly Notification function
        :param user: User to send the notification to.
        :type user: dict
        """
        notifications = list(PushNotificationModel().find(
            query={
                'notification_type': 3,
                'schedule.start': {
                    '$lte': self.user_timezone_time.strftime('%Y/%m/%d')
                },
                'schedule.end': {
                    '$gt': self.user_timezone_time.strftime('%Y/%m/%d')
                }
            }
        ))

        self.__send_random_notifications(notifications, user)

        notifications = [notification for notification in notifications if
                         not notification['endTime']]

        for notification in notifications:
            device_ids = self.get_user_device_id(notification)

            if len(device_ids):
                user_time = self.user_timezone_time.strftime('%H:%M')
                notification_time = notification['startTime']
                day_of_week = int(self.user_timezone_time.weekday()) + 1
                notification_day_of_week = int(notification['schedule']['dayOfWeek'])
                user_data_send = self.user_timezone_time.strftime('%Y/%m/%d')
                notification_date_send = notification['dateSend']

                to_send = day_of_week == notification_day_of_week and user_time > notification_time and (
                    not notification_date_send or user_data_send > notification_date_send)

                if to_send:
                    self.__send_notification(notification, device_ids)

    def __send_daily_notifications(self, user):
        """
        Daily Notification function
        :param user: User to send the notification to.
        :type user: dict
        """
        notifications = list(PushNotificationModel().find(
            query={
                'notification_type': 2,
                'schedule.start': {
                    '$lte': self.user_timezone_time.strftime('%Y/%m/%d')
                },
                'schedule.end': {
                    '$gt': self.user_timezone_time.strftime('%Y/%m/%d')
                }
            }
        ))

        self.__send_random_notifications(notifications, user)

        notifications = [notification for notification in notifications if
                         not notification['endTime']]

        for notification in notifications:
            device_ids = self.get_user_device_id(notification)

            if len(device_ids):
                user_time = self.user_timezone_time.strftime('%H:%M')
                notification_time = notification['startTime']

                user_data_send = self.user_timezone_time.strftime('%Y/%m/%d')
                notification_date_send = notification['dateSend']

                to_send = user_time > notification_time and (not notification_date_send
                                                             or user_data_send > notification_date_send)

                if to_send:
                    self.__send_notification(notification, device_ids)

    def __send_random_notifications(self, notifications, user):
        """
        Random Notification function
        :param notifications: List of notification dict
        :type notifications: list
        :param user: User to send the notification to.
        :type user: dict
        """
        notifications_with_end = [notification for notification in notifications if
                                  notification['endTime']]

        for notification in notifications_with_end:
            device_ids = self.get_user_device_id(notification)

            if len(device_ids):
                format_str = '%H:%M'

                if not notification['lastRandomTime'] or notification['dateSend']:
                    # set random time
                    notification['lastRandomTime'] = self.__random_date(
                        notification['startTime'],
                        notification['endTime'],
                        format_str
                    ).strftime(format_str)

                user_time = self.user_timezone_time.strftime(format_str)
                notification_time = notification['lastRandomTime']

                user_data_send = self.user_timezone_time.strftime('%Y/%m/%d')
                notification_date_send = notification['dateSend']

                to_send = user_time > notification_time and (not notification_date_send
                                                             or user_data_send > notification_date_send)

                if to_send:
                    self.__send_notification(notification, device_ids)
                PushNotificationModel().save(notification, validate=False)

    def __random_date(self, start, end, format_str='%H:%M'):
        """
        Random date set between range of date
        :params start: Start date range
        :type start: str
        :params end: End date range
        :type end: str
        :params format_str: Format date
        :type format_str: str
        """
        start_date = datetime.datetime.strptime(start, format_str)
        end_date = datetime.datetime.strptime(end, format_str)

        time_between_dates = end_date - start_date
        days_between_dates = time_between_dates.seconds
        random_number_of_seconds = random.randrange(days_between_dates)
        return start_date + datetime.timedelta(seconds=random_number_of_seconds)

    def __send_notification(self, notification, user_ids=None):
        """
        Main bode to send notification
        :params notification: Notification which should be sent to user
        :params notification: dict
        :params user: User to send the notification to.
        :params user: dict
        """
        notification['dateSend'] = self.user_timezone_time.strftime('%Y/%m/%d')
        message_title = notification['head']
        message_body = notification['content']
        result = self.push_service.notify_multiple_devices(registration_ids=user_ids,
                                                           message_title=message_title,
                                                           message_body=message_body)
        notification['attempts'] += 1
        notification['progress'] = ProgressState.ACTIVE
        if result['failure']:
            notification['progress'] = ProgressState.ERROR
            self.error += result['failure']
            print(result['results'])

        if result['success']:
            notification['progress'] = ProgressState.SUCCESS
            self.success += result['success']

        PushNotificationModel().save(notification, validate=False)

    def get_user_device_id(self, notification):
        user_ids = None

        if len(notification['users']):
            user_ids = [
                profile['userId'] for profile in list(ProfileModel().find(
                    query={
                        '_id': {
                            '$in': notification['users']
                        },
                        'userId': {
                            '$exists': True
                        },
                        'profile': True
                    }
                )) if profile
            ]
        else:
            user_ids = [
                profile['userId'] for profile in list(ProfileModel().find(
                    query={
                        'appletId': notification['applet'],
                        'userId': {
                            '$exists': True
                        },
                        'profile': True
                    }
                )) if profile
            ]

        if user_ids:
            device_ids = [
                user['deviceId'] for user in list(UserModel().find(
                    query={
                        '_id': {
                            '$in': user_ids
                        }
                    }
                )) if user]

            return device_ids
        return []
