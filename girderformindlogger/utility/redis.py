import json
import os
import time

import redis


class _RedisCache:
    _redis: redis.Redis
    _config: dict

    def create(self):
        self._config = {
            'host': os.environ.get('REDIS_URI', 'localhost'),
            'port': os.environ.get('REDIS_PORT', 6379),
            'password': os.environ.get('REDIS_PASSWORD', '')
        }
        self._start()

    def _start(self):
        assert self._config is not None, 'redis configuration is not initialized'

        self._redis = redis.Redis(**self._config)

    def set(self, key: str, data: dict, timeout=60):
        assert self._redis is not None, 'redis is not initialized'
        assert isinstance(data, dict), 'data should be dictionary'

        self._redis.set(key, json.dumps(data), ex=timeout)

    def get(self, key):
        assert self._redis is not None, 'redis is not initialized'
        return self._redis.get(key)

    def stop(self):
        if self._redis:
            self._redis.close()


cache = _RedisCache()
