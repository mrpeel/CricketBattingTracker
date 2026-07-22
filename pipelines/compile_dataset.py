#!/usr/bin/env python3
import os
import re
import sys
import json
import numpy as np
import pandas as pd
from scipy.stats import skew as scipy_skew

# Allow importing from project root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from automate_pipeline import load_watch_sensor

# ─── Configuration ────────────────────────────────────────────────────────────
BASE_DIR = "/Users/neilkloot/Code/Batting Sensor Stats"
NON_SWING_TYPES = {'facing up', 'no shot', 'leave', 'evade', 'evasion'}

# 12 Polar bottom-hand features (imputed to 0.0 when Polar is absent)
POLAR_FEATURE_COLS = [
    'bottom_hand_gyro_peak',
    'bottom_hand_acc_peak',
    'bottom_hand_gyro_ratio',
    'bottom_hand_acc_ratio',
    'bottom_hand_time_lead_ms',
    'bottom_hand_sync_score',
    's1_bottom_gyro_mag',
    's1_bottom_deltaZ',
    's2_bottom_acc_mean',
    's2_dynamic_ratio_slope',
    's3_bottom_pronation_deg',
    's3_bottom_gyro_y_min',
]

TOP_FEATURE_COLS = [
    's1_gyro_y_std', 's1_gyro_z_std', 's1_deltaX', 's1_deltaZ',
    's2_gyroMag', 's2_grav_y_mean', 's2_deltaX', 's2_deltaZ',
    's3_rollImpactDeg', 's3_yawImpactDeg', 's3_deltaX', 's3_deltaZ',
    's3_planeRatio', 's3_gyro_y_min', 'gyroMag', 'grav_x_max'
]

# Augmented synthetic training data directory (never used for evaluation)
AUG_DIR = os.path.join(BASE_DIR, "augmented_training_data")

# Dynamically list all session directories in live_watch_sessions
base_live_dir = os.path.join(BASE_DIR, "live_watch_sessions")
if os.path.exists(base_live_dir):
    TRUSTWORTHY_SESSIONS = sorted([
        d for d in os.listdir(base_live_dir)
        if (d.startswith("session-") or d.startswith("session_")) and os.path.isdir(os.path.join(base_live_dir, d))
    ])
else:
    TRUSTWORTHY_SESSIONS = []

# ─── Quaternion math (exact port from SwingDetector.kt) ──────────────────────
def multiply_quats(q1, q2):
    x1, y1, z1, w1 = q1
    x2, y2, z2, w2 = q2
    return np.array([
        w1*x2 + x1*w2 + y1*z2 - z1*y2,
        w1*y2 - x1*z2 + y1*w2 + z1*x2,
        w1*z2 + x1*y2 - y1*x2 + z1*w2,
        w1*w2 - x1*x2 - y1*y2 - z1*z2,
    ])

def conjugate_quat(q):
    return np.array([-q[0], -q[1], -q[2], q[3]])

def rotate_vector(q, v):
    qx, qy, qz, qw = q
    vx, vy, vz = v
    tx = 2.0 * (qy*vz - qz*vy)
    ty = 2.0 * (qz*vx - qx*vz)
    tz = 2.0 * (qx*vy - qy*vx)
    return np.array([
        vx + qw*tx + (qy*tz - qz*ty),
        vy + qw*ty + (qz*tx - qx*tz),
        vz + qw*tz + (qx*ty - qy*tx),
    ])

def calc_relative_roll(q):
    x, y, z, w = q
    return np.degrees(np.arctan2(2.0 * (w*y + x*z), 1.0 - 2.0 * (y*y + z*z)))

def average_quats(qx_arr, qy_arr, qz_arr, qw_arr):
    if len(qx_arr) == 0:
        return np.array([0, 0, 0, 1.0])
    q0 = np.array([qx_arr[0], qy_arr[0], qz_arr[0], qw_arr[0]])
    s = q0.copy()
    for i in range(1, len(qx_arr)):
        qi = np.array([qx_arr[i], qy_arr[i], qz_arr[i], qw_arr[i]])
        dot = np.dot(q0, qi)
        sign = 1.0 if dot >= 0 else -1.0
        s += sign * qi
    norm = np.linalg.norm(s)
    return s / norm if norm > 0 else np.array([0, 0, 0, 1.0])

V_LOCAL = np.array([0.0, -1.0, 0.0])  # bat forearm unit vector

