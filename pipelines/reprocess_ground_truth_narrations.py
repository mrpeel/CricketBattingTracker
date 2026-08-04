#!/usr/bin/env python3
"""
pipelines/reprocess_ground_truth_narrations.py — Ground Truth Position-Constrained Parser & Compound Splitting

1. Position-Constrained Lexicon Matching:
   - A shot keyword match is valid ONLY if it appears at/near the start of the utterance
     (character start index <= 15 / within the first 3 words).
   - Discards ambient conversational chatter where keywords appear deep in sentences
     (e.g., "3 what matas what do think right...").
2. Compound Entry Splitting:
   - When an utterance starts with a valid shot narration and ends with "facing up"
     (e.g., "flick shot okay facing up"):
       * Event 1: Shot event at T_shot.
       * Event 2: "Facing up" stance event generated at T_shot + 1.0s.
3. Database & Dataset Refresh:
   - Updates narrations_raw.json and ground_truth_aligned.csv across all sessions.
   - Rebuilds facing_up_sessions_423hz.pkl.
   - Executes run_multitier_pipeline.py and prints updated scorecard.
"""

import os
import sys
import json
import glob
import re
import subprocess
import numpy as np
import pandas as pd

ROOT_DIR = "/Users/neilkloot/Code/CricketBattingTracker"
BASE_DIR = "/Users/neilkloot/Code/Batting Sensor Stats"
SESSIONS_DIR = os.path.join(BASE_DIR, "live_watch_sessions")
LEXICON_PATH = os.path.join(ROOT_DIR, "docs", "ground_truth_lexicon.json")

sys.path.append(os.path.join(ROOT_DIR, "pipelines"))
from build_unified_dataset import normalise_shot_type

