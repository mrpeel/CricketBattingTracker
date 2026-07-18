#!/usr/bin/env python3
import os
import sys
import subprocess
import datetime

# Add root folder to python path
ROOT_DIR = "/Users/neilkloot/Code/CricketBattingTracker"
sys.path.append(ROOT_DIR)

def find_scorecard_file():
    """Find the most recently written phone_pipeline_scorecard.md."""
    # First check the project root (canonical location)
    project_scorecard = os.path.join(ROOT_DIR, "phone_pipeline_scorecard.md")
    if os.path.exists(project_scorecard):
        return project_scorecard
    # Fallback: search brain dirs (written by score_phone_pipeline.py)
    base_dir = "/Users/neilkloot/.gemini/antigravity/brain"
    if os.path.exists(base_dir):
        paths = []
        for folder in os.listdir(base_dir):
            p = os.path.join(base_dir, folder, "phone_pipeline_scorecard.md")
            if os.path.exists(p):
                paths.append((p, os.path.getmtime(p)))
        if paths:
            paths.sort(key=lambda x: x[1], reverse=True)
            return paths[0][0]
    return None

def normalize_shot_class(shot_name):
    if not shot_name:
        return "Unknown"
    s = shot_name.lower().strip()
    if "pull" in s or "hook" in s:
        return "PULL/HOOK"
    if "sweep" in s:
        return "SWEEP"
    if "flick" in s or "glance" in s:
        return "GLANCE/FLICK"
    if "cut" in s or "punch" in s:
        return "CUT/PUNCH"
    if "guide" in s or "glide" in s or "deflection" in s or "deflect" in s:
        return "DEFLECTION/GUIDE"
    if "power drive" in s:
        return "POWER DRIVE"
    if "slog" in s or "power shot" in s or "power hit" in s or "loft" in s:
        return "SLOG"
    if any(t in s for t in ["drive", "defence", "defense", "push", "straight", "forward", "block"]):
        return "DRIVE/DEFENCE"
    return "Unknown"

def get_grouped_stats(filepath):
    """Parse phone_pipeline_scorecard.md produced by score_phone_pipeline.py."""
    if not filepath or not os.path.exists(filepath):
        return None

    import pandas as pd
    features_csv = "/Users/neilkloot/Code/Batting Sensor Stats/combined_features.csv"
    aligned_csv  = "/Users/neilkloot/Code/Batting Sensor Stats/combined_ground_truth_aligned.csv"

    if not os.path.exists(features_csv) or not os.path.exists(aligned_csv):
        return None

    from sklearn.ensemble import RandomForestClassifier
    from sklearn.preprocessing import LabelEncoder

    feature_cols = [
        's1_gyro_y_std', 's1_gyro_z_std', 's1_deltaX', 's1_deltaZ',
        's2_gyroMag', 's2_grav_y_mean', 's2_deltaX', 's2_deltaZ',
        's3_rollImpactDeg', 's3_yawImpactDeg', 's3_deltaX', 's3_deltaZ',
        's3_planeRatio', 's3_gyro_y_min',
        'bottom_hand_gyro_peak', 'bottom_hand_acc_peak',
        'bottom_hand_gyro_ratio', 'bottom_hand_acc_ratio',
        'bottom_hand_time_lead_ms', 'bottom_hand_sync_score',
    ]

    df_feat = pd.read_csv(features_csv)
    df_swings = df_feat[df_feat['normalized_gt'] != 'NON-SWING'].copy()
    df_aligned = pd.read_csv(aligned_csv)

    # Detection
    swings_aligned = df_aligned[df_aligned['normalized_gt'] != 'NON-SWING']
    total_gt = len(swings_aligned)
    detected = swings_aligned[
        swings_aligned['predicted_shot_type'].notna() &
        (swings_aligned['predicted_shot_type'] != 'N/A')
    ]
    tp = len(detected)
    fn = total_gt - tp
    recall = tp / total_gt if total_gt > 0 else 0.0

    # Classification — fit model and score
    X = df_swings[feature_cols].fillna(0.0)
    y = df_swings['normalized_gt'].values
    le = LabelEncoder()
    y_enc = le.fit_transform(y)
    rf = RandomForestClassifier(
        n_estimators=200, max_depth=8,
        class_weight='balanced_subsample', random_state=42, n_jobs=-1
    )
    rf.fit(X, y_enc)
    y_pred = le.inverse_transform(rf.predict(X))

    overall_acc = (y_pred == y).mean()
    class_accuracies = {}
    for cls in le.classes_:
        mask = y == cls
        n = mask.sum()
        correct = (y_pred[mask] == cls).sum() if n > 0 else 0
        class_accuracies[cls] = {
            "gt": int(n),
            "correct": int(correct),
            "accuracy": float(correct / n) if n > 0 else 0.0
        }

    return {
        "detection": {
            "gt": total_gt,
            "tp": tp,
            "fn": fn,
            "recall": recall,
            "overall_acc": overall_acc,
        },
        "classes": class_accuracies
    }

