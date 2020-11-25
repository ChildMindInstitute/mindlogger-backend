import datetime

from bson import ObjectId
from pyfcm import FCMNotification
from girderformindlogger.utility.notification import FirebaseNotification
from girderformindlogger.models.notification import Notification
from collections import defaultdict


push_service = FirebaseNotification(
        api_key='AAAAJOyOEz4:APA91bFudM5Cc1Qynqy7QGxDBa-2zrttoRw6ZdvE9PQbfIuAB9SFvPje7DcFMmPuX1IizR1NAa7eHC3qXmE6nmOpgQxXbZ0sNO_n1NITc1sE5NH3d8W9ld-cfN7sXNr6IAOuodtEwQy-',
        proxy_dict={})

AMOUNT_MESSAGES_PER_REQUEST = 1000


def get_profiles_need_renotify(event, ):
    pass


# this handles notifications for activities
def send_push_notification(applet_id, event_id, activity_id=None, send_time=None, notification_id=None):
    from girderformindlogger.models.events import Events
    from girderformindlogger.models.profile import Profile

    now = datetime.datetime.utcnow()
    now = datetime.datetime.strptime(now.strftime('%Y/%m/%d %H:%M'), '%Y/%m/%d %H:%M')

    event = Events().findOne({'_id': event_id})

    if event:
        event_time = datetime.datetime.strptime(
            f"{now.year}/{now.month}/{now.day} {send_time}", '%Y/%m/%d %H:%M')

        end_time = None
        if notification_id:
            notification = Notification().findOne(query={
                '_id': notification_id
            })

            if notification:
                end = notification.get('date', {}).get('end', None)
                if end:
                    end_time = datetime.datetime.strptime(
                        f"{now.year}/{now.month}/{now.day} {end}", '%Y/%m/%d %H:%M')

        # if notification_id:
        #     notification = Notification().findOne(query={
        #         '_id': notification_id
        #     })
        #
        #     if notification:
        #         start = notification.get('date', {}).get('start', None)
        #         if start:
        #             event_time = datetime.datetime.strptime(
        #                 f"{now.year}/{now.month}/{now.day} {start}", '%Y/%m/%d %H:%M')

        timezone = (event_time - now).total_seconds() / 3600

        # this is temporary fix for timezone issue
        if timezone >= 12:
            timezone = timezone - 24
        elif timezone < -12:
            timezone = timezone + 24

        query = {
            'appletId': applet_id,
            'timezone': round(timezone, 2),
            'profile': True,
            'individual_events': 0
        }

        if event['individualized']:
            query['individual_events'] = {'$gte': 1}
            query['_id'] = {
                '$in': event['data']['users']
            }

        if activity_id and not notification_id:
            query['completed_activities'] = {
                '$elemMatch': {
                    '$or': [
                        {
                            'activity_id': activity_id,
                            'completed_time': {
                                '$not': {
                                    '$gt': now - datetime.timedelta(hours=12),
                                    '$lt': now
                                }
                            }
                        },
                        {
                            'activity_id': activity_id,
                            'completed_time': {
                                '$eq': None
                            }
                        }
                    ]
                }
            }

        if activity_id and notification_id:
            query['completed_activities'] = {
                '$elemMatch': {
                    '$or': [
                        {
                            'activity_id': activity_id,
                            'completed_time': {
                                '$not': {
                                    '$gt': event_time,
                                    '$lt': end_time
                                }
                            }
                        },
                        {
                            'activity_id': activity_id,
                            'completed_time': {
                                '$eq': None
                            }
                        }
                    ]
                }
            }

        profiles = list(Profile().find(query=query, fields=['deviceId', 'badge']))

        # ordered by badge
        message_requests = defaultdict(list)
        for profile in profiles:
            message_requests[profile["badge"]].append(profile["deviceId"])

        for badge in message_requests:
            result = push_service.notify_multiple_devices(
                registration_ids=message_requests[badge],
                message_title=event['data']['title'],
                message_body=event['data']['description'],
                data_message={
                    "event_id": str(event_id),
                    "applet_id": str(applet_id),
                    "activity_id": str(activity_id),
                    "type": 'event-alert'
                },
                badge=int(badge) +1
            )

            print(f'Notifications with failure status - {str(result["failure"])}')
            print(f'Notifications with success status - {str(result["success"])}')

        Profile().updateProfileBadgets(profiles)

        # if random time we will reschedule it in time between 23:45 and 23:59
        if event['data']['notifications'][0]['random'] and now.hour == 23 and 59 >= now.minute >= 45:
            Events().rescheduleRandomNotifications(event)





# this handles other custom notifications
def send_custom_notification(notification):
    from girderformindlogger.models.user import User as UserModel
    from girderformindlogger.models.profile import Profile

    if notification['type'] == 'response-data-alert':
        user = UserModel().load(notification['userId'], force=True)

        if user['deviceId']:
            push_service.notify_single_device(
                registration_id=user['deviceId'],
                message_title=notification['data'].get('title', 'Response Alert'),
                message_body=notification['data'].get('description', ''),
                data_message={
                    "user_id": str(user['_id']),
                    "type": notification['type']
                }
            )
