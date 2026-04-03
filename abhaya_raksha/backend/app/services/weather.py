"""
Smart-Shift Planner — rule-based shift advice from OpenWeather 5-day forecast.
"""
import logging
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)

# IST offset
_IST = timezone(timedelta(hours=5, minutes=30))

# Thresholds for a "good" delivery window
_MAX_RAIN_MM  = 1.0   # mm per 3-hour slot
_MAX_TEMP_C   = 35.0  # °C
_WINDOW_SLOTS = 2     # 2 consecutive 3-hour slots = 6-hour window


def _fmt_time(dt) -> str:
    """Format a datetime to '9:00 AM' style — compatible with Windows and Linux."""
    return dt.strftime("%I:%M %p").lstrip("0")


async def get_shift_advice(lat: float, lon: float, api_key: str) -> str:
    """
    Fetch the OpenWeather 5-day/3-hour forecast for (lat, lon) and find the
    first 6-hour window tomorrow where rain < 1mm AND temp < 35°C.

    Returns a plain-English advice string.
    Raises ValueError with a user-facing message on API errors (e.g. 401).
    """
    if not api_key:
        return _fallback_advice(lat)

    import httpx

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(
                "https://api.openweathermap.org/data/2.5/forecast",
                params={
                    "lat": lat,
                    "lon": lon,
                    "appid": api_key,
                    "units": "metric",
                    "cnt": 16,
                },
            )

        if r.status_code in (401, 403):
            raise ValueError("API_KEY_ACTIVATING")

        r.raise_for_status()
        data = r.json()

    except ValueError:
        raise
    except Exception as exc:
        logger.warning("Smart-Shift forecast fetch failed: %s", exc)
        return _fallback_advice(lat)

    # ── Filter to tomorrow's slots (IST date) ─────────────────────────────────
    tomorrow_ist = (datetime.now(_IST) + timedelta(days=1)).date()

    tomorrow_slots = []
    for slot in data.get("list", []):
        slot_dt = datetime.fromtimestamp(slot["dt"], tz=_IST)
        if slot_dt.date() == tomorrow_ist:
            rain_mm = slot.get("rain", {}).get("3h", 0.0)
            temp_c  = slot["main"]["temp"]
            tomorrow_slots.append({
                "dt":      slot_dt,
                "rain_mm": rain_mm,
                "temp_c":  temp_c,
                "good":    rain_mm < _MAX_RAIN_MM and temp_c < _MAX_TEMP_C,
            })

    if not tomorrow_slots:
        return _fallback_advice(lat)

    # ── Find first run of _WINDOW_SLOTS consecutive good slots ───────────────
    for i in range(len(tomorrow_slots) - _WINDOW_SLOTS + 1):
        window = tomorrow_slots[i : i + _WINDOW_SLOTS]
        if all(s["good"] for s in window):
            start = _fmt_time(window[0]["dt"])
            end   = window[-1]["dt"] + timedelta(hours=3)
            end_s = _fmt_time(end)
            return (
                f"Optimal window tomorrow: {start}–{end_s} IST. "
                f"Rain < 1mm, temp < 35°C — high productivity expected."
            )

    return (
        "Challenging conditions tomorrow. "
        "We suggest shorter shifts and frequent breaks to stay safe."
    )


def _fallback_advice(lat: float) -> str:
    """
    Deterministic mock advice when no API key is configured.
    Uses latitude as a rough proxy for city climate.
    """
    if lat > 25:          # North India (Delhi, Rohini)
        return (
            "Optimal window tomorrow: 7:00 AM–1:00 PM IST. "
            "Morning hours expected to be clear — high productivity expected."
        )
    elif lat > 15:        # Central / West India (Mumbai, Hyderabad)
        return (
            "Challenging conditions tomorrow. "
            "We suggest shorter shifts and frequent breaks to stay safe."
        )
    else:                 # South India (Chennai, Bangalore)
        return (
            "Optimal window tomorrow: 6:00 AM–12:00 PM IST. "
            "Early morning window looks clear — high productivity expected."
        )
