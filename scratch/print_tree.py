#!/usr/bin/env python3
import os
import pandas as pd
from sklearn.tree import DecisionTreeClassifier, export_text
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import classification_report, accuracy_score
from sklearn.model_selection import StratifiedKFold, cross_val_score

BASE_DIR = "/Users/neilkloot/Code/Batting Sensor Stats"
FEATURES_CSV = os.path.join(BASE_DIR, "combined_features.csv")

def main():
    df = pd.read_csv(FEATURES_CSV)
    df = df[df['normalized_gt'] != 'NON-SWING'].copy()
    
    recommended_features = [
        'gyroMag', 'rollImpactDeg', 'yawImpactDeg', 'deltaX', 'deltaZ', 'planeRatio',
        'gyro_y_min', 'gyro_y_skew', 'grav_x_max', 'grav_y_min', 'mag_x_max', 'gameori_qz_range'
    ]
    
    meta_cols = ['session_id', 'session_date', 'shot_index', 'shot_number', 'shot_type', 
                 'normalized_gt', 'pred_current', 'is_correct']
    feature_cols = [c for c in df.columns if c not in meta_cols]
    
    df_features = df[feature_cols].copy().fillna(df[feature_cols].median())
    X = df_features[recommended_features]
    y = df['normalized_gt'].values

    le = LabelEncoder()
    y_enc = le.fit_transform(y)
    class_names = le.classes_

    # 1. Depth-3 Decision Tree
    dt3 = DecisionTreeClassifier(max_depth=3, min_samples_split=10, random_state=42)
    dt3.fit(X, y_enc)
    
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    scores3 = cross_val_score(dt3, X, y_enc, cv=cv, scoring='accuracy')
    
    print("\n=================== DECISION TREE DEPTH 3 ===================")
    print(f"5-Fold CV Accuracy: {scores3.mean()*100:.2f}% ± {scores3.std()*100:.2f}%")
    print(f"Training Accuracy:  {accuracy_score(y_enc, dt3.predict(X))*100:.2f}%")
    print("\nTree Structure:")
    print(export_text(dt3, feature_names=recommended_features))
    print("\nClassification Report:")
    print(classification_report(y_enc, dt3.predict(X), target_names=class_names))

    # 2. Depth-4 Decision Tree
    dt4 = DecisionTreeClassifier(max_depth=4, min_samples_split=10, random_state=42)
    dt4.fit(X, y_enc)
    scores4 = cross_val_score(dt4, X, y_enc, cv=cv, scoring='accuracy')
    
    print("\n=================== DECISION TREE DEPTH 4 ===================")
    print(f"5-Fold CV Accuracy: {scores4.mean()*100:.2f}% ± {scores4.std()*100:.2f}%")
    print(f"Training Accuracy:  {accuracy_score(y_enc, dt4.predict(X))*100:.2f}%")
    print("\nTree Structure:")
    print(export_text(dt4, feature_names=recommended_features))
    print("\nClassification Report:")
    print(classification_report(y_enc, dt4.predict(X), target_names=class_names))

if __name__ == "__main__":
    main()
