#!/usr/bin/env python3
"""
pipelines/retroactive_bat_tagger.py

Retrospectively parses audio narration transcripts (raw_transcript.txt) and existing
ground truth annotations across all historical sessions in live_watch_sessions.

Identifies:
  1. Bat announcements and transitions across practice rounds.
  2. Maps each session to physical bat profiles:
     - Bat 1: "Game bat", 1425g, knob: 31cm, toe: 57cm
     - Bat 2: "Gray Nicholls Giant", 1625g, knob: 31cm, toe: 57cm
     - Bat 3: "Eye in bat", 1200g, knob: 31cm, toe: 55cm
  3. Writes/updates session_config.json in each session folder.
  4. Augments ground_truth_aligned.csv with:
     - bat_id (1, 2, 3)
     - bat_name ("Game bat", "Gray Nicholls Giant", "Eye in bat")
     - bat_weight_grams (1425.0, 1625.0, 1200.0)
     - bat_sensor_offset_knob_cm (31.0)
     - bat_sensor_offset_toe_cm (57.0 or 55.0)

Usage:
  python3 pipelines/retroactive_bat_tagger.py --dry-run
  python3 pipelines/retroactive_bat_tagger.py --apply
  python3 pipelines/retroactive_bat_tagger.py --session session_2026-06-14_13-16-12 --apply
"""

import os
import sys
import glob
import re
import json
import argparse
import datetime
import pandas as pd
import numpy as np

SESSIONS_DIR = "/Users/neilkloot/Code/Batting Sensor Stats/live_watch_sessions"

BAT_SPECS = {
    1: {
        "bat_id": 1,
        "name": "Game bat",
        "weight_grams": 1425.0,
        "sensor_offset_from_knob_cm": 31.0,
        "sensor_offset_from_toe_cm": 57.0
    },
    2: {
        "bat_id": 2,
        "name": "Gray Nicholls Giant",
        "weight_grams": 1625.0,
        "sensor_offset_from_knob_cm": 31.0,
        "sensor_offset_from_toe_cm": 57.0
    },
    3: {
        "bat_id": 3,
        "name": "Eye in bat",
        "weight_grams": 1200.0,
        "sensor_offset_from_knob_cm": 31.0,
        "sensor_offset_from_toe_cm": 55.0
    }
}

DEFAULT_BAT_PROFILES = [BAT_SPECS[1], BAT_SPECS[2], BAT_SPECS[3]]


def parse_session_start_ms(session_dir):
    name = os.path.basename(session_dir)
    m = re.match(r"session[-_](\d{4})-(\d{2})-(\d{2})_(\d{2})[-_](\d{2})[-_](\d{2})", name)
    if m:
        parts = [int(x) for x in m.groups()]
        dt = datetime.datetime(parts[0], parts[1], parts[2], parts[3], parts[4], parts[5])
        return int(dt.timestamp() * 1000)
    return int(os.path.getmtime(session_dir) * 1000)


def map_bat_name_to_id(text):
    if not isinstance(text, str):
        return None
    t = text.lower()
    if any(k in t for k in ["gray", "giant"]):
        return 2
    if any(k in t for k in ["eye", "iron", "thin", "light"]):
        return 3
    if any(k in t for k in ["game"]):
        return 1
    return None


def parse_transcript_timeline(transcript_path):
    """
    Parses raw_transcript.txt and returns:
      - detected_cues: list of (time_s, bat_id, raw_line)
      - round_announcements: list of (time_s, round_num, raw_line)
    """
    if not os.path.exists(transcript_path):
        return [], []

    detected_cues = []
    round_announcements = []

    with open(transcript_path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if not line or ":" not in line:
                continue
            t_str, text = line.split(":", 1)
            t_parts = t_str.strip().split(".")
            if len(t_parts) != 3:
                continue
            try:
                sec = int(t_parts[0]) * 60 + int(t_parts[1]) + int(t_parts[2]) / 100.0
            except ValueError:
                continue

            t_lower = text.strip().lower()

            # Check for round announcement
            round_num = None
            if re.search(r"\bround\s+(one|1)\b", t_lower):
                round_num = 1
            elif re.search(r"\bround\s+(two|2)\b", t_lower):
                round_num = 2
            elif re.search(r"\bround\s+(three|3)\b", t_lower):
                round_num = 3

            if round_num is not None:
                round_announcements.append((sec, round_num, text.strip()))

            # Check for bat mentions (pick last mentioned if multiple, e.g. self-correction)
            cues_in_line = []
            for bid, words in [
                (3, ["iron bat", "eye in", "thin bat", "light bat", "onion bat", "i in bat", "iron back", "eye invert", "eye invas", "my impact", "eye in bath"]),
                (2, ["gray nicolls", "gray nicholls", "giant", "gray mix", "mister gray", "gray back", "trusty gray", "heavy bat"]),
                (1, ["game bat", "game day bat", "game back", "same bat", "normal bat", "standard bat"])
            ]:
                for w in words:
                    pos = t_lower.rfind(w)
                    if pos != -1:
                        cues_in_line.append((pos, bid))

            if cues_in_line:
                cues_in_line.sort()
                bat_id = cues_in_line[-1][1]
                detected_cues.append((sec, bat_id, text.strip()))

    return detected_cues, round_announcements


def resolve_bat_timeline(session_dir, session_start_ms):
    """
    Resolves the initial_bat_id and list of bat_switches for a session.
    Returns:
      (initial_bat_id, bat_switches)
      where bat_switches is a list of {"timestamp_ms": int, "bat_id": int}
    """
    gt_file = os.path.join(session_dir, "ground_truth_aligned.csv")
    tf_file = os.path.join(session_dir, "raw_transcript.txt")

    # Strategy 1: If ground_truth_aligned.csv already has a populated "bat" column
    if os.path.exists(gt_file):
        try:
            df = pd.read_csv(gt_file)
            if "bat" in df.columns and df["bat"].dropna().count() > 0:
                time_col = None
                for c in ["sensor_narr_time_seconds", "audio_time_seconds", "impact_time_seconds"]:
                    if c in df.columns:
                        time_col = c
                        break

                df_clean = df.copy()
                df_clean["mapped_bat_id"] = df_clean["bat"].apply(map_bat_name_to_id)
                df_clean["mapped_bat_id"] = df_clean["mapped_bat_id"].ffill().bfill()
                valid_mapped = df_clean["mapped_bat_id"].dropna()

                if not valid_mapped.empty:
                    initial_bat_id = int(valid_mapped.iloc[0])
                    switches = []
                    prev_bat = initial_bat_id

                    for idx, row in df_clean.iterrows():
                        bid = row["mapped_bat_id"]
                        if pd.notna(bid) and int(bid) != prev_bat:
                            t_sec = float(row[time_col]) if time_col and pd.notna(row[time_col]) else (idx * 5.0)
                            sw_ms = session_start_ms + int(t_sec * 1000)
                            switches.append({
                                "timestamp_ms": sw_ms,
                                "timestamp_offset_s": round(float(t_sec), 2),
                                "bat_id": int(bid)
                            })
                            prev_bat = int(bid)

                    return initial_bat_id, switches
        except Exception:
            pass

    # Strategy 2: Infer from raw_transcript.txt
    detected_cues, round_announcements = parse_transcript_timeline(tf_file)

    if detected_cues:
        # Check round 1, round 2, round 3 matches
        round_bats = {}
        for r_sec, r_num, r_txt in round_announcements:
            # Find closest cue within 45s
            nearby_cues = [c for c in detected_cues if abs(c[0] - r_sec) < 45.0]
            if nearby_cues:
                round_bats[r_num] = (r_sec, nearby_cues[0][1])

        # If cues exist without explicit rounds, use cues directly
        if not round_bats:
            cues_sorted = sorted(detected_cues, key=lambda x: x[0])
            initial_bat_id = cues_sorted[0][1]
            switches = []
            prev_bat = initial_bat_id
            for sec, bid, _ in cues_sorted:
                if bid != prev_bat:
                    sw_ms = session_start_ms + int(sec * 1000)
                    switches.append({
                        "timestamp_ms": sw_ms,
                        "timestamp_offset_s": round(float(sec), 2),
                        "bat_id": bid
                    })
                    prev_bat = bid
            return initial_bat_id, switches

        # Handle round deduction
        # Standard 3-round rotation: (3 or 2) -> (2 or 3) -> 1
        known_bats = {b for _, b in round_bats.values()}
        missing_bats = [b for b in [1, 2, 3] if b not in known_bats]

        # Deduce round 1 if unknown but round 2 & 3 known
        if 1 not in round_bats and 2 in round_bats and 3 in round_bats:
            round_bats[1] = (0.0, missing_bats[0] if missing_bats else 3)
        elif 1 not in round_bats and 2 in round_bats:
            r2_bat = round_bats[2][1]
            r1_bat = 3 if r2_bat == 2 else 2
            round_bats[1] = (0.0, r1_bat)

        # Deduce round 3 if unknown
        if 3 not in round_bats and 2 in round_bats:
            r3_ann = [r for r in round_announcements if r[1] == 3]
            if r3_ann:
                round_bats[3] = (r3_ann[0][0], 1)

        # Build switches from round_bats
        rounds_sorted = sorted(round_bats.items(), key=lambda x: x[1][0])
        initial_bat_id = rounds_sorted[0][1][1]
        switches = []
        prev_bat = initial_bat_id
        for r_num, (sec, bid) in rounds_sorted:
            if bid != prev_bat:
                sw_ms = session_start_ms + int(sec * 1000)
                switches.append({
                    "timestamp_ms": sw_ms,
                    "timestamp_offset_s": round(float(sec), 2),
                    "bat_id": bid
                })
                prev_bat = bid

        return initial_bat_id, switches

    # Strategy 3: Default to Game Bat (Bat 1) with no switches
    return 1, []


def update_session_files(session_dir, initial_bat_id, bat_switches, dry_run=True):
    session_start_ms = parse_session_start_ms(session_dir)
    config_file = os.path.join(session_dir, "session_config.json")
    gt_file = os.path.join(session_dir, "ground_truth_aligned.csv")

    # Read existing config if present
    polar_mount_mode = "NONE"
    if os.path.isdir(os.path.join(session_dir, "PolarSense")):
        polar_mount_mode = "WRIST"
    if os.path.exists(config_file):
        try:
            with open(config_file, "r") as f:
                cfg = json.load(f)
                polar_mount_mode = cfg.get("polar_mount_mode", polar_mount_mode)
        except Exception:
            pass

    config_data = {
        "polar_mount_mode": polar_mount_mode,
        "initial_bat_id": initial_bat_id,
        "bat_profiles": DEFAULT_BAT_PROFILES,
        "bat_switches": bat_switches
    }

    if not dry_run:
        with open(config_file, "w") as f:
            json.dump(config_data, f, indent=2)

    # Update ground_truth_aligned.csv
    updated_gt = False
    if os.path.exists(gt_file):
        try:
            df = pd.read_csv(gt_file)
            time_col = None
            for c in ["sensor_narr_time_seconds", "audio_time_seconds", "impact_time_seconds"]:
                if c in df.columns:
                    time_col = c
                    break

            bat_id_col = []
            bat_name_col = []
            bat_weight_col = []
            bat_knob_col = []
            bat_toe_col = []

            for idx, row in df.iterrows():
                # Resolve bat for row
                t_sec = float(row[time_col]) if time_col and pd.notna(row[time_col]) else (idx * 5.0)
                row_ms = session_start_ms + int(t_sec * 1000)

                # Find active bat
                active_bid = initial_bat_id
                for sw in sorted(bat_switches, key=lambda x: x["timestamp_ms"]):
                    if sw["timestamp_ms"] <= row_ms:
                        active_bid = sw["bat_id"]

                # If row had an explicit valid bat name that differs, respect it
                if "bat" in row and pd.notna(row["bat"]):
                    explicit_id = map_bat_name_to_id(row["bat"])
                    if explicit_id is not None:
                        active_bid = explicit_id

                spec = BAT_SPECS.get(active_bid, BAT_SPECS[1])
                bat_id_col.append(active_bid)
                bat_name_col.append(spec["name"])
                bat_weight_col.append(spec["weight_grams"])
                bat_knob_col.append(spec["sensor_offset_from_knob_cm"])
                bat_toe_col.append(spec["sensor_offset_from_toe_cm"])

            df["bat_id"] = bat_id_col
            df["bat_name"] = bat_name_col
            df["bat_weight_grams"] = bat_weight_col
            df["bat_sensor_offset_knob_cm"] = bat_knob_col
            df["bat_sensor_offset_toe_cm"] = bat_toe_col

            if not dry_run:
                df.to_csv(gt_file, index=False)
            updated_gt = True
        except Exception as e:
            print(f"    Error updating GT file: {e}")

    return config_data, updated_gt


def main():
    parser = argparse.ArgumentParser(description="Retroactive Bat Tagger")
    parser.add_argument("--dry-run", action="store_true", default=False, help="Preview without writing")
    parser.add_argument("--apply", action="store_true", default=False, help="Write session_config.json and update ground_truth_aligned.csv")
    parser.add_argument("--session", type=str, default=None, help="Target specific session directory name")
    args = parser.parse_args()

    if not args.apply and not args.dry_run:
        args.dry_run = True

    session_dirs = sorted(glob.glob(os.path.join(SESSIONS_DIR, "session-*")) +
                          glob.glob(os.path.join(SESSIONS_DIR, "session_*")))
    session_dirs = sorted(list(set(session_dirs)))

    if args.session:
        session_dirs = [d for d in session_dirs if os.path.basename(d) == args.session]

    mode_label = "DRY-RUN (Preview)" if args.dry_run else "APPLY (Writing Files)"
    print(f"\n=======================================================")
    print(f"🏏 Retroactive Bat Tagger [{mode_label}]")
    print(f"Total sessions to process: {len(session_dirs)}")
    print(f"=======================================================\n")

    stats = {
        "multi_bat": 0,
        "single_bat": 0,
        "default_bat": 0,
        "gt_updated": 0
    }

    for sdir in session_dirs:
        sname = os.path.basename(sdir)
        start_ms = parse_session_start_ms(sdir)
        init_bat, switches = resolve_bat_timeline(sdir, start_ms)

        init_spec = BAT_SPECS[init_bat]
        num_switches = len(switches)

        if num_switches > 0:
            stats["multi_bat"] += 1
            sw_str = ", ".join([f"{BAT_SPECS[sw['bat_id']]['name']} (+{(sw['timestamp_ms'] - start_ms)/1000.0:.1f}s)" for sw in switches])
            print(f"[{sname}]")
            print(f"  Initial Bat: Bat {init_bat} ({init_spec['name']}, {init_spec['weight_grams']}g)")
            print(f"  Switches ({num_switches}): {sw_str}")
        else:
            if init_bat != 1:
                stats["single_bat"] += 1
                print(f"[{sname}] Single-bat: Bat {init_bat} ({init_spec['name']}, {init_spec['weight_grams']}g)")
            else:
                stats["default_bat"] += 1

        cfg, gt_ok = update_session_files(sdir, init_bat, switches, dry_run=args.dry_run)
        if gt_ok:
            stats["gt_updated"] += 1

    print(f"\n=======================================================")
    print(f"📊 Summary:")
    print(f"  Total Sessions Processed: {len(session_dirs)}")
    print(f"  Multi-Bat Switch Sessions: {stats['multi_bat']}")
    print(f"  Specific Single-Bat Sessions: {stats['single_bat']}")
    print(f"  Default Game-Bat Sessions: {stats['default_bat']}")
    print(f"  Ground Truth CSVs Processed: {stats['gt_updated']}")
    print(f"=======================================================\n")


if __name__ == "__main__":
    main()
