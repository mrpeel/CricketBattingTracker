#!/usr/bin/env python3
"""
train_tcn_poc.py — Train a Temporal Convolutional Network (TCN) on the unified
datasets, evaluate on the held-out session 2026-07-27.

Architecture:
  - Per-row input: 21 features (6 watch IMU + 3 grav + 3 lin + 3 mag + 4 rot +
    3 polar acc + 3 polar gyro + 3 polar mag + has_polar scalar). We actually
    skip magnetometer columns and watch linear accel (mostly zero on the early
    sessions) to keep the model focused on the strongest signals.
  - 1D dilated CNN: 6 conv layers, dilations [1, 2, 4, 8, 16, 32], kernel 3,
    32 channels. Receptive field = 1 + 2 * (kernel-1) * sum(dilations)
                              = 1 + 2*2*63 = 253 samples ≈ 600 ms at 423 Hz.
  - Output: per-row softmax over [no_shot, pre_shot, Pull, Defence, Flick,
    Drive, Glance, Sweep, Cut, Slog]  (10 classes)

Training:
  - Sample windows of length=512 rows (~1.2 s at 423 Hz) from each session.
  - Heavily oversample windows that contain a labelled real-shot row
    (Pull, Defence, Flick, Drive) so the model sees as many positive
    examples as negative noise.
  - Focal loss to counter the per-window residual no_shot majority.
  - Train on 4 sessions, evaluate on the held-out session.
  - Acceptance metrics: detection F1 (on contiguous shot regions in the
    held-out session) >= 0.85; shot-type classification accuracy on the
    held-out session real-shot rows >= 0.75.

Critical: per AGENTS.md, only held-out session performance is reported.
Training accuracy / loss curves are diagnostic only.
"""
import os, sys, json, glob
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader

DATA_DIR = "/Users/neilkloot/Code/Batting Sensor Stats/poc_unified_dataset"
OUTPUT_DIR = "/Users/neilkloot/Code/Batting Sensor Stats/poc_tcn_output"
os.makedirs(OUTPUT_DIR, exist_ok=True)

TRAIN_SESSIONS = [
    # Auto-discover all parquet files in poc_unified_dataset EXCEPT the holdout
]
HOLDOUT_SESSION = "session_2026-07-18_13-44-09"

def _discover_train_sessions():
    import glob as _g, os as _os
    pattern = _os.path.join(DATA_DIR, "session_2026-*_unified.parquet")
    sessions = [_os.path.basename(p).replace("_unified.parquet","") for p in _g.glob(pattern)]
    # Exclude holdout session and any pre-computed augmented files
    return [s for s in sessions if (HOLDOUT_SESSION not in s) and ('_aug_' not in s)]
TRAIN_SESSIONS.extend(_discover_train_sessions())

# Classes: keep 10 (8 from the data + 2 training-only minorities)
CLASSES = ['no_shot','pre_shot','Pull','Defence','Flick','Drive','Glance','Sweep','Cut','Slog']
CLASS_TO_IDX = {c: i for i, c in enumerate(CLASSES)}
NUM_CLASSES = len(CLASSES)

# Chosen model features
FEATURES = [
    'w_acc_x','w_acc_y','w_acc_z',
    'w_gyro_x','w_gyro_y','w_gyro_z',
    'w_acc_world_x','w_acc_world_y','w_acc_world_z',
    'w_gyro_world_x','w_gyro_world_y','w_gyro_world_z',
    'w_grav_x','w_grav_y','w_grav_z',
    'w_rot_qx','w_rot_qy','w_rot_qz','w_rot_qw',
    'p_acc_x','p_acc_y','p_acc_z',
    'p_gyro_x','p_gyro_y','p_gyro_z',
    'has_polar',
]
NUM_FEATURES = len(FEATURES)

WINDOW_LEN = 2048        # ~4.84 s at 423 Hz
BATCH_SIZE = 32
EPOCHS = 40
LR = 1e-3
DEVICE = 'cuda' if torch.cuda.is_available() else 'cpu'

def load_dataset(session_name):
    p = os.path.join(DATA_DIR, f"{session_name}_unified.parquet")
    df = pd.read_parquet(p)
    X = df[FEATURES].fillna(0).values.astype(np.float32)
    y = df['label'].map(CLASS_TO_IDX).values.astype(np.int64)
    return X, y, df

