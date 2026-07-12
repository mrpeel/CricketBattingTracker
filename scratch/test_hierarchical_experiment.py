#!/usr/bin/env python3
import os
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import classification_report, accuracy_score

FEATURES_CSV = "/Users/neilkloot/Code/Batting Sensor Stats/combined_features.csv"

def get_video_inspired_hierarchy_prediction(X_train, y_train, X_test, features):
    # Step 1: FF vs BF (SLOG is BF)
    def map_ff_bf(val):
        if val in ["PULL/HOOK", "CUT/PUNCH", "DEFLECTION/GUIDE", "SLOG"]:
            return "BF"
        return "FF"
        
    y_train_ff_bf = np.array([map_ff_bf(val) for val in y_train])
    clf_ff_bf = RandomForestClassifier(n_estimators=100, max_depth=8, class_weight='balanced_subsample', random_state=42)
    clf_ff_bf.fit(X_train[features], y_train_ff_bf)
    
    # Step 2a: FF -> Defensive vs Attacking
    ff_mask = (y_train_ff_bf == "FF")
    y_train_ff = y_train[ff_mask]
    y_train_ff_def_att = np.array(["Defensive" if val == "DRIVE/DEFENCE" else "Attacking" for val in y_train_ff])
    
    clf_ff_def_att = RandomForestClassifier(n_estimators=100, max_depth=8, class_weight='balanced_subsample', random_state=42)
    clf_ff_def_att.fit(X_train[ff_mask][features], y_train_ff_def_att)
    
    # Step 3a: FF Attacking Leaf (GLANCE/FLICK, SWEEP, POWER DRIVE)
    ff_att_mask = ff_mask & (y_train != "DRIVE/DEFENCE")
    clf_ff_att_leaf = RandomForestClassifier(n_estimators=100, max_depth=8, class_weight='balanced_subsample', random_state=42)
    if sum(ff_att_mask) > 0:
        clf_ff_att_leaf.fit(X_train[ff_att_mask][features], y_train[ff_att_mask])
        
    # Step 2b: BF -> High vs Low
    bf_mask = (y_train_ff_bf == "BF")
    y_train_bf = y_train[bf_mask]
    y_train_bf_high_low = np.array(["High" if val in ["PULL/HOOK", "SLOG"] else "Low" for val in y_train_bf])
    
    clf_bf_high_low = RandomForestClassifier(n_estimators=100, max_depth=8, class_weight='balanced_subsample', random_state=42)
    clf_bf_high_low.fit(X_train[bf_mask][features], y_train_bf_high_low)
    
    # Step 3b: BF High Leaf (PULL/HOOK vs SLOG)
    bf_high_mask = bf_mask & np.isin(y_train, ["PULL/HOOK", "SLOG"])
    clf_bf_high_leaf = RandomForestClassifier(n_estimators=100, max_depth=8, class_weight='balanced_subsample', random_state=42)
    if sum(bf_high_mask) > 0:
        clf_bf_high_leaf.fit(X_train[bf_high_mask][features], y_train[bf_high_mask])
        
    # Step 3c: BF Low Leaf (CUT/PUNCH vs DEFLECTION/GUIDE)
    bf_low_mask = bf_mask & np.isin(y_train, ["CUT/PUNCH", "DEFLECTION/GUIDE"])
    clf_bf_low_leaf = RandomForestClassifier(n_estimators=100, max_depth=8, class_weight='balanced_subsample', random_state=42)
    if sum(bf_low_mask) > 0:
        clf_bf_low_leaf.fit(X_train[bf_low_mask][features], y_train[bf_low_mask])
        
    # Inference
    preds = []
    for _, row in X_test.iterrows():
        row_df = pd.DataFrame([row])
        ff_bf = clf_ff_bf.predict(row_df[features])[0]
        
        if ff_bf == "FF":
            def_att = clf_ff_def_att.predict(row_df[features])[0]
            if def_att == "Defensive":
                preds.append("DRIVE/DEFENCE")
            else:
                preds.append(clf_ff_att_leaf.predict(row_df[features])[0] if sum(ff_att_mask) > 0 else "DRIVE/DEFENCE")
        else: # BF
            high_low = clf_bf_high_low.predict(row_df[features])[0]
            if high_low == "High":
                preds.append(clf_bf_high_leaf.predict(row_df[features])[0] if sum(bf_high_mask) > 0 else "PULL/HOOK")
            else:
                preds.append(clf_bf_low_leaf.predict(row_df[features])[0] if sum(bf_low_mask) > 0 else "CUT/PUNCH")
                
    return np.array(preds)


