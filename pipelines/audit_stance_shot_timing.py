#!/usr/bin/env python3
"""
pipelines/audit_stance_shot_timing.py — Stance-to-Shot Timing & Detection Correlation Audit

Analyzes the time difference delta_T = T_shot - T_facing_up from narrations_raw.json
across unseen holdout sessions (session_2026-07-21_12-43-37 & session_2026-07-25_15-16-32).

Computes per-shot-class timing statistics (Min, Max, Avg, Variance) and correlates
delta_T with Stage 1 stance detection and candidate trigger success.
"""

import os
import sys
import json
import pickle
import numpy as np
import pandas as pd
import torch
import torch.nn as nn

ROOT_DIR = "/Users/neilkloot/Code/CricketBattingTracker"
BASE_DIR = "/Users/neilkloot/Code/Batting Sensor Stats"
DATASET_PATH = os.path.join(ROOT_DIR, "facing_up_sessions_423hz.pkl")
STAGE1_MODEL_PATH = os.path.join(ROOT_DIR, "facing_up_tcn_model.pt")
SESSIONS_DIR = os.path.join(BASE_DIR, "live_watch_sessions")

HOLDOUT_OFFSETS = {
    "session_2026-07-21_12-43-37": 1.85,
    "session_2026-07-25_15-16-32": 0.60
}

SHOT_CLASSES = [
    'SLOG', 'PULL/HOOK', 'DRIVE/DEFENCE', 'GLANCE/FLICK',
    'POWER DRIVE', 'DEFLECTION/GUIDE', 'SWEEP', 'CUT/PUNCH'
]

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

