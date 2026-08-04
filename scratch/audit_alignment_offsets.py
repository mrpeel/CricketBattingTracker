#!/usr/bin/env python3
"""
audit_alignment_offsets.py — Inspect exact time deltas between model predictions and GT narrations
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

w_gyro_mags = np.linalg.norm(X[:, 3:6], axis=1)
shot_probs = probs_full[2:10, :].sum(axis=0)

# Filter candidate regions with prob >= 0.70 and gyro >= 3.0 rad/s
is_shot_p = (shot_probs >= 0.70) & (w_gyro_mags >= 3.0)
reg_p = []
i = 0
while i < len(is_shot_p):
    if is_shot_p[i]:
        j = i
        while j < len(is_shot_p) and is_shot_p[j]: j += 1
        peak_idx = i + np.argmax(shot_probs[i:j])
        peak_sec = peak_idx / 423.0
        w_gyro_max = w_gyro_mags[i:j].max()
        top_cls = classes[preds_full[peak_idx]]
        top_prob = probs_full[preds_full[peak_idx], peak_idx]
        reg_p.append({'peak_sec': peak_sec, 'w_gyro_max': w_gyro_max, 'top_cls': top_cls, 'top_prob': top_prob})
        i = j
    else: i += 1

# Apply NMS with 1.5s gap
nms_shots = []
for r in sorted(reg_p, key=lambda x: x['peak_sec']):
    if not nms_shots or (r['peak_sec'] - nms_shots[-1]['peak_sec']) >= 1.5:
        nms_shots.append(r)

print(f"Total NMS Detections (prob >= 0.70 & gyro >= 3.0): {len(nms_shots)}")
print(f"Total Narrated Ground Truth Shots: {len(gt_events)}")

# Inspect time deltas for all GT shots to nearest NMS detection
deltas = []
matched_gt_ids = set()
for idx, e in enumerate(gt_events):
    gt_sec = float(e['timestamp_seconds'])
    nearest_det = min(nms_shots, key=lambda r: abs(r['peak_sec'] - gt_sec)) if nms_shots else None
    dt = nearest_det['peak_sec'] - gt_sec if nearest_det else 999.0
    abs_dt = abs(dt)
    is_matched = abs_dt <= 1.5
    if is_matched:
        matched_gt_ids.add(idx)
    deltas.append({
        'gt_id': idx + 1,
        'gt_sec': gt_sec,
        'gt_type': e['shot_type'],
        'det_sec': nearest_det['peak_sec'] if nearest_det else 0,
        'det_cls': nearest_det['top_cls'] if nearest_det else '',
        'dt_sec': dt,
        'abs_dt_sec': abs_dt,
        'matched_1.5s': is_matched
    })

print("\n============================================================")
print("  ACCURACY & RECALL VS TOLERANCE WINDOW (0.75s to 3.5s)")
print("============================================================")

for window in [0.75, 1.25, 1.75, 2.25, 2.75, 3.25]:
    matched_gt = sum(1 for d in deltas if any(abs(r['peak_sec'] - d['gt_sec']) <= window for r in nms_shots))
    matched_dets = sum(1 for r in nms_shots if any(abs(r['peak_sec'] - d['gt_sec']) <= window for d in deltas))
    rec = matched_gt / len(gt_events) if gt_events else 0
    prec = matched_dets / len(nms_shots) if nms_shots else 0
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0
    print(f"  Matching Window +- {window:4.2f}s | GT Recall: {rec*100:5.1f}% ({matched_gt:2d}/{len(gt_events)}) | Precision: {prec*100:5.1f}% ({matched_dets:2d}/{len(nms_shots)}) | F1: {f1*100:5.1f}%")


# Inspect False Alarms (Detections that are NOT near any GT shot)
false_alarms = []
for r in nms_shots:
    nearest_gt = min(gt_events, key=lambda e: abs(float(e['timestamp_seconds']) - r['peak_sec']))
    min_dist = abs(float(nearest_gt['timestamp_seconds']) - r['peak_sec'])
    if min_dist > 1.5:
        false_alarms.append({
            'det_sec': r['peak_sec'],
            'top_cls': r['top_cls'],
            'top_prob': r['top_prob'],
            'w_gyro_max': r['w_gyro_max'],
            'nearest_gt_dist_sec': min_dist
        })

df_fa = pd.DataFrame(false_alarms)
print(f"\n--- FALSE ALARM DETECTIONS ({len(false_alarms)} Detections > 1.5s from any GT shot) ---")
if not df_fa.empty:
    print(df_fa.to_string(index=False))
