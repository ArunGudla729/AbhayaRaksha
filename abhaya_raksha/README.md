# �️ AbhayaRaksha — AI-Powered Parametric Micro-Insurance for Gig Workers

> *"What if your income was protected the moment it rained — without filing a single claim?"*

India has over 15 million gig delivery workers. Every monsoon shower, every AQI spike, every heat wave silently steals their income. They can't afford to stop working, but they also can't afford to work in dangerous conditions. Traditional insurance doesn't help — it requires claims, documentation, and weeks of waiting.

**AbhayaRaksha changes that.** It's a zero-friction parametric insurance platform that monitors weather in real time, detects disruptions automatically, and credits workers' accounts instantly — no forms, no waiting, no manual action required.

---

## 🧠 The Problem

| Traditional Insurance | AbhayaRaksha |
|---|---|
| File a claim manually | No claim needed |
| Wait days for approval | Instant payout |
| Prove your loss | Objective weather trigger |
| High premiums, one-size-fits-all | AI-priced per worker |
| Excludes gig workers | Built for gig workers |

---

## 💡 How It Works

```
Worker activates policy
        ↓
APScheduler polls weather every 15 minutes (OpenWeather API)
        ↓
Parametric threshold breached? (rain / AQI / heat / curfew)
        ↓
Fraud check via GPS + ML anomaly detection
        ↓
Claim auto-approved → Razorpay order created instantly
        ↓
✅ ₹ credited (simulated via Razorpay test mode) — TXN ID in notification (zero manual steps)
```

👉 Result: Zero-touch, instant income protection for gig workers

The worker does not need to take any action for claims or payouts. The system handles everything automatically.

---

## 🔥 Key Features

### Zero-Touch Parametric Payouts
Claims are triggered, approved, and paid automatically when weather thresholds are breached. Workers receive a push notification with their transaction ID — no withdrawal step, no manual action.

### AI-Driven Dynamic Pricing
Premiums are calculated using a trained `GradientBoostingClassifier` on live weather features (rain, AQI, temperature, hour, day-of-week, monsoon season). Worker type multipliers apply: food delivery workers (highest outdoor exposure) pay slightly more; e-commerce workers pay less.

**Premium formula:**
```
Premium = trigger_probability × daily_income × exposure_days × worker_type_multiplier
```

Where `trigger_probability = TRIGGER_PROBABILITY × (1 + risk_score)` — risk-adjusted and personalised.

### Women-Specific Benefits
Female workers automatically receive an 8% premium discount and 12% higher coverage — applied additively with no impact on other workers.

### GPS-Based Fraud Detection
Live GPS captured on dashboard load is compared against the disruption zone. An ML Isolation Forest model scores each claim for anomalies. High-fraud-score claims are rejected; admins are alerted above a 0.7 threshold.

### City-Aware Thresholds
Rain thresholds are calibrated per city using IMD climatological normals — a flat 15mm threshold would fire constantly in Mumbai while almost never triggering in Delhi.

| City | Rain Threshold | Rationale |
|---|---|---|
| Mumbai | 35mm | 15mm is a routine monsoon shower |
| Chennai | 25mm | Moderate monsoon city |
| Bangalore | 20mm | Moderate |
| Hyderabad | 15mm | Default |
| Delhi | 12mm | Semi-arid; 12mm is genuinely disruptive |

### Systemic Pause Kill-Switch
Admins can declare a Force Majeure event (war, pandemic, flood) to suspend all automated payouts and protect fund solvency. Workers see a live emergency banner on their dashboard.

### Admin Simulation Dashboard
Admins can inject any weather event (rain, AQI, heat, curfew) for any city and watch the full parametric flow execute in real time — threshold check → fraud validation → auto-payout.

---

## 🎯 Demo Flow

### Step 1 — Login as Worker
```
Email:    ravi@demo.com
Password: demo1234
```
Ravi's dashboard shows his active policy with ML-calculated premium and two historical paid claims from 3 days ago (rain + AQI).

### Step 2 — Activate Policy (if needed)
Click **Activate Weekly Policy**. The system calculates a personalised premium based on live weather risk and Ravi's income profile.

### Step 3 — Switch to Admin
```
Email:    admin@abhayaraksha.com
Password: admin1234
```
Navigate to **Disruption Simulator**.

### Step 4 — Run a Simulation
Select any preset (e.g. *Heavy Rainfall – Mumbai*) or enter a custom event. Watch the parametric flow:

