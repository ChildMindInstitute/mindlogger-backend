from rq_scheduler import Scheduler

from girderformindlogger.models import getRedisConnection
redis = getRedisConnection()

Scheduler(connection=redis, interval=5).run()