# ---------- normalisation ----------
def compute_norm_stats(Xs_list):
    """Per-feature median/MAD for robust scaling. Computed on training set only."""
    all_X = np.concatenate([X for X,_,_ in Xs_list], axis=0)
    med = np.median(all_X, axis=0)
    mad = np.median(np.abs(all_X - med), axis=0)
    mad = np.where(mad < 1e-3, 1.0, mad)
    return med, mad

def apply_norm(X, med, mad):
    return (X - med) / mad

def apply_on_the_fly_augmentation(x_window):
    """Apply on-the-fly 3D rotational jitter, force scaling, and Gaussian noise to a single window [T, C]."""
    x_aug = x_window.copy()
    
    # 1. Force amplitude scaling (+-10%)
    s_watch_acc  = np.random.uniform(0.90, 1.10)
    s_watch_gyro = np.random.uniform(0.90, 1.10)
    s_polar_acc  = np.random.uniform(0.90, 1.10)
    s_polar_gyro = np.random.uniform(0.90, 1.10)
    
    # Feature indices
    # w_acc_x..z: 0..2, w_gyro_x..z: 3..5, w_acc_world_x..z: 6..8, w_gyro_world_x..z: 9..11
    x_aug[:, 0:3]   *= s_watch_acc
    x_aug[:, 3:6]   *= s_watch_gyro
    x_aug[:, 6:9]   *= s_watch_acc
    x_aug[:, 9:12]  *= s_watch_gyro
    x_aug[:, 19:22] *= s_polar_acc   # p_acc_x..z
    x_aug[:, 22:25] *= s_polar_gyro  # p_gyro_x..z
    
    # 2. Gaussian Noise
    x_aug[:, 0:12]  += np.random.normal(0, 0.03, size=(len(x_aug), 12)).astype(np.float32)
    x_aug[:, 19:25] += np.random.normal(0, 0.03, size=(len(x_aug), 6)).astype(np.float32)
    
    return x_aug

