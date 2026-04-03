"""
Gemini AI Integration
- Generates natural language risk summaries for workers
- Provides AI-powered insights for admin dashboard
- Answers worker queries about their policy
"""
import google.generativeai as genai
from ..config import settings

def _get_model():
    genai.configure(api_key=settings.GEMINI_API_KEY)
    return genai.GenerativeModel("gemini-1.5-flash")

async def generate_risk_summary(risk_data: dict) -> str:
    """Generate a plain-language risk summary for a worker."""
    if not settings.GEMINI_API_KEY:
        return _fallback_risk_summary(risk_data)
    try:
        model = _get_model()
        prompt = f"""
You are an insurance assistant for Indian gig delivery workers.
Write a SHORT (3-4 sentences), friendly risk summary in simple English.

Current conditions:
- City: {risk_data.get('city')}
- Rain: {risk_data.get('rain_mm', 0)} mm/3h (threshold: 15mm)
- AQI: {risk_data.get('aqi', 0)} (threshold: 200)
- Temperature: {risk_data.get('temp_c', 0)}°C
- Curfew active: {risk_data.get('curfew', False)}
- Risk Score: {risk_data.get('risk_score', 0):.0%}
- Weekly Premium: ₹{risk_data.get('weekly_premium', 0)}
- Coverage: ₹{risk_data.get('coverage_amount', 0)}

Tell the worker: current risk level, what could trigger a payout, and reassure them their income is protected.
"""
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        return _fallback_risk_summary(risk_data)

def _fallback_risk_summary(risk_data: dict) -> str:
    risk_pct = int(risk_data.get('risk_score', 0) * 100)
    city = risk_data.get('city', 'your city')
    rain = risk_data.get('rain_mm', 0)
    aqi = risk_data.get('aqi', 0)
    premium = risk_data.get('weekly_premium', 0)
    coverage = risk_data.get('coverage_amount', 0)

    level = "low" if risk_pct < 30 else "moderate" if risk_pct < 60 else "high"
    triggers = []
    if rain >= 15:
        triggers.append("heavy rainfall")
    if aqi >= 200:
        triggers.append("poor air quality")

    trigger_text = " and ".join(triggers) if triggers else "no active disruptions"
    return (
        f"Current risk in {city} is {level} ({risk_pct}%). "
        f"Conditions show {trigger_text}. "
        f"Your weekly premium is ₹{premium:.0f} with ₹{coverage:.0f} income protection. "
        f"If disruptions exceed thresholds, your claim will be processed automatically — no action needed."
    )

async def answer_worker_query(question: str, worker_context: dict) -> str:
    """Answer a worker's question about their policy using Gemini."""
    if not settings.GEMINI_API_KEY:
        return "Please contact support for assistance with your query."
    try:
        model = _get_model()
        prompt = f"""
You are a helpful insurance assistant for Indian gig delivery workers.
Worker context: {worker_context}
Worker question: {question}
Answer in 2-3 sentences, simply and clearly. Focus on income protection insurance only.
"""
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception:
        return "I'm unable to process your query right now. Please try again later."

async def generate_admin_insight(stats: dict) -> str:
    """Generate AI insight for admin dashboard."""
    if not settings.GEMINI_API_KEY:
        return f"Loss ratio is {stats.get('loss_ratio', 0):.1%}. Monitor fraud alerts closely."
    try:
        model = _get_model()
        prompt = f"""
You are an insurance analytics AI. Given these platform stats, provide a 3-sentence business insight:
{stats}
Focus on: loss ratio health, fraud risk, and one actionable recommendation.
"""
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception:
        return f"Platform loss ratio: {stats.get('loss_ratio', 0):.1%}. Review fraud alerts for anomalies."
