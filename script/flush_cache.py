# flush_cache.py
import redis

redis_client = redis.Redis(
    host="localhost",
    port=6379,
    db=0,
    decode_responses=True
)

# Flush all cached answers
redis_client.flushdb()
print("✓ Redis cache cleared!")