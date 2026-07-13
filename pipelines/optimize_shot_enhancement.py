#!/usr/bin/env python3
import os
import sys
import numpy as np
import pandas as pd

# Configuration
BASE_DIR = "/Users/neilkloot/Code/Batting Sensor Stats"
KOTLIN_CONFIG_PATH = "/Users/neilkloot/Code/CricketBattingTracker/app/src/main/java/com/mrpeel/cricketbattingtracker/services/ShotEnhancementConfig.kt"

# Default heuristic thresholds in case data is insufficient
DEFAULT_THRESHOLDS = {
    "DRIVE_TO_POWER_GYRO_RATIO": 1.35,
    "DRIVE_TO_POWER_ACC_PEAK": 25.0,
    "FLICK_TO_GUIDE_GYRO_RATIO": 0.6,
    "FLICK_TO_GUIDE_GYRO_PEAK": 6.0,
    "PULL_TO_SLOG_GYRO_RATIO": 1.6,
    "PULL_TO_SLOG_GYRO_PEAK": 14.0
}

def load_polar_ground_truth():
    """Scan all sessions and compile shots that contain Polar Sense data."""
    base_live_dir = os.path.join(BASE_DIR, "live_watch_sessions")
    if not os.path.isdir(base_live_dir):
        return pd.DataFrame()

    all_shots = []
    sessions = sorted([
        d for d in os.listdir(base_live_dir)
        if d.startswith("session-") and os.path.isdir(os.path.join(base_live_dir, d))
    ])

    for session_id in sessions:
        csv_path = os.path.join(base_live_dir, session_id, "ground_truth_aligned.csv")
        if os.path.exists(csv_path):
            try:
                df = pd.read_csv(csv_path)
                # Filter rows that have bottom hand metrics populated
                if "bottom_hand_gyro_ratio" in df.columns:
                    valid_df = df[df["bottom_hand_gyro_ratio"].notna() & (df["bottom_hand_gyro_ratio"] > 0)]
                    if not valid_df.empty:
                        valid_df = valid_df.copy()
                        valid_df["session_id"] = session_id
                        all_shots.append(valid_df)
            except Exception as e:
                print(f"⚠️ Error reading {csv_path}: {e}")

    if not all_shots:
        return pd.DataFrame()
    return pd.concat(all_shots, ignore_index=True)

def normalize_shot_class(shot_name):
    if not shot_name:
        return "Unknown"
    s = str(shot_name).lower().strip()
    if "pull" in s or "hook" in s:
        return "PULL/HOOK"
    if "sweep" in s:
        return "SWEEP"
    if "flick" in s or "glance" in s:
        return "GLANCE/FLICK"
    if "cut" in s or "punch" in s:
        return "CUT/PUNCH"
    if "guide" in s or "glide" in s or "deflection" in s or "deflect" in s:
        return "DEFLECTION/GUIDE"
    if "power drive" in s:
        return "POWER DRIVE"
    if "slog" in s or "power shot" in s or "power hit" in s or "loft" in s:
        return "SLOG"
    if any(t in s for t in ["drive", "defence", "defense", "push", "straight", "forward", "block"]):
        return "DRIVE/DEFENCE"
    return "Unknown"

def optimize_drive_to_power(df):
    """Find thresholds to split DRIVE/DEFENCE vs POWER DRIVE/SLOG."""
    sub = df[df["normalized_gt"].isin(["DRIVE/DEFENCE", "POWER DRIVE", "SLOG"])].copy()
    if len(sub) < 5:
        return DEFAULT_THRESHOLDS["DRIVE_TO_POWER_GYRO_RATIO"], DEFAULT_THRESHOLDS["DRIVE_TO_POWER_ACC_PEAK"]

    best_ratio = DEFAULT_THRESHOLDS["DRIVE_TO_POWER_GYRO_RATIO"]
    best_acc = DEFAULT_THRESHOLDS["DRIVE_TO_POWER_ACC_PEAK"]
    best_acc_score = 0

    # Grid search
    for r in np.arange(1.0, 1.8, 0.05):
        for a in np.arange(15.0, 35.0, 1.0):
            # Predict: POWER DRIVE if gyro_ratio > r and acc_peak > a
            preds = np.where((sub["bottom_hand_gyro_ratio"] > r) & (sub["bottom_hand_acc_peak"] > a), "POWER DRIVE", "DRIVE/DEFENCE")
            score = np.sum(preds == sub["normalized_gt"])
            if score > best_acc_score:
                best_acc_score = score
                best_ratio = float(r)
                best_acc = float(a)

    return best_ratio, best_acc

