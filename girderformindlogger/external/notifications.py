from pyfcm import FCMNotification

push_service = FCMNotification(
    api_key='AAAAJOyOEz4:APA91bFudM5Cc1Qynqy7QGxDBa-2zrttoRw6ZdvE9PQbfIuAB9SFvPje7DcFMmPuX1IizR1NAa7eHC3qXmE6nmOpgQxXbZ0sNO_n1NITc1sE5NH3d8W9ld-cfN7sXNr6IAOuodtEwQy-',
    proxy_dict={})


def send_push_notification(data):
    message_title = data['head']
    message_body = data['content']
    result = push_service.notify_multiple_devices(registration_ids=[data['device_id']],
                                                  message_title=message_title,
                                                  message_body=message_body)
