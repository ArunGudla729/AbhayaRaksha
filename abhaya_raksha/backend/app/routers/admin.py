from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from ..database import get_db
from ..models import Worker, Policy, Claim, PolicyStatus, ClaimStatus, DisruptionEvent, RiskLog, GlobalSettings
from ..schemas import AdminStats, SimulationRequest, SimulationResult, ClaimOut
from ..services.claim_engine import trigger_claims_for_event
from ..services.gemini_ai import generate_admin_insight
from ..auth import get_current_admin

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/stats", response_model=AdminStats)
def get_stats(db: Session = Depends(get_db), _: Worker = Depends(get_current_admin)):
    total_workers = db.query(Worker).count()
    total_policies = db.query(Policy).count()
    active_policies = db.query(Policy).filter(Policy.status == PolicyStatus.active).count()
    total_claims = db.query(Claim).count()
    approved_claims = db.query(Claim).filter(
        Claim.status.in_([ClaimStatus.approved, ClaimStatus.paid])
    ).count()
    fraud_alerts = db.query(Claim).filter(Claim.fraud_score >= 0.6).count()

    total_payout = db.query(func.sum(Claim.payout_amount)).filter(
        Claim.status.in_([ClaimStatus.approved, ClaimStatus.paid])
    ).scalar() or 0.0

    total_premium = db.query(func.sum(Policy.weekly_premium)).scalar() or 0.0
    loss_ratio = round(total_payout / total_premium, 4) if total_premium > 0 else 0.0

    return AdminStats(
        total_workers=total_workers,
        total_policies=total_policies,
        active_policies=active_policies,
        total_claims=total_claims,
        approved_claims=approved_claims,
        total_payout=total_payout,
        fraud_alerts=fraud_alerts,
        loss_ratio=loss_ratio
    )

@router.get("/stats/insight")
async def get_ai_insight(db: Session = Depends(get_db), _: Worker = Depends(get_current_admin)):
    stats = get_stats(db)
    insight = await generate_admin_insight(stats.model_dump())
    return {"insight": insight}

@router.get("/workers")
def list_workers(db: Session = Depends(get_db), _: Worker = Depends(get_current_admin)):
    workers = db.query(Worker).all()
    return [{"id": w.id, "name": w.name, "city": w.city, "zone": w.zone,
             "worker_type": w.worker_type, "avg_daily_income": w.avg_daily_income} for w in workers]

@router.get("/claims")
def list_all_claims(
    status: str = Query(None),
    db: Session = Depends(get_db),
    _: Worker = Depends(get_current_admin)
):
    q = db.query(Claim)
    if status:
        q = q.filter(Claim.status == status)
    return q.order_by(Claim.created_at.desc()).limit(100).all()

@router.get("/fraud-alerts")
def get_fraud_alerts(db: Session = Depends(get_db), _: Worker = Depends(get_current_admin)):
    return db.query(Claim).filter(Claim.fraud_score >= 0.4).order_by(
        Claim.fraud_score.desc()
    ).limit(50).all()

@router.get("/disruptions")
def get_disruptions(db: Session = Depends(get_db), _: Worker = Depends(get_current_admin)):
    return db.query(DisruptionEvent).order_by(
        DisruptionEvent.recorded_at.desc()
    ).limit(50).all()

@router.get("/risk-heatmap")
def get_risk_heatmap(db: Session = Depends(get_db), _: Worker = Depends(get_current_admin)):
    """Aggregate risk scores by city for heatmap."""
    results = db.query(
        RiskLog.city,
        func.avg(RiskLog.risk_score).label("avg_risk"),
        func.count(RiskLog.id).label("data_points")
    ).group_by(RiskLog.city).all()
    return [{"city": r.city, "avg_risk": round(r.avg_risk, 4), "data_points": r.data_points}
            for r in results]

