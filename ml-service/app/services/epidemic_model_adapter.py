"""
Epidemic_Spread_Prediction adapter for ml-service.

This adapter keeps the existing ml-service HTTP contracts intact while using
signal engineering inspired by the Epidemic_Spread_Prediction model API spec.
If adapter logic fails at runtime, callers are expected to fall back to the
existing template-based behavior.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
import json
import logging
import math
import os
from typing import Any

from app.data.region_templates import (
    RISK_WEIGHTS,
    compute_risk_score,
    get_all_region_ids,
    get_region,
    risk_level_from_score,
)

logger = logging.getLogger(__name__)

ADAPTER_METADATA_PATH_ENV = "EPIDEMIC_ADAPTER_METADATA_PATH"


def _default_adapter_metadata_path() -> str:
    # app/services -> app -> ml-service root
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    return os.path.join(base_dir, "data", "epidemic_spread_adapter_metadata.json")


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


@dataclass
class AdapterRiskDriver:
    factor: str
    value: float
    weight: float


@dataclass
class AdapterForecastResult:
    region_id: str
    predicted_cases: list[int]
    growth_rate: float
    risk_score: float
    risk_level: str
    horizon_days: int
    as_of_date: str


@dataclass
class AdapterSimulateResult:
    region_id: str
    baseline_cases: list[int]
    simulated_cases: list[int]
    delta_cases: int
    impact_summary: str


@dataclass
class AdapterRiskResult:
    region_id: str
    risk_level: str
    risk_score: float
    drivers: list[AdapterRiskDriver]


class EpidemicModelAdapter:
    """
    Contract-preserving adapter for Epidemic_Spread_Prediction priority behavior.

    The public ml-service routes still accept and return the same schemas. Internally,
    this adapter applies spec-inspired signals (lags, policy index, reproduction) and
    converts those into the existing forecast/risk/simulate response fields.
    """

    def __init__(self) -> None:
        self._ready = False
        self._metadata: dict[str, Any] = {}
        self._supported_regions: set[str] = set()

    @property
    def is_ready(self) -> bool:
        return self._ready

    def initialize(self) -> None:
        metadata: dict[str, Any] = {
            "model_name": "Epidemic_Spread_Prediction",
            "model_type": "XGBoost (log-growth, quantile regression)",
            "naive_baseline_mae": 1682,
            "model_mae": 1394,
            "improvement_over_naive_pct": 17.1,
            "coefficients": {
                "intercept": 0.003,
                "reproduction_rate": 0.30,
                "stringency_index": -0.0022,
                "momentum": 0.22,
                "weekend": -0.035,
                "death_ratio": 0.07,
                "seasonality": 0.02,
            },
        }

        metadata_path = os.getenv(ADAPTER_METADATA_PATH_ENV, _default_adapter_metadata_path())
        if os.path.exists(metadata_path):
            try:
                with open(metadata_path, "r", encoding="utf-8") as file:
                    loaded = json.load(file)
                    if isinstance(loaded, dict):
                        metadata.update(loaded)
            except Exception as exc:
                logger.warning(
                    "[EPI_ADAPTER] Failed to load metadata from %s: %s",
                    metadata_path,
                    exc,
                )

        self._metadata = metadata

        regions = set(get_all_region_ids())
        extra_regions = metadata.get("supported_regions")
        if isinstance(extra_regions, list):
            regions.update(str(item).upper() for item in extra_regions if item)

        self._supported_regions = regions
        self._ready = True

        logger.info(
            "[EPI_ADAPTER] Initialized with %d region(s)",
            len(self._supported_regions),
        )

    def supports_region(self, region_id: str) -> bool:
        if not self._ready:
            return False
        region = region_id.upper()
        return region in self._supported_regions and get_region(region) is not None

    def _derive_signal_state(
        self,
        region_id: str,
        mobility_reduction: float = 0.0,
        vaccination_increase: float = 0.0,
    ) -> dict[str, float]:
        region = get_region(region_id)
        if not region:
            raise ValueError(f"Region '{region_id}' not supported")

        mobility_delta = _clamp(mobility_reduction, 0.0, 1.0)
        vaccination_delta = _clamp(vaccination_increase, 0.0, 1.0)

        mobility = _clamp(float(region["mobility_index"]) * (1.0 - mobility_delta), 0.0, 1.0)
        vaccination = _clamp(float(region["vaccination_rate"]) + vaccination_delta, 0.0, 1.0)
        stringency = _clamp(
            float(region.get("stringency_index", 40.0)) + mobility_delta * 20.0 + vaccination_delta * 10.0,
            0.0,
            100.0,
        )
        hospital = _clamp(float(region["hospital_pressure"]), 0.0, 1.0)
        baseline_growth = float(region["growth_rate"])

        reproduction_rate = _clamp(
            0.74
            + baseline_growth * 3.4
            + mobility * 0.62
            - vaccination * 0.52
            + hospital * 0.24
            - (stringency / 100.0) * 0.18,
            0.45,
            2.40,
        )

        return {
            "mobility_index": mobility,
            "vaccination_rate": vaccination,
            "stringency_index": stringency,
            "hospital_pressure": hospital,
            "baseline_growth": baseline_growth,
            "reproduction_rate": reproduction_rate,
        }

    def _predict_weekly_growth(self, state: dict[str, float], day: date, current_cases: float) -> float:
        coeff = self._metadata.get("coefficients") or {}

        lag1 = max(current_cases, 0.0)
        lag3 = max(current_cases * (1.0 - state["baseline_growth"] * 0.35), 0.0)
        lag7 = max(current_cases * (1.0 - state["baseline_growth"] * 0.90), 0.0)
        lag14 = max(current_cases * (1.0 - state["baseline_growth"] * 1.40), 0.0)
        roll14_lag1 = (lag1 + lag3 + lag7 + lag14) / 4.0
        deaths_lag1 = max(current_cases * (0.002 + state["hospital_pressure"] * 0.004), 0.0)

        momentum = (lag1 - lag7) / max(lag7, 1.0)
        death_ratio = deaths_lag1 / max(lag1, 1.0)
        is_weekend = 1.0 if day.weekday() >= 5 else 0.0
        seasonal = math.sin((2.0 * math.pi * day.timetuple().tm_yday) / 365.0)

        log_growth = (
            float(coeff.get("intercept", 0.003))
            + float(coeff.get("reproduction_rate", 0.30)) * (state["reproduction_rate"] - 1.0)
            + float(coeff.get("stringency_index", -0.0022)) * ((state["stringency_index"] - 45.0) / 10.0)
            + float(coeff.get("momentum", 0.22)) * momentum
            + float(coeff.get("weekend", -0.035)) * is_weekend
            + float(coeff.get("death_ratio", 0.07)) * (death_ratio * 100.0)
            + float(coeff.get("seasonality", 0.02)) * seasonal
            + ((roll14_lag1 - lag1) / max(lag1, 1.0)) * 0.03
        )

        daily_growth = _clamp(
            (math.exp(_clamp(log_growth, -0.18, 0.24)) - 1.0) * 0.55
            + state["baseline_growth"] / 7.0,
            -0.03,
            0.16,
        )

        return _clamp(daily_growth * 7.0, -0.08, 0.24)

    def _rollout_cases(
        self,
        region_id: str,
        horizon_days: int,
        mobility_reduction: float = 0.0,
        vaccination_increase: float = 0.0,
    ) -> tuple[list[int], float, dict[str, float]]:
        region = get_region(region_id)
        if not region:
            raise ValueError(f"Region '{region_id}' not supported")

        current_cases = float(region["base_cases"])
        state = self._derive_signal_state(
            region_id=region_id,
            mobility_reduction=mobility_reduction,
            vaccination_increase=vaccination_increase,
        )

        predicted: list[int] = []
        weekly_growth_values: list[float] = []

        today = date.today()
        for step in range(horizon_days):
            step_day = today + timedelta(days=step + 1)
            weekly_growth = self._predict_weekly_growth(state=state, day=step_day, current_cases=current_cases)
            daily_growth = weekly_growth / 7.0

            current_cases = max(current_cases * (1.0 + daily_growth), 0.0)
            predicted.append(int(round(current_cases)))
            weekly_growth_values.append(weekly_growth)

            reproduction_drift = (state["reproduction_rate"] - 1.0) * 0.02
            policy_drift = -((state["stringency_index"] / 100.0) - 0.35) * 0.01
            state["baseline_growth"] = _clamp(
                state["baseline_growth"] + reproduction_drift + policy_drift,
                -0.08,
                0.24,
            )

        avg_weekly_growth = (
            round(sum(weekly_growth_values) / len(weekly_growth_values), 4)
            if weekly_growth_values
            else round(state["baseline_growth"], 4)
        )

        return predicted, avg_weekly_growth, state

    @staticmethod
    def _risk_drivers(growth_rate: float, state: dict[str, float]) -> list[AdapterRiskDriver]:
        growth_normalized = _clamp(growth_rate / 0.15, 0.0, 1.0)
        vaccination_gap = 1.0 - _clamp(state["vaccination_rate"], 0.0, 1.0)

        return [
            AdapterRiskDriver(
                factor="predicted_growth_rate",
                value=round(growth_normalized, 3),
                weight=RISK_WEIGHTS["predicted_growth_rate"],
            ),
            AdapterRiskDriver(
                factor="mobility_index",
                value=round(_clamp(state["mobility_index"], 0.0, 1.0), 3),
                weight=RISK_WEIGHTS["mobility_index"],
            ),
            AdapterRiskDriver(
                factor="vaccination_gap",
                value=round(vaccination_gap, 3),
                weight=RISK_WEIGHTS["vaccination_gap"],
            ),
            AdapterRiskDriver(
                factor="hospital_pressure",
                value=round(_clamp(state["hospital_pressure"], 0.0, 1.0), 3),
                weight=RISK_WEIGHTS["hospital_pressure"],
            ),
        ]

    def forecast(self, region_id: str, horizon_days: int) -> AdapterForecastResult:
        region = region_id.upper()
        if not self.supports_region(region):
            raise ValueError(f"Region '{region}' not supported by epidemic adapter")

        predicted_cases, growth_rate, state = self._rollout_cases(region, horizon_days)

        risk_score = compute_risk_score(
            growth_rate=growth_rate,
            mobility=state["mobility_index"],
            vaccination_rate=state["vaccination_rate"],
            hospital_pressure=state["hospital_pressure"],
        )

        return AdapterForecastResult(
            region_id=region,
            predicted_cases=predicted_cases,
            growth_rate=growth_rate,
            risk_score=risk_score,
            risk_level=risk_level_from_score(risk_score),
            horizon_days=horizon_days,
            as_of_date=date.today().isoformat(),
        )

    def simulate(
        self,
        region_id: str,
        mobility_reduction: float,
        vaccination_increase: float,
    ) -> AdapterSimulateResult:
        region = region_id.upper()
        if not self.supports_region(region):
            raise ValueError(f"Region '{region}' not supported by epidemic adapter")

        horizon_days = 7
        baseline_cases, _, _ = self._rollout_cases(region, horizon_days)
        simulated_cases, _, _ = self._rollout_cases(
            region,
            horizon_days,
            mobility_reduction=mobility_reduction,
            vaccination_increase=vaccination_increase,
        )

        delta_cases = max(sum(baseline_cases) - sum(simulated_cases), 0)

        parts: list[str] = []
        if mobility_reduction > 0:
            parts.append(f"{int(mobility_reduction * 100)}% mobility reduction")
        if vaccination_increase > 0:
            parts.append(f"{int(vaccination_increase * 100)}% vaccination increase")
        intervention_desc = " + ".join(parts) if parts else "no intervention"

        impact_summary = f"{intervention_desc} could avert ~{delta_cases:,} cases over {horizon_days} days"

        return AdapterSimulateResult(
            region_id=region,
            baseline_cases=baseline_cases,
            simulated_cases=simulated_cases,
            delta_cases=delta_cases,
            impact_summary=impact_summary,
        )

    def risk(self, region_id: str) -> AdapterRiskResult:
        region = region_id.upper()
        if not self.supports_region(region):
            raise ValueError(f"Region '{region}' not supported by epidemic adapter")

        region_data = get_region(region)
        if not region_data:
            raise ValueError(f"Region '{region}' not supported")

        state = self._derive_signal_state(region)
        growth_rate = self._predict_weekly_growth(
            state=state,
            day=date.today(),
            current_cases=float(region_data["base_cases"]),
        )

        risk_score = compute_risk_score(
            growth_rate=growth_rate,
            mobility=state["mobility_index"],
            vaccination_rate=state["vaccination_rate"],
            hospital_pressure=state["hospital_pressure"],
        )
        risk_level = risk_level_from_score(risk_score)

        return AdapterRiskResult(
            region_id=region,
            risk_level=risk_level,
            risk_score=risk_score,
            drivers=self._risk_drivers(growth_rate=growth_rate, state=state),
        )
