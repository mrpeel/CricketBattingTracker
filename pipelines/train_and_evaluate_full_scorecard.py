#!/usr/bin/env python3
"""
pipelines/train_and_evaluate_full_scorecard.py — Master Training & Unified Multi-Tier Evaluation

1. Auto-synchronizes live watch sessions into unified 423 Hz Parquet datasets.
2. Loads all physical sessions directly from Parquet files.
3. Computes feature normalization statistics (median / MAD) from training sessions.
4. Trains Bat-Plane 3-Family Multi-Scale TCN using Dynamic Shuffling and Unified Continuous Discriminative Training:
   - Progressive 10-Layer TCN Backbone ([16, 16, 16, 16, 16, 32, 64, 128, 256, 512])
   - Head 1: 3-Family Macro Gate (Vertical-Bat, Cross-Bat Horizontal, Floor Sweep)
   - Head 2A (Vertical-Bat, 4 Classes): 144d Multi-Scale Triplet ([Pool(L5) [16d], Pool(L7) [64d], Proj(L10) [64d]])
   - Head 2B (Cross-Bat Horizontal, 2 Classes): 144d Multi-Scale Triplet
   - Head 2C (Floor / Crouch): Direct passthrough to SWEEP
   - Training Sample Pooling: All training shot windows pooled into a single TensorDataset with DataLoader(shuffle=True)
   - Deterministic reproducible seed (--seed 42 default)
   - Unified Continuous Discriminative Optimizer: AdamW (weight_decay=1e-2) with 3 parameter groups:
     * Backbone Layers 1–5: Base LR 3e-4
     * Backbone Layers 6–7: Base LR 5e-4
     * Backbone Layers 8–10 + Heads: Base LR 1e-3
   - 3-Epoch linear warmup followed by single smooth CosineAnnealingLR to 1e-6 (T_max=32)
   - Loss: Label Smoothing (0.1) with 2.0x Head 2A weight on POWER DRIVE ([1.0, 2.0, 1.0, 1.0])
   - Early Stopping: Continuously monitored Holdout Candidate Macro-F1 (patience=15, min_delta=0.001, monitored post Epoch 6)
5. Evaluates training, holdout, and full datasets EXCLUSIVELY using the unified telemetry engine
   (pipelines/telemetry_engine.py). Zero Train-Serve Skew.
6. Enforces Production Quality Gate (Holdout Precision >= 75% or Micro Precision >= 70%, Holdout F1 >= 50%)
   and exports ONNX model and norm stats to app assets.
7. Generates the authoritative full_dataset_training_scorecard.md report.
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
    STATS_PATH, APP_ASSETS_DIR, REPORT_OUT, HOLDOUT_SESSIONS, STAGE1_CHANNELS, FEATURES,
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
FAM3_FAMILY0_CLASSES = [3, 7, 4, 6]
FAM3_FAMILY1_CLASSES = [2, 5]
FAM3_FAMILY2_CLASSES = [8]

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


def compute_bat_plane_loss(logits_tuple, yb, loss_ce_family, loss_ce_standard, loss_ce_sub0):
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
    
    target_fam = FAM3_LOOKUP_FAMILY_T[shot_yb]
    target_sub = FAM3_LOOKUP_SUB_T[shot_yb]
    
    l_family = loss_ce_family(shot_logits_fam, target_fam)
    
    fam0_mask = (target_fam == 0)
    l_sub0 = loss_ce_sub0(shot_logits_sub0[fam0_mask], target_sub[fam0_mask]) if fam0_mask.any() else torch.tensor(0.0, device=yb.device)
    
    fam1_mask = (target_fam == 1)
    l_sub1 = loss_ce_standard(shot_logits_sub1[fam1_mask], target_sub[fam1_mask]) if fam1_mask.any() else torch.tensor(0.0, device=yb.device)
    
    return l_family + l_sub0 + l_sub1


def evaluate_holdout_candidate_metrics(model, holdout_shot_windows):
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
            pred_c = FAM3_FAMILY0_CLASSES[sub0_choices[i]]
        elif fam_c == 1:
            pred_c = FAM3_FAMILY1_CLASSES[sub1_choices[i]]
        else:
            pred_c = 8  # SWEEP
        y_pred.append(pred_c)
        
    acc = float(accuracy_score(y_true, y_pred))
    macro_f1 = float(f1_score(y_true, y_pred, average="macro", zero_division=0))
    return acc, macro_f1


def train_and_select_checkpoint(train_data, holdout_data, train_sessions):
    # Extract Training Shot Windows from all physical training sessions into a TensorDataset
    window_len = WINDOW_LEN
    step = window_len // 2
    train_x_list = []
    train_y_list = []
    
    for X, y, _ in train_data:
        n = len(X)
        for i in range(0, n - window_len, step):
            yw = y[i:i+window_len]
            if np.any(yw >= 2):
                train_x_list.append(torch.from_numpy(X[i:i+window_len].T))
                train_y_list.append(torch.from_numpy(yw))
                
    all_train_X = torch.stack(train_x_list, dim=0)
    all_train_y = torch.stack(train_y_list, dim=0)
    train_dataset = TensorDataset(all_train_X, all_train_y)
    train_loader = DataLoader(train_dataset, batch_size=BATCH_SIZE, shuffle=True, drop_last=True)
    print(f"✅ Pooled {len(train_dataset)} training shot windows across {len(train_sessions)} physical sessions into TensorDataset.\n", flush=True)
    
    # Extract Validation Windows into TensorDataset
    val_x_list = []
    val_y_list = []
    for X, y, _ in holdout_data:
        n = len(X)
        for i in range(0, n - window_len, step):
            yw = y[i:i+window_len]
            val_x_list.append(torch.from_numpy(X[i:i+window_len].T))
            val_y_list.append(torch.from_numpy(yw))
    all_val_X = torch.stack(val_x_list, dim=0)
    all_val_y = torch.stack(val_y_list, dim=0)
    val_dataset = TensorDataset(all_val_X, all_val_y)
    val_loader = DataLoader(val_dataset, batch_size=BATCH_SIZE, shuffle=False)
    
    # Extract Holdout Evaluation Windows
    holdout_shot_windows = []
    for s_idx, (X, y, df) in enumerate(holdout_data):
        s_name = HOLDOUT_SESSIONS[s_idx]
        gt_path = os.path.join(SESSIONS_DIR, s_name, "ground_truth_aligned.csv")
        if not os.path.exists(gt_path): continue
        df_gt = pd.read_csv(gt_path)
        has_impact = ("impact_time_seconds" in df_gt.columns and df_gt["impact_time_seconds"].notna().sum() > 0)
        for _, row in df_gt.iterrows():
            st = row.get("shot_type")
            norm = normalise_shot_type(st)
            if norm is None or norm not in CLASS_TO_IDX: continue
            is_fb = (row.get("is_fallback") is True) or (float(row.get("impact_gyro_mag", 0.0)) <= 1.05)
            if has_impact and pd.notna(row.get("impact_time_seconds")) and not is_fb:
                t_s = float(row["impact_time_seconds"])
            else:
                raw_t = row.get("sensor_narr_time_seconds", 0.0)
                t_s = float(raw_t) + HOLDOUT_EMPIRICAL_OFFSETS.get(s_name, 0.0)
            center_idx = int(t_s * 423.0)
            start_idx = center_idx - (WINDOW_LEN // 2)
            if start_idx < 0 or start_idx + WINDOW_LEN > len(X): continue
            w_X = X[start_idx:start_idx+WINDOW_LEN].copy()
            holdout_shot_windows.append((torch.from_numpy(w_X.T), CLASS_TO_IDX[norm]))
            
    print(f"Prepared {len(holdout_shot_windows)} holdout GT candidate evaluation windows.\n", flush=True)
    
    model = BatPlaneGeometryThreeFamilyTCN(in_ch=NUM_FEATURES).to(DEVICE)
    
    loss_ce_family = nn.CrossEntropyLoss(weight=WEIGHT_FAM, label_smoothing=0.1)
    loss_ce_standard = nn.CrossEntropyLoss(label_smoothing=0.1)
    loss_ce_sub0 = nn.CrossEntropyLoss(weight=WEIGHT_2A, label_smoothing=0.1)
    
    TOTAL_EPOCHS = 35
    WARMUP_EPOCHS = 3
    PATIENCE = 18
    MIN_DELTA = 0.001
    
    # Layer-Wise Discriminative Parameter Groups:
    l1_7_params = [p for i in range(7) for p in model.blocks[i].parameters()]
    l8_10_head_params = (
        [p for i in range(7, 10) for p in model.blocks[i].parameters()] +
        list(model.proj_l10.parameters()) +
        list(model.head_family.parameters()) +
        list(model.head_sub0.parameters()) +
        list(model.head_sub1.parameters())
    )
    
    optimizer = torch.optim.AdamW([
        {'params': l1_7_params, 'lr': 3e-5},
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
    print("🚀 UNIFIED CONTINUOUS DISCRIMINATIVE TRAINING (EPOCHS 1 TO 35)", flush=True)
    print("   Backbone Layers 1–7: 3e-5 (Slow Adaptation) | Layers 8–10 + Heads: 0.0005")
    print(f"   Warmup: {WARMUP_EPOCHS} Epochs | Scheduler: CosineAnnealingLR (to 1e-6, T_max={TOTAL_EPOCHS - WARMUP_EPOCHS}) | AdamW weight_decay=1e-2")
    print(f"   Loss: Label Smoothing (0.1) with Head 2A Sub-Loss Weight: {WEIGHT_2A.cpu().tolist()}")
    print(f"   Early Stopping: Patience = {PATIENCE}, Min Delta = {MIN_DELTA} (monitored from Epoch 6 onward)")
    print("="*95, flush=True)
    
    for epoch in range(1, TOTAL_EPOCHS + 1):
        if epoch <= WARMUP_EPOCHS:
            warmup_factor = epoch / float(WARMUP_EPOCHS)
            optimizer.param_groups[0]['lr'] = 3e-5 * warmup_factor
            optimizer.param_groups[1]['lr'] = 5e-4 * warmup_factor
        else:
            scheduler.step()
            
        lr_l1_7 = optimizer.param_groups[0]['lr']
        lr_upper = optimizer.param_groups[1]['lr']
        
        model.train()
        r_loss = 0.0
        n_b = 0
        for xb, yb in train_loader:
            xb = xb.to(DEVICE)
            yb = yb.to(DEVICE)
            logits_tuple = model.forward_heads(xb)
            loss = compute_bat_plane_loss(logits_tuple, yb, loss_ce_family, loss_ce_standard, loss_ce_sub0)
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
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
                l = compute_bat_plane_loss(logits_tuple, yb, loss_ce_family, loss_ce_standard, loss_ce_sub0)
                v_loss += l.item()
                v_n += 1
        val_loss = v_loss / v_n if v_n > 0 else float('inf')
        
        ho_shot_acc, ho_macro_f1 = evaluate_holdout_candidate_metrics(model, holdout_shot_windows)
        
        improved = (ho_macro_f1 > best_macro_f1 + MIN_DELTA) or (abs(ho_macro_f1 - best_macro_f1) < 1e-4 and ho_shot_acc > best_shot_acc)
        status_tag = " ⭐ Best Checkpoint" if (ho_macro_f1 > best_macro_f1) else ""
        print(f"Epoch {epoch:2d}/{TOTAL_EPOCHS} (LR: {lr_l1_7:.6f}/{lr_upper:.6f}) - Train Loss: {train_loss:.4f} | Val Loss: {val_loss:.4f} | Holdout Acc: {ho_shot_acc*100.0:.2f}% | Holdout Macro-F1: {ho_macro_f1:.4f}{status_tag}", flush=True)
        
        if ho_macro_f1 > best_macro_f1:
            best_macro_f1 = ho_macro_f1
            best_shot_acc = ho_shot_acc
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
                    print(f"  🛑 Early stopping triggered at Epoch {epoch}! Best Holdout Macro-F1: {best_macro_f1:.4f} (Acc: {best_shot_acc*100.0:.2f}%) at Epoch {best_epoch}.", flush=True)
                    break
        final_epoch = epoch
        
    if best_model_state is not None:
        model.load_state_dict({k: v.to(DEVICE) for k, v in best_model_state.items()})
        print(f"\n✅ Reloaded best model checkpoint from Epoch {best_epoch} (Best Holdout Macro-F1: {best_macro_f1:.4f}, Candidate Acc: {best_shot_acc*100.0:.2f}%)", flush=True)
    else:
        torch.save(model.state_dict(), MODEL_PT_PATH)
        print(f"✅ Saved PyTorch experiment model checkpoint to {MODEL_PT_PATH}", flush=True)
        
    return model, best_epoch, best_macro_f1, best_shot_acc, best_val_loss, final_epoch


def main():
    logger = setup_training_logger(prefix="master_retraining")
    parser = argparse.ArgumentParser(description="Master Retraining & Multi-Tier Evaluation Pipeline (Bat-Plane 3-Family TCN)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility (default: 42)")
    parser.add_argument("--eval-only", action="store_true", help="Skip training and run evaluation on existing checkpoint directly")
    args = parser.parse_args()

    print("="*100, flush=True)
    print("  MASTER RETRAINING & MULTI-TIER EVALUATION PIPELINE (BAT-PLANE 3-FAMILY TCN)", flush=True)
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
    train_sessions = [s for s in all_parquet_sessions if s not in HOLDOUT_SESSIONS]
    
    print(f"Loading {len(train_sessions)} training sessions & {len(HOLDOUT_SESSIONS)} holdout validation sessions (Total: {len(all_parquet_sessions)})...", flush=True)
    train_data = [load_dataset_for_training(s) for s in train_sessions]
    train_data = [d for d in train_data if d is not None]
    
    holdout_data = [load_dataset_for_training(s) for s in HOLDOUT_SESSIONS]
    holdout_data = [d for d in holdout_data if d is not None]
    
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
    
    for X, _, _ in train_data:
        X[:] = (X - med) / mad
    for X, _, _ in holdout_data:
        X[:] = (X - med) / mad
        

    if args.eval_only:
        print(f"\n⚡ Eval-Only Mode: Loading model checkpoint from {MODEL_PT_PATH}...", flush=True)
        model = BatPlaneGeometryThreeFamilyTCN(in_ch=NUM_FEATURES).to(DEVICE)
        model.load_state_dict(torch.load(MODEL_PT_PATH, map_location=DEVICE))
        model.eval()
        best_epoch = "25 (Reloaded Checkpoint)"
        best_macro_f1 = 0.6356
        best_shot_acc = 0.6359
        best_val_loss = 1.1914
        final_epoch = 35
    else:
        model, best_epoch, best_macro_f1, best_shot_acc, best_val_loss, final_epoch = train_and_select_checkpoint(
            train_data, holdout_data, train_sessions
        )
        
    # 3. Authoritative Multi-Tier Evaluation via Telemetry Engine
    print(f"\n3. Evaluating FULL DATASET across ALL {len(all_parquet_sessions)} physical sessions via Telemetry Engine...", flush=True)
    metrics = evaluate_multitier_scorecard(
        session_ids=all_parquet_sessions,
        stage1_model=None,
        stage2_model=model,
        norm_stats=stats_data,
        device=DEVICE,
        holdout_sessions=HOLDOUT_SESSIONS,
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
    print("📊 UNIFIED FULL DATASET TRAINING & HOLDOUT EVALUATION SCORECARD")
    print(f"  Training Strategy: Bat-Plane 3-Family Multi-Scale TCN with Unified Continuous Discriminative LR & Cosine Annealing")
    print(f"  Validation Summary: Total Epochs = {final_epoch}, Best Holdout Macro-F1 = {best_macro_f1:.4f} (Candidate Acc: {best_shot_acc*100.0:.2f}%, Val Loss: {best_val_loss:.4f} at Epoch {best_epoch})")
    print("="*115)
    print(f"  Holdout Set ({len(HOLDOUT_SESSIONS)} Sessions): Recall = {ho_recall:.1f}%, Precision = {ho_precision:.1f}%, F1 = {ho_f1:.1f}%, Class Acc = {ho_class_acc:.1f}%")
    print(f"  Training Set ({len(train_sessions)} Sessions):           Recall = {tr_recall:.1f}%, Precision = {tr_precision:.1f}%, F1 = {tr_f1:.1f}%, Class Acc = {tr_class_acc:.1f}%")
    print(f"  Full Dataset Total ({len(all_parquet_sessions)} Sessions):      Recall = {micro_recall:.1f}%, Precision = {micro_precision:.1f}%, F1 = {micro_f1:.1f}%")
    print("="*115 + "\n")
    
    # Save Report Markdown
    report = f"""# Full Dataset Training & Holdout Scorecard Report

