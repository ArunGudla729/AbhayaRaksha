GigShield -> Abhaya Raksha
# 🛡️ AbhayaRaksha
### Parametric Income Insurance for India's Gig Economy

> **10 million+ delivery workers** ride through monsoons, smog, and curfews every day with zero income protection. AbhayaRaksha changes that — with a fully automated, AI-powered parametric insurance platform that pays out *before* a worker even knows to file a claim.

---

##  Project Vision

India's gig delivery workforce is the backbone of the urban economy, yet it remains the most financially exposed segment in the country. A single day of heavy rain in Mumbai can wipe out ₹900 in earnings — with no safety net, no sick pay, and no recourse.

**AbhayaRaksha is built for the worker, not the boardroom.** By combining real-time weather data, actuarially-sound micro-pricing, and a zero-touch parametric trigger engine, we deliver income protection that is as fast, simple, and affordable as the workers who need it most.

---

##  Phase 2 Key Features

### Live Parametric Oracle
A background scheduler (the "Parametric Heart") polls the **OpenWeather API** every 15 minutes for Mumbai, Delhi, Bangalore, Chennai, and Hyderabad. The moment a city-specific threshold is breached — rain, AQI, heat, or curfew — claims are created and approved automatically. No worker action required. Ever.

###  Micro-Insurance Pricing — Built for Financial Inclusion
Premiums are calculated using an actuarially-grounded formula designed to keep coverage accessible:

$$\text{Premium} = P_{\text{trigger}} \times \text{Daily Income} \times \text{Exposure Days}$$

At a trigger probability of **0.8%** and 5 exposure days per week, a worker earning ₹850/day pays just **₹34/week** — less than a cup of chai. The premium scales with actual income and city-specific risk, not arbitrary tiers.

###  7-Day Anti-Fraud Underwriting Window
Every new policy includes a mandatory 7-day underwriting period before coverage activates. This prevents adverse selection — a worker cannot sign up during a live monsoon event and immediately collect a payout. The claim engine enforces this at the database query level, not just the UI.

###  Admin Actuarial Command Center
The admin dashboard provides real-time actuarial monitoring with:
- **BCR (Burning Cost Rate):** $\text{BCR} = \frac{\text{Total Claims Paid}}{\text{Total Premiums Collected}}$
- **Loss Ratio** with automated 🚨 enrollment suspension when BCR > 85%
- **Systemic Pause Kill-Switch** for Force Majeure events (War / Pandemic / Nuclear)
- **Fraud Alert Panel** with Isolation Forest ML anomaly detection
- **Risk Heatmap** across 5 cities with live data points

###  AI-Driven Risk Insights (Gemini 1.5 Flash)
Complex weather data is translated into plain-language, worker-friendly advice using Google's Gemini 1.5 Flash. A delivery worker in Andheri West doesn't need to understand AQI indices — they need to know: *"Today's air quality is poor. Your policy covers disruptions above AQI 200. Stay safe."*

###  Abhaya Smart-Shift Planner
A rule-based shift optimizer that scans tomorrow's 5-day forecast and identifies the first 6-hour window where rain < 1mm and temperature < 35°C — giving workers a concrete, actionable recommendation for when to maximize their earnings.

---

##  The Actuarial Math

### Premium Calculation

$$\text{Premium} = P_{\text{trigger}} \times (1 + \text{Risk Score}) \times \text{Daily Income} \times \text{Exposure Days}$$

| Parameter | Value | Rationale |
|---|---|---|
| Base trigger probability | 0.8% | Parametric rain cover industry benchmark |
| Risk score multiplier | 0–1 (ML-derived) | Higher-risk cities pay proportionally more |
| Exposure days | 5 per week | Standard gig worker working week |
| Coverage | 1× weekly income | Income replacement, not a windfall |

**Result:** ₹30–₹45/week for the average Indian gig worker.

### Burning Cost Rate (BCR)

$$\text{BCR} = \frac{\sum \text{Claims Paid}}{\sum \text{Premiums Collected}}$$

A BCR below 0.50 (50%) indicates a healthy fund. Above 0.85 (85%), the platform automatically suspends new enrollments to protect existing policyholders.

### Payout Structure

| Trigger | Threshold | Payout Rate | Max Payout |
|---|---|---|---|
| Rain | City-specific (12–35mm) | 16.7% of weekly income | 1 day's income |
| AQI | 200 | 16.7% | 1 day's income |
| Heat | 42°C | 16.7% | 1 day's income |
| Curfew | Active | 33.3% | 2 days' income |
| Flood | Active | 50.0% | 3 days' income |

City-specific rain thresholds prevent Mumbai's routine monsoon showers from triggering payouts that would bankrupt the fund:

| City | Rain Threshold | Rationale |
|---|---|---|
| Mumbai | 35mm/3h | IMD "heavy rainfall" — 15mm is a routine shower |
| Delhi | 12mm/3h | Semi-arid; 12mm is genuinely disruptive |
| Chennai | 25mm/3h | Moderate monsoon city |
| Bangalore | 20mm/3h | Moderate |
| Hyderabad | 15mm/3h | Default |

---

