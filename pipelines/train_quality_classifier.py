#!/usr/bin/env python3
"""
Quality Classifier — Python-side only (not transpiled to Kotlin).

Trains a Random Forest to predict shot quality (good/poor/miss/edge)
from the same 20-feature vector used for shot classification.

Saves:
  quality_classifier.pkl   — fitted RandomForestClassifier
  quality_le.pkl           — fitted LabelEncoder for quality labels

These are loaded by reprocess_sessions.py to retrospectively re-score
historical shots and flag updates in the phone app's History screen.
"""
import os
import sys
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import StratifiedKFold, cross_val_score

BASE_DIR = "/Users/neilkloot/Code/Batting Sensor Stats"
FEATURES_CSV = os.path.join(BASE_DIR, "combined_features.csv")
MODEL_OUT     = os.path.join(BASE_DIR, "quality_classifier.pkl")
LE_OUT        = os.path.join(BASE_DIR, "quality_le.pkl")

FEATURE_COLS = [
    's1_gyro_y_std', 's1_gyro_z_std', 's1_deltaX', 's1_deltaZ',
    's2_gyroMag', 's2_grav_y_mean', 's2_deltaX', 's2_deltaZ',
    's3_rollImpactDeg', 's3_yawImpactDeg', 's3_deltaX', 's3_deltaZ',
    's3_planeRatio', 's3_gyro_y_min',
    # Polar features — 0.0 when absent
    'bottom_hand_gyro_peak', 'bottom_hand_acc_peak',
    'bottom_hand_gyro_ratio', 'bottom_hand_acc_ratio',
    'bottom_hand_time_lead_ms', 'bottom_hand_sync_score',
]

# Canonical quality labels (map "okay" → "good" for a 4-class problem)
QUALITY_MAP = {
    "good": "good", "okay": "good", "ok": "good",
    "excellent": "good", "perfect": "good",   # treat excellent as good tier
    "poor": "poor", "bad": "poor",
    "miss": "miss",
    "edge": "edge", "edged": "edge",
}
VALID_CLASSES = {"good", "poor", "miss", "edge"}

def normalise_quality(q):
    q = str(q).lower().strip()
    return QUALITY_MAP.get(q, None)


def main():
    print("=" * 60)
    print("Quality Classifier Training")
    print("=" * 60)

    if not os.path.exists(FEATURES_CSV):
        print(f"❌ Features CSV not found: {FEATURES_CSV}")
        sys.exit(1)

    df = pd.read_csv(FEATURES_CSV)

    # Only train on real swing shots (not non-swings, not synthetic rows without quality labels)
    df = df[df['normalized_gt'] != 'NON-SWING'].copy()
    df = df[df['quality'].notna()].copy()
    df['quality_norm'] = df['quality'].map(lambda q: normalise_quality(q))
    df = df[df['quality_norm'].isin(VALID_CLASSES)].copy()

    if df.empty:
        print("❌ No training rows with valid quality labels — ensure compile_dataset.py was run first.")
        sys.exit(1)

    print(f"\nTraining set: {len(df)} shots across {df['session_id'].nunique()} sessions")
    print("\nQuality class distribution:")
    print(df['quality_norm'].value_counts().to_string())

    X = df[FEATURE_COLS].fillna(0.0)
    y = df['quality_norm'].values

    le = LabelEncoder()
    y_enc = le.fit_transform(y)
    class_names = list(le.classes_)

    print(f"\nClasses: {class_names}")

    # Cross-validation diagnostic (NOT the model accuracy — training diagnostic only)
    rf = RandomForestClassifier(
        n_estimators=100,
        max_depth=6,
        class_weight='balanced_subsample',
        random_state=42,
        n_jobs=-1
    )

    n_splits = min(5, df['quality_norm'].value_counts().min())
    if n_splits < 2:
        print("⚠️  Not enough samples per class for cross-validation. Training without CV.")
        cv_mean = None
    else:
        cv = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=42)
        cv_scores = cross_val_score(rf, X, y_enc, cv=cv, scoring='accuracy')
        cv_mean = np.mean(cv_scores)
        print(f"\n[Diagnostic only] CV accuracy ({n_splits}-fold): {cv_mean:.1%} ± {np.std(cv_scores):.1%}")
        print("  ⚠️  This is a training diagnostic. Do NOT use as model accuracy.")

    # Fit final model on all data
    rf.fit(X, y_enc)
    train_acc = (rf.predict(X) == y_enc).mean()
    print(f"\nTraining-set fit: {train_acc:.1%} (overfit indicator only)")

    # Per-class CV breakdown
    if n_splits >= 2:
        from sklearn.model_selection import cross_val_predict
        y_pred_cv = le.inverse_transform(
            cross_val_predict(rf, X, y_enc, cv=StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=42))
        )
        print("\nPer-class CV recall:")
        for cls in class_names:
            mask = y == cls
            if mask.sum() > 0:
                recall = (y_pred_cv[mask] == cls).mean()
                print(f"  {cls:<8}: {recall:.0%} ({mask.sum()} shots)")

    # Save model
    joblib.dump(rf, MODEL_OUT)
    joblib.dump(le, LE_OUT)
    print(f"\n✅ Quality classifier saved to: {MODEL_OUT}")
    print(f"✅ Label encoder saved to: {LE_OUT}")


if __name__ == "__main__":
    main()
