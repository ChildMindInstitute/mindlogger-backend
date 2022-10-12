import datetime
import time
from collections import defaultdict
from concurrent.futures.thread import ThreadPoolExecutor

from pyfcm import FCMNotification
from rq_scheduler import Scheduler
from bson import ObjectId
from redis import Redis, ConnectionPool
from girderformindlogger.models import getRedisConnection

DAILY = 'Daily'
WEEKLY = 'Weekly'
MONTHLY = 'Monthly'

HOUR = 60 * 60
DAY = HOUR * 24
WEEK = DAY * 7
MONTH = WEEK * 4

MIN_TIMEZONE = -12
MAX_TIMEZONE = 12

DEBUG = False


class _NotificationService(FCMNotification):
    def do_request(self, payload, timeout=5):
        response = self.requests_session.post(self.FCM_END_POINT, data=payload, timeout=timeout)
        if 'Retry-After' in response.headers and int(response.headers['Retry-After']) > 0:
            sleep_time = int(response.headers['Retry-After'])
            print(f'Sleep for sending notification {sleep_time}')
            time.sleep(sleep_time)
            return self.do_request(payload, timeout)
        return response

    def send_request(self, payloads=None, timeout=None):
        self.send_request_responses = []
        with ThreadPoolExecutor(max_workers=2) as executor:
            response = executor.map(self.do_request, payloads)
            executor.map(self.send_request_responses.append, response)


_notification_service = _NotificationService(
    api_key='AAAAJOyOEz4:APA91bFudM5Cc1Qynqy7QGxDBa-2zrttoRw6ZdvE9PQbfIuAB9SFvPje7DcFMmPuX1IizR1NAa7eHC3qXmE6nmOpgQxXbZ0sNO_n1NITc1sE5NH3d8W9ld-cfN7sXNr6IAOuodtEwQy-',
    proxy_dict={}
)  # TODO: get from env

if DEBUG:
    _scheduler = Scheduler(connection=Redis(connection_pool=ConnectionPool(**{
        'host': 'localhost',
        'port': 6379,
        'password': ''
    })))
else:
    _scheduler = Scheduler(connection=getRedisConnection())


class _Time:
    def __init__(self, time_: str):
        if not time_:
            self.hour = None
            self.minute = None
            return
        self.hour, self.minute = map(int, time_.split(':'))
        assert 0 <= self.hour < 24 and 0 <= self.minute < 60, 'Time is wrong'

    def __bool__(self):
        return self.hour and self.minute

    def __str__(self):
        if self.hour is None or self.minute is None:
            return ''
        return f'{self.hour}:{self.minute}'

    def __gt__(self, other):
        if self.hour > other.hour:
            return True
        elif self.minute > other.minute:
            return True
        return False

    def __lt__(self, other):
        if self.hour < other.hour:
            return True
        elif self.minute < other.minute:
            return True
        return False


