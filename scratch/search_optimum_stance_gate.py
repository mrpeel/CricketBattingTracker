#!/usr/bin/env python3
import os
import json
import numpy as np
import pandas as pd
import datetime

# Grid search space options
GRID = {
    'gyro_std_max': [1.2, 1.5, 1.6],
    'accel_std_max': [2.0, 3.0, 3.25],
    'ori_disp_max_deg': [2.5, 3.0, 3.5, 4.0],
    'grav_y_min': [-1.5, -2.5, -3.5, -6.0],
    'facing_up_min_duration_ns': [600000000, 800000000],  # 0.6s, 0.8s
    'min_flexible_conditions': [3], # Strict 4-of-4 gate
    'post_shot_guard_ns': [500000000, 1000000000, 1500000000, 2500000000] # 0.5s, 1.0s, 1.5s, 2.5s
}

sessions = [
    {"name": "session-2026-05-30_15-04-41", "path": "session-2026-05-30_15-04-41"},
    {"name": "session-2026-05-31_10-06-52", "path": "session-2026-05-31_10-06-52"},
    {"name": "session-2026-05-31_14-12-10", "path": "session-2026-05-31_14-12-10"},
    {"name": "session-2026-06-01_12-23-38", "path": "session-2026-06-01_12-23-38"},
    {"name": "session-2026-06-05_12-29-59", "path": "session-2026-06-05_12-29-59"},
    {"name": "session-2026-06-07_14-34-24", "path": "session-2026-06-07_14-34-24"},
    {"name": "session-2026-06-08_12-22-26", "path": "sessions/session-2026-06-08_12-22-26"}
]

base_dir = "/Users/neilkloot/Code/Batting Sensor Stats/live_watch_sessions"

def load_sensor_and_gt(session_path):
    session_dir = os.path.join(base_dir, session_path)
    
    # Load raw CSVs
    gyro = pd.read_csv(os.path.join(session_dir, "WatchGyroscope.csv"))
    accel = pd.read_csv(os.path.join(session_dir, "WatchAccelerometer.csv"))
    gravity = pd.read_csv(os.path.join(session_dir, "WatchGravity.csv"))
    
    game_orient_path = os.path.join(session_dir, "WatchGameOrientation.csv")
    orient_path = os.path.join(session_dir, "WatchOrientation.csv")
    orient = pd.read_csv(game_orient_path) if os.path.exists(game_orient_path) else pd.read_csv(orient_path)
    
    steps_path = os.path.join(session_dir, "WatchSteps.csv")
    steps = pd.read_csv(steps_path) if os.path.exists(steps_path) else None
    
    # Load ground truth aligned shots
    gt = pd.read_csv(os.path.join(session_dir, "ground_truth_aligned.csv"))
    # Filter out non-swings
    gt = gt[~gt['shot_type'].str.upper().isin(["FACING UP", "NO SHOT", "LEAVE", "EVADE", "EVASION", "NON-SWING"])]
    gt_times = gt['impact_time_seconds'].values
    
    gyro['mag'] = np.sqrt(gyro['x']**2 + gyro['y']**2 + gyro['z']**2)
    accel['mag'] = np.sqrt(accel['x']**2 + accel['y']**2 + accel['z']**2)
    
    return gyro, accel, gravity, orient, steps, gt_times

