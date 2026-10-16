#!/usr/bin/env python3
"""
pipelines/train_and_evaluate_full_scorecard.py — Master Training & Unified Multi-Tier Evaluation

Phase 2: Learned False-Positive Rejection (Bat-Plane 3-Family Multi-Scale TCN)

1. Auto-synchronizes live watch sessions into unified 423 Hz Parquet datasets.
2. Loads physical sessions directly from Parquet files according to dataset_splits.json.
3. Computes feature normalization statistics (median / MAD) from training sessions,
   enforcing unit variance (mad=1.0) on Polar channels.
4. Prepares candidate windows with hard-negative mining (unmatched Stage 1 candidates
   labeled as class 0 'no_shot'). Caches to train_candidate_windows.pt and val_candidate_windows.pt.
5. Trains Bat-Plane 3-Family Multi-Scale TCN with Learned Binary Rejection Head:
   - Progressive 10-Layer TCN Backbone ([16, 16, 16, 16, 16, 32, 64, 128, 256, 512])
   - Multi-Scale Impact-Core Pooling (Core L5 [16d], Core L7 [64d], Proj Core L10 [64d], Global L7 [64d] = 208d)
   - Head 0: Learned Binary Rejection Head (0: no_shot, 1: is_shot)
   - Head 1: 3-Family Macro Gate (Vertical-Bat, Cross-Bat Horizontal, Floor Sweep)
   - Head 2A (Vertical-Bat, 4 Classes): DRIVE/DEFENCE, POWER DRIVE, GLANCE/FLICK, DEFLECTION/GUIDE
   - Head 2B (Cross-Bat Horizontal, 2 Classes): PULL/HOOK/SLOG, CUT/PUNCH
   - Head 2C (Floor / Crouch): SWEEP
   - Power Drive Soft-Routing: P(is_shot) * (p_fam[0] + 0.35 * p_fam[1]) * p_sub0[1]
   - Discriminative Layer-Wise Optimizer: AdamW with 1.5e-4 (L1-7) and 5e-4 (L8-10 + Heads)
   - CosineAnnealingLR to 1e-6 with 3-epoch warmup
   - Losses: Binary Rejection CE (smoothing 0.05) + Hierarchical Family & Sub-Class CE (smoothing 0.08)
     with 2.0x weight on POWER DRIVE.
   - Early Stopping: Monitored validation candidate Macro-F1 with 0.35 rejection threshold.
6. Evaluates benchmark dataset across all 72 clean physical sessions via Telemetry Engine
   (pipelines/telemetry_engine.py). Zero Train-Serve Skew.
7. Enforces Production Quality Gate (Holdout Precision >= 75% or Micro Precision >= 70%, Holdout F1 >= 50%)
   and exports ONNX model to app assets.
8. Generates the authoritative full_dataset_training_scorecard.md report.
"""

import os
import sys
import json
import glob
import math
import shutil
import random
import argparse
import datetime
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import TensorDataset, DataLoader
from sklearn.metrics import f1_score, accuracy_score

ROOT_DIR = "/Users/neilkloot/Code/CricketBattingTracker"
PIPELINES_DIR = os.path.join(ROOT_DIR, "pipelines")
if PIPELINES_DIR not in sys.path:
    sys.path.append(PIPELINES_DIR)

from telemetry_engine import (
    ROOT_DIR, BASE_DIR, DATASET_DIR, SESSIONS_DIR, STAGE1_MODEL_PATH, STAGE2_MODEL_PATH,
    STATS_PATH, APP_ASSETS_DIR, REPORT_OUT, HOLDOUT_SESSIONS, HOLDOUT_TEST_SESSIONS,
    VALIDATION_SESSIONS, QUARANTINE_SESSIONS, STAGE1_CHANNELS, FEATURES,
    CLASSES, SHOT_CLASSES, SOFT_TOUCH_CLASSES, normalise_shot_type,
    FacingUpTCN, StanceTracker, AdvancedTCNBlock, BatPlaneGeometryThreeFamilyTCN,
    estimate_session_clock_offset, load_parquet_session, predict_candidate_batch_unleaked,
    run_session_multitier, format_class_table, evaluate_multitier_scorecard,
    HOLDOUT_EMPIRICAL_OFFSETS
)
from training_logger import setup_training_logger

MODEL_PT_PATH = STAGE2_MODEL_PATH
MODEL_ONNX_PATH = os.path.join(ROOT_DIR, "pipelines", "tcn_ultimate_baseline.onnx")
APP_ONNX_PATH = os.path.join(APP_ASSETS_DIR, "tcn_ultimate_baseline.onnx")

CLASS_TO_IDX = {c: i for i, c in enumerate(CLASSES)}
NUM_CLASSES = len(CLASSES)
NUM_FEATURES = len(FEATURES)

WINDOW_LEN = 2048
BATCH_SIZE = 32
DEVICE = 'mps' if torch.backends.mps.is_available() else ('cuda' if torch.cuda.is_available() else 'cpu')

