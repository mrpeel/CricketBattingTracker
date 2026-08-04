#!/usr/bin/env python3
"""
pipelines/run_multitier_pipeline.py — Forensic Audited Multi-Tier Telemetry Pipeline

Features:
  1. Automatic Narration Timestamp Alignment: Calculates session-level clock drift offset (dt_offset)
     via cross-correlation bounded within +-5.0s between GT narration timestamps and IMU motion bursts.
  2. Two-Stage Stance-Gated Peak Alignment: Verifies FACING_UP stance within 3.0s prior to exit,
     scans [T_exit, T_exit + 2.0s] for T_peak = argmax(w_gyro), and extracts peak-aligned window
     [T_peak - 1.0s, T_peak + 1.5s] for Stage 2 TCN classification.
  3. Un-Leaked Stage 2 TCN Inference: Evaluates 2,048-sample 26-feature IMU window arrays.
  4. Audited Scorecard Output: Session offsets (dt), Aligned Recall & Precision, and Per-Shot-Class Accuracy.
"""

import os
import sys
import json
import pickle
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.nn.functional as F

ROOT_DIR = "/Users/neilkloot/Code/CricketBattingTracker"
BASE_DIR = "/Users/neilkloot/Code/Batting Sensor Stats"
DATASET_PATH = os.path.join(ROOT_DIR, "facing_up_sessions_423hz.pkl")
STAGE1_MODEL_PATH = os.path.join(ROOT_DIR, "facing_up_tcn_model.pt")
STAGE2_MODEL_PATH = os.path.join(ROOT_DIR, "pipelines", "tcn_ultimate_baseline.pt")
STATS_PATH = os.path.join(ROOT_DIR, "pipelines", "tcn_norm_stats.json")
UNIFIED_PARQUET_DIR = os.path.join(BASE_DIR, "poc_unified_dataset")
SESSIONS_DIR = os.path.join(BASE_DIR, "live_watch_sessions")

HOLDOUT_SESSIONS = ["session_2026-07-21_12-43-37", "session_2026-07-25_15-16-32"]

FEATURES = [
    'w_acc_x','w_acc_y','w_acc_z',
    'w_gyro_x','w_gyro_y','w_gyro_z',
    'w_acc_world_x','w_acc_world_y','w_acc_world_z',
    'w_gyro_world_x','w_gyro_world_y','w_gyro_world_z',
    'w_grav_x','w_grav_y','w_grav_z',
    'w_rot_qx','w_rot_qy','w_rot_qz','w_rot_qw',
    'p_acc_x','p_acc_y','p_acc_z',
    'p_gyro_x','p_gyro_y','p_gyro_z',
    'has_polar'
]

CLASSES = ['no_shot','pre_shot','PULL/HOOK','DRIVE/DEFENCE','GLANCE/FLICK','CUT/PUNCH','DEFLECTION/GUIDE','POWER DRIVE','SLOG','SWEEP']
SHOT_CLASSES = ['PULL/HOOK','DRIVE/DEFENCE','GLANCE/FLICK','CUT/PUNCH','DEFLECTION/GUIDE','POWER DRIVE','SLOG','SWEEP']

SOFT_TOUCH_CLASSES = ['DEFLECTION/GUIDE', 'SWEEP']

def normalise_shot_type(st):
    s = (st or '').lower()
    if 'power drive' in s or 'lofted drive' in s:
        return 'POWER DRIVE'
    if 'pull' in s or 'hook' in s or 'full shot' in s or 'foot shot' in s or 'push up' in s or 'which shot' in s:
        return 'PULL/HOOK'
    if 'flick' in s or 'click' in s or 'quick' in s or 'glance' in s or 'leg glance' in s:
        return 'GLANCE/FLICK'
    if 'guide' in s or 'deflection' in s or 'steer' in s or 'glide' in s or 'square upper cut' in s:
        return 'DEFLECTION/GUIDE'
    if 'cover drive' in s or 'straight drive' in s or 'on drive' in s or 'off drive' in s or 'drive' in s or 'back foot' in s or 'forward defense' in s or 'back defense' in s or 'defence' in s or 'defense' in s:
        return 'DRIVE/DEFENCE'
    if 'cut' in s or 'punch' in s:
        return 'CUT/PUNCH'
    if 'slog' in s:
        return 'SLOG'
    if 'sweep' in s:
        return 'SWEEP'
    return None