def get_kinematics_optimized_hierarchy_prediction(X_train, y_train, X_test, features):
    # Step 1: High Velocity (SLOG, PULL/HOOK, POWER DRIVE, SWEEP) vs Low/Medium Velocity (DRIVE/DEFENCE, GLANCE/FLICK, CUT/PUNCH, DEFLECTION/GUIDE)
    high_vel_classes = ["SLOG", "PULL/HOOK", "POWER DRIVE", "SWEEP"]
    
    def map_vel(val):
        if val in high_vel_classes:
            return "High"
        return "Low"
        
    y_train_vel = np.array([map_vel(val) for val in y_train])
    clf_vel = RandomForestClassifier(n_estimators=100, max_depth=8, class_weight='balanced_subsample', random_state=42)
    clf_vel.fit(X_train[features], y_train_vel)
    
    # Step 2a: High Vel -> Offside/Vertical Plane (POWER DRIVE, PULL/HOOK) vs Legside/Sweep Plane (SLOG, SWEEP)
    high_mask = (y_train_vel == "High")
    y_train_high = y_train[high_mask]
    y_train_high_plane = np.array(["Vertical" if val in ["POWER DRIVE", "PULL/HOOK"] else "Horizontal" for val in y_train_high])
    
    clf_high_plane = RandomForestClassifier(n_estimators=100, max_depth=8, class_weight='balanced_subsample', random_state=42)
    clf_high_plane.fit(X_train[high_mask][features], y_train_high_plane)
    
    # Step 3a: High-Vertical leaf (POWER DRIVE vs PULL/HOOK)
    high_vert_mask = high_mask & np.isin(y_train, ["POWER DRIVE", "PULL/HOOK"])
    clf_high_vert = RandomForestClassifier(n_estimators=100, max_depth=8, class_weight='balanced_subsample', random_state=42)
    if sum(high_vert_mask) > 0:
        clf_high_vert.fit(X_train[high_vert_mask][features], y_train[high_vert_mask])
        
    # Step 3b: High-Horizontal leaf (SLOG vs SWEEP)
    high_horiz_mask = high_mask & np.isin(y_train, ["SLOG", "SWEEP"])
    clf_high_horiz = RandomForestClassifier(n_estimators=100, max_depth=8, class_weight='balanced_subsample', random_state=42)
    if sum(high_horiz_mask) > 0:
        clf_high_horiz.fit(X_train[high_horiz_mask][features], y_train[high_horiz_mask])
        
    # Step 2b: Low/Medium Vel -> Closed/Flick (GLANCE/FLICK, DRIVE/DEFENCE) vs Open/Cut (CUT/PUNCH, DEFLECTION/GUIDE)
    low_mask = (y_train_vel == "Low")
    y_train_low = y_train[low_mask]
    y_train_low_plane = np.array(["Closed" if val in ["GLANCE/FLICK", "DRIVE/DEFENCE"] else "Open" for val in y_train_low])
    
    clf_low_plane = RandomForestClassifier(n_estimators=100, max_depth=8, class_weight='balanced_subsample', random_state=42)
    clf_low_plane.fit(X_train[low_mask][features], y_train_low_plane)
    
    # Step 3c: Low-Closed leaf (GLANCE/FLICK vs DRIVE/DEFENCE)
    low_closed_mask = low_mask & np.isin(y_train, ["GLANCE/FLICK", "DRIVE/DEFENCE"])
    clf_low_closed = RandomForestClassifier(n_estimators=100, max_depth=8, class_weight='balanced_subsample', random_state=42)
    if sum(low_closed_mask) > 0:
        clf_low_closed.fit(X_train[low_closed_mask][features], y_train[low_closed_mask])
        
    # Step 3d: Low-Open leaf (CUT/PUNCH vs DEFLECTION/GUIDE)
    low_open_mask = low_mask & np.isin(y_train, ["CUT/PUNCH", "DEFLECTION/GUIDE"])
    clf_low_open = RandomForestClassifier(n_estimators=100, max_depth=8, class_weight='balanced_subsample', random_state=42)
    if sum(low_open_mask) > 0:
        clf_low_open.fit(X_train[low_open_mask][features], y_train[low_open_mask])
        
    # Inference
    preds = []
    for _, row in X_test.iterrows():
        row_df = pd.DataFrame([row])
        vel = clf_vel.predict(row_df[features])[0]
        
        if vel == "High":
            plane = clf_high_plane.predict(row_df[features])[0]
            if plane == "Vertical":
                preds.append(clf_high_vert.predict(row_df[features])[0] if sum(high_vert_mask) > 0 else "PULL/HOOK")
            else:
                preds.append(clf_high_horiz.predict(row_df[features])[0] if sum(high_horiz_mask) > 0 else "SLOG")
        else: # Low
            plane = clf_low_plane.predict(row_df[features])[0]
            if plane == "Closed":
                preds.append(clf_low_closed.predict(row_df[features])[0] if sum(low_closed_mask) > 0 else "DRIVE/DEFENCE")
            else:
                preds.append(clf_low_open.predict(row_df[features])[0] if sum(low_open_mask) > 0 else "CUT/PUNCH")
                
    return np.array(preds)


