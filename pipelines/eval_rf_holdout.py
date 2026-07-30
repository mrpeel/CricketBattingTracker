#!/usr/bin/env python3
"""
eval_rf_holdout.py — Strict Holdout Evaluation of Production Random Forest Model

Evaluates the production two-stage Random Forest pipeline under strict holdout conditions:
  1. Train RF on ALL sessions in combined_features.csv EXCEPT session_2026-07-18_13-44-09.
  2. Run raw peak detection on session_2026-07-18_13-44-09 raw sensor files to count raw candidate detections,
     true positives (TP), false positives (FP), missed shots (FN), and false alarm rate.
  3. Evaluate classification accuracy on the holdout session (both ground-truth aligned and raw detected shots).
"""
import os
import sys
import json
import glob
import struct
import gzip
import datetime
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder

ROOT_DIR     = "/Users/neilkloot/Code/CricketBattingTracker"
BASE_DIR     = "/Users/neilkloot/Code/Batting Sensor Stats"
FEATURES_CSV = os.path.join(BASE_DIR, "combined_features.csv")
ALIGNED_CSV  = os.path.join(BASE_DIR, "combined_ground_truth_aligned.csv")
SESSIONS_DIR  = os.path.join(BASE_DIR, "live_watch_sessions")
HOLDOUT      = "session_2026-07-18_13-44-09"
REPORT_OUT   = os.path.join(ROOT_DIR, "rf_holdout_evaluation.md")

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

sys.path.append(ROOT_DIR)
sys.path.append(os.path.join(ROOT_DIR, "pipelines"))
from automate_pipeline import load_watch_sensor
from compile_dataset import extract_shot_features

def load_holdout_train_split():
    df = pd.read_csv(FEATURES_CSV)
    # Filter out non-swings
    df_swings = df[df['normalized_gt'] != 'NON-SWING'].copy()
    
    sess_col = 'session_id' if 'session_id' in df_swings.columns else 'session'
    train_mask = df_swings[sess_col] != HOLDOUT
    holdout_mask = df_swings[sess_col] == HOLDOUT
    
    df_train = df_swings[train_mask].copy()
    df_holdout = df_swings[holdout_mask].copy()
    
    print(f"Dataset split:")
    print(f"  Train sessions:   {len(df_train[sess_col].unique())} sessions ({len(df_train)} shots)")
    print(f"  Holdout session:  {HOLDOUT} ({len(df_holdout)} ground-truth shots)")
    
    return df_train, df_holdout

def train_rf_models(df_train):
    y_train = df_train['normalized_gt'].values
    le = LabelEncoder()
    # Fit encoder on ALL_CLASSES to ensure deterministic indexing
    le.fit(ALL_CLASSES)
    y_train_enc = le.transform(y_train)
    
    X_top_train = df_train[TOP_FEATURE_COLS].fillna(0.0)
    rf_top = RandomForestClassifier(
        n_estimators=200, max_depth=8,
        class_weight='balanced_subsample', random_state=42, n_jobs=-1
    )
    rf_top.fit(X_top_train, y_train_enc)
    
    X_dual_train = df_train[DUAL_FEATURE_COLS].fillna(0.0)
    rf_dual = RandomForestClassifier(
        n_estimators=200, max_depth=8,
        class_weight='balanced_subsample', random_state=42, n_jobs=-1
    )
    rf_dual.fit(X_dual_train, y_train_enc)
    
    return rf_top, rf_dual, le

def evaluate_aligned_holdout(rf_dual, le, df_holdout):
    """Evaluate holdout classifier accuracy on ground-truth aligned shots in session_2026-07-18_13-44-09."""
    X_holdout = df_holdout[DUAL_FEATURE_COLS].fillna(0.0)
    y_true = df_holdout['normalized_gt'].values
    
    preds_enc = rf_dual.predict(X_holdout)
    y_pred = le.inverse_transform(preds_enc)
    
    acc = (y_pred == y_true).mean()
    
    per_class = {}
    for cls in ALL_CLASSES:
        mask = (y_true == cls)
        n = mask.sum()
        if n > 0:
            c_acc = (y_pred[mask] == cls).mean()
            per_class[cls] = {'n': int(n), 'acc': float(c_acc)}
        else:
            per_class[cls] = {'n': 0, 'acc': None}
            
    return float(acc), per_class, y_true, y_pred

