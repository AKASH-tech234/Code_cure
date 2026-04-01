from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Literal


# ── Gateway Request/Response Schemas ──────────────────────────────────

class ForecastRequest(BaseModel):
    region_id: str = Field(..., min_length=3, max_length=3)
    horizon_days: int = Field(default=7, ge=1, le=30)


class SimulateInterventionInput(BaseModel):
    mobility_reduction: float = Field(..., ge=0.0, le=1.0)
    vaccination_increase: float = Field(..., ge=0.0, le=1.0)


class SimulateRequest(BaseModel):
    region_id: str = Field(..., min_length=3, max_length=3)
    intervention: SimulateInterventionInput


class RiskRequest(BaseModel):
    region_id: str = Field(..., min_length=3, max_length=3)


class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)
    session_id: Optional[str] = None
    region_id: Optional[str] = Field(default=None, min_length=3, max_length=3)
    intervention: Optional[SimulateInterventionInput] = None


class FollowUp(BaseModel):
    question: str
    missing_fields: List[str]


class SlotStatus(BaseModel):
    required_fields: List[str] = Field(default_factory=list)
    resolved_fields: List[str] = Field(default_factory=list)
    missing_fields: List[str] = Field(default_factory=list)
    is_complete: bool


class VerificationStatus(BaseModel):
    status: Literal["ready", "missing_fields", "error"]
    can_execute: bool
    reason: Optional[str] = None


class ExecutionStep(BaseModel):
    step: Literal["planner", "tool", "llm"]
    status: Literal["completed", "skipped", "blocked", "failed"]
    detail: Optional[str] = None

class QueryResponse(BaseModel):
    session_id: str
    answer: Optional[str] = None
    intent: Optional[str] = None
    tool: Optional[str] = None
    reasoning: Optional[str] = None
    sources: List[str] = Field(default_factory=list)
    structured_data: Optional[Dict[str, Any]] = None
    followup: Optional[FollowUp] = None
    slot_status: Optional[SlotStatus] = None
    verification: Optional[VerificationStatus] = None
    execution_steps: List[ExecutionStep] = Field(default_factory=list)
    fallback_used: bool = False


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: Optional[str] = None


class ErrorResponse(BaseModel):
    error: ErrorDetail
