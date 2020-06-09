import datetime
from pyfcm import FCMNotification

push_service = FCMNotification(
        api_key='AAAAJOyOEz4:APA91bFudM5Cc1Qynqy7QGxDBa-2zrttoRw6ZdvE9PQbfIuAB9SFvPje7DcFMmPuX1IizR1NAa7eHC3qXmE6nmOpgQxXbZ0sNO_n1NITc1sE5NH3d8W9ld-cfN7sXNr6IAOuodtEwQy-',
        proxy_dict={})


def send_push_notification(applet_id, event_id):
    from girderformindlogger.models.events import Events
    from girderformindlogger.models.profile import Profile

    now = datetime.datetime.utcnow()
    now = datetime.datetime.strptime(now.strftime('%Y/%m/%d %H:%M'), '%Y/%m/%d %H:%M')

    event = Events().findOne({'_id': event_id})

    if event:
        event_time = datetime.datetime.strptime(
            f"{now.year}/{now.month}/{now.day} {event['sendTime'][0]}", '%Y/%m/%d %H:%M')

        timezone = (event_time - now).total_seconds() / 3600

        query = {
            'appletId': applet_id,
            'timezone': round(timezone, 2),
            'profile': True
        }

        if event['individualized']:
            query['individual_events'] = {'$gte': 1}

        if event['data']['notifications'][0]['notifyIfIncomplete']:
            query['completed_activities.completed_time'] = {
                '$ne': now.strftime('%Y/%m/%d')
            }

        print(f'Query - {query}')
        profiles = list(Profile().find(query=query, fields=['deviceId']))

        device_ids = [profile['deviceId'] for profile in profiles]
        print(f'Device ids found - {len(device_ids)}')

        message_title = event['data']['title']
        message_body = event['data']['description']
        result = push_service.notify_multiple_devices(registration_ids=device_ids,
                                                      message_title=message_title,
                                                      message_body=message_body)

        print(f'Status - {"failed " + str(result["failure"]) if result["failure"] else "success " + str(result["success"])}')

        # if random time we will reschedule it in time between 23:45 and 23:59
        if event['data']['notifications'][0]['random'] and now.hour == 23 and 59 >= now.minute >= 45:
            Events().rescheduleRandomNotifications(event)