##  Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| **Backend** | Python 3.12 + FastAPI | REST API, parametric engine, scheduler |
| **Database** | SQLite (SQLAlchemy ORM) | Zero-config, portable, demo-ready |
| **ML / Risk** | scikit-learn (GradientBoosting + Isolation Forest) | Risk scoring + fraud detection |
| **Weather** | OpenWeather API (Current + Forecast) | Live parametric triggers + Smart-Shift |
| **AI** | Google Gemini 1.5 Flash | Worker risk summaries + admin insights |
| **Frontend** | React 18 + Vite + Tailwind CSS | Worker & admin dashboards |
| **Auth** | JWT (python-jose) + bcrypt | Secure token-based authentication |
| **Scheduling** | APScheduler (AsyncIO) | 15-minute parametric polling loop |

---

##  Media

| | |
|---|---|
|  **Phase 2 Demo Video** | [Watch the "Zero-Touch" Payout in Action](#) |
|  **Installation Guide** | [From Clone to Localhost in 3 Minutes](#) |

---

##  Setup — 4 Steps

### Prerequisites
- Python 3.12
- Node.js 18+
- No database server needed — SQLite is built in

### Step 1 — Clone

```bash
git clone https://github.com/your-org/abhayaraksha.git
cd abhaya_raksha
```

### Step 2 — Configure `.env`

```bash
cd backend
copy .env.example .env
```

Edit `backend/.env` and add your API keys (both are optional — the platform runs fully on safe mocks without them):

```env
OPENWEATHER_API_KEY=your_key_here   # optional — enables live weather
GEMINI_API_KEY=your_key_here        # optional — enables AI summaries
```

### Step 3 — Run Setup Script (Windows)

```bat
setup.bat  (or) .\setup.bat
```

This installs Python dependencies, trains ML models, and installs frontend packages in one step.

### Step 4 — Start & Seed

```bash
# Terminal 1 — Backend
cd backend
venv\Scripts\activate
pip install email-validator # once for new user
uvicorn app.main:app --reload --port 8000

# Terminal 2 — Seed demo data
cd backend
venv\Scripts\activate
python seed.py

# Terminal 3 — Frontend
cd frontend
npm run dev
```

Open **http://localhost:5173** in your browser.

---

##  Demo Credentials

After running `python seed.py`:

| Email | Password | Role | City |
|---|---|---|---|
| `ravi@demo.com` | `demo1234` | Worker | Mumbai — Food Delivery |
| `bhargav@demo.com` | `demo1234` | Worker | Hyderabad — Food Delivery |
| `suresh@demo.com` | `demo1234` | Worker | Delhi — E-commerce |
| `anjali@demo.com` | `demo1234` | Worker | Bangalore — Grocery |
| `priya@demo.com` | `demo1234` | Worker | Delhi — Grocery |
| `meena@demo.com` | `demo1234` | Worker | Chennai — Food Delivery |
| `admin@abhayaraksha.com` | `admin1234` | Admin | Platform Operator |

**Ravi's account** is pre-loaded with 2 paid claims (rain + AQI) and an active policy — the ideal starting point for a demo walkthrough.

---

##  Demo Script (2 Minutes)

1. **Register** as a new food delivery worker in Mumbai — watch the ML risk engine calculate a personalised ₹34–₹41/week premium in real time
2. **Activate Policy** — confirm the Force Majeure exclusions, pay, and watch the 7-day underwriting countdown begin
3. **Admin Login** → Run Simulation → Heavy Rainfall Mumbai → watch claims auto-trigger with fraud scores, payout amounts, and transaction IDs
4. **Switch back to Ravi** → new approved claim → "Withdraw to UPI" → animated gateway → Transfer Successful
5. **Admin Actuarial Panel** → BCR, Loss Ratio, System Health — the full financial picture in one view

---

##  API Reference

Interactive docs at `http://localhost:8000/docs`

| Endpoint | Method | Description |
|---|---|---|
| `/api/auth/register` | POST | Register a new worker |
| `/api/auth/login` | POST | Authenticate and receive JWT |
| `/api/workers/risk` | GET | Live risk score + dynamic premium |
| `/api/workers/shift-advice` | GET | Smart-Shift Planner recommendation |
| `/api/policies/activate` | POST | Purchase weekly policy |
| `/api/claims/my` | GET | Worker's claim history |
| `/api/claims/{id}/withdraw` | POST | Initiate UPI payout |
| `/api/admin/simulate` | POST | Trigger a disruption event |
| `/api/admin/system-health` | GET | BCR + Loss Ratio + enrollment status |
| `/api/system/status` | GET | Systemic pause state (worker-accessible) |

---

##  Roadmap

- **Mobile App** (React Native) with push notifications for real-time claim alerts
- **UPI AutoPay** for frictionless weekly premium collection
- **Multi-language UI** — Hindi, Tamil, Telugu for low-literacy workers
- **Zomato/Swiggy API Integration** — actual earnings data for hyper-accurate pricing
- **Blockchain Audit Trail** — immutable claim records for regulatory compliance
- **Reinsurance Pool** — sell risk tranches to institutional reinsurers
