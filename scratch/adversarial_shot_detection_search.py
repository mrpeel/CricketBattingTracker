#!/usr/bin/env python3
import os
import re
import sys
import json
import argparse
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import classification_report, confusion_matrix

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--session-dir", required=True, help="Path to the session directory")
    parser.add_argument("--features-csv", default="/Users/neilkloot/Code/Batting Sensor Stats/combined_features.csv", help="Path to combined_features.csv")
    return parser.parse_args()

def load_sensor_data(session_dir):
    gyro_path = os.path.join(session_dir, "WatchGyroscope.csv")
    accel_path = os.path.join(session_dir, "WatchAccelerometer.csv")
    grav_path = os.path.join(session_dir, "WatchGravity.csv")
    linacc_path = os.path.join(session_dir, "WatchLinearAcceleration.csv")
    mag_path = os.path.join(session_dir, "WatchMagnetometer.csv")
    orient_path = os.path.join(session_dir, "WatchGameOrientation.csv")
    if not os.path.exists(orient_path):
        orient_path = os.path.join(session_dir, "WatchOrientation.csv")
    steps_path = os.path.join(session_dir, "WatchSteps.csv")

    df_gyro = pd.read_csv(gyro_path)
    df_gyro['mag'] = np.sqrt(df_gyro['x']**2 + df_gyro['y']**2 + df_gyro['z']**2)
    
    df_accel = pd.read_csv(accel_path)
    df_accel['mag'] = np.sqrt(df_accel['x']**2 + df_accel['y']**2 + df_accel['z']**2)
    
    df_grav = pd.read_csv(grav_path)
    
    df_linacc = pd.read_csv(linacc_path) if os.path.exists(linacc_path) else None
    if df_linacc is not None:
        df_linacc['mag'] = np.sqrt(df_linacc['x']**2 + df_linacc['y']**2 + df_linacc['z']**2)
        
    df_mag = pd.read_csv(mag_path) if os.path.exists(mag_path) else None
    if df_mag is not None:
        df_mag['mag'] = np.sqrt(df_mag['x']**2 + df_mag['y']**2 + df_mag['z']**2)
        
    df_orient = pd.read_csv(orient_path)
    df_steps = pd.read_csv(steps_path) if os.path.exists(steps_path) else None
    
    return df_gyro, df_accel, df_grav, df_linacc, df_mag, df_orient, df_steps

def get_clock_offset(session_dir):
    gt_aligned_path = os.path.join(session_dir, "ground_truth_aligned.csv")
    if os.path.exists(gt_aligned_path):
        try:
            df_gt = pd.read_csv(gt_aligned_path)
            df_shots_only = df_gt[df_gt['shot_type'] != 'Facing up']
            if len(df_shots_only) > 0:
                row = df_shots_only.iloc[0]
                return row['sensor_narr_time_seconds'] - row['audio_time_seconds']
        except:
            pass
    return 0.0

def load_shot_times(session_dir):
    offset = get_clock_offset(session_dir)
    narrations_path = os.path.join(session_dir, "narrations_raw.json")
    gyro_path = os.path.join(session_dir, "WatchGyroscope.csv")
    if not os.path.exists(narrations_path):
        return [], offset
    with open(narrations_path, "r") as f:
        narrations = json.load(f)
        
    # MMSS conversion
    if os.path.exists(gyro_path) and narrations:
        df_gyro = pd.read_csv(gyro_path)
        gyro_duration = df_gyro.iloc[-1]['seconds_elapsed']
        is_mmss = True
        for n in narrations:
            t = n['timestamp_seconds']
            sec_part = int(t) % 100
            if sec_part >= 60:
                is_mmss = False
                break
        max_t = max(n['timestamp_seconds'] for n in narrations)
        if max_t > gyro_duration:
            is_mmss = True
        if is_mmss:
            for n in narrations:
                t = n['timestamp_seconds']
                ival = int(t)
                frac = t - ival
                minutes = ival // 100
                seconds = ival % 100
                n['timestamp_seconds'] = float(minutes * 60 + seconds + frac)
    
    shots = []
    for n in narrations:
        st = n.get('shot_type', '')
        if any(term in st.lower() for term in ['facing up', 'no shot', 'leave', 'evade']):
            continue
        shots.append({
            'time': n['timestamp_seconds'] + offset,
            'type': st,
            'text': n.get('narrated_text', '')
        })
    return shots, offset

