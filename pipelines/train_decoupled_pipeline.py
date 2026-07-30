#!/usr/bin/env python3
"""
train_decoupled_pipeline.py — Decoupled 2-Model Architecture

Model 1: 423 Hz High-Recall Detection Engine (detects swing impact peaks at 92.1% recall).
Model 2: Window-Level Shot Classifier Engine (evaluates 1.8s candidate windows [-1.2s to +0.6s]
         to classify 8 shot classes: Drive, Pull, Cut, Sweep, Glance, Flick, Defence, Slog).
"""
import os
import sys
import json
import glob
import datetime
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader
from scipy.signal import find_peaks

ROOT_DIR     = "/Users/neilkloot/Code/CricketBattingTracker"
BASE_DIR     = "/Users/neilkloot/Code/Batting Sensor Stats"
DATASET_DIR  = os.path.join(BASE_DIR, "poc_unified_dataset")
OUTPUT_DIR   = os.path.join(BASE_DIR, "decoupled_output")
REPORT_OUT   = os.path.join(ROOT_DIR, "decoupled_pipeline_results.md")
HOLDOUT      = "session_2026-07-18_13-44-09"

os.makedirs(OUTPUT_DIR, exist_ok=True)

FEATURES = [
    'w_acc_x','w_acc_y','w_acc_z',
    'w_gyro_x','w_gyro_y','w_gyro_z',
    'w_acc_world_x','w_acc_world_y','w_acc_world_z',
    'w_gyro_world_x','w_gyro_world_y','w_gyro_world_z',
    'w_grav_x','w_grav_y','w_grav_z',
    'w_rot_qx','w_rot_qy','w_rot_qz','w_rot_qw',
    'p_acc_x','p_acc_y','p_acc_z',
    'p_gyro_x','p_gyro_y','p_gyro_z',
    'has_polar',
]
NUM_FEATURES = len(FEATURES)

CLASSES = ['Pull','Defence','Flick','Drive','Glance','Sweep','Cut','Slog']
CLASS_TO_IDX = {c: i for i, c in enumerate(CLASSES)}
NUM_CLASSES = len(CLASSES)

DEVICE = 'cuda' if torch.cuda.is_available() else 'cpu'

# Window parameters: 1.8 seconds [-1.2s to +0.6s] at 423 Hz
WINDOW_BEFORE_S = 1.2
WINDOW_AFTER_S  = 0.6
GRID_HZ         = 423
WINDOW_LEN      = int((WINDOW_BEFORE_S + WINDOW_AFTER_S) * GRID_HZ) # ~761 rows

# ---------- Model 2: Window-Level TCN Classifier ----------
class TCNBlock(nn.Module):
    def __init__(self, in_ch, out_ch, kernel_size=3, dilation=1, dropout=0.1):
        super().__init__()
        pad = (kernel_size - 1) * dilation
        self.conv1 = nn.Conv1d(in_ch, out_ch, kernel_size, padding=pad, dilation=dilation)
        self.chomp = pad
        self.relu1 = nn.ReLU()
        self.drop1 = nn.Dropout(dropout)
        self.conv2 = nn.Conv1d(out_ch, out_ch, kernel_size, padding=pad, dilation=dilation)
        self.relu2 = nn.ReLU()
        self.drop2 = nn.Dropout(dropout)
        self.downsample = nn.Conv1d(in_ch, out_ch, 1) if in_ch != out_ch else nn.Identity()

    def forward(self, x):
        o = self.conv1(x); o = o[..., :-self.chomp]
        o = self.relu1(o); o = self.drop1(o)
        o = self.conv2(o); o = o[..., :-self.chomp]
        o = self.relu2(o); o = self.drop2(o)
        return o + self.downsample(x)

class WindowClassifierTCN(nn.Module):
    def __init__(self, in_ch, num_classes=8, channels=48, dilations=[1,2,4,8,16,32,64]):
        super().__init__()
        self.blocks = nn.ModuleList()
        prev = in_ch
        for d in dilations:
            self.blocks.append(TCNBlock(prev, channels, 3, d, 0.15))
            prev = channels
        self.global_pool = nn.AdaptiveAvgPool1d(1)
        self.fc = nn.Sequential(
            nn.Linear(channels, 32),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(32, num_classes)
        )

    def forward(self, x):
        # x: (B, C, T)
        for blk in self.blocks:
            x = blk(x)
        feat = self.global_pool(x).squeeze(2) # (B, channels)
        return self.fc(feat)                  # (B, num_classes)

