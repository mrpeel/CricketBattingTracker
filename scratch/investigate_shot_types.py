#!/usr/bin/env python3
"""
investigate_shot_types.py — Audit all narration shot types across 45 sessions
"""
import os
import glob
import json
import pandas as pd
from collections import Counter

BASE_DIR = "/Users/neilkloot/Code/Batting Sensor Stats"
SESSIONS_DIR = os.path.join(BASE_DIR, "live_watch_sessions")
UNIFIED_DIR = os.path.join(BASE_DIR, "poc_unified_dataset")

pattern = os.path.join(SESSIONS_DIR, "session_2026-*")
session_dirs = sorted([d for d in glob.glob(pattern) if os.path.isdir(d)])

print(f"Auditing narration raw JSON files across {len(session_dirs)} sessions...")

raw_shot_counts = Counter()
session_shot_map = {}

for sdir in session_dirs:
    sname = os.path.basename(sdir)
    n_path = os.path.join(sdir, "narrations_raw.json")
    if os.path.exists(n_path):
        try:
            narr = json.load(open(n_path))
            shots_in_s = []
            for e in narr:
                st = e.get('shot_type', '')
                if st:
                    raw_shot_counts[st] += 1
                    shots_in_s.append(st)
            session_shot_map[sname] = shots_in_s
        except Exception as ex:
            print(f"Error reading {sname}: {ex}")

print("\n============================================================")
print("  RAW NARRATION SHOT TYPE FREQUENCIES (narrations_raw.json)")
print("============================================================")
for st, count in raw_shot_counts.most_common():
    print(f"  '{st}': {count}")

print("\n============================================================")
print("  PARQUET DATASET LABEL FREQUENCIES (poc_unified_dataset)")
print("============================================================")
parquet_files = sorted(glob.glob(os.path.join(UNIFIED_DIR, "*_unified.parquet")))
parquet_files = [f for f in parquet_files if '_aug_' not in f]

parquet_label_counts = Counter()
for pf in parquet_files:
    df = pd.read_parquet(pf)
    if 'label' in df.columns:
        counts = df['label'].value_counts().to_dict()
        for k, v in counts.items():
            parquet_label_counts[k] += v

for lbl, count in parquet_label_counts.most_common():
    print(f"  '{lbl}': {count} frames")