def calculate_snr(df_gyro, df_accel, df_linacc, df_mag, shots):
    snr_results = {}
    
    # Define swing vs stance window offsets
    # Swing: [T_impact - 0.8s, T_impact + 0.3s]
    # Stance: [T_impact - 3.5s, T_impact - 1.5s]
    sensors = {
        'Gyroscope': (df_gyro, 'mag'),
        'Accelerometer': (df_accel, 'mag'),
    }
    if df_linacc is not None:
        sensors['LinearAccel'] = (df_linacc, 'mag')
    if df_mag is not None:
        sensors['Magnetometer'] = (df_mag, 'mag')
        
    for name, (df, col) in sensors.items():
        t_arr = df['seconds_elapsed'].values
        val_arr = df[col].values
        
        swing_peaks = []
        stance_means = []
        
        for shot in shots:
            t = shot['time']
            # Swing slice
            sw_idx = (t_arr >= t - 0.8) & (t_arr <= t + 0.3)
            # Stance slice
            st_idx = (t_arr >= t - 3.5) & (t_arr <= t - 1.5)
            
            if sw_idx.any() and st_idx.any():
                swing_peaks.append(np.max(val_arr[sw_idx]))
                stance_means.append(np.mean(val_arr[st_idx]))
                
        if len(swing_peaks) > 0:
            avg_peak = np.mean(swing_peaks)
            avg_stance = np.mean(stance_means)
            snr = avg_peak / avg_stance if avg_stance > 0 else 0.0
            snr_results[name] = {
                'avg_swing_peak': avg_peak,
                'avg_stance_baseline': avg_stance,
                'snr': snr
            }
            
    return snr_results