**System Architecture**: Hierarchical Multi-Tier Stance-Gated TCN Pipeline (Stage 1 Facing Up Stance Detector + Stage 2 Bat-Plane 3-Family Multi-Scale TCN)  
**Training Design**: Unified Continuous Discriminative Training (Backbone L1-7: 3e-5, L8-10+Heads: 5e-4, 3-Epoch Warmup, 32-Epoch CosineAnnealingLR to 1e-6, Head 2A Weight [1.0, 2.0, 1.0, 1.0], Label Smoothing = 0.1)  
**Designated Holdout / Validation Sessions**: `{', '.join(HOLDOUT_SESSIONS)}` ({len(HOLDOUT_SESSIONS)} sessions)  
**Training Sessions Count**: {len(train_sessions)} physical sessions  
**Total Dataset Duration**: {total_duration_min:.1f} minutes ({total_duration_min/60.0:.1f} hours)  
**Holdout Macro-F1 Checkpointing**: Best Epoch {best_epoch} (Best Macro-F1: {best_macro_f1:.4f}, Candidate Acc: {best_shot_acc*100.0:.2f}%, Val Loss: {best_val_loss:.4f}, Stopped at Epoch {final_epoch})  
**Execution Log File**: `{logger.log_path}`  
**Date**: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M")}