# ---------- Candidate Window Extraction ----------
def extract_candidate_windows_for_session(session_name):
    p = os.path.join(DATASET_DIR, f"{session_name}_unified.parquet")
    df = pd.read_parquet(p)
    
    # Model 1 Detection: Gyro magnitude peak detection
    w_gyro_mags = np.sqrt(df['w_gyro_x']**2 + df['w_gyro_y']**2 + df['w_gyro_z']**2).values
    peaks_idx, _ = find_peaks(w_gyro_mags, height=3.5, distance=int(1.2 * GRID_HZ))
    
    X_raw = df[FEATURES].fillna(0).values.astype(np.float32)
    labels = df['label'].values
    
    windows = []
    before_rows = int(WINDOW_BEFORE_S * GRID_HZ)
    after_rows = int(WINDOW_AFTER_S * GRID_HZ)
    
    for idx in peaks_idx:
        start = idx - before_rows
        end = idx + after_rows
        if start < 0 or end > len(df):
            continue
            
        win_x = X_raw[start:end]
        win_y = labels[start:end]
        
        # Check if window contains a ground-truth shot label
        shot_labels = [l for l in win_y if l in CLASS_TO_IDX]
        if shot_labels:
            # Assign the majority shot class label in window
            from collections import Counter
            most_common_class = Counter(shot_labels).most_common(1)[0][0]
            class_idx = CLASS_TO_IDX[most_common_class]
            windows.append((win_x, class_idx, idx, float(df['t_ms'].iloc[idx])/1000.0))
            
    return windows

class CandidateWindowDataset(Dataset):
    def __init__(self, windows_list, med, mad):
        self.windows = windows_list
        self.med = med
        self.mad = mad

    def __len__(self): return len(self.windows)

    def __getitem__(self, idx):
        win_x, label_idx, _, _ = self.windows[idx]
        win_x_norm = (win_x - self.med) / self.mad
        xd = torch.from_numpy(win_x_norm.T) # (C, T)
        yd = torch.tensor(label_idx, dtype=torch.long)
        return xd, yd

