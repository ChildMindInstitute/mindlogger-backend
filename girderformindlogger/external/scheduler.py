from rq_scheduler import Scheduler

from girderformindlogger.utility import reconnect
from girderformindlogger.models import getRedisConnection
redis = getRedisConnection()


@reconnect(name='Scheduler')
def start():
    Scheduler(connection=redis, interval=5).run()


if __name__ == '__main__':
    start()
