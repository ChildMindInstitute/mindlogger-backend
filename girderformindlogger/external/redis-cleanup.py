# remove duplicated and not scheduled keys in case of redis is out of memory

from redis import Redis
import pprint
import os

def main(redis):

    stats = {"all": 0, "processed": 0, "unprocessed": 0, "duplicated": 0, "unscheduled": 0, "removed": 0}

    index = {}
    queueObj = dict.fromkeys(redis.lrange(b'rq:queue:default', 0, -1), 1) # LIST
    scheduledObj = dict(redis.zrange(b'rq:scheduler:scheduled_jobs', 0, -1, withscores=True)) #ZSET
    jobKeys = redis.keys('rq:job:*')

    print('keys to process', len(jobKeys))

    def dropJob(key):
        id = key.decode().split(':').pop().encode()
        if (id in scheduledObj):
            redis.zrem(b'rq:scheduler:scheduled_jobs', id)
        if (id in queueObj):
            redis.lrem(b'rq:queue:default', 0, id)
        redis.delete(key)

    for key in jobKeys:
        if redis.type(key) != b'hash':
            continue

        stats['all'] += 1
        val = redis.hgetall(key)

        id = key.decode().split(':').pop().encode()
        if (id not in scheduledObj):
            dropJob(key)
            stats['removed'] += 1
            stats['unscheduled'] += 1
            continue

        dkey = val[b'description']
        if (dkey in index):
            dropJob(key)
            index[dkey] += 1
            stats['duplicated'] += 1
            stats['removed'] += 1
            continue
        else:
            index[dkey] = 1

        if (val[b'started_at'] != b'' and val[b'ended_at'] != b''):
            stats['processed'] += 1
            continue

        stats['unprocessed'] += 1

    pprint.pprint(stats)


if __name__ == '__main__':
    redis = Redis(host=os.environ.get('REDIS_URI', 'localhost'),
                  port=os.environ.get('REDIS_PORT', 6379),
                  password=os.environ.get('REDIS_PASSWORD', ''))
    main(redis)
