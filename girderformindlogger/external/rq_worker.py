from rq import SimpleWorker

from girderformindlogger.utility import reconnect
from girderformindlogger.models import getRedisConnection
redis = getRedisConnection()


@reconnect(name='Worker')
def start():
    SimpleWorker(['default'], connection=redis).work(with_scheduler=True)


if __name__ == '__main__':
    start()
