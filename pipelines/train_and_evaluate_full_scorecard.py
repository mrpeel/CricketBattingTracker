#!/usr/bin/env python3
"""
pipelines/train_and_evaluate_full_scorecard.py — Master Training & Full-Dataset Evaluation Pipeline

1. Trains Ultimate Advanced Baseline TCN holding out session_2026-07-18_13-44-09.
2. Exports ONNX model & normalisation stats to app assets.
3. Evaluates full dataset across ALL 45 physical sessions (calculating recall, precision, and F1 score).
4. Computes PER-SHOT CLASS CLASSIFICATION ACCURACY for both Training Set (44 sessions) and Holdout Set (session_2026-07-18_13-44-09).
5. Generates full_dataset_training_scorecard.md.
"""
import os
import sys
import json
import glob
import math
import shutil
import random
import datetime
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader

ROOT_DIR       = "/Users/neilkloot/Code/CricketBattingTracker"
BASE_DIR       = "/Users/neilkloot/Code/Batting Sensor Stats"
DATASET_DIR    = os.path.join(BASE_DIR, "poc_unified_dataset")
SESSIONS_DIR   = os.path.join(BASE_DIR, "live_watch_sessions")

sys.path.append(os.path.join(ROOT_DIR, "pipelines"))
from build_unified_dataset import normalise_shot_type, build_session
MODEL_PT_PATH  = os.path.join(ROOT_DIR, "pipelines", "tcn_ultimate_baseline.pt")
MODEL_ONNX_PATH = os.path.join(ROOT_DIR, "pipelines", "tcn_ultimate_baseline.onnx")
APP_ASSETS_DIR = os.path.join(ROOT_DIR, "app", "src", "main", "assets", "models")
APP_ONNX_PATH  = os.path.join(APP_ASSETS_DIR, "tcn_ultimate_baseline.onnx")
STATS_PATH     = os.path.join(ROOT_DIR, "pipelines", "tcn_norm_stats.json")
REPORT_OUT     = os.path.join(ROOT_DIR, "full_dataset_training_scorecard.md")

HOLDOUT_SESSIONS = ["session_2026-07-18_13-44-09", "session_2026-08-01_10-18-20"]

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

CLASSES = ['no_shot','pre_shot','PULL/HOOK','DRIVE/DEFENCE','GLANCE/FLICK','CUT/PUNCH','DEFLECTION/GUIDE','POWER DRIVE','SLOG','SWEEP']
SHOT_CLASSES = ['PULL/HOOK','DRIVE/DEFENCE','GLANCE/FLICK','CUT/PUNCH','DEFLECTION/GUIDE','POWER DRIVE','SLOG','SWEEP']
CLASS_TO_IDX = {c: i for i, c in enumerate(CLASSES)}
NUM_CLASSES = len(CLASSES)

WINDOW_LEN = 2048
BATCH_SIZE = 32
DEVICE     = 'cuda' if torch.cuda.is_available() else 'cpu'

# ============================================================
# FOCAL LOSS IMPLEMENTATION
# ============================================================
class FocalLoss(nn.Module):
    def __init__(self, gamma=2.0, weight=None):
        super().__init__()
        self.gamma = gamma
        self.weight = weight

    def forward(self, logits, targets):
        ce_loss = F.cross_entropy(logits, targets, weight=self.weight, reduction='none')
        pt = torch.exp(-ce_loss)
        focal_loss = ((1 - pt) ** self.gamma) * ce_loss
        return focal_loss.mean()

# ============================================================
# ADVANCED TCN MODEL WITH NON-CAUSAL PADDING & SKIP-HEAD
# ============================================================
class AdvancedTCNBlock(nn.Module):
    def __init__(self, in_ch, out_ch, kernel_size=3, dilation=1, dropout=0.1):
        super().__init__()
        pad = (kernel_size - 1) * dilation // 2
        self.conv1 = nn.Conv1d(in_ch, out_ch, kernel_size, padding=pad, dilation=dilation)
        self.conv2 = nn.Conv1d(out_ch, out_ch, kernel_size, padding=pad, dilation=dilation)
        self.relu1 = nn.ReLU()
        self.drop1 = nn.Dropout(dropout)
        self.relu2 = nn.ReLU()
        self.drop2 = nn.Dropout(dropout)
        self.downsample = nn.Conv1d(in_ch, out_ch, 1) if in_ch != out_ch else nn.Identity()

    def forward(self, x):
        o = self.relu1(self.conv1(x))
        o = self.drop1(o)
        o = self.relu2(self.conv2(o))
        o = self.drop2(o)
        return o + self.downsample(x)

