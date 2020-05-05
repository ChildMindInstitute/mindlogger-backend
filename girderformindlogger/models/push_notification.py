import random
from pyfcm import FCMNotification
from bson import ObjectId
from redis import Redis
from rq_scheduler import Scheduler
from datetime import datetime, timedelta


class PushNotification(Scheduler):
    def __init__(self, event, callback):
        super(PushNotification, self).__init__(connection=Redis())
        self.current_time = datetime.utcnow()
        self.event = event
        self.notification_type = 1
        self.schedule_range = {
            "start": datetime.utcnow(),
            "end": None
        }
        self.start_time = datetime.strptime(event['data']['notifications'][0]['start'], '%H:%M')
        self.end_time = None
        self.send_push_notification = callback

    def set_schedules(self):
        self.remove_schedules()
        self.event['sendTime'] = []

        for notification in self.event['data']['notifications']:
            self.date_format(notification)
            if notification['random']:
                self._set_scheduler_with_random_time(notification)
            else:
                self.event['sendTime'] = self.start_time.strftime('%H:%M')
                launch_time = self.first_launch_time()

                if self.notification_type in [1, 2]:
                    repeat = self.repeat_time(launch_time)
                    self.__set_job(launch_time, repeat)

                if self.notification_type == 3:
                    self.__set_cron(launch_time)

    def first_launch_time(self, start_time=None):
        launch_time = self.current_time
        tmp = start_time or self.start_time
        for _ in range(4):
            if tmp.minute <= launch_time.minute <= (tmp + timedelta(minutes=15)).minute\
            or 45 <= tmp.minute <= 59 and 45 < launch_time.minute <= 59:
                time = tmp + timedelta(minutes=15)
                launch_time = datetime.strptime(
                    f'{launch_time.year}/{launch_time.month}/{launch_time.day} {launch_time.hour}:{time.minute}',
                    '%Y/%m/%d %H:%M')
                break
            tmp = tmp + timedelta(minutes=15)

        return launch_time

    def repeat_time(self, launch_time):
        end_time = self.schedule_range["end"]
        if self.notification_type == 1:
            end_time = datetime.strptime(
                f'{self.current_time.year}/{self.current_time.month}/{self.current_time.day} {self.start_time.strftime("%H:%M")}',
                '%Y/%m/%d %H:%M')

        if self.schedule_range["end"]:
            end_time = datetime.strptime(
                f'{self.schedule_range["end"]} {self.start_time.strftime("%H:%M")}', '%Y/%m/%d %H:%M')

        start_time = datetime.strptime(
            f'{launch_time.year}/{launch_time.month}/{launch_time.day} {launch_time.strftime("%H:%M")}',
            '%Y/%m/%d %H:%M')

        if end_time:
            end_time += timedelta(hours=11, minutes=45)
            return round(((end_time - start_time).total_seconds() / 3600) * 4) + 1

        return end_time

    def prepare_weekly_schedule(self):
        if 'dayOfWeek' in self.event["schedule"]:
            return f"*/15 * * * {self.event['schedule'][0]}"
        return f"*/15 * * * {self.current_time.weekday()}"

    def random_reschedule(self):
        self.remove_schedules()
        for notification in self.event['data']['notifications']:
            self._set_scheduler_with_random_time(notification)

    def _set_scheduler_with_random_time(self, notification):
        self.end_time = datetime.strptime(notification['end'], '%H:%M') \
            if notification['end'] else None

        random_time = self.__random_date() if self.end_time else self.start_time
        self.event['sendTime'].append(random_time.strftime('%H:%M'))
        first_launch = self.first_launch_time(start_time=random_time)
        if self.notification_type in [1, 2]:
            repeat = self.repeat_time(first_launch)
            self.__set_job(first_launch, repeat)
            return 0
        self.__set_cron()

    def __set_job(self, first_launch=datetime.utcnow(), repeat=None):
        job = self.schedule(
                scheduled_time=first_launch,
                func=self.send_push_notification,
                kwargs={
                    "applet_id": self.event.get("applet_id"),
                    "event_id": self.event.get("_id")
                },
                interval=900,
                repeat=repeat
            )
        self.event["schedulers"].append(job.id)
        print('------ Job was set')

    def __set_cron(self, first_launch=datetime.utcnow()):
        job = self.cron(
                first_launch,
                func=self.send_push_notification,
                kwargs={
                    "applet_id": self.event.get("applet_id"),
                    "event_id": self.event.get("_id")
                },
                repeat=None,
                use_local_timezone=False
            )
        self.event["schedulers"].append(job.id)
        print('------ Cron was set')

    def __random_date(self):
        """
        Random date set between range of date
        :params start: Start date range
        :type start: str
        :params end: End date range
        :type end: str
        :params format_str: Format date
        :type format_str: str
        """
        time_between_dates = self.end_time - self.start_time
        days_between_dates = time_between_dates.seconds
        random_number_of_seconds = random.randrange(days_between_dates)
        return self.start_time + timedelta(seconds=random_number_of_seconds)

    def date_format(self, notification):
        if 'dayOfMonth' in self.event['schedule']:
            """
            Does not repeat configuration in case of single event with exact year, month, day
            """
            if self.event['data'].get('notifications', None) and notification['random']:
                self.end_time = notification['end']
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
        jobs = jobs or self.event['schedulers']
        for job in jobs:
            self.cancel(job)

        print('All jobs were removed')
        self.event['schedulers'] = []
