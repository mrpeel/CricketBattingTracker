import sys
import numpy as np
import pandas as pd
from sklearn.tree import DecisionTreeClassifier, export_text

sys.path.append("/Users/neilkloot/Code/CricketBattingTracker/pipelines")
import adversarial_facing_up_search

sys.path.append("/Users/neilkloot/Code/CricketBattingTracker/scratch")
import compare_facing_up_features

def build_correct_dataset_for_session(session_dir, shot_times):
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
        
    precomputed = compare_facing_up_features.get_compare_precomputed_features(df_gyro, df_accel, df_grav, df_orient, df_steps)
    
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
        
        # Stance candidates features
        pit_gyro_std = precomputed['pit_gyro_std'][i]
        pit_accel_std = precomputed['pit_accel_std'][i]
        pit_ori_disp = precomputed['pit_ori_disp'][i]
        
        # We define "still" as low sensor variance
        is_still = (pit_gyro_std < 1.0 and pit_accel_std < 1.5 and pit_ori_disp < 1.0)
        
        row = (
            # Point-in-Time Features
            pit_gyro_std,
            pit_accel_std,
            pit_ori_disp,
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
        
        if is_pos:
            rows.append(row)
        elif is_neg and not is_still:
            # Only keep negative samples if they represent actual active movement wiggles
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
    
    dfs = []
    for s_path in all_sessions:
        shot_times, offset = adversarial_facing_up_search.load_shot_times(s_path)
        if len(shot_times) == 0:
            continue
        df = build_correct_dataset_for_session(s_path, shot_times)
        if df is not None and len(df) > 0:
            dfs.append(df)
            
    merged_df = pd.concat(dfs, ignore_index=True)
    print(f"Dataset compiled: {len(merged_df)} rows.")
    
    segment_features = [
        'seg1_gyro_std', 'seg1_accel_std', 'seg1_ori_disp', 'seg1_mean_grav_y',
        'seg2_gyro_std', 'seg2_accel_std', 'seg2_ori_disp', 'seg2_mean_grav_y',
        'step_age'
    ]
    
    X_seg = merged_df[segment_features].values
    y = merged_df['label'].values
    
    dt_seg = DecisionTreeClassifier(max_depth=4, random_state=42)
    dt_seg.fit(X_seg, y)
    
    rules = export_text(dt_seg, feature_names=segment_features)
    print("==============================================================")
    print("RULES FOR THE CORRECTED SEGMENT-BASED CLASSIFIER")
    print("==============================================================")
    print(rules)
    print("==============================================================")

if __name__ == "__main__":
    main()
