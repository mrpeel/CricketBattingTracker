#!/usr/bin/env python3
"""
train_facing_up_detector.py — Train 5-Layer TCN Binary Facing Up (Stance) Detector and Evaluate 2-Session Holdout Scorecard.

Features:
  - 46 Training Sessions / 2 Unseen Holdout Sessions (session_2026-07-21_12-43-37 & session_2026-07-25_15-16-32).
  - Model: 5-Layer 1D TCN / CNN accepting (Batch, Channels=12, Time=423).
  - Output: Sigmoid P(facing_up) in [0.0, 1.0].
  - Inference State Machine:
      STATE = FACING_UP when P >= 0.70 sustained for >= 200ms.
      STATE = STANCE_EXIT the instant P < 0.40 or rotational velocity w > 1.8 rad/s.
  - Scorecard:
      1. Stance Precision & Recall on explicit "Facing up" entries.
      2. False Positive Rate during ambient rest/collection periods.
      3. Mean Lead Time delta(t) between STANCE_EXIT and physical shot execution.
"""

import os
import sys
import pickle
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import TensorDataset, DataLoader

DATASET_PATH = "/Users/neilkloot/Code/CricketBattingTracker/facing_up_sessions_423hz.pkl"
MODEL_SAVE_PATH = "/Users/neilkloot/Code/CricketBattingTracker/facing_up_tcn_model.pt"

WINDOW_LEN = 423
TRAIN_STRIDE = 100   # ~236ms stride for fast high-density training
EVAL_STRIDE = 42     # ~100ms stride for continuous state machine evaluation

