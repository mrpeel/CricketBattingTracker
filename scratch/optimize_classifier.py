#!/usr/bin/env python3
import os
import numpy as np
import pandas as pd
from sklearn.model_selection import StratifiedKFold, GridSearchCV
from sklearn.tree import DecisionTreeClassifier, export_text
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import classification_report, accuracy_score, f1_score

# ─── Configuration ────────────────────────────────────────────────────────────
BASE_DIR = "/Users/neilkloot/Code/Batting Sensor Stats"
FEATURES_CSV = os.path.join(BASE_DIR, "combined_features.csv")

def main():
    if not os.path.exists(FEATURES_CSV):
        print(f"❌ ERROR: Features CSV not found at {FEATURES_CSV}")
        return

    df = pd.read_csv(FEATURES_CSV)
    
    # Exclude non-swing rows
    df = df[df['normalized_gt'] != 'NON-SWING'].copy()
    
    total_shots = len(df)
    print(f"Loaded {total_shots} swing shots for optimization.")

    # Fill NaNs in features with column median
    meta_cols = ['session_id', 'session_date', 'shot_index', 'shot_number', 'shot_type', 
                 'normalized_gt', 'pred_current', 'is_correct']
    feature_cols = [c for c in df.columns if c not in meta_cols]
    
    # Drop features with all NaN
    df_features = df[feature_cols].copy()
    all_nan_cols = df_features.columns[df_features.isna().all()]
    df_features = df_features.drop(columns=all_nan_cols)
    feature_cols = list(df_features.columns)
    
    # Fill remaining NaNs
    df_features = df_features.fillna(df_features.median())
    
    X = df_features
    y = df['normalized_gt'].values

    le = LabelEncoder()
    y_enc = le.fit_transform(y)
    class_names = le.classes_

    # Define Feature Subsets
    baseline_features = ['gyroMag', 'rollImpactDeg', 'yawImpactDeg', 'deltaX', 'deltaZ', 'planeRatio']
    
    recommended_features = [
        'gyroMag', 'rollImpactDeg', 'yawImpactDeg', 'deltaX', 'deltaZ', 'planeRatio',
        'gyro_y_min', 'gyro_y_skew', 'grav_x_max', 'grav_y_min', 'mag_x_max', 'gameori_qz_range'
    ]
    
    # Ensure all listed features exist in the dataset
    baseline_features = [f for f in baseline_features if f in feature_cols]
    recommended_features = [f for f in recommended_features if f in feature_cols]
    all_features = feature_cols

    feature_subsets = {
        "Baseline Features": baseline_features,
        "Recommended Features": recommended_features,
        "All Sensor Features": all_features
    }

    # Grid Search Definition
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    
    dt_param_grid = {
        'max_depth': [3, 4, 5, 6],
        'min_samples_split': [2, 5, 10],
        'class_weight': [None, 'balanced'],
        'criterion': ['gini', 'entropy']
    }
    
    rf_param_grid = {
        'n_estimators': [100, 200, 300],
        'max_depth': [5, 6, 7, 8],
        'class_weight': ['balanced', 'balanced_subsample'],
        'random_state': [42]
    }

    best_overall_score = 0.0
    best_overall_model = None
    best_overall_features = None
    best_overall_name = ""

    print(f"\n=================== GRID SEARCHING MODELS ===================")
    
    for feat_name, feat_list in feature_subsets.items():
        print(f"\n--- Feature Subset: {feat_name} ({len(feat_list)} features) ---")
        X_sub = X[feat_list]
        
        # 1. Decision Tree Grid Search
        dt_grid = GridSearchCV(
            DecisionTreeClassifier(random_state=42),
            dt_param_grid,
            cv=cv,
            scoring='accuracy',
            n_jobs=-1
        )
        dt_grid.fit(X_sub, y_enc)
        print(f"  Best Decision Tree CV Accuracy: {dt_grid.best_score_*100:.2f}%")
        print(f"    Params: {dt_grid.best_params_}")
        
        if dt_grid.best_score_ > best_overall_score:
            best_overall_score = dt_grid.best_score_
            best_overall_model = dt_grid.best_estimator_
            best_overall_features = feat_list
            best_overall_name = f"Decision Tree on {feat_name}"
            
        # 2. Random Forest Grid Search
        rf_grid = GridSearchCV(
            RandomForestClassifier(random_state=42),
            rf_param_grid,
            cv=cv,
            scoring='accuracy',
            n_jobs=-1
        )
        rf_grid.fit(X_sub, y_enc)
        print(f"  Best Random Forest CV Accuracy: {rf_grid.best_score_*100:.2f}%")
        print(f"    Params: {rf_grid.best_params_}")
        
        if rf_grid.best_score_ > best_overall_score:
            best_overall_score = rf_grid.best_score_
            best_overall_model = rf_grid.best_estimator_
            best_overall_features = feat_list
            best_overall_name = f"Random Forest on {feat_name}"

    print(f"\n==============================================================")
    print(f"🏆 Best Model: {best_overall_name}")
    print(f"🏆 Best Cross-Validated Accuracy: {best_overall_score*100:.2f}%")
    print(f"==============================================================")

    # Re-evaluate the best model on the full dataset
    X_best = X[best_overall_features]
    best_overall_model.fit(X_best, y_enc)
    y_pred = best_overall_model.predict(X_best)
    
    print("\nBest Model Classification Report (Full Dataset):")
    print(classification_report(y_enc, y_pred, target_names=class_names))
    
    # If the best model is a Decision Tree, print the structure so we can implement it
    if isinstance(best_overall_model, DecisionTreeClassifier):
        print("\nDecision Tree Structure:")
        print(export_text(best_overall_model, feature_names=best_overall_features))
        
    # Generate proposed_logic_aligned.csv
    print(f"\nRe-running best model over the full dataset to generate proposed_logic_aligned.csv...")
    proposed_preds = le.inverse_transform(y_pred)
    
    # We load ground_truth_aligned.csv and map predictions
    # Build a lookup table from combined_features.csv for prediction
    df_pred_lookup = df[['session_id', 'shot_index']].copy()
    df_pred_lookup['pred_proposed'] = proposed_preds
    
    # Read the combined ground truth aligned CSV
    combined_gt_path = os.path.join(BASE_DIR, "combined_ground_truth_aligned.csv")
    df_combined_gt = pd.read_csv(combined_gt_path)
    
    # Merge proposed prediction
    df_proposed_gt = df_combined_gt.merge(
        df_pred_lookup,
        on=['session_id', 'shot_index'],
        how='left'
    )
    
    # Fill N/A for non-swing rows
    df_proposed_gt['pred_proposed'] = df_proposed_gt['pred_proposed'].fillna("N/A")
    
    # Compute accuracy for proposed
    def check_correct(row):
        if row['normalized_gt'] == 'NON-SWING':
            return "N/A"
        return 1 if row['pred_proposed'] == row['normalized_gt'] else 0
        
    df_proposed_gt['is_correct_proposed'] = df_proposed_gt.apply(check_correct, axis=1)
    
    # Re-order columns to match standard format
    cols = list(df_combined_gt.columns)
    # Remove predicted_shot_type and is_correct from end
    cols.remove('predicted_shot_type')
    cols.remove('is_correct')
    
    df_proposed_gt = df_proposed_gt[cols + ['pred_proposed', 'is_correct_proposed']]
    df_proposed_gt.rename(columns={
        'pred_proposed': 'predicted_shot_type',
        'is_correct_proposed': 'is_correct'
    }, inplace=True)
    
    out_proposed_path = os.path.join(BASE_DIR, "proposed_logic_aligned.csv")
    df_proposed_gt.to_csv(out_proposed_path, index=False)
    print(f"Successfully generated proposed logic alignment CSV at: {out_proposed_path}")

if __name__ == "__main__":
    main()
