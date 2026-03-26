from fastapi import APIRouter
import logging
from app.schemas import RetrieveRequest, RetrieveResponse
from app.retrieval.retriever import retrieve

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("", response_model=RetrieveResponse)
def retrieve_endpoint(body: RetrieveRequest):
    logger.info("[RAG] /retrieve called top_k=%s", body.top_k)
    result = retrieve(body.query, body.top_k)
    logger.info("[RAG] /retrieve success sources=%s", len(result.get("sources", [])))
    return result

