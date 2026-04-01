"""
Internal epidemic runtime for ml-service.

Phase 1 implementation notes:
- USA-only model path is enabled.
- Non-USA continues to use existing template behavior in routers.
- If runtime initialization fails, routers gracefully fall back.
"""

from __future__ import annotations

import json
import logging
import math
import os
from dataclasses import dataclass
from datetime import date
from typing import Any

logger = logging.getLogger(__name__)


MODEL_METADATA_PATH_ENV = "EPIDEMIC_MODEL_METADATA_PATH"


def _default_metadata_path() -> str:
    # app/services -> app -> ml-service root
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    return os.path.join(base_dir, "data", "epidemic_model_metadata.json")


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


@dataclass
class EpiForecastResult:
    region_id: str
    predicted_cases: list[int]
    growth_rate: float
    risk_score: float
    risk_level: str
    horizon_days: int
    as_of_date: str


@dataclass
class EpiSimulateResult:
    region_id: str
    baseline_cases: list[int]
    simulated_cases: list[int]
    delta_cases: int
    impact_summary: str


@dataclass
class EpiRiskDriver:
    factor: str
    value: float
    weight: float


@dataclass
class EpiRiskResult:
    region_id: str
    risk_level: str
    risk_score: float
    drivers: list[EpiRiskDriver]