# ─── Sensor loading (binary-aware via load_watch_sensor) ─────────────────────
def load_all_sensors(session_dir):
    """Load all watch IMU sensors using load_watch_sensor() which handles both
    .csv.gz and .bin.gz binary formats transparently."""
    sensors = {}
    for name, base_name in [
        ("gyro",        "WatchGyroscope"),
        ("accel",       "WatchAccelerometer"),
        ("gravity",     "WatchGravity"),
        ("linacc",      "WatchLinearAcceleration"),
        ("mag",         "WatchMagnetometer"),
        ("game_orient", "WatchGameOrientation"),
        ("orient",      "WatchOrientation")
    ]:
        df = load_watch_sensor(session_dir, base_name)
        if not df.empty and len(df) > 0:
            sensors[name] = df
    for name in ["gyro", "accel", "gravity", "mag", "linacc"]:
        if name in sensors:
            df = sensors[name]
            df['mag_total'] = np.sqrt(df['x']**2 + df['y']**2 + df['z']**2)
    return sensors


def measure_session_hz(session_dir, n_samples=500):
    """Estimate the watch gyro sampling rate for this session."""
    df = load_watch_sensor(session_dir, "WatchGyroscope")
    if df.empty or len(df) < 2:
        return 50
    sub = df.head(n_samples)
    duration = sub['seconds_elapsed'].iloc[-1] - sub['seconds_elapsed'].iloc[0]
    return round((len(sub) - 1) / duration) if duration > 0 else 50


def get_data_profile(session_dir):
    """Return data profile tag and measured Hz for this session."""
    hz = measure_session_hz(session_dir)
    polar_dir = os.path.join(session_dir, "PolarSense")
    has_polar = os.path.isdir(polar_dir) and any(
        f.endswith('.csv') or f.endswith('.csv.gz') or f.endswith('.bin') or f.endswith('.bin.gz')
        for f in os.listdir(polar_dir)
    ) if os.path.isdir(polar_dir) else False
    if not has_polar:
        profile = "50hz_watch" if hz <= 75 else "100hz_watch"
    elif hz <= 75:
        profile = "50hz_watch_polar"
    else:
        profile = "100hz_watch_polar"
    return profile, hz, has_polar

