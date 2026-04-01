"""In-memory history store for constructing model features aligned with notebook schema."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
import math
from typing import Any

from app.data.region_templates import get_region


FEATURE_COLUMNS = [
    "DayOfWeek",
    "Month",
    "IsWeekend",
    "New_Confirmed_Lag1",
    "New_Confirmed_Lag3",
    "New_Confirmed_Lag7",
    "New_Deaths_Lag1",
    "New_Confirmed_Roll14_Lag1",
    "stringency_index",
    "reproduction_rate",
]


@dataclass
class HistoryEntry:
    date: date
    new_confirmed: float
    new_deaths: float
    stringency_index: float
    reproduction_rate: float
    roll7: float


class HistoryStore:
    """Builds deterministic history snapshots for feature extraction per region."""

    def __init__(self, seed_days: int = 40) -> None:
        self._seed_days = seed_days
        self._history: dict[str, list[HistoryEntry]] = {}

    @staticmethod
    def _clamp(value: float, low: float, high: float) -> float:
        return max(low, min(high, value))

    def _seed_region(self, region_id: str) -> list[HistoryEntry]:
        region = get_region(region_id)
        if not region:
            raise ValueError(f"Region '{region_id}' not found")

        base_cases = float(region["base_cases"])
        weekly_growth = float(region["growth_rate"])
        stringency = float(region.get("stringency_index", 40.0))
        mobility = float(region["mobility_index"])
        vaccination = float(region["vaccination_rate"])
        hospital = float(region["hospital_pressure"])

        start = date.today() - timedelta(days=self._seed_days)
        series: list[HistoryEntry] = []

        current = max(base_cases * 0.72, 1.0)
        for idx in range(self._seed_days):
            point_day = start + timedelta(days=idx)
            seasonality = 1.0 + 0.03 * math.sin(idx / 4.0)
            current = max(current * (1.0 + weekly_growth / 7.0) * seasonality, 1.0)

            new_confirmed = float(round(current))
            new_deaths = float(round(new_confirmed * (0.002 + hospital * 0.004), 2))
            reproduction_rate = self._clamp(
                0.75 + weekly_growth * 3.1 + mobility * 0.52 - vaccination * 0.44 + hospital * 0.23,
                0.45,
                2.4,
            )
            stringency_point = self._clamp(
                stringency + 2.0 * math.sin(idx / 5.0),
                0.0,
                100.0,
            )

            roll7_window = [entry.new_confirmed for entry in series[-6:]] + [new_confirmed]
            roll7 = sum(roll7_window) / len(roll7_window)

            series.append(
                HistoryEntry(
                    date=point_day,
                    new_confirmed=new_confirmed,
                    new_deaths=new_deaths,
                    stringency_index=stringency_point,
                    reproduction_rate=reproduction_rate,
                    roll7=roll7,
                )
            )

        return series

    def get_history_copy(self, region_id: str) -> list[HistoryEntry]:
        region = region_id.upper()
        if region not in self._history:
            self._history[region] = self._seed_region(region)
        return list(self._history[region])

    def append_prediction(
        self,
        history: list[HistoryEntry],
        point_day: date,
        predicted_roll7: float,
    ) -> None:
        prev = history[-1]
        new_confirmed = max(predicted_roll7, 0.0)
        new_deaths = max(new_confirmed * (prev.new_deaths / max(prev.new_confirmed, 1.0)), 0.0)
        roll7_window = [entry.new_confirmed for entry in history[-6:]] + [new_confirmed]
        roll7 = sum(roll7_window) / len(roll7_window)

        history.append(
            HistoryEntry(
                date=point_day,
                new_confirmed=new_confirmed,
                new_deaths=new_deaths,
                stringency_index=prev.stringency_index,
                reproduction_rate=prev.reproduction_rate,
                roll7=roll7,
            )
        )

    def build_feature_row(
        self,
        history: list[HistoryEntry],
        point_day: date,
        features_override: dict[str, float] | None = None,
        prev_roll7_override: float | None = None,
    ) -> tuple[dict[str, float], float]:
        if features_override is not None:
            parsed = {name: float(features_override[name]) for name in FEATURE_COLUMNS}
            prev_roll7 = float(prev_roll7_override) if prev_roll7_override is not None else float(
                parsed["New_Confirmed_Roll14_Lag1"]
            )
            return parsed, max(prev_roll7, 0.0)

        if len(history) < 14:
            raise ValueError("Insufficient history to compute lag features")

        lag1 = history[-1].new_confirmed
        lag3 = history[-3].new_confirmed
        lag7 = history[-7].new_confirmed
        deaths_lag1 = history[-1].new_deaths
        roll14_lag1 = sum(entry.new_confirmed for entry in history[-14:]) / 14.0

        features = {
            "DayOfWeek": float(point_day.weekday()),
            "Month": float(point_day.month),
            "IsWeekend": 1.0 if point_day.weekday() >= 5 else 0.0,
            "New_Confirmed_Lag1": float(lag1),
            "New_Confirmed_Lag3": float(lag3),
            "New_Confirmed_Lag7": float(lag7),
            "New_Deaths_Lag1": float(deaths_lag1),
            "New_Confirmed_Roll14_Lag1": float(roll14_lag1),
            "stringency_index": float(history[-1].stringency_index),
            "reproduction_rate": float(history[-1].reproduction_rate),
        }

        return features, max(history[-1].roll7, 0.0)
