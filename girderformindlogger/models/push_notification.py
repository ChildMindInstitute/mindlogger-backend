import random

import cherrypy
from redis import Redis
from rq_scheduler import Scheduler
from datetime import datetime, timedelta
from girderformindlogger.external.notification import send_push_notification
from girderformindlogger.models import getRedisConnection


class PushNotification(Scheduler):
    def __init__(self, event):
        super(PushNotification, self).__init__(connection=getRedisConnection())
        self.current_time = datetime.utcnow()
        self.event = event
        self.schedule_range = {
            "start": self.current_time.strftime('%Y/%m/%d'),
            "end": None
        }
        self.start_time = self.current_time.strftime('%H:%M')

        if event and 'notifications' in event['data'] and event['data']['notifications'][0]['start']:
            self.start_time = event['data']['notifications'][0]['start']
        self.start_time = datetime.strptime(self.start_time, '%H:%M')

        self.end_time = None

    def set_schedules(self):
        """
        Creates the cronjobs for sending notifications
        """
        self.remove_schedules()
        notifications = self.event.get('data', {}).get('notifications', [])
        event_type = self.event.get('data', {}).get('eventType', '')

        if self.event['data'].get('reminder', {}).get('valid', False):
            self.set_reminders()

        for notification in notifications:
            if not notification['start']:
                continue

            self.date_format(notification)

            if notification['random']:
                return self._set_scheduler_with_random_time()

            self.event['sendTime'].append(self.start_time.strftime('%H:%M'))

            if event_type == '' or event_type == 'Daily':  # Daily or non-recurrent event.
                launch_time = self.first_launch_time()
                repeat = self.repeat_time(launch_time)
                self.__set_job(launch_time, repeat)

            if event_type == 'Weekly':
                self.__set_cron(self.prepare_weekly_schedule())

            if event_type == 'Monthly':
                self.__set_cron(self.prepare_monthly_schedule())


    def set_reminders(self):
        event_type = self.event.get('data', {}).get('eventType', '')
        reminder = self.event.get('data', {}).get('reminder', {})

        self.date_format({
            "start": reminder.get('time', '00:00'),
            "end": None,
            "random": False
        })

        def addDays(dateStr, days):
            date = datetime.strptime(dateStr, '%Y/%m/%d')
            date = date + timedelta(days=int(days))

            return datetime.strftime(date, '%Y/%m/%d')

        if self.schedule_range['start']:
            self.schedule_range['start'] = addDays(self.schedule_range['start'], reminder.get('days', 0))

        if self.schedule_range['end']:
            self.schedule_range['end'] = addDays(self.schedule_range['end'], reminder.get('days', 0))

        self.event['sendTime'].append(self.start_time.strftime('%H:%M'))

        if event_type == '' or event_type == 'Daily':  # Daily or non-recurrent event.
            launch_time = self.first_launch_time()
            repeat = self.repeat_time(launch_time)
            self.__set_job(launch_time, repeat, True)

        if event_type == 'Weekly':
            self.__set_cron(self.prepare_weekly_schedule(), True)

        if event_type == 'Monthly':
            self.__set_cron(self.prepare_monthly_schedule(), True)

    def first_launch_time(self, start_time=None):
        launch_day = self.schedule_range['start']
        tmp = datetime.strptime(
                f'{ launch_day } {start_time.hour if start_time else self.start_time.hour}:{start_time.minute if start_time else self.start_time.minute}',
                '%Y/%m/%d %H:%M') - timedelta(hours=12)

        if tmp <= self.current_time:
            tmp = datetime.strptime(
                    f'{self.current_time.year}/{self.current_time.month}/{self.current_time.day} '
                    f'{self.current_time.hour}:{start_time.minute if start_time else self.start_time.minute}',
                    '%Y/%m/%d %H:%M')
            for _ in range(4):
                if tmp < self.current_time:
                    tmp += timedelta(minutes=15)
                    continue
                if tmp > self.current_time and (tmp - self.current_time).total_seconds() / 60 > 15:
                    tmp -= timedelta(hours=1)
                    continue
                break
        return tmp

    def repeat_time(self, launch_time):
        end_time = self.schedule_range["end"]

        if end_time:
            end_time = datetime.strptime(f'{end_time} {self.start_time.strftime("%H:%M")}', '%Y/%m/%d %H:%M')

        start_time = datetime.strptime(
            f'{launch_time.year}/{launch_time.month}/{launch_time.day} {launch_time.strftime("%H:%M")}',
            '%Y/%m/%d %H:%M')

        if end_time:
            end_time += timedelta(hours=11, minutes=45)

            if end_time < start_time:
                return 0
            repeats = round(((end_time - start_time).total_seconds() / 3600) * 4) + 1
            return repeats
        return None

    def prepare_weekly_schedule(self):
        """
        Generates the cron string the weekly events.

        :return: the cron string.
        """
        first_cron_launch = min([(self.start_time + timedelta(minutes=15 * i)).minute for i in range(1, 5)])
        week_day = self.event.get('schedule', {}).get('dayOfWeek', [self.current_time.weekday()])[0]

        return f"{first_cron_launch}/15 * * * {week_day}"

    def prepare_monthly_schedule(self):
        """
        Generates the cron string the weekly events.

        :return: the cron string.
        """
        first_cron_launch = min([(self.start_time + timedelta(minutes=15 * i)).minute for i in range(1, 5)])
        dayOfMonth = self.event.get('schedule', {}).get('dayOfMonth', [None])[0]

        return f"{first_cron_launch}/15 * {dayOfMonth} * *"

    def random_reschedule(self):
        self.remove_schedules()
        for notification in self.event['data']['notifications']:
            self.date_format(notification)
            self._set_scheduler_with_random_time()

    def _set_scheduler_with_random_time(self):
        event_type = self.event.get('data', {}).get('eventType', '')
        self.event['sendTime'] = []

        self.start_time = self.__random_date() if self.end_time else self.start_time
        self.event['sendTime'].append(self.start_time.strftime('%H:%M'))

        if event_type == '' or event_type == 'Daily':  # Non-recurring or daily event.
            first_launch = self.first_launch_time(start_time=self.start_time)
            repeat = self.repeat_time(first_launch)
            self.__set_job(first_launch, repeat)
            return 0

        if event_type == 'Weekly':
            self.__set_cron(self.prepare_weekly_schedule())

        if event_type == 'Monthly':
            self.__set_cron(self.prepare_monthly_schedule())

    def __set_job(self, first_launch=datetime.utcnow(), repeat=None, isReminder=False):
        """
        Sets a job to send the notification on the given date.

        :param first_launch: the datetime for the first notification.
        :param repeat: Number of times that the notification will be sent.
        """
        if repeat == 0:
            return

        job = self.schedule(
                scheduled_time=first_launch,  # Time for the first execution.
                func=send_push_notification,  # Function to be executed.
                kwargs={
                    "applet_id": self.event.get("applet_id"),
                    "event_id": self.event.get("_id"),
                    "activity_id": self.event["data"].get("activity_id", None),
                    "send_time": self.start_time.strftime('%H:%M'),
                    "reminder": isReminder
                },
                interval=900,  # Time before the function is called again (in seconds).
                repeat=repeat,  # Repeat the event this number of times.
            )
        self.event["schedulers"].append(job.id)

    def __set_cron(self, cron_string, repeat=None, isReminder=False):
        """
        Sets a cron job to send notifications periodically.

        :param repeat: Number of times that the notification will be sent.
        """
        job = self.cron(
                cron_string,
                func=send_push_notification,  # Function to be executed.
                kwargs={
                    "applet_id": self.event.get("applet_id"),
                    "event_id": self.event.get("_id"),
                    "activity_id": self.event["data"].get("activity_id", None),
                    "send_time": self.start_time.strftime('%H:%M'),
                    "reminder": isReminder
                },
                repeat=repeat,  # Repeat the event this number of times.
                use_local_timezone=False
            )
        self.event["schedulers"].append(job.id)

    def __random_date(self):
        """
        Random date set between range of date
        """
        time_between_dates = self.end_time - self.start_time
        days_between_dates = time_between_dates.seconds
        random_number_of_seconds = random.randrange(days_between_dates)
        return self.start_time + timedelta(seconds=random_number_of_seconds)

    def date_format(self, notification):
        schedule = self.event.get('schedule', {})
        event_data = self.event.get('data', {})
        event_type = event_data.get('eventType', '')
        current_year = self.current_time.year
        current_month = self.current_time.month
        current_day = self.current_time.day

        self.start_time = datetime.strptime(
            f'{current_year}/{current_month}/{current_day} {notification["start"]}',
            '%Y/%m/%d %H:%M')

        if event_type == '':  # Single non-recurring event.
            self.notification_type = 1  # Backwards-compatibility.
            year = schedule.get('year', [None])
            scheduled_date = str(
                str(schedule['year'][0]) + '/' +  # Year.
                ('0' + str(schedule['month'][0] + 1))[-2:] + '/' +  # Zero-padded month.
                ('0' + str(schedule['dayOfMonth'][0]))[-2:])  # Zero-padded date.
            self.schedule_range['start'] = scheduled_date
            self.schedule_range['end'] = scheduled_date

            if notification and notification['random']:
                self.end_time = datetime.strptime(
                    f'{self.current_time.year}/{self.current_time.month}/{self.current_time.day} {notification["end"]}',
                    '%Y/%m/%d %H:%M') if notification['end'] else self.start_time

        else:  # Daily, weekly or monthly event.
            start = schedule.get('start', None)
            end = schedule.get('end', None)

            if start:
                self.schedule_range['start'] = datetime.fromtimestamp(
                    float(start) / 1000).strftime('%Y/%m/%d')
            if end:
                self.schedule_range['end'] = datetime.fromtimestamp(
                    float(end) / 1000).strftime('%Y/%m/%d')

        if event_type == 'Daily':
            self.notification_type = 2  # Backwards-compatibility.

        if event_type == 'Weekly':
            self.notification_type = 3  # Backwards-compatibility.
            self.schedule_range['dayOfWeek'] = schedule['dayOfWeek'][0]  # Is this being used?

        if event_type == 'Monthly':
            self.notification_type = 4  # Backwards-compatibility.

    def remove_schedules(self, jobs=None):
        jobs = jobs or self.event.get('schedulers') or []
        for job in jobs:
            self.cancel(job)

        self.event['schedulers'] = []
        self.event['sendTime'] = []
