#!/usr/bin/env python3
"""
Stance Gate Threshold Simulator
================================
Replays raw sensor data from a live session under multiple threshold
configurations and produces objective recall / false-positive metrics.

For each configuration:
  1. Scans the entire session at 50Hz (every gyro sample)
  2. Evaluates the 5-condition gate using rolling 1s/500ms windows
  3. Tracks continuous gate-open durations to find lock windows (≥ lock_duration_s)
  4. Maps lock windows to narrated shot times → recall
  5. Maps lock windows to non-shot periods → false arms
  6. Outputs a comparison table
"""

import sys
import os
import json
import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import List, Tuple, Optional

@dataclass
class ThresholdConfig:
    name: str
    gyro_std_max: float
    accel_std_max: float
    ori_disp_max_deg: float
    grav_y_max: float  # must be <= this value
    step_window_s: float  # look back this far for steps
    lock_duration_s: float  # how long all conditions must hold
    min_motion_conditions: int = 4  # how many of the 4 motion conditions must be met
    description: str = ""

# ─── Threshold configurations to test ────────────────────────────────────────

CONFIGS = [
    ThresholdConfig(
        name="Current (Tight)",
        gyro_std_max=0.9,
        accel_std_max=1.5,
        ori_disp_max_deg=1.5,
        grav_y_max=-3.5,
        step_window_s=2.0,
        lock_duration_s=0.8,
        min_motion_conditions=4,
        description="Current production thresholds (post May-29 tightening)"
    ),
    ThresholdConfig(
        name="A: Loosen All",
        gyro_std_max=1.5,
        accel_std_max=3.0,
        ori_disp_max_deg=3.0,
        grav_y_max=-2.0,
        step_window_s=2.0,
        lock_duration_s=0.8,
        min_motion_conditions=4,
        description="Revert to pre-May-29 values + loosen Gravity Y to -2.0"
    ),
    ThresholdConfig(
        name="A2: Loosen, Keep GravY",
        gyro_std_max=1.5,
        accel_std_max=3.0,
        ori_disp_max_deg=3.0,
        grav_y_max=-3.5,
        step_window_s=2.0,
        lock_duration_s=0.8,
        min_motion_conditions=4,
        description="Loosen gyro/accel/ori but keep strict Gravity Y"
    ),
    ThresholdConfig(
        name="B: Drop Grav Y",
        gyro_std_max=0.9,
        accel_std_max=1.5,
        ori_disp_max_deg=1.5,
        grav_y_max=999.0,   # effectively disabled
        step_window_s=2.0,
        lock_duration_s=0.8,
        min_motion_conditions=4,
        description="Current tight + completely remove Gravity Y condition"
    ),
    ThresholdConfig(
        name="C: Moderate",
        gyro_std_max=1.2,
        accel_std_max=2.0,
        ori_disp_max_deg=2.0,
        grav_y_max=-2.5,
        step_window_s=2.0,
        lock_duration_s=0.8,
        min_motion_conditions=4,
        description="Moderate loosening — halfway between current and Option A"
    ),
    ThresholdConfig(
        name="D: Steps Only",
        gyro_std_max=999.0,
        accel_std_max=999.0,
        ori_disp_max_deg=999.0,
        grav_y_max=999.0,
        step_window_s=2.0,
        lock_duration_s=0.8,
        min_motion_conditions=4,
        description="Only require no steps (baseline upper bound for recall)"
    ),
    ThresholdConfig(
        name="E: Loosen + Short Lock",
        gyro_std_max=1.5,
        accel_std_max=3.0,
        ori_disp_max_deg=3.0,
        grav_y_max=-2.0,
        step_window_s=2.0,
        lock_duration_s=0.5,
        min_motion_conditions=4,
        description="Option A thresholds + shorter lock duration (0.5s)"
    ),
    ThresholdConfig(
        name="H2: Loosen All (2 of 4)",
        gyro_std_max=1.5,
        accel_std_max=3.0,
        ori_disp_max_deg=3.0,
        grav_y_max=-2.0,
        step_window_s=2.0,
        lock_duration_s=0.8,
        min_motion_conditions=2,
        description="Loosen all thresholds + require steps + any 2 of 4 motion metrics"
    ),
    ThresholdConfig(
        name="H3: Loosen All (3 of 4)",
        gyro_std_max=1.5,
        accel_std_max=3.0,
        ori_disp_max_deg=3.0,
        grav_y_max=-2.0,
        step_window_s=2.0,
        lock_duration_s=0.8,
        min_motion_conditions=3,
        description="Loosen all thresholds + require steps + any 3 of 4 motion metrics"
    ),
    ThresholdConfig(
        name="M2: Moderate (2 of 4)",
        gyro_std_max=1.2,
        accel_std_max=2.0,
        ori_disp_max_deg=2.0,
        grav_y_max=-2.5,
        step_window_s=2.0,
        lock_duration_s=0.8,
        min_motion_conditions=2,
        description="Moderate thresholds + require steps + any 2 of 4 motion metrics"
    ),
    ThresholdConfig(
        name="M3: Moderate (3 of 4)",
        gyro_std_max=1.2,
        accel_std_max=2.0,
        ori_disp_max_deg=2.0,
        grav_y_max=-2.5,
        step_window_s=2.0,
        lock_duration_s=0.8,
        min_motion_conditions=3,
        description="Moderate thresholds + require steps + any 3 of 4 motion metrics"
    ),
]


