from girderformindlogger.models.model_base import AccessControlledModel, Model
import datetime

class ResponseLog(Model):
    """
    collection to store the responses logs
    """

    def initialize(self):
        self.name = 'responseLog'

    def validate(self, document):
        return document

    def addCheckFileUploadedLog(self, applet_id, activity_id, fileIds, activityStartedAt, user, deviceId):
        newLog = {
            'type': 'checkFileUploaded',
            'appletId': applet_id,
            'activityId': activity_id,
            'fileIds': fileIds,
            'userId': user['_id'],
            'deviceId': deviceId,
            'responseStarted': activityStartedAt,
            'created': datetime.datetime.utcnow(),
            'success': False,
        }
        return self.save(newLog)

    def addCheckResponseExistsLog(self, applet_id, activity_id, activityStartedAt, user, deviceId):
        newLog = {
            'type': 'checkResponseExists',
            'appletId': applet_id,
            'activityId': activity_id,
            'userId': user['_id'],
            'deviceId': deviceId,
            'responseStarted': activityStartedAt,
            'created': datetime.datetime.utcnow(),
            'success': False,
        }
        return self.save(newLog)

    def addResponseLog(self, applet_id, activity_id, metadata, params, user, deviceId, activityStartedAt):
        isFile = bool(params)
        itemsSource = params if isFile else metadata.get('responses', {})
        newLog = {
            'type': 'file' if isFile else 'activity',
            'appletId': applet_id,
            'activityId': activity_id,
            'userId': user['_id'],
            'deviceId': deviceId,
            'responseStarted': activityStartedAt if isFile else metadata.get('responseStarted'),
            'items': [key.split('/').pop() for key in itemsSource],
            'fileIds': [v.filename for k,v in params.items()],
            'created': datetime.datetime.utcnow(),
            'success': False,
        }
        return self.save(newLog)

    def markSuccess(self, log):
        log['success'] = True
        return self.save(log)