def precompute_stats_for_session(gyro, accel, gravity, orient, steps):
    gyro_t = gyro['time'].values
    gyro_sec = gyro['seconds_elapsed'].values
    gyro_mag = gyro['mag'].values
    
    accel_t = accel['time'].values
    accel_mag = accel['mag'].values
    
    grav_t = gravity['time'].values
    grav_y = gravity['y'].values
    
    orient_t = orient['time'].values
    orient_qx = orient['qx'].values
    orient_qy = orient['qy'].values
    orient_qz = orient['qz'].values
    orient_qw = orient['qw'].values
    
    step_t = steps['time'].values if steps is not None else np.array([])
    
    n_samples = len(gyro_t)
    precomputed = {
        'gyro_std': np.zeros(n_samples),
        'accel_std': np.zeros(n_samples),
        'ori_disp': np.zeros(n_samples),
        'mean_grav_y': np.zeros(n_samples),
        'step_age': np.zeros(n_samples)
    }
    
    for i in range(n_samples):
        t = gyro_t[i]
        
        # Gyro std (1.0s window)
        g_start = t - 1000000000
        idx_start = np.searchsorted(gyro_t, g_start)
        mags_g = gyro_mag[idx_start:i+1]
        precomputed['gyro_std'][i] = np.std(mags_g) if len(mags_g) >= 2 else 0.0
        
        # Accel std (1.0s window)
        a_start_idx = np.searchsorted(accel_t, g_start)
        a_end_idx = np.searchsorted(accel_t, t, side='right')
        mags_a = accel_mag[a_start_idx:a_end_idx]
        precomputed['accel_std'][i] = np.std(mags_a) if len(mags_a) >= 2 else 0.0
        
        # Mean gravity Y (1.0s window)
        gr_start_idx = np.searchsorted(grav_t, g_start)
        gr_end_idx = np.searchsorted(grav_t, t, side='right')
        y_gr = grav_y[gr_start_idx:gr_end_idx]
        precomputed['mean_grav_y'][i] = np.mean(y_gr) if len(y_gr) >= 5 else 0.0
        
        # Ori disp (500ms window)
        o_start = t - 500000000
        o_start_idx = np.searchsorted(orient_t, o_start)
        o_end_idx = np.searchsorted(orient_t, t, side='right')
        
        n_ori = o_end_idx - o_start_idx
        if n_ori >= 2:
            qx = orient_qx[o_start_idx:o_end_idx]
            qy = orient_qy[o_start_idx:o_end_idx]
            qz = orient_qz[o_start_idx:o_end_idx]
            qw = orient_qw[o_start_idx:o_end_idx]
            dots = qx[:-1]*qx[1:] + qy[:-1]*qy[1:] + qz[:-1]*qz[1:] + qw[:-1]*qw[1:]
            dots = np.clip(np.abs(dots), -1.0, 1.0)
            angles = np.degrees(2.0 * np.arccos(dots))
            precomputed['ori_disp'][i] = np.mean(angles) if len(angles) > 0 else 999.0
        else:
            precomputed['ori_disp'][i] = 999.0
            
        # Step age
        if len(step_t) > 0:
            step_idx = np.searchsorted(step_t, t, side='right')
            if step_idx > 0:
                precomputed['step_age'][i] = t - step_t[step_idx - 1]
            else:
                precomputed['step_age'][i] = 999999999999
        else:
            precomputed['step_age'][i] = 999999999999
            
    return precomputed

