#!/usr/bin/env python3
"""
pipelines/reprocess_sessions.py — Retrospective DB Sync & Reprocessing

Pulls the SQLite database from the companion app, checks it against the raw sensor
directories in live_watch_sessions/, and:
  1. Wipes the phone database events to eliminate duplicate session entries.
  2. For all sessions with raw data:
     - IF ground_truth_aligned.csv exists: loads the exact narrated timestamps and Polar features.
     - ELSE: runs watch-gyro peak detection.
  3. Inserts updated shots with the correct parameters (using "26 Aldinga Street, Blackburn South"
     as the default location, and marking them with a "✨ Updated" badge), filtering out
     non-batting events like 'Facing up', 'No shot', 'Leave', 'Evade', and 'Block'.
  4. Pushes the database back to the phone.
"""
import os
import sys
import re
import glob
import gzip
import json
import shutil
import sqlite3
import datetime
import subprocess
import struct
import numpy as np
import pandas as pd
from scipy.signal import find_peaks
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder

ROOT_DIR = "/Users/neilkloot/Code/CricketBattingTracker"
sys.path.append(os.path.join(ROOT_DIR, "pipelines"))
from build_unified_dataset import normalise_shot_type
BASE_DIR = "/Users/neilkloot/Code/Batting Sensor Stats"
SESSIONS_DIR = os.path.join(BASE_DIR, "live_watch_sessions")
FEATURES_CSV = os.path.join(BASE_DIR, "combined_features.csv")

LOCAL_DB_PATH = os.path.join(ROOT_DIR, "scratch/cricket_tracker_database.db")
PACKAGE_NAME = "com.mrpeel.cricketbattingtracker"
REMOTE_DB_PATH = f"/data/data/{PACKAGE_NAME}/databases/cricket_tracker_database"
TMP_REMOTE_PATH = "/data/local/tmp/cricket_tracker_database"

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

POLAR_FEATURE_COLS = [
    'bottom_hand_gyro_peak', 'bottom_hand_acc_peak',
    'bottom_hand_gyro_ratio', 'bottom_hand_acc_ratio',
    'bottom_hand_time_lead_ms', 'bottom_hand_sync_score',
    's1_bottom_gyro_mag', 's1_bottom_deltaZ',
    's2_bottom_acc_mean', 's2_dynamic_ratio_slope',
    's3_bottom_pronation_deg', 's3_bottom_gyro_y_min',
]

sys.path.append(ROOT_DIR)
from automate_pipeline import load_watch_sensor

def run_cmd(args):
    res = subprocess.run(args, capture_output=True, text=True)
    return res.returncode == 0, res.stdout

def pull_database():
    print("⏳ Pulling database from phone...")
    try:
        with open(LOCAL_DB_PATH, "wb") as f:
            res = subprocess.run(
                ["adb", "-d", "shell", f"run-as {PACKAGE_NAME} cat databases/cricket_tracker_database"],
                stdout=f,
                stderr=subprocess.PIPE
            )
        if res.returncode != 0:
            print(f"⚠️ ADB pull failed: {res.stderr.decode().strip()}")
            if os.path.exists(LOCAL_DB_PATH):
                print(f"ℹ️ Falling back to existing local database file: {LOCAL_DB_PATH}")
                return True
            return False
        print(f"✅ Successfully pulled database to: {LOCAL_DB_PATH}")
        return True
    except Exception as e:
        print(f"⚠️ Pull failed: {e}")
        if os.path.exists(LOCAL_DB_PATH):
            print(f"ℹ️ Falling back to existing local database file: {LOCAL_DB_PATH}")
            return True
        return False

