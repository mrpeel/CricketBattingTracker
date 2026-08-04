#!/usr/bin/env python3
"""
inspect_recovered_session.py — Assembles and verifies recovered session_2026-08-01_10-18-20
"""
import os
import sys
import glob
import gzip
import shutil
import struct
import numpy as np

RECOVERED_DIR = "/Users/neilkloot/Code/CricketBattingTracker/scratch/phone_session_2026-08-01"
TARGET_SESSION_DIR = "/Users/neilkloot/Code/Batting Sensor Stats/live_watch_sessions/session_2026-08-01_10-18-20"

os.makedirs(TARGET_SESSION_DIR, exist_ok=True)
os.makedirs(os.path.join(TARGET_SESSION_DIR, "PolarSense"), exist_ok=True)

print("=== Assembling Recovered Session 2026-08-01_10-18-20 ===")

# 1. Copy Audio Narration
audio_src = os.path.join(RECOVERED_DIR, "narration_20260801_101820.m4a")
audio_dst = os.path.join(TARGET_SESSION_DIR, "narration_20260801_101820.m4a")
if os.path.exists(audio_src):
    shutil.copy2(audio_src, audio_dst)
    print(f"✅ Copied audio narration: {os.path.basename(audio_dst)} ({os.path.getsize(audio_dst)/1e6:.2f} MB)")

# 2. Compress & Copy Watch Binary Files
watch_dir = os.path.join(RECOVERED_DIR, "watch_session_2026-08-01_10-18-26")
if os.path.exists(watch_dir):
    for fpath in glob.glob(os.path.join(watch_dir, "Watch*.bin")):
        fname = os.path.basename(fpath)
        out_gz = os.path.join(TARGET_SESSION_DIR, f"{fname}.gz")
        # Check if already gzipped
        with open(fpath, 'rb') as f_in:
            head = f_in.read(2)
        if head == b'\x1f\x8b':
            shutil.copy2(fpath, out_gz)
        else:
            with open(fpath, 'rb') as f_in:
                with gzip.open(out_gz, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
        print(f"✅ Packaged watch sensor file: {fname}.gz ({os.path.getsize(out_gz)/1e6:.2f} MB)")

# 3. Compress & Copy Polar Binary Files (session_2026-08-01_10-18-20)
polar_dir = os.path.join(RECOVERED_DIR, "polar_session_2026-08-01_10-18-20")
if os.path.exists(polar_dir):
    for fpath in glob.glob(os.path.join(polar_dir, "Polar*.bin")):
        fname = os.path.basename(fpath)
        out_gz = os.path.join(TARGET_SESSION_DIR, "PolarSense", f"{fname}.gz")
        with open(fpath, 'rb') as f_in:
            head = f_in.read(2)
        if head == b'\x1f\x8b':
            shutil.copy2(fpath, out_gz)
        else:
            with open(fpath, 'rb') as f_in:
                with gzip.open(out_gz, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
        print(f"✅ Packaged Polar sensor file: {fname}.gz ({os.path.getsize(out_gz)/1e6:.2f} MB)")

print("\nSession Assembly Complete!")
