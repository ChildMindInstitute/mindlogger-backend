# -*- coding: utf-8 -*-
import random

import cherrypy
import json
import bson
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

from girderformindlogger.models import getRedisConnection
from rq_scheduler import Scheduler

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

def sayHello():
    print('hello world!')

class Notification(Resource):
    api_key = 'AAAAJOyOEz4:APA91bFudM5Cc1Qynqy7QGxDBa-2zrttoRw6ZdvE9PQbfIuAB9SFvPje7DcFMmPuX1IizR1NAa7eHC3qXmE6nmOpgQxXbZ0sNO_n1NITc1sE5NH3d8W9ld-cfN7sXNr6IAOuodtEwQy-'
    push_service = FCMNotification(api_key=api_key, proxy_dict={})
    user_timezone_time = None
    current_time = None
    success = 0
    error = 0

    def __init__(self):
        super(Notification, self).__init__()
        self.resourceName = 'notification'
        self.route('GET', ('stream',), self.stream)
        self.route('GET', ('send-push-notifications',), self.sendPushNotifications)
        self.route('GET', (), self.listNotifications)
        self.route('GET', ('test-scheduling', ), self.testScheduling)

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
        .notes(
            'This endpoint is used to send push notifications to users using FCMNotification. <br>'
            'This endpoint is going to be removed soon.'
        )
            .errorResponse()
            .errorResponse('You are not logged in.', 403)
    )
    def testScheduling(self):
        redis = getRedisConnection()
        scheduler = Scheduler(connection=redis)
        job_id = scheduler.enqueue_in(datetime.timedelta(minutes=1), sayHello)

    @disableAuditLog
    @access.public
    @autoDescribeRoute(
        Description('Send push notifications')
        .notes(
            'This endpoint is used to send push notifications to users using FCMNotification. <br>'
            'This endpoint is going to be removed soon.'
        )
            .errorResponse()
            .errorResponse('You are not logged in.', 403)
    )
    def sendPushNotifications(self):
        self.current_time = datetime.datetime.utcnow().strftime('%Y/%m/%d %H:%M')
        self.send_single_notifications()
        self.send_daily_notifications()
        self.send_weekly_notifications()

        result = {'successed': self.success, 'errors': self.error}

        self.success = 0
        self.error = 0

        return result

    def get_notifications_by_type(self, notification_type=1):
        return list(PushNotificationModel().find(
            query={
                'notification_type': notification_type,
            }
        ))

    def send_single_notifications(self):
        notifications = self.get_notifications_by_type(1)
        self.get_profiles_by_notifications(notifications)

    def send_daily_notifications(self):
        notifications = self.get_notifications_by_type(2)
        self.get_profiles_by_notifications(notifications)

    def send_weekly_notifications(self):
        notifications = self.get_notifications_by_type(3)
        self.get_profiles_by_notifications(notifications)

    def get_profiles_by_notifications(self, notifications):
        for notification in notifications:
            if 'notifiedUsers' not in notification:
                notification.update({
                    'notifiedUsers': []
                })
            user_ids = [profile['userId'] for profile in self.get_profiles(notification) if profile]
            users = list(UserModel().get_users_by_ids(user_ids))
            self.set_random_date(notification)
            current_users = self.filter_users_by_timezone(notification, users)

            if current_users:
                notification.get('notifiedUsers')
                notification.update({
                    'notifiedUsers': notification.get('notifiedUsers', []) + [
                        {
                            '_id': user['_id'],
                            'dateSend': (datetime.datetime.strptime(self.current_time, '%Y/%m/%d %H:%M') \
                                + datetime.timedelta(hours=int(user['timezone']))).strftime('%Y/%m/%d')
                        }
                        for user in current_users]
                })
                device_ids = [user['deviceId'] for user in current_users]
                self.__send_notification(notification, device_ids)

            PushNotificationModel().save(notification, validate=False)

    def set_random_date(self, notification):
        if notification['endTime'] and (not notification['lastRandomTime'] or notification['dateSend']):
            # set random time
            notification['lastRandomTime'] = self.__random_date(
                notification['startTime'],
                notification['endTime'],
                '%H:%M'
            ).strftime('%H:%M')

    # the main logic of notification
    def filter_users_by_timezone(self, notification, users):
        current_users = []

        notification_start_date = notification['schedule']['start']
        notification_end_date = notification['schedule']['end']
        notification_start_time = notification['startTime']
        notification_end_time = notification['endTime']
        notification_week_day = notification['schedule'].get('dayOfWeek', None)
        notification_h = int(
            datetime.datetime.strptime(notification["startTime"], "%H:%M").hour)
        notification_m = int(
            datetime.datetime.strptime(notification["startTime"], "%H:%M").minute)
        notification_random_h = None
        notification_random_m = None
        if notification['lastRandomTime']:
            notification_random_h = int(
                datetime.datetime.strptime(notification["lastRandomTime"], "%H:%M").hour)
            notification_random_m = int(
                datetime.datetime.strptime(notification["lastRandomTime"], "%H:%M").minute)

        for user in users:
            current_user_time = datetime.datetime.strptime(self.current_time, '%Y/%m/%d %H:%M') \
                                + datetime.timedelta(hours=int(user['timezone']))

            self.refresh_notification_users(notification, user)

            does_notified_user = None
            if 'notifiedUsers' in notification:
                does_notified_user = self.__list_filter(notification['notifiedUsers'], '_id', user['_id'])

            usr_h = int(current_user_time.strftime("%H"))
            usr_m = int(current_user_time.strftime("%M"))

            if current_user_time.strftime('%H:%M') >= notification_start_time \
                and notification_start_date <= current_user_time.strftime('%Y/%m/%d') \
                <= notification_end_date:
                if 'notifiedUsers' not in notification or not does_notified_user:

                    if notification['notification_type'] in [1, 2]:
                        if notification_end_time and notification['lastRandomTime'] \
                            and current_user_time.strftime('%H:%M') \
                            >= notification['lastRandomTime'] and usr_h == notification_random_h \
                            and usr_m >= notification_random_m:
                            # in random time case for single\daily notification
                            current_users.append(user)
                        if not notification_end_time and usr_h == notification_h \
                            and usr_m >= notification_m:
                            # in single\daily notification case
                            current_users.append(user)

                    if notification['notification_type'] == 3:
                        if notification_week_day and notification_week_day == int(current_user_time.weekday()) + 1:
                            if notification_end_time and notification['lastRandomTime'] \
                                and current_user_time.strftime('%H:%M') \
                                >= notification['lastRandomTime'] and usr_h == notification_random_h \
                                and usr_m >= notification_random_m:
                                # in random time case for weekly notification case
                                current_users.append(user)

                            if not notification_end_time and usr_h == notification_h and usr_m >= notification_m:
                                # in weekly notification case
                                current_users.append(user)
        return current_users

    def __list_filter(self, obj_list, arg, value) -> dict:
        filtered_users = [obj for obj in obj_list if arg in obj and obj[arg] == value]
        return filtered_users[0] if len(filtered_users) else {}

    def __exclude_from_list(self, obj_list, arg, value):
        return [obj for obj in obj_list if arg in obj and obj[arg] != value]

    def refresh_notification_users(self, notification, user):
        """
        Remove sent notification users from the list whose dates do not coincide with the UTC date
        :params notification: notification dict
        :type notification: dict
        :params user: user dict
        :type user: dict
        """
        if not notification['notification_type'] == 1:
            current_user_time = datetime.datetime.strptime(self.current_time, '%Y/%m/%d %H:%M') \
                                + datetime.timedelta(hours=int(user['timezone']))

            notification_start_date = notification['schedule']['start']
            notification_end_date = notification['schedule']['end']

            date_notified_last_date = self.__list_filter(notification['notifiedUsers'], '_id', user['_id'])

            if notification_start_date <= current_user_time.strftime('%Y/%m/%d') \
            <= notification_end_date:
                if 'dateSend' in date_notified_last_date and date_notified_last_date['dateSend'] \
                    < current_user_time.strftime('%Y/%m/%d'):
                    notification['notifiedUsers'] = \
                        self.__exclude_from_list(notification['notifiedUsers'], '_id', user['_id'])

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
        # notification['dateSend'] = self.user_timezone_time.strftime('%Y/%m/%d')
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
        profiles = self.get_profiles(notification)

        user_ids = [profile['userId'] for profile in list(profiles) if profile]

        if user_ids:
            device_ids = [
                user['deviceId'] for user in list(UserModel().get_users_by_ids(user_ids)) if user
            ]
            return device_ids
        return []

    def get_profiles(self, notification):
        if len(notification['users']):
            return list(ProfileModel().get_profiles_by_ids(notification['users']))

        notification_with_applet = list(PushNotificationModel().find(query={
            'applet': notification['applet'],
            'users': {
                '$exists': True,
                '$ne': []
            }
        }))
        notification_with_applet = list(set(user for n in notification_with_applet for user in n['users']))
        profiles = list(ProfileModel().get_profiles_by_applet_id(notification['applet']))
        # exclude existed users from general schedule
        return [profile for profile in profiles if profile['_id'] and profile['_id'] not in notification_with_applet]
