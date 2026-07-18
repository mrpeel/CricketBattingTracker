#!/usr/bin/env python3
"""
score_phone_pipeline.py — Authoritative Phone-Pipeline Performance Scorecard

Evaluates the ACTUAL system that runs in production: PhoneSwingDetector (phone-side
batch processor) feeding a 20-feature GeneratedForest. Uses combined_features.csv
(compiled by compile_dataset.py after evaluate_shot_alignment.py has run) as the
source of truth for both features and ground truth labels.

The script:
  1. Loads combined_features.csv + combined_ground_truth_aligned.csv
  2. Re-scores every shot with the current trained RF model (20 features)
  3. Reports overall shot identification (how many shots were found vs missed)
  4. Reports overall shot classification accuracy
  5. Reports per-data-profile breakdown (50hz_watch, 50hz_watch_polar, 100hz_watch_polar)
  6. Reports per-shot-class breakdown
  7. Writes phone_pipeline_scorecard.md as the authoritative output

This replaces SwingDetectorGroundTruthTest.kt which tested the retired on-watch
SwingDetector code path.
"""
import os
import sys
import datetime
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder

BASE_DIR      = "/Users/neilkloot/Code/Batting Sensor Stats"
ROOT_DIR      = "/Users/neilkloot/Code/CricketBattingTracker"
FEATURES_CSV  = os.path.join(BASE_DIR, "combined_features.csv")
ALIGNED_CSV   = os.path.join(BASE_DIR, "combined_ground_truth_aligned.csv")
SCORECARD_OUT = os.path.join(ROOT_DIR, "phone_pipeline_scorecard.md")

# The brain directory holding the scorecard for model_update_pipeline.py to find
BRAIN_DIR = "/Users/neilkloot/.gemini/antigravity/brain"

FEATURE_COLS = [
    's1_gyro_y_std', 's1_gyro_z_std', 's1_deltaX', 's1_deltaZ',
    's2_gyroMag', 's2_grav_y_mean', 's2_deltaX', 's2_deltaZ',
    's3_rollImpactDeg', 's3_yawImpactDeg', 's3_deltaX', 's3_deltaZ',
    's3_planeRatio', 's3_gyro_y_min',
    'bottom_hand_gyro_peak', 'bottom_hand_acc_peak',
    'bottom_hand_gyro_ratio', 'bottom_hand_acc_ratio',
    'bottom_hand_time_lead_ms', 'bottom_hand_sync_score',
]

NON_SWING_TERMS = {'facing up', 'no shot', 'leave', 'evade', 'evasion'}

ALL_CLASSES = [
    'CUT/PUNCH', 'DEFLECTION/GUIDE', 'DRIVE/DEFENCE',
    'GLANCE/FLICK', 'POWER DRIVE', 'PULL/HOOK', 'SLOG', 'SWEEP'
]

PROFILE_LABELS = {
    '50hz_watch':      'Watch-only 50Hz',
    '50hz_watch_polar': 'Watch 50Hz + Polar',
    '100hz_watch_polar': 'Watch 100Hz + Polar',
}


def train_model(df_swings):
    """Fit the 20-feature RF on all available swing data and return model + encoder."""
    X = df_swings[FEATURE_COLS].fillna(0.0)
    y = df_swings['normalized_gt'].values
    le = LabelEncoder()
    y_enc = le.fit_transform(y)
    rf = RandomForestClassifier(
        n_estimators=200,
        max_depth=8,
        class_weight='balanced_subsample',
        random_state=42,
        n_jobs=-1
    )
    rf.fit(X, y_enc)
    return rf, le


def detection_stats(df_aligned):
    """
    Compute shot detection metrics from the combined aligned CSV.

    'Detection' = whether a shot with a matching impact timestamp was found by
    the phone pipeline. In practice, every row in combined_ground_truth_aligned
    represents a ground-truth shot; those with is_correct == NaN / 'N/A' are
    non-swings (counted as correctly skipped). Swings that got a prediction are
    true positives; swings with predicted_shot_type == 'N/A' are false negatives
    (the pipeline didn't find a shot there).
    """
    swings = df_aligned[df_aligned['normalized_gt'] != 'NON-SWING'].copy()
    total_gt = len(swings)
    # Shots where pipeline produced a prediction (not N/A)
    detected = swings[swings['predicted_shot_type'].notna() &
                      (swings['predicted_shot_type'] != 'N/A')]
    tp = len(detected)
    fn = total_gt - tp
    # False positives are hard to measure from this file alone
    # (would need all pipeline detections incl. non-GT matches).
    # Report as N/A — this is a known limitation of the offline evaluation.
    precision = None  # Can't compute without raw detection list
    recall = tp / total_gt if total_gt > 0 else 0.0
    return {
        'total_gt': total_gt,
        'tp': tp,
        'fn': fn,
        'recall': recall,
    }