# -----------------------------------------------------------------------------
# 1. 5-Layer TCN / 1D-CNN Architecture
# -----------------------------------------------------------------------------
class FacingUpTCN(nn.Module):
    def __init__(self, in_channels=12, num_filters=32):
        super(FacingUpTCN, self).__init__()
        self.layer1 = nn.Sequential(
            nn.Conv1d(in_channels, num_filters, kernel_size=5, padding=2),
            nn.BatchNorm1d(num_filters),
            nn.ReLU(),
            nn.MaxPool1d(kernel_size=2)  # (423 -> 211)
        )
        self.layer2 = nn.Sequential(
            nn.Conv1d(num_filters, num_filters * 2, kernel_size=5, padding=4, dilation=2),
            nn.BatchNorm1d(num_filters * 2),
            nn.ReLU(),
            nn.MaxPool1d(kernel_size=2)  # (211 -> 105)
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
        # Input shape: (Batch, Time=423, Channels=12) -> transpose to (Batch, 12, 423)
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
# 2. Vectorized Window Extraction
# -----------------------------------------------------------------------------
def build_window_tensors(sessions_data, is_holdout_set=False, stride=TRAIN_STRIDE):
    X_list = []
    y_list = []
    
    for sid, sdata in sessions_data.items():
        if sdata["is_holdout"] != is_holdout_set:
            continue
        ch = sdata["channels"]
        lbl = sdata["labels"]
        n_samples = len(lbl)
        w_gyr_mag = np.linalg.norm(ch[:, 3:6], axis=1)
        
        for start_idx in range(0, n_samples - WINDOW_LEN, stride):
            end_idx = start_idx + WINDOW_LEN
            win_ch = ch[start_idx:end_idx]
            win_lbl = lbl[start_idx:end_idx]
            
            c1_ratio = np.mean(win_lbl == 1)
            c0_ratio = np.mean(win_lbl == 0)
            win_w_max = np.max(w_gyr_mag[start_idx:end_idx])
            
            if c1_ratio >= 0.50 and win_w_max < 1.2:
                X_list.append(win_ch)
                y_list.append(1.0)
            elif c0_ratio >= 0.30 or win_w_max >= 1.5:
                X_list.append(win_ch)
                y_list.append(0.0)
                
    if not X_list:
        return torch.empty((0, WINDOW_LEN, 12), dtype=torch.float32), torch.empty((0,), dtype=torch.float32)
        
    X_arr = np.array(X_list, dtype=np.float32)
    y_arr = np.array(y_list, dtype=np.float32)
    return torch.tensor(X_arr), torch.tensor(y_arr)

# -----------------------------------------------------------------------------
# 3. Inference State Machine Simulation
# -----------------------------------------------------------------------------
class StanceStateMachine:
    def __init__(self, high_thresh=0.70, low_thresh=0.40, motion_surge_w=1.8, sustain_ms=200):
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

def evaluate_session_state_machine(model, device, sess_data):
    t_grid = sess_data["t_grid"]
    channels = sess_data["channels"]
    fu_times = sess_data["fu_times"]
    shot_times = sess_data["shot_times"]
    
    num_samples = len(t_grid)
    w_gyr_mag = np.linalg.norm(channels[:, 3:6], axis=1)
    
    windows = []
    t_mids = []
    w_mags = []
    
    for start_idx in range(0, num_samples - WINDOW_LEN, EVAL_STRIDE):
        end_idx = start_idx + WINDOW_LEN
        win = channels[start_idx:end_idx]
        windows.append(win)
        t_mids.append(t_grid[start_idx + WINDOW_LEN // 2])
        w_mags.append(np.max(w_gyr_mag[start_idx:end_idx]))
        
    if not windows:
        return 0, 0, 0, 0, []
        
    batch_size = 512
    probs = []
    model.eval()
    with torch.no_grad():
        for b in range(0, len(windows), batch_size):
            b_win = np.array(windows[b:b+batch_size], dtype=np.float32)
            b_tensor = torch.tensor(b_win, dtype=torch.float32).to(device)
            b_logits = model(b_tensor)
            b_prob = torch.sigmoid(b_logits).cpu().numpy()
            probs.extend(b_prob)
            
    sm = StanceStateMachine()
    facing_up_triggers = []
    stance_exits = []
    
    for i in range(len(probs)):
        p = probs[i]
        w = w_mags[i]
        t = t_mids[i]
        
        prev_state = sm.state
        new_state, exited = sm.process_step(p, w, dt_ms=100)
        
        if prev_state != "FACING_UP" and new_state == "FACING_UP":
            facing_up_triggers.append(t)
        if exited:
            stance_exits.append(t)
            
    tp_fu = 0
    fn_fu = 0
    for tf in fu_times:
        matched = any(tf - 3.0 <= trg <= tf + 1.5 for trg in facing_up_triggers)
        if matched:
            tp_fu += 1
        else:
            fn_fu += 1
            
    fp_ambient = 0
    all_events = fu_times + shot_times
    for trg in facing_up_triggers:
        near_event = any(abs(trg - ev) <= 5.0 for ev in all_events)
        if not near_event:
            fp_ambient += 1
            
    lead_times = []
    for ts in shot_times:
        prior_exits = [tx for tx in stance_exits if ts - 4.0 <= tx <= ts + 0.2]
        if prior_exits:
            closest_exit = max(prior_exits)
            dt = ts - closest_exit
            lead_times.append(dt)
            
    return tp_fu, fn_fu, fp_ambient, len(fu_times), lead_times

# -----------------------------------------------------------------------------
# 4. Main Training & Evaluation Loop
# -----------------------------------------------------------------------------
def main():
    print("==========================================================", flush=True)
    print("  TRAINING FACING UP (STANCE) TCN & HOLDOUT EVALUATION", flush=True)
    print("==========================================================", flush=True)
    
    if not os.path.exists(DATASET_PATH):
        print(f"Error: Dataset file missing at {DATASET_PATH}. Run build_facing_up_dataset.py first.", flush=True)
        sys.exit(1)
        
    with open(DATASET_PATH, "rb") as f:
        dataset = pickle.load(f)
        
    sessions_data = dataset["sessions_data"]
    
    print("Vectorizing training window tensors...", flush=True)
    X_train, y_train = build_window_tensors(sessions_data, is_holdout_set=False, stride=TRAIN_STRIDE)
    X_holdout, y_holdout = build_window_tensors(sessions_data, is_holdout_set=True, stride=TRAIN_STRIDE)
    
    pos_train = (y_train == 1.0).sum().item()
    neg_train = (y_train == 0.0).sum().item()
    pos_holdout = (y_holdout == 1.0).sum().item()
    neg_holdout = (y_holdout == 0.0).sum().item()
    
    print(f"Loaded Dataset Tensors:")
    print(f"  Training Set (46 Sessions): {len(y_train)} windows (Pos: {int(pos_train)}, Neg: {int(neg_train)})", flush=True)
    print(f"  Holdout Set  (2 Sessions) : {len(y_holdout)} windows (Pos: {int(pos_holdout)}, Neg: {int(neg_holdout)})\n", flush=True)
    
    if torch.backends.mps.is_available():
        device = torch.device("mps")
    elif torch.cuda.is_available():
        device = torch.device("cuda")
    else:
        device = torch.device("cpu")
    print(f"Training Device: {device}", flush=True)
    
    train_dataset = TensorDataset(X_train, y_train)
    train_loader = DataLoader(train_dataset, batch_size=512, shuffle=True, num_workers=0)
    
    model = FacingUpTCN(in_channels=12, num_filters=32).to(device)
    
    pos_cnt = max(1, pos_train)
    neg_cnt = max(1, neg_train)
    pos_weight = torch.tensor([(neg_cnt / pos_cnt)], dtype=torch.float32).to(device)
    criterion = nn.BCEWithLogitsLoss(pos_weight=pos_weight)
    optimizer = optim.Adam(model.parameters(), lr=1e-3, weight_decay=1e-4)
    
    epochs = 12
    print("\nStarting Fast TCN Training on 46 Sessions...", flush=True)
    for epoch in range(1, epochs + 1):
        model.train()
        total_loss = 0.0
        correct = 0
        total = 0
        
        for batch_X, batch_y in train_loader:
            batch_X, batch_y = batch_X.to(device), batch_y.to(device)
            optimizer.zero_grad()
            logits = model(batch_X)
            loss = criterion(logits, batch_y)
            loss.backward()
            optimizer.step()
            
            total_loss += loss.item() * batch_X.size(0)
            preds = (torch.sigmoid(logits) >= 0.50).float()
            correct += (preds == batch_y).sum().item()
            total += batch_y.size(0)
            
        epoch_loss = total_loss / max(1, total)
        epoch_acc = (correct / max(1, total)) * 100.0
        print(f"  Epoch {epoch:02d}/{epochs:02d} | Loss: {epoch_loss:.4f} | Window Acc: {epoch_acc:.2f}%", flush=True)
        
    os.makedirs(os.path.dirname(MODEL_SAVE_PATH), exist_ok=True)
    torch.save(model.state_dict(), MODEL_SAVE_PATH)
    print(f"\nModel saved to {MODEL_SAVE_PATH}", flush=True)
    
    # -----------------------------------------------------------------------------
    # 5. Continuous Scorecard Evaluation (Train vs Unseen Holdout)
    # -----------------------------------------------------------------------------
    print("\n==========================================================", flush=True)
    print("          CONTINUOUS INFERENCE SCORECARD EVALUATION", flush=True)
    print("==========================================================", flush=True)
    
    train_tp, train_fn, train_fp, train_total_fu = 0, 0, 0, 0
    train_leads = []
    
    holdout_tp, holdout_fn, holdout_fp, holdout_total_fu = 0, 0, 0, 0
    holdout_leads = []
    
    for sid, sess_data in sessions_data.items():
        tp, fn, fp, total_fu, leads = evaluate_session_state_machine(model, device, sess_data)
        
        if sess_data["is_holdout"]:
            holdout_tp += tp
            holdout_fn += fn
            holdout_fp += fp
            holdout_total_fu += total_fu
            holdout_leads.extend(leads)
            print(f"[HOLDOUT] {sid} | Rec: {tp}/{total_fu} ({tp/max(1,total_fu)*100:.1f}%) | Ambient FP: {fp} | Mean Lead: {np.mean(leads) if leads else 0:.2f}s", flush=True)
        else:
            train_tp += tp
            train_fn += fn
            train_fp += fp
            train_total_fu += total_fu
            train_leads.extend(leads)

    train_rec = (train_tp / max(1, train_total_fu)) * 100.0
    train_prec = (train_tp / max(1, (train_tp + train_fp))) * 100.0
    train_mean_lead = np.mean(train_leads) if train_leads else 0.0
    train_std_lead = np.std(train_leads) if train_leads else 0.0
    
    holdout_rec = (holdout_tp / max(1, holdout_total_fu)) * 100.0
    holdout_prec = (holdout_tp / max(1, (holdout_tp + holdout_fp))) * 100.0
    holdout_mean_lead = np.mean(holdout_leads) if holdout_leads else 0.0
    holdout_std_lead = np.std(holdout_leads) if holdout_leads else 0.0
    
    print("\n" + "="*70, flush=True)
    print("               FACING UP DETECTOR SCORECARD REPORT", flush=True)
    print("="*70, flush=True)
    print(f"| Metric                              | Train (46 Sessions) | Holdout (2 Unseen Sessions) |", flush=True)
    print(f"|-------------------------------------|---------------------|-----------------------------|", flush=True)
    print(f"| Facing Up Stance Recall (%)         | {train_rec:6.2f}%             | {holdout_rec:6.2f}%                      |", flush=True)
    print(f"| Facing Up Stance Precision (%)      | {train_prec:6.2f}%             | {holdout_prec:6.2f}%                      |", flush=True)
    print(f"| Total Explicit Narrations Matched   | {train_tp:4d} / {train_total_fu:4d}      | {holdout_tp:4d} / {holdout_total_fu:4d}               |", flush=True)
    print(f"| Ambient Rest False Positives (FPs)  | {train_fp:4d}                | {holdout_fp:4d}                         |", flush=True)
    print(f"| Mean Lead Time dt (STANCE_EXIT->Shot)| {train_mean_lead:.3f}s (+/-{train_std_lead:.2f}s) | {holdout_mean_lead:.3f}s (+/-{holdout_std_lead:.2f}s)       |", flush=True)
    print("="*70 + "\n", flush=True)

if __name__ == "__main__":
    main()
