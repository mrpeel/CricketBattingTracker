#!/usr/bin/env python3
"""
diagnose_session_2026-07-31.py — Diagnosis of ONNX TCN model on session_2026-07-31_12-44-46
"""
import os
import sys
import json
import numpy as np
import pandas as pd
import torch
import onnxruntime as ort

ROOT_DIR = "/Users/neilkloot/Code/CricketBattingTracker"
BASE_DIR = "/Users/neilkloot/Code/Batting Sensor Stats"
SESSION_DIR = os.path.join(BASE_DIR, "live_watch_sessions", "session_2026-07-31_12-44-46")
UNIFIED_DIR = os.path.join(BASE_DIR, "poc_unified_dataset")
MODEL_ONNX_PATH = os.path.join(ROOT_DIR, "app/src/main/assets/models/tcn_ultimate_baseline.onnx")
STATS_PATH = os.path.join(ROOT_DIR, "pipelines/tcn_norm_stats.json")

# Load Normalization Stats
stats = json.load(open(STATS_PATH))
features = stats['features']
classes = stats['classes']
med = np.array(stats['median'], dtype=np.float32)
mad = np.array(stats['mad'], dtype=np.float32)
mad = np.where(mad < 1e-3, 1.0, mad)

# Load Unified Dataframe or build from session
unified_path = os.path.join(UNIFIED_DIR, "session_2026-07-31_12-44-46_unified.parquet")
if os.path.exists(unified_path):
    df = pd.read_parquet(unified_path)
    print(f"Loaded unified dataset parquet: {len(df)} rows ({len(df)/423.0:.1f} seconds)")
else:
    # Build on the fly from build_unified_dataset
    sys.path.append(os.path.join(ROOT_DIR, "pipelines"))
    from build_unified_dataset import build_session
    build_session("session_2026-07-31_12-44-46")
    df = pd.read_parquet(unified_path)
    print(f"Loaded unified dataframe: {len(df)} rows ({len(df)/423.0:.1f} seconds)")

# Prepare feature matrix
X = df[features].fillna(0).values.astype(np.float32)
X_norm = (X - med) / mad

# Load PyTorch Model
MODEL_PT_PATH = os.path.join(ROOT_DIR, "pipelines/tcn_ultimate_baseline.pt")
sys.path.append(os.path.join(ROOT_DIR, "pipelines"))
from export_tcn_to_onnx import AdvancedTCN

model = AdvancedTCN(in_ch=len(features), num_classes=len(classes), channels=32)
model.load_state_dict(torch.load(MODEL_PT_PATH, map_location='cpu'))
model.eval()

# Run Inference in 2048 chunks
WINDOW_LEN = 2048
preds_list = []
probs_list = []

with torch.no_grad():
    for i in range(0, len(X_norm), WINDOW_LEN):
        chunk = X_norm[i:i+WINDOW_LEN].T[np.newaxis, :, :] # (1, 26, T)
        n_frames = chunk.shape[2]
        if n_frames < WINDOW_LEN:
            pad = np.zeros((1, len(features), WINDOW_LEN - n_frames), dtype=np.float32)
            chunk = np.concatenate([chunk, pad], axis=2)
            
        chunk_t = torch.from_numpy(chunk)
        logits = model(chunk_t)[0, :, :n_frames].numpy() # (10, n_frames)
        
        # Softmax
        exp_logits = np.exp(logits - np.max(logits, axis=0, keepdims=True))
        probs = exp_logits / np.sum(exp_logits, axis=0, keepdims=True)
        
        preds = np.argmax(probs, axis=0)
        preds_list.append(preds)
        probs_list.append(probs)

preds_full = np.concatenate(preds_list)
probs_full = np.hstack(probs_list)

# Analyze Raw Frame Detections
SHOT_INDICES = set([2,3,4,5,6,7,8,9]) # Pull, Defence, Flick, Drive, Glance, Sweep, Cut, Slog
is_shot_frame = np.isin(preds_full, list(SHOT_INDICES))

