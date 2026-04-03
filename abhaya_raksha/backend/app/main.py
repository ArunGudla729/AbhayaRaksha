import logging
from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from .database import engine, Base, SessionLocal, get_db
from .models import GlobalSettings, Worker
from .auth import get_current_worker
from .routers import auth, workers, policies, claims, admin

logger = logging.getLogger(__name__)

# Create all tables on startup
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="AbhayaRaksha API",
    description="AI-powered parametric income insurance for India's gig delivery workers",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(workers.router)
app.include_router(policies.router)
app.include_router(claims.router)
app.include_router(admin.router)

# ── Parametric Heart — Background Scheduler ───────────────────────────────────
# Polls weather every 15 minutes for all key cities and auto-triggers claims
# when parametric thresholds are breached. This is the zero-touch core of the
# platform — no admin or worker action required.

MONITORED_CITIES = ["Mumbai", "Delhi", "Bangalore", "Chennai", "Hyderabad"]

# Map weather keys to claim engine event types
_WEATHER_EVENT_MAP = {
    "rain_mm": "rain",
    "aqi":     "aqi",
    "temp_c":  "heat",
}

async def poll_and_trigger():
    """
    Fetch live weather for each monitored city and fire parametric claims
    for any threshold breach. Runs every 15 minutes via APScheduler.
    Each city gets its own DB session that is always closed, even on error.
    """
    from .services.risk_engine import fetch_weather
    from .services.claim_engine import trigger_claims_for_event, THRESHOLDS, _get_rain_threshold

    for city in MONITORED_CITIES:
        db = SessionLocal()
        try:
            weather = await fetch_weather(city)
            logger.info(
                "[scheduler] %s — rain=%.1fmm  aqi=%.0f  temp=%.1f°C",
                city, weather["rain_mm"], weather["aqi"], weather["temp_c"]
            )

            for weather_key, event_type in _WEATHER_EVENT_MAP.items():
                value = weather.get(weather_key, 0.0)
                # BUG-H04 fix: use city-aware rain threshold, not the flat global default
                threshold = _get_rain_threshold(city) if event_type == "rain" else THRESHOLDS.get(event_type, 0)
                if value >= threshold:
                    triggered = trigger_claims_for_event(
                        city=city,
                        zone="",          # city-wide event
                        event_type=event_type,
                        value=value,
                        db=db,
                    )
                    if triggered:
                        logger.info(
                            "[scheduler] %s %s=%.2f breached threshold %.2f → %d claims created",
                            city, event_type, value, threshold, len(triggered)
                        )
        except Exception as exc:
            # Log and continue — never let one city failure stop the whole poll
            logger.error("[scheduler] Error processing %s: %s", city, exc)
        finally:
            db.close()

_scheduler = AsyncIOScheduler()

@app.on_event("startup")
async def start_scheduler():
    _scheduler.add_job(
        poll_and_trigger,
        trigger="interval",
        minutes=15,
        id="parametric_heart",
        replace_existing=True,
    )
    _scheduler.start()
    logger.info("[scheduler] Parametric Heart started — polling every 15 minutes")

@app.on_event("shutdown")
async def stop_scheduler():
    _scheduler.shutdown(wait=False)
    logger.info("[scheduler] Parametric Heart stopped")

# ── Health & Root ─────────────────────────────────────────────────────────────

@app.get("/api/system/status")
def system_status(
    db: Session = Depends(get_db),
    _: Worker = Depends(get_current_worker),   # any logged-in worker or admin
):
    """
    Public (worker-accessible) read of platform-wide settings.
    Returns the systemic pause state so the worker dashboard can show the
    emergency banner without needing admin credentials.
    """
    settings = db.query(GlobalSettings).filter(GlobalSettings.id == 1).first()
    return {
        "is_systemic_pause": settings.is_systemic_pause if settings else False,
    }


@app.get("/")
def root():
    return {
        "name": "AbhayaRaksha",
        "tagline": "Parametric income insurance for gig workers",
        "docs": "/docs",
        "scheduler": "running" if _scheduler.running else "stopped",
    }

@app.get("/health")
def health():
    return {
        "status": "ok",
        "scheduler": "running" if _scheduler.running else "stopped",
    }
