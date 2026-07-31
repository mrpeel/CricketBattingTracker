#!/usr/bin/env python3
"""
test_burst_mode_hysteresis.py — Python Simulation of Burst Mode Adaptive Hysteresis Gate

Evaluates:
1. Tightened Pre-Shot Stillness Window: [-0.8s, -0.2s] (254 frames at 423 Hz).
2. Dynamic Hysteresis State Machine:
   - Delta T < 8.0s (Burst Mode): Stillness Threshold <= 0.25 (Relaxed for rapid feeds)
   - Delta T >= 8.0s (Rest Mode): Stillness Threshold <= 0.12 (Strict to reject walking/reloading)
Across ALL 45 Physical Sessions in the dataset.
"""
import os
import sys
import glob
import json
import numpy as np
import pandas as pd
import torch

ROOT_DIR = "/Users/neilkloot/Code/CricketBattingTracker"
BASE_DIR = "/Users/neilkloot/Code/Batting Sensor Stats"
DATASET_DIR = os.path.join(BASE_DIR, "poc_unified_dataset")
SESSIONS_DIR = os.path.join(BASE_DIR, "live_watch_sessions")

sys.path.append(os.path.join(ROOT_DIR, "pipelines"))
from build_unified_dataset import normalise_shot_type

pattern = os.path.join(DATASET_DIR, "session_2026-*_unified.parquet")
all_sessions = sorted([os.path.basename(p).replace("_unified.parquet","") for p in glob.glob(pattern) if '_aug_' not in p])

print(f"Loading sensor data for {len(all_sessions)} physical sessions...")
session_cache = []

for sname in all_sessions:
    p = os.path.join(DATASET_DIR, f"{sname}_unified.parquet")
    df = pd.read_parquet(p)
    if df.empty or len(df) < 100: continue
    
    w_acc_mags  = np.linalg.norm(df[['w_acc_x','w_acc_y','w_acc_z']].fillna(0).values, axis=1)
    w_gyro_mags = np.linalg.norm(df[['w_gyro_x','w_gyro_y','w_gyro_z']].fillna(0).values, axis=1)
    
    # Calculate pre-shot angular velocity std over sliding [-0.8s, -0.2s] window (254 frames)
    # Using pandas rolling std
    gyro_std_254 = pd.Series(w_gyro_mags).rolling(window=254, min_periods=50).std().shift(85).fillna(0.0).values
    
    sdir = os.path.join(SESSIONS_DIR, sname)
    narr_path = os.path.join(sdir, "narrations_raw.json")
    gt_events = []
    if os.path.exists(narr_path):
        narr = json.load(open(narr_path))
        for e in narr:
            st = e.get('shot_type', '')
            gt_cls = normalise_shot_type(st)
            if gt_cls and gt_cls != 'Leave':
                gt_events.append({'sec': float(e['timestamp_seconds']), 'cls': gt_cls})
                
    session_cache.append({
        'name': sname,
        'w_acc': w_acc_mags,
        'w_gyro': w_gyro_mags,
        'gyro_std': gyro_std_254,
        'gt_events': gt_events,
        'duration_min': len(df) / 423.0 / 60.0
    })

print(f"Loaded {len(session_cache)} valid sessions ({sum(s['duration_min'] for s in session_cache):.1f} total minutes)!")

