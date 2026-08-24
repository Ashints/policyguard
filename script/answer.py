import os
import time
import hashlib
import json
import logging

from openai import OpenAI
from dotenv import load_dotenv

from script.cache import (
    redis_client,
    CACHE_TTL_SECONDS,
    make_cache_key,
)


load_dotenv()

logger = logging.getLogger(__name__)

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

if not OPENROUTER_API_KEY:
    raise RuntimeError("OPENROUTER_API_KEY is not set")


client = OpenAI(
    api_key=OPENROUTER_API_KEY,
    base_url="https://openrouter.ai/api/v1",
    default_headers={
        "HTTP-Referer": "http://localhost:3000",
        "X-Title": "PolicyGuard",
    },
)


SYSTEM_PROMPT = """
You are a GDPR document assistant.

Rules:
- Answer using the provided document excerpts.
- You may synthesize information from multiple excerpts into a coherent,
  detailed response.
- When asked for detailed or long-form answers, combine relevant information
  from the documents.
- Conversation history is ONLY for resolving references such as "this" or "it".
- If the documents do not contain enough information to answer, respond with:
  "I cannot find this information in the provided documents."
- Do not use external knowledge or speculate beyond what is in the documents.
"""


def _make_context_aware_cache_key(
    question: str,
    memory: list[dict],
) -> str:
    """
    Include only the previous conversation context in the key.
    The current answer is not yet stored in memory.
    """

    memory_hash = ""

    if memory:
        memory_string = json.dumps(
            memory[-3:],
            sort_keys=True,
        )

        memory_hash = hashlib.md5(
            memory_string.encode("utf-8")
        ).hexdigest()[:8]

    question_normalized = " ".join(
        question.strip().lower().split()
    )

    cache_key_data = (
        f"{question_normalized}|{memory_hash}"
        if memory_hash
        else question_normalized
    )

    return make_cache_key(
        "answer",
        cache_key_data,
    )

def get_answer(
    question: str,
    retrieved_docs: list[dict],
    memory: list[dict],
) -> tuple[str, str]:
    """
    Get an answer from Redis or generate it with the LLM.

    Returns:
        (answer, source)
    """

    total_start = time.perf_counter()

    answer_cache_key = _make_context_aware_cache_key(
        question,
        memory,
    )

    redis_start = time.perf_counter()

    cached_answer = redis_client.get(
        answer_cache_key
    )

    redis_read_ms = (
        time.perf_counter() - redis_start
    ) * 1000

    if cached_answer:
        total_ms = (
            time.perf_counter() - total_start
        ) * 1000

        logger.info("Answer cache hit")
        logger.info(
            "Answer Redis read: %.2f ms",
            redis_read_ms,
        )
        logger.info(
            "Cached answer total: %.2f ms",
            total_ms,
        )

        return cached_answer, "cache"

    logger.info(
        "Answer cache miss; Redis read: %.2f ms",
        redis_read_ms,
    )

    contexts = [
        doc["text"]
        for doc in retrieved_docs
    ]

    llm_start = time.perf_counter()

    answer = generate_answer(
        question=question,
        contexts=contexts,
        memory=memory,
    )

    llm_ms = (
        time.perf_counter() - llm_start
    ) * 1000

    logger.info(
        "LLM generation: %.2f ms",
        llm_ms,
    )

    redis_write_start = time.perf_counter()

    redis_client.setex(
        answer_cache_key,
        CACHE_TTL_SECONDS,
        answer,
    )

    redis_write_ms = (
        time.perf_counter() - redis_write_start
    ) * 1000

    total_ms = (
        time.perf_counter() - total_start
    ) * 1000

    logger.info(
        "Answer Redis write: %.2f ms",
        redis_write_ms,
    )
    logger.info(
        "Answer generation total: %.2f ms",
        total_ms,
    )

    return answer, "llm"