def optimize_flick_to_guide(df):
    """Find thresholds to split GLANCE/FLICK vs DEFLECTION/GUIDE."""
    sub = df[df["normalized_gt"].isin(["GLANCE/FLICK", "DEFLECTION/GUIDE"])].copy()
    if len(sub) < 5:
        return DEFAULT_THRESHOLDS["FLICK_TO_GUIDE_GYRO_RATIO"], DEFAULT_THRESHOLDS["FLICK_TO_GUIDE_GYRO_PEAK"]

    best_ratio = DEFAULT_THRESHOLDS["FLICK_TO_GUIDE_GYRO_RATIO"]
    best_gyro = DEFAULT_THRESHOLDS["FLICK_TO_GUIDE_GYRO_PEAK"]
    best_acc_score = 0

    # Grid search
    for r in np.arange(0.3, 0.9, 0.05):
        for g in np.arange(3.0, 10.0, 0.5):
            # Predict: DEFLECTION/GUIDE if gyro_ratio < r and gyro_peak < g
            preds = np.where((sub["bottom_hand_gyro_ratio"] < r) & (sub["bottom_hand_gyro_peak"] < g), "DEFLECTION/GUIDE", "GLANCE/FLICK")
            score = np.sum(preds == sub["normalized_gt"])
            if score > best_acc_score:
                best_acc_score = score
                best_ratio = float(r)
                best_gyro = float(g)

    return best_ratio, best_gyro

def optimize_pull_to_slog(df):
    """Find thresholds to split PULL/HOOK vs SLOG."""
    sub = df[df["normalized_gt"].isin(["PULL/HOOK", "SLOG"])].copy()
    if len(sub) < 5:
        return DEFAULT_THRESHOLDS["PULL_TO_SLOG_GYRO_RATIO"], DEFAULT_THRESHOLDS["PULL_TO_SLOG_GYRO_PEAK"]

    best_ratio = DEFAULT_THRESHOLDS["PULL_TO_SLOG_GYRO_RATIO"]
    best_gyro = DEFAULT_THRESHOLDS["PULL_TO_SLOG_GYRO_PEAK"]
    best_acc_score = 0

    # Grid search
    for r in np.arange(1.1, 2.0, 0.05):
        for g in np.arange(8.0, 20.0, 0.5):
            # Predict: SLOG if gyro_ratio > r and gyro_peak > g
            preds = np.where((sub["bottom_hand_gyro_ratio"] > r) & (sub["bottom_hand_gyro_peak"] > g), "SLOG", "PULL/HOOK")
            score = np.sum(preds == sub["normalized_gt"])
            if score > best_acc_score:
                best_acc_score = score
                best_ratio = float(r)
                best_gyro = float(g)

    return best_ratio, best_gyro

def main():
    print("============================================================")
    print("🚀 Optimizing Polar Sense Bottom Hand Refinement Thresholds...")
    df = load_polar_ground_truth()
    
    if df.empty:
        print("⚠️ No ground-truth shots with Polar Sense data found. Using default thresholds.")
        drive_ratio, drive_acc = DEFAULT_THRESHOLDS["DRIVE_TO_POWER_GYRO_RATIO"], DEFAULT_THRESHOLDS["DRIVE_TO_POWER_ACC_PEAK"]
        flick_ratio, flick_gyro = DEFAULT_THRESHOLDS["FLICK_TO_GUIDE_GYRO_RATIO"], DEFAULT_THRESHOLDS["FLICK_TO_GUIDE_GYRO_PEAK"]
        pull_ratio, pull_gyro = DEFAULT_THRESHOLDS["PULL_TO_SLOG_GYRO_RATIO"], DEFAULT_THRESHOLDS["PULL_TO_SLOG_GYRO_PEAK"]
    else:
        df["normalized_gt"] = df["shot_type"].apply(normalize_shot_class)
        print(f"📊 Loaded {len(df)} shots containing Polar Sense telemetry.")
        
        drive_ratio, drive_acc = optimize_drive_to_power(df)
        flick_ratio, flick_gyro = optimize_flick_to_guide(df)
        pull_ratio, pull_gyro = optimize_pull_to_slog(df)

    print("\n💡 Optimized Threshold Configurations:")
    print(f"  * DRIVE -> POWER DRIVE: ratio > {drive_ratio:.2f}, acc_peak > {drive_acc:.2f} m/s^2")
    print(f"  * FLICK -> DEFLECTION:  ratio < {flick_ratio:.2f}, gyro_peak < {flick_gyro:.2f} dps")
    print(f"  * PULL  -> SLOG:        ratio > {pull_ratio:.2f}, gyro_peak > {pull_gyro:.2f} dps")

    # Generate Kotlin Config file
    os.makedirs(os.path.dirname(KOTLIN_CONFIG_PATH), exist_ok=True)
    with open(KOTLIN_CONFIG_PATH, "w") as f:
        f.write(f"""package com.mrpeel.cricketbattingtracker.services

/**
 * Auto-generated by optimize_shot_enhancement.py
 * Contains optimized bottom-hand reclassification thresholds.
 */
object ShotEnhancementConfig {{
    const val DRIVE_TO_POWER_GYRO_RATIO = {drive_ratio:.4f}f
    const val DRIVE_TO_POWER_ACC_PEAK = {drive_acc:.4f}f

    const val FLICK_TO_GUIDE_GYRO_RATIO = {flick_ratio:.4f}f
    const val FLICK_TO_GUIDE_GYRO_PEAK = {flick_gyro:.4f}f

    const val PULL_TO_SLOG_GYRO_RATIO = {pull_ratio:.4f}f
    const val PULL_TO_SLOG_GYRO_PEAK = {pull_gyro:.4f}f
}}
""")
    print(f"✅ Generated Kotlin configuration class at: {KOTLIN_CONFIG_PATH}")
    print("============================================================")

if __name__ == "__main__":
    main()