def simulate_with_config(df_gyro, df_accel, df_grav, df_orient, df_steps, shots, config):
    # State machine simulation
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
    
    # Config parameters
    gyro_std_max = 1.2
    accel_std_max = 3.25
    ori_disp_max = 2.5
    grav_y_min = -6.0
    min_flexible = 3
    
    step_recency_ns = 1000000000 # 1s
    facing_up_min_duration_ns = 800000000 # 0.8s
    facing_up_break_tolerance_ns = 1500000000 # 1.5s
    
    # Variable parameters to search
    backswing_trigger_rad_s = config['trigger_threshold']
    backswing_timeout_ns = int(config['timeout_seconds'] * 1e9)
    post_shot_guard_ns = int(config['post_shot_guard_seconds'] * 1e9)
    contact_wait_ns = int(config['contact_wait_seconds'] * 1e9)
    
    n_samples = len(df_gyro)
    gyro_t = df_gyro['seconds_elapsed'].values
    gyro_sec = df_gyro['seconds_elapsed'].values
    gyro_mag = df_gyro['mag'].values
    
    accel_t = df_accel['seconds_elapsed'].values
    accel_mag = df_accel['mag'].values
    grav_t = df_grav['seconds_elapsed'].values
    grav_y = df_grav['y'].values
    orient_t = df_orient['seconds_elapsed'].values
    orient_qx = df_orient['qx'].values
    orient_qy = df_orient['qy'].values
    orient_qz = df_orient['qz'].values
    orient_qw = df_orient['qw'].values
    step_t = df_steps['seconds_elapsed'].values if (df_steps is not None and len(df_steps) > 0) else np.array([])
    
    precomputed = {
        'gyro_std': np.zeros(n_samples),
        'accel_std': np.zeros(n_samples),
        'mean_grav_y': np.zeros(n_samples),
        'ori_disp': np.zeros(n_samples),
        'step_age': np.zeros(n_samples)
    }
    
    for i in range(n_samples):
        t = gyro_t[i]
        g_start = t - 1.0
        g_start_idx = np.searchsorted(gyro_t, g_start)
        g_end_idx = i + 1
        precomputed['gyro_std'][i] = np.std(gyro_mag[g_start_idx:g_end_idx]) if (g_end_idx - g_start_idx) >= 2 else 0.0
        
        a_start_idx = np.searchsorted(accel_t, g_start)
        a_end_idx = np.searchsorted(accel_t, t, side='right')
        precomputed['accel_std'][i] = np.std(accel_mag[a_start_idx:a_end_idx]) if (a_end_idx - a_start_idx) >= 2 else 0.0
        
        gr_start_idx = np.searchsorted(grav_t, g_start)
        gr_end_idx = np.searchsorted(grav_t, t, side='right')
        y_gr = grav_y[gr_start_idx:gr_end_idx]
        precomputed['mean_grav_y'][i] = np.mean(y_gr) if len(y_gr) >= 5 else 0.0
        
        o_start = t - 0.5
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
            
        if len(step_t) > 0:
            step_idx = np.searchsorted(step_t, t, side='right')
            if step_idx > 0:
                precomputed['step_age'][i] = (t - step_t[step_idx - 1]) * 1e9
            else:
                precomputed['step_age'][i] = 999999.0 * 1e9
        else:
            precomputed['step_age'][i] = 999999.0 * 1e9

    gyro_std_arr = precomputed['gyro_std']
    accel_std_arr = precomputed['accel_std']
    ori_disp_arr = precomputed['ori_disp']
    mean_grav_y_arr = precomputed['mean_grav_y']
    step_age_arr = precomputed['step_age']
    
    # Forensic logs to analyze missed shots
    forensics = []
    
    for i in range(n_samples):
        t_ns = int(gyro_t[i] * 1e9)
        sec = gyro_sec[i]
        g_mag = gyro_mag[i]
        
        if state == STATE_ACTIVITY_CLASSIFY:
            if t_ns <= last_shot_end_time + post_shot_guard_ns:
                continue
                
            gyro_ok = gyro_std_arr[i] < gyro_std_max
            steps_ok = step_age_arr[i] > step_recency_ns
            accel_ok = accel_std_arr[i] < accel_std_max
            ori_ok = ori_disp_arr[i] < ori_disp_max
            arm_extended = (mean_grav_y_arr[i] == 0.0 or mean_grav_y_arr[i] <= grav_y_min)
            
            flexible_passed = int(accel_ok) + int(ori_ok) + int(arm_extended)
            all_conditions_met = gyro_ok and steps_ok and (flexible_passed >= min_flexible)
            
            if all_conditions_met:
                if not facing_up_gate_active:
                    facing_up_gate_active = True
                    facing_up_gate_start = t_ns
                    facing_up_break_start = 0
                else:
                    if facing_up_break_start != 0:
                        break_duration = t_ns - facing_up_break_start
                        facing_up_gate_start += break_duration
                        facing_up_break_start = 0
                    held_for = t_ns - facing_up_gate_start
                    if held_for >= facing_up_min_duration_ns:
                        facing_up_locked_at = t_ns
                        state = STATE_FACING_UP_LOCKED
            else:
                if facing_up_gate_active:
                    if facing_up_break_start == 0:
                        facing_up_break_start = t_ns
                    elif (t_ns - facing_up_break_start) > facing_up_break_tolerance_ns:
                        facing_up_gate_active = False
                        facing_up_break_start = 0
                        
        elif state == STATE_FACING_UP_LOCKED:
            steps_ok = step_age_arr[i] > step_recency_ns
            if not steps_ok:
                state = STATE_ACTIVITY_CLASSIFY
                facing_up_gate_active = False
                facing_up_break_start = 0
                continue
                
            elapsed = t_ns - facing_up_locked_at
            if elapsed > backswing_timeout_ns:
                state = STATE_ACTIVITY_CLASSIFY
                facing_up_gate_active = False
                facing_up_break_start = 0
                continue
                
            if g_mag >= backswing_trigger_rad_s:
                state = STATE_MEASURING_ARC
                swing_start_time = t_ns
                peak_gyro = g_mag
                peak_gyro_time = t_ns
                
        elif state == STATE_MEASURING_ARC:
            if g_mag > peak_gyro:
                peak_gyro = g_mag
                peak_gyro_time = t_ns
            if (t_ns - swing_start_time) >= 1000000000:
                state = STATE_CONTACT_WAIT
                
        elif state == STATE_CONTACT_WAIT:
            if (t_ns - peak_gyro_time) >= contact_wait_ns:
                detected_shots.append({
                    'time': sec,
                    'max_gyro': peak_gyro,
                    'time_ns': peak_gyro_time
                })
                last_shot_end_time = peak_gyro_time + 1000000000
                state = STATE_ACTIVITY_CLASSIFY
                facing_up_gate_active = False
                facing_up_break_start = 0

    # Forensics for each ground truth shot
    # Check if a GT shot matches any detected shot
    gt_times = [s['time'] for s in shots]
    for gt_idx, gt in enumerate(shots):
        gt_t = gt['time']
        matched = False
        reason = "Unknown"
        
        # Check if matched
        for det in detected_shots:
            if abs(det['time'] - 0.75 - gt_t) < 3.0:
                matched = True
                break
                
        if not matched:
            # Let's inspect what happened in the state machine at gt_t
            # Find closest gyro sample index to gt_t
            closest_idx = np.argmin(np.abs(gyro_sec - gt_t))
            # Let's inspect the state of the detector in a window before the shot
            # [gt_t - 4.0, gt_t]
            win_start = gt_t - 4.0
            win_end = gt_t
            win_idx = (gyro_sec >= win_start) & (gyro_sec <= win_end)
            
            # Check if any step event occurred in [gt_t - 4.0, gt_t]
            step_in_win = step_t[(step_t >= win_start) & (step_t <= win_end)]
            if len(step_in_win) > 0:
                reason = f"Step detector fired at {step_in_win[0]:.2f}s, breaking stance gate"
            else:
                # Check if gyro_std was too high
                mean_gyro_std = np.mean(gyro_std_arr[win_idx]) if win_idx.any() else 0.0
                mean_accel_std = np.mean(accel_std_arr[win_idx]) if win_idx.any() else 0.0
                if mean_gyro_std > gyro_std_max:
                    reason = f"Gyro std-of-mag too high ({mean_gyro_std:.2f} > {gyro_std_max}), bat was not still"
                elif mean_accel_std > accel_std_max:
                    reason = f"Accel std-of-mag too high ({mean_accel_std:.2f} > {accel_std_max}), too much motion/shock"
                else:
                    reason = "Stance gate opened but backswing trigger failed to cross threshold, or timeout expired"
            
            forensics.append({
                'gt_index': gt_idx,
                'gt_time': gt_t,
                'shot_type': gt['type'],
                'text': gt['text'],
                'reason': reason
            })
            
    return detected_shots, forensics

