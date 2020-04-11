import redis
from config import *
RedisClient = redis.Redis(
    redis_server,
    redis_port
)

try:
    RedisClient.incr('test')
except redis.ConnectionError:
    raise

