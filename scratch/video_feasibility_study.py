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
from sklearn.metrics import classification_report, accuracy_score, confusion_matrix

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

def extract_features_from_video(video_path, detector):
    """
    Extracts normalized pose keypoints and dense optical flow features from a video clip.
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"⚠️  Could not open video {video_path}")
        return None

    # Get video properties
    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps <= 0:
        fps = 25.0

    frames_features = []
    prev_gray = None
    pose_detected_once = False
    consecutive_no_pose = 0
    
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        
        # Convert BGR to RGB for MediaPipe
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Convert to MediaPipe Image wrapper
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
        results = detector.detect(mp_image)
        
        frame_feat = {}
        has_pose = False
        
        # 1. Pose landmarks processing
        if results.pose_landmarks and len(results.pose_landmarks) > 0:
            landmarks = results.pose_landmarks[0] # Take first detected person
            
            # Check detection confidence for key landmarks
            # We need hips (23, 24) and shoulders (11, 12) for normalization
            hip_l, hip_r = landmarks[23], landmarks[24]
            sh_l, sh_r = landmarks[11], landmarks[12]
            
            if hip_l.presence > 0.5 and hip_r.presence > 0.5:
                # Pelvis reference point (origin)
                origin_x = (hip_l.x + hip_r.x) / 2.0
                origin_y = (hip_l.y + hip_r.y) / 2.0
                origin_z = (hip_l.z + hip_r.z) / 2.0
                
                # Torso length scale
                torso_len = np.sqrt(
                    ((sh_l.x + sh_r.x)/2.0 - origin_x)**2 +
                    ((sh_l.y + sh_r.y)/2.0 - origin_y)**2
                )
                if torso_len <= 0:
                    torso_len = 1.0
                    
                # Calculate camera-invariant biomechanical joint angles
                frame_feat["el_l_angle"] = calculate_angle(landmarks[11], landmarks[13], landmarks[15])
                frame_feat["el_r_angle"] = calculate_angle(landmarks[12], landmarks[14], landmarks[16])
                frame_feat["kn_l_angle"] = calculate_angle(landmarks[23], landmarks[25], landmarks[27])
                frame_feat["kn_r_angle"] = calculate_angle(landmarks[24], landmarks[26], landmarks[28])
                frame_feat["sh_l_angle"] = calculate_angle(landmarks[23], landmarks[11], landmarks[13])
                frame_feat["sh_r_angle"] = calculate_angle(landmarks[24], landmarks[12], landmarks[14])
                frame_feat["hip_l_angle"] = calculate_angle(landmarks[11], landmarks[23], landmarks[25])
                frame_feat["hip_r_angle"] = calculate_angle(landmarks[12], landmarks[24], landmarks[26])
                
                # Keep normalized wrist positions to track reach and hand trajectory relative to pelvis
                frame_feat["wr_l_x"] = (landmarks[15].x - origin_x) / torso_len
                frame_feat["wr_l_y"] = (landmarks[15].y - origin_y) / torso_len
                frame_feat["wr_r_x"] = (landmarks[16].x - origin_x) / torso_len
                frame_feat["wr_r_y"] = (landmarks[16].y - origin_y) / torso_len
                
                has_pose = True
            
        if not has_pose:
            # Just skip this frame and keep looking
            prev_gray = gray_frame
            continue
            
        # 2. Optical Flow processing (Farneback Dense Optical Flow)
        flow_mag_max = 0.0
        flow_dir_mean = 0.0
        if prev_gray is not None:
            # Farneback parameters optimized for fast motion
            flow = cv2.calcOpticalFlowFarneback(
                prev_gray, gray_frame, None,
                pyr_scale=0.5, levels=3, winsize=15,
                iterations=3, poly_n=5, poly_sigma=1.2, flags=0
            )
            mag, ang = cv2.cartToPolar(flow[..., 0], flow[..., 1])
            
            # Exclude pixels inside the human bounding box to focus on bat motion
            h, w = frame.shape[:2]
            xs = [lm.x * w for lm in landmarks if lm.presence > 0.5]
            ys = [lm.y * h for lm in landmarks if lm.presence > 0.5]
            if xs and ys:
                xmin, xmax = int(min(xs)), int(max(xs))
                ymin, ymax = int(min(ys)), int(max(ys))
                
                # Pad the body mask slightly
                pad_w = int((xmax - xmin) * 0.1)
                pad_h = int((ymax - ymin) * 0.1)
                
                mask = np.ones(mag.shape, dtype=bool)
                y_start, y_end = max(0, ymin - pad_h), min(h, ymax + pad_h)
                x_start, x_end = max(0, xmin - pad_w), min(w, xmax + pad_w)
                mask[y_start:y_end, x_start:x_end] = False
                
                # Apply mask
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
    
    # Statistical aggregates across three temporal segments (backswing, contact, follow-through)
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
        # Fallback for very short videos
        segments = {
            "seg1": df_feat,
            "seg2": df_feat,
            "seg3": df_feat
        }
        
    for seg_name, df_seg in segments.items():
        if df_seg.empty:
            continue
            
        pose_cols = [c for c in df_seg.columns if c not in ["flow_mag_max", "flow_dir_mean"]]
        for col in pose_cols:
            summary[f"{seg_name}_{col}_mean"] = df_seg[col].mean()
            summary[f"{seg_name}_{col}_std"] = df_seg[col].std()
            summary[f"{seg_name}_{col}_range"] = df_seg[col].max() - df_seg[col].min()
            
        # Optical flow statistics for speed / direction tracking
        summary[f"{seg_name}_peak_flow_speed"] = df_seg["flow_mag_max"].max()
        summary[f"{seg_name}_mean_flow_speed"] = df_seg["flow_mag_max"].mean()
        
        if not df_seg["flow_mag_max"].empty:
            peak_flow_idx = df_seg["flow_mag_max"].idxmax()
            summary[f"{seg_name}_peak_flow_direction"] = df_seg.loc[peak_flow_idx, "flow_dir_mean"] if peak_flow_idx in df_seg.index else 0.0
        else:
            summary[f"{seg_name}_peak_flow_direction"] = 0.0
            
    # Add overall features for baseline
    summary["overall_peak_flow_speed"] = df_feat["flow_mag_max"].max()
    summary["overall_mean_flow_speed"] = df_feat["flow_mag_max"].mean()
    
    return summary

def process_dataset(root_dir, detector, limit_per_class=None):
    """
    Processes the train, val, and test splits under the root directory.
    """
    dataset = {}
    splits = ["train", "val", "test"]
    
    for split in splits:
        split_dir = os.path.join(root_dir, split)
        if not os.path.exists(split_dir):
            continue
            
        print(f"📂  Processing {split} split...")
        X, y, files = [], [], []
        
        # List shot classes
        classes = sorted([d for d in os.listdir(split_dir) if os.path.isdir(os.path.join(split_dir, d))])
        
        for cls in classes:
            class_dir = os.path.join(split_dir, cls)
            video_files = glob.glob(os.path.join(class_dir, "*.avi")) + glob.glob(os.path.join(class_dir, "*.mp4"))
            
            # Sort for determinism
            video_files = sorted(video_files)
            if limit_per_class:
                video_files = video_files[:limit_per_class]
                
            print(f"   Class: {cls:<12} | Processing {len(video_files)} videos...")
            
            for v_path in video_files:
                feats = extract_features_from_video(v_path, detector)
                if feats is not None:
                    X.append(feats)
                    y.append(cls)
                    files.append(v_path)
                    
        dataset[split] = {"X": pd.DataFrame(X), "y": np.array(y), "files": files}
        
    return dataset

def main():
    parser = argparse.ArgumentParser(description="Cricket Shot Video Identification Feasibility Study")
    parser.add_argument("--root-dir", default="/Users/neilkloot/Code/Batting Sensor Stats/cricketshot", help="Path to dataset root")
    parser.add_argument("--cache-file", default="scratch/video_features_cache.pkl", help="Path to cache extracted features")
    parser.add_argument("--limit-per-class", type=int, default=10, help="Limit number of videos per class for feasibility runtime (default: 10)")
    parser.add_argument("--full", action="store_true", help="Process entire dataset (ignores limit-per-class)")
    parser.add_argument("--model-path", default="scratch/pose_landmarker_full.task", help="Path to pose landmarker task file")
    parser.add_argument("--results-file", default="scratch/video_feasibility_results.txt", help="Path to save evaluation results")
    args = parser.parse_args()

    # Ensure output directories exist
    os.makedirs(os.path.dirname(args.cache_file), exist_ok=True)
    os.makedirs(os.path.dirname(args.results_file), exist_ok=True)
    
    limit = None if args.full else args.limit_per_class
    
    # Initialize MediaPipe detector
    base_options = python.BaseOptions(model_asset_path=args.model_path)
    options = vision.PoseLandmarkerOptions(
        base_options=base_options,
        output_segmentation_masks=False
    )
    detector = vision.PoseLandmarker.create_from_options(options)

    # Note: If running on full dataset, we cache to a separate cache file
    cache_path = args.cache_file if not args.full else "scratch/video_features_full_cache.pkl"

    if os.path.exists(cache_path):
        print(f"💾  Loading cached features from {cache_path}...")
        with open(cache_path, "rb") as f:
            dataset = pickle.load(f)
    else:
        print(f"🎬  Extracting features from videos (limit per class: {limit if limit else 'None'})...")
        dataset = process_dataset(args.root_dir, detector, limit_per_class=limit)
        # Cache features
        with open(cache_path, "wb") as f:
            pickle.dump(dataset, f)
        print(f"💾  Cached features to {cache_path}")

    # Train model
    if "train" in dataset and "test" in dataset:
        train_data = dataset["train"]
        test_data = dataset["test"]
        
        X_train = train_data["X"].fillna(0.0)
        y_train = train_data["y"]
        X_test = test_data["X"].fillna(0.0)
        y_test = test_data["y"]
        
        print(f"\n🧠  Training Random Forest Classifier on {len(X_train)} samples...")
        clf = RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42)
        clf.fit(X_train, y_train)
        
        # Test evaluation
        y_pred = clf.predict(X_test)
        acc = accuracy_score(y_test, y_pred)
        
        report_str = classification_report(y_test, y_pred)
        matrix_str = str(confusion_matrix(y_test, y_pred))
        
        # Feature Importance
        importances = clf.feature_importances_
        indices = np.argsort(importances)[::-1]
        
        importances_str = ""
        for f in range(min(15, len(importances))):
            importances_str += f"   {f+1}. {X_train.columns[indices[f]]:<30} : {importances[indices[f]]:.4f}\n"
            
        results_content = f"""Cricket Shot Video Identification Feasibility Study Results
============================================================
Samples Trained: {len(X_train)}
Samples Tested : {len(X_test)}
Accuracy       : {acc*100:.2f}%

Classification Report:
------------------------------------------------------------
{report_str}

Confusion Matrix:
------------------------------------------------------------
{matrix_str}

Top 15 Feature Importances:
------------------------------------------------------------
{importances_str}
"""
        
        print(f"\n📊  Evaluation Results:")
        print("-" * 60)
        print(report_str)
        print("Confusion Matrix:")
        print(matrix_str)
        
        print("\n🔝  Top 10 Feature Importances:")
        for f in range(min(10, len(importances))):
            print(f"   {f+1}. {X_train.columns[indices[f]]:<30} : {importances[indices[f]]:.4f}")
            
        # Save results to file
        with open(args.results_file, "w") as rf:
            rf.write(results_content)
        print(f"\n💾  Saved full study results to {args.results_file}")
            
    else:
        print("⚠️  Train/Test splits not complete in dataset.")

if __name__ == "__main__":
    main()