# ─── Feature extraction ──────────────────────────────────────────────────────
def extract_shot_features(sensors, t_shot):
    feats = {}
    
    # Identify orientation dataframe
    orient = sensors.get("game_orient", sensors.get("orient"))
    
    # Compute stance reference quaternion using dynamic look-back stability search
    q_stance = np.array([0, 0, 0, 1.0])
    if orient is not None:
        def compute_stability(df_window):
            if len(df_window) < 2:
                return 999.0
            df_sorted = df_window.sort_values('seconds_elapsed')
            total_disp = 0.0
            count = 0
            q_vals = df_sorted[['qx', 'qy', 'qz', 'qw']].values
            for i in range(1, len(q_vals)):
                q1 = q_vals[i-1]
                q2 = q_vals[i]
                dot = np.clip(np.dot(q1, q2), -1.0, 1.0)
                angle_deg = np.degrees(2.0 * np.arccos(np.abs(dot)))
                total_disp += angle_deg
                count += 1
            return total_disp / count if count > 0 else 999.0

        window_df = orient[(orient['seconds_elapsed'] >= t_shot - 3.0) & 
                           (orient['seconds_elapsed'] <= t_shot - 1.0)]
        if len(window_df) >= 2:
            best_stability = 999.0
            best_sub_df = None
            window_df = window_df.sort_values('seconds_elapsed')
            times = window_df['seconds_elapsed'].values
            for i in range(len(times)):
                t_start = times[i]
                t_end = t_start + 0.8
                if t_end > t_shot - 1.0 + 1e-5:
                    break
                sub_df = window_df[(window_df['seconds_elapsed'] >= t_start) & 
                                   (window_df['seconds_elapsed'] <= t_end)]
                if len(sub_df) >= 2:
                    stab = compute_stability(sub_df)
                    if stab < best_stability:
                        best_stability = stab
                        best_sub_df = sub_df
            
            if best_sub_df is not None and len(best_sub_df) >= 2:
                q_stance = average_quats(best_sub_df['qx'].values, best_sub_df['qy'].values, 
                                         best_sub_df['qz'].values, best_sub_df['qw'].values)
            else:
                stance_ori = orient[(orient['seconds_elapsed'] >= t_shot - 3.0) & 
                                    (orient['seconds_elapsed'] <= t_shot - 1.5)]
                if len(stance_ori) >= 2:
                    q_stance = average_quats(stance_ori['qx'].values, stance_ori['qy'].values, 
                                             stance_ori['qz'].values, stance_ori['qw'].values)
                                     
    q_stance_inv = conjugate_quat(q_stance)
    
    # Helper to calculate deltaX and deltaZ for a specific time range
    def get_displacement_feats(ts, te, prefix):
        if orient is None:
            return {f"{prefix}_deltaX": 0.0, f"{prefix}_deltaZ": 0.0}
        sub = orient[(orient['seconds_elapsed'] >= t_shot + ts) & (orient['seconds_elapsed'] <= t_shot + te)]
        if len(sub) >= 2:
            min_x, max_x = 1e10, -1e10
            min_z, max_z = 1e10, -1e10
            for _, row in sub.iterrows():
                q_curr = np.array([row['qx'], row['qy'], row['qz'], row['qw']])
                q_rel = multiply_quats(q_stance_inv, q_curr)
                v_rot = rotate_vector(q_rel, V_LOCAL)
                if v_rot[0] < min_x: min_x = v_rot[0]
                if v_rot[0] > max_x: max_x = v_rot[0]
                if v_rot[2] < min_z: min_z = v_rot[2]
                if v_rot[2] > max_z: max_z = v_rot[2]
            return {
                f"{prefix}_deltaX": max_x - min_x,
                f"{prefix}_deltaZ": max_z - min_z
            }
        return {f"{prefix}_deltaX": 0.0, f"{prefix}_deltaZ": 0.0}

    # Boundaries: [-0.80, -0.20, -0.05, 0.30]
    t_start, t_split1, t_split2, t_end = -0.80, -0.20, -0.05, 0.30
    
    # --- Segment 1: Footwork [-0.80s, -0.20s] ---
    feats.update(get_displacement_feats(t_start, t_split1, "s1"))
    gyro = sensors.get("gyro")
    if gyro is not None:
        sub = gyro[(gyro['seconds_elapsed'] >= t_shot + t_start) & (gyro['seconds_elapsed'] <= t_shot + t_split1)]
        if len(sub) >= 2:
            feats["s1_gyro_y_std"] = float(np.std(sub['y'].values))
            feats["s1_gyro_z_std"] = float(np.std(sub['z'].values))
        else:
            feats["s1_gyro_y_std"] = 0.0
            feats["s1_gyro_z_std"] = 0.0
    else:
        feats["s1_gyro_y_std"] = 0.0
        feats["s1_gyro_z_std"] = 0.0
        
    # --- Segment 2: Intent & Height [-0.20s, -0.05s] ---
    feats.update(get_displacement_feats(t_split1, t_split2, "s2"))
    if gyro is not None:
        sub = gyro[(gyro['seconds_elapsed'] >= t_shot + t_split1) & (gyro['seconds_elapsed'] <= t_shot + t_split2)]
        feats["s2_gyroMag"] = sub['mag_total'].max() if len(sub) > 0 else 0.0
    else:
        feats["s2_gyroMag"] = 0.0
        
    grav = sensors.get("gravity")
    if grav is not None:
        sub = grav[(grav['seconds_elapsed'] >= t_shot + t_split1) & (grav['seconds_elapsed'] <= t_shot + t_split2)]
        feats["s2_grav_y_mean"] = sub['y'].mean() if len(sub) > 0 else -9.8
    else:
        feats["s2_grav_y_mean"] = -9.8
        
    # --- Segment 3: Shot Selection [-0.05s, 0.30s] ---
    feats.update(get_displacement_feats(t_split2, t_end, "s3"))
    feats["s3_planeRatio"] = feats["s3_deltaX"] / feats["s3_deltaZ"] if feats["s3_deltaZ"] > 0 else 0.0
    
    if orient is not None:
        impact_ori = orient[(orient['seconds_elapsed'] >= t_shot + t_split2 - 0.05) & 
                            (orient['seconds_elapsed'] <= t_shot + t_split2 + 0.05)]
        if len(impact_ori) == 0:
            impact_ori = orient.iloc[(orient['seconds_elapsed'] - (t_shot + t_split2)).abs().argsort()[:1]]
        if len(impact_ori) > 0:
            row = impact_ori.iloc[0]
            q_impact = np.array([row['qx'], row['qy'], row['qz'], row['qw']])
            q_rel = multiply_quats(q_stance_inv, q_impact)
            feats['s3_rollImpactDeg'] = calc_relative_roll(q_rel)
            v_rot = rotate_vector(q_rel, V_LOCAL)
            feats['s3_yawImpactDeg'] = np.degrees(np.arctan2(v_rot[0], -v_rot[1]))
        else:
            feats['s3_rollImpactDeg'] = 0.0
            feats['s3_yawImpactDeg'] = 0.0
    else:
        feats['s3_rollImpactDeg'] = 0.0
        feats['s3_yawImpactDeg'] = 0.0
        
    if gyro is not None:
        sub = gyro[(gyro['seconds_elapsed'] >= t_shot + t_split2) & (gyro['seconds_elapsed'] <= t_shot + t_end)]
        feats['s3_gyro_y_min'] = sub['y'].min() if len(sub) > 0 else 0.0
        
        full_swing_gyro = gyro[(gyro['seconds_elapsed'] >= t_shot + t_start) & (gyro['seconds_elapsed'] <= t_shot + t_end)]
        feats['gyroMag'] = full_swing_gyro['mag_total'].max() if len(full_swing_gyro) > 0 else 0.0
    else:
        feats['s3_gyro_y_min'] = 0.0
        feats['gyroMag'] = 0.0
        
    if grav is not None:
        full_swing_grav = grav[(grav['seconds_elapsed'] >= t_shot + t_start) & (grav['seconds_elapsed'] <= t_shot + t_end)]
        feats['grav_x_max'] = full_swing_grav['x'].max() if len(full_swing_grav) > 0 else 0.0
    else:
        feats['grav_x_max'] = 0.0
        
    return feats

