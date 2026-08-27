#!/usr/bin/env python3
"""
pipelines/run_dimension_balanced_experiment.py — Dimension-Balanced Multi-Scale Triplet 3-Family Hierarchical TCN

Resolves the SLOG vs. POWER DRIVE trade-off via:
  1. Progressive 10-Layer TCN Backbone: [16, 16, 16, 16, 16, 32, 64, 128, 256, 512]
  2. Dimension-Balanced Multi-Scale Feature Projection on Head 2B:
     - f_l5 = GlobalAvgPool(Layer 5) [16 dims] (~150ms micro wrist snap / shockwave)
     - f_l7 = GlobalAvgPool(Layer 7) [64 dims] (~600ms downswing acceleration plane)
     - f_l10 = GlobalAvgPool(Layer 10) [512 dims] (~9.6s macro sequence)
     - f_l10_proj = GELU(Linear(512, 64)(f_l10)) [64 dims]
     - feat_2b = concat([f_l5, f_l7, f_l10_proj]) [144 dims]
     - Dense Classifier: Linear(144, 64) -> BatchNorm1d(64) -> GELU -> Dropout(0.1) -> Linear(64, 4)
  3. Intra-Head Sub-Loss Weighting (Head 2B Only):
     - weight_2b = [1.1, 1.35, 1.0, 1.0] for [PULL/HOOK, POWER DRIVE, SLOG, CUT/PUNCH]
     - Unweighted Heads 1 & 2A with label_smoothing=0.1
  4. Optimization: AdamW (weight_decay=1e-2), Discriminative LR (3e-4 for L1-5, 1e-3 for L6-10+Heads), 3-epoch warmup
  5. Slicing Augmentation: +/-30ms temporal jitter (+/-13 frames at 423 Hz)
  6. Checkpointing: Peak Holdout Candidate Macro-F1 (patience=10, min_delta=0.0)
  7. Full multi-tier scorecard evaluation across all 59 physical sessions.
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
    ROOT_DIR, BASE_DIR, DATASET_DIR, SESSIONS_DIR, STAGE1_MODEL_PATH, STAGE2_MODEL_PATH,
    STATS_PATH, HOLDOUT_SESSIONS, STAGE1_CHANNELS, FEATURES, CLASSES, SHOT_CLASSES,
    normalise_shot_type, FacingUpTCN, StanceTracker, AdvancedTCNBlock,
    load_parquet_session, evaluate_multitier_scorecard, format_class_table
)
from train_and_evaluate_full_scorecard import (
    sync_unified_dataset, load_dataset_for_training, SessionWindowDataset,
    CLASS_TO_IDX, NUM_CLASSES, NUM_FEATURES, WINDOW_LEN, BATCH_SIZE, DEVICE
)

# Canonical 3-Family Mappings:
# Family 0 (Upright Vertical): DRIVE/DEFENCE(3), GLANCE/FLICK(4), DEFLECTION/GUIDE(6)
# Family 1 (Upright Cross/Power): PULL/HOOK(2), POWER DRIVE(7), SLOG(8), CUT/PUNCH(5)
# Family 2 (Crouched Floor): SWEEP(9)
FAM3_FAMILY0_CLASSES = [3, 4, 6]     # ['DRIVE/DEFENCE', 'GLANCE/FLICK', 'DEFLECTION/GUIDE']
FAM3_FAMILY1_CLASSES = [2, 7, 8, 5]  # ['PULL/HOOK', 'POWER DRIVE', 'SLOG', 'CUT/PUNCH']
FAM3_FAMILY2_CLASSES = [9]           # ['SWEEP']

# Fast Vectorized GPU Lookups
# CLASSES: ['no_shot'(0), 'pre_shot'(1), 'PULL/HOOK'(2), 'DRIVE/DEFENCE'(3), 'GLANCE/FLICK'(4), 'CUT/PUNCH'(5), 'DEFLECTION/GUIDE'(6), 'POWER DRIVE'(7), 'SLOG'(8), 'SWEEP'(9)]
FAM3_LOOKUP_FAMILY_T = torch.tensor([0, 0, 1, 0, 0, 1, 0, 1, 1, 2], dtype=torch.int64, device=DEVICE)
FAM3_LOOKUP_SUB_T    = torch.tensor([0, 0, 0, 0, 1, 3, 2, 1, 2, 0], dtype=torch.int64, device=DEVICE)

WEIGHT_2B = torch.tensor([1.1, 1.35, 1.0, 1.0], dtype=torch.float32, device=DEVICE)


# =============================================================================
# Dimension-Balanced Multi-Scale Triplet 3-Family Hierarchical TCN Architecture
# =============================================================================
class DimensionBalancedThreeFamilyTCN(nn.Module):
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
            
        # Head 1 & Head 2A Feature Concatenation: Layer 4 (16) + Layer 7 (64) + Layer 10 (512) = 592 dims
        concat_dim = channels_list[3] + channels_list[6] + channels_list[9]  # 16 + 64 + 512 = 592
        self.head_family = nn.Conv1d(concat_dim, 3, 1)  # Head 1: Macro Family Gate (3-Class Softmax)
        self.head_sub0 = nn.Conv1d(concat_dim, 3, 1)    # Head 2A: Sub-Classifier Family 0 (3-Class: Drive/Glance/Guide)
        
        # Head 2B: Dimension-Balanced Multi-Scale Triplet Feature Projection
        # 1. f_l5 = GlobalAvgPool(Layer 5) [16 dims]
        # 2. f_l7 = GlobalAvgPool(Layer 7) [64 dims]
        # 3. f_l10 = GlobalAvgPool(Layer 10) [512 dims] -> Linear(512, 64) -> GELU [64 dims]
        self.proj_l10 = nn.Linear(channels_list[9], 64)
        
        # 4. Dense Classifier on Concatenated [16 + 64 + 64 = 144 dims]
        self.head_sub1 = nn.Sequential(
            nn.Linear(144, 64),
            nn.BatchNorm1d(64),
            nn.GELU(),
            nn.Dropout(0.1),
            nn.Linear(64, 4)
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
        
        # Head 1 & Head 2A (Upright Vertical)
        concat_feat = torch.cat([l4, l7, l10], dim=1)  # (B, 592, L)
        logits_family = self.head_family(concat_feat)  # (B, 3, L)
        logits_sub0 = self.head_sub0(concat_feat)      # (B, 3, L)
        
        # Head 2B: Dimension-Balanced Multi-Scale Triplet Feature Projection
        f_l5 = l5.mean(dim=2)                          # (B, 16)
        f_l7 = l7.mean(dim=2)                          # (B, 64)
        f_l10 = l10.mean(dim=2)                        # (B, 512)
        f_l10_proj = F.gelu(self.proj_l10(f_l10))      # (B, 64)
        
        feat_2b = torch.cat([f_l5, f_l7, f_l10_proj], dim=1)  # (B, 144)
        out_sub1 = self.head_sub1(feat_2b)             # (B, 4)
        logits_sub1 = out_sub1.unsqueeze(-1).expand(-1, -1, L)  # (B, 4, L)
        
        return logits_family, logits_sub0, logits_sub1

    def forward(self, x):
        logits_family, logits_sub0, logits_sub1 = self.forward_heads(x)
        p_fam = F.softmax(logits_family, dim=1)  # (B, 3, L)
        p_sub0 = F.softmax(logits_sub0, dim=1)   # (B, 3, L)
        p_sub1 = F.softmax(logits_sub1, dim=1)   # (B, 4, L)
        
        B, _, L = logits_family.shape
        probs = torch.zeros((B, 10, L), device=x.device, dtype=x.dtype)
        probs[:, 0, :] = 0.0  # no_shot
        probs[:, 1, :] = 0.0  # pre_shot
        
        # Family 0 (Upright Vertical)
        probs[:, 3, :] = p_fam[:, 0, :] * p_sub0[:, 0, :]  # DRIVE/DEFENCE (3)
        probs[:, 4, :] = p_fam[:, 0, :] * p_sub0[:, 1, :]  # GLANCE/FLICK (4)
        probs[:, 6, :] = p_fam[:, 0, :] * p_sub0[:, 2, :]  # DEFLECTION/GUIDE (6)
        
        # Family 1 (Upright Cross/Power)
        probs[:, 2, :] = p_fam[:, 1, :] * p_sub1[:, 0, :]  # PULL/HOOK (2)
        probs[:, 7, :] = p_fam[:, 1, :] * p_sub1[:, 1, :]  # POWER DRIVE (7)
        probs[:, 8, :] = p_fam[:, 1, :] * p_sub1[:, 2, :]  # SLOG (8)
        probs[:, 5, :] = p_fam[:, 1, :] * p_sub1[:, 3, :]  # CUT/PUNCH (5)
        
        # Family 2 (Crouched Floor - Passthrough to SWEEP)
        probs[:, 9, :] = p_fam[:, 2, :]                    # SWEEP (9)
        
        return torch.log(probs + 1e-12)


# =============================================================================
# Vectorized GPU Hierarchical Loss Function with Head 2B Intra-Head Weighting
# =============================================================================
def compute_dimension_balanced_loss(logits_tuple, yb, loss_ce_standard, loss_ce_sub1):
    """
    Vectorized GPU computation of L_total = L_family + L_sub0 + L_sub1 on shot frames (yb >= 2).
    - Head 1 (Macro Family Gate): Unweighted CrossEntropy with Label Smoothing (0.1)
    - Head 2A (Upright Vertical): Unweighted CrossEntropy with Label Smoothing (0.1)
    - Head 2B (Upright Cross/Power): Weighted CrossEntropy (1.1, 1.35, 1.0, 1.0) with Label Smoothing (0.1)
    """
    logits_fam, logits_sub0, logits_sub1 = logits_tuple
    B, _, L = logits_fam.shape
    logits_fam_flat = logits_fam.transpose(1, 2).reshape(-1, 3)
    logits_sub0_flat = logits_sub0.transpose(1, 2).reshape(-1, 3)
    logits_sub1_flat = logits_sub1.transpose(1, 2).reshape(-1, 4)
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
    
    # 1. Macro Family Gate Loss
    l_family = loss_ce_standard(shot_logits_fam, target_fam)
    
    # 2. Head 2A (Vertical/Touch) Loss
    fam0_mask = (target_fam == 0)
    l_sub0 = loss_ce_standard(shot_logits_sub0[fam0_mask], target_sub[fam0_mask]) if fam0_mask.any() else torch.tensor(0.0, device=yb.device)
    
    # 3. Head 2B (Cross/Power) Weighted Sub-Loss
    fam1_mask = (target_fam == 1)
    l_sub1 = loss_ce_sub1(shot_logits_sub1[fam1_mask], target_sub[fam1_mask]) if fam1_mask.any() else torch.tensor(0.0, device=yb.device)
    
    return l_family + l_sub0 + l_sub1


# =============================================================================
# Batched Holdout Candidate Metric Evaluator
# =============================================================================
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
            pred_c = 9  # SWEEP
        y_pred.append(pred_c)
        
    acc = float(accuracy_score(y_true, y_pred))
    macro_f1 = float(f1_score(y_true, y_pred, average="macro", zero_division=0))
    return acc, macro_f1


# =============================================================================
# Main Training & Evaluation Harness
# =============================================================================
def main():
    print("="*100, flush=True)
    print("  DIMENSION-BALANCED MULTI-SCALE TRIPLET 3-FAMILY HIERARCHICAL TCN EXPERIMENT", flush=True)
    print(f"  Holdout / Validation Sessions ({len(HOLDOUT_SESSIONS)}): {', '.join(HOLDOUT_SESSIONS)}", flush=True)
    print(f"  Execution Device: {DEVICE}", flush=True)
    print("="*100, flush=True)
    
    # 1. Synchronize unified dataset
    sync_unified_dataset()
    
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
    
    stats_data = {'features': FEATURES, 'classes': CLASSES, 'median': med.tolist(), 'mad': mad.tolist()}
    
    for X, _, _ in train_data:
        X[:] = (X - med) / mad
    for X, _, _ in holdout_data:
        X[:] = (X - med) / mad
        
    train_dataset = SessionWindowDataset(train_data, WINDOW_LEN, is_train=True)
    train_sampler = torch.utils.data.WeightedRandomSampler(train_dataset.weights, len(train_dataset.weights), replacement=True)
    train_loader = DataLoader(train_dataset, batch_size=BATCH_SIZE, sampler=train_sampler, num_workers=0)
    
    val_dataset = SessionWindowDataset(holdout_data, WINDOW_LEN, is_train=False)
    val_loader = DataLoader(val_dataset, batch_size=BATCH_SIZE, shuffle=False, num_workers=0)
    
    # 2. Extract Holdout Candidate Ground-Truth Windows
    holdout_shot_windows = []
    for s_idx, (X, y, df) in enumerate(holdout_data):
        s_name = HOLDOUT_SESSIONS[s_idx]
        gt_path = os.path.join(SESSIONS_DIR, s_name, "ground_truth_aligned.csv")
        if not os.path.exists(gt_path): continue
        df_gt = pd.read_csv(gt_path)
        t_col = "sensor_narr_time_seconds" if "sensor_narr_time_seconds" in df_gt.columns else "impact_time_seconds"
        for _, row in df_gt.iterrows():
            st = row.get("shot_type")
            norm = normalise_shot_type(st)
            if norm is None or norm not in CLASS_TO_IDX: continue
            t_s = row[t_col]
            center_idx = int(t_s * 423.0)
            start_idx = center_idx - (WINDOW_LEN // 2)
            if start_idx < 0 or start_idx + WINDOW_LEN > len(X): continue
            w_X = X[start_idx:start_idx+WINDOW_LEN].copy()
            holdout_shot_windows.append((torch.from_numpy(w_X.T), CLASS_TO_IDX[norm]))
            
    print(f"Prepared {len(holdout_shot_windows)} holdout GT candidate evaluation windows.\n", flush=True)
    
    # 3. Model Initialization
    torch.manual_seed(42)
    np.random.seed(42)
    random.seed(42)
    
    model = DimensionBalancedThreeFamilyTCN(in_ch=NUM_FEATURES).to(DEVICE)
    
    # Parameter Groups for Discriminative Learning Rates
    l1_5_params = [p for i in range(5) for p in model.blocks[i].parameters()]
    l6_10_head_params = (
        [p for i in range(5, 10) for p in model.blocks[i].parameters()] +
        list(model.head_family.parameters()) +
        list(model.head_sub0.parameters()) +
        list(model.proj_l10.parameters()) +
        list(model.head_sub1.parameters())
    )
    
    BASE_LR_L1_5 = 3e-4
    BASE_LR_L6_10 = 1e-3
    WARMUP_EPOCHS = 3
    MAX_EPOCHS = 25
    PATIENCE = 10
    
    optim = torch.optim.AdamW([
        {'params': l1_5_params, 'lr': BASE_LR_L1_5},
        {'params': l6_10_head_params, 'lr': BASE_LR_L6_10}
    ], weight_decay=1e-2)
    
    loss_ce_standard = nn.CrossEntropyLoss(label_smoothing=0.1)
    loss_ce_sub1 = nn.CrossEntropyLoss(weight=WEIGHT_2B, label_smoothing=0.1)
    
    best_macro_f1 = -1.0
    best_shot_acc = 0.0
    best_val_loss = float('inf')
    best_epoch = 0
    patience_counter = 0
    best_model_state = None
    final_epoch = MAX_EPOCHS
    
    print("="*80, flush=True)
    print("🚀 TRAINING DIMENSION-BALANCED 3-FAMILY HIERARCHICAL TCN", flush=True)
    print(f"   Optimization: AdamW (weight_decay=1e-2), Warmup: {WARMUP_EPOCHS} Epochs", flush=True)
    print(f"   Discriminative LR: {BASE_LR_L1_5} (L1-5) / {BASE_LR_L6_10} (L6-10 + Heads)", flush=True)
    print(f"   Head 2B Weights: {WEIGHT_2B.cpu().numpy().tolist()} [PULL/HOOK, POWER DRIVE, SLOG, CUT/PUNCH]", flush=True)
    print(f"   Checkpoint Metric: Peak Holdout Macro-F1 (patience={PATIENCE})", flush=True)
    print("="*80, flush=True)
    
    for epoch in range(1, MAX_EPOCHS + 1):
        # Warmup Schedule
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
            
            logits_tuple = model.forward_heads(xb)
            loss = compute_dimension_balanced_loss(logits_tuple, yb, loss_ce_standard, loss_ce_sub1)
            
            optim.zero_grad()
            loss.backward()
            optim.step()
            r_loss += loss.item()
            n_b += 1
            
        train_loss = r_loss / n_b
        
        # Validation Pass
        model.eval()
        v_loss = 0.0
        v_n = 0
        with torch.no_grad():
            for xb, yb in val_loader:
                xb = xb.to(DEVICE)
                yb = yb.to(DEVICE)
                logits_tuple = model.forward_heads(xb)
                l = compute_dimension_balanced_loss(logits_tuple, yb, loss_ce_standard, loss_ce_sub1)
                v_loss += l.item()
                v_n += 1
        val_loss = v_loss / v_n if v_n > 0 else float('inf')
        
        ho_shot_acc, ho_macro_f1 = evaluate_holdout_candidate_metrics(model, holdout_shot_windows)
        
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

    # 4. Comprehensive Authoritative Multi-Tier Scorecard across all 59 sessions
    print("="*100, flush=True)
    print(f"📊 EVALUATING ACROSS ALL {len(all_parquet_sessions)} PHYSICAL SESSIONS VIA AUTHORITATIVE TELEMETRY ENGINE...", flush=True)
    print("="*100, flush=True)
    metrics = evaluate_multitier_scorecard(
        session_ids=all_parquet_sessions,
        stage1_model=None,
        stage2_model=model,
        norm_stats=stats_data,
        device=DEVICE,
        holdout_sessions=HOLDOUT_SESSIONS,
        verbose=True
    )
    
    # 5. Formatted Focus Summary Table
    print("\n" + "="*115, flush=True)
    print("🏆 FINAL EXPERIMENT SCORECARD: DIMENSION-BALANCED MULTI-SCALE TRIPLET 3-FAMILY TCN", flush=True)
    print("="*115, flush=True)
    print(f"  • Best Checkpoint Epoch : Epoch {best_epoch}")
    print(f"  • Holdout Macro-F1      : 🏆 {best_macro_f1:.4f}")
    print(f"  • Holdout Class Acc     : 🏆 {metrics['ho_cls_acc']:.2f}%")
    print(f"  • Holdout Shot Recall   : 🏆 {metrics['ho_rec']:.2f}% ({metrics['ho_tp']}/{metrics['ho_total_gt']} GT shots)")
    print(f"  • Holdout Precision     : 🏆 {metrics['ho_prec']:.2f}% ({metrics['ho_tp']}/{metrics['ho_total_cand']} candidates)")
    print(f"  • Holdout F1 Score      : 🏆 {metrics['ho_f1']:.2f}%")
    print(f"  • Global Precision      : 🏆 {metrics['global_prec']:.2f}% ({metrics['total_tp']}/{metrics['total_cand']} total candidates)")
    print(f"  • Global Shot Recall    : 🏆 {metrics['global_rec']:.2f}% ({metrics['total_tp']}/{metrics['total_gt']} total GT shots)")
    print(f"  • Training Class Acc    : 🏆 {metrics['tr_cls_acc']:.2f}%")
    print(f"  • Full Dataset Class Acc: 🏆 {metrics['full_cls_acc']:.2f}%")
    
    print("\n" + "="*115, flush=True)
    print("🎯 HOLDOUT 8-CLASS ACCURACY BREAKDOWN (FOCUS: POWER DRIVE, SLOG, PULL/HOOK, CUT/PUNCH)", flush=True)
    print("="*115, flush=True)
    ho_agg = metrics['holdout_agg']
    print("| Shot Class        | GT Count | Detected TPs | Correctly Classified | Classification Acc (%) | Total Coverage Rate (%) |")
    print("|---|:---:|:---:|:---:|:---:|:---:|")
    for s_cls in ["POWER DRIVE", "SLOG", "PULL/HOOK", "CUT/PUNCH", "DRIVE/DEFENCE", "GLANCE/FLICK", "DEFLECTION/GUIDE", "SWEEP"]:
        gt = ho_agg[s_cls]['gt_count']
        det = ho_agg[s_cls]['detected_count']
        corr = ho_agg[s_cls]['correct_class_count']
        cls_acc = (corr / det * 100.0) if det > 0 else 0.0
        cov_rec = (corr / gt * 100.0) if gt > 0 else 0.0
        highlight = "🔥" if s_cls in ["POWER DRIVE", "SLOG", "PULL/HOOK", "CUT/PUNCH"] else "  "
        print(f"| {highlight} **{s_cls:16s}** | {gt:8d} | {det:12d} | {corr:20d} | **{cls_acc:21.2f}%** | **{cov_rec:22.2f}%** |")
    print("="*115, flush=True)
    
    # Save checkpoint model
    out_model_path = os.path.join(PIPELINES_DIR, "dimension_balanced_3fam_model.pt")
    torch.save(best_model_state, out_model_path)
    print(f"\n💾 Saved best model checkpoint to: {out_model_path}\n", flush=True)


if __name__ == "__main__":
    main()
