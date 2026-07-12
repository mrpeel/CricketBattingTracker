#!/usr/bin/env python3
import os
import sys
import glob
import pickle
import argparse
import numpy as np
import pandas as pd
import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score, confusion_matrix

# Biomechanical Angle Helper
def calculate_angle(p1, p2, p3):
    """Calculates the angle at p2 formed by p1-p2-p3 in 3D space."""
    v1 = np.array([p1.x - p2.x, p1.y - p2.y, p1.z - p2.z])
    v2 = np.array([p3.x - p2.x, p3.y - p2.y, p3.z - p2.z])
    
    norm1 = np.linalg.norm(v1)
    norm2 = np.linalg.norm(v2)
    if norm1 == 0 or norm2 == 0:
        return 0.0
        
    cosine_angle = np.dot(v1, v2) / (norm1 * norm2)
    cosine_angle = np.clip(cosine_angle, -1.0, 1.0)
    return np.degrees(np.arccos(cosine_angle))

# Feature Extraction Pipeline
def extract_features_from_video(video_path, detector):
    """
    Extracts camera-invariant joint angles and dense optical flow features from a video clip.
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return None

    # Load all frames first
    frames = []
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        frames.append(frame)
    cap.release()

    if len(frames) < 5:
        return None

    class MockLandmark:
        def __init__(self, x, y, z, presence=1.0, visibility=1.0):
            self.x = x
            self.y = y
            self.z = z
            self.presence = presence
            self.visibility = visibility

    # 1. Run Pose Detection on all frames
    raw_landmarks = []
    for frame in frames:
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
        results = detector.detect(mp_image)
        
        valid_pose = None
        if results.pose_landmarks and len(results.pose_landmarks) > 0:
            landmarks = results.pose_landmarks[0]
            if landmarks[23].presence > 0.5 and landmarks[24].presence > 0.5:
                valid_pose = landmarks
        raw_landmarks.append(valid_pose)

    # 2. Locate first and last valid frame indices (Live Window)
    valid_indices = [i for i, lm in enumerate(raw_landmarks) if lm is not None]
    if len(valid_indices) < 5:
        return None  # Discard as un-trackable or too short
        
    start_idx = valid_indices[0]
    end_idx = valid_indices[-1]

    # 3. Interpolate missing poses within the live window
    interpolated_landmarks = []
    for i in range(start_idx, end_idx + 1):
        if raw_landmarks[i] is not None:
            interpolated_landmarks.append(raw_landmarks[i])
        else:
            # Find nearest preceding valid frame
            p_idx = max([idx for idx in valid_indices if idx < i])
            # Find nearest succeeding valid frame
            s_idx = min([idx for idx in valid_indices if idx > i])
            
            p_lms = raw_landmarks[p_idx]
            s_lms = raw_landmarks[s_idx]
            ratio = (i - p_idx) / (s_idx - p_idx)
            
            # Linearly interpolate landmarks
            interp = []
            for j in range(len(p_lms)):
                pl = p_lms[j]
                sl = s_lms[j]
                x = pl.x * (1 - ratio) + sl.x * ratio
                y = pl.y * (1 - ratio) + sl.y * ratio
                z = pl.z * (1 - ratio) + sl.z * ratio
                pres = pl.presence * (1 - ratio) + sl.presence * ratio
                vis = pl.visibility * (1 - ratio) + sl.visibility * ratio
                interp.append(MockLandmark(x, y, z, pres, vis))
            interpolated_landmarks.append(interp)

    # 4. Extract features only for frames in the live window
    frames_features = []
    prev_gray = None
    
    for i, idx in enumerate(range(start_idx, end_idx + 1)):
        frame = frames[idx]
        landmarks = interpolated_landmarks[i]
        gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Calculate coordinate system origin and torso scale
        hip_l, hip_r = landmarks[23], landmarks[24]
        sh_l, sh_r = landmarks[11], landmarks[12]
        
        origin_x = (hip_l.x + hip_r.x) / 2.0
        origin_y = (hip_l.y + hip_r.y) / 2.0
        origin_z = (hip_l.z + hip_r.z) / 2.0
        
        torso_len = np.sqrt(
            ((sh_l.x + sh_r.x)/2.0 - origin_x)**2 +
            ((sh_l.y + sh_r.y)/2.0 - origin_y)**2
        )
        if torso_len <= 0:
            torso_len = 1.0
            
        frame_feat = {}
        # 8 camera-invariant biomechanical angles
        frame_feat["el_l_angle"] = calculate_angle(landmarks[11], landmarks[13], landmarks[15])
        frame_feat["el_r_angle"] = calculate_angle(landmarks[12], landmarks[14], landmarks[16])
        frame_feat["kn_l_angle"] = calculate_angle(landmarks[23], landmarks[25], landmarks[27])
        frame_feat["kn_r_angle"] = calculate_angle(landmarks[24], landmarks[26], landmarks[28])
        frame_feat["sh_l_angle"] = calculate_angle(landmarks[23], landmarks[11], landmarks[13])
        frame_feat["sh_r_angle"] = calculate_angle(landmarks[24], landmarks[12], landmarks[14])
        frame_feat["hip_l_angle"] = calculate_angle(landmarks[11], landmarks[23], landmarks[25])
        frame_feat["hip_r_angle"] = calculate_angle(landmarks[12], landmarks[24], landmarks[26])
        
        # Wrist positions relative to pelvis origin
        frame_feat["wr_l_x"] = (landmarks[15].x - origin_x) / torso_len
        frame_feat["wr_l_y"] = (landmarks[15].y - origin_y) / torso_len
        frame_feat["wr_r_x"] = (landmarks[16].x - origin_x) / torso_len
        frame_feat["wr_r_y"] = (landmarks[16].y - origin_y) / torso_len
        
        # Dense Optical Flow
        flow_mag_max = 0.0
        flow_dir_mean = 0.0
        if prev_gray is not None:
            flow = cv2.calcOpticalFlowFarneback(
                prev_gray, gray_frame, None,
                pyr_scale=0.5, levels=3, winsize=15,
                iterations=3, poly_n=5, poly_sigma=1.2, flags=0
            )
            mag, ang = cv2.cartToPolar(flow[..., 0], flow[..., 1])
            
            # Exclude human body mask from flow to isolate bat motion
            h, w = frame.shape[:2]
            xs = [lm.x * w for lm in landmarks if lm.presence > 0.5]
            ys = [lm.y * h for lm in landmarks if lm.presence > 0.5]
            if xs and ys:
                xmin, xmax = int(min(xs)), int(max(xs))
                ymin, ymax = int(min(ys)), int(max(ys))
                pad_w, pad_h = int((xmax - xmin) * 0.1), int((ymax - ymin) * 0.1)
                
                mask = np.ones(mag.shape, dtype=bool)
                y_start, y_end = max(0, ymin - pad_h), min(h, ymax + pad_h)
                x_start, x_end = max(0, xmin - pad_w), min(w, xmax + pad_w)
                mask[y_start:y_end, x_start:x_end] = False
                
                filtered_mag = mag[mask]
                filtered_ang = ang[mask]
                if len(filtered_mag) > 0:
                    flow_mag_max = float(np.max(filtered_mag))
                    fast_idx = np.where(filtered_mag >= 0.8 * flow_mag_max)[0]
                    if len(fast_idx) > 0:
                        flow_dir_mean = float(np.mean(filtered_ang[fast_idx]))
            else:
                flow_mag_max = float(np.max(mag))
                flow_dir_mean = float(np.mean(ang[mag >= 0.8 * flow_mag_max]))
                
        frame_feat["flow_mag_max"] = flow_mag_max
        frame_feat["flow_dir_mean"] = flow_dir_mean
        frames_features.append(frame_feat)
        prev_gray = gray_frame

    cap.release()
    
    if not frames_features:
        return None
        
    df_feat = pd.DataFrame(frames_features)
    summary = {}
    n_frames = len(df_feat)
    seg_size = n_frames // 3
    
    if seg_size >= 2:
        segments = {
            "seg1": df_feat.iloc[:seg_size],
            "seg2": df_feat.iloc[seg_size:2*seg_size],
            "seg3": df_feat.iloc[2*seg_size:]
        }
    else:
        segments = {"seg1": df_feat, "seg2": df_feat, "seg3": df_feat}
        
    for seg_name, df_seg in segments.items():
        if df_seg.empty:
            continue
            
        pose_cols = [c for c in df_seg.columns if c not in ["flow_mag_max", "flow_dir_mean"]]
        for col in pose_cols:
            summary[f"{seg_name}_{col}_mean"] = df_seg[col].mean()
            summary[f"{seg_name}_{col}_std"] = df_seg[col].std()
            summary[f"{seg_name}_{col}_range"] = df_seg[col].max() - df_seg[col].min()
            
        summary[f"{seg_name}_peak_flow_speed"] = df_seg["flow_mag_max"].max()
        summary[f"{seg_name}_mean_flow_speed"] = df_seg["flow_mag_max"].mean()
        
        if not df_seg["flow_mag_max"].empty:
            peak_flow_idx = df_seg["flow_mag_max"].idxmax()
            summary[f"{seg_name}_peak_flow_direction"] = df_seg.loc[peak_flow_idx, "flow_dir_mean"] if peak_flow_idx in df_seg.index else 0.0
        else:
            summary[f"{seg_name}_peak_flow_direction"] = 0.0
            
    summary["overall_peak_flow_speed"] = df_feat["flow_mag_max"].max()
    summary["overall_mean_flow_speed"] = df_feat["flow_mag_max"].mean()
    
    return summary

def process_cricshot10k(root_dir, detector, limit_per_class=None):
    """
    Processes the CricShot10k folders and extracts features.
    """
    X, y, file_paths = [], [], []
    classes = sorted([d for d in os.listdir(root_dir) if os.path.isdir(os.path.join(root_dir, d))])
    
    for cls in classes:
        class_dir = os.path.join(root_dir, cls)
        video_files = glob.glob(os.path.join(class_dir, "*.avi")) + glob.glob(os.path.join(class_dir, "*.mp4"))
        video_files = sorted(video_files)
        
        if limit_per_class:
            video_files = video_files[:limit_per_class]
            
        print(f"🎬  Processing: {cls:<15} | {len(video_files)} videos...")
        for v_path in video_files:
            feats = extract_features_from_video(v_path, detector)
            if feats is not None:
                X.append(feats)
                y.append(cls)
                file_paths.append(v_path)
                
    return pd.DataFrame(X), np.array(y), file_paths

# Hierarchical Taxonomy Definitions
FF_CLASSES = {
    "Cover Drive", "Defensive", "Down The Wicket", "Flick", 
    "Lofted Legside", "Lofted Offside", "Reverse Sweep", "Straight Drive", "Sweep"
}
BF_CLASSES = {
    "Hook", "Late Cut", "Pull", "Scoop", "Square Cut", "Upper Cut"
}
FF_DEFENSIVE = {"Defensive"}
BF_HIGH = {"Hook", "Pull", "Upper Cut"}

def get_hierarchical_targets(y):
    """Maps the 15 output classes to target structures at each hierarchy level."""
    y_ff_bf = np.array(["FF" if val in FF_CLASSES else "BF" for val in y])
    
    # FF subset targets
    ff_mask = (y_ff_bf == "FF")
    y_ff_def_att = np.array(["Defensive" if val in FF_DEFENSIVE else "Attacking" for val in y[ff_mask]])
    
    # BF subset targets
    bf_mask = (y_ff_bf == "BF")
    y_bf_high_low = np.array(["High" if val in BF_HIGH else "Low" for val in y[bf_mask]])
    
    return y_ff_bf, y_ff_def_att, y_bf_high_low

def main():
    parser = argparse.ArgumentParser(description="CricShot10k Hierarchical Classification Pipeline")
    parser.add_argument("--root-dir", default="/Users/neilkloot/Code/Batting Sensor Stats/cricshot10k/Videos", help="Path to dataset root")
    parser.add_argument("--cache-file", default="scratch/cricshot10k_features_cache.pkl", help="Path to cache extracted features")
    parser.add_argument("--limit-per-class", type=int, default=15, help="Limit videos per class for testing (default: 15)")
    parser.add_argument("--full", action="store_true", help="Process entire 10k dataset")
    parser.add_argument("--model-path", default="scratch/pose_landmarker_full.task", help="Path to pose landmarker task file")
    parser.add_argument("--results-file", default="scratch/cricshot10k_hierarchical_results.txt", help="Path to save evaluation results")
    args = parser.parse_args()

    os.makedirs(os.path.dirname(args.results_file), exist_ok=True)
    limit = None if args.full else args.limit_per_class
    cache_path = args.cache_file if not args.full else "scratch/cricshot10k_features_full_cache.pkl"

    # 1. Feature Extraction / Load from Cache
    if os.path.exists(cache_path):
        print(f"💾  Loading cached features from {cache_path}...")
        with open(cache_path, "rb") as f:
            X, y, file_paths = pickle.load(f)
    else:
        # Initialize detector
        base_options = python.BaseOptions(model_asset_path=args.model_path)
        options = vision.PoseLandmarkerOptions(base_options=base_options, output_segmentation_masks=False)
        detector = vision.PoseLandmarker.create_from_options(options)
        
        print(f"🎬  Extracting features from dataset (limit per class: {limit if limit else 'None'})...")
        X, y, file_paths = process_cricshot10k(args.root_dir, detector, limit_per_class=limit)
        
        # Save cache
        with open(cache_path, "wb") as f:
            pickle.dump((X, y, file_paths), f)
        print(f"💾  Saved features cache to {cache_path}")

    # Fill NaNs
    X = X.fillna(0.0)

    # 2. Random 80/20 Train/Test Split
    indices = np.arange(len(X))
    try:
        train_idx, test_idx = train_test_split(indices, test_size=0.20, random_state=42, stratify=y)
    except ValueError:
        print("⚠️  Warning: Test split size is smaller than class count. Falling back to non-stratified split.")
        train_idx, test_idx = train_test_split(indices, test_size=0.20, random_state=42)
    
    X_train, y_train = X.iloc[train_idx], y[train_idx]
    X_test, y_test = X.iloc[test_idx], y[test_idx]

    # Map hierarchical targets for training splits
    y_train_ff_bf, y_train_ff_def_att, y_train_bf_high_low = get_hierarchical_targets(y_train)

    print(f"\n🧠  Training Hierarchical Classifiers (Train: {len(X_train)} samples, Test: {len(X_test)} samples)...")

    # Step 1 Model: Front-Foot vs Back-Foot
    clf_ff_bf = RandomForestClassifier(n_estimators=150, max_depth=None, class_weight='balanced', random_state=42)
    clf_ff_bf.fit(X_train, y_train_ff_bf)

    # Step 2a Model: Front-Foot Defensive vs Attacking
    ff_train_mask = (y_train_ff_bf == "FF")
    clf_ff_def_att = RandomForestClassifier(n_estimators=150, max_depth=None, class_weight='balanced', random_state=42)
    clf_ff_def_att.fit(X_train[ff_train_mask], y_train_ff_def_att)

    # Step 2b Model: Back-Foot High-Swing vs Low-Swing
    bf_train_mask = (y_train_ff_bf == "BF")
    clf_bf_high_low = RandomForestClassifier(n_estimators=150, max_depth=None, class_weight='balanced', random_state=42)
    clf_bf_high_low.fit(X_train[bf_train_mask], y_train_bf_high_low)

    # Step 3a Model: FF Attacking Specific Shot
    ff_att_train_mask = ff_train_mask & (y_train != "Defensive")
    clf_ff_att_leaf = RandomForestClassifier(n_estimators=150, max_depth=None, class_weight='balanced', random_state=42)
    clf_ff_att_leaf.fit(X_train[ff_att_train_mask], y_train[ff_att_train_mask])

    # Step 3b Model: BF High Specific Shot
    bf_high_train_mask = bf_train_mask & np.isin(y_train, list(BF_HIGH))
    clf_bf_high_leaf = RandomForestClassifier(n_estimators=150, max_depth=None, class_weight='balanced', random_state=42)
    clf_bf_high_leaf.fit(X_train[bf_high_train_mask], y_train[bf_high_train_mask])

    # Step 3c Model: BF Low Specific Shot
    bf_low_train_mask = bf_train_mask & ~np.isin(y_train, list(BF_HIGH))
    clf_bf_low_leaf = RandomForestClassifier(n_estimators=150, max_depth=None, class_weight='balanced', random_state=42)
    clf_bf_low_leaf.fit(X_train[bf_low_train_mask], y_train[bf_low_train_mask])

    # 3. Evaluation Cycle
    print("📊  Evaluating full hierarchical pipeline...")
    y_pred = []
    
    for idx, row in X_test.iterrows():
        row_df = pd.DataFrame([row])
        
        # Step 1: Front vs Back
        ff_bf_pred = clf_ff_bf.predict(row_df)[0]
        
        if ff_bf_pred == "FF":
            # Step 2a: Defensive vs Attacking
            def_att_pred = clf_ff_def_att.predict(row_df)[0]
            if def_att_pred == "Defensive":
                y_pred.append("Defensive")
            else:
                # Step 3a: FF Attacking Specific
                y_pred.append(clf_ff_att_leaf.predict(row_df)[0])
        else:
            # Step 2b: High vs Low
            high_low_pred = clf_bf_high_low.predict(row_df)[0]
            if high_low_pred == "High":
                # Step 3b: BF High Specific
                y_pred.append(clf_bf_high_leaf.predict(row_df)[0])
            else:
                # Step 3c: BF Low Specific
                y_pred.append(clf_bf_low_leaf.predict(row_df)[0])

    y_pred = np.array(y_pred)
    acc = accuracy_score(y_test, y_pred)
    report_str = classification_report(y_test, y_pred, zero_division=0)
    matrix_str = str(confusion_matrix(y_test, y_pred))

    # Calculate sub-model validation accuracies on Test split
    y_test_ff_bf, y_test_ff_def_att, y_test_bf_high_low = get_hierarchical_targets(y_test)
    
    # Model 1 Acc
    m1_pred = clf_ff_bf.predict(X_test)
    m1_acc = accuracy_score(y_test_ff_bf, m1_pred)
    
    # Model 2a Acc
    ff_test_mask = (y_test_ff_bf == "FF")
    if np.any(ff_test_mask):
        m2a_pred = clf_ff_def_att.predict(X_test[ff_test_mask])
        m2a_acc = accuracy_score(y_test_ff_def_att, m2a_pred)
    else:
        m2a_acc = 0.0
    
    # Model 2b Acc
    bf_test_mask = (y_test_ff_bf == "BF")
    if np.any(bf_test_mask):
        m2b_pred = clf_bf_high_low.predict(X_test[bf_test_mask])
        m2b_acc = accuracy_score(y_test_bf_high_low, m2b_pred)
    else:
        m2b_acc = 0.0

    results_content = f"""CricShot10k Hierarchical Evaluation Results
