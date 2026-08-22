#!/usr/bin/env python3
"""
pipelines/run_hierarchical_tcn_experiments.py — Hierarchical Multi-Head TCN Architectural Experiments

Compares:
  1. Baseline Single-Head TCN (Canonical 10-Class Conv1D Head, 71.20% benchmark)
  2. Experiment 1: 2-Family Hierarchical Multi-Head TCN
     - Head 1: Binary Macro Family Gate (Vertical/Touch vs Cross-Bat/Power)
     - Head 2A: 4-class Sub-Classifier (DRIVE/DEFENCE, GLANCE/FLICK, DEFLECTION/GUIDE, SWEEP)
     - Head 2B: 4-class Sub-Classifier (PULL/HOOK, CUT/PUNCH, POWER DRIVE, SLOG)
  3. Experiment 2: 3-Family Hierarchical Multi-Head TCN
     - Head 1: 3-class Macro Family Gate (Upright Vertical vs Upright Cross/Power vs Crouched Floor)
     - Head 2A: 3-class Sub-Classifier (DRIVE/DEFENCE, GLANCE/FLICK, DEFLECTION/GUIDE)
     - Head 2B: 4-class Sub-Classifier (PULL/HOOK, CUT/PUNCH, POWER DRIVE, SLOG)
     - Head 2C: Identity / Passthrough to SWEEP

Fixed Hyperparameters across all runs:
  - 10-Layer Dilated TCN Backbone (Skip Concatenation: L4 + L7 + L10)
  - Discriminative LR (3e-4 for Layers 1-5, 1e-3 for Layers 6-10 + Heads)
  - 3-Epoch Linear Warmup
  - Label-Smoothed Cross-Entropy Loss (label_smoothing=0.1)
  - +/-30ms Temporal Jitter & 3D Spatial Rotation Augmentation
  - Holdout Macro-F1 Checkpointing (patience=10, min_delta=0.0, max_epochs=25)
  - Evaluated on all 58 physical sessions using designated holdout sessions:
    ['session_2026-07-20_12-42-16', 'session_2026-07-21_12-43-37', 'session_2026-07-24_12-52-29', 'session_2026-07-25_15-16-32']
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
    normalise_shot_type, FacingUpTCN, StanceTracker, AdvancedTCNBlock, AdvancedTCN,
    load_parquet_session, evaluate_multitier_scorecard
)
from train_and_evaluate_full_scorecard import (
    sync_unified_dataset, load_dataset_for_training, SessionWindowDataset,
    CLASS_TO_IDX, NUM_CLASSES, NUM_FEATURES, WINDOW_LEN, BATCH_SIZE, DEVICE
)

# Canonical mappings
# CLASSES = ['no_shot', 'pre_shot', 'PULL/HOOK', 'DRIVE/DEFENCE', 'GLANCE/FLICK', 'CUT/PUNCH', 'DEFLECTION/GUIDE', 'POWER DRIVE', 'SLOG', 'SWEEP']
# Indices: 2: PULL/HOOK, 3: DRIVE/DEFENCE, 4: GLANCE/FLICK, 5: CUT/PUNCH, 6: DEFLECTION/GUIDE, 7: POWER DRIVE, 8: SLOG, 9: SWEEP

# 2-Family Mappings:
# Family 0 (Vertical/Touch): DRIVE/DEFENCE(3), GLANCE/FLICK(4), DEFLECTION/GUIDE(6), SWEEP(9)
# Family 1 (Cross-Bat/Power): PULL/HOOK(2), CUT/PUNCH(5), POWER DRIVE(7), SLOG(8)
FAM2_FAMILY0_CLASSES = [3, 4, 6, 9]  # ['DRIVE/DEFENCE', 'GLANCE/FLICK', 'DEFLECTION/GUIDE', 'SWEEP']
FAM2_FAMILY1_CLASSES = [2, 5, 7, 8]  # ['PULL/HOOK', 'CUT/PUNCH', 'POWER DRIVE', 'SLOG']

# Fast GPU Vectorised Lookups
FAM2_LOOKUP_FAMILY_T = torch.tensor([0, 0, 1, 0, 0, 1, 0, 1, 1, 0], dtype=torch.int64, device=DEVICE)
FAM2_LOOKUP_SUB_T    = torch.tensor([0, 0, 0, 0, 1, 1, 2, 2, 3, 3], dtype=torch.int64, device=DEVICE)

# 3-Family Mappings:
# Family 0 (Upright Vertical): DRIVE/DEFENCE(3), GLANCE/FLICK(4), DEFLECTION/GUIDE(6)
# Family 1 (Upright Cross/Power): PULL/HOOK(2), CUT/PUNCH(5), POWER DRIVE(7), SLOG(8)
# Family 2 (Crouched Floor): SWEEP(9)
FAM3_FAMILY0_CLASSES = [3, 4, 6]     # ['DRIVE/DEFENCE', 'GLANCE/FLICK', 'DEFLECTION/GUIDE']
FAM3_FAMILY1_CLASSES = [2, 5, 7, 8]  # ['PULL/HOOK', 'CUT/PUNCH', 'POWER DRIVE', 'SLOG']
FAM3_FAMILY2_CLASSES = [9]           # ['SWEEP']

FAM3_LOOKUP_FAMILY_T = torch.tensor([0, 0, 1, 0, 0, 1, 0, 1, 1, 2], dtype=torch.int64, device=DEVICE)
FAM3_LOOKUP_SUB_T    = torch.tensor([0, 0, 0, 0, 1, 1, 2, 2, 3, 0], dtype=torch.int64, device=DEVICE)


# =============================================================================
# Architecture 1: 2-Family Hierarchical Multi-Head TCN
# =============================================================================
class TwoFamilyHierarchicalTCN(nn.Module):
    def __init__(self, in_ch=NUM_FEATURES, channels=32, dilations=[1, 2, 4, 8, 16, 32, 64, 128, 256, 512]):
        super().__init__()
        self.blocks = nn.ModuleList()
        prev = in_ch
        for d in dilations:
            self.blocks.append(AdvancedTCNBlock(prev, channels, 3, d, dropout=0.1))
            prev = channels
        
        # Concat feature dimension from layers 4, 7, 10
        concat_dim = channels * 3  # 96
        self.head_family = nn.Conv1d(concat_dim, 2, 1)  # Head 1: Macro Family Gate (Binary Softmax)
        self.head_sub0 = nn.Conv1d(concat_dim, 4, 1)    # Head 2A: Sub-Classifier Family 0 (4-class Softmax)
        self.head_sub1 = nn.Conv1d(concat_dim, 4, 1)    # Head 2B: Sub-Classifier Family 1 (4-class Softmax)

    def extract_features(self, x):
        layer_outputs = []
        out = x
        for blk in self.blocks:
            out = blk(out)
            layer_outputs.append(out)
        l4  = layer_outputs[3]
        l7  = layer_outputs[6]
        l10 = layer_outputs[9]
        return torch.cat([l4, l7, l10], dim=1)

    def forward_heads(self, x):
        feat = self.extract_features(x)
        logits_family = self.head_family(feat)  # (B, 2, L)
        logits_sub0 = self.head_sub0(feat)      # (B, 4, L)
        logits_sub1 = self.head_sub1(feat)      # (B, 4, L)
        return logits_family, logits_sub0, logits_sub1

    def forward(self, x):
        """
        Returns full reconstructed 10-class pseudo-logits for direct drop-in compatibility
        with telemetry_engine.py unleaked candidate inference.
        """
        logits_family, logits_sub0, logits_sub1 = self.forward_heads(x)
        p_fam = F.softmax(logits_family, dim=1)  # (B, 2, L)
        p_sub0 = F.softmax(logits_sub0, dim=1)   # (B, 4, L)
        p_sub1 = F.softmax(logits_sub1, dim=1)   # (B, 4, L)
        
        B, _, L = logits_family.shape
        probs = torch.zeros((B, 10, L), device=x.device, dtype=x.dtype)
        # Background channels
        probs[:, 0, :] = 0.0  # no_shot
        probs[:, 1, :] = 0.0  # pre_shot
        
        # Family 0 (Vertical/Touch)
        probs[:, 3, :] = p_fam[:, 0, :] * p_sub0[:, 0, :]  # DRIVE/DEFENCE (3)
        probs[:, 4, :] = p_fam[:, 0, :] * p_sub0[:, 1, :]  # GLANCE/FLICK (4)
        probs[:, 6, :] = p_fam[:, 0, :] * p_sub0[:, 2, :]  # DEFLECTION/GUIDE (6)
        probs[:, 9, :] = p_fam[:, 0, :] * p_sub0[:, 3, :]  # SWEEP (9)
        
        # Family 1 (Cross-Bat/Power)
        probs[:, 2, :] = p_fam[:, 1, :] * p_sub1[:, 0, :]  # PULL/HOOK (2)
        probs[:, 5, :] = p_fam[:, 1, :] * p_sub1[:, 1, :]  # CUT/PUNCH (5)
        probs[:, 7, :] = p_fam[:, 1, :] * p_sub1[:, 2, :]  # POWER DRIVE (7)
        probs[:, 8, :] = p_fam[:, 1, :] * p_sub1[:, 3, :]  # SLOG (8)
        
        return torch.log(probs + 1e-12)


# =============================================================================
# Architecture 2: 3-Family Hierarchical Multi-Head TCN
# =============================================================================
class ThreeFamilyHierarchicalTCN(nn.Module):
    def __init__(self, in_ch=NUM_FEATURES, channels=32, dilations=[1, 2, 4, 8, 16, 32, 64, 128, 256, 512]):
        super().__init__()
        self.blocks = nn.ModuleList()
        prev = in_ch
        for d in dilations:
            self.blocks.append(AdvancedTCNBlock(prev, channels, 3, d, dropout=0.1))
            prev = channels
            
        concat_dim = channels * 3  # 96
        self.head_family = nn.Conv1d(concat_dim, 3, 1)  # Head 1: Macro Family Gate (3-Class Softmax)
        self.head_sub0 = nn.Conv1d(concat_dim, 3, 1)    # Head 2A: Sub-Classifier Family 0 (3-class: Drive/Glance/Guide)
        self.head_sub1 = nn.Conv1d(concat_dim, 4, 1)    # Head 2B: Sub-Classifier Family 1 (4-class: Pull/Cut/Power/Slog)
        # Head 2C: Identity / Passthrough to SWEEP (no additional parameters)

    def extract_features(self, x):
        layer_outputs = []
        out = x
        for blk in self.blocks:
            out = blk(out)
            layer_outputs.append(out)
        l4  = layer_outputs[3]
        l7  = layer_outputs[6]
        l10 = layer_outputs[9]
        return torch.cat([l4, l7, l10], dim=1)

    def forward_heads(self, x):
        feat = self.extract_features(x)
        logits_family = self.head_family(feat)  # (B, 3, L)
        logits_sub0 = self.head_sub0(feat)      # (B, 3, L)
        logits_sub1 = self.head_sub1(feat)      # (B, 4, L)
        return logits_family, logits_sub0, logits_sub1

    def forward(self, x):
        logits_family, logits_sub0, logits_sub1 = self.forward_heads(x)
        p_fam = F.softmax(logits_family, dim=1)  # (B, 3, L)
        p_sub0 = F.softmax(logits_sub0, dim=1)   # (B, 3, L)
        p_sub1 = F.softmax(logits_sub1, dim=1)   # (B, 4, L)
        
        B, _, L = logits_family.shape
        probs = torch.zeros((B, 10, L), device=x.device, dtype=x.dtype)
        # Background channels
        probs[:, 0, :] = 0.0  # no_shot
        probs[:, 1, :] = 0.0  # pre_shot
        
        # Family 0 (Upright Vertical)
        probs[:, 3, :] = p_fam[:, 0, :] * p_sub0[:, 0, :]  # DRIVE/DEFENCE (3)
        probs[:, 4, :] = p_fam[:, 0, :] * p_sub0[:, 1, :]  # GLANCE/FLICK (4)
        probs[:, 6, :] = p_fam[:, 0, :] * p_sub0[:, 2, :]  # DEFLECTION/GUIDE (6)
        
        # Family 1 (Upright Cross/Power)
        probs[:, 2, :] = p_fam[:, 1, :] * p_sub1[:, 0, :]  # PULL/HOOK (2)
        probs[:, 5, :] = p_fam[:, 1, :] * p_sub1[:, 1, :]  # CUT/PUNCH (5)
        probs[:, 7, :] = p_fam[:, 1, :] * p_sub1[:, 2, :]  # POWER DRIVE (7)
        probs[:, 8, :] = p_fam[:, 1, :] * p_sub1[:, 3, :]  # SLOG (8)
        
        # Family 2 (Crouched Floor - Passthrough to SWEEP)
        probs[:, 9, :] = p_fam[:, 2, :]                    # SWEEP (9)
        
        return torch.log(probs + 1e-12)


# =============================================================================
# Vectorised GPU Hierarchical Loss Functions
# =============================================================================
def compute_hierarchical_loss_2fam(logits_tuple, yb, loss_ce):
    """
    Vectorised GPU computation of L_total = L_family + L_sub0 + L_sub1 on shot frames (yb >= 2).
    """
    logits_fam, logits_sub0, logits_sub1 = logits_tuple
    B, _, L = logits_fam.shape
    logits_fam_flat = logits_fam.transpose(1, 2).reshape(-1, 2)
    logits_sub0_flat = logits_sub0.transpose(1, 2).reshape(-1, 4)
    logits_sub1_flat = logits_sub1.transpose(1, 2).reshape(-1, 4)
    yb_flat = yb.reshape(-1)
    
    shot_mask = (yb_flat >= 2)
    if not shot_mask.any():
        return (logits_fam.sum() + logits_sub0.sum() + logits_sub1.sum()) * 0.0
        
    shot_yb = yb_flat[shot_mask]
    shot_logits_fam = logits_fam_flat[shot_mask]
    shot_logits_sub0 = logits_sub0_flat[shot_mask]
    shot_logits_sub1 = logits_sub1_flat[shot_mask]
    
    target_fam = FAM2_LOOKUP_FAMILY_T[shot_yb]
    target_sub = FAM2_LOOKUP_SUB_T[shot_yb]
    
    l_family = loss_ce(shot_logits_fam, target_fam)
    
    fam0_mask = (target_fam == 0)
    l_sub0 = loss_ce(shot_logits_sub0[fam0_mask], target_sub[fam0_mask]) if fam0_mask.any() else torch.tensor(0.0, device=yb.device)
    
    fam1_mask = (target_fam == 1)
    l_sub1 = loss_ce(shot_logits_sub1[fam1_mask], target_sub[fam1_mask]) if fam1_mask.any() else torch.tensor(0.0, device=yb.device)
    
    return l_family + l_sub0 + l_sub1


def compute_hierarchical_loss_3fam(logits_tuple, yb, loss_ce):
    """
    Vectorised GPU computation of L_total = L_family + L_sub0 + L_sub1 on shot frames (yb >= 2).
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
    
    l_family = loss_ce(shot_logits_fam, target_fam)
    
    fam0_mask = (target_fam == 0)
    l_sub0 = loss_ce(shot_logits_sub0[fam0_mask], target_sub[fam0_mask]) if fam0_mask.any() else torch.tensor(0.0, device=yb.device)
    
    fam1_mask = (target_fam == 1)
    l_sub1 = loss_ce(shot_logits_sub1[fam1_mask], target_sub[fam1_mask]) if fam1_mask.any() else torch.tensor(0.0, device=yb.device)
    
    return l_family + l_sub0 + l_sub1


