#!/usr/bin/env python3
"""
Stance Gate Threshold Optimization Tool
=======================================
Uses real ground-truth narration timestamps and watch sensor logs to:
  1. Label windows right before shots [T_impact - 3.5s, T_impact - 1.5s] as "Facing Up" (1).
  2. Label windows far from shots as "Rest/Walking/Admin" (0).
  3. Extract rolling features (std, mean, range) over 1s/500ms windows.
  4. Perform Random Forest Feature Importance to identify the most predictive signals.
  5. Run Grid Search over heuristic threshold limits to find the optimal F1 and F2 configurations.
  6. Evaluate additional sensor signals (Linear Acceleration, Magnetometer) for stance detection.
"""

import sys
import os
import json
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.tree import DecisionTreeClassifier, export_text

def load_sensor_data(session_dir):
    """Load all sensor CSVs and compute magnitudes."""
    gyro = pd.read_csv(os.path.join(session_dir, "WatchGyroscope.csv"))
    accel = pd.read_csv(os.path.join(session_dir, "WatchAccelerometer.csv"))
    gravity = pd.read_csv(os.path.join(session_dir, "WatchGravity.csv"))
    
    game_orient_path = os.path.join(session_dir, "WatchGameOrientation.csv")
    orient_path = os.path.join(session_dir, "WatchOrientation.csv")
    orient = pd.read_csv(game_orient_path) if os.path.exists(game_orient_path) else pd.read_csv(orient_path)
    
    steps_path = os.path.join(session_dir, "WatchSteps.csv")
    steps = pd.read_csv(steps_path) if os.path.exists(steps_path) else None
    
    linaccel_path = os.path.join(session_dir, "WatchLinearAcceleration.csv")
    linaccel = pd.read_csv(linaccel_path) if os.path.exists(linaccel_path) else None
    
    mag_path = os.path.join(session_dir, "WatchMagnetometer.csv")
    mag = pd.read_csv(mag_path) if os.path.exists(mag_path) else None

    # Compute magnitudes
    gyro['mag'] = np.sqrt(gyro['x']**2 + gyro['y']**2 + gyro['z']**2)
    accel['mag'] = np.sqrt(accel['x']**2 + accel['y']**2 + accel['z']**2)
    if linaccel is not None:
        linaccel['mag'] = np.sqrt(linaccel['x']**2 + linaccel['y']**2 + linaccel['z']**2)
    if mag is not None:
        mag['mag'] = np.sqrt(mag['x']**2 + mag['y']**2 + mag['z']**2)
        
    return gyro, accel, gravity, orient, steps, linaccel, mag

def get_offset(session_dir):
    """Calculate audio-to-sensor clock offset from metadata."""
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
    except Exception as e:
        print(f"⚠️ Could not calculate clock offset dynamically: {e}")
    return 0.0