def analyze_session_timing(sid, sess_data, dt_offset, stage1_model, device):
    t_grid = sess_data["t_grid"]
    channels = sess_data["channels"]
    num_samples = len(t_grid)
    
    w_acc_mag = np.linalg.norm(channels[:, 0:3], axis=1)
    w_gyr_mag = np.linalg.norm(channels[:, 3:6], axis=1)
    
    # Stage 1 Stance Inference over continuous windows
    window_len = 423
    stride = 42
    windows = []
    t_mids = []
    w_mags = []
    
    for start_idx in range(0, num_samples - window_len, stride):
        end_idx = start_idx + window_len
        win = channels[start_idx:end_idx]
        windows.append(win)
        t_mids.append(t_grid[start_idx + window_len // 2])
        w_mags.append(np.max(w_gyr_mag[start_idx:end_idx]))
        
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
            
    # Stance state machine tracking
    sm = StanceTracker(sustain_ms=300)
    stance_exits = []
    
    for i in range(len(s1_probs)):
        p = s1_probs[i]
        w = w_mags[i]
        t = t_mids[i]
        
        was_facing_up = (sm.state == "FACING_UP")
        new_state, exited = sm.process_step(p, w, dt_ms=100)
        
        if exited and was_facing_up:
            stance_exits.append(t)
            
    # Candidate window creation
    candidate_triggers = []
    for t_exit in stance_exits:
        f_exit = int(np.searchsorted(t_grid, t_exit))
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
        
        if peak_acc >= 30.0 or peak_gyr >= 1.5:
            candidate_triggers.append(t_peak)
            
    # Parse narrations_raw.json for Facing up -> Shot pairs
    narr_path = os.path.join(SESSIONS_DIR, sid, "narrations_raw.json")
    items = json.load(open(narr_path)) if os.path.exists(narr_path) else []
    
    pairs = []
    last_fu_t = None
    
    for item in items:
        stype = item.get("shot_type") or ""
        t_sec = float(item.get("timestamp_seconds", 0.0))
        
        if stype.lower() == "facing up":
            last_fu_t = t_sec
        else:
            c_name = normalise_shot_type(stype)
            if c_name:
                delta_t = (t_sec - last_fu_t) if (last_fu_t is not None and t_sec > last_fu_t) else None
                
                # Check detection success with aligned timestamp
                t_aligned_shot = t_sec + dt_offset
                
                # Stance check in [t_aligned_shot - 4.0, t_aligned_shot - 0.5]
                t_w_start = t_aligned_shot - 4.0
                t_w_end = t_aligned_shot - 0.5
                stance_detected = False
                for i_mid in range(len(t_mids)):
                    if t_w_start <= t_mids[i_mid] <= t_w_end and s1_probs[i_mid] >= 0.70:
                        stance_detected = True
                        break
                        
                shot_triggered = any(abs(t_cand - t_aligned_shot) <= 1.5 for t_cand in candidate_triggers)
                
                pairs.append({
                    "sid": sid,
                    "cls": c_name,
                    "raw_shot_t": t_sec,
                    "last_fu_t": last_fu_t,
                    "delta_t": delta_t,
                    "aligned_shot_t": t_aligned_shot,
                    "stance_detected": stance_detected,
                    "shot_triggered": shot_triggered
                })
                
    return pairs

def main():
    print("==========================================================", flush=True)
    print("  STANCE-TO-SHOT TIMING & DETECTION CORRELATION AUDIT", flush=True)
    print("==========================================================", flush=True)
    
    if not os.path.exists(DATASET_PATH):
        print(f"Error: Dataset missing at {DATASET_PATH}.", flush=True)
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
    
    all_pairs = []
    for sid, dt_offset in HOLDOUT_OFFSETS.items():
        if sid in sessions_data:
            pairs = analyze_session_timing(sid, sessions_data[sid], dt_offset, stage1_model, device)
            all_pairs.extend(pairs)
            
    df = pd.DataFrame(all_pairs)
    
    # -----------------------------------------------------------------------------
    # 1. Per-Shot-Class Timing Statistics Table
    # -----------------------------------------------------------------------------
    print("\n" + "="*95, flush=True)
    print("      FACING UP -> SHOT NARRATION TIMING METRICS (DELTA T = T_shot - T_facing_up)", flush=True)
    print("="*95, flush=True)
    print("| Shot Class        | GT Shots | Paired Stances | Min (s) | Max (s) | Avg (s) | Variance (s²) | Std Dev (s) |", flush=True)
    print("="*95, flush=True)
    
    valid_deltas = []
    
    for s_cls in SHOT_CLASSES:
        df_c = df[df["cls"] == s_cls]
        gt_cnt = len(df_c)
        
        if gt_cnt == 0:
            cls_str = f"{s_cls:17s}"
            print(f"| {cls_str} |        0 |              - |       - |       - |       - |             - |           - |", flush=True)
            continue
            
        deltas = df_c["delta_t"].dropna().values
        paired_cnt = len(deltas)
        valid_deltas.extend(deltas)
        
        if paired_cnt > 0:
            min_t = np.min(deltas)
            max_t = np.max(deltas)
            avg_t = np.mean(deltas)
            var_t = np.var(deltas)
            std_t = np.std(deltas)
            cls_str = f"{s_cls:17s}"
            print(f"| {cls_str} | {gt_cnt:8d} | {paired_cnt:14d} | {min_t:7.2f} | {max_t:7.2f} | {avg_t:7.2f} | {var_t:13.2f} | {std_t:11.2f} |", flush=True)
        else:
            cls_str = f"{s_cls:17s}"
            print(f"| {cls_str} | {gt_cnt:8d} |              0 |       - |       - |       - |             - |           - |", flush=True)
            
    print("="*95, flush=True)
    tot_gt = len(df)
    tot_paired = len(valid_deltas)
    if tot_paired > 0:
        overall_min = np.min(valid_deltas)
        overall_max = np.max(valid_deltas)
        overall_avg = np.mean(valid_deltas)
        overall_var = np.var(valid_deltas)
        overall_std = np.std(valid_deltas)
        print(f"| {'TOTAL / OVERALL':17s} | {tot_gt:8d} | {tot_paired:14d} | {overall_min:7.2f} | {overall_max:7.2f} | {overall_avg:7.2f} | {overall_var:13.2f} | {overall_std:11.2f} |", flush=True)
    print("="*95 + "\n", flush=True)

    # -----------------------------------------------------------------------------
    # 2. Timing Correlation Analysis with Detection Success
    # -----------------------------------------------------------------------------
    print("📊 CORRELATION ANALYSIS: FACING UP -> SHOT TIMING vs DETECTION SUCCESS", flush=True)
    print("===================================================================================================", flush=True)
    
    df_valid = df.dropna(subset=["delta_t"]).copy()
    
    # Stance Detection Breakdown
    df_st_det = df_valid[df_valid["stance_detected"]]
    df_st_mis = df_valid[~df_valid["stance_detected"]]
    
    avg_t_st_det = df_st_det["delta_t"].mean() if len(df_st_det) > 0 else 0.0
    avg_t_st_mis = df_st_mis["delta_t"].mean() if len(df_st_mis) > 0 else 0.0
    
    # Candidate Trigger Breakdown
    df_tr_det = df_valid[df_valid["shot_triggered"]]
    df_tr_mis = df_valid[~df_valid["shot_triggered"]]
    
    avg_t_tr_det = df_tr_det["delta_t"].mean() if len(df_tr_det) > 0 else 0.0
    avg_t_tr_mis = df_tr_mis["delta_t"].mean() if len(df_tr_mis) > 0 else 0.0
    
    # Point-biserial correlation coefficients
    if len(df_valid) > 5:
        r_stance = np.corrcoef(df_valid["delta_t"], df_valid["stance_detected"].astype(float))[0, 1]
        r_trig = np.corrcoef(df_valid["delta_t"], df_valid["shot_triggered"].astype(float))[0, 1]
    else:
        r_stance, r_trig = 0.0, 0.0
        
    print(f"1. STANCE DETECTION (Stage 1 Facing Up P >= 0.70):", flush=True)
    print(f"   • Mean Delta T when Stance DETECTED : {avg_t_st_det:.2f}s (N = {len(df_st_det)})", flush=True)
    print(f"   • Mean Delta T when Stance MISSED   : {avg_t_st_mis:.2f}s (N = {len(df_st_mis)})", flush=True)
    print(f"   • Point-Biserial Correlation (r)    : {r_stance:+.3f} ({'Slight Positive' if r_stance > 0 else 'Slight Negative'})", flush=True)
    print("---------------------------------------------------------------------------------------------------", flush=True)
    print(f"2. CANDIDATE SHOT TRIGGERING (Downstream Transition):", flush=True)
    print(f"   • Mean Delta T when Shot TRIGGERED : {avg_t_tr_det:.2f}s (N = {len(df_tr_det)})", flush=True)
    print(f"   • Mean Delta T when Shot MISSED    : {avg_t_tr_mis:.2f}s (N = {len(df_tr_mis)})", flush=True)
    print(f"   • Point-Biserial Correlation (r)   : {r_trig:+.3f} ({'Slight Positive' if r_trig > 0 else 'Slight Negative'})", flush=True)
    print("===================================================================================================\n", flush=True)

if __name__ == "__main__":
    main()