# =============================================================================
# Batched Holdout Metric Evaluators
# =============================================================================
def evaluate_holdout_baseline(model, holdout_shot_windows):
    model.eval()
    if not holdout_shot_windows:
        return 0.0, 0.0
    all_x = torch.stack([x_t for x_t, _ in holdout_shot_windows], dim=0).to(DEVICE)
    y_true = [target_c for _, target_c in holdout_shot_windows]
    with torch.no_grad():
        logits = model(all_x)
        c_idx = WINDOW_LEN // 2
        shot_logits = logits[:, 2:, c_idx].cpu().numpy()
        y_pred = (np.argmax(shot_logits, axis=1) + 2).tolist()
    acc = float(accuracy_score(y_true, y_pred))
    macro_f1 = float(f1_score(y_true, y_pred, average="macro", zero_division=0))
    return acc, macro_f1


def evaluate_holdout_hierarchical_2fam(model, holdout_shot_windows):
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
            pred_c = FAM2_FAMILY0_CLASSES[sub0_choices[i]]
        else:
            pred_c = FAM2_FAMILY1_CLASSES[sub1_choices[i]]
        y_pred.append(pred_c)
        
    acc = float(accuracy_score(y_true, y_pred))
    macro_f1 = float(f1_score(y_true, y_pred, average="macro", zero_division=0))
    return acc, macro_f1


