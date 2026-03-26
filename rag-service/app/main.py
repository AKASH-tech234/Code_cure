from fastapi import FastAPI
from dotenv import load_dotenv
import logging

load_dotenv()

from app.routers import retrieve
from app.retrieval import retriever  # import your module

app = FastAPI()

logger = logging.getLogger(__name__)


@app.on_event("startup")
def startup_event():
    logger.info("[RAG] initializing resources at startup...")
    retriever.load_resources()
    logger.info("[RAG] ready!")


app.include_router(retrieve.router, prefix="/retrieve")