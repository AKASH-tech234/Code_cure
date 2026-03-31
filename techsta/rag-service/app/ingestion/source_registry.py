"""
Source registry for external dataset ingestion.

Initial scope (Phase 3 slice):
- JHU CSSE global confirmed cases (direct raw CSV)
- Mendeley AMR dataset (public ZIP endpoint)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


ConnectorType = Literal["http_csv", "http_zip"]
Cadence = Literal["5m", "15m", "hourly", "daily", "weekly", "manual"]


@dataclass(frozen=True)
class SourceConfig:
    source_id: str
    display_name: str
    connector_type: ConnectorType
    url: str
    trust_tier: Literal["high", "medium", "low"]
    cadence: Cadence
    stale_after_minutes: int
    usage_notes: str


SOURCES: tuple[SourceConfig, ...] = (
    SourceConfig(
        source_id="jhu_csse_confirmed_global",
        display_name="JHU CSSE COVID-19 Confirmed Global",
        connector_type="http_csv",
        url=(
            "https://github.com/CSSEGISandData/COVID-19/raw/refs/heads/master/"
            "csse_covid_19_data/csse_covid_19_time_series/"
            "time_series_covid19_confirmed_global.csv"
        ),
        trust_tier="high",
        cadence="daily",
        stale_after_minutes=60 * 24 * 3,
        usage_notes="Repository archived; historical dataset with occasional static revisions only.",
    ),
    SourceConfig(
        source_id="mendeley_amr_dataset",
        display_name="Mendeley AMR Dataset (ccmrx8n7mk.1)",
        connector_type="http_zip",
        url="https://data.mendeley.com/public-api/zip/ccmrx8n7mk/download/1",
        trust_tier="medium",
        cadence="weekly",
        stale_after_minutes=60 * 24 * 30,
        usage_notes="Public dataset ZIP endpoint; ingest with provenance and DOI attribution.",
    ),
)
