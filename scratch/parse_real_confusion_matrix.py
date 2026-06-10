#!/usr/bin/env python3
import os
import json
import numpy as np
import pandas as pd

def normalize_shot_class(shot_name):
    if not shot_name:
        return "Unknown"
    s = shot_name.lower().strip()
    if "pull" in s or "hook" in s:
        return "PULL/HOOK"
    if "flick" in s or "glance" in s:
        return "GLANCE/FLICK"
    if "cut" in s or "punch" in s:
        return "CUT/PUNCH"
    if "guide" in s or "glide" in s or "deflection" in s or "deflect" in s:
        return "DEFLECTION/GUIDE"
    if "power" in s or "loft" in s:
        return "POWER SHOT"
    if any(t in s for t in ["drive", "defence", "defense", "push", "straight", "forward", "block"]):
        return "DRIVE/DEFENCE"
    return "Unknown"

def main():
    session_dir = "/Users/neilkloot/Code/Batting Sensor Stats/live_watch_sessions/session-2026-06-01_12-23-38"
    
    # Load narrations
    with open(os.path.join(session_dir, "narrations_raw.json")) as f:
        narrations = json.load(f)
        
    gt_shots = []
    for n in narrations:
        st = n.get('shot_type', '')
        if any(term in st.lower() for term in ['facing up', 'no shot', 'leave', 'evade']):
            continue
        gt_shots.append({
            'audio_time': n['timestamp_seconds'],
            'type': normalize_shot_class(st),
            'raw_type': st
        })
        
    # Load watch shots from timeline
    watch_shots = []
    start_ts = None
    with open(os.path.join(session_dir, "latest_timeline.txt")) as f:
        for line in f:
            if line.startswith("SYSTEM_START:"):
                start_ts = int(line.split("Ts=")[1]) / 1000.0
            elif line.startswith("Shot:"):
                parts = line.split(", ")
                shot_type = parts[0].split("Type=")[1]
                ts = int(parts[-1].split("Ts=")[1].strip()) / 1000.0
                rel_t = ts - start_ts if start_ts else 0.0
                watch_shots.append({
                    'time': rel_t,
                    'type': shot_type
                })
                
    print(f"Total Ground Truth Swings: {len(gt_shots)}")
    print(f"Total Watch Shots Detected: {len(watch_shots)}")
    
    # Match using 0.0 offset
    matches = []
    matched_watch_indices = set()
    
    for gt in gt_shots:
        best_ws = None
        min_diff = 4.0
        best_idx = -1
        for idx, ws in enumerate(watch_shots):
            if idx in matched_watch_indices:
                continue
            diff = abs(ws['time'] - gt['audio_time']) # offset is 0.0
            if diff < min_diff:
                min_diff = diff
                best_ws = ws
                best_idx = idx
        if best_ws is not None:
            matched_watch_indices.add(best_idx)
            matches.append({'gt': gt, 'ws': best_ws, 'diff': min_diff, 'matched': True})
        else:
            matches.append({'gt': gt, 'ws': None, 'diff': None, 'matched': False})
            
    print(f"Matched Swings: {len([m for m in matches if m['matched']])}")
    
    # Compute true confusion matrix
    y_true = []
    y_pred = []
    for m in matches:
        if m['matched']:
            y_true.append(m['gt']['type'])
            y_pred.append(m['ws']['type'])
            
    classes = sorted(list(set(y_true + y_pred)))
    
    print(f"\n{'='*60}")
    print("  TRUE CONFUSION MATRIX (Kotlin Classifier on Watch)")
    print(f"{'='*60}")
    print(f"\n  {'Predicted →':>20}", end="")
    for cls in classes:
        print(f" {cls[:8]:>8}", end="")
    print()
    print(f"  {'Actual ↓':>20}", end="")
    for _ in classes:
        print(f" {'────────':>8}", end="")
    print()
    
    for actual in classes:
        print(f"  {actual[:20]:>20}", end="")
        for pred in classes:
            count = sum(1 for t, p in zip(y_true, y_pred) if t == actual and p == pred)
            if count > 0:
                marker = f"[{count}]" if actual == pred else f" {count} "
                print(f" {marker:>8}", end="")
            else:
                print(f" {'·':>8}", end="")
        print()
        
    # Accuracy
    correct = sum(1 for t, p in zip(y_true, y_pred) if t == p)
    total = len(y_true)
    if total > 0:
        print(f"\nShot Classification Accuracy on Matched: {correct}/{total} ({100*correct/total:.1f}%)")
        
if __name__ == "__main__":
    main()