1. ✅ Disruption event detected
2. ✅ Threshold check: value vs city limit
3. ✅ Fraud validation for each worker
4. ✅ Claims auto-approved and paid instantly
5. ✅ **Payouts auto-credited via Razorpay**

### Step 5 — Switch Back to Worker
Ravi's dashboard now shows a new claim with status **Paid** and a real Razorpay transaction ID (e.g. `order_XXXXXXXXXXXXXXXX`). A notification confirms: *"₹72 credited automatically due to disruption. TXN: order_..."*

**No withdraw step. No manual action. The money is already there.**

---

## 🧾 Actuarial Design

### Coverage Model
Coverage = 25% of weekly income. This is intentionally conservative — parametric insurance is a supplement, not a replacement. It covers the income lost on a disrupted day without creating moral hazard (workers should never be financially better off by not working).

### Payout Rates (% of coverage per trigger)
| Event | Rate | Rationale |
|---|---|---|
| Rain | 8% | ~1/3 of a lost working day |
| AQI | 8% | ~1/3 of a lost working day |
| Heat | 8% | ~1/3 of a lost working day |
| Curfew | 15% | ~2/3 of a day (curfews last longer) |
| Flood | 22% | ~1 full lost working day |

### Anti-Stacking Guards
- **Daily cap**: One payout per worker per calendar day. Rain + AQI cannot stack on the same day.
- **Weekly cap**: Total payouts cannot exceed weekly income.
- **Moral hazard cap**: No single trigger pays more than 1.2× a day's income.

### Basis Risk Acknowledgement
Parametric insurance carries inherent basis risk — the weather trigger may fire when a specific worker wasn't disrupted, or may not fire when they were. AbhayaRaksha mitigates this with hyperlocal zone-level triggers and city-calibrated thresholds, but does not eliminate it. This is disclosed transparently in the policy exclusions.

---

## 🛠️ Tech Stack

### Backend
| Component | Technology |
|---|---|
| API Framework | FastAPI 0.135 |
| Database | SQLite (dev) / PostgreSQL (prod) |
| ORM | SQLAlchemy 2.0 |
| Scheduler | APScheduler 3.11 (polls every 15 min) |
| Auth | JWT via python-jose + passlib/bcrypt |
| ML Models | scikit-learn GradientBoostingClassifier + Isolation Forest |
| AI Summaries | Google Gemini API |
| Payments | Razorpay Orders API (test mode) |
| Weather | OpenWeather API (current weather + Air Pollution) |

### Frontend
| Component | Technology |
|---|---|
| Framework | React 18 + Vite |
| Styling | Tailwind CSS |
| Charts | Recharts |
| HTTP | Axios |
| Notifications | react-hot-toast |

---

## ⚡ Local Setup

### Prerequisites
- Python 3.10+
- Node.js 18+
- Git

### 1. Clone the repo
```bash
git clone <repo-url>
cd abhayaraksha
```

### 2. Backend setup
```bash
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux
pip install -r requirements.txt
```

### 3. Environment variables
Create `backend/.env`:
```env
DATABASE_URL=sqlite:///./AbhayaRaksha.db
SECRET_KEY=your-secret-key-here
OPENWEATHER_API_KEY=your_openweather_key
RAZORPAY_KEY_ID=your_razorpay_key_id
RAZORPAY_KEY_SECRET=your_razorpay_key_secret
GEMINI_API_KEY=your_gemini_key
```

> **Note:** The app runs without Razorpay/OpenWeather/Gemini keys — it falls back to mock data automatically. You only need real keys for live weather and real Razorpay order IDs.

### 4. Seed the database
```bash
cd backend
python seed.py
```

This creates all demo workers, policies, and historical claims.

### 5. Start the backend
```bash
uvicorn app.main:app --reload
```
API available at `http://localhost:8000` — interactive docs at `http://localhost:8000/docs`

### 6. Frontend setup
```bash
cd frontend
npm install
npm run dev
```
App available at `http://localhost:5173`

### One-command startup (Windows)
```bash
# From project root:
system.bat
```

---

## 🔑 Demo Credentials

### Worker Accounts (password: `demo1234`)
| Email | Name | City | Worker Type |
|---|---|---|---|
| ravi@demo.com | Ravi Kumar | Mumbai | Food Delivery |
| bhargav@demo.com | Bhargav Reddy | Hyderabad | Food Delivery |
| suresh@demo.com | Suresh Raina | Delhi | E-commerce |
| anjali@demo.com | Anjali Gupta | Bangalore | Grocery |
| priya@demo.com | Priya Sharma | Delhi | Grocery |
| meena@demo.com | Meena Devi | Chennai | Food Delivery |

