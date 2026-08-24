import os
import re
import time

from fastapi import FastAPI, Depends, Request
from pydantic import BaseModel
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware

from script.bootstrap_admin import bootstrap_admin
from script.routes_admin import router as admin_router
from script.routes_auth import router as auth_router
from script.logger import setup_logging, get_logger
from script.retrieval import retrieve
from script.answer import get_answer
from script.auth import rate_limit
from script.memory import get_memory, add_to_memory
from script.jwt_auth import get_current_user


load_dotenv()
setup_logging()

app = FastAPI()

app.include_router(auth_router)
app.include_router(admin_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logger = get_logger("api")

# Call this only after load_dotenv()
bootstrap_admin()


MIN_SCORE = 0.25


@app.middleware("http")
async def measure_request_latency(
    request: Request,
    call_next,
):
    start_time = time.perf_counter()

    response = await call_next(request)

    latency_ms = (
        time.perf_counter() - start_time
    ) * 1000

    response.headers["X-Process-Time-ms"] = (
        f"{latency_ms:.2f}"
    )

    logger.info(
        "%s %s completed in %.2f ms",
        request.method,
        request.url.path,
        latency_ms,
    )

    return response


def expand_query_with_context(
    question: str,
    memory: list[dict],
) -> str:
    """
    Expand queries containing pronouns by replacing
    them with entities from the previous question.
    """

    if not memory:
        return question

    question_lower = question.lower()
    words = question_lower.split()

    pronouns = {
        "it",
        "this",
        "that",
        "they",
        "those",
        "these",
        "them",
        "its",
        "their",
    }

    contains_pronoun = any(
        word in pronouns
        for word in words
    )

    if contains_pronoun:
        previous_question = memory[-1]["question"]

        article_match = re.search(
            r"Article\s*\d+",
            previous_question,
            re.IGNORECASE,
        )

        if article_match:
            entity = article_match.group(0)
        else:
            entity = previous_question

        expanded = question

        for pronoun in [
            "it",
            "this",
            "that",
            "its",
        ]:
            expanded = re.sub(
                r"\b" + pronoun + r"\b",
                entity,
                expanded,
                flags=re.IGNORECASE,
            )

        logger.debug(
            "Query expansion: '%s' -> '%s'",
            question,
            expanded,
        )

        return expanded

    follow_up_patterns = [
        "what about",
        "tell me more",
        "explain",
        "how about",
    ]

    if any(
        question_lower.startswith(pattern)
        for pattern in follow_up_patterns
    ):
        previous_question = memory[-1]["question"]

        return (
            f"{previous_question} {question}"
        )

    return question


def is_exact_article_lookup(
    question: str,
) -> bool:
    """
    Detect questions such as:
    - What is Article 64?
    - what is article 65
    """

    return bool(
        re.fullmatch(
            r"\s*what\s+is\s+article\s+\d+\s*\??\s*",
            question,
            re.IGNORECASE,
        )
    )


def build_sources(
    documents: list[dict],
) -> list[dict]:
    """
    Remove duplicate article/file source entries.
    """

    seen = set()
    sources = []

    for item in documents:
        key = (
            item.get("article"),
            item.get("file"),
        )

        if key in seen:
            continue

        seen.add(key)

        sources.append(
            {
                "article": item.get("article"),
                "file": item.get("file"),
            }
        )

    return sources


class QuestionRequest(BaseModel):
    question: str


@app.post("/retrieve")
async def retrieve_and_answer(
    req: QuestionRequest,
    payload: dict = Depends(get_current_user),
    __: None = Depends(rate_limit),
):
    request_start_time = time.perf_counter()

    logger.info("========== NEW QUERY ==========")
    logger.info(
        "Original question: %s",
        req.question,
    )

    user_id = payload["sub"]

    memory = get_memory(user_id)

    logger.info(
        "Memory has %d turns",
        len(memory),
    )

    if memory:
        logger.info(
            "Last question was: %s",
            memory[-1]["question"],
        )

    query = expand_query_with_context(
        req.question,
        memory,
    )

    logger.info(
        "Expanded query: '%s'",
        query,
    )

    retrieved = retrieve(query)

    logger.info(
        "Retrieved %d total documents",
        len(retrieved),
    )

    filtered = [
        result
        for result in retrieved
        if result.get("score", 0) >= MIN_SCORE
    ]

    logger.info(
        "Filtered to %d documents "
        "(score >= %.2f)",
        len(filtered),
        MIN_SCORE,
    )

    if not filtered:
        answer = (
            "I cannot find this information "
            "in the provided documents."
        )

        add_to_memory(
            user_id,
            req.question,
            answer,
        )

        total_latency_ms = (
            time.perf_counter()
            - request_start_time
        ) * 1000

        logger.info(
            "No-document response: %.2f ms",
            total_latency_ms,
        )

        return {
            "question": req.question,
            "answer": answer,
            "sources": [],
            "latency_ms": round(
                total_latency_ms,
                2,
            ),
        }

    if is_exact_article_lookup(req.question):
        direct_answer = "\n\n".join(
            document["text"]
            for document in filtered
        )

        sources = build_sources(filtered)

        add_to_memory(
            user_id,
            req.question,
            direct_answer,
        )

        total_latency_ms = (
            time.perf_counter()
            - request_start_time
        ) * 1000

        logger.info(
            "Direct article response: %.2f ms",
            total_latency_ms,
        )

        return {
            "question": req.question,
            "answer": direct_answer,
            "sources": sources,
            "latency_ms": round(
                total_latency_ms,
                2,
            ),
        }

    try:
        answer, source = get_answer(
            question=req.question,
            retrieved_docs=filtered,
            memory=memory,
        )

        logger.info(
            "Answer source: %s",
            source,
        )

        logger.info(
            "Answer preview: %s...",
            answer[:200],
        )

        add_to_memory(
            user_id,
            req.question,
            answer,
        )

        sources = build_sources(filtered)

        total_latency_ms = (
            time.perf_counter()
            - request_start_time
        ) * 1000

        logger.info(
            "Total /retrieve latency: %.2f ms",
            total_latency_ms,
        )

        return {
            "question": req.question,
            "answer": answer,
            "sources": sources,
            "latency_ms": round(
                total_latency_ms,
                2,
            ),
        }

    except Exception:
        logger.exception("Request failed")
        raise


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
    )