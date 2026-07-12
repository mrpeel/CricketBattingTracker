import sys
import numpy as np
import pandas as pd
from sklearn.tree import DecisionTreeClassifier, export_text

sys.path.append("/Users/neilkloot/Code/CricketBattingTracker/pipelines")
import adversarial_facing_up_search

sys.path.append("/Users/neilkloot/Code/CricketBattingTracker/scratch")
import compare_facing_up_features

def main():
    sessions_base = "/Users/neilkloot/Code/Batting Sensor Stats/live_watch_sessions"
    all_sessions = adversarial_facing_up_search.load_all_sessions(sessions_base)
    
    dfs = []
    for s_path in all_sessions:
        shot_times, offset = adversarial_facing_up_search.load_shot_times(s_path)
        if len(shot_times) == 0:
            continue
        df = compare_facing_up_features.build_dataset_for_session(s_path, shot_times)
        if df is not None and len(df) > 0:
            dfs.append(df)
            
    merged_df = pd.concat(dfs, ignore_index=True)
    
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
    print("RULES FOR SEGMENT-BASED CLASSIFIER")
    print("==============================================================")
    print(rules)
    print("==============================================================")

if __name__ == "__main__":
    main()
