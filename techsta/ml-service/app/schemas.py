from pydantic import BaseModel, Field
from typing import List, Optional


# ── FORECAST ──────────────────────────────────────────────────────────

class ForecastRequest(BaseModel):
    region_id: str = Field(..., min_length=3, max_length=3, description="ISO alpha-3 country code")
    horizon_days: int = Field(default=7, ge=1, le=30)


class ForecastResponse(BaseModel):
    region_id: str
    predicted_cases: List[int]
    growth_rate: float
    risk_score: float
    risk_level: str  # "Low" | "Medium" | "High"
    horizon_days: int
    as_of_date: str


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
