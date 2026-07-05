import os
import sys
import numpy as np
import pandas as pd
from sklearn.tree import DecisionTreeClassifier, export_text

sys.path.append("/Users/neilkloot/Code/CricketBattingTracker/pipelines")
import adversarial_facing_up_search

def build_stressed_stance_dataset(session_dir, shot_times):
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
        
    precomputed = adversarial_facing_up_search.get_precomputed_features(df_gyro, df_accel, df_grav, df_orient, df_steps)
    
    times = df_gyro['seconds_elapsed'].values
    gyro_std = precomputed['gyro_std']
    accel_std = precomputed['accel_std']
    mean_grav_y = precomputed['mean_grav_y']
    ori_disp = precomputed['ori_disp']
    step_age = precomputed['step_age'] / 1e9  # convert back to seconds
    
    rows = []
    for i, t in enumerate(times):
        is_pos = False
        is_neg = True
        for st in shot_times:
            if (st - 3.5) <= t <= (st - 1.5):
                is_pos = True
            if abs(t - st) < 8.0:
                is_neg = False
        
        sa = min(step_age[i], 10.0)
        
        if is_pos:
            rows.append((gyro_std[i], accel_std[i], ori_disp[i], mean_grav_y[i], sa, 1))
        elif is_neg:
            rows.append((gyro_std[i], accel_std[i], ori_disp[i], mean_grav_y[i], sa, 0))
            
    return pd.DataFrame(rows, columns=['gyro_std', 'accel_std', 'ori_disp', 'mean_grav_y', 'step_age', 'label'])

def generate_python_code(tree, feature_names):
    """
    Generate Python if-else nested function from sklearn DecisionTree.
    """
    tree_ = tree.tree_
    feature_name = [
        feature_names[i] if i != -2 else "undefined!"
        for i in tree_.feature
    ]
    
    lines = []
    lines.append("def predict_stance(gyro_std, accel_std, ori_disp, mean_grav_y, step_age):")
    
    def recurse(node, depth):
        indent = "    " * (depth + 1)
        if tree_.feature[node] != -2:
            name = feature_name[node]
            threshold = tree_.threshold[node]
            lines.append(f"{indent}if {name} <= {threshold:.6f}:")
            recurse(tree_.children_left[node], depth + 1)
            lines.append(f"{indent}else:")
            recurse(tree_.children_right[node], depth + 1)
        else:
            # Leaf node: get class probabilities
            values = tree_.value[node][0]
            stance_prob = values[1] / sum(values) if sum(values) > 0 else 0.0
            # Predict stance (1) if prob > 0.5
            pred = 1 if stance_prob > 0.5 else 0
            lines.append(f"{indent}return {pred}")
            
    recurse(0, 0)
    return "\n".join(lines) + "\n"

def main():
    sessions_base = "/Users/neilkloot/Code/Batting Sensor Stats/live_watch_sessions"
    all_sessions = adversarial_facing_up_search.load_all_sessions(sessions_base)
    
    print(f"Loading and compiling stance features across {len(all_sessions)} sessions...")
    dfs = []
    for s_path in all_sessions:
        shot_times, offset = adversarial_facing_up_search.load_shot_times(s_path)
        if len(shot_times) == 0:
            continue
        df = build_stressed_stance_dataset(s_path, shot_times)
        if df is not None and len(df) > 0:
            dfs.append(df)
            
    if not dfs:
        print("Error: No stance data compiled.")
        return
        
    combined_df = pd.concat(dfs, ignore_index=True)
    print(f"Dataset compiled successfully. Total rows: {len(combined_df)}")
    print(f"Class distribution: Stance(1)={combined_df['label'].sum()}, Fidget/NoStance(0)={len(combined_df) - combined_df['label'].sum()}")
    
    # Train shallow DecisionTreeClassifier
    feature_cols = ['gyro_std', 'accel_std', 'ori_disp', 'mean_grav_y', 'step_age']
    X = combined_df[feature_cols].fillna(0.0)
    y = combined_df['label']
    
    # max_depth=4 keeps tree simple enough to easily write in Kotlin nested if-elses
    clf = DecisionTreeClassifier(max_depth=4, class_weight='balanced', random_state=42)
    clf.fit(X, y)
    
    print("\nDecision Tree Structure (sklearn text format):")
    print(export_text(clf, feature_names=feature_cols))
    
    code = generate_python_code(clf, feature_cols)
    rules_path = "/Users/neilkloot/Code/CricketBattingTracker/pipelines/stance_decision_tree_rules.py"
    with open(rules_path, "w") as f:
        f.write(code)
    print(f"Generated python logic rules written to: {rules_path}")

if __name__ == "__main__":
    main()
