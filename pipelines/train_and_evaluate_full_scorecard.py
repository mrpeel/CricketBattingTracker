#!/usr/bin/env python3
"""
pipelines/train_and_evaluate_full_scorecard.py — Master Training & Unified Multi-Tier Evaluation

1. Auto-synchronizes live watch sessions into unified 423 Hz Parquet datasets.
2. Loads all 53 physical sessions directly from Parquet files.
3. Computes feature normalization statistics (median / MAD) from training sessions.
4. Trains Variant C AdvancedTCN with Discriminative LR (1e-4 for Layers 1-5, 1e-3 for Layers 6-10 + Head,
   label_smoothing=0.1) and holdout validation loss early stopping.
5. Evaluates training, holdout, and full datasets EXCLUSIVELY using the unified telemetry engine
   (pipelines/telemetry_engine.py). Zero Train-Serve Skew.
6. Enforces Production Quality Gate (Holdout Precision >= 75% or Micro Precision >= 70%, Holdout F1 >= 50%)
   and exports ONNX model to app assets.
7. Generates the authoritative full_dataset_training_scorecard.md report.
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
from sklearn.metrics import f1_score, accuracy_score

ROOT_DIR = "/Users/neilkloot/Code/CricketBattingTracker"
PIPELINES_DIR = os.path.join(ROOT_DIR, "pipelines")
if PIPELINES_DIR not in sys.path:
    sys.path.append(PIPELINES_DIR)

from telemetry_engine import (
    ROOT_DIR, BASE_DIR, DATASET_DIR, SESSIONS_DIR, STAGE1_MODEL_PATH, STAGE2_MODEL_PATH,
    STATS_PATH, APP_ASSETS_DIR, REPORT_OUT, HOLDOUT_SESSIONS, STAGE1_CHANNELS, FEATURES,
    CLASSES, SHOT_CLASSES, SOFT_TOUCH_CLASSES, normalise_shot_type,
    FacingUpTCN, StanceTracker, AdvancedTCNBlock, AdvancedTCN, Stage2TCNClassifier,
    estimate_session_clock_offset, load_parquet_session, predict_candidate_batch_unleaked,
    run_session_multitier, format_class_table, evaluate_multitier_scorecard
)

MODEL_PT_PATH = STAGE2_MODEL_PATH
MODEL_ONNX_PATH = os.path.join(ROOT_DIR, "pipelines", "tcn_ultimate_baseline.onnx")
APP_ONNX_PATH = os.path.join(APP_ASSETS_DIR, "tcn_ultimate_baseline.onnx")

CLASS_TO_IDX = {c: i for i, c in enumerate(CLASSES)}
NUM_CLASSES = len(CLASSES)
NUM_FEATURES = len(FEATURES)

WINDOW_LEN = 2048
BATCH_SIZE = 32
DEVICE = 'mps' if torch.backends.mps.is_available() else ('cuda' if torch.cuda.is_available() else 'cpu')


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
    y = df['label'].map(CLASS_TO_IDX).fillna(0).values.astype(np.int64)
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

    def __len__(self):
        return len(self.windows)

    def __getitem__(self, idx):
        s_idx, start, _ = self.windows[idx]
        X, y, _ = self.sessions_data[s_idx]
        if self.is_train:
            jitter = random.randint(-13, 13)  # +/-30ms optimal temporal anchor jitter at 423 Hz
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


def compute_val_loss(model, val_loader, loss_fn):
    model.eval()
    v_loss = 0.0
    n_b = 0
    with torch.no_grad():
        for xb, yb in val_loader:
            xb = xb.to(DEVICE)
            yb = yb.to(DEVICE)
            logits = model(xb)
            loss = loss_fn(logits, yb)
            v_loss += loss.item()
            n_b += 1
    return v_loss / n_b if n_b > 0 else float('inf')


def evaluate_holdout_shot_metrics(model, holdout_shot_windows):
    model.eval()
    if not holdout_shot_windows:
        return 0.0, 0.0
    y_true, y_pred = [], []
    with torch.no_grad():
        for x_t, target_c in holdout_shot_windows:
            x_t = x_t.unsqueeze(0).to(DEVICE)
            logits = model(x_t) # (1, num_classes, window_len)
            center_logits = logits[0, 2:, WINDOW_LEN // 2].cpu().numpy()
            pred_class = int(np.argmax(center_logits)) + 2
            y_true.append(target_c)
            y_pred.append(pred_class)
    acc = float(accuracy_score(y_true, y_pred))
    macro_f1 = float(f1_score(y_true, y_pred, average="macro", zero_division=0))
    return acc, macro_f1


def main():
    print("============================================================")
    print("  Master Training & Unified Multi-Tier Scorecard Pipeline")
    print(f"  Holdout / Validation Sessions ({len(HOLDOUT_SESSIONS)}): {', '.join(HOLDOUT_SESSIONS)}")
    print("============================================================")
    
    # Auto-sync raw live watch sessions to unified parquets
    sync_unified_dataset()
    
    pattern = os.path.join(DATASET_DIR, "session_2026-*_unified.parquet")
    all_parquet_sessions = sorted([os.path.basename(p).replace("_unified.parquet", "") for p in glob.glob(pattern) if '_aug_' not in p])
    train_sessions = [s for s in all_parquet_sessions if s not in HOLDOUT_SESSIONS]
    
    print(f"1. Loading {len(train_sessions)} training sessions & {len(HOLDOUT_SESSIONS)} holdout validation sessions...")
    train_data = [load_dataset_for_training(s) for s in train_sessions]
    train_data = [d for d in train_data if d is not None]
    
    holdout_data = [load_dataset_for_training(s) for s in HOLDOUT_SESSIONS]
    holdout_data = [d for d in holdout_data if d is not None]
    
    all_X = np.concatenate([X for X, _, _ in train_data], axis=0)
    med = np.median(all_X, axis=0)
    mad = np.median(np.abs(all_X - med), axis=0)
    mad = np.where(mad < 1e-3, 1.0, mad)
    
    # Save Normalisation Stats JSON
    os.makedirs(APP_ASSETS_DIR, exist_ok=True)
    stats_data = {'features': FEATURES, 'classes': CLASSES, 'median': med.tolist(), 'mad': mad.tolist()}
    with open(STATS_PATH, 'w') as f:
        json.dump(stats_data, f, indent=2)
    APP_STATS_PATH = os.path.join(APP_ASSETS_DIR, "tcn_norm_stats.json")
    with open(APP_STATS_PATH, 'w') as f:
        json.dump(stats_data, f, indent=2)
    print(f"✅ Saved normalisation stats to {STATS_PATH} & {APP_STATS_PATH}")
    
    for X, _, _ in train_data:
        X[:] = (X - med) / mad
    for X, _, _ in holdout_data:
        X[:] = (X - med) / mad
        
    train_dataset = SessionWindowDataset(train_data, WINDOW_LEN, is_train=True)
    train_sampler = torch.utils.data.WeightedRandomSampler(train_dataset.weights, len(train_dataset.weights), replacement=True)
    train_loader = DataLoader(train_dataset, batch_size=BATCH_SIZE, sampler=train_sampler, num_workers=0)
    
    val_dataset = SessionWindowDataset(holdout_data, WINDOW_LEN, is_train=False)
    val_loader = DataLoader(val_dataset, batch_size=BATCH_SIZE, shuffle=False, num_workers=0)
    
    # Build holdout ground-truth shot evaluation windows for direct candidate metric tracking
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
            
    print(f"✅ Prepared {len(holdout_shot_windows)} holdout GT candidate evaluation windows.")
    
    loss_fn = nn.CrossEntropyLoss(label_smoothing=0.1)
    
    model = AdvancedTCN(in_ch=NUM_FEATURES, num_classes=NUM_CLASSES, channels=32).to(DEVICE)
    
    # Harmonized Discriminative LR + 3-Epoch Warmup
    BASE_LR_L1_5 = 3e-4
    BASE_LR_L6_10 = 1e-3
    WARMUP_EPOCHS = 3
    
    l1_5_params = [p for i in range(5) for p in model.blocks[i].parameters()]
    l6_10_head_params = [p for i in range(5, 10) for p in model.blocks[i].parameters()] + list(model.head.parameters())
    optim = torch.optim.Adam([
        {'params': l1_5_params, 'lr': BASE_LR_L1_5},
        {'params': l6_10_head_params, 'lr': BASE_LR_L6_10}
    ])
    
    MAX_EPOCHS = 25
    PATIENCE = 10
    MIN_DELTA = 0.0
    
    print(f"\n2. Training AdvancedTCN with Harmonized LR (L1-5: {BASE_LR_L1_5}, L6-10+Head: {BASE_LR_L6_10}, {WARMUP_EPOCHS}-Epoch Warmup, Max {MAX_EPOCHS} Epochs & Holdout Macro-F1 Checkpointing)...")
    best_macro_f1 = -1.0
    best_shot_acc = 0.0
    best_val_loss = float('inf')
    best_epoch = 0
    patience_counter = 0
    best_model_state = None
    final_epoch = MAX_EPOCHS
    
    for epoch in range(1, MAX_EPOCHS + 1):
        # 3-Epoch Linear Warmup
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
            logits = model(xb)
            loss = loss_fn(logits, yb)
            optim.zero_grad()
            loss.backward()
            optim.step()
            r_loss += loss.item()
            n_b += 1
            
        train_loss = r_loss / n_b
        val_loss = compute_val_loss(model, val_loader, loss_fn)
        ho_shot_acc, ho_macro_f1 = evaluate_holdout_shot_metrics(model, holdout_shot_windows)
        
        improved = (ho_macro_f1 > best_macro_f1 + MIN_DELTA) or \
                   (abs(ho_macro_f1 - best_macro_f1) < 1e-4 and ho_shot_acc > best_shot_acc)
        
        status_tag = " ⭐ Best Model" if improved else ""
        print(f"  Epoch {epoch:2d}/{MAX_EPOCHS} - Train Loss: {train_loss:.4f} | Val Loss: {val_loss:.4f} | Holdout Shot Acc: {ho_shot_acc*100.0:.2f}% | Holdout Macro-F1: {ho_macro_f1:.4f}{status_tag}", flush=True)
        
        if improved:
            best_macro_f1 = ho_macro_f1
            best_shot_acc = ho_shot_acc
            best_val_loss = val_loss
            best_epoch = epoch
            patience_counter = 0
            best_model_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}
            torch.save(model.state_dict(), MODEL_PT_PATH)
        else:
            patience_counter += 1
            if best_model_state is None:
                best_macro_f1 = ho_macro_f1
                best_shot_acc = ho_shot_acc
                best_val_loss = val_loss
                best_epoch = epoch
                best_model_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}
                torch.save(model.state_dict(), MODEL_PT_PATH)
            if patience_counter >= PATIENCE:
                final_epoch = epoch
                print(f"  🛑 Early stopping triggered at Epoch {epoch}! Best Holdout Macro-F1: {best_macro_f1:.4f} (Acc: {best_shot_acc*100.0:.2f}%, Val Loss: {best_val_loss:.4f}) at Epoch {best_epoch} (No improvement over {PATIENCE} consecutive epochs).", flush=True)
                break
                
        final_epoch = epoch

    if best_model_state is not None:
        model.load_state_dict({k: v.to(DEVICE) for k, v in best_model_state.items()})
        print(f"✅ Reloaded best model checkpoint from Epoch {best_epoch} (Best Holdout Macro-F1: {best_macro_f1:.4f}, Shot Acc: {best_shot_acc*100.0:.2f}%)", flush=True)
    else:
        torch.save(model.state_dict(), MODEL_PT_PATH)
        print(f"✅ Saved PyTorch experiment model checkpoint to {MODEL_PT_PATH}", flush=True)
    
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
    print(f"  Training Strategy: Variant C (Harmonized LR: {BASE_LR_L1_5} / {BASE_LR_L6_10}, 3-Epoch Warmup, Holdout Macro-F1 Checkpointing)")
    print(f"  Validation Summary: Total Epochs = {final_epoch}, Best Holdout Macro-F1 = {best_macro_f1:.4f} (Shot Acc: {best_shot_acc*100.0:.2f}%, Val Loss: {best_val_loss:.4f} at Epoch {best_epoch})")
    print("="*115)
    print(f"  Holdout Set ({len(HOLDOUT_SESSIONS)} Sessions): Recall = {ho_recall:.1f}%, Precision = {ho_precision:.1f}%, F1 = {ho_f1:.1f}%, Class Acc = {ho_class_acc:.1f}%")
    print(f"  Training Set ({len(train_sessions)} Sessions):           Recall = {tr_recall:.1f}%, Precision = {tr_precision:.1f}%, F1 = {tr_f1:.1f}%, Class Acc = {tr_class_acc:.1f}%")
    print(f"  Full Dataset Total ({len(all_parquet_sessions)} Sessions):      Recall = {micro_recall:.1f}%, Precision = {micro_precision:.1f}%, F1 = {micro_f1:.1f}%")
    print("="*115 + "\n")
    
    # Save Report Markdown
    report = f"""# Full Dataset Training & Holdout Scorecard Report