def load_lexicon():
    if os.path.exists(LEXICON_PATH):
        with open(LEXICON_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

LEXICON = load_lexicon()

def parse_utterance_positional(text):
    """
    Parses an utterance string with position constraints.
    Returns: (shot_type, quality, trailing_facing_up)
    """
    if not text:
        return None, None, False
        
    text_clean = text.strip()
    text_lower = text_clean.lower()
    
    # 1. Check if utterance starts with Facing Up
    if text_lower.startswith("facing up") or text_lower.startswith("facing") or text_lower.startswith("pacing up"):
        return "Facing up", "good", False
        
    # 2. Match Shot Type with Position Constraint (must start at index <= 15 / within first 3 words)
    shot_type = None
    match_start_idx = 999
    
    # Check Ground-Truth Lexicon first
    for canonical_term, variants in LEXICON.items():
        for var in variants:
            var_l = var.lower()
            idx = text_lower.find(var_l)
            if idx != -1 and idx < match_start_idx and idx <= 15:
                # Ensure word boundary
                match_start_idx = idx
                shot_type = canonical_term
                
    # Fallback stroke keywords if lexicon didn't match
    if shot_type is None:
        fallback_keywords = [
            ("power drive", "Power drive"), ("cover drive", "Cover drive"),
            ("straight drive", "Straight drive"), ("off drive", "Off drive"),
            ("on drive", "On drive"), ("drive", "Cover drive"),
            ("pull shot", "Pull shot"), ("pull", "Pull shot"), ("hook", "Pull shot"),
            ("flick shot", "Flick shot"), ("flick", "Flick shot"), ("glance", "Glance"),
            ("cut shot", "Cut shot"), ("cut", "Cut shot"), ("punch", "Punch"),
            ("slog", "Slog"), ("sweep", "Sweep"), ("guide", "Guide"),
            ("defense", "Forward defense"), ("defence", "Forward defense"),
            ("block", "Forward defense")
        ]
        for kw, canon in fallback_keywords:
            idx = text_lower.find(kw)
            if idx != -1 and idx < match_start_idx and idx <= 15:
                match_start_idx = idx
                shot_type = canon
                break
                
    if shot_type is None or match_start_idx > 15:
        # Keyword appeared too deep in text or not found -> Ambient chatter
        return None, None, False
        
    # 3. Quality Extraction
    quality = "good"
    if any(q in text_lower for q in ["excellent", "perfect", "nailed", "smoked"]):
        quality = "excellent"
    elif any(q in text_lower for q in ["poor", "bad", "edge", "edged"]):
        quality = "poor"
    elif any(q in text_lower for q in ["miss", "missed", "beaten"]):
        quality = "miss"
    elif any(q in text_lower for q in ["okay", "ok", "decent", "average"]):
        quality = "okay"
        
    # 4. Check trailing Facing Up in compound phrase
    # E.g. "flick shot okay facing up" or "hook shot good facing up"
    trailing_facing_up = False
    facing_idx = text_lower.rfind("facing up")
    if facing_idx == -1:
        facing_idx = text_lower.rfind("facing")
        
    if facing_idx > match_start_idx:
        trailing_facing_up = True
        
    return shot_type, quality, trailing_facing_up

def reprocess_session_narrations(sdir):
    narr_path = os.path.join(sdir, "narrations_raw.json")
    if not os.path.exists(narr_path):
        return 0, 0
        
    with open(narr_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    new_narrations = []
    shot_counter = 1
    split_count = 0
    discard_count = 0
    
    for item in data:
        t_sec = float(item.get("timestamp_seconds", 0.0))
        full_text = item.get("narrated_text") or item.get("text") or ""
        bat = item.get("bat")
        
        shot_type, quality, trailing_facing_up = parse_utterance_positional(full_text)
        
        if shot_type is None:
            discard_count += 1
            continue
            
        if shot_type == "Facing up":
            new_narrations.append({
                "timestamp_seconds": t_sec,
                "shot_number": None,
                "shot_type": "Facing up",
                "quality": "good",
                "bat": bat,
                "narrated_text": full_text
            })
        else:
            # Valid Shot Event
            new_narrations.append({
                "timestamp_seconds": t_sec,
                "shot_number": shot_counter,
                "shot_type": shot_type,
                "quality": quality,
                "bat": bat,
                "narrated_text": full_text
            })
            shot_counter += 1
            
            # Split compound trailing Facing Up
            if trailing_facing_up:
                new_narrations.append({
                    "timestamp_seconds": round(t_sec + 1.0, 2),
                    "shot_number": None,
                    "shot_type": "Facing up",
                    "quality": "good",
                    "bat": bat,
                    "narrated_text": "facing up (auto-split from compound phrase)"
                })
                split_count += 1
                
    # Sort chronologically by timestamp_seconds
    new_narrations.sort(key=lambda x: x["timestamp_seconds"])
    
    # Save updated narrations_raw.json
    with open(narr_path, "w", encoding="utf-8") as f:
        json.dump(new_narrations, f, indent=2)
        
    # Re-generate ground_truth_aligned.csv
    csv_path = os.path.join(sdir, "ground_truth_aligned.csv")
    csv_rows = []
    for item in new_narrations:
        st = item["shot_type"]
        norm_cls = normalise_shot_type(st)
        csv_rows.append({
            "sensor_narr_time_seconds": item["timestamp_seconds"],
            "shot_number": item["shot_number"],
            "shot_type": st,
            "normalised_class": norm_cls,
            "quality": item["quality"],
            "bat": item["bat"],
            "narrated_text": item["narrated_text"]
        })
    pd.DataFrame(csv_rows).to_csv(csv_path, index=False)
    
    return split_count, discard_count

def main():
    print("==========================================================", flush=True)
    print("  REPROCESSING GROUND TRUTH NARRATIONS & COMPOUND SPLITTING", flush=True)
    print("==========================================================", flush=True)
    
    session_dirs = sorted([d for d in glob.glob(os.path.join(SESSIONS_DIR, "*")) if os.path.isdir(d)])
    print(f"Scanning {len(session_dirs)} physical session directories...", flush=True)
    
    total_splits = 0
    total_discards = 0
    
    for sdir in session_dirs:
        sid = os.path.basename(sdir)
        splits, discards = reprocess_session_narrations(sdir)
        total_splits += splits
        total_discards += discards
        if splits > 0 or discards > 0:
            print(f"  • {sid:32s}: Split {splits:2d} compound stance phrases | Discarded {discards:2d} ambient chatter lines", flush=True)
            
    print(f"\n✅ Total Compound Stance Splits Inserted : {total_splits}", flush=True)
    print(f"✅ Total Ambient Chatter Lines Discarded: {total_discards}", flush=True)
    
    # Rebuild facing_up_sessions_423hz.pkl dataset
    print("\n📦 Rebuilding facing_up_sessions_423hz.pkl dataset...", flush=True)
    cmd_build = ["python3", os.path.join(ROOT_DIR, "pipelines", "build_facing_up_dataset.py")]
    res_build = subprocess.run(cmd_build, capture_output=True, text=True)
    if res_build.returncode == 0:
        print("✅ facing_up_sessions_423hz.pkl successfully rebuilt.", flush=True)
    else:
        print(f"❌ Dataset rebuild error: {res_build.stderr}", flush=True)
        sys.exit(1)
        
    # Re-run run_multitier_pipeline.py
    print("\n🚀 Re-evaluating Multi-Tier Pipeline on Clean Ground Truth...", flush=True)
    cmd_eval = ["python3", os.path.join(ROOT_DIR, "pipelines", "run_multitier_pipeline.py")]
    subprocess.run(cmd_eval)

if __name__ == "__main__":
    main()
