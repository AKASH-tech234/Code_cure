"""Artifact-first Epidemic_Spread_Prediction adapter for ml-service."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
import json
import logging
import os
import pickle
from typing import Any

from app.data.region_templates import (
    RISK_WEIGHTS,
    compute_risk_score,
    get_all_region_ids,
    get_region,
    risk_level_from_score,
)
from app.services.history_store import FEATURE_COLUMNS, HistoryStore

logger = logging.getLogger(__name__)

ADAPTER_METADATA_PATH_ENV = "EPIDEMIC_ADAPTER_METADATA_PATH"
MODEL_ARTIFACT_DIR_ENV = "EPIDEMIC_MODEL_ARTIFACT_DIR"
STRICT_ARTIFACT_MODE_ENV = "EPIDEMIC_STRICT_ARTIFACT_MODE"

POINT_MODEL_FILE = "epidemic_xgboost_point.pkl"
Q10_MODEL_FILE = "epidemic_xgboost_q10.pkl"
Q50_MODEL_FILE = "epidemic_xgboost_q50.pkl"
Q90_MODEL_FILE = "epidemic_xgboost_q90.pkl"
METADATA_FILE = "model_metadata.json"


def _default_artifact_dir() -> str:
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    return os.path.join(base_dir, "data", "models")


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _inv_log_growth(prev_roll7: float, lg_pred: float, epsilon: float = 1.0) -> float:
    return (max(prev_roll7, 0.0) + epsilon) * (2.718281828459045 ** lg_pred) - epsilon


def _bool_env(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


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
    prediction_date: str | None = None
    country: str | None = None
    point_forecast: dict[str, Any] | None = None
    prediction_interval_80pct: dict[str, Any] | None = None
    model_metadata: dict[str, Any] | None = None


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
    """Notebook-artifact-backed adapter with model-spec-compatible fields."""

    def __init__(self) -> None:
        self._ready = False
        self._metadata: dict[str, Any] = {}
        self._supported_regions: set[str] = set()
        self._history_store = HistoryStore()
        self._artifact_dir = os.getenv(MODEL_ARTIFACT_DIR_ENV, _default_artifact_dir())
        self._strict_artifact_mode = _bool_env(STRICT_ARTIFACT_MODE_ENV, default=False)

        self._point_model: Any = None
        self._q10_model: Any = None
        self._q50_model: Any = None
        self._q90_model: Any = None
        self._artifact_ready = False

    @property
    def is_ready(self) -> bool:
        return self._ready

    @property
    def artifact_ready(self) -> bool:
        return self._artifact_ready

    def initialize(self) -> None:
        metadata = {
            "target": "New_Confirmed_Roll7",
            "model_type": "XGBoost (log-growth, quantile regression)",
            "naive_baseline_mae": 1682,
            "model_mae": 1394,
            "improvement_over_naive_pct": 17.1,
            "supported_regions": ["USA"],
            "features": FEATURE_COLUMNS,
        }

        metadata_path = os.getenv(
            ADAPTER_METADATA_PATH_ENV,
            os.path.join(self._artifact_dir, METADATA_FILE),
        )
        if os.path.exists(metadata_path):
            try:
                with open(metadata_path, "r", encoding="utf-8") as file:
                    loaded = json.load(file)
                    if isinstance(loaded, dict):
                        metadata.update(loaded)
            except Exception as exc:
                logger.warning("[EPI_ADAPTER] Failed to read metadata %s: %s", metadata_path, exc)

        self._metadata = metadata
        self._artifact_ready = self._load_artifacts()

        configured_regions = metadata.get("supported_regions")
        if isinstance(configured_regions, list) and configured_regions:
            self._supported_regions = {str(item).upper() for item in configured_regions}
        else:
            self._supported_regions = set(get_all_region_ids())

        self._ready = True
        logger.info(
            "[EPI_ADAPTER] ready=%s artifact_ready=%s artifact_dir=%s",
            self._ready,
            self._artifact_ready,
            self._artifact_dir,
        )

        if self._strict_artifact_mode and not self._artifact_ready:
            raise RuntimeError("Strict artifact mode enabled but XGBoost artifacts are missing")

    def _load_artifacts(self) -> bool:
        required = {
            "point": os.path.join(self._artifact_dir, POINT_MODEL_FILE),
            "q10": os.path.join(self._artifact_dir, Q10_MODEL_FILE),
            "q50": os.path.join(self._artifact_dir, Q50_MODEL_FILE),
            "q90": os.path.join(self._artifact_dir, Q90_MODEL_FILE),
        }

        missing = [name for name, path in required.items() if not os.path.exists(path)]
        if missing:
            logger.warning("[EPI_ADAPTER] Missing model artifacts: %s", ", ".join(missing))
            return False

        try:
            with open(required["point"], "rb") as file:
                self._point_model = pickle.load(file)
            with open(required["q10"], "rb") as file:
                self._q10_model = pickle.load(file)
            with open(required["q50"], "rb") as file:
                self._q50_model = pickle.load(file)
            with open(required["q90"], "rb") as file:
                self._q90_model = pickle.load(file)
        except Exception as exc:
            logger.exception("[EPI_ADAPTER] Failed loading artifacts: %s", exc)
            return False

        return True

    def supports_region(self, region_id: str) -> bool:
        if not self._ready:
            return False
        region = region_id.upper()
        return region in self._supported_regions and get_region(region) is not None

    @staticmethod
    def _resolve_prediction_date(prediction_date: str | None) -> date:
        if not prediction_date:
            return date.today() + timedelta(days=1)
        try:
            return datetime.fromisoformat(prediction_date).date()
        except ValueError:
            return date.today() + timedelta(days=1)

    def _predict_quantiles(self, features: dict[str, float], prev_roll7: float) -> tuple[float, float, float, float]:
        if not self._artifact_ready:
            raise RuntimeError("XGBoost artifacts are not loaded")

        vector = [[float(features[name]) for name in FEATURE_COLUMNS]]

        point_lg = float(self._point_model.predict(vector)[0])
        q10_lg = float(self._q10_model.predict(vector)[0])
        q50_lg = float(self._q50_model.predict(vector)[0])
        q90_lg = float(self._q90_model.predict(vector)[0])

        point = max(_inv_log_growth(prev_roll7, point_lg), 0.0)
        q10 = max(_inv_log_growth(prev_roll7, q10_lg), 0.0)
        q50 = max(_inv_log_growth(prev_roll7, q50_lg), 0.0)
        q90 = max(_inv_log_growth(prev_roll7, q90_lg), 0.0)

        ordered = sorted([q10, q50, q90])
        return point, ordered[0], ordered[1], ordered[2]

    def _risk_drivers(self, growth_rate: float, region_id: str) -> list[AdapterRiskDriver]:
        region = get_region(region_id)
        if not region:
            raise ValueError(f"Region '{region_id}' not supported")

        growth_normalized = _clamp(growth_rate / 0.15, 0.0, 1.0)
        vaccination_gap = 1.0 - _clamp(float(region["vaccination_rate"]), 0.0, 1.0)

        return [
            AdapterRiskDriver(
                factor="predicted_growth_rate",
                value=round(growth_normalized, 3),
                weight=RISK_WEIGHTS["predicted_growth_rate"],
            ),
            AdapterRiskDriver(
                factor="mobility_index",
                value=round(float(region["mobility_index"]), 3),
                weight=RISK_WEIGHTS["mobility_index"],
            ),
            AdapterRiskDriver(
                factor="vaccination_gap",
                value=round(vaccination_gap, 3),
                weight=RISK_WEIGHTS["vaccination_gap"],
            ),
            AdapterRiskDriver(
                factor="hospital_pressure",
                value=round(float(region["hospital_pressure"]), 3),
                weight=RISK_WEIGHTS["hospital_pressure"],
            ),
        ]

    @staticmethod
    def _model_metadata_payload(metadata: dict[str, Any]) -> dict[str, Any]:
        return {
            "target": metadata.get("target", "New_Confirmed_Roll7"),
            "model_type": metadata.get("model_type", "XGBoost (log-growth, quantile regression)"),
            "naive_baseline_mae": metadata.get("naive_baseline_mae", 1682),
            "model_mae": metadata.get("model_mae", 1394),
            "improvement_over_naive_pct": metadata.get("improvement_over_naive_pct", 17.1),
        }

    @staticmethod
    def _parse_feature_overrides(features: dict[str, Any] | None) -> dict[str, float] | None:
        if features is None:
            return None
        missing = [name for name in FEATURE_COLUMNS if name not in features]
        if missing:
            raise ValueError(f"Missing feature fields: {', '.join(missing)}")
        return {name: float(features[name]) for name in FEATURE_COLUMNS}

    def forecast(
        self,
        region_id: str,
        horizon_days: int,
        features: dict[str, Any] | None = None,
        prev_roll7: float | None = None,
        prediction_date: str | None = None,
        country: str | None = None,
    ) -> AdapterForecastResult:
        region = region_id.upper()
        if not self.supports_region(region):
            raise ValueError(f"Region '{region}' not supported by epidemic adapter")
        if not self._artifact_ready:
            raise RuntimeError("Artifact models are not loaded")

        override_features = self._parse_feature_overrides(features)
        forecast_start = self._resolve_prediction_date(prediction_date)
        history = self._history_store.get_history_copy(region)

        predicted_cases: list[int] = []
        first_interval: tuple[float, float, float] | None = None
        first_point = 0.0
        first_prev_roll7 = 0.0

        for step in range(horizon_days):
            point_day = forecast_start + timedelta(days=step)
            feature_row, prev_roll = self._history_store.build_feature_row(
                history=history,
                point_day=point_day,
                features_override=override_features if step == 0 else None,
                prev_roll7_override=prev_roll7 if step == 0 else None,
            )

            point, q10, q50, q90 = self._predict_quantiles(feature_row, prev_roll)
            if step == 0:
                first_point = point
                first_prev_roll7 = prev_roll
                first_interval = (q10, q50, q90)

            predicted_cases.append(int(round(point)))
            self._history_store.append_prediction(history, point_day=point_day, predicted_roll7=point)

        if horizon_days > 1:
            growth_rate = (predicted_cases[-1] - predicted_cases[0]) / max(predicted_cases[0], 1)
        else:
            growth_rate = (first_point - first_prev_roll7) / max(first_prev_roll7, 1.0)
        growth_rate = round(float(growth_rate), 4)

        region_data = get_region(region)
        if not region_data:
            raise ValueError(f"Region '{region}' not supported")

        risk_score = compute_risk_score(
            growth_rate=growth_rate,
            mobility=float(region_data["mobility_index"]),
            vaccination_rate=float(region_data["vaccination_rate"]),
            hospital_pressure=float(region_data["hospital_pressure"]),
        )
        risk_level = risk_level_from_score(risk_score)

        q10, q50, q90 = first_interval if first_interval else (first_point, first_point, first_point)
        resolved_country = country or str(region_data.get("name") or region)

        return AdapterForecastResult(
            region_id=region,
            predicted_cases=predicted_cases,
            growth_rate=growth_rate,
            risk_score=risk_score,
            risk_level=risk_level,
            horizon_days=horizon_days,
            as_of_date=date.today().isoformat(),
            prediction_date=forecast_start.isoformat(),
            country=resolved_country,
            point_forecast={
                "predicted_roll7_cases": round(first_point, 2),
                "description": "Expected 7-day rolling average of new confirmed cases",
            },
            prediction_interval_80pct={
                "lower_q10": round(q10, 2),
                "median_q50": round(q50, 2),
                "upper_q90": round(q90, 2),
                "coverage_guarantee": "80% - actual value falls in this range 80% of the time",
            },
            model_metadata=self._model_metadata_payload(self._metadata),
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
        if not self._artifact_ready:
            raise RuntimeError("Artifact models are not loaded")

        horizon_days = 7
        baseline = self.forecast(region, horizon_days=horizon_days)

        history = self._history_store.get_history_copy(region)
        forecast_start = date.today() + timedelta(days=1)
        simulated_cases: list[int] = []

        for step in range(horizon_days):
            point_day = forecast_start + timedelta(days=step)
            features, prev_roll = self._history_store.build_feature_row(history, point_day)

            case_scale = _clamp(1.0 - mobility_reduction * 0.55 - vaccination_increase * 0.35, 0.25, 1.0)
            features["New_Confirmed_Lag1"] *= case_scale
            features["New_Confirmed_Lag3"] *= case_scale
            features["New_Confirmed_Lag7"] *= case_scale
            features["New_Confirmed_Roll14_Lag1"] *= case_scale
            features["stringency_index"] = _clamp(
                features["stringency_index"] + mobility_reduction * 25.0 + vaccination_increase * 10.0,
                0.0,
                100.0,
            )
            features["reproduction_rate"] = _clamp(
                features["reproduction_rate"] - mobility_reduction * 0.45 - vaccination_increase * 0.35,
                0.4,
                2.2,
            )

            point, _, _, _ = self._predict_quantiles(features, prev_roll)
            simulated_cases.append(int(round(point)))
            self._history_store.append_prediction(history, point_day=point_day, predicted_roll7=point)

        baseline_cases = baseline.predicted_cases[:horizon_days]
        delta_cases = max(sum(baseline_cases) - sum(simulated_cases), 0)

        parts: list[str] = []
        if mobility_reduction > 0:
            parts.append(f"{int(mobility_reduction * 100)}% mobility reduction")
        if vaccination_increase > 0:
            parts.append(f"{int(vaccination_increase * 100)}% vaccination increase")
        intervention_desc = " + ".join(parts) if parts else "no intervention"

        return AdapterSimulateResult(
            region_id=region,
            baseline_cases=baseline_cases,
            simulated_cases=simulated_cases,
            delta_cases=delta_cases,
            impact_summary=f"{intervention_desc} could avert ~{delta_cases:,} cases over {horizon_days} days",
        )

    def risk(self, region_id: str) -> AdapterRiskResult:
        region = region_id.upper()
        if not self.supports_region(region):
            raise ValueError(f"Region '{region}' not supported by epidemic adapter")
        if not self._artifact_ready:
            raise RuntimeError("Artifact models are not loaded")

        forecast = self.forecast(region_id=region, horizon_days=7)
        drivers = self._risk_drivers(growth_rate=forecast.growth_rate, region_id=region)

        return AdapterRiskResult(
            region_id=region,
            risk_level=forecast.risk_level,
            risk_score=forecast.risk_score,
            drivers=drivers,
        )
