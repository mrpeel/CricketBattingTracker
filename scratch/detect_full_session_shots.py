#!/usr/bin/env python3
"""
detect_full_session_shots.py — Run Stage 1 Impact Shockwave Anchor Detector
+ Ultimate TCN Classifier across the FULL 28.8 minute sensor recording for session_2026-08-01_10-18-20.
"""
import os
import sys
import numpy as np
import pandas as pd
import torch

ROOT_DIR = "/Users/neilkloot/Code/CricketBattingTracker"
BASE_DIR = "/Users/neilkloot/Code/Batting Sensor Stats"
UNIFIED_PARQUET = os.path.join(BASE_DIR, "poc_unified_dataset", "session_2026-08-01_10-18-20_unified.parquet")

sys.path.append(os.path.join(ROOT_DIR, "pipelines"))
from train_and_evaluate_full_scorecard import AdvancedTCN, CLASSES, FEATURES

print(f"Loading full session sensor dataset: {UNIFIED_PARQUET}")
df = pd.read_parquet(UNIFIED_PARQUET)
print(f"Loaded {len(df)} frames ({len(df)/423.0/60.0:.2f} total minutes at 423 Hz)!")

# Extract features
X = df[FEATURES].fillna(0).values
w_acc_mags  = np.linalg.norm(df[['w_acc_x','w_acc_y','w_acc_z']].fillna(0).values, axis=1)
w_gyro_mags = np.linalg.norm(df[['w_gyro_x','w_gyro_y','w_gyro_z']].fillna(0).values, axis=1)

# Pre-shot stillness rolling std over 254 frames
gyro_std_254 = pd.Series(w_gyro_mags).rolling(window=254, min_periods=50).std().shift(85).fillna(0.0).values

# Stage 1: Decoupled Impact Shockwave Anchor Detector
impact_mask = (w_acc_mags >= 30.0) & (w_gyro_mags >= 4.0)
impact_frames = np.where(impact_mask)[0]

anchors = []
if len(impact_frames) > 0:
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

print(f"Stage 1 Impact Shockwave Anchors Found: {len(anchors)} candidates")

# Apply Burst Mode Adaptive Hysteresis Gate
verified_anchors = []
last_verified_sec = -999.0
for f in anchors:
    candidate_sec = f / 423.0
    pre_stillness_std = gyro_std_254[f]
    delta_t = candidate_sec - last_verified_sec
    thresh = 3.0 if delta_t < 10.0 else 2.0
    if pre_stillness_std <= thresh or delta_t < 2.0:
        verified_anchors.append(f)
        last_verified_sec = candidate_sec

print(f"Verified Anchors after Burst Mode Hysteresis Gate: {len(verified_anchors)} physical shots")

# Stage 2: TCN Shot Classification
ckpt_path = os.path.join(ROOT_DIR, "pipelines", "tcn_ultimate_baseline.pt")
model = AdvancedTCN(in_ch=X.shape[1], num_classes=len(CLASSES))
model.load_state_dict(torch.load(ckpt_path, map_location='cpu'))
model.eval()

# Run sliding TCN inference
with torch.no_grad():
    input_tensor = torch.from_numpy(X.T).unsqueeze(0).float()
    logits = model(input_tensor)
    probs = torch.softmax(logits, dim=1).squeeze(0).numpy()

classified_shots = []
for f in verified_anchors:
    sec = f / 423.0
    w_s = max(0, f - 42)
    w_e = min(len(X), f + 42)
    win_probs = probs[:, w_s:w_e]
    top_class_idx = np.argmax(win_probs[2:10, :].max(axis=1)) + 2
    top_prob = win_probs[top_class_idx, :].max()
    shot_cls = CLASSES[top_class_idx]
    classified_shots.append({
        'sec': sec,
        'min_sec': f"{int(sec//60)}m {sec%60:.1f}s",
        'acc_peak': w_acc_mags[f],
        'gyro_peak': w_gyro_mags[f],
        'class': shot_cls,
        'prob': top_prob
    })

df_results = pd.DataFrame(classified_shots)
print("\n" + "="*80)
print(f"🏆 DETECTED PHYSICAL SHOTS ACROSS FULL 28.8 MINUTE SESSION ({len(df_results)} TOTAL SHOTS)")
print("="*80)
print(df_results[['min_sec', 'class', 'acc_peak', 'gyro_peak', 'prob']].to_string(index=False))

print("\n📊 SHOT CLASS BREAKDOWN:")
print(df_results['class'].value_counts().to_string())