def main():
    if not os.path.exists(FEATURES_CSV):
        print(f"ERROR: {FEATURES_CSV} not found.")
        return
        
    df = pd.read_csv(FEATURES_CSV)
    df_swings = df[df['normalized_gt'] != 'NON-SWING'].copy()
    
    features = [
        'gyroMag', 'rollImpactDeg', 'yawImpactDeg', 'deltaX', 'deltaZ', 'planeRatio',
        'gyro_y_min', 'grav_x_max', 'grav_y_min', 'mag_x_max'
    ]
    
    # Fill NAs
    df_swings[features] = df_swings[features].fillna(df_swings[features].median())
    
    X = df_swings[features + ['session_date']]
    y = df_swings['normalized_gt'].values
    
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    
    # Store results (overall and per-class) on REAL data ONLY
    flat_real_preds_all = []
    flat_real_gts_all = []
    
    video_real_preds_all = []
    video_real_gts_all = []
    
    opt_real_preds_all = []
    opt_real_gts_all = []
    
    for fold, (train_idx, test_idx) in enumerate(cv.split(X, y)):
        X_train, y_train = X.iloc[train_idx], y[train_idx]
        X_test, y_test = X.iloc[test_idx], y[test_idx]
        
        # Test fold real-only mask
        test_real_mask = (X_test['session_date'] != 'synthetic').values
        if sum(test_real_mask) == 0:
            continue
            
        X_test_real = X_test[test_real_mask]
        y_test_real = y_test[test_real_mask]
        
        # --- Flat Classifier ---
        flat_clf = RandomForestClassifier(n_estimators=100, max_depth=8, class_weight='balanced_subsample', random_state=42)
        flat_clf.fit(X_train[features], y_train)
        flat_preds = flat_clf.predict(X_test_real[features])
        
        flat_real_preds_all.extend(flat_preds)
        flat_real_gts_all.extend(y_test_real)
        
        # --- Video-Inspired Hierarchical Classifier ---
        video_preds = get_video_inspired_hierarchy_prediction(X_train, y_train, X_test_real, features)
        video_real_preds_all.extend(video_preds)
        video_real_gts_all.extend(y_test_real)
        
        # --- Kinematics-Optimized Hierarchical Classifier ---
        opt_preds = get_kinematics_optimized_hierarchy_prediction(X_train, y_train, X_test_real, features)
        opt_real_preds_all.extend(opt_preds)
        opt_real_gts_all.extend(y_test_real)

    # Calculate overall metrics on real-world ground truth
    print("\n========================================================")
    print("REAL-WORLD GROUND TRUTH EVALUATION RESULTS")
    print("========================================================")
    
    flat_acc = accuracy_score(flat_real_gts_all, flat_real_preds_all)
    video_acc = accuracy_score(video_real_gts_all, video_real_preds_all)
    opt_acc = accuracy_score(opt_real_gts_all, opt_real_preds_all)
    
    print(f"Flat Baseline Classifier Accuracy          : {flat_acc*100:.2f}%")
    print(f"Video-Inspired Hierarchical Accuracy       : {video_acc*100:.2f}%")
    print(f"Watch-Kinematics-Optimized Hierarchical Acc : {opt_acc*100:.2f}%")
    print("========================================================\n")
    
    print("Flat Baseline Classification Report:")
    print(classification_report(flat_real_gts_all, flat_real_preds_all, zero_division=0))
    print("--------------------------------------------------------\n")
    
    print("Video-Inspired Hierarchical Classification Report:")
    print(classification_report(video_real_gts_all, video_real_preds_all, zero_division=0))
    print("--------------------------------------------------------\n")
    
    print("Watch-Kinematics-Optimized Hierarchical Classification Report:")
    print(classification_report(opt_real_gts_all, opt_real_preds_all, zero_division=0))
    print("========================================================")

if __name__ == "__main__":
    main()