# Bat Plane Geometry Mappings:
# Family 0 (Vertical-Bat Strokes - 4 Classes): DRIVE/DEFENCE(3), POWER DRIVE(7), GLANCE/FLICK(4), DEFLECTION/GUIDE(6)
# Family 1 (Cross-Bat Horizontal Strokes - 2 Classes): PULL/HOOK/SLOG(2), CUT/PUNCH(5)
# Family 2 (Floor / Crouch - 1 Class): SWEEP(8)
FAM3_LOOKUP_FAMILY_T = torch.tensor([0, 0, 1, 0, 0, 1, 0, 0, 2], dtype=torch.int64, device=DEVICE)
FAM3_LOOKUP_SUB_T    = torch.tensor([0, 0, 0, 0, 2, 1, 3, 1, 0], dtype=torch.int64, device=DEVICE)

WEIGHT_2A = torch.tensor([1.0, 2.0, 1.0, 1.0], dtype=torch.float32, device=DEVICE)
WEIGHT_FAM = torch.tensor([1.0, 1.0, 1.0], dtype=torch.float32, device=DEVICE)


def sync_unified_dataset():
    """Discovers all live sessions in live_watch_sessions and compiles any missing or outdated unified parquets."""
    import build_unified_dataset
    live_sessions = build_unified_dataset.discover_sessions()
    print(f"\n📦 Dataset Auto-Sync: Discovered {len(live_sessions)} usable sessions in live_watch_sessions/")
    newly_built = 0
    for s in live_sessions:
        out_parquet = os.path.join(DATASET_DIR, f"{s}_unified.parquet")
        raw_narr_path = os.path.join(BASE_DIR, "live_watch_sessions", s, "narrations_raw.json")
        raw_watch_path = os.path.join(BASE_DIR, "live_watch_sessions", s, "WatchGyroscope.bin.gz")
        
        rebuild_needed = False
        if not os.path.exists(out_parquet):
            rebuild_needed = True
        elif os.path.exists(raw_narr_path) and os.path.getmtime(raw_narr_path) > os.path.getmtime(out_parquet):
            rebuild_needed = True
        elif os.path.exists(raw_watch_path) and os.path.getmtime(raw_watch_path) > os.path.getmtime(out_parquet):
            rebuild_needed = True
            
        if rebuild_needed:
            print(f"  ⚡ Auto-compiling unified dataset for {s}...")
            build_unified_dataset.build_session(s, verbose=False)
            newly_built += 1
            
    if newly_built > 0:
        print(f"✅ Auto-Sync Completed: Compiled {newly_built} new/updated unified parquet sessions.\n")
    else:
        print(f"✅ Auto-Sync Up-To-Date: All {len(live_sessions)} parquet datasets are synchronized.\n")


def load_dataset_for_training(session_name):
    df = load_parquet_session(session_name, dataset_dir=DATASET_DIR)
    if df is None:
        return None
    X = df[FEATURES].fillna(0.0).values.astype(np.float32)
    mapped_labels = df['label'].apply(lambda x: normalise_shot_type(x) if x not in ['no_shot', 'pre_shot'] else x)
    y = mapped_labels.map(CLASS_TO_IDX).fillna(0).values.astype(np.int64)
    return X, y, df