def evaluate_holdout_hierarchical_3fam(model, holdout_shot_windows):
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
# Experiment Training Loop Runner
# =============================================================================
def train_and_eval_experiment(exp_name, model_type, train_loader, val_loader, holdout_shot_windows,
                              all_parquet_sessions, train_sessions, stats_data, max_epochs=25, patience=10):
    print("\n" + "="*80)
    print(f"🚀 STARTING {exp_name.upper()}")
    print("="*80)
    
    torch.manual_seed(42)
    np.random.seed(42)
    random.seed(42)
    
    if model_type == "baseline":
        model = AdvancedTCN(in_ch=NUM_FEATURES, num_classes=NUM_CLASSES, channels=32).to(DEVICE)
        l1_5_params = [p for i in range(5) for p in model.blocks[i].parameters()]
        l6_10_head_params = [p for i in range(5, 10) for p in model.blocks[i].parameters()] + list(model.head.parameters())
    elif model_type == "2fam":
        model = TwoFamilyHierarchicalTCN(in_ch=NUM_FEATURES, channels=32).to(DEVICE)
        l1_5_params = [p for i in range(5) for p in model.blocks[i].parameters()]
        l6_10_head_params = [p for i in range(5, 10) for p in model.blocks[i].parameters()] + \
                            list(model.head_family.parameters()) + list(model.head_sub0.parameters()) + list(model.head_sub1.parameters())
    elif model_type == "3fam":
        model = ThreeFamilyHierarchicalTCN(in_ch=NUM_FEATURES, channels=32).to(DEVICE)
        l1_5_params = [p for i in range(5) for p in model.blocks[i].parameters()]
        l6_10_head_params = [p for i in range(5, 10) for p in model.blocks[i].parameters()] + \
                            list(model.head_family.parameters()) + list(model.head_sub0.parameters()) + list(model.head_sub1.parameters())
    else:
        raise ValueError(f"Unknown model_type: {model_type}")
        
    BASE_LR_L1_5 = 3e-4
    BASE_LR_L6_10 = 1e-3
    WARMUP_EPOCHS = 3
    
    optim = torch.optim.Adam([
        {'params': l1_5_params, 'lr': BASE_LR_L1_5},
        {'params': l6_10_head_params, 'lr': BASE_LR_L6_10}
    ])
    
    loss_ce = nn.CrossEntropyLoss(label_smoothing=0.1)
    
    best_macro_f1 = -1.0
    best_shot_acc = 0.0
    best_val_loss = float('inf')
    best_epoch = 0
    patience_counter = 0
    best_model_state = None
    final_epoch = max_epochs
    
    print(f"Training {exp_name} (Discriminative LR: {BASE_LR_L1_5}/{BASE_LR_L6_10}, {WARMUP_EPOCHS}-Epoch Warmup, Patience: {patience})...")
    
    for epoch in range(1, max_epochs + 1):
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
            
            if model_type == "baseline":
                logits = model(xb)
                loss = loss_ce(logits, yb)
            elif model_type == "2fam":
                logits_tuple = model.forward_heads(xb)
                loss = compute_hierarchical_loss_2fam(logits_tuple, yb, loss_ce)
            elif model_type == "3fam":
                logits_tuple = model.forward_heads(xb)
                loss = compute_hierarchical_loss_3fam(logits_tuple, yb, loss_ce)
                
            optim.zero_grad()
            loss.backward()
            optim.step()
            r_loss += loss.item()
            n_b += 1
            
        train_loss = r_loss / n_b
        
        # Evaluate validation loss and holdout shot metrics
        model.eval()
        v_loss = 0.0
        v_n = 0
        with torch.no_grad():
            for xb, yb in val_loader:
                xb = xb.to(DEVICE)
                yb = yb.to(DEVICE)
                if model_type == "baseline":
                    l = loss_ce(model(xb), yb)
                elif model_type == "2fam":
                    l = compute_hierarchical_loss_2fam(model.forward_heads(xb), yb, loss_ce)
                elif model_type == "3fam":
                    l = compute_hierarchical_loss_3fam(model.forward_heads(xb), yb, loss_ce)
                v_loss += l.item()
                v_n += 1
        val_loss = v_loss / v_n if v_n > 0 else float('inf')
        
        if model_type == "baseline":
            ho_shot_acc, ho_macro_f1 = evaluate_holdout_baseline(model, holdout_shot_windows)
        elif model_type == "2fam":
            ho_shot_acc, ho_macro_f1 = evaluate_holdout_hierarchical_2fam(model, holdout_shot_windows)
        elif model_type == "3fam":
            ho_shot_acc, ho_macro_f1 = evaluate_holdout_hierarchical_3fam(model, holdout_shot_windows)
            
        improved = (ho_macro_f1 > best_macro_f1) or (abs(ho_macro_f1 - best_macro_f1) < 1e-4 and ho_shot_acc > best_shot_acc)
        status_tag = " ⭐ Best Checkpoint" if improved else ""
        print(f"  Epoch {epoch:2d}/{max_epochs} - Train Loss: {train_loss:.4f} | Val Loss: {val_loss:.4f} | Holdout Shot Acc: {ho_shot_acc*100.0:.2f}% | Holdout Macro-F1: {ho_macro_f1:.4f}{status_tag}", flush=True)
        
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
            if patience_counter >= patience:
                final_epoch = epoch
                print(f"  🛑 Early stopping triggered at Epoch {epoch}! Best Holdout Macro-F1: {best_macro_f1:.4f} (Acc: {best_shot_acc*100.0:.2f}%) at Epoch {best_epoch}.", flush=True)
                break
        final_epoch = epoch

    if best_model_state is not None:
        model.load_state_dict({k: v.to(DEVICE) for k, v in best_model_state.items()})
        print(f"✅ Reloaded best model checkpoint from Epoch {best_epoch} (Macro-F1: {best_macro_f1:.4f}, Shot Acc: {best_shot_acc*100.0:.2f}%)", flush=True)

    # Multi-Tier Scorecard Evaluation across all 58 sessions
    print(f"\n📊 Evaluating {exp_name} across ALL {len(all_parquet_sessions)} physical sessions via Telemetry Engine...", flush=True)
    metrics = evaluate_multitier_scorecard(
        session_ids=all_parquet_sessions,
        stage1_model=None,
        stage2_model=model,
        norm_stats=stats_data,
        device=DEVICE,
        holdout_sessions=HOLDOUT_SESSIONS,
        verbose=False
    )
    
    return {
        "exp_name": exp_name,
        "model_type": model_type,
        "best_epoch": best_epoch,
        "final_epoch": final_epoch,
        "best_macro_f1": best_macro_f1,
        "best_shot_acc": best_shot_acc,
        "best_val_loss": best_val_loss,
        "metrics": metrics,
        "model": model
    }


