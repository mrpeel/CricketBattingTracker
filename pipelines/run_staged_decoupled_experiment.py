#!/usr/bin/env python3
"""
pipelines/run_staged_decoupled_experiment.py — Staged Decoupled Training with Cosine Annealing (Bat-Plane 3-Family TCN)

Schedule:
  - Phase 1 (Epochs 1–8): Joint Spatial Warmup
    * Full model end-to-end (Backbone Layers 1–10 + Heads)
    * AdamW (weight_decay=1e-2), 3-epoch warmup, discriminative LR (3e-4 L1-5, 1e-3 L6-10+Heads)
    * Standard label-smoothed Cross-Entropy (0.1)
    * Early stopping disabled
  - Phase 2 (Epochs 9–35): Decoupled Upper-Head Optimization
    * Freeze Backbone Layers 1–7 (locking micro wrist snap & downswing plane extractors)
    * Trainable: Backbone Layers 8–10, Layer 10 Linear Projection, Head 1, Head 2A, Head 2B
    * CosineAnnealingLR: lr_max=5e-4 decaying to lr_min=1e-6 over 27 epochs
    * Head 2A Sub-Loss Weighting: weight_2a = [1.0, 1.6, 1.0, 1.0] for [DRIVE/DEFENCE, POWER DRIVE, GLANCE/FLICK, DEFLECTION/GUIDE]
    * Early stopping: patience = 18 consecutive epochs on Holdout Candidate Macro-F1

Evaluates and reports:
  - Complete Multi-Tier Scorecard across all 59 physical sessions and 4 holdout validation sessions.
  - Complete 7-Class Holdout Breakdown table.
"""

import os
import sys
import json
import glob
import math
import random
import datetime
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader
from sklearn.metrics import f1_score, accuracy_score, confusion_matrix

ROOT_DIR = "/Users/neilkloot/Code/CricketBattingTracker"
PIPELINES_DIR = os.path.join(ROOT_DIR, "pipelines")
if PIPELINES_DIR not in sys.path:
    sys.path.append(PIPELINES_DIR)

from telemetry_engine import (
    ROOT_DIR, BASE_DIR, DATASET_DIR, SESSIONS_DIR, STAGE1_MODEL_PATH,
    STATS_PATH, HOLDOUT_SESSIONS, STAGE1_CHANNELS, FEATURES,
    FacingUpTCN, StanceTracker, AdvancedTCNBlock,
    estimate_session_clock_offset, load_parquet_session
)

# Canonical 7-Class Taxonomy
CLASSES_7 = [
    'no_shot', 'pre_shot',
    'PULL/HOOK/SLOG', 'DRIVE/DEFENCE', 'GLANCE/FLICK',
    'CUT/PUNCH', 'DEFLECTION/GUIDE', 'POWER DRIVE', 'SWEEP'
]
SHOT_CLASSES_7 = [
    'PULL/HOOK/SLOG', 'DRIVE/DEFENCE', 'GLANCE/FLICK',
    'CUT/PUNCH', 'DEFLECTION/GUIDE', 'POWER DRIVE', 'SWEEP'
]

CLASS_TO_IDX_7 = {c: i for i, c in enumerate(CLASSES_7)}
NUM_CLASSES_7 = len(CLASSES_7)
NUM_FEATURES = len(FEATURES)
WINDOW_LEN = 2048
BATCH_SIZE = 32
DEVICE = 'mps' if torch.backends.mps.is_available() else ('cuda' if torch.cuda.is_available() else 'cpu')

# Bat Plane Geometry Mappings:
# Family 0 (Vertical-Bat Strokes - 4 Classes): DRIVE/DEFENCE(3), POWER DRIVE(7), GLANCE/FLICK(4), DEFLECTION/GUIDE(6)
# Family 1 (Cross-Bat Horizontal Strokes - 2 Classes): PULL/HOOK/SLOG(2), CUT/PUNCH(5)
# Family 2 (Floor / Crouch - 1 Class): SWEEP(8)
FAM3_FAMILY0_CLASSES_7 = [3, 7, 4, 6]
FAM3_FAMILY1_CLASSES_7 = [2, 5]
FAM3_FAMILY2_CLASSES_7 = [8]

FAM3_LOOKUP_FAMILY_T_7 = torch.tensor([0, 0, 1, 0, 0, 1, 0, 0, 2], dtype=torch.int64, device=DEVICE)
FAM3_LOOKUP_SUB_T_7    = torch.tensor([0, 0, 0, 0, 2, 1, 3, 1, 0], dtype=torch.int64, device=DEVICE)

# Targeted Intra-Head Sub-Loss Calibration for Head 2A in Phase 2
WEIGHT_2A_PHASE2 = torch.tensor([1.0, 1.6, 1.0, 1.0], dtype=torch.float32, device=DEVICE)


def normalise_shot_type_7(st):
    """Maps arbitrary shot narration string into one of the 7 canonical classes."""
    s = (st or '').lower()
    if 'power drive' in s or 'lofted drive' in s:
        return 'POWER DRIVE'
    if 'pull' in s or 'hook' in s or 'full shot' in s or 'foot shot' in s or 'push up' in s or 'which shot' in s or 'slog' in s:
        return 'PULL/HOOK/SLOG'
    if 'flick' in s or 'click' in s or 'quick' in s or 'glance' in s or 'leg glance' in s:
        return 'GLANCE/FLICK'
    if 'guide' in s or 'deflection' in s or 'steer' in s or 'glide' in s or 'square upper cut' in s:
        return 'DEFLECTION/GUIDE'
    if 'cover drive' in s or 'straight drive' in s or 'on drive' in s or 'off drive' in s or 'drive' in s or 'back foot' in s or 'forward defense' in s or 'back defense' in s or 'defence' in s or 'defense' in s:
        return 'DRIVE/DEFENCE'
    if 'cut' in s or 'punch' in s:
        return 'CUT/PUNCH'
    if 'sweep' in s:
        return 'SWEEP'
    return None