def run_simulation(precomputed, gyro_t, gyro_sec, gyro_mag, config):
    STATE_ACTIVITY_CLASSIFY = 0
    STATE_FACING_UP_LOCKED = 1
    STATE_MEASURING_ARC = 2
    STATE_CONTACT_WAIT = 3
    
    state = STATE_ACTIVITY_CLASSIFY
    facing_up_gate_start = 0
    facing_up_gate_active = False
    facing_up_break_start = 0
    facing_up_locked_at = 0
    last_shot_end_time = 0
    
    detected_shots = []
    
    n_samples = len(gyro_t)
    gyro_std_arr = precomputed['gyro_std']
    accel_std_arr = precomputed['accel_std']
    ori_disp_arr = precomputed['ori_disp']
    mean_grav_y_arr = precomputed['mean_grav_y']
    step_age_arr = precomputed['step_age']
    
    gyro_std_max = config['gyro_std_max']
    accel_std_max = config['accel_std_max']
    ori_disp_max_deg = config['ori_disp_max_deg']
    grav_y_min = config['grav_y_min']
    step_recency_ns = 1000000000 # 1.0s
    facing_up_min_duration_ns = config['facing_up_min_duration_ns']
    facing_up_break_tolerance_ns = 1500000000 # 1.5s
    backswing_timeout_ns = 10000000000 # 10.0s
    backswing_trigger_rad_s = 5.0
    post_shot_guard_ns = config['post_shot_guard_ns']
    min_flexible_conditions = config['min_flexible_conditions']
    
    for i in range(n_samples):
        t = gyro_t[i]
        sec = gyro_sec[i]
        g_mag = gyro_mag[i]
        
        if state == STATE_ACTIVITY_CLASSIFY:
            if t <= last_shot_end_time + post_shot_guard_ns:
                continue
            
            gyro_ok = gyro_std_arr[i] < gyro_std_max
            steps_ok = step_age_arr[i] > step_recency_ns
            accel_ok = accel_std_arr[i] < accel_std_max
            ori_ok = ori_disp_arr[i] < ori_disp_max_deg
            arm_extended = (mean_grav_y_arr[i] == 0.0 or mean_grav_y_arr[i] <= grav_y_min)
            
            flexible_passed = int(accel_ok) + int(ori_ok) + int(arm_extended)
            all_conditions_met = gyro_ok and steps_ok and (flexible_passed >= min_flexible_conditions)
            
            if all_conditions_met:
                if not facing_up_gate_active:
                    facing_up_gate_active = True
                    facing_up_gate_start = t
                    facing_up_break_start = 0
                else:
                    if facing_up_break_start != 0:
                        break_duration = t - facing_up_break_start
                        facing_up_gate_start += break_duration
                        facing_up_break_start = 0
                    held_for = t - facing_up_gate_start
                    if held_for >= facing_up_min_duration_ns:
                        facing_up_locked_at = t
                        state = STATE_FACING_UP_LOCKED
            else:
                if facing_up_gate_active:
                    if facing_up_break_start == 0:
                        facing_up_break_start = t
                    elif (t - facing_up_break_start) > facing_up_break_tolerance_ns:
                        facing_up_gate_active = False
                        facing_up_break_start = 0
                        
        elif state == STATE_FACING_UP_LOCKED:
            steps_ok = step_age_arr[i] > step_recency_ns
            if not steps_ok:
                state = STATE_ACTIVITY_CLASSIFY
                facing_up_gate_active = False
                facing_up_break_start = 0
                continue
                
            elapsed = t - facing_up_locked_at
            if elapsed > backswing_timeout_ns:
                state = STATE_ACTIVITY_CLASSIFY
                facing_up_gate_active = False
                facing_up_break_start = 0
                continue
            
            if g_mag >= backswing_trigger_rad_s:
                state = STATE_MEASURING_ARC
                swing_start_time = t
                peak_gyro = g_mag
                peak_gyro_time = t
                
        elif state == STATE_MEASURING_ARC:
            if g_mag > peak_gyro:
                peak_gyro = g_mag
                peak_gyro_time = t
            if (t - swing_start_time) >= 1000000000:
                state = STATE_CONTACT_WAIT
                
        elif state == STATE_CONTACT_WAIT:
            if (t - peak_gyro_time) >= 750000000:
                detected_shots.append(sec)
                last_shot_end_time = peak_gyro_time + 1000000000
                state = STATE_ACTIVITY_CLASSIFY
                facing_up_gate_active = False
                facing_up_break_start = 0
                
    return detected_shots

def evaluate_detections(detected_secs, gt_times, session_duration):
    # Align and calculate TP / FP
    # Matched if detected contact time (secs - 0.75) is within 3.0s of gt
    tp = 0
    fn = 0
    matched_gt = set()
    matched_det = set()
    
    for gt_idx, gt_t in enumerate(gt_times):
        best_diff = 999.0
        best_det_idx = -1
        for det_idx, det_sec in enumerate(detected_secs):
            if det_idx in matched_det:
                continue
            detected_contact_time = det_sec - 0.75
            diff = abs(detected_contact_time - gt_t)
            if diff <= 3.0 and diff < best_diff:
                best_diff = diff
                best_det_idx = det_idx
                
        if best_det_idx != -1:
            tp += 1
            matched_gt.add(gt_idx)
            matched_det.add(best_det_idx)
            
    fn = len(gt_times) - tp
    fp = len(detected_secs) - tp
    
    recall = tp / len(gt_times) if len(gt_times) > 0 else 1.0
    fp_rate = fp / (session_duration / 60.0) # FP per minute
    
    return recall, fp, fp_rate

