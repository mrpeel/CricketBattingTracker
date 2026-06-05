#!/usr/bin/env python3
import os
import json
import numpy as np
import pandas as pd
from collections import Counter
from scipy.stats import skew as scipy_skew

sessions = [
    {
        "id": "pull_shots",
        "canonicalName": "Pull shots",
        "relativePath": "old_session_data/2026_05_02/Pull shots",
        "wristFolder": "Wrist_pull_shots-2026-05-02_02-15-11",
        "transcriptFile": "pull_shots_full_transcript.csv",
    },
    {
        "id": "cover_drives",
        "canonicalName": "Cover drives",
        "relativePath": "old_session_data/2026_05_02/Cover drives ",
        "wristFolder": "Wrist_cover_drives-2026-05-02_02-40-41",
        "transcriptFile": "cover_drives_transcript.csv",
    },
    {
        "id": "on_drives",
        "canonicalName": "On drives and flick shots",
        "relativePath": "old_session_data/2026_05_02/On drives and flick shots",
        "wristFolder": "Wrist_on_drives_and_flick_shots-2026-05-02_02-30-57",
        "transcriptFile": "on_drives_flick_shots_full_transcript.csv",
    },
    {
        "id": "full_toss",
        "canonicalName": "full_toss",
        "relativePath": "old_session_data/2026_05_10/full_toss",
        "wristFolder": "Wrist_-_full_toss-2026-05-10_05-28-06",
        "transcriptFile": "full_toss_practice_transcript.csv",
    },
    {
        "id": "live_session_1",
        "canonicalName": "live_session_1",
        "relativePath": "old_session_data/session-2026-05-23_15-01-17",
        "wristFolder": "",
        "transcriptFile": "ground_truth_aligned.csv",
    },
    {
        "id": "session_20260530",
        "canonicalName": "session_20260530",
        "relativePath": "live_watch_sessions/session-2026-05-30_15-04-41",
        "wristFolder": "",
        "transcriptFile": "ground_truth_aligned.csv",
    },
    {
        "id": "session_20260531_10",
        "canonicalName": "session_20260531_10",
        "relativePath": "live_watch_sessions/session-2026-05-31_10-06-52",
        "wristFolder": "",
        "transcriptFile": "ground_truth_aligned.csv",
    },
    {
        "id": "session_20260531",
        "canonicalName": "session_20260531",
        "relativePath": "live_watch_sessions/session-2026-05-31_14-12-10",
        "wristFolder": "",
        "transcriptFile": "ground_truth_aligned.csv",
    },
    {
        "id": "session_20260601",
        "canonicalName": "session_20260601",
        "relativePath": "live_watch_sessions/session-2026-06-01_12-23-38",
        "wristFolder": "",
        "transcriptFile": "ground_truth_aligned.csv",
    },
    {
        "id": "session_20260605",
        "canonicalName": "session_20260605",
        "relativePath": "live_watch_sessions/session-2026-06-05_12-29-59",
        "wristFolder": "",
        "transcriptFile": "ground_truth_aligned.csv",
    }
]

baseDir = "/Users/neilkloot/Code/Batting Sensor Stats"
NON_SWING_TYPES = {'facing up', 'no shot', 'leave', 'evade', 'evasion'}

def normalize_shot_class(shot_name):
    if not shot_name: return "Unknown"
    s = shot_name.lower().strip()
    if "pull" in s or "hook" in s: return "PULL/HOOK"
    if "flick" in s or "glance" in s: return "GLANCE/FLICK"
    if "cut" in s or "punch" in s: return "CUT/PUNCH"
    if "guide" in s or "glide" in s or "deflection" in s or "deflect" in s: return "DEFLECTION/GUIDE"
    if "power" in s or "loft" in s: return "POWER SHOT"
    if any(t in s for t in ["drive","defence","defense","push","straight","forward","block"]): return "DRIVE/DEFENCE"
    return "Unknown"

# --- Quaternion math ---
def multiply_quats(q1, q2):
    x1,y1,z1,w1 = q1
    x2,y2,z2,w2 = q2
    return np.array([
        w1*x2 + x1*w2 + y1*z2 - z1*y2,
        w1*y2 - x1*z2 + y1*w2 + z1*x2,
        w1*z2 + x1*y2 - y1*x2 + z1*w2,
        w1*w2 - x1*x2 - y1*y2 - z1*z2,
    ])

