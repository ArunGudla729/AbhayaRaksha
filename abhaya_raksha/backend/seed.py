"""
AbhayaRaksha Demo Seed Script
==========================
Resets the database and populates it with a realistic "Success Story" for demos.

Run from backend/ directory:
    python seed.py

What it creates:
  - 5 gig workers across 3 cities (food, ecommerce, grocery)
  - 1 admin user
  - Active 7-day policies for all workers (ML-calculated premiums)
  - 2 paid historical claims for Ravi (rain + AQI, 3 days ago)
  - 1 approved claim for Priya (AQI spike, 2 days ago)
  - 15 RiskLog entries across 5 cities for heatmap visibility
"""
import sys
import os
import warnings
warnings.filterwarnings("ignore")

sys.path.insert(0, os.path.dirname(__file__))

from datetime import datetime, timedelta
from app.database import SessionLocal, engine
from app.models import Base, Worker, Policy, Claim, RiskLog, PolicyStatus, ClaimStatus, GlobalSettings
from app.auth import hash_password
from app.services.risk_engine import compute_risk_score, calculate_premium
from app.services.claim_engine import THRESHOLDS, PAYOUT_RATES

# ── Reset database ─────────────────────────────────────────────────────────────
print("Resetting database...")
Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)
print("  Tables recreated.\n")

db = SessionLocal()

# ── Worker definitions ─────────────────────────────────────────────────────────
WORKERS = [
    {
        "name": "Ravi Kumar",
        "email": "ravi@demo.com",
        "phone": "9876543210",
        "worker_type": "food_delivery",
        "city": "Mumbai",
        "zone": "Andheri West",
        "lat": 19.1136,
        "lng": 72.8697,
        "avg_daily_income": 900.0,
    },
    {
        "name": "Bhargav Reddy",
        "email": "bhargav@demo.com",
        "phone": "9876543215",
        "worker_type": "food_delivery",
        "city": "Hyderabad",
        "zone": "Banjara Hills",
        "lat": 17.4126,
        "lng": 78.4482,
        "avg_daily_income": 850.0,
    },
    {
        "name": "Suresh Raina",
        "email": "suresh@demo.com",
        "phone": "9876543211",
        "worker_type": "ecommerce",
        "city": "Delhi",
        "zone": "Rohini",
        "lat": 28.7041,
        "lng": 77.1025,
        "avg_daily_income": 780.0,
    },
    {
        "name": "Anjali Gupta",
        "email": "anjali@demo.com",
        "phone": "9876543212",
        "worker_type": "grocery",
        "city": "Bangalore",
        "zone": "Indiranagar",
        "lat": 12.9784,
        "lng": 77.6408,
        "avg_daily_income": 820.0,
    },
    {
        "name": "Priya Sharma",
        "email": "priya@demo.com",
        "phone": "9876543213",
        "worker_type": "grocery",
        "city": "Delhi",
        "zone": "Connaught Place",
        "lat": 28.6315,
        "lng": 77.2167,
        "avg_daily_income": 750.0,
    },
    {
        "name": "Meena Devi",
        "email": "meena@demo.com",
        "phone": "9876543214",
        "worker_type": "food_delivery",
        "city": "Chennai",
        "zone": "T Nagar",
        "lat": 13.0418,
        "lng": 80.2341,
        "avg_daily_income": 700.0,
    },
]

# ── City weather snapshots (mock values matching risk_engine mocks) ────────────
CITY_WEATHER = {
    "Mumbai":    {"rain_mm": 18.0, "aqi": 120.0, "temp_c": 29.0},
    "Delhi":     {"rain_mm":  2.0, "aqi": 280.0, "temp_c": 38.0},
    "Bangalore": {"rain_mm":  8.0, "aqi":  90.0, "temp_c": 26.0},
    "Chennai":   {"rain_mm":  5.0, "aqi": 110.0, "temp_c": 35.0},
    "Hyderabad": {"rain_mm":  3.0, "aqi": 130.0, "temp_c": 33.0},
}

# ── Task 1: Create workers ─────────────────────────────────────────────────────
print("Creating workers...")
worker_objects = {}
for w in WORKERS:
    worker = Worker(**w, hashed_password=hash_password("demo1234"))
    db.add(worker)
    db.flush()
    worker_objects[w["email"]] = worker
    print(f"  {worker.name} ({worker.city} / {worker.zone})")