**System Architecture**: Hierarchical Multi-Tier Stance-Gated TCN Pipeline (Stage 1 Facing Up Stance Detector + Stage 2 AdvancedTCN Classifier)  
**Training Design**: Variant C (Harmonized LR: `3e-4` for Layers 1-5, `1e-3` for Layers 6-10 + Head, 3-Epoch Warmup, Holdout Macro-F1 Checkpointing, Label Smoothing = 0.1)  
**Designated Holdout / Validation Sessions**: `{', '.join(HOLDOUT_SESSIONS)}` ({len(HOLDOUT_SESSIONS)} sessions)  
**Training Sessions Count**: {len(train_sessions)} physical sessions  
**Total Dataset Duration**: {total_duration_min:.1f} minutes ({total_duration_min/60.0:.1f} hours)  
**Holdout Macro-F1 Checkpointing**: Best Epoch {best_epoch} (Best Macro-F1: {best_macro_f1:.4f}, Shot Acc: {best_shot_acc*100.0:.2f}%, Val Loss: {best_val_loss:.4f}, Stopped at Epoch {final_epoch})  
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
        s_tp = int(df_s["is_tp"].sum()) if not df_s.empty else 0
        s_gt = sum(1 for s, g in metrics["all_gt_events"] if s == sid)
        s_rec = (s_tp / max(1, s_gt)) * 100.0
        s_prec = (s_tp / max(1, s_cand)) * 100.0
        s_f1 = (2 * s_prec * s_rec / (s_prec + s_rec)) if (s_prec + s_rec) > 0 else 0.0
        report += f"| `{sid}` | {part_str} | {dur:.1f} | {s_gt} | {s_cand} | {s_rec:.1f}% | {s_prec:.1f}% | {s_f1:.1f}%\n"

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
            model_cpu, dummy_input, MODEL_ONNX_PATH, export_params=True, opset_version=17,
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
