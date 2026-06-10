#!/usr/bin/env python3
import os
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
    return sensors

def main():
    records = []
    for s_cfg in sessions:
        s_dir = os.path.join(baseDir, s_cfg['relativePath'])
        wrist_dir = os.path.join(s_dir, s_cfg['wristFolder']) if s_cfg['wristFolder'] else s_dir
        
        sensors = load_all_sensors(wrist_dir)
        df_gyro = sensors.get("gyro")
        if df_gyro is None: continue
        
        # Load ground truth
        t_path = os.path.join(s_dir, s_cfg['transcriptFile'])
        if not os.path.exists(t_path): continue
            
        df_t = pd.read_csv(t_path)
        col_type = next((c for c in df_t.columns if c.lower() in ('shot_type', 'narration')), None)
        col_time = next((c for c in df_t.columns if c.lower() in ('impact_time_seconds', 'wrist_timestamp')), None)
        
        if not col_type or not col_time: continue
        
        gt_list = []
        for _, row in df_t.iterrows():
            t_val = row[col_time]
            type_val = row[col_type]
            if pd.isna(t_val) or pd.isna(type_val): continue
            gt_list.append((float(t_val), str(type_val)))
            
        for t_impact, shot_type in gt_list:
            if any(term in shot_type.lower() for term in ['facing up', 'no shot', 'leave', 'evade']):
                continue
            shot_class = normalize_shot_class(shot_type)
            if shot_class not in ("PULL/HOOK", "GLANCE/FLICK"): continue
            
            # Slice gyro
            mask = (df_gyro['seconds_elapsed'] >= t_impact - 0.8) & (df_gyro['seconds_elapsed'] <= t_impact + 0.3)
            sw = df_gyro[mask]
            if len(sw) < 2: continue
            
            y_vals = sw['y'].values
            
            # Gravity
            grav = sensors.get("gravity")
            if grav is not None:
                sw_grav = grav[(grav['seconds_elapsed'] >= t_impact - 0.8) & (grav['seconds_elapsed'] <= t_impact + 0.3)]
                if len(sw_grav) > 0:
                    grav_y_min = sw_grav['y'].min()
                    grav_y_max = sw_grav['y'].max()
                    grav_x_max = sw_grav['x'].max()
                    grav_x_min = sw_grav['x'].min()
                else:
                    continue
            else:
                continue
                
            records.append({
                'session': s_cfg['canonicalName'],
                'shot_class': shot_class,
                'gyro_y_min': y_vals.min(),
                'grav_y_min': grav_y_min,
                'grav_y_max': grav_y_max,
                'grav_x_min': grav_x_min,
                'grav_x_max': grav_x_max
            })
            
    df = pd.DataFrame(records)
    print(f"Total extracted: {len(df)}")
    
    # Save to CSV for reference
    df.to_csv("scratch/pull_vs_glance_features.csv", index=False)
    
    # Show stats
    print("\nSummary Statistics:")
    print(df.groupby('shot_class')[['gyro_y_min', 'grav_y_min', 'grav_y_max', 'grav_x_min', 'grav_x_max']].describe().T)

if __name__ == "__main__":
    main()