# ── Task 2: Active policies with ML-calculated premiums ───────────────────────
print("\nCreating active policies...")
policy_objects = {}
for email, worker in worker_objects.items():
    weather = CITY_WEATHER.get(worker.city, {"rain_mm": 4.0, "aqi": 100.0, "temp_c": 30.0})
    risk_score = compute_risk_score(
        rain_mm=weather["rain_mm"],
        aqi=weather["aqi"],
        temp_c=weather["temp_c"],
        curfew=False,
    )
    pricing = calculate_premium(risk_score, worker.avg_daily_income)
    policy = Policy(
        worker_id=worker.id,
        weekly_premium=pricing["weekly_premium"],
        coverage_amount=pricing["coverage_amount"],
        risk_score=risk_score,
        status=PolicyStatus.active,
        start_date=datetime.utcnow() - timedelta(days=1),
        end_date=datetime.utcnow() + timedelta(days=6),
        underwriting_start_date=datetime.utcnow() - timedelta(days=1),  # waiting period already passed
    )
    db.add(policy)
    db.flush()
    policy_objects[email] = policy
    print(
        f"  {worker.name}: risk={risk_score:.3f}  "
        f"premium=₹{pricing['weekly_premium']:.0f}/week  "
        f"coverage=₹{pricing['coverage_amount']:.0f}"
    )

# ── Task 3: Success Story — paid claims for Ravi (3 days ago) ─────────────────
print("\nCreating historical claims for Ravi Kumar...")
ravi = worker_objects["ravi@demo.com"]
ravi_policy = policy_objects["ravi@demo.com"]

# Event 1 — Heavy Rain (28mm, threshold 15mm) — 3 days ago
rain_payout = round(ravi_policy.coverage_amount * PAYOUT_RATES["rain"], 2)
claim_rain = Claim(
    worker_id=ravi.id,
    policy_id=ravi_policy.id,
    trigger_type="rain",
    trigger_value=28.0,
    trigger_threshold=THRESHOLDS["rain"],
    payout_amount=rain_payout,
    status=ClaimStatus.paid,
    fraud_score=0.0,
    fraud_flags="",
    created_at=datetime.utcnow() - timedelta(days=3, hours=2),
    approved_at=datetime.utcnow() - timedelta(days=3, hours=1),
)
db.add(claim_rain)
db.flush()
# Patch a realistic transaction ID into fraud_flags field (no dedicated txn column)
claim_rain.fraud_flags = f"TXN_MUM_{claim_rain.id:05d}"
print(f"  Rain claim: ₹{rain_payout:.0f} paid  (TXN_MUM_{claim_rain.id:05d})")

# Event 2 — AQI Spike (350, threshold 200) — 3 days ago, different hour
aqi_payout = round(ravi_policy.coverage_amount * PAYOUT_RATES["aqi"], 2)
claim_aqi = Claim(
    worker_id=ravi.id,
    policy_id=ravi_policy.id,
    trigger_type="aqi",
    trigger_value=350.0,
    trigger_threshold=THRESHOLDS["aqi"],
    payout_amount=aqi_payout,
    status=ClaimStatus.paid,
    fraud_score=0.0,
    fraud_flags="",
    created_at=datetime.utcnow() - timedelta(days=3, hours=5),
    approved_at=datetime.utcnow() - timedelta(days=3, hours=4),
)
db.add(claim_aqi)
db.flush()
claim_aqi.fraud_flags = f"TXN_MUM_{claim_aqi.id:05d}"
print(f"  AQI claim:  ₹{aqi_payout:.0f} paid  (TXN_MUM_{claim_aqi.id:05d})")
print(f"  Total income protected for Ravi: ₹{rain_payout + aqi_payout:.0f}")

# Approved (not yet collected) claim for Priya — AQI spike in Delhi, 2 days ago
print("\nCreating pending payout claim for Priya Sharma...")
priya = worker_objects["priya@demo.com"]
priya_policy = policy_objects["priya@demo.com"]
priya_aqi_payout = round(priya_policy.coverage_amount * PAYOUT_RATES["aqi"], 2)
claim_priya = Claim(
    worker_id=priya.id,
    policy_id=priya_policy.id,
    trigger_type="aqi",
    trigger_value=310.0,
    trigger_threshold=THRESHOLDS["aqi"],
    payout_amount=priya_aqi_payout,
    status=ClaimStatus.approved,
    fraud_score=0.0,
    fraud_flags="",
    created_at=datetime.utcnow() - timedelta(days=2, hours=3),
    approved_at=datetime.utcnow() - timedelta(days=2, hours=2),
)
db.add(claim_priya)
print(f"  Priya AQI claim: ₹{priya_aqi_payout:.0f} approved (ready to collect)")

