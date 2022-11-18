import datetime

from pymongo import DESCENDING

from girderformindlogger.models.model_base import Model


class NotificationLog(Model):

    def initialize(self):
        self.name = 'notification_logs'

    def create_log(
        self,
        userId,
        deviceId,
        actionType,
        notificationDescriptions=None,
        notificationsInQueue=None,
        scheduledNotifications=None,
    ):
        if not any([notificationDescriptions, notificationsInQueue, scheduledNotifications]):
            return None

        if notificationDescriptions is None:
            notificationDescriptions = dict()
        if notificationsInQueue is None:
            notificationsInQueue = dict()
        if scheduledNotifications is None:
            scheduledNotifications = dict()

        logs = self.get_logs(userId, deviceId, 1)
        previous = dict()
        if logs:
            previous = logs[0]
        notificationDescriptionsUpdated = True
        notificationsInQueueUpdated = True
        scheduledNotificationsUpdated = True
        creationDateTime = datetime.datetime.utcnow()

        if not notificationDescriptions:
            notificationDescriptions = previous.get('notificationDescriptions', dict())
            if notificationDescriptions:
                notificationDescriptionsUpdated = False

        if not notificationsInQueue:
            notificationsInQueue = previous.get('notificationsInQueue', dict())
            if notificationsInQueue:
                notificationsInQueueUpdated = False

        if not scheduledNotifications:
            scheduledNotifications = previous.get('scheduledNotifications', dict())
            if scheduledNotifications:
                scheduledNotificationsUpdated = False

        log = self.save(
            dict(
                userId=userId,
                deviceId=deviceId,
                actionType=actionType,
                creationDateTime=creationDateTime,
                notificationDescriptions=notificationDescriptions,
                notificationsInQueue=notificationsInQueue,
                scheduledNotifications=scheduledNotifications,
                notificationDescriptionsUpdated=notificationDescriptionsUpdated,
                notificationsInQueueUpdated=notificationsInQueueUpdated,
                scheduledNotificationsUpdated=scheduledNotificationsUpdated,
            )
        )
        return log

    def get_logs(self, userId, deviceId, limit=1):
        logs = self.find(
            query=dict(
                userId=userId,
                deviceId=deviceId,
            ),
            offset=0,
            limit=limit,
            sort=[('creationDateTime', DESCENDING)]
        )
        return list(logs)

    def validate(self, doc):
        return doc
