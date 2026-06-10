#!/usr/bin/env python3
import os
import json
import numpy as np
import pandas as pd
from collections import defaultdict

def load_sensor_data(session_dir):
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

def get_offset(session_dir):
    try:
        aligned_path = os.path.join(session_dir, "ground_truth_aligned.csv")
        if os.path.exists(aligned_path):
            df = pd.read_csv(aligned_path)
            if len(df) > 0:
                row = df.iloc[0]
                return float(row['sensor_narr_time_seconds'] - row['audio_time_seconds'])
    except Exception as e:
        print(f"⚠️ Error getting optimized offset: {e}")
    return 0.0

def calculate_quat_displacement(q_slice):
    if len(q_slice) < 2:
        return 0.0
    qx, qy, qz, qw = q_slice['qx'].values, q_slice['qy'].values, q_slice['qz'].values, q_slice['qw'].values
    dots = qx[:-1]*qx[1:] + qy[:-1]*qy[1:] + qz[:-1]*qz[1:] + qw[:-1]*qw[1:]
    dots = np.clip(np.abs(dots), -1.0, 1.0)
    return np.mean(np.degrees(2.0 * np.arccos(dots)))

def main():
    session_base = "/Users/neilkloot/Code/Batting Sensor Stats/live_watch_sessions"
    session_dirs = []
    for root, dirs, files in os.walk(session_base):
        for d in dirs:
            if d.startswith("session-"):
                session_dirs.append(os.path.join(root, d))
    session_dirs = sorted(session_dirs)
    
    all_features = []
    all_labels = []
    
    print("Loading and labeling data across all sessions...")
    for session_dir in session_dirs:
        session_name = os.path.basename(session_dir)
        try:
            gyro, accel, gravity, orient, steps = load_sensor_data(session_dir)
        except Exception as e:
            print(f"Skipping {session_name}: {e}")
            continue
            
        max_t = gyro['seconds_elapsed'].max()
        offset = get_offset(session_dir)
        narr_path = os.path.join(session_dir, "narrations_raw.json")
        if not os.path.exists(narr_path):
            continue
            
        with open(narr_path) as f:
            narrations = json.load(f)
            
        shot_times = [n['timestamp_seconds'] + offset for n in narrations 
                      if not any(term in n.get('shot_type', '').lower() for term in ['facing up', 'no shot', 'leave', 'evade'])]
        
        def check_labels(t):
            is_pos = False
            is_neg = True
            for st in shot_times:
                if (st - 3.5) <= t <= (st - 1.5):
                    is_pos = True
                if abs(t - st) < 8.0:
                    is_neg = False
            return 1 if is_pos else (0 if is_neg else -1)
            
        time_grid = np.arange(2.0, max_t - 2.0, 0.2) # 5Hz sampling to run faster over multiple sessions
        gyro_t, gyro_mag = gyro['seconds_elapsed'].values, gyro['mag'].values
        accel_t, accel_mag = accel['seconds_elapsed'].values, accel['mag'].values
        grav_t, grav_y = gravity['seconds_elapsed'].values, gravity['y'].values
        ori_t = orient['seconds_elapsed'].values
        ori_qx, ori_qy, ori_qz, ori_qw = orient['qx'].values, orient['qy'].values, orient['qz'].values, orient['qw'].values
        step_times = steps['seconds_elapsed'].values if (steps is not None and len(steps) > 0) else np.array([])
        
        session_feats = []
        session_labs = []
        
        for t in time_grid:
            label = check_labels(t)
            if label == -1:
                continue
            w_start, w_end = t - 1.0, t
            feat = {}
            
            # Gyro
            mask_g = (gyro_t >= w_start) & (gyro_t <= w_end)
            feat['gyro_std'] = np.std(gyro_mag[mask_g], ddof=0) if mask_g.sum() >= 2 else 0.0
            
            # Accel
            mask_a = (accel_t >= w_start) & (accel_t <= w_end)
            feat['accel_std'] = np.std(accel_mag[mask_a], ddof=0) if mask_a.sum() >= 2 else 0.0
            
            # Gravity
            mask_gr = (grav_t >= w_start) & (grav_t <= w_end)
            feat['gravity_y_mean'] = np.mean(grav_y[mask_gr]) if mask_gr.sum() > 0 else -9.8
            
            # Orientation
            mask_o = (ori_t >= t - 0.5) & (ori_t <= t)
            if mask_o.sum() >= 2:
                idx = np.where(mask_o)[0]
                qx_slice = pd.DataFrame({'qx': ori_qx[idx], 'qy': ori_qy[idx], 'qz': ori_qz[idx], 'qw': ori_qw[idx]})
                feat['ori_disp_mean'] = calculate_quat_displacement(qx_slice)
            else:
                feat['ori_disp_mean'] = 999.0
                
            # Steps
            feat['steps_count'] = np.sum((step_times >= t - 2.0) & (step_times <= t)) if len(step_times) > 0 else 0
            
            session_feats.append(feat)
            session_labs.append(label)
            
        print(f"  {session_name}: loaded {len(session_feats)} samples")
        all_features.extend(session_feats)
        all_labels.extend(session_labs)
        
    df_feat = pd.DataFrame(all_features)
    X = df_feat
    y = np.array(all_labels)
    
    total_samples = len(y)
    pos_samples = np.sum(y == 1)
    neg_samples = np.sum(y == 0)
    print(f"\nTotal combined dataset size: {total_samples} samples (Stance: {pos_samples}, Rest: {neg_samples})")
    
    # Grid search bounds
    g_grid = np.arange(0.8, 1.8, 0.2)
    a_grid = np.arange(1.5, 3.5, 0.5)
    o_grid = np.arange(1.5, 3.5, 0.5)
    gy_grid = np.arange(-5.0, -1.5, 0.5)
    
    for k in [3, 4]: # evaluate 3-of-4 vs 4-of-4 gate configurations
        print(f"\n--- Global Grid Search: Steps + Gyro mandatory, plus at least {k} of remaining conditions ---")
        best_f1 = 0.0
        best_config = None
        
        for g_th in g_grid:
            for a_th in a_grid:
                for o_th in o_grid:
                    for gy_th in gy_grid:
                        c_gyro = X['gyro_std'] < g_th
                        c_accel = X['accel_std'] < a_th
                        c_ori = X['ori_disp_mean'] < o_th
                        c_grav = X['gravity_y_mean'] <= gy_th
                        
                        motion_passed = c_accel.astype(int) + c_ori.astype(int) + c_grav.astype(int) + c_gyro.astype(int)
                        
                        pred = (
                            (X['steps_count'] == 0) &
                            c_gyro &
                            (motion_passed >= k)
                        ).astype(int)
                        
                        tp = np.sum((pred == 1) & (y == 1))
                        fp = np.sum((pred == 1) & (y == 0))
                        fn = np.sum((pred == 0) & (y == 1))
                        
                        prec = tp / (tp + fp) if (tp + fp) > 0 else 0
                        rec = tp / (tp + fn) if (tp + fn) > 0 else 0
                        f1 = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0
                        
                        if f1 > best_f1:
                            best_f1 = f1
                            best_config = {
                                'gyro_std_limit': g_th, 'accel_std_limit': a_th,
                                'ori_disp_limit': o_th, 'gravity_y_limit': gy_th,
                                'precision': prec, 'recall': rec, 'f1_score': f1,
                                'tp': tp, 'fp': fp, 'fn': fn
                            }
                            
        print(f"🏆 Best Global F1 Config (at least {k} conditions):")
        print(f"  * Gyro Std limit:      <{best_config['gyro_std_limit']:.2f} rad/s")
        print(f"  * Accel Std limit:     <{best_config['accel_std_limit']:.2f} m/s²")
        print(f"  * Ori Disp limit:      <{best_config['ori_disp_limit']:.2f} deg")
        print(f"  * Gravity Y limit:     <={best_config['gravity_y_limit']:.2f} m/s²")
        print(f"  -------------------------------------------------------------")
        print(f"  Precision:             {best_config['precision']:.1%}")
        print(f"  Recall:                {best_config['recall']:.1%}")
        print(f"  F1 Score:              {best_config['f1_score']:.4f}")
        print(f"  Conf Matrix (TP/FP/FN): {best_config['tp']}/{best_config['fp']}/{best_config['fn']}")

if __name__ == "__main__":
    main()
