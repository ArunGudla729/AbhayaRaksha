from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime
from .models import WorkerType, PolicyStatus, ClaimStatus

# ── Auth ──────────────────────────────────────────────────────────────────────
class WorkerRegister(BaseModel):
    name: str
    email: EmailStr
    phone: str
    password: str
    worker_type: WorkerType
    city: str
    zone: str
    lat: float
    lng: float
    avg_daily_income: float = 800.0

class WorkerLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    is_admin: bool = False

# ── Worker ────────────────────────────────────────────────────────────────────
class WorkerOut(BaseModel):
    id: int
    name: str
    email: str
    phone: str
    worker_type: WorkerType
    city: str
    zone: str
    lat: float
    lng: float
    avg_daily_income: float
    is_admin: bool
    created_at: datetime

    class Config:
        from_attributes = True

# ── Policy ────────────────────────────────────────────────────────────────────
class PolicyCreate(BaseModel):
    pass  # premium is calculated server-side

class PolicyOut(BaseModel):
    id: int
    worker_id: int
    weekly_premium: float
    coverage_amount: float
    risk_score: float
    status: PolicyStatus
    start_date: datetime
    end_date: datetime
    underwriting_start_date: Optional[datetime] = None  # cover begins after 7-day waiting period

    class Config:
        from_attributes = True

# ── Claim ─────────────────────────────────────────────────────────────────────
class ClaimOut(BaseModel):
    id: int
    worker_id: int
    policy_id: int
    trigger_type: str
    trigger_value: float
    trigger_threshold: float
    payout_amount: float
    status: ClaimStatus
    fraud_score: float
    fraud_flags: str
    created_at: datetime
    approved_at: Optional[datetime]

    class Config:
        from_attributes = True

# ── Risk ──────────────────────────────────────────────────────────────────────
class RiskResponse(BaseModel):
    city: str
    zone: str
    risk_score: float
    rain_mm: float
    aqi: float
    temp_c: float
    curfew: bool
    weekly_premium: float
    coverage_amount: float

# ── Disruption ────────────────────────────────────────────────────────────────
class DisruptionEventOut(BaseModel):
    id: int
    city: str
    zone: Optional[str]
    event_type: str
    value: float
    threshold: float
    triggered: bool
    recorded_at: datetime

    class Config:
        from_attributes = True

# ── Admin ─────────────────────────────────────────────────────────────────────
class AdminStats(BaseModel):
    total_workers: int
    total_policies: int
    active_policies: int
    total_claims: int
    approved_claims: int
    total_payout: float
    fraud_alerts: int
    loss_ratio: float

# ── Simulation ────────────────────────────────────────────────────────────────
class SimulationRequest(BaseModel):
    city: str
    zone: str
    event_type: str   # rain / aqi / curfew
    value: float

class SimulationResult(BaseModel):
    event_type: str
    value: float
    threshold: float
    triggered: bool
    affected_workers: int
    total_payout: float
    claims_created: List[ClaimOut]
