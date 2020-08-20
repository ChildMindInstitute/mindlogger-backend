import datetime

from bson import ObjectId
from pyfcm import FCMNotification

push_service = FCMNotification(
        api_key='AAAAJOyOEz4:APA91bFudM5Cc1Qynqy7QGxDBa-2zrttoRw6ZdvE9PQbfIuAB9SFvPje7DcFMmPuX1IizR1NAa7eHC3qXmE6nmOpgQxXbZ0sNO_n1NITc1sE5NH3d8W9ld-cfN7sXNr6IAOuodtEwQy-',
        proxy_dict={})


def send_push_notification(applet_id, event_id, activity_id=None, send_time=None):
    from girderformindlogger.models.events import Events
    from girderformindlogger.models.profile import Profile

    now = datetime.datetime.utcnow()
    now = datetime.datetime.strptime(now.strftime('%Y/%m/%d %H:%M'), '%Y/%m/%d %H:%M')

    event = Events().findOne({'_id': event_id})

    if event:
        event_time = datetime.datetime.strptime(
            f"{now.year}/{now.month}/{now.day} {send_time}", '%Y/%m/%d %H:%M')

        timezone = (event_time - now).total_seconds() / 3600

        # this is temporary fix for timezone issue
        if timezone >= 12:
            timezone = timezone - 24
        elif timezone < -12:
            timezone = timezone + 24

        print(f'Timezone - {timezone}')

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

        if activity_id:
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

        profiles = list(Profile().find(query=query, fields=['deviceId', 'badge']))

        message_title = event['data']['title']
        message_body = event['data']['description']

        for profile in profiles:
            if len(profile['deviceId']):
                profile['badge'] = profile['badge'] + 1
                result = push_service.notify_single_device(
                    registration_id=profile['deviceId'],
                    badge=int(profile.get('badge', 0)),
                    message_title=message_title,
                    message_body=message_body,
                    data_message={
                        "event_id": str(event_id),
                        "applet_id": str(applet_id),
                        "activity_id": str(activity_id)
                    }
                )
                print(
                    f'Status - {"failed " + str(result["failure"]) if result["failure"] else "success " + str(result["success"])}')
                if 'success' in result:
                    Profile().increment(query={"_id": profile['_id']}, field='badge', amount=1)

        # if random time we will reschedule it in time between 23:45 and 23:59
        if event['data']['notifications'][0]['random'] and now.hour == 23 and 59 >= now.minute >= 45:
            Events().rescheduleRandomNotifications(event)
