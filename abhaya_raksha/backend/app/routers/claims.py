import random
import string
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import Worker, Claim, ClaimStatus
from ..schemas import ClaimOut
from ..auth import get_current_worker
from ..services.fraud_detector import update_worker_position

router = APIRouter(prefix="/api/claims", tags=["claims"])


def _generate_txn_id(claim_id: int) -> str:
    """Generate a mock UPI transaction ID in the format UKO-UPI-XXXXXXX."""
    suffix = ''.join(random.choices(string.digits, k=6)) + random.choice(string.ascii_uppercase)
    return f"UKO-UPI-{suffix}"

@router.get("/my", response_model=list[ClaimOut])
def get_my_claims(
    db: Session = Depends(get_db),
    current_worker: Worker = Depends(get_current_worker)
):
    return db.query(Claim).filter(
        Claim.worker_id == current_worker.id
    ).order_by(Claim.created_at.desc()).all()

@router.get("/{claim_id}", response_model=ClaimOut)
def get_claim(
    claim_id: int,
    db: Session = Depends(get_db),
    current_worker: Worker = Depends(get_current_worker)
):
    claim = db.query(Claim).filter(
        Claim.id == claim_id,
        Claim.worker_id == current_worker.id
    ).first()
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    return claim

@router.post("/{claim_id}/withdraw")
def withdraw_to_upi(
    claim_id: int,
    db: Session = Depends(get_db),
    current_worker: Worker = Depends(get_current_worker)
):
    """
    Instant payout workflow — transitions an approved claim to paid via mock UPI gateway.
    Generates a realistic transaction ID and persists it in fraud_flags for audit trail.
    """
    claim = db.query(Claim).filter(
        Claim.id == claim_id,
        Claim.worker_id == current_worker.id
    ).first()
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    if claim.status != ClaimStatus.approved:
        raise HTTPException(status_code=400, detail=f"Claim is {claim.status}, not approved")

    # Generate mock UPI transaction ID
    txn_id = _generate_txn_id(claim.id)

    # Transition to paid and persist transaction ID
    claim.status = ClaimStatus.paid
    # Append to fraud_flags (semicolon-separated) so existing flags aren't lost
    if claim.fraud_flags:
        claim.fraud_flags += f"; TXN:{txn_id}"
    else:
        claim.fraud_flags = f"TXN:{txn_id}"
    
    db.commit()
    db.refresh(claim)

    # Update last known position — withdrawal confirms worker is active
    update_worker_position(current_worker, current_worker.lat, current_worker.lng, db)

    return {
        "success": True,
        "message": "Transfer successful",
        "transaction_id": txn_id,
        "amount": claim.payout_amount,
        "method": "UPI",
        "claim": ClaimOut.model_validate(claim)
    }


@router.post("/{claim_id}/payout")
def simulate_payout(
    claim_id: int,
    db: Session = Depends(get_db),
    current_worker: Worker = Depends(get_current_worker)
):
    """Simulate instant payout for an approved claim."""
    claim = db.query(Claim).filter(
        Claim.id == claim_id,
        Claim.worker_id == current_worker.id
    ).first()
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    if claim.status != ClaimStatus.approved:
        raise HTTPException(status_code=400, detail=f"Claim is {claim.status}, not approved")

    claim.status = ClaimStatus.paid
    db.commit()
    db.refresh(claim)

    # Update last known position — payout endpoint confirms worker is active
    update_worker_position(current_worker, current_worker.lat, current_worker.lng, db)

    return {
        "message": "Payout successful",
        "transaction_id": f"TXN{claim.id:08d}",
        "amount": claim.payout_amount,
        "method": "UPI / Bank Transfer (simulated)",
        "claim": ClaimOut.model_validate(claim)
    }
