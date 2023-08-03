from girderformindlogger.models.model_base import AccessControlledModel, Model
import datetime
import sys

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
            'responseSize': self.getSize(metadata)
        }
        return self.save(newLog)

    def markSuccess(self, log):
        log['success'] = True
        return self.save(log)

    def getSize(self, obj, seen=None):
        """Recursively finds size of objects"""
        size = sys.getsizeof(obj)
        if seen is None:
            seen = set()
        obj_id = id(obj)
        if obj_id in seen:
            return 0
        # Important mark as seen *before* entering recursion to gracefully handle
        # self-referential objects
        seen.add(obj_id)
        if isinstance(obj, dict):
            size += sum([self.getSize(v, seen) for v in obj.values()])
            size += sum([self.getSize(k, seen) for k in obj.keys()])
        elif hasattr(obj, '__dict__'):
            size += self.getSize(obj.__dict__, seen)
        elif hasattr(obj, '__iter__') and not isinstance(obj, (str, bytes, bytearray)):
            size += sum([self.getSize(i, seen) for i in obj])
        return size
