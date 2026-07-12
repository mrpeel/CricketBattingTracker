#!/usr/bin/env python3
import os
import sys
import numpy as np
import pandas as pd
from sklearn.tree import DecisionTreeClassifier
from sklearn.model_selection import KFold
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score

# Add pipelines to python path
sys.path.append("/Users/neilkloot/Code/CricketBattingTracker/pipelines")
import adversarial_facing_up_search

def get_compare_precomputed_features(df_gyro, df_accel, df_grav, df_orient, df_steps):
    df_gyro = df_gyro.copy()
    df_accel = df_accel.copy()
    df_gyro['mag'] = np.sqrt(df_gyro['x']**2 + df_gyro['y']**2 + df_gyro['z']**2)
    df_accel['mag'] = np.sqrt(df_accel['x']**2 + df_accel['y']**2 + df_accel['z']**2)
    
    gyro_t = df_gyro['seconds_elapsed'].values
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
    
    pit_gyro_std = np.zeros(n_samples)
    pit_accel_std = np.zeros(n_samples)
    pit_mean_grav_y = np.zeros(n_samples)
    pit_ori_disp = np.zeros(n_samples)
    
    seg1_gyro_std = np.zeros(n_samples)
    seg1_accel_std = np.zeros(n_samples)
    seg1_mean_grav_y = np.zeros(n_samples)
    seg1_ori_disp = np.zeros(n_samples)
    
    seg2_gyro_std = np.zeros(n_samples)
    seg2_accel_std = np.zeros(n_samples)
    seg2_mean_grav_y = np.zeros(n_samples)
    seg2_ori_disp = np.zeros(n_samples)
    
    step_age = np.zeros(n_samples)
    
    # Compute orientation displacements
    dots = orient_qx[:-1]*orient_qx[1:] + orient_qy[:-1]*orient_qy[1:] + orient_qz[:-1]*orient_qz[1:] + orient_qw[:-1]*orient_qw[1:]
    dots = np.clip(np.abs(dots), -1.0, 1.0)
    angles = np.degrees(2.0 * np.arccos(dots))
    angles = np.insert(angles, 0, 0.0)
    
    for i in range(n_samples):
        t = gyro_t[i]
        
        # Step Age
        if len(step_t) > 0:
            idx = np.searchsorted(step_t, t, side='right')
            if idx > 0:
                step_age[i] = t - step_t[idx - 1]
            else:
                step_age[i] = 999.0
        else:
            step_age[i] = 999.0
            
        # Point-in-Time (Baseline)
        g_start = t - 1.0
        g_start_idx = np.searchsorted(gyro_t, g_start)
        pit_gyro_std[i] = np.std(gyro_mag[g_start_idx:i+1]) if (i+1 - g_start_idx) >= 2 else 0.0
        
        a_start_idx = np.searchsorted(accel_t, g_start)
        a_end_idx = np.searchsorted(accel_t, t, side='right')
        pit_accel_std[i] = np.std(accel_mag[a_start_idx:a_end_idx]) if (a_end_idx - a_start_idx) >= 2 else 0.0
        
        gr_start_idx = np.searchsorted(grav_t, g_start)
        gr_end_idx = np.searchsorted(grav_t, t, side='right')
        pit_mean_grav_y[i] = np.mean(grav_y[gr_start_idx:gr_end_idx]) if (gr_end_idx - gr_start_idx) >= 2 else 0.0
        
        o_start = t - 0.5
        o_start_idx = np.searchsorted(orient_t, o_start)
        o_end_idx = np.searchsorted(orient_t, t, side='right')
        pit_ori_disp[i] = np.mean(angles[o_start_idx:o_end_idx]) if (o_end_idx - o_start_idx) >= 2 else 0.0
        
        # Segment 1 [-2.0s, -1.0s]
        s1_start = t - 2.0
        s1_end = t - 1.0
        
        s1_g_start_idx = np.searchsorted(gyro_t, s1_start)
        s1_g_end_idx = np.searchsorted(gyro_t, s1_end, side='right')
        seg1_gyro_std[i] = np.std(gyro_mag[s1_g_start_idx:s1_g_end_idx]) if (s1_g_end_idx - s1_g_start_idx) >= 2 else 0.0
        
        s1_a_start_idx = np.searchsorted(accel_t, s1_start)
        s1_a_end_idx = np.searchsorted(accel_t, s1_end, side='right')
        seg1_accel_std[i] = np.std(accel_mag[s1_a_start_idx:s1_a_end_idx]) if (s1_a_end_idx - s1_a_start_idx) >= 2 else 0.0
        
        s1_gr_start_idx = np.searchsorted(grav_t, s1_start)
        s1_gr_end_idx = np.searchsorted(grav_t, s1_end, side='right')
        seg1_mean_grav_y[i] = np.mean(grav_y[s1_gr_start_idx:s1_gr_end_idx]) if (s1_gr_end_idx - s1_gr_start_idx) >= 2 else 0.0
        
        s1_o_start_idx = np.searchsorted(orient_t, s1_start)
        s1_o_end_idx = np.searchsorted(orient_t, s1_end, side='right')
        seg1_ori_disp[i] = np.mean(angles[s1_o_start_idx:s1_o_end_idx]) if (s1_o_end_idx - s1_o_start_idx) >= 2 else 0.0
        
        # Segment 2 [-1.0s, 0.0s]
        seg2_gyro_std[i] = pit_gyro_std[i]
        seg2_accel_std[i] = pit_accel_std[i]
        seg2_mean_grav_y[i] = pit_mean_grav_y[i]
        
        s2_o_start_idx = np.searchsorted(orient_t, g_start)
        seg2_ori_disp[i] = np.mean(angles[s2_o_start_idx:o_end_idx]) if (o_end_idx - s2_o_start_idx) >= 2 else 0.0

    return {
        'pit_gyro_std': pit_gyro_std,
        'pit_accel_std': pit_accel_std,
        'pit_mean_grav_y': pit_mean_grav_y,
        'pit_ori_disp': pit_ori_disp,
        'seg1_gyro_std': seg1_gyro_std,
        'seg1_accel_std': seg1_accel_std,
        'seg1_mean_grav_y': seg1_mean_grav_y,
        'seg1_ori_disp': seg1_ori_disp,
        'seg2_gyro_std': seg2_gyro_std,
        'seg2_accel_std': seg2_accel_std,
        'seg2_mean_grav_y': seg2_mean_grav_y,
        'seg2_ori_disp': seg2_ori_disp,
        'step_age': step_age
    }

