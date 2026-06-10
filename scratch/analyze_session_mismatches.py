#!/usr/bin/env python3
import os
import sys
import json
import numpy as np
import pandas as pd

def load_data(session_dir):
    gyro = pd.read_csv(os.path.join(session_dir, "WatchGyroscope.csv"))
    accel = pd.read_csv(os.path.join(session_dir, "WatchAccelerometer.csv"))
    gravity = pd.read_csv(os.path.join(session_dir, "WatchGravity.csv"))
    
    game_orient_path = os.path.join(session_dir, "WatchGameOrientation.csv")
    orient_path = os.path.join(session_dir, "WatchOrientation.csv")
    orient = pd.read_csv(game_orient_path) if os.path.exists(game_orient_path) else pd.read_csv(orient_path)
    
    steps_path = os.path.join(session_dir, "WatchSteps.csv")
    steps = pd.read_csv(steps_path) if os.path.exists(steps_path) else None
    
    return gyro, accel, gravity, orient, steps

def main():
    session_dir = "/Users/neilkloot/Code/Batting Sensor Stats/live_watch_sessions/session-2026-06-01_12-23-38"
    gyro, accel, gravity, orient, steps = load_data(session_dir)
    
    # Load offset
    timeline_path = os.path.join(session_dir, "latest_timeline.txt")
    start_ts = None
    watch_shots = []
    
    with open(timeline_path) as f:
        for line in f:
            line = line.strip()
            if line.startswith("SYSTEM_START:"):
                start_ts = int(line.split("Ts=")[1]) / 1000.0
            elif line.startswith("Shot:"):
                # Parse shot details
                parts = line.split(", ")
                shot_type = parts[0].split("Type=")[1]
                spd = float(parts[1].split("Spd=")[1])
                ts_ms = int(parts[-1].split("Ts=")[1]) / 1000.0
                rel_t = ts_ms - start_ts if start_ts else 0.0
                watch_shots.append({'time': rel_t, 'type': shot_type, 'speed': spd, 'raw_line': line})
                
    # Load narrations
    with open(os.path.join(session_dir, "narrations_raw.json")) as f:
        narrations = json.load(f)
        
    # Get offset
    narration_files = [f for f in os.listdir(session_dir) if f.startswith("narration_") and f.endswith(".m4a")]
    fname = narration_files[0]
    parts = fname.replace("narration_", "").replace(".m4a", "")
    import datetime
    dt = datetime.datetime.strptime(parts, "%Y%m%d_%H%M%S")
    audio_epoch = dt.timestamp()
    offset = audio_epoch - start_ts
    
    gt_shots = []
    for i, shot in enumerate(narrations):
        audio_t = shot['timestamp_seconds']
        sensor_t = audio_t + offset
        shot_type = shot.get('shot_type', 'Unknown')
        if any(term in shot_type.lower() for term in ['facing up', 'no shot', 'leave', 'evade']):
            continue
        gt_shots.append({'index': i+1, 'time': sensor_t, 'type': shot_type})
        
    print(f"Total Watch Shots: {len(watch_shots)}")
    print(f"Total Ground Truth Shots: {len(gt_shots)}")
    
    # Matching watch shots to GT
    matched_watch_indices = set()
    gt_matches = []
    
    for gt in gt_shots:
        best_match_idx = -1
        min_diff = 3.5
        for idx, ws in enumerate(watch_shots):
            diff = abs(ws['time'] - gt['time'])
            if diff < min_diff:
                min_diff = diff
                best_match_idx = idx
        if best_match_idx != -1:
            matched_watch_indices.add(best_match_idx)
            gt_matches.append({'gt': gt, 'ws': watch_shots[best_match_idx], 'diff': min_diff, 'matched': True})
        else:
            gt_matches.append({'gt': gt, 'ws': None, 'diff': None, 'matched': False})
            
    unmatched_watch_shots = [ws for idx, ws in enumerate(watch_shots) if idx not in matched_watch_indices]
    
    print(f"Matched Watch Shots: {len(matched_watch_indices)}")
    print(f"Unmatched Watch Shots (False Positives): {len(unmatched_watch_shots)}")
    
    # Analyze false positives sensor activity
    print("\n--- ANALYZING UNMATCHED WATCH SHOTS (FALSE POSITIVES) ---")
    fp_records = []
    for idx, ws in enumerate(unmatched_watch_shots[:15]): # Print first 15 details
        t = ws['time']
        # Compute pre-trigger metrics
        t_start = t - 1.5
        t_end = t - 0.2
        
        g_win = gyro[(gyro['seconds_elapsed'] >= t_start) & (gyro['seconds_elapsed'] <= t_end)]
        gyro_std = np.std(np.sqrt(g_win['x']**2 + g_win['y']**2 + g_win['z']**2)) if len(g_win) >= 2 else 0.0
        
        a_win = accel[(accel['seconds_elapsed'] >= t_start) & (accel['seconds_elapsed'] <= t_end)]
        accel_std = np.std(np.sqrt(a_win['x']**2 + a_win['y']**2 + a_win['z']**2)) if len(a_win) >= 2 else 0.0
        
        gr_win = gravity[(gravity['seconds_elapsed'] >= t_start) & (gravity['seconds_elapsed'] <= t_end)]
        grav_y = np.mean(gr_win['y']) if len(gr_win) > 0 else 0.0
        
        print(f"FP {idx+1:>2}: Time={t:>6.1f}s, Type={ws['type']:<15}, gyro_std={gyro_std:.2f}, accel_std={accel_std:.2f}, grav_y={grav_y:.2f}")

if __name__ == "__main__":
    main()