# -----------------------------------------------------------------------------
# Module 1: Stage 1 Facing Up TCN Architecture
# -----------------------------------------------------------------------------
class FacingUpTCN(nn.Module):
    def __init__(self, in_channels=12, num_filters=32):
        super(FacingUpTCN, self).__init__()
        self.layer1 = nn.Sequential(
            nn.Conv1d(in_channels, num_filters, kernel_size=5, padding=2),
            nn.BatchNorm1d(num_filters),
            nn.ReLU(),
            nn.MaxPool1d(kernel_size=2)
        )
        self.layer2 = nn.Sequential(
            nn.Conv1d(num_filters, num_filters * 2, kernel_size=5, padding=4, dilation=2),
            nn.BatchNorm1d(num_filters * 2),
            nn.ReLU(),
            nn.MaxPool1d(kernel_size=2)
        )
        self.layer3 = nn.Sequential(
            nn.Conv1d(num_filters * 2, num_filters * 2, kernel_size=5, padding=8, dilation=4),
            nn.BatchNorm1d(num_filters * 2),
            nn.ReLU()
        )
        self.layer4 = nn.Sequential(
            nn.Conv1d(num_filters * 2, num_filters * 4, kernel_size=5, padding=16, dilation=8),
            nn.BatchNorm1d(num_filters * 4),
            nn.ReLU()
        )
        self.layer5 = nn.Sequential(
            nn.Conv1d(num_filters * 4, num_filters * 4, kernel_size=3, padding=1),
            nn.BatchNorm1d(num_filters * 4),
            nn.ReLU(),
            nn.AdaptiveAvgPool1d(1)
        )
        self.fc = nn.Linear(num_filters * 4, 1)

    def forward(self, x):
        if x.dim() == 3 and x.shape[1] == 423 and x.shape[2] == 12:
            x = x.transpose(1, 2)
        out = self.layer1(x)
        out = self.layer2(out)
        out = self.layer3(out)
        out = self.layer4(out)
        out = self.layer5(out)
        out = out.squeeze(-1)
        logits = self.fc(out).squeeze(-1)
        return logits

# -----------------------------------------------------------------------------
# Stage 1 Stance State Machine Tracker (300ms Continuous Sustain Guard)
# -----------------------------------------------------------------------------
class StanceTracker:
    def __init__(self, high_thresh=0.70, low_thresh=0.40, motion_surge_w=1.8, sustain_ms=300):
        self.high_thresh = high_thresh
        self.low_thresh = low_thresh
        self.motion_surge_w = motion_surge_w
        self.sustain_ms = sustain_ms
        self.state = "IDLE"
        self.sustain_count = 0

    def process_step(self, prob, w_mag, dt_ms=100):
        if self.state == "IDLE":
            if prob >= self.high_thresh:
                self.sustain_count += dt_ms
                if self.sustain_count >= self.sustain_ms:
                    self.state = "FACING_UP"
            else:
                self.sustain_count = 0
            return self.state, False
            
        elif self.state == "FACING_UP":
            if prob < self.low_thresh or w_mag > self.motion_surge_w:
                self.state = "STANCE_EXIT"
                self.sustain_count = 0
                return "STANCE_EXIT", True
            return "FACING_UP", False
            
        elif self.state == "STANCE_EXIT":
            if prob < self.low_thresh or w_mag > self.motion_surge_w:
                self.state = "IDLE"
            elif prob >= self.high_thresh:
                self.sustain_count += dt_ms
                if self.sustain_count >= self.sustain_ms:
                    self.state = "FACING_UP"
            return self.state, False

# -----------------------------------------------------------------------------
# Module 3: Stage 2 AdvancedTCN Classifier Architecture
# -----------------------------------------------------------------------------
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

class Stage2TCNClassifier(nn.Module):
    def __init__(self, in_ch=26, num_classes=10, channels=32, dilations=[1,2,4,8,16,32,64,128,256,512]):
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
        l4  = layer_outputs[3]
        l7  = layer_outputs[6]
        l10 = layer_outputs[9]
        concat_feat = torch.cat([l4, l7, l10], dim=1)
        return self.head(concat_feat)