### Admin Account
| Email | Password |
|---|---|
| admin@abhayaraksha.com | admin1234 |

---

## 📡 API Reference

Base URL: `http://localhost:8000`  
Interactive docs: `http://localhost:8000/docs`

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/auth/login` | Worker/admin login → JWT token |
| POST | `/api/auth/register` | Register new worker |
| GET | `/api/workers/me` | Current worker profile |
| GET | `/api/workers/risk` | Live risk score + premium quote |
| GET | `/api/workers/risk/summary` | AI-generated risk summary (Gemini) |
| GET | `/api/workers/shift-advice` | Smart-Shift timing recommendation |
| POST | `/api/workers/location` | Update live GPS coordinates |
| POST | `/api/policies/activate` | Activate weekly policy |
| GET | `/api/policies/active` | Get active policy |
| POST | `/api/policies/cancel` | Cancel active policy |
| GET | `/api/claims/my` | Worker's claim history |
| POST | `/api/admin/simulate` | Trigger disruption simulation (admin) |
| GET | `/api/admin/workers` | All workers (admin) |
| GET | `/api/admin/claims` | All claims (admin) |
| GET | `/api/admin/risk-heatmap` | Risk heatmap data (admin) |
| POST | `/api/admin/systemic-pause` | Toggle Force Majeure pause (admin) |
| GET | `/api/notifications` | Worker notifications |
| POST | `/api/notifications/clear` | Mark all notifications read |
| GET | `/api/payments/status` | Premium payment status |
| POST | `/api/payments` | Record premium payment |
| GET | `/api/manual-claims/my` | Manual claim history |
| POST | `/api/manual-claims` | Submit manual claim (≤ ₹1,000) |
| GET | `/api/system/status` | Platform status (systemic pause flag) |
| GET | `/health` | Health check |

---

## 🔄 Phase 3 Updates (Latest Improvements)

### Auto-Payout — No Manual Withdraw
Claims are now marked `paid` immediately at creation. The claim engine calls the Razorpay Orders API inline, attaches the `order_id` as `transaction_id`, and sets status to `paid` in the same DB transaction. Workers never see an "approved" state that requires action — the money is credited automatically.

No withdraw step. No manual action. The money is already credited.

### Processing → Paid UI Animation
The worker dashboard detects claims paid within the last 60 seconds and briefly shows a "Processing..." animation before revealing the paid status. This gives the auto-payout flow a satisfying visual confirmation without any artificial delay in the backend.

### Notification-Based Payout Confirmation
Workers receive an in-app notification the moment a payout is credited: *"₹{amount} credited automatically due to disruption. TXN: {order_id}"*. The notification bell updates in real time.

### Simulation Flow Alignment
The admin Disruption Simulator now shows all 5 steps of the parametric flow completing instantly after the API responds — matching the actual backend behaviour where claims go directly to `paid`.

### City-Calibrated Rain Thresholds
Rain thresholds are now city-specific (Mumbai: 35mm, Delhi: 12mm, etc.) in both the claim engine and the worker dashboard UI, ensuring the warning colours and trigger logic are always in sync.

### Basis Risk Transparency
Policy exclusions now include a plain-language explanation of basis risk — the gap between the weather trigger and a worker's actual disruption experience. This aligns with IRDAI parametric product guidelines.

### Women-Specific Benefits
Female workers automatically receive an 8% premium discount and 12% higher coverage with no opt-in required.

---

## 🗺️ Roadmap

- [ ] UPI Payout API integration (NPCI / Razorpay Payouts) for real money movement
- [ ] ONDC integration for verified gig worker identity
- [ ] Multi-city geofence zones with polygon-level precision
- [ ] Reinsurance pool simulation for fund sustainability modelling
- [ ] Mobile app (React Native) with offline-first claim visibility
- [ ] IRDAI sandbox registration for regulatory pilot

---

PITCH DECK :- https://drive.google.com/file/d/1RMq10LOxyK66AhP49lgX9C8LYYEtb09h/view?usp=sharing
DEMO VIDEO :- https://youtu.be/IAsSsD1xkos

## ⚠️ Disclaimer

This is a hackathon prototype. All payments are simulated via Razorpay test mode — no real money moves. GPS data is collected with explicit user consent and used solely for fraud prevention. The platform is not a licensed insurance product.

---

*Built with ❤️ for India's gig workers.*
*crafted in Chennai*
