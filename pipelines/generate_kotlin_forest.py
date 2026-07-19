#!/usr/bin/env python3
import os
import json
import struct
import shutil
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder

BASE_DIR = "/Users/neilkloot/Code/Batting Sensor Stats"
FEATURES_CSV = os.path.join(BASE_DIR, "combined_features.csv")
CONFIG_JSON = os.path.join(BASE_DIR, "optimized_detection_config.json")

# Outputs for Shot Type Model
OUTPUT_TYPE_WEAR = "/Users/neilkloot/Code/CricketBattingTracker/wear/src/main/java/com/mrpeel/cricketbattingtracker/ml/GeneratedForest.kt"
OUTPUT_TYPE_APP  = "/Users/neilkloot/Code/CricketBattingTracker/app/src/main/java/com/mrpeel/cricketbattingtracker/ml/GeneratedForest.kt"

# Outputs for Shot Quality Model
OUTPUT_QUALITY_WEAR = "/Users/neilkloot/Code/CricketBattingTracker/wear/src/main/java/com/mrpeel/cricketbattingtracker/ml/GeneratedQualityForest.kt"
OUTPUT_QUALITY_APP  = "/Users/neilkloot/Code/CricketBattingTracker/app/src/main/java/com/mrpeel/cricketbattingtracker/ml/GeneratedQualityForest.kt"

# Output for Detection Config
OUTPUT_CONFIG_APP = "/Users/neilkloot/Code/CricketBattingTracker/app/src/main/java/com/mrpeel/cricketbattingtracker/services/ShotEnhancementConfig.kt"

PROPOSED_CSV_PATH = os.path.join(BASE_DIR, "proposed_logic_aligned.csv")

FEATURE_COLS = [
    's1_gyro_y_std', 's1_gyro_z_std', 's1_deltaX', 's1_deltaZ',
    's2_gyroMag', 's2_grav_y_mean', 's2_deltaX', 's2_deltaZ',
    's3_rollImpactDeg', 's3_yawImpactDeg', 's3_deltaX', 's3_deltaZ',
    's3_planeRatio', 's3_gyro_y_min',
    # Polar features — 0.0 when Polar is absent (imputed during training)
    'bottom_hand_gyro_peak', 'bottom_hand_acc_peak',
    'bottom_hand_gyro_ratio', 'bottom_hand_acc_ratio',
    'bottom_hand_time_lead_ms', 'bottom_hand_sync_score',
]

def to_kotlin_string_array(hex_str, chunk_char_limit=16000):
    chunks = [hex_str[i:i+chunk_char_limit] for i in range(0, len(hex_str), chunk_char_limit)]
    formatted_chunks = []
    for chunk in chunks:
        sublines = [f'            "{chunk[j:j+100]}"' for j in range(0, len(chunk), 100)]
        formatted_chunks.append("(\n" + " +\n".join(sublines) + "\n        )")
    return "arrayOf(\n        " + ",\n        ".join(formatted_chunks) + "\n    )"