def load_dataset_for_training_7class(session_name):
    df = load_parquet_session(session_name, dataset_dir=DATASET_DIR)
    if df is None:
        return None
    X = df[FEATURES].fillna(0.0).values.astype(np.float32)
    mapped_labels = df['label'].apply(lambda x: normalise_shot_type_7(x) if x not in ['no_shot', 'pre_shot'] else x)
    y = mapped_labels.map(CLASS_TO_IDX_7).fillna(0).values.astype(np.int64)
    return X, y, df


class SessionWindowDataset7(Dataset):
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

    def __len__(self):
        return len(self.windows)

    def __getitem__(self, idx):
        s_idx, start, _ = self.windows[idx]
        X, y, _ = self.sessions_data[s_idx]
        if self.is_train:
            jitter = random.randint(-13, 13)
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


# =============================================================================
# Bat Plane Geometry 3-Family Multi-Head TCN Architecture
# =============================================================================
class BatPlaneGeometryThreeFamilyTCN(nn.Module):
    def __init__(
        self,
        in_ch=NUM_FEATURES,
        channels_list=[16, 16, 16, 16, 16, 32, 64, 128, 256, 512],
        dilations=[1, 2, 4, 8, 16, 32, 64, 128, 256, 512]
    ):
        super().__init__()
        self.blocks = nn.ModuleList()
        prev = in_ch
        for ch, d in zip(channels_list, dilations):
            self.blocks.append(AdvancedTCNBlock(prev, ch, kernel_size=3, dilation=d, dropout=0.1))
            prev = ch
            
        concat_dim = channels_list[3] + channels_list[6] + channels_list[9]  # 16 + 64 + 512 = 592
        self.head_family = nn.Conv1d(concat_dim, 3, 1)  # Head 1: Macro Family Gate (3-Class Softmax)
        
        self.proj_l10 = nn.Linear(channels_list[9], 64)
        
        # Head 2A: Vertical-Bat Sub-Classifier (4 Classes: DRIVE/DEFENCE, POWER DRIVE, GLANCE/FLICK, DEFLECTION/GUIDE)
        # Using 144-dim Multi-Scale Feature Triplet [Pool(L5) [16d], Pool(L7) [64d], Proj(L10) [64d]]
        self.head_sub0 = nn.Sequential(
            nn.Linear(144, 64),
            nn.BatchNorm1d(64),
            nn.GELU(),
            nn.Dropout(0.1),
            nn.Linear(64, 4)
        )
        
        # Head 2B: Cross-Bat Sub-Classifier (2 Classes: PULL/HOOK/SLOG, CUT/PUNCH)
        # Using 144-dim Multi-Scale Feature Triplet [Pool(L5) [16d], Pool(L7) [64d], Proj(L10) [64d]]
        self.head_sub1 = nn.Sequential(
            nn.Linear(144, 64),
            nn.BatchNorm1d(64),
            nn.GELU(),
            nn.Dropout(0.1),
            nn.Linear(64, 2)
        )
        # Head 2C: Identity / Passthrough to SWEEP

    def extract_features(self, x):
        layer_outputs = []
        out = x
        for blk in self.blocks:
            out = blk(out)
            layer_outputs.append(out)
        return layer_outputs

    def forward_heads(self, x):
        layer_outputs = self.extract_features(x)
        l4  = layer_outputs[3]  # (B, 16, L)
        l5  = layer_outputs[4]  # (B, 16, L)
        l7  = layer_outputs[6]  # (B, 64, L)
        l10 = layer_outputs[9]  # (B, 512, L)
        
        B, _, L = x.shape
        
        concat_feat = torch.cat([l4, l7, l10], dim=1)  # (B, 592, L)
        logits_family = self.head_family(concat_feat)  # (B, 3, L)
        
        f_l5 = l5.mean(dim=2)                          # (B, 16)
        f_l7 = l7.mean(dim=2)                          # (B, 64)
        f_l10 = l10.mean(dim=2)                        # (B, 512)
        f_l10_proj = F.gelu(self.proj_l10(f_l10))      # (B, 64)
        
        # 144-dim Multi-Scale Triplet Feature
        feat_triplet = torch.cat([f_l5, f_l7, f_l10_proj], dim=1)  # (B, 144)
        
        # Head 2A: Vertical-Bat (144 dims)
        out_sub0 = self.head_sub0(feat_triplet)                     # (B, 4)
        logits_sub0 = out_sub0.unsqueeze(-1).expand(-1, -1, L)       # (B, 4, L)
        
        # Head 2B: Cross-Bat (144 dims)
        out_sub1 = self.head_sub1(feat_triplet)                     # (B, 2)
        logits_sub1 = out_sub1.unsqueeze(-1).expand(-1, -1, L)       # (B, 2, L)
        
        return logits_family, logits_sub0, logits_sub1

    def forward(self, x):
        logits_family, logits_sub0, logits_sub1 = self.forward_heads(x)
        p_fam = F.softmax(logits_family, dim=1)  # (B, 3, L)
        p_sub0 = F.softmax(logits_sub0, dim=1)   # (B, 4, L)
        p_sub1 = F.softmax(logits_sub1, dim=1)   # (B, 2, L)
        
        B, _, L = logits_family.shape
        probs = torch.zeros((B, 9, L), device=x.device, dtype=x.dtype)
        probs[:, 0, :] = 0.0  # no_shot
        probs[:, 1, :] = 0.0  # pre_shot
        
        # Family 0 (Vertical-Bat Strokes)
        probs[:, 3, :] = p_fam[:, 0, :] * p_sub0[:, 0, :]  # DRIVE/DEFENCE (3)
        probs[:, 7, :] = p_fam[:, 0, :] * p_sub0[:, 1, :]  # POWER DRIVE (7)
        probs[:, 4, :] = p_fam[:, 0, :] * p_sub0[:, 2, :]  # GLANCE/FLICK (4)
        probs[:, 6, :] = p_fam[:, 0, :] * p_sub0[:, 3, :]  # DEFLECTION/GUIDE (6)
        
        # Family 1 (Cross-Bat Horizontal Strokes)
        probs[:, 2, :] = p_fam[:, 1, :] * p_sub1[:, 0, :]  # PULL/HOOK/SLOG (2)
        probs[:, 5, :] = p_fam[:, 1, :] * p_sub1[:, 1, :]  # CUT/PUNCH (5)
        
        # Family 2 (Floor / Crouch Strokes)
        probs[:, 8, :] = p_fam[:, 2, :]                    # SWEEP (8)
        
        return torch.log(probs + 1e-12)


