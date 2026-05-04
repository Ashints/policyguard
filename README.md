PolicyGuard — GDPR RAG Assistant

PolicyGuard is a Retrieval-Augmented Generation (RAG) system built on top of the official GDPR articles from https://gdpr-info.eu/
.
It allows users to ask natural language questions about GDPR and receive answers grounded strictly in the regulation text.

The system combines:

FastAPI backend
Qdrant vector database
Redis caching
MongoDB user & admin management
OpenRouter LLM integration
Next.js frontend
Dockerized infrastructure
Architecture Overview

Key Features
User Features
Register & Login (JWT based)
Ask GDPR questions in natural language
Context-aware conversation memory
Answers strictly grounded in GDPR articles
Admin Features
Promote/deactivate users
Upload new GDPR PDFs for ingestion
Maintain document index
RAG Pipeline
GDPR PDFs ingested and chunked (ingest.py)
Chunks embedded using all-mpnet-base-v2
Stored in Qdrant vector DB
User query → embedding → vector search
Relevant chunks → LLM (OpenRouter)
Answer returned with sources
Tech Stack
Layer	Technology
Backend API	FastAPI
Frontend	Next.js
Vector DB	Qdrant
Cache	Redis
Database	MongoDB
Embeddings	sentence-transformers/all-mpnet-base-v2
LLM	OpenRouter
Auth	JWT
Infra	Docker Compose
Project Structure
policyguard/
│
├── app/main.py
├── script/
│   ├── routes_auth.py
│   ├── routes_admin.py
│   ├── auth.py
│   ├── jwt_auth.py
│   ├── security.py
│   ├── retrieval.py
│   ├── answer.py
│   ├── memory.py
│   ├── cache.py
│   ├── db.py
│   ├── ingest.py
│   ├── bootstrap_admin.py
│   ├── evaluate.py
│   └── delete_data.py
│
├── frontend/ (Next.js)
├── docker-compose.yml
└── README.md
How It Works
Ingestion (Offline)
PDF → text → chunks → embeddings → Qdrant

Run once unless GDPR content updates.

Retrieval (Online)
User Question → embedding → Qdrant search → top chunks → LLM → answer
Caching
Redis caches retrieval results and answers
Reduces LLM cost and latency
Memory
Conversation context stored per user
Enables follow-up questions like “What about this article?”
Running the Project
1. Start Infrastructure
docker-compose up -d

Starts:

Qdrant on :6333
Redis on :6379
2. Run Backend
uvicorn app.main:app --reload
3. Run Frontend
cd frontend
npm install
npm run dev
4. Ingest GDPR Data

Place GDPR PDFs in:

data/raw/gdpr

Then run:

python script/ingest.py
Environment Variables (.env)
OPENROUTER_API_KEY=
SECRET_KEY=
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
MONGO_URL=
APP_API_KEY=
Why Docker?

Docker ensures Qdrant and Redis:

Persist data between restarts
Require zero local installation
Run identically in dev and production
Scalability Notes

If many users join:

Redis prevents repeated LLM calls
Qdrant handles fast vector search
FastAPI can scale with workers
LLM calls are the primary bottleneck (can be parallelized)
Evaluation & Maintenance Tools
evaluate.py — measure retrieval quality
delete_data.py — clear vectors/cache
bootstrap_admin.py — seed first admin
Goal

Provide a trustworthy, source-grounded GDPR assistant where every answer is backed by the actual regulation text from gdpr-info.eu.

License

Educational / Research use.