@router.post("/simulate", response_model=SimulationResult)
def simulate_disruption(req: SimulationRequest, db: Session = Depends(get_db), _: Worker = Depends(get_current_admin)):
    """
    Simulate a disruption event and trigger parametric claims.
    Also writes a RiskLog entry so the heatmap reflects simulated events immediately.
    """
    import logging
    from ..services.claim_engine import THRESHOLDS
    from ..services.risk_engine import compute_risk_score

    logger = logging.getLogger(__name__)

    threshold = THRESHOLDS.get(req.event_type, 0)
    triggered = req.value >= threshold

    claims = []
    if triggered:
        claims = trigger_claims_for_event(
            city=req.city,
            zone=req.zone,
            event_type=req.event_type,
            value=req.value,
            db=db
        )

    # ── Write RiskLog so heatmap shows data after simulation ──────────────────
    # Map the simulated event value to the correct weather field; use neutral
    # defaults for the other fields so the risk score reflects the event type.
    rain_mm = req.value if req.event_type == "rain"  else 4.0
    aqi     = req.value if req.event_type == "aqi"   else 100.0
    temp_c  = req.value if req.event_type == "heat"  else 30.0
    curfew  = req.event_type in ("curfew", "flood")

    try:
        risk_score = compute_risk_score(rain_mm=rain_mm, aqi=aqi, temp_c=temp_c, curfew=curfew)
        log = RiskLog(
            city=req.city,
            zone=req.zone,
            risk_score=risk_score,
            rain_mm=rain_mm,
            aqi=aqi,
            temp_c=temp_c,
            curfew=curfew,
        )
        db.add(log)
        db.commit()
    except Exception as exc:
        logger.warning("Failed to write RiskLog for simulation %s/%s: %s", req.city, req.event_type, exc)
        db.rollback()

    total_payout = sum(c.payout_amount for c in claims if c.status == ClaimStatus.approved)

    return SimulationResult(
        event_type=req.event_type,
        value=req.value,
        threshold=threshold,
        triggered=triggered,
        affected_workers=len(claims),
        total_payout=total_payout,
        claims_created=[ClaimOut.model_validate(c) for c in claims]
    )

@router.get("/system-health")
def get_system_health(db: Session = Depends(get_db), _: Worker = Depends(get_current_admin)):
    """
    Actuarial health metrics for the System Health panel.

    BCR (Burning Cost Rate) = total_claims_paid / total_premiums_collected
    Loss Ratio              = same value expressed as a percentage
    Enrollment Suspended    = True when loss_ratio > 85%
    """
    total_premium = db.query(func.sum(Policy.weekly_premium)).scalar() or 0.0
    total_payout  = db.query(func.sum(Claim.payout_amount)).filter(
        Claim.status.in_([ClaimStatus.approved, ClaimStatus.paid])
    ).scalar() or 0.0

    bcr         = round(total_payout / total_premium, 4) if total_premium > 0 else 0.0
    loss_ratio  = round(bcr * 100, 2)          # percentage form
    enrollment_suspended = loss_ratio > 85.0

    return {
        "total_premiums_collected": round(total_premium, 2),
        "total_claims_paid":        round(total_payout, 2),
        "bcr":                      bcr,
        "loss_ratio_pct":           loss_ratio,
        "enrollment_suspended":     enrollment_suspended,
    }


@router.get("/systemic-pause")
def get_systemic_pause(db: Session = Depends(get_db), _: Worker = Depends(get_current_admin)):
    """Return the current state of the systemic pause kill-switch."""
    settings = db.query(GlobalSettings).filter(GlobalSettings.id == 1).first()
    is_paused = settings.is_systemic_pause if settings else False
    return {"is_systemic_pause": is_paused}


@router.post("/toggle-pause")
def toggle_systemic_pause(db: Session = Depends(get_db), _: Worker = Depends(get_current_admin)):
    """
    Flip the systemic pause kill-switch.
    When True, all automated parametric payouts are suspended platform-wide.
    Use ONLY during declared Force Majeure events (war, pandemic, nuclear hazard).
    """
    import logging
    logger = logging.getLogger(__name__)

    settings = db.query(GlobalSettings).filter(GlobalSettings.id == 1).first()
    if not settings:
        # First call — create the singleton row
        settings = GlobalSettings(id=1, is_systemic_pause=True)
        db.add(settings)
    else:
        settings.is_systemic_pause = not settings.is_systemic_pause

    db.commit()
    db.refresh(settings)

    state = "ACTIVATED" if settings.is_systemic_pause else "DEACTIVATED"
    logger.warning("SYSTEMIC PAUSE %s by admin.", state)

    return {
        "is_systemic_pause": settings.is_systemic_pause,
        "message": f"Systemic pause {state}. All parametric payouts are {'suspended' if settings.is_systemic_pause else 'resumed'}."
    }


@router.get("/analytics/weekly")
def weekly_analytics(db: Session = Depends(get_db), _: Worker = Depends(get_current_admin)):
    """Weekly risk trends and claim frequency."""
    from sqlalchemy import text
    from datetime import datetime, timedelta

    weeks = []
    for i in range(4):
        week_end = datetime.utcnow() - timedelta(weeks=i)
        week_start = week_end - timedelta(weeks=1)
        claims_count = db.query(Claim).filter(
            Claim.created_at >= week_start,
            Claim.created_at < week_end
        ).count()
        payout = db.query(func.sum(Claim.payout_amount)).filter(
            Claim.created_at >= week_start,
            Claim.created_at < week_end,
            Claim.status.in_([ClaimStatus.approved, ClaimStatus.paid])
        ).scalar() or 0.0
        weeks.append({
            "week": f"Week -{i}",
            "start": week_start.isoformat(),
            "end": week_end.isoformat(),
            "claims": claims_count,
            "payout": payout
        })
    return weeks
