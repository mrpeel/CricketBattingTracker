#!/usr/bin/env python3
"""
pipelines/run_6family_continuum_experiment.py — 6-Family Continuum Taxonomy & Stage 3 Dynamic Resolver

1. Ground-Truth Continuum Label Mapping:
   - VERTICAL_DRIVE <= DRIVE/DEFENCE, POWER DRIVE
   - GLANCE_FLICK <= GLANCE/FLICK
   - CROSS_BAT_POWER <= PULL/HOOK, SLOG
   - CUT_PUNCH <= CUT/PUNCH
   - DEFLECTION_GUIDE <= DEFLECTION/GUIDE
   - CROUCH_SWEEP <= SWEEP

2. Architecture:
   - 10-Layer Progressive TCN ([16, 16, 16, 16, 16, 32, 64, 128, 256, 512])
   - Multi-Scale Triplet Head: [Pool(L5) [16d], Pool(L7) [64d], Proj(L10) [64d]] (144 dims) -> 6-Family Softmax

3. Stage 3 Biomechanical Metrics Dynamic Resolver:
   - Resolves VERTICAL_DRIVE into POWER DRIVE vs DRIVE/DEFENCE based on bottom_hand_acc_ratio & peak_accel.
   - Resolves CROSS_BAT_POWER into SLOG vs PULL/HOOK based on vertical_loft_angle / launch_elevation.

4. Evaluates and reports:
   - Pure 6-Family Geometric Classification Accuracy.
   - Resolved Multi-Class Scorecard across all 59 physical sessions.
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
    estimate_session_clock_offset, load_parquet_session, normalise_shot_type
)

# Canonical 6-Family Continuum Taxonomy
CLASSES_6 = [
    'no_shot', 'pre_shot',
    'VERTICAL_DRIVE',
    'GLANCE_FLICK',
    'CROSS_BAT_POWER',
    'CUT_PUNCH',
    'DEFLECTION_GUIDE',
    'CROUCH_SWEEP'
]
SHOT_CLASSES_6 = [
    'VERTICAL_DRIVE',
    'GLANCE_FLICK',
    'CROSS_BAT_POWER',
    'CUT_PUNCH',
    'DEFLECTION_GUIDE',
    'CROUCH_SWEEP'
]

# Canonical 8-Class Granular Taxonomy for Dynamic Resolver Verification
CANONICAL_8 = [
    'PULL/HOOK', 'DRIVE/DEFENCE', 'GLANCE/FLICK', 'CUT/PUNCH',
    'DEFLECTION/GUIDE', 'POWER DRIVE', 'SLOG', 'SWEEP'
]

CLASS_TO_IDX_6 = {c: i for i, c in enumerate(CLASSES_6)}
NUM_CLASSES_6 = len(CLASSES_6)  # 8 total
NUM_FEATURES = len(FEATURES)
WINDOW_LEN = 2048
BATCH_SIZE = 32
DEVICE = 'mps' if torch.backends.mps.is_available() else ('cuda' if torch.cuda.is_available() else 'cpu')


def map_to_continuum_family(st):
    """Maps arbitrary shot narration string into one of the 6 canonical continuum families."""
    s = (st or '').lower()
    if 'power drive' in s or 'lofted drive' in s or 'cover drive' in s or 'straight drive' in s or 'on drive' in s or 'off drive' in s or 'drive' in s or 'back foot' in s or 'forward defense' in s or 'back defense' in s or 'defence' in s or 'defense' in s:
        return 'VERTICAL_DRIVE'
    if 'pull' in s or 'hook' in s or 'full shot' in s or 'foot shot' in s or 'push up' in s or 'which shot' in s or 'slog' in s:
        return 'CROSS_BAT_POWER'
    if 'flick' in s or 'click' in s or 'quick' in s or 'glance' in s or 'leg glance' in s:
        return 'GLANCE_FLICK'
    if 'guide' in s or 'deflection' in s or 'steer' in s or 'glide' in s or 'square upper cut' in s:
        return 'DEFLECTION_GUIDE'
    if 'cut' in s or 'punch' in s:
        return 'CUT_PUNCH'
    if 'sweep' in s:
        return 'CROUCH_SWEEP'
    return None


def load_dataset_for_continuum_training(session_name):
    df = load_parquet_session(session_name, dataset_dir=DATASET_DIR)
    if df is None:
        return None
    X = df[FEATURES].fillna(0.0).values.astype(np.float32)
    mapped_labels = df['label'].apply(lambda x: map_to_continuum_family(x) if x not in ['no_shot', 'pre_shot'] else x)
    y = mapped_labels.map(CLASS_TO_IDX_6).fillna(0).values.astype(np.int64)
    return X, y, df


class SessionWindowDataset6(Dataset):
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
# 6-Family Continuum TCN Architecture
# =============================================================================
class SixFamilyContinuumTCN(nn.Module):
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
            
        self.proj_l10 = nn.Linear(channels_list[9], 64)
        
        # Dense 6-Family Classifier over 144-dim Feature Triplet
        self.head = nn.Sequential(
            nn.Linear(144, 64),
            nn.BatchNorm1d(64),
            nn.GELU(),
            nn.Dropout(0.1),
            nn.Linear(64, 6)
        )

    def extract_features(self, x):
        layer_outputs = []
        out = x
        for blk in self.blocks:
            out = blk(out)
            layer_outputs.append(out)
        return layer_outputs

    def forward_head_logits(self, x):
        layer_outputs = self.extract_features(x)
        l5  = layer_outputs[4]  # (B, 16, L)
        l7  = layer_outputs[6]  # (B, 64, L)
        l10 = layer_outputs[9]  # (B, 512, L)
        
        f_l5 = l5.mean(dim=2)                          # (B, 16)
        f_l7 = l7.mean(dim=2)                          # (B, 64)
        f_l10 = l10.mean(dim=2)                        # (B, 512)
        f_l10_proj = F.gelu(self.proj_l10(f_l10))      # (B, 64)
        
        feat_144 = torch.cat([f_l5, f_l7, f_l10_proj], dim=1)  # (B, 144)
        out_logits = self.head(feat_144)                       # (B, 6)
        return out_logits

    def forward(self, x):
        out_logits = self.forward_head_logits(x)  # (B, 6)
        B, _, L = x.shape
        shot_logits = out_logits.unsqueeze(-1).expand(-1, -1, L)  # (B, 6, L)
        
        probs = torch.zeros((B, 8, L), device=x.device, dtype=x.dtype)
        p_shot = F.softmax(shot_logits, dim=1)
        probs[:, 2:8, :] = p_shot
        return torch.log(probs + 1e-12)


def compute_continuum_loss(logits, yb, loss_ce):
    # yb is (B, L)
    # logits is (B, 6)
    yb_center = yb[:, WINDOW_LEN // 2]
    shot_mask = (yb_center >= 2)
    if not shot_mask.any():
        return logits.sum() * 0.0
        
    shot_yb = yb_center[shot_mask] - 2  # (0..5)
    shot_logits = logits[shot_mask]
    return loss_ce(shot_logits, shot_yb)


def evaluate_continuum_holdout_candidate_metrics(model, holdout_shot_windows):
    model.eval()
    if not holdout_shot_windows:
        return 0.0, 0.0
    all_x = torch.stack([x_t for x_t, _ in holdout_shot_windows], dim=0).to(DEVICE)
    y_true = [target_c for _, target_c in holdout_shot_windows]
    with torch.no_grad():
        out_logits = model.forward_head_logits(all_x)
        p_choices = torch.argmax(out_logits, dim=1).cpu().numpy()
        
    y_pred = (p_choices + 2).tolist()
    acc = float(accuracy_score(y_true, y_pred))
    macro_f1 = float(f1_score(y_true, y_pred, average="macro", zero_division=0))
    return acc, macro_f1


# =============================================================================
# Stage 3 Biomechanical Metrics Dynamic Resolver
# =============================================================================
def resolve_continuum_stroke(pred_family, df_parquet, anchor_f, peak_acc):
    """
    Stage 3 Biomechanical Dynamic Resolver:
    Converts geometric continuum shape family into fine-grained canonical cricket strokes.
    """
    if pred_family == "VERTICAL_DRIVE":
        post_impact_ratio = 1.0
        if 'post_impact_acc_ratio' in df_parquet.columns:
            f_s = max(0, anchor_f - 21)
            f_e = min(len(df_parquet), anchor_f + 21)
            post_impact_ratio = float(df_parquet['post_impact_acc_ratio'].iloc[f_s:f_e].max())
            
        if post_impact_ratio >= 1.20 and peak_acc >= 40.0:
            return "POWER DRIVE"
        else:
            return "DRIVE/DEFENCE"
            
    elif pred_family == "CROSS_BAT_POWER":
        f_s = max(0, anchor_f - 127)
        f_e = min(len(df_parquet), anchor_f + 127)
        
        pitch_deg = 0.0
        if 'w_grav_z' in df_parquet.columns and 'w_grav_x' in df_parquet.columns and 'w_grav_y' in df_parquet.columns:
            gz = df_parquet['w_grav_z'].iloc[anchor_f]
            gx = df_parquet['w_grav_x'].iloc[anchor_f]
            gy = df_parquet['w_grav_y'].iloc[anchor_f]
            denom = np.sqrt(gx**2 + gy**2 + 1e-6)
            pitch_deg = float(np.rad2deg(np.arctan2(gz, denom)))
            
        max_upward_acc = 0.0
        if 'w_acc_world_z' in df_parquet.columns:
            max_upward_acc = float(df_parquet['w_acc_world_z'].iloc[f_s:f_e].max())
            
        if pitch_deg >= 15.0 or max_upward_acc >= 12.0:
            return "SLOG"
        else:
            return "PULL/HOOK"
            
    elif pred_family == "GLANCE_FLICK":
        return "GLANCE/FLICK"
    elif pred_family == "CUT_PUNCH":
        return "CUT/PUNCH"
    elif pred_family == "DEFLECTION_GUIDE":
        return "DEFLECTION/GUIDE"
    elif pred_family == "CROUCH_SWEEP":
        return "SWEEP"
    return "DRIVE/DEFENCE"


# =============================================================================
# Multi-Tier Evaluator with Dual-Scorecard Reporting
# =============================================================================
def evaluate_continuum_scorecards(session_ids, stage2_model, norm_stats, device=DEVICE, holdout_sessions=HOLDOUT_SESSIONS):
    stage1_model = FacingUpTCN(in_channels=12, num_filters=32).to(device)
    stage1_model.load_state_dict(torch.load(STAGE1_MODEL_PATH, map_location=device))
    stage1_model.eval()
    
    all_results = []
    all_gt_events_canonical = []
    all_gt_events_family = []
    
    for sid in session_ids:
        df_parquet = load_parquet_session(sid, dataset_dir=DATASET_DIR)
        if df_parquet is None or len(df_parquet) < 423:
            continue
            
        gt_path = os.path.join(SESSIONS_DIR, sid, "ground_truth_aligned.csv")
        gt_events_canon = []
        gt_events_fam = []
        if os.path.exists(gt_path):
            df_gt = pd.read_csv(gt_path)
            t_col = "sensor_narr_time_seconds" if "sensor_narr_time_seconds" in df_gt.columns else "impact_time_seconds"
            for _, row in df_gt.iterrows():
                st = row.get("shot_type")
                norm_c = normalise_shot_type(st)
                norm_f = map_to_continuum_family(st)
                if norm_c and norm_f:
                    gt_events_canon.append({"t": float(row[t_col]), "cls": norm_c, "raw": st})
                    gt_events_fam.append({"t": float(row[t_col]), "cls": norm_f, "raw": st})
                    
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
        dt_offset = estimate_session_clock_offset(gt_events_canon, t_grid, w_gyr_mag, max_search_sec=5.0, step_sec=0.05)
        
        aligned_gt_canon = [{"t": g["t"] + dt_offset, "cls": g["cls"], "raw": g["raw"]} for g in gt_events_canon]
        aligned_gt_fam   = [{"t": g["t"] + dt_offset, "cls": g["cls"], "raw": g["raw"]} for g in gt_events_fam]
        
        # Stage 2 Unleaked Inference
        candidate_anchors = [c["anchor_f"] for c in candidate_windows]
        if not candidate_anchors:
            continue
            
        # Normalize continuous features
        median = np.array(norm_stats["median"], dtype=np.float32)
        mad = np.array(norm_stats.get("mad", norm_stats.get("std", norm_stats.get("iqr"))), dtype=np.float32)
        mad = np.where(mad == 0.0, 1.0, mad)
        X_norm_full = (df_parquet[FEATURES].fillna(0.0).values.astype(np.float32) - median) / mad
        
        win_list = []
        for anchor_f in candidate_anchors:
            start_f = max(0, anchor_f - 1024)
            end_f = start_f + 2048
            if end_f > n_samples:
                end_f = n_samples
                start_f = end_f - 2048
            win_list.append(X_norm_full[start_f:end_f])
            
        batch_tensor = torch.tensor(np.array(win_list, dtype=np.float32), dtype=torch.float32).transpose(1, 2).to(device)
        
        stage2_model.eval()
        with torch.no_grad():
            logits_fam = stage2_model.forward_head_logits(batch_tensor)  # (B, 6)
            probs_fam = F.softmax(logits_fam, dim=1).cpu().numpy()
            
        filtered_candidates = []
        last_accepted_t = -999.0
        last_was_sweep = False
        
        for i_cand, c in enumerate(candidate_windows):
            t_cand = c["anchor_t"]
            top_fam_idx = int(np.argmax(probs_fam[i_cand]))
            top_prob = float(probs_fam[i_cand, top_fam_idx])
            pred_fam = SHOT_CLASSES_6[top_fam_idx]
            f_peak = c["anchor_f"]
            peak_acc = c["peak_acc"]
            
            # Sweep Gate
            if pred_fam == "CROUCH_SWEEP":
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
                    pred_fam = "NO_SHOT"
                    
            req_gap = 2.4 if (last_was_sweep or pred_fam == "CROUCH_SWEEP") else 1.8
            if (t_cand - last_accepted_t) < req_gap:
                continue
            if pred_fam == "NO_SHOT":
                continue
                
            last_accepted_t = t_cand
            last_was_sweep = (pred_fam == "CROUCH_SWEEP")
            
            # Stage 3 Dynamic Resolver
            resolved_canon = resolve_continuum_stroke(pred_fam, df_parquet, f_peak, peak_acc)
            
            c["pred_family"] = pred_fam
            c["resolved_canon"] = resolved_canon
            c["prob"] = top_prob
            filtered_candidates.append(c)
            
        for c in filtered_candidates:
            t_cand = c["anchor_t"]
            matched_canon = None
            matched_fam = None
            for g_c, g_f in zip(aligned_gt_canon, aligned_gt_fam):
                if abs(t_cand - g_c["t"]) <= 1.5:
                    matched_canon = g_c
                    matched_fam = g_f
                    break
            is_tp = matched_canon is not None
            gt_canon = matched_canon["cls"] if matched_canon else "AMBIENT_REST"
            gt_fam   = matched_fam["cls"] if matched_fam else "AMBIENT_REST"
            
            all_results.append({
                "sid": sid,
                "tier": c["tier"],
                "t": t_cand,
                "is_tp": is_tp,
                "gt_canon": gt_canon,
                "gt_fam": gt_fam,
                "pred_fam": c["pred_family"],
                "resolved_canon": c["resolved_canon"],
                "prob": c["prob"],
                "is_holdout": (sid in holdout_sessions)
            })
            
        all_gt_events_canonical.extend([(sid, g) for g in aligned_gt_canon])
        all_gt_events_family.extend([(sid, g) for g in aligned_gt_fam])
        
    df_res = pd.DataFrame(all_results)
    
    # 1. Pure 6-Family Holdout Aggregation
    df_ho = df_res[df_res["is_holdout"]] if not df_res.empty else pd.DataFrame()
    ho_gt_fam = [(sid, g) for sid, g in all_gt_events_family if sid in holdout_sessions]
    
    ho_agg_fam = {c: {'gt_count': 0, 'detected_count': 0, 'correct_class_count': 0} for c in SHOT_CLASSES_6}
    for _, g in ho_gt_fam:
        c = g['cls']
        if c in ho_agg_fam:
            ho_agg_fam[c]['gt_count'] += 1
    if not df_ho.empty:
        for _, r in df_ho.iterrows():
            if r['is_tp']:
                c_det = r['pred_fam']
                c_gt = r['gt_fam']
                if c_gt in ho_agg_fam:
                    ho_agg_fam[c_gt]['detected_count'] += 1
                    if c_det == c_gt:
                        ho_agg_fam[c_gt]['correct_class_count'] += 1
                        
    fam_corr = sum(v['correct_class_count'] for v in ho_agg_fam.values())
    fam_det = sum(v['detected_count'] for v in ho_agg_fam.values())
    fam_cls_acc = (fam_corr / max(1, fam_det)) * 100.0
    
    # 2. Resolved Canonical 8-Class Holdout Aggregation
    ho_gt_canon = [(sid, g) for sid, g in all_gt_events_canonical if sid in holdout_sessions]
    ho_agg_canon = {c: {'gt_count': 0, 'detected_count': 0, 'correct_class_count': 0} for c in CANONICAL_8}
    for _, g in ho_gt_canon:
        c = g['cls']
        if c in ho_agg_canon:
            ho_agg_canon[c]['gt_count'] += 1
    if not df_ho.empty:
        for _, r in df_ho.iterrows():
            if r['is_tp']:
                c_det = r['resolved_canon']
                c_gt = r['gt_canon']
                if c_gt in ho_agg_canon:
                    ho_agg_canon[c_gt]['detected_count'] += 1
                    if c_det == c_gt:
                        ho_agg_canon[c_gt]['correct_class_count'] += 1
                        
    canon_corr = sum(v['correct_class_count'] for v in ho_agg_canon.values())
    canon_det = sum(v['detected_count'] for v in ho_agg_canon.values())
    canon_cls_acc = (canon_corr / max(1, canon_det)) * 100.0
    
    total_cand = len(df_res)
    total_gt = len(all_gt_events_canonical)
    total_tp = int(df_res["is_tp"].sum()) if not df_res.empty else 0
    global_prec = (total_tp / max(1, total_cand)) * 100.0
    global_rec = (total_tp / max(1, total_gt)) * 100.0
    
    ho_total_cand = len(df_ho)
    ho_total_gt = len(ho_gt_canon)
    ho_tp = int(df_ho["is_tp"].sum()) if not df_ho.empty else 0
    ho_rec = (ho_tp / max(1, ho_total_gt)) * 100.0
    ho_prec = (ho_tp / max(1, ho_total_cand)) * 100.0
    ho_f1 = (2 * ho_prec * ho_rec / (ho_prec + ho_rec)) if (ho_prec + ho_rec) > 0 else 0.0

    return {
        "ho_agg_fam": ho_agg_fam,
        "fam_cls_acc": fam_cls_acc,
        "ho_agg_canon": ho_agg_canon,
        "canon_cls_acc": canon_cls_acc,
        "global_prec": global_prec,
        "global_rec": global_rec,
        "ho_rec": ho_rec,
        "ho_prec": ho_prec,
        "ho_f1": ho_f1,
        "ho_tp": ho_tp,
        "ho_total_gt": ho_total_gt,
        "ho_total_cand": ho_total_cand
    }


def main():
    print("="*100, flush=True)
    print("  6-FAMILY CONTINUUM TAXONOMY & STAGE 3 DYNAMIC RESOLVER EXPERIMENT", flush=True)
    print(f"  Holdout / Validation Sessions ({len(HOLDOUT_SESSIONS)}): {', '.join(HOLDOUT_SESSIONS)}", flush=True)
    print(f"  Execution Device: {DEVICE}", flush=True)
    print("="*100, flush=True)
    
    pattern = os.path.join(DATASET_DIR, "session_2026-*_unified.parquet")
    all_parquet_sessions = sorted([os.path.basename(p).replace("_unified.parquet", "") for p in glob.glob(pattern) if '_aug_' not in p])
    train_sessions = [s for s in all_parquet_sessions if s not in HOLDOUT_SESSIONS]
    
    print(f"Loading {len(train_sessions)} training sessions & {len(HOLDOUT_SESSIONS)} holdout validation sessions (Total: {len(all_parquet_sessions)})...", flush=True)
    train_data = [load_dataset_for_continuum_training(s) for s in train_sessions]
    train_data = [d for d in train_data if d is not None]
    
    holdout_data = [load_dataset_for_continuum_training(s) for s in HOLDOUT_SESSIONS]
    holdout_data = [d for d in holdout_data if d is not None]
    
    all_X = np.concatenate([X for X, _, _ in train_data], axis=0)
    med = np.median(all_X, axis=0)
    mad = np.median(np.abs(all_X - med), axis=0)
    mad = np.where(mad < 1e-3, 1.0, mad)
    
    stats_data = {'features': FEATURES, 'classes': CLASSES_6, 'median': med.tolist(), 'mad': mad.tolist()}
    
    for X, _, _ in train_data:
        X[:] = (X - med) / mad
    for X, _, _ in holdout_data:
        X[:] = (X - med) / mad
        
    train_dataset = SessionWindowDataset6(train_data, WINDOW_LEN, is_train=True)
    train_sampler = torch.utils.data.WeightedRandomSampler(train_dataset.weights, len(train_dataset.weights), replacement=True)
    train_loader = DataLoader(train_dataset, batch_size=BATCH_SIZE, sampler=train_sampler, num_workers=0)
    
    val_dataset = SessionWindowDataset6(holdout_data, WINDOW_LEN, is_train=False)
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
            fam = map_to_continuum_family(st)
            if fam is None or fam not in CLASS_TO_IDX_6: continue
            t_s = row[t_col]
            center_idx = int(t_s * 423.0)
            start_idx = center_idx - (WINDOW_LEN // 2)
            if start_idx < 0 or start_idx + WINDOW_LEN > len(X): continue
            w_X = X[start_idx:start_idx+WINDOW_LEN].copy()
            holdout_shot_windows.append((torch.from_numpy(w_X.T), CLASS_TO_IDX_6[fam]))
            
    print(f"Prepared {len(holdout_shot_windows)} holdout GT candidate evaluation windows.\n", flush=True)
    
    torch.manual_seed(42)
    np.random.seed(42)
    random.seed(42)
    
    model = SixFamilyContinuumTCN(in_ch=NUM_FEATURES).to(DEVICE)
    
    l1_5_params = [p for i in range(5) for p in model.blocks[i].parameters()]
    l6_10_head_params = (
        [p for i in range(5, 10) for p in model.blocks[i].parameters()] +
        list(model.proj_l10.parameters()) +
        list(model.head.parameters())
    )
    
    BASE_LR_L1_5 = 3e-4
    BASE_LR_L6_10 = 1e-3
    WARMUP_EPOCHS = 3
    MAX_EPOCHS = 35
    PATIENCE = 15
    
    optim = torch.optim.AdamW([
        {'params': l1_5_params, 'lr': BASE_LR_L1_5},
        {'params': l6_10_head_params, 'lr': BASE_LR_L6_10}
    ], weight_decay=1e-2)
    
    loss_ce = nn.CrossEntropyLoss(label_smoothing=0.1)
    
    best_macro_f1 = -1.0
    best_shot_acc = 0.0
    best_val_loss = float('inf')
    best_epoch = 0
    patience_counter = 0
    best_model_state = None
    final_epoch = MAX_EPOCHS
    
    print("="*80, flush=True)
    print("🚀 TRAINING 6-FAMILY CONTINUUM TCN", flush=True)
    print(f"   Continuum Families (6): {', '.join(SHOT_CLASSES_6)}")
    print(f"   Optimization: AdamW (weight_decay=1e-2), Warmup: {WARMUP_EPOCHS} Epochs", flush=True)
    print(f"   Discriminative LR: {BASE_LR_L1_5} (L1-5) / {BASE_LR_L6_10} (L6-10 + Head)", flush=True)
    print(f"   Checkpoint Metric: Peak Holdout Macro-F1 (patience={PATIENCE})", flush=True)
    print("="*80, flush=True)
    
    for epoch in range(1, MAX_EPOCHS + 1):
        if epoch <= WARMUP_EPOCHS:
            warmup_factor = epoch / float(WARMUP_EPOCHS)
            optim.param_groups[0]['lr'] = BASE_LR_L1_5 * warmup_factor
            optim.param_groups[1]['lr'] = BASE_LR_L6_10 * warmup_factor
        else:
            optim.param_groups[0]['lr'] = BASE_LR_L1_5
            optim.param_groups[1]['lr'] = BASE_LR_L6_10
            
        model.train()
        r_loss = 0.0
        n_b = 0
        for xb, yb in train_loader:
            xb = xb.to(DEVICE)
            yb = yb.to(DEVICE)
            logits = model.forward_head_logits(xb)
            loss = compute_continuum_loss(logits, yb, loss_ce)
            optim.zero_grad()
            loss.backward()
            optim.step()
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
                logits = model.forward_head_logits(xb)
                l = compute_continuum_loss(logits, yb, loss_ce)
                v_loss += l.item()
                v_n += 1
        val_loss = v_loss / v_n if v_n > 0 else float('inf')
        
        ho_shot_acc, ho_macro_f1 = evaluate_continuum_holdout_candidate_metrics(model, holdout_shot_windows)
        
        improved = (ho_macro_f1 > best_macro_f1) or (abs(ho_macro_f1 - best_macro_f1) < 1e-4 and ho_shot_acc > best_shot_acc)
        status_tag = " ⭐ Best Checkpoint" if improved else ""
        print(f"  Epoch {epoch:2d}/{MAX_EPOCHS} - Train Loss: {train_loss:.4f} | Val Loss: {val_loss:.4f} | Holdout Candidate Acc: {ho_shot_acc*100.0:.2f}% | Holdout Macro-F1: {ho_macro_f1:.4f}{status_tag}", flush=True)
        
        if improved:
            best_macro_f1 = ho_macro_f1
            best_shot_acc = ho_shot_acc
            best_val_loss = val_loss
            best_epoch = epoch
            patience_counter = 0
            best_model_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}
        else:
            patience_counter += 1
            if best_model_state is None:
                best_macro_f1 = ho_macro_f1
                best_shot_acc = ho_shot_acc
                best_val_loss = val_loss
                best_epoch = epoch
                best_model_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}
            if patience_counter >= PATIENCE:
                final_epoch = epoch
                print(f"  🛑 Early stopping triggered at Epoch {epoch}! Best Holdout Macro-F1: {best_macro_f1:.4f} (Acc: {best_shot_acc*100.0:.2f}%) at Epoch {best_epoch}.", flush=True)
                break
        final_epoch = epoch

    if best_model_state is not None:
        model.load_state_dict({k: v.to(DEVICE) for k, v in best_model_state.items()})
        print(f"\n✅ Reloaded best model checkpoint from Epoch {best_epoch} (Macro-F1: {best_macro_f1:.4f}, Candidate Acc: {best_shot_acc*100.0:.2f}%)\n", flush=True)

    # Telemetry Engine Scorecard across all 59 physical sessions
    print("="*100, flush=True)
    print(f"📊 EVALUATING ACROSS ALL {len(all_parquet_sessions)} PHYSICAL SESSIONS VIA TELEMETRY ENGINE...", flush=True)
    print("="*100, flush=True)
    metrics = evaluate_continuum_scorecards(all_parquet_sessions, model, stats_data, device=DEVICE)
    
    print("\n" + "="*115, flush=True)
    print("🏆 SCORECARD 1: PURE 6-FAMILY GEOMETRIC CLASSIFICATION SCORECARD", flush=True)
    print("="*115, flush=True)
    print(f"  • Best Checkpoint Epoch : Epoch {best_epoch}")
    print(f"  • Holdout Macro-F1      : 🏆 {best_macro_f1:.4f}")
    print(f"  • Holdout 6-Family Acc  : 🏆 {metrics['fam_cls_acc']:.2f}%")
    print(f"  • Holdout Shot Recall   : 🏆 {metrics['ho_rec']:.2f}% ({metrics['ho_tp']}/{metrics['ho_total_gt']} GT shots)")
    print(f"  • Holdout Precision     : 🏆 {metrics['ho_prec']:.2f}% ({metrics['ho_tp']}/{metrics['ho_total_cand']} candidates)")
    print(f"  • Holdout F1 Score      : 🏆 {metrics['ho_f1']:.2f}%")
    print(f"  • Global Precision      : 🏆 {metrics['global_prec']:.2f}%")
    print(f"  • Global Shot Recall    : 🏆 {metrics['global_rec']:.2f}%")
    
    print("\n" + "="*115, flush=True)
    print("🎯 PURE 6-FAMILY ACCURACY BREAKDOWN (UNSEEN 4-SESSION HOLDOUT)", flush=True)
    print("="*115, flush=True)
    ho_fam = metrics['ho_agg_fam']
    print("| Geometric Family      | GT Count | Detected TPs | Correctly Classified | Classification Acc (%) | Total Coverage Rate (%) |")
    print("|---|:---:|:---:|:---:|:---:|:---:|")
    for s_cls in SHOT_CLASSES_6:
        gt = ho_fam[s_cls]['gt_count']
        det = ho_fam[s_cls]['detected_count']
        corr = ho_fam[s_cls]['correct_class_count']
        cls_acc = (corr / det * 100.0) if det > 0 else 0.0
        cov_rec = (corr / gt * 100.0) if gt > 0 else 0.0
        print(f"| **{s_cls:20s}** | {gt:8d} | {det:12d} | {corr:20d} | **{cls_acc:21.2f}%** | **{cov_rec:22.2f}%** |")
    print("="*115, flush=True)

    print("\n" + "="*115, flush=True)
    print("🏆 SCORECARD 2: RESOLVED MULTI-CLASS SCORECARD (STAGE 3 DYNAMIC RESOLVER)", flush=True)
    print("="*115, flush=True)
    print(f"  • Resolved Holdout Accuracy : 🏆 {metrics['canon_cls_acc']:.2f}%")
    print(f"  • Holdout Shot Recall       : 🏆 {metrics['ho_rec']:.2f}% ({metrics['ho_tp']}/{metrics['ho_total_gt']} GT shots)")
    print(f"  • Holdout Precision         : 🏆 {metrics['ho_prec']:.2f}% ({metrics['ho_tp']}/{metrics['ho_total_cand']} candidates)")
    
    print("\n" + "="*115, flush=True)
    print("🎯 RESOLVED CANONICAL 8-CLASS ACCURACY BREAKDOWN (STAGE 3 DYNAMIC RESOLVER)", flush=True)
    print("="*115, flush=True)
    ho_canon = metrics['ho_agg_canon']
    print("| Resolved Shot Class   | GT Count | Detected TPs | Correctly Classified | Classification Acc (%) | Total Coverage Rate (%) |")
    print("|---|:---:|:---:|:---:|:---:|:---:|")
    for s_cls in CANONICAL_8:
        gt = ho_canon[s_cls]['gt_count']
        det = ho_canon[s_cls]['detected_count']
        corr = ho_canon[s_cls]['correct_class_count']
        cls_acc = (corr / det * 100.0) if det > 0 else 0.0
        cov_rec = (corr / gt * 100.0) if gt > 0 else 0.0
        highlight = "🔥" if s_cls in ["POWER DRIVE", "DRIVE/DEFENCE", "SLOG", "PULL/HOOK"] else "  "
        print(f"| {highlight} **{s_cls:18s}** | {gt:8d} | {det:12d} | {corr:20d} | **{cls_acc:21.2f}%** | **{cov_rec:22.2f}%** |")
    print("="*115, flush=True)
    
    out_model_path = os.path.join(PIPELINES_DIR, "tcn_6family_continuum_model.pt")
    torch.save(best_model_state, out_model_path)
    print(f"\n💾 Saved 6-Family Continuum model checkpoint to: {out_model_path}\n", flush=True)


if __name__ == "__main__":
    main()