def load_sensor_data(session_dir):
    """Load all sensor CSVs and precompute magnitudes."""
    gyro = pd.read_csv(os.path.join(session_dir, "WatchGyroscope.csv"))
    accel = pd.read_csv(os.path.join(session_dir, "WatchAccelerometer.csv"))
    gravity = pd.read_csv(os.path.join(session_dir, "WatchGravity.csv"))
    
    game_orient_path = os.path.join(session_dir, "WatchGameOrientation.csv")
    orient_path = os.path.join(session_dir, "WatchOrientation.csv")
    orient = pd.read_csv(game_orient_path) if os.path.exists(game_orient_path) else pd.read_csv(orient_path)
    
    steps_path = os.path.join(session_dir, "WatchSteps.csv")
    steps = pd.read_csv(steps_path) if os.path.exists(steps_path) else None
    
    gyro['mag'] = np.sqrt(gyro['x']**2 + gyro['y']**2 + gyro['z']**2)
    accel['mag'] = np.sqrt(accel['x']**2 + accel['y']**2 + accel['z']**2)
    
    return gyro, accel, gravity, orient, steps


def precompute_rolling_stats(df_gyro, df_accel, df_gravity, df_orient, df_steps, sample_interval=0.5):
    """
    Precompute rolling statistics at regular time intervals across the session.
    Returns a DataFrame with one row per sample point containing all 5 gate values.
    """
    max_t = df_gyro['seconds_elapsed'].max()
    sample_times = np.arange(1.0, max_t, sample_interval)
    
    gyro_t = df_gyro['seconds_elapsed'].values
    gyro_mag = df_gyro['mag'].values
    accel_t = df_accel['seconds_elapsed'].values
    accel_mag = df_accel['mag'].values
    grav_t = df_gravity['seconds_elapsed'].values
    grav_y = df_gravity['y'].values
    ori_t = df_orient['seconds_elapsed'].values
    ori_qx = df_orient['qx'].values
    ori_qy = df_orient['qy'].values
    ori_qz = df_orient['qz'].values
    ori_qw = df_orient['qw'].values
    
    step_times = df_steps['seconds_elapsed'].values if (df_steps is not None and len(df_steps) > 0) else np.array([])
    
    results = []
    
    for t in sample_times:
        # 1. Gyro std (1s window)
        mask_g = (gyro_t >= t - 1.0) & (gyro_t <= t)
        if mask_g.sum() >= 2:
            g_std = np.std(gyro_mag[mask_g], ddof=0)
        else:
            g_std = 0.0
        
        # 2. Accel std (1s window)
        mask_a = (accel_t >= t - 1.0) & (accel_t <= t)
        if mask_a.sum() >= 2:
            a_std = np.std(accel_mag[mask_a], ddof=0)
        else:
            a_std = 0.0
        
        # 3. Ori disp (500ms window)
        mask_o = (ori_t >= t - 0.5) & (ori_t <= t)
        o_count = mask_o.sum()
        if o_count >= 2:
            idx = np.where(mask_o)[0]
            qx_w = ori_qx[idx]
            qy_w = ori_qy[idx]
            qz_w = ori_qz[idx]
            qw_w = ori_qw[idx]
            dots = qx_w[:-1]*qx_w[1:] + qy_w[:-1]*qy_w[1:] + qz_w[:-1]*qz_w[1:] + qw_w[:-1]*qw_w[1:]
            dots = np.clip(np.abs(dots), -1.0, 1.0)
            angles = np.degrees(2.0 * np.arccos(dots))
            o_disp = np.mean(angles)
        else:
            o_disp = 999.0
        
        # 4. Gravity Y (1s mean)
        mask_gr = (grav_t >= t - 1.0) & (grav_t <= t)
        if mask_gr.sum() > 0:
            g_y = np.mean(grav_y[mask_gr])
        else:
            g_y = -9.8
        
        # 5. Steps in window (variable, checked per config later)
        # Store the step times for this sample for later per-config evaluation
        
        results.append({
            'time': t,
            'gyro_std': g_std,
            'accel_std': a_std,
            'ori_disp': o_disp,
            'grav_y': g_y,
        })
    
    df = pd.DataFrame(results)
    
    return df, step_times


