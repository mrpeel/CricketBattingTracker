#!/usr/bin/env python3
"""
export_tcn_to_onnx.py — Train & Export Ultimate Advanced Baseline TCN to ONNX

1. Trains the Ultimate Advanced Baseline TCN on all training sessions.
2. Saves PyTorch weights to pipelines/tcn_ultimate_baseline.pt.
3. Exports model to ONNX format: pipelines/tcn_ultimate_baseline.onnx.
4. Copies ONNX model to app/src/main/assets/models/tcn_ultimate_baseline.onnx.
"""
import os
import sys
import json
import glob
import datetime
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader

ROOT_DIR      = "/Users/neilkloot/Code/CricketBattingTracker"
BASE_DIR      = "/Users/neilkloot/Code/Batting Sensor Stats"
DATASET_DIR   = os.path.join(BASE_DIR, "poc_unified_dataset")
MODEL_PT_PATH = os.path.join(ROOT_DIR, "pipelines", "tcn_ultimate_baseline.pt")
MODEL_ONNX_PATH = os.path.join(ROOT_DIR, "pipelines", "tcn_ultimate_baseline.onnx")
APP_ASSETS_DIR = os.path.join(ROOT_DIR, "app", "src", "main", "assets", "models")
APP_ONNX_PATH  = os.path.join(APP_ASSETS_DIR, "tcn_ultimate_baseline.onnx")
STATS_PATH     = os.path.join(ROOT_DIR, "pipelines", "tcn_norm_stats.json")

os.makedirs(APP_ASSETS_DIR, exist_ok=True)

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

CLASSES = ['no_shot','pre_shot','Pull','Defence','Flick','Drive','Glance','Sweep','Cut','Slog']
CLASS_TO_IDX = {c: i for i, c in enumerate(CLASSES)}
NUM_CLASSES = len(CLASSES)

WINDOW_LEN = 2048
BATCH_SIZE = 32
DEVICE     = 'cuda' if torch.cuda.is_available() else 'cpu'

# ============================================================
# FOCAL LOSS IMPLEMENTATION
# ============================================================
class FocalLoss(nn.Module):
    def __init__(self, gamma=2.0, weight=None):
        super().__init__()
        self.gamma = gamma
        self.weight = weight

    def forward(self, logits, targets):
        ce_loss = F.cross_entropy(logits, targets, weight=self.weight, reduction='none')
        pt = torch.exp(-ce_loss)
        focal_loss = ((1 - pt) ** self.gamma) * ce_loss
        return focal_loss.mean()

# ============================================================
# ADVANCED TCN MODEL WITH NON-CAUSAL PADDING & SKIP-HEAD
# ============================================================
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

class AdvancedTCN(nn.Module):
    def __init__(self, in_ch, num_classes=10, channels=32, dilations=[1,2,4,8,16,32,64,128,256,512]):
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
            
        l4  = layer_outputs[3]  # Layer 4 (d=8)
        l7  = layer_outputs[6]  # Layer 7 (d=64)
        l10 = layer_outputs[9]  # Layer 10 (d=512)
        concat_feat = torch.cat([l4, l7, l10], dim=1) # (B, 3*C, T)
        return self.head(concat_feat)

# ---------- Data Loading & Dataset ----------
def load_dataset(session_name):
    p = os.path.join(DATASET_DIR, f"{session_name}_unified.parquet")
    df = pd.read_parquet(p)
    X = df[FEATURES].fillna(0).values.astype(np.float32)
    y = df['label'].map(CLASS_TO_IDX).values.astype(np.int64)
    return X, y, df

class SessionWindowDataset(Dataset):
    def __init__(self, sessions_data, window_len=WINDOW_LEN):
        self.window_len = window_len
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

    def __len__(self): return len(self.windows)

    def __getitem__(self, idx):
        s_idx, start, _ = self.windows[idx]
        X, y, _ = self.sessions_data[s_idx]
        xd = torch.from_numpy(X[start:start+self.window_len].T)
        yd = torch.from_numpy(y[start:start+self.window_len])
        return xd, yd

