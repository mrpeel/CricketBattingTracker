#!/usr/bin/env python3
import os
import pandas as pd
from sklearn.model_selection import StratifiedKFold, GridSearchCV
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder

BASE_DIR = "/Users/neilkloot/Code/Batting Sensor Stats"
FEATURES_CSV = os.path.join(BASE_DIR, "combined_features.csv")

def main():
    if not os.path.exists(FEATURES_CSV):
        print(f"❌ ERROR: Features CSV not found")
        return

    df = pd.read_csv(FEATURES_CSV)
    df = df[df['normalized_gt'] != 'NON-SWING'].copy()
    
    # Define features that are ALREADY computed in SwingDetector.kt
    # Note that in SwingDetector.kt:
    # - gyroYMin is computed from swing window
    # - gravXMax is computed from swing window
    # - gravYMin is computed from swing window
    # - magXMax is computed from swing window
    kotlin_features = [
        'gyroMag', 'rollImpactDeg', 'yawImpactDeg', 'deltaX', 'deltaZ', 'planeRatio',
        'gyro_y_min', 'grav_x_max', 'grav_y_min', 'mag_x_max'
    ]
    
    # Ensure they exist
    kotlin_features = [f for f in kotlin_features if f in df.columns]
    print(f"Evaluating RF on {len(kotlin_features)} features: {kotlin_features}")
    
    X = df[kotlin_features].fillna(df[kotlin_features].median())
    y = df['normalized_gt'].values
    
    le = LabelEncoder()
    y_enc = le.fit_transform(y)
    
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    rf_param_grid = {
        'n_estimators': [100, 200, 300],
        'max_depth': [5, 6, 7, 8],
        'class_weight': ['balanced', 'balanced_subsample'],
        'random_state': [42]
    }
    
    rf_grid = GridSearchCV(
        RandomForestClassifier(random_state=42),
        rf_param_grid,
        cv=cv,
        scoring='accuracy',
        n_jobs=-1
    )
    rf_grid.fit(X, y_enc)
    print(f"Best RF CV Accuracy: {rf_grid.best_score_*100:.2f}%")
    print(f"Params: {rf_grid.best_params_}")

if __name__ == "__main__":
    main()