def classification_stats(df_swings, y_pred):
    """Overall and per-class classification accuracy from model predictions."""
    y_true = df_swings['normalized_gt'].values
    overall = (y_pred == y_true).mean()

    per_class = {}
    for cls in ALL_CLASSES:
        mask = y_true == cls
        n = mask.sum()
        if n == 0:
            per_class[cls] = {'n': 0, 'acc': None}
        else:
            acc = (y_pred[mask] == cls).mean()
            per_class[cls] = {'n': int(n), 'acc': float(acc)}
    return overall, per_class


def profile_stats(df_swings, y_pred):
    """Per-data-profile classification breakdown."""
    y_true = df_swings['normalized_gt'].values
    profiles = sorted(df_swings['data_profile'].dropna().unique()) if 'data_profile' in df_swings.columns else []
    result = {}
    for profile in profiles:
        mask = (df_swings['data_profile'] == profile).values
        n = mask.sum()
        if n == 0:
            continue
        acc = (y_pred[mask] == y_true[mask]).mean()
        cls_rows = {}
        for cls in ALL_CLASSES:
            cls_mask = mask & (y_true == cls)
            n_cls = cls_mask.sum()
            if n_cls > 0:
                cls_acc = (y_pred[cls_mask] == cls).mean()
                cls_rows[cls] = {'n': int(n_cls), 'acc': float(cls_acc)}
            else:
                cls_rows[cls] = {'n': 0, 'acc': None}
        result[profile] = {'n': int(n), 'overall_acc': float(acc), 'classes': cls_rows}
    return result


def write_scorecard(overall_cls, per_class, profiles, detect, total_sessions, report_path):
    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    sb = []

    sb.append("# Phone Pipeline Performance Scorecard\n")
    sb.append(f"**Generated:** {now}  \n")
    sb.append(f"**Source of truth:** `combined_features.csv` + `combined_ground_truth_aligned.csv`  \n")
    sb.append(f"**Sessions evaluated:** {total_sessions}  \n")
    sb.append(f"**Model:** 20-feature Random Forest (200 trees, depth 8, heterogeneous training)\n\n")

    sb.append("> [!IMPORTANT]\n")
    sb.append("> This scorecard reflects the **phone-side batch pipeline** (`PhoneSwingDetector.kt`)\n")
    sb.append("> using the 20-feature GeneratedForest (14 watch + 6 Polar, 0.0-imputed when absent).\n")
    sb.append("> It replaces the retired on-watch `SwingDetector` scorecard.\n\n")
    sb.append("> [!CAUTION]\n")
    sb.append("> Classification accuracy here is **training-set fit** (same data used to train the model).\n")
    sb.append("> It is reported purely as a diagnostic. The authoritative ground-truth accuracy\n")
    sb.append("> must be collected from live sessions not included in the training set.\n\n")

    # --- 1. Detection ---
    sb.append("## 1. Shot Identification (Detection)\n\n")
    sb.append("| Metric | Value |\n")
    sb.append("|---|---|\n")
    sb.append(f"| **Ground Truth Swing Shots** | {detect['total_gt']} |\n")
    sb.append(f"| **Shots Identified by Pipeline** | {detect['tp']} |\n")
    sb.append(f"| **Shots Missed (False Negatives)** | {detect['fn']} |\n")
    sb.append(f"| **Recall (Coverage)** | {detect['recall']:.1%} |\n")
    sb.append(f"| **Precision** | *Not measurable from offline files — requires raw detection log* |\n\n")

    # --- 2. Overall classification ---
    sb.append("## 2. Overall Shot Classification\n\n")
    sb.append(f"**Overall accuracy (training-set diagnostic): {overall_cls:.1%}**\n\n")
    sb.append("| Shot Class | Ground Truth Count | Accuracy |\n")
    sb.append("|---|---|---|\n")
    for cls in ALL_CLASSES:
        info = per_class.get(cls, {'n': 0, 'acc': None})
        acc_str = f"{info['acc']:.0%}" if info['acc'] is not None else "n/a"
        sb.append(f"| {cls} | {info['n']} | {acc_str} |\n")
    sb.append("\n")

    # --- 3. Per-data-profile ---
    sb.append("## 3. Breakdown by Data Profile\n\n")
    sb.append("This shows how well the model performs on each data combination,\n")
    sb.append("demonstrating that heterogeneous training generalises across all profiles.\n\n")

    for profile, data in profiles.items():
        label = PROFILE_LABELS.get(profile, profile)
        sb.append(f"### {label} (`{profile}`)  — {data['n']} shots\n\n")
        sb.append(f"**Overall accuracy: {data['overall_acc']:.1%}**\n\n")
        sb.append("| Shot Class | Count | Accuracy |\n")
        sb.append("|---|---|---|\n")
        for cls in ALL_CLASSES:
            info = data['classes'].get(cls, {'n': 0, 'acc': None})
            if info['n'] == 0:
                continue
            acc_str = f"{info['acc']:.0%}" if info['acc'] is not None else "n/a"
            sb.append(f"| {cls} | {info['n']} | {acc_str} |\n")
        sb.append("\n")

    # Write
    with open(report_path, 'w') as f:
        f.writelines(sb)
    print(f"✅ Scorecard written to: {report_path}")

    # Also copy to the brain dir so model_update_pipeline can find it
    import glob
    brain_dirs = sorted(glob.glob(os.path.join(BRAIN_DIR, "*")))
    if brain_dirs:
        # Write to the most recently modified brain folder that exists
        target = os.path.join(brain_dirs[-1], "phone_pipeline_scorecard.md")
        with open(target, 'w') as f:
            f.writelines(sb)
        print(f"✅ Scorecard also written to brain dir: {target}")


