from dotenv import load_dotenv
import os
import requests
import logging

load_dotenv()

logger = logging.getLogger(__name__)

RAG_URL = os.getenv("RAG_URL", "http://localhost:8003")


def rag_tool(query: str, top_k: int = 5) -> dict:
    try:
        logger.info("[AGENT_TOOL][RAG][REQ] query_len=%s top_k=%s", len(query or ""), top_k)
        logger.debug("[AGENT_TOOL][RAG][REQ_PAYLOAD] payload=%s", {"query": query, "top_k": top_k})

        response = requests.post(
            f"{RAG_URL}/retrieve",
            json={"query": query, "top_k": top_k},
            timeout=5
        )

        response.raise_for_status()

        data = response.json()

        logger.info(
            "[AGENT_TOOL][RAG][RESP] status=%s source_count=%s has_context=%s",
            response.status_code,
            len(data.get("sources") or []),
            bool((data.get("context") or "").strip()),
        )
        logger.debug("[AGENT_TOOL][RAG][RESP_PAYLOAD] payload=%s", data)

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