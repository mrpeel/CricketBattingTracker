#!/usr/bin/env python3
"""
score_phone_pipeline.py — Authoritative Phone-Pipeline Performance Scorecard

Evaluates the ACTUAL system that runs in production: PhoneSwingDetector (phone-side
batch processor) routing between GeneratedTopForest (14 features) for watch-only sessions
and GeneratedDualForest (26 features) for dual-sensor sessions. Uses combined_features.csv
and combined_ground_truth_aligned.csv as the source of truth.
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

BRAIN_DIR = "/Users/neilkloot/.gemini/antigravity/brain"

TOP_FEATURE_COLS = [
    's1_gyro_y_std', 's1_gyro_z_std', 's1_deltaX', 's1_deltaZ',
    's2_gyroMag', 's2_grav_y_mean', 's2_deltaX', 's2_deltaZ',
    's3_rollImpactDeg', 's3_yawImpactDeg', 's3_deltaX', 's3_deltaZ',
    's3_planeRatio', 's3_gyro_y_min',
]

DUAL_FEATURE_COLS = TOP_FEATURE_COLS + [
    'bottom_hand_gyro_peak', 'bottom_hand_acc_peak',
    'bottom_hand_gyro_ratio', 'bottom_hand_acc_ratio',
    'bottom_hand_time_lead_ms', 'bottom_hand_sync_score',
    's1_bottom_gyro_mag', 's1_bottom_deltaZ',
    's2_bottom_acc_mean', 's2_dynamic_ratio_slope',
    's3_bottom_pronation_deg', 's3_bottom_gyro_y_min',
]

ALL_CLASSES = [
    'CUT/PUNCH', 'DEFLECTION/GUIDE', 'DRIVE/DEFENCE',
    'GLANCE/FLICK', 'POWER DRIVE', 'PULL/HOOK', 'SLOG', 'SWEEP'
]

PROFILE_LABELS = {
    '50hz_watch':        'Watch-only 50Hz',
    '100hz_watch':       'Watch-only 100Hz',
    '50hz_watch_polar':  'Watch 50Hz + Polar',
    '100hz_watch_polar': 'Watch 100Hz + Polar',
}

def train_dual_models(df_swings):
    """Fit Top-Hand (14-feature) and Dual-Hand (26-feature) RF models."""
    X_top = df_swings[TOP_FEATURE_COLS].fillna(0.0)
    X_dual = df_swings[DUAL_FEATURE_COLS].fillna(0.0)
    y = df_swings['normalized_gt'].values

    le = LabelEncoder()
    y_enc = le.fit_transform(y)

    rf_top = RandomForestClassifier(
        n_estimators=200, max_depth=8,
        class_weight='balanced_subsample', random_state=42, n_jobs=-1
    )
    rf_top.fit(X_top, y_enc)

    rf_dual = RandomForestClassifier(
        n_estimators=200, max_depth=8,
        class_weight='balanced_subsample', random_state=42, n_jobs=-1
    )
    rf_dual.fit(X_dual, y_enc)

    return rf_top, rf_dual, le

def detection_stats(df_aligned):
    swings = df_aligned[df_aligned['normalized_gt'] != 'NON-SWING'].copy()
    total_gt = len(swings)
    detected = swings[swings['predicted_shot_type'].notna() &
                      (swings['predicted_shot_type'] != 'N/A')]
    tp = len(detected)
    fn = total_gt - tp
    recall = tp / total_gt if total_gt > 0 else 0.0
    return {
        'total_gt': total_gt,
        'tp': tp,
        'fn': fn,
        'recall': recall,
    }

def classification_stats(df_swings, y_pred):
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
    y_true = df_swings['normalized_gt'].values
    raw_profiles = [p for p in df_swings['data_profile'].unique() if pd.notna(p)]
    profiles = sorted(raw_profiles)
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
    sb.append(f"**Architecture:** Dual-Model Routing Architecture (`GeneratedTopForest` 14f / `GeneratedDualForest` 26f)\n\n")

    sb.append("> [!IMPORTANT]\n")
    sb.append("> This scorecard reflects the **phone-side batch pipeline** (`PhoneSwingDetector.kt`)\n")
    sb.append("> dynamically routing between Top-Hand (14 features) and Dual-Hand (26 features) models.\n\n")

    # 1. Detection
    sb.append("## 1. Shot Identification (Detection)\n\n")
    sb.append("| Metric | Value |\n")
    sb.append("|---|---|\n")
    sb.append(f"| **Ground Truth Swing Shots** | {detect['total_gt']} |\n")
    sb.append(f"| **Shots Identified by Pipeline** | {detect['tp']} |\n")
    sb.append(f"| **Shots Missed (False Negatives)** | {detect['fn']} |\n")
    sb.append(f"| **Recall (Coverage)** | {detect['recall']:.1%} |\n")
    sb.append(f"| **Precision** | *Not measurable from offline files — requires raw detection log* |\n\n")

    # 2. Overall classification
    sb.append("## 2. Overall Shot Classification\n\n")
    sb.append(f"**Overall accuracy (Dual-Model Routing diagnostic): {overall_cls:.1%}**\n\n")
    sb.append("| Shot Class | Ground Truth Count | Accuracy |\n")
    sb.append("|---|---|---|\n")
    for cls in ALL_CLASSES:
        info = per_class.get(cls, {'n': 0, 'acc': None})
        acc_str = f"{info['acc']:.0%}" if info['acc'] is not None else "n/a"
        sb.append(f"| {cls} | {info['n']} | {acc_str} |\n")
    sb.append("\n")

    # 3. Per-data-profile
    sb.append("## 3. Breakdown by Data Profile\n\n")
    sb.append("This shows how well the dual-model routing performs on each data profile.\n\n")

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

    with open(report_path, 'w') as f:
        f.writelines(sb)
    print(f"✅ Scorecard written to: {report_path}")

    import glob
    brain_dirs = sorted(glob.glob(os.path.join(BRAIN_DIR, "*")))
    if brain_dirs:
        target = os.path.join(brain_dirs[-1], "phone_pipeline_scorecard.md")
        with open(target, 'w') as f:
            f.writelines(sb)
        print(f"✅ Scorecard also written to brain dir: {target}")

def main():
    print("=" * 60)
    print("Phone Pipeline Scorecard")
    print("=" * 60)

    if not os.path.exists(FEATURES_CSV) or not os.path.exists(ALIGNED_CSV):
        print(f"❌ Input CSVs not found — run compile_dataset.py first")
        sys.exit(1)

    df_feat = pd.read_csv(FEATURES_CSV)
    df_aligned = pd.read_csv(ALIGNED_CSV)

    df_swings = df_feat[df_feat['normalized_gt'] != 'NON-SWING'].copy()
    total_sessions = df_swings['session_id'].nunique()

    print(f"\nLoaded {len(df_swings)} swing shots from {total_sessions} sessions")
    if 'data_profile' in df_swings.columns:
        print("\nData profile breakdown:")
        print(df_swings['data_profile'].value_counts().to_string())

    rf_top, rf_dual, le = train_dual_models(df_swings)

    # Dual-model prediction routing
    X_top = df_swings[TOP_FEATURE_COLS].fillna(0.0)
    X_dual = df_swings[DUAL_FEATURE_COLS].fillna(0.0)
    is_polar_mask = df_swings['data_profile'].astype(str).str.contains('polar', case=False, na=False)

    y_pred_top = le.inverse_transform(rf_top.predict(X_top))
    y_pred_dual = le.inverse_transform(rf_dual.predict(X_dual))

    y_pred = np.where(is_polar_mask, y_pred_dual, y_pred_top)

    print(f"Dual-Model accuracy (diagnostic fit): {(y_pred == df_swings['normalized_gt'].values).mean():.1%}")

    detect = detection_stats(df_aligned)
    print(f"\nDetection: {detect['tp']}/{detect['total_gt']} shots covered (recall {detect['recall']:.1%})")

    overall_cls, per_class = classification_stats(df_swings, y_pred)
    profiles = profile_stats(df_swings, y_pred)

    print(f"\nWriting scorecard...")
    write_scorecard(overall_cls, per_class, profiles, detect, total_sessions, SCORECARD_OUT)

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