def run_classification_parity(features_csv, detected_shots, df_gyro, df_accel, df_grav, df_orient, session_dir):
    # Train the exact Random Forest parity model
    if not os.path.exists(features_csv):
        return {"status": "error", "message": "combined_features.csv not found for RF parity"}
        
    df_feats = pd.read_csv(features_csv)
    df_swings = df_feats[df_feats['normalized_gt'] != 'NON-SWING'].copy()
    
    features = [
        'gyroMag', 'rollImpactDeg', 'yawImpactDeg', 'deltaX', 'deltaZ', 'planeRatio',
        'gyro_y_min', 'grav_x_max', 'grav_y_min', 'mag_x_max'
    ]
    
    X = df_swings[features].fillna(df_swings[features].median())
    y = df_swings['normalized_gt'].values
    
    le = LabelEncoder()
    y_enc = le.fit_transform(y)
    
    rf = RandomForestClassifier(
        n_estimators=200,
        max_depth=8,
        class_weight='balanced_subsample',
        random_state=42,
        n_jobs=-1
    )
    rf.fit(X, y_enc)
    
    # For each detected shot, extract the 10 features exactly as in SwingDetector.kt
    # Let's write the feature extraction logic
    extracted_features = []
    
    # We need to find stance exit time and contact time
    # For simplicity, we can load ground_truth_aligned.csv to match predictions
    gt_aligned_path = os.path.join(session_dir, "ground_truth_aligned.csv")
    if not os.path.exists(gt_aligned_path):
        return {"status": "error", "message": "ground_truth_aligned.csv not found"}
        
    df_gt = pd.read_csv(gt_aligned_path)
    df_gt_swings = df_gt[df_gt['shot_type'] != 'Facing up']
    
    # Match detected shots with ground truth to get predictions
    y_true = []
    y_pred = []
    
    # We will use the already generated scorecard predictions or evaluate here
    # Since SwingDetectorGroundTruthTest runs the Random Forest model and writes predictions,
    # let's look at the classification accuracy in the scorecard report or computed dynamically.
    pass

