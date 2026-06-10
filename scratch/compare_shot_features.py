#!/usr/bin/env python3
import os
import json
import numpy as np
import pandas as pd
from scipy.stats import skew as scipy_skew

NON_SWING_TYPES = {'facing up', 'no shot', 'leave', 'evade', 'evasion'}

def normalize_shot_class(shot_name):
    if not shot_name:
        return "Unknown"
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
    for name, fname in [("gyro","WatchGyroscope.csv"),("accel","WatchAccelerometer.csv"),
                         ("gravity","WatchGravity.csv"),("mag","WatchMagnetometer.csv"),
                         ("game_orient","WatchGameOrientation.csv"),("orient","WatchOrientation.csv")]:
        path = os.path.join(session_dir, fname)
        if os.path.exists(path):
            df = pd.read_csv(path)
            if len(df) > 0:
                sensors[name] = df
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
    
    # Gyro
    gyro = sensors.get("gyro")
    if gyro is not None:
        sw = gyro[(gyro['seconds_elapsed'] >= t_shot - swing_window_before) & (gyro['seconds_elapsed'] <= t_shot + swing_window_after)]
        if len(sw) >= 2:
            feats['gyroMag'] = sw['mag_total'].max()
            feats['gyro_y_min'] = sw['y'].min()
            feats['gyro_y_max'] = sw['y'].max()
            feats['gyro_y_skew'] = float(scipy_skew(sw['y'].values)) if np.std(sw['y'].values) > 1e-6 else 0.0
            feats['gyro_z_min'] = sw['z'].min()
            feats['gyro_z_max'] = sw['z'].max()
            feats['gyro_z_skew'] = float(scipy_skew(sw['z'].values)) if np.std(sw['z'].values) > 1e-6 else 0.0
        else:
            feats['gyroMag'] = 0.0
            feats['gyro_y_min'] = 0.0
            feats['gyro_y_max'] = 0.0
            feats['gyro_y_skew'] = 0.0
            feats['gyro_z_min'] = 0.0
            feats['gyro_z_max'] = 0.0
            feats['gyro_z_skew'] = 0.0

    # Quaternions
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
        
    # Gravity
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

def main():
    session_dir = "/Users/neilkloot/Code/Batting Sensor Stats/live_watch_sessions/sessions/session-2026-06-05_12-29-59"
    sensors = load_all_sensors(session_dir)
    offset = get_offset(session_dir)
    
    with open(os.path.join(session_dir, "narrations_raw.json")) as f:
        narrations = json.load(f)
    
    aligned_path = os.path.join(session_dir, "ground_truth_aligned.csv")
    aligned_df = pd.read_csv(aligned_path) if os.path.exists(aligned_path) else None
    
    shots = []
    for n in narrations:
        st = n.get('shot_type', '')
        if st.lower() in NON_SWING_TYPES: continue
        gt_class = normalize_shot_class(st)
        if gt_class in ("Unknown", "Miss", "Sweep"): continue
        
        audio_time = n['timestamp_seconds']
        sensor_time = audio_time + offset
        if aligned_df is not None:
            matched = aligned_df[(aligned_df['shot_type'] == st) & (abs(aligned_df['audio_time_seconds'] - audio_time) < 1.0)]
            if len(matched) > 0:
                sensor_time = matched.iloc[0]['impact_time_seconds']
                
        feats = extract_shot_features(sensors, sensor_time)
        feats['gt_class'] = gt_class
        feats['raw_type'] = st
        feats['pred_class'] = classify_current(feats)
        shots.append(feats)
        
    df = pd.DataFrame(shots)
    
    print("==========================================================================================")
    print("  SHOT FEATURE DETAILS: DRIVE/DEFENCE vs GLANCE/FLICK in session-2026-06-01_12-23-38")
    print("==========================================================================================")
    print(f"{'Shot':<4} {'GT Class':<15} {'Pred Class':<15} {'Roll':>7} {'Yaw':>7} {'DX':>6} {'DZ':>6} {'Ratio':>6} {'GyMag':>6} {'GyYmin':>7} {'GyYmax':>7} {'QZrng':>6}")
    print("─"*105)
    for idx, s in enumerate(shots):
        print(f"{idx+1:<4} {s['gt_class']:<15} {s['pred_class']:<15} "
              f"{s['rollImpactDeg']:>7.1f} {s['yawImpactDeg']:>7.1f} {s['deltaX']:>6.2f} {s['deltaZ']:>6.2f} "
              f"{s['planeRatio']:>6.2f} {s['gyroMag']:>6.1f} {s['gyro_y_min']:>7.2f} {s['gyro_y_max']:>7.2f} {s['gameori_qz_range']:>6.2f}")
              
if __name__ == "__main__":
    main()
