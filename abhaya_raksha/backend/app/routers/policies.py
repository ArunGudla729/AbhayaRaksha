import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from ..database import get_db
from ..models import Worker, Policy, PolicyStatus
from ..schemas import PolicyOut
from ..auth import get_current_worker
from ..services.risk_engine import get_risk_for_location

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/policies", tags=["policies"])


def expire_lapsed_policies(db: Session, worker_id: int | None = None) -> int:
    """
    Scan for policies whose end_date has passed but status is still 'active'
    and flip them to 'expired'. Returns the number of policies updated.

    Called automatically on every active-policy lookup so the DB stays
    consistent without needing a separate cron job.

    Args:
        db: SQLAlchemy session.
        worker_id: If provided, only checks policies for that worker.
                   Pass None to scan all workers (bulk expiry).
    """
    q = db.query(Policy).filter(
        Policy.status == PolicyStatus.active,
        Policy.end_date < datetime.utcnow(),
    )
    if worker_id is not None:
        q = q.filter(Policy.worker_id == worker_id)

    lapsed = q.all()
    for policy in lapsed:
        policy.status = PolicyStatus.expired
        logger.info(
            "Policy #%d for worker #%d expired (end_date=%s)",
            policy.id, policy.worker_id, policy.end_date.isoformat()
        )

    if lapsed:
        db.commit()

    return len(lapsed)


@router.post("/activate", response_model=PolicyOut, status_code=201)
async def activate(
    db: Session = Depends(get_db),
    current_worker: Worker = Depends(get_current_worker),
):
    """
    Activate a new weekly income-protection policy (alias for /subscribe).
    Called by the ActivationModal after the worker confirms terms.
    Premium and coverage are calculated dynamically from the ML risk engine.
    Policy window: exactly 7 days from activation.
    """
    return await subscribe(db=db, current_worker=current_worker)


@router.post("/subscribe", response_model=PolicyOut, status_code=201)
async def subscribe(
    db: Session = Depends(get_db),
    current_worker: Worker = Depends(get_current_worker),
):
    """
    Purchase a new weekly income-protection policy.
    Premium and coverage are calculated dynamically from the ML risk engine.
    A worker may only hold one active policy at a time.
    Policy window: exactly 7 days from activation.
    """
    # Expire any lapsed policies first so the duplicate check is accurate
    expire_lapsed_policies(db, worker_id=current_worker.id)

    existing = db.query(Policy).filter(
        Policy.worker_id == current_worker.id,
        Policy.status == PolicyStatus.active,
        Policy.end_date >= datetime.utcnow(),
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="You already have an active policy")

    risk_data = await get_risk_for_location(
        city=current_worker.city,
        zone=current_worker.zone,
        avg_daily_income=current_worker.avg_daily_income,
    )

    policy = Policy(
        worker_id=current_worker.id,
        weekly_premium=risk_data["weekly_premium"],
        coverage_amount=risk_data["coverage_amount"],
        risk_score=risk_data["risk_score"],
        status=PolicyStatus.active,
        underwriting_start_date=datetime.utcnow() + timedelta(days=7),   # cover begins after 7-day wait
        end_date=datetime.utcnow() + timedelta(days=14),                  # 7-day wait + 7-day coverage
    )
    db.add(policy)
    db.commit()
    db.refresh(policy)
    return policy


@router.get("/my", response_model=list[PolicyOut])
def get_my_policies(
    db: Session = Depends(get_db),
    current_worker: Worker = Depends(get_current_worker),
):
    """Return all policies (active, expired, cancelled) for the worker."""
    # Expire any lapsed ones before returning so statuses are accurate
    expire_lapsed_policies(db, worker_id=current_worker.id)
    return db.query(Policy).filter(Policy.worker_id == current_worker.id).all()


@router.get("/active", response_model=PolicyOut)
def get_active_policy(
    db: Session = Depends(get_db),
    current_worker: Worker = Depends(get_current_worker),
):
    """
    Return the worker's current active policy.
    If the policy's end_date has passed, it is immediately transitioned to
    'expired' in the database and a 404 is returned so the frontend shows
    the 'Activate Policy' button rather than a stale active policy.
    """
    # Step 1 — expire any lapsed policies for this worker
    expired_count = expire_lapsed_policies(db, worker_id=current_worker.id)
    if expired_count:
        logger.info(
            "Expired %d lapsed policy/policies for worker #%d on active-policy lookup",
            expired_count, current_worker.id
        )

    # Step 2 — fetch a genuinely active, in-window policy
    policy = db.query(Policy).filter(
        Policy.worker_id == current_worker.id,
        Policy.status == PolicyStatus.active,
        Policy.end_date >= datetime.utcnow(),
    ).first()

    if not policy:
        raise HTTPException(status_code=404, detail="No active policy found")

    return policy