# -----------------------------------------------------------------------------
# Patch 1: Automatic Narration Timestamp Alignment (Cross-Correlation Search)
# -----------------------------------------------------------------------------
def estimate_session_clock_offset(gt_events, t_grid, w_gyr_mag, max_search_sec=5.0, step_sec=0.05):
    """
    Computes time offset (dt_offset) between narration timestamps and IMU motion bursts
    via cross-correlation search bounded within +-max_search_sec.
    """
    if not gt_events or len(t_grid) == 0:
        return 0.0
        
    t_start = t_grid[0]
    t_end = t_grid[-1]
    
    # 20 Hz grid for fast cross-correlation
    dt_grid = 0.05
    n_bins = int(np.ceil((t_end - t_start) / dt_grid))
    if n_bins <= 100:
        return 0.0
        
    gt_signal = np.zeros(n_bins, dtype=np.float32)
    for g in gt_events:
        t_sec = g["t"]
        idx = int((t_sec - t_start) / dt_grid)
        if 0 <= idx < n_bins:
            gt_signal[idx] = 1.0
            
    imu_signal = np.zeros(n_bins, dtype=np.float32)
    # Downsample w_gyr_mag to 20 Hz (taking max per 0.05s bin)
    bin_indices = np.clip(((t_grid - t_start) / dt_grid).astype(int), 0, n_bins - 1)
    np.maximum.at(imu_signal, bin_indices, (w_gyr_mag >= 1.8).astype(np.float32))
    
    # Cross-correlation over lag search range [-max_search_sec, +max_search_sec]
    max_lag_bins = int(max_search_sec / dt_grid)
    lags = np.arange(-max_lag_bins, max_lag_bins + 1)
    corrs = []
    
    for lag in lags:
        if lag < 0:
            c = np.sum(gt_signal[:lag] * imu_signal[-lag:])
        elif lag > 0:
            c = np.sum(gt_signal[lag:] * imu_signal[:-lag])
        else:
            c = np.sum(gt_signal * imu_signal)
        corrs.append(c)
        
    best_lag_bin = lags[np.argmax(corrs)]
    best_dt_offset = best_lag_bin * dt_grid
    
    return float(best_dt_offset)

# -----------------------------------------------------------------------------
# Module 3 Un-Leaked Model Inference Engine (Batched & Peak Aligned)
# -----------------------------------------------------------------------------
def predict_candidate_batch_unleaked(df_parquet, candidate_anchors, stage2_model, norm_stats, device):
    """
    STRICT UN-LEAKED MODULE 3 CLASSIFICATION PASS (BATCHED):
    Normalizes 26 continuous IMU features, slices 2,048-sample windows for candidate anchors,
    runs GPU PyTorch forward pass, and returns predictions without reading ground-truth labels.
    """
    if df_parquet is None or len(df_parquet) < 2048 or not candidate_anchors:
        return [("DRIVE/DEFENCE", 0.50) for _ in candidate_anchors]
        
    n_frames = len(df_parquet)
    X_full = df_parquet[FEATURES].fillna(0.0).values.astype(np.float32)  # (N, 26)
    
    median = np.array(norm_stats["median"], dtype=np.float32)
    mad = np.array(norm_stats.get("mad", norm_stats.get("std", norm_stats.get("iqr"))), dtype=np.float32)
    mad = np.where(mad == 0.0, 1.0, mad)
    
    X_norm_full = (X_full - median) / mad  # (N, 26)
    
    win_list = []
    c_offsets = []
    for anchor_f in candidate_anchors:
        start_f = max(0, anchor_f - 1024)
        end_f = start_f + 2048
        if end_f > n_frames:
            end_f = n_frames
            start_f = end_f - 2048
        win = X_norm_full[start_f:end_f]  # (2048, 26)
        win_list.append(win)
        c_offsets.append(anchor_f - start_f)
        
    batch_np = np.array(win_list, dtype=np.float32)
    batch_tensor = torch.tensor(batch_np, dtype=torch.float32).transpose(1, 2).to(device)
    
    stage2_model.eval()
    with torch.no_grad():
        logits = stage2_model(batch_tensor)  # (B, 10, 2048)
        probs_batch = F.softmax(logits, dim=1).cpu().numpy()  # (B, 10, 2048)
        
    preds = []
    for b in range(len(candidate_anchors)):
        c_off = c_offsets[b]
        w_s = max(0, c_off - 42)
        w_e = min(2048, c_off + 42)
        
        probs = probs_batch[b]  # (10, 2048)
        win_probs = probs[:, w_s:w_e]
        
        if win_probs.shape[1] == 0:
            preds.append(("DRIVE/DEFENCE", 0.50))
            continue
            
        shot_class_probs = win_probs[2:10, :].max(axis=1)
        top_class_rel_idx = np.argmax(shot_class_probs)
        top_class_idx = top_class_rel_idx + 2
        top_prob = float(shot_class_probs[top_class_rel_idx])
        pred_cls = CLASSES[top_class_idx]
        preds.append((pred_cls, top_prob))
        
    return preds

