#!/usr/bin/env python3
import os
import re
import sys
import json
import argparse
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--session-dir", required=True, help="Path to the target session directory")
    parser.add_argument("--sessions-base", default="/Users/neilkloot/Code/Batting Sensor Stats/live_watch_sessions", help="Base directory containing all sessions")
    return parser.parse_args()

def load_all_sessions(sessions_base):
    sessions = []
    for d in sorted(os.listdir(sessions_base)):
        full_path = os.path.join(sessions_base, d)
        if os.path.isdir(full_path) and d.startswith("session-"):
            sessions.append(full_path)
    return sessions

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
    # Fallback to metadata
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

def load_shot_times(session_dir):
    offset = get_clock_offset(session_dir)
    narrations_path = os.path.join(session_dir, "narrations_raw.json")
    gyro_path = os.path.join(session_dir, "WatchGyroscope.csv")
    if not os.path.exists(narrations_path):
        return [], offset
    with open(narrations_path, "r") as f:
        narrations = json.load(f)
    
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
                
    shot_times = []
    for n in narrations:
        st = n.get('shot_type', '')
        if any(term in st.lower() for term in ['facing up', 'no shot', 'leave', 'evade']):
            continue
        shot_times.append(n['timestamp_seconds'] + offset)
    return shot_times, offset

def compute_rolling_features(df, value_cols, windows=[0.5, 1.0, 2.0], prefix=""):
    df = df.sort_values('seconds_elapsed')
    feats_dict = {}
    feats_dict['seconds_elapsed'] = df['seconds_elapsed']
    
    dt_idx = pd.to_timedelta(df['seconds_elapsed'], unit='s')
    df_temp = df.copy()
    df_temp.index = dt_idx
    
    for w in windows:
        roll = df_temp[value_cols].rolling(window=f'{int(w*1000)}ms', min_periods=2)
        mean = roll.mean()
        std = roll.std()
        rmin = roll.min()
        rmax = roll.max()
        rrange = rmax - rmin
        
        for col in value_cols:
            feats_dict[f"{prefix}_{col}_mean_{w}s"] = mean[col].values
            feats_dict[f"{prefix}_{col}_std_{w}s"] = std[col].values
            feats_dict[f"{prefix}_{col}_min_{w}s"] = rmin[col].values
            feats_dict[f"{prefix}_{col}_max_{w}s"] = rmax[col].values
            feats_dict[f"{prefix}_{col}_range_{w}s"] = rrange[col].values
            
    feats = pd.DataFrame(feats_dict, index=df.index)
    return feats

def compute_quat_features(df, prefix=""):
    df = df.sort_values('seconds_elapsed')
    qx = df['qx'].values
    qy = df['qy'].values
    qz = df['qz'].values
    qw = df['qw'].values
    
    dots = qx[:-1]*qx[1:] + qy[:-1]*qy[1:] + qz[:-1]*qz[1:] + qw[:-1]*qw[1:]
    dots = np.clip(np.abs(dots), -1.0, 1.0)
    angles = np.degrees(2.0 * np.arccos(dots))
    
    angles = np.insert(angles, 0, 0.0)
    df_temp = pd.DataFrame(index=pd.to_timedelta(df['seconds_elapsed'], unit='s'))
    df_temp['angle_disp'] = angles
    
    feats_dict = {}
    feats_dict['seconds_elapsed'] = df['seconds_elapsed']
    
    for w in [0.5, 1.0, 2.0]:
        roll = df_temp['angle_disp'].rolling(window=f'{int(w*1000)}ms', min_periods=2)
        feats_dict[f"{prefix}_ori_disp_mean_{w}s"] = roll.mean().values
        feats_dict[f"{prefix}_ori_disp_max_{w}s"] = roll.max().values
        
    feats = pd.DataFrame(feats_dict, index=df.index)
    return feats

