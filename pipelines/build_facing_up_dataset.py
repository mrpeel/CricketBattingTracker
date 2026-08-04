#!/usr/bin/env python3
"""
build_facing_up_dataset.py — Build 423 Hz Session Dataset for Facing Up (Stance) Binary Detector.

Saves continuous 423 Hz IMU streams and stance labels across all 48 sessions in a fast,
compact dataset format (/Users/neilkloot/Code/CricketBattingTracker/facing_up_sessions_423hz.pkl).

Class 1 (Facing Up Stance):
  - Explicit Positives: Regions during "Facing up" narration entries where rotational velocity
    w < 1.0 rad/s and static gravity g_y <= -3.0 m/s^2.
  - Implicit Pre-Shot Positives (Fallback): For physical shots (T_shot) lacking a "Facing up"
    narration entry within 6s prior, mark [T_shot - 3.5s, T_shot - 1.0s] as Class 1.

Class 0 (Non-Stance):
  - Active Motion (Swings/Shots): Windows during backswing/stroke/follow-through (w >= 1.5 rad/s).
  - Ambient Rest: Windows during non-batting periods (walking, running between wickets, ball collection).

Holdout Partition:
  - Holdout Set: session_2026-07-21_12-43-37 & session_2026-07-25_15-16-32 (2 unseen Polar sessions).
  - Training Set: 46 remaining physical sessions.
"""

import os
import glob
import gzip
import struct
import json
import pickle
import numpy as np
import pandas as pd

BASE_DIR = "/Users/neilkloot/Code/Batting Sensor Stats/live_watch_sessions"
OUTPUT_PATH = "/Users/neilkloot/Code/CricketBattingTracker/facing_up_sessions_423hz.pkl"

HOLDOUT_SESSIONS = [
    "session_2026-07-21_12-43-37",
    "session_2026-07-25_15-16-32",
]

TARGET_HZ = 423

def load_watch_bin_xyz(path):
    if not os.path.exists(path):
        return None
    fmt = "<qffff"
    rs = struct.calcsize(fmt)
    with gzip.open(path, "rb") as f:
        data = f.read()
    n = len(data) // rs
    if n == 0:
        return None
    arr = np.empty((n, 4), dtype=np.float64)
    for i in range(n):
        t, sec, x, y, z = struct.unpack_from(fmt, data, i * rs)
        arr[i] = (sec, x, y, z)
    return arr

def load_polar_bin_xyz(path, is_gyro=False):
    if not os.path.exists(path):
        return None
    fmt = "<qqfff"
    rs = struct.calcsize(fmt)
    with gzip.open(path, "rb") as f:
        data = f.read()
    n = len(data) // rs
    if n == 0:
        return None
    arr = np.empty((n, 4), dtype=np.float64)
    scale = (np.pi / 180.0) if is_gyro else 0.00980665
    for i in range(n):
        phoneMs, sensorNs, x, y, z = struct.unpack_from(fmt, data, i * rs)
        arr[i] = (phoneMs / 1000.0, x * scale, y * scale, z * scale)
    return arr

def load_session_imu(sdir):
    w_acc = load_watch_bin_xyz(os.path.join(sdir, "WatchAccelerometer.bin.gz"))
    w_gyr = load_watch_bin_xyz(os.path.join(sdir, "WatchGyroscope.bin.gz"))
    w_grav = load_watch_bin_xyz(os.path.join(sdir, "WatchGravity.bin.gz"))
    
    if w_acc is None or w_gyr is None:
        return None
    
    p_acc = load_polar_bin_xyz(os.path.join(sdir, "PolarSense", "PolarAccelerometer.bin.gz"), is_gyro=False)
    
    t_start = max(w_acc[0, 0], w_gyr[0, 0])
    t_end = min(w_acc[-1, 0], w_gyr[-1, 0])
    if t_end <= t_start + 5.0:
        return None
    
    num_samples = int(np.round((t_end - t_start) * TARGET_HZ))
    t_grid = np.linspace(t_start, t_end, num_samples, endpoint=False)
    
    w_acc_grid = np.column_stack([np.interp(t_grid, w_acc[:, 0], w_acc[:, col]) for col in (1, 2, 3)])
    w_gyr_grid = np.column_stack([np.interp(t_grid, w_gyr[:, 0], w_gyr[:, col]) for col in (1, 2, 3)])
    
    if w_grav is not None and len(w_grav) > 0:
        w_grav_grid = np.column_stack([np.interp(t_grid, w_grav[:, 0], w_grav[:, col]) for col in (1, 2, 3)])
    else:
        w_grav_grid = np.zeros((num_samples, 3), dtype=np.float64)
        w_grav_grid[:, 1] = -4.0
        
    if p_acc is not None and len(p_acc) > 0:
        p_t = p_acc[:, 0]
        p_t_norm = t_start + (p_t - p_t[0]) * ((t_end - t_start) / max(p_t[-1] - p_t[0], 1e-3))
        p_acc_grid = np.column_stack([np.interp(t_grid, p_t_norm, p_acc[:, col]) for col in (1, 2, 3)])
    else:
        p_acc_grid = np.zeros((num_samples, 3), dtype=np.float64)
        
    channels = np.hstack([w_acc_grid, w_gyr_grid, w_grav_grid, p_acc_grid]).astype(np.float32)
    return t_grid, channels