def conjugate_quat(q):
    return np.array([-q[0], -q[1], -q[2], q[3]])

def rotate_vector(q, v):
    qx,qy,qz,qw = q
    vx,vy,vz = v
    tx = 2.0*(qy*vz - qz*vy)
    ty = 2.0*(qz*vx - qx*vz)
    tz = 2.0*(qx*vy - qy*vx)
    return np.array([
        vx + qw*tx + (qy*tz - qz*ty),
        vy + qw*ty + (qz*tx - qx*tz),
        vz + qw*tz + (qx*ty - qy*tx),
    ])

def calc_relative_roll(q):
    x,y,z,w = q
    return np.degrees(np.arctan2(2.0*(w*y + x*z), 1.0 - 2.0*(y*y + z*z)))

def average_quats(qx_arr, qy_arr, qz_arr, qw_arr):
    if len(qx_arr) == 0:
        return np.array([0,0,0,1.0])
    q0 = np.array([qx_arr[0], qy_arr[0], qz_arr[0], qw_arr[0]])
    s = q0.copy()
    for i in range(1, len(qx_arr)):
        qi = np.array([qx_arr[i], qy_arr[i], qz_arr[i], qw_arr[i]])
        dot = np.dot(q0, qi)
        sign = 1.0 if dot >= 0 else -1.0
        s += sign * qi
    norm = np.linalg.norm(s)
    return s / norm if norm > 0 else np.array([0,0,0,1.0])

V_LOCAL = np.array([0.0, -1.0, 0.0])

def load_all_sensors(session_dir):
    sensors = {}
    for name, fnames in [
        ("gyro", ["WatchGyroscope.csv", "Gyroscope.csv"]),
        ("accel", ["WatchAccelerometer.csv", "Accelerometer.csv"]),
        ("gravity", ["WatchGravity.csv", "Gravity.csv"]),
        ("mag", ["WatchMagnetometer.csv", "Magnetometer.csv"]),
        ("game_orient", ["WatchGameOrientation.csv"]),
        ("orient", ["WatchOrientation.csv", "Orientation.csv"])
    ]:
        for fname in fnames:
            path = os.path.join(session_dir, fname)
            if os.path.exists(path):
                df = pd.read_csv(path)
                if len(df) > 0:
                    sensors[name] = df
                    break
    for name in ["gyro","accel","gravity","mag"]:
        if name in sensors:
            df = sensors[name]
            df['mag_total'] = np.sqrt(df['x']**2 + df['y']**2 + df['z']**2)
    return sensors

def get_offset(session_dir):
    import datetime
    narration_files = [f for f in os.listdir(session_dir) if f.startswith("narration_") and f.endswith(".m4a")]
    if not narration_files: return 0.0
    fname = narration_files[0]
    parts = fname.replace("narration_","").replace(".m4a","")
    try:
        dt = datetime.datetime.strptime(parts, "%Y%m%d_%H%M%S")
        audio_epoch = dt.timestamp()
        with open(os.path.join(session_dir, "latest_timeline.txt")) as f:
            for line in f:
                if line.startswith("SYSTEM_START:"):
                    watch_epoch = int(line.split("Ts=")[1].strip()) / 1000.0
                    return audio_epoch - watch_epoch
    except: pass
    return 0.0

