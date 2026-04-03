"""
Fraud Detection Service
Techniques:
  1. GPS zone validation      – worker's registered zone vs claim zone
  2. Duplicate claim detection – same worker, same day, same trigger
  3. Time-based anomaly       – claim filed outside working hours (IST)
  4. Claim velocity check     – too many claims in short window
  5. ML anomaly score         – Isolation Forest flags unusual patterns
  6. Impossible velocity      – GPS teleportation between last known position
"""
import os
import math
import logging
import joblib
import numpy as np
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from ..models import Claim, Worker, ClaimStatus

logger = logging.getLogger(__name__)

# ── Model path ────────────────────────────────────────────────────────────────
_MODEL_PATH = os.path.join(os.path.dirname(__file__), "../../../ml/fraud_model.joblib")
_fraud_model = None

def _get_fraud_model():
    """Lazy-load the Isolation Forest model once. Returns None if file is missing."""
    global _fraud_model
    if _fraud_model is None:
        path = os.path.abspath(_MODEL_PATH)
        if os.path.exists(path):
            _fraud_model = joblib.load(path)
            logger.info("fraud_model.joblib loaded from %s", path)
        else:
            logger.warning("fraud_model.joblib not found at %s — ML fraud layer disabled", path)
    return _fraud_model

# ── Constants ─────────────────────────────────────────────────────────────────
MAX_ZONE_DISTANCE_KM = 30.0
WORKING_HOURS = (6, 23)        # 6 AM – 11 PM IST
MAX_CLAIMS_PER_WEEK = 3
MAX_TRAVEL_SPEED_KMH = 80.0    # above this between two GPS pings → impossible velocity

def haversine_km(lat1, lon1, lat2, lon2) -> float:
    """Great-circle distance in km."""
    R = 6371
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

def check_teleportation(worker: Worker, current_lat: float, current_lng: float) -> dict:
    """
    Detects impossible GPS movement between the worker's last recorded position
    and their current position.

    Returns a dict with:
      - triggered (bool): True if speed exceeds MAX_TRAVEL_SPEED_KMH
      - speed_kmh (float): calculated speed, or 0.0 if no prior position
      - distance_km (float): distance travelled since last ping
      - flag (str): human-readable fraud flag string, or ""

    A score of +0.8 is applied by check_fraud() when triggered=True.
    This is high enough to auto-reject on its own (threshold is 0.6).

    Safe defaults:
      - If last_lat/lng are None (first ever ping), returns triggered=False.
      - If last_activity_at is None or time_delta is zero, returns triggered=False
        to avoid division-by-zero on the very first request.
    """
    if worker.last_lat is None or worker.last_lng is None or worker.last_activity_at is None:
        return {"triggered": False, "speed_kmh": 0.0, "distance_km": 0.0, "flag": ""}

    distance_km = haversine_km(worker.last_lat, worker.last_lng, current_lat, current_lng)
    time_delta_hours = (datetime.utcnow() - worker.last_activity_at).total_seconds() / 3600.0

    if time_delta_hours <= 0:
        return {"triggered": False, "speed_kmh": 0.0, "distance_km": distance_km, "flag": ""}

    speed_kmh = distance_km / time_delta_hours

    if speed_kmh > MAX_TRAVEL_SPEED_KMH:
        flag = (
            f"IMPOSSIBLE_VELOCITY: {speed_kmh:.1f} km/h over {distance_km:.1f} km "
            f"in {time_delta_hours * 60:.0f} min"
        )
        logger.warning(
            "Teleportation detected for worker #%d: %.1f km/h (%.1f km in %.0f min)",
            worker.id, speed_kmh, distance_km, time_delta_hours * 60,
        )
        return {"triggered": True, "speed_kmh": speed_kmh, "distance_km": distance_km, "flag": flag}

    return {"triggered": False, "speed_kmh": speed_kmh, "distance_km": distance_km, "flag": ""}


