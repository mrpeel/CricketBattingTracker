#!/usr/bin/env python3
"""
pipelines/audit_facing_up_per_shot_class.py — Standalone Diagnostic Audit

Audits why overall shot detection recall is ~32% on the unseen holdout set by evaluating:
  1. Facing Up Stance Detection Recall per shot class (P >= 0.70 within [T_shot - 4.0s, T_shot - 0.5s]).
  2. Candidate Shot Triggering Recall per shot class.
  3. Conversion Gap (Stance Detected -> Candidate Shot Triggered).
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

def audit_session(sid, sess_data, dt_offset, stage1_model, device):
    t_grid = sess_data["t_grid"]
    channels = sess_data["channels"]
    num_samples = len(t_grid)
    
    w_acc_mag = np.linalg.norm(channels[:, 0:3], axis=1)
    w_gyr_mag = np.linalg.norm(channels[:, 3:6], axis=1)
    
    # 1. Stage 1 Stance Inference over continuous windows
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
            
    # Candidate window creation (Peak Motion Aligned)
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
            
    # Load GT Physical Shots
    gt_path = os.path.join(SESSIONS_DIR, sid, "ground_truth_aligned.csv")
    gt_shots = []
    if os.path.exists(gt_path):
        df_gt = pd.read_csv(gt_path)
        for _, row in df_gt.iterrows():
            stype = str(row.get("shot_type", "")).lower()
            c_name = normalise_shot_type(stype)
            t_sec = float(row.get("sensor_narr_time_seconds", 0.0))
            if c_name:
                gt_shots.append({
                    "raw_t": t_sec,
                    "aligned_t": t_sec + dt_offset,
                    "cls": c_name,
                    "raw": stype
                })
                
    # Per-shot dual Boolean evaluation
    shot_audits = []
    for g in gt_shots:
        t_shot = g["aligned_t"]
        c_name = g["cls"]
        
        # Check 1: Facing Up Stance Detected in [T_shot - 4.0s, T_shot - 0.5s]?
        t_w_start = t_shot - 4.0
        t_w_end = t_shot - 0.5
        
        stance_detected = False
        for i_mid in range(len(t_mids)):
            t_mid = t_mids[i_mid]
            if t_w_start <= t_mid <= t_w_end:
                if s1_probs[i_mid] >= 0.70:
                    stance_detected = True
                    break
                    
        # Check 2: Physical Candidate Window Triggered & Matched (+-1.5s)?
        shot_triggered = any(abs(t_cand - t_shot) <= 1.5 for t_cand in candidate_triggers)
        
        shot_audits.append({
            "sid": sid,
            "cls": c_name,
            "t_shot": t_shot,
            "stance_detected": stance_detected,
            "shot_triggered": shot_triggered
        })
        
    return shot_audits

def main():
    print("==========================================================", flush=True)
    print("  PER-SHOT-CLASS FACING UP STANCE & CANDIDATE AUDIT", flush=True)
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
    
    print(f"\nAuditing unseen holdout sessions: {list(HOLDOUT_OFFSETS.keys())}...", flush=True)
    
    all_shot_audits = []
    for sid, dt_offset in HOLDOUT_OFFSETS.items():
        if sid in sessions_data:
            audits = audit_session(sid, sessions_data[sid], dt_offset, stage1_model, device)
            all_shot_audits.extend(audits)
            
    df_audit = pd.DataFrame(all_shot_audits)
    
    # -----------------------------------------------------------------------------
    # Diagnostic Output Table
    # -----------------------------------------------------------------------------
    print("\n" + "="*95, flush=True)
    print("       PER-SHOT-CLASS FACING UP STANCE & CANDIDATE TRIGGER DIAGNOSTIC TABLE", flush=True)
    print("="*95, flush=True)
    print("| Shot Class        | GT Shots | Facing Up Detected | Stance Recall (%) | Shots Triggered | Shot Recall (%) | Conversion Gap |", flush=True)
    print("="*95, flush=True)
    
    total_gt = 0
    total_stance = 0
    total_trig = 0
    
    for s_cls in SHOT_CLASSES:
        df_c = df_audit[df_audit["cls"] == s_cls]
        gt_cnt = len(df_c)
        
        if gt_cnt == 0:
            cls_str = f"{s_cls:17s}"
            print(f"| {cls_str} |        0 |                 -  |                -  |              -  |              -  |              - |", flush=True)
            continue
            
        total_gt += gt_cnt
        stance_cnt = df_c["stance_detected"].sum()
        trig_cnt = df_c["shot_triggered"].sum()
        
        total_stance += stance_cnt
        total_trig += trig_cnt
        
        stance_rec = (stance_cnt / gt_cnt) * 100.0
        shot_rec = (trig_cnt / gt_cnt) * 100.0
        conv_gap = stance_cnt - trig_cnt
        conv_gap_pct = ((stance_cnt - trig_cnt) / gt_cnt) * 100.0
        
        cls_str = f"{s_cls:17s}"
        print(f"| {cls_str} | {gt_cnt:8d} | {stance_cnt:18d} | {stance_rec:16.1f}% | {trig_cnt:15d} | {shot_rec:13.1f}% | {conv_gap:3d} ({conv_gap_pct:4.1f}%) |", flush=True)
        
    print("="*95, flush=True)
    tot_stance_rec = (total_stance / max(1, total_gt)) * 100.0
    tot_shot_rec = (total_trig / max(1, total_gt)) * 100.0
    tot_gap = total_stance - total_trig
    tot_gap_pct = (tot_gap / max(1, total_gt)) * 100.0
    
    print(f"| {'TOTAL / OVERALL':17s} | {total_gt:8d} | {total_stance:18d} | 🏆 {tot_stance_rec:14.1f}% | {total_trig:15d} | 🏆 {tot_shot_rec:11.1f}% | {tot_gap:3d} ({tot_gap_pct:4.1f}%) |", flush=True)
    print("="*95 + "\n", flush=True)
    
    # -----------------------------------------------------------------------------
    # Diagnostic Answers
    # -----------------------------------------------------------------------------
    print("💡 DIAGNOSTIC ANSWERS & ARCHITECTURAL INSIGHTS:", flush=True)
    print("----------------------------------------------------------------------", flush=True)
    print(f"1. Overall Facing Up Stance Recall: {tot_stance_rec:.1f}% ({total_stance}/{total_gt} GT shots preceded by Facing Up stance P >= 0.70).", flush=True)
    
    # Calculate per-class conversion gaps
    gaps = []
    missed_stance = []
    for s_cls in SHOT_CLASSES:
        df_c = df_audit[df_audit["cls"] == s_cls]
        gt_cnt = len(df_c)
        if gt_cnt > 0:
            st_cnt = df_c["stance_detected"].sum()
            tr_cnt = df_c["shot_triggered"].sum()
            gap = st_cnt - tr_cnt
            st_rec = (st_cnt / gt_cnt) * 100.0
            gaps.append((s_cls, gap, st_cnt, tr_cnt))
            if st_cnt == 0:
                missed_stance.append(s_cls)
                
    gaps.sort(key=lambda x: x[1], reverse=True)
    print("2. Largest Conversion Gaps (Stance Detected -> Candidate Shot NOT Triggered):", flush=True)
    for g in gaps[:3]:
        print(f"   • {g[0]}: {g[1]} shots lost between stance detection ({g[2]} stances) and candidate trigger ({g[3]} candidates).", flush=True)
        
    if missed_stance:
        print(f"3. Shot Classes with 0% Stance Recall: {missed_stance}", flush=True)
    else:
        print("3. Shot Classes with 0% Stance Recall: NONE. Facing Up stance was detected across all present shot classes!", flush=True)
    print("----------------------------------------------------------------------\n", flush=True)

if __name__ == "__main__":
    main()
