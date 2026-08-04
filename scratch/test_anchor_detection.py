#!/usr/bin/env python3
"""
test_anchor_detection.py — Test Impact Shockwave Anchored Detection + TCN Classification
"""
import os
import sys
import json
import numpy as np
import pandas as pd
import torch

ROOT_DIR = "/Users/neilkloot/Code/CricketBattingTracker"
BASE_DIR = "/Users/neilkloot/Code/Batting Sensor Stats"
SESSION_DIR = os.path.join(BASE_DIR, "live_watch_sessions", "session_2026-07-31_12-44-46")
UNIFIED_DIR = os.path.join(BASE_DIR, "poc_unified_dataset")

STATS_PATH = os.path.join(ROOT_DIR, "pipelines/tcn_norm_stats.json")
stats = json.load(open(STATS_PATH))
features = stats['features']
classes = stats['classes']
med = np.array(stats['median'], dtype=np.float32)
mad = np.array(stats['mad'], dtype=np.float32)
mad = np.where(mad < 1e-3, 1.0, mad)

unified_path = os.path.join(UNIFIED_DIR, "session_2026-07-31_12-44-46_unified.parquet")
df = pd.read_parquet(unified_path)

X = df[features].fillna(0).values.astype(np.float32)
X_norm = (X - med) / mad

MODEL_PT_PATH = os.path.join(ROOT_DIR, "pipelines/tcn_ultimate_baseline.pt")
sys.path.append(os.path.join(ROOT_DIR, "pipelines"))
from export_tcn_to_onnx import AdvancedTCN

model = AdvancedTCN(in_ch=len(features), num_classes=len(classes), channels=32)
model.load_state_dict(torch.load(MODEL_PT_PATH, map_location='cpu'))
model.eval()

# Run TCN inference
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
        logits = model(chunk_t)[0, :, :n_frames].numpy()
        exp_logits = np.exp(logits - np.max(logits, axis=0, keepdims=True))
        probs = exp_logits / np.sum(exp_logits, axis=0, keepdims=True)
        preds = np.argmax(probs, axis=0)
        preds_list.append(preds)
        probs_list.append(probs)

preds_full = np.concatenate(preds_list)[:len(X)]
probs_full = np.hstack(probs_list)[:, :len(X)]

# Load Narrations
narr_path = os.path.join(SESSION_DIR, "narrations_raw.json")
narr = json.load(open(narr_path))
gt_events = [e for e in narr if e.get('shot_type') and not any(k in e['shot_type'].lower() for k in ['facing up','no shot','leave','evade','block'])]
gt_times = [float(e['timestamp_seconds']) for e in gt_events]

w_acc_mags  = np.linalg.norm(X[:, 0:3], axis=1)
w_gyro_mags = np.linalg.norm(X[:, 3:6], axis=1)
p_acc_mags  = np.linalg.norm(X[:, 19:22], axis=1) if X[0, 25] > 0.5 else w_acc_mags

print("============================================================")
print("  TESTING IMPACT ANCHOR DETECTOR + TCN CLASSIFICATION")
print("============================================================")

# Strategy: Find physical impact peaks in Polar Acc / Watch Accel & Watch Gyro
for min_acc in [35.0, 45.0, 55.0, 65.0]:
    for min_gyro in [5.0, 6.5, 8.0]:
        # Identify impact frames
        impact_mask = (w_acc_mags >= min_acc) & (w_gyro_mags >= min_gyro)
        
        impact_frames = np.where(impact_mask)[0]
        if len(impact_frames) == 0: continue
        
        # Group impact peaks within 1.5s (634 frames at 423Hz)
        anchors = []
        cluster = [impact_frames[0]]
        for idx in range(1, len(impact_frames)):
            if impact_frames[idx] - impact_frames[idx-1] <= 423:
                cluster.append(impact_frames[idx])
            else:
                peak_f = cluster[np.argmax(w_acc_mags[cluster])]
                anchors.append(peak_f)
                cluster = [impact_frames[idx]]
        if cluster:
            peak_f = cluster[np.argmax(w_acc_mags[cluster])]
            anchors.append(peak_f)
            
        # Classify each anchor using TCN model output around peak_f (+-100ms)
        anchored_shots = []
        for f in anchors:
            w_s = max(0, f - 42)
            w_e = min(len(X), f + 42)
            
            # Find class with max prob in +-100ms window
            win_probs = probs_full[:, w_s:w_e]
            top_class_idx = np.argmax(win_probs[2:10, :].max(axis=1)) + 2 # Shot classes only
            top_prob = win_probs[top_class_idx, :].max()
            pred_name = classes[top_class_idx]
            
            anchored_shots.append({
                'frame': f,
                'sec': f / 423.0,
                'pred_class': pred_name,
                'prob': top_prob,
                'w_acc': w_acc_mags[f],
                'w_gyro': w_gyro_mags[f]
            })
            
# Run optimal operating point: Acc >= 45.0 m/s2, Gyro >= 6.5 rad/s
impact_mask = (w_acc_mags >= 45.0) & (w_gyro_mags >= 6.5)
impact_frames = np.where(impact_mask)[0]

cluster = [impact_frames[0]]
anchors = []
for idx in range(1, len(impact_frames)):
    if impact_frames[idx] - impact_frames[idx-1] <= 423:
        cluster.append(impact_frames[idx])
    else:
        peak_f = cluster[np.argmax(w_acc_mags[cluster])]
        anchors.append(peak_f)
        cluster = [impact_frames[idx]]
if cluster:
    peak_f = cluster[np.argmax(w_acc_mags[cluster])]
    anchors.append(peak_f)

final_shots = []
for f in anchors:
    w_s = max(0, f - 42)
    w_e = min(len(X), f + 42)
    win_probs = probs_full[:, w_s:w_e]
    top_class_idx = np.argmax(win_probs[2:10, :].max(axis=1)) + 2
    top_prob = win_probs[top_class_idx, :].max()
    pred_name = classes[top_class_idx]
    
    # Match to nearest GT
    gt_match = None
    min_dist = 999.0
    for e in gt_events:
        dist = abs(float(e['timestamp_seconds']) - (f / 423.0))
        if dist < min_dist:
            min_dist = dist
            gt_match = e
            
    final_shots.append({
        'sec': f / 423.0,
        'pred_class': pred_name,
        'prob': top_prob,
        'gt_type': gt_match['shot_type'] if min_dist <= 2.5 else 'FALSE_ALARM',
        'dist_s': min_dist if min_dist <= 2.5 else None
    })

df_final = pd.DataFrame(final_shots)
print("\n============================================================")
print(f"  FINAL SCORECARD: SESSION 2026-07-31_12-44-46")
print("============================================================")
print(f"  Total Narrated Shots: {len(gt_events)}")
print(f"  Total Detections: {len(df_final)}")
print(f"  Physical Shots Captured: {sum(df_final['gt_type'] != 'FALSE_ALARM')} / {len(gt_events)} ({(sum(df_final['gt_type'] != 'FALSE_ALARM')/len(gt_events))*100:.1f}% RECALL)")
print(f"  False Alarms: {sum(df_final['gt_type'] == 'FALSE_ALARM')} (PRECISION: {(sum(df_final['gt_type'] != 'FALSE_ALARM')/len(df_final))*100:.1f}%)")

print("\n--- DETAILED SHOT-BY-SHOT SCORECARD ---")
print(df_final.to_string(index=False))

