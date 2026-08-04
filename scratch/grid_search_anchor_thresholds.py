#!/usr/bin/env python3
"""
grid_search_anchor_thresholds.py — Grid Search for Stage 1 Impact Thresholds across All 45 Sessions

Goal: Optimize Defence Recall & Overall Recall while controlling over-detection.
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

print(f"Loading sensor data for {len(all_sessions)} sessions...")
session_cache = []

for sname in all_sessions:
    p = os.path.join(DATASET_DIR, f"{sname}_unified.parquet")
    df = pd.read_parquet(p)
    if df.empty or len(df) < 100: continue
    
    w_acc_mags  = np.linalg.norm(df[['w_acc_x','w_acc_y','w_acc_z']].fillna(0).values, axis=1)
    w_gyro_mags = np.linalg.norm(df[['w_gyro_x','w_gyro_y','w_gyro_z']].fillna(0).values, axis=1)
    
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
        'gt_events': gt_events
    })

print(f"Loaded {len(session_cache)} valid sessions with ground truth!")

print("\n============================================================")
print("  STAGE 1 ANCHOR THRESHOLD GRID SEARCH")
print("============================================================")
print(f"{'Acc Thresh':<11} | {'Gyro Thresh':<12} | {'Total Dets':<10} | {'Over-Det Factor':<16} | {'Overall Rec (%)':<15} | {'Defence Rec (%)':<15} | {'Prec (%)':<9} | {'F1 (%)'}")
print("-"*120)

for min_acc in [25.0, 30.0, 35.0, 40.0, 45.0]:
    for min_gyro in [3.0, 4.0, 5.0, 6.0, 6.5]:
        tot_gt = 0
        tot_def_gt = 0
        tot_det = 0
        tot_matched_gt = 0
        tot_matched_def_gt = 0
        tot_matched_det = 0
        
        for s in session_cache:
            w_acc = s['w_acc']
            w_gyro = s['w_gyro']
            gt_events = s['gt_events']
            
            impact_mask = (w_acc >= min_acc) & (w_gyro >= min_gyro)
            impact_frames = np.where(impact_mask)[0]
            
            anchors = []
            if len(impact_frames) > 0:
                cluster = [impact_frames[0]]
                for idx in range(1, len(impact_frames)):
                    if impact_frames[idx] - impact_frames[idx-1] <= 423:
                        cluster.append(impact_frames[idx])
                    else:
                        peak_f = cluster[np.argmax(w_acc[cluster])]
                        anchors.append(peak_f)
                        cluster = [impact_frames[idx]]
                if cluster:
                    peak_f = cluster[np.argmax(w_acc[cluster])]
                    anchors.append(peak_f)
                    
            det_secs = [f / 423.0 for f in anchors]
            
            tot_gt += len(gt_events)
            def_gts = [gt for gt in gt_events if gt['cls'] == 'Defence']
            tot_def_gt += len(def_gts)
            tot_det += len(det_secs)
            
            # Overall recall
            m_gt = sum(1 for gt in gt_events if any(abs(d - gt['sec']) <= 2.5 for d in det_secs))
            tot_matched_gt += m_gt
            
            # Defence recall
            m_def_gt = sum(1 for gt in def_gts if any(abs(d - gt['sec']) <= 2.5 for d in det_secs))
            tot_matched_def_gt += m_def_gt
            
            # Precision
            m_det = sum(1 for d in det_secs if any(abs(d - gt['sec']) <= 2.5 for gt in gt_events))
            tot_matched_det += m_det
            
        over_det_factor = tot_det / tot_gt if tot_gt else 0
        rec = tot_matched_gt / tot_gt * 100.0 if tot_gt else 0
        def_rec = tot_matched_def_gt / tot_def_gt * 100.0 if tot_def_gt else 0
        prec = tot_matched_det / tot_det * 100.0 if tot_det else 0
        f1 = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0
        
        print(f"Acc >= {min_acc:4.1f} | Gyro >= {min_gyro:4.1f} | {tot_det:10d} | {over_det_factor:16.2f}x | {rec:15.1f}% | {def_rec:15.1f}% | {prec:9.1f}% | {f1:5.1f}%")