def simulate_config(config: ThresholdConfig, df_stats: pd.DataFrame, step_times: np.ndarray,
                    shot_times: List[float], session_duration: float) -> dict:
    """
    Simulate a threshold configuration against precomputed rolling stats.
    
    Returns metrics dict with recall, false-arm counts, etc.
    """
    times = df_stats['time'].values
    sample_interval = times[1] - times[0] if len(times) > 1 else 0.5
    
    # Evaluate individual motion conditions
    c_gyro = df_stats['gyro_std'].values < config.gyro_std_max
    c_accel = df_stats['accel_std'].values < config.accel_std_max
    c_ori = df_stats['ori_disp'].values < config.ori_disp_max_deg
    c_grav = (df_stats['grav_y'].values <= config.grav_y_max) if config.grav_y_max < 900 else np.ones(len(df_stats), dtype=bool)
    
    # Calculate how many conditions are met at each sample
    conditions_met = c_gyro.astype(int) + c_accel.astype(int) + c_ori.astype(int) + c_grav.astype(int)
    
    # Check if we meet the minimum number of required conditions
    gate_open = (conditions_met >= config.min_motion_conditions)
    
    # Apply step condition (steps must be 0 in the window - mandatory)
    for i, t in enumerate(times):
        if len(step_times) > 0:
            steps_in_window = np.sum((step_times >= t - config.step_window_s) & (step_times <= t))
            if steps_in_window > 0:
                gate_open[i] = False
    
    # Find continuous lock windows (gate open for >= lock_duration_s)
    lock_windows = []  # list of (start_time, end_time)
    current_start = None
    
    for i, (t, is_open) in enumerate(zip(times, gate_open)):
        if is_open:
            if current_start is None:
                current_start = t
        else:
            if current_start is not None:
                duration = t - current_start
                if duration >= config.lock_duration_s:
                    lock_windows.append((current_start, t))
                current_start = None
    
    # Handle end of session
    if current_start is not None:
        duration = times[-1] - current_start
        if duration >= config.lock_duration_s:
            lock_windows.append((current_start, times[-1]))
    
    # Calculate total lock time
    total_lock_time = sum(end - start for start, end in lock_windows)
    
    # For each narrated shot, check if a lock window existed in the pre-shot period
    # The watch needs to lock BEFORE the backswing, which is ~0.5-1.5s before impact
    # So we check for a lock window ending in [t_impact - 3.0, t_impact - 0.3]
    PRE_SHOT_WINDOW_START = 4.0  # seconds before impact to start looking
    PRE_SHOT_WINDOW_END = 0.3    # seconds before impact (backswing already started)
    
    shots_with_lock = 0
    shots_without_lock = 0
    
    for st in shot_times:
        window_start = st - PRE_SHOT_WINDOW_START
        window_end = st - PRE_SHOT_WINDOW_END
        
        # Check if any lock window overlaps with this pre-shot period
        found_lock = False
        for (ls, le) in lock_windows:
            # Lock window [ls, le] overlaps with [window_start, window_end]
            if ls < window_end and le > window_start:
                found_lock = True
                break
        
        if found_lock:
            shots_with_lock += 1
        else:
            shots_without_lock += 1
    
    # False arms: lock windows that do NOT overlap with any shot's pre-shot period
    # (i.e., the gate locked during a break with no shot nearby)
    SHOT_PROXIMITY = 5.0  # seconds — if a lock window is within 5s of any shot, it's legit
    false_arms = 0
    for (ls, le) in lock_windows:
        near_shot = False
        for st in shot_times:
            if abs(ls - st) < SHOT_PROXIMITY or abs(le - st) < SHOT_PROXIMITY:
                near_shot = True
                break
        if not near_shot:
            false_arms += 1
    
    # Gate open percentage across session
    gate_open_pct = 100.0 * gate_open.sum() / len(gate_open)
    
    # Per-condition pass rates
    gyro_pass = 100.0 * (df_stats['gyro_std'].values < config.gyro_std_max).sum() / len(df_stats)
    accel_pass = 100.0 * (df_stats['accel_std'].values < config.accel_std_max).sum() / len(df_stats)
    ori_pass = 100.0 * (df_stats['ori_disp'].values < config.ori_disp_max_deg).sum() / len(df_stats)
    grav_pass = 100.0 * ((df_stats['grav_y'].values <= config.grav_y_max) if config.grav_y_max < 900 
                         else np.ones(len(df_stats), dtype=bool)).sum() / len(df_stats)
    
    return {
        'config_name': config.name,
        'description': config.description,
        'total_shots': len(shot_times),
        'shots_with_lock': shots_with_lock,
        'shots_without_lock': shots_without_lock,
        'recall_pct': 100.0 * shots_with_lock / len(shot_times) if shot_times else 0,
        'lock_windows': len(lock_windows),
        'false_arms': false_arms,
        'total_lock_time_s': total_lock_time,
        'lock_pct': 100.0 * total_lock_time / session_duration,
        'gate_open_pct': gate_open_pct,
        'gyro_pass_pct': gyro_pass,
        'accel_pass_pct': accel_pass,
        'ori_pass_pct': ori_pass,
        'grav_pass_pct': grav_pass,
    }


