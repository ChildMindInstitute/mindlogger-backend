# copy jobs from src and merge them to dst redis
# hint: run redis-cleanup against src first

from redis import Redis
import pprint

redisSrc = Redis(host='localhost', port=6379)
redisDst = Redis(host='localhost', port=6179)

index = {}
for key in redisDst.scan_iter('rq:job:*'):
    if redisDst.type(key) != b'hash':
        continue
    val = redisDst.hgetall(key)
    dkey = val[b'description']
    if (dkey in index):
        index[dkey] += 1
        continue
    else:
        index[dkey] = 1

stats = {"all": 0, "duplicated": 0, "copied": 0}

index = {}

scheduledObj = dict(redisSrc.zrange(b'rq:scheduler:scheduled_jobs', 0, -1, withscores=True)) #ZSET
jobKeys = redisSrc.keys('rq:job:*')

print('keys to process', len(jobKeys))


for key in jobKeys:
    if redisSrc.type(key) != b'hash':
        continue

    stats['all'] += 1
    val = redisSrc.hgetall(key)

    dkey = val[b'description']
    if (dkey in index):
        index[dkey] += 1
        stats['duplicated'] += 1
        continue
    else:
        index[dkey] = 1

    stats['copied'] += 1

    # insert job
    for k in val:
        if (redisDst.hget(key, k) is None):
            redisDst.hset(key, k, val[k])

    # schedule the job
    id = key.decode().split(':').pop().encode()
    if (id in scheduledObj):
        time = scheduledObj[id]
        redisDst.zadd(b'rq:scheduler:scheduled_jobs', {id: time})

pprint.pprint(stats)