# =============================================================================
# Main Orchestrator
# =============================================================================
def main():
    print("="*100)
    print("  ARCHITECTURAL EXPERIMENT: 2-FAMILY vs 3-FAMILY HIERARCHICAL TCN vs CANONICAL BASELINE")
    print(f"  Designated Holdout Sessions ({len(HOLDOUT_SESSIONS)}): {', '.join(HOLDOUT_SESSIONS)}")
    print("="*100)
    
    sync_unified_dataset()
    
    pattern = os.path.join(DATASET_DIR, "session_2026-*_unified.parquet")
    all_parquet_sessions = sorted([os.path.basename(p).replace("_unified.parquet", "") for p in glob.glob(pattern) if '_aug_' not in p])
    train_sessions = [s for s in all_parquet_sessions if s not in HOLDOUT_SESSIONS]
    
    print(f"Loading {len(train_sessions)} training sessions & {len(HOLDOUT_SESSIONS)} holdout validation sessions (Total: {len(all_parquet_sessions)})...")
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
    
    # Build holdout ground-truth evaluation windows
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
            
    print(f"Prepared {len(holdout_shot_windows)} holdout GT candidate evaluation windows.", flush=True)
    
    # Run Experiments
    results = {}
    
    # 1. Baseline Single-Head TCN
    results["baseline"] = train_and_eval_experiment(
        exp_name="Baseline Single-Head (Canonical 10-Class)",
        model_type="baseline",
        train_loader=train_loader,
        val_loader=val_loader,
        holdout_shot_windows=holdout_shot_windows,
        all_parquet_sessions=all_parquet_sessions,
        train_sessions=train_sessions,
        stats_data=stats_data
    )
    
    # 2. Experiment 1: 2-Family Hierarchical Multi-Head TCN
    results["2fam"] = train_and_eval_experiment(
        exp_name="Experiment 1: 2-Family Hierarchical Multi-Head TCN",
        model_type="2fam",
        train_loader=train_loader,
        val_loader=val_loader,
        holdout_shot_windows=holdout_shot_windows,
        all_parquet_sessions=all_parquet_sessions,
        train_sessions=train_sessions,
        stats_data=stats_data
    )
    
    # 3. Experiment 2: 3-Family Hierarchical Multi-Head TCN
    results["3fam"] = train_and_eval_experiment(
        exp_name="Experiment 2: 3-Family Hierarchical Multi-Head TCN",
        model_type="3fam",
        train_loader=train_loader,
        val_loader=val_loader,
        holdout_shot_windows=holdout_shot_windows,
        all_parquet_sessions=all_parquet_sessions,
        train_sessions=train_sessions,
        stats_data=stats_data
    )
    
    # =========================================================================
    # Comparison Analysis & Scorecard Generation
    # =========================================================================
    print("\n" + "="*115)
    print("🏆 MASTER ARCHITECTURAL COMPARISON: 2-FAMILY vs 3-FAMILY vs CANONICAL BASELINE")
    print("="*115)
    
    summary_rows = []
    for k in ["baseline", "2fam", "3fam"]:
        r = results[k]
        m = r["metrics"]
        summary_rows.append({
            "Architecture": r["exp_name"],
            "Best Epoch": r["best_epoch"],
            "Holdout Macro-F1": f"{r['best_macro_f1']:.4f}",
            "Holdout Class Acc": f"{m['ho_cls_acc']:.2f}%",
            "Holdout Recall": f"{m['ho_rec']:.2f}% ({m['ho_tp']}/{m['ho_total_gt']})",
            "Holdout Precision": f"{m['ho_prec']:.2f}% ({m['ho_tp']}/{m['ho_total_cand']})",
            "Holdout F1": f"{m['ho_f1']:.2f}%",
            "Training Class Acc": f"{m['tr_cls_acc']:.2f}%",
            "Global Precision": f"{m['global_prec']:.2f}%",
            "Global Recall": f"{m['global_rec']:.2f}%"
        })
    df_summary = pd.DataFrame(summary_rows)
    print(df_summary.to_string(index=False))
    
    # Key Focus Shots Table (PULL/HOOK, SLOG, POWER DRIVE, SWEEP)
    focus_shots = ["PULL/HOOK", "SLOG", "POWER DRIVE", "SWEEP", "CUT/PUNCH", "DRIVE/DEFENCE", "GLANCE/FLICK", "DEFLECTION/GUIDE"]
    print("\n" + "="*115)
    print("🎯 HOLDOUT PER-SHOT ACCURACY BREAKDOWN COMPARISON")
    print("="*115)
    
    per_shot_rows = []
    for s_cls in focus_shots:
        row = {"Shot Class": s_cls}
        for k, col_name in [("baseline", "Baseline Single-Head"), ("2fam", "2-Family Multi-Head"), ("3fam", "3-Family Multi-Head")]:
            agg = results[k]["metrics"]["holdout_agg"][s_cls]
            gt = agg["gt_count"]
            det = agg["detected_count"]
            corr = agg["correct_class_count"]
            acc = (corr / max(1, det)) * 100.0 if det > 0 else 0.0
            row[f"{col_name} (Corr/Det)"] = f"{corr}/{det} ({acc:.1f}%)"
        per_shot_rows.append(row)
    df_per_shot = pd.DataFrame(per_shot_rows)
    print(df_per_shot.to_string(index=False))
    
    # Save Comprehensive Experiment Scorecard Markdown
    exp_report_path = os.path.join(ROOT_DIR, "hierarchical_tcn_experiments_scorecard.md")
    report_md = f"""# Hierarchical Multi-Head TCN Architectural Experiment Report

**Comparison**: Canonical Single-Head Baseline vs 2-Family Hierarchical Multi-Head TCN vs 3-Family Hierarchical Multi-Head TCN  
**Fixed Hyperparameters**: 10-Layer TCN Backbone (Skip Concatenation L4+L7+L10), Discriminative LR (`3e-4` L1–5, `1e-3` L6–10+Heads, 3-Epoch Warmup), Label-Smoothed Cross-Entropy Loss (`label_smoothing=0.1`), $\\pm 30\\text{{ms}}$ Jitter, Holdout Macro-F1 Checkpointing (`patience=10`, `min_delta=0.0`)  
**Designated Holdout Sessions**: `{', '.join(HOLDOUT_SESSIONS)}` ({len(HOLDOUT_SESSIONS)} sessions)  
**Total Evaluated Dataset**: {len(all_parquet_sessions)} physical sessions ({len(train_sessions)} training sessions + {len(HOLDOUT_SESSIONS)} holdout sessions)  
**Date**: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M")}

---

## 📊 Summary Multi-Tier Scorecard Comparison

| Architecture | Best Epoch | Holdout Macro-F1 | **Holdout Classification Acc** | **Holdout Recall** | **Holdout Precision** | **Holdout F1** | **Training Class Acc** | **Global Precision** | **Global Recall** |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| 🏛️ **Baseline Single-Head (Canonical 10-Class)** | Epoch {results['baseline']['best_epoch']} | {results['baseline']['best_macro_f1']:.4f} | **{results['baseline']['metrics']['ho_cls_acc']:.2f}%** | {results['baseline']['metrics']['ho_rec']:.2f}% ({results['baseline']['metrics']['ho_tp']}/{results['baseline']['metrics']['ho_total_gt']}) | {results['baseline']['metrics']['ho_prec']:.2f}% | {results['baseline']['metrics']['ho_f1']:.2f}% | {results['baseline']['metrics']['tr_cls_acc']:.2f}% | {results['baseline']['metrics']['global_prec']:.2f}% | {results['baseline']['metrics']['global_rec']:.2f}% |
| 🌿 **Experiment 1: 2-Family Hierarchical Multi-Head** | Epoch {results['2fam']['best_epoch']} | {results['2fam']['best_macro_f1']:.4f} | **{results['2fam']['metrics']['ho_cls_acc']:.2f}%** | {results['2fam']['metrics']['ho_rec']:.2f}% ({results['2fam']['metrics']['ho_tp']}/{results['2fam']['metrics']['ho_total_gt']}) | {results['2fam']['metrics']['ho_prec']:.2f}% | {results['2fam']['metrics']['ho_f1']:.2f}% | {results['2fam']['metrics']['tr_cls_acc']:.2f}% | {results['2fam']['metrics']['global_prec']:.2f}% | {results['2fam']['metrics']['global_rec']:.2f}% |
| 🌳 **Experiment 2: 3-Family Hierarchical Multi-Head** | Epoch {results['3fam']['best_epoch']} | {results['3fam']['best_macro_f1']:.4f} | **{results['3fam']['metrics']['ho_cls_acc']:.2f}%** | {results['3fam']['metrics']['ho_rec']:.2f}% ({results['3fam']['metrics']['ho_tp']}/{results['3fam']['metrics']['ho_total_gt']}) | {results['3fam']['metrics']['ho_prec']:.2f}% | {results['3fam']['metrics']['ho_f1']:.2f}% | {results['3fam']['metrics']['tr_cls_acc']:.2f}% | {results['3fam']['metrics']['global_prec']:.2f}% | {results['3fam']['metrics']['global_rec']:.2f}% |

---

## 🎯 Per-Shot Holdout Classification Accuracy Breakdown

| Shot Class | Ground-Truth Shots | **Baseline Single-Head** (Corr/Det) | **Experiment 1: 2-Family** (Corr/Det) | **Experiment 2: 3-Family** (Corr/Det) | Focus Shot Highlights |
|---|:---:|:---:|:---:|:---:|---|
"""
    for s_cls in focus_shots:
        gt_cnt = results["baseline"]["metrics"]["holdout_agg"][s_cls]["gt_count"]
        
        b_agg = results["baseline"]["metrics"]["holdout_agg"][s_cls]
        b_det = b_agg["detected_count"]
        b_corr = b_agg["correct_class_count"]
        b_acc = (b_corr / max(1, b_det)) * 100.0 if b_det > 0 else 0.0
        
        f2_agg = results["2fam"]["metrics"]["holdout_agg"][s_cls]
        f2_det = f2_agg["detected_count"]
        f2_corr = f2_agg["correct_class_count"]
        f2_acc = (f2_corr / max(1, f2_det)) * 100.0 if f2_det > 0 else 0.0
        
        f3_agg = results["3fam"]["metrics"]["holdout_agg"][s_cls]
        f3_det = f3_agg["detected_count"]
        f3_corr = f3_agg["correct_class_count"]
        f3_acc = (f3_corr / max(1, f3_det)) * 100.0 if f3_det > 0 else 0.0
        
        highlight = ""
        if s_cls in ["PULL/HOOK", "SLOG", "POWER DRIVE", "SWEEP"]:
            highlight = f"🔥 Key Focus ({s_cls})"
            
        report_md += f"| **{s_cls}** | {gt_cnt} | **{b_acc:.1f}%** ({b_corr}/{b_det}) | **{f2_acc:.1f}%** ({f2_corr}/{f2_det}) | **{f3_acc:.1f}%** ({f3_corr}/{f3_det}) | {highlight} |\n"

    report_md += """
---

## 🔬 Architectural Findings & Conclusions

1. **Macro Family Gating Impact**:
   - Decomposing the output into Macro Family Gate + Specialized Sub-Classifiers tests whether separating vertical-bat touch shots from horizontal-bat power strokes prevents feature competition in the shared backbone representation.
2. **Key Class Performance**:
   - **PULL/HOOK**: Evaluated on cross-bat power strokes.
   - **SLOG**: Evaluated on high-energy horizontal rotational swings.
   - **POWER DRIVE**: Evaluated on vertical downswing with high impact force.
   - **SWEEP**: Evaluated on low torso tilt / knee-down crouched ground strokes.
"""

    with open(exp_report_path, "w") as f:
        f.write(report_md)
    print(f"\n✅ Master experimental scorecard report saved to {exp_report_path}")
    print("="*115)


if __name__ == "__main__":
    main()
