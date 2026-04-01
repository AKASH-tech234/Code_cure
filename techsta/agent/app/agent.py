import logging
from app.tools.rag_tool import rag_tool
from app.llm.client import generate_answer

logger = logging.getLogger(__name__)


def build_prompt(query: str, context: str) -> str:
    return f"""
You are an AI epidemiology expert.

User question:
{query}

Relevant knowledge:
{context}

Task:
- Answer clearly and concisely
- Explain cause-effect relationships
- If multiple strategies exist, summarize them

Answer:
"""


def run_agent(query: str) -> dict:
    try:
        logger.info("[AGENT] running agent for query=%s", query)

        # Step 1: retrieve context
        rag_result = rag_tool(query)
        context = rag_result.get("context", "")

        # Step 2: build prompt
        prompt = build_prompt(query, context)

        # Step 3: generate answer
        answer = generate_answer(prompt)

        return {
            "query": query,
            "answer": answer,
            "sources": rag_result.get("sources", [])
        }

    except Exception as e:
        logger.error("[AGENT] error: %s", str(e))
        return {
            "query": query,
            "answer": "",
            "error": str(e)
        }