def extract_all_features_for_session(session_dir):
    files = {
        'WatchAccelerometer': ('accel', ['x', 'y', 'z']),
        'WatchGyroscope': ('gyro', ['x', 'y', 'z']),
        'WatchGravity': ('grav', ['x', 'y', 'z']),
        'WatchLinearAcceleration': ('linacc', ['x', 'y', 'z']),
        'WatchMagnetometer': ('mag', ['x', 'y', 'z']),
        'WatchGyroscopeUncalibrated': ('gyrouncal', ['x', 'y', 'z', 'bias_x', 'bias_y', 'bias_z']),
        'WatchMagnetometerUncalibrated': ('maguncal', ['x', 'y', 'z', 'bias_x', 'bias_y', 'bias_z']),
        'WatchBarometer': ('baro', ['pressure']),
        'WatchHeartRate': ('hr', ['bpm'])
    }
    
    feats_dfs = []
    
    gyro_path = os.path.join(session_dir, "WatchGyroscope.csv")
    if not os.path.exists(gyro_path):
        return None, None
        
    df_gyro = pd.read_csv(gyro_path)
    df_gyro['mag'] = np.sqrt(df_gyro['x']**2 + df_gyro['y']**2 + df_gyro['z']**2)
    gyro_feats = compute_rolling_features(df_gyro, ['x', 'y', 'z', 'mag'], prefix='gyro')
    feats_dfs.append(gyro_feats)
    
    for name, (prefix, cols) in files.items():
        if name == 'WatchGyroscope':
            continue
        p = os.path.join(session_dir, f"{name}.csv")
        if os.path.exists(p):
            df = pd.read_csv(p)
            if 'x' in cols and 'y' in cols and 'z' in cols:
                df['mag'] = np.sqrt(df['x']**2 + df['y']**2 + df['z']**2)
                cur_cols = cols + ['mag']
            else:
                cur_cols = cols
            df_feats = compute_rolling_features(df, cur_cols, prefix=prefix)
            feats_dfs.append(df_feats)
            
    quats = {
        'WatchGameOrientation': 'game_ori',
        'WatchGeomagneticOrientation': 'geomag_ori',
        'WatchOrientation': 'ori'
    }
    for name, prefix in quats.items():
        p = os.path.join(session_dir, f"{name}.csv")
        if os.path.exists(p):
            df = pd.read_csv(p)
            df_feats = compute_quat_features(df, prefix=prefix)
            feats_dfs.append(df_feats)
            
    max_t = df_gyro['seconds_elapsed'].max()
    time_grid = np.arange(2.0, max_t - 2.0, 0.1)
    grid_df = pd.DataFrame({'seconds_elapsed': time_grid})
    
    merged_df = grid_df
    for f_df in feats_dfs:
        merged_df = pd.merge_asof(merged_df, f_df, on='seconds_elapsed', direction='nearest')
        
    steps_path = os.path.join(session_dir, "WatchSteps.csv")
    if os.path.exists(steps_path):
        df_steps = pd.read_csv(steps_path)
        step_times = df_steps['seconds_elapsed'].values
    else:
        step_times = np.array([])
        
    step_ages = []
    for t in time_grid:
        if len(step_times) > 0:
            idx = np.searchsorted(step_times, t, side='right')
            if idx > 0:
                step_ages.append(t - step_times[idx - 1])
            else:
                step_ages.append(999999.0)
        else:
            step_ages.append(999999.0)
    merged_df['step_age'] = step_ages
    
    return merged_df, df_gyro

def build_labeled_dataset(merged_df, shot_times):
    labels = []
    indices_to_keep = []
    
    times = merged_df['seconds_elapsed'].values
    for idx, t in enumerate(times):
        is_pos = False
        is_neg = True
        for st in shot_times:
            if (st - 3.5) <= t <= (st - 1.5):
                is_pos = True
            if abs(t - st) < 8.0:
                is_neg = False
        if is_pos:
            labels.append(1)
            indices_to_keep.append(idx)
        elif is_neg:
            labels.append(0)
            indices_to_keep.append(idx)
            
    filtered_df = merged_df.iloc[indices_to_keep].copy()
    filtered_df['label'] = labels
    return filtered_df