============================================================
Total Train Samples: {len(X_train)}
Total Test Samples : {len(X_test)}
Overall Accuracy   : {acc*100:.2f}%

Sub-Classifier Test Accuracies:
------------------------------------------------------------
- Step 1 (Front-Foot vs Back-Foot) Accuracy     : {m1_acc*100:.2f}%
- Step 2a (Front-Foot Def vs Att) Accuracy      : {m2a_acc*100:.2f}%
- Step 2b (Back-Foot High vs Low) Accuracy      : {m2b_acc*100:.2f}%

Classification Report:
------------------------------------------------------------
{report_str}

Confusion Matrix:
------------------------------------------------------------
{matrix_str}
"""

    print(f"\n📊  Overall Hierarchical Accuracy: {acc*100:.2f}%")
    print(f"   - FF vs BF Classifier Acc  : {m1_acc*100:.2f}%")
    print(f"   - FF Def vs Att Classifier : {m2a_acc*100:.2f}%")
    print(f"   - BF High vs Low Classifier: {m2b_acc*100:.2f}%")
    print("-" * 60)
    print(report_str)

    with open(args.results_file, "w") as f:
        f.write(results_content)
    print(f"\n💾  Saved hierarchical study results to {args.results_file}")

if __name__ == "__main__":
    main()
