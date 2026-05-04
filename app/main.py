import os
from fastapi import FastAPI, Depends, HTTPException, Header
from pydantic import BaseModel  
from dotenv import load_dotenv
from script.bootstrap_admin import bootstrap_admin

from script.routes_admin import router as admin_router
from script.routes_auth import router as auth_router
from script.logger import setup_logging,get_logger
from script.retrieval import retrieve
from script.answer import generate_answer,get_answer
from script.auth import verify_api_key, rate_limit
from script.memory import get_memory, add_to_memory
from script.jwt_auth import get_current_user
app = FastAPI()
app.include_router(auth_router)
app.include_router(admin_router)
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
bootstrap_admin()
load_dotenv()
setup_logging()

logger = get_logger("api")
APP_API_KEY = os.getenv("APP_API_KEY")

def expand_query_with_context(question: str, memory: list[dict]) -> str:
    """
    Expand queries containing pronouns by replacing them with actual entities.
    """
    if not memory:
        return question
    
    question_lower = question.lower()
    words = question_lower.split()
    
    # Pronouns to replace
    pronouns = {"it", "this", "that", "they", "those", "these", "them", "its", "their"}
    
    contains_pronoun = any(word in pronouns for word in words)
    
    if contains_pronoun:
        # Extract main entity from previous question
        prev_q = memory[-1]['question']
        
        # Simple entity extraction: look for capitalized words or "Article X"
        import re
        
        # Try to find "Article X" pattern
        article_match = re.search(r'Article\s*\d+', prev_q, re.IGNORECASE)
        if article_match:
            entity = article_match.group(0)
        else:
            # Fall back to simple replacement
            entity = prev_q
        
        # Replace pronouns with entity
        expanded = question
        for pronoun in ["it", "this", "that", "its"]:
            expanded = re.sub(
                r'\b' + pronoun + r'\b', 
                entity, 
                expanded, 
                flags=re.IGNORECASE
            )
        
        logger.debug(f"Query expansion: '{question}' → '{expanded}'")
        return expanded
    
    # Check for vague follow-ups
    follow_up_patterns = ["what about", "tell me more", "explain", "how about"]
    if any(question_lower.startswith(pattern) for pattern in follow_up_patterns):
        prev_q = memory[-1]['question']
        return f"{prev_q} {question}"
    
    return question
class QuestionRequest(BaseModel):
    question: str


MIN_SCORE = 0.25 
@app.post("/retrieve")
async def retrieve_and_answer(
    req: QuestionRequest,
    payload: dict = Depends(get_current_user),
    __: None = Depends(rate_limit),
):    
    
    logger.info(f"========== NEW QUERY ==========")
    logger.info(f"Original question: {req.question}")

    user_id=payload["sub"]
    memory = get_memory(user_id)
    logger.info(f"Memory has {len(memory)} turns")
 
    if memory:
        logger.info(f"Last question was: {memory[-1]['question']}")

    query = expand_query_with_context(req.question, memory)
    logger.info(f"🔍 Expanded query: '{query}'") 
    logger.info(f"🔍 Original question: '{req.question}'") 
    
    retrieved = retrieve(query)
    logger.info(f"📚 Retrieved {len(retrieved)} total documents")

    filtered = [r for r in retrieved if r["score"] >= MIN_SCORE]
    logger.info(f"✅ Filtered to {len(filtered)} documents (score >= {MIN_SCORE})")
        

    if filtered:
        logger.info("Retrieved document previews:")
        for i, doc in enumerate(filtered[:3], 1):
            preview = doc['text'][:150].replace('\n', ' ')
            logger.info(f"  {i}. {doc['article']} (score: {doc['score']:.3f})")
            logger.info(f"     Preview: {preview}...")

    try:
        if not filtered:
            logger.warning("⚠️ No documents found!")
            answer = "I cannot find this information in the provided documents."
            add_to_memory(user_id, req.question, answer)
            return {
                "question": req.question,
                "answer": answer,
                "sources": []
            }

        answer, source = get_answer(
        question=req.question,
        retrieved_docs=filtered,
        memory=memory
        )

        logger.info(f"💬 Answer source: {source}")
        logger.info(f"📝 Answer preview: {answer[:200]}...")

        add_to_memory(user_id, req.question, answer)
        logger.info(f"Stored answer in memory (source: {source})")
        logger.debug(f"Memory state: {get_memory(user_id)}")

        seen = set()
        sources = []
        for item in filtered:
            key = (item["article"], item["file"])
            if key not in seen:
                seen.add(key)
                sources.append({
                    "article": item["article"],
                    "file": item["file"]
                })


        return {
            "question": req.question,
            "answer": answer,
            "sources": sources
        }
    except Exception:
        logger.exception("Request failed")
        raise