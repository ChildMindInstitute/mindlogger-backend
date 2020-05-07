import random
from redis import Redis
from rq_scheduler import Scheduler
from datetime import datetime, timedelta
from girderformindlogger.external.notification import send_push_notification


class PushNotification(Scheduler):
    def __init__(self, event):
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

    def set_schedules(self):
        self.remove_schedules()

        for notification in self.event['data']['notifications']:
            self.date_format(notification)
            if notification['random']:
                self._set_scheduler_with_random_time(notification)
            else:
                self.event['sendTime'] = self.start_time.strftime('%H:%M')

                if self.notification_type in [1, 2]:
                    launch_time = self.first_launch_time()
                    repeat = self.repeat_time(launch_time)
                    self.__set_job(launch_time, repeat)

                if self.notification_type == 3:
                    launch_time = self.prepare_weekly_schedule()
                    print(launch_time)
                    self.__set_cron(launch_time)

    def first_launch_time(self, start_time=None):
        launch_time = self.current_time
        tmp = start_time or datetime.strptime(
                f'{launch_time.year}/{launch_time.month}/{launch_time.day} {launch_time.hour}:{self.start_time.minute}',
                '%Y/%m/%d %H:%M')

        for _ in range(4):
            if tmp < launch_time:
                tmp += timedelta(minutes=15)
                continue
            if tmp > launch_time and (tmp - launch_time).total_seconds() / 60 > 15:
                tmp -= timedelta(hours=1)
                continue
            break
        return tmp

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
            return f"*/15 * * * {self.event['schedule']['dayOfWeek'][0]}"
        return f"*/15 * * * {self.current_time.weekday()}"

    def random_reschedule(self):
        self.remove_schedules()
        for notification in self.event['data']['notifications']:
            self._set_scheduler_with_random_time(notification)

    def _set_scheduler_with_random_time(self, notification):
        self.event['sendTime'] = []
        self.end_time = datetime.strptime(notification['end'], '%H:%M') \
            if notification['end'] else None

        random_time = self.__random_date() if self.end_time else self.start_time
        self.event['sendTime'].append(random_time.strftime('%H:%M'))

        if self.notification_type in [1, 2]:
            first_launch = self.first_launch_time(start_time=random_time)
            repeat = self.repeat_time(first_launch)
            self.__set_job(first_launch, repeat)
            return 0
        first_launch = self.prepare_weekly_schedule()
        self.__set_cron(first_launch)

    def __set_job(self, first_launch=datetime.utcnow(), repeat=None):
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

    def __set_cron(self, first_launch, repeat=None):
        job = self.cron(
                first_launch,
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

        self.event['schedulers'] = []
