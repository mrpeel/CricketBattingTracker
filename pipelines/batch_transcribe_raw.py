#!/usr/bin/env python3
"""
Batch Raw Audio Transcribe Script for Pitch Analytix Pro
Scans all live watch sessions and requests raw audio transcriptions from Gemini Stage 1.
Features:
- Restartable: Skips sessions that already have a valid raw_transcript.txt newer than --since.
- Cutoff Timestamp (--since): Re-transcribes any raw_transcript.txt older than the specified datetime.
- Rate-Limit Resilience: Automatic exponential backoff retry on Gemini 503/429 errors.
"""

import os
import sys
import glob
import time
import argparse
import datetime
from pathlib import Path

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(ROOT_DIR)

from automate_pipeline import transcribe_audio_gemini, compress_audio_in_place

SESSIONS_DIR = "/Users/neilkloot/Code/Batting Sensor Stats/live_watch_sessions"

def parse_since_datetime(since_str):
    if not since_str:
        return None
    formats = [
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d_%H:%M:%S",
        "%Y-%m-%d",
    ]
    for fmt in formats:
        try:
            return datetime.datetime.strptime(since_str, fmt)
        except ValueError:
            pass
    raise ValueError(f"❌ Invalid --since datetime format: '{since_str}'. Supported formats: YYYY-MM-DD, YYYY-MM-DDTHH:MM:SS")

def transcribe_session_with_retries(audio_path, model_name="gemini-3.5-flash", max_retries=3):
    for attempt in range(1, max_retries + 1):
        try:
            raw_text = transcribe_audio_gemini(audio_path, preferred_model=model_name)
            return raw_text, None
        except Exception as e:
            err_str = str(e)
            is_transient = any(k in err_str.lower() for k in ["503", "429", "unavailable", "quota", "overloaded", "resource exhausted"])
            if is_transient and attempt < max_retries:
                wait_time = 30
                m_delay = re.search(r"retry\s*in\s*([\d\.]+)\s*s", err_str, re.IGNORECASE)
                if not m_delay:
                    m_delay = re.search(r"retryDelay':\s*'(\d+)s'", err_str)
                if m_delay:
                    wait_time = int(float(m_delay.group(1))) + 2
                print(f"   ⚠️ Gemini 3.5 rate-limit/quota hit (Attempt {attempt}/{max_retries}): {e}")
                print(f"   ⏳ Waiting {wait_time}s for rate limit window to clear before retrying gemini-3.5-flash...")
                time.sleep(wait_time)
            else:
                return None, e
    return None, "Max retries exceeded"

def main():
    parser = argparse.ArgumentParser(description="Batch Raw Audio Transcribe Tool (Restartable & Resilient)")
    parser.add_argument("--since", type=str, default=None, help="Cutoff datetime (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS). Re-transcribes transcripts older than this timestamp.")
    parser.add_argument("--force", action="store_true", help="Force re-transcription of all sessions regardless of file age.")
    parser.add_argument("--model", type=str, default="gemini-3.5-flash", help="Gemini model to use for transcription.")
    parser.add_argument("--session-dir", type=str, default=None, help="Optionally transcribe a single specific session directory.")
    args = parser.parse_args()

    since_dt = None
    if args.since:
        try:
            since_dt = parse_since_datetime(args.since)
            print(f"📅 Filter cutoff set: Re-transcribing transcripts older than {since_dt}")
        except ValueError as e:
            print(e)
            sys.exit(1)

    if args.session_dir:
        session_dirs = [args.session_dir]
    else:
        session_dirs = sorted([d for d in glob.glob(os.path.join(SESSIONS_DIR, "*")) if os.path.isdir(d)])

    print("=" * 90)
    print(f"🎙️ BATCH RAW AUDIO TRANSCRIPTION (Scanning {len(session_dirs)} sessions)")
    print("=" * 90)

    total_sessions = 0
    skipped_count = 0
    success_count = 0
    failed_count = 0

    for idx, s_dir in enumerate(session_dirs, 1):
        session_id = os.path.basename(s_dir)
        audio_files = glob.glob(os.path.join(s_dir, "*.m4a")) + glob.glob(os.path.join(s_dir, "*.mp3"))
        
        if not audio_files:
            continue

        total_sessions += 1
        audio_path = audio_files[0]
        raw_transcript_path = os.path.join(s_dir, "raw_transcript.txt")

        # Check if transcription is needed
        needs_transcription = False
        if args.force or not os.path.exists(raw_transcript_path):
            needs_transcription = True
            reason = "missing" if not os.path.exists(raw_transcript_path) else "forced"
        elif since_dt is not None:
            mtime = datetime.datetime.fromtimestamp(os.path.getmtime(raw_transcript_path))
            if mtime < since_dt:
                needs_transcription = True
                reason = f"older than cutoff ({mtime.strftime('%Y-%m-%d %H:%M')})"

        if not needs_transcription:
            mtime_str = datetime.datetime.fromtimestamp(os.path.getmtime(raw_transcript_path)).strftime('%Y-%m-%d %H:%M')
            print(f"[{idx:02d}/{len(session_dirs)}] ⏩ Skipping {session_id:<32} (Transcript exists: {mtime_str})")
            skipped_count += 1
            continue

        print(f"\n[{idx:02d}/{len(session_dirs)}] 🎙️ Processing {session_id} ({reason})...")
        audio_path = compress_audio_in_place(audio_path)
        
        raw_text, err = transcribe_session_with_retries(audio_path, model_name=args.model)
        
        if raw_text:
            with open(raw_transcript_path, "w", encoding="utf-8") as f:
                f.write(raw_text)
            print(f"   ✅ Successfully saved raw transcript ({len(raw_text.splitlines())} lines) -> {raw_transcript_path}")
            success_count += 1
        else:
            print(f"   ❌ Failed to transcribe {session_id}: {err}")
            failed_count += 1

    print("\n" + "=" * 90)
    print("📊 BATCH TRANSCRIPTION COMPLETE")
    print(f"   Total Sessions Scanned: {total_sessions}")
    print(f"   ⏩ Skipped (Up-to-date): {skipped_count}")
    print(f"   ✅ Successfully Transcribed: {success_count}")
    print(f"   ❌ Failed: {failed_count}")
    print("=" * 90)

if __name__ == "__main__":
    main()
