PolicyGuard — GDPR RAG Assistant

PolicyGuard is a Retrieval-Augmented Generation (RAG) system built on GDPR articles from GDPR-info.eu.
It allows users to ask questions about GDPR in natural language and receive answers grounded strictly in the regulation text.

🚀 Features
GDPR question answering with source citations
Article-level retrieval using vector search
User authentication (register/login)
Admin panel to manage users and upload new GDPR PDFs
Conversation memory for follow-up questions
Redis caching for fast responses

🛠️ Tech Stack

Backend

FastAPI
MongoDB
Qdrant (vector database)
Redis (cache)
Sentence-Transformers (embeddings)
pdfplumber + tiktoken
JWT authentication

Frontend

Next.js

LLM

OpenRouter API

Infrastructure

Docker (Qdrant + Redis with persistent storage)
⚙️ How It Works
GDPR PDFs are parsed, chunked, embedded, and stored in Qdrant.
User query is embedded and matched against GDPR chunks.
Retrieved text is sent to the LLM to generate a grounded answer.
Sources are returned with the answer.
🐳 Run Locally

Start services:

docker compose up -d

Ingest GDPR articles:

python script/ingest.py

Run API:

uvicorn app.main:app --reload
🎯 Goal

To build a reliable GDPR assistant that answers only from official regulation text and avoids hallucinations.

Author: Ashints