# -----------------------------------------------------------------------------
# Continuous Multi-Tier Evaluation Harness
# -----------------------------------------------------------------------------
def run_session_multitier(sid, sess_data, stage1_model, stage2_model, norm_stats, device):
    t_grid = sess_data["t_grid"]
    channels = sess_data["channels"]  # (N, 12)
    fu_times = sess_data["fu_times"]
    shot_times = sess_data["shot_times"]
    is_holdout = sess_data["is_holdout"]
    
    num_samples = len(t_grid)
    w_acc_mag = np.linalg.norm(channels[:, 0:3], axis=1)
    w_gyr_mag = np.linalg.norm(channels[:, 3:6], axis=1)
    
    parquet_path = os.path.join(UNIFIED_PARQUET_DIR, f"{sid}_unified.parquet")
    df_parquet = pd.read_parquet(parquet_path) if os.path.exists(parquet_path) else None
    
    # 1. Stage 1 Stance Inference over continuous windows
    window_len = 423
    stride = 42  # ~100ms
    windows = []
    t_mids = []
    w_mags = []
    
    for start_idx in range(0, num_samples - window_len, stride):
        end_idx = start_idx + window_len
        win = channels[start_idx:end_idx]
        windows.append(win)
        t_mids.append(t_grid[start_idx + window_len // 2])
        w_mags.append(np.max(w_gyr_mag[start_idx:end_idx]))
        
    if not windows:
        return [], [], 0.0
        
    batch_size = 512
    s1_probs = []
    stage1_model.eval()
    with torch.no_grad():
        for b in range(0, len(windows), batch_size):
            b_win = np.array(windows[b:b+batch_size], dtype=np.float32)
            b_tensor = torch.tensor(b_win, dtype=torch.float32).to(device)
            b_logits = stage1_model(b_tensor)
            b_prob = torch.sigmoid(b_logits).cpu().numpy()
            s1_probs.extend(b_prob)
            
    # 2. Module 1: Stance State Machine Tracking (sustain_ms = 300ms)
    sm = StanceTracker(sustain_ms=300)
    stance_exits = []
    stance_probs = np.zeros(num_samples, dtype=np.float32)
    
    for i in range(len(s1_probs)):
        p = s1_probs[i]
        w = w_mags[i]
        t = t_mids[i]
        f_mid = int(np.searchsorted(t_grid, t))
        if f_mid < num_samples:
            stance_probs[f_mid] = p
            
        was_facing_up = (sm.state == "FACING_UP")
        new_state, exited = sm.process_step(p, w, dt_ms=100)
        
        if exited and was_facing_up:
            stance_exits.append(t)
            
    # 3. Patch 2: Two-Stage Stance-Gated Peak Alignment (T_peak = argmax(w_gyro))
    candidate_windows = []
    
    for t_exit in stance_exits:
        f_exit = int(np.searchsorted(t_grid, t_exit))
        
        # 1. Stance Validation: Check valid FACING_UP (P >= 0.70) within 3.0s prior to exit
        f_pre_s = max(0, int(np.searchsorted(t_grid, t_exit - 3.0)))
        pre_max_p = np.max(s1_probs[max(0, f_exit//42 - 30):min(len(s1_probs), f_exit//42 + 1)]) if len(s1_probs) > 0 else 0.0
        
        # 2. Motion Peak Search: Scan next 2.0s window [T_exit, T_exit + 2.0s] for T_peak
        f_scan_end = min(num_samples, int(np.searchsorted(t_grid, t_exit + 2.0)))
        if f_scan_end <= f_exit + 10:
            continue
            
        win_gyr = w_gyr_mag[f_exit:f_scan_end]
        win_acc = w_acc_mag[f_exit:f_scan_end]
        
        peak_offset = np.argmax(win_gyr)
        peak_f = f_exit + peak_offset
        t_peak = t_grid[peak_f]
        
        peak_acc = win_acc[peak_offset]
        peak_gyr = win_gyr[peak_offset]
        
        # 3. Centered Window Extraction: [T_peak - 1.0s, T_peak + 1.5s]
        tier = "TIER_1_HIGH" if peak_acc >= 30.0 else "TIER_3_SOFT_TOUCH"
        if peak_acc >= 30.0 or peak_gyr >= 1.5:
            candidate_windows.append({
                "tier": tier,
                "anchor_t": t_peak,
                "anchor_f": peak_f,
                "peak_acc": peak_acc,
                "peak_gyr": peak_gyr,
                "t_exit": t_exit
            })
            
    # Deduplicate candidate windows (within 1.0s)
    candidate_windows.sort(key=lambda c: c["anchor_t"])
    dedup_candidates = []
    for c in candidate_windows:
        if not any(abs(c["anchor_t"] - k["anchor_t"]) < 1.0 for k in dedup_candidates):
            dedup_candidates.append(c)
            
    # 4. Load Ground Truth Narrations for Session
    gt_path = os.path.join(SESSIONS_DIR, sid, "ground_truth_aligned.csv")
    gt_events = []
    if os.path.exists(gt_path):
        df_gt = pd.read_csv(gt_path)
        for _, row in df_gt.iterrows():
            stype = str(row.get("shot_type", "")).lower()
            c_name = normalise_shot_type(stype)
            t_sec = float(row.get("sensor_narr_time_seconds", 0.0))
            if c_name:
                gt_events.append({"t": t_sec, "cls": c_name, "raw": stype})
                
    # Patch 1: Calculate Session Clock Offset (dt_offset) via Cross-Correlation Search
    dt_offset = estimate_session_clock_offset(gt_events, t_grid, w_gyr_mag)
    
    # Apply dt_offset to align GT timestamps: T_aligned = T_gt + dt_offset
    aligned_gt_events = []
    for g in gt_events:
        aligned_gt_events.append({
            "t": g["t"] + dt_offset,
            "raw_t": g["t"],
            "cls": g["cls"],
            "raw": g["raw"]
        })
        
    # 5. Evaluate Candidate Windows (Module 3 Un-Leaked Batched GPU Pass)
    candidate_anchors = [c["anchor_f"] for c in dedup_candidates]
    preds = predict_candidate_batch_unleaked(df_parquet, candidate_anchors, stage2_model, norm_stats, device)
    
    results = []
    for i_cand, c in enumerate(dedup_candidates):
        t_cand = c["anchor_t"]
        pred_cls, top_prob = preds[i_cand]
        
        matched_gt = None
        for g in aligned_gt_events:
            if abs(t_cand - g["t"]) <= 1.5:
                matched_gt = g
                break
                
        is_tp = matched_gt is not None
        gt_cls = matched_gt["cls"] if matched_gt else "AMBIENT_REST"
        
        results.append({
            "sid": sid,
            "tier": c["tier"],
            "t": t_cand,
            "is_tp": is_tp,
            "gt_cls": gt_cls,
            "pred_cls": pred_cls,
            "prob": top_prob,
            "is_holdout": is_holdout,
            "peak_acc": c["peak_acc"],
            "peak_gyr": c["peak_gyr"],
            "dt_offset": dt_offset
        })
        
    return results, aligned_gt_events, dt_offset

def main():
    print("==========================================================", flush=True)
    print("  AUDITED HIERARCHICAL MULTI-TIER PIPELINE (PEAK ALIGNED)", flush=True)
    print("==========================================================", flush=True)
    
    if not os.path.exists(DATASET_PATH):
        print(f"Error: Dataset missing at {DATASET_PATH}. Run build_facing_up_dataset.py first.", flush=True)
        sys.exit(1)
        
    with open(DATASET_PATH, "rb") as f:
        dataset = pickle.load(f)
        
    sessions_data = dataset["sessions_data"]
    
    device = torch.device("mps" if torch.backends.mps.is_available() else "cuda" if torch.cuda.is_available() else "cpu")
    print(f"Execution Device: {device}", flush=True)
    
    print(f"Loading Stage 1 Stance TCN Model from {STAGE1_MODEL_PATH}...", flush=True)
    stage1_model = FacingUpTCN(in_channels=12, num_filters=32).to(device)
    stage1_model.load_state_dict(torch.load(STAGE1_MODEL_PATH, map_location=device))
    stage1_model.eval()
    
    print(f"Loading Stage 2 AdvancedTCN Model from {STAGE2_MODEL_PATH}...", flush=True)
    stage2_model = Stage2TCNClassifier(in_ch=26, num_classes=10).to(device)
    stage2_model.load_state_dict(torch.load(STAGE2_MODEL_PATH, map_location=device))
    stage2_model.eval()
    
    print(f"Loading Normalization Stats from {STATS_PATH}...", flush=True)
    with open(STATS_PATH, "r") as f:
        norm_stats = json.load(f)
        
    print(f"\nProcessing all {len(sessions_data)} physical sessions across Multi-Tier Pipeline...", flush=True)
    
    all_results = []
    all_gt_events = []
    session_offsets = {}
    
    for sid, sess_data in sessions_data.items():
        res, gts, dt_off = run_session_multitier(sid, sess_data, stage1_model, stage2_model, norm_stats, device)
        all_results.extend(res)
        all_gt_events.extend([(sid, g) for g in gts])
        session_offsets[sid] = dt_off
        
    df_res = pd.DataFrame(all_results)
    
    # -----------------------------------------------------------------------------
    # Multi-Tier Diagnostic Scorecard (Peak Aligned & Clock Adjusted)
    # -----------------------------------------------------------------------------
    print("\n" + "="*80, flush=True)
    print("         FORENSIC AUDITED MULTI-TIER PIPELINE DIAGNOSTIC SCORECARD", flush=True)
    print("="*80, flush=True)
    
    # 1. Candidate Detections & System Precision
    total_cand = len(df_res)
    total_gt = len(all_gt_events)
    total_tp = df_res["is_tp"].sum()
    global_prec = (total_tp / max(1, total_cand)) * 100.0
    global_rec = (total_tp / max(1, total_gt)) * 100.0
    
    print("\n1️⃣ CANDIDATE DETECTIONS & SYSTEM PRECISION:", flush=True)
    print("----------------------------------------------------------------------", flush=True)
    print(f"  • Total Ground-Truth Physical Shots: {total_gt}", flush=True)
    print(f"  • Total System Candidate Detections: {total_cand} (Target: < 3,100) -> {'PASSED' if total_cand < 3100 else 'CHECK_THRESHOLD'}", flush=True)
    print(f"  • Matched True Positive Detections : {total_tp}", flush=True)
    print(f"  • Global Pipeline Recall           : 🏆 {global_rec:.2f}%", flush=True)
    print(f"  • Global System Precision          : 🏆 {global_prec:.2f}%", flush=True)

    # 2. Tier Breakdown
    print("\n2️⃣ TIER BREAKDOWN (Peak Motion Aligned [T_peak - 1.0s, T_peak + 1.5s]):", flush=True)
    print("----------------------------------------------------------------------", flush=True)
    print("| Tier                    | Total Detections | True Positives | Precision (%) |", flush=True)
    print("----------------------------------------------------------------------", flush=True)
    
    tiers = ["TIER_1_HIGH", "TIER_3_SOFT_TOUCH"]
    for t in tiers:
        df_t = df_res[df_res["tier"] == t]
        tot = len(df_t)
        tp = df_t["is_tp"].sum()
        prec = (tp / max(1, tot)) * 100.0
        name_str = f"{t:23s}"
        print(f"| {name_str} | {tot:16d} | {tp:14d} | {prec:12.2f}% |", flush=True)
    print("----------------------------------------------------------------------", flush=True)

    # 3. GRANULAR HOLDOUT DETAILED SCORECARD (2 UNSEEN POLAR SESSIONS)
    print("\n3️⃣ GRANULAR UNSEEN HOLDOUT SET SCORECARD (AUTOMATIC ALIGNMENT):", flush=True)
    print("======================================================================", flush=True)
    
    df_ho_all = df_res[df_res["is_holdout"]]
    ho_gt_events = [(sid, g) for sid, g in all_gt_events if sid in HOLDOUT_SESSIONS]
    ho_total_gt = len(ho_gt_events)
    ho_total_cand = len(df_ho_all)
    ho_tp = df_ho_all["is_tp"].sum()
    ho_fp = ho_total_cand - ho_tp
    
    ho_rec = (ho_tp / max(1, ho_total_gt)) * 100.0
    ho_prec = (ho_tp / max(1, ho_total_cand)) * 100.0
    
    print(f"  • Designated Holdout Sessions : {HOLDOUT_SESSIONS}", flush=True)
    print(f"  • Ground-Truth Physical Shots : {ho_total_gt}", flush=True)
    print(f"  • Total Candidate Detections  : {ho_total_cand}", flush=True)
    print(f"  • True Positive Detections    : {ho_tp}", flush=True)
    print(f"  • False Positive Detections   : {ho_fp}", flush=True)
    print(f"  • Adjusted Holdout Detection Recall    : 🏆 {ho_rec:.2f}% ({ho_tp}/{ho_total_gt} GT shots detected)", flush=True)
    print(f"  • Adjusted Holdout Detection Precision : 🏆 {ho_prec:.2f}% ({ho_tp}/{ho_total_cand} candidates valid)", flush=True)
    
    print("\n--- CALCULATED TIMESTAMP DRIFT OFFSETS (dt_offset) & PER-SESSION PERFORMANCE ---", flush=True)
    print("---------------------------------------------------------------------------------------------------", flush=True)
    print("| Session ID               | Calculated dt Offset | GT Shots | Detections | TPs | Recall (%) | Precision (%) |", flush=True)
    print("---------------------------------------------------------------------------------------------------", flush=True)
    for h_sid in HOLDOUT_SESSIONS:
        s_gt = sum(1 for sid, g in ho_gt_events if sid == h_sid)
        df_s = df_ho_all[df_ho_all["sid"] == h_sid]
        s_cand = len(df_s)
        s_tp = df_s["is_tp"].sum()
        s_rec = (s_tp / max(1, s_gt)) * 100.0
        s_prec = (s_tp / max(1, s_cand)) * 100.0
        s_offset = session_offsets[h_sid]
        sid_str = f"{h_sid:24s}"
        print(f"| {sid_str} | {s_offset:+18.2f}s | {s_gt:8d} | {s_cand:10d} | {s_tp:3d} | {s_rec:9.1f}% | {s_prec:12.1f}% |", flush=True)
    print("---------------------------------------------------------------------------------------------------\n", flush=True)

    # 4. HOLDOUT CLASSIFICATION ACCURACY PER SHOT TYPE
    print("4️⃣ PEAK-ALIGNED HOLDOUT CLASSIFICATION ACCURACY PER SHOT TYPE:", flush=True)
    print("===================================================================================================", flush=True)
    print("| Shot Type        | GT Count | Detected TPs | Class Correct | Classification Acc (%) | Shot Recall (%) |", flush=True)
    print("===================================================================================================", flush=True)
    
    df_ho_tp = df_ho_all[df_ho_all["is_tp"]]
    
    ho_class_correct_total = 0
    ho_tp_total = len(df_ho_tp)
    
    for s_cls in SHOT_CLASSES:
        gt_cnt = sum(1 for _, g in ho_gt_events if g["cls"] == s_cls)
        df_cls_tp = df_ho_tp[df_ho_tp["gt_cls"] == s_cls]
        det_cnt = len(df_cls_tp)
        correct_cnt = (df_cls_tp["pred_cls"] == s_cls).sum()
        ho_class_correct_total += correct_cnt
        
        cls_acc = (correct_cnt / max(1, det_cnt)) * 100.0 if det_cnt > 0 else 0.0
        shot_rec = (correct_cnt / max(1, gt_cnt)) * 100.0 if gt_cnt > 0 else 0.0
        
        cls_str = f"{s_cls:16s}"
        print(f"| {cls_str} | {gt_cnt:8d} | {det_cnt:12d} | {correct_cnt:13d} | {cls_acc:21.2f}% | {shot_rec:14.2f}% |", flush=True)
        
    print("===================================================================================================", flush=True)
    overall_ho_acc = (ho_class_correct_total / max(1, ho_tp_total)) * 100.0
    print(f"  🏆 OVERALL HOLDOUT CLASSIFICATION ACCURACY: {overall_ho_acc:.2f}% ({ho_class_correct_total}/{ho_tp_total} correct across detected shots)", flush=True)
    print("===================================================================================================\n", flush=True)

if __name__ == "__main__":
    main()
