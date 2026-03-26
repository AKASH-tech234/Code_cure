from dotenv import load_dotenv
import os
from pinecone import Pinecone
from sentence_transformers import SentenceTransformer
import logging

load_dotenv()

logger = logging.getLogger(__name__)

PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_INDEX = os.getenv("PINECONE_INDEX")

if not PINECONE_API_KEY or not PINECONE_INDEX:
    raise ValueError("Pinecone env vars missing")

# Load same embedding model
model = SentenceTransformer("all-MiniLM-L6-v2")

# Initialize Pinecone
pc = Pinecone(api_key=PINECONE_API_KEY)
index = pc.Index(PINECONE_INDEX)


def retrieve_pinecone(query: str, top_k: int = 5):
    try:
        logger.info("[RAG] Pinecone retrieval query=%s", query)

        query_vector = model.encode(query).tolist()

        results = index.query(
            vector=query_vector,
            top_k=top_k,
            include_metadata=True
        )

        matches = results.get("matches", [])

        if not matches:
            logger.warning("[RAG] No matches found in Pinecone")
            return {
                "context": "",
                "sources": []
            }

        docs = []
        sources = []

        for match in matches:
            metadata = match.get("metadata", {})
            docs.append(metadata.get("text", ""))
            sources.append(metadata.get("source", ""))

        context = "\n\n".join(docs)

        return {
            "context": context,
            "sources": list(set(sources))
        }

    except Exception as e:
        logger.error("[RAG] Pinecone retrieval error: %s", str(e))
        return {
            "context": "",
            "sources": []
        }