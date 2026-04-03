"""
Risk Prediction Engine
- Fetches real weather data from OpenWeather API
- Computes risk score using a trained ML model (GradientBoostingClassifier)
  with rule-based weighted formula as fallback
- Calculates dynamic weekly premium
"""
import os
import logging
import joblib
import numpy as np
from datetime import datetime
from ..config import settings

logger = logging.getLogger(__name__)

# ── Model path ────────────────────────────────────────────────────────────────
_MODEL_PATH = os.path.join(os.path.dirname(__file__), "../../../ml/risk_model.joblib")
_risk_model = None

def _get_risk_model():
    """Lazy-load the risk model once. Returns None if file is missing."""
    global _risk_model
    if _risk_model is None:
        path = os.path.abspath(_MODEL_PATH)
        if os.path.exists(path):
            _risk_model = joblib.load(path)
            logger.info("risk_model.joblib loaded from %s", path)
        else:
            logger.warning("risk_model.joblib not found at %s — using rule-based fallback", path)
    return _risk_model

# ── Thresholds ────────────────────────────────────────────────────────────────
RAIN_THRESHOLD_MM = 15.0
AQI_THRESHOLD = 200
TEMP_HEAT_THRESHOLD = 42.0

# ── Micro-Insurance Premium config ───────────────────────────────────────────
# Formula: Premium = trigger_prob × daily_income × exposure_days
# At trigger_prob=0.008, daily_income=850, exposure_days=5 → ₹34/week
# Scales naturally with the worker's actual avg_daily_income.
TRIGGER_PROBABILITY = 0.008   # parametric rain/disruption trigger probability
EXPOSURE_DAYS       = 5       # working days exposed per week
COVERAGE_MULTIPLIER = 1.0     # coverage = 1× weekly income (income replacement only)

async def fetch_weather(city: str) -> dict:
    """
    Fetch current weather from OpenWeather using the city name.
    Falls back to deterministic mock on any error or missing key.
    Temperature is rounded to 1 decimal place.
    AQI uses a safe city-based static value (avoids a second API call).
    """
    if not settings.OPENWEATHER_API_KEY:
        return _mock_weather(city)
    try:
        import httpx
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(
                "https://api.openweathermap.org/data/2.5/weather",
                params={
                    "q": city + ",IN",
                    "appid": settings.OPENWEATHER_API_KEY,
                    "units": "metric",   # temp already in °C — no Kelvin conversion needed
                },
            )
            if r.status_code in (401, 403):
                logger.warning("OpenWeather API key issue (%d) — using mock", r.status_code)
                return _mock_weather(city)
            r.raise_for_status()
            data = r.json()
            # rain.1h preferred; fall back to rain.3h; 0.0 if no rain key (clear/cloudy)
            rain_mm = data.get("rain", {}).get("1h", data.get("rain", {}).get("3h", 0.0))
            temp_c  = round(data["main"]["temp"], 1)
            # AQI: static safe mock per city — avoids a second API call that could
            # hit rate limits during a live demo. Values are climatologically realistic.
            aqi = _static_aqi(city)
            return {"rain_mm": rain_mm, "temp_c": temp_c, "aqi": aqi}
    except Exception as exc:
        logger.warning("fetch_weather(%s) failed: %s — using mock", city, exc)
        return _mock_weather(city)


async def fetch_weather_by_coords(lat: float, lon: float) -> dict:
    """
    Fetch current weather by lat/lon — used by the Smart-Shift planner and
    any future location-aware features. Same fallback behaviour as fetch_weather.
    """
    if not settings.OPENWEATHER_API_KEY:
        return {"rain_mm": 4.0, "temp_c": 30.0, "aqi": 100.0}
    try:
        import httpx
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(
                "https://api.openweathermap.org/data/2.5/weather",
                params={
                    "lat": lat,
                    "lon": lon,
                    "appid": settings.OPENWEATHER_API_KEY,
                    "units": "metric",
                },
            )
            if r.status_code in (401, 403):
                return {"rain_mm": 4.0, "temp_c": 30.0, "aqi": 100.0}
            r.raise_for_status()
            data = r.json()
            rain_mm = data.get("rain", {}).get("1h", data.get("rain", {}).get("3h", 0.0))
            temp_c  = round(data["main"]["temp"], 1)
            return {"rain_mm": rain_mm, "temp_c": temp_c, "aqi": 100.0}
    except Exception as exc:
        logger.warning("fetch_weather_by_coords(%.4f,%.4f) failed: %s", lat, lon, exc)
        return {"rain_mm": 4.0, "temp_c": 30.0, "aqi": 100.0}


