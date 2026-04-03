# GigShield — Phase 1 Submission

> Parametric Income Protection for India's Gig Delivery Workers

**Demo Video:**  - https://youtu.be/JSjbthavZE0

---

## Inspiration

Meet Ravi. He wakes up at 5:30 AM in Andheri West, Mumbai, charges his phone, and logs into his delivery app. By 7 AM he has already completed three orders. Then the monsoon hits.

By noon, rainfall in Mumbai crosses 18mm in a three-hour window. The roads flood. Platforms suspend deliveries. Ravi earns nothing for the rest of the day — and the next two days after that. He has no sick leave, no employer, and no insurance. His weekly income of ₹5,400 drops to ₹1,800. His rent is due in four days.

Ravi is not an edge case. He is the rule.

India's 15 million gig delivery workers — food delivery, e-commerce, and quick-commerce riders — lose an estimated **20–30% of their annual income** to weather and civic disruptions: monsoon flooding, hazardous AQI days, extreme heat waves, and sudden curfews or bandhs. Traditional insurance products do not serve them. Claim processes require documentation, adjuster visits, and weeks of waiting — none of which work for a worker who needs income protection *today*.

GigShield was built to answer one question: **what if a worker's income was protected the moment a disruption was detected, with zero paperwork and instant payout?**

---

## What It Does

GigShield is a **parametric income protection platform** for gig delivery workers. Unlike traditional insurance, it does not require workers to file claims, submit evidence, or wait for approval. Instead, it monitors real-world disruption signals continuously and triggers payouts automatically when pre-defined thresholds are breached.

**For Ravi, the flow looks like this:**

1. He registers on GigShield, enters his city (Mumbai), delivery zone (Andheri West), and average daily income (₹900).
2. The risk engine fetches live weather data for his zone and calculates a dynamic weekly premium — typically 4–12% of his weekly income, adjusted for current conditions.
3. He activates a weekly policy with one tap. Coverage is set at 3× his weekly income.
4. When Mumbai rainfall crosses 15mm/3h, the parametric engine fires automatically. Every worker in the affected zone with an active policy receives an approved claim — no action required.
5. Ravi opens the app, sees "₹2,700 approved", and taps "Collect Payout". The transaction is simulated instantly.

**Disruption triggers supported:**

| Trigger | Threshold | Payout Rate |
|---|---|---|
| Heavy Rainfall | ≥ 15 mm / 3h | 50% of weekly coverage |
| Hazardous AQI | ≥ 200 index | 40% of weekly coverage |
| Extreme Heat | ≥ 42°C | 35% of weekly coverage |
| Curfew / Bandh | Active = 1 | 100% of weekly coverage |
| Flood Event | Active = 1 | 100% of weekly coverage |

The platform also includes a full **Admin Dashboard** for platform operators to monitor loss ratios, fraud alerts, weekly analytics, and trigger simulations — all protected behind Role-Based Access Control.

---

## How We Built It

### Backend — FastAPI + SQLAlchemy + SQLite

We utilized **FastAPI** for a high-performance asynchronous backend to handle real-time weather polling. The async architecture means weather fetches, risk calculations, and claim triggers all run concurrently without blocking the API. SQLAlchemy 2.0 with SQLite provides a zero-configuration relational store — the full schema (workers, policies, claims, disruption events, risk logs) is created automatically on startup via `Base.metadata.create_all()`.

The data model is structured around five core tables:

- `workers` — stores identity, GPS coordinates (`lat`, `lng`), delivery zone, average daily income, and the `is_admin` RBAC flag
- `policies` — weekly policies with dynamically calculated `weekly_premium`, `coverage_amount`, and `risk_score` at time of subscription
- `claims` — parametric claims with `trigger_type`, `trigger_value`, `trigger_threshold`, `payout_amount`, `fraud_score`, and `fraud_flags`
- `disruption_events` — immutable log of every event that crossed a threshold
- `risk_logs` — time-series of risk scores per city for heatmap analytics

### Risk Engine — Gradient Boosting + Rule-Based Scoring

