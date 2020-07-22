import os
import datetime

import firebase_admin
from firebase_admin import messaging, credentials

AMOUNT_MESSAGES_PER_REQUEST = 500
REQUESTS_LIMITATION_PER_EVENT = 230

ABSOLUTE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'serviceAccountKey.json')
cred = credentials.Certificate(ABSOLUTE_PATH)
app = firebase_admin.initialize_app(cred)


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

        notification = messaging.Notification(
            title=event['data']['title'],
            body=event['data']['description']
        )

        chunk_requests = [profiles[i:i + AMOUNT_MESSAGES_PER_REQUEST] for i in
                          range(0, len(profiles), AMOUNT_MESSAGES_PER_REQUEST)]

        # Limitation by firebase no more then 230 requests per minute
        if len(chunk_requests) > REQUESTS_LIMITATION_PER_EVENT:
            chunk_requests = chunk_requests[0:REQUESTS_LIMITATION_PER_EVENT]

        total_message_chunks = []

        for profiles in chunk_requests:
            messages = []

            for profile in profiles:
                messages.append(messaging.Message(
                    token=profile['deviceId'],
                    notification=notification,
                    data={
                        "event_id": str(event_id),
                        "applet_id": str(applet_id),
                        "activity_id": str(activity_id)
                    },
                    apns=messaging.APNSConfig(
                        payload=messaging.APNSPayload(
                            aps=messaging.Aps(badge=int(profile.get('badge', 0) + 1))
                        )
                    )
                ))
            total_message_chunks.append(messages)

        for messages in total_message_chunks:
            messaging.send_all(messages)

        Profile().increment(query={"_id": {
            "$in": [profile['_id'] for profile in profiles]
        }}, field='badge', amount=1)

        # if random time we will reschedule it in time between 23:45 and 23:59
        if event['data']['notifications'][0]['random'] and now.hour == 23 and 59 >= now.minute >= 45:
            Events().rescheduleRandomNotifications(event)