class EpidemicRuntime:
    """
    Lightweight deterministic runtime placeholder for USA-only model behavior.

    This runtime intentionally avoids adding heavyweight dependencies in this phase.
    It loads metadata if present and uses deterministic trajectory logic derived from
    metadata defaults. A later phase can swap this with artifact-backed model inference
    without changing router contracts.
    """

    def __init__(self) -> None:
        self._ready = False
        self._metadata: dict[str, Any] = {}

    def initialize(self) -> None:
        metadata_path = os.getenv(MODEL_METADATA_PATH_ENV, _default_metadata_path())

        metadata: dict[str, Any] = {
            "supported_regions": ["USA"],
            "base_cases": 45000,
            "weekly_growth_rate": 0.06,
            "mobility_index": 0.30,
            "vaccination_rate": 0.72,
            "hospital_pressure": 0.20,
            "risk_weights": {
                "predicted_growth_rate": 0.35,
                "mobility_index": 0.25,
                "vaccination_gap": 0.22,
                "hospital_pressure": 0.18,
            },
        }

        if os.path.exists(metadata_path):
            try:
                with open(metadata_path, "r", encoding="utf-8") as file:
                    loaded = json.load(file)
                    if isinstance(loaded, dict):
                        metadata.update(loaded)
            except Exception as exc:
                logger.warning("[EPI_RUNTIME] Failed to load metadata from %s: %s", metadata_path, exc)

        self._metadata = metadata
        self._ready = True
        logger.info("[EPI_RUNTIME] Initialized (supported_regions=%s)", metadata.get("supported_regions"))

    @property
    def is_ready(self) -> bool:
        return self._ready

    def supports_region(self, region_id: str) -> bool:
        if not self._ready:
            return False
        supported = self._metadata.get("supported_regions") or []
        return region_id.upper() in supported

    def _risk_score(self, growth_rate: float, mobility: float, vaccination_rate: float, hospital_pressure: float) -> float:
        weights = self._metadata.get("risk_weights") or {}
        w_growth = float(weights.get("predicted_growth_rate", 0.35))
        w_mobility = float(weights.get("mobility_index", 0.25))
        w_vaccination = float(weights.get("vaccination_gap", 0.22))
        w_hospital = float(weights.get("hospital_pressure", 0.18))

        growth_normalized = _clamp(growth_rate / 0.15, 0.0, 1.0)
        vaccination_gap = 1.0 - _clamp(vaccination_rate, 0.0, 1.0)

        score = (
            w_growth * growth_normalized
            + w_mobility * _clamp(mobility, 0.0, 1.0)
            + w_vaccination * vaccination_gap
            + w_hospital * _clamp(hospital_pressure, 0.0, 1.0)
        )
        return round(_clamp(score, 0.0, 1.0), 3)

    @staticmethod
    def _risk_level(score: float) -> str:
        if score > 0.7:
            return "High"
        if score > 0.4:
            return "Medium"
        return "Low"

    def forecast(self, region_id: str, horizon_days: int) -> EpiForecastResult:
        if not self.supports_region(region_id):
            raise ValueError(f"Region '{region_id}' not supported by epidemic runtime")

        base_cases = int(self._metadata.get("base_cases", 45000))
        growth_rate = float(self._metadata.get("weekly_growth_rate", 0.06))
        mobility = float(self._metadata.get("mobility_index", 0.30))
        vaccination = float(self._metadata.get("vaccination_rate", 0.72))
        hospital = float(self._metadata.get("hospital_pressure", 0.20))

        daily_growth = growth_rate / 7.0
        current = float(base_cases)
        predicted_cases: list[int] = []

        for _ in range(horizon_days):
            current = current * (1.0 + daily_growth)
            predicted_cases.append(int(max(0, round(current))))

        risk_score = self._risk_score(growth_rate, mobility, vaccination, hospital)

        return EpiForecastResult(
            region_id=region_id.upper(),
            predicted_cases=predicted_cases,
            growth_rate=round(growth_rate, 4),
            risk_score=risk_score,
            risk_level=self._risk_level(risk_score),
            horizon_days=horizon_days,
            as_of_date=date.today().isoformat(),
        )

    def simulate(self, region_id: str, mobility_reduction: float, vaccination_increase: float) -> EpiSimulateResult:
        if not self.supports_region(region_id):
            raise ValueError(f"Region '{region_id}' not supported by epidemic runtime")

        base_cases = int(self._metadata.get("base_cases", 45000))
        weekly_growth = float(self._metadata.get("weekly_growth_rate", 0.06))
        horizon_days = 7

        # Baseline
        baseline_cases: list[int] = []
        current_base = float(base_cases)
        baseline_daily = weekly_growth / 7.0
        for _ in range(horizon_days):
            current_base = current_base * (1.0 + baseline_daily)
            baseline_cases.append(int(max(0, round(current_base))))

        # Intervention-adjusted growth
        mobility_effect = _clamp(mobility_reduction, 0.0, 1.0) * 0.15
        vaccination_effect = _clamp(vaccination_increase, 0.0, 1.0) * 0.10
        adjusted_weekly = max(weekly_growth - mobility_effect - vaccination_effect, -0.05)
        adjusted_daily = adjusted_weekly / 7.0

        simulated_cases: list[int] = []
        current_sim = float(base_cases)
        for _ in range(horizon_days):
            current_sim = current_sim * (1.0 + adjusted_daily)
            simulated_cases.append(int(max(0, round(current_sim))))

        delta_cases = max(sum(baseline_cases) - sum(simulated_cases), 0)

        parts: list[str] = []
        if mobility_reduction > 0:
            parts.append(f"{int(mobility_reduction * 100)}% mobility reduction")
        if vaccination_increase > 0:
            parts.append(f"{int(vaccination_increase * 100)}% vaccination increase")
        intervention_desc = " + ".join(parts) if parts else "no intervention"

        impact_summary = f"{intervention_desc} could avert ~{delta_cases:,} cases over {horizon_days} days"

        return EpiSimulateResult(
            region_id=region_id.upper(),
            baseline_cases=baseline_cases,
            simulated_cases=simulated_cases,
            delta_cases=delta_cases,
            impact_summary=impact_summary,
        )

    def risk(self, region_id: str) -> EpiRiskResult:
        if not self.supports_region(region_id):
            raise ValueError(f"Region '{region_id}' not supported by epidemic runtime")

        growth = float(self._metadata.get("weekly_growth_rate", 0.06))
        mobility = float(self._metadata.get("mobility_index", 0.30))
        vaccination = float(self._metadata.get("vaccination_rate", 0.72))
        hospital = float(self._metadata.get("hospital_pressure", 0.20))

        score = self._risk_score(growth, mobility, vaccination, hospital)
        level = self._risk_level(score)
        growth_normalized = _clamp(growth / 0.15, 0.0, 1.0)
        vaccination_gap = 1.0 - _clamp(vaccination, 0.0, 1.0)

        weights = self._metadata.get("risk_weights") or {}
        drivers = [
            EpiRiskDriver(
                factor="predicted_growth_rate",
                value=round(growth_normalized, 3),
                weight=float(weights.get("predicted_growth_rate", 0.35)),
            ),
            EpiRiskDriver(
                factor="mobility_index",
                value=round(mobility, 3),
                weight=float(weights.get("mobility_index", 0.25)),
            ),
            EpiRiskDriver(
                factor="vaccination_gap",
                value=round(vaccination_gap, 3),
                weight=float(weights.get("vaccination_gap", 0.22)),
            ),
            EpiRiskDriver(
                factor="hospital_pressure",
                value=round(hospital, 3),
                weight=float(weights.get("hospital_pressure", 0.18)),
            ),
        ]

        return EpiRiskResult(
            region_id=region_id.upper(),
            risk_level=level,
            risk_score=score,
            drivers=drivers,
        )


epidemic_runtime = EpidemicRuntime()


def initialize_epidemic_runtime() -> None:
    try:
        epidemic_runtime.initialize()
    except Exception:
        logger.exception("[EPI_RUNTIME] Initialization failed; service will keep template fallback behavior")