def serialize_forest(rf, num_classes):
    nodes = []
    leaf_probs = []
    tree_offsets = []
    
    for tree_idx, estimator in enumerate(rf.estimators_):
        tree = estimator.tree_
        tree_offsets.append(len(nodes))
        
        def build_node(node_id):
            curr_idx = len(nodes)
            nodes.append(None) # placeholder
            
            if tree.children_left[node_id] == -1: # Leaf
                val = tree.value[node_id][0]
                prob = val / val.sum()
                prob_idx = len(leaf_probs) // num_classes
                leaf_probs.extend(prob.tolist())
                
                nodes[curr_idx] = {
                    'feature': -1,
                    'threshold': 0.0,
                    'left_child': prob_idx,
                    'right_child': 0
                }
            else:
                feat = tree.feature[node_id]
                thresh = tree.threshold[node_id]
                left_node_id = tree.children_left[node_id]
                right_node_id = tree.children_right[node_id]
                
                # Recurse
                left_child_idx = build_node(left_node_id)
                right_child_idx = build_node(right_node_id)
                
                nodes[curr_idx] = {
                    'feature': feat,
                    'threshold': thresh,
                    'left_child': left_child_idx,
                    'right_child': right_child_idx
                }
            return curr_idx
            
        build_node(0)

    feature_indices_hex = "".join(f"{n['feature'] & 0xFF:02x}" for n in nodes)
    thresholds_hex = "".join(struct.pack('>f', n['threshold']).hex() for n in nodes)
    left_children_hex = "".join(struct.pack('>i', n['left_child']).hex() for n in nodes)
    right_children_hex = "".join(struct.pack('>i', n['right_child']).hex() for n in nodes)
    tree_offsets_hex = "".join(struct.pack('>i', o).hex() for o in tree_offsets)
    leaf_probabilities_hex = "".join(struct.pack('>f', p).hex() for p in leaf_probs)

    return {
        "num_trees": rf.n_estimators,
        "feature_indices_hex": feature_indices_hex,
        "thresholds_hex": thresholds_hex,
        "left_children_hex": left_children_hex,
        "right_children_hex": right_children_hex,
        "tree_offsets_hex": tree_offsets_hex,
        "leaf_probabilities_hex": leaf_probabilities_hex
    }