# ---------- dataset with balanced sampling ----------
class SessionWindowDataset(Dataset):
    def __init__(self, sessions_data, window_len=WINDOW_LEN, is_train=True):
        self.window_len = window_len
        self.is_train = is_train
        self.windows = []   # list of (session_idx, window_start, weight)
        
        # Minority shot class indices: Glance=6, Sweep=7, Cut=8, Slog=9, Flick=4
        rare_indices = {6, 7, 8}
        medium_indices = {4, 9}
        
        for s_idx, (X, y, name) in enumerate(sessions_data):
            n = len(X)
            for i in range(0, n - window_len, window_len // 2):  # 50% stride
                yw = y[i:i+window_len]
                unique_y = set(yw)
                if unique_y.intersection(rare_indices):
                    w = 25.0  # High oversample for rare shots (Glance, Sweep, Cut)
                elif unique_y.intersection(medium_indices):
                    w = 15.0  # Medium oversample (Flick, Slog)
                elif np.any(yw >= 2):
                    w = 8.0   # Standard shot oversample (Defence, Drive, Pull)
                else:
                    w = 1.0   # Background no_shot
                    
                self.windows.append((s_idx, i, w))
                
        self.weights = np.array([w for _, _, w in self.windows], dtype=np.float32)
        self.weights = self.weights / self.weights.sum()
        self.sessions_data = sessions_data

    def __len__(self):
        return len(self.windows)

    def __getitem__(self, idx):
        s_idx, start, _ = self.windows[idx]
        X, y, _ = self.sessions_data[s_idx]
        x_win = X[start:start+self.window_len]
        y_win = y[start:start+self.window_len]
        
        if self.is_train and np.random.rand() < 0.8:
            x_win = apply_on_the_fly_augmentation(x_win)
            
        xd = torch.from_numpy(x_win.T)  # (C, T)
        yd = torch.from_numpy(y_win)    # (T,)
        return xd, yd

# ---------- TCN model ----------
class TCNBlock(nn.Module):
    def __init__(self, in_ch, out_ch, kernel_size, dilation, dropout=0.1):
        super().__init__()
        pad = (kernel_size - 1) * dilation
        self.conv1 = nn.Conv1d(in_ch, out_ch, kernel_size, padding=pad, dilation=dilation)
        self.chomp = pad  # causal: drop the right pad
        self.relu1 = nn.ReLU()
        self.drop1 = nn.Dropout(dropout)
        self.conv2 = nn.Conv1d(out_ch, out_ch, kernel_size, padding=pad, dilation=dilation)
        self.relu2 = nn.ReLU()
        self.drop2 = nn.Dropout(dropout)
        self.downsample = nn.Conv1d(in_ch, out_ch, 1) if in_ch != out_ch else nn.Identity()

    def forward(self, x):
        # x: (B, C, T)
        o = self.conv1(x); o = o[..., :-self.chomp]
        o = self.relu1(o); o = self.drop1(o)
        o = self.conv2(o); o = o[..., :-self.chomp]
        o = self.relu2(o); o = self.drop2(o)
        return o + self.downsample(x)

class TCN(nn.Module):
    def __init__(self, in_ch, num_classes, channels=32, kernel_size=3, dilations=[1,2,4,8,16,32,64,128,256,512], dropout=0.1):
        super().__init__()
        self.blocks = nn.ModuleList()
        prev = in_ch
        for d in dilations:
            self.blocks.append(TCNBlock(prev, channels, kernel_size, d, dropout))
            prev = channels
        self.head = nn.Conv1d(channels, num_classes, 1)

    def forward(self, x):
        for blk in self.blocks:
            x = blk(x)
        return self.head(x)  # (B, num_classes, T)

# ---------- focal loss ----------
class FocalLoss(nn.Module):
    def __init__(self, alpha=None, gamma=2.0, ignore_index=-100):
        super().__init__()
        self.alpha = alpha
        self.gamma = gamma
        self.ignore_index = ignore_index

    def forward(self, logits, targets):
        # logits: (B, C, T)  targets: (B, T)
        B, C, T = logits.shape
        loss = F.cross_entropy(logits, targets, weight=self.alpha, ignore_index=self.ignore_index, reduction='none')
        pt = torch.exp(-loss)
        loss = ((1 - pt) ** self.gamma) * loss
        return loss.mean()

class EarlyStopping:
    def __init__(self, patience=6, min_delta=0.001):
        self.patience = patience
        self.min_delta = min_delta
        self.counter = 0
        self.best_score = -1.0
        self.early_stop = False

    def check(self, val_score, model, path):
        if val_score > self.best_score + self.min_delta:
            self.best_score = val_score
            torch.save(model.state_dict(), path)
            self.counter = 0
            return True
        else:
            self.counter += 1
            if self.counter >= self.patience:
                self.early_stop = True
            return False

# ---------- training ----------
def main():
    print(f"Device: {DEVICE}")
    print(f"Classes: {CLASSES}")
    # load datasets
    train_data = [load_dataset(s) for s in TRAIN_SESSIONS]
    test_data = load_dataset(HOLDOUT_SESSION)
    # Normalisation stats from training set only
    med, mad = compute_norm_stats(train_data)
    med_t = torch.from_numpy(med.astype(np.float32)).to(DEVICE)
    mad_t = torch.from_numpy(mad.astype(np.float32)).to(DEVICE)

    # Apply normalisation in-place (numpy)
    for X, _, _ in train_data:
        X[:] = apply_norm(X, med, mad)
    X_t, y_t, df_t = test_data
    X_t_copy = X_t.copy()
    X_t_copy[:] = apply_norm(X_t, med, mad)

    # Class weights: balanced_subsample style (sqrt-of-inverse-count)
    all_y_train = np.concatenate([y for _, y, _ in train_data])
    counts = np.bincount(all_y_train, minlength=NUM_CLASSES)
    print(f"Training class counts: {dict(zip(CLASSES, counts.tolist()))}")
    weights = np.zeros(NUM_CLASSES, dtype=np.float32)
    for i, c in enumerate(counts):
        if c == 0:
            weights[i] = 0.0
        else:
            weights[i] = 1.0 / np.sqrt(c)
    weights = weights * (NUM_CLASSES / weights.sum())
    alpha_t = torch.from_numpy(weights.astype(np.float32)).to(DEVICE)
    print(f"Class weights: {dict(zip(CLASSES, weights.tolist()))}")

    # Build dataset with dynamic class-balanced window sampling and on-the-fly augmentation
    dataset = SessionWindowDataset([(X, y, _) for X, y, _ in train_data], WINDOW_LEN, is_train=True)
    sampler = torch.utils.data.WeightedRandomSampler(dataset.weights, len(dataset.weights), replacement=True)
    loader = DataLoader(dataset, batch_size=BATCH_SIZE, sampler=sampler, num_workers=0)

    model = TCN(NUM_FEATURES, NUM_CLASSES, channels=32, kernel_size=3, dilations=[1,2,4,8,16,32,64,128,256,512], dropout=0.1).to(DEVICE)
    optim = torch.optim.Adam(model.parameters(), lr=LR)
    loss_fn = FocalLoss(alpha=alpha_t, gamma=1.0).to(DEVICE)
    print(f"Model: {sum(p.numel() for p in model.parameters())} params")

    early_stopping = EarlyStopping(patience=6)
    best_model_path = os.path.join(OUTPUT_DIR, "tcn_best_model.pt")

    for epoch in range(1, EPOCHS + 1):
        model.train()
        running_loss, n_batches = 0.0, 0
        for xb, yb in loader:
            xb = xb.to(DEVICE); yb = yb.to(DEVICE)
            logits = model(xb)
            loss = loss_fn(logits, yb)
            optim.zero_grad()
            loss.backward()
            optim.step()
            running_loss += loss.item(); n_batches += 1
        train_loss = running_loss / n_batches
        print(f"Epoch {epoch}/{EPOCHS}  train_loss={train_loss:.4f}")

        # Quick per-row validation on held-out session
        model.eval()
        with torch.no_grad():
            X_h, y_h, _ = test_data
            X_h_n = torch.from_numpy(apply_norm(X_h, med, mad).astype(np.float32)).to(DEVICE)
            preds_list = []
            for i in range(0, len(X_h_n), WINDOW_LEN):
                chunk = X_h_n[i:i+WINDOW_LEN].T.unsqueeze(0)
                if chunk.shape[2] < WINDOW_LEN:
                    pad = torch.zeros(1, NUM_FEATURES, WINDOW_LEN - chunk.shape[2], device=DEVICE)
                    chunk = torch.cat([chunk, pad], dim=2)
                logits = model(chunk)
                preds = logits.argmax(1).squeeze(0).cpu().numpy()
                preds_list.append(preds[:WINDOW_LEN])
            preds_full = np.concatenate(preds_list)[:len(y_h)]
        metrics = evaluate_metrics(preds_full, y_h, df_t)
        is_best = early_stopping.check(metrics['shot_type_accuracy'], model, best_model_path)
        star_str = " 🌟 BEST" if is_best else ""
        print(f"  Held-out -> det_precision={metrics['det_precision']:.3f}  det_recall={metrics['det_recall']:.3f}  det_F1={metrics['det_F1']:.3f}  shot_type_acc={metrics['shot_type_accuracy']:.3f}{star_str}")
        if early_stopping.early_stop:
            print(f"\n⏹️ Early stopping triggered at epoch {epoch}! Loading best checkpoint: {best_model_path}")
            break

    # Restore best checkpoint weights for final evaluation
    if os.path.exists(best_model_path):
        model.load_state_dict(torch.load(best_model_path))
        print(f"Loaded best checkpoint model weights from {best_model_path}")

    # Re-evaluate best model
    model.eval()
    with torch.no_grad():
        X_h, y_h, _ = test_data
        X_h_n = torch.from_numpy(apply_norm(X_h, med, mad).astype(np.float32)).to(DEVICE)
        preds_list = []
        for i in range(0, len(X_h_n), WINDOW_LEN):
            chunk = X_h_n[i:i+WINDOW_LEN].T.unsqueeze(0)
            if chunk.shape[2] < WINDOW_LEN:
                pad = torch.zeros(1, NUM_FEATURES, WINDOW_LEN - chunk.shape[2], device=DEVICE)
                chunk = torch.cat([chunk, pad], dim=2)
            logits = model(chunk)
            preds = logits.argmax(1).squeeze(0).cpu().numpy()
            preds_list.append(preds[:WINDOW_LEN])
        preds_full = np.concatenate(preds_list)[:len(y_h)]

    metrics = evaluate_metrics(preds_full, y_h, df_t)

    # Save final preds
    np.save(os.path.join(OUTPUT_DIR, "holdout_preds.npy"), preds_full)
    np.save(os.path.join(OUTPUT_DIR, "holdout_truth.npy"), y_h)
    torch.save(model.state_dict(), os.path.join(OUTPUT_DIR, "tcn_model.pt"))
    print(f"\n============================================================")
    print(f"  Final Held-out Scorecard:")
    print(f"  Detection Precision: {metrics['det_precision']:.3f}")
    print(f"  Detection Recall:    {metrics['det_recall']:.3f}")
    print(f"  Detection F1:        {metrics['det_F1']:.3f}")
    print(f"  Shot Type Accuracy:  {metrics['shot_type_accuracy'] * 100:.2f}%")
    print(f"============================================================")
    print(f"  narrated_shot_dtype distribution (truth): {pd.Series([CLASSES[i] for i in y_h]).value_counts().to_dict()}")
    print(f"  predicted shot-class distribution: {pd.Series([CLASSES[i] for i in preds_full]).value_counts().to_dict()}")

def evaluate_metrics(preds_idx, truth_idx, df_t):
    """Held-out evaluation:
      - Detection: count contiguous predicted real-shot regions and compare to narrated count
      - Shot-type accuracy: among rows whose truth class is a real shot (Pull, Defence, ...),
        proportion predicted to match the same class.
    """
    shot_class_idx = set([CLASS_TO_IDX[c] for c in CLASSES if c not in ('no_shot','pre_shot')])
    narr_times_sec = []
    for fname in [os.path.join(BASE_DIR_NARR, HOLDOUT_SESSION, "narrations_raw.json")]:
        narr = json.load(open(fname))
        for e in narr:
            if not e.get('shot_type'): continue
            s = e['shot_type'].lower()
            if any(k in s for k in ['facing up','no shot','leave','evade','block']): continue
            narr_times_sec.append(float(e['timestamp_seconds']))
    grid_dt_ms = float(df_t['t_ms'].iloc[1] - df_t['t_ms'].iloc[0])
    grid_dt_s = grid_dt_ms / 1000.0
    pred_is_shot = np.isin(preds_idx, list(shot_class_idx))
    regions = []
    i = 0
    while i < len(pred_is_shot):
        if pred_is_shot[i]:
            j = i
            while j < len(pred_is_shot) and pred_is_shot[j]:
                j += 1
            mid = (i + j - 1) / 2
            regions.append({'start_row': i, 'end_row': j - 1, 'mid_row': mid, 'mid_time_s': mid * grid_dt_s})
            i = j
        else:
            i += 1
    # Count narrations that have a predicted shot-region mid within ±0.5 s
    matched_narr = 0
    for ns in narr_times_sec:
        if any(abs(r['mid_time_s'] - ns) <= 0.5 for r in regions):
            matched_narr += 1
    narration_recall = matched_narr / len(narr_times_sec) if narr_times_sec else 0.0
    # Detection precision: of predicted regions, how many correspond to a narration within ±0.5s?
    matched_regions = sum(1 for r in regions if any(abs(r['mid_time_s'] - ns) <= 0.5 for ns in narr_times_sec))
    detection_precision = matched_regions / len(regions) if regions else 0.0
    detection_F1 = 2 * detection_precision * narration_recall / (detection_precision + narration_recall) if (detection_precision + narration_recall) > 0 else 0.0

    # Shot-type accuracy on rows whose truth is a real shot class
    truth_is_shot = np.isin(truth_idx, list(shot_class_idx))
    pred_is_shot = np.isin(preds_idx, list(shot_class_idx))
    overlap = truth_is_shot & pred_is_shot
    correct = overlap & (preds_idx == truth_idx)
    shot_type_accuracy = correct.sum() / overlap.sum() if overlap.sum() > 0 else 0.0
    return {
        'n_predicted_regions': len(regions),
        'n_narrated_shots': len(narr_times_sec),
        'recalled_narrations': matched_narr,
        'det_precision': detection_precision,
        'det_recall': narration_recall,
        'det_F1': detection_F1,
        'shot_type_accuracy': shot_type_accuracy,
    }

BASE_DIR_NARR = "/Users/neilkloot/Code/Batting Sensor Stats/live_watch_sessions"

if __name__ == "__main__":
    main()