The risk engine is powered by a **Gradient Boosting Classifier** (Scikit-Learn) that analyzes historical weather patterns to calculate weekly premiums. The model is trained on a synthetic dataset of 5,000 samples with features: `rain_mm`, `aqi`, `temp_c`, `hour_of_day`, `day_of_week`, and `is_monsoon_month`. It predicts disruption probability, which feeds into a weighted risk score:

```
risk_score = (0.40 × rain_risk) + (0.30 × aqi_risk) + (0.20 × heat_risk) + (0.10 × curfew_risk)
```

The weekly premium is then calculated as:

```
premium_rate = BASE_RATE(4%) + (MAX_RATE(12%) - BASE_RATE) × risk_score
weekly_premium = worker.avg_daily_income × 6 days × premium_rate
coverage_amount = weekly_income × 3.0
```

Live weather data is fetched from the OpenWeather API (with deterministic city-based mocks as fallback when no API key is configured), ensuring the premium Ravi sees reflects actual current conditions in his zone.

### Fraud Detection — Isolation Forest + Rule Engine

Every parametric claim passes through a four-layer fraud detection pipeline before approval:

1. **GPS Zone Validation** — Haversine distance between the worker's registered coordinates and the claim coordinates. Workers more than 30km outside their registered zone are flagged (`GPS_MISMATCH`).
2. **Duplicate Claim Detection** — Same worker, same trigger type, same calendar day is rejected (`DUPLICATE_CLAIM`).
3. **Time-Based Anomaly** — Claims filed outside working hours (6 AM – 11 PM UTC) are flagged (`OFF_HOURS`).
4. **Velocity Check** — More than 3 approved claims in a rolling 7-day window triggers `HIGH_VELOCITY`.

A composite `fraud_score` (0.0–1.0) is computed from these signals. Claims with `fraud_score ≥ 0.6` are automatically rejected. The Isolation Forest model (`ml/fraud_model.joblib`) trained on synthetic behavioral data provides an additional anomaly layer.

### Authentication & RBAC — JWT + python-jose + passlib/bcrypt

Authentication uses **HS256 JWT tokens** via `python-jose`. The `sub` claim stores the worker ID as a string (per RFC 7519 spec enforcement by python-jose). On decode, it is cast back to `int` for the database lookup.

Role-Based Access Control is implemented via two FastAPI dependencies:

- `get_current_worker` — validates the JWT and returns the authenticated worker
- `get_current_admin` — chains from `get_current_worker` and raises `HTTP 403` if `worker.is_admin` is `False`

All `/api/admin/*` routes are protected by `get_current_admin`. The `is_admin` flag is returned in the login response and stored in `localStorage` on the frontend to gate the React admin routes.

### Frontend — React + Vite + Tailwind CSS

For the frontend, we chose **React + Vite** for a responsive, mobile-first experience for workers on the go. The UI is built with Tailwind CSS for rapid, utility-first styling. Axios handles all API communication with a request interceptor that attaches the JWT Bearer token to every call, and a response interceptor that auto-clears credentials and redirects to `/login` on any `401`.

Route protection is handled by two guard components:
- `PrivateRoute` — requires a valid token in `localStorage`
- `AdminRoute` — requires both a valid token and `is_admin === 'true'` in `localStorage`

---

## Challenges We Ran Into

### 1. Bcrypt / Passlib Version Conflict — Silent Authentication Failure

The most disorienting bug we encountered was a completely silent login failure. The frontend would accept credentials, store the token, navigate to the dashboard, and then immediately redirect back to `/login` — with no error message and no backend log.

The root cause was a **breaking API change in bcrypt 4.x**. `passlib 1.7.4` reads `bcrypt.__about__.__version__` during `CryptContext` initialization to detect the bcrypt version. In bcrypt 4.0+, the `__about__` module was removed entirely. This caused an `AttributeError` that passlib silently swallowed, leaving the `CryptContext` in a broken state where `verify_password()` returned `False` for every call — regardless of whether the password was correct.

The fix was a targeted monkey-patch applied before `CryptContext` is constructed:

```python
import bcrypt as _bcrypt
if not hasattr(_bcrypt, "__about__"):
    class _About:
        __version__ = "4.0.1"
    _bcrypt.__about__ = _About()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
```