class NotificationSchedulerV2:
    def __init__(self):
        self.utcnow = datetime.datetime.utcnow()

    def set_schedules(self, event, notification):
        # event = self._remove_schedules(event) # TODO: uncomment when fully moved to this logic
        event_type = event['data']['eventType']

        if event_type == DAILY:
            self._set_daily_schedule(event, notification)

        elif event_type == WEEKLY:
            pass
        elif event_type == MONTHLY:
            pass
        else:
            pass

    def _set_daily_schedule(self, event, notification):
        utc_now = datetime.datetime.utcnow()
        schedule = event['schedule']
        start_date = datetime.datetime.fromtimestamp(schedule['start'] / 1000).date()
        if start_date < self.utcnow.date():
            start_date = self.utcnow.date()

        end_date = None
        if schedule.get('end'):
            end_date = datetime.datetime.fromtimestamp(schedule['end'] / 1000).date()

        start_time = _Time(notification['start'])
        end_time = _Time(notification.get('end'))

        start_datetime = datetime.datetime(
            year=start_date.year,
            month=start_date.month,
            day=start_date.day,
            hour=start_time.hour,
            minute=start_time.minute
        )
        end_datetime = None
        if end_date:
            end_datetime = datetime.datetime(
                year=end_date.year,
                month=end_date.month,
                day=end_date.day,
                hour=start_time.hour,
                minute=start_time.minute,
            )

        start_datetime += datetime.timedelta(hours=MIN_TIMEZONE)
        if end_datetime:
            end_datetime += datetime.timedelta(hours=MAX_TIMEZONE)

        if start_datetime < utc_now:
            hour = utc_now.hour
            if start_time.minute < utc_now.minute:
                hour += 1
            start_datetime = datetime.datetime(
                year=utc_now.year,
                month=utc_now.month,
                day=utc_now.day,
                hour=hour,
                minute=start_time.minute
            )

        if start_datetime and end_datetime:
            repeat_time = ((end_date - start_date).total_seconds() / HOUR)
            if repeat_time > 0:
                sending_notification_job = _scheduler.schedule(
                    scheduled_time=start_datetime,
                    func=send_activity_notification,
                    kwargs=dict(
                        applet_id=event['applet_id'],
                        event_id=event['_id'],
                        activity_id=event['data']['activity_id'],
                        from_time=str(start_time),
                        end_time=str(end_time),
                    ),
                    interval=HOUR,
                    repeat=repeat_time,
                )
                event['schedulers'].append(sending_notification_job.id)
        else:
            sending_notification_job = _scheduler.schedule(
                scheduled_time=start_datetime,
                func=send_activity_notification,
                kwargs=dict(
                    applet_id=event['applet_id'],
                    event_id=event['_id'],
                    activity_id=event['data']['activity_id'],
                    from_time=str(start_time),
                    end_time=str(end_time),
                ),
                interval=HOUR,
            )
            event['schedulers'].append(sending_notification_job.id)

    def _get_user_groups_by_timezone(self, applet_id, event_id, activity_id):
        from girderformindlogger.models.events import Events
        from girderformindlogger.models.profile import Profile

        event = Events().findOne(dict(_id=event_id))

        profile_query = dict(
            appletId=applet_id,
            profile=True,
            completed_activity={'$elemMatch': {'activity_id': activity_id}}
        )
        if event['individualized']:
            profile_query.update({
                'individual_events': {'$gte': 1},
                '_id': {'$in': event['data']['users']}
            })

        profiles = Profile().find(
            query=profile_query,
            fields=['device_id', 'badge', 'user_id', 'timezone']
        )

        timezone_user_map = defaultdict(list)

        for profile in profiles:
            timezone = profile.get('timezone', 0) or 0
            timezone_user_map[timezone].append(profile['device_id'])
        return timezone_user_map

    def _set_weekly_schedule(self, event):
        pass

    def _set_monthly_schedule(self, event):
        pass

    def _remove_schedules(self, event):
        jobs = event.get('schedulers') or []
        for job in jobs:
            _scheduler.cancel(job)

        event['schedulers'] = []
        event['sendTime'] = []
        return event

    def _set_reminder(self, event):
        pass


def send_activity_notification(
    applet_id,
    event_id,
    activity_id,
    from_time,
    end_time,
):
    from girderformindlogger.models.events import Events
    from girderformindlogger.models.profile import Profile

    from_time = _Time(from_time)
    to_time = _Time(end_time)

    utc_now = datetime.datetime.utcnow()
    sent_at = datetime.datetime(
        year=utc_now.year,
        month=utc_now.month,
        day=utc_now.day,
        hour=from_time.hour,
        minute=from_time.minute
    )

    completion_from_datetime = datetime.datetime(
        year=utc_now.year,
        month=utc_now.month,
        day=utc_now.day,
        hour=0,
        minute=0
    )

    completion_to_datetime = datetime.datetime(
        year=utc_now.year,
        month=utc_now.month,
        day=utc_now.day,
        hour=23,
        minute=59
    )

    timezone = round((sent_at - utc_now).total_seconds() / HOUR)

    event = Events().findOne(dict(_id=event_id))

    profile_query = dict(
        appletId=applet_id,
        timezone=timezone,
        profile=True,
        completed_activities={'$elemMatch': dict(activity_id=ObjectId(activity_id))}
    )

    if event['individualized']:
        profile_query.update(dict(
            individual_events={'$gte': 1},
            _id={'$in': event['data']['users']}
        ))

    profiles = Profile().find(
        query=profile_query,
        fields=['deviceId', 'badge', 'userId', 'timezone', '_id', 'completed_activities']
    )

    should_be_send_device_ids = []

    for profile in profiles:
        not_completed = True

        for completed_activity in profile['completed_activities']:
            completed_time = completed_activity['completed_time']
            if completed_activity['activity_id'] != ObjectId(activity_id):
                continue
            if not completed_time:
                continue
            if completion_from_datetime < completed_time < completion_to_datetime:
                not_completed = False
                break

        if not_completed:
            should_be_send_device_ids.append(profile['deviceId'])

    if should_be_send_device_ids:
        message_title = event['data']['title']
        message_body = event['data']['description']
        _send_notification(
            registration_ids=should_be_send_device_ids,
            message_title=message_title,
            message_body=message_body,
            data_message={
                "event_id": str(event_id),
                "applet_id": str(applet_id),
                "activity_id": str(activity_id),
                "activity_flow_id": None,
                "type": 'event-alert'
            },
            extra_kwargs={"apns_expiration": "0"},
            content_available=True,
        )


def _send_notification(**kwargs):
    result = _notification_service.notify_multiple_devices(**kwargs)
    print(f'Notifications with failure status - {str(result["failure"])}')
    print(f'Notifications with success status - {str(result["success"])}')
