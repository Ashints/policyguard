from pathlib import Path
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance
import tiktoken
import pdfplumber
import logging
import uuid
import re

from sentence_transformers import SentenceTransformer

# ---------- CONFIG ----------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATA_DIR = Path(r"C:\Users\pc\Desktop\Projects\policyguard\data\raw\gdpr")
COLLECTION_NAME = "policy_docs"

# ---------- CLIENTS ----------
qdrant = QdrantClient(host="localhost", port=6333)
model = SentenceTransformer("sentence-transformers/all-mpnet-base-v2")
tokenizer = tiktoken.get_encoding("cl100k_base")

# ---------- HELPERS ----------
def extract_text_from_pdf(file_path: Path) -> str:
    if file_path.suffix.lower() == ".txt":
        return file_path.read_text(encoding="utf-8")

    if file_path.suffix.lower() == ".pdf":
        text = ""
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        return text

    return ""

def chunk_text(text, chunk_size=500, overlap=100):
    tokens = tokenizer.encode(text)
    chunks = []
    start = 0

    while start < len(tokens):
        end = start + chunk_size
        chunks.append(tokenizer.decode(tokens[start:end]))
        start += chunk_size - overlap

    return chunks

def normalize_article_id(stem: str) -> str:
    """
    Ensures Article IDs are always: article<number>
    """
    match = re.search(r"article\s*(\d+)", stem, re.IGNORECASE)
    if match:
        return f"article{match.group(1)}"
    return stem.lower().replace(" ", "")

# ---------- CREATE COLLECTION ----------
collections = qdrant.get_collections().collections
if not any(c.name == COLLECTION_NAME for c in collections):
    logger.info("Creating Qdrant collection: %s", COLLECTION_NAME)
    qdrant.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(
            size=768,
            distance=Distance.COSINE
        )
    )

# ---------- INGEST ----------
def ingest():
    logger.info("Ingesting from directory: %s", DATA_DIR.resolve())

    if not DATA_DIR.exists():
        logger.error("DATA_DIR does not exist!")
        return

    files = list(DATA_DIR.iterdir())
    logger.info("Found %d files", len(files))

    for file_path in files:
        logger.info("Found file: %s", file_path.name)

        if file_path.suffix.lower() not in {".txt", ".pdf"}:
            logger.info("Skipping unsupported file")
            continue

        article_id = normalize_article_id(file_path.stem)

        existing, _ = qdrant.scroll(
            collection_name=COLLECTION_NAME,
            scroll_filter={
                "must": [{
                    "key": "article",
                    "match": {"value": article_id}
                }]
            },
            limit=1
        )

        if existing:
            logger.info("Skipping already ingested article: %s", article_id)
            continue

        text = extract_text_from_pdf(file_path)
        if not text.strip():
            logger.warning("No text extracted from %s", file_path.name)
            continue

        chunks = chunk_text(text)
        logger.info("Created %d chunks", len(chunks))

        vectors = model.encode(chunks, normalize_embeddings=True)

        points = []
        for chunk, vector in zip(chunks, vectors):
            points.append({
                "id": str(uuid.uuid4()),
                "vector": vector.tolist(),
                "payload": {
                    "source": "GDPR",
                    "article": article_id,
                    "file": file_path.name,
                    "text": chunk
                }
            })

        qdrant.upsert(
            collection_name=COLLECTION_NAME,
            points=points,
            wait=True
        )

        logger.info("Ingested article: %s", article_id)

if __name__ == "__main__":
    ingest()