# Group contiguous shot frames into candidate regions
regions = []
i = 0
while i < len(is_shot_frame):
    if is_shot_frame[i]:
        j = i
        while j < len(is_shot_frame) and is_shot_frame[j]:
            j += 1
        duration_frames = j - i
        duration_ms = duration_frames * (1000.0 / 423.0)
        peak_idx = i + np.argmax(probs_full[preds_full[i:j], i:j].max(axis=0)) if j > i else i
        peak_class = classes[preds_full[peak_idx]]
        peak_prob = probs_full[:, peak_idx].max()
        
        # Calculate raw gyro/accel peak in this region
        w_gyro_max = np.linalg.norm(X[i:j, 3:6], axis=1).max() if j > i else 0
        w_acc_max = np.linalg.norm(X[i:j, 0:3], axis=1).max() if j > i else 0
        
        regions.append({
            'start_frame': i,
            'end_frame': j,
            'duration_ms': duration_ms,
            'start_sec': i / 423.0,
            'peak_sec': peak_idx / 423.0,
            'class': peak_class,
            'prob': peak_prob,
            'w_gyro_max': w_gyro_max,
            'w_acc_max': w_acc_max
        })
        i = j
    else:
        i += 1

print(f"\n============================================================")
print(f"  RAW UNFILTERED ONNX TCN DETECTIONS: {len(regions)} Candidate Regions")
print(f"============================================================")

df_regions = pd.DataFrame(regions)
print("\nDuration Distribution of Candidate Regions:")
print(f"  Short (<150ms): {sum(r['duration_ms'] < 150 for r in regions)} regions")
print(f"  Medium (150ms - 800ms): {sum(150 <= r['duration_ms'] <= 800 for r in regions)} regions")
print(f"  Long (>800ms): {sum(r['duration_ms'] > 800 for r in regions)} regions")

print("\nGyroscope Peak Distribution (w_gyro_max rad/s):")
print(f"  Low Gyro (< 3.0 rad/s): {sum(r['w_gyro_max'] < 3.0 for r in regions)} regions")
print(f"  Medium Gyro (3.0 - 5.0 rad/s): {sum(3.0 <= r['w_gyro_max'] < 5.0 for r in regions)} regions")
print(f"  High Gyro (>= 5.0 rad/s): {sum(r['w_gyro_max'] >= 5.0 for r in regions)} regions")

# Load narrated ground truth
narr_path = os.path.join(SESSION_DIR, "narrations_raw.json")
if os.path.exists(narr_path):
    narr = json.load(open(narr_path))
    gt_times = [float(e['timestamp_seconds']) for e in narr if e.get('shot_type') and not any(k in e['shot_type'].lower() for k in ['facing up','no shot','leave','evade','block'])]
    print(f"\nGround Truth Physical Shots in Narration: {len(gt_times)}")

# ============================================================
# EXPERIMENT: PROBABILITY THRESHOLD SWEEP & NMS FILTERS
# ============================================================
print(f"\n============================================================")
print(f"  POST-PROCESSING EXPERIMENT: PROBABILITY THRESHOLD SWEEP")
print(f"============================================================")

for min_p in [0.5, 0.6, 0.7, 0.8, 0.9]:
    for min_gyro in [3.5, 4.5, 5.5]:
        # Extract regions matching min_p
        is_shot_p = (probs_full[2:10, :].sum(axis=0) >= min_p)
        reg_p = []
        i = 0
        while i < len(is_shot_p):
            if is_shot_p[i]:
                j = i
                while j < len(is_shot_p) and is_shot_p[j]: j += 1
                dur_ms = (j - i) * (1000.0 / 423.0)
                w_gyro_max = np.linalg.norm(X[i:j, 3:6], axis=1).max() if j > i else 0
                peak_sec = (i + j) / 2.0 / 423.0
                reg_p.append({'peak_sec': peak_sec, 'w_gyro_max': w_gyro_max, 'dur_ms': dur_ms})
                i = j
            else: i += 1
            
        filt_p = [r for r in reg_p if r['w_gyro_max'] >= min_gyro and r['dur_ms'] >= 100]
        nms_p = []
        for r in sorted(filt_p, key=lambda x: x['peak_sec']):
            if not nms_p or (r['peak_sec'] - nms_p[-1]['peak_sec']) >= 1.5:
                nms_p.append(r)
                
        matched_gt = sum(1 for gt in gt_times if any(abs(r['peak_sec'] - gt) <= 0.75 for r in nms_p))
        recall = matched_gt / len(gt_times) if gt_times else 0
        precision = matched_gt / len(nms_p) if nms_p else 0
        
        print(f"  Min Prob >= {min_p:3.2f} | Gyro >= {min_gyro:3.1f} rad/s | NMS 1.5s -> {len(nms_p):3d} shots detected | Recall: {recall*100:5.1f}% ({matched_gt}/{len(gt_times)}) | Precision: {precision*100:5.1f}%")