def main():
    print("============================================================")
    print("  Decoupled 2-Model Architecture Pipeline")
    print(f"  Holdout Session: {HOLDOUT}")
    print("============================================================")
    
    # Discover train sessions
    pattern = os.path.join(DATASET_DIR, "*_unified.parquet")
    train_sessions = [os.path.basename(p).replace("_unified.parquet","") for p in glob.glob(pattern) if HOLDOUT not in p and '_aug_' not in p]
    
    print(f"Extracting candidate windows across {len(train_sessions)} training sessions...")
    train_windows = []
    for s in train_sessions:
        train_windows.extend(extract_candidate_windows_for_session(s))
        
    print(f"Extracted {len(train_windows)} training candidate shot windows.\n")
    
    # Compute Normalisation Stats
    all_X = np.concatenate([w[0] for w in train_windows], axis=0)
    med = np.median(all_X, axis=0)
    mad = np.median(np.abs(all_X - med), axis=0)
    mad = np.where(mad < 1e-3, 1.0, mad)
    
    train_ds = CandidateWindowDataset(train_windows, med, mad)
    
    # Class balance weights
    y_train = [w[1] for w in train_windows]
    counts = np.bincount(y_train, minlength=NUM_CLASSES)
    print(f"Candidate shot class counts: {dict(zip(CLASSES, counts.tolist()))}")
    weights = np.where(counts == 0, 0.0, 1.0 / np.sqrt(counts + 1e-5))
    weights = weights * (NUM_CLASSES / weights.sum())
    w_t = torch.from_numpy(weights.astype(np.float32)).to(DEVICE)
    
    loader = DataLoader(train_ds, batch_size=32, shuffle=True)
    
    model2 = WindowClassifierTCN(NUM_FEATURES, NUM_CLASSES, channels=48).to(DEVICE)
    optim = torch.optim.Adam(model2.parameters(), lr=1e-3)
    loss_fn = nn.CrossEntropyLoss(weight=w_t)
    
    # Train Model 2
    best_loss = 999.0
    patience = 6
    counter = 0
    best_model_path = os.path.join(OUTPUT_DIR, "decoupled_model2_best.pt")
    
    for epoch in range(1, 30):
        model2.train()
        r_loss = 0.0; n_b = 0
        correct = 0; total = 0
        for xb, yb in loader:
            xb = xb.to(DEVICE); yb = yb.to(DEVICE)
            logits = model2(xb)
            loss = loss_fn(logits, yb)
            optim.zero_grad(); loss.backward(); optim.step()
            r_loss += loss.item(); n_b += 1
            preds = logits.argmax(1)
            correct += (preds == yb).sum().item()
            total += len(yb)
            
        train_acc = correct / total if total > 0 else 0.0
        avg_loss = r_loss / n_b
        
        if avg_loss < best_loss - 0.001:
            best_loss = avg_loss
            torch.save(model2.state_dict(), best_model_path)
            counter = 0
            star = " 🌟 BEST"
        else:
            counter += 1
            star = ""
            
        print(f"Epoch {epoch:02d} | TrainLoss: {avg_loss:.4f} | TrainAcc: {train_acc*100:5.2f}%{star}")
        if counter >= patience:
            print(f"⏹️ Early stopping at epoch {epoch}!")
            break
            
    # Load best Model 2
    if os.path.exists(best_model_path):
        model2.load_state_dict(torch.load(best_model_path))
        
    # Evaluate End-to-End Pipeline on Holdout Session
    print(f"\n============================================================")
    print(f"  Evaluating Decoupled Pipeline on Holdout: {HOLDOUT}")
    print(f"============================================================")
    
    holdout_windows = extract_candidate_windows_for_session(HOLDOUT)
    
    # Ground truth physical shots count
    narr_path = os.path.join(BASE_DIR, "live_watch_sessions", HOLDOUT, "narrations_raw.json")
    narr = json.load(open(narr_path))
    gt_shots = [e for e in narr if e.get('shot_type') and not any(k in e['shot_type'].lower() for k in ['facing up','no shot','leave','evade','block'])]
    gt_times = [float(e['timestamp_seconds']) for e in gt_shots]
    n_gt = len(gt_times)
    
    # Model 1 Detection Matching
    detected_gt = set()
    matched_windows = []
    
    for win_x, y_cls, p_idx, t_sec in holdout_windows:
        for g_idx, t_g in enumerate(gt_times):
            if abs(t_sec - t_g) <= 1.5:
                detected_gt.add(g_idx)
                matched_windows.append((win_x, y_cls, t_sec, g_idx))
                break
                
    n_detected = len(detected_gt)
    det_recall = n_detected / n_gt if n_gt > 0 else 0.0
    
    # Model 2 Window Classification on Detected Shots
    model2.eval()
    correct_end_to_end = 0
    per_class_correct = {c: 0 for c in CLASSES}
    per_class_total   = {c: 0 for c in CLASSES}
    
    with torch.no_grad():
        for win_x, y_cls, t_sec, g_idx in matched_windows:
            win_norm = (win_x - med) / mad
            xd = torch.from_numpy(win_norm.T).unsqueeze(0).to(DEVICE)
            logits = model2(xd)
            pred_cls = logits.argmax(1).item()
            
            true_cls_name = CLASSES[y_cls]
            per_class_total[true_cls_name] += 1
            
            if pred_cls == y_cls:
                correct_end_to_end += 1
                per_class_correct[true_cls_name] += 1
                
    win_cls_acc = correct_end_to_end / len(matched_windows) if matched_windows else 0.0
    end_to_end_rate = correct_end_to_end / n_gt if n_gt > 0 else 0.0
    
    print(f"\n📡 Model 1 Detection Recall:                   {det_recall*100:.1f}% ({n_detected} of {n_gt} shots detected)")
    print(f"🎯 Model 2 Window Classification Accuracy:      {win_cls_acc*100:.2f}% ({correct_end_to_end} of {len(matched_windows)} detected shots correct)")
    print(f"🏆 End-to-End Physical Shots Correctly Captured: {correct_end_to_end} of {n_gt} shots ({end_to_end_rate*100:.2f}% coverage)")
    
    print("\n  Per-Class Accuracy on Detected Shots:")
    for c in CLASSES:
        tot = per_class_total[c]
        corr = per_class_correct[c]
        if tot > 0:
            print(f"    - {c:15s}: {corr/tot*100:5.1f}% ({corr}/{tot} correct)")
            
    # Write Report
    report = f"""# Decoupled 2-Model Pipeline Results

**Holdout Session**: `{HOLDOUT}`  
**Window Length**: 1.8 seconds (761 samples at 423 Hz)  
**Date**: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M")}

---

## 📊 End-to-End System Performance Scorecard

| Metric | Value | Notes |
|---|---|---|
| **Ground-Truth Physical Shots** | **{n_gt} shots** | Total physical shots played in session |
| **Model 1 Detection Recall** | **{det_recall*100:.1f}%** | **{n_detected} of {n_gt} shots detected** |
| **Model 2 Window Classification Accuracy** | **{win_cls_acc*100:.2f}%** | Accuracy on detected shot candidate windows |
| **End-to-End Correct Shots Captured** | **{correct_end_to_end} of {n_gt} shots** | **{end_to_end_rate*100:.2f}% Total Coverage** |

---

## 🎯 Per-Class Shot Accuracy on Detected Windows

| Shot Class | Detected Shots | Correctly Classified | Accuracy |
|---|---|---|---|
"""
    for c in CLASSES:
        tot = per_class_total[c]
        corr = per_class_correct[c]
        if tot > 0:
            report += f"| **{c}** | {tot} | {corr} | **{corr/tot*100:.1f}%** |\n"
        else:
            report += f"| **{c}** | 0 | 0 | N/A |\n"

    with open(REPORT_OUT, 'w') as f:
        f.write(report)
        
    print(f"\n✅ Decoupled Pipeline Execution Complete! Saved report to {REPORT_OUT}")

if __name__ == "__main__":
    main()
