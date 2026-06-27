#!/usr/bin/env python3
import os
import json
import numpy as np
import pandas as pd
from scipy.stats import skew as scipy_skew

sessions = [
    {
        "id": "pull_shots",
        "canonicalName": "Pull shots",
        "relativePath": "ground_truth/2026_05_02/Pull shots",
        "wristFolder": "Wrist_pull_shots-2026-05-02_02-15-11",
        "transcriptFile": "pull_shots_full_transcript.csv",
    },
    {
        "id": "cover_drives",
        "canonicalName": "Cover drives",
        "relativePath": "ground_truth/2026_05_02/Cover drives ",
        "wristFolder": "Wrist_cover_drives-2026-05-02_02-40-41",
        "transcriptFile": "cover_drives_transcript.csv",
    },
    {
        "id": "on_drives",
        "canonicalName": "On drives and flick shots",
        "relativePath": "ground_truth/2026_05_02/On drives and flick shots",
        "wristFolder": "Wrist_on_drives_and_flick_shots-2026-05-02_02-30-57",
        "transcriptFile": "on_drives_flick_shots_full_transcript.csv",
    },
    {
        "id": "full_toss",
        "canonicalName": "full_toss",
        "relativePath": "ground_truth/2026_05_10/full_toss",
        "wristFolder": "Wrist_-_full_toss-2026-05-10_05-28-06",
        "transcriptFile": "full_toss_practice_transcript.csv",
    },
    {
        "id": "live_session_1",
        "canonicalName": "live_session_1",
        "relativePath": "live_watch_sessions/session-2026-05-23_15-01-17",
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
    }
]

baseDir = "/Users/neilkloot/Code/Batting Sensor Stats"
unifiedFile = pd.read_csv(os.path.join(baseDir, "analysis_outputs/unified_labeled_shots.csv"))

def normalize_shot_class(shot_name):
    if not shot_name: return "Unknown"
    s = shot_name.lower().strip()
    if "pull" in s or "hook" in s: return "PULL/HOOK"
    if "flick" in s or "glance" in s or "sweep" in s: return "GLANCE/FLICK/SWEEP"
    if "cut" in s or "punch" in s: return "CUT/PUNCH"
    if "guide" in s or "glide" in s or "deflection" in s or "deflect" in s: return "DEFLECTION/GUIDE"
    if "power" in s or "loft" in s: return "POWER SHOT"
    if any(t in s for t in ["drive","defence","defense","push","straight","forward","block"]): return "DRIVE/DEFENCE"
    return "Unknown"

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
    for name in ["gyro", "accel", "gravity", "mag"]:
        if name in sensors:
            df = sensors[name]
            df['mag_total'] = np.sqrt(df['x']**2 + df['y']**2 + df['z']**2)
    return sensors

def main():
    records = []
    
    for s_cfg in sessions:
        s_dir = os.path.join(baseDir, s_cfg['relativePath'])
        wrist_dir = os.path.join(s_dir, s_cfg['wristFolder']) if s_cfg['wristFolder'] else s_dir
        
        sensors = load_all_sensors(wrist_dir)
        df_gyro = sensors.get("gyro")
        if df_gyro is None:
            print(f"⚠️ Gyroscope missing for {s_cfg['canonicalName']}")
            continue
            
        # Load ground truth
        t_path = os.path.join(s_dir, s_cfg['transcriptFile'])
        if not os.path.exists(t_path):
            print(f"⚠️ Transcript missing for {s_cfg['canonicalName']}")
            continue
            
        df_t = pd.read_csv(t_path)
        
        # Find time and type columns
        col_type = next((c for c in df_t.columns if c.lower() in ('shot_type', 'narration')), None)
        col_time = next((c for c in df_t.columns if c.lower() in ('impact_time_seconds', 'wrist_timestamp')), None)
        
        if not col_type or not col_time:
            # Fallback to loading from unifiedFile matching this session
            df_s_gt = unifiedFile[unifiedFile['session'] == s_cfg['canonicalName']]
            gt_list = []
            for _, row in df_s_gt.iterrows():
                gt_list.append((row['wrist_timestamp'], row['shot_type']))
        else:
            gt_list = []
            for _, row in df_t.iterrows():
                t_val = row[col_time]
                type_val = row[col_type]
                if pd.isna(t_val) or pd.isna(type_val): continue
                gt_list.append((float(t_val), str(type_val)))
                
        # Extract features for each shot
        for t_impact, shot_type in gt_list:
            if any(term in shot_type.lower() for term in ['facing up', 'no shot', 'leave', 'evade']):
                continue
            shot_class = normalize_shot_class(shot_type)
            if shot_class == "Unknown": continue
            
            # Slice gyro around impact
            mask = (df_gyro['seconds_elapsed'] >= t_impact - 0.8) & (df_gyro['seconds_elapsed'] <= t_impact + 0.3)
            sw = df_gyro[mask]
            if len(sw) < 2: continue
            
            y_vals = sw['y'].values
            z_vals = sw['z'].values
            x_vals = sw['x'].values
            mag_vals = np.sqrt(x_vals**2 + y_vals**2 + z_vals**2)
            
            # Gravity
            grav = sensors.get("gravity")
            if grav is not None:
                sw_grav = grav[(grav['seconds_elapsed'] >= t_impact - 0.8) & (grav['seconds_elapsed'] <= t_impact + 0.3)]
                grav_y_min = sw_grav['y'].min() if len(sw_grav) > 0 else -9.8
                grav_x_max = sw_grav['x'].max() if len(sw_grav) > 0 else 0.0
            else:
                grav_y_min = -9.8
                grav_x_max = 0.0
                
            records.append({
                'session': s_cfg['canonicalName'],
                'shot_class': shot_class,
                'raw_type': shot_type,
                'gyro_y_min': y_vals.min(),
                'gyro_y_skew': float(scipy_skew(y_vals)) if np.std(y_vals) > 1e-6 else 0.0,
                'gyro_z_min': z_vals.min(),
                'gyro_mag_max': mag_vals.max(),
                'grav_y_min': grav_y_min,
                'grav_x_max': grav_x_max
            })
            
    df_res = pd.DataFrame(records)
    print(f"\nTotal shots extracted across all sessions: {len(df_res)}")
    
    # Group by shot_class and print statistics
    print("\n==========================================================================================")
    print("  GYRO & GRAVITY METRICS BY BIOMECHANICAL SHOT CLASS (AGGREGATED)")
    print("==========================================================================================")
    print(f"{'Shot Class':<20} {'Count':>5} {'Mean GyYmin':>12} {'Mean GyYskew':>12} {'Mean GrYmin':>12} {'Mean GrXmax':>12}")
    print("─"*85)
    for cls in sorted(df_res['shot_class'].unique()):
        sub = df_res[df_res['shot_class'] == cls]
        print(f"{cls:<20} {len(sub):>5} "
              f"{sub['gyro_y_min'].mean():>12.2f} "
              f"{sub['gyro_y_skew'].mean():>12.2f} "
              f"{sub['grav_y_min'].mean():>12.2f} "
              f"{sub['grav_x_max'].mean():>12.2f}")
              
if __name__ == "__main__":
    main()