def extract_shot_features(sensors, t_shot, stance_window=2.0, swing_window_before=0.8, swing_window_after=0.3):
    feats = {}
    gyro = sensors.get("gyro")
    if gyro is not None:
        sw = gyro[(gyro['seconds_elapsed'] >= t_shot - swing_window_before) & (gyro['seconds_elapsed'] <= t_shot + swing_window_after)]
        if len(sw) >= 2:
            feats['gyroMag'] = sw['mag_total'].max()
            feats['gyro_y_min'] = sw['y'].min()
            feats['gyro_y_max'] = sw['y'].max()
            feats['gyro_y_skew'] = float(scipy_skew(sw['y'].values)) if np.std(sw['y'].values) > 1e-6 else 0.0
            feats['gyro_z_min'] = sw['z'].min()
        else:
            feats['gyroMag'] = 0.0
            feats['gyro_y_min'] = 0.0
            feats['gyro_y_max'] = 0.0
            feats['gyro_y_skew'] = 0.0
            feats['gyro_z_min'] = 0.0

    orient = sensors.get("game_orient", sensors.get("orient"))
    if orient is not None:
        stance_ori = orient[(orient['seconds_elapsed'] >= t_shot - stance_window - 0.5) & (orient['seconds_elapsed'] <= t_shot - stance_window + 0.5)]
        if len(stance_ori) < 3:
            stance_ori = orient[(orient['seconds_elapsed'] >= t_shot - 3.0) & (orient['seconds_elapsed'] <= t_shot - 1.5)]
        if len(stance_ori) >= 2:
            q_stance = average_quats(stance_ori['qx'].values, stance_ori['qy'].values, stance_ori['qz'].values, stance_ori['qw'].values)
        else:
            q_stance = np.array([0,0,0,1.0])
        
        q_stance_inv = conjugate_quat(q_stance)
        
        swing_ori = orient[(orient['seconds_elapsed'] >= t_shot - swing_window_before) & (orient['seconds_elapsed'] <= t_shot + swing_window_after)]
        if len(swing_ori) >= 2:
            min_x = 1e10; max_x = -1e10
            min_z = 1e10; max_z = -1e10
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
        else:
            feats['deltaX'] = 0.0
            feats['deltaZ'] = 0.0
            feats['gameori_qz_range'] = 0.0
            
        impact_ori = orient[(orient['seconds_elapsed'] >= t_shot - 0.1) & (orient['seconds_elapsed'] <= t_shot + 0.1)]
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
        
    grav = sensors.get("gravity")
    if grav is not None:
        w = grav[(grav['seconds_elapsed'] >= t_shot - swing_window_before) & (grav['seconds_elapsed'] <= t_shot + swing_window_after)]
        if len(w) >= 2:
            feats['grav_x_max'] = w['x'].max()
            feats['grav_y_min'] = w['y'].min()
        else:
            feats['grav_x_max'] = 0.0
            feats['grav_y_min'] = -9.8
    else:
        feats['grav_x_max'] = 0.0
        feats['grav_y_min'] = -9.8
        
    mag = sensors.get("mag")
    if mag is not None:
        w = mag[(mag['seconds_elapsed'] >= t_shot - swing_window_before) & (mag['seconds_elapsed'] <= t_shot + swing_window_after)]
        if len(w) >= 2:
            feats['mag_x_max'] = w['x'].max()
        else:
            feats['mag_x_max'] = 0.0
    else:
        feats['mag_x_max'] = 0.0
        
    return feats

def classify_current(f):
    gyroMag = f['gyroMag']
    roll = f['rollImpactDeg']
    yaw = f['yawImpactDeg']
    dx = f['deltaX']
    dz = f['deltaZ']
    ratio = f['planeRatio']
    
    if gyroMag > 22.12: return "POWER SHOT"
    if roll <= -3.22:
        if dz <= 0.44:
            if dx <= 0.75:
                return "DRIVE/DEFENCE" if gyroMag <= 14.11 else ("PULL/HOOK" if roll <= -15.0 and dx >= 0.30 else "CUT/PUNCH")
            else:
                return "GLANCE/FLICK" if dx <= 0.97 else ("PULL/HOOK" if roll <= -15.0 and dx >= 0.30 else "CUT/PUNCH")
        else:
            if yaw <= 6.22:
                return "DRIVE/DEFENCE" if ratio <= 0.67 else "DEFLECTION/GUIDE"
            else:
                return ("PULL/HOOK" if roll <= -15.0 and dx >= 0.30 else "CUT/PUNCH") if roll <= -35.84 else "DRIVE/DEFENCE"
    else:
        if ratio <= 2.85:
            if roll <= 18.16:
                return "DRIVE/DEFENCE" if roll <= 1.67 else ("PULL/HOOK" if roll <= -15.0 and dx >= 0.30 else "CUT/PUNCH")
            else:
                return "DRIVE/DEFENCE" if gyroMag <= 11.72 else "GLANCE/FLICK"
        else:
            return "DRIVE/DEFENCE" if yaw <= 3.94 else "GLANCE/FLICK"

# --- Proposed Overrides ---

