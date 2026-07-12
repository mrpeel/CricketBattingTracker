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
    
    # 14 Segmented temporal features
    features = [
        's1_gyro_y_std', 's1_gyro_z_std', 's1_deltaX', 's1_deltaZ',
        's2_gyroMag', 's2_grav_y_mean', 's2_deltaX', 's2_deltaZ',
        's3_rollImpactDeg', 's3_yawImpactDeg', 's3_deltaX', 's3_deltaZ',
        's3_planeRatio', 's3_gyro_y_min'
    ]
    
    X = df_swings[features].fillna(df_swings[features].median())
    y = df_swings['normalized_gt'].values
    
    le = LabelEncoder()
    y_enc = le.fit_transform(y)
    class_names = list(le.classes_)
    
    print(f"Class names matching LabelEncoder order: {class_names}")
    
    # Grid Search configurations to compare size/accuracy
    from sklearn.model_selection import cross_val_score, StratifiedKFold
    
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    configs = [
        {"n_estimators": 200, "max_depth": 8},
        {"n_estimators": 100, "max_depth": 7},
        {"n_estimators": 50, "max_depth": 6},
        {"n_estimators": 30, "max_depth": 6},
    ]
    
    results = []
    baseline_cv_acc = 0.0
    
    for config in configs:
        model = RandomForestClassifier(
            n_estimators=config["n_estimators"],
            max_depth=config["max_depth"],
            class_weight='balanced_subsample',
            random_state=42,
            n_jobs=-1
        )
        scores = cross_val_score(model, X, y_enc, cv=cv, scoring='accuracy')
        mean_score = np.mean(scores)
        
        # Fit to count nodes
        model.fit(X, y_enc)
        total_nodes = sum(t.tree_.node_count for t in model.estimators_)
        
        results.append({
            "config": config,
            "cv_acc": mean_score,
            "nodes": total_nodes,
            "model": model
        })
        
        if config["n_estimators"] == 200 and config["max_depth"] == 8:
            baseline_cv_acc = mean_score
            
    print("\nModel Variants Evaluation:")
    for r in results:
        print(f" - {r['config']}: CV Accuracy = {r['cv_acc']:.4f}, Total Nodes = {r['nodes']}")
        
    # Select smallest where CV accuracy drop is within 0.5% (0.005)
    allowed_min_acc = baseline_cv_acc - 0.005
    selected_r = None
    for r in sorted(results, key=lambda x: x["nodes"]):
        if r["cv_acc"] >= allowed_min_acc:
            selected_r = r
            break
            
    if selected_r is None:
        selected_r = results[0]
        
    print(f"\nSelected Config: {selected_r['config']} (CV Accuracy: {selected_r['cv_acc']:.4f}, Nodes: {selected_r['nodes']})")
    rf = selected_r["model"]
    
    num_classes = len(class_names)
    
    # DFS tree serialization
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

    # Encode arrays as big-endian hex strings
    import struct
    
    feature_indices_hex = "".join(f"{n['feature'] & 0xFF:02x}" for n in nodes)
    thresholds_hex = "".join(struct.pack('>f', n['threshold']).hex() for n in nodes)
    left_children_hex = "".join(struct.pack('>i', n['left_child']).hex() for n in nodes)
    right_children_hex = "".join(struct.pack('>i', n['right_child']).hex() for n in nodes)
    tree_offsets_hex = "".join(struct.pack('>i', o).hex() for o in tree_offsets)
    leaf_probabilities_hex = "".join(struct.pack('>f', p).hex() for p in leaf_probs)

    def to_kotlin_string_array(hex_str, chunk_char_limit=16000):
        chunks = [hex_str[i:i+chunk_char_limit] for i in range(0, len(hex_str), chunk_char_limit)]
        formatted_chunks = []
        for chunk in chunks:
            sublines = [f'            "{chunk[j:j+100]}"' for j in range(0, len(chunk), 100)]
            formatted_chunks.append("(\n" + " +\n".join(sublines) + "\n        )")
        return "arrayOf(\n        " + ",\n        ".join(formatted_chunks) + "\n    )"

    # Transpile the forest to Kotlin
    print(f"Generating Kotlin Random Forest in {OUTPUT_KOTLIN}...")
    os.makedirs(os.path.dirname(OUTPUT_KOTLIN), exist_ok=True)
    
    with open(OUTPUT_KOTLIN, 'w') as f:
        # Write file header
        f.write("// Generated Random Forest Classifier for Cricket Batting Tracker\n")
        f.write(f"// Trained on {len(df_swings)} swings across {df_swings['session_id'].nunique()} trustworthy sessions\n")
        f.write(f"// Selected hyperparameter configuration: {selected_r['config']}\n")
        f.write("package com.mrpeel.cricketbattingtracker.ml\n\n")
        f.write("import java.nio.ByteBuffer\n")
        f.write("import java.nio.ByteOrder\n\n")
        
        # Write data class
        f.write("data class SwingFeatures(\n")
        for feat in features:
            f.write(f"    val {feat}: Float,\n")
        f.seek(f.tell() - 2)
        f.write("\n)\n\n")
        
        # Write object header
        f.write("object GeneratedForest {\n")
        f.write("    private val CLASSES = arrayOf(\n")
        for name in class_names:
            f.write(f"        \"{name}\",\n")
        f.write("    )\n\n")
        
        f.write(f"    const val NUM_TREES = {rf.n_estimators}\n\n")
        
        # Write Hex string constants
        f.write("    private val FEATURE_INDICES_HEX = " + to_kotlin_string_array(feature_indices_hex) + "\n\n")
        f.write("    private val THRESHOLDS_HEX = " + to_kotlin_string_array(thresholds_hex) + "\n\n")
        f.write("    private val LEFT_CHILDREN_HEX = " + to_kotlin_string_array(left_children_hex) + "\n\n")
        f.write("    private val RIGHT_CHILDREN_HEX = " + to_kotlin_string_array(right_children_hex) + "\n\n")
        f.write("    private val TREE_OFFSETS_HEX = " + to_kotlin_string_array(tree_offsets_hex) + "\n\n")
        f.write("    private val LEAF_PROBABILITIES_HEX = " + to_kotlin_string_array(leaf_probabilities_hex) + "\n\n")
        
        # Write decoded flat arrays (initialized once during class loading)
        f.write("    private val FEATURE_INDICES = decodeHexToByteArray(FEATURE_INDICES_HEX)\n")
        f.write("    private val THRESHOLDS = decodeHexToFloatArray(THRESHOLDS_HEX)\n")
        f.write("    private val LEFT_CHILDREN = decodeHexToIntArray(LEFT_CHILDREN_HEX)\n")
        f.write("    private val RIGHT_CHILDREN = decodeHexToIntArray(RIGHT_CHILDREN_HEX)\n")
        f.write("    private val TREE_OFFSETS = decodeHexToIntArray(TREE_OFFSETS_HEX)\n")
        f.write("    private val LEAF_PROBABILITIES = decodeHexToFloatArray(LEAF_PROBABILITIES_HEX)\n\n")
        
        # Write main predict method
        f.write("    fun predict(f: SwingFeatures): String {\n")
        f.write(f"        val votes = FloatArray({num_classes})\n")
        f.write("        val features = floatArrayOf(\n")
        f.write("            f.s1_gyro_y_std, f.s1_gyro_z_std, f.s1_deltaX, f.s1_deltaZ,\n")
        f.write("            f.s2_gyroMag, f.s2_grav_y_mean, f.s2_deltaX, f.s2_deltaZ,\n")
        f.write("            f.s3_rollImpactDeg, f.s3_yawImpactDeg, f.s3_deltaX, f.s3_deltaZ,\n")
        f.write("            f.s3_planeRatio, f.s3_gyro_y_min\n")
        f.write("        )\n\n")
        f.write("        for (t in 0 until NUM_TREES) {\n")
        f.write("            var nodeIdx = TREE_OFFSETS[t]\n")
        f.write("            while (true) {\n")
        f.write("                val feat = FEATURE_INDICES[nodeIdx].toInt()\n")
        f.write("                if (feat == -1 || feat == 255) {\n") # handle unsigned/signed byte conversion
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
        
        # Write hex decoding helpers
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
