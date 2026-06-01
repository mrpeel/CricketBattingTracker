#!/usr/bin/env python3
"""
SwingDetector E2E State Machine Simulator
=========================================
Runs a high-fidelity simulation of the Wear OS SwingDetector state machine
at 10Hz across raw sensor data, including all state transitions:
  ACTIVITY_CLASSIFY -> FACING_UP_LOCKED -> MEASURING_ARC -> CONTACT_WAIT
  
Computes the exact number of True Positives (narrated swings detected)
and False Positives (spurious swing triggers) that would occur on the watch.
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
    gyro_mandatory: bool = False
    accel_mandatory: bool = False
    ori_mandatory: bool = False
    grav_mandatory: bool = False
    description: str = ""

CONFIGS = [
    ThresholdConfig(
        name="Production Kotlin",
        gyro_std_max=1.6,
        accel_std_max=3.25,
        ori_disp_max_deg=3.05,
        grav_y_max=-6.0,
        step_window_s=2.0,
        lock_duration_s=1.2,
        min_motion_conditions=4,
        description="Thresholds currently deployed in SwingDetector.kt (1.2s lock)"
    ),
    ThresholdConfig(
        name="Production (grav -5.5)",
        gyro_std_max=1.6,
        accel_std_max=3.25,
        ori_disp_max_deg=3.05,
        grav_y_max=-5.5,
        step_window_s=2.0,
        lock_duration_s=1.2,
        min_motion_conditions=4,
        description="Production with looser Gravity Y (-5.5)"
    ),
    ThresholdConfig(
        name="Production (grav -5.0)",
        gyro_std_max=1.6,
        accel_std_max=3.25,
        ori_disp_max_deg=3.05,
        grav_y_max=-5.0,
        step_window_s=2.0,
        lock_duration_s=1.2,
        min_motion_conditions=4,
        description="Production with looser Gravity Y (-5.0)"
    ),
    ThresholdConfig(
        name="Production (grav -4.5)",
        gyro_std_max=1.6,
        accel_std_max=3.25,
        ori_disp_max_deg=3.05,
        grav_y_max=-4.5,
        step_window_s=2.0,
        lock_duration_s=1.2,
        min_motion_conditions=4,
        description="Production with looser Gravity Y (-4.5)"
    ),
    ThresholdConfig(
        name="Production (grav -4.0)",
        gyro_std_max=1.6,
        accel_std_max=3.25,
        ori_disp_max_deg=3.05,
        grav_y_max=-4.0,
        step_window_s=2.0,
        lock_duration_s=1.2,
        min_motion_conditions=4,
        description="Production with looser Gravity Y (-4.0)"
    ),
    ThresholdConfig(
        name="Production (grav -3.5)",
        gyro_std_max=1.6,
        accel_std_max=3.25,
        ori_disp_max_deg=3.05,
        grav_y_max=-3.5,
        step_window_s=2.0,
        lock_duration_s=1.2,
        min_motion_conditions=4,
        description="Production with looser Gravity Y (-3.5)"
    ),
    ThresholdConfig(
        name="Production (no grav)",
        gyro_std_max=1.6,
        accel_std_max=3.25,
        ori_disp_max_deg=3.05,
        grav_y_max=999.0,
        step_window_s=2.0,
        lock_duration_s=1.2,
        min_motion_conditions=4,
        description="Production without Gravity Y check"
    ),
    ThresholdConfig(
        name="Grid Search F1-Opt",
        gyro_std_max=1.3,
        accel_std_max=2.75,
        ori_disp_max_deg=3.5,
        grav_y_max=-5.0,
        step_window_s=2.0,
        lock_duration_s=0.8,
        min_motion_conditions=4,
        description="F1-balanced optimized thresholds (0.8s lock)"
    ),
    ThresholdConfig(
        name="Grid Search F2-Opt",
        gyro_std_max=2.2,
        accel_std_max=4.25,
        ori_disp_max_deg=4.25,
        grav_y_max=-1.5,
        step_window_s=2.0,
        lock_duration_s=0.8,
        min_motion_conditions=4,
        description="F2-recall prioritized optimized thresholds (0.8s lock)"
    ),
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
        name="D2: Steps Only (1.5s)",
        gyro_std_max=999.0,
        accel_std_max=999.0,
        ori_disp_max_deg=999.0,
        grav_y_max=999.0,
        step_window_s=1.5,
        lock_duration_s=0.8,
        min_motion_conditions=4,
        description="Only require no steps in last 1.5s (baseline upper bound)"
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
    ThresholdConfig(
        name="H4: Steps+Gyro Mand(3/4)",
        gyro_std_max=1.5,
        accel_std_max=3.0,
        ori_disp_max_deg=3.0,
        grav_y_max=-2.0,
        step_window_s=2.0,
        lock_duration_s=0.8,
        min_motion_conditions=3,
        gyro_mandatory=True,
        description="Steps & Gyro < 1.5 mandatory + any 2 of remaining 3"
    ),
    ThresholdConfig(
        name="H5: Steps+Gyro Mand(2/4)",
        gyro_std_max=1.5,
        accel_std_max=3.0,
        ori_disp_max_deg=3.0,
        grav_y_max=-2.0,
        step_window_s=2.0,
        lock_duration_s=0.8,
        min_motion_conditions=2,
        gyro_mandatory=True,
        description="Steps & Gyro < 1.5 mandatory + any 1 of remaining 3"
    ),
    ThresholdConfig(
        name="H6: Steps+G+A Mand(3/4)",
        gyro_std_max=1.5,
        accel_std_max=3.0,
        ori_disp_max_deg=3.0,
        grav_y_max=-2.0,
        step_window_s=2.0,
        lock_duration_s=0.8,
        min_motion_conditions=3,
        gyro_mandatory=True,
        accel_mandatory=True,
        description="Steps, Gyro < 1.5 & Accel < 3.0 mandatory + any 1 of remaining 2"
    ),
    ThresholdConfig(
        name="H7: Steps+Gyro Mand(Tight)",
        gyro_std_max=0.9,
        accel_std_max=1.5,
        ori_disp_max_deg=1.5,
        grav_y_max=-3.5,
        step_window_s=2.0,
        lock_duration_s=0.8,
        min_motion_conditions=2,
        gyro_mandatory=True,
        description="Tight thresholds, Gyro < 0.9 & steps mandatory + any 1 of remaining 3"
    ),
    ThresholdConfig(
        name="H8: Steps+G+A Mand(Tight)",
        gyro_std_max=0.9,
        accel_std_max=1.5,
        ori_disp_max_deg=1.5,
        grav_y_max=-3.5,
        step_window_s=2.0,
        lock_duration_s=0.8,
        min_motion_conditions=3,
        gyro_mandatory=True,
        accel_mandatory=True,
        description="Tight thresholds, Gyro & Accel & steps mandatory + any 1 of remaining 2"
    ),
    ThresholdConfig(
        name="H9: Steps+Gyro Mand(Mod 2/4)",
        gyro_std_max=1.2,
        accel_std_max=2.0,
        ori_disp_max_deg=2.0,
        grav_y_max=-3.5,
        step_window_s=2.0,
        lock_duration_s=1.2,
        min_motion_conditions=2,
        gyro_mandatory=True,
        description="Moderate thresholds, Gyro < 1.2 & steps mandatory + any 1 of remaining 3 (1.2s lock)"
    ),
    ThresholdConfig(
        name="H10: Steps+Gyro Mand(grav -2.5)",
        gyro_std_max=1.2,
        accel_std_max=2.0,
        ori_disp_max_deg=2.0,
        grav_y_max=-2.5,
        step_window_s=2.0,
        lock_duration_s=1.2,
        min_motion_conditions=2,
        gyro_mandatory=True,
        description="Moderate thresholds, Gyro < 1.2 & steps mandatory + any 1 of remaining 3 (grav -2.5, 1.2s lock)"
    ),
    ThresholdConfig(
        name="New Optimized Kotlin",
        gyro_std_max=1.2,
        accel_std_max=2.0,
        ori_disp_max_deg=2.0,
        grav_y_max=-2.5,
        step_window_s=1.0,
        lock_duration_s=0.8,
        min_motion_conditions=4,
        description="Updated logic: C: Mod thresholds, 0.8s lock, 1.0s step window, 4-of-4 check"
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

def precompute_rolling_stats(df_gyro, df_accel, df_gravity, df_orient, df_steps, sample_interval=0.1):
    """
    Precompute rolling statistics at regular time intervals across the session.
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
        g_std = np.std(gyro_mag[mask_g], ddof=0) if mask_g.sum() >= 2 else 0.0
        
        # 2. Accel std (1s window)
        mask_a = (accel_t >= t - 1.0) & (accel_t <= t)
        a_std = np.std(accel_mag[mask_a], ddof=0) if mask_a.sum() >= 2 else 0.0
        
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
        g_y = np.mean(grav_y[mask_gr]) if mask_gr.sum() > 0 else -9.8
        
        results.append({
            'time': t,
            'gyro_std': g_std,
            'accel_std': a_std,
            'ori_disp': o_disp,
            'grav_y': g_y,
        })
    
    df = pd.DataFrame(results)
    return df, step_times