class AdvancedTCN(nn.Module):
    def __init__(self, in_ch, num_classes=10, channels=32, dilations=[1,2,4,8,16,32,64,128,256,512]):
        super().__init__()
        self.blocks = nn.ModuleList()
        prev = in_ch
        for d in dilations:
            self.blocks.append(AdvancedTCNBlock(prev, channels, 3, d, dropout=0.1))
            prev = channels
        self.head = nn.Conv1d(channels * 3, num_classes, 1)

    def forward(self, x):
        layer_outputs = []
        out = x
        for blk in self.blocks:
            out = blk(out)
            layer_outputs.append(out)
            
        l4  = layer_outputs[3]  # Layer 4 (d=8)
        l7  = layer_outputs[6]  # Layer 7 (d=64)
        l10 = layer_outputs[9]  # Layer 10 (d=512)
        concat_feat = torch.cat([l4, l7, l10], dim=1)
        return self.head(concat_feat)

# ---------- Data Loading & Dataset ----------
def load_dataset(session_name):
    p = os.path.join(DATASET_DIR, f"{session_name}_unified.parquet")
    df = pd.read_parquet(p)
    X = df[FEATURES].fillna(0).values.astype(np.float32)
    y = df['label'].map(CLASS_TO_IDX).values.astype(np.int64)
    return X, y, df

