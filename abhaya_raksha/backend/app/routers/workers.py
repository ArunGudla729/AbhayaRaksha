import logging
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import Worker, RiskLog
from ..schemas import WorkerOut, RiskResponse
from ..auth import get_current_worker
from ..services.risk_engine import get_risk_for_location
from ..services.gemini_ai import generate_risk_summary
from ..services.fraud_detector import update_worker_position
from ..services.weather import get_shift_advice
from ..config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/workers", tags=["workers"])


@router.get("/me", response_model=WorkerOut)
def get_me(current_worker: Worker = Depends(get_current_worker)):
    return current_worker


@router.get("/risk", response_model=RiskResponse)
async def get_my_risk(
    curfew: bool = False,
    db: Session = Depends(get_db),
    current_worker: Worker = Depends(get_current_worker),
):
    """
    Return the live risk score and dynamic weekly premium for the logged-in worker.
    Also persists a RiskLog entry so the Admin heatmap has real data points.
    """
    risk_data = await get_risk_for_location(
        city=current_worker.city,
        zone=current_worker.zone,
        avg_daily_income=current_worker.avg_daily_income,
        curfew=curfew,
    )

    # ── Persist to RiskLog for Admin heatmap ──────────────────────────────────
    try:
        log = RiskLog(
            city=risk_data["city"],
            zone=risk_data["zone"],
            risk_score=risk_data["risk_score"],
            rain_mm=risk_data["rain_mm"],
            aqi=risk_data["aqi"],
            temp_c=risk_data["temp_c"],
            curfew=risk_data["curfew"],
        )
        db.add(log)
        db.commit()
    except Exception as exc:
        logger.warning("Failed to write RiskLog for %s: %s", current_worker.city, exc)
        db.rollback()

    # ── Update last known position for teleportation fraud detection ──────────
    update_worker_position(current_worker, current_worker.lat, current_worker.lng, db)

    return risk_data


@router.get("/shift-advice")
async def get_shift_advice_endpoint(
    current_worker: Worker = Depends(get_current_worker),
):
    """
    Return a Smart-Shift Planner recommendation for tomorrow based on the
    OpenWeather 5-day forecast for the worker's registered coordinates.
    """
    try:
        advice = await get_shift_advice(
            lat=current_worker.lat,
            lon=current_worker.lng,
            api_key=settings.OPENWEATHER_API_KEY,
        )
    except ValueError as exc:
        if str(exc) == "API_KEY_ACTIVATING":
            advice = (
                "Smart-Shift is syncing with local weather stations... "
                "Check back shortly."
            )
        else:
            advice = "Shift advice temporarily unavailable."
    except Exception as exc:
        logger.warning("Shift advice error for worker #%d: %s", current_worker.id, exc)
        advice = "Shift advice temporarily unavailable."

    return {"shift_advice": advice}


@router.get("/risk/summary")
async def get_risk_summary(
    curfew: bool = False,
    current_worker: Worker = Depends(get_current_worker),
):
    """Return an AI-generated plain-language risk summary for the worker."""
    risk_data = await get_risk_for_location(
        city=current_worker.city,
        zone=current_worker.zone,
        avg_daily_income=current_worker.avg_daily_income,
        curfew=curfew,
    )
    summary = await generate_risk_summary(risk_data)
    return {"summary": summary, "risk_data": risk_data}
