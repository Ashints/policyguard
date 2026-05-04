import os
import hashlib
import json
import logging
from openai import OpenAI
from dotenv import load_dotenv

from script.cache import redis_client, CACHE_TTL_SECONDS, make_cache_key

# Load environment variables from .env
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
- You may synthesize information from multiple excerpts into a coherent, detailed response.
- When asked for detailed or long-form answers, combine relevant information from the documents.
- Conversation history is ONLY for resolving references (e.g. "this", "it").
- If the documents don't contain enough information to answer, respond with:
  "I cannot find this information in the provided documents."
- Do not use external knowledge or speculate beyond what's in the documents.
"""

def _make_context_aware_cache_key(question: str, memory: list[dict]) -> str:
    """
    Create cache key that includes conversation context.
    This ensures "What is it?" gets different cached answers based on context.
    """
    # Create a hash of the conversation history
    memory_hash = ""
    if memory:
        memory_str = json.dumps(memory, sort_keys=True)
        memory_hash = hashlib.md5(memory_str.encode()).hexdigest()[:8]
    
    # Combine question with memory hash
    cache_key_data = f"{question}|{memory_hash}" if memory_hash else question
    return make_cache_key("answer", cache_key_data)


def generate_answer(question: str, contexts: list[str],memory:list[dict]) -> str:
    """
    Generate an answer using ONLY retrieved GDPR document excerpts.
    Memory is provided only for conversational continuity, not grounding.
    """

    logger.info("Generating answer using LLM")
    logger.debug(f"Question: {question}")
    logger.debug(f"Number of context chunks: {len(contexts)}")


    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    if memory:
        for turn in memory[-3:]:  # Last 3 turns for context
            messages.append({
                "role": "user",
                "content": turn["question"]
            })
            messages.append({
                "role": "assistant",
                "content": turn["answer"]
            })

    document_text = "\n\n---\n\n".join(contexts)        
    messages.append({
            "role": "user",
            "content": f"""Document excerpts:
    {document_text}
    Question: {question}"""
        })

    try:
        response = client.chat.completions.create(
            model="openai/gpt-4o-mini",
            messages=messages,
            temperature=0.0,
        )
        logger.info("LLM response received successfully")
        return response.choices[0].message.content.strip()
    except Exception:
        logger.exception("LLM request failed")
        raise

def get_answer(
    question: str,retrieved_docs: list[dict],memory: list[dict]) -> tuple[str, str]:    
    """
    Get answer from cache or generate new one.
    
    Returns:
        (answer, source) where source is 'cache' or 'llm'
    """
     
    answer_cache_key = _make_context_aware_cache_key(question, memory)  
    
    cached_answer = redis_client.get(answer_cache_key)
    if cached_answer:
        logger.info("Answer cache hit")
        return cached_answer, "cache"
    
    contexts = [doc["text"] for doc in retrieved_docs]


    answer = generate_answer(
        question=question,
        contexts=contexts,
        memory=memory
    )
    redis_client.setex(
        answer_cache_key,
        CACHE_TTL_SECONDS,
        answer
    )
    logger.info("Answer cached")

    return answer, "llm"
