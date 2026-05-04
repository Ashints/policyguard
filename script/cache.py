import redis
import json
import hashlib
import logging

logger=logging.getLogger(__name__)

redis_client= redis.Redis(
    host="localhost",
    port=6379,
    db=0,
    decode_responses=True
)
CACHE_TTL_SECONDS = 60 * 60 * 24 

def make_cache_key(prefix: str, text: str) -> str:
    digest = hashlib.sha256(text.strip().lower().encode()).hexdigest()
    return f"{prefix}:{digest}"