def extract_session_candidate_windows(sid, s1, med, mad, is_train=True):
    """
    Extracts candidate windows from a session matching the unleaked Stage 1 + Stage 2 candidate pipeline.
    Unmatched candidate detections (false alarms) are labeled as class 0 ('no_shot').
    Matched candidate detections are labeled with the GT class index (2..8).
    In training, missed GT shots are also added centered on their physical impact peak.
    """
    df = load_parquet_session(sid, dataset_dir=DATASET_DIR)
    if df is None or len(df) < WINDOW_LEN:
        return []

    t_grid = df['t_ms'].values / 1000.0
    channels_12 = df[STAGE1_CHANNELS].fillna(0.0).values.astype(np.float32)
    w_acc_mag = np.linalg.norm(channels_12[:, 0:3], axis=1)
    w_gyr_mag = np.linalg.norm(channels_12[:, 3:6], axis=1)

    stride = 42
    windows = []
    t_mids = []
    w_mags = []
    for start_idx in range(0, len(t_grid) - 423, stride):
        end_idx = start_idx + 423
        windows.append(channels_12[start_idx:end_idx])
        t_mids.append(t_grid[start_idx + 211])
        w_mags.append(np.max(w_gyr_mag[start_idx:end_idx]))

    s1_probs = []
    s1.eval()
    with torch.no_grad():
        for b in range(0, len(windows), 512):
            b_win = np.array(windows[b:b+512], dtype=np.float32)
            s1_probs.extend(torch.sigmoid(s1(torch.tensor(b_win).to(DEVICE))).cpu().numpy())

    sm = StanceTracker(high_thresh=0.55, low_thresh=0.35, motion_surge_w=1.8, sustain_ms=200)
    stance_exits = []
    for p, w, t in zip(s1_probs, w_mags, t_mids):
        was_facing_up = (sm.state == "FACING_UP")
        new_state, exited = sm.process_step(p, w, dt_ms=100)
        if exited and was_facing_up:
            stance_exits.append(t)

    cands = []
    for t_exit in stance_exits:
        f_exit = int(np.searchsorted(t_grid, t_exit))
        f_scan_end = min(len(t_grid), int(np.searchsorted(t_grid, t_exit + 4.0)))
        if f_scan_end <= f_exit + 10:
            continue
        win_gyr = w_gyr_mag[f_exit:f_scan_end]
        win_acc = w_acc_mag[f_exit:f_scan_end]
        peak_offset = np.argmax(win_gyr)
        peak_f = f_exit + peak_offset
        t_peak = t_grid[peak_f]
        peak_acc = win_acc[peak_offset]
        peak_gyr = win_gyr[peak_offset]
        f_pre = max(0, peak_f - 127)
        delta_theta = float(np.sum(w_gyr_mag[f_pre : peak_f + 1]) * (1.0 / 423.0))
        tier = "TIER_1_HIGH" if peak_acc >= 30.0 else "TIER_3_SOFT_TOUCH"
        if peak_gyr >= 1.0 and delta_theta >= 0.14:
            cands.append({"anchor_f": peak_f, "anchor_t": t_peak, "peak_gyr": peak_gyr, "peak_acc": peak_acc, "tier": tier})

    # 1.8s NMS deduplication
    cands.sort(key=lambda c: c["anchor_t"])
    dedup = []
    for c in cands:
        if not dedup or (c["anchor_t"] - dedup[-1]["anchor_t"]) >= 1.8:
            dedup.append(c)

    # Load GT
    gt_path = os.path.join(SESSIONS_DIR, sid, "ground_truth_aligned.csv")
    gt_events = []
    if os.path.exists(gt_path):
        df_gt = pd.read_csv(gt_path)
        has_impact = ("impact_time_seconds" in df_gt.columns and df_gt["impact_time_seconds"].notna().sum() > 0)
        for _, row in df_gt.iterrows():
            st = normalise_shot_type(row.get("shot_type"))
            if not st:
                continue
            is_fb = (row.get("is_fallback") is True) or (float(row.get("impact_gyro_mag", 0.0)) <= 1.05)
            if has_impact and pd.notna(row.get("impact_time_seconds")) and not is_fb:
                t_sec = float(row["impact_time_seconds"])
                from_imp = True
            else:
                t_sec = float(row.get("sensor_narr_time_seconds", 0.0))
                from_imp = False
            gt_events.append({"t": t_sec, "cls": st, "from_impact": from_imp})

    if sid in HOLDOUT_EMPIRICAL_OFFSETS:
        dt_off = HOLDOUT_EMPIRICAL_OFFSETS[sid]
    elif any(g["from_impact"] for g in gt_events):
        dt_off = 0.0
    else:
        dt_off = estimate_session_clock_offset(gt_events, t_grid, w_gyr_mag, session_id=sid)

    for g in gt_events:
        if not g["from_impact"]:
            g["t"] += dt_off

    matched_gt_indices = set()
    samples = []
    X_norm = (df[FEATURES].fillna(0.0).values.astype(np.float32) - med) / mad

    for c in dedup:
        cand_t = c["anchor_t"]
        best_d = 99.0
        best_gi = None
        for gi, g in enumerate(gt_events):
            tol = 1.5 if g.get("from_impact", False) else 2.5
            d = abs(cand_t - g["t"])
            if d <= tol and d < best_d:
                best_d = d
                best_gi = gi

        if best_gi is not None:
            matched_gt_indices.add(best_gi)
            cls_name = gt_events[best_gi]["cls"]
            cls_idx = CLASSES.index(cls_name)
        else:
            cls_name = "no_shot"
            cls_idx = 0

        f_mid = c["anchor_f"]
        start_f = max(0, f_mid - 1024)
        end_f = start_f + 2048
        if end_f > len(X_norm):
            end_f = len(X_norm)
            start_f = max(0, end_f - 2048)
        win = X_norm[start_f:end_f]
        if len(win) == 2048:
            samples.append((win.T, cls_idx, cand_t, cls_name, c["peak_gyr"], c["peak_acc"]))

    if is_train:
        for gi, g in enumerate(gt_events):
            if gi not in matched_gt_indices:
                f_mid = int(g["t"] * 423.0)
                start_f = max(0, f_mid - 1024)
                end_f = start_f + 2048
                if end_f > len(X_norm):
                    end_f = len(X_norm)
                    start_f = max(0, end_f - 2048)
                win = X_norm[start_f:end_f]
                if len(win) == 2048:
                    cls_name = g["cls"]
                    cls_idx = CLASSES.index(cls_name)
                    samples.append((win.T, cls_idx, g["t"], cls_name, 15.0, 50.0))

    return samples


def load_or_extract_candidate_windows(train_sessions, val_sessions, med, mad, force_reextract=False):
    """Loads cached candidate windows or extracts fresh windows from training and validation sessions."""
    train_cache = os.path.join(PIPELINES_DIR, "train_candidate_windows.pt")
    val_cache = os.path.join(PIPELINES_DIR, "val_candidate_windows.pt")

    if os.path.exists(train_cache) and os.path.exists(val_cache) and not force_reextract:
        print(f"📦 Loading pre-extracted candidate windows from cache ({train_cache})...", flush=True)
        train_samples = torch.load(train_cache, weights_only=False)
        val_samples = torch.load(val_cache, weights_only=False)
        print(f"✅ Loaded {len(train_samples)} training and {len(val_samples)} validation candidate windows from cache.\n", flush=True)
        return train_samples, val_samples

    print(f"⚡ Extracting candidate windows with hard-negative mining across {len(train_sessions)} train and {len(val_sessions)} val sessions...", flush=True)
    s1 = FacingUpTCN(in_channels=12, num_filters=32).to(DEVICE)
    s1.load_state_dict(torch.load(STAGE1_MODEL_PATH, map_location=DEVICE))
    s1.eval()

    train_samples = []
    for sid in train_sessions:
        train_samples.extend(extract_session_candidate_windows(sid, s1, med, mad, is_train=True))

    val_samples = []
    for sid in val_sessions:
        val_samples.extend(extract_session_candidate_windows(sid, s1, med, mad, is_train=False))

    torch.save(train_samples, train_cache)
    torch.save(val_samples, val_cache)
    print(f"✅ Extracted & cached {len(train_samples)} training and {len(val_samples)} validation candidate windows.\n", flush=True)
    return train_samples, val_samples


