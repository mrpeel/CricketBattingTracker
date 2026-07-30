#!/usr/bin/env python3
"""
run_ablation_study.py — Systematic 8-Run Ablation Assessment Pipeline

Evaluates the 3 experimental factors independently, in pairs, and all 3 combined:
  Factor A: Downsampling (200Hz, 5ms grid, 600-sample window) vs 423Hz (2048-sample window)
  Factor B: Derived Kinematic Data (32 features: +Gyro/Acc Mags, Jerk, Energy, Polar Mags) vs Raw 26
  Factor C: Multi-Task Dual-Head Network (det_head + cls_head) vs Single Softmax Head

Outputs:
  - ablation_study_results.md (Complete markdown report comparing all 8 runs against baselines)
"""
import os
import sys
import json
import glob
import time
import datetime
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader

ROOT_DIR     = "/Users/neilkloot/Code/CricketBattingTracker"
BASE_DIR     = "/Users/neilkloot/Code/Batting Sensor Stats"
DATASET_DIR  = os.path.join(BASE_DIR, "poc_unified_dataset")
OUTPUT_DIR   = os.path.join(BASE_DIR, "ablation_output")
REPORT_OUT   = os.path.join(ROOT_DIR, "ablation_study_results.md")
HOLDOUT      = "session_2026-07-18_13-44-09"

os.makedirs(OUTPUT_DIR, exist_ok=True)