def build_dataset_for_session(session_dir, shot_times):
    adversarial_facing_up_search.apply_stance_stress_to_session_cache(session_dir, shot_times)
    
    df_gyro = adversarial_facing_up_search.load_parquet_or_csv(session_dir, "gyro")
    df_accel = adversarial_facing_up_search.load_parquet_or_csv(session_dir, "accel")
    df_grav = adversarial_facing_up_search.load_parquet_or_csv(session_dir, "gravity")
    df_orient = adversarial_facing_up_search.load_parquet_or_csv(session_dir, "game_orient")
    if df_orient is None:
        df_orient = adversarial_facing_up_search.load_parquet_or_csv(session_dir, "orient")
    df_steps = adversarial_facing_up_search.load_parquet_or_csv(session_dir, "steps")
    
    if df_gyro is None or df_accel is None or df_grav is None:
        return None
        
    precomputed = get_compare_precomputed_features(df_gyro, df_accel, df_grav, df_orient, df_steps)
    
    times = df_gyro['seconds_elapsed'].values
    
    rows = []
    for i, t in enumerate(times):
        is_pos = False
        is_neg = True
        for st in shot_times:
            if (st - 3.5) <= t <= (st - 1.5):
                is_pos = True
            if abs(t - st) < 8.0:
                is_neg = False
        
        sa = min(precomputed['step_age'][i], 10.0)
        
        row = (
            # Point-in-Time Features
            precomputed['pit_gyro_std'][i],
            precomputed['pit_accel_std'][i],
            precomputed['pit_ori_disp'][i],
            precomputed['pit_mean_grav_y'][i],
            # Segment 1 Features
            precomputed['seg1_gyro_std'][i],
            precomputed['seg1_accel_std'][i],
            precomputed['seg1_ori_disp'][i],
            precomputed['seg1_mean_grav_y'][i],
            # Segment 2 Features
            precomputed['seg2_gyro_std'][i],
            precomputed['seg2_accel_std'][i],
            precomputed['seg2_ori_disp'][i],
            precomputed['seg2_mean_grav_y'][i],
            # Step age
            sa,
            1 if is_pos else 0
        )
        if is_pos or is_neg:
            rows.append(row)
            
    cols = [
        'pit_gyro_std', 'pit_accel_std', 'pit_ori_disp', 'pit_mean_grav_y',
        'seg1_gyro_std', 'seg1_accel_std', 'seg1_ori_disp', 'seg1_mean_grav_y',
        'seg2_gyro_std', 'seg2_accel_std', 'seg2_ori_disp', 'seg2_mean_grav_y',
        'step_age', 'label'
    ]
    return pd.DataFrame(rows, columns=cols)

