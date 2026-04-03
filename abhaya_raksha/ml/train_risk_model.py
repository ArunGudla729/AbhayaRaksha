"""
Risk Prediction Model Training
================================
Trains a Gradient Boosting classifier to predict disruption probability.
Features: rain_mm, aqi, temp_c, hour_of_day, day_of_week, is_monsoon_month
Target: disruption_occurred (1 = income loss event, 0 = normal)

Run: python ml/train_risk_model.py
Output: ml/risk_model.joblib
"""
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, roc_auc_score
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
import joblib
import os

np.random.seed(42)
N = 5000

# ── Synthetic Dataset ─────────────────────────────────────────────────────────
def generate_dataset(n: int) -> pd.DataFrame:
    rain_mm = np.random.exponential(scale=5, size=n)          # mostly low rain
    aqi = np.random.normal(loc=120, scale=60, size=n).clip(20, 500)
    temp_c = np.random.normal(loc=32, scale=6, size=n).clip(15, 48)
    hour = np.random.randint(6, 23, size=n)
    day_of_week = np.random.randint(0, 7, size=n)
    is_monsoon = np.random.choice([0, 1], size=n, p=[0.6, 0.4])

    # Disruption probability based on conditions
    prob = (
        0.4 * (rain_mm / 50).clip(0, 1) +
        0.3 * ((aqi - 100) / 300).clip(0, 1) +
        0.2 * ((temp_c - 35) / 15).clip(0, 1) +
        0.1 * is_monsoon
    )
    disruption = (np.random.rand(n) < prob).astype(int)

    return pd.DataFrame({
        "rain_mm": rain_mm,
        "aqi": aqi,
        "temp_c": temp_c,
        "hour": hour,
        "day_of_week": day_of_week,
        "is_monsoon": is_monsoon,
        "disruption": disruption
    })

df = generate_dataset(N)
print(f"Dataset: {N} samples | Disruption rate: {df['disruption'].mean():.1%}")

X = df.drop("disruption", axis=1)
y = df["disruption"]

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# ── Model Pipeline ────────────────────────────────────────────────────────────
pipeline = Pipeline([
    ("scaler", StandardScaler()),
    ("clf", GradientBoostingClassifier(
        n_estimators=100,
        learning_rate=0.1,
        max_depth=4,
        random_state=42
    ))
])

pipeline.fit(X_train, y_train)

# ── Evaluation ────────────────────────────────────────────────────────────────
y_pred = pipeline.predict(X_test)
y_prob = pipeline.predict_proba(X_test)[:, 1]
print("\nClassification Report:")
print(classification_report(y_test, y_pred))
print(f"ROC-AUC: {roc_auc_score(y_test, y_prob):.4f}")

# ── Save Model ────────────────────────────────────────────────────────────────
os.makedirs("ml", exist_ok=True)
joblib.dump(pipeline, "ml/risk_model.joblib")
print("\nModel saved to ml/risk_model.joblib")

# ── Sample Predictions ────────────────────────────────────────────────────────
samples = pd.DataFrame([
    {"rain_mm": 20, "aqi": 250, "temp_c": 30, "hour": 14, "day_of_week": 2, "is_monsoon": 1},
    {"rain_mm": 2,  "aqi": 80,  "temp_c": 28, "hour": 10, "day_of_week": 1, "is_monsoon": 0},
    {"rain_mm": 35, "aqi": 300, "temp_c": 38, "hour": 18, "day_of_week": 5, "is_monsoon": 1},
])
probs = pipeline.predict_proba(samples)[:, 1]
print("\nSample predictions (disruption probability):")
for i, p in enumerate(probs):
    print(f"  Sample {i+1}: {p:.2%}")
