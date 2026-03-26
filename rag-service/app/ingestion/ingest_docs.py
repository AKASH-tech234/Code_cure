import os
import logging
from pathlib import Path

from dotenv import load_dotenv
from pinecone import Pinecone
from sentence_transformers import SentenceTransformer
from pypdf import PdfReader

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


def ingest_documents() -> int:
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
                "source": f"docs.txt#chunk-{i}"
            })

    # Process PDF documents
    for item in pdf_docs:
        chunks = _chunk_text(item["text"])
        for chunk in chunks:
            docs.append({
                "text": chunk,
                "source": item["source"]
            })

    if not docs:
        logger.warning("[RAG] no docs found after processing")
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
    for i, (doc, vector) in enumerate(zip(docs, vectors)):
        records.append({
            "id": f"doc-{i}",
            "values": vector,
            "metadata": {
                "text": doc["text"],
                "source": doc["source"]
            }
        })

    index.upsert(vectors=records)

    logger.info("[RAG] ingestion completed. total upserted=%s", len(records))

    return len(records)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    total = ingest_documents()
    print(f"Ingested {total} document chunks into Pinecone.")