def main():
    sessions_base = "/Users/neilkloot/Code/Batting Sensor Stats/live_watch_sessions"
    all_sessions = adversarial_facing_up_search.load_all_sessions(sessions_base)
    
    print(f"Loading and compiling stance features across {len(all_sessions)} sessions...")
    dfs = []
    for s_path in all_sessions:
        shot_times, offset = adversarial_facing_up_search.load_shot_times(s_path)
        if len(shot_times) == 0:
            continue
        df = build_dataset_for_session(s_path, shot_times)
        if df is not None and len(df) > 0:
            dfs.append(df)
            
    if not dfs:
        print("❌ Error: No datasets could be built.")
        sys.exit(1)
        
    merged_df = pd.concat(dfs, ignore_index=True)
    print(f"Total samples compiled: {len(merged_df)} ({merged_df['label'].sum()} positive, {(merged_df['label'] == 0).sum()} negative)")
    
    # Define feature groups
    pit_features = ['pit_gyro_std', 'pit_accel_std', 'pit_ori_disp', 'pit_mean_grav_y', 'step_age']
    segment_features = [
        'seg1_gyro_std', 'seg1_accel_std', 'seg1_ori_disp', 'seg1_mean_grav_y',
        'seg2_gyro_std', 'seg2_accel_std', 'seg2_ori_disp', 'seg2_mean_grav_y',
        'step_age'
    ]
    
    # 5-fold cross-validation
    kf = KFold(n_splits=5, shuffle=True, random_state=42)
    
    pit_metrics = {'acc': [], 'prec': [], 'rec': [], 'f1': []}
    seg_metrics = {'acc': [], 'prec': [], 'rec': [], 'f1': []}
    
    X_pit = merged_df[pit_features].values
    X_seg = merged_df[segment_features].values
    y = merged_df['label'].values
    
    # Depth 4 Decision Trees (TinyML friendly)
    dt_pit = DecisionTreeClassifier(max_depth=4, random_state=42)
    dt_seg = DecisionTreeClassifier(max_depth=4, random_state=42)
    
    for train_idx, test_idx in kf.split(X_pit):
        # PIT
        dt_pit.fit(X_pit[train_idx], y[train_idx])
        y_pred_pit = dt_pit.predict(X_pit[test_idx])
        pit_metrics['acc'].append(accuracy_score(y[test_idx], y_pred_pit))
        pit_metrics['prec'].append(precision_score(y[test_idx], y_pred_pit, zero_division=0))
        pit_metrics['rec'].append(recall_score(y[test_idx], y_pred_pit, zero_division=0))
        pit_metrics['f1'].append(f1_score(y[test_idx], y_pred_pit, zero_division=0))
        
        # Segment
        dt_seg.fit(X_seg[train_idx], y[train_idx])
        y_pred_seg = dt_seg.predict(X_seg[test_idx])
        seg_metrics['acc'].append(accuracy_score(y[test_idx], y_pred_seg))
        seg_metrics['prec'].append(precision_score(y[test_idx], y_pred_seg, zero_division=0))
        seg_metrics['rec'].append(recall_score(y[test_idx], y_pred_seg, zero_division=0))
        seg_metrics['f1'].append(f1_score(y[test_idx], y_pred_seg, zero_division=0))
        
    print("\n==============================================================")
    print("📊 CLASSIFICATION PERFORMANCE COMPARISON (5-Fold CV)")
    print("==============================================================")
    print(f"Point-in-Time (PIT) - Accuracy:  {np.mean(pit_metrics['acc']):.2%}")
    print(f"Point-in-Time (PIT) - Precision: {np.mean(pit_metrics['prec']):.2%}")
    print(f"Point-in-Time (PIT) - Recall:    {np.mean(pit_metrics['rec']):.2%}")
    print(f"Point-in-Time (PIT) - F1 Score:  {np.mean(pit_metrics['f1']):.4f}")
    print("--------------------------------------------------------------")
    print(f"Segment-Based       - Accuracy:  {np.mean(seg_metrics['acc']):.2%}")
    print(f"Segment-Based       - Precision: {np.mean(seg_metrics['prec']):.2%}")
    print(f"Segment-Based       - Recall:    {np.mean(seg_metrics['rec']):.2%}")
    print(f"Segment-Based       - F1 Score:  {np.mean(seg_metrics['f1']):.4f}")
    print("==============================================================\n")
    
    # Train final estimators on the full set to show rules
    dt_pit.fit(X_pit, y)
    dt_seg.fit(X_seg, y)
    
    # Write the report
    report_path = "/Users/neilkloot/Code/CricketBattingTracker/facing_up_feature_comparison.md"
    print(f"Writing comparison report to {report_path}...")
    with open(report_path, "w") as f:
        f.write("# Stance Gate Feature Extraction Comparison Report\n\n")
        f.write("This report evaluates the accuracy of **Segment-Based Feature Extraction** (partitioning the last 2.0s history window into multiple segments) vs **Point-in-Time (PIT) Feature Extraction** (evaluating features over a single 1.0s/0.5s window ending at time `t`) for the Wear OS smartwatch stance gate.\n\n")
        
        f.write("## 1. Feature Representation\n\n")
        f.write("- **Point-in-Time (Baseline)**:\n")
        f.write("  - `gyro_std` (std of gyro magnitude over the last 1.0s)\n")
        f.write("  - `accel_std` (std of accel magnitude over the last 1.0s)\n")
        f.write("  - `mean_grav_y` (mean gravity y over the last 1.0s)\n")
        f.write("  - `ori_disp` (mean orientation displacement over the last 0.5s)\n")
        f.write("  - `step_age` (time elapsed since last pedometer step)\n\n")
        
        f.write("- **Segment-Based (Proposed)**:\n")
        f.write("  - **Segment 1** (`[-2.0s, -1.0s]`): std of gyro, std of accel, mean gravity y, mean orientation displacement.\n")
        f.write("  - **Segment 2** (`[-1.0s, 0.0s]`): std of gyro, std of accel, mean gravity y, mean orientation displacement.\n")
        f.write("  - `step_age` (time elapsed since last pedometer step)\n\n")
        
        f.write("## 2. Classification Metrics (5-Fold Cross-Validation)\n\n")
        f.write("| Feature Extraction Method | CV Accuracy | CV Precision | CV Recall | CV F1 Score |\n")
        f.write("|---|---|---|---|---|\n")
        f.write(f"| Point-in-Time (PIT, Current) | {np.mean(pit_metrics['acc']):.2%} | {np.mean(pit_metrics['prec']):.2%} | {np.mean(pit_metrics['rec']):.2%} | {np.mean(pit_metrics['f1']):.4f} |\n")
        f.write(f"| Segment-Based (Proposed) | {np.mean(seg_metrics['acc']):.2%} | {np.mean(seg_metrics['prec']):.2%} | {np.mean(seg_metrics['rec']):.2%} | {np.mean(seg_metrics['f1']):.4f} |\n\n")
        
        f.write("## 3. Analysis & Recommendation\n\n")
        f1_diff = np.mean(seg_metrics['f1']) - np.mean(pit_metrics['f1'])
        if f1_diff > 0.005:
            f.write(f"✅ **Segment-Based feature extraction yields a +{f1_diff:.4f} F1-score improvement.**\n\n")
            f.write("By dividing the 2.0-second window into two segments, the model successfully captures the temporal transition from movement to stillness (and vice versa). This helps prevent wiggles, walks, and waddles from triggering the stance gate, while maintaining high recall during genuine stances.\n")
        elif abs(f1_diff) <= 0.005:
            f.write(f"⚪ **Both feature extraction methods perform similarly (F1 difference = {f1_diff:.4f}).**\n\n")
            f.write("The point-in-time features perform comparably to the segment-based approach on the stressed dataset, with segment features showing no substantial accuracy gains.\n")
        else:
            f.write(f"❌ **Point-in-Time feature extraction performs better by {abs(f1_diff):.4f} F1-score.**\n\n")
            f.write("Point-in-time features provide sufficient signal, and segment-based features introduce unnecessary dimensionality or noise that degrades the depth-4 Decision Tree performance.\n")

if __name__ == "__main__":
    main()
