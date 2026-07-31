#!/usr/bin/env python3
"""
pipelines/evaluate_all_sessions_scorecard.py — Full-Dataset Evaluation Scorecard

Evaluates the Decoupled Impact Shockwave Anchor Detector (Stage 1) + Ultimate TCN Classifier (Stage 2)
across ALL physical sessions in live_watch_sessions.
"""
import os
import sys
import json
import glob
import datetime
import numpy as np
import pandas as pd
import torch

ROOT_DIR = "/Users/neilkloot/Code/CricketBattingTracker"
BASE_DIR = "/Users/neilkloot/Code/Batting Sensor Stats"
SESSIONS_DIR = os.path.join(BASE_DIR, "live_watch_sessions")
UNIFIED_DIR = os.path.join(BASE_DIR, "poc_unified_dataset")
STATS_PATH = os.path.join(ROOT_DIR, "pipelines/tcn_norm_stats.json")
MODEL_PT_PATH = os.path.join(ROOT_DIR, "pipelines/tcn_ultimate_baseline.pt")
REPORT_OUT = os.path.join(ROOT_DIR, "full_dataset_scorecard_results.md")

sys.path.append(os.path.join(ROOT_DIR, "pipelines"))
from build_unified_dataset import build_session
from export_tcn_to_onnx import AdvancedTCN

# Load Normalisation Stats
stats = json.load(open(STATS_PATH))
features = stats['features']
classes = stats['classes']
med = np.array(stats['median'], dtype=np.float32)
mad = np.array(stats['mad'], dtype=np.float32)
mad = np.where(mad < 1e-3, 1.0, mad)

# Load Trained PyTorch Model
model = AdvancedTCN(in_ch=len(features), num_classes=len(classes), channels=32)
model.load_state_dict(torch.load(MODEL_PT_PATH, map_location='cpu'))
model.eval()

WINDOW_LEN = 2048

def evaluate_session(session_name):
    # Check if parquet exists, else build it
    p = os.path.join(UNIFIED_DIR, f"{session_name}_unified.parquet")
    if not os.path.exists(p):
        try:
            build_session(session_name, verbose=False)
        except Exception as e:
            return None
            
    if not os.path.exists(p):
        return None
        
    df = pd.read_parquet(p)
    if df.empty or len(df) < 100:
        return None
        
    X = df[features].fillna(0).values.astype(np.float32)
    X_norm = (X - med) / mad
    
    # Run TCN Model Inference
    preds_list = []
    probs_list = []
    with torch.no_grad():
        for i in range(0, len(X_norm), WINDOW_LEN):
            chunk = X_norm[i:i+WINDOW_LEN].T[np.newaxis, :, :]
            n_frames = chunk.shape[2]
            if n_frames < WINDOW_LEN:
                pad = np.zeros((1, len(features), WINDOW_LEN - n_frames), dtype=np.float32)
                chunk = np.concatenate([chunk, pad], axis=2)
            chunk_t = torch.from_numpy(chunk)
            logits = model(chunk_t)[0, :, :n_frames].numpy()
            exp_logits = np.exp(logits - np.max(logits, axis=0, keepdims=True))
            probs = exp_logits / np.sum(exp_logits, axis=0, keepdims=True)
            preds = np.argmax(probs, axis=0)
            preds_list.append(preds)
            probs_list.append(probs)
            
    preds_full = np.concatenate(preds_list)[:len(X)]
    probs_full = np.hstack(probs_list)[:, :len(X)]
    
    # Load Ground Truth Narrations
    sdir = os.path.join(SESSIONS_DIR, session_name)
    narr_path = os.path.join(sdir, "narrations_raw.json")
    gt_times = []
    if os.path.exists(narr_path):
        narr = json.load(open(narr_path))
        for e in narr:
            st = e.get('shot_type', '')
            gt_cls = normalise_shot_type(st)
            if gt_cls and gt_cls != 'Leave':
                gt_times.append(float(e['timestamp_seconds']))
        
    w_acc_mags  = np.linalg.norm(X[:, 0:3], axis=1)
    w_gyro_mags = np.linalg.norm(X[:, 3:6], axis=1)
    
    # Stage 1: Impact Shockwave Anchor Detector (Acc >= 45.0 m/s2, Gyro >= 6.5 rad/s)
    impact_mask = (w_acc_mags >= 45.0) & (w_gyro_mags >= 6.5)
    impact_frames = np.where(impact_mask)[0]
    
    anchors = []
    if len(impact_frames) > 0:
        cluster = [impact_frames[0]]
        for idx in range(1, len(impact_frames)):
            if impact_frames[idx] - impact_frames[idx-1] <= 423:
                cluster.append(impact_frames[idx])
            else:
                peak_f = cluster[np.argmax(w_acc_mags[cluster])]
                anchors.append(peak_f)
                cluster = [impact_frames[idx]]
        if cluster:
            peak_f = cluster[np.argmax(w_acc_mags[cluster])]
            anchors.append(peak_f)
            
    # Stage 2: TCN Shot Classification
    detections = []
    for f in anchors:
        w_s = max(0, f - 42)
        w_e = min(len(X), f + 42)
        win_probs = probs_full[:, w_s:w_e]
        top_class_idx = np.argmax(win_probs[2:10, :].max(axis=1)) + 2
        top_prob = win_probs[top_class_idx, :].max()
        pred_name = classes[top_class_idx]
        detections.append({'sec': f / 423.0, 'class': pred_name, 'prob': top_prob})
        
    # Evaluate Recall and Precision against Ground Truth
    matched_gt = sum(1 for gt in gt_times if any(abs(d['sec'] - gt) <= 2.5 for d in detections))
    matched_dets = sum(1 for d in detections if any(abs(d['sec'] - gt) <= 2.5 for gt in gt_times))
    
    dur_min = len(df) / 423.0 / 60.0
    rec = matched_gt / len(gt_times) if gt_times else 0.0
    prec = matched_dets / len(detections) if detections else 0.0
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0.0
    
    return {
        'session_name': session_name,
        'duration_min': dur_min,
        'gt_shots': len(gt_times),
        'detected_shots': len(detections),
        'matched_gt': matched_gt,
        'matched_dets': matched_dets,
        'recall': rec,
        'precision': prec,
        'f1': f1
    }

