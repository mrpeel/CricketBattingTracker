#!/usr/bin/env python3
"""
deep_dive_session_2026-07-31.py — Deep Diagnostic Audit of session_2026-07-31_12-44-46
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

preds_full = np.concatenate(preds_list)[:len(X)]
probs_full = np.hstack(probs_list)[:, :len(X)]

# Ground Truth Narrations
narr_path = os.path.join(SESSION_DIR, "narrations_raw.json")
narr = json.load(open(narr_path))
gt_events = [e for e in narr if e.get('shot_type') and not any(k in e['shot_type'].lower() for k in ['facing up','no shot','leave','evade','block'])]

print(f"============================================================")
print(f"  DEEP AUDIT: {len(gt_events)} NARRATED PHYSICAL SHOTS")
print(f"============================================================")

w_gyro_mags = np.linalg.norm(X[:, 3:6], axis=1)
w_acc_mags  = np.linalg.norm(X[:, 0:3], axis=1)
p_acc_mags  = np.linalg.norm(X[:, 19:22], axis=1) if X[0, 25] > 0.5 else w_acc_mags

shot_probs = probs_full[2:10, :].sum(axis=0)

gt_audit = []
for idx, e in enumerate(gt_events):
    gt_sec = float(e['timestamp_seconds'])
    gt_frame = int(gt_sec * 423.0)
    shot_type = e['shot_type']
    
    # Search around +- 1.0s window (423 frames)
    w_start = max(0, gt_frame - 423)
    w_end   = min(len(df), gt_frame + 423)
    
    win_probs = shot_probs[w_start:w_end]
    win_gyro  = w_gyro_mags[w_start:w_end]
    win_acc   = w_acc_mags[w_start:w_end]
    win_p_acc = p_acc_mags[w_start:w_end]
    
    max_p = win_probs.max() if len(win_probs) > 0 else 0
    max_g = win_gyro.max() if len(win_gyro) > 0 else 0
    max_a = win_acc.max() if len(win_acc) > 0 else 0
    max_pa = win_p_acc.max() if len(win_p_acc) > 0 else 0
    
    # Get top predicted class around peak
    top_frame = w_start + np.argmax(win_probs) if len(win_probs) > 0 else gt_frame
    pred_cls  = classes[preds_full[top_frame]]
    pred_cls_prob = probs_full[preds_full[top_frame], top_frame]
    
    gt_audit.append({
        'id': idx + 1,
        'gt_sec': gt_sec,
        'shot_type': shot_type,
        'max_shot_prob': max_p,
        'max_w_gyro': max_g,
        'max_w_acc': max_a,
        'max_p_acc': max_pa,
        'pred_class': pred_cls,
        'pred_prob': pred_cls_prob
    })

df_gt_audit = pd.DataFrame(gt_audit)
print("\n--- GROUND TRUTH SHOTS AUDIT (First 20 Shots) ---")
print(df_gt_audit.head(20).to_string(index=False))

print("\n--- GROUND TRUTH SHOTS SUMMARY STATISTICS ---")
print(f"Max Shot Prob Distribution across GT shots:")
print(f"  >= 0.70: {sum(df_gt_audit['max_shot_prob'] >= 0.70)} / {len(gt_events)}")
print(f"  >= 0.50: {sum(df_gt_audit['max_shot_prob'] >= 0.50)} / {len(gt_events)}")
print(f"  >= 0.30: {sum(df_gt_audit['max_shot_prob'] >= 0.30)} / {len(gt_events)}")
print(f"  <  0.30: {sum(df_gt_audit['max_shot_prob'] <  0.30)} / {len(gt_events)}")

print(f"\nMax Watch Gyroscope Distribution across GT shots (rad/s):")
print(f"  >= 5.0: {sum(df_gt_audit['max_w_gyro'] >= 5.0)} / {len(gt_events)}")
print(f"  >= 3.0: {sum(df_gt_audit['max_w_gyro'] >= 3.0)} / {len(gt_events)}")
print(f"  >= 1.5: {sum(df_gt_audit['max_w_gyro'] >= 1.5)} / {len(gt_events)}")
print(f"  <  1.5: {sum(df_gt_audit['max_w_gyro'] <  1.5)} / {len(gt_events)}")

print(f"\nMax Polar Acceleration Distribution across GT shots (m/s^2):")
print(f"  >= 30.0: {sum(df_gt_audit['max_p_acc'] >= 30.0)} / {len(gt_events)}")
print(f"  >= 20.0: {sum(df_gt_audit['max_p_acc'] >= 20.0)} / {len(gt_events)}")
print(f"  >= 12.0: {sum(df_gt_audit['max_p_acc'] >= 12.0)} / {len(gt_events)}")
print(f"  <  12.0: {sum(df_gt_audit['max_p_acc'] <  12.0)} / {len(gt_events)}")