def simulate_state_machine(config: ThresholdConfig, df_stats: pd.DataFrame, step_times: np.ndarray,
                           gyro_times: np.ndarray, gyro_mags: np.ndarray,
                           post_shot_guard_s: float = 2.5) -> List[float]:
    """
    Simulates the SwingDetector state machine at 10Hz.
    Returns the list of timestamps at which a shot was successfully detected.
    """
    times = df_stats['time'].values
    gyro_std = df_stats['gyro_std'].values
    accel_std = df_stats['accel_std'].values
    ori_disp = df_stats['ori_disp'].values
    grav_y = df_stats['grav_y'].values
    
    # States:
    # 0 = ACTIVITY_CLASSIFY
    # 1 = FACING_UP_LOCKED
    # 2 = MEASURING_ARC & CONTACT_WAIT
    state = 0
    
    gate_active = False
    gate_start_time = 0.0
    break_start_time = 0.0
    locked_time = 0.0
    swing_start_time = 0.0
    last_shot_end_time = -100.0
    
    detected_shot_times = []
    
    for idx, t in enumerate(times):
        # 1. Apply post-shot guard window
        if t <= last_shot_end_time + post_shot_guard_s:
            continue
            
        # 2. ACTIVITY_CLASSIFY state
        if state == 0:
            # Step check (mandatory kill-switch)
            if len(step_times) > 0:
                steps_in_window = np.sum((step_times >= t - config.step_window_s) & (step_times <= t))
                has_steps = (steps_in_window > 0)
            else:
                has_steps = False
                
            if has_steps:
                gate_active = False
                break_start_time = 0.0
            else:
                c_gyro = gyro_std[idx] < config.gyro_std_max
                c_accel = accel_std[idx] < config.accel_std_max
                c_ori = ori_disp[idx] < config.ori_disp_max_deg
                c_grav = grav_y[idx] <= config.grav_y_max if config.grav_y_max < 900 else True
                
                # Check mandatory conditions
                mandatory_ok = True
                if config.gyro_mandatory and not c_gyro: mandatory_ok = False
                if config.accel_mandatory and not c_accel: mandatory_ok = False
                if config.ori_mandatory and not c_ori: mandatory_ok = False
                if config.grav_mandatory and not c_grav: mandatory_ok = False
                
                if not mandatory_ok:
                    all_met = False
                else:
                    conditions_met = int(c_gyro) + int(c_accel) + int(c_ori) + int(c_grav)
                    all_met = (conditions_met >= config.min_motion_conditions)
                
                if all_met:
                    if not gate_active:
                        gate_active = True
                        gate_start_time = t
                        break_start_time = 0.0
                    else:
                        if break_start_time > 0.0:
                            # Recovering from a temporary break
                            break_dur = t - break_start_time
                            gate_start_time += break_dur
                            break_start_time = 0.0
                        
                        held_for = t - gate_start_time
                        if held_for >= config.lock_duration_s:
                            state = 1
                            locked_time = t
                else:
                    if gate_active:
                        if break_start_time == 0.0:
                            break_start_time = t
                        elif t - break_start_time > 1.2:  # 1.2s break tolerance
                            gate_active = False
                            break_start_time = 0.0
                            
        # 3. FACING_UP_LOCKED state
        elif state == 1:
            # Timeout (12s)
            if t - locked_time > 12.0:
                state = 0
                gate_active = False
                break_start_time = 0.0
                continue
                
            # Step break check during lock
            if len(step_times) > 0:
                steps_in_window = np.sum((step_times >= t - config.step_window_s) & (step_times <= t))
                if steps_in_window > 0:
                    state = 0
                    gate_active = False
                    break_start_time = 0.0
                    continue
            
            # Check gyro magnitude above 5.0 rad/s
            mask_gyro = (gyro_times >= t - 0.1) & (gyro_times <= t)
            max_gyro = np.max(gyro_mags[mask_gyro]) if mask_gyro.sum() > 0 else 0.0
            
            if max_gyro >= 5.0:
                state = 2
                swing_start_time = t
                
        # 4. MEASURING_ARC & CONTACT_WAIT (1.75s combined)
        elif state == 2:
            if t - swing_start_time >= 1.75:
                detected_shot_times.append(swing_start_time)
                last_shot_end_time = t
                state = 0
                gate_active = False
                break_start_time = 0.0
                
    return detected_shot_times