# ── Task 4: RiskLog entries for heatmap ───────────────────────────────────────
print("\nPopulating RiskLog heatmap data...")

RISK_LOG_DATA = [
    # Mumbai — high rain risk
    ("Mumbai", "Andheri West",   18.0, 120.0, 29.0, False),
    ("Mumbai", "Bandra",         22.0, 115.0, 28.5, False),
    ("Mumbai", "Dadar",          16.0, 130.0, 29.5, False),
    ("Mumbai", "Andheri West",   28.0, 120.0, 29.0, False),  # peak rain day
    # Delhi — high AQI risk
    ("Delhi",  "Rohini",          2.0, 280.0, 38.0, False),
    ("Delhi",  "Connaught Place", 1.5, 310.0, 37.5, False),
    ("Delhi",  "Rohini",          3.0, 260.0, 39.0, False),
    # Bangalore — moderate
    ("Bangalore", "Indiranagar",  8.0,  90.0, 26.0, False),
    ("Bangalore", "Koramangala",  6.0,  85.0, 25.5, False),
    # Chennai — heat risk
    ("Chennai", "T Nagar",        5.0, 110.0, 35.0, False),
    ("Chennai", "Anna Nagar",     4.0, 105.0, 36.5, False),
    # Hyderabad — low risk
    ("Hyderabad", "Banjara Hills", 3.0, 130.0, 33.0, False),
    ("Hyderabad", "Hitech City",   2.5, 125.0, 32.5, False),
    # Curfew scenario — Mumbai
    ("Mumbai", "Dharavi",          4.0, 100.0, 30.0, True),
    ("Delhi",  "Old Delhi",        2.0, 290.0, 37.0, False),
]

for i, (city, zone, rain, aqi, temp, curfew) in enumerate(RISK_LOG_DATA):
    risk_score = compute_risk_score(rain_mm=rain, aqi=aqi, temp_c=temp, curfew=curfew)
    # Spread timestamps across the last 6 days for realistic chart data
    hours_ago = (i * 9) + 1   # 1h, 10h, 19h, 28h … spread over ~5 days
    log = RiskLog(
        city=city,
        zone=zone,
        risk_score=risk_score,
        rain_mm=rain,
        aqi=aqi,
        temp_c=temp,
        curfew=curfew,
        recorded_at=datetime.utcnow() - timedelta(hours=hours_ago),
    )
    db.add(log)

print(f"  {len(RISK_LOG_DATA)} RiskLog entries across 5 cities")

# ── Admin user ─────────────────────────────────────────────────────────────────
print("\nCreating admin user...")
admin = Worker(
    name="AbhayaRaksha Admin",
    email="admin@abhayaraksha.com",
    phone="0000000000",
    hashed_password=hash_password("admin1234"),
    worker_type="food_delivery",
    city="Mumbai",
    zone="HQ",
    lat=19.076,
    lng=72.877,
    avg_daily_income=0.0,
    is_admin=True,
)
db.add(admin)

# ── GlobalSettings singleton — systemic pause defaults to OFF ─────────────────
print("Seeding GlobalSettings (systemic pause = OFF)...")
db.add(GlobalSettings(id=1, is_systemic_pause=False))

# ── Commit everything ──────────────────────────────────────────────────────────
db.commit()
db.close()

print("\n" + "=" * 55)
print("  Seed complete. Demo is ready.")
print("=" * 55)
print("\nWorker accounts (password: demo1234):")
for w in WORKERS:
    print(f"  {w['email']:<28} {w['city']}")
print(f"\nAdmin account:")
print(f"  admin@abhayaraksha.com          password: admin1234")
print(f"\nRavi's dashboard will show:")
print(f"  - Active policy with ML-calculated premium")
print(f"  - 2 paid claims (rain + AQI) from 3 days ago")
print(f"  - Total income protected: ₹{rain_payout + aqi_payout:.0f}")
print(f"\nAdmin heatmap: {len(RISK_LOG_DATA)} data points across 5 cities")
print(f"\nBhargav Reddy: bhargav@demo.com / demo1234 (Hyderabad, food_delivery)")