def transpile_to_kotlin(hex_data, class_names, file_path, class_name):
    num_classes = len(class_names)
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    with open(file_path, 'w') as f:
        f.write("// Generated Random Forest Classifier for Cricket Batting Tracker\n")
        f.write("package com.mrpeel.cricketbattingtracker.ml\n\n")
        f.write("import java.nio.ByteBuffer\n")
        f.write("import java.nio.ByteOrder\n\n")
        
        # Write object header
        f.write(f"object {class_name} {{\n")
        f.write("    private val CLASSES = arrayOf(\n")
        for name in class_names:
            f.write(f"        \"{name}\",\n")
        f.write("    )\n\n")
        
        f.write(f"    const val NUM_TREES = {hex_data['num_trees']}\n\n")
        
        f.write("    private val FEATURE_INDICES_HEX = " + to_kotlin_string_array(hex_data['feature_indices_hex']) + "\n\n")
        f.write("    private val THRESHOLDS_HEX = " + to_kotlin_string_array(hex_data['thresholds_hex']) + "\n\n")
        f.write("    private val LEFT_CHILDREN_HEX = " + to_kotlin_string_array(hex_data['left_children_hex']) + "\n\n")
        f.write("    private val RIGHT_CHILDREN_HEX = " + to_kotlin_string_array(hex_data['right_children_hex']) + "\n\n")
        f.write("    private val TREE_OFFSETS_HEX = " + to_kotlin_string_array(hex_data['tree_offsets_hex']) + "\n\n")
        f.write("    private val LEAF_PROBABILITIES_HEX = " + to_kotlin_string_array(hex_data['leaf_probabilities_hex']) + "\n\n")
        
        f.write("    private val FEATURE_INDICES = decodeHexToByteArray(FEATURE_INDICES_HEX)\n")
        f.write("    private val THRESHOLDS = decodeHexToFloatArray(THRESHOLDS_HEX)\n")
        f.write("    private val LEFT_CHILDREN = decodeHexToIntArray(LEFT_CHILDREN_HEX)\n")
        f.write("    private val RIGHT_CHILDREN = decodeHexToIntArray(RIGHT_CHILDREN_HEX)\n")
        f.write("    private val TREE_OFFSETS = decodeHexToIntArray(TREE_OFFSETS_HEX)\n")
        f.write("    private val LEAF_PROBABILITIES = decodeHexToFloatArray(LEAF_PROBABILITIES_HEX)\n\n")
        
        f.write("    fun predict(f: SwingFeatures): String {\n")
        f.write(f"        val votes = FloatArray({num_classes})\n")
        f.write("        val features = floatArrayOf(\n")
        f.write("            // 14 watch features\n")
        f.write("            f.s1_gyro_y_std, f.s1_gyro_z_std, f.s1_deltaX, f.s1_deltaZ,\n")
        f.write("            f.s2_gyroMag, f.s2_grav_y_mean, f.s2_deltaX, f.s2_deltaZ,\n")
        f.write("            f.s3_rollImpactDeg, f.s3_yawImpactDeg, f.s3_deltaX, f.s3_deltaZ,\n")
        f.write("            f.s3_planeRatio, f.s3_gyro_y_min,\n")
        f.write("            // 6 Polar bottom-hand features (0f when Polar absent)\n")
        f.write("            f.bottom_hand_gyro_peak, f.bottom_hand_acc_peak,\n")
        f.write("            f.bottom_hand_gyro_ratio, f.bottom_hand_acc_ratio,\n")
        f.write("            f.bottom_hand_time_lead_ms, f.bottom_hand_sync_score\n")
        f.write("        )\n\n")
        f.write("        for (t in 0 until NUM_TREES) {\n")
        f.write("            var nodeIdx = TREE_OFFSETS[t]\n")
        f.write("            while (true) {\n")
        f.write("                val feat = FEATURE_INDICES[nodeIdx].toInt()\n")
        f.write("                if (feat == -1 || feat == 255) {\n")
        f.write(f"                    val probIdx = LEFT_CHILDREN[nodeIdx] * {num_classes}\n")
        f.write(f"                    for (c in 0 until {num_classes}) {{\n")
        f.write("                        votes[c] += LEAF_PROBABILITIES[probIdx + c]\n")
        f.write("                    }\n")
        f.write("                    break\n")
        f.write("                }\n")
        f.write("                val valToCompare = features[feat]\n")
        f.write("                val threshold = THRESHOLDS[nodeIdx]\n")
        f.write("                nodeIdx = if (valToCompare <= threshold) {\n")
        f.write("                    LEFT_CHILDREN[nodeIdx]\n")
        f.write("                } else {\n")
        f.write("                    RIGHT_CHILDREN[nodeIdx]\n")
        f.write("                }\n")
        f.write("            }\n")
        f.write("        }\n\n")
        f.write("        var maxVal = -1f\n")
        f.write("        var maxIdx = 0\n")
        f.write(f"        for (i in 0 until {num_classes}) {{\n")
        f.write("            if (votes[i] > maxVal) {\n")
        f.write("                maxVal = votes[i]\n")
        f.write("                maxIdx = i\n")
        f.write("            }\n")
        f.write("        }\n")
        f.write("        return CLASSES[maxIdx]\n")
        f.write("    }\n\n")
        
        f.write("    private fun decodeHexToByteArray(hexStrings: Array<String>): ByteArray {\n")
        f.write("        val totalLength = hexStrings.sumOf { it.length } / 2\n")
        f.write("        val result = ByteArray(totalLength)\n")
        f.write("        var outIdx = 0\n")
        f.write("        for (s in hexStrings) {\n")
        f.write("            var i = 0\n")
        f.write("            while (i < s.length) {\n")
        f.write("                val high = Character.digit(s[i], 16)\n")
        f.write("                val low = Character.digit(s[i + 1], 16)\n")
        f.write("                result[outIdx++] = ((high shl 4) or low).toByte()\n")
        f.write("                i += 2\n")
        f.write("            }\n")
        f.write("        }\n")
        f.write("        return result\n")
        f.write("    }\n\n")
        
        f.write("    private fun decodeHexToFloatArray(hexStrings: Array<String>): FloatArray {\n")
        f.write("        val bytes = decodeHexToByteArray(hexStrings)\n")
        f.write("        val buffer = ByteBuffer.wrap(bytes).order(ByteOrder.BIG_ENDIAN)\n")
        f.write("        val result = FloatArray(bytes.size / 4)\n")
        f.write("        for (i in result.indices) {\n")
        f.write("            result[i] = buffer.float\n")
        f.write("        }\n")
        f.write("        return result\n")
        f.write("    }\n\n")
        
        f.write("    private fun decodeHexToIntArray(hexStrings: Array<String>): IntArray {\n")
        f.write("        val bytes = decodeHexToByteArray(hexStrings)\n")
        f.write("        val buffer = ByteBuffer.wrap(bytes).order(ByteOrder.BIG_ENDIAN)\n")
        f.write("        val result = IntArray(bytes.size / 4)\n")
        f.write("        for (i in result.indices) {\n")
        f.write("            result[i] = buffer.int\n")
        f.write("        }\n")
        f.write("        return result\n")
        f.write("    }\n")
        f.write("}\n")

