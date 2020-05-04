import math
from redis import Redis
from rq_scheduler import Scheduler
from datetime import datetime, timedelta
from girderformindlogger.external.notifications import send_push_notification


class PushNotification(Scheduler):
    def __init__(self, event):
        super(PushNotification, self).__init__(connection=Redis())
        self.current_time = datetime.utcnow()
        self.event = event
        self.notification_type = 1
        self.schedule = {
            "start": datetime.utcnow(),
            "end": None
        }
        self.start_time = datetime.strptime(event['data']['notifications'][0]['start'], '%H:%M')

    def set_schedules(self):
        data = {
            "applet_id": self.event.get("applet_id"),
            "event_id": self.event.get("_id")
        }

        self.date_format()
        # print(f'repeat times - {self.repeat_time()}')
        launch_time = self.first_launch_time()
        print(f'first launch - {launch_time}')
        print(f'repeat_time - {self.repeat_time(launch_time)}')

        # job = self.enqueue_in(
        #     timedelta(2020, 4, 27, 16, 5),
        #     send_push_notification,
        #     data
        # )
        # self.notifications.append(job)

    def first_launch_time(self):
        launch_time = self.current_time
        tmp = self.start_time
        for _ in range(4):
            if tmp.minute <= launch_time.minute <= (tmp + timedelta(minutes=15)).minute\
            or 45 <= tmp.minute <= 59 and 45 < launch_time.minute <= 59 or 0 <= launch_time.minute <= 15:
                time = tmp + timedelta(minutes=15)
                launch_time = datetime.strptime(
                    f'{launch_time.year}/{launch_time.month}/{launch_time.day} {launch_time.hour}:{time.minute}',
                    '%Y/%m/%d %H:%M')
                break
            tmp = tmp + timedelta(minutes=15)

        return launch_time

    def repeat_time(self, launch_time):
        pass
        # end_time = datetime.strptime(
        #     f'{self.schedule["end"]} {launch_time.strftime("%H:%M")}', '%Y/%m/%d %H:%M')
        # start_time = datetime.strptime(
        #     f'{self.schedule["start"]} {launch_time.strftime("%H:%M")}', '%Y/%m/%d %H:%M')
        #
        # return math.floor((end_time - start_time).total_seconds() / 3600) * 4

    def date_format(self):
        if 'dayOfMonth' in self.event['schedule']:
            """
            Does not repeat configuration in case of single event with exact year, month, day
            """
            if self.event['data'].get('notifications', None) and \
                self.event['data']['notifications'][0]['random']:
                self.end_time = self.event['data']['notifications'][0]['end']
            if 'year' in self.event['schedule'] and 'month' in self.event['schedule'] \
                and 'dayOfMonth' in self.event['schedule']:
                current_date_schedule = str(str(self.event['schedule']['year'][0]) + '/' +
                                            ('0' + str(self.event['schedule']['month'][0] + 1))[
                                            -2:] + '/' +
                                            ('0' + str(self.event['schedule']['dayOfMonth'][0]))[-2:])
                self.schedule['start'] = current_date_schedule
                self.schedule['end'] = current_date_schedule

        elif 'dayOfWeek' in self.event['schedule']:
            """
            Weekly configuration in case of weekly event
            """
            self.notification_type = 3
            if 'start' in self.event['schedule'] and self.event['schedule']['start']:
                self.schedule['start'] = datetime.fromtimestamp(
                    float(self.event['schedule']['start']) / 1000).strftime('%Y/%m/%d')
            if 'end' in self.event['schedule'] and self.event['schedule']['end']:
                self.schedule['end'] = datetime.fromtimestamp(
                    float(self.event['schedule']['end']) / 1000).strftime('%Y/%m/%d')
            self.schedule['dayOfWeek'] = self.event['schedule']['dayOfWeek'][0]
        else:
            """
            Daily configuration in case of daily event
            """
            self.notification_type = 2
            if 'start' in self.event['schedule'] and self.event['schedule']['start']:
                self.schedule['start'] = datetime.fromtimestamp(
                    float(self.event['schedule']['start']) / 1000).strftime('%Y/%m/%d')
            if 'end' in self.event['schedule'] and self.event['schedule']['end']:
                self.schedule['end'] = datetime.fromtimestamp(
                    float(self.event['schedule']['end']) / 1000).strftime('%Y/%m/%d')

    def remove_schedules(self, jobs=None):
        for job in jobs:
            #self.cancel(job)
            print(f'{job} - removed')
