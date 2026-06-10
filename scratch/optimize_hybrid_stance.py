#!/usr/bin/env python3
"""
Hybrid Stance Gate Optimizer
============================
Performs a grid search over the hybrid "M of N" stance gate logic:
  - Steps count == 0 (mandatory)
  - Gyro Std < gyro_lim (mandatory)
  - At least K of:
    - Accel Std < accel_lim
    - Ori Disp < ori_lim
    - Gravity Y <= grav_y_lim
Finds the thresholds that maximize F1/F2 scores on the labeled session dataset.
"""

import sys
import os
import json
import numpy as np
import pandas as pd

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
    import datetime
    narration_files = [f for f in os.listdir(session_dir) if f.startswith("narration_") and f.endswith(".m4a")]
    if not narration_files:
        return 0.0
    fname = narration_files[0]
    parts = fname.replace("narration_", "").replace(".m4a", "")
    try:
        dt = datetime.datetime.strptime(parts, "%Y%m%d_%H%M%S")
        return dt.timestamp() - (int(open(os.path.join(session_dir, "latest_timeline.txt")).readline().split("Ts=")[1].strip()) / 1000.0)
    except:
        return 0.0

def calculate_quat_displacement(q_slice):
    if len(q_slice) < 2:
        return 0.0
    qx, qy, qz, qw = q_slice['qx'].values, q_slice['qy'].values, q_slice['qz'].values, q_slice['qw'].values
    dots = qx[:-1]*qx[1:] + qy[:-1]*qy[1:] + qz[:-1]*qz[1:] + qw[:-1]*qw[1:]
    dots = np.clip(np.abs(dots), -1.0, 1.0)
    return np.mean(np.degrees(2.0 * np.arccos(dots)))

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 optimize_hybrid_stance.py <session_dir>")
        sys.exit(1)
        
    session_dir = sys.argv[1]
    gyro, accel, gravity, orient, steps = load_sensor_data(session_dir)
    max_t = gyro['seconds_elapsed'].max()
    
    offset = get_offset(session_dir)
    narr_path = os.path.join(session_dir, "narrations_raw.json")
    with open(narr_path) as f:
        narrations = json.load(f)
        
    shot_times = [n['timestamp_seconds'] + offset for n in narrations 
                  if not any(term in n.get('shot_type', '').lower() for term in ['facing up', 'no shot', 'leave', 'evade'])]
                  
    # Define labels
    def check_labels(t):
        is_pos = False
        is_neg = True
        for st in shot_times:
            if (st - 3.5) <= t <= (st - 1.5):
                is_pos = True
            if abs(t - st) < 8.0:
                is_neg = False
        return 1 if is_pos else (0 if is_neg else -1)

    time_grid = np.arange(2.0, max_t - 2.0, 0.1)
    features_list = []
    labels_list = []
    
    gyro_t, gyro_mag = gyro['seconds_elapsed'].values, gyro['mag'].values
    accel_t, accel_mag = accel['seconds_elapsed'].values, accel['mag'].values
    grav_t, grav_y = gravity['seconds_elapsed'].values, gravity['y'].values
    ori_t = orient['seconds_elapsed'].values
    ori_qx, ori_qy, ori_qz, ori_qw = orient['qx'].values, orient['qy'].values, orient['qz'].values, orient['qw'].values
    step_times = steps['seconds_elapsed'].values if (steps is not None and len(steps) > 0) else np.array([])
    
    for t in time_grid:
        label = check_labels(t)
        if label == -1:
            continue
        w_start, w_end = t - 1.0, t
        feat = {'time': t}
        
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
        
        features_list.append(feat)
        labels_list.append(label)
        
    df_feat = pd.DataFrame(features_list)
    X = df_feat.drop(columns=['time'])
    y = np.array(labels_list)
    
    print(f"Extracted dataset size: {X.shape[0]} samples (Class 1: {np.sum(y == 1)}, Class 0: {np.sum(y == 0)})")
    
    # Grid Search over hybrid parameters
    # mandatory: steps == 0, gyro < gyro_lim
    # any 1 of: accel < accel_lim, ori < ori_lim, grav_y <= grav_y_lim
    g_grid = np.arange(0.7, 2.0, 0.1)
    a_grid = np.arange(1.0, 3.5, 0.25)
    o_grid = np.arange(1.0, 3.5, 0.25)
    gy_grid = np.arange(-9.0, -1.0, 0.5)
    
    for k in [1, 2]: # require at least k of accel, ori, grav_y to pass
        print(f"\n--- Optimizing for: Steps & Gyro Mandatory + at least {k} of Accel/Ori/Gravity ---")
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
                        
                        motion_passed = c_accel.astype(int) + c_ori.astype(int) + c_grav.astype(int)
                        
                        pred = (
                            (X['steps_count'] == 0) &
                            c_gyro &
                            (motion_passed >= k)
                        ).astype(int)
                        
                        tp = np.sum((pred == 1) & (y == 1))
                        fp = np.sum((pred == 1) & (y == 0))
                        fn = np.sum((pred == 0) & (y == 1))
                        tn = np.sum((pred == 0) & (y == 0))
                        
                        prec = tp / (tp + fp) if (tp + fp) > 0 else 0
                        rec = tp / (tp + fn) if (tp + fn) > 0 else 0
                        f1 = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0
                        
                        if f1 > best_f1:
                            best_f1 = f1
                            best_config = {
                                'gyro_std_limit': g_th, 'accel_std_limit': a_th,
                                'ori_disp_limit': o_th, 'gravity_y_limit': gy_th,
                                'precision': prec, 'recall': rec, 'f1_score': f1,
                                'tp': tp, 'fp': fp, 'fn': fn, 'tn': tn
                            }
                            
        print(f"🏆 Best F1 Config (any {k} of 3):")
        print(f"  * Gyro Std limit:      <{best_config['gyro_std_limit']:.2f} rad/s (Mandatory)")
        print(f"  * Accel Std limit:     <{best_config['accel_std_limit']:.2f} m/s²")
        print(f"  * Ori Disp limit:      <{best_config['ori_disp_limit']:.2f} deg")
        print(f"  * Gravity Y limit:     <={best_config['gravity_y_limit']:.2f} m/s²")
        print(f"  -------------------------------------------------------------")
        print(f"  Precision:             {best_config['precision']:.1%}")
        print(f"  Recall:                {best_config['recall']:.1%}")
        print(f"  F1 Score:              {best_config['f1_score']:.4f}")
        print(f"  Conf Matrix (TP/FP/FN/TN): {best_config['tp']}/{best_config['fp']}/{best_config['fn']}/{best_config['tn']}")

if __name__ == "__main__":
    main()
