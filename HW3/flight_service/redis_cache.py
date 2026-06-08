import os
import json
import logging
import redis

logger = logging.getLogger("redis_cache")
handler = logging.StreamHandler()
logger.addHandler(handler)
logger.setLevel(logging.INFO)

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))

try:
    redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
    redis_client.ping()
except Exception:
    redis_client = None

def get_from_cache(key):
    if not redis_client: return None
    try:
        val = redis_client.get(key)
        if val:
            logger.info(f"CACHE HIT: {key}")
            return json.loads(val)
        logger.info(f"CACHE MISS: {key}")
    except Exception:
        pass
    return None

def set_in_cache(key, data, ttl=300):
    if not redis_client: return
    try:
        redis_client.setex(key, ttl, json.dumps(data))
    except Exception:
        pass

def invalidate_cache(keys):
    if not redis_client: return
    try:
        for key in keys:
            redis_client.delete(key)
    except Exception:
        pass