def compute_bat_plane_loss(logits_tuple, yb, loss_ce_standard, loss_ce_sub0):
    logits_fam, logits_sub0, logits_sub1 = logits_tuple
    B, _, L = logits_fam.shape
    logits_fam_flat = logits_fam.transpose(1, 2).reshape(-1, 3)
    logits_sub0_flat = logits_sub0.transpose(1, 2).reshape(-1, 4)
    logits_sub1_flat = logits_sub1.transpose(1, 2).reshape(-1, 2)
    yb_flat = yb.reshape(-1)
    
    shot_mask = (yb_flat >= 2)
    if not shot_mask.any():
        return (logits_fam.sum() + logits_sub0.sum() + logits_sub1.sum()) * 0.0
        
    shot_yb = yb_flat[shot_mask]
    shot_logits_fam = logits_fam_flat[shot_mask]
    shot_logits_sub0 = logits_sub0_flat[shot_mask]
    shot_logits_sub1 = logits_sub1_flat[shot_mask]
    
    target_fam = FAM3_LOOKUP_FAMILY_T_7[shot_yb]
    target_sub = FAM3_LOOKUP_SUB_T_7[shot_yb]
    
    l_family = loss_ce_standard(shot_logits_fam, target_fam)
    
    fam0_mask = (target_fam == 0)
    l_sub0 = loss_ce_sub0(shot_logits_sub0[fam0_mask], target_sub[fam0_mask]) if fam0_mask.any() else torch.tensor(0.0, device=yb.device)
    
    fam1_mask = (target_fam == 1)
    l_sub1 = loss_ce_standard(shot_logits_sub1[fam1_mask], target_sub[fam1_mask]) if fam1_mask.any() else torch.tensor(0.0, device=yb.device)
    
    return l_family + l_sub0 + l_sub1


def evaluate_bat_plane_holdout_candidate_metrics(model, holdout_shot_windows):
    model.eval()
    if not holdout_shot_windows:
        return 0.0, 0.0
    all_x = torch.stack([x_t for x_t, _ in holdout_shot_windows], dim=0).to(DEVICE)
    y_true = [target_c for _, target_c in holdout_shot_windows]
    with torch.no_grad():
        logits_fam, logits_sub0, logits_sub1 = model.forward_heads(all_x)
        c_idx = WINDOW_LEN // 2
        p_fam = F.softmax(logits_fam[:, :, c_idx], dim=1).cpu().numpy()
        p_sub0 = F.softmax(logits_sub0[:, :, c_idx], dim=1).cpu().numpy()
        p_sub1 = F.softmax(logits_sub1[:, :, c_idx], dim=1).cpu().numpy()
        
    fam_choices = np.argmax(p_fam, axis=1)
    sub0_choices = np.argmax(p_sub0, axis=1)
    sub1_choices = np.argmax(p_sub1, axis=1)
    
    y_pred = []
    for i, fam_c in enumerate(fam_choices):
        if fam_c == 0:
            pred_c = FAM3_FAMILY0_CLASSES_7[sub0_choices[i]]
        elif fam_c == 1:
            pred_c = FAM3_FAMILY1_CLASSES_7[sub1_choices[i]]
        else:
            pred_c = 8  # SWEEP
        y_pred.append(pred_c)
        
    acc = float(accuracy_score(y_true, y_pred))
    macro_f1 = float(f1_score(y_true, y_pred, average="macro", zero_division=0))
    return acc, macro_f1


# =============================================================================
# 7-Class Telemetry Engine Evaluator
# =============================================================================
def predict_candidate_batch_unleaked_7class(df_parquet, candidate_anchors, stage2_model, norm_stats, device):
    if df_parquet is None or len(df_parquet) < 2048 or not candidate_anchors:
        return [("DRIVE/DEFENCE", 0.50) for _ in candidate_anchors]
        
    n_frames = len(df_parquet)
    X_full = df_parquet[FEATURES].fillna(0.0).values.astype(np.float32)
    
    median = np.array(norm_stats["median"], dtype=np.float32)
    mad = np.array(norm_stats.get("mad", norm_stats.get("std", norm_stats.get("iqr"))), dtype=np.float32)
    mad = np.where(mad == 0.0, 1.0, mad)
    
    X_norm_full = (X_full - median) / mad
    
    win_list = []
    c_offsets = []
    for anchor_f in candidate_anchors:
        start_f = max(0, anchor_f - 1024)
        end_f = start_f + 2048
        if end_f > n_frames:
            end_f = n_frames
            start_f = end_f - 2048
        win = X_norm_full[start_f:end_f]
        win_list.append(win)
        c_offsets.append(anchor_f - start_f)
        
    batch_np = np.array(win_list, dtype=np.float32)
    batch_tensor = torch.tensor(batch_np, dtype=torch.float32).transpose(1, 2).to(device)
    
    stage2_model.eval()
    with torch.no_grad():
        logits = stage2_model(batch_tensor)
        probs_batch = F.softmax(logits, dim=1).cpu().numpy()
        
    preds = []
    for b in range(len(candidate_anchors)):
        c_off = c_offsets[b]
        w_s = max(0, c_off - 42)
        w_e = min(2048, c_off + 42)
        
        probs = probs_batch[b]
        win_probs = probs[:, w_s:w_e]
        
        if win_probs.shape[1] == 0:
            preds.append(("DRIVE/DEFENCE", 0.50))
            continue
            
        shot_class_probs = win_probs[2:9, :].max(axis=1)  # 7 classes
        top_class_rel_idx = np.argmax(shot_class_probs)
        top_class_idx = top_class_rel_idx + 2
        top_prob = float(shot_class_probs[top_class_rel_idx])
        pred_cls = CLASSES_7[top_class_idx]
        preds.append((pred_cls, top_prob))
        
    return preds


