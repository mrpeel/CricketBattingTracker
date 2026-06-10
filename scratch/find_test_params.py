import os
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder

BASE_DIR = "/Users/neilkloot/Code/Batting Sensor Stats"
FEATURES_CSV = os.path.join(BASE_DIR, "combined_features.csv")

def main():
    if not os.path.exists(FEATURES_CSV):
        print(f"ERROR: {FEATURES_CSV} not found")
        return
        
    df = pd.read_csv(FEATURES_CSV)
    df_swings = df[df['normalized_gt'] != 'NON-SWING'].copy()
    
    features = [
        'gyroMag', 'rollImpactDeg', 'yawImpactDeg', 'deltaX', 'deltaZ', 'planeRatio',
        'gyro_y_min', 'grav_x_max', 'grav_y_min', 'mag_x_max'
    ]
    
    X = df_swings[features].fillna(df_swings[features].median())
    y = df_swings['normalized_gt'].values
    
    le = LabelEncoder()
    y_enc = le.fit_transform(y)
    
    rf = RandomForestClassifier(
        n_estimators=200,
        max_depth=8,
        class_weight='balanced_subsample',
        random_state=42,
        n_jobs=-1
    )
    rf.fit(X, y_enc)
    
    # Let's inspect class names and their LabelEncoder indices
    for i, name in enumerate(le.classes_):
        print(f"Class {i}: {name}")
        
    # Print stats for each class
    for cls in le.classes_:
        print(f"\n--- Stats for {cls} ---")
        cls_df = X[y == cls]
        print(cls_df.describe().loc[['min', '50%', 'max']])
        
    # Find a good point for GLANCE/FLICK (let's check samples in the dataset that are GLANCE/FLICK)
    gf_samples = df_swings[df_swings['normalized_gt'] == 'GLANCE/FLICK']
    print("\n--- Some GLANCE/FLICK samples ---")
    print(gf_samples[features].head(10))
    
    # Test if we can find a sample that gets predicted as GLANCE/FLICK
    print("\nTesting predictions on GF samples:")
    for idx, row in gf_samples[features].head(10).iterrows():
        feat_vals = row.values.reshape(1, -1)
        pred_idx = rf.predict(feat_vals)[0]
        pred_cls = le.classes_[pred_idx]
        print(f"Sample {idx}: features={row.to_dict()}, prediction={pred_cls}")
        
    # Find a good point for CUT/PUNCH
    cp_samples = df_swings[df_swings['normalized_gt'] == 'CUT/PUNCH']
    print("\n--- Some CUT/PUNCH samples ---")
    print(cp_samples[features].head(10))
    
    print("\nTesting predictions on CP samples:")
    for idx, row in cp_samples[features].head(10).iterrows():
        feat_vals = row.values.reshape(1, -1)
        pred_idx = rf.predict(feat_vals)[0]
        pred_cls = le.classes_[pred_idx]
        print(f"Sample {idx}: features={row.to_dict()}, prediction={pred_cls}")

if __name__ == '__main__':
    main()
