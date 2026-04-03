"""
Parametric Claim Engine
Automatically triggers claims when disruption thresholds are breached.
No manual filing needed – pure parametric insurance.
"""
import logging
from datetime import datetime, timedelta
from sqlalchemy import func
from sqlalchemy.orm import Session
from ..models import Worker, Policy, Claim, PolicyStatus, ClaimStatus, DisruptionEvent, GlobalSettings
from .fraud_detector import check_fraud

logger = logging.getLogger(__name__)

# ── Parametric Thresholds ─────────────────────────────────────────────────────
THRESHOLDS = {
    "rain":   15.0,   # mm/3h — default; overridden per city by CITY_RAIN_THRESHOLDS
    "aqi":    200.0,  # AQI index
    "heat":   42.0,   # °C
    "curfew": 1.0,    # boolean as float
    "flood":  1.0,
}

# City-specific rain thresholds (mm/3h) based on IMD climatological normals.
# A uniform 15mm threshold is actuarially unfair: it fires constantly in monsoon
# Mumbai while almost never firing in arid Delhi.
CITY_RAIN_THRESHOLDS = {
    "mumbai":    35.0,  # IMD "heavy rainfall" category; 15mm is a routine Mumbai shower
    "chennai":   25.0,  # moderate monsoon city
    "bangalore": 20.0,  # moderate
    "hyderabad": 15.0,  # default
    "delhi":     12.0,  # semi-arid; 12mm is genuinely disruptive here
}

def _get_rain_threshold(city: str) -> float:
    """Return the city-appropriate rain threshold, falling back to the default."""
    return CITY_RAIN_THRESHOLDS.get(city.lower(), THRESHOLDS["rain"])

# Payout % of coverage per trigger type
# Coverage is now 1× weekly income, so these rates represent days of income replaced:
#   0.167 ≈ 1/6 weekly income = 1 lost working day
#   0.333 ≈ 2 lost working days
#   0.500 ≈ 3 lost working days
PAYOUT_RATES = {
    "rain":   0.167,  # 1 lost working day
    "aqi":    0.167,  # 1 lost working day
    "heat":   0.167,  # 1 lost working day
    "curfew": 0.333,  # 2 lost working days (curfew typically lasts longer)
    "flood":  0.500,  # 3 lost working days (severe event)
}

def trigger_claims_for_event(
    city: str,
    zone: str,
    event_type: str,
    value: float,
    db: Session
) -> list[Claim]:
    """
    Called by the scheduler or simulation endpoint.
    Finds all active policies in the affected city/zone and creates claims.
    """
    threshold = _get_rain_threshold(city) if event_type == "rain" else THRESHOLDS.get(event_type, 0)
    if value < threshold:
        return []

    # ── Systemic pause kill-switch ────────────────────────────────────────────
    # Checked before any DB writes. If a Force Majeure event (war, pandemic,
    # nuclear) has been declared by an admin, all automated payouts are suspended
    # to prevent fund insolvency.
    settings = db.query(GlobalSettings).filter(GlobalSettings.id == 1).first()
    if settings and settings.is_systemic_pause:
        logger.warning(
            "SYSTEMIC PAUSE: Payouts suspended for fund sustainability during a "
            "Force Majeure event. Event %s/%s=%s not processed.",
            city, event_type, value
        )
        return []

    # Record disruption event
    event = DisruptionEvent(
        city=city, zone=zone,
        event_type=event_type,
        value=value,
        threshold=threshold,
        triggered=True
    )
    db.add(event)
    db.flush()

    # Find affected workers with active policies
    workers = db.query(Worker).filter(
        Worker.city.ilike(f"%{city}%"),
        Worker.is_active == True
    ).all()

    created_claims = []
    for worker in workers:
        # Get active policy — must be within its coverage window AND past underwriting period
        policy = db.query(Policy).filter(
            Policy.worker_id == worker.id,
            Policy.status == PolicyStatus.active,
            Policy.start_date <= datetime.utcnow(),
            Policy.end_date >= datetime.utcnow(),
            # BUG-H02 fix: never fire claims during the underwriting waiting period
            (Policy.underwriting_start_date == None) |
            (Policy.underwriting_start_date <= datetime.utcnow()),
        ).first()
        if not policy:
            continue

        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        week_start  = datetime.utcnow() - timedelta(days=7)

        # ── Double-dip guard: one payout per worker per calendar day ─────────
        # Blocks Rain + AQI same-day stacking — any approved/paid claim today
        # means the worker has already been compensated for this disruption day.
        today_paid = db.query(func.sum(Claim.payout_amount)).filter(
            Claim.worker_id == worker.id,
            Claim.created_at >= today_start,
            Claim.status.in_([ClaimStatus.approved, ClaimStatus.paid]),
        ).scalar() or 0.0

        if today_paid >= worker.avg_daily_income:
            continue  # daily cap reached — worker already compensated for today

        # ── Weekly aggregate cap: total payouts cannot exceed weekly income ──
        weekly_paid = db.query(func.sum(Claim.payout_amount)).filter(
            Claim.worker_id == worker.id,
            Claim.created_at >= week_start,
            Claim.status.in_([ClaimStatus.approved, ClaimStatus.paid]),
        ).scalar() or 0.0

        weekly_income = worker.avg_daily_income * 6
        if weekly_paid >= weekly_income:
            continue  # weekly cap exhausted — no further payouts this policy week

        # Fraud check
        fraud_result = check_fraud(
            worker=worker,
            claim_lat=worker.lat,
            claim_lng=worker.lng,
            trigger_type=event_type,
            db=db
        )

        payout = round(policy.coverage_amount * PAYOUT_RATES.get(event_type, 0.167), 2)
        # Moral hazard cap: no single trigger can pay more than 1.2× a day's income.
        # This ensures the worker is never financially better off by not working.
        daily_income_cap = round(worker.avg_daily_income * 1.2, 2)
        payout = min(payout, daily_income_cap)
        claim_status = ClaimStatus.rejected if fraud_result["is_fraud"] else ClaimStatus.approved

        claim = Claim(
            worker_id=worker.id,
            policy_id=policy.id,
            trigger_type=event_type,
            trigger_value=value,
            trigger_threshold=threshold,
            payout_amount=payout,
            status=claim_status,
            fraud_score=fraud_result["fraud_score"],
            fraud_flags=fraud_result["fraud_flags"],
            approved_at=datetime.utcnow() if claim_status == ClaimStatus.approved else None
        )
        db.add(claim)
        created_claims.append(claim)

    db.commit()
    for c in created_claims:
        db.refresh(c)
    return created_claims
