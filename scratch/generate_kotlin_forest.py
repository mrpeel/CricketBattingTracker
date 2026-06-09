#!/usr/bin/env python3
import os
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder

BASE_DIR = "/Users/neilkloot/Code/Batting Sensor Stats"
FEATURES_CSV = os.path.join(BASE_DIR, "combined_features.csv")
OUTPUT_KOTLIN = "/Users/neilkloot/Code/CricketBattingTracker/wear/src/main/java/com/mrpeel/cricketbattingtracker/ml/GeneratedForest.kt"
PROPOSED_CSV_PATH = os.path.join(BASE_DIR, "proposed_logic_aligned.csv")

def main():
    if not os.path.exists(FEATURES_CSV):
        print(f"❌ ERROR: Features CSV not found at {FEATURES_CSV}")
        return

    df = pd.read_csv(FEATURES_CSV)
    df_swings = df[df['normalized_gt'] != 'NON-SWING'].copy()
    
    # 10 Kotlin-native features
    features = [
        'gyroMag', 'rollImpactDeg', 'yawImpactDeg', 'deltaX', 'deltaZ', 'planeRatio',
        'gyro_y_min', 'grav_x_max', 'grav_y_min', 'mag_x_max'
    ]
    
    X = df_swings[features].fillna(df_swings[features].median())
    y = df_swings['normalized_gt'].values
    
    le = LabelEncoder()
    y_enc = le.fit_transform(y)
    class_names = list(le.classes_)
    
    print(f"Class names matching LabelEncoder order: {class_names}")
    
    # Train the Random Forest
    rf = RandomForestClassifier(
        n_estimators=200,
        max_depth=8,
        class_weight='balanced_subsample',
        random_state=42,
        n_jobs=-1
    )
    rf.fit(X, y_enc)
    
    # Transpile the forest to Kotlin
    print(f"Generating Kotlin Random Forest in {OUTPUT_KOTLIN}...")
    
    os.makedirs(os.path.dirname(OUTPUT_KOTLIN), exist_ok=True)
    
    with open(OUTPUT_KOTLIN, 'w') as f:
        # Write file header
        f.write("// Generated Random Forest Classifier for Cricket Batting Tracker\n")
        f.write(f"// Trained on {len(df_swings)} swings across {df_swings['session_id'].nunique()} trustworthy sessions\n")
        f.write("package com.mrpeel.cricketbattingtracker.ml\n\n")
        
        # Write data class
        f.write("data class SwingFeatures(\n")
        for feat in features:
            f.write(f"    val {feat}: Float,\n")
        # Remove trailing comma / close class
        f.seek(f.tell() - 2)
        f.write("\n)\n\n")
        
        # Write object header
        f.write("object GeneratedForest {\n")
        f.write("    private val CLASSES = arrayOf(\n")
        for name in class_names:
            f.write(f"        \"{name}\",\n")
        f.write("    )\n\n")
        
        # Write main predict method
        f.write("    fun predict(f: SwingFeatures): String {\n")
        f.write("        val votes = FloatArray(6)\n\n")
        for i in range(rf.n_estimators):
            f.write(f"        predictTree{i}(f, votes)\n")
        f.write("\n")
        f.write("        var maxVal = -1f\n")
        f.write("        var maxIdx = 0\n")
        f.write("        for (i in 0 until 6) {\n")
        f.write("            if (votes[i] > maxVal) {\n")
        f.write("                maxVal = votes[i]\n")
        f.write("                maxIdx = i\n")
        f.write("            }\n")
        f.write("        }\n")
        f.write("        return CLASSES[maxIdx]\n")
        f.write("    }\n\n")
        
        # Write tree prediction helper methods
        for tree_idx, estimator in enumerate(rf.estimators_):
            tree = estimator.tree_
            f.write(f"    private fun predictTree{tree_idx}(f: SwingFeatures, votes: FloatArray) {{\n")
            
            def recurse(node, depth):
                indent = "    " * (depth + 1)
                if tree.children_left[node] == -1:  # Leaf node
                    val = tree.value[node][0]
                    prob = val / val.sum()
                    leaf_lines = []
                    for class_idx, p in enumerate(prob):
                        if p > 1e-6:
                            leaf_lines.append(f"{indent}votes[{class_idx}] += {p:.6f}f")
                    return "\n".join(leaf_lines)
                else:
                    feat_idx = tree.feature[node]
                    thresh = tree.threshold[node]
                    feat_name = features[feat_idx]
                    left_code = recurse(tree.children_left[node], depth + 1)
                    right_code = recurse(tree.children_right[node], depth + 1)
                    return (f"{indent}if (f.{feat_name} <= {thresh:.6f}f) {{\n"
                            f"{left_code}\n"
                            f"{indent}}} else {{\n"
                            f"{right_code}\n"
                            f"{indent}}}")
            
            f.write(recurse(0, 1))
            f.write("\n    }\n\n")
            
        f.write("}\n")
        
    print("✅ Successfully generated GeneratedForest.kt")
    
    # ─── Overwrite proposed_logic_aligned.csv ───
    print(f"Overwriting {PROPOSED_CSV_PATH} with 10-feature RF predictions...")
    y_pred = rf.predict(X)
    proposed_preds = le.inverse_transform(y_pred)
    
    # Load combined ground truth aligned
    combined_gt_path = os.path.join(BASE_DIR, "combined_ground_truth_aligned.csv")
    df_combined_gt = pd.read_csv(combined_gt_path)
    
    df_pred_lookup = df_swings[['session_id', 'shot_index']].copy()
    df_pred_lookup['pred_proposed'] = proposed_preds
    
    df_proposed_gt = df_combined_gt.merge(
        df_pred_lookup,
        on=['session_id', 'shot_index'],
        how='left'
    )
    
    df_proposed_gt['pred_proposed'] = df_proposed_gt['pred_proposed'].fillna("N/A")
    
    def check_correct(row):
        if row['normalized_gt'] == 'NON-SWING':
            return "N/A"
        return 1 if row['pred_proposed'] == row['normalized_gt'] else 0
        
    df_proposed_gt['is_correct_proposed'] = df_proposed_gt.apply(check_correct, axis=1)
    
    cols = list(df_combined_gt.columns)
    cols.remove('predicted_shot_type')
    cols.remove('is_correct')
    
    df_proposed_gt = df_proposed_gt[cols + ['pred_proposed', 'is_correct_proposed']]
    df_proposed_gt.rename(columns={
        'pred_proposed': 'predicted_shot_type',
        'is_correct_proposed': 'is_correct'
    }, inplace=True)
    
    df_proposed_gt.to_csv(PROPOSED_CSV_PATH, index=False)
    print(f"✅ Successfully updated proposed_logic_aligned.csv")

if __name__ == "__main__":
    main()