def get_offset(session_dir):
    """Calculate audio-to-sensor clock offset."""
    import datetime
    narration_files = [f for f in os.listdir(session_dir) if f.startswith("narration_") and f.endswith(".m4a")]
    if not narration_files:
        return 0.0
    
    fname = narration_files[0]
    parts = fname.replace("narration_", "").replace(".m4a", "")
    try:
        dt = datetime.datetime.strptime(parts, "%Y%m%d_%H%M%S")
        audio_epoch = dt.timestamp()
        
        timeline_path = os.path.join(session_dir, "latest_timeline.txt")
        with open(timeline_path) as f:
            for line in f:
                if line.startswith("SYSTEM_START:"):
                    watch_epoch = int(line.split("Ts=")[1].strip()) / 1000.0
                    return audio_epoch - watch_epoch
    except:
        pass
    return 0.0


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 simulate_thresholds.py <session_dir> [session_dir2 ...]")
        sys.exit(1)
    
    session_dirs = sys.argv[1:]
    
    for session_dir in session_dirs:
        session_name = os.path.basename(session_dir)
        
        print(f"\n{'='*100}")
        print(f"  STANCE GATE THRESHOLD SIMULATION — {session_name}")
        print(f"{'='*100}\n")
        
        # Load data
        df_gyro, df_accel, df_gravity, df_orient, df_steps = load_sensor_data(session_dir)
        session_duration = df_gyro['seconds_elapsed'].max()
        
        # Load narrations and compute shot times in sensor space
        offset = get_offset(session_dir)
        narr_path = os.path.join(session_dir, "narrations_raw.json")
        with open(narr_path) as f:
            narrations = json.load(f)
        
        # Filter to swing-type shots only
        shot_times = []
        for n in narrations:
            st = n.get('shot_type', '')
            if any(term in st.lower() for term in ['facing up', 'no shot', 'leave']):
                continue
            shot_times.append(n['timestamp_seconds'] + offset)
        
        print(f"Session duration: {session_duration:.0f}s ({session_duration/60:.1f} min)")
        print(f"Swing-type narrated shots: {len(shot_times)}")
        print(f"Clock offset: {offset:+.3f}s")
        
        # Precompute rolling stats at 0.5s intervals
        print(f"\nPrecomputing rolling sensor statistics...")
        df_stats, step_times = precompute_rolling_stats(df_gyro, df_accel, df_gravity, df_orient, df_steps, sample_interval=0.5)
        print(f"Computed {len(df_stats)} sample points\n")
        
        # Run each configuration
        all_results = []
        for config in CONFIGS:
            result = simulate_config(config, df_stats, step_times, shot_times, session_duration)
            all_results.append(result)
        
        # Print comparison table
        print(f"{'─'*100}")
        print(f"{'Config':<24} {'Recall':>8} {'Locks':>7} {'FalseArm':>9} {'LockTime':>9} {'LockPct':>8} {'GateOpen':>9}")
        print(f"{'─'*100}")
        
        for r in all_results:
            print(f"{r['config_name']:<24} "
                  f"{r['shots_with_lock']:>3}/{r['total_shots']:<3} "
                  f"  {r['lock_windows']:>5} "
                  f"  {r['false_arms']:>7} "
                  f"  {r['total_lock_time_s']:>6.1f}s "
                  f"  {r['lock_pct']:>5.1f}% "
                  f"  {r['gate_open_pct']:>5.1f}%")
        
        # Detailed view
        print(f"\n{'─'*100}")
        print(f"  DETAILED BREAKDOWN")
        print(f"{'─'*100}\n")
        
        for r in all_results:
            recall_bar = "█" * int(r['recall_pct'] / 2)
            fp_indicator = "⚠️" if r['false_arms'] > 5 else "✅"
            
            print(f"  {r['config_name']}")
            print(f"    {r['description']}")
            print(f"    Shot Recall:    {r['shots_with_lock']:>3} / {r['total_shots']} ({r['recall_pct']:>5.1f}%) {recall_bar}")
            print(f"    Lock Windows:   {r['lock_windows']} total, {r['false_arms']} false arms {fp_indicator}")
            print(f"    Lock Time:      {r['total_lock_time_s']:.1f}s of {session_duration:.0f}s ({r['lock_pct']:.1f}%)")
            print(f"    Per-condition pass rates: Gyro {r['gyro_pass_pct']:.0f}% | Accel {r['accel_pass_pct']:.0f}% | Ori {r['ori_pass_pct']:.0f}% | GravY {r['grav_pass_pct']:.0f}%")
            print()
        
        # Recommendation
        print(f"{'─'*100}")
        print(f"  RECOMMENDATION MATRIX")
        print(f"{'─'*100}\n")
        
        print(f"  {'Config':<24} {'Recall%':>8} {'FalseArms':>10} {'Verdict'}")
        print(f"  {'─'*60}")
        
        for r in all_results:
            if r['recall_pct'] >= 80 and r['false_arms'] <= 3:
                verdict = "⭐ OPTIMAL"
            elif r['recall_pct'] >= 60 and r['false_arms'] <= 5:
                verdict = "✅ GOOD"
            elif r['recall_pct'] >= 40 and r['false_arms'] <= 10:
                verdict = "🟡 ACCEPTABLE"
            elif r['false_arms'] > 15:
                verdict = "❌ TOO MANY FP"
            else:
                verdict = "🟠 LOW RECALL"
            
            print(f"  {r['config_name']:<24} {r['recall_pct']:>7.1f}% {r['false_arms']:>9} {verdict}")
        
        print()


if __name__ == "__main__":
    main()