def main():
    print("============================================================")
    print("  Train & Export Ultimate Advanced Baseline TCN to ONNX")
    print("============================================================")
    
    pattern = os.path.join(DATASET_DIR, "session_2026-*_unified.parquet")
    all_sessions = [os.path.basename(p).replace("_unified.parquet","") for p in glob.glob(pattern) if '_aug_' not in p]
    
    print(f"Loading {len(all_sessions)} sessions for training...")
    sessions_data = [load_dataset(s) for s in all_sessions]
    
    all_X = np.concatenate([X for X,_,_ in sessions_data], axis=0)
    med = np.median(all_X, axis=0)
    mad = np.median(np.abs(all_X - med), axis=0)
    mad = np.where(mad < 1e-3, 1.0, mad)
    
    # Save Normalisation Stats JSON
    stats_data = {
        'features': FEATURES,
        'classes': CLASSES,
        'median': med.tolist(),
        'mad': mad.tolist()
    }
    with open(STATS_PATH, 'w') as f:
        json.dump(stats_data, f, indent=2)
    print(f"Saved normalisation stats to {STATS_PATH}")
    
    for X, _, _ in sessions_data:
        X[:] = (X - med) / mad
        
    dataset = SessionWindowDataset(sessions_data, WINDOW_LEN)
    sampler = torch.utils.data.WeightedRandomSampler(dataset.weights, len(dataset.weights), replacement=True)
    loader = DataLoader(dataset, batch_size=BATCH_SIZE, sampler=sampler, num_workers=0)
    
    model = AdvancedTCN(NUM_FEATURES, NUM_CLASSES, channels=32).to(DEVICE)
    optim = torch.optim.Adam(model.parameters(), lr=1e-3)
    
    all_y = np.concatenate([y for _, y, _ in sessions_data])
    counts = np.bincount(all_y, minlength=NUM_CLASSES)
    weights = np.where(counts == 0, 0.0, 1.0 / np.sqrt(counts + 1e-5))
    weights = weights * (NUM_CLASSES / weights.sum())
    w_t = torch.from_numpy(weights.astype(np.float32)).to(DEVICE)
    loss_fn = FocalLoss(gamma=2.0, weight=w_t)
    
    if os.path.exists(MODEL_PT_PATH):
        print(f"\nLoading trained PyTorch model weights from {MODEL_PT_PATH}...")
        model.load_state_dict(torch.load(MODEL_PT_PATH, map_location=DEVICE))
    else:
        print("\nTraining Ultimate Baseline TCN (12 Epochs with Two-Stage Layer Freezing at Epoch 5)...")
        for epoch in range(1, 13):
            if epoch == 5:
                print("  🔒 Freezing Low-Level TCN Layers 1-5 (locking shockwave feature extractors)...")
                for idx in range(5):
                    for param in model.blocks[idx].parameters():
                        param.requires_grad = False
                        
            model.train()
            r_loss = 0.0; n_b = 0
            for xb, yb in loader:
                xb = xb.to(DEVICE); yb = yb.to(DEVICE)
                logits = model(xb)
                loss = loss_fn(logits, yb)
                optim.zero_grad(); loss.backward(); optim.step()
                r_loss += loss.item(); n_b += 1
                
            print(f"  Epoch {epoch:02d} / 12 | Train Loss: {r_loss/n_b:.4f}")
            
        torch.save(model.state_dict(), MODEL_PT_PATH)
        print(f"\n✅ Saved PyTorch model to {MODEL_PT_PATH}")
    
    # Export ONNX Model
    model.eval()
    dummy_input = torch.randn(1, NUM_FEATURES, WINDOW_LEN, device=DEVICE)
    
    torch.onnx.export(
        model,
        dummy_input,
        MODEL_ONNX_PATH,
        export_params=True,
        opset_version=14,
        do_constant_folding=True,
        input_names=['input_imu_stream'],
        output_names=['output_logits'],
        dynamic_axes={
            'input_imu_stream': {0: 'batch_size', 2: 'sequence_length'},
            'output_logits': {0: 'batch_size', 2: 'sequence_length'}
        }
    )
    print(f"✅ Exported ONNX model to {MODEL_ONNX_PATH}")
    
    # Copy to App Assets
    import shutil
    shutil.copy(MODEL_ONNX_PATH, APP_ONNX_PATH)
    print(f"✅ Copied ONNX model to Android App assets: {APP_ONNX_PATH}")

if __name__ == "__main__":
    main()