def calculate_quat_displacement(q_slice):
    """Calculate mean angular displacement over orientation slice."""
    if len(q_slice) < 2:
        return 0.0
    qx = q_slice['qx'].values
    qy = q_slice['qy'].values
    qz = q_slice['qz'].values
    qw = q_slice['qw'].values
    dots = qx[:-1]*qx[1:] + qy[:-1]*qy[1:] + qz[:-1]*qz[1:] + qw[:-1]*qw[1:]
    dots = np.clip(np.abs(dots), -1.0, 1.0)
    angles = np.degrees(2.0 * np.arccos(dots))
    return np.mean(angles)

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 optimize_stance_gate.py <session_dir>")
        sys.exit(1)
        
    session_dir = sys.argv[1]
    session_name = os.path.basename(session_dir)
    
    print(f"\n{'='*80}")
    print(f"  STANCE GATE THRESHOLD OPTIMIZER")
    print(f"  Session: {session_name}")
    print(f"{'='*80}\n")
    
    # 1. Load data
    gyro, accel, gravity, orient, steps, linaccel, mag = load_sensor_data(session_dir)
    max_t = gyro['seconds_elapsed'].max()
    print(f"Session duration: {max_t:.1f}s ({max_t/60:.1f} min)")
    
    # 2. Get clock offset and load narrations
    offset = get_offset(session_dir)
    narr_path = os.path.join(session_dir, "narrations_raw.json")
    if not os.path.exists(narr_path):
        print(f"❌ Error: {narr_path} not found.")
        sys.exit(1)
        
    with open(narr_path) as f:
        narrations = json.load(f)
        
    # Extract actual swing-shot impact times in sensor timeline
    shot_times = []
    for n in narrations:
        st = n.get('shot_type', '')
        if any(term in st.lower() for term in ['facing up', 'no shot', 'leave', 'evade']):
            continue
        shot_times.append(n['timestamp_seconds'] + offset)
        
    print(f"Narrated swing-type shots: {len(shot_times)}")
    print(f"Clock offset: {offset:+.3f}s")
    
    # 3. Labeling functions
    # Positive label: 3.5s to 1.5s before a shot (guard stance)
    # Negative label: > 8s away from any shot impact (rest / walking / break)
    def check_labels(t):
        is_pos = False
        is_neg = True
        for st in shot_times:
            if (st - 3.5) <= t <= (st - 1.5):
                is_pos = True
            if abs(t - st) < 8.0:
                is_neg = False
        if is_pos:
            return 1
        elif is_neg:
            return 0
        else:
            return -1 # Discard transition periods
            
    # 4. Feature Extraction over sliding grid (100ms step)
    print("\nExtracting rolling features and labeling training dataset...")
    time_grid = np.arange(2.0, max_t - 2.0, 0.1)
    
    features_list = []
    labels_list = []
    
    gyro_t = gyro['seconds_elapsed'].values
    gyro_mag = gyro['mag'].values
    accel_t = accel['seconds_elapsed'].values
    accel_mag = accel['mag'].values
    grav_t = gravity['seconds_elapsed'].values
    grav_y = gravity['y'].values
    grav_z = gravity['z'].values
    ori_t = orient['seconds_elapsed'].values
    ori_qx = orient['qx'].values
    ori_qy = orient['qy'].values
    ori_qz = orient['qz'].values
    ori_qw = orient['qw'].values
    
    step_times = steps['seconds_elapsed'].values if (steps is not None and len(steps) > 0) else np.array([])
    lin_t = linaccel['seconds_elapsed'].values if linaccel is not None else np.array([])
    lin_mag = linaccel['mag'].values if linaccel is not None else np.array([])
    mag_t = mag['seconds_elapsed'].values if mag is not None else np.array([])
    mag_mag = mag['mag'].values if mag is not None else np.array([])
    
    for t in time_grid:
        label = check_labels(t)
        if label == -1:
            continue
            
        w_start = t - 1.0
        w_end = t
        
        feat = {'time': t}
        
        # Gyro features (1.0s window)
        mask_g = (gyro_t >= w_start) & (gyro_t <= w_end)
        if mask_g.sum() >= 2:
            feat['gyro_std'] = np.std(gyro_mag[mask_g], ddof=0)
            feat['gyro_mean'] = np.mean(gyro_mag[mask_g])
        else:
            feat['gyro_std'] = 0.0
            feat['gyro_mean'] = 0.0
            
        # Accel features (1.0s window)
        mask_a = (accel_t >= w_start) & (accel_t <= w_end)
        if mask_a.sum() >= 2:
            feat['accel_std'] = np.std(accel_mag[mask_a], ddof=0)
            feat['accel_mean'] = np.mean(accel_mag[mask_a])
        else:
            feat['accel_std'] = 0.0
            feat['accel_mean'] = 0.0
            
        # Gravity features (1.0s window)
        mask_gr = (grav_t >= w_start) & (grav_t <= w_end)
        if mask_gr.sum() > 0:
            feat['gravity_y_mean'] = np.mean(grav_y[mask_gr])
            feat['gravity_z_mean'] = np.mean(grav_z[mask_gr])
        else:
            feat['gravity_y_mean'] = -9.8
            feat['gravity_z_mean'] = 0.0
            
        # Orientation features (500ms window)
        mask_o = (ori_t >= t - 0.5) & (ori_t <= t)
        if mask_o.sum() >= 2:
            idx = np.where(mask_o)[0]
            qx_slice = pd.DataFrame({
                'qx': ori_qx[idx], 'qy': ori_qy[idx], 
                'qz': ori_qz[idx], 'qw': ori_qw[idx]
            })
            feat['ori_disp_mean'] = calculate_quat_displacement(qx_slice)
        else:
            feat['ori_disp_mean'] = 999.0
            
        # Steps count (2.0s recency window)
        if len(step_times) > 0:
            feat['steps_count'] = np.sum((step_times >= t - 2.0) & (step_times <= t))
        else:
            feat['steps_count'] = 0
            
        # Optional: Linear Acceleration (1.0s window)
        if len(lin_t) > 0:
            mask_l = (lin_t >= w_start) & (lin_t <= w_end)
            if mask_l.sum() >= 2:
                feat['linaccel_std'] = np.std(lin_mag[mask_l], ddof=0)
                feat['linaccel_mean'] = np.mean(lin_mag[mask_l])
            else:
                feat['linaccel_std'] = 0.0
                feat['linaccel_mean'] = 0.0
        else:
            feat['linaccel_std'] = 0.0
            feat['linaccel_mean'] = 0.0
            
        # Optional: Magnetometer magnitude (1.0s window)
        if len(mag_t) > 0:
            mask_m = (mag_t >= w_start) & (mag_t <= w_end)
            if mask_m.sum() >= 2:
                feat['mag_std'] = np.std(mag_mag[mask_m], ddof=0)
                feat['mag_mean'] = np.mean(mag_mag[mask_m])
            else:
                feat['mag_std'] = 0.0
                feat['mag_mean'] = 0.0
        else:
            feat['mag_std'] = 0.0
            feat['mag_mean'] = 0.0
            
        features_list.append(feat)
        labels_list.append(label)
        
    df_feat = pd.DataFrame(features_list)
    X = df_feat.drop(columns=['time'])
    y = np.array(labels_list)
    
    print(f"Extracted dataset size: {X.shape[0]} samples.")
    print(f"  Class 1 (Facing Up): {np.sum(y == 1)} samples ({100*np.sum(y==1)/len(y):.1f}%)")
    print(f"  Class 0 (Rest/Walk): {np.sum(y == 0)} samples ({100*np.sum(y==0)/len(y):.1f}%)")
    
    # 5. Random Forest Feature Importance Analysis
    rf = RandomForestClassifier(n_estimators=100, random_state=42)
    rf.fit(X, y)
    
    importances = pd.Series(rf.feature_importances_, index=X.columns).sort_values(ascending=False)
    print("\n" + "="*80)
    print("  RANDOM FOREST FEATURE IMPORTANCES (FOR STANCE DISCRIMINATION)")
    print("="*80)
    print(importances.to_string())
    
    # 6. Decision Tree for Rules Extraction
    dt = DecisionTreeClassifier(max_depth=3, random_state=42)
    dt.fit(X, y)
    print("\n" + "="*80)
    print("  EXTRACTED DECISION TREE RULES (Depth=3)")
    print("="*80)
    print(export_text(dt, feature_names=list(X.columns)))
    
    # 7. Grid Search over heuristic thresholds
    print("\n" + "="*80)
    print("  HEURISTIC THRESHOLD BOUNDS GRID SEARCH")
    print("="*80)
    print("Optimizing combination of: gyro_std, accel_std, ori_disp_mean, gravity_y_mean")
    print("(Steps count is strictly enforced to be 0)")
    
    # Define grid search limits based on feature distributions
    g_grid = np.arange(0.5, 2.5, 0.1)     # Gyro Std limit
    a_grid = np.arange(1.0, 4.5, 0.25)    # Accel Std limit
    o_grid = np.arange(1.0, 4.5, 0.25)    # Ori Disp limit
    gy_grid = np.arange(-9.0, -1.0, 0.5)  # Gravity Y limit (<=)
    
    best_f1 = 0.0
    best_f1_config = None
    
    best_f2 = 0.0
    best_f2_config = None
    
    for g_th in g_grid:
        for a_th in a_grid:
            for o_th in o_grid:
                for gy_th in gy_grid:
                    # Enforce steps count = 0 as mandatory walking kill switch
                    pred = (
                        (X['gyro_std'] < g_th) &
                        (X['accel_std'] < a_th) &
                        (X['ori_disp_mean'] < o_th) &
                        (X['gravity_y_mean'] <= gy_th) &
                        (X['steps_count'] == 0)
                    ).astype(int)
                    
                    tp = np.sum((pred == 1) & (y == 1))
                    fp = np.sum((pred == 1) & (y == 0))
                    fn = np.sum((pred == 0) & (y == 1))
                    tn = np.sum((pred == 0) & (y == 0))
                    
                    prec = tp / (tp + fp) if (tp + fp) > 0 else 0
                    rec = tp / (tp + fn) if (tp + fn) > 0 else 0
                    
                    # F1 Score
                    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0
                    # F2 Score (Recall is twice as important as Precision)
                    f2 = 5 * prec * rec / (4 * prec + rec) if (4 * prec + rec) > 0 else 0
                    
                    if f1 > best_f1:
                        best_f1 = f1
                        best_f1_config = {
                            'gyro_std_limit': g_th, 'accel_std_limit': a_th,
                            'ori_disp_limit': o_th, 'gravity_y_limit': gy_th,
                            'precision': prec, 'recall': rec, 'f1_score': f1,
                            'tp': tp, 'fp': fp, 'fn': fn, 'tn': tn
                        }
                    
                    if f2 > best_f2:
                        best_f2 = f2
                        best_f2_config = {
                            'gyro_std_limit': g_th, 'accel_std_limit': a_th,
                            'ori_disp_limit': o_th, 'gravity_y_limit': gy_th,
                            'precision': prec, 'recall': rec, 'f2_score': f2,
                            'tp': tp, 'fp': fp, 'fn': fn, 'tn': tn
                        }
                        
    print("\n🏆 OPTIMAL CONFIGURATION FOR F1 SCORE (Balanced Precision/Recall):")
    print(f"  * Gyro Std limit:      <{best_f1_config['gyro_std_limit']:.2f} rad/s")
    print(f"  * Accel Std limit:     <{best_f1_config['accel_std_limit']:.2f} m/s²")
    print(f"  * Ori Disp limit:      <{best_f1_config['ori_disp_limit']:.2f} deg")
    print(f"  * Gravity Y limit:     <={best_f1_config['gravity_y_limit']:.2f} m/s²")
    print(f"  -------------------------------------------------------------")
    print(f"  Precision:             {best_f1_config['precision']:.1%}")
    print(f"  Recall:                {best_f1_config['recall']:.1%}")
    print(f"  F1 Score:              {best_f1_config['f1_score']:.4f}")
    print(f"  Conf Matrix (TP/FP/FN/TN): {best_f1_config['tp']}/{best_f1_config['fp']}/{best_f1_config['fn']}/{best_f1_config['tn']}")
    
    print("\n🏆 OPTIMAL CONFIGURATION FOR F2 SCORE (Prioritizing Recall):")
    print(f"  * Gyro Std limit:      <{best_f2_config['gyro_std_limit']:.2f} rad/s")
    print(f"  * Accel Std limit:     <{best_f2_config['accel_std_limit']:.2f} m/s²")
    print(f"  * Ori Disp limit:      <{best_f2_config['ori_disp_limit']:.2f} deg")
    print(f"  * Gravity Y limit:     <={best_f2_config['gravity_y_limit']:.2f} m/s²")
    print(f"  -------------------------------------------------------------")
    print(f"  Precision:             {best_f2_config['precision']:.1%}")
    print(f"  Recall:                {best_f2_config['recall']:.1%}")
    print(f"  F2 Score:              {best_f2_config['f2_score']:.4f}")
    print(f"  Conf Matrix (TP/FP/FN/TN): {best_f2_config['tp']}/{best_f2_config['fp']}/{best_f2_config['fn']}/{best_f2_config['tn']}")

    # 8. Evaluate sensor extensions
    print("\n" + "="*80)
    print("  EVALUATING ALTERNATIVE SENSOR EXTENSIONS")
    print("="*80)
    
    # Try adding Linear Acceleration std to F1-optimal config
    best_f1_lin = 0.0
    best_lin_val = 0.0
    best_lin_metrics = None
    
    for lin_th in np.arange(0.1, 2.5, 0.1):
        pred = (
            (X['gyro_std'] < best_f1_config['gyro_std_limit']) &
            (X['accel_std'] < best_f1_config['accel_std_limit']) &
            (X['ori_disp_mean'] < best_f1_config['ori_disp_limit']) &
            (X['gravity_y_mean'] <= best_f1_config['gravity_y_limit']) &
            (X['linaccel_std'] < lin_th) &
            (X['steps_count'] == 0)
        ).astype(int)
        
        tp = np.sum((pred == 1) & (y == 1))
        fp = np.sum((pred == 1) & (y == 0))
        fn = np.sum((pred == 0) & (y == 1))
        
        prec = tp / (tp + fp) if (tp + fp) > 0 else 0
        rec = tp / (tp + fn) if (tp + fn) > 0 else 0
        f1 = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0
        
        if f1 > best_f1_lin:
            best_f1_lin = f1
            best_lin_val = lin_th
            best_lin_metrics = {'precision': prec, 'recall': rec, 'f1': f1}
            
    if best_lin_metrics:
        diff_f1 = best_lin_metrics['f1'] - best_f1_config['f1_score']
        print(f"Adding Linear Acceleration Std limit (linaccel_std < {best_lin_val:.2f} m/s²):")
        print(f"  F1 Score:  {best_lin_metrics['f1']:.4f} (Diff vs baseline: {diff_f1:+.4f})")
        print(f"  Precision: {best_lin_metrics['precision']:.1%}, Recall: {best_lin_metrics['recall']:.1%}")
    else:
        print("Linear acceleration data not available/not evaluated.")
        
    # Try adding Magnetometer magnitude std to F1-optimal config
    best_f1_mag = 0.0
    best_mag_val = 0.0
    best_mag_metrics = None
    
    for mag_th in np.arange(0.1, 5.0, 0.2):
        pred = (
            (X['gyro_std'] < best_f1_config['gyro_std_limit']) &
            (X['accel_std'] < best_f1_config['accel_std_limit']) &
            (X['ori_disp_mean'] < best_f1_config['ori_disp_limit']) &
            (X['gravity_y_mean'] <= best_f1_config['gravity_y_limit']) &
            (X['mag_std'] < mag_th) &
            (X['steps_count'] == 0)
        ).astype(int)
        
        tp = np.sum((pred == 1) & (y == 1))
        fp = np.sum((pred == 1) & (y == 0))
        fn = np.sum((pred == 0) & (y == 1))
        
        prec = tp / (tp + fp) if (tp + fp) > 0 else 0
        rec = tp / (tp + fn) if (tp + fn) > 0 else 0
        f1 = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0
        
        if f1 > best_f1_mag:
            best_f1_mag = f1
            best_mag_val = mag_th
            best_mag_metrics = {'precision': prec, 'recall': rec, 'f1': f1}
            
    if best_mag_metrics:
        diff_f1_mag = best_mag_metrics['f1'] - best_f1_config['f1_score']
        print(f"Adding Magnetometer Std limit (mag_std < {best_mag_val:.2f} uT):")
        print(f"  F1 Score:  {best_mag_metrics['f1']:.4f} (Diff vs baseline: {diff_f1_mag:+.4f})")
        print(f"  Precision: {best_mag_metrics['precision']:.1%}, Recall: {best_mag_metrics['recall']:.1%}")
    else:
        print("Magnetometer data not available/not evaluated.")

if __name__ == "__main__":
    main()