def _static_aqi(city: str) -> float:
    """
    Climatologically realistic static AQI per city.
    Avoids a second API call while keeping values meaningful for risk scoring.
    """
    mapping = {
        "mumbai":    120.0,
        "delhi":     280.0,
        "bangalore": 90.0,
        "bengaluru": 90.0,
        "chennai":   110.0,
        "hyderabad": 130.0,
    }
    return mapping.get(city.lower(), 100.0)

def _mock_weather(city: str) -> dict:
    """Deterministic mock based on city name for demo."""
    city_lower = city.lower()
    if "mumbai" in city_lower:
        return {"rain_mm": 18.0, "temp_c": 29.0, "aqi": 120.0}
    elif "delhi" in city_lower:
        return {"rain_mm": 2.0, "temp_c": 38.0, "aqi": 280.0}
    elif "bangalore" in city_lower or "bengaluru" in city_lower:
        return {"rain_mm": 8.0, "temp_c": 26.0, "aqi": 90.0}
    elif "chennai" in city_lower:
        return {"rain_mm": 5.0, "temp_c": 35.0, "aqi": 110.0}
    elif "hyderabad" in city_lower:
        return {"rain_mm": 3.0, "temp_c": 33.0, "aqi": 130.0}
    return {"rain_mm": 4.0, "temp_c": 30.0, "aqi": 100.0}

def compute_risk_score(rain_mm: float, aqi: float, temp_c: float, curfew: bool = False) -> float:
    """
    Compute risk score (0.0–1.0) using the trained GradientBoostingClassifier.
    Falls back to a weighted rule-based formula if the model is unavailable.

    ML features: [rain_mm, aqi, temp_c, hour, day_of_week, is_monsoon]
    Curfew penalty: +0.3 added on top of ML score (capped at 1.0).
    """
    now = datetime.utcnow()
    hour = now.hour
    day_of_week = now.weekday()          # 0 = Monday … 6 = Sunday
    is_monsoon = 1 if now.month in (6, 7, 8, 9) else 0

    model = _get_risk_model()
    if model is not None:
        import pandas as pd
        features = pd.DataFrame([[rain_mm, aqi, temp_c, hour, day_of_week, is_monsoon]],
                                columns=["rain_mm", "aqi", "temp_c", "hour", "day_of_week", "is_monsoon"])
        ml_prob = float(model.predict_proba(features)[0][1])  # P(disruption)
        score = ml_prob + (0.3 if curfew else 0.0)
        return round(min(score, 1.0), 4)

    # ── Rule-based fallback ───────────────────────────────────────────────────
    rain_risk = min(rain_mm / 50.0, 1.0)
    aqi_risk = min(max(aqi - 100, 0) / 300.0, 1.0)
    heat_risk = min(max(temp_c - 35, 0) / 15.0, 1.0)
    curfew_risk = 1.0 if curfew else 0.0
    score = (
        0.40 * rain_risk +
        0.30 * aqi_risk +
        0.20 * heat_risk +
        0.10 * curfew_risk
    )
    return round(min(score, 1.0), 4)

def calculate_premium(risk_score: float, avg_daily_income: float) -> dict:
    """
    Micro-insurance weekly premium using the parametric formula:
        Premium = trigger_prob × daily_income × exposure_days

    At the reference income of ₹850/day:
        0.008 × 850 × 5 = ₹34/week  (target: ₹30–₹45)

    The risk_score (0–1) scales the trigger probability so higher-risk
    cities/conditions attract a slightly higher premium, capped at 2×
    the base to keep it affordable.

    Coverage = 1× weekly income (income replacement, not a windfall).
    """
    # Scale trigger probability by risk: base at risk=0, up to 2× at risk=1
    effective_trigger_prob = TRIGGER_PROBABILITY * (1.0 + risk_score)
    weekly_premium  = round(effective_trigger_prob * avg_daily_income * EXPOSURE_DAYS, 2)
    weekly_income   = avg_daily_income * EXPOSURE_DAYS
    coverage_amount = round(weekly_income * COVERAGE_MULTIPLIER, 2)
    return {
        "weekly_premium":  weekly_premium,
        "coverage_amount": coverage_amount,
        "premium_rate":    round(effective_trigger_prob, 6),
    }

async def get_risk_for_location(
    city: str, zone: str, avg_daily_income: float, curfew: bool = False
) -> dict:
    weather = await fetch_weather(city)
    risk_score = compute_risk_score(
        rain_mm=weather["rain_mm"],
        aqi=weather["aqi"],
        temp_c=weather["temp_c"],
        curfew=curfew,
    )
    pricing = calculate_premium(risk_score, avg_daily_income)
    return {
        "city": city,
        "zone": zone,
        "risk_score": risk_score,
        **weather,
        "curfew": curfew,
        **pricing,
    }