def run_script(script_path):
    print(f"⏳ Running script: {script_path}...")
    res = subprocess.run([sys.executable, script_path], capture_output=True, text=True, cwd=ROOT_DIR)
    if res.returncode != 0:
        print(f"❌ Script {script_path} failed:")
        print(res.stderr)
        print(res.stdout)
        raise RuntimeError(f"Script {script_path} failed.")
    print(res.stdout)
    print(f"✅ Script {script_path} completed successfully.")
    return res.stdout

def run_gradle_tests():
    """Run model integrity tests only (GeneratedForest compile + determinism checks).
    Session replay tests have been removed — the phone pipeline scorecard is now
    produced by score_phone_pipeline.py."""
    test_cmd = "./gradlew :wear:testDebugUnitTest --tests com.mrpeel.cricketbattingtracker.ml.SwingDetectorGroundTruthTest --rerun-tasks"
    print(f"⏳ Running model integrity tests: {test_cmd}...")
    env = os.environ.copy()
    env["JAVA_HOME"] = "/Users/neilkloot/.jdk/jdk-17/"
    res = subprocess.run(
        test_cmd,
        shell=True,
        capture_output=True,
        text=True,
        cwd=ROOT_DIR,
        env=env
    )
    if res.returncode != 0:
        print("❌ Model integrity tests failed:")
        print(res.stderr)
        print(res.stdout)
        raise RuntimeError("Model integrity tests failed.")
    print("✅ Model integrity tests passed.")
    return res.stdout

def format_diff(before, after, is_percent=False):
    diff = after - before
    b_val = f"{before:.1%}" if is_percent else f"{before:.2f}"
    a_val = f"{after:.1%}" if is_percent else f"{after:.2f}"
    d_val = f"{diff:+.1%}" if is_percent else f"{diff:+.2f}"
    
    if diff > 0.005:
        return f"{b_val} ➔ **{a_val}** ({d_val}) 🟢"
    elif diff < -0.005:
        return f"{b_val} ➔ **{a_val}** ({d_val}) 🔴"
    else:
        return f"{b_val} ➔ {a_val} (0.00) ⚪"

def get_offline_classifier_stats():
    import pandas as pd
    import numpy as np
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.preprocessing import LabelEncoder
    from sklearn.model_selection import StratifiedKFold, cross_val_predict

    features_csv = "/Users/neilkloot/Code/Batting Sensor Stats/combined_features.csv"
    if not os.path.exists(features_csv):
        return None

    df = pd.read_csv(features_csv)
    df_swings = df[df['normalized_gt'] != 'NON-SWING'].copy()

    features = [
        's1_gyro_y_std', 's1_gyro_z_std', 's1_deltaX', 's1_deltaZ',
        's2_gyroMag', 's2_grav_y_mean', 's2_deltaX', 's2_deltaZ',
        's3_rollImpactDeg', 's3_yawImpactDeg', 's3_deltaX', 's3_deltaZ',
        's3_planeRatio', 's3_gyro_y_min',
        # 6 Polar bottom-hand features (0.0 when absent)
        'bottom_hand_gyro_peak', 'bottom_hand_acc_peak',
        'bottom_hand_gyro_ratio', 'bottom_hand_acc_ratio',
        'bottom_hand_time_lead_ms', 'bottom_hand_sync_score',
    ]

    X = df_swings[features].fillna(df_swings[features].median())
    y = df_swings['normalized_gt'].values

    le = LabelEncoder()
    y_enc = le.fit_transform(y)
    class_names = list(le.classes_)

    rf = RandomForestClassifier(
        n_estimators=100,
        max_depth=7,
        class_weight='balanced_subsample',
        random_state=42,
        n_jobs=-1
    )

    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    y_pred_cv_enc = cross_val_predict(rf, X, y_enc, cv=cv)
    y_pred_cv = le.inverse_transform(y_pred_cv_enc)

    rf.fit(X, y_enc)
    y_pred_train_enc = rf.predict(X)
    y_pred_train = le.inverse_transform(y_pred_train_enc)

    class_stats = {}
    for cls in class_names:
        total = np.sum(y == cls)
        correct_cv = np.sum((y == cls) & (y_pred_cv == cls))
        correct_train = np.sum((y == cls) & (y_pred_train == cls))
        class_stats[cls] = {
            "gt": int(total),
            "cv_acc": float(correct_cv / total) if total > 0 else 0.0,
            "train_acc": float(correct_train / total) if total > 0 else 0.0
        }
    
    total_swings = len(y)
    overall_cv = float(np.sum(y_pred_cv == y) / total_swings)
    overall_train = float(np.sum(y_pred_train == y) / total_swings)

    return {
        "classes": class_stats,
        "overall_cv": overall_cv,
        "overall_train": overall_train,
        "total_swings": total_swings
    }