This stubs the missing attribute so passlib initializes correctly, without requiring a bcrypt downgrade or a passlib upgrade.

### 2. JWT Strict Type Enforcement — Post-Login 401 Loop

After fixing the bcrypt issue, login succeeded but the dashboard immediately showed "Failed to load data" and redirected back to `/login`. Every authenticated API call was returning `401`.

The cause was a **strict type enforcement in python-jose**: the JWT specification (RFC 7519) requires the `sub` claim to be a string. Our `create_access_token` was passing `worker.id` as a Python `int`. The token encoded without error, but `jwt.decode()` raised `JWTClaimsError: Subject must be a string` on every subsequent request. This was caught by the `except JWTError` block, which raised `HTTP 401`, which triggered the frontend auto-logout interceptor — creating a perfect redirect loop.

The fix was a two-line type correction:

```python
# Encode: cast to string
token = create_access_token({"sub": str(worker.id)})

# Decode: cast back to int
worker_id = int(payload.get("sub"))
```

### 3. Python 3.13 / scikit-learn Wheel Incompatibility

The development environment was initialized with Python 3.13.12, for which `scikit-learn 1.4.1.post1`, `numpy 1.26.4`, and `pandas 2.2.1` have no pre-built wheels on PyPI for Windows. Building from source requires Microsoft Visual C++ Build Tools, which were not present. The resolution was to standardize the project on **Python 3.12**, which has full `cp312` wheel coverage for all dependencies, and to update `setup.bat` to use `py -3.12 -m venv venv` explicitly rather than the unversioned `python` command.

---

## Accomplishments That We're Proud Of

**A fully working RBAC system.** The separation between worker and admin roles is enforced at every layer: the database (`is_admin` column), the backend (FastAPI dependency injection with `get_current_admin`), the API response (login returns `is_admin` flag), and the frontend (React `AdminRoute` guard). A regular worker JWT cannot access any `/api/admin/*` endpoint — they receive a clean `403 Forbidden`.

**A live ML-integrated backend.** The risk engine runs a real Gradient Boosting model pipeline (StandardScaler → GradientBoostingClassifier) on every policy subscription and risk query. The fraud detector runs a real Isolation Forest model on every parametric claim. Both models are serialized with `joblib` and loaded at runtime — this is not a mock or a hardcoded score.

**Zero-click parametric claims.** The claim engine is fully automated. When a disruption event is simulated or detected, the system queries all active policies in the affected city, runs fraud checks, calculates payouts, and commits approved claims — all in a single database transaction. Workers do not file anything.

**A debugged, production-quality auth stack.** We shipped working JWT authentication with bcrypt password hashing, resolved two non-trivial library compatibility bugs under time pressure, and ended up with a cleaner, more robust implementation than we started with.

---

## What We Learned

We learned that **parametric insurance is highly vulnerable to GPS spoofing**. Because payouts are triggered automatically based on location and environmental data, a bad actor who can fake their GPS coordinates to appear inside a high-rainfall zone — while physically being elsewhere — can fraudulently collect payouts without any disruption to their actual work. This led us to research and design our **Adversarial Defense Strategy (Multi-Factor Presence Validation)** to protect the liquidity pool.

We also learned the importance of **JWT-based Role Access** to ensure that sensitive parametric triggers are only accessible by verified administrators. Without RBAC, any authenticated worker could POST to `/api/admin/simulate` and trigger mass payouts across the entire platform — a catastrophic liquidity risk. The `get_current_admin` dependency pattern in FastAPI makes this enforcement clean, composable, and impossible to accidentally bypass.

Finally, we learned that library version pinning is not optional in a Python ML stack. The bcrypt/passlib conflict and the scikit-learn wheel gap both stem from unpinned or under-specified dependencies. Every package in `requirements.txt` is now pinned to an exact version.

---

## Adversarial Defense & Anti-Spoofing Strategy

During a 24-hour crisis pivot after identifying the GPS spoofing vulnerability, we designed a **Multi-Factor Presence Validation** framework. The core insight is that no single signal is sufficient to confirm physical presence — but three independent signals that agree are extremely difficult to simultaneously fake.

