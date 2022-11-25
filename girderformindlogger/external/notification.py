import datetime

from bson import ObjectId
from pyfcm import FCMNotification
from girderformindlogger.utility.notification import FirebaseNotification
from collections import defaultdict

push_service = FirebaseNotification(
        api_key='AAAAJOyOEz4:APA91bFudM5Cc1Qynqy7QGxDBa-2zrttoRw6ZdvE9PQbfIuAB9SFvPje7DcFMmPuX1IizR1NAa7eHC3qXmE6nmOpgQxXbZ0sNO_n1NITc1sE5NH3d8W9ld-cfN7sXNr6IAOuodtEwQy-',
        proxy_dict={})

AMOUNT_MESSAGES_PER_REQUEST = 1000


# this handles notifications for activities
def send_push_notification(applet_id, event_id, activity_id=None, activity_flow_id=None, send_time=None, reminder=False ,type_="event-alert"):
    return
    from girderformindlogger.models.events import Events
    from girderformindlogger.models.profile import Profile

    now = datetime.datetime.utcnow()
    now = datetime.datetime.strptime(now.strftime('%Y/%m/%d %H:%M'), '%Y/%m/%d %H:%M')

    eventsModel = Events()
    event = eventsModel.findOne({'_id': event_id})

    print('notification params', applet_id, event_id, activity_id, send_time, reminder)

    if event:
        event_time = datetime.datetime.strptime(
            f"{now.year}/{now.month}/{now.day} {send_time}", '%Y/%m/%d %H:%M')

        diff = (event_time - now).total_seconds() / 3600

        # this is temporary fix for timezone issue
        if diff >= 12:
            diff = diff - 24
        elif diff < -12:
            diff = diff + 24

        timezone = round(diff * 4, 0) / 4

        query = {
            'appletId': applet_id,
            'timezone': round(timezone, 2),
            'profile': True,
            'individual_events': 0
        }

        print('current time - ', now)
        print('query - ', query)

        if event['individualized']:
            query['individual_events'] = {'$gte': 1}
            query['_id'] = {
                '$in': event['data']['users']
            }

        if activity_id or activity_flow_id:
            rangeStart = now - datetime.timedelta(hours=12)

            if reminder:
                days = int(event.get('data', {}).get('reminder', {}).get('days', 0))
                time = event.get('data', {}).get('reminder', {}).get('time', '00:00')

                rangeStart = now - datetime.timedelta(days=days, hours=int(time[:2]), minutes=int(time[-2:]))

            if activity_id:
                query['completed_activities'] = {
                    '$elemMatch': {
                        '$or': [
                            {
                                'activity_id': activity_id,
                                'completed_time': { '$not': { '$gt': rangeStart, '$lt': now } }
                            },
                            {
                                'activity_id': activity_id,
                                'completed_time': { '$eq': None }
                            }
                        ]
                    }
                }
            else:
                query['activity_flows'] = {
                    '$elemMatch': {
                        '$or': [
                            {
                                'activity_flow_id': activity_flow_id,
                                'completed_time': { '$not': { '$gt': rangeStart, '$lt': now } }
                            },
                            {
                                'activity_flow_id': activity_flow_id,
                                'completed_time': { '$eq': None }
                            }
                        ]
                    }
                }

        profiles = list(Profile().find(query=query, fields=['deviceId', 'badge', 'userId']))

        # ordered by badge
        device_ids = []
        for profile in profiles:
            device_ids.append(profile["deviceId"])

        title = 'Tap to update the schedule.'
        body = 'Your schedule has been changed, tap to update.'

        result = push_service.notify_multiple_devices(
            registration_ids=device_ids,
            message_title=title,
            message_body=body,
            time_to_live=0,
            data_message={
                "event_id": str(event_id),
                "applet_id": str(applet_id),
                "activity_id": str(activity_id),
                "activity_flow_id": str(activity_flow_id),
                "type": type_,
                "is_server": True
            },
            extra_kwargs={"apns_expiration": "0"},
        )

        print(f'Notifications with failure status - {str(result["failure"])}')
        print(f'Notifications with success status - {str(result["success"])}')

        Profile().updateProfileBadgets(profiles)

        # if random time we will reschedule it in time between 23:45 and 23:59
        # if not reminder and event['data']['notifications'][0][
        #     'random'] and now.hour == 23 and 59 >= now.minute >= 45:
        #     eventsModel.rescheduleRandomNotifications(event)
        # elif abs(
        #     diff - timezone) * 30 >= 1:  # reschedule notification if difference is larger than 2 min
        #     print('rescheduling event ...')
        #     eventsModel.setSchedule(event)
        #     eventsModel.save(event)


def send_notification(title:str, body:str, type_:str, device_ids:list):
    result = push_service.notify_multiple_devices(
        registration_ids=device_ids,
        message_title=title,
        message_body=body,
        time_to_live=0,
        data_message={
            "type": type_,
            "is_server": True
        },
        extra_kwargs={
            "apns_expiration": str(
                int((datetime.datetime.utcnow() + datetime.timedelta(hours=8)).microsecond / 1000)
            )
        },
    )

    print(f'Notifications with failure status - {str(result["failure"])}')
    print(f'Notifications with success status - {str(result["success"])}')
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


def send_applet_update_notification(applet, isDeleted=False, profiles=[]):
    from girderformindlogger.models.profile import Profile

    applet_id = applet['_id']
    appletName = applet['meta']['applet'].get('displayName',
                                              applet.get('displayName', 'new applet'))

    profiles = Profile().get_profiles_by_applet_id(applet_id) if not profiles else profiles

    # ordered by badge
    message_requests = defaultdict(list)
    for profile in profiles:
        if (isDeleted or not profile.get('deactivated', False)) and profile.get('deviceId', None):
            message_requests[profile['badge']].append(profile['deviceId'])

    message_title = 'Applet Update',
    message_body = f'Content of your applet ({appletName}) was updated by editor.',
    data_message = {
        "applet_id": str(applet_id),
        "type": 'applet-update-alert'
    }

    if isDeleted:
        message_title = 'Applet Delete'
        message_body = f'Your applet ({appletName}) was deleted by manager'
        data_message['type'] = 'applet-delete-alert'

    for badge in message_requests:
        result = push_service.notify_multiple_devices(
            registration_ids=message_requests[badge],
            message_title=message_title,
            message_body=message_body,
            time_to_live=0,
            data_message=data_message,
            badge=int(badge) + 1
        )

    Profile().updateProfileBadgets(profiles)