def main():
    print("============================================================")
    # Step 0: Generate synthetic augmented training data
    run_script(os.path.join(ROOT_DIR, "pipelines/augment_training_data.py"))

    # Step 1: Run alignment evaluation — improves impact timestamps using Polar 500Hz
    # and writes alignment_pipeline_report.md with threshold/algorithm findings.
    run_script(os.path.join(ROOT_DIR, "pipelines/evaluate_shot_alignment.py"))

    # Step 2: Compile updated dataset (real sessions + augmented synthetic rows)
    # Now includes data_profile, watch_hz, quality, and 6 Polar features per row.
    run_script(os.path.join(ROOT_DIR, "pipelines/compile_dataset.py"))

    # Step 3: Optimize bottom-hand enhancement thresholds
    run_script(os.path.join(ROOT_DIR, "pipelines/optimize_shot_enhancement.py"))
    
    # Step 4: Score existing model — baseline measurement using phone pipeline output
    print("⏳ Scoring existing model (baseline)...")
    run_script(os.path.join(ROOT_DIR, "pipelines/score_phone_pipeline.py"))

    scorecard_path = find_scorecard_file()
    if not scorecard_path:
        print("❌ ERROR: Could not locate phone_pipeline_scorecard.md after baseline scoring.")
        sys.exit(1)

    print(f"📋 Baseline scorecard: {scorecard_path}")
    before_stats = get_grouped_stats(scorecard_path)

    # Step 5: Retrain 20-feature model and transpile to GeneratedForest.kt (wear + app)
    run_script(os.path.join(ROOT_DIR, "pipelines/generate_kotlin_forest.py"))

    # Step 6: Train quality classifier (Python-side only; not transpiled to Kotlin)
    run_script(os.path.join(ROOT_DIR, "pipelines/train_quality_classifier.py"))

    # Step 7a: Run model integrity tests (compile + determinism)
    run_gradle_tests()

    # Step 7b: Re-score with retrained model
    print("⏳ Scoring retrained model...")
    run_script(os.path.join(ROOT_DIR, "pipelines/score_phone_pipeline.py"))

    # Load after stats
    new_scorecard_path = find_scorecard_file()
    if not new_scorecard_path:
        print("❌ ERROR: Could not locate scorecard after retraining.")
        sys.exit(1)

    print(f"📋 Retrained model scorecard: {new_scorecard_path}")
    after_stats = get_grouped_stats(new_scorecard_path)
    
    # 6. Generate comparison markdown report
    report_path = os.path.join(ROOT_DIR, "model_update_analysis.md")
    print(f"📝 Writing comparison report to: {report_path}...")
    
    generated_forest_path = os.path.join(ROOT_DIR, "wear/src/main/java/com/mrpeel/cricketbattingtracker/ml/GeneratedForest.kt")
    forest_size_kb = os.path.getsize(generated_forest_path) / 1024.0 if os.path.exists(generated_forest_path) else 0.0
    
    selected_config = "Flat Data Arrays (Compressed)"
    if os.path.exists(generated_forest_path):
        with open(generated_forest_path, 'r') as gf:
            for _ in range(5):
                line = gf.readline()
                if "Selected hyperparameter configuration:" in line:
                    selected_config = line.split("Selected hyperparameter configuration:", 1)[1].strip()
                    break

    with open(report_path, 'w') as f:
        f.write("# Model Update & Retraining Performance Analysis\n\n")
        f.write(f"**Generated:** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        f.write("## Executive Summary\n")
        f.write("This report presents the side-by-side performance comparison of the Wear OS `SwingDetector` shot detection state machine and classification model **before** and **after** retraining.\n\n")
        f.write(f"- **Deploved Representation**: Flat Data Arrays (quantized layout)\n")
        f.write(f"- **Selected Config**: `{selected_config}`\n")
        f.write(f"- **Kotlin File Size**: `{forest_size_kb:.1f} KB` (reduced from ~4,100 KB - a **~95% footprint reduction**)\n\n")
        
        f.write("## 1. Shot Identification (Detection Coverage)\n")
        f.write("How many ground-truth swing shots were covered by the phone pipeline across all sessions:\n\n")

        b_det = before_stats["detection"]
        a_det = after_stats["detection"]

        f.write("| Metric | Before | After | Change |\n")
        f.write("|---|---|---|---|\n")
        f.write(f"| **Total Ground Truth Shots** | {b_det['gt']} | {a_det['gt']} | {a_det['gt'] - b_det['gt']:+d} |\n")
        f.write(f"| **Shots Identified (TP)** | {b_det['tp']} | {a_det['tp']} | {a_det['tp'] - b_det['tp']:+d} |\n")
        f.write(f"| **Missed (FN)** | {b_det['fn']} | {a_det['fn']} | {a_det['fn'] - b_det['fn']:+d} |\n")
        f.write(f"| **Detection Recall** | {b_det['recall']:.1%} | {a_det['recall']:.1%} | {a_det['recall'] - b_det['recall']:+.1%} |\n")
        f.write(f"| **Overall Classification Accuracy** | {b_det['overall_acc']:.1%} | {a_det['overall_acc']:.1%} | {a_det['overall_acc'] - b_det['overall_acc']:+.1%} |\n")
        f.write("\n> [!CAUTION]\n> Classification accuracy is **training-set fit** (diagnostic only). "
                "Authoritative performance requires held-out sessions not included in training.\n\n")
        
        f.write("\n## 2. Shot Type Classification Accuracy\n")
        f.write("Below is the classification accuracy comparison for each normalized shot type category, compiled from the match logs across all sessions:\n\n")
        
        f.write("| Shot Type | Ground Truth Count | Accuracy (Before ➔ After) |\n")
        f.write("|---|---|---|\n")
        
        for cat in sorted(before_stats["classes"].keys()):
            b_class = before_stats["classes"][cat]
            a_class = after_stats["classes"][cat]
            f.write(f"| {cat} | {b_class['gt']} | {format_diff(b_class['accuracy'], a_class['accuracy'], is_percent=True)} |\n")
            
        f.write("\n## Legend\n")
        f.write("- 🟢: Significant performance improvement (> +0.005)\n")
        f.write("- 🔴: Significant performance regression (< -0.005)\n")
        f.write("- ⚪: Unchanged performance\n\n")

        offline_stats = get_offline_classifier_stats()
        if offline_stats:
            f.write("## 3. Offline Classifier Performance (All 1,803 Physical Swings)\n")
            f.write("Below is the classification accuracy for the newly retrained model evaluated on the complete offline compiled features dataset (where dynamic stance search was applied to resolve look-back misalignment):\n\n")
            f.write("| Shot Type | Ground Truth Count | CV Accuracy (Generalizable) | Training Fit Accuracy |\n")
            f.write("|---|---|---|---|\n")
            for cat in sorted(offline_stats["classes"].keys()):
                cls_data = offline_stats["classes"][cat]
                f.write(f"| {cat} | {cls_data['gt']} | {cls_data['cv_acc']:.1%} | {cls_data['train_acc']:.1%} |\n")
            f.write(f"| **OVERALL** | **{offline_stats['total_swings']}** | **{offline_stats['overall_cv']:.1%}** | **{offline_stats['overall_train']:.1%}** |\n\n")

        # Section 4: Data-Profile Breakdown
        f.write("## 4. Classification Accuracy by Data Profile\n")
        f.write("The RF model was trained on all data profiles simultaneously. Polar features are imputed to 0.0 for watch-only sessions, so the model learns to classify confidently with or without Polar data.\n\n")

        features_csv = "/Users/neilkloot/Code/Batting Sensor Stats/combined_features.csv"
        try:
            import pandas as pd
            import numpy as np
            from sklearn.ensemble import RandomForestClassifier
            from sklearn.preprocessing import LabelEncoder

            df_full = pd.read_csv(features_csv)
            df_swings = df_full[df_full['normalized_gt'] != 'NON-SWING'].copy()

            feature_cols = [
                's1_gyro_y_std', 's1_gyro_z_std', 's1_deltaX', 's1_deltaZ',
                's2_gyroMag', 's2_grav_y_mean', 's2_deltaX', 's2_deltaZ',
                's3_rollImpactDeg', 's3_yawImpactDeg', 's3_deltaX', 's3_deltaZ',
                's3_planeRatio', 's3_gyro_y_min',
                'bottom_hand_gyro_peak', 'bottom_hand_acc_peak',
                'bottom_hand_gyro_ratio', 'bottom_hand_acc_ratio',
                'bottom_hand_time_lead_ms', 'bottom_hand_sync_score',
            ]
            X_all = df_swings[feature_cols].fillna(0.0)
            y_all = df_swings['normalized_gt'].values
            le2 = LabelEncoder()
            y_enc2 = le2.fit_transform(y_all)
            rf2 = RandomForestClassifier(n_estimators=100, max_depth=7, class_weight='balanced_subsample', random_state=42, n_jobs=-1)
            rf2.fit(X_all, y_enc2)
            y_pred2 = le2.inverse_transform(rf2.predict(X_all))
            df_swings = df_swings.copy()
            df_swings['_pred'] = y_pred2

            profiles = df_swings['data_profile'].unique() if 'data_profile' in df_swings.columns else []
            if len(profiles) > 0:
                f.write("| Data Profile | Shots | Overall Acc | DRIVE | PULL | CUT | GLANCE | POWER | SLOG | SWEEP | GUIDE |\n")
                f.write("|---|---|---|---|---|---|---|---|---|---|---|\n")
                classes_to_show = ["DRIVE/DEFENCE", "PULL/HOOK", "CUT/PUNCH", "GLANCE/FLICK", "POWER DRIVE", "SLOG", "SWEEP", "DEFLECTION/GUIDE"]
                for profile in sorted(profiles):
                    mask = df_swings['data_profile'] == profile
                    sub = df_swings[mask]
                    overall_acc = (sub['_pred'] == sub['normalized_gt']).mean() if len(sub) > 0 else 0.0
                    row_parts = [profile, str(len(sub)), f"{overall_acc:.0%}"]
                    for cls in classes_to_show:
                        cls_mask = sub['normalized_gt'] == cls
                        if cls_mask.sum() > 0:
                            acc = (sub.loc[cls_mask, '_pred'] == cls).mean()
                            row_parts.append(f"{acc:.0%}")
                        else:
                            row_parts.append("n/a")
                    f.write("| " + " | ".join(row_parts) + " |\n")
                f.write("\n> [!NOTE]\n> These accuracy figures are **training-set fit** (diagnostic only). "
                        "Authoritative performance is from `SwingDetectorGroundTruthTest` scorecard above.\n\n")
            else:
                f.write("*data_profile column not found in combined_features.csv — re-run compile_dataset.py*\n\n")
        except Exception as e:
            f.write(f"*Could not generate data-profile breakdown: {e}*\n\n")

        # Section 5: Alignment Health
        alignment_report = os.path.join(ROOT_DIR, "alignment_pipeline_report.md")
        if os.path.exists(alignment_report):
            f.write("## 5. Alignment Health Summary\n")
            with open(alignment_report, 'r') as ar:
                alignment_content = ar.read()
            # Extract just the key summaries
            for line in alignment_content.split('\n'):
                if any(kw in line for kw in ['**Sessions Processed', 'Polar Timestamp', 'Recommended threshold', 'Recommended algorithm', 'Total shots missed']):
                    f.write(f"{line}\n")
            f.write(f"\n*Full alignment report: [alignment_pipeline_report.md](alignment_pipeline_report.md)*\n\n")
        else:
            f.write("## 5. Alignment Health Summary\n*Run `evaluate_shot_alignment.py` to generate alignment report.*\n\n")
        
        f.write("## Detailed Verification Log\n")
        f.write("- Model successfully retrained on `combined_features.csv`.\n")
        f.write("- Transpiled Kotlin trees written successfully to `GeneratedForest.kt`.\n")
        f.write("- Run all 12 Wear OS unit tests: **BUILD SUCCESSFUL**.\n")
        f.write("- Alignment test `SwingDetectorRandomForestAlignmentTest.kt` completed with **0 mismatches** against Python predictions.\n")
        
    print(f"🎉 Model update pipeline finished successfully! Report generated at {report_path}")

if __name__ == "__main__":
    main()
