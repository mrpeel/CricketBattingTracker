#!/usr/bin/env python3
import os
import re
import json
import numpy as np
import pandas as pd
from scipy.stats import skew as scipy_skew

# ─── Configuration ────────────────────────────────────────────────────────────
BASE_DIR = "/Users/neilkloot/Code/Batting Sensor Stats"
NON_SWING_TYPES = {'facing up', 'no shot', 'leave', 'evade', 'evasion'}

# Dynamically list all session directories in live_watch_sessions
base_live_dir = os.path.join(BASE_DIR, "live_watch_sessions")
if os.path.exists(base_live_dir):
    TRUSTWORTHY_SESSIONS = sorted([
        d for d in os.listdir(base_live_dir)
        if d.startswith("session-") and os.path.isdir(os.path.join(base_live_dir, d))
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

# ─── Sensor loading ──────────────────────────────────────────────────────────
def load_all_sensors(session_dir):
    sensors = {}
    for name, fname in [
        ("gyro",        "WatchGyroscope.csv"),
        ("accel",       "WatchAccelerometer.csv"),
        ("gravity",     "WatchGravity.csv"),
        ("linacc",      "WatchLinearAcceleration.csv"),
        ("mag",         "WatchMagnetometer.csv"),
        ("game_orient", "WatchGameOrientation.csv"),
        ("orient",      "WatchOrientation.csv")
    ]:
        path = os.path.join(session_dir, fname)
        if os.path.exists(path):
            df = pd.read_csv(path)
            if len(df) > 0:
                sensors[name] = df
    for name in ["gyro", "accel", "gravity", "mag", "linacc"]:
        if name in sensors:
            df = sensors[name]
            df['mag_total'] = np.sqrt(df['x']**2 + df['y']**2 + df['z']**2)
    return sensors

# ─── Feature extraction ──────────────────────────────────────────────────────
def extract_shot_features(sensors, t_shot, stance_window=2.0, swing_window_before=0.8, swing_window_after=0.3):
    feats = {}
    
    # ── Gyroscope features ──
    gyro = sensors.get("gyro")
    if gyro is not None:
        sw = gyro[(gyro['seconds_elapsed'] >= t_shot - swing_window_before) & 
                  (gyro['seconds_elapsed'] <= t_shot + swing_window_after)]
        if len(sw) >= 2:
            feats['gyroMag'] = sw['mag_total'].max()
            feats['gyro_y_min'] = sw['y'].min()
            feats['gyro_y_max'] = sw['y'].max()
            feats['gyro_y_skew'] = float(scipy_skew(sw['y'].values)) if np.std(sw['y'].values) > 1e-6 else 0.0
            feats['gyro_x_std'] = float(np.std(sw['x'].values))
            feats['gyro_y_std'] = float(np.std(sw['y'].values))
            feats['gyro_z_std'] = float(np.std(sw['z'].values))
        else:
            feats['gyroMag'] = 0.0
            feats['gyro_y_min'] = 0.0
            feats['gyro_y_max'] = 0.0
            feats['gyro_y_skew'] = 0.0
            feats['gyro_x_std'] = 0.0
            feats['gyro_y_std'] = 0.0
            feats['gyro_z_std'] = 0.0
    else:
        feats['gyroMag'] = 0.0
        feats['gyro_y_min'] = 0.0
        feats['gyro_y_max'] = 0.0
        feats['gyro_y_skew'] = 0.0
        feats['gyro_x_std'] = 0.0
        feats['gyro_y_std'] = 0.0
        feats['gyro_z_std'] = 0.0

    # ── Quaternion-relative features ──
    orient = sensors.get("game_orient", sensors.get("orient"))
    if orient is not None:
        stance_ori = orient[(orient['seconds_elapsed'] >= t_shot - stance_window - 0.5) & 
                            (orient['seconds_elapsed'] <= t_shot - stance_window + 0.5)]
        if len(stance_ori) < 3:
            stance_ori = orient[(orient['seconds_elapsed'] >= t_shot - 3.0) & 
                                (orient['seconds_elapsed'] <= t_shot - 1.5)]
        if len(stance_ori) >= 2:
            q_stance = average_quats(stance_ori['qx'].values, stance_ori['qy'].values, 
                                     stance_ori['qz'].values, stance_ori['qw'].values)
        else:
            q_stance = np.array([0, 0, 0, 1.0])
        
        q_stance_inv = conjugate_quat(q_stance)
        
        swing_ori = orient[(orient['seconds_elapsed'] >= t_shot - swing_window_before) & 
                           (orient['seconds_elapsed'] <= t_shot + swing_window_after)]
        if len(swing_ori) >= 2:
            min_x, max_x = 1e10, -1e10
            min_z, max_z = 1e10, -1e10
            for _, row in swing_ori.iterrows():
                q_curr = np.array([row['qx'], row['qy'], row['qz'], row['qw']])
                q_rel = multiply_quats(q_stance_inv, q_curr)
                v_rot = rotate_vector(q_rel, V_LOCAL)
                if v_rot[0] < min_x: min_x = v_rot[0]
                if v_rot[0] > max_x: max_x = v_rot[0]
                if v_rot[2] < min_z: min_z = v_rot[2]
                if v_rot[2] > max_z: max_z = v_rot[2]
            feats['deltaX'] = max_x - min_x
            feats['deltaZ'] = max_z - min_z
            feats['gameori_qz_range'] = swing_ori['qz'].max() - swing_ori['qz'].min()
            feats['gameori_qx_range'] = swing_ori['qx'].max() - swing_ori['qx'].min()
            feats['gameori_qy_range'] = swing_ori['qy'].max() - swing_ori['qy'].min()
        else:
            feats['deltaX'] = 0.0
            feats['deltaZ'] = 0.0
            feats['gameori_qz_range'] = 0.0
            feats['gameori_qx_range'] = 0.0
            feats['gameori_qy_range'] = 0.0
            
        impact_ori = orient[(orient['seconds_elapsed'] >= t_shot - 0.1) & 
                            (orient['seconds_elapsed'] <= t_shot + 0.1)]
        if len(impact_ori) == 0:
            impact_ori = orient.iloc[(orient['seconds_elapsed'] - t_shot).abs().argsort()[:1]]
        if len(impact_ori) > 0:
            row = impact_ori.iloc[0]
            q_impact = np.array([row['qx'], row['qy'], row['qz'], row['qw']])
            q_rel = multiply_quats(q_stance_inv, q_impact)
            feats['rollImpactDeg'] = calc_relative_roll(q_rel)
            v_rot = rotate_vector(q_rel, V_LOCAL)
            feats['yawImpactDeg'] = np.degrees(np.arctan2(v_rot[0], -v_rot[1]))
        else:
            feats['rollImpactDeg'] = 0.0
            feats['yawImpactDeg'] = 0.0
        
        feats['planeRatio'] = feats['deltaX'] / feats['deltaZ'] if feats['deltaZ'] > 0 else 0.0
    else:
        feats['deltaX'] = 0.0
        feats['deltaZ'] = 0.0
        feats['rollImpactDeg'] = 0.0
        feats['yawImpactDeg'] = 0.0
        feats['planeRatio'] = 0.0
        feats['gameori_qz_range'] = 0.0
        feats['gameori_qx_range'] = 0.0
        feats['gameori_qy_range'] = 0.0
        
    # ── Gravity features ──
    grav = sensors.get("gravity")
    if grav is not None:
        w = grav[(grav['seconds_elapsed'] >= t_shot - swing_window_before) & 
                 (grav['seconds_elapsed'] <= t_shot + swing_window_after)]
        if len(w) >= 2:
            feats['grav_x_max'] = w['x'].max()
            feats['grav_y_min'] = w['y'].min()
            feats['grav_y_mean'] = w['y'].mean()
            feats['grav_x_mean'] = w['x'].mean()
            feats['grav_z_mean'] = w['z'].mean()
        else:
            feats['grav_x_max'] = 0.0
            feats['grav_y_min'] = -9.8
            feats['grav_y_mean'] = -9.8
            feats['grav_x_mean'] = 0.0
            feats['grav_z_mean'] = 0.0
    else:
        feats['grav_x_max'] = 0.0
        feats['grav_y_min'] = -9.8
        feats['grav_y_mean'] = -9.8
        feats['grav_x_mean'] = 0.0
        feats['grav_z_mean'] = 0.0
        
    # ── Magnetometer features ──
    mag = sensors.get("mag")
    if mag is not None:
        w = mag[(mag['seconds_elapsed'] >= t_shot - swing_window_before) & 
                (mag['seconds_elapsed'] <= t_shot + swing_window_after)]
        if len(w) >= 2:
            feats['mag_x_max'] = w['x'].max()
            feats['mag_x_min'] = w['x'].min()
            feats['mag_x_range'] = w['x'].max() - w['x'].min()
            feats['mag_x_std'] = float(np.std(w['x'].values))
            feats['mag_y_mean'] = w['y'].mean()
            feats['mag_z_mean'] = w['z'].mean()
        else:
            feats['mag_x_max'] = 0.0
            feats['mag_x_min'] = 0.0
            feats['mag_x_range'] = 0.0
            feats['mag_x_std'] = 0.0
            feats['mag_y_mean'] = 0.0
            feats['mag_z_mean'] = 0.0
    else:
        feats['mag_x_max'] = 0.0
        feats['mag_x_min'] = 0.0
        feats['mag_x_range'] = 0.0
        feats['mag_x_std'] = 0.0
        feats['mag_y_mean'] = 0.0
        feats['mag_z_mean'] = 0.0

    # ── Accelerometer features ──
    accel = sensors.get("accel")
    if accel is not None:
        w = accel[(accel['seconds_elapsed'] >= t_shot - swing_window_before) & 
                  (accel['seconds_elapsed'] <= t_shot + swing_window_after)]
        if len(w) >= 2:
            feats['accel_mag_max'] = w['mag_total'].max()
            feats['accel_x_range'] = w['x'].max() - w['x'].min()
            feats['accel_y_range'] = w['y'].max() - w['y'].min()
            feats['accel_z_range'] = w['z'].max() - w['z'].min()
        else:
            feats['accel_mag_max'] = 0.0
            feats['accel_x_range'] = 0.0
            feats['accel_y_range'] = 0.0
            feats['accel_z_range'] = 0.0
    else:
        feats['accel_mag_max'] = 0.0
        feats['accel_x_range'] = 0.0
        feats['accel_y_range'] = 0.0
        feats['accel_z_range'] = 0.0
        
    return feats

# ─── Deployed Kotlin Logic (Current) ──────────────────────────────────────────
def get_cut_pull_type(roll, dx):
    if roll <= -15.0 and dx >= 0.30:
        return "PULL/HOOK"
    return "CUT/PUNCH"

def classify_current(f):
    gyroMag = f['gyroMag']
    roll = f['rollImpactDeg']
    yaw = f['yawImpactDeg']
    dx = f['deltaX']
    dz = f['deltaZ']
    ratio = f['planeRatio']
    
    # Base decision tree
    if gyroMag > 22.12:
        base = "POWER SHOT"
    elif roll <= -3.22:
        if dz <= 0.44:
            if dx <= 0.75:
                base = "DRIVE/DEFENCE" if gyroMag <= 14.11 else get_cut_pull_type(roll, dx)
            else:
                base = "GLANCE/FLICK" if dx <= 0.97 else get_cut_pull_type(roll, dx)
        else:
            if yaw <= 6.22:
                base = "DRIVE/DEFENCE" if ratio <= 0.67 else "DEFLECTION/GUIDE"
            else:
                base = get_cut_pull_type(roll, dx) if roll <= -35.84 else "DRIVE/DEFENCE"
    else:
        if ratio <= 2.85:
            if roll <= 18.16:
                base = "DRIVE/DEFENCE" if roll <= 1.67 else get_cut_pull_type(roll, dx)
            else:
                base = "DRIVE/DEFENCE" if gyroMag <= 11.72 else "GLANCE/FLICK"
        else:
            base = "DRIVE/DEFENCE" if yaw <= 3.94 else "GLANCE/FLICK"

    # Post-classification Glance/Flick overrides
    if base == "DRIVE/DEFENCE":
        if f['gyro_y_min'] <= -4.5 and f['rollImpactDeg'] <= -3.22 and f['yawImpactDeg'] >= 15.0 and f['deltaX'] <= 1.25:
            base = "GLANCE/FLICK"
    elif base == "PULL/HOOK":
        if f['gyro_y_min'] >= -9.0 and f['grav_y_min'] <= -8.0 and f['rollImpactDeg'] >= -50.0:
            base = "GLANCE/FLICK"

    # Post-classification Power Shot override
    if base != "POWER SHOT":
        if f['grav_x_max'] > 7.0 and f['mag_x_max'] > 40.0:
            base = "POWER SHOT"

    return base

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
    if "power drive" in s or "power hit" in s:
        return "POWER DRIVE"
    if "power" in s or "loft" in s:
        return "POWER SHOT"
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
            
        session_date = parse_session_date(session_id)
        
        # Iterate over all rows in the aligned ground truth
        for idx, row in df_aligned.iterrows():
            shot_type = str(row['shot_type'])
            
            # Identify if it is a swing shot (rather than Stance / non-swing)
            is_non_swing = any(term in shot_type.lower() for term in NON_SWING_TYPES)
            normalized_gt = normalize_shot_class(shot_type)
            
            # We only evaluate classification on active, normalized shot types
            if is_non_swing or normalized_gt == "Unknown":
                # Save non-swing rows to aligned output for completeness but without prediction
                all_aligned_rows.append({
                    "session_id": session_id,
                    "session_date": session_date,
                    "shot_index": row["shot_index"],
                    "shot_number": row["shot_number"],
                    "audio_time_seconds": row["audio_time_seconds"],
                    "sensor_narr_time_seconds": row["sensor_narr_time_seconds"],
                    "impact_time_seconds": row["impact_time_seconds"],
                    "impact_timestamp_ns": row["impact_timestamp_ns"],
                    "impact_gyro_mag": row["impact_gyro_mag"],
                    "shot_type": shot_type,
                    "normalized_gt": "NON-SWING",
                    "quality": row["quality"],
                    "narrated_text": row["narrated_text"],
                    "predicted_shot_type": "N/A",
                    "is_correct": "N/A"
                })
                continue
                
            # Extract features for this shot
            t_impact = float(row["impact_time_seconds"])
            feats = extract_shot_features(sensors, t_impact)
            
            # Quality control: filter out misaligned wiggles
            g_mag = feats.get('gyroMag', 0.0)
            if normalized_gt in ["POWER SHOT", "POWER DRIVE", "PULL/HOOK", "SWEEP", "CUT/PUNCH", "GLANCE/FLICK"]:
                if g_mag < 9.0:
                    continue
            else:
                if g_mag < 4.0:
                    continue
            
            # Biomechanical split: POWER SHOT -> POWER DRIVE if grav_x_max <= 5.5
            if normalized_gt == "POWER SHOT" and feats.get('grav_x_max', 0.0) <= 5.5:
                normalized_gt = "POWER DRIVE"
            
            # Predict using currently active logic
            pred = classify_current(feats)
            is_correct = 1 if pred == normalized_gt else 0
            
            # Add to aligned rows
            all_aligned_rows.append({
                "session_id": session_id,
                "session_date": session_date,
                "shot_index": row["shot_index"],
                "shot_number": row["shot_number"],
                "audio_time_seconds": row["audio_time_seconds"],
                "sensor_narr_time_seconds": row["sensor_narr_time_seconds"],
                "impact_time_seconds": row["impact_time_seconds"],
                "impact_timestamp_ns": row["impact_timestamp_ns"],
                "impact_gyro_mag": row["impact_gyro_mag"],
                "shot_type": shot_type,
                "normalized_gt": normalized_gt,
                "quality": row["quality"],
                "narrated_text": row["narrated_text"],
                "predicted_shot_type": pred,
                "is_correct": is_correct
            })
            
            # Combine all features for training / grid search
            feats_row = feats.copy()
            feats_row["session_id"] = session_id
            feats_row["session_date"] = session_date
            feats_row["shot_index"] = row["shot_index"]
            feats_row["shot_number"] = row["shot_number"]
            feats_row["shot_type"] = shot_type
            feats_row["normalized_gt"] = normalized_gt
            feats_row["pred_current"] = pred
            feats_row["is_correct"] = is_correct
            all_features_rows.append(feats_row)

    # ─── Save Results ───
    df_combined_aligned = pd.DataFrame(all_aligned_rows)
    df_combined_features = pd.DataFrame(all_features_rows)
    
    out_aligned_path = os.path.join(BASE_DIR, "combined_ground_truth_aligned.csv")
    out_features_path = os.path.join(BASE_DIR, "combined_features.csv")
    
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