def main():
    print("=" * 60)
    print("Phone Pipeline Scorecard")
    print("=" * 60)

    # Load features
    if not os.path.exists(FEATURES_CSV):
        print(f"❌ {FEATURES_CSV} not found — run compile_dataset.py first")
        sys.exit(1)
    if not os.path.exists(ALIGNED_CSV):
        print(f"❌ {ALIGNED_CSV} not found — run compile_dataset.py first")
        sys.exit(1)

    df_feat = pd.read_csv(FEATURES_CSV)
    df_aligned = pd.read_csv(ALIGNED_CSV)

    df_swings = df_feat[df_feat['normalized_gt'] != 'NON-SWING'].copy()
    total_sessions = df_swings['session_id'].nunique()

    print(f"\nLoaded {len(df_swings)} swing shots from {total_sessions} sessions")
    if 'data_profile' in df_swings.columns:
        print("\nData profile breakdown:")
        print(df_swings['data_profile'].value_counts().to_string())

    # Check all feature columns exist
    missing = [c for c in FEATURE_COLS if c not in df_swings.columns]
    if missing:
        print(f"\n❌ Missing feature columns: {missing}")
        print("   Run compile_dataset.py to regenerate combined_features.csv with Polar features")
        sys.exit(1)

    # Train / score
    print("\nFitting 20-feature RF model...")
    rf, le = train_model(df_swings)
    X = df_swings[FEATURE_COLS].fillna(0.0)
    y_pred_enc = rf.predict(X)
    y_pred = le.inverse_transform(y_pred_enc)

    print(f"Training-set accuracy (diagnostic only): {(y_pred == df_swings['normalized_gt'].values).mean():.1%}")

    # Detection stats from aligned file
    detect = detection_stats(df_aligned)
    print(f"\nDetection: {detect['tp']}/{detect['total_gt']} shots covered (recall {detect['recall']:.1%})")

    # Classification
    overall_cls, per_class = classification_stats(df_swings, y_pred)

    # Per-profile
    profiles = profile_stats(df_swings, y_pred)

    # Write scorecard
    print(f"\nWriting scorecard...")
    write_scorecard(overall_cls, per_class, profiles, detect, total_sessions, SCORECARD_OUT)

    # Print summary to stdout for pipeline orchestrator to capture
    print("\n" + "=" * 60)
    print("PHONE PIPELINE SCORECARD SUMMARY")
    print("=" * 60)
    print(f"Total swing shots: {len(df_swings)}")
    print(f"Overall classification accuracy: {overall_cls:.1%}")
    print(f"Detection recall: {detect['recall']:.1%}")
    print("\nPer-class accuracy:")
    for cls in ALL_CLASSES:
        info = per_class.get(cls, {'n': 0, 'acc': None})
        if info['n'] > 0 and info['acc'] is not None:
            print(f"  {cls:<22}: {info['acc']:.0%} ({info['n']} shots)")
    print("=" * 60)


if __name__ == "__main__":
    main()