def transpile_swing_features_class():
    """Ensure SwingFeatures data class is defined at wear/ml/SwingFeatures.kt,
    exposing both watch and Polar properties."""
    path = "/Users/neilkloot/Code/CricketBattingTracker/wear/src/main/java/com/mrpeel/cricketbattingtracker/ml/SwingFeatures.kt"
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write("""package com.mrpeel.cricketbattingtracker.ml

/**
 * Extracted kinematic swing features for machine learning models.
 * Exposes 14 watch-side fields and 6 Polar Sense (bottom hand) fields.
 * Polar fields have default values of 0f so watch-only inference works seamlessly.
 */
data class SwingFeatures(
    // 14 watch features (always populated)
    val s1_gyro_y_std: Float,
    val s1_gyro_z_std: Float,
    val s1_deltaX: Float,
    val s1_deltaZ: Float,
    val s2_gyroMag: Float,
    val s2_grav_y_mean: Float,
    val s2_deltaX: Float,
    val s2_deltaZ: Float,
    val s3_rollImpactDeg: Float,
    val s3_yawImpactDeg: Float,
    val s3_deltaX: Float,
    val s3_deltaZ: Float,
    val s3_planeRatio: Float,
    val s3_gyro_y_min: Float,
    // 6 Polar bottom-hand features (default 0f when Polar absent)
    val bottom_hand_gyro_peak: Float = 0f,
    val bottom_hand_acc_peak: Float = 0f,
    val bottom_hand_gyro_ratio: Float = 0f,
    val bottom_hand_acc_ratio: Float = 0f,
    val bottom_hand_time_lead_ms: Float = 0f,
    val bottom_hand_sync_score: Float = 0f
)
""")
    # Sync to app module
    app_path = "/Users/neilkloot/Code/CricketBattingTracker/app/src/main/java/com/mrpeel/cricketbattingtracker/ml/SwingFeatures.kt"
    os.makedirs(os.path.dirname(app_path), exist_ok=True)
    shutil.copy2(path, app_path)

