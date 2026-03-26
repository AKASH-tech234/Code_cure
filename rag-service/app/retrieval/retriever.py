from dotenv import load_dotenv
import os
import numpy as np
from sentence_transformers import SentenceTransformer
from pathlib import Path
import logging
from pinecone import Pinecone

load_dotenv()
logger = logging.getLogger(__name__)

# ----------------------------
# ENV
# ----------------------------
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_INDEX = os.getenv("PINECONE_INDEX")

# ----------------------------
# LAZY GLOBALS
# ----------------------------
model = None
doc_embeddings = None
documents = None
pinecone_index = None


# ----------------------------
# LOAD RESOURCES
# ----------------------------
def load_resources():
    global model, doc_embeddings, documents, pinecone_index

    # Load embedding model
    if model is None:
        logger.info("[RAG] loading embedding model...")
        model = SentenceTransformer("all-MiniLM-L6-v2")

    # Load local documents
    if documents is None:
        BASE_DIR = Path(__file__).resolve().parent
        DOC_PATH = BASE_DIR.parent / "data" / "docs.txt"

        if DOC_PATH.exists():
            raw = DOC_PATH.read_text(encoding="utf-8")
            documents = [d.strip() for d in raw.split("\n\n") if d.strip()]
        else:
            documents = []

        logger.info("[RAG] local documents loaded=%s", len(documents))

    # Compute local embeddings
    if doc_embeddings is None and documents:
        logger.info("[RAG] computing local embeddings...")
        doc_embeddings = [model.encode(doc) for doc in documents]

    # Init Pinecone (optional)
    if pinecone_index is None and PINECONE_API_KEY and PINECONE_INDEX:
        try:
            pc = Pinecone(api_key=PINECONE_API_KEY)
            pinecone_index = pc.Index(PINECONE_INDEX)
            logger.info("[RAG] Pinecone initialized")
        except Exception as e:
            logger.warning("[RAG] Pinecone init failed: %s", str(e))
            pinecone_index = None


# ----------------------------
# LOCAL RETRIEVER
# ----------------------------
def cosine_similarity(a, b):
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))


def retrieve_local(query, top_k):
    if not documents or not doc_embeddings:
        return {"context": "", "sources": []}

    query_vec = model.encode(query)

    scores = [
        (doc, cosine_similarity(query_vec, doc_vec))
        for doc, doc_vec in zip(documents, doc_embeddings)
    ]

    scores.sort(key=lambda x: x[1], reverse=True)

    top_docs = [doc for doc, _ in scores[:top_k]]

    return {
        "context": "\n\n".join(top_docs),
        "sources": ["local"]
    }


# ----------------------------
# PINECONE RETRIEVER
# ----------------------------
def retrieve_pinecone(query, top_k):
    if pinecone_index is None:
        return {"context": "", "sources": []}

    try:
        query_vector = model.encode(query).tolist()

        results = pinecone_index.query(
            vector=query_vector,
            top_k=top_k,
            include_metadata=True
        )

        matches = results.get("matches", [])

        if not matches:
            return {"context": "", "sources": []}

        docs = []
        sources = []

        for match in matches:
            metadata = match.get("metadata", {})
            docs.append(metadata.get("text", ""))
            sources.append(metadata.get("source", ""))

        return {
            "context": "\n\n".join(docs),
            "sources": list(set(sources))
        }

    except Exception as e:
        logger.error("[RAG] Pinecone error: %s", str(e))
        return {"context": "", "sources": []}


# ----------------------------
# MAIN RETRIEVE FUNCTION
# ----------------------------
def retrieve(query, top_k=5):
    try:
        logger.info("[RAG] unified retrieval started")

        load_resources()

        # 1️⃣ Try Pinecone first
        pinecone_result = retrieve_pinecone(query, top_k)

        if pinecone_result["context"]:
            logger.info("[RAG] using Pinecone results")
            return pinecone_result

        # 2️⃣ Fallback to local
        logger.warning("[RAG] Pinecone empty → fallback to local")

        local_result = retrieve_local(query, top_k)

        return local_result

    except Exception as e:
        logger.error("[RAG] retrieval failed: %s", str(e))
        return {
            "context": "",
            "sources": []
        }