def evaluate_detections(detected_times: List[float], shot_times: List[float], max_window: float = 4.0) -> Tuple[int, int, int]:
    """
    Evaluates detected times against narrated shot times.
    Returns: (TP, FP, FN)
    """
    matched_shots = set()
    tp = 0
    fp = 0
    
    for dt in detected_times:
        # Find closest narrated shot that hasn't been matched yet
        best_match = None
        min_diff = max_window
        
        for st in shot_times:
            if st in matched_shots:
                continue
            diff = abs(dt - st)
            if diff < min_diff:
                min_diff = diff
                best_match = st
                
        if best_match is not None:
            tp += 1
            matched_shots.add(best_match)
        else:
            fp += 1
            
    fn = len(shot_times) - len(matched_shots)
    return tp, fp, fn

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
        print("Usage: python3 analyze_spurious_triggers.py <session_dir> [session_dir2 ...]")
        sys.exit(1)
        
    session_dirs = sys.argv[1:]
    
    for session_dir in session_dirs:
        session_name = os.path.basename(session_dir)
        print(f"\n==========================================================================")
        print(f"  SWINGDETECTOR E2E SIMULATION REPORT — {session_name}")
        print(f"==========================================================================\n")
        
        # Load raw sensors
        gyro, accel, gravity, orient, steps = load_sensor_data(session_dir)
        session_duration_m = gyro['seconds_elapsed'].max() / 60.0
        
        # Load narrated shots
        offset = 0.0
        narr_path = os.path.join(session_dir, "narrations_raw.json")
        with open(narr_path) as f:
            narrations = json.load(f)
            
        shot_times = []
        for n in narrations:
            st = n.get('shot_type', '')
            if any(term in st.lower() for term in ['facing up', 'no shot', 'leave']):
                continue
            shot_times.append(n['timestamp_seconds'] + offset)
            
        print(f"Session Duration: {session_duration_m:.2f} minutes")
        print(f"Total Narrated Swings: {len(shot_times)}")
        
        # Precompute stats at 10Hz
        print("Precomputing 10Hz rolling metrics...")
        df_stats, step_times = precompute_rolling_stats(gyro, accel, gravity, orient, steps, sample_interval=0.1)
        
        gyro_times = gyro['seconds_elapsed'].values
        gyro_mags = gyro['mag'].values
        
        print("\n| Configuration | Detected | TP | FP | FN | Recall % | Precision % | FPs / Min | Description |")
        print("| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |")
        
        for config in CONFIGS:
            detected_times = simulate_state_machine(config, df_stats, step_times, gyro_times, gyro_mags)
            tp, fp, fn = evaluate_detections(detected_times, shot_times)
            
            recall = (100.0 * tp / len(shot_times)) if len(shot_times) > 0 else 0.0
            precision = (100.0 * tp / len(detected_times)) if len(detected_times) > 0 else 0.0
            fp_per_min = fp / session_duration_m
            
            print(f"| {config.name:<22} | {len(detected_times):^8} | {tp:^2} | {fp:^2} | {fn:^2} | {recall:>7.1f}% | {precision:>10.1f}% | {fp_per_min:>9.2f} | {config.description} |")
            
        print()

if __name__ == "__main__":
    main()
