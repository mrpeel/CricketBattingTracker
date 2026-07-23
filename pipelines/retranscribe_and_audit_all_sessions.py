#!/usr/bin/env python3
"""
Batch Session Transcription & Lexicon Audit Runner
Scans all local live watch sessions, parses audio transcripts using ground_truth_lexicon.json,
checks timestamp boundaries and shot numbering continuity, and reports audit status.
"""

import os
import sys
import glob
import json
import re
import pandas as pd
import numpy as np

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(ROOT_DIR)

from automate_pipeline import parse_raw_transcript, load_ground_truth_lexicon, load_watch_sensor

SESSIONS_DIR = "/Users/neilkloot/Code/Batting Sensor Stats/live_watch_sessions"

def get_audio_duration_seconds(audio_path):
    if not os.path.exists(audio_path):
        return None
    try:
        import subprocess
        res = subprocess.run(["afinfo", audio_path], capture_output=True, text=True)
        if res.returncode == 0:
            m = re.search(r"estimated duration:\s*([\d\.]+)\s*sec", res.stdout)
            if m:
                return float(m.group(1))
    except Exception as e:
        pass
    return None

def audit_session(session_dir):
    session_id = os.path.basename(session_dir)
    audio_files = glob.glob(os.path.join(session_dir, "*.m4a")) + glob.glob(os.path.join(session_dir, "*.mp3"))
    if not audio_files:
        return None

    audio_path = audio_files[0]
    audio_dur = get_audio_duration_seconds(audio_path)
    
    # Load WatchGyroscope for sensor duration limit
    df_gyro = load_watch_sensor(session_dir, "WatchGyroscope")
    gyro_dur = df_gyro.iloc[-1]['seconds_elapsed'] if not df_gyro.empty else (audio_dur or 9999.0)

    raw_transcript_path = os.path.join(session_dir, "raw_transcript.txt")
    if not os.path.exists(raw_transcript_path):
        return {
            "session_id": session_id,
            "status": "❌ NO RAW TRANSCRIPT",
            "audio_dur_s": audio_dur,
            "shots_count": 0,
            "max_shot_num": 0,
            "unmapped_phrases": [],
            "errors": ["raw_transcript.txt missing"]
        }

    with open(raw_transcript_path, "r", encoding="utf-8") as f:
        raw_text = f.read()

    # Parse using Stage 2 rules with max_audio_seconds=gyro_dur
    narrations = parse_raw_transcript(raw_text, max_audio_seconds=gyro_dur)
    
    shots = [x for x in narrations if x.get("shot_type") not in ["Facing up", "No shot", "Leave", "Evade"]]
    
    max_shot_num = max([x["shot_number"] for x in shots if x.get("shot_number")], default=0)
    
    # Check for unmapped utterances
    lexicon = load_ground_truth_lexicon()
    unmapped = []
    lines = raw_text.splitlines()
    for line in lines:
        line = line.strip()
        m = re.match(r"^\[?([\d\.:]+)\]?\s*:\s*(.*)$", line)
        if m:
            text = m.group(2).strip()
            text_lower = text.lower()
            if any(h in text_lower for h in ["round ", "end of round", "end of session", "check ", "one, two"]):
                continue
            matched = False
            for canonical, variants in lexicon.items():
                if any(v.lower() in text_lower for v in variants):
                    matched = True
                    break
            if not matched and not any(q in text_lower for q in ["good", "okay", "ok", "poor", "excellent", "perfect", "edge", "edged", "miss", "missed"]):
                unmapped.append(text)

    errors = []
    if len(shots) == 0:
        errors.append("Zero active shots parsed")
    if max_shot_num > 0 and max_shot_num != len(shots):
        errors.append(f"Shot count mismatch (Max narrated: #{max_shot_num}, Parsed: {len(shots)})")

    status = "🟢 PASSED" if not errors and not unmapped else ("⚠️ REQUIRES REVIEW" if unmapped else "❌ ERROR")

    return {
        "session_id": session_id,
        "status": status,
        "audio_dur_s": audio_dur,
        "shots_count": len(shots),
        "max_shot_num": max_shot_num,
        "unmapped_phrases": list(set(unmapped)),
        "errors": errors
    }

def main():
    session_dirs = sorted([d for d in glob.glob(os.path.join(SESSIONS_DIR, "*")) if os.path.isdir(d)])
    print("=" * 110)
    print(f"📊 BATCH AUDIO TRANSCRIPTION & GROUND-TRUTH LEXICON AUDIT ({len(session_dirs)} sessions)")
    print("=" * 110)
    print(f"{'Session Directory':<32} | {'Status':<18} | {'Audio Dur':<10} | {'Shots':<6} | {'Max #':<6} | {'Issues / Unmapped'}")
    print("-" * 110)

    total_audited = 0
    passed_count = 0

    for s_dir in session_dirs:
        res = audit_session(s_dir)
        if res is None:
            continue
        total_audited += 1
        if "PASSED" in res["status"]:
            passed_count += 1
            
        dur_str = f"{res['audio_dur_s']/60:.1f}m" if res['audio_dur_s'] else "N/A"
        issues_str = ""
        if res["errors"]:
            issues_str += "; ".join(res["errors"])
        if res["unmapped_phrases"]:
            if issues_str:
                issues_str += " | "
            issues_str += f"Unmapped: {res['unmapped_phrases'][:2]}"

        print(f"{res['session_id']:<32} | {res['status']:<18} | {dur_str:<10} | {res['shots_count']:<6} | #{res['max_shot_num']:<5} | {issues_str}")

    print("=" * 110)
    print(f"✅ Audit Summary: {passed_count}/{total_audited} sessions passed clean ground-truth validation.")
    print("=" * 110)

if __name__ == "__main__":
    main()
