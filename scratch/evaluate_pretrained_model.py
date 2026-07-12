#!/usr/bin/env python3
import os
import zipfile
import shutil
import random
import glob
import numpy as np
import cv2
import keras
from keras import layers
from sklearn.metrics import classification_report, accuracy_score, confusion_matrix

# Configuration
keras_file = "/Users/neilkloot/Code/Batting Sensor Stats/cricshot10k/Models/Efficientnetv2-s_GRU_128_NEEDS_CROPPED_SEGMENTED_SHOTS.keras"
videos_root = "/Users/neilkloot/Code/Batting Sensor Stats/cricshot10k/Videos"
weights_temp = "scratch/model.weights.h5"
results_file = "scratch/pretrained_model_results.txt"

# Alphabetical sorted classes matching Keras directory mapping
CLASS_NAMES = sorted([
    "Cover Drive", "Defensive", "Down The Wicket", "Flick", "Hook", 
    "Late Cut", "Lofted Legside", "Lofted Offside", "Pull", "Reverse Sweep", 
    "Scoop", "Square Cut", "Straight Drive", "Sweep", "Upper Cut"
])

def load_pretrained_model():
    print("🎬  Extracting weights from model archive...")
    with zipfile.ZipFile(keras_file, 'r') as zip_ref:
        zip_ref.extract("model.weights.h5", "scratch")
        
    print("🧠  Rebuilding EfficientNetV2-S + GRU model structure...")
    # Recreate base functional model
    base_model = keras.applications.EfficientNetV2S(
        include_top=False,
        weights=None,
        input_shape=(224, 224, 3)
    )
    base_model._name = "efficientnetv2-s"

    # Recreate Sequential wrapper
    model = keras.Sequential([
        layers.Input(shape=(15, 224, 224, 3)),
        layers.TimeDistributed(base_model, name="time_distributed_8"),
        layers.TimeDistributed(layers.Flatten(), name="time_distributed_9"),
        layers.GRU(128, return_sequences=False, name="gru_4"),
        layers.BatchNormalization(name="batch_normalization_4"),
        layers.Dense(1024, activation="relu", name="dense_8"),
        layers.Dense(15, activation="softmax", name="dense_9")
    ])

    print("⚖️  Loading weights into model...")
    model.load_weights(weights_temp)
    
    if os.path.exists(weights_temp):
        os.remove(weights_temp)
        
    return model

def process_video_to_frames(video_path):
    """Loads video, center-crops, and samples exactly 15 frames."""
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return None
        
    frames = []
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
            
        # Center crop to square
        h, w = frame.shape[:2]
        side = min(h, w)
        start_x = (w - side) // 2
        start_y = (h - side) // 2
        crop = frame[start_y:start_y+side, start_x:start_x+side]
        
        # Resize to 224x224 and convert to RGB
        resized = cv2.resize(crop, (224, 224))
        rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
        frames.append(rgb.astype(np.float32))
        
    cap.release()
    
    if not frames:
        return None
        
    # Sample exactly 15 frames uniformly across the video
    N = len(frames)
    if N >= 15:
        indices = np.linspace(0, N - 1, 15, dtype=int)
        sampled_frames = [frames[i] for i in indices]
    else:
        # Zero-pad or pad with last frame if the video is too short
        sampled_frames = list(frames)
        last_frame = frames[-1]
        while len(sampled_frames) < 15:
            sampled_frames.append(last_frame)
            
    return np.array(sampled_frames) # Shape: (15, 224, 224, 3)

def main():
    # Set random seed for reproducibility
    random.seed(42)
    
    # 1. Load Model
    model = load_pretrained_model()
    print("✅  Model loaded successfully.")

    # 2. Gather videos and sample 20% of each class
    print("\n📂  Sampling 20% of videos per shot type...")
    all_sampled_videos = []
    
    for cls in CLASS_NAMES:
        class_dir = os.path.join(videos_root, cls)
        if not os.path.exists(class_dir):
            print(f"⚠️  Warning: class directory not found: {class_dir}")
            continue
            
        video_files = glob.glob(os.path.join(class_dir, "*.avi")) + glob.glob(os.path.join(class_dir, "*.mp4"))
        video_files = sorted(video_files)
        
        # Calculate 20% sample count
        sample_count = max(1, int(len(video_files) * 0.20))
        sampled = random.sample(video_files, sample_count)
        print(f"   - {cls:<15}: sampled {len(sampled)} / {len(video_files)} videos")
        
        for path in sampled:
            all_sampled_videos.append((path, cls))
            
    print(f"\n🎬  Total videos to evaluate: {len(all_sampled_videos)}")

    # 3. Predict & Evaluate
    y_true, y_pred = [], []
    processed_count = 0
    
    for v_path, cls in all_sampled_videos:
        frames = process_video_to_frames(v_path)
        if frames is None:
            print(f"⚠️  Skipping unreadable video: {v_path}")
            continue
            
        # Add batch dimension: (1, 15, 224, 224, 3)
        batch = np.expand_dims(frames, axis=0)
        
        # Predict
        preds = model.predict(batch, verbose=0)
        pred_idx = np.argmax(preds[0])
        pred_class = CLASS_NAMES[pred_idx]
        
        y_true.append(cls)
        y_pred.append(pred_class)
        
        processed_count += 1
        if processed_count % 50 == 0:
            print(f"   Processed {processed_count} / {len(all_sampled_videos)} videos...")

    # 4. Generate Reports
    acc = accuracy_score(y_true, y_pred)
    report_str = classification_report(y_true, y_pred, zero_division=0)
    matrix_str = str(confusion_matrix(y_true, y_pred))

    results_content = f"""CricShot10k Pre-trained Keras Model Evaluation
============================================================
Total Evaluated Videos: {processed_count}
Baseline Accuracy     : {acc*100:.2f}%

Classification Report:
------------------------------------------------------------
{report_str}

Confusion Matrix:
------------------------------------------------------------
{matrix_str}
"""

    print(f"\n📊  Evaluation Complete. Accuracy: {acc*100:.2f}%")
    print("-" * 60)
    print(report_str)

    with open(results_file, "w") as f:
        f.write(results_content)
    print(f"\n💾  Saved evaluation results to {results_file}")

if __name__ == "__main__":
    main()
