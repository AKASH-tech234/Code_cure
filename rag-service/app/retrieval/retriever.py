from dotenv import load_dotenv
import numpy as np
from sentence_transformers import SentenceTransformer
from pathlib import Path
import logging

load_dotenv()
logger = logging.getLogger(__name__)

# Lazy model load
model = None
doc_embeddings = None
documents = None


def load_resources():
    global model, doc_embeddings, documents

    if model is None:
        logger.info("[RAG] loading embedding model...")
        model = SentenceTransformer("all-MiniLM-L6-v2")

    if documents is None:
        BASE_DIR = Path(__file__).resolve().parent
        DOC_PATH = BASE_DIR.parent / "data" / "docs.txt"

        if not DOC_PATH.exists():
            raise FileNotFoundError(f"Docs file not found: {DOC_PATH}")

        documents = DOC_PATH.read_text(encoding="utf-8").split("\n\n")
        documents = [d.strip() for d in documents if d.strip()]

        logger.info("[RAG] documents loaded: %s", len(documents))

    if doc_embeddings is None:
        logger.info("[RAG] computing embeddings...")
        doc_embeddings = [model.encode(doc) for doc in documents]


def cosine_similarity(a, b):
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))


def retrieve(query, top_k=2):
    try:
        logger.info("[RAG] retrieval started top_k=%s query_len=%s", top_k, len(query or ""))
        load_resources()

        if model is None or documents is None or doc_embeddings is None:
            raise RuntimeError("RAG resources are not initialized")

        query_vec = model.encode(query)

        scores = [
            (doc, cosine_similarity(query_vec, doc_vec))
            for doc, doc_vec in zip(documents, doc_embeddings)
        ]

        scores.sort(key=lambda x: x[1], reverse=True)

        top_docs = [doc for doc, _ in scores[:top_k]]

        logger.info("[RAG] retrieval completed returned_docs=%s", len(top_docs))

        return {
            "context": "\n\n".join(top_docs),
            "sources": ["local-embedding"]
        }

    except Exception as e:
        logger.error("[RAG] retrieval error: %s", str(e))
        raise