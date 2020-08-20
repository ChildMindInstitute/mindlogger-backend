from rq import Worker

from girderformindlogger.models import getRedisConnection
redis = getRedisConnection()

Worker(['default'], connection=redis).work(with_scheduler=True)