def build_session_labels(sdir, t_grid, channels):
    gt_path = os.path.join(sdir, "ground_truth_aligned.csv")
    if not os.path.exists(gt_path):
        return None, None
        
    df_gt = pd.read_csv(gt_path)
    
    num_samples = len(t_grid)
    labels = np.zeros(num_samples, dtype=np.int32)
    
    w_gyr_mag = np.linalg.norm(channels[:, 3:6], axis=1)
    w_grav_y = channels[:, 7]
    
    fu_times = []
    shot_times = []
    
    for _, row in df_gt.iterrows():
        stype = str(row.get("shot_type", "")).lower()
        t_sec = float(row.get("sensor_narr_time_seconds", 0.0))
        if "facing up" in stype:
            fu_times.append(t_sec)
        elif not any(term in stype for term in ["no shot", "leave", "evade"]):
            shot_times.append(t_sec)
            
    # 2. Explicit Positives (Class 1)
    for tf in fu_times:
        idx_mask = (t_grid >= tf - 2.5) & (t_grid <= tf + 1.0)
        valid_kin = (w_gyr_mag < 1.0) & (w_grav_y <= -3.0)
        labels[idx_mask & valid_kin] = 1
        
    # 3. Implicit Pre-Shot Positives (Class 1 Fallback)
    for ts in shot_times:
        has_prior_fu = any((ts - 6.0 <= tf <= ts) for tf in fu_times)
        if not has_prior_fu:
            idx_mask = (t_grid >= ts - 3.5) & (t_grid <= ts - 1.0)
            valid_kin = (w_gyr_mag < 1.0) & (w_grav_y <= -3.0)
            labels[idx_mask & valid_kin] = 1

    # 4. Active Motion Swings & Shots (Class 0 Negatives)
    for ts in shot_times:
        idx_swing = (t_grid >= ts - 0.8) & (t_grid <= ts + 1.2)
        labels[idx_swing] = 0

    return labels, (fu_times, shot_times)

def main():
    print("==========================================================", flush=True)
    print("     BUILDING 423 Hz FACING UP (STANCE) DATASET", flush=True)
    print("==========================================================", flush=True)
    
    all_sdirs = sorted([d for d in glob.glob(os.path.join(BASE_DIR, "session*")) if os.path.isdir(d)])
    print(f"Discovered {len(all_sdirs)} physical session directories.", flush=True)
    print(f"Designated Unseen Holdout Sessions (2): {HOLDOUT_SESSIONS}", flush=True)
    
    sessions_data = {}
    
    total_samples = 0
    total_c1_samples = 0
    
    for sdir in all_sdirs:
        sid = os.path.basename(sdir)
        is_holdout = sid in HOLDOUT_SESSIONS
        
        imu_res = load_session_imu(sdir)
        if imu_res is None:
            print(f"Skipping {sid}: insufficient IMU stream data.", flush=True)
            continue
            
        t_grid, channels = imu_res
        labels, narr_info = build_session_labels(sdir, t_grid, channels)
        if labels is None:
            print(f"Skipping {sid}: missing ground_truth_aligned.csv.", flush=True)
            continue
            
        fu_times, shot_times = narr_info
        
        n_c1 = np.sum(labels == 1)
        total_samples += len(labels)
        total_c1_samples += n_c1
        
        tag = "[HOLDOUT]" if is_holdout else "[TRAIN]  "
        print(f"{tag} {sid}: {len(labels)} samples ({len(labels)/423:.1f}s) | Stance C1: {n_c1} samples", flush=True)
        
        sessions_data[sid] = {
            "t_grid": t_grid,
            "channels": channels,
            "labels": labels,
            "fu_times": fu_times,
            "shot_times": shot_times,
            "is_holdout": is_holdout
        }

    dataset = {
        "sessions_data": sessions_data,
        "holdout_session_ids": HOLDOUT_SESSIONS
    }

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "wb") as f:
        pickle.dump(dataset, f, protocol=pickle.HIGHEST_PROTOCOL)
        
    size_mb = os.path.getsize(OUTPUT_PATH) / (1024 * 1024)
    print("\n----------------------------------------------------------", flush=True)
    print(f"Dataset successfully built and saved to: {OUTPUT_PATH} ({size_mb:.2f} MB)", flush=True)
    print(f"Total Physical Sessions: {len(sessions_data)} (46 Train, 2 Holdout)", flush=True)
    print(f"Total Samples: {total_samples} (~{total_samples/423/60:.1f} mins) | Total Stance Samples: {total_c1_samples}", flush=True)
    print("----------------------------------------------------------\n", flush=True)

if __name__ == "__main__":
    main()