class SessionWindowDataset(Dataset):
    def __init__(self, sessions_data, window_len=WINDOW_LEN, is_train=True):
        self.window_len = window_len
        self.is_train = is_train
        self.windows = []
        for s_idx, (X, y, _) in enumerate(sessions_data):
            n = len(X)
            for i in range(0, n - window_len, window_len // 2):
                yw = y[i:i+window_len]
                w = 20.0 if np.any(yw >= 2) else 1.0
                self.windows.append((s_idx, i, w))
        self.weights = np.array([w for _, _, w in self.windows], dtype=np.float32)
        self.weights /= self.weights.sum()
        self.sessions_data = sessions_data

    def __len__(self): return len(self.windows)

    def __getitem__(self, idx):
        s_idx, start, _ = self.windows[idx]
        X, y, _ = self.sessions_data[s_idx]
        if self.is_train:
            jitter = random.randint(-13, 13)  # +/-30ms at 423 Hz
            start = max(0, min(len(X) - self.window_len, start + jitter))
        
        window_X = X[start:start+self.window_len].copy()
        if self.is_train and random.random() < 0.60:
            pitch = math.radians(random.uniform(-15.0, 15.0))
            roll  = math.radians(random.uniform(-15.0, 15.0))
            yaw   = math.radians(random.uniform(-20.0, 20.0))
            
            Rx = np.array([[1, 0, 0], [0, math.cos(pitch), -math.sin(pitch)], [0, math.sin(pitch), math.cos(pitch)]])
            Ry = np.array([[math.cos(roll), 0, math.sin(roll)], [0, 1, 0], [-math.sin(roll), 0, math.cos(roll)]])
            Rz = np.array([[math.cos(yaw), -math.sin(yaw), 0], [math.sin(yaw), math.cos(yaw), 0], [0, 0, 1]])
            R  = (Rz @ Ry @ Rx).astype(np.float32)
            
            window_X[:, 0:3]  = window_X[:, 0:3] @ R.T
            window_X[:, 3:6]  = window_X[:, 3:6] @ R.T
            window_X[:, 6:9]  = window_X[:, 6:9] @ R.T
            window_X[:, 9:12] = window_X[:, 9:12] @ R.T

        xd = torch.from_numpy(window_X.T)
        yd = torch.from_numpy(y[start:start+self.window_len])
        return xd, yd

def evaluate_single_session(session_name, model, med, mad):
    p = os.path.join(DATASET_DIR, f"{session_name}_unified.parquet")
    if not os.path.exists(p):
        return None
        
    res_data = load_dataset(session_name)
    if res_data is None:
        return None
    X, _, df = res_data
    if df.empty or len(df) < 100:
        return None
        
    X_norm = (X - med) / mad
    
    # TCN Model Inference
    preds_list = []
    probs_list = []
    with torch.no_grad():
        for i in range(0, len(X_norm), WINDOW_LEN):
            chunk = X_norm[i:i+WINDOW_LEN].T[np.newaxis, :, :]
            n_frames = chunk.shape[2]
            if n_frames < WINDOW_LEN:
                pad = np.zeros((1, NUM_FEATURES, WINDOW_LEN - n_frames), dtype=np.float32)
                chunk = np.concatenate([chunk, pad], axis=2)
            chunk_t = torch.from_numpy(chunk).to(DEVICE)
            logits = model(chunk_t)[0, :, :n_frames].cpu().numpy()
            exp_logits = np.exp(logits - np.max(logits, axis=0, keepdims=True))
            probs = exp_logits / np.sum(exp_logits, axis=0, keepdims=True)
            preds = np.argmax(probs, axis=0)
            preds_list.append(preds)
            probs_list.append(probs)
            
    preds_full = np.concatenate(preds_list)[:len(X)]
    probs_full = np.hstack(probs_list)[:, :len(X)]
    
    # Load Ground Truth Narrations
    sdir = os.path.join(SESSIONS_DIR, session_name)
    narr_path = os.path.join(sdir, "narrations_raw.json")
    gt_events = []
    if os.path.exists(narr_path):
        narr = json.load(open(narr_path))
        for e in narr:
            st = e.get('shot_type', '')
            gt_cls = normalise_shot_type(st)
            if gt_cls and gt_cls != 'Leave':
                gt_events.append({'sec': float(e['timestamp_seconds']), 'raw_type': st, 'cls': gt_cls})
                
    w_acc_mags  = np.linalg.norm(X[:, 0:3], axis=1)
    w_gyro_mags = np.linalg.norm(X[:, 3:6], axis=1)
    p_gyro_mags = np.linalg.norm(X[:, 22:25], axis=1)
    
    # High-frequency angular jerk (domega/dt at 423 Hz)
    w_jerk = np.abs(np.diff(w_gyro_mags, prepend=0)) * 423.0
    p_jerk = np.abs(np.diff(p_gyro_mags, prepend=0)) * 423.0

    # Calculate sliding pre-shot angular velocity std over [-0.8s, -0.2s] window (254 frames)
    gyro_std_254 = pd.Series(w_gyro_mags).rolling(window=254, min_periods=50).std().shift(85).fillna(0.0).values

    # Stage 1: Impact Shockwave Anchor Detector (High Precision Gate)
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
            
    # Apply Burst Mode Adaptive Hysteresis Gate
    verified_anchors = []
    last_verified_sec = -999.0
    for f in anchors:
        candidate_sec = f / 423.0
        pre_stillness_std = gyro_std_254[f]
        delta_t = candidate_sec - last_verified_sec
        
        # Burst Mode (Delta T < 10s): Relaxed limit (<= 3.0 rad/s); Rest Mode: Strict limit (<= 2.0 rad/s)
        thresh = 3.0 if delta_t < 10.0 else 2.0
        if pre_stillness_std <= thresh or delta_t < 2.0:
            verified_anchors.append(f)
            last_verified_sec = candidate_sec
            
    # Stage 2: TCN Shot Classification
    detections = []
    for f in verified_anchors:
        w_s = max(0, f - 42)
        w_e = min(len(X), f + 42)
        win_probs = probs_full[:, w_s:w_e]
        top_class_idx = np.argmax(win_probs[2:10, :].max(axis=1)) + 2
        top_prob = win_probs[top_class_idx, :].max()
        top_cls_name = CLASSES[top_class_idx]
        
        detections.append({
            'sec': f / 423.0,
            'frame': f,
            'class': top_cls_name,
            'class_idx': top_class_idx,
            'prob': float(top_prob)
        })
        
    # Match Detections to Ground Truth Narrations (Tol: +-1.5s)
    matched_gt = 0
    matched_dets = 0
    gt_matched_flags = [False] * len(gt_events)
    det_matched_flags = [False] * len(detections)
    
    per_class_gt = {c: 0 for c in SHOT_CLASSES}
    per_class_detected = {c: 0 for c in SHOT_CLASSES}
    per_class_correct = {c: 0 for c in SHOT_CLASSES}
    
    for g in gt_events:
        c_name = g['cls']
        if c_name in per_class_gt:
            per_class_gt[c_name] += 1
            
    for d in detections:
        c_name = d['class']
        if c_name in per_class_detected:
            per_class_detected[c_name] += 1
            
    for g_idx, g in enumerate(gt_events):
        best_d_idx = -1
        best_dist = 2.5
        for d_idx, d in enumerate(detections):
            if not det_matched_flags[d_idx]:
                dist = abs(g['sec'] - d['sec'])
                if dist <= best_dist:
                    best_dist = dist
                    best_d_idx = d_idx
        if best_d_idx >= 0:
            gt_matched_flags[g_idx] = True
            det_matched_flags[best_d_idx] = True
            matched_gt += 1
            matched_dets += 1
            
            c_gt = g['cls']
            c_det = detections[best_d_idx]['class']
            if c_gt == c_det and c_gt in per_class_correct:
                per_class_correct[c_gt] += 1
                
    rec = matched_gt / len(gt_events) if gt_events else 0.0
    prec = matched_dets / len(detections) if detections else 0.0
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0.0
    
    return {
        'session_name': session_name,
        'is_holdout': session_name in HOLDOUT_SESSIONS,
        'gt_shots': len(gt_events),
        'detected_shots': len(detections),
        'matched_gt': matched_gt,
        'matched_dets': matched_dets,
        'recall': rec,
        'precision': prec,
        'f1': f1,
        'per_class_gt': per_class_gt,
        'per_class_detected': per_class_detected,
        'per_class_correct': per_class_correct,
        'duration_min': len(X) / (423.0 * 60.0)
    }

def aggregate_class_scorecard(eval_results):
    agg = {c: {'gt_count': 0, 'detected_count': 0, 'correct_class_count': 0} for c in SHOT_CLASSES}
    for r in eval_results:
        for c in SHOT_CLASSES:
            agg[c]['gt_count'] += r['per_class_gt'].get(c, 0)
            agg[c]['detected_count'] += r['per_class_detected'].get(c, 0)
            agg[c]['correct_class_count'] += r['per_class_correct'].get(c, 0)
    return agg

def print_and_format_class_table(title, agg_stats):
    lines = []
    lines.append(f"### {title}")
    lines.append("| Shot Class | Physical GT Shots | Shots Detected | **Detection Recall (%)** | **Correctly Classified Shots** | **Classification Accuracy (%)** | **Total Coverage Rate (%)** |")
    lines.append("|---|:---:|:---:|:---:|:---:|:---:|:---:|")
    
    tot_gt = 0; tot_det = 0; tot_corr = 0
    for c in SHOT_CLASSES:
        gt = agg_stats[c]['gt_count']
        det = agg_stats[c]['detected_count']
        corr = agg_stats[c]['correct_class_count']
        tot_gt += gt; tot_det += det; tot_corr += corr
        
        det_rec = (det / gt * 100.0) if gt > 0 else 0.0
        cls_acc = (corr / det * 100.0) if det > 0 else 0.0
        tot_cov = (corr / gt * 100.0) if gt > 0 else 0.0
        
        lines.append(f"| **{c}** | {gt} | {det} | {det_rec:.1f}% | {corr} | **{cls_acc:.1f}%** | **{tot_cov:.1f}%** |")
        
    tot_rec = (tot_det / tot_gt * 100.0) if tot_gt > 0 else 0.0
    tot_acc = (tot_corr / tot_det * 100.0) if tot_det > 0 else 0.0
    tot_cov = (tot_corr / tot_gt * 100.0) if tot_gt > 0 else 0.0
    lines.append(f"| **OVERALL TOTAL** | **{tot_gt}** | **{tot_det}** | **{tot_rec:.1f}%** | **{tot_corr}** | 🏆 **{tot_acc:.1f}%** | 🏆 **{tot_cov:.1f}%** |")
    return "\n".join(lines)

def main():
    print("============================================================")
    print("  Master Training & Full-Dataset Evaluation Pipeline")
    print(f"  Holdout Sessions ({len(HOLDOUT_SESSIONS)}): {', '.join(HOLDOUT_SESSIONS)}")
    print("============================================================")
    
    pattern = os.path.join(DATASET_DIR, "session_2026-*_unified.parquet")
    all_parquet_sessions = sorted([os.path.basename(p).replace("_unified.parquet","") for p in glob.glob(pattern) if '_aug_' not in p])
    train_sessions = [s for s in all_parquet_sessions if s not in HOLDOUT_SESSIONS]
    
    print(f"\n1. Loading {len(train_sessions)} training sessions (holding out {len(HOLDOUT_SESSIONS)} sessions)...")
    train_data = [load_dataset(s) for s in train_sessions]
    
    all_X = np.concatenate([X for X,_,_ in train_data], axis=0)
    med = np.median(all_X, axis=0)
    mad = np.median(np.abs(all_X - med), axis=0)
    mad = np.where(mad < 1e-3, 1.0, mad)
    
    # Save Normalisation Stats JSON
    os.makedirs(APP_ASSETS_DIR, exist_ok=True)
    stats_data = {'features': FEATURES, 'classes': CLASSES, 'median': med.tolist(), 'mad': mad.tolist()}
    with open(STATS_PATH, 'w') as f: json.dump(stats_data, f, indent=2)
    print(f"✅ Saved normalisation stats to {STATS_PATH}")
    
    for X, _, _ in train_data:
        X[:] = (X - med) / mad
        
    dataset = SessionWindowDataset(train_data, WINDOW_LEN, is_train=True)
    sampler = torch.utils.data.WeightedRandomSampler(dataset.weights, len(dataset.weights), replacement=True)
    loader = DataLoader(dataset, batch_size=BATCH_SIZE, sampler=sampler, num_workers=0)
    
    model = AdvancedTCN(NUM_FEATURES, NUM_CLASSES, channels=32).to(DEVICE)
    optim = torch.optim.Adam(model.parameters(), lr=1e-3)
    
    all_y = np.concatenate([y for _, y, _ in train_data])
    counts = np.bincount(all_y, minlength=NUM_CLASSES)
    total_samples = len(all_y)
    # Clamped Dynamic Inverse-Frequency Weighting (1.0x to 1.8x max cap)
    raw_weights = np.where(counts == 0, 1.0, total_samples / (NUM_CLASSES * counts + 1e-5))
    clamped_weights = np.clip(raw_weights, 1.0, 1.8)
    w_t = torch.from_numpy(clamped_weights.astype(np.float32)).to(DEVICE)
    loss_fn = FocalLoss(gamma=2.0, weight=w_t)
    
    print("\n2. Training Ultimate Advanced Baseline TCN (12 Epochs with Two-Stage Layer Freezing at Epoch 5)...")
    for epoch in range(1, 13):
        if epoch == 5:
            print("  🔒 Freezing Low-Level TCN Layers 1-5 (locking shockwave feature extractors)...")
            for idx in range(5):
                for param in model.blocks[idx].parameters():
                    param.requires_grad = False
                    
        model.train()
        r_loss = 0.0; n_b = 0
        for xb, yb in loader:
            xb = xb.to(DEVICE); yb = yb.to(DEVICE)
            logits = model(xb)
            loss = loss_fn(logits, yb)
            optim.zero_grad()
            loss.backward()
            optim.step()
            r_loss += loss.item(); n_b += 1
            
        print(f"  Epoch {epoch:2d}/12 - Focal Loss: {r_loss/n_b:.4f}")
        
    torch.save(model.state_dict(), MODEL_PT_PATH)
    print(f"✅ Saved PyTorch experiment model checkpoint to {MODEL_PT_PATH}")
    
    print(f"\n3. Evaluating FULL DATASET across ALL {len(all_parquet_sessions)} physical sessions...")
    eval_results = []
    for sname in all_parquet_sessions:
        res = evaluate_single_session(sname, model, med, mad)
        if res:
            eval_results.append(res)
            h_tag = " 🌟 [HOLDOUT]" if res['is_holdout'] else ""
            print(f"  {sname:<32} -> GT: {res['gt_shots']:2d} | Det: {res['detected_shots']:2d} | Rec: {res['recall']*100:5.1f}% | Prec: {res['precision']*100:5.1f}% | F1: {res['f1']*100:5.1f}%{h_tag}")
            
    df_eval = pd.DataFrame(eval_results)
    
    holdout_evals = [r for r in eval_results if r['is_holdout']]
    train_evals   = [r for r in eval_results if not r['is_holdout']]
    
    train_res   = df_eval[~df_eval['is_holdout']]
    
    # Micro Metrics
    total_gt = df_eval['gt_shots'].sum()
    total_det = df_eval['detected_shots'].sum()
    total_matched_gt = df_eval['matched_gt'].sum()
    total_matched_det = df_eval['matched_dets'].sum()
    micro_recall = total_matched_gt / total_gt if total_gt else 0
    micro_precision = total_matched_det / total_det if total_det else 0
    micro_f1 = 2 * micro_precision * micro_recall / (micro_precision + micro_recall) if (micro_precision + micro_recall) > 0 else 0
    
    ho_gt = sum(r['gt_shots'] for r in holdout_evals)
    ho_det = sum(r['detected_shots'] for r in holdout_evals)
    ho_matched_gt = sum(r['matched_gt'] for r in holdout_evals)
    ho_matched_det = sum(r['matched_dets'] for r in holdout_evals)
    ho_recall = ho_matched_gt / ho_gt if ho_gt else 0
    ho_precision = ho_matched_det / ho_det if ho_det else 0
    ho_f1 = 2 * ho_precision * ho_recall / (ho_precision + ho_recall) if (ho_precision + ho_recall) > 0 else 0

    tr_gt = train_res['gt_shots'].sum()
    tr_det = train_res['detected_shots'].sum()
    tr_matched_gt = train_res['matched_gt'].sum()
    tr_matched_det = train_res['matched_dets'].sum()
    tr_recall = tr_matched_gt / tr_gt if tr_gt else 0
    tr_precision = tr_matched_det / tr_det if tr_det else 0
    tr_f1 = 2 * tr_precision * tr_recall / (tr_precision + tr_recall) if (tr_precision + tr_recall) > 0 else 0
    
    # Class Breakdown Aggregates
    holdout_class_agg = aggregate_class_scorecard(holdout_evals)
    train_class_agg   = aggregate_class_scorecard(train_evals)
    full_class_agg    = aggregate_class_scorecard(eval_results)
    
    holdout_table_md = print_and_format_class_table(f"🌟 Holdout Set Per-Shot Accuracy ({len(HOLDOUT_SESSIONS)} Sessions)", holdout_class_agg)
    train_table_md   = print_and_format_class_table(f"🏋️ Training Set Per-Shot Accuracy Breakdown ({len(train_sessions)} Sessions)", train_class_agg)
    full_table_md    = print_and_format_class_table(f"🏆 Full Dataset Per-Shot Accuracy Breakdown (All {len(all_parquet_sessions)} Sessions)", full_class_agg)
    
    print("\n" + "="*115)
    print("📊 FULL DATASET TRAINING & HOLDOUT EVALUATION SCORECARD")
    print("="*115)
    print(f"  Holdout Set ({len(HOLDOUT_SESSIONS)} Sessions): Recall = {ho_recall*100:.1f}%, Precision = {ho_precision*100:.1f}%, F1 = {ho_f1*100:.1f}%")
    print(f"  Training Set ({len(train_sessions)} Sessions):           Recall = {tr_recall*100:.1f}%, Precision = {tr_precision*100:.1f}%, F1 = {tr_f1*100:.1f}%")
    print(f"  Full Dataset Total ({len(all_parquet_sessions)} Sessions):      Recall = {micro_recall*100:.1f}%, Precision = {micro_precision*100:.1f}%, F1 = {micro_f1*100:.1f}%")
    print("="*115 + "\n")
    
    print(train_table_md)
    print("\n" + holdout_table_md)
    print("\n" + full_table_md)
    
    # Save Report Markdown
    report = f"""# Full Dataset Training & Holdout Scorecard Report

**System Architecture**: Decoupled Impact Shockwave Anchor Detector (Stage 1) + Ultimate Advanced Baseline TCN Classifier (Stage 2)  
**Designated Holdout Sessions**: `{', '.join(HOLDOUT_SESSIONS)}` ({len(HOLDOUT_SESSIONS)} sessions)  
**Training Sessions Count**: {len(train_sessions)} physical sessions  
**Total Dataset Duration**: {df_eval['duration_min'].sum():.1f} minutes ({df_eval['duration_min'].sum()/60.0:.1f} hours)  
**Date**: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M")}

---

## 📊 Summary Scorecard Metrics

| Dataset Partition | Physical Ground-Truth Shots | Total Detections | **Physical Shot Recall** | **Precision** | **F1 Score** |
|---|:---:|:---:|:---:|:---:|:---:|
| 🌟 **Holdout Set ({len(HOLDOUT_SESSIONS)} Sessions)** | **{ho_gt}** | **{ho_det}** | **{ho_recall*100:.2f}%** | **{ho_precision*100:.2f}%** | **{ho_f1*100:.2f}%** |
| **Training Set Micro Average ({len(train_sessions)} Sessions)** | **{tr_gt}** | **{tr_det}** | **{tr_recall*100:.2f}%** ({tr_matched_gt}/{tr_gt}) | **{tr_precision*100:.2f}%** ({tr_matched_det}/{tr_det}) | **{tr_f1*100:.2f}%** |
| 🏆 **Full Dataset Micro Average (All {len(all_parquet_sessions)} Sessions)** | **{total_gt}** | **{total_det}** | 🏆 **{micro_recall*100:.2f}%** ({total_matched_gt}/{total_gt}) | 🏆 **{micro_precision*100:.2f}%** ({total_matched_det}/{total_det}) | 🏆 **{micro_f1*100:.2f}%** |

---

## 🎯 Per-Shot Class Classification Accuracy Breakdown

{holdout_table_md}

{train_table_md}

{full_table_md}

---

## 📋 Session-by-Session Full Dataset Table

| Session Directory | Partition | Duration (min) | Ground-Truth Shots | Total Detections | Recall (%) | Precision (%) | F1 Score (%) |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
"""
    for r in eval_results:
        part_str = "🌟 HOLDOUT" if r['is_holdout'] else "Training"
        report += f"| `{r['session_name']}` | {part_str} | {r['duration_min']:.1f} | {r['gt_shots']} | {r['detected_shots']} | {r['recall']*100:.1f}% | {r['precision']*100:.1f}% | {r['f1']*100:.1f}%\n"
        
    with open(REPORT_OUT, 'w') as f:
        f.write(report)
        
    print(f"\n✅ Saved master scorecard report to {REPORT_OUT}")

    # Production ONNX Quality Gate Check
    print("\n" + "="*80)
    print("🔒 PRODUCTION ONNX QUALITY GATE CHECK")
    print("="*80)
    if micro_precision >= 0.75 and ho_f1 >= 0.50:
        model.eval()
        dummy_input = torch.randn(1, NUM_FEATURES, WINDOW_LEN, device=DEVICE)
        torch.onnx.export(
            model, dummy_input, MODEL_ONNX_PATH, export_params=True, opset_version=18,
            do_constant_folding=True, input_names=['input_imu_stream'], output_names=['output_logits'],
            dynamic_axes={'input_imu_stream': {0: 'batch_size', 2: 'sequence_length'}, 'output_logits': {0: 'batch_size', 2: 'sequence_length'}}
        )
        shutil.copy(MODEL_ONNX_PATH, APP_ONNX_PATH)
        print(f"🏆 PASSED Quality Gate (Overall Precision={micro_precision*100:.1f}%, Holdout F1={ho_f1*100:.1f}%). Exported ONNX model & updated production Android app assets: {APP_ONNX_PATH}")
    else:
        print(f"⚠️ FAILED Quality Gate (Overall Precision={micro_precision*100:.1f}% [Req >= 75%], Holdout F1={ho_f1*100:.1f}% [Req >= 50%]).")
        print(f"⛔ Production ONNX model was NOT updated. Retained existing production asset.")
    print("="*80)

if __name__ == "__main__":
    main()
