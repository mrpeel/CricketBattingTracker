#!/usr/bin/env python3
import os
import json
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, accuracy_score

# Paths
base_path = "/Users/neilkloot/Code/Batting Sensor Stats/ViTPose"
annotations_dir = os.path.join(base_path, "JSONAnnotations")
keypoints_dir = os.path.join(base_path, "KeypointsViTPose")

# Option mappings
STROKE_MAP = {
    "0": "OffDrive",
    "1": "OnDrive",
    "2": "Cut",
    "3": "Glance",
    "4": "Hook",
    "5": "Sweep",
    "6": "Block"
}

FOOT_MAP = {
    "0": "FrontFoot",
    "1": "BackFoot"
}

def calculate_angle(a, b, c):
    """Calculates angle ABC in degrees at vertex B."""
    a = np.array(a)
    b = np.array(b)
    c = np.array(c)
    
    ba = a - b
    bc = c - b
    
    norm_ba = np.linalg.norm(ba)
    norm_bc = np.linalg.norm(bc)
    
    if norm_ba == 0 or norm_bc == 0:
        return 0.0
        
    cosine_angle = np.dot(ba, bc) / (norm_ba * norm_bc)
    angle = np.arccos(np.clip(cosine_angle, -1.0, 1.0))
    return float(np.degrees(angle))

def extract_features_from_frame(points, prev_points=None):
    """
    Extracts geometric features from 25 BODY_25 keypoints.
    Each keypoint is points[i] = [x, y, confidence].
    """
    # Helper to get xy coordinate or default
    def get_xy(idx):
        if idx < len(points) and points[idx][2] > 0.1:
            return points[idx][:2]
        return [0.0, 0.0]
        
    # Get all joints
    nose = get_xy(0)
    neck = get_xy(1)
    r_shoulder = get_xy(2)
    r_elbow = get_xy(3)
    r_wrist = get_xy(4)
    l_shoulder = get_xy(5)
    l_elbow = get_xy(6)
    l_wrist = get_xy(7)
    mid_hip = get_xy(8)
    r_hip = get_xy(9)
    r_knee = get_xy(10)
    r_ankle = get_xy(11)
    l_hip = get_xy(12)
    l_knee = get_xy(13)
    l_ankle = get_xy(14)
    l_heel = get_xy(21)
    r_heel = get_xy(24)
    
    # 1. Joint angles
    features = [
        calculate_angle(neck, r_shoulder, r_elbow),  # R Shoulder Angle
        calculate_angle(neck, l_shoulder, l_elbow),  # L Shoulder Angle
        calculate_angle(r_shoulder, r_elbow, r_wrist),  # R Elbow Angle
        calculate_angle(l_shoulder, l_elbow, l_wrist),  # L Elbow Angle
        calculate_angle(neck, r_hip, r_knee),  # R Hip Angle
        calculate_angle(neck, l_hip, l_knee),  # L Hip Angle
        calculate_angle(r_hip, r_knee, r_ankle),  # R Knee Angle
        calculate_angle(l_hip, l_knee, l_ankle),  # L Knee Angle
    ]
    
    # 2. Wrist positions relative to MidHip
    features.extend([
        r_wrist[0] - mid_hip[0], r_wrist[1] - mid_hip[1],
        l_wrist[0] - mid_hip[0], l_wrist[1] - mid_hip[1]
    ])
    
    # 3. Wrist velocity
    if prev_points:
        def get_prev_xy(idx):
            if idx < len(prev_points) and prev_points[idx][2] > 0.1:
                return prev_points[idx][:2]
            return [0.0, 0.0]
        prev_r_wrist = get_prev_xy(4)
        prev_l_wrist = get_prev_xy(7)
        features.extend([
            r_wrist[0] - prev_r_wrist[0], r_wrist[1] - prev_r_wrist[1],
            l_wrist[0] - prev_l_wrist[0], l_wrist[1] - prev_l_wrist[1]
        ])
    else:
        features.extend([0.0, 0.0, 0.0, 0.0])
        
    # 4. Head alignment (Nose relative to Neck)
    features.extend([
        nose[0] - neck[0], nose[1] - neck[1]
    ])
    
    # 5. Footwork spacing
    features.extend([
        l_ankle[0] - r_ankle[0], l_ankle[1] - r_ankle[1],
        l_heel[0] - r_heel[0], l_heel[1] - r_heel[1]
    ])
    
    return features