def run_simulation(enable_burst_hysteresis=True, strict_limit=0.12, relaxed_limit=0.25, burst_delta_sec=8.0):
    tot_gt = 0
    tot_def_gt = 0
    tot_det = 0
    tot_matched_gt = 0
    tot_matched_def_gt = 0
    tot_matched_det = 0
    
    for s in session_cache:
        w_acc = s['w_acc']
        w_gyro = s['w_gyro']
        gyro_std = s['gyro_std']
        gt_events = s['gt_events']
        
        # Stage 1 Baseline Anchor Detection: Acc >= 30.0, Gyro >= 4.0
        impact_mask = (w_acc >= 30.0) & (w_gyro >= 4.0)
        impact_frames = np.where(impact_mask)[0]
        
        raw_anchors = []
        if len(impact_frames) > 0:
            cluster = [impact_frames[0]]
            for idx in range(1, len(impact_frames)):
                if impact_frames[idx] - impact_frames[idx-1] <= 423:
                    cluster.append(impact_frames[idx])
                else:
                    peak_f = cluster[np.argmax(w_acc[cluster])]
                    raw_anchors.append(peak_f)
                    cluster = [impact_frames[idx]]
            if cluster:
                peak_f = cluster[np.argmax(w_acc[cluster])]
                raw_anchors.append(peak_f)
                
        # Apply Adaptive Burst-Mode Hysteresis Gate
        verified_anchors = []
        last_verified_sec = -999.0
        
        for f in raw_anchors:
            candidate_sec = f / 423.0
            pre_stillness_std = gyro_std[f]
            
            if enable_burst_hysteresis:
                delta_t = candidate_sec - last_verified_sec
                # Dynamic Threshold Selection
                if delta_t < burst_delta_sec:
                    # Burst Mode: Relaxed Threshold
                    thresh = relaxed_limit
                else:
                    # Rest Mode: Strict Threshold
                    thresh = strict_limit
                    
                if pre_stillness_std <= thresh or delta_t < 2.0:
                    verified_anchors.append(f)
                    last_verified_sec = candidate_sec
            else:
                verified_anchors.append(f)
                
        det_secs = [f / 423.0 for f in verified_anchors]
        
        tot_gt += len(gt_events)
        def_gts = [gt for gt in gt_events if gt['cls'] == 'Defence']
        tot_def_gt += len(def_gts)
        tot_det += len(det_secs)
        
        # Recall & Precision
        m_gt = sum(1 for gt in gt_events if any(abs(d - gt['sec']) <= 2.5 for d in det_secs))
        tot_matched_gt += m_gt
        
        m_def_gt = sum(1 for gt in def_gts if any(abs(d - gt['sec']) <= 2.5 for d in det_secs))
        tot_matched_def_gt += m_def_gt
        
        m_det = sum(1 for d in det_secs if any(abs(d - gt['sec']) <= 2.5 for gt in gt_events))
        tot_matched_det += m_det
        
    rec = tot_matched_gt / tot_gt * 100.0 if tot_gt else 0
    def_rec = tot_matched_def_gt / tot_def_gt * 100.0 if tot_def_gt else 0
    prec = tot_matched_det / tot_det * 100.0 if tot_det else 0
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0
    over_det = tot_det / tot_gt if tot_gt else 0
    
    return {
        'total_gt': tot_gt,
        'total_det': tot_det,
        'over_det_factor': over_det,
        'recall': rec,
        'def_recall': def_rec,
        'precision': prec,
        'f1': f1
    }

print("\n============================================================")
print("  BURST MODE ADAPTIVE HYSTERESIS SIMULATION RESULTS")
print("============================================================")

res_base = run_simulation(enable_burst_hysteresis=False)
print(f"1. BASELINE (No Burst Gate):")
print(f"   Detections: {res_base['total_det']} ({res_base['over_det_factor']:.2f}x GT)")
print(f"   Overall Recall: {res_base['recall']:.1f}%")
print(f"   Defence Recall: {res_base['def_recall']:.1f}%")
print(f"   Precision: {res_base['precision']:.1f}%")
print(f"   F1 Score: {res_base['f1']:.1f}%")

print("\n2. TESTING HYSTERESIS THRESHOLD COMBINATIONS:")
print(f"{'Strict (Rest)':<13} | {'Relaxed (Burst)':<15} | {'Delta T (s)':<11} | {'Detections':<10} | {'Over-Det':<9} | {'Recall (%)':<11} | {'Def Rec (%)':<12} | {'Prec (%)':<9} | {'F1 (%)'}")
print("-"*115)

for s_lim in [1.8, 2.0, 2.2, 2.5, 2.8, 3.0]:
    for r_lim in [3.0, 4.0, 5.0]:
        for dt_sec in [8.0, 10.0, 12.0]:
            r = run_simulation(enable_burst_hysteresis=True, strict_limit=s_lim, relaxed_limit=r_lim, burst_delta_sec=dt_sec)
            print(f"{s_lim:<13.2f} | {r_lim:<15.2f} | {dt_sec:<11.1f} | {r['total_det']:10d} | {r['over_det_factor']:8.2f}x | {r['recall']:11.1f}% | {r['def_recall']:12.1f}% | {r['precision']:8.1f}% | {r['f1']:5.1f}%")