### Layer 1 — Velocity Tracking

The fraud detector maintains a rolling 7-day claim history per worker. A worker who files more than 3 claims in 7 days triggers a `HIGH_VELOCITY` flag (+0.3 to fraud score). In the production roadmap, this extends to cross-session GPS trajectory analysis: if a worker's registered location shows no movement consistent with active delivery (stationary for hours during a claimed disruption window), the claim is flagged for manual review.

### Layer 2 — Cell-Tower Triangulation

GPS coordinates submitted by the app can be spoofed at the software level. Cell-tower triangulation operates at the network layer and is significantly harder to fake without physical presence. In the production architecture, the mobile app would submit both GPS coordinates and the serving cell tower ID. The backend cross-references the tower's known coverage area against the claimed disruption zone. A GPS coordinate inside the disruption zone but a cell tower outside it is a strong spoofing signal.

### Layer 3 — Device Telemetry

The third layer uses passive device signals that are consistent with genuine outdoor delivery activity: accelerometer data (is the device moving?), ambient noise levels (is there rain/wind audio consistent with the claimed weather event?), and battery drain patterns (consistent with active navigation use?). These signals are aggregated into a presence confidence score. A worker claiming a monsoon disruption payout while their device shows zero movement, silence, and a charging pattern is flagged automatically.

**Combined fraud score logic (production target):**

```
fraud_score = w1 × gps_mismatch
            + w2 × velocity_anomaly
            + w3 × cell_tower_mismatch
            + w4 × telemetry_anomaly
            + w5 × duplicate_claim
            + w6 × off_hours_flag

Claims with fraud_score ≥ 0.6 → auto-rejected
Claims with fraud_score 0.4–0.6 → queued for admin review
Claims with fraud_score < 0.4 → auto-approved
```

The current implementation covers GPS mismatch, velocity, duplicate detection, and off-hours anomaly. Cell-tower and telemetry layers are designed and ready for the mobile app integration in Phase 2.

---

## What's Next for GigShield

**UPI 2.0 Integration.** The current payout flow is simulated — claims are marked `paid` in the database and a transaction ID is generated. The immediate next step is integrating with the UPI 2.0 mandate flow, which allows GigShield to push payouts directly to a worker's linked UPI ID within seconds of claim approval. For Ravi, this means the ₹2,700 appears in his PhonePe or GPay wallet before he has even closed the app.

**Q-Commerce Expansion.** The platform currently supports food delivery, e-commerce, and grocery delivery worker types. The Q-Commerce segment (Zepto, Blinkit, Swiggy Instamart) operates on 10-minute delivery windows with extremely high weather sensitivity — a 15-minute rain delay can cascade into dozens of failed deliveries and significant income loss. We are designing zone-level micro-policies for Q-Commerce riders with 30-minute policy windows and sub-threshold partial payouts.

**Scheduled Parametric Monitoring.** The current architecture triggers claims via the simulation endpoint. The production roadmap adds an APScheduler job that polls OpenWeather every 15 minutes for all active worker cities, automatically fires `trigger_claims_for_event` when thresholds are breached, and logs results to the `RiskLog` table for heatmap analytics — making the platform fully autonomous.

**Aadhaar-Linked Identity Verification.** To prevent synthetic identity fraud at registration, Phase 2 will integrate DigiLocker for Aadhaar-based KYC. This ties each worker account to a verified government identity, making it significantly harder to create multiple accounts for the same individual to multiply payouts.

---

## Built With

- Python 3.12 · FastAPI 0.110 · SQLAlchemy 2.0 · SQLite
- Scikit-Learn 1.4 (GradientBoostingClassifier, IsolationForest) · NumPy · Pandas · Joblib
- python-jose · passlib · bcrypt
- React 18 · Vite · Tailwind CSS · Recharts · Axios
- OpenWeather API · Google Gemini 1.5 Flash
- Google Gemini AI (risk summaries, admin insights)

---

*GigShield — because Ravi's income deserves the same protection as anyone else's.*