def load_dataset():
    print("📋 Phase 1: Loading annotations...")
    annotations = {}
    for filename in os.listdir(annotations_dir):
        if not filename.endswith(".json"):
            continue
        video_id = filename.replace(".json", "") # e.g. P1_V1
        json_path = os.path.join(annotations_dir, filename)
        
        with open(json_path, 'r') as f:
            data = json.load(f)
            
        metadata = data.get("metadata", {})
        video_annotations = []
        for key, val in metadata.items():
            av = val.get("av", {})
            if av.get("1") == "Execution" and "9" in av:
                z_vals = val.get("z", [])
                if z_vals:
                    video_annotations.append({
                        "timestamp": z_vals[0],
                        "stroke": STROKE_MAP.get(av["9"], "Unknown"),
                        "foot": FOOT_MAP.get(av.get("8", ""), "Unknown")
                    })
        annotations[video_id] = video_annotations
        
    print(f"Loaded annotations for {len(annotations)} video files.")

    print("\n📁 Phase 2: Processing pose folders and extracting features...")
    X = []
    y_stroke = []
    y_foot = []
    
    subdirs = sorted([d for d in os.listdir(keypoints_dir) if os.path.isdir(os.path.join(keypoints_dir, d)) and not d.startswith(".")])
    
    skipped_count = 0
    matched_count = 0
    
    for idx, sd in enumerate(subdirs):
        # Extract video id from subdir name (e.g. P1_V10_Phase2 -> video_id = P1_V10)
        parts = sd.split("_Phase")
        if len(parts) < 2:
            continue
        video_id = parts[0]
        
        # Get annotated executions for this video
        video_annots = annotations.get(video_id, [])
        if not video_annots:
            skipped_count += 1
            continue
            
        sd_path = os.path.join(keypoints_dir, sd)
        frame_files = sorted([f for f in os.listdir(sd_path) if f.endswith(".json")])
        if not frame_files:
            continue
            
        # Parse frames to get frame indices
        frames = []
        for f in frame_files:
            try:
                frames.append(int(f.replace("frame", "").replace(".json", "")))
            except:
                pass
        
        if not frames:
            continue
            
        # Calculate time range midpoint
        t_start = frames[0] / 25.0
        t_end = frames[-1] / 25.0
        t_mid = (t_start + t_end) / 2.0
        
        # Match to closest annotated execution within 1.0 second
        closest_annot = min(video_annots, key=lambda x: abs(x["timestamp"] - t_mid))
        if abs(closest_annot["timestamp"] - t_mid) > 1.0:
            skipped_count += 1
            continue
            
        # Extract features across frames
        folder_features = []
        prev_points = None
        for f_file in frame_files:
            with open(os.path.join(sd_path, f_file), 'r') as f:
                frame_data = json.load(f)
            # The list of 25 keypoints is under key "0"
            points = frame_data.get("0", [])
            if not points:
                continue
            frame_feat = extract_features_from_frame(points, prev_points)
            folder_features.append(frame_feat)
            prev_points = points
            
        if not folder_features:
            continue
            
        # Compute temporal aggregation (mean, std, min, max) for each feature
        folder_features = np.array(folder_features)
        mean_feat = np.mean(folder_features, axis=0)
        std_feat = np.std(folder_features, axis=0)
        min_feat = np.min(folder_features, axis=0)
        max_feat = np.max(folder_features, axis=0)
        
        agg_features = np.hstack([mean_feat, std_feat, min_feat, max_feat])
        
        X.append(agg_features)
        y_stroke.append(closest_annot["stroke"])
        y_foot.append(closest_annot["foot"])
        matched_count += 1
        
    print(f"Successfully processed and matched {matched_count} folders. (Skipped {skipped_count} unmatched folders)")
    return np.array(X), np.array(y_stroke), np.array(y_foot)

def main():
    X, y_stroke, y_foot = load_dataset()
    if len(X) == 0:
        print("❌ Error: No samples loaded!")
        return
        
    # --- 1. Evaluate Stroke Type Classifier ---
    print("\n⚔️  Training Stroke Type Classifier (OffDrive, OnDrive, Cut, Glance, Hook, Sweep, Block)...")
    X_train, X_test, y_train, y_test = train_test_split(X, y_stroke, test_size=0.2, random_state=42, stratify=y_stroke)
    
    rf_stroke = RandomForestClassifier(n_estimators=100, random_state=42)
    rf_stroke.fit(X_train, y_train)
    
    y_pred = rf_stroke.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    
    print(f"\n📊 Overall Stroke Classification Accuracy: {acc*100:.2f}%")
    print("\nDetailed Stroke Classification Report:")
    print(classification_report(y_test, y_pred))
    
    # --- 2. Evaluate Foot Type Classifier ---
    print("\n⚔️  Training Foot Type Classifier (FrontFoot vs BackFoot)...")
    X_train_f, X_test_f, y_train_f, y_test_f = train_test_split(X, y_foot, test_size=0.2, random_state=42, stratify=y_foot)
    
    rf_foot = RandomForestClassifier(n_estimators=100, random_state=42)
    rf_foot.fit(X_train_f, y_train_f)
    
    y_pred_f = rf_foot.predict(X_test_f)
    acc_f = accuracy_score(y_test_f, y_pred_f)
    
    print(f"\n📊 Overall Footwork Classification Accuracy: {acc_f*100:.2f}%")
    print("\nDetailed Footwork Classification Report:")
    print(classification_report(y_test_f, y_pred_f))

if __name__ == "__main__":
    main()
