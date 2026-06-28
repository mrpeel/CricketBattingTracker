#!/usr/bin/env python3
"""
video_analysis_poc.py — Pitch Analytix Pro
Pulls the most recent video session (MP4) and watch sensor CSVs from the
connected Android device and organises them into the POC folder.

Usage:
    python3 video_analysis_poc.py [--device <serial>] [--output-dir <path>]

Requirements:
    • ADB in PATH and a single Android device connected (or specify --device)
    • The Pitch Analytix phone app must be installed on the device
"""

import argparse
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# ── Configuration ──────────────────────────────────────────────────────────────
APP_PACKAGE          = "com.mrpeel.cricketbattingtracker"
PHONE_VIDEO_DIR      = f"/sdcard/Android/data/{APP_PACKAGE}/files/video_sessions"
WATCH_SENSOR_DIR     = f"/sdcard/Android/data/{APP_PACKAGE}/files/raw_logs"   # same path used by automate_pipeline.py

DEFAULT_OUTPUT_ROOT  = os.path.expanduser(
    "~/Code/Batting Sensor Stats/poc/video_analysis"
)

# ── Helpers ────────────────────────────────────────────────────────────────────

def run(cmd: list[str], check=True, capture=True) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, check=check,
                          capture_output=capture, text=True)


def adb(*args, device: str | None = None) -> subprocess.CompletedProcess:
    prefix = ["adb"]
    if device:
        prefix += ["-s", device]
    return run(prefix + list(args))


def list_adb_devices() -> list[str]:
    result = run(["adb", "devices"])
    lines = result.stdout.strip().splitlines()
    devices = []
    for line in lines[1:]:
        parts = line.split()
        if len(parts) == 2 and parts[1] == "device":
            devices.append(parts[0])
    return devices


def adb_ls(path: str, device: str | None) -> list[str]:
    """Return a list of filenames in the given on-device path, or [] if missing."""
    try:
        result = adb("shell", f"ls {path}", device=device)
        return [f.strip() for f in result.stdout.splitlines() if f.strip()]
    except subprocess.CalledProcessError:
        return []


def adb_pull(src: str, dst: str, device: str | None):
    adb("pull", src, dst, device=device)


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Pull video analysis session from device")
    parser.add_argument("--device",     help="ADB device serial (auto-detected if only one connected)")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_ROOT,
                        help=f"Root output directory (default: {DEFAULT_OUTPUT_ROOT})")
    args = parser.parse_args()

    # ── 1. Validate ADB device ─────────────────────────────────────────────────
    devices = list_adb_devices()
    if not devices:
        print("❌  No ADB device found. Connect your phone and ensure USB debugging is on.")
        sys.exit(1)

    device = args.device
    if device is None:
        if len(devices) > 1:
            print(f"⚠️  Multiple devices found: {devices}")
            print("   Use --device <serial> to select one.")
            sys.exit(1)
        device = devices[0]

    print(f"✅  Device: {device}")

    # ── 2. Find most recent video file ─────────────────────────────────────────
    video_files = [f for f in adb_ls(PHONE_VIDEO_DIR, device) if f.endswith(".mp4")]
    if not video_files:
        print(f"❌  No .mp4 files found in {PHONE_VIDEO_DIR}")
        print("   Record a video session from the phone app first.")
        sys.exit(1)

    video_files.sort(reverse=True)   # lexicographic sort on video_YYYYMMDD_HHmmss.mp4 → newest first
    latest_video = video_files[0]
    video_remote = f"{PHONE_VIDEO_DIR}/{latest_video}"
    print(f"📹  Latest video: {latest_video}")

    # Extract session timestamp from filename: video_YYYYMMDD_HHmmss.mp4
    try:
        stem = Path(latest_video).stem          # video_20260628_153000
        ts   = stem.replace("video_", "")       # 20260628_153000
        session_name = f"session_{ts}"
    except Exception:
        session_name = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    # ── 3. Create output folder ─────────────────────────────────────────────────
    output_root   = Path(args.output_dir)
    session_dir   = output_root / session_name
    sensor_dir    = session_dir / "wearos_sensor"
    session_dir.mkdir(parents=True, exist_ok=True)
    sensor_dir.mkdir(parents=True, exist_ok=True)
    print(f"📁  Session folder: {session_dir}")

    # ── 4. Pull video ──────────────────────────────────────────────────────────
    video_dst = str(session_dir / latest_video)
    print(f"⬇️   Pulling video → {latest_video} …", end=" ", flush=True)
    try:
        adb_pull(video_remote, video_dst, device)
        size_mb = Path(video_dst).stat().st_size / (1024 * 1024)
        print(f"✅  ({size_mb:.1f} MB)")
    except subprocess.CalledProcessError as e:
        print(f"❌  Failed: {e.stderr.strip()}")

    # ── 5. Pull watch sensor CSVs ──────────────────────────────────────────────
    sensor_files = [f for f in adb_ls(WATCH_SENSOR_DIR, device) if f.endswith(".csv")]
    if not sensor_files:
        print(f"⚠️   No watch sensor CSVs found in {WATCH_SENSOR_DIR}")
        print("    Ensure the watch was recording and raw logging is enabled.")
    else:
        print(f"⬇️   Pulling {len(sensor_files)} sensor CSV(s) …")
        pulled = 0
        for fname in sensor_files:
            src = f"{WATCH_SENSOR_DIR}/{fname}"
            dst = str(sensor_dir / fname)
            try:
                adb_pull(src, dst, device)
                pulled += 1
                print(f"      ✅  {fname}")
            except subprocess.CalledProcessError as e:
                print(f"      ❌  {fname}: {e.stderr.strip()}")
        print(f"   {pulled}/{len(sensor_files)} sensor files pulled.")

    # ── 6. Summary ─────────────────────────────────────────────────────────────
    print()
    print("─" * 60)
    print(f"Session ready: {session_dir}")
    print(f"  Video     : {session_dir / latest_video}")
    print(f"  Sensors   : {sensor_dir}/")
    print()
    print("Next steps:")
    print("  1. Run poc1_tap_sync.py    — detect 3-tap sync event")
    print("  2. Run poc2_shot_slicer.py — extract per-shot clips")
    print("  3. Run poc3_audio_extract.py — extract audio narration")
    print("─" * 60)


if __name__ == "__main__":
    main()