def main():
    print("Loading sensor data and ground truth for all 7 sessions...")
    session_data = []
    for s in sessions:
        print(f"  Loading {s['name']}...")
        gyro, accel, gravity, orient, steps, gt_times = load_sensor_and_gt(s['path'])
        duration = gyro['seconds_elapsed'].max()
        precomputed = precompute_stats_for_session(gyro, accel, gravity, orient, steps)
        session_data.append({
            'name': s['name'],
            'gyro_t': gyro['time'].values,
            'gyro_sec': gyro['seconds_elapsed'].values,
            'gyro_mag': gyro['mag'].values,
            'precomputed': precomputed,
            'gt_times': gt_times,
            'duration': duration
        })
    print("Precomputation completed for all sessions.")
    
    # Generate all grid candidates
    import itertools
    keys, values = zip(*GRID.items())
    grid_configs = [dict(zip(keys, v)) for v in itertools.product(*values)]
    print(f"Running grid search over {len(grid_configs)} configurations...")
    
    best_config = None
    best_avg_recall = -1.0
    best_total_fp = 999999
    
    results = []
    
    for idx, config in enumerate(grid_configs):
        recalls = []
        fps = []
        fp_rates = []
        for s in session_data:
            det = run_simulation(s['precomputed'], s['gyro_t'], s['gyro_sec'], s['gyro_mag'], config)
            rec, fp, fp_rate = evaluate_detections(det, s['gt_times'], s['duration'])
            recalls.append(rec)
            fps.append(fp)
            fp_rates.append(fp_rate)
            
        avg_recall = np.mean(recalls)
        avg_fp_rate = np.mean(fp_rates)
        total_fp = np.sum(fps)
        
        results.append({
            'config': config,
            'avg_recall': avg_recall,
            'avg_fp_rate': avg_fp_rate,
            'total_fp': total_fp,
            'recalls': recalls,
            'fps': fps
        })
        
    # Sort and display the top 15 configurations by average recall
    results.sort(key=lambda x: (-x['avg_recall'], x['total_fp']))
    
    print("\n=======================================================")
    print("  TOP 15 GRID SEARCH CONFIGURATIONS BY RECALL")
    print("=======================================================\n")
    print(f"{'Idx':<3} {'Recall':<8} {'FP/min':<8} {'FP':<5} {'GyroStd':<8} {'AccStd':<8} {'OriDisp':<8} {'GravY':<6} {'MinDur':<8} {'Guard':<6}")
    print("-" * 85)
    for i in range(min(15, len(results))):
        r = results[i]
        c = r['config']
        print(f"{i+1:<3} {r['avg_recall']*100:>5.1f}%  {r['avg_fp_rate']:>7.3f}  {r['total_fp']:<5} {c['gyro_std_max']:<8} {c['accel_std_max']:<8} {c['ori_disp_max_deg']:<8} {c['grav_y_min']:<6} {c['facing_up_min_duration_ns']/1e9:<8} {c['post_shot_guard_ns']/1e9:<6}")
    
    # Select best config using a balanced score
    # Let's say: score = recall - 0.1 * fp_rate (to penalize FPs moderately)
    best_item = max(results, key=lambda x: x['avg_recall'] - 0.1 * x['avg_fp_rate'])
    best_config = best_item['config']
    best_avg_recall = best_item['avg_recall']
    best_total_fp = best_item['total_fp']
    
    print("\n=======================================================")
    print("  BALANCED OPTIMAL CONFIGURATION RESULTS")
    print("=======================================================\n")
    print(f"Best Config:")
    print(json.dumps(best_config, indent=2))
    print(f"\nAverage Recall: {best_avg_recall*100:.2f}%")
    print(f"Total False Positives: {best_total_fp}")
    print(f"Average FP/min: {best_item['avg_fp_rate']:.3f}")
    
    # Detailed breakdown of best config
    print("\nDetailed Session Breakdown:")
    for s_idx, s in enumerate(session_data):
        det = run_simulation(s['precomputed'], s['gyro_t'], s['gyro_sec'], s['gyro_mag'], best_config)
        rec, fp, fp_rate = evaluate_detections(det, s['gt_times'], s['duration'])
        print(f"  {s['name']}: Recall={rec*100:.1f}% ({len(det) - fp}/{len(s['gt_times'])}), FP={fp} ({fp_rate:.2f} FP/min), Detections={len(det)}")

if __name__ == "__main__":
    main()