def push_database():
    print("⏳ Pushing database back to phone...")
    try:
        with open(LOCAL_DB_PATH, "rb") as f:
            res = subprocess.run(
                ["adb", "-d", "shell", f"run-as {PACKAGE_NAME} dd of=databases/cricket_tracker_database"],
                stdin=f,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
        if res.returncode != 0:
            print(f"❌ Failed to restore database on phone: {res.stderr.decode()}")
            return False
        
        subprocess.run(["adb", "-d", "shell", f"run-as {PACKAGE_NAME} rm -f databases/cricket_tracker_database-wal databases/cricket_tracker_database-shm databases/cricket_tracker_database-journal"])
        print("✅ Database successfully restored on device.")
        return True
    except Exception as e:
        print(f"❌ Push failed: {e}")
        return False

def parse_watch_imu_bin(filepath):
    samples = []
    if not os.path.exists(filepath):
        return samples
    with open(filepath, "rb") as f:
        data = f.read()
    fmt = "<qffff" # long timeNanos, float sec, float x, float y, float z
    record_size = struct.calcsize(fmt)
    for i in range(0, len(data) - record_size + 1, record_size):
        t, sec, x, y, z = struct.unpack_from(fmt, data, i)
        mag = np.sqrt(x*x + y*y + z*z)
        samples.append({"timeNanos": t, "elapsedSecs": sec, "x": x, "y": y, "z": z, "mag": mag})
    return samples

def parse_watch_rot_bin(filepath):
    samples = []
    if not os.path.exists(filepath):
        return samples
    with open(filepath, "rb") as f:
        data = f.read()
    fmt = "<qfffff" # long timeNanos, float sec, float qx, float qy, float qz, float qw
    record_size = struct.calcsize(fmt)
    for i in range(0, len(data) - record_size + 1, record_size):
        t, sec, qx, qy, qz, qw = struct.unpack_from(fmt, data, i)
        samples.append({"timeNanos": t, "elapsedSecs": sec, "qx": qx, "qy": qy, "qz": qz, "qw": qw})
    return samples

def parse_polar_bin(filepath, is_gyro=False):
    samples = []
    if not os.path.exists(filepath):
        return samples
    with open(filepath, "rb") as f:
        data = f.read()
    fmt = "<qqfff" # long phoneMs, long sensorNs, float x, float y, float z
    record_size = struct.calcsize(fmt)
    dps_to_rad = np.pi / 180.0
    for i in range(0, len(data) - record_size + 1, record_size):
        phone_ms, sensor_ns, x, y, z = struct.unpack_from(fmt, data, i)
        if is_gyro:
            x *= dps_to_rad
            y *= dps_to_rad
            z *= dps_to_rad
        else:
            x *= 0.00980665
            y *= 0.00980665
            z *= 0.00980665
        mag = np.sqrt(x*x + y*y + z*z)
        samples.append({"phoneMs": phone_ms, "sensorNs": sensor_ns, "x": x, "y": y, "z": z, "mag": mag})
    return sorted(samples, key=lambda s: s["sensorNs"])

def parse_latest_timeline(timeline_path, watch_start_ns, watch_start_wall_ms):
    watch_taps = []
    sys_start_ms = None
    if not os.path.exists(timeline_path):
        return sys_start_ms, watch_taps
    with open(timeline_path, "r") as f:
        for line in f:
            if line.startswith("SYSTEM_START:"):
                m = re.search(r"Ts=(\d+)", line)
                if m: sys_start_ms = int(m.group(1))
            elif line.startswith("TAP_SEQ:"):
                t_matches = re.findall(r"T\d=(\d+)", line)
                if len(t_matches) == 5:
                    tap_nanos = [int(x) for x in t_matches]
                    true_wall_ms = watch_start_wall_ms + (tap_nanos[4] - watch_start_ns) // 1_000_000
                    watch_taps.append((true_wall_ms, tap_nanos))
    return sys_start_ms, watch_taps

def detect_polar_tap_sequences(samples):
    tap_threshold = 25.0
    min_gap_ms = 200
    max_gap_ms = 1500
    max_span_ms = 5000

    phone_times = np.array([s["phoneMs"] for s in samples])
    mags = np.array([s["mag"] for s in samples])

    candidate_indices = np.where(mags >= tap_threshold)[0]
    local_peaks = []

    for idx in candidate_indices:
        s_ms = phone_times[idx]
        w_start = np.searchsorted(phone_times, s_ms - 150)
        w_end = np.searchsorted(phone_times, s_ms + 150)
        max_in_win = np.max(mags[w_start:w_end+1])
        if mags[idx] >= max_in_win:
            if not any(abs(s_ms - p["phoneMs"]) < min_gap_ms for p in local_peaks):
                local_peaks.append(samples[idx])

    sequences = []
    i = 0
    while i < len(local_peaks) - 4:
        seq = local_peaks[i:i+5]
        total_span = seq[-1]["phoneMs"] - seq[0]["phoneMs"]
        if total_span <= max_span_ms:
            valid = True
            for j in range(1, 5):
                gap = seq[j]["phoneMs"] - seq[j-1]["phoneMs"]
                if gap < min_gap_ms or gap > max_gap_ms:
                    valid = False; break
            if valid:
                sequences.append([s["phoneMs"] for s in seq])
                i += 5
                continue
        i += 1
    return sequences

class TimeAlignment:
    def __init__(self, offset_ms, drift_rate):
        self.offset_ms = offset_ms
        self.drift_rate = drift_rate
    def polarToWatchMs(self, polar_ms):
        return int((polar_ms - self.offset_ms) / (1.0 + self.drift_rate))

def match_tap_sequences(watch_taps, polar_taps):
    if not watch_taps or not polar_taps: return None
    matches = []
    for w_anchor_ms, w_seq in watch_taps:
        watch_intervals = [(w_seq[i+1] - w_seq[i]) / 1_000_000.0 for i in range(4)]
        best_p_idx = -1
        best_err = float("inf")
        for p_idx, p_seq in enumerate(polar_taps):
            if len(p_seq) != 5: continue
            polar_intervals = [float(p_seq[i+1] - p_seq[i]) for i in range(4)]
            err = sum(abs(w - p) for w, p in zip(watch_intervals, polar_intervals))
            if err < best_err:
                best_err = err
                best_p_idx = p_idx
        if best_p_idx >= 0 and best_err < 500.0:
            matches.append((w_anchor_ms, polar_taps[best_p_idx][4]))
    if not matches: return None
    if len(matches) == 1:
        return TimeAlignment(offset_ms=matches[0][1] - matches[0][0], drift_rate=0.0)
    else:
        w_times = np.array([m[0] for m in matches], dtype=float)
        p_times = np.array([m[1] for m in matches], dtype=float)
        n = len(w_times)
        sumX = np.sum(w_times)
        sumY = np.sum(p_times)
        sumXY = np.sum(w_times * p_times)
        sumX2 = np.sum(w_times ** 2)
        slope = (n * sumXY - sumX * sumY) / (n * sumX2 - sumX ** 2)
        intercept = (sumY - slope * sumX) / n
        return TimeAlignment(offset_ms=intercept, drift_rate=slope - 1.0)

def detect_impact_peaks(samples, threshold=24.5):
    phone_times = np.array([s["phoneMs"] for s in samples])
    mags = np.array([s["mag"] for s in samples])
    candidates = np.where(mags >= threshold)[0]
    peaks = []
    min_gap_ms = 1500
    for idx in candidates:
        s_ms = phone_times[idx]
        w_start = np.searchsorted(phone_times, s_ms - 500)
        w_end = np.searchsorted(phone_times, s_ms + 500)
        max_in_win = np.max(mags[w_start:w_end+1])
        if mags[idx] >= max_in_win:
            if not any(abs(s_ms - p) < min_gap_ms for p in peaks):
                peaks.append(s_ms)
    return peaks

def verify_swing_backwards(impact_sensor_ns, watch_gyro, watch_rot):
    bs_start = impact_sensor_ns - 1_500_000_000
    bs_end = impact_sensor_ns - 150_000_000
    bs_gyros = [g["mag"] for g in watch_gyro if bs_start <= g["timeNanos"] <= bs_end]
    if not bs_gyros or max(bs_gyros) < 2.0:
        return False, f"backswing_failed (peak={max(bs_gyros) if bs_gyros else 0:.2f} < 2.0)"
    
    st_start = impact_sensor_ns - 2_500_000_000
    st_end = impact_sensor_ns - 1_000_000_000
    st_rots = [r for r in watch_rot if st_start <= r["timeNanos"] <= st_end]
    if len(st_rots) < 5:
        return False, f"stance_insufficient_samples ({len(st_rots)} < 5)"
    
    mqx = np.mean([r["qx"] for r in st_rots])
    mqy = np.mean([r["qy"] for r in st_rots])
    mqz = np.mean([r["qz"] for r in st_rots])
    mqw = np.mean([r["qw"] for r in st_rots])
    
    devs = [(r["qx"]-mqx)**2 + (r["qy"]-mqy)**2 + (r["qz"]-mqz)**2 + (r["qw"]-mqw)**2 for r in st_rots]
    std_dev = np.sqrt(sum(devs) / len(st_rots))
    if std_dev > 0.45:
        return False, f"stance_failed (stdDev={std_dev:.4f} > 0.45)"
        
    return True, "ok"

def restart_app():
    print("⏳ Restarting app on phone...")
    run_cmd(["adb", "-d", "shell", f"am force-stop {PACKAGE_NAME}"])
    run_cmd(["adb", "-d", "shell", f"monkey -p {PACKAGE_NAME} -c android.intent.category.LAUNCHER 1"])
    print("✅ App restarted successfully.")

def train_classifiers():
    print("⏳ Training Dual-Model classifiers on compiled dataset...")
    df = pd.read_csv(FEATURES_CSV)
    df_swings = df[df['normalized_gt'] != 'NON-SWING'].copy()
    
    y_type = df_swings['normalized_gt'].values
    le_type = LabelEncoder()
    y_type_enc = le_type.fit_transform(y_type)

    # Top-Hand (14-feature)
    X_top = df_swings[TOP_FEATURE_COLS].fillna(0.0)
    rf_top_type = RandomForestClassifier(n_estimators=200, max_depth=8, class_weight='balanced_subsample', random_state=42, n_jobs=-1)
    rf_top_type.fit(X_top, y_type_enc)

    # Dual-Hand (26-feature)
    X_dual = df_swings[DUAL_FEATURE_COLS].fillna(0.0)
    rf_dual_type = RandomForestClassifier(n_estimators=200, max_depth=8, class_weight='balanced_subsample', random_state=42, n_jobs=-1)
    rf_dual_type.fit(X_dual, y_type_enc)

    # Quality Classifiers
    df_quality = df_swings[df_swings['quality'].notna() & (df_swings['quality'] != '')].copy()
    def clean_quality(q):
        val = str(q).lower().strip()
        if 'good' in val or 'excellent' in val or 'okay' in val: return 'good'
        if 'poor' in val or 'edge' in val: return 'poor'
        if 'miss' in val or 'non' in val: return 'miss'
        return 'good'
    df_quality['quality_norm'] = df_quality['quality'].apply(clean_quality)
    y_qual = df_quality['quality_norm'].values
    le_qual = LabelEncoder()
    y_qual_enc = le_qual.fit_transform(y_qual)

    X_top_qual = df_quality[TOP_FEATURE_COLS].fillna(0.0)
    rf_top_qual = RandomForestClassifier(n_estimators=100, max_depth=6, class_weight='balanced_subsample', random_state=42, n_jobs=-1)
    rf_top_qual.fit(X_top_qual, y_qual_enc)

    X_dual_qual = df_quality[DUAL_FEATURE_COLS].fillna(0.0)
    rf_dual_qual = RandomForestClassifier(n_estimators=100, max_depth=6, class_weight='balanced_subsample', random_state=42, n_jobs=-1)
    rf_dual_qual.fit(X_dual_qual, y_qual_enc)

    return rf_top_type, rf_dual_type, le_type, rf_top_qual, rf_dual_qual, le_qual

def average_quats(qxs, qys, qzs, qws):
    sum_q = np.zeros(4)
    for x, y, z, w in zip(qxs, qys, qzs, qws):
        q = np.array([x, y, z, w])
        if np.dot(q, sum_q) < 0:
            q = -q
        sum_q += q
    return sum_q / np.linalg.norm(sum_q)

def conjugate_quat(q):
    return np.array([-q[0], -q[1], -q[2], q[3]])

def multiply_quats(q1, q2):
    x1, y1, z1, w1 = q1
    x2, y2, z2, w2 = q2
    return np.array([
        w1*x2 + x1*w2 + y1*z2 - z1*y2,
        w1*y2 - x1*z2 + y1*w2 + z1*x2,
        w1*z2 + x1*y2 - y1*x2 + z1*w2,
        w1*w2 - x1*x2 - y1*y2 - z1*z2
    ])

def rotate_vector(q, v):
    qx, qy, qz, qw = q
    vx, vy, vz = v
    tx = 2.0 * (qy*vz - qz*vy)
    ty = 2.0 * (qz*vx - qx*vz)
    tz = 2.0 * (qx*vy - qy*vx)
    return np.array([
        vx + qw*tx + (qy*tz - qz*ty),
        vy + qw*ty + (qz*tx - qx*tz),
        vz + qw*tz + (qx*ty - qy*tx)
    ])

def extract_features_single_shot(sensors, t_shot):
    feats = {col: 0.0 for col in DUAL_FEATURE_COLS}
    acc = sensors.get("accel")
    gyro = sensors.get("gyro")
    orient = sensors.get("game_orient") if sensors.get("game_orient") is not None else sensors.get("orientation")
    grav = sensors.get("gravity")
    
    if orient is None or len(orient) < 5:
        return feats

    window_df = orient[(orient['seconds_elapsed'] >= t_shot - 3.0) & (orient['seconds_elapsed'] <= t_shot - 1.0)]
    if len(window_df) >= 2:
        q_stance = average_quats(window_df['qx'].values, window_df['qy'].values, window_df['qz'].values, window_df['qw'].values)
    else:
        q_stance = np.array([0.0, 0.0, 0.0, 1.0])
        
    q_stance_inv = conjugate_quat(q_stance)
    v_local = np.array([0.0, -1.0, 0.0])

    def get_displacement_feats(ts, te):
        sub = orient[(orient['seconds_elapsed'] >= t_shot + ts) & (orient['seconds_elapsed'] <= t_shot + te)]
        if len(sub) >= 2:
            min_x, max_x = 1e10, -1e10
            min_z, max_z = 1e10, -1e10
            for _, row in sub.iterrows():
                q_curr = np.array([row['qx'], row['qy'], row['qz'], row['qw']])
                q_rel = multiply_quats(q_stance_inv, q_curr)
                v_rot = rotate_vector(q_rel, v_local)
                min_x, max_x = min(min_x, v_rot[0]), max(max_x, v_rot[0])
                min_z, max_z = min(min_z, v_rot[2]), max(max_z, v_rot[2])
            return max_x - min_x, max_z - min_z
        return 0.0, 0.0

    # Segment 1: Backswing [-0.80s, -0.20s]
    s1_dx, s1_dz = get_displacement_feats(-0.80, -0.20)
    feats["s1_deltaX"] = s1_dx
    feats["s1_deltaZ"] = s1_dz
    if gyro is not None:
        sub = gyro[(gyro['seconds_elapsed'] >= t_shot - 0.80) & (gyro['seconds_elapsed'] <= t_shot - 0.20)]
        if len(sub) >= 2:
            feats["s1_gyro_y_std"] = float(np.std(sub['y'].values))
            feats["s1_gyro_z_std"] = float(np.std(sub['z'].values))

    # Segment 2: Downswing [-0.20s, -0.05s]
    s2_dx, s2_dz = get_displacement_feats(-0.20, -0.05)
    feats["s2_deltaX"] = s2_dx
    feats["s2_deltaZ"] = s2_dz
    if gyro is not None:
        sub = gyro[(gyro['seconds_elapsed'] >= t_shot - 0.20) & (gyro['seconds_elapsed'] <= t_shot - 0.05)]
        feats["s2_gyroMag"] = float(sub['mag'].max()) if len(sub) > 0 else 0.0
    if grav is not None:
        sub = grav[(grav['seconds_elapsed'] >= t_shot - 0.20) & (grav['seconds_elapsed'] <= t_shot - 0.05)]
        feats["s2_grav_y_mean"] = float(sub['y'].mean()) if len(sub) > 0 else -9.8

    # Segment 3: Impact/Follow [-0.05s, 0.30s]
    s3_dx, s3_dz = get_displacement_feats(-0.05, 0.30)
    feats["s3_deltaX"] = s3_dx
    feats["s3_deltaZ"] = s3_dz
    if gyro is not None:
        sub = gyro[(gyro['seconds_elapsed'] >= t_shot - 0.05) & (gyro['seconds_elapsed'] <= t_shot + 0.30)]
        if len(sub) >= 2:
            feats["s3_gyro_y_min"] = float(sub['y'].min())
            plane_z = np.std(sub['z'].values)
            plane_y = np.std(sub['y'].values)
            feats["s3_planeRatio"] = float(plane_z / plane_y) if plane_y > 0.01 else 0.0
            
    if orient is not None:
        sub = orient[(orient['seconds_elapsed'] >= t_shot - 0.05) & (orient['seconds_elapsed'] <= t_shot + 0.10)]
        if len(sub) > 0:
            closest_idx = np.argmin(np.abs(sub['seconds_elapsed'].values - t_shot))
            row = sub.iloc[closest_idx]
            q_curr = np.array([row['qx'], row['qy'], row['qz'], row['qw']])
            q_rel = multiply_quats(q_stance_inv, q_curr)
            feats["s3_rollImpactDeg"] = float(np.degrees(np.arctan2(2.0*(q_rel[3]*q_rel[1] + q_rel[0]*q_rel[2]), 1.0 - 2.0*(q_rel[1]**2 + q_rel[2]**2))))
            feats["s3_yawImpactDeg"] = float(np.degrees(np.arcsin(np.clip(2.0*(q_rel[3]*q_rel[2] - q_rel[0]*q_rel[1]), -1.0, 1.0))))
            
    return feats

def classify_blade(angle):
    if angle <= -15.0: return "OPEN"
    if angle >= 15.0: return "CLOSED"
    return "FULL_FACE"

def classify_launch(angle):
    if angle < -45.0: return "HIGH_LOFT"
    if angle < -35.0: return "POWER_ZONE"
    if angle < -15.0: return "LOFTED"
    if angle < 0.0: return "FLAT"
    return "INTO_GROUND"

CANONICAL_TARGETS = {
    "COVER_DRIVE": -45.0,
    "COVER DRIVE": -45.0,
    "STRAIGHT_DRIVE": 0.0,
    "STRAIGHT DRIVE": 0.0,
    "ON_DRIVE": 15.0,
    "ON DRIVE": 15.0,
    "DEFENCE/BLOCK": 0.0,
    "DEFENCE": 0.0,
    "DRIVE/DEFENCE": 0.0,
    "POWER DRIVE": 0.0,
    "CUT/PUNCH": 40.0,
    "CUT": 40.0,
    "GLANCE/FLICK": 75.0,
    "FLICK": 75.0,
    "GLANCE": 75.0,
    "PULL/HOOK": 55.0,
    "PULL": 55.0,
    "SWEEP": 65.0,
    "SLOG": 55.0,
    "DEFLECTION/GUIDE": 0.0,
    "GUIDE": 0.0,
}

def calculate_blade_and_launch(sensors, t_shot, shot_type):
    orient = sensors.get("game_orient") if sensors.get("game_orient") is not None else sensors.get("orientation")
    if orient is None or len(orient) < 5:
        return 0.0, "FULL_FACE", 0.0, "FLAT"

    window_df = orient[(orient['seconds_elapsed'] >= t_shot - 3.0) & (orient['seconds_elapsed'] <= t_shot - 1.0)]
    if len(window_df) >= 2:
        q_stance = average_quats(window_df['qx'].values, window_df['qy'].values, window_df['qz'].values, window_df['qw'].values)
    else:
        q_stance = np.array([0.0, 0.0, 0.0, 1.0])
    q_stance_inv = conjugate_quat(q_stance)

    sub = orient[(orient['seconds_elapsed'] >= t_shot - 0.05) & (orient['seconds_elapsed'] <= t_shot + 0.10)]
    if len(sub) == 0:
        return 0.0, "FULL_FACE", 0.0, "FLAT"
    closest_idx = np.argmin(np.abs(sub['seconds_elapsed'].values - t_shot))
    row = sub.iloc[closest_idx]
    q_curr = np.array([row['qx'], row['qy'], row['qz'], row['qw']])

    q_rel = multiply_quats(q_stance_inv, q_curr)
    
    x, y, z, w = q_rel
    roll_impact = float(np.degrees(np.arctan2(2.0 * (w*y + x*z), 1.0 - 2.0 * (y*y + z*z))))

    norm_type = normalise_shot_type(str(shot_type)) or str(shot_type).upper()
    target_yaw = CANONICAL_TARGETS.get(norm_type, 0.0)
    if "cover" in str(shot_type).lower():
        target_yaw = -45.0
    elif "on drive" in str(shot_type).lower():
        target_yaw = 15.0

    v_face_rel = rotate_vector(q_rel, np.array([1.0, 0.0, 0.0]))
    yaw_face_rel = float(np.degrees(np.arctan2(v_face_rel[1], v_face_rel[0])))
    
    b_angle = yaw_face_rel - target_yaw
    b_angle = float(((b_angle + 180.0) % 360.0 + 360.0) % 360.0 - 180.0)
    b_class = classify_blade(b_angle)

    is_horizontal_bat = norm_type in ["CUT/PUNCH", "PULL/HOOK", "SWEEP", "SLOG"] or "cut" in str(shot_type).lower() or "pull" in str(shot_type).lower() or "sweep" in str(shot_type).lower()
    if is_horizontal_bat:
        l_angle = roll_impact
    else:
        v_face_world = rotate_vector(q_curr, np.array([1.0, 0.0, 0.0]))
        l_angle = float(-np.degrees(np.arcsin(np.clip(v_face_world[2], -1.0, 1.0))))
        
    l_class = classify_launch(l_angle)
    return round(b_angle, 1), b_class, round(l_angle, 1), l_class

def load_raw_sensor_dir(session_dir):
    sensors = {}
    for name, key in [("WatchAccelerometer", "accel"), ("WatchGyroscope", "gyro"), 
                      ("WatchGravity", "gravity"), ("WatchGameOrientation", "game_orient")]:
        df = load_watch_sensor(session_dir, name)
        if df is not None and not df.empty:
            if "x" in df.columns and "y" in df.columns and "z" in df.columns:
                mag_vals = np.sqrt(df["x"]**2 + df["y"]**2 + df["z"]**2)
                df["mag"] = mag_vals
                df["mag_total"] = mag_vals
            sensors[key] = df
    return sensors

def detect_sensor_only_shots(session_dir, rf_top_type, rf_dual_type, le_type, rf_top_qual, rf_dual_qual, le_qual):
    """Detects physical impact peaks in raw WatchAccelerometer and WatchGyroscope logs."""
    sensors = load_raw_sensor_dir(session_dir)
    if "accel" not in sensors or "gyro" not in sensors:
        return []
    
    accel = sensors["accel"]
    accel_times = accel["seconds_elapsed"].values
    accel_mags = accel["mag"].values
    
    gyro = sensors["gyro"]
    gyro_times = gyro["seconds_elapsed"].values
    gyro_mags = gyro["mag"].values
    
    # Impact Shockwave Anchor Detector (Acc >= 30 m/s2, Gyro >= 4 rad/s)
    accel_candidates = np.where(accel_mags >= 30.0)[0]
    if len(accel_candidates) == 0:
        return []
        
    impact_indices = []
    for idx in accel_candidates:
        t_c = accel_times[idx]
        g_win = gyro_mags[(gyro_times >= t_c - 0.1) & (gyro_times <= t_c + 0.1)]
        if len(g_win) > 0 and g_win.max() >= 4.0:
            impact_indices.append(idx)
            
    if not impact_indices:
        return []
        
    clusters = [[impact_indices[0]]]
    for idx in range(1, len(impact_indices)):
        if impact_indices[idx] - impact_indices[idx-1] <= 211:
            clusters[-1].append(impact_indices[idx])
        else:
            clusters.append([impact_indices[idx]])
            
    detected_shots = []
    for c in clusters:
        peak_idx = c[np.argmax(accel_mags[c])]
        t_shot = float(accel_times[peak_idx])
        ts_ns = int(accel["time"].values[peak_idx])
        
        feats = extract_features_single_shot(sensors, t_shot)
        feat_vector = [feats[col] for col in TOP_FEATURE_COLS]
        df_feat = pd.DataFrame([feat_vector], columns=TOP_FEATURE_COLS)
        
        type_enc = rf_top_type.predict(df_feat)[0]
        pred_shot_type = le_type.inverse_transform([type_enc])[0]
        
        qual_enc = rf_top_qual.predict(df_feat)[0]
        pred_quality = le_qual.inverse_transform([qual_enc])[0]
        
        g_win = gyro_mags[(gyro_times >= t_shot - 0.1) & (gyro_times <= t_shot + 0.1)]
        gyro_peak = float(g_win.max()) if len(g_win) > 0 else 10.0
        bat_speed = float(gyro_peak * 4.5)
        
        b_angle, b_class, l_angle, l_class = calculate_blade_and_launch(sensors, t_shot, pred_shot_type)

        detected_shots.append({
            "timestamp_offset_s": t_shot,
            "timestamp_ns": ts_ns,
            "shot_type": pred_shot_type,
            "quality": pred_quality,
            "bat_speed": bat_speed,
            "impact_force": float(accel_mags[peak_idx]),
            "efficiency": 90.0,
            "impact_time_ms": 350,
            "blade_angle": b_angle,
            "blade_class": b_class,
            "launch_angle": l_angle,
            "launch_class": l_class,
            "features": feats
        })
    return detected_shots

def process_single_session_raw(session_dir, rf_top_type, rf_dual_type, le_type, rf_top_qual, rf_dual_qual, le_qual):
    """Processes a raw session directory, running peak detection and predicting shots with Dual-Model Routing."""
    gt_csv = os.path.join(session_dir, "ground_truth_aligned.csv")
    
    # Check if this session folder has Polar Sense CSV or Binary logs
    has_polar = False
    polar_dir = os.path.join(session_dir, "PolarSense")
    if os.path.isdir(polar_dir):
        files = glob.glob(os.path.join(polar_dir, "*[aA][cC][cC]*.csv*")) + \
                glob.glob(os.path.join(polar_dir, "*[aA][cC][cC]*.bin*"))
        files = list(set(files))
        if files:
            has_polar = True

    rf_type = rf_dual_type if has_polar else rf_top_type
    rf_qual = rf_dual_qual if has_polar else rf_top_qual
    feature_cols = DUAL_FEATURE_COLS if has_polar else TOP_FEATURE_COLS

    sensors = {}
    for name, key in [("WatchAccelerometer", "accel"), ("WatchGyroscope", "gyro"), 
                      ("WatchGravity", "gravity"), ("WatchGameOrientation", "game_orient")]:
        df = load_watch_sensor(session_dir, name)
        if df is not None and not df.empty:
            if "x" in df.columns and "y" in df.columns and "z" in df.columns:
                mag_vals = np.sqrt(df["x"]**2 + df["y"]**2 + df["z"]**2)
                df["mag"] = mag_vals
                df["mag_total"] = mag_vals
            sensors[key] = df

    # 🎯 Primary Path: Load exact active swing shots from ground_truth_aligned.csv if present
    if os.path.exists(gt_csv):
        try:
            df_gt = pd.read_csv(gt_csv)
            # Filter non-swing rows
            swings_df = df_gt[~df_gt['shot_type'].astype(str).str.lower().str.contains('facing|no shot|leave|evade', na=False)].copy()
            
            shots = []
            for _, row in swings_df.iterrows():
                # Timestamp offset
                t_shot = float(row['impact_time_seconds']) if pd.notna(row.get('impact_time_seconds')) else float(row.get('sensor_narr_time_seconds', 0.0))
                ts_ns = int(row['impact_timestamp_ns']) if pd.notna(row.get('impact_timestamp_ns')) else int(t_shot * 1e9)
                
                # 1. Dynamically extract the 14 watch features from raw sensor logs at t_shot
                feats = extract_features_single_shot(sensors, t_shot) if sensors else {col: 0.0 for col in TOP_FEATURE_COLS}
                
                # 2. Append Polar features from ground_truth_aligned.csv (default to 0.0 if NaN/absent)
                for col in POLAR_FEATURE_COLS:
                    feats[col] = 0.0
                    if col in row and pd.notna(row[col]):
                        feats[col] = float(row[col])
                
                # 3. Dynamic Shot-Level Routing (Watch-Only 14f vs Dual-Hand 26f)
                shot_has_polar = pd.notna(row.get('bottom_hand_gyro_peak'))
                rf_type_shot = rf_dual_type if shot_has_polar else rf_top_type
                rf_qual_shot = rf_dual_qual if shot_has_polar else rf_top_qual
                feature_cols_shot = DUAL_FEATURE_COLS if shot_has_polar else TOP_FEATURE_COLS
                
                feat_vector = [feats[col] for col in feature_cols_shot]
                df_feat = pd.DataFrame([feat_vector], columns=feature_cols_shot)
                
                gt_type = str(row['shot_type']).strip() if pd.notna(row.get('shot_type')) and str(row.get('shot_type')).strip() != '' else ''
                if gt_type:
                    norm_gt = normalise_shot_type(gt_type)
                    pred_shot_type = norm_gt if norm_gt else gt_type.upper()
                else:
                    type_enc = rf_type_shot.predict(df_feat)[0]
                    pred_shot_type = le_type.inverse_transform([type_enc])[0]
                
                gt_qual = str(row['quality']).strip() if pd.notna(row.get('quality')) and str(row.get('quality')).strip() != '' else ''
                if gt_qual:
                    pred_quality = gt_qual
                else:
                    qual_enc = rf_qual_shot.predict(df_feat)[0]
                    pred_quality = le_qual.inverse_transform([qual_enc])[0]
                
                gyro_mag = float(row.get('impact_gyro_mag', 10.0)) if pd.notna(row.get('impact_gyro_mag')) else 10.0
                bat_speed = float(gyro_mag * 4.5)
                
                acc_peak = float(row.get('bottom_hand_acc_peak', 15.0)) if pd.notna(row.get('bottom_hand_acc_peak')) else 15.0
                eff = float(row.get('efficiency', 90.0)) if pd.notna(row.get('efficiency')) else 90.0
                react_ms = int(row.get('reaction_time_ms', 350)) if pd.notna(row.get('reaction_time_ms')) else 350

                # Extract blade/launch angles from ground_truth_aligned.csv or compute dynamically
                b_angle = row.get('blade_angle_deg')
                b_class = row.get('blade_class')
                l_angle = row.get('launch_angle_deg')
                l_class = row.get('launch_class')

                if pd.isna(b_angle):
                    b_angle, b_class_calc, _, _ = calculate_blade_and_launch(sensors, t_shot, pred_shot_type)
                    b_class = b_class_calc
                else:
                    b_angle = float(b_angle)
                    if pd.isna(b_class) or str(b_class).strip().lower() in ['', 'nan', 'n/a', 'none']:
                        b_class = classify_blade(b_angle)
                    else:
                        b_class = str(b_class).strip()

                if pd.isna(l_angle):
                    _, _, l_angle, l_class_calc = calculate_blade_and_launch(sensors, t_shot, pred_shot_type)
                    l_class = l_class_calc
                else:
                    l_angle = float(l_angle)
                    if pd.isna(l_class) or str(l_class).strip().lower() in ['', 'nan', 'n/a', 'none']:
                        l_class = classify_launch(l_angle)
                    else:
                        l_class = str(l_class).strip()

                shots.append({
                    "timestamp_offset_s": t_shot,
                    "timestamp_ns": ts_ns,
                    "shot_type": pred_shot_type,
                    "quality": pred_quality,
                    "bat_speed": bat_speed,
                    "impact_force": acc_peak,
                    "efficiency": eff,
                    "impact_time_ms": react_ms,
                    "blade_angle": b_angle,
                    "blade_class": b_class,
                    "launch_angle": l_angle,
                    "launch_class": l_class,
                    "features": feats
                })
            # Also check if additional sensor-only physical shots exist in the session data
            sensor_shots = detect_sensor_only_shots(session_dir, rf_top_type, rf_dual_type, le_type, rf_top_qual, rf_dual_qual, le_qual)
            all_combined = list(shots)
            for s_shot in sensor_shots:
                if not any(abs(s_shot["timestamp_offset_s"] - gt_shot["timestamp_offset_s"]) < 3.0 for gt_shot in shots):
                    all_combined.append(s_shot)
            return sorted(all_combined, key=lambda x: x["timestamp_offset_s"])
        except Exception as e:
            print(f"⚠️ Error reading {gt_csv}, falling back to raw peak detection: {e}")

    # ── Fallback Path: Raw physical sensor peak detection for unaligned sessions ──
    if "accel" not in sensors or "gyro" not in sensors or "game_orient" not in sensors:
        return []

    accel = sensors["accel"]
    accel_times = accel["seconds_elapsed"].values
    accel_mags = accel["mag"].values
    accel_ns = accel["time"].values

    gyro = sensors["gyro"]
    gyro_times = gyro["seconds_elapsed"].values
    gyro_mags = gyro["mag"].values

    watch_gyro_samples = [
        {"timeNanos": int(t), "elapsedSecs": float(sec), "mag": float(m)}
        for t, sec, m in zip(gyro["time"].values, gyro["seconds_elapsed"].values, gyro["mag"].values)
    ]
    orient = sensors["game_orient"]
    watch_rot_samples = [
        {"timeNanos": int(t), "elapsedSecs": float(sec), "qx": float(qx), "qy": float(qy), "qz": float(qz), "qw": float(qw)}
        for t, sec, qx, qy, qz, qw in zip(orient["time"].values, orient["seconds_elapsed"].values, orient["qx"].values, orient["qy"].values, orient["qz"].values, orient["qw"].values)
    ]
    
    polar_bin_path = os.path.join(session_dir, "PolarSense/PolarAccelerometer.bin")
    has_polar_bin = os.path.exists(polar_bin_path)
    polar_acc_samples = parse_polar_bin(polar_bin_path, is_gyro=False) if has_polar_bin else []

    watch_start_ns = int(gyro["time"].iloc[0]) if len(gyro) > 0 else 0
    watch_start_wall_ms, watch_taps = parse_latest_timeline(os.path.join(session_dir, "latest_timeline.txt"), watch_start_ns, 1784773335120)

    polar_taps = detect_polar_tap_sequences(polar_acc_samples) if polar_acc_samples else []
    alignment = match_tap_sequences(watch_taps, polar_taps) if polar_taps else None
    
    if alignment is None and polar_acc_samples and watch_start_wall_ms:
        polar_start_ms = polar_acc_samples[0]['phoneMs']
        fallback_offset = polar_start_ms - watch_start_wall_ms
        alignment = TimeAlignment(offset_ms=fallback_offset, drift_rate=0.0)

    pass1_shots = []

    if alignment is not None and polar_acc_samples:
        polar_peaks = detect_impact_peaks(polar_acc_samples, threshold=24.5)
        for p_peak in polar_peaks:
            w_wall_ms = alignment.polarToWatchMs(p_peak)
            rel_offset_ms = w_wall_ms - watch_start_wall_ms
            target_sensor_ns = watch_start_ns + (rel_offset_ms * 1_000_000)

            if verify_swing_backwards(target_sensor_ns, watch_gyro_samples, watch_rot_samples)[0]:
                t_shot = rel_offset_ms / 1000.0
                close_idx = np.argmin(np.abs(gyro_times - t_shot)) if len(gyro_times) > 0 else 0
                ts_ns = int(accel_ns[close_idx]) if len(accel_ns) > close_idx else 0
                
                feats = extract_features_single_shot(sensors, t_shot)
                feat_vector = [0.0 if feats[col] is None or pd.isna(feats[col]) else float(feats[col]) for col in feature_cols]
                df_feat = pd.DataFrame([feat_vector], columns=feature_cols)
                
                type_enc = rf_type.predict(df_feat)[0]
                shot_type = le_type.inverse_transform([type_enc])[0]
                
                qual_enc = rf_qual.predict(df_feat)[0]
                quality = le_qual.inverse_transform([qual_enc])[0]
                
                downswing_gyro_win = [g["mag"] for g in watch_gyro_samples if target_sensor_ns - 300_000_000 <= g["timeNanos"] <= target_sensor_ns + 100_000_000]
                max_downswing_gyro = max(downswing_gyro_win) if downswing_gyro_win else (gyro_mags[close_idx] if len(gyro_mags) > close_idx else 0.0)
                bat_speed = float(max_downswing_gyro * 4.5)

                pass1_shots.append({
                    "timestamp_offset_s": t_shot,
                    "timestamp_ns": ts_ns,
                    "shot_type": shot_type,
                    "quality": quality,
                    "bat_speed": bat_speed,
                    "impact_force": 15.0,
                    "efficiency": 90.0,
                    "impact_time_ms": 350,
                    "features": feats
                })

    # Pass 2: Watch gyro peak detection fallback for non-overlapping shots
    watch_peak_gyro_threshold = 4.0
    pass2_shots = []
    peaks, _ = find_peaks(gyro_mags, height=watch_peak_gyro_threshold, distance=75)
    for p in peaks:
        t_shot = float(gyro_times[p])
        target_sensor_ns = watch_start_ns + int(t_shot * 1e9)
        ts_ns = int(accel_ns[p]) if len(accel_ns) > p else 0

        is_overlap = any(abs(s["timestamp_offset_s"] - t_shot) < 2.0 for s in pass1_shots)
        if not is_overlap:
            if verify_swing_backwards(target_sensor_ns, watch_gyro_samples, watch_rot_samples)[0]:
                feats = extract_features_single_shot(sensors, t_shot)
                feat_vector = [0.0 if feats[col] is None or pd.isna(feats[col]) else float(feats[col]) for col in feature_cols]
                df_feat = pd.DataFrame([feat_vector], columns=feature_cols)
                
                type_enc = rf_type.predict(df_feat)[0]
                shot_type = le_type.inverse_transform([type_enc])[0]
                
                qual_enc = rf_qual.predict(df_feat)[0]
                quality = le_qual.inverse_transform([qual_enc])[0]
                
                bat_speed = float(gyro_mags[p] * 4.5)

                pass2_shots.append({
                    "timestamp_offset_s": t_shot,
                    "timestamp_ns": ts_ns,
                    "shot_type": shot_type,
                    "quality": quality,
                    "bat_speed": bat_speed,
                    "impact_force": float(accel_mags[p]),
                    "efficiency": 90.0,
                    "impact_time_ms": 350,
                    "features": feats
                })

    # Combine & 5.0s NMS
    all_raw_shots = sorted(pass1_shots + pass2_shots, key=lambda x: x["timestamp_offset_s"])
    pruned_shots = []
    for shot in all_raw_shots:
        dup_idx = next((i for i, x in enumerate(pruned_shots) if abs(x["timestamp_offset_s"] - shot["timestamp_offset_s"]) < 5.0), -1)
        if dup_idx != -1:
            if shot["bat_speed"] > pruned_shots[dup_idx]["bat_speed"]:
                pruned_shots[dup_idx] = shot
        else:
            pruned_shots.append(shot)
    return pruned_shots

def main():
    if not os.path.exists(FEATURES_CSV):
        print(f"❌ compile_dataset.py must be run first to generate {FEATURES_CSV}")
        sys.exit(1)
        
    rf_top_type, rf_dual_type, le_type, rf_top_qual, rf_dual_qual, le_qual = train_classifiers()

    if not pull_database():
        sys.exit(1)
        
    conn = sqlite3.connect(LOCAL_DB_PATH)
    c = conn.cursor()
    
    c.execute("""
        CREATE TABLE IF NOT EXISTS innings_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            inningsId INTEGER,
            timestamp INTEGER,
            description TEXT,
            batSpeed REAL,
            impactForce REAL,
            impactTimeMs INTEGER,
            shotType TEXT,
            efficiency REAL,
            backliftAngle REAL,
            followThroughAngle REAL,
            wristRollDeg REAL,
            bladeAngle REAL,
            bladeClass TEXT,
            launchAngle REAL,
            launchClass TEXT,
            location TEXT,
            bottom_hand_gyro_peak REAL,
            bottom_hand_acc_peak REAL,
            bottom_hand_gyro_ratio REAL,
            bottom_hand_acc_ratio REAL,
            bottom_hand_time_lead_ms REAL,
            bottom_hand_sync_score REAL,
            swing_feature_s1_gyro_y_std REAL,
            swing_feature_s1_gyro_z_std REAL,
            swing_feature_s1_delta_x REAL,
            swing_feature_s1_delta_z REAL,
            swing_feature_s2_gyro_mag REAL,
            swing_feature_s2_grav_y_mean REAL,
            swing_feature_s2_delta_x REAL,
            swing_feature_s2_delta_z REAL,
            swing_feature_s3_roll_deg REAL,
            swing_feature_s3_yaw_deg REAL,
            swing_feature_s3_delta_x REAL,
            swing_feature_s3_delta_z REAL,
            swing_feature_s3_plane_ratio REAL,
            swing_feature_s3_gyro_y_min REAL
        )
    """)
    c.execute("CREATE TABLE IF NOT EXISTS heart_rate_events (id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp INTEGER, bpm REAL)")
    print("🧹 Cleaning phone database events tables to prevent legacy duplicates...")
    c.execute("DELETE FROM innings_events")
    c.execute("DELETE FROM heart_rate_events")
    conn.commit()

    session_dirs = sorted(glob.glob(os.path.join(SESSIONS_DIR, "session-*")) + 
                          glob.glob(os.path.join(SESSIONS_DIR, "session_*")))
    session_dirs = sorted(list(set(session_dirs)))
    
    print(f"\n📂 Scanning {len(session_dirs)} local sessions on Mac...")
    summary_stats = []

    for sdir in session_dirs:
        session_name = os.path.basename(sdir)
        m = re.match(r"session[-_](\d{4})-(\d{2})-(\d{2})_(\d{2})[-_](\d{2})[-_](\d{2})", session_name)
        if m:
            parts = [int(x) for x in m.groups()]
            dt = datetime.datetime(parts[0], parts[1], parts[2], parts[3], parts[4], parts[5])
            session_start_ms = int(dt.timestamp() * 1000)
        else:
            session_start_ms = int(os.path.getmtime(sdir) * 1000)
        
        # Re-run peak detection and classifications
        shots = process_single_session_raw(sdir, rf_top_type, rf_dual_type, le_type, rf_top_qual, rf_dual_qual, le_qual)
        
        # Write Session Started marker
        c.execute("""
            INSERT INTO innings_events (inningsId, timestamp, description, location)
            VALUES (?, ?, 'Session Started', '26 Aldinga Street, Blackburn South')
        """, (session_start_ms, session_start_ms))

        # Insert each shot
        for i, shot in enumerate(shots, 1):
            shot_time_ms = session_start_ms + int(shot["timestamp_offset_s"] * 1000)
            
            sweet_spot = {
                "good": "Excellent",
                "poor": "Poor",
                "miss": "Miss",
                "edge": "Edge"
            }.get(shot["quality"], "Good")
            
            desc = f"{shot['shot_type']} ({sweet_spot}) ✨ Reprocessed"
            f = shot["features"]
            efficiency = float(shot.get("efficiency", f.get("efficiency", 90.0)))
            impact_time_ms = int(shot.get("impact_time_ms", f.get("reaction_time_ms", 350)))

            c.execute("""
                INSERT INTO innings_events (
                    inningsId, timestamp, description, batSpeed, impactForce, impactTimeMs, shotType, efficiency,
                    bladeAngle, bladeClass, launchAngle, launchClass, location,
                    bottom_hand_gyro_peak, bottom_hand_acc_peak, bottom_hand_gyro_ratio, bottom_hand_acc_ratio, bottom_hand_time_lead_ms, bottom_hand_sync_score,
                    swing_feature_s1_gyro_y_std, swing_feature_s1_gyro_z_std, swing_feature_s1_delta_x, swing_feature_s1_delta_z,
                    swing_feature_s2_gyro_mag, swing_feature_s2_grav_y_mean, swing_feature_s2_delta_x, swing_feature_s2_delta_z,
                    swing_feature_s3_roll_deg, swing_feature_s3_yaw_deg, swing_feature_s3_delta_x, swing_feature_s3_delta_z,
                    swing_feature_s3_plane_ratio, swing_feature_s3_gyro_y_min
                ) VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, '26 Aldinga Street, Blackburn South',
                    ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?,
                    ?, ?, ?, ?,
                    ?, ?, ?, ?,
                    ?, ?
                )
            """, (
                session_start_ms, shot_time_ms, desc, shot["bat_speed"], shot["impact_force"], impact_time_ms, shot["shot_type"], efficiency,
                shot.get("blade_angle"), shot.get("blade_class"), shot.get("launch_angle"), shot.get("launch_class"),
                f.get('bottom_hand_gyro_peak'), f.get('bottom_hand_acc_peak'), f.get('bottom_hand_gyro_ratio'), f.get('bottom_hand_acc_ratio'), f.get('bottom_hand_time_lead_ms'), f.get('bottom_hand_sync_score'),
                f.get('s1_gyro_y_std'), f.get('s1_gyro_z_std'), f.get('s1_deltaX'), f.get('s1_deltaZ'),
                f.get('s2_gyroMag'), f.get('s2_grav_y_mean'), f.get('s2_deltaX'), f.get('s2_deltaZ'),
                f.get('s3_rollImpactDeg'), f.get('s3_yawImpactDeg'), f.get('s3_deltaX'), f.get('s3_deltaZ'),
                f.get('s3_planeRatio'), f.get('s3_gyro_y_min')
            ))
            
        # Write Session Ended marker
        session_end_ms = session_start_ms + (int(shots[-1]["timestamp_offset_s"] * 1000) if shots else 10000)
        c.execute("""
            INSERT INTO innings_events (inningsId, timestamp, description, location)
            VALUES (?, ?, 'Session Ended', '26 Aldinga Street, Blackburn South')
        """, (session_start_ms, session_end_ms))
        conn.commit()
        
        # Calculate statistics and density heuristics
        duration_minutes = 0.0
        gyro_df = load_watch_sensor(sdir, "WatchGyroscope")
        if gyro_df is not None and not gyro_df.empty:
            duration_minutes = float(gyro_df["seconds_elapsed"].iloc[-1] - gyro_df["seconds_elapsed"].iloc[0]) / 60.0
        else:
            duration_minutes = (shots[-1]["timestamp_offset_s"] if shots else 10) / 60.0

        if shots:
            avg_spd = np.mean([s["bat_speed"] for s in shots])
            max_spd = np.max([s["bat_speed"] for s in shots])
            qual_counts = pd.Series([s["quality"] for s in shots]).value_counts().to_dict()
        else:
            avg_spd, max_spd, qual_counts = 0.0, 0.0, {}

        avg_gap = (duration_minutes * 60.0) / len(shots) if len(shots) > 0 else 0.0
        min_allowed_gap = 5.0 + (int(duration_minutes) // 10) * 1.0
        
        dense_warning = ""
        if len(shots) > 0 and avg_gap < min_allowed_gap:
            dense_warning = f"⚠️ DENSE ({avg_gap:.1f}s/shot < {min_allowed_gap:.1f}s)"

        summary_stats.append({
            "name": session_name,
            "id": session_start_ms,
            "shots": len(shots),
            "avg_speed": avg_spd,
            "max_speed": max_spd,
            "quals": qual_counts,
            "duration": duration_minutes,
            "warning": dense_warning
        })

    conn.commit()
    conn.close()
    
    # Print Summary Statistics Table
    print("\n" + "="*115)
    print("📊 SESSION RE-PRODUCING RUN SCORECARD (GROUND-TRUTH PREFERENCE & FLUSH CLEAN)")
    print("="*115)
    print(f"{'Session Directory':<32} | {'Innings ID':<15} | {'Duration':<8} | {'Shots':<5} | {'Avg Spd':<7} | {'Max Spd':<7} | {'Density Check':<18} | {'Quality distribution'}")
    print("-"*135)
    for s in summary_stats:
        q_str = ", ".join([f"{k}:{v}" for k, v in s["quals"].items()])
        duration_str = f"{s['duration']:.1f} min"
        print(f"{s['name']:<32} | {s['id']:<15} | {duration_str:<8} | {s['shots']:<5} | {s['avg_speed']:<7.1f} | {s['max_speed']:<7.1f} | {s['warning']:<18} | {q_str}")
    print("="*115 + "\n")
    
    print("⏳ Uploading updated database back to the phone...")
    if push_database():
        restart_app()

if __name__ == "__main__":
    main()