RAW_FEATURES = [
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

DERIVED_FEATURES = RAW_FEATURES + [
    'w_gyro_mag', 'w_acc_mag', 'w_jerk_mag', 'w_gyro_energy', 'p_acc_mag', 'p_gyro_mag'
]

CLASSES = ['no_shot','pre_shot','Pull','Defence','Flick','Drive','Glance','Sweep','Cut','Slog']
CLASS_TO_IDX = {c: i for i, c in enumerate(CLASSES)}
NUM_CLASSES = len(CLASSES)
SHOT_CLASS_INDICES = set([CLASS_TO_IDX[c] for c in CLASSES if c not in ('no_shot','pre_shot')])

DEVICE = 'cuda' if torch.cuda.is_available() else 'cpu'

# ---------- TCN Architecture Variants ----------
class TCNBlock(nn.Module):
    def __init__(self, in_ch, out_ch, kernel_size, dilation, dropout=0.1):
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

class SingleHeadTCN(nn.Module):
    def __init__(self, in_ch, num_classes=10, channels=32, dilations=[1,2,4,8,16,32,64,128,256,512]):
        super().__init__()
        self.blocks = nn.ModuleList()
        prev = in_ch
        for d in dilations:
            self.blocks.append(TCNBlock(prev, channels, 3, d, 0.1))
            prev = channels
        self.head = nn.Conv1d(channels, num_classes, 1)

    def forward(self, x):
        for blk in self.blocks:
            x = blk(x)
        return self.head(x)  # (B, num_classes, T)

class MultiTaskDualHeadTCN(nn.Module):
    def __init__(self, in_ch, num_classes=10, channels=32, dilations=[1,2,4,8,16,32,64,128,256,512]):
        super().__init__()
        self.blocks = nn.ModuleList()
        prev = in_ch
        for d in dilations:
            self.blocks.append(TCNBlock(prev, channels, 3, d, 0.1))
            prev = channels
        # Head 1: Binary Detection Head (is_shot vs no_shot)
        self.det_head = nn.Conv1d(channels, 1, 1)
        # Head 2: 10-class Shot Classifier Head
        self.cls_head = nn.Conv1d(channels, num_classes, 1)

    def forward(self, x):
        for blk in self.blocks:
            x = blk(x)
        det_logits = self.det_head(x).squeeze(1)  # (B, T)
        cls_logits = self.cls_head(x)             # (B, C, T)
        return det_logits, cls_logits

def load_session(session_name, feature_cols, downsample_factor=1):
    p = os.path.join(DATASET_DIR, f"{session_name}_unified.parquet")
    df = pd.read_parquet(p)
    if downsample_factor > 1:
        df = df.iloc[::downsample_factor].reset_index(drop=True)

    # Compute derived columns on the fly if needed
    if 'w_gyro_mag' not in df.columns:
        w_gyro_grid = df[['w_gyro_x','w_gyro_y','w_gyro_z']].values.astype(np.float32)
        w_acc_grid  = df[['w_acc_x','w_acc_y','w_acc_z']].values.astype(np.float32)
        p_acc_grid  = df[['p_acc_x','p_acc_y','p_acc_z']].values.astype(np.float32)
        p_gyro_grid = df[['p_gyro_x','p_gyro_y','p_gyro_z']].values.astype(np.float32)

        w_gyro_mag = np.linalg.norm(w_gyro_grid, axis=1).astype(np.float32)
        w_acc_mag  = np.linalg.norm(w_acc_grid, axis=1).astype(np.float32)
        w_jerk_mag = np.concatenate([[0.0], np.abs(np.diff(w_gyro_mag))]).astype(np.float32)
        w_gyro_energy = (w_gyro_grid[:,0]**2 + w_gyro_grid[:,1]**2 + w_gyro_grid[:,2]**2).astype(np.float32)
        p_acc_mag  = np.linalg.norm(p_acc_grid, axis=1).astype(np.float32)
        p_gyro_mag = np.linalg.norm(p_gyro_grid, axis=1).astype(np.float32)

        df['w_gyro_mag'] = w_gyro_mag
        df['w_acc_mag']  = w_acc_mag
        df['w_jerk_mag'] = w_jerk_mag
        df['w_gyro_energy'] = w_gyro_energy
        df['p_acc_mag']  = p_acc_mag
        df['p_gyro_mag'] = p_gyro_mag

    X = df[feature_cols].fillna(0).values.astype(np.float32)
    y = df['label'].map(CLASS_TO_IDX).values.astype(np.int64)
    return X, y, df

class AblationDataset(Dataset):
    def __init__(self, sessions_data, window_len):
        self.window_len = window_len
        self.windows = []
        for s_idx, (X, y, _) in enumerate(sessions_data):
            n = len(X)
            for i in range(0, n - window_len, window_len // 2):
                yw = y[i:i+window_len]
                w = 20.0 if np.any(np.isin(yw, [6, 7, 8])) else (10.0 if np.any(yw >= 2) else 1.0)
                self.windows.append((s_idx, i, w))
        self.weights = np.array([w for _, _, w in self.windows], dtype=np.float32)
        self.weights /= self.weights.sum()
        self.sessions_data = sessions_data

    def __len__(self): return len(self.windows)

    def __getitem__(self, idx):
        s_idx, start, _ = self.windows[idx]
        X, y, _ = self.sessions_data[s_idx]
        xd = torch.from_numpy(X[start:start+self.window_len].T)
        yd = torch.from_numpy(y[start:start+self.window_len])
        return xd, yd

# ---------- Metrics Evaluation ----------
def evaluate_holdout(model, test_data, med, mad, window_len, is_multi_task, feature_cols):
    model.eval()
    X_h, y_h, df_t = test_data
    X_h_norm = (X_h - med) / mad
    X_h_t = torch.from_numpy(X_h_norm.astype(np.float32)).to(DEVICE)
    
    preds_list = []
    with torch.no_grad():
        for i in range(0, len(X_h_t), window_len):
            chunk = X_h_t[i:i+window_len].T.unsqueeze(0)
            if chunk.shape[2] < window_len:
                pad = torch.zeros(1, len(feature_cols), window_len - chunk.shape[2], device=DEVICE)
                chunk = torch.cat([chunk, pad], dim=2)
            if is_multi_task:
                det_l, cls_l = model(chunk)
                preds = cls_l.argmax(1).squeeze(0).cpu().numpy()
            else:
                logits = model(chunk)
                preds = logits.argmax(1).squeeze(0).cpu().numpy()
            preds_list.append(preds[:window_len])
            
    preds_full = np.concatenate(preds_list)[:len(y_h)]
    
    # Contiguous detection matching within +-0.5s
    narr_times_sec = []
    narr_path = os.path.join(BASE_DIR, "live_watch_sessions", HOLDOUT, "narrations_raw.json")
    if os.path.exists(narr_path):
        narr = json.load(open(narr_path))
        for e in narr:
            if e.get('shot_type') and not any(k in e['shot_type'].lower() for k in ['facing up','no shot','leave','evade','block']):
                narr_times_sec.append(float(e['timestamp_seconds']))
                
    grid_dt_s = float(df_t['t_ms'].iloc[1] - df_t['t_ms'].iloc[0]) / 1000.0 if len(df_t) > 1 else 0.002364
    if 't_ms' in df_t.columns and len(df_t) > 1:
        # Check actual step in test_data if downsampled
        grid_dt_s = float(df_t['t_ms'].iloc[1] - df_t['t_ms'].iloc[0]) / 1000.0
        
    pred_is_shot = np.isin(preds_full, list(SHOT_CLASS_INDICES))
    regions = []
    i = 0
    while i < len(pred_is_shot):
        if pred_is_shot[i]:
            j = i
            while j < len(pred_is_shot) and pred_is_shot[j]: j += 1
            mid = (i + j - 1) / 2
            regions.append(mid * grid_dt_s)
            i = j
        else: i += 1
        
    matched_narr = sum(1 for ns in narr_times_sec if any(abs(r - ns) <= 0.5 for r in regions))
    recall = matched_narr / len(narr_times_sec) if narr_times_sec else 0.0
    matched_regions = sum(1 for r in regions if any(abs(r - ns) <= 0.5 for ns in narr_times_sec))
    precision = matched_regions / len(regions) if regions else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
    
    truth_is_shot = np.isin(y_h, list(SHOT_CLASS_INDICES))
    overlap = truth_is_shot & pred_is_shot
    correct = overlap & (preds_full == y_h)
    shot_acc = float(correct.sum() / overlap.sum()) if overlap.sum() > 0 else 0.0
    
    return {
        'det_precision': float(precision),
        'det_recall': float(recall),
        'det_F1': float(f1),
        'shot_type_acc': float(shot_acc)
    }

# ---------- Run Single Ablation Test ----------
def run_ablation_experiment(run_id, use_downsample, use_derived, use_multitask, train_sessions):
    print(f"\n============================================================")
    print(f"  RUN {run_id}: Downsample={use_downsample} | Derived={use_derived} | MultiTask={use_multitask}")
    print(f"============================================================")
    
    feature_cols = DERIVED_FEATURES if use_derived else RAW_FEATURES
    downsample_factor = 2 if use_downsample else 1
    window_len = 600 if use_downsample else 2048
    
    # Load session data
    train_data = [load_session(s, feature_cols, downsample_factor) for s in train_sessions]
    test_data = load_session(HOLDOUT, feature_cols, downsample_factor)
    
    # Stats
    all_X = np.concatenate([X for X,_,_ in train_data], axis=0)
    med = np.median(all_X, axis=0)
    mad = np.median(np.abs(all_X - med), axis=0)
    mad = np.where(mad < 1e-3, 1.0, mad)
    
    for X, _, _ in train_data:
        X[:] = (X - med) / mad
        
    dataset = AblationDataset(train_data, window_len)
    sampler = torch.utils.data.WeightedRandomSampler(dataset.weights, len(dataset.weights), replacement=True)
    loader = DataLoader(dataset, batch_size=32, sampler=sampler, num_workers=0)
    
    # Model & Optim
    in_ch = len(feature_cols)
    if use_multitask:
        model = MultiTaskDualHeadTCN(in_ch, NUM_CLASSES, channels=32).to(DEVICE)
    else:
        model = SingleHeadTCN(in_ch, NUM_CLASSES, channels=32).to(DEVICE)
        
    optim = torch.optim.Adam(model.parameters(), lr=1e-3)
    
    # Class weights
    all_y = np.concatenate([y for _, y, _ in train_data])
    counts = np.bincount(all_y, minlength=NUM_CLASSES)
    weights = np.where(counts == 0, 0.0, 1.0 / np.sqrt(counts + 1e-5))
    weights = weights * (NUM_CLASSES / weights.sum())
    w_t = torch.from_numpy(weights.astype(np.float32)).to(DEVICE)
    
    best_acc = -1.0
    patience = 6
    counter = 0
    best_metrics = None
    
    for epoch in range(1, 25):
        model.train()
        r_loss = 0.0; n_b = 0
        for xb, yb in loader:
            xb = xb.to(DEVICE); yb = yb.to(DEVICE)
            if use_multitask:
                det_l, cls_l = model(xb)
                target_is_shot = (yb >= 2).float()
                loss_det = F.binary_cross_entropy_with_logits(det_l, target_is_shot)
                loss_cls = F.cross_entropy(cls_l, yb, weight=w_t)
                loss = loss_det + 2.0 * loss_cls
            else:
                logits = model(xb)
                loss = F.cross_entropy(logits, yb, weight=w_t)
                
            optim.zero_grad(); loss.backward(); optim.step()
            r_loss += loss.item(); n_b += 1
            
        metrics = evaluate_holdout(model, test_data, med, mad, window_len, use_multitask, feature_cols)
        acc = metrics['shot_type_acc']
        
        if acc > best_acc + 0.001:
            best_acc = acc
            best_metrics = metrics
            counter = 0
            star = " 🌟 BEST"
        else:
            counter += 1
            star = ""
            
        print(f"  Epoch {epoch:02d} | TrainLoss: {r_loss/n_b:.4f} | Recall: {metrics['det_recall']:.3f} | F1: {metrics['det_F1']:.3f} | HoldoutAcc: {acc*100:5.2f}%{star}")
        if counter >= patience:
            print(f"  ⏹️ Early stopping at epoch {epoch}")
            break
            
    return best_metrics

def main():
    print("============================================================")
    print("  Systematic 8-Run Ablation Study Pipeline")
    print(f"  Holdout Session: {HOLDOUT}")
    print("============================================================")
    
    # Discover train sessions
    pattern = os.path.join(DATASET_DIR, "session_2026-*_unified.parquet")
    train_sessions = [os.path.basename(p).replace("_unified.parquet","") for p in glob.glob(pattern) if HOLDOUT not in p and '_aug_' not in p]
    
    experiments = [
        ("Run 0 (Control)",  False, False, False),
        ("Run A (Downsample)", True,  False, False),
        ("Run B (Derived)",    False, True,  False),
        ("Run C (MultiTask)",  False, False, True),
        ("Run A+B (Pair)",    True,  True,  False),
        ("Run A+C (Pair)",    True,  False, True),
        ("Run B+C (Pair)",    False, True,  True),
        ("Run A+B+C (All 3)", True,  True,  True),
    ]
    
    results = {}
    for exp_id, fA, fB, fC in experiments:
        m = run_ablation_experiment(exp_id, fA, fB, fC, train_sessions)
        results[exp_id] = m
        
    # Write Markdown Report
    report = f"""# Systematic Ablation Study Results & Comparative Scorecard

**Holdout Session**: `{HOLDOUT}`  
**Date**: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M")}

---

## 📊 Ablation Experiment Results Table

| Run ID | Downsampling (200Hz) | Derived Data (+Jerk/Mags) | Multi-Task (2-Head) | Detection Recall (±0.5s) | Detection Precision | Detection F1 | Holdout Shot Classification Accuracy |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
"""
    for exp_id, fA, fB, fC in experiments:
        m = results[exp_id]
        fA_str = "YES (200Hz)" if fA else "NO (423Hz)"
        fB_str = "YES (32 Feats)" if fB else "NO (Raw 26)"
        fC_str = "YES (Dual-Head)" if fC else "NO (Single Head)"
        report += f"| **{exp_id}** | {fA_str} | {fB_str} | {fC_str} | **{m['det_recall']*100:.1f}%** | {m['det_precision']*100:.1f}% | {m['det_F1']:.3f} | **{m['shot_type_acc']*100:.2f}%** |\n"

    report += f"""
---

## 🏆 Reference Benchmarks Comparison

| Reference Model / Architecture | Detection Recall | False Alarm Rate | Holdout Shot Classification Accuracy | Notes |
|---|---|---|---|---|
| **Production Random Forest** | 74.6% (±1.5s) | **4.27 FP/min** | **35.87%** | Severe training-set overfitting (>90% -> 35.87%) |
| **Previous TCN Baseline (423Hz)** | **92.1%** (±0.5s) | Continuous Softmax | **52.40%** | Peaked at Epoch 3, overfit past Epoch 3 |
| **Noise-Augmented TCN (423Hz)** | **86.8%** (±0.5s) | Continuous Softmax | **47.34%** | Global noise blurred continuous time steps |
"""
    with open(REPORT_OUT, 'w') as f:
        f.write(report)
        
    print(f"\n✅ Ablation Study Complete! Saved full report to {REPORT_OUT}")

if __name__ == "__main__":
    main()