def rank_features(df):
    feature_cols = [c for c in df.columns if c not in ['seconds_elapsed', 'label', 'time']]
    X = df[feature_cols].fillna(0.0)
    y = df['label']
    
    rf = RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1)
    rf.fit(X, y)
    
    importances = rf.feature_importances_
    ranking = sorted(zip(feature_cols, importances), key=lambda x: x[1], reverse=True)
    return ranking

def simulate_detector_for_session(session_dir, gyro_std_max, accel_std_max, ori_disp_max, grav_y_min, min_flexible):
    gyro_path = os.path.join(session_dir, "WatchGyroscope.csv")
    accel_path = os.path.join(session_dir, "WatchAccelerometer.csv")
    gravity_path = os.path.join(session_dir, "WatchGravity.csv")
    orient_path = os.path.join(session_dir, "WatchGameOrientation.csv")
    if not os.path.exists(orient_path):
        orient_path = os.path.join(session_dir, "WatchOrientation.csv")
    steps_path = os.path.join(session_dir, "WatchSteps.csv")
    
    if not all(os.path.exists(p) for p in [gyro_path, accel_path, gravity_path, orient_path]):
        return [], 0.0
        
    df_gyro = pd.read_csv(gyro_path)
    df_accel = pd.read_csv(accel_path)
    df_grav = pd.read_csv(gravity_path)
    df_orient = pd.read_csv(orient_path)
    df_steps = pd.read_csv(steps_path) if os.path.exists(steps_path) else None
    
    df_gyro['mag'] = np.sqrt(df_gyro['x']**2 + df_gyro['y']**2 + df_gyro['z']**2)
    df_accel['mag'] = np.sqrt(df_accel['x']**2 + df_accel['y']**2 + df_accel['z']**2)
    
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
    
    n_samples = len(gyro_t)
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
    
    gyro_std_arr = precomputed['gyro_std']
    accel_std_arr = precomputed['accel_std']
    ori_disp_arr = precomputed['ori_disp']
    mean_grav_y_arr = precomputed['mean_grav_y']
    step_age_arr = precomputed['step_age']
    
    step_recency_ns = 1000000000
    facing_up_min_duration_ns = 800000000
    facing_up_break_tolerance_ns = 1500000000
    backswing_timeout_ns = 10000000000
    backswing_trigger_rad_s = 5.0
    post_shot_guard_ns = 1500000000
    
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
            if (t_ns - peak_gyro_time) >= 750000000:
                detected_shots.append(sec)
                last_shot_end_time = peak_gyro_time + 1000000000
                state = STATE_ACTIVITY_CLASSIFY
                facing_up_gate_active = False
                facing_up_break_start = 0
                
    return detected_shots, gyro_sec.max()

def evaluate_detections(detected_secs, gt_times, session_duration):
    tp = 0
    matched_gt = set()
    matched_det = set()
    
    for gt_idx, gt_t in enumerate(gt_times):
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
            matched_gt.add(gt_idx)
            matched_det.add(best_det_idx)
            
    fp = len(detected_secs) - tp
    fn = len(gt_times) - tp
    recall = tp / len(gt_times) if len(gt_times) > 0 else 1.0
    precision = tp / len(detected_secs) if len(detected_secs) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
    fp_min = fp / (session_duration / 60.0) if session_duration > 0 else 0.0
    return recall, fp, fp_min, f1

