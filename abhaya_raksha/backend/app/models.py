from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Enum, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base
import enum

class WorkerType(str, enum.Enum):
    food_delivery = "food_delivery"
    ecommerce = "ecommerce"
    grocery = "grocery"

class PolicyStatus(str, enum.Enum):
    active = "active"
    expired = "expired"
    cancelled = "cancelled"

class ClaimStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    paid = "paid"

class Worker(Base):
    __tablename__ = "workers"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    phone = Column(String, nullable=False)
    hashed_password = Column(String, nullable=False)
    worker_type = Column(Enum(WorkerType), nullable=False)
    city = Column(String, nullable=False)
    zone = Column(String, nullable=False)          # delivery zone / area
    lat = Column(Float, nullable=False)
    lng = Column(Float, nullable=False)
    avg_daily_income = Column(Float, default=800.0) # INR
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    # ── Velocity fraud tracking ───────────────────────────────────────────────
    last_lat = Column(Float, nullable=True)          # last known GPS latitude
    last_lng = Column(Float, nullable=True)          # last known GPS longitude
    last_activity_at = Column(DateTime(timezone=True), nullable=True)  # UTC

    policies = relationship("Policy", back_populates="worker")
    claims = relationship("Claim", back_populates="worker")

class Policy(Base):
    __tablename__ = "policies"
    id = Column(Integer, primary_key=True, index=True)
    worker_id = Column(Integer, ForeignKey("workers.id"), nullable=False)
    weekly_premium = Column(Float, nullable=False)   # INR
    coverage_amount = Column(Float, nullable=False)  # INR (max payout per week)
    risk_score = Column(Float, nullable=False)
    status = Column(Enum(PolicyStatus), default=PolicyStatus.active)
    start_date = Column(DateTime(timezone=True), server_default=func.now())
    end_date = Column(DateTime(timezone=True), nullable=False)
    underwriting_start_date = Column(DateTime(timezone=True), nullable=True)  # cover begins after 7-day wait
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    worker = relationship("Worker", back_populates="policies")
    claims = relationship("Claim", back_populates="policy")

class Claim(Base):
    __tablename__ = "claims"
    id = Column(Integer, primary_key=True, index=True)
    worker_id = Column(Integer, ForeignKey("workers.id"), nullable=False)
    policy_id = Column(Integer, ForeignKey("policies.id"), nullable=False)
    trigger_type = Column(String, nullable=False)    # rain / aqi / curfew
    trigger_value = Column(Float, nullable=False)    # actual measured value
    trigger_threshold = Column(Float, nullable=False)
    payout_amount = Column(Float, nullable=False)
    status = Column(Enum(ClaimStatus), default=ClaimStatus.pending)
    fraud_score = Column(Float, default=0.0)         # 0=clean, 1=fraud
    fraud_flags = Column(Text, default="")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    approved_at = Column(DateTime(timezone=True), nullable=True)

    worker = relationship("Worker", back_populates="claims")
    policy = relationship("Policy", back_populates="claims")

class DisruptionEvent(Base):
    __tablename__ = "disruption_events"
    id = Column(Integer, primary_key=True, index=True)
    city = Column(String, nullable=False)
    zone = Column(String, nullable=True)
    event_type = Column(String, nullable=False)      # rain / aqi / curfew / flood
    value = Column(Float, nullable=False)
    threshold = Column(Float, nullable=False)
    triggered = Column(Boolean, default=False)
    recorded_at = Column(DateTime(timezone=True), server_default=func.now())

class RiskLog(Base):
    __tablename__ = "risk_logs"
    id = Column(Integer, primary_key=True, index=True)
    city = Column(String, nullable=False)
    zone = Column(String, nullable=True)
    risk_score = Column(Float, nullable=False)
    rain_mm = Column(Float, default=0.0)
    aqi = Column(Float, default=0.0)
    temp_c = Column(Float, default=0.0)
    curfew = Column(Boolean, default=False)
    recorded_at = Column(DateTime(timezone=True), server_default=func.now())


class GlobalSettings(Base):
    """
    Singleton table — always contains exactly one row (id=1).
    Controls platform-wide kill-switches for Force Majeure events.
    """
    __tablename__ = "global_settings"
    id = Column(Integer, primary_key=True, default=1)
    is_systemic_pause = Column(Boolean, default=False, nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