def evaluate_7class_scorecard(session_ids, stage2_model, norm_stats, device=DEVICE, holdout_sessions=HOLDOUT_SESSIONS):
    stage1_model = FacingUpTCN(in_channels=12, num_filters=32).to(device)
    stage1_model.load_state_dict(torch.load(STAGE1_MODEL_PATH, map_location=device))
    stage1_model.eval()
    
    all_results = []
    all_gt_events = []
    
    for sid in session_ids:
        df_parquet = load_parquet_session(sid, dataset_dir=DATASET_DIR)
        if df_parquet is None or len(df_parquet) < 423:
            continue
            
        gt_path = os.path.join(SESSIONS_DIR, sid, "ground_truth_aligned.csv")
        gt_events = []
        if os.path.exists(gt_path):
            df_gt = pd.read_csv(gt_path)
            t_col = "sensor_narr_time_seconds" if "sensor_narr_time_seconds" in df_gt.columns else "impact_time_seconds"
            for _, row in df_gt.iterrows():
                st = row.get("shot_type")
                norm = normalise_shot_type_7(st)
                if norm:
                    gt_events.append({
                        "t": float(row[t_col]),
                        "cls": norm,
                        "raw": st
                    })
                    
        # Stage 1 Stance
        channels_12 = df_parquet[STAGE1_CHANNELS].fillna(0.0).values.astype(np.float32)
        n_samples = len(channels_12)
        w_len = 423
        stride = 42
        n_windows = max(1, (n_samples - w_len) // stride + 1)
        
        sliding_windows = np.zeros((n_windows, 12, w_len), dtype=np.float32)
        window_times = np.zeros(n_windows, dtype=np.float32)
        for i in range(n_windows):
            start = i * stride
            sliding_windows[i] = channels_12[start : start + w_len].T
            window_times[i] = (start + w_len) / 423.0
            
        batch_size = 512
        s1_probs = []
        with torch.no_grad():
            for b in range(0, n_windows, batch_size):
                b_win = sliding_windows[b:b+batch_size]
                b_tensor = torch.tensor(b_win, dtype=torch.float32).to(device)
                b_logits = stage1_model(b_tensor).flatten()
                b_prob = torch.sigmoid(b_logits).cpu().numpy()
                if b_prob.ndim == 0:
                    s1_probs.append(float(b_prob))
                else:
                    s1_probs.extend(b_prob.tolist())
            
        tracker = StanceTracker(high_thresh=0.70, low_thresh=0.40, motion_surge_w=1.8, sustain_ms=300)
        stance_exits = []
        w_gyr_mag = np.linalg.norm(df_parquet[['w_gyro_x', 'w_gyro_y', 'w_gyro_z']].values, axis=1)
        
        for i in range(n_windows):
            t_w = window_times[i]
            p_w = float(s1_probs[i])
            idx_frame = min(int(t_w * 423.0), n_samples - 1)
            w_mag = float(w_gyr_mag[idx_frame])
            state, exited = tracker.process_step(p_w, w_mag, dt_ms=100)
            if exited:
                stance_exits.append(t_w)
                
        # Candidate Peaks
        w_acc_mag = np.linalg.norm(df_parquet[['w_acc_x', 'w_acc_y', 'w_acc_z']].values, axis=1)
        candidate_windows = []
        for t_exit in stance_exits:
            f_exit = int(t_exit * 423.0)
            f_window_end = min(n_samples, f_exit + int(3.5 * 423.0))
            if f_window_end <= f_exit:
                continue
                
            gyr_slice = w_gyr_mag[f_exit:f_window_end]
            if len(gyr_slice) == 0:
                continue
                
            local_peak_idx = int(np.argmax(gyr_slice))
            peak_f = f_exit + local_peak_idx
            peak_gyr = float(w_gyr_mag[peak_f])
            peak_acc = float(w_acc_mag[peak_f])
            
            if peak_gyr < 1.0:
                continue
                
            bs_start_f = max(0, peak_f - 127)
            dt_s = 1.0 / 423.0
            delta_theta = float(np.sum(w_gyr_mag[bs_start_f:peak_f]) * dt_s)
            if delta_theta < 0.14:
                continue
                
            tier = "TIER_1_HIGH" if (peak_acc >= 25.0 or peak_gyr >= 5.0) else "TIER_3_SOFT_TOUCH"
            candidate_windows.append({
                "anchor_t": peak_f / 423.0,
                "anchor_f": peak_f,
                "peak_acc": peak_acc,
                "peak_gyr": peak_gyr,
                "tier": tier
            })
            
        t_grid = df_parquet['t_ms'].values / 1000.0 if 't_ms' in df_parquet.columns else np.arange(len(df_parquet)) / 423.0
        dt_offset = estimate_session_clock_offset(gt_events, t_grid, w_gyr_mag, max_search_sec=5.0, step_sec=0.05)
        
        aligned_gt = [{"t": g["t"] + dt_offset, "cls": g["cls"], "raw": g["raw"]} for g in gt_events]
        
        # Stage 2 Pass
        candidate_anchors = [c["anchor_f"] for c in candidate_windows]
        preds = predict_candidate_batch_unleaked_7class(df_parquet, candidate_anchors, stage2_model, norm_stats, device)
        
        # Filters
        filtered_candidates = []
        last_accepted_t = -999.0
        last_was_sweep = False
        
        for i_cand, c in enumerate(candidate_windows):
            t_cand = c["anchor_t"]
            pred_cls, top_prob = preds[i_cand]
            f_peak = c["anchor_f"]
            
            if pred_cls == "SWEEP":
                f_start = max(0, f_peak - 211)
                gx_win = channels_12[f_start : f_peak + 1, 6] if channels_12.shape[1] > 6 else np.zeros(f_peak + 1 - f_start)
                gy_win = channels_12[f_start : f_peak + 1, 7] if channels_12.shape[1] > 7 else np.zeros(f_peak + 1 - f_start)
                gz_win = channels_12[f_start : f_peak + 1, 8] if channels_12.shape[1] > 8 else np.zeros(f_peak + 1 - f_start)
                delta_gz = float(np.ptp(gz_win))
                denom = np.sqrt(gx_win**2 + gy_win**2 + 1e-6)
                pitch_deg = np.rad2deg(np.arctan2(gz_win, denom))
                delta_pitch = float(np.ptp(pitch_deg))
                w_roll_win = channels_12[f_start : f_peak + 1, 3] if channels_12.shape[1] > 3 else np.zeros(f_peak + 1 - f_start)
                omega_roll = float(np.max(np.abs(w_roll_win)))

                is_path1 = (delta_pitch >= 10.0 or delta_gz >= 1.2) and (top_prob >= 0.30)
                is_path2 = (omega_roll >= 1.6) and (top_prob >= 0.35)
                if not (is_path1 or is_path2):
                    pred_cls = "NO_SHOT"
                    
            req_gap = 2.4 if (last_was_sweep or pred_cls == "SWEEP") else 1.8
            if (t_cand - last_accepted_t) < req_gap:
                continue
            if pred_cls == "NO_SHOT":
                continue
                
            last_accepted_t = t_cand
            last_was_sweep = (pred_cls == "SWEEP")
            c["pred_cls"] = pred_cls
            c["prob"] = top_prob
            filtered_candidates.append(c)
            
        for c in filtered_candidates:
            t_cand = c["anchor_t"]
            pred_cls = c["pred_cls"]
            top_prob = c["prob"]
            matched_gt = None
            for g in aligned_gt:
                if abs(t_cand - g["t"]) <= 1.5:
                    matched_gt = g
                    break
            is_tp = matched_gt is not None
            gt_cls = matched_gt["cls"] if matched_gt else "AMBIENT_REST"
            all_results.append({
                "sid": sid,
                "tier": c["tier"],
                "t": t_cand,
                "is_tp": is_tp,
                "gt_cls": gt_cls,
                "pred_cls": pred_cls,
                "prob": top_prob,
                "is_holdout": (sid in holdout_sessions)
            })
        all_gt_events.extend([(sid, g) for g in aligned_gt])
        
    df_res = pd.DataFrame(all_results)
    
    total_cand = len(df_res)
    total_gt = len(all_gt_events)
    total_tp = int(df_res["is_tp"].sum()) if not df_res.empty else 0
    global_prec = (total_tp / max(1, total_cand)) * 100.0
    global_rec = (total_tp / max(1, total_gt)) * 100.0
    global_f1 = (2 * global_prec * global_rec / (global_prec + global_rec)) if (global_prec + global_rec) > 0 else 0.0
    
    df_ho_all = df_res[df_res["is_holdout"]] if not df_res.empty else pd.DataFrame()
    ho_gt_events = [(sid, g) for sid, g in all_gt_events if sid in holdout_sessions]
    ho_total_gt = len(ho_gt_events)
    ho_total_cand = len(df_ho_all)
    ho_tp = int(df_ho_all["is_tp"].sum()) if not df_ho_all.empty else 0
    ho_rec = (ho_tp / max(1, ho_total_gt)) * 100.0
    ho_prec = (ho_tp / max(1, ho_total_cand)) * 100.0
    ho_f1 = (2 * ho_prec * ho_rec / (ho_prec + ho_rec)) if (ho_prec + ho_rec) > 0 else 0.0
    
    def build_agg_7(df_subset, gt_subset):
        agg = {c: {'gt_count': 0, 'detected_count': 0, 'correct_class_count': 0} for c in SHOT_CLASSES_7}
        for _, g in gt_subset:
            c = g['cls']
            if c in agg:
                agg[c]['gt_count'] += 1
        if not df_subset.empty:
            for _, r in df_subset.iterrows():
                if r['is_tp']:
                    c_det = r['pred_cls']
                    c_gt = r['gt_cls']
                    if c_gt in agg:
                        agg[c_gt]['detected_count'] += 1
                        if c_det == c_gt:
                            agg[c_gt]['correct_class_count'] += 1
        return agg

    ho_agg = build_agg_7(df_ho_all, ho_gt_events)
    ho_corr_tot = sum(v['correct_class_count'] for v in ho_agg.values())
    ho_det_tot = sum(v['detected_count'] for v in ho_agg.values())
    ho_cls_acc = (ho_corr_tot / max(1, ho_det_tot)) * 100.0
    
    return {
        "global_rec": global_rec,
        "global_prec": global_prec,
        "global_f1": global_f1,
        "ho_rec": ho_rec,
        "ho_prec": ho_prec,
        "ho_f1": ho_f1,
        "ho_cls_acc": ho_cls_acc,
        "ho_tp": ho_tp,
        "ho_total_gt": ho_total_gt,
        "ho_total_cand": ho_total_cand,
        "total_tp": total_tp,
        "total_gt": total_gt,
        "total_cand": total_cand,
        "holdout_agg": ho_agg
    }


def main():
    print("="*100, flush=True)
    print("  STAGED DECOUPLED TRAINING EXPERIMENT (BAT-PLANE 3-FAMILY TCN + COSINE ANNEALING)", flush=True)
    print(f"  Holdout / Validation Sessions ({len(HOLDOUT_SESSIONS)}): {', '.join(HOLDOUT_SESSIONS)}", flush=True)
    print(f"  Execution Device: {DEVICE}", flush=True)
    print("="*100, flush=True)
    
    pattern = os.path.join(DATASET_DIR, "session_2026-*_unified.parquet")
    all_parquet_sessions = sorted([os.path.basename(p).replace("_unified.parquet", "") for p in glob.glob(pattern) if '_aug_' not in p])
    train_sessions = [s for s in all_parquet_sessions if s not in HOLDOUT_SESSIONS]
    
    print(f"Loading {len(train_sessions)} training sessions & {len(HOLDOUT_SESSIONS)} holdout validation sessions (Total: {len(all_parquet_sessions)})...", flush=True)
    train_data = [load_dataset_for_training_7class(s) for s in train_sessions]
    train_data = [d for d in train_data if d is not None]
    
    holdout_data = [load_dataset_for_training_7class(s) for s in HOLDOUT_SESSIONS]
    holdout_data = [d for d in holdout_data if d is not None]
    
    all_X = np.concatenate([X for X, _, _ in train_data], axis=0)
    med = np.median(all_X, axis=0)
    mad = np.median(np.abs(all_X - med), axis=0)
    mad = np.where(mad < 1e-3, 1.0, mad)
    
    stats_data = {'features': FEATURES, 'classes': CLASSES_7, 'median': med.tolist(), 'mad': mad.tolist()}
    
    for X, _, _ in train_data:
        X[:] = (X - med) / mad
    for X, _, _ in holdout_data:
        X[:] = (X - med) / mad
        
    train_dataset = SessionWindowDataset7(train_data, WINDOW_LEN, is_train=True)
    train_sampler = torch.utils.data.WeightedRandomSampler(train_dataset.weights, len(train_dataset.weights), replacement=True)
    train_loader = DataLoader(train_dataset, batch_size=BATCH_SIZE, sampler=train_sampler, num_workers=0)
    
    val_dataset = SessionWindowDataset7(holdout_data, WINDOW_LEN, is_train=False)
    val_loader = DataLoader(val_dataset, batch_size=BATCH_SIZE, shuffle=False, num_workers=0)
    
    # Extract Holdout Evaluation Windows
    holdout_shot_windows = []
    for s_idx, (X, y, df) in enumerate(holdout_data):
        s_name = HOLDOUT_SESSIONS[s_idx]
        gt_path = os.path.join(SESSIONS_DIR, s_name, "ground_truth_aligned.csv")
        if not os.path.exists(gt_path): continue
        df_gt = pd.read_csv(gt_path)
        t_col = "sensor_narr_time_seconds" if "sensor_narr_time_seconds" in df_gt.columns else "impact_time_seconds"
        for _, row in df_gt.iterrows():
            st = row.get("shot_type")
            norm = normalise_shot_type_7(st)
            if norm is None or norm not in CLASS_TO_IDX_7: continue
            t_s = row[t_col]
            center_idx = int(t_s * 423.0)
            start_idx = center_idx - (WINDOW_LEN // 2)
            if start_idx < 0 or start_idx + WINDOW_LEN > len(X): continue
            w_X = X[start_idx:start_idx+WINDOW_LEN].copy()
            holdout_shot_windows.append((torch.from_numpy(w_X.T), CLASS_TO_IDX_7[norm]))
            
    print(f"Prepared {len(holdout_shot_windows)} holdout GT candidate evaluation windows.\n", flush=True)
    
    torch.manual_seed(42)
    np.random.seed(42)
    random.seed(42)
    
    model = BatPlaneGeometryThreeFamilyTCN(in_ch=NUM_FEATURES).to(DEVICE)
    
    loss_ce_standard = nn.CrossEntropyLoss(label_smoothing=0.1)
    loss_ce_sub0_p2 = nn.CrossEntropyLoss(weight=WEIGHT_2A_PHASE2, label_smoothing=0.1)
    
    PHASE1_EPOCHS = 8
    TOTAL_EPOCHS = 35
    PHASE2_PATIENCE = 18
    
    # Phase 1 Setup
    l1_5_params = [p for i in range(5) for p in model.blocks[i].parameters()]
    l6_10_head_params = (
        [p for i in range(5, 10) for p in model.blocks[i].parameters()] +
        list(model.head_family.parameters()) +
        list(model.proj_l10.parameters()) +
        list(model.head_sub0.parameters()) +
        list(model.head_sub1.parameters())
    )
    
    BASE_LR_L1_5 = 3e-4
    BASE_LR_L6_10 = 1e-3
    WARMUP_EPOCHS = 3
    
    optim1 = torch.optim.AdamW([
        {'params': l1_5_params, 'lr': BASE_LR_L1_5},
        {'params': l6_10_head_params, 'lr': BASE_LR_L6_10}
    ], weight_decay=1e-2)
    
    best_macro_f1 = -1.0
    best_shot_acc = 0.0
    best_val_loss = float('inf')
    best_epoch = 0
    patience_counter = 0
    best_model_state = None
    
    print("="*85, flush=True)
    print("🚀 PHASE 1: JOINT SPATIAL WARMUP (EPOCHS 1 TO 8)", flush=True)
    print(f"   Backbone Layers 1–10 + All Heads Active | LR: {BASE_LR_L1_5} (L1-5) / {BASE_LR_L6_10} (L6-10+Heads)")
    print(f"   Loss: Standard Label Smoothing (0.1) | Early Stopping: Disabled during warmup")
    print("="*85, flush=True)
    
    # Phase 1 Loop
    for epoch in range(1, PHASE1_EPOCHS + 1):
        if epoch <= WARMUP_EPOCHS:
            warmup_factor = epoch / float(WARMUP_EPOCHS)
            optim1.param_groups[0]['lr'] = BASE_LR_L1_5 * warmup_factor
            optim1.param_groups[1]['lr'] = BASE_LR_L6_10 * warmup_factor
        else:
            optim1.param_groups[0]['lr'] = BASE_LR_L1_5
            optim1.param_groups[1]['lr'] = BASE_LR_L6_10
            
        model.train()
        r_loss = 0.0
        n_b = 0
        for xb, yb in train_loader:
            xb = xb.to(DEVICE)
            yb = yb.to(DEVICE)
            logits_tuple = model.forward_heads(xb)
            loss = compute_bat_plane_loss(logits_tuple, yb, loss_ce_standard, loss_ce_standard)
            optim1.zero_grad()
            loss.backward()
            optim1.step()
            r_loss += loss.item()
            n_b += 1
            
        train_loss = r_loss / n_b
        
        model.eval()
        v_loss = 0.0
        v_n = 0
        with torch.no_grad():
            for xb, yb in val_loader:
                xb = xb.to(DEVICE)
                yb = yb.to(DEVICE)
                logits_tuple = model.forward_heads(xb)
                l = compute_bat_plane_loss(logits_tuple, yb, loss_ce_standard, loss_ce_standard)
                v_loss += l.item()
                v_n += 1
        val_loss = v_loss / v_n if v_n > 0 else float('inf')
        
        ho_shot_acc, ho_macro_f1 = evaluate_bat_plane_holdout_candidate_metrics(model, holdout_shot_windows)
        
        improved = (ho_macro_f1 > best_macro_f1) or (abs(ho_macro_f1 - best_macro_f1) < 1e-4 and ho_shot_acc > best_shot_acc)
        status_tag = " ⭐ Best Checkpoint" if improved else ""
        print(f"  [Phase 1] Epoch {epoch:2d}/{PHASE1_EPOCHS} - Train Loss: {train_loss:.4f} | Val Loss: {val_loss:.4f} | Holdout Acc: {ho_shot_acc*100.0:.2f}% | Holdout Macro-F1: {ho_macro_f1:.4f}{status_tag}", flush=True)
        
        if improved:
            best_macro_f1 = ho_macro_f1
            best_shot_acc = ho_shot_acc
            best_val_loss = val_loss
            best_epoch = epoch
            best_model_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}
            
    # Phase 2 Transition: Freeze Layers 1–7
    if best_model_state is not None:
        model.load_state_dict({k: v.to(DEVICE) for k, v in best_model_state.items()})
        print(f"\n🔄 Restored optimal Phase 1 checkpoint from Epoch {best_epoch} (Holdout Macro-F1: {best_macro_f1:.4f}, Acc: {best_shot_acc*100.0:.2f}%) for Phase 2 initialization.", flush=True)

    print("\n" + "="*85, flush=True)
    print("🔒 FREEZING BACKBONE LAYERS 1 TO 7 (LOCKED TEMPORAL KERNELS)", flush=True)
    print("🚀 PHASE 2: DECOUPLED UPPER-HEAD OPTIMIZATION (EPOCHS 9 TO 35)", flush=True)
    print(f"   Trainable: Layers 8–10, Layer 10 Proj, Head 1, Head 2A, Head 2B")
    print(f"   CosineAnnealingLR: lr_max=5e-4 decaying to 1e-6 (T_max={TOTAL_EPOCHS - PHASE1_EPOCHS})")
    print(f"   Head 2A Sub-Loss Weight: {WEIGHT_2A_PHASE2.cpu().tolist()} | Patience: {PHASE2_PATIENCE}")
    print("="*85, flush=True)
    
    # Freeze layers 1 to 7 (blocks 0 to 6)
    for i in range(7):
        for p in model.blocks[i].parameters():
            p.requires_grad = False
            
    phase2_trainable_params = (
        [p for i in range(7, 10) for p in model.blocks[i].parameters() if p.requires_grad] +
        [p for p in model.proj_l10.parameters() if p.requires_grad] +
        [p for p in model.head_family.parameters() if p.requires_grad] +
        [p for p in model.head_sub0.parameters() if p.requires_grad] +
        [p for p in model.head_sub1.parameters() if p.requires_grad]
    )
    
    LR_PHASE2_MAX = 5e-4
    LR_PHASE2_MIN = 1e-6
    T_MAX_PHASE2 = TOTAL_EPOCHS - PHASE1_EPOCHS
    
    optim2 = torch.optim.AdamW(phase2_trainable_params, lr=LR_PHASE2_MAX, weight_decay=1e-2)
    scheduler2 = torch.optim.lr_scheduler.CosineAnnealingLR(optim2, T_max=T_MAX_PHASE2, eta_min=LR_PHASE2_MIN)
    
    patience_counter = 0
    final_epoch = TOTAL_EPOCHS
    
    for epoch in range(PHASE1_EPOCHS + 1, TOTAL_EPOCHS + 1):
        current_lr = optim2.param_groups[0]['lr']
        model.train()
        r_loss = 0.0
        n_b = 0
        for xb, yb in train_loader:
            xb = xb.to(DEVICE)
            yb = yb.to(DEVICE)
            logits_tuple = model.forward_heads(xb)
            loss = compute_bat_plane_loss(logits_tuple, yb, loss_ce_standard, loss_ce_sub0_p2)
            optim2.zero_grad()
            loss.backward()
            optim2.step()
            r_loss += loss.item()
            n_b += 1
            
        scheduler2.step()
        train_loss = r_loss / n_b
        
        model.eval()
        v_loss = 0.0
        v_n = 0
        with torch.no_grad():
            for xb, yb in val_loader:
                xb = xb.to(DEVICE)
                yb = yb.to(DEVICE)
                logits_tuple = model.forward_heads(xb)
                l = compute_bat_plane_loss(logits_tuple, yb, loss_ce_standard, loss_ce_sub0_p2)
                v_loss += l.item()
                v_n += 1
        val_loss = v_loss / v_n if v_n > 0 else float('inf')
        
        ho_shot_acc, ho_macro_f1 = evaluate_bat_plane_holdout_candidate_metrics(model, holdout_shot_windows)
        
        improved = (ho_macro_f1 > best_macro_f1) or (abs(ho_macro_f1 - best_macro_f1) < 1e-4 and ho_shot_acc > best_shot_acc)
        status_tag = " ⭐ Best Checkpoint" if improved else ""
        print(f"  [Phase 2] Epoch {epoch:2d}/{TOTAL_EPOCHS} (LR: {current_lr:.6f}) - Train Loss: {train_loss:.4f} | Val Loss: {val_loss:.4f} | Holdout Acc: {ho_shot_acc*100.0:.2f}% | Holdout Macro-F1: {ho_macro_f1:.4f}{status_tag}", flush=True)
        
        if improved:
            best_macro_f1 = ho_macro_f1
            best_shot_acc = ho_shot_acc
            best_val_loss = val_loss
            best_epoch = epoch
            patience_counter = 0
            best_model_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}
        else:
            patience_counter += 1
            if patience_counter >= PHASE2_PATIENCE:
                final_epoch = epoch
                print(f"  🛑 Early stopping triggered at Epoch {epoch}! Best Holdout Macro-F1: {best_macro_f1:.4f} (Acc: {best_shot_acc*100.0:.2f}%) at Epoch {best_epoch}.", flush=True)
                break
        final_epoch = epoch

    if best_model_state is not None:
        model.load_state_dict({k: v.to(DEVICE) for k, v in best_model_state.items()})
        print(f"\n✅ Reloaded best model checkpoint from Epoch {best_epoch} (Macro-F1: {best_macro_f1:.4f}, Candidate Acc: {best_shot_acc*100.0:.2f}%)\n", flush=True)

    # Telemetry Engine Scorecard across all 59 physical sessions
    print("="*100, flush=True)
    print(f"📊 EVALUATING ACROSS ALL {len(all_parquet_sessions)} PHYSICAL SESSIONS VIA TELEMETRY ENGINE (7-CLASS STAGED DECOUPLED)...", flush=True)
    print("="*100, flush=True)
    metrics = evaluate_7class_scorecard(all_parquet_sessions, model, stats_data, device=DEVICE)
    
    print("\n" + "="*115, flush=True)
    print("🏆 FINAL STAGED DECOUPLED 7-CLASS BAT PLANE MULTI-TIER SCORECARD", flush=True)
    print("="*115, flush=True)
    print(f"  • Best Checkpoint Epoch : Epoch {best_epoch}")
    print(f"  • Holdout Macro-F1      : 🏆 {best_macro_f1:.4f}")
    print(f"  • Holdout Class Acc     : 🏆 {metrics['ho_cls_acc']:.2f}%")
    print(f"  • Holdout Shot Recall   : 🏆 {metrics['ho_rec']:.2f}% ({metrics['ho_tp']}/{metrics['ho_total_gt']} GT shots)")
    print(f"  • Holdout Precision     : 🏆 {metrics['ho_prec']:.2f}% ({metrics['ho_tp']}/{metrics['ho_total_cand']} candidates)")
    print(f"  • Holdout F1 Score      : 🏆 {metrics['ho_f1']:.2f}%")
    print(f"  • Global Precision      : 🏆 {metrics['global_prec']:.2f}% ({metrics['total_tp']}/{metrics['total_cand']} total candidates)")
    print(f"  • Global Shot Recall    : 🏆 {metrics['global_rec']:.2f}% ({metrics['total_tp']}/{metrics['total_gt']} total GT shots)")
    
    print("\n" + "="*115, flush=True)
    print("🎯 HOLDOUT 7-CLASS ACCURACY BREAKDOWN (STAGED DECOUPLED TRAINING)", flush=True)
    print("="*115, flush=True)
    ho_agg = metrics['holdout_agg']
    print("| Shot Class            | GT Count | Detected TPs | Correctly Classified | Classification Acc (%) | Total Coverage Rate (%) |")
    print("|---|:---:|:---:|:---:|:---:|:---:|")
    for s_cls in SHOT_CLASSES_7:
        gt = ho_agg[s_cls]['gt_count']
        det = ho_agg[s_cls]['detected_count']
        corr = ho_agg[s_cls]['correct_class_count']
        cls_acc = (corr / det * 100.0) if det > 0 else 0.0
        cov_rec = (corr / gt * 100.0) if gt > 0 else 0.0
        highlight = "🔥" if s_cls in ["POWER DRIVE", "PULL/HOOK/SLOG", "CUT/PUNCH"] else "  "
        print(f"| {highlight} **{s_cls:18s}** | {gt:8d} | {det:12d} | {corr:20d} | **{cls_acc:21.2f}%** | **{cov_rec:22.2f}%** |")
    print("="*115, flush=True)
    
    out_model_path = os.path.join(PIPELINES_DIR, "tcn_7class_staged_decoupled_model.pt")
    torch.save(best_model_state, out_model_path)
    print(f"\n💾 Saved Staged Decoupled 7-class model checkpoint to: {out_model_path}\n", flush=True)


if __name__ == "__main__":
    main()
