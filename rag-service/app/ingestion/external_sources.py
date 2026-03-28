from __future__ import annotations

import csv
import hashlib
import io
import json
import logging
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from urllib.request import Request, urlopen

from .source_registry import SOURCES, SourceConfig


logger = logging.getLogger(__name__)


@dataclass
class ExternalChunk:
    text: str
    metadata: dict[str, Any]


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _fetch_bytes(url: str, timeout_sec: int = 20) -> bytes:
    request = Request(url, headers={"User-Agent": "techsta-rag-ingestor/1.0"})
    with urlopen(request, timeout=timeout_sec) as response:  # nosec B310
        return response.read()


def _csv_rows_preview(csv_bytes: bytes, max_rows: int = 50) -> list[dict[str, str]]:
    decoded = csv_bytes.decode("utf-8", errors="replace")
    reader = csv.DictReader(io.StringIO(decoded))
    rows: list[dict[str, str]] = []

    for index, row in enumerate(reader):
        if index >= max_rows:
            break
        rows.append({k: (v or "") for k, v in row.items()})

    return rows


def _rows_to_chunks(rows: list[dict[str, str]], chunk_size: int = 20) -> list[str]:
    chunks: list[str] = []

    for start in range(0, len(rows), chunk_size):
        segment = rows[start : start + chunk_size]
        chunks.append(json.dumps(segment, ensure_ascii=True))

    return chunks


def _ingest_http_csv(source: SourceConfig) -> list[ExternalChunk]:
    payload = _fetch_bytes(source.url)
    checksum = _sha256_bytes(payload)
    rows = _csv_rows_preview(payload, max_rows=120)
    chunks = _rows_to_chunks(rows, chunk_size=20)

    ingested_at = _utc_now_iso()
    external_chunks: list[ExternalChunk] = []

    for index, chunk in enumerate(chunks):
        external_chunks.append(
            ExternalChunk(
                text=(
                    f"Source: {source.display_name}\n"
                    f"Chunk: {index + 1}/{len(chunks)}\n"
                    f"Data sample (JSON rows):\n{chunk}"
                ),
                metadata={
                    "source": f"external:{source.source_id}:chunk-{index}",
                    "source_id": source.source_id,
                    "source_name": source.display_name,
                    "connector_type": source.connector_type,
                    "source_url": source.url,
                    "trust_tier": source.trust_tier,
                    "cadence": source.cadence,
                    "checksum": checksum,
                    "source_version": checksum[:12],
                    "ingested_at": ingested_at,
                    "stale_after_minutes": source.stale_after_minutes,
                },
            )
        )

    return external_chunks


def _ingest_http_zip(source: SourceConfig) -> list[ExternalChunk]:
    payload = _fetch_bytes(source.url)
    checksum = _sha256_bytes(payload)
    ingested_at = _utc_now_iso()

    chunks: list[ExternalChunk] = []

    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        names = archive.namelist()
        summary_text = (
            f"Source: {source.display_name}\n"
            f"Archive entries: {len(names)}\n"
            f"Files: {', '.join(names[:30])}"
        )
        chunks.append(
            ExternalChunk(
                text=summary_text,
                metadata={
                    "source": f"external:{source.source_id}:summary",
                    "source_id": source.source_id,
                    "source_name": source.display_name,
                    "connector_type": source.connector_type,
                    "source_url": source.url,
                    "trust_tier": source.trust_tier,
                    "cadence": source.cadence,
                    "checksum": checksum,
                    "source_version": checksum[:12],
                    "ingested_at": ingested_at,
                    "stale_after_minutes": source.stale_after_minutes,
                },
            )
        )

        for name in names:
            if not name.lower().endswith(".csv"):
                continue

            raw = archive.read(name)
            rows = _csv_rows_preview(raw, max_rows=80)
            row_chunks = _rows_to_chunks(rows, chunk_size=20)

            for idx, row_chunk in enumerate(row_chunks):
                chunks.append(
                    ExternalChunk(
                        text=(
                            f"Source: {source.display_name}\n"
                            f"File: {name}\n"
                            f"Chunk: {idx + 1}/{len(row_chunks)}\n"
                            f"Data sample (JSON rows):\n{row_chunk}"
                        ),
                        metadata={
                            "source": f"external:{source.source_id}:{name}:chunk-{idx}",
                            "source_id": source.source_id,
                            "source_name": source.display_name,
                            "connector_type": source.connector_type,
                            "source_url": source.url,
                            "archive_entry": name,
                            "trust_tier": source.trust_tier,
                            "cadence": source.cadence,
                            "checksum": checksum,
                            "source_version": checksum[:12],
                            "ingested_at": ingested_at,
                            "stale_after_minutes": source.stale_after_minutes,
                        },
                    )
                )

    return chunks


def ingest_external_sources() -> list[ExternalChunk]:
    external_chunks: list[ExternalChunk] = []

    for source in SOURCES:
        try:
            logger.info("[RAG] ingesting external source id=%s", source.source_id)
            if source.connector_type == "http_csv":
                produced = _ingest_http_csv(source)
            elif source.connector_type == "http_zip":
                produced = _ingest_http_zip(source)
            else:
                logger.warning("[RAG] unsupported connector=%s source=%s", source.connector_type, source.source_id)
                produced = []

            logger.info("[RAG] source=%s produced chunks=%s", source.source_id, len(produced))
            external_chunks.extend(produced)
        except Exception as exc:
            logger.warning("[RAG] external source failed id=%s error=%s", source.source_id, str(exc))

    return external_chunks
