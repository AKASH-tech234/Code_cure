import os
import logging
from pathlib import Path
import hashlib
from typing import Any

from dotenv import load_dotenv
from pinecone import Pinecone
from sentence_transformers import SentenceTransformer
from pypdf import PdfReader
from .external_sources import ingest_external_sources

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
DOC_PATH = BASE_DIR.parent / "data" / "docs.txt"
PDF_DIR = BASE_DIR.parent / "data" / "pdfs"

logger = logging.getLogger(__name__)

# Load embedding model (same as retriever)
model = SentenceTransformer("all-MiniLM-L6-v2")


def _get_required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise ValueError(f"Missing required environment variable: {name}")
    return value


def _load_txt_documents():
    docs = []

    if DOC_PATH.exists():
        raw_text = DOC_PATH.read_text(encoding="utf-8")
        docs = [chunk.strip() for chunk in raw_text.split("\n\n") if chunk.strip()]

    logger.info("[RAG] loaded txt chunks=%s", len(docs))
    return docs


def _load_pdf_documents():
    docs = []

    if not PDF_DIR.exists():
        logger.warning("[RAG] PDF directory not found: %s", PDF_DIR)
        return docs

    for pdf_file in PDF_DIR.glob("*.pdf"):
        reader = PdfReader(str(pdf_file))

        for page_num, page in enumerate(reader.pages):
            text = page.extract_text()

            if text:
                docs.append({
                    "text": text.strip(),
                    "source": f"{pdf_file.name}-page-{page_num}"
                })

    logger.info("[RAG] loaded PDF pages=%s", len(docs))
    return docs


def _chunk_text(text, chunk_size=500, overlap=100):
    chunks = []

    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)
        start += chunk_size - overlap

    return chunks


def _stable_record_id(source: str, text: str) -> str:
    digest = hashlib.sha1(f"{source}:{text}".encode("utf-8")).hexdigest()  # nosec B324
    return f"doc-{digest}"


def _source_id_for_doc(doc: dict[str, Any]) -> str:
    metadata = doc.get("metadata") or {}
    source_id = metadata.get("source_id")
    if source_id:
        return str(source_id)

    source = str(doc.get("source") or "")
    if source.startswith("external:"):
        parts = source.split(":")
        if len(parts) >= 2:
            return parts[1]

    return "local_docs"


def _upsert_in_batches(index, records: list[dict], batch_size: int = 40) -> None:
    for start in range(0, len(records), batch_size):
        batch = records[start : start + batch_size]
        index.upsert(vectors=batch)


def ingest_documents(return_details: bool = False):
    logger.info("[RAG] ingestion started")

    pinecone_api_key = _get_required_env("PINECONE_API_KEY")
    pinecone_index = _get_required_env("PINECONE_INDEX")

    # Load raw documents
    txt_docs = _load_txt_documents()
    pdf_docs = _load_pdf_documents()

    docs = []

    # Process TXT documents
    for i, text in enumerate(txt_docs):
        chunks = _chunk_text(text)
        for chunk in chunks:
            docs.append({
                "text": chunk,
                "source": f"docs.txt#chunk-{i}",
                "metadata": {},
            })

    # Process PDF documents
    for item in pdf_docs:
        chunks = _chunk_text(item["text"])
        for chunk in chunks:
            docs.append({
                "text": chunk,
                "source": item["source"],
                "metadata": {},
            })

    # Process external connector documents
    external_chunks = ingest_external_sources()
    for item in external_chunks:
        docs.append(
            {
                "text": item.text,
                "source": item.metadata.get("source", "external:unknown"),
                "metadata": item.metadata,
            }
        )

    if not docs:
        logger.warning("[RAG] no docs found after processing")
        if return_details:
            return {
                "total_chunks": 0,
                "source_counts": {},
            }
        return 0

    logger.info("[RAG] total chunks created=%s", len(docs))

    # Generate embeddings
    logger.info("[RAG] generating embeddings...")
    vectors = [model.encode(doc["text"]).tolist() for doc in docs]

    # Connect Pinecone
    pc = Pinecone(api_key=pinecone_api_key)
    index = pc.Index(pinecone_index)

    logger.info("[RAG] upserting into Pinecone index=%s", pinecone_index)

    records = []
    source_counts: dict[str, int] = {}

    for i, (doc, vector) in enumerate(zip(docs, vectors)):
        text_to_store = doc["text"]
        
        # Ensure metadata text payload doesn't exceed Pinecone's size limit
        if len(text_to_store.encode('utf-8')) > 35000:
            # truncate to approx 35000 bytes, keeping it simple by character slicing
            text_to_store = text_to_store[:35000]

        metadata = {
            "text": text_to_store,
            "source": doc["source"],
        }
        metadata.update(doc.get("metadata") or {})

        source_id = _source_id_for_doc(doc)
        source_counts[source_id] = source_counts.get(source_id, 0) + 1

        records.append({
            "id": _stable_record_id(doc["source"], doc["text"]),
            "values": vector,
            "metadata": metadata,
        })

    _upsert_in_batches(index, records, batch_size=40)

    logger.info("[RAG] ingestion completed. total upserted=%s", len(records))

    if return_details:
        return {
            "total_chunks": len(records),
            "source_counts": source_counts,
        }

    return len(records)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    total = ingest_documents()
    print(f"Ingested {total} document chunks into Pinecone.")