def main():
    print("============================================================")
    print("  Full-Dataset Evaluation Scorecard Across All Sessions")
    print("============================================================")
    
    pattern = os.path.join(SESSIONS_DIR, "session_2026-*")
    session_dirs = [d for d in glob.glob(pattern) if os.path.isdir(d)]
    session_names = sorted([os.path.basename(d) for d in session_dirs])
    
    print(f"Found {len(session_names)} physical sessions to evaluate...")
    
    results = []
    for idx, sname in enumerate(session_names, 1):
        print(f"  [{idx:02d}/{len(session_names)}] Evaluating {sname}...", end="", flush=True)
        res = evaluate_session(sname)
        if res:
            results.append(res)
            print(f" -> GT: {res['gt_shots']:2d} | Det: {res['detected_shots']:2d} | Rec: {res['recall']*100:5.1f}% | Prec: {res['precision']*100:5.1f}% | F1: {res['f1']*100:5.1f}%")
        else:
            print(" -> Skipped (No ground truth or unparseable)")
            
    df_res = pd.DataFrame(results)
    
    # Calculate Dataset-Wide Micro and Macro Averages
    total_gt = df_res['gt_shots'].sum()
    total_det = df_res['detected_shots'].sum()
    total_matched_gt = df_res['matched_gt'].sum()
    total_matched_det = df_res['matched_dets'].sum()
    
    micro_recall = total_matched_gt / total_gt if total_gt else 0
    micro_precision = total_matched_det / total_det if total_det else 0
    micro_f1 = 2 * micro_precision * micro_recall / (micro_precision + micro_recall) if (micro_precision + micro_recall) > 0 else 0
    
    macro_recall = df_res['recall'].mean()
    macro_precision = df_res['precision'].mean()
    macro_f1 = df_res['f1'].mean()
    
    print("\n" + "="*115)
    print("📊 FULL DATASET SCORECARD TABLE ACROSS ALL PHYSICAL SESSIONS")
    print("="*115)
    print(f"{'Session Name':<32} | {'Dur (min)':<9} | {'GT Shots':<8} | {'Detections':<10} | {'Recall (%)':<10} | {'Precision (%)':<13} | {'F1 Score (%)'}")
    print("-"*115)
    for r in results:
        print(f"{r['session_name']:<32} | {r['duration_min']:<9.1f} | {r['gt_shots']:<8d} | {r['detected_shots']:<10d} | {r['recall']*100:<10.1f} | {r['precision']*100:<13.1f} | {r['f1']*100:<10.1f}")
    print("="*115)
    print(f"{'DATASET TOTALS / MICRO AVG':<32} | {df_res['duration_min'].sum():<9.1f} | {total_gt:<8d} | {total_det:<10d} | {micro_recall*100:<10.1f} | {micro_precision*100:<13.1f} | {micro_f1*100:<10.1f}")
    print(f"{'DATASET MACRO AVERAGE':<32} | {'-':<9} | {'-':<8} | {'-':<10} | {macro_recall*100:<10.1f} | {macro_precision*100:<13.1f} | {macro_f1*100:<10.1f}")
    print("="*115 + "\n")
    
    # Save Report Markdown
    report = f"""# Full Dataset Evaluation Scorecard

**System Architecture**: Decoupled Impact Shockwave Anchor Detector (Stage 1) + Ultimate Advanced Baseline TCN Classifier (Stage 2)  
**Total Physical Sessions**: {len(df_res)}  
**Total Dataset Duration**: {df_res['duration_min'].sum():.1f} minutes  
**Date**: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M")}

---

## 📊 Summary Performance Metrics

| Metric Type | Physical Ground-Truth Shots | Total Detections | **Physical Shot Recall** | **Precision** | **F1 Score** |
|---|:---:|:---:|:---:|:---:|:---:|
| **Micro Average (Total Dataset-Wide)** | **{total_gt}** | **{total_det}** | **{micro_recall*100:.2f}%** ({total_matched_gt}/{total_gt}) | **{micro_precision*100:.2f}%** ({total_matched_det}/{total_det}) | **{micro_f1*100:.2f}%** |
| **Macro Average (Per-Session Mean)** | - | - | **{macro_recall*100:.2f}%** | **{macro_precision*100:.2f}%** | **{macro_f1*100:.2f}%** |

---

## 📋 Session-by-Session Scorecard Table

| Session Directory | Duration (min) | Ground-Truth Shots | Total Detections | Recall (%) | Precision (%) | F1 Score (%) |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
"""
    for r in results:
        report += f"| `{r['session_name']}` | {r['duration_min']:.1f} | {r['gt_shots']} | {r['detected_shots']} | {r['recall']*100:.1f}% | {r['precision']*100:.1f}% | {r['f1']*100:.1f}%\n"
        
    with open(REPORT_OUT, 'w') as f:
        f.write(report)
        
    print(f"✅ Saved full dataset evaluation report to {REPORT_OUT}")

if __name__ == "__main__":
    main()
