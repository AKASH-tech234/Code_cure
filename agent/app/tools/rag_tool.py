from dotenv import load_dotenv
import os
import requests
import logging

load_dotenv()

logger = logging.getLogger(__name__)

RAG_URL = os.getenv("RAG_URL")

if not RAG_URL:
    raise ValueError("RAG_URL not set in environment")


def rag_tool(query: str, top_k: int = 5) -> dict:
    try:
        logger.info("[AGENT] calling RAG tool query=%s", query)

        response = requests.post(
            f"{RAG_URL}/retrieve",
            json={"query": query, "top_k": top_k},
            timeout=5
        )

        response.raise_for_status()

        data = response.json()

        return {
            "context": data.get("context", ""),
            "sources": data.get("sources", [])
        }

    except Exception as e:
        logger.error("[AGENT] RAG tool error: %s", str(e))

        return {
            "context": "",
            "sources": [],
            "error": str(e)
        }