# ─── Deployed Kotlin Logic (Current) ──────────────────────────────────────────
def classify_current(f):
    return "DRIVE/DEFENCE"

# ─── Normalization of Ground Truth ───────────────────────────────────────────

def normalize_shot_class(shot_name):
    if not shot_name:
        return "Unknown"
    s = shot_name.lower().strip()
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


# ─── Date Parsing ────────────────────────────────────────────────────────────
def parse_session_date(session_id):
    # Format: session-YYYY-MM-DD_HH-MM-SS
    m = re.match(r"session-(\d{4}-\d{2}-\d{2})_(\d{2})-(\d{2})-(\d{2})", session_id)
    if m:
        date_part, h, min_part, s = m.groups()
        return f"{date_part} {h}:{min_part}:{s}"
    return ""

# ─── Main Compilation Loop ───────────────────────────────────────────────────
def main():
    print("Starting data compilation for shot classification running total...")
    all_aligned_rows = []
    all_features_rows = []

    for session_id in TRUSTWORTHY_SESSIONS:
        session_dir = os.path.join(BASE_DIR, "live_watch_sessions", session_id)
        print(f"\nProcessing session: {session_id}")
        
        aligned_path = os.path.join(session_dir, "ground_truth_aligned.csv")
        if not os.path.exists(aligned_path):
            print(f"  ⚠️ Warning: ground_truth_aligned.csv not found, skipping.")
            continue
            
        df_aligned = pd.read_csv(aligned_path)
        sensors = load_all_sensors(session_dir)

        if "gyro" not in sensors:
            print(f"  ⚠️ Warning: gyro sensor CSV missing, skipping.")
            continue

        # Detect data profile for this session
        data_profile, watch_hz, has_polar = get_data_profile(session_dir)
        print(f"  Profile: {data_profile} ({watch_hz}Hz, {'Polar' if has_polar else 'watch-only'})")
            
        session_date = parse_session_date(session_id)
        
        # Iterate over all rows in the aligned ground truth
        for idx, row in df_aligned.iterrows():
            shot_type = str(row['shot_type'])
            
            # Identify if it is a swing shot (rather than Stance / non-swing)
            is_non_swing = any(term in shot_type.lower() for term in NON_SWING_TYPES)
            normalized_gt = normalize_shot_class(shot_type)
            
            t_impact = float(row["impact_time_seconds"])
            t_impact_ns = int(row["impact_timestamp_ns"]) if ("impact_timestamp_ns" in row and pd.notna(row["impact_timestamp_ns"])) else int(t_impact * 1e9)

            s1_start_ns = row.get("s1_start_ns", t_impact_ns - 800_000_000)
            s1_end_ns = row.get("s1_end_ns", t_impact_ns - 200_000_000)
            s1_start_sec = row.get("s1_start_sec", round(t_impact - 0.80, 6))
            s1_end_sec = row.get("s1_end_sec", round(t_impact - 0.20, 6))

            s2_start_ns = row.get("s2_start_ns", t_impact_ns - 200_000_000)
            s2_end_ns = row.get("s2_end_ns", t_impact_ns - 50_000_000)
            s2_start_sec = row.get("s2_start_sec", round(t_impact - 0.20, 6))
            s2_end_sec = row.get("s2_end_sec", round(t_impact - 0.05, 6))

            s3_start_ns = row.get("s3_start_ns", t_impact_ns - 50_000_000)
            s3_end_ns = row.get("s3_end_ns", t_impact_ns + 300_000_000)
            s3_start_sec = row.get("s3_start_sec", round(t_impact - 0.05, 6))
            s3_end_sec = row.get("s3_end_sec", round(t_impact + 0.30, 6))

            # We only evaluate classification on active, normalized shot types
            if is_non_swing or normalized_gt == "Unknown":
                non_swing_entry = {
                    "session_id": session_id,
                    "session_date": session_date,
                    "shot_index": row["shot_index"],
                    "shot_number": row["shot_number"],
                    "audio_time_seconds": row["audio_time_seconds"],
                    "sensor_narr_time_seconds": row["sensor_narr_time_seconds"],
                    "impact_time_seconds": row["impact_time_seconds"],
                    "impact_timestamp_ns": row["impact_timestamp_ns"],
                    "impact_gyro_mag": row["impact_gyro_mag"],
                    "s1_start_ns": s1_start_ns,
                    "s1_end_ns": s1_end_ns,
                    "s1_start_sec": s1_start_sec,
                    "s1_end_sec": s1_end_sec,
                    "s2_start_ns": s2_start_ns,
                    "s2_end_ns": s2_end_ns,
                    "s2_start_sec": s2_start_sec,
                    "s2_end_sec": s2_end_sec,
                    "s3_start_ns": s3_start_ns,
                    "s3_end_ns": s3_end_ns,
                    "s3_start_sec": s3_start_sec,
                    "s3_end_sec": s3_end_sec,
                    "efficiency": float(row.get("efficiency", 0.0)),
                    "reaction_time_ms": int(row.get("reaction_time_ms", 350)),
                    "shot_type": shot_type,
                    "normalized_gt": "NON-SWING",
                    "quality": row["quality"],
                    "narrated_text": row["narrated_text"],
                    "predicted_shot_type": "N/A",
                    "is_correct": "N/A"
                }
                for col in TOP_FEATURE_COLS + POLAR_FEATURE_COLS:
                    val = row.get(col, 0.0)
                    non_swing_entry[col] = float(val) if (val is not None and pd.notna(val)) else 0.0
                all_aligned_rows.append(non_swing_entry)
                continue
                
            t_impact = float(row["impact_time_seconds"])
            t_impact_ns = int(row["impact_timestamp_ns"]) if ("impact_timestamp_ns" in row and pd.notna(row["impact_timestamp_ns"])) else int(t_impact * 1e9)
            feats = extract_shot_features(sensors, t_impact)

            # Extract phase nanoseconds & seconds from row (or compute fallback)
            s1_start_ns = row.get("s1_start_ns", t_impact_ns - 800_000_000)
            s1_end_ns = row.get("s1_end_ns", t_impact_ns - 200_000_000)
            s1_start_sec = row.get("s1_start_sec", round(t_impact - 0.80, 6))
            s1_end_sec = row.get("s1_end_sec", round(t_impact - 0.20, 6))

            s2_start_ns = row.get("s2_start_ns", t_impact_ns - 200_000_000)
            s2_end_ns = row.get("s2_end_ns", t_impact_ns - 50_000_000)
            s2_start_sec = row.get("s2_start_sec", round(t_impact - 0.20, 6))
            s2_end_sec = row.get("s2_end_sec", round(t_impact - 0.05, 6))

            s3_start_ns = row.get("s3_start_ns", t_impact_ns - 50_000_000)
            s3_end_ns = row.get("s3_end_ns", t_impact_ns + 300_000_000)
            s3_start_sec = row.get("s3_start_sec", round(t_impact - 0.05, 6))
            s3_end_sec = row.get("s3_end_sec", round(t_impact + 0.30, 6))

            # Quality control: filter out misaligned wiggles
            g_mag = feats.get('gyroMag', 0.0)
            if normalized_gt in ["SLOG", "POWER DRIVE", "PULL/HOOK", "SWEEP", "CUT/PUNCH", "GLANCE/FLICK"]:
                if g_mag < 9.0:
                    continue
            else:
                if g_mag < 4.0:
                    continue
            
            # Biomechanical split: SLOG -> POWER DRIVE if grav_x_max <= 5.5
            if normalized_gt == "SLOG" and feats.get('grav_x_max', 0.0) <= 5.5:
                normalized_gt = "POWER DRIVE"
            
            # Predict using currently active logic
            pred = classify_current(feats)
            is_correct = 1 if pred == normalized_gt else 0

            # Calculate physical efficiency & reaction time
            impact_gyro_mag = float(row.get('impact_gyro_mag', 0.0))
            max_gyro_mag = float(feats.get('gyroMag', impact_gyro_mag))
            eff = row.get('efficiency', min(100.0, round((impact_gyro_mag / max_gyro_mag) * 100.0, 1)) if max_gyro_mag > 0.1 else 90.0)
            react_ms = row.get('reaction_time_ms', 350)
            
            # Add to aligned rows with full transparency (all 26 features + timings)
            aligned_entry = {
                "session_id": session_id,
                "session_date": session_date,
                "shot_index": row["shot_index"],
                "shot_number": row["shot_number"],
                "audio_time_seconds": row["audio_time_seconds"],
                "sensor_narr_time_seconds": row["sensor_narr_time_seconds"],
                "impact_time_seconds": row["impact_time_seconds"],
                "impact_timestamp_ns": row["impact_timestamp_ns"],
                "impact_gyro_mag": row["impact_gyro_mag"],
                "s1_start_ns": s1_start_ns,
                "s1_end_ns": s1_end_ns,
                "s1_start_sec": s1_start_sec,
                "s1_end_sec": s1_end_sec,
                "s2_start_ns": s2_start_ns,
                "s2_end_ns": s2_end_ns,
                "s2_start_sec": s2_start_sec,
                "s2_end_sec": s2_end_sec,
                "s3_start_ns": s3_start_ns,
                "s3_end_ns": s3_end_ns,
                "s3_start_sec": s3_start_sec,
                "s3_end_sec": s3_end_sec,
                "efficiency": eff,
                "reaction_time_ms": react_ms,
                "shot_type": shot_type,
                "normalized_gt": normalized_gt,
                "quality": row["quality"],
                "narrated_text": row["narrated_text"],
                "predicted_shot_type": pred,
                "is_correct": is_correct
            }
            # Copy all 26 extracted features into aligned_entry
            aligned_entry.update(feats)
            for col in POLAR_FEATURE_COLS:
                val = row.get(col, np.nan)
                aligned_entry[col] = float(val) if (val is not None and pd.notna(val)) else 0.0

            all_aligned_rows.append(aligned_entry)
            
            # Combine all features for training / grid search
            feats_row = feats.copy()
            feats_row["session_id"] = session_id
            feats_row["session_date"] = session_date
            feats_row["shot_index"] = row["shot_index"]
            feats_row["shot_number"] = row["shot_number"]
            feats_row["shot_type"] = shot_type
            feats_row["normalized_gt"] = normalized_gt
            feats_row["quality"] = str(row.get("quality", ""))
            feats_row["data_profile"] = data_profile
            feats_row["watch_hz"] = watch_hz
            feats_row["pred_current"] = pred
            feats_row["is_correct"] = is_correct

            # Append 12 Polar features (imputed to 0.0 for sessions without Polar data)
            for col in POLAR_FEATURE_COLS:
                val = row.get(col, np.nan)
                if val is None or (isinstance(val, float) and np.isnan(val)):
                    feats_row[col] = 0.0
                else:
                    feats_row[col] = float(val)

            all_features_rows.append(feats_row)

    # ─── Load augmented synthetic training data ────────────────────────────────
    # These rows are appended to combined_features.csv for training ONLY.
    # They are NEVER added to all_aligned_rows (evaluation uses real data only).
    synthetic_count = 0
    skipped_count = 0
    if os.path.exists(AUG_DIR):
        aug_dirs = sorted([
            d for d in os.listdir(AUG_DIR)
            if os.path.isdir(os.path.join(AUG_DIR, d))
        ])
        for aug_name in aug_dirs:
            aug_session_dir = os.path.join(AUG_DIR, aug_name)
            aug_gt_path = os.path.join(aug_session_dir, "ground_truth_aligned.csv")
            if not os.path.exists(aug_gt_path):
                continue

            df_aug_gt = pd.read_csv(aug_gt_path)
            aug_sensors = load_all_sensors(aug_session_dir)

            if "gyro" not in aug_sensors:
                continue

            for _, row in df_aug_gt.iterrows():
                shot_type = str(row['shot_type'])
                normalized_gt = normalize_shot_class(shot_type)

                if normalized_gt == "Unknown":
                    continue

                t_impact = float(row["impact_time_seconds"])
                feats = extract_shot_features(aug_sensors, t_impact)

                # Apply same gyroMag quality gate as real data
                g_mag = feats.get('gyroMag', 0.0)
                if normalized_gt in ["SLOG", "POWER DRIVE", "PULL/HOOK", "SWEEP", "CUT/PUNCH", "GLANCE/FLICK"]:
                    if g_mag < 9.0:
                        skipped_count += 1
                        continue
                else:
                    if g_mag < 4.0:
                        skipped_count += 1
                        continue

                # Apply same SLOG -> POWER DRIVE biomechanical split
                if normalized_gt == "SLOG" and feats.get('grav_x_max', 0.0) <= 5.5:
                    normalized_gt = "POWER DRIVE"

                feats_row = feats.copy()
                feats_row["session_id"]    = aug_name
                feats_row["session_date"]  = "synthetic"
                feats_row["shot_index"]    = row.get("shot_index", 0)
                feats_row["shot_number"]   = row.get("shot_number", "")
                feats_row["shot_type"]     = shot_type
                feats_row["normalized_gt"] = normalized_gt
                feats_row["pred_current"]  = "N/A"
                feats_row["is_correct"]    = 0
                feats_row["source"]        = "synthetic"
                all_features_rows.append(feats_row)
                synthetic_count += 1

        print(f"\n  Loaded {synthetic_count} synthetic training rows from {AUG_DIR}")
        if skipped_count > 0:
            print(f"  Skipped {skipped_count} synthetic rows (failed gyroMag quality gate)")
    else:
        print(f"\n  ⚠️  Augmented data directory not found: {AUG_DIR}")
        print("     Run pipelines/augment_training_data.py first to generate synthetic data.")

    # ─── Save Results ───
    df_combined_aligned = pd.DataFrame(all_aligned_rows)
    df_combined_features = pd.DataFrame(all_features_rows)
    
    out_aligned_path = os.path.join(BASE_DIR, "combined_ground_truth_aligned.csv")
    out_features_path = os.path.join(BASE_DIR, "combined_features.csv")
    
    print(f"DEBUG: df_combined_aligned rows: {len(df_combined_aligned)}")
    print(f"DEBUG: df_combined_features rows: {len(df_combined_features)}")
    
    df_combined_aligned.to_csv(out_aligned_path, index=False)
    df_combined_features.to_csv(out_features_path, index=False)
    
    print(f"\nSaved combined ground truth aligned analysis to: {out_aligned_path}")
    print(f"Saved combined extracted features dataset to: {out_features_path}")
    
    # Print accuracy scorecard for current logic
    df_swings = df_combined_features[df_combined_features["normalized_gt"] != "NON-SWING"]
    total_swings = len(df_swings)
    correct_swings = sum(df_swings["is_correct"])
    accuracy = (correct_swings / total_swings) * 100 if total_swings > 0 else 0.0
    print(f"\n=================== CURRENT LOGIC SCORECARD ===================")
    print(f"Total swing shots: {total_swings}")
    print(f"Correctly classified: {correct_swings}")
    print(f"Overall Accuracy: {accuracy:.2f}%")
    print(f"================================================================")
    
    # Class-specific breakdown
    for name, group in df_swings.groupby("normalized_gt"):
        grp_total = len(group)
        grp_correct = sum(group["is_correct"])
        grp_acc = (grp_correct / grp_total) * 100 if grp_total > 0 else 0.0
        print(f"  {name:<20s}: {grp_correct:>3}/{grp_total:<3} ({grp_acc:.1f}%)")
    print("================================================================")

if __name__ == "__main__":
    main()
