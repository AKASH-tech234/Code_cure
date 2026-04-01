from pydantic import BaseModel, Field
from typing import List, Optional


# ── FORECAST ──────────────────────────────────────────────────────────

class ForecastRequest(BaseModel):
    region_id: str = Field(..., min_length=3, max_length=3, description="ISO alpha-3 country code")
    horizon_days: int = Field(default=7, ge=1, le=30)
    country: Optional[str] = None
    prediction_date: Optional[str] = None
    features: Optional["ForecastModelFeatures"] = None
    prev_roll7: Optional[float] = Field(default=None, ge=0.0)


class ForecastModelFeatures(BaseModel):
    DayOfWeek: int = Field(..., ge=0, le=6)
    Month: int = Field(..., ge=1, le=12)
    IsWeekend: int = Field(..., ge=0, le=1)
    New_Confirmed_Lag1: float = Field(..., ge=0.0)
    New_Confirmed_Lag3: float = Field(..., ge=0.0)
    New_Confirmed_Lag7: float = Field(..., ge=0.0)
    New_Deaths_Lag1: float = Field(..., ge=0.0)
    New_Confirmed_Roll14_Lag1: float = Field(..., ge=0.0)
    stringency_index: float = Field(..., ge=0.0, le=100.0)
    reproduction_rate: float = Field(..., ge=0.1, le=5.0)


class PointForecast(BaseModel):
    predicted_roll7_cases: float
    description: Optional[str] = None


class PredictionInterval80Pct(BaseModel):
    lower_q10: float
    median_q50: float
    upper_q90: float
    coverage_guarantee: Optional[str] = None


class ForecastModelMetadata(BaseModel):
    target: Optional[str] = None
    model_type: Optional[str] = None
    naive_baseline_mae: Optional[float] = None
    model_mae: Optional[float] = None
    improvement_over_naive_pct: Optional[float] = None


class ForecastResponse(BaseModel):
    region_id: str
    predicted_cases: List[int]
    growth_rate: float
    risk_score: float
    risk_level: str  # "Low" | "Medium" | "High"
    horizon_days: int
    as_of_date: str
    prediction_date: Optional[str] = None
    country: Optional[str] = None
    point_forecast: Optional[PointForecast] = None
    prediction_interval_80pct: Optional[PredictionInterval80Pct] = None
    model_metadata: Optional[ForecastModelMetadata] = None


# ── SIMULATE ──────────────────────────────────────────────────────────

class InterventionInput(BaseModel):
    mobility_reduction: float = Field(..., ge=0.0, le=1.0)
    vaccination_increase: float = Field(..., ge=0.0, le=1.0)


class SimulateRequest(BaseModel):
    region_id: str = Field(..., min_length=3, max_length=3)
    intervention: InterventionInput


class SimulateResponse(BaseModel):
    region_id: str
    baseline_cases: List[int]
    simulated_cases: List[int]
    delta_cases: int
    impact_summary: str


# ── RISK ──────────────────────────────────────────────────────────────

class RiskRequest(BaseModel):
    region_id: str = Field(..., min_length=3, max_length=3)


class RiskDriver(BaseModel):
    factor: str
    value: float
    weight: float


class RiskResponse(BaseModel):
    region_id: str
    risk_level: str  # "Low" | "Medium" | "High"
    risk_score: float
    drivers: List[RiskDriver]