def check_fraud(
    worker: Worker,
    claim_lat: float,
    claim_lng: float,
    trigger_type: str,
    db: Session,
) -> dict:
    """
    Returns fraud_score (0.0–1.0) and a list of human-readable flags.
    Score >= 0.6 → claim is automatically rejected.

    Scoring breakdown:
      GPS mismatch          +0.40
      Duplicate claim       +0.50
      Off-hours             +0.20
      High velocity         +0.65
      Impossible velocity   +0.80
      ML anomaly            +0.25
    """
    flags = []
    score = 0.0

    # ── 1. GPS zone validation ────────────────────────────────────────────────
    # NOTE: Architectural Design Choice for Hackathon Demo
    # This check currently uses the worker's registered coordinates to simulate 
    # parametric triggers. The architecture is mobile-ready; in production, 
    # 'claim_lat/lng' would be replaced by live GPS telemetry from the worker's app.
    dist_km = haversine_km(worker.lat, worker.lng, claim_lat, claim_lng)
    if dist_km > MAX_ZONE_DISTANCE_KM:
        flags.append(f"GPS_MISMATCH: {dist_km:.1f}km from registered zone")
        score += 0.4

    # ── 2. Duplicate claim – same trigger type today ──────────────────────────
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    duplicate = db.query(Claim).filter(
        Claim.worker_id == worker.id,
        Claim.trigger_type == trigger_type,
        Claim.created_at >= today_start,
    ).first()
    if duplicate:
        flags.append("DUPLICATE_CLAIM: same trigger type already claimed today")
        score += 0.5

    # ── 3. Time-based anomaly – claim outside working hours (IST) ───────────────
    # Workers are in India — evaluate working hours in IST, not UTC.
    # UTC+5:30 offset prevents legitimate 6–11 AM IST claims being flagged as off-hours.
    from datetime import timezone
    IST = timezone(timedelta(hours=5, minutes=30))
    hour_ist = datetime.now(IST).hour
    if not (WORKING_HOURS[0] <= hour_ist <= WORKING_HOURS[1]):
        flags.append(f"OFF_HOURS: claim at {hour_ist}:00 IST")
        score += 0.2

    # ── 4. Velocity check – too many claims this week ─────────────────────────
    week_start = datetime.utcnow() - timedelta(days=7)
    recent_claims = db.query(Claim).filter(
        Claim.worker_id == worker.id,
        Claim.created_at >= week_start,
        Claim.status != ClaimStatus.rejected,
    ).count()
    if recent_claims >= MAX_CLAIMS_PER_WEEK:
        flags.append(f"HIGH_VELOCITY: {recent_claims} claims in last 7 days")
        score += 0.65  # sufficient on its own to trigger rejection (>= 0.6 threshold)

    # ── 5. Impossible velocity – GPS teleportation check ─────────────────────
    teleport = check_teleportation(worker, claim_lat, claim_lng)
    if teleport["triggered"]:
        flags.append(teleport["flag"])
        score += 0.8

    # ── 6. ML anomaly score (Isolation Forest) ────────────────────────────────
    # Features: [claims_per_week, avg_claim_gap_hours, gps_distance_km, claim_hour, payout_ratio]
    # avg_claim_gap_hours and payout_ratio use safe defaults when not available in scope.
    model = _get_fraud_model()
    if model is not None:
        try:
            avg_gap_hours = 48.0   # conservative default (normal behaviour)
            payout_ratio = 0.5     # mid-range default
            features = np.array([[
                float(recent_claims),
                avg_gap_hours,
                dist_km,
                float(hour_ist),
                payout_ratio,
            ]])
            prediction = model.predict(features)[0]   # -1 = anomaly, 1 = normal
            if prediction == -1:
                flags.append("ML_ANOMALY: Isolation Forest flagged unusual activity")
                score += 0.25
        except Exception as exc:
            logger.warning("Fraud ML inference failed: %s", exc)

    fraud_score = round(min(score, 1.0), 4)
    return {
        "fraud_score": fraud_score,
        "fraud_flags": "; ".join(flags),
        "is_fraud": fraud_score >= 0.6,
    }


def update_worker_position(worker: Worker, lat: float, lng: float, db: Session) -> None:
    """
    Persist the worker's current GPS position and activity timestamp.
    Called after every /risk and /claim request so check_teleportation()
    always has a fresh prior position to compare against.
    Silently swallows errors — position tracking must never break a request.
    """
    try:
        worker.last_lat = lat
        worker.last_lng = lng
        worker.last_activity_at = datetime.utcnow()
        db.add(worker)
        db.commit()
    except Exception as exc:
        logger.warning("Failed to update position for worker #%d: %s", worker.id, exc)
        db.rollback()
