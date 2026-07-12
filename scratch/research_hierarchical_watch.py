#!/usr/bin/env python3
import os
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.metrics import accuracy_score

FEATURES_CSV = "/Users/neilkloot/Code/Batting Sensor Stats/combined_features.csv"

def main():
    if not os.path.exists(FEATURES_CSV):
        print(f"ERROR: {FEATURES_CSV} does not exist.")
        return

    df = pd.read_csv(FEATURES_CSV)
    df_swings = df[df['normalized_gt'] != 'NON-SWING'].copy()

    print(f"Total swing samples: {len(df_swings)}")
    print(df_swings['normalized_gt'].value_counts())

    # Features currently used in flat RF
    features = [
        'gyroMag', 'rollImpactDeg', 'yawImpactDeg', 'deltaX', 'deltaZ', 'planeRatio',
        'gyro_y_min', 'grav_x_max', 'grav_y_min', 'mag_x_max'
    ]

    X = df_swings[features].fillna(df_swings[features].median())
    y = df_swings['normalized_gt'].values

    # Taxonomy mapping for watch data
    # Step 1: Front-Foot vs Back-Foot
    # FF: DRIVE/DEFENCE, GLANCE/FLICK, SWEEP, POWER DRIVE
    # BF: PULL/HOOK, CUT/PUNCH, DEFLECTION/GUIDE, SLOG (Wait, is SLOG FF or BF? Let's check both)
    
    # Let's define two options for mapping
    # Option A: SLOG is Front-Foot
    # Option B: SLOG is Back-Foot (since pull/hook and slog have high bat speeds, maybe they share similar kinematics)
    
    for slog_mapping in ['FF', 'BF']:
        print(f"\n==========================================")
        print(f"Testing Hierarchical Model with SLOG mapped to {slog_mapping}")
        print(f"==========================================")
        
        def map_step1(val):
            if val in ["PULL/HOOK", "CUT/PUNCH", "DEFLECTION/GUIDE"]:
                return "BF"
            elif val in ["DRIVE/DEFENCE", "GLANCE/FLICK", "SWEEP", "POWER DRIVE"]:
                return "FF"
            else: # SLOG
                return slog_mapping

        y_ff_bf = np.array([map_step1(val) for val in y])
        
        # Stratified 5-Fold CV
        cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
        
        flat_accs = []
        hierarchical_accs = []
        
        for fold, (train_idx, test_idx) in enumerate(cv.split(X, y)):
            X_train, y_train = X.iloc[train_idx], y[train_idx]
            X_test, y_test = X.iloc[test_idx], y[test_idx]
            
            # --- Baseline Flat Model ---
            flat_clf = RandomForestClassifier(n_estimators=100, max_depth=8, class_weight='balanced_subsample', random_state=42)
            flat_clf.fit(X_train, y_train)
            flat_preds = flat_clf.predict(X_test)
            flat_accs.append(accuracy_score(y_test, flat_preds))
            
            # --- Hierarchical Models ---
            # 1. FF vs BF
            y_train_ff_bf = np.array([map_step1(val) for val in y_train])
            clf_ff_bf = RandomForestClassifier(n_estimators=100, max_depth=8, class_weight='balanced_subsample', random_state=42)
            clf_ff_bf.fit(X_train, y_train_ff_bf)
            
            # 2a. FF Branch: DRIVE/DEFENCE (Control/Defensive) vs Attacking
            ff_train_mask = (y_train_ff_bf == "FF")
            y_train_ff_branch = y_train[ff_train_mask]
            
            # Sub-split FF into: DRIVE/DEFENCE vs Attacking-FF (Glance/Flick, Sweep, Power Drive, Slog if FF)
            y_train_ff_def_att = np.array(["Control" if val == "DRIVE/DEFENCE" else "Attacking" for val in y_train_ff_branch])
            clf_ff_def_att = RandomForestClassifier(n_estimators=100, max_depth=8, class_weight='balanced_subsample', random_state=42)
            clf_ff_def_att.fit(X_train[ff_train_mask], y_train_ff_def_att)
            
            # 3a. FF Attacking Leaf: GLANCE/FLICK, SWEEP, POWER DRIVE, SLOG (if FF)
            ff_att_train_mask = ff_train_mask & (y_train != "DRIVE/DEFENCE")
            clf_ff_att_leaf = RandomForestClassifier(n_estimators=100, max_depth=8, class_weight='balanced_subsample', random_state=42)
            clf_ff_att_leaf.fit(X_train[ff_att_train_mask], y_train[ff_att_train_mask])
            
            # 2b. BF Branch: High vs Low
            bf_train_mask = (y_train_ff_bf == "BF")
            y_train_bf_branch = y_train[bf_train_mask]
            
            # High = PULL/HOOK, SLOG (if BF). Low = CUT/PUNCH, DEFLECTION/GUIDE
            bf_high_classes = ["PULL/HOOK"]
            if slog_mapping == "BF":
                bf_high_classes.append("SLOG")
                
            y_train_bf_high_low = np.array(["High" if val in bf_high_classes else "Low" for val in y_train_bf_branch])
            clf_bf_high_low = RandomForestClassifier(n_estimators=100, max_depth=8, class_weight='balanced_subsample', random_state=42)
            clf_bf_high_low.fit(X_train[bf_train_mask], y_train_bf_high_low)
            
            # 3b. BF High Leaf: PULL/HOOK vs SLOG (only if SLOG is BF)
            if slog_mapping == "BF":
                bf_high_train_mask = bf_train_mask & np.isin(y_train, bf_high_classes)
                clf_bf_high_leaf = RandomForestClassifier(n_estimators=100, max_depth=8, class_weight='balanced_subsample', random_state=42)
                clf_bf_high_leaf.fit(X_train[bf_high_train_mask], y_train[bf_high_train_mask])
                
            # 3c. BF Low Leaf: CUT/PUNCH vs DEFLECTION/GUIDE
            bf_low_train_mask = bf_train_mask & ~np.isin(y_train, bf_high_classes)
            clf_bf_low_leaf = RandomForestClassifier(n_estimators=100, max_depth=8, class_weight='balanced_subsample', random_state=42)
            clf_bf_low_leaf.fit(X_train[bf_low_train_mask], y_train[bf_low_train_mask])
            
            # --- Inference ---
            fold_preds = []
            for _, row in X_test.iterrows():
                row_df = pd.DataFrame([row])
                ff_bf_pred = clf_ff_bf.predict(row_df)[0]
                
                if ff_bf_pred == "FF":
                    def_att_pred = clf_ff_def_att.predict(row_df)[0]
                    if def_att_pred == "Control":
                        fold_preds.append("DRIVE/DEFENCE")
                    else:
                        fold_preds.append(clf_ff_att_leaf.predict(row_df)[0])
                else: # BF
                    high_low_pred = clf_bf_high_low.predict(row_df)[0]
                    if high_low_pred == "High":
                        if slog_mapping == "BF":
                            fold_preds.append(clf_bf_high_leaf.predict(row_df)[0])
                        else:
                            fold_preds.append("PULL/HOOK")
                    else:
                        fold_preds.append(clf_bf_low_leaf.predict(row_df)[0])
            
            hierarchical_accs.append(accuracy_score(y_test, fold_preds))
            
        print(f"Flat CV Acc: {np.mean(flat_accs):.4f}")
        print(f"Hierarchical CV Acc: {np.mean(hierarchical_accs):.4f}")

if __name__ == "__main__":
    main()