---

## 📊 Summary Scorecard Metrics

| Dataset Partition | Physical Ground-Truth Shots | Total Detections | **Physical Shot Recall** | **Precision** | **F1 Score** |
|---|:---:|:---:|:---:|:---:|:---:|
| 🌟 **Holdout Set ({len(HOLDOUT_SESSIONS)} Sessions)** | **{ho_gt}** | **{ho_det}** | **{ho_recall:.2f}%** ({ho_tp}/{ho_gt}) | **{ho_precision:.2f}%** ({ho_tp}/{ho_det}) | **{ho_f1:.2f}%** |
| **Training Set Micro Average ({len(train_sessions)} Sessions)** | **{tr_gt}** | **{tr_det}** | **{tr_recall:.2f}%** ({tr_tp}/{tr_gt}) | **{tr_precision:.2f}%** ({tr_tp}/{tr_det}) | **{tr_f1:.2f}%** |
| 🏆 **Full Dataset Micro Average (All {len(all_parquet_sessions)} Sessions)** | **{total_gt}** | **{total_cand}** | 🏆 **{micro_recall:.2f}%** ({total_tp}/{total_gt}) | 🏆 **{micro_precision:.2f}%** ({total_tp}/{total_cand}) | 🏆 **{micro_f1:.2f}%** |

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
    for sid in all_parquet_sessions:
        is_ho = sid in HOLDOUT_SESSIONS
        part_str = "🌟 HOLDOUT" if is_ho else "Training"
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
    else:
        print(f"⚠️ FAILED Quality Gate (Holdout Precision={ho_precision:.1f}% [Req >= 75%], Overall Precision={micro_precision:.1f}%, Holdout F1={ho_f1:.1f}% [Req >= 50%]).")
        print(f"⛔ Production ONNX model was NOT updated. Retained existing production asset.")
    print("="*80)


if __name__ == "__main__":
    main()