def main():
    args = parse_args()
    
    print("Loading session data...")
    df_gyro, df_accel, df_grav, df_linacc, df_mag, df_orient, df_steps = load_sensor_data(args.session_dir)
    shots, offset = load_shot_times(args.session_dir)
    
    print(f"Loaded {len(shots)} swing-type shots. Clock offset: {offset:+.3f}s")
    
    # 1. Multi-Sensor Swing SNR
    print("\nCalculating Swing SNR across all motion sensors...")
    snr_res = calculate_snr(df_gyro, df_accel, df_linacc, df_mag, shots)
    for name, stats in snr_res.items():
        print(f"  {name:<15}: Swing Peak={stats['avg_swing_peak']:5.2f} | Stance Baseline={stats['avg_stance_baseline']:5.2f} | SNR={stats['snr']:5.2f}x")
        
    # 2. Grid Search triggers
    # Trigger threshold search space: 2.0 to 8.0 rad/s
    # Contact wait search space: 0.5s to 1.0s
    print("\nGrid searching shot detection trigger parameters...")
    configs = []
    for th in [3.0, 5.0, 7.0]:
        for cw in [0.5, 0.75, 1.0]:
            cfg = {
                'trigger_threshold': th,
                'timeout_seconds': 5.0,
                'post_shot_guard_seconds': 1.5,
                'contact_wait_seconds': cw
            }
            det, _ = simulate_with_config(df_gyro, df_accel, df_grav, df_orient, df_steps, shots, cfg)
            det_secs = [d['time'] for d in det]
            rec, fp, fp_min, f1 = evaluate_detections = evaluate_detections_metrics(det_secs, [s['time'] for s in shots], df_gyro['seconds_elapsed'].max())
            configs.append((th, cw, rec, fp, fp_min, f1))
            
    configs.sort(key=lambda x: -x[5])
    print("Top 3 Trigger Configs:")
    for i, c in enumerate(configs[:3]):
        print(f"  {i+1}. Threshold={c[0]:.1f} rad/s, ContactWait={c[1]:.2f}s -> Recall={c[2]:.1%}, FPs={c[3]} ({c[4]:.2f} FP/min), F1={c[5]:.3f}")

    # 3. Forensics on Missed Shots
    default_cfg = {
        'trigger_threshold': 5.0,
        'timeout_seconds': 10.0,
        'post_shot_guard_seconds': 1.5,
        'contact_wait_seconds': 0.75
    }
    det, forensics = simulate_with_config(df_gyro, df_accel, df_grav, df_orient, df_steps, shots, default_cfg)
    print(f"\nMissed Shot Forensics ({len(forensics)} missed shots):")
    for f in forensics[:10]:
        print(f"  Shot #{f['gt_index']+1} ({f['shot_type']}) at {f['gt_time']:.2f}s: {f['reason']}")

def evaluate_detections_metrics(detected_secs, gt_times, session_duration):
    tp = 0
    matched_det = set()
    for gt_t in gt_times:
        best_diff = 999.0
        best_det_idx = -1
        for det_idx, det_sec in enumerate(detected_secs):
            if det_idx in matched_det:
                continue
            diff = abs(det_sec - 0.75 - gt_t)
            if diff < best_diff:
                best_diff = diff
                best_det_idx = det_idx
        if best_diff <= 3.0:
            tp += 1
            matched_det.add(best_det_idx)
            
    fp = len(detected_secs) - tp
    fn = len(gt_times) - tp
    recall = tp / len(gt_times) if len(gt_times) > 0 else 1.0
    precision = tp / len(detected_secs) if len(detected_secs) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
    fp_min = fp / (session_duration / 60.0) if session_duration > 0 else 0.0
    return recall, fp, fp_min, f1

if __name__ == "__main__":
    main()