def classify_override_variant1(f):
    # Proposed Override: if predicted as DRIVE/DEFENCE, but gyro_y_min <= -4.0 rad/s, override to GLANCE/FLICK
    base = classify_current(f)
    if base == "DRIVE/DEFENCE" and f['gyro_y_min'] <= -4.0:
        return "GLANCE/FLICK"
    return base

def classify_override_variant2(f):
    # Proposed Override: Require negative roll (closed bat face) and gyro_y_min <= -4.5
    base = classify_current(f)
    if base == "DRIVE/DEFENCE" and f['gyro_y_min'] <= -4.5 and f['rollImpactDeg'] <= -3.22:
        return "GLANCE/FLICK"
    return base

def classify_override_variant3(f):
    # Proposed Override: Add yaw check (leg side)
    base = classify_current(f)
    if base == "DRIVE/DEFENCE" and f['gyro_y_min'] <= -4.5 and f['rollImpactDeg'] <= -3.22 and f['yawImpactDeg'] >= 15.0:
        return "GLANCE/FLICK"
    return base

def classify_override_variant4(f):
    # Proposed Override: What if the base is CUT/PUNCH or PULL/HOOK but it's actually GLANCE/FLICK?
    # Glances with roll <= -15 and dx >= 0.30 get classified as PULL/HOOK in the tree.
    # Let's see if we can differentiate PULL/HOOK from GLANCE/FLICK.
    base = classify_current(f)
    # If base is PULL/HOOK, but it has steep Y gravity (grav_y_min <= -8.0) and moderate roll, is it GLANCE/FLICK?
    # Let's see if we can override PULL/HOOK to GLANCE/FLICK
    if base == "PULL/HOOK" and f['gyro_y_min'] >= -9.0 and f['grav_y_min'] <= -8.0 and f['rollImpactDeg'] >= -50.0:
        # Glances have vertical bat, pulls have horizontal.
        return "GLANCE/FLICK"
    return base

def classify_override_variant5(f):
    # Proposed Override: Add deltaX <= 1.25 constraint to prevent On drive regression
    base = classify_current(f)
    if base == "DRIVE/DEFENCE" and f['gyro_y_min'] <= -4.5 and f['rollImpactDeg'] <= -3.22 and f['yawImpactDeg'] >= 15.0 and f['deltaX'] <= 1.25:
        return "GLANCE/FLICK"
    return base

def classify_override_variant6(f):
    # Combine V4 and V5
    # Start with base
    base = classify_current(f)
    
    # Override A (from V5): DRIVE/DEFENCE -> GLANCE/FLICK
    if base == "DRIVE/DEFENCE" and f['gyro_y_min'] <= -6.0 and f['rollImpactDeg'] <= -3.22 and f['yawImpactDeg'] >= 15.0 and f['deltaX'] <= 1.25:
        return "GLANCE/FLICK"
        
    # Override B (from V4): PULL/HOOK -> GLANCE/FLICK
    if base == "PULL/HOOK" and -9.0 <= f['gyro_y_min'] <= -3.0 and f['grav_y_min'] <= -8.0 and f['rollImpactDeg'] >= -50.0:
        return "GLANCE/FLICK"
        
    return base

def classify_override_detector(f):
    # Current deployed overrides in SwingDetector.kt
    base = classify_current(f)
    
    # Override A: DRIVE/DEFENCE -> GLANCE/FLICK (gyro_y_min <= -4.5)
    if base == "DRIVE/DEFENCE" and f['gyro_y_min'] <= -4.5 and f['rollImpactDeg'] <= -3.22 and f['yawImpactDeg'] >= 15.0 and f['deltaX'] <= 1.25:
        return "GLANCE/FLICK"
        
    # Override B: PULL/HOOK -> GLANCE/FLICK (gyro_y_min >= -9.0)
    if base == "PULL/HOOK" and f['gyro_y_min'] >= -9.0 and f['grav_y_min'] <= -8.0 and f['rollImpactDeg'] >= -50.0:
        return "GLANCE/FLICK"
        
    return base

