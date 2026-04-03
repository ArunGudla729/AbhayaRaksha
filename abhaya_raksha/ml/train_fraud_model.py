"""
Fraud Detection Model Training
================================
Uses Isolation Forest (unsupervised anomaly detection) to flag suspicious claims.
Features: claims_per_week, avg_claim_gap_hours, gps_distance_km, claim_hour, payout_ratio

Run: python ml/train_fraud_model.py
Output: ml/fraud_model.joblib
"""
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
import joblib

np.random.seed(42)

def generate_fraud_dataset(n_normal=4000, n_fraud=500):
    # Normal claims
    normal = pd.DataFrame({
        "claims_per_week": np.random.randint(0, 3, n_normal),
        "avg_claim_gap_hours": np.random.normal(48, 12, n_normal).clip(12, 200),
        "gps_distance_km": np.random.exponential(5, n_normal).clip(0, 25),
        "claim_hour": np.random.randint(7, 22, n_normal),
        "payout_ratio": np.random.normal(0.5, 0.1, n_normal).clip(0.1, 1.0),
    })

    # Fraudulent claims (anomalous patterns)
    fraud = pd.DataFrame({
        "claims_per_week": np.random.randint(4, 10, n_fraud),          # too many claims
        "avg_claim_gap_hours": np.random.normal(4, 2, n_fraud).clip(0.5, 10),  # too frequent
        "gps_distance_km": np.random.normal(50, 20, n_fraud).clip(30, 200),    # far from zone
        "claim_hour": np.random.choice([1, 2, 3, 4, 5], n_fraud),              # odd hours
        "payout_ratio": np.random.normal(0.95, 0.05, n_fraud).clip(0.8, 1.0), # always max payout
    })

    return pd.concat([normal, fraud], ignore_index=True)

df = generate_fraud_dataset()
X = df.values

pipeline = Pipeline([
    ("scaler", StandardScaler()),
    ("iso", IsolationForest(
        n_estimators=100,
        contamination=0.1,   # ~10% fraud rate
        random_state=42
    ))
])

pipeline.fit(X)

# Test: -1 = anomaly (fraud), 1 = normal
scores = pipeline.decision_function(X)
predictions = pipeline.predict(X)
fraud_detected = (predictions == -1).sum()
print(f"Fraud detected in training set: {fraud_detected} / {len(X)} ({fraud_detected/len(X):.1%})")

joblib.dump(pipeline, "ml/fraud_model.joblib")
print("Fraud model saved to ml/fraud_model.joblib")

# Sample scoring
samples = np.array([
    [1, 48, 3, 14, 0.5],    # normal
    [7, 2, 80, 3, 0.99],    # fraud
    [2, 36, 8, 11, 0.45],   # normal
])
sample_scores = pipeline.decision_function(samples)
sample_preds = pipeline.predict(samples)
print("\nSample fraud scores (lower = more anomalous):")
for i, (s, p) in enumerate(zip(sample_scores, sample_preds)):
    label = "FRAUD" if p == -1 else "NORMAL"
    print(f"  Sample {i+1}: score={s:.4f} → {label}")