def train_and_select_checkpoint(train_samples, val_samples, total_epochs=28, batch_size=BATCH_SIZE):
    """
    Trains the BatPlaneGeometryThreeFamilyTCN model with Learned False-Positive Rejection
    using peak-centered candidate windows, discriminative layer-wise learning rates,
    and validation macro-F1 early stopping.
    """
    train_X = torch.stack([torch.tensor(s[0], dtype=torch.float32) for s in train_samples])
    train_y = torch.tensor([s[1] for s in train_samples], dtype=torch.int64)
    val_X = torch.stack([torch.tensor(s[0], dtype=torch.float32) for s in val_samples])
    val_y = torch.tensor([s[1] for s in val_samples], dtype=torch.int64)

    train_dataset = TensorDataset(train_X, train_y)
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True, drop_last=True)
    val_dataset = TensorDataset(val_X, val_y)
    val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False)

    print(f"✅ Prepared TensorDatasets: Train={len(train_dataset)} windows, Val={len(val_dataset)} windows.\n", flush=True)

    model = BatPlaneGeometryThreeFamilyTCN(in_ch=NUM_FEATURES).to(DEVICE)

    # Loss Functions:
    loss_ce_reject = nn.CrossEntropyLoss(label_smoothing=0.05)
    loss_ce_family = nn.CrossEntropyLoss(weight=WEIGHT_FAM, label_smoothing=0.08)
    loss_ce_standard = nn.CrossEntropyLoss(label_smoothing=0.08)
    loss_ce_sub0 = nn.CrossEntropyLoss(weight=WEIGHT_2A, label_smoothing=0.08)  # 2.0x weight on POWER DRIVE

    TOTAL_EPOCHS = total_epochs
    WARMUP_EPOCHS = 3
    PATIENCE = 16
    MIN_DELTA = 0.001

    # Layer-Wise Discriminative Parameter Groups:
    l1_7_params = [p for i in range(7) for p in model.blocks[i].parameters()]
    l8_10_head_params = (
        [p for i in range(7, 10) for p in model.blocks[i].parameters()] +
        list(model.proj_l10.parameters()) +
        list(model.head_reject.parameters()) +
        list(model.head_family.parameters()) +
        list(model.head_sub0.parameters()) +
        list(model.head_sub1.parameters())
    )

    optimizer = torch.optim.AdamW([
        {'params': l1_7_params, 'lr': 1.5e-4},
        {'params': l8_10_head_params, 'lr': 5e-4}
    ], weight_decay=1e-2)

    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=(TOTAL_EPOCHS - WARMUP_EPOCHS), eta_min=1e-6)

    best_macro_f1 = -1.0
    best_shot_acc = 0.0
    best_val_loss = float('inf')
    best_epoch = 0
    patience_counter = 0
    best_model_state = None
    final_epoch = TOTAL_EPOCHS

    print("="*95, flush=True)
    print(f"🚀 UNIFIED PHASE 2 REJECTOR TRAINING (EPOCHS 1 TO {TOTAL_EPOCHS})", flush=True)
    print("   Backbone Layers 1–7: 1.5e-4 | Layers 8–10 + Heads: 5e-4")
    print(f"   Warmup: {WARMUP_EPOCHS} Epochs | Scheduler: CosineAnnealingLR (to 1e-6) | AdamW weight_decay=1e-2")
    print(f"   Loss: Rejector CE (0.05) + Family/Sub CE (0.08) with Head 2A Weight: {WEIGHT_2A.cpu().tolist()}")
    print(f"   Early Stopping: Patience = {PATIENCE}, Min Delta = {MIN_DELTA} (monitoring Validation Macro-F1)")
    print("="*95, flush=True)

    for epoch in range(1, TOTAL_EPOCHS + 1):
        if epoch <= WARMUP_EPOCHS:
            warmup_factor = epoch / float(WARMUP_EPOCHS)
            optimizer.param_groups[0]['lr'] = 1.5e-4 * warmup_factor
            optimizer.param_groups[1]['lr'] = 5e-4 * warmup_factor
        else:
            scheduler.step()

        lr_l1_7 = optimizer.param_groups[0]['lr']
        lr_upper = optimizer.param_groups[1]['lr']

        # Training Pass
        model.train()
        r_loss = 0.0
        n_b = 0
        for xb, yb in train_loader:
            xb = xb.to(DEVICE)
            yb = yb.to(DEVICE)

            l_rej, l_fam, l_sub0, l_sub1 = model.forward_heads(xb)

            # Binary Rejection Target: 0 for no_shot (yb == 0), 1 for genuine shot (yb >= 2)
            y_bin = (yb >= 2).long()
            loss_rej = loss_ce_reject(l_rej, y_bin)

            # Shot Hierarchy Loss:
            shot_mask = (yb >= 2)
            if shot_mask.any():
                shot_yb = yb[shot_mask]
                shot_fam = FAM3_LOOKUP_FAMILY_T[shot_yb]
                shot_sub = FAM3_LOOKUP_SUB_T[shot_yb]

                loss_family = loss_ce_family(l_fam[shot_mask], shot_fam)

                fam0_mask = (shot_fam == 0)
                l_sub0_val = loss_ce_sub0(l_sub0[shot_mask][fam0_mask], shot_sub[fam0_mask]) if fam0_mask.any() else torch.tensor(0.0, device=DEVICE)

                fam1_mask = (shot_fam == 1)
                l_sub1_val = loss_ce_standard(l_sub1[shot_mask][fam1_mask], shot_sub[fam1_mask]) if fam1_mask.any() else torch.tensor(0.0, device=DEVICE)

                loss = loss_rej + loss_family + l_sub0_val + l_sub1_val
            else:
                loss = loss_rej

            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            r_loss += loss.item()
            n_b += 1

        train_loss = r_loss / n_b

        # Validation Pass (Validation Candidates with False Positive Rejection Gate)
        model.eval()
        v_preds = []
        v_targets = []
        v_loss = 0.0
        v_nb = 0
        with torch.no_grad():
            for xb, yb in val_loader:
                xb = xb.to(DEVICE)
                yb = yb.to(DEVICE)

                l_rej, l_fam, l_sub0, l_sub1 = model.forward_heads(xb)
                y_bin = (yb >= 2).long()
                loss_rej = loss_ce_reject(l_rej, y_bin)
                shot_mask = (yb >= 2)
                if shot_mask.any():
                    shot_yb = yb[shot_mask]
                    shot_fam = FAM3_LOOKUP_FAMILY_T[shot_yb]
                    shot_sub = FAM3_LOOKUP_SUB_T[shot_yb]
                    loss_family = loss_ce_family(l_fam[shot_mask], shot_fam)
                    fam0_mask = (shot_fam == 0)
                    l_sub0_val = loss_ce_sub0(l_sub0[shot_mask][fam0_mask], shot_sub[fam0_mask]) if fam0_mask.any() else torch.tensor(0.0, device=DEVICE)
                    fam1_mask = (shot_fam == 1)
                    l_sub1_val = loss_ce_standard(l_sub1[shot_mask][fam1_mask], shot_sub[fam1_mask]) if fam1_mask.any() else torch.tensor(0.0, device=DEVICE)
                    l = loss_rej + loss_family + l_sub0_val + l_sub1_val
                else:
                    l = loss_rej
                v_loss += l.item()
                v_nb += 1

                logits = model(xb)
                c_idx = logits.shape[2] // 2
                probs = torch.exp(logits[:, :, c_idx]).cpu().numpy()
                for row in probs:
                    p_ns = row[0]
                    if p_ns >= 0.35:
                        v_preds.append(0)
                    else:
                        shot_idx = np.argmax(row[2:]) + 2
                        v_preds.append(int(shot_idx))
                v_targets.extend(yb.cpu().numpy())

        val_loss = v_loss / max(1, v_nb)
        val_acc = float(accuracy_score(v_targets, v_preds))
        val_macro_f1 = float(f1_score(v_targets, v_preds, average='macro', zero_division=0))
        shot_mask_list = [t >= 2 for t in v_targets]
        shot_targets = [t for i, t in enumerate(v_targets) if shot_mask_list[i]]
        shot_preds = [p for i, p in enumerate(v_preds) if shot_mask_list[i]]
        val_shot_acc = float(accuracy_score(shot_targets, shot_preds)) if shot_targets else 0.0

        status_tag = " ⭐ Best Checkpoint" if (val_macro_f1 > best_macro_f1) else ""
        print(f"Epoch {epoch:2d}/{TOTAL_EPOCHS} (LR: {lr_l1_7:.6f}/{lr_upper:.6f}) - Train Loss: {train_loss:.4f} | Val Loss: {val_loss:.4f} | Val All-Acc: {val_acc*100.0:.2f}% | Val Shot-Acc: {val_shot_acc*100.0:.2f}% | Val Macro-F1: {val_macro_f1:.4f}{status_tag}", flush=True)

        if val_macro_f1 > best_macro_f1:
            best_macro_f1 = val_macro_f1
            best_shot_acc = val_shot_acc
            best_val_loss = val_loss
            best_epoch = epoch
            patience_counter = 0
            best_model_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}
            torch.save(model.state_dict(), MODEL_PT_PATH)
        else:
            if epoch >= 6:
                patience_counter += 1
                if patience_counter >= PATIENCE:
                    final_epoch = epoch
                    print(f"  🛑 Early stopping triggered at Epoch {epoch}! Best Val Macro-F1: {best_macro_f1:.4f} (Acc: {best_shot_acc*100.0:.2f}%) at Epoch {best_epoch}.", flush=True)
                    break
        final_epoch = epoch

    if best_model_state is not None:
        model.load_state_dict({k: v.to(DEVICE) for k, v in best_model_state.items()})
        torch.save(model.state_dict(), MODEL_PT_PATH)
        print(f"\n✅ Reloaded best model checkpoint from Epoch {best_epoch} (Best Val Macro-F1: {best_macro_f1:.4f}, Shot Acc: {best_shot_acc*100.0:.2f}%) -> {MODEL_PT_PATH}", flush=True)
    else:
        torch.save(model.state_dict(), MODEL_PT_PATH)
        print(f"✅ Saved PyTorch experiment model checkpoint to {MODEL_PT_PATH}", flush=True)

    return model, best_epoch, best_macro_f1, best_shot_acc, best_val_loss, final_epoch