def main():
    if not os.path.exists(FEATURES_CSV):
        print(f"❌ ERROR: Features CSV not found at {FEATURES_CSV}")
        return

    df = pd.read_csv(FEATURES_CSV)
    df_swings = df[df['normalized_gt'] != 'NON-SWING'].copy()
    
    X = df_swings[FEATURE_COLS].fillna(0.0)

    # 1. Train & Transpile SHOT TYPE Model
    print("\nTraining Shot Type Random Forest model...")
    y_type = df_swings['normalized_gt'].values
    le_type = LabelEncoder()
    y_type_enc = le_type.fit_transform(y_type)
    
    rf_type = RandomForestClassifier(
        n_estimators=200,
        max_depth=8,
        class_weight='balanced_subsample',
        random_state=42,
        n_jobs=-1
    )
    rf_type.fit(X, y_type_enc)
    
    print("Transpiling GeneratedForest.kt...")
    hex_type = serialize_forest(rf_type, len(le_type.classes_))
    transpile_swing_features_class()
    transpile_to_kotlin(hex_type, list(le_type.classes_), OUTPUT_TYPE_WEAR, "GeneratedForest")
    os.makedirs(os.path.dirname(OUTPUT_TYPE_APP), exist_ok=True)
    shutil.copy2(OUTPUT_TYPE_WEAR, OUTPUT_TYPE_APP)
    print("✅ Transpiled GeneratedForest.kt to both modules.")

    # 2. Train & Transpile SHOT QUALITY Model
    print("\nTraining Shot Quality Random Forest model...")
    # Drop rows that don't have quality populated or are NON-SWING
    df_quality = df_swings[df_swings['quality'].notna() & (df_swings['quality'] != '')].copy()
    
    # Standardize quality labels
    def clean_quality(q):
        val = str(q).lower().strip()
        if "good" in val or "okay" in val or "ok" in val or "excellent" in val:
            return "good"
        if "poor" in val or "bad" in val:
            return "poor"
        if "miss" in val:
            return "miss"
        if "edge" in val:
            return "edge"
        return "good" # default fallback
        
    y_qual = df_quality['quality'].apply(clean_quality).values
    X_qual = df_quality[FEATURE_COLS].fillna(0.0)

    le_qual = LabelEncoder()
    y_qual_enc = le_qual.fit_transform(y_qual)
    
    rf_qual = RandomForestClassifier(
        n_estimators=100,
        max_depth=6,
        class_weight='balanced_subsample',
        random_state=42,
        n_jobs=-1
    )
    rf_qual.fit(X_qual, y_qual_enc)
    
    print("Transpiling GeneratedQualityForest.kt...")
    hex_qual = serialize_forest(rf_qual, len(le_qual.classes_))
    transpile_to_kotlin(hex_qual, list(le_qual.classes_), OUTPUT_QUALITY_WEAR, "GeneratedQualityForest")
    os.makedirs(os.path.dirname(OUTPUT_QUALITY_APP), exist_ok=True)
    shutil.copy2(OUTPUT_QUALITY_WEAR, OUTPUT_QUALITY_APP)
    print("✅ Transpiled GeneratedQualityForest.kt to both modules.")

    # 3. Export optimized detection config
    print("\nSyncing optimized detection thresholds...")
    watch_gyro_threshold = 1.5 # default
    if os.path.exists(CONFIG_JSON):
        try:
            with open(CONFIG_JSON, "r") as jf:
                cfg = json.load(jf)
                watch_gyro_threshold = cfg.get("WATCH_GYRO_THRESHOLD", 1.5)
            print(f"  * Loaded optimized watch gyro threshold from JSON: {watch_gyro_threshold:.2f} rad/s")
        except Exception as e:
            print(f"⚠️ Failed to parse {CONFIG_JSON}, using default threshold: {e}")
    else:
        print("  * optimized_detection_config.json not found — using default threshold")

    # Write ShotEnhancementConfig.kt
    os.makedirs(os.path.dirname(OUTPUT_CONFIG_APP), exist_ok=True)
    with open(OUTPUT_CONFIG_APP, "w") as f:
        f.write(f"""package com.mrpeel.cricketbattingtracker.services

/**
 * Auto-generated by generate_kotlin_forest.py
 * Contains optimized bottom-hand reclassification and shockwave thresholds.
 */
object ShotEnhancementConfig {{
    const val POLAR_SHOCKWAVE_THRESHOLD = 24.5f
    const val WATCH_SHOCKWAVE_THRESHOLD = {watch_gyro_threshold:.4f}f
}}
""")
    print(f"✅ Generated ShotEnhancementConfig.kt at: {OUTPUT_CONFIG_APP}")

    # 4. Update proposed_logic_aligned.csv
    print(f"\nOverwriting {PROPOSED_CSV_PATH} with 20-feature RF predictions...")
    y_pred = rf_type.predict(X)
    proposed_preds = le_type.inverse_transform(y_pred)
    
    combined_gt_path = os.path.join(BASE_DIR, "combined_ground_truth_aligned.csv")
    if os.path.exists(combined_gt_path):
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
        if 'predicted_shot_type' in cols:
            cols.remove('predicted_shot_type')
        if 'is_correct' in cols:
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