def main():
    # Load all shots across all sessions
    all_shots = []
    
    for s_cfg in sessions:
        s_dir = os.path.join(baseDir, s_cfg['relativePath'])
        wrist_dir = os.path.join(s_dir, s_cfg['wristFolder']) if s_cfg['wristFolder'] else s_dir
        
        sensors = load_all_sensors(wrist_dir)
        df_gyro = sensors.get("gyro")
        if df_gyro is None: continue
        
        offset = get_offset(wrist_dir)
        
        t_path = os.path.join(s_dir, s_cfg['transcriptFile'])
        if not os.path.exists(t_path): continue
            
        df_t = pd.read_csv(t_path)
        col_type = next((c for c in df_t.columns if c.lower() in ('shot_type', 'narration')), None)
        col_time = next((c for c in df_t.columns if c.lower() in ('impact_time_seconds', 'wrist_timestamp')), None)
        
        if not col_type or not col_time: continue
        
        aligned_path = os.path.join(s_dir, "ground_truth_aligned.csv")
        aligned_df = pd.read_csv(aligned_path) if os.path.exists(aligned_path) else None
        
        for _, row in df_t.iterrows():
            t_val = row[col_time]
            type_val = row[col_type]
            if pd.isna(t_val) or pd.isna(type_val): continue
            
            shot_type = str(type_val)
            if any(term in shot_type.lower() for term in ['facing up', 'no shot', 'leave', 'evade']):
                continue
                
            gt_class = normalize_shot_class(shot_type)
            if gt_class in ("Unknown", "Miss", "Sweep"): continue
            
            audio_time = row.get('timestamp_seconds', t_val)
            sensor_time = float(t_val)
            if aligned_df is not None:
                matched = aligned_df[
                    (aligned_df['shot_type'] == shot_type) &
                    (abs(aligned_df['audio_time_seconds'] - audio_time) < 1.0)
                ]
                if len(matched) > 0:
                    sensor_time = matched.iloc[0]['impact_time_seconds']
            
            feats = extract_shot_features(sensors, sensor_time)
            if not feats or 'gyroMag' not in feats: continue
            
            feats['gt_class'] = gt_class
            feats['session'] = s_cfg['canonicalName']
            feats['raw_type'] = shot_type
            
            # Predict
            feats['pred_baseline'] = classify_current(feats)
            feats['pred_v1'] = classify_override_variant1(feats)
            feats['pred_v2'] = classify_override_variant2(feats)
            feats['pred_v3'] = classify_override_variant3(feats)
            feats['pred_v4'] = classify_override_variant4(feats)
            feats['pred_v5'] = classify_override_variant5(feats)
            feats['pred_v6'] = classify_override_variant6(feats)
            feats['pred_detector'] = classify_override_detector(feats)
            
            all_shots.append(feats)
            
    df = pd.DataFrame(all_shots)
    total = len(df)
    print(f"Loaded {total} shots across all sessions.")
    
    # Evaluate baseline vs variants
    correct_base = sum(df['pred_baseline'] == df['gt_class'])
    correct_v1 = sum(df['pred_v1'] == df['gt_class'])
    correct_v2 = sum(df['pred_v2'] == df['gt_class'])
    correct_v3 = sum(df['pred_v3'] == df['gt_class'])
    correct_v4 = sum(df['pred_v4'] == df['gt_class'])
    correct_v5 = sum(df['pred_v5'] == df['gt_class'])
    correct_v6 = sum(df['pred_v6'] == df['gt_class'])
    correct_det = sum(df['pred_detector'] == df['gt_class'])
    
    print(f"\nOverall Results:")
    print(f"Baseline Accuracy (No Overrides): {correct_base}/{total} ({100*correct_base/total:.1f}%)")
    print(f"Variant 1 (GyYmin <= -4.0) Accuracy: {correct_v1}/{total} ({100*correct_v1/total:.1f}%)")
    print(f"Variant 2 (GyYmin <= -4.5, Roll <= -3.22) Accuracy: {correct_v2}/{total} ({100*correct_v2/total:.1f}%)")
    print(f"Variant 3 (GyYmin <= -4.5, Roll <= -3.22, Yaw >= 15.0) Accuracy: {correct_v3}/{total} ({100*correct_v3/total:.1f}%)")
    print(f"Variant 4 (PULL/HOOK -> GLANCE/FLICK) Accuracy: {correct_v4}/{total} ({100*correct_v4/total:.1f}%)")
    print(f"Variant 5 (GyYmin <= -4.5, Roll <= -3.22, Yaw >= 15.0, DX <= 1.25) Accuracy: {correct_v5}/{total} ({100*correct_v5/total:.1f}%)")
    print(f"Variant 6 (Proposed: Combine V4 and V5 with tighter gates) Accuracy: {correct_v6}/{total} ({100*correct_v6/total:.1f}%)")
    print(f"Current Deployed SwingDetector.kt Overrides Accuracy: {correct_det}/{total} ({100*correct_det/total:.1f}%)")
    
    # Per-session breakdown
    print("\n" + "="*70)
    print("PER-SESSION ACCURACY BREAKDOWN (Currently Deployed vs Proposed Variant 6)")
    print("="*70)
    
    sessions_in_df = df['session'].unique()
    for s_name in sessions_in_df:
        sdf = df[df['session'] == s_name]
        s_total = len(sdf)
        s_det = sum(sdf['pred_detector'] == sdf['gt_class'])
        s_v6 = sum(sdf['pred_v6'] == sdf['gt_class'])
        s_imp = sdf[(sdf['pred_v6'] == sdf['gt_class']) & (sdf['pred_detector'] != sdf['gt_class'])]
        s_reg = sdf[(sdf['pred_v6'] != sdf['gt_class']) & (sdf['pred_detector'] == sdf['gt_class'])]
        
        is_live = "live" in s_name or "session_20" in s_name
        live_label = " [LIVE]" if is_live else " [HISTORICAL]"
        
        print(f"\n{s_name}{live_label}:")
        print(f"  Shots loaded: {s_total}")
        print(f"  Currently Deployed Accuracy: {s_det}/{s_total} ({100*s_det/s_total:.1f}%)")
        print(f"  Proposed Variant 6 Accuracy: {s_v6}/{s_total} ({100*s_v6/s_total:.1f}%)")
        print(f"  Net change: +{len(s_imp)} improved, -{len(s_reg)} regressed")
        
        if len(s_imp) > 0:
            print("  Improvements:")
            for _, row in s_imp.iterrows():
                print(f"    - {row['raw_type']}: {row['pred_detector']} -> {row['pred_v6']} (gyro_y_min={row['gyro_y_min']:.2f}, roll={row['rollImpactDeg']:.2f}, yaw={row['yawImpactDeg']:.2f}, dx={row['deltaX']:.2f}, grav_y_min={row['grav_y_min']:.2f})")
        if len(s_reg) > 0:
            print("  Regressions:")
            for _, row in s_reg.iterrows():
                print(f"    - {row['raw_type']}: {row['pred_detector']} -> {row['pred_v6']} (gyro_y_min={row['gyro_y_min']:.2f}, roll={row['rollImpactDeg']:.2f}, yaw={row['yawImpactDeg']:.2f}, dx={row['deltaX']:.2f}, grav_y_min={row['grav_y_min']:.2f})")

    # Regression analysis for Variant 6 (overall summary vs Deployed)
    print("\n" + "="*50)
    print("OVERALL SUMMARY OF CHANGES VS CURRENT DEPLOYED")
    print("="*50)
    imp = df[(df['pred_v6'] == df['gt_class']) & (df['pred_detector'] != df['gt_class'])]
    print(f"Total improved: {len(imp)}")
    for _, row in imp.iterrows():
        print(f"  [{row['session']}] {row['raw_type']}: Pred {row['pred_detector']} -> {row['pred_v6']} (GT {row['gt_class']}) (gyro_y_min={row['gyro_y_min']:.2f}, roll={row['rollImpactDeg']:.2f}, yaw={row['yawImpactDeg']:.2f}, dx={row['deltaX']:.2f})")
        
    print("\nVariant 6 Regressions vs Deployed:")
    reg = df[(df['pred_v6'] != df['gt_class']) & (df['pred_detector'] == df['gt_class'])]
    print(f"Total regressed: {len(reg)}")
    for _, row in reg.iterrows():
        print(f"  [{row['session']}] {row['raw_type']}: Pred {row['pred_detector']} -> {row['pred_v6']} (GT {row['gt_class']}) (gyro_y_min={row['gyro_y_min']:.2f}, roll={row['rollImpactDeg']:.2f}, yaw={row['yawImpactDeg']:.2f}, dx={row['deltaX']:.2f})")

if __name__ == "__main__":
    main()
