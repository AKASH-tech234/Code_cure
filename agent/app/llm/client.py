from dotenv import load_dotenv
import os
from groq import Groq
import logging

load_dotenv()
logger = logging.getLogger(__name__)

API_KEY = os.getenv("GROQ_API_KEY")

if not API_KEY:
    raise ValueError("GROQ_API_KEY not set")

client = Groq(api_key=API_KEY)


def generate_answer(prompt: str) -> str:
    try:
        logger.info("[LLM] calling Groq")

        response = client.chat.completions.create(
            model="openai/gpt-oss-120b",  # ✅ FIXED MODEL
            messages=[
                {"role": "system", "content": "You are an expert epidemiology assistant."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2
        )

        return response.choices[0].message.content

    except Exception as e:
        logger.error("[LLM] error: %s", str(e))
        return f"[LLM ERROR] {str(e)}"