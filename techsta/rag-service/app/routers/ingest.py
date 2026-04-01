from fastapi import APIRouter
import logging

from app.schemas import IngestResponse, IngestSourceStatus
from app.ingestion.ingest_docs import ingest_documents
from app.ingestion.source_registry import SOURCES

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("", response_model=IngestResponse)
def ingest_endpoint():
    logger.info("[RAG] /ingest called")
    try:
        details = ingest_documents(return_details=True)
        source_counts = details.get("source_counts", {})

        source_status: list[IngestSourceStatus] = []
        for source in SOURCES:
            chunks = int(source_counts.get(source.source_id, 0))
            status = "ok" if chunks > 0 else "empty"
            source_status.append(
                IngestSourceStatus(
                    source_id=source.source_id,
                    connector_type=source.connector_type,
                    status=status,
                    chunks=chunks,
                    message=source.usage_notes,
                )
            )

        return IngestResponse(
            run_status="ok",
            message="Ingestion completed",
            total_chunks=int(details.get("total_chunks", 0)),
            source_status=source_status,
        )
    except Exception as exc:
        logger.exception("[RAG] /ingest failed")

        source_status = [
            IngestSourceStatus(
                source_id=source.source_id,
                connector_type=source.connector_type,
                status="failed",
                chunks=0,
                message=f"{source.usage_notes} | error={str(exc)}",
            )
            for source in SOURCES
        ]

        return IngestResponse(
            run_status="failed",
            message=str(exc),
            total_chunks=0,
            source_status=source_status,
        )