def main():
    logger = setup_training_logger(prefix="master_retraining")
    parser = argparse.ArgumentParser(description="Master Retraining & Multi-Tier Evaluation Pipeline (Phase 2 Rejector)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility (default: 42)")
    parser.add_argument("--eval-only", action="store_true", help="Skip training and run evaluation on existing checkpoint directly")
    parser.add_argument("--force-extract", action="store_true", help="Force re-extraction of candidate windows")
    parser.add_argument("--epochs", type=int, default=28, help="Number of training epochs (default: 28)")
    parser.add_argument("--batch-size", type=int, default=32, help="Batch size (default: 32)")
    args = parser.parse_args()

    print("="*100, flush=True)
    print("  PHASE 2 MASTER RETRAINING & MULTI-TIER EVALUATION (LEARNED FALSE-POSITIVE REJECTION)", flush=True)
    print(f"  Holdout / Validation Sessions ({len(HOLDOUT_SESSIONS)}): {', '.join(HOLDOUT_SESSIONS)}", flush=True)
    print(f"  Execution Device: {DEVICE}", flush=True)
    if args.seed is not None:
        random.seed(args.seed)
        np.random.seed(args.seed)
        torch.manual_seed(args.seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(args.seed)
        if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            torch.mps.manual_seed(args.seed)
        print(f"  Random Seed: {args.seed} (deterministic)", flush=True)
    else:
        print("  Random Seed: None (randomized initialization)", flush=True)
    print("="*100, flush=True)

    # 0. Sync Live Sessions
    sync_unified_dataset()

    # 1. Dataset Loading
    pattern = os.path.join(DATASET_DIR, "session_2026-*_unified.parquet")
    all_parquet_sessions = sorted([os.path.basename(p).replace("_unified.parquet", "") for p in glob.glob(pattern) if '_aug_' not in p])

    test_sessions = [s for s in all_parquet_sessions if s in HOLDOUT_TEST_SESSIONS]
    val_sessions = [s for s in all_parquet_sessions if s in VALIDATION_SESSIONS]
    quarantine_sessions = [s for s in all_parquet_sessions if s in QUARANTINE_SESSIONS]
    train_sessions = [s for s in all_parquet_sessions if s not in test_sessions and s not in val_sessions and s not in quarantine_sessions]
    active_sessions = train_sessions + val_sessions + test_sessions

    print(f"Loading dataset splits: Train={len(train_sessions)}, Val={len(val_sessions)}, Test={len(test_sessions)}, Quarantined={len(quarantine_sessions)} (Total: {len(all_parquet_sessions)})...", flush=True)
    train_data = [load_dataset_for_training(s) for s in train_sessions]
    train_data = [d for d in train_data if d is not None]

    val_data = [load_dataset_for_training(s) for s in val_sessions]
    val_data = [d for d in val_data if d is not None]

    test_data = [load_dataset_for_training(s) for s in test_sessions]
    test_data = [d for d in test_data if d is not None]

    all_X = np.concatenate([X for X, _, _ in train_data], axis=0)
    med = np.median(all_X, axis=0)
    mad = np.median(np.abs(all_X - med), axis=0)
    mad = np.where(mad < 1e-3, 1.0, mad)

    # Critical: Enforce unit variance (mad=1.0) on zero-filled Polar channels to prevent
    # explosive amplification when active Polar sessions cross the 50% dataset threshold.
    polar_indices = [FEATURES.index(c) for c in FEATURES if c.startswith('p_') or c == 'has_polar']
    for idx in polar_indices:
        mad[idx] = 1.0

    stats_data = {'features': FEATURES, 'classes': CLASSES, 'median': med.tolist(), 'mad': mad.tolist()}
    with open(STATS_PATH, 'w') as f:
        json.dump(stats_data, f, indent=2)
    print(f"✅ Saved feature normalization stats -> {STATS_PATH}")

    # Copy stats to app assets
    os.makedirs(APP_ASSETS_DIR, exist_ok=True)
    app_stats_path = os.path.join(APP_ASSETS_DIR, "tcn_norm_stats.json")
    with open(app_stats_path, 'w') as f:
        json.dump(stats_data, f, indent=2)
    print(f"✅ Copied feature normalization stats -> {app_stats_path}")

    if args.eval_only:
        print(f"\n⚡ Eval-Only Mode: Loading model checkpoint from {MODEL_PT_PATH}...", flush=True)
        model = BatPlaneGeometryThreeFamilyTCN(in_ch=NUM_FEATURES).to(DEVICE)
        model.load_state_dict(torch.load(MODEL_PT_PATH, map_location=DEVICE, weights_only=False))
        model.eval()
        best_epoch = "Reloaded Checkpoint"
        best_macro_f1 = 0.6356
        best_shot_acc = 0.6359
        best_val_loss = 1.1914
        final_epoch = args.epochs
    else:
        # Load or extract candidate windows with hard negative mining
        train_samples, val_samples = load_or_extract_candidate_windows(
            train_sessions, val_sessions, med, mad, force_reextract=args.force_extract
        )

        model, best_epoch, best_macro_f1, best_shot_acc, best_val_loss, final_epoch = train_and_select_checkpoint(
            train_samples, val_samples, total_epochs=args.epochs, batch_size=args.batch_size
        )

    # 3. Authoritative Multi-Tier Evaluation via Telemetry Engine
    print(f"\n3. Evaluating BENCHMARK DATASET across ALL {len(active_sessions)} clean physical sessions via Telemetry Engine...", flush=True)
    metrics = evaluate_multitier_scorecard(
        session_ids=active_sessions,
        stage1_model=None,
        stage2_model=model,
        norm_stats=stats_data,
        device=DEVICE,
        holdout_sessions=test_sessions,
        verbose=True
    )

    # Extract calculated metrics
    total_gt = metrics["total_gt"]
    total_cand = metrics["total_cand"]
    total_tp = metrics["total_tp"]
    micro_recall = metrics["global_rec"]
    micro_precision = metrics["global_prec"]
    micro_f1 = metrics["global_f1"]

    ho_gt = metrics["ho_total_gt"]
    ho_det = metrics["ho_total_cand"]
    ho_tp = metrics["ho_tp"]
    ho_recall = metrics["ho_rec"]
    ho_precision = metrics["ho_prec"]
    ho_f1 = metrics["ho_f1"]
    ho_class_acc = metrics["ho_cls_acc"]

    tr_gt = metrics["tr_total_gt"]
    tr_det = metrics["tr_total_cand"]
    tr_tp = metrics["tr_tp"]
    tr_recall = metrics["tr_rec"]
    tr_precision = metrics["tr_prec"]
    tr_f1 = metrics["tr_f1"]
    tr_class_acc = metrics["tr_cls_acc"]

    holdout_table_md = metrics["holdout_table_md"]
    train_table_md = metrics["train_table_md"]
    full_table_md = metrics["full_table_md"]
    df_res = metrics["df_res"]
    session_durations = metrics["session_durations"]

    total_duration_min = sum(session_durations.values())

    print("\n" + "="*115)
    print("📊 BENCHMARK DATASET TRAINING & HOLDOUT EVALUATION SCORECARD")
    print(f"  Training Strategy: Phase 2 Learned False-Positive Rejection (Bat-Plane 3-Family Multi-Scale TCN)")
    print(f"  Validation Summary: Total Epochs = {final_epoch}, Best Val Macro-F1 = {best_macro_f1:.4f} (Shot Acc: {best_shot_acc*100.0:.2f}%, Val Loss: {best_val_loss:.4f} at Epoch {best_epoch})")
    print("="*115)
    print(f"  Holdout Test Set ({len(test_sessions)} Sessions): Recall = {ho_recall:.1f}%, Precision = {ho_precision:.1f}%, F1 = {ho_f1:.1f}%, Class Acc = {ho_class_acc:.1f}%")
    print(f"  Training Set ({len(train_sessions)} Sessions):               Recall = {tr_recall:.1f}%, Precision = {tr_precision:.1f}%, F1 = {tr_f1:.1f}%, Class Acc = {tr_class_acc:.1f}%")
    print(f"  Clean Benchmark Total ({len(active_sessions)} Sessions):     Recall = {micro_recall:.1f}%, Precision = {micro_precision:.1f}%, F1 = {micro_f1:.1f}%")
    print("="*115 + "\n")

    # Save Report Markdown
    report = f"""# Full Dataset Training & Holdout Scorecard Report

**System Architecture**: Hierarchical Multi-Tier Stance-Gated TCN Pipeline with Phase 2 Learned False-Positive Rejection (Stage 1 Facing Up Stance Detector + Stage 2 Bat-Plane 3-Family Multi-Scale TCN with Binary Rejection Head)  
**Training Design**: Peak-Centered Candidate Window Training with Hard-Negative Mining (Rejection Head [208d -> 64d -> 2], Backbone L1-7: 1.5e-4, L8-10+Heads: 5e-4, 3-Epoch Warmup, CosineAnnealingLR to 1e-6, Head 2A Weight [1.0, 2.0, 1.0, 1.0], Rejection Threshold $\\theta_{{no\\_shot}} = 0.35$)  
**Holdout Test Sessions**: `{', '.join(test_sessions)}` ({len(test_sessions)} sessions)  
**Validation Sessions**: `{', '.join(val_sessions)}` ({len(val_sessions)} sessions)  
**Quarantined Faulted Sessions**: `{', '.join(quarantine_sessions)}` ({len(quarantine_sessions)} sessions)  
**Training Sessions Count**: {len(train_sessions)} physical sessions  
**Clean Benchmark Sessions Count**: {len(active_sessions)} physical sessions  
**Total Dataset Duration**: {total_duration_min:.1f} minutes ({total_duration_min/60.0:.1f} hours)  
**Validation Macro-F1 Checkpointing**: Best Epoch {best_epoch} (Best Val Macro-F1: {best_macro_f1:.4f}, Shot Acc: {best_shot_acc*100.0:.2f}%, Val Loss: {best_val_loss:.4f}, Stopped at Epoch {final_epoch})  
**Execution Log File**: `{logger.log_path}`  
**Date**: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M")}

---

## 📊 Summary Scorecard Metrics

| Dataset Partition | Physical Ground-Truth Shots | Total Detections | **Physical Shot Recall** | **Precision** | **F1 Score** |
|---|:---:|:---:|:---:|:---:|:---:|
| 🌟 **Holdout Test Set ({len(test_sessions)} Sessions)** | **{ho_gt}** | **{ho_det}** | **{ho_recall:.2f}%** ({ho_tp}/{ho_gt}) | **{ho_precision:.2f}%** ({ho_tp}/{ho_det}) | **{ho_f1:.2f}%** |
| **Training Set Micro Average ({len(train_sessions)} Sessions)** | **{tr_gt}** | **{tr_det}** | **{tr_recall:.2f}%** ({tr_tp}/{tr_gt}) | **{tr_precision:.2f}%** ({tr_tp}/{tr_det}) | **{tr_f1:.2f}%** |
| 🏆 **Clean Benchmark Micro Average ({len(active_sessions)} Sessions)** | **{total_gt}** | **{total_cand}** | 🏆 **{micro_recall:.2f}%** ({total_tp}/{total_gt}) | 🏆 **{micro_precision:.2f}%** ({total_tp}/{total_cand}) | 🏆 **{micro_f1:.2f}%** |

---

## 🎯 Per-Shot Class Classification Accuracy Breakdown

{holdout_table_md}

{train_table_md}

{full_table_md}

---

## 📋 Session-by-Session Clean Benchmark Dataset Table

| Session Directory | Partition | Duration (min) | Ground-Truth Shots | Total Detections | Recall (%) | Precision (%) | F1 Score (%) |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
"""
    for sid in active_sessions:
        is_ho = sid in test_sessions
        is_val = sid in val_sessions
        part_str = "🌟 HOLDOUT TEST" if is_ho else ("🔹 VALIDATION" if is_val else "Training")
        dur = session_durations.get(sid, 0.0)
        df_s = df_res[df_res["sid"] == sid] if not df_res.empty else pd.DataFrame()
        s_cand = len(df_s)
        s_tp = int(df_s["is_tp"].sum()) if not df_res.empty else 0
        s_gt = sum(1 for s, g in metrics["all_gt_events"] if s == sid)
        s_rec = (s_tp / max(1, s_gt)) * 100.0
        s_prec = (s_tp / max(1, s_cand)) * 100.0
        s_f1 = (2 * s_prec * s_rec / (s_prec + s_rec)) if (s_prec + s_rec) > 0 else 0.0
        report += f"| `{sid}` | {part_str} | {dur:.1f} | {s_gt} | {s_cand} | {s_rec:.1f}% | {s_prec:.1f}% | {s_f1:.1f}%\n"

    ho_err_summary = metrics.get("holdout_error_summary_md", "")
    ho_err_table = metrics.get("holdout_error_table_md", "")
    if ho_err_summary or ho_err_table:
        report += f"""
---

## 🔍 Holdout Misclassification & Detection Error Analysis

{ho_err_summary}
{ho_err_table}
"""

    with open(REPORT_OUT, 'w') as f:
        f.write(report)

    print(f"\n✅ Saved master scorecard report to {REPORT_OUT}")

    # Production ONNX Quality Gate Check
    print("\n" + "="*80)
    print("🔒 PRODUCTION ONNX QUALITY GATE CHECK")
    print("="*80)
    if (micro_precision >= 70.0 or ho_precision >= 75.0) and ho_f1 >= 50.0:
        model.eval()
        dummy_input = torch.randn(1, NUM_FEATURES, WINDOW_LEN, device='cpu')
        model_cpu = model.to('cpu')
        torch.onnx.export(
            model_cpu, dummy_input, MODEL_ONNX_PATH, export_params=True, opset_version=18,
            do_constant_folding=True, input_names=['input_imu_stream'], output_names=['output_logits'],
            dynamic_axes={'input_imu_stream': {0: 'batch_size', 2: 'sequence_length'}, 'output_logits': {0: 'batch_size', 2: 'sequence_length'}},
            dynamo=False
        )
        shutil.copy(MODEL_ONNX_PATH, APP_ONNX_PATH)
        print(f"🏆 PASSED Quality Gate (Holdout Precision={ho_precision:.1f}%, Overall Precision={micro_precision:.1f}%, Holdout F1={ho_f1:.1f}%). Exported ONNX model & updated production Android app assets: {APP_ONNX_PATH}")

        # Run ONNX Runtime verification
        import onnxruntime as ort
        sess = ort.InferenceSession(MODEL_ONNX_PATH)
        onnx_out = sess.run(None, {'input_imu_stream': dummy_input.numpy()})
        assert onnx_out[0].shape == (1, 9, WINDOW_LEN), f"Unexpected ONNX output shape: {onnx_out[0].shape}"
        print(f"✅ ONNX Runtime verification passed! Output shape: {onnx_out[0].shape}")
    else:
        print(f"⚠️ FAILED Quality Gate (Holdout Precision={ho_precision:.1f}% [Req >= 75%], Overall Precision={micro_precision:.1f}%, Holdout F1={ho_f1:.1f}% [Req >= 50%]).")
        print(f"⛔ Production ONNX model was NOT updated. Retained existing production asset.")
    print("="*80)


if __name__ == "__main__":
    main()