def main():
    args = parse_args()
    
    print("Loading target session features...")
    merged_df, _ = extract_all_features_for_session(args.session_dir)
    if merged_df is None:
        print("Error: Could not load target session.")
        return
        
    shot_times, offset = load_shot_times(args.session_dir)
    print(f"Loaded {len(shot_times)} shots. Running feature importance on all physical + virtual sensors...")
    
    labeled_df = build_labeled_dataset(merged_df, shot_times)
    ranking = rank_features(labeled_df)
    
    print("\nTop 30 Feature Importances:")
    for i, (feat, imp) in enumerate(ranking[:30]):
        print(f"  {i+1:2d}. {feat:<50} : {imp:.4f}")
        
    curr_gyro = 1.2
    curr_accel = 3.25
    curr_ori = 2.5
    curr_grav_y = -6.0
    curr_min_flex = 3
    
    print("\nSimulating current deployed gate config...")
    det_shots, duration = simulate_detector_for_session(args.session_dir, curr_gyro, curr_accel, curr_ori, curr_grav_y, curr_min_flex)
    recall, fp, fp_min, f1 = evaluate_detections(det_shots, shot_times, duration)
    print(f"Current Gate -> Recall: {recall:.2%}, FPs: {fp} ({fp_min:.2f} FP/min), F1: {f1:.3f}")
    
    gyro_grids = [0.9, 1.2, 1.5]
    accel_grids = [2.0, 3.25, 4.0]
    ori_grids = [2.0, 2.5, 3.0]
    grav_y_grids = [-4.0, -6.0, -7.0]
    min_flex_grids = [2, 3]
    
    print("\nGrid searching alternative gate thresholds on the latest session...")
    candidates = []
    for g_std in gyro_grids:
        for a_std in accel_grids:
            for o_disp in ori_grids:
                for gr_y in grav_y_grids:
                    for mf in min_flex_grids:
                        det, dur = simulate_detector_for_session(args.session_dir, g_std, a_std, o_disp, gr_y, mf)
                        rec, f_p, fp_m, f1_score = evaluate_detections(det, shot_times, dur)
                        candidates.append((g_std, a_std, o_disp, gr_y, mf, rec, f_p, fp_m, f1_score))
                        
    candidates.sort(key=lambda x: (-x[8], x[6]))
    print("Top 5 Alternative Gate Configs (Latest Session):")
    for i, c in enumerate(candidates[:5]):
        print(f"  {i+1}. GyroStd={c[0]:.2f}, AccelStd={c[1]:.2f}, OriDisp={c[2]:.2f}, GravY={c[3]:.1f}, MinFlex={c[4]} -> Recall={c[5]:.1%}, FPs={c[6]} ({c[7]:.2f} FP/min), F1={c[8]:.3f}")

    all_sessions = load_all_sessions(args.sessions_base)
    print(f"\nPerforming cross-session validation across {len(all_sessions)} sessions...")
    
    session_data = []
    for s_path in all_sessions:
        s_shots, s_off = load_shot_times(s_path)
        if len(s_shots) == 0:
            continue
        session_data.append((s_path, s_shots))
        
    print(f"Loaded {len(session_data)} historical sessions for validation.")
    
    top_configs = [(curr_gyro, curr_accel, curr_ori, curr_grav_y, curr_min_flex)] + [c[:5] for c in candidates[:3]]
    configs_metrics = []
    
    for cfg in top_configs:
        g_std, a_std, o_disp, gr_y, mf = cfg
        recalls, fps, f1s = [], [], []
        for s_path, s_shots in session_data:
            det, dur = simulate_detector_for_session(s_path, g_std, a_std, o_disp, gr_y, mf)
            rec, f_p, fp_m, f1_score = evaluate_detections(det, s_shots, dur)
            recalls.append(rec)
            fps.append(f_p)
            f1s.append(f1_score)
        configs_metrics.append({
            'config': cfg,
            'mean_recall': np.mean(recalls),
            'total_fps': np.sum(fps),
            'mean_f1': np.mean(f1s)
        })
        
    print("\nCross-Session Validation Results:")
    for i, res in enumerate(configs_metrics):
        cfg = res['config']
        label = "Current Deployed" if i == 0 else f"Candidate {i}"
        print(f"  {label:<18}: GyroStd={cfg[0]:.2f}, AccelStd={cfg[1]:.2f}, OriDisp={cfg[2]:.2f}, GravY={cfg[3]:.1f}, MinFlex={cfg[4]}")
        print(f"    Avg Recall: {res['mean_recall']:.2%}, Total FPs: {res['total_fps']}, Avg F1: {res['mean_f1']:.3f}")

if __name__ == "__main__":
    main()
