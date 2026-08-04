#!/usr/bin/env python3
"""
verify_ground_truth_counts.py — Verify ground-truth shot class counts using normalise_shot_type
"""
import os
import sys
import glob
import json
from collections import Counter

ROOT_DIR = "/Users/neilkloot/Code/CricketBattingTracker"
BASE_DIR = "/Users/neilkloot/Code/Batting Sensor Stats"
SESSIONS_DIR = os.path.join(BASE_DIR, "live_watch_sessions")

sys.path.append(os.path.join(ROOT_DIR, "pipelines"))
from build_unified_dataset import normalise_shot_type

pattern = os.path.join(SESSIONS_DIR, "session_2026-*")
session_dirs = sorted([d for d in glob.glob(pattern) if os.path.isdir(d)])

print(f"Auditing ground-truth shot classes using normalise_shot_type across {len(session_dirs)} sessions...")

gt_counts = Counter()

for sdir in session_dirs:
    n_path = os.path.join(sdir, "narrations_raw.json")
    if os.path.exists(n_path):
        narr = json.load(open(n_path))
        for e in narr:
            st = e.get('shot_type', '')
            norm = normalise_shot_type(st)
            if norm and norm != 'Leave':
                gt_counts[norm] += 1

print("\n============================================================")
print("  CORRECT GROUND-TRUTH SHOT CLASS COUNTS (ALL 45 SESSIONS)")
print("============================================================")
for cls_name, count in gt_counts.most_common():
    print(f"  {cls_name:<10}: {count:4d} shots")
print(f"  TOTAL     : {sum(gt_counts.values()):4d} shots")
