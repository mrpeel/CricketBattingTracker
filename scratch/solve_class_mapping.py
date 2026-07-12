#!/usr/bin/env python3
import os
import zipfile
import random
import glob
import numpy as np
import cv2
import keras
from keras import layers
from scipy.optimize import linear_sum_assignment
from sklearn.metrics import classification_report, accuracy_score

keras_file = "/Users/neilkloot/Code/Batting Sensor Stats/cricshot10k/Models/Efficientnetv2-s_GRU_128_NEEDS_CROPPED_SEGMENTED_SHOTS.keras"
videos_root = "/Users/neilkloot/Code/Batting Sensor Stats/cricshot10k/Videos"
weights_temp = "scratch/model.weights.h5"

CLASS_NAMES = sorted([
    "Cover Drive", "Defensive", "Down The Wicket", "Flick", "Hook", 
    "Late Cut", "Lofted Legside", "Lofted Offside", "Pull", "Reverse Sweep", 
    "Scoop", "Square Cut", "Straight Drive", "Sweep", "Upper Cut"
])

def load_pretrained_model():
    with zipfile.ZipFile(keras_file, 'r') as zip_ref:
        zip_ref.extract("model.weights.h5", "scratch")
    base_model = keras.applications.EfficientNetV2S(
        include_top=False, weights=None, input_shape=(224, 224, 3)
    )
    base_model._name = "efficientnetv2-s"
    model = keras.Sequential([
        layers.Input(shape=(15, 224, 224, 3)),
        layers.TimeDistributed(base_model, name="time_distributed_8"),
        layers.TimeDistributed(layers.Flatten(), name="time_distributed_9"),
        layers.GRU(128, return_sequences=False, name="gru_4"),
        layers.BatchNormalization(name="batch_normalization_4"),
        layers.Dense(1024, activation="relu", name="dense_8"),
        layers.Dense(15, activation="softmax", name="dense_9")
    ])
    model.load_weights(weights_temp)
    if os.path.exists(weights_temp):
        os.remove(weights_temp)
    return model

def process_video_to_frames(video_path):
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return None
    frames = []
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        h, w = frame.shape[:2]
        side = min(h, w)
        start_x = (w - side) // 2
        start_y = (h - side) // 2
        crop = frame[start_y:start_y+side, start_x:start_x+side]
        resized = cv2.resize(crop, (224, 224))
        rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
        frames.append(rgb.astype(np.float32))
    cap.release()
    if not frames:
        return None
    N = len(frames)
    if N >= 15:
        indices = np.linspace(0, N - 1, 15, dtype=int)
        sampled_frames = [frames[i] for i in indices]
    else:
        sampled_frames = list(frames)
        last_frame = frames[-1]
        while len(sampled_frames) < 15:
            sampled_frames.append(last_frame)
    return np.array(sampled_frames)

def main():
    random.seed(42)
    model = load_pretrained_model()
    
    # We sample a smaller set of 10% of each class for speed in solving mapping
    print("Sampling 10% of dataset...")
    sampled_videos = []
    for cls in CLASS_NAMES:
        class_dir = os.path.join(videos_root, cls)
        if not os.path.exists(class_dir):
            continue
        video_files = sorted(glob.glob(os.path.join(class_dir, "*.avi")) + glob.glob(os.path.join(class_dir, "*.mp4")))
        sample_count = max(1, int(len(video_files) * 0.10))
        sampled = random.sample(video_files, sample_count)
        for path in sampled:
            sampled_videos.append((path, cls))
            
    print(f"Total videos to evaluate for mapping: {len(sampled_videos)}")
    
    y_true_labels = []
    y_pred_probs = []
    
    for idx, (v_path, cls) in enumerate(sampled_videos):
        frames = process_video_to_frames(v_path)
        if frames is None:
            continue
        batch = np.expand_dims(frames, axis=0)
        preds = model.predict(batch, verbose=0)[0]
        
        y_true_labels.append(cls)
        y_pred_probs.append(preds)
        
        if (idx + 1) % 50 == 0:
            print(f"Processed {idx + 1} / {len(sampled_videos)}...")
            
    y_true_labels = np.array(y_true_labels)
    y_pred_probs = np.array(y_pred_probs)
    y_pred_indices = np.argmax(y_pred_probs, axis=1)
    
    # Build a cost matrix for linear sum assignment
    # We want to match output indices (0-14) to ground truth classes (0-14)
    # The cost will be the negative sum of probabilities or counts
    num_classes = len(CLASS_NAMES)
    cost_matrix = np.zeros((num_classes, num_classes))
    
    for i, cls in enumerate(CLASS_NAMES):
        class_mask = (y_true_labels == cls)
        if not np.any(class_mask):
            continue
        # Average predicted probability of this class for each output index
        mean_probs = np.mean(y_pred_probs[class_mask], axis=0)
        cost_matrix[i, :] = -mean_probs
        
    # Solve linear sum assignment
    row_ind, col_ind = linear_sum_assignment(cost_matrix)
    
    print("\n🔍 Optimal Mapping Found:")
    mapped_index_to_class = {}
    for r, c in zip(row_ind, col_ind):
        mapped_index_to_class[c] = CLASS_NAMES[r]
        print(f"Output Index {c:<2} ---> Class: {CLASS_NAMES[r]} (Average prob: {-cost_matrix[r, c]:.4f})")
        
    # Calculate accuracy under optimal mapping
    y_mapped_pred = [mapped_index_to_class.get(idx, "Unknown") for idx in y_pred_indices]
    mapped_acc = accuracy_score(y_true_labels, y_mapped_pred)
    
    print(f"\n📊 Accuracy under alphabetical mapping: {accuracy_score(y_true_labels, [CLASS_NAMES[idx] for idx in y_pred_indices])*100:.2f}%")
    print(f"📊 Accuracy under OPTIMAL mapping      : {mapped_acc*100:.2f}%")
    
    # Print classification report under optimal mapping
    print("\nClassification Report under Optimal Mapping:")
    print("-" * 60)
    print(classification_report(y_true_labels, y_mapped_pred, zero_division=0))

if __name__ == "__main__":
    main()
