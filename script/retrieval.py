import hashlib
import json
import logging
import re
import time

from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer

from script.cache import (
    redis_client,
    CACHE_TTL_SECONDS,
    make_cache_key,
)


logger = logging.getLogger(__name__)

COLLECTION_NAME = "policy_docs"
TOP_K = 3
MIN_SCORE = 0.25

qdrant = QdrantClient(
    host="localhost",
    port=6333,
)

logger.info("Loading embedding model...")

model = SentenceTransformer(
    "sentence-transformers/all-MiniLM-L6-v2"
)


def retrieve(query: str) -> list[dict]:
    total_start = time.perf_counter()

    normalized_query = " ".join(
        query.strip().lower().split()
    )

    cache_key = make_cache_key(
        "retrieval",
        normalized_query,
    )

    redis_start = time.perf_counter()

    cached = redis_client.get(cache_key)

    redis_read_ms = (
        time.perf_counter() - redis_start
    ) * 1000

    if cached:
        total_ms = (
            time.perf_counter() - total_start
        ) * 1000

        logger.info("Retrieval cache hit")
        logger.info(
            "Retrieval Redis read: %.2f ms",
            redis_read_ms,
        )
        logger.info(
            "Retrieval total: %.2f ms",
            total_ms,
        )

        return json.loads(cached)

    logger.info(
        "Retrieval cache miss: Redis read %.2f ms",
        redis_read_ms,
    )

    article_match = re.search(
        r"\barticle\s*(\d+)\b",
        normalized_query,
        re.IGNORECASE,
    )

    if article_match:
        article_id = f"article{article_match.group(1)}"

        logger.info(
            "Detected article lookup: %s",
            article_id,
        )

        qdrant_start = time.perf_counter()

        points, _ = qdrant.scroll(
            collection_name=COLLECTION_NAME,
            scroll_filter={
                "must": [
                    {
                        "key": "article",
                        "match": {
                            "value": article_id,
                        },
                    }
                ]
            },
            limit=50,
            with_payload=True,
            with_vectors=False,
        )

        qdrant_ms = (
            time.perf_counter() - qdrant_start
        ) * 1000

        logger.info(
            "Qdrant article lookup: %.2f ms",
            qdrant_ms,
        )

        results = []

        for point in points:
            payload = point.payload or {}

            results.append(
                {
                    "text": payload.get("text", ""),
                    "article": payload.get("article"),
                    "file": payload.get("file"),
                    "score": 1.0,
                }
            )

        redis_write_start = time.perf_counter()

        redis_client.setex(
            cache_key,
            CACHE_TTL_SECONDS,
            json.dumps(results),
        )

        redis_write_ms = (
            time.perf_counter() - redis_write_start
        ) * 1000

        total_ms = (
            time.perf_counter() - total_start
        ) * 1000

        logger.info(
            "Retrieval Redis write: %.2f ms",
            redis_write_ms,
        )
        logger.info(
            "Article retrieval total: %.2f ms",
            total_ms,
        )

        return results

    embedding_start = time.perf_counter()

    query_vector = model.encode(
        query,
        normalize_embeddings=True,
        convert_to_numpy=True,
        show_progress_bar=False,
    ).tolist()

    embedding_ms = (
        time.perf_counter() - embedding_start
    ) * 1000

    logger.info(
        "Query embedding: %.2f ms",
        embedding_ms,
    )

    qdrant_start = time.perf_counter()

    search_result = qdrant.query_points(
        collection_name=COLLECTION_NAME,
        query=query_vector,
        limit=TOP_K,
        with_payload=True,
        with_vectors=False,
    )

    qdrant_ms = (
        time.perf_counter() - qdrant_start
    ) * 1000

    logger.info(
        "Qdrant vector search: %.2f ms",
        qdrant_ms,
    )

    results = []

    for hit in search_result.points:
        if hit.score < MIN_SCORE:
            continue

        payload = hit.payload or {}

        results.append(
            {
                "text": payload.get("text", ""),
                "article": payload.get("article"),
                "file": payload.get("file"),
                "score": hit.score,
            }
        )

    redis_write_start = time.perf_counter()

    redis_client.setex(
        cache_key,
        CACHE_TTL_SECONDS,
        json.dumps(results),
    )

    redis_write_ms = (
        time.perf_counter() - redis_write_start
    ) * 1000

    total_ms = (
        time.perf_counter() - total_start
    ) * 1000

    logger.info(
        "Retrieval Redis write: %.2f ms",
        redis_write_ms,
    )
    logger.info(
        "Retrieval total: %.2f ms",
        total_ms,
    )

    return results