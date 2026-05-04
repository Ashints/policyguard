from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer
import logging
import json
import hashlib
import re
from script.cache import redis_client, CACHE_TTL_SECONDS, make_cache_key


logger = logging.getLogger(__name__)
COLLECTION_NAME = "policy_docs"
TOP_K = 3
MIN_SCORE=0.25
CACHE_TTL_SECONDS = 60 * 60 * 24 

logger.info("Connecting to Qdrant...")
qdrant = QdrantClient(host="localhost", port=6333)

logger.info("Loading embedding model...")
model = SentenceTransformer("sentence-transformers/all-mpnet-base-v2")

def retrieve(query: str):
    # 1. Embed the query
    logger.info("Received retrieval query")
    logger.debug(f"Query text: {query}")

    cache_key = make_cache_key("retrieval",query)
    cached = redis_client.get(cache_key)

    if cached:
        logger.info("Retrieval cache hit")
        return json.loads(cached)
    
    points = []
    
    try:
        article_match = re.search(r'article\s*(\d+)', query, re.IGNORECASE)
        if article_match:
            article_id = f"article{article_match.group(1)}"
            logger.info("Detected article lookup: %s", article_id)

            points, _ = qdrant.scroll(
            collection_name=COLLECTION_NAME,
            scroll_filter={
                "must": [{
                    "key": "article",
                    "match": {"value": article_id}
                }]
            },
            limit=50
        )
            
        if points:
            results = [{
                "text": p.payload["text"],
                "article": p.payload["article"],
                "file": p.payload["file"],
                "score": 1.0
            } for p in points]        


            redis_client.setex(
                cache_key,
                CACHE_TTL_SECONDS,
                json.dumps(results)
            )
            return results 

        query_vector = model.encode(
            query,
            normalize_embeddings=True
        ).tolist()
        logger.debug("Query embedding created successfully")
    except Exception as e:
        logger.exception("Failed to embed query")
        raise

    try:
        results = qdrant.query_points(
            collection_name=COLLECTION_NAME,
            query=query_vector,
            limit=TOP_K,
            with_payload=True
        )
        logger.info(f"Qdrant returned {len(results.points)} results")
    except Exception as e:
        logger.exception("Qdrant search failed")
        raise

    # 3. Format results
    formatted = []
    for hit in results.points:
        if hit.score < MIN_SCORE:
            continue
        payload = hit.payload
        score = hit.score

        formatted.append({
            "text": payload["text"],
            "article": payload.get("article"),
            "file": payload.get("file"),
            "score": score
        })

    try:
        redis_client.setex(
            cache_key,
            CACHE_TTL_SECONDS,
            json.dumps(formatted)
        )
        logger.info("Retrieval cached")
    except Exception:
        logger.warning("Failed to write retrieval to cache")


    logger.debug("Results formatted successfully")
    return formatted

    
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    query = "Is consent required for processing personal data?"
    results = retrieve(query)

    for i, r in enumerate(results, 1):
        print(f"\n--- Result {i} ---")
        print(f"Article: {r['article']}")
        print(r["text"])
      
        