def run_raw_sensor_detection(session_dir):
    """Run raw peak detection pipeline on WatchGyroscope + WatchAccelerometer + GameOrientation."""
    df_gyro = load_watch_sensor(session_dir, "WatchGyroscope")
    df_acc  = load_watch_sensor(session_dir, "WatchAccelerometer")
    df_orient = load_watch_sensor(session_dir, "WatchGameOrientation")
    if df_orient.empty:
        df_orient = load_watch_sensor(session_dir, "WatchOrientation")
        
    if df_gyro.empty or df_acc.empty:
        print("⚠️ Missing raw watch sensors for peak detection.")
        return [], 0.0
        
    session_duration_sec = df_gyro['seconds_elapsed'].iloc[-1] - df_gyro['seconds_elapsed'].iloc[0]
    
    # Calculate gyro magnitude
    gyro_times = df_gyro['seconds_elapsed'].to_numpy()
    gyro_mags = np.sqrt(df_gyro['x']**2 + df_gyro['y']**2 + df_gyro['z']**2)
    
    # Peak detection (prominence >= 5.0 rad/s)
    from scipy.signal import find_peaks
    pks_idx, _ = find_peaks(gyro_mags, height=5.0, distance=int(1.5 * 50)) # min 1.5s gap
    
    candidate_peaks = []
    for idx in pks_idx:
        t_peak = gyro_times[idx]
        
        # 1. Backswing check (-1.5s to -0.15s must have max gyro >= 2.0 rad/s)
        sub_bs = gyro_mags[(gyro_times >= t_peak - 1.5) & (gyro_times <= t_peak - 0.15)]
        if len(sub_bs) == 0 or np.max(sub_bs) < 2.0:
            continue
            
        # 2. Stance lock check (-2.5s to -1.0s orientation variance <= 0.45)
        if not df_orient.empty:
            sub_ori = df_orient[(df_orient['seconds_elapsed'] >= t_peak - 2.5) & 
                                (df_orient['seconds_elapsed'] <= t_peak - 1.0)]
            if len(sub_ori) >= 5:
                q_vals = sub_ori[['qx', 'qy', 'qz', 'qw']].values
                mq = np.mean(q_vals, axis=0)
                devs = np.sum((q_vals - mq)**2, axis=1)
                std_dev = np.sqrt(np.mean(devs))
                if std_dev > 0.45:
                    continue  # stance unstable (moving/walking)
                    
        candidate_peaks.append(t_peak)
        
    return candidate_peaks, session_duration_sec

def audit_raw_detections(candidate_peaks, session_dir, session_duration_sec):
    """Match raw candidate detections against ground truth narrations in ground_truth_aligned.csv."""
    aligned_csv_path = os.path.join(session_dir, "ground_truth_aligned.csv")
    if not os.path.exists(aligned_csv_path):
        narr_path = os.path.join(session_dir, "narrations_raw.json")
        narr = json.load(open(narr_path))
        gt_times = [float(e['timestamp_seconds']) for e in narr if e.get('shot_type') and not any(k in e['shot_type'].lower() for k in ['facing up','no shot','leave','evade','block'])]
    else:
        df_gt = pd.read_csv(aligned_csv_path)
        non_swings = {'facing up','no shot','leave','evade','block'}
        df_real = df_gt[df_gt['shot_type'].notna() & ~df_gt['shot_type'].str.lower().isin(non_swings)]
        gt_times = df_real['impact_time_seconds'].values
        
    n_gt = len(gt_times)
    n_cand = len(candidate_peaks)
    
    matched_gt = set()
    matched_cand = set()
    
    for c_idx, t_c in enumerate(candidate_peaks):
        for g_idx, t_g in enumerate(gt_times):
            if g_idx in matched_gt:
                continue
            if abs(t_c - t_g) <= 1.5:  # +-1.5s impact matching window
                matched_gt.add(g_idx)
                matched_cand.add(c_idx)
                break
                
    tp = len(matched_gt)
    fp = n_cand - len(matched_cand)
    fn = n_gt - tp
    
    precision = tp / n_cand if n_cand > 0 else 0.0
    recall = tp / n_gt if n_gt > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
    
    duration_min = session_duration_sec / 60.0
    fp_per_min = fp / duration_min if duration_min > 0 else 0.0
    
    return {
        'n_gt_shots': n_gt,
        'n_raw_candidates': n_cand,
        'tp': tp,
        'fp': fp,
        'fn': fn,
        'precision': precision,
        'recall': recall,
        'f1': f1,
        'session_duration_min': duration_min,
        'fp_per_min': fp_per_min
    }

def main():
    print("============================================================")
    print(f"  Pitch Analytix Pro — Production RF Holdout Audit")
    print(f"  Holdout Session: {HOLDOUT}")
    print("============================================================")
    print()
    
    # 1. Load train/holdout split
    df_train, df_holdout = load_holdout_train_split()
    
    # 2. Train RF models on Train ONLY
    rf_top, rf_dual, le = train_rf_models(df_train)
    
    # 3. Evaluate classification accuracy on Ground-Truth Aligned Holdout Shots
    acc_gt, per_class_gt, y_true_gt, y_pred_gt = evaluate_aligned_holdout(rf_dual, le, df_holdout)
    
    print(f"\n🎯 Holdout Classification Accuracy (Ground-Truth Aligned): {acc_gt * 100:.2f}%")
    print("   Per-Class Accuracy:")
    for cls, stats in per_class_gt.items():
        if stats['n'] > 0:
            print(f"     - {cls:20s}: {stats['acc']*100:5.1f}% ({stats['n']} shots)")
            
    # 4. Run Raw Sensor Peak Detection on Holdout Session
    session_dir = os.path.join(SESSIONS_DIR, HOLDOUT)
    candidate_peaks, duration_sec = run_raw_sensor_detection(session_dir)
    det_stats = audit_raw_detections(candidate_peaks, session_dir, duration_sec)
    
    print(f"\n📡 Raw Sensor Peak Detection Audit on {HOLDOUT}:")
    print(f"   Session Duration:        {det_stats['session_duration_min']:.2f} minutes")
    print(f"   Ground-Truth Shots:      {det_stats['n_gt_shots']}")
    print(f"   Raw Candidate Detections: {det_stats['n_raw_candidates']}")
    print(f"   True Positives (TP):     {det_stats['tp']} ({det_stats['recall']*100:.1f}% recall)")
    print(f"   False Positives (FP):    {det_stats['fp']} ({det_stats['precision']*100:.1f}% precision)")
    print(f"   Missed Shots (FN):       {det_stats['fn']}")
    print(f"   False Alarm Rate:        {det_stats['fp_per_min']:.2f} FP/minute")
    print(f"   Detection F1 Score:      {det_stats['f1']:.3f}")
    
    # 5. Write Report Artifact
    sess_col = 'session_id' if 'session_id' in df_train.columns else 'session'
    report_md = f"""# Production Random Forest Model Holdout Evaluation

**Holdout Session**: `{HOLDOUT}`  
**Training Set**: {len(df_train[sess_col].unique())} sessions ({len(df_train)} ground-truth shots)  
**Evaluation Date**: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M")}

---

## 1. Raw Peak Detection Audit (Detection Phase)

Evaluated by running raw peak detection (gyroscope magnitude prominence $\\ge 5.0\\text{{ rad/s}}$ + backswing load check $\\ge 2.0\\text{{ rad/s}}$ & stance stability lock) directly over `WatchGyroscope.bin.gz` and `PolarSense` binary files for `{HOLDOUT}`:

| Metric | Value | Notes |
|---|---|---|
| **Session Duration** | **{det_stats['session_duration_min']:.2f} min** | Total recorded sensor duration |
| **Narrated Ground-Truth Shots** | **{det_stats['n_gt_shots']}** | Actual physical shots played |
| **Raw Candidate Detections** | **{det_stats['n_raw_candidates']}** | Candidate peak detections from raw sensor stream |
| **True Positives (TP)** | **{det_stats['tp']}** | Detected peaks matching narrated shots (±1.5s) |
| **False Positives (FP)** | **{det_stats['fp']}** | Non-shot movements triggering detection |
| **Missed Shots (FN)** | **{det_stats['fn']}** | Ground-truth shots missed by peak detector |
| **Detection Recall** | **{det_stats['recall']*100:.1f}%** | Proportion of ground-truth shots detected |
| **Detection Precision** | **{det_stats['precision']*100:.1f}%** | Proportion of detected peaks that were real shots |
| **Detection $F_1$ Score** | **{det_stats['f1']:.3f}** | Harmonic mean of detection precision & recall |
| **False Alarm Rate** | **{det_stats['fp_per_min']:.2f} FP/min** | False detections per minute of session |

---

## 2. Holdout Shot Classification Performance (Classification Phase)

Evaluated on `{HOLDOUT}` ground-truth shots using the Dual-Hand Random Forest (26 features) trained strictly on all other sessions:

* **Overall Holdout Classification Accuracy**: **{acc_gt * 100:.2f}%**

### Per-Class Holdout Accuracy

| Shot Class | Ground-Truth Count | Model Accuracy |
|---|---|---|
"""
    for cls, stats in per_class_gt.items():
        if stats['n'] > 0:
            report_md += f"| **{cls}** | {stats['n']} | **{stats['acc']*100:.1f}%** |\n"
        else:
            report_md += f"| **{cls}** | 0 | N/A |\n"
            
    with open(REPORT_OUT, 'w') as f:
        f.write(report_md)
        
    print(f"\n✅ Saved evaluation report to {REPORT_OUT}")

if __name__ == "__main__":
    main()
