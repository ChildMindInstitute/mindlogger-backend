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
        self.notification_type = 1
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
        self.remove_schedules()

        for notification in self.event['data']['notifications']:
            self.date_format(notification)
            if notification['random']:
                self._set_scheduler_with_random_time()
            else:
                self.event['sendTime'].append(self.start_time.strftime('%H:%M'))

                if self.notification_type in [1, 2]:
                    launch_time = self.first_launch_time()
                    repeat = self.repeat_time(launch_time)
                    self.__set_job(launch_time, repeat)

                if self.notification_type == 3:
                    self.__set_cron()

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

        print(f'First launch Time - {tmp}')
        return tmp

    def repeat_time(self, launch_time):
        end_time = self.schedule_range["end"]

        if end_time:
            end_time = datetime.strptime(f'{end_time} {self.start_time.strftime("%H:%M")}', '%Y/%m/%d %H:%M')
        else:
            end_time = datetime.strptime(
                f'{self.current_time.year}/{self.current_time.month}/{self.current_time.day} {self.start_time.strftime("%H:%M")}',
                '%Y/%m/%d %H:%M')

        start_time = datetime.strptime(
            f'{launch_time.year}/{launch_time.month}/{launch_time.day} {launch_time.strftime("%H:%M")}',
            '%Y/%m/%d %H:%M')

        if end_time:
            end_time += timedelta(hours=14)

            if end_time < start_time:
                return 0
            repeats = round(((end_time - start_time).total_seconds() / 3600) * 4) + 1
            return repeats
        return None

    def prepare_weekly_schedule(self):
        first_cron_launch = min([(self.start_time + timedelta(minutes=15 * i)).minute for i in range(1, 5)])
        if 'dayOfWeek' in self.event["schedule"]:
            return f"{first_cron_launch}/15 * * * {self.event['schedule']['dayOfWeek'][0]}"
        return f"{first_cron_launch}/15 * * * {self.current_time.weekday()}"

    def random_reschedule(self):
        self.remove_schedules()
        for notification in self.event['data']['notifications']:
            self.date_format(notification)
            self._set_scheduler_with_random_time()

    def _set_scheduler_with_random_time(self):
        self.event['sendTime'] = []
        print(f'Random end time - {self.end_time}')

        self.start_time = self.__random_date() if self.end_time else self.start_time
        self.event['sendTime'].append(self.start_time.strftime('%H:%M'))

        if self.notification_type in [1, 2]:
            first_launch = self.first_launch_time(start_time=self.start_time)
            repeat = self.repeat_time(first_launch)
            self.__set_job(first_launch, repeat)
            return 0
        self.__set_cron()

    def __set_job(self, first_launch=datetime.utcnow(), repeat=None):
        if repeat == 0:
            return

        job = self.schedule(
                scheduled_time=first_launch,
                func=send_push_notification,
                kwargs={
                    "applet_id": self.event.get("applet_id"),
                    "event_id": self.event.get("_id")
                },
                interval=900,
                repeat=repeat
            )
        self.event["schedulers"].append(job.id)

    def __set_cron(self, repeat=None):
        launch_time = self.prepare_weekly_schedule()
        print(f'Cron launch time - {launch_time}')
        job = self.cron(
                launch_time,
                func=send_push_notification,
                kwargs={
                    "applet_id": self.event.get("applet_id"),
                    "event_id": self.event.get("_id")
                },
                repeat=repeat,
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
        self.start_time = datetime.strptime(
            f'{self.current_time.year}/{self.current_time.month}/{self.current_time.day} {notification["start"]}',
            '%Y/%m/%d %H:%M')
        if 'dayOfMonth' in self.event['schedule']:
            """
            Does not repeat configuration in case of single event with exact year, month, day
            """
            if self.event['data'].get('notifications', None) and notification['random']:
                self.end_time = datetime.strptime(
                    f'{self.current_time.year}/{self.current_time.month}/{self.current_time.day} {notification["end"]}',
                    '%Y/%m/%d %H:%M') if notification['end'] else self.start_time
            if 'year' in self.event['schedule'] and 'month' in self.event['schedule'] \
                and 'dayOfMonth' in self.event['schedule']:
                current_date_schedule = str(str(self.event['schedule']['year'][0]) + '/' +
                                            ('0' + str(self.event['schedule']['month'][0] + 1))[
                                            -2:] + '/' +
                                            ('0' + str(self.event['schedule']['dayOfMonth'][0]))[-2:])
                self.schedule_range['start'] = current_date_schedule
                self.schedule_range['end'] = current_date_schedule

        elif 'dayOfWeek' in self.event['schedule']:
            """
            Weekly configuration in case of weekly event
            """
            self.notification_type = 3
            if 'start' in self.event['schedule'] and self.event['schedule']['start']:
                self.schedule_range['start'] = datetime.fromtimestamp(
                    float(self.event['schedule']['start']) / 1000).strftime('%Y/%m/%d')
            if 'end' in self.event['schedule'] and self.event['schedule']['end']:
                self.schedule_range['end'] = datetime.fromtimestamp(
                    float(self.event['schedule']['end']) / 1000).strftime('%Y/%m/%d')
            self.schedule_range['dayOfWeek'] = self.event['schedule']['dayOfWeek'][0]
        else:
            """
            Daily configuration in case of daily event
            """
            self.notification_type = 2
            if 'start' in self.event['schedule'] and self.event['schedule']['start']:
                self.schedule_range['start'] = datetime.fromtimestamp(
                    float(self.event['schedule']['start']) / 1000).strftime('%Y/%m/%d')
            if 'end' in self.event['schedule'] and self.event['schedule']['end']:
                self.schedule_range['end'] = datetime.fromtimestamp(
                    float(self.event['schedule']['end']) / 1000).strftime('%Y/%m/%d')

    def remove_schedules(self, jobs=None):
        jobs = jobs or self.event.get('schedulers') or []
        for job in jobs:
            self.cancel(job)

        self.event['schedulers'] = []
