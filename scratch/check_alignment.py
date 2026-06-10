import os
import re
import pandas as pd
import numpy as np

BASE_DIR = "/Users/neilkloot/Code/Batting Sensor Stats"
SESSION_DIR = os.path.join(BASE_DIR, "live_watch_sessions/sessions/session-2026-06-08_12-22-26")

def main():
    timeline_path = os.path.join(SESSION_DIR, "latest_timeline.txt")
    gt_path = os.path.join(SESSION_DIR, "ground_truth_aligned.csv")
    
    if not os.path.exists(timeline_path) or not os.path.exists(gt_path):
        print("Files not found")
        return
        
    # Read SYSTEM_START
    system_start = None
    timeline_shots = []
    with open(timeline_path) as f:
        for line in f:
            if line.startswith("SYSTEM_START:"):
                system_start = int(line.split("Ts=")[1].strip())
            elif line.startswith("Shot:"):
                # parse Ts and type
                m_ts = re.search(r"Ts=(\d+)", line)
                m_type = re.search(r"Type=(\S+),", line)
                if m_ts and m_type:
                    timeline_shots.append({
                        'ts': int(m_ts.group(1)),
                        'type': m_type.group(1)
                    })
                    
    print(f"SYSTEM_START: {system_start}")
    print(f"Number of shots in timeline: {len(timeline_shots)}")
    
    if timeline_shots and system_start:
        first_timeline_t = (timeline_shots[0]['ts'] - system_start) / 1000.0
        print(f"First timeline shot elapsed seconds from SYSTEM_START: {first_timeline_t:.3f}s")
        
    # Read ground_truth_aligned.csv
    df_gt = pd.read_csv(gt_path)
    df_gt_swings = df_gt[~df_gt['shot_type'].isin(['Facing up', 'no shot', 'leave', 'evade', 'evasion', 'NON-SWING'])]
    print(f"Number of swings in ground truth: {len(df_gt_swings)}")
    
    if len(df_gt_swings) > 0:
        first_gt_t = df_gt_swings.iloc[0]['impact_time_seconds']
        first_gt_audio_t = df_gt_swings.iloc[0]['audio_time_seconds']
        first_gt_narr_t = df_gt_swings.iloc[0]['sensor_narr_time_seconds']
        print(f"First GT swing impact_time_seconds: {first_gt_t:.3f}s")
        print(f"First GT swing audio_time_seconds: {first_gt_audio_t:.3f}s")
        print(f"First GT swing sensor_narr_time_seconds: {first_gt_narr_t:.3f}s")
        
    # Let's inspect the offset between timeline shots and GT aligned shots
    print("\nComparing timeline shots vs GT aligned shots:")
    # We want to see if they match up when shifted by some constant
    # Let's print the first 10 shots of both
    for i in range(min(10, len(timeline_shots), len(df_gt_swings))):
        timeline_el = (timeline_shots[i]['ts'] - system_start) / 1000.0
        gt_el = df_gt_swings.iloc[i]['impact_time_seconds']
        diff = gt_el - timeline_el
        print(f"Shot {i+1}: Timeline relative = {timeline_el:.3f}s, GT Aligned relative = {gt_el:.3f}s, Diff = {diff:.3f}s")

if __name__ == '__main__':
    main()
