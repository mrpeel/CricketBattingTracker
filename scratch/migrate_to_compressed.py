#!/usr/bin/env python3
import os
import sys
import gzip
import shutil
import subprocess

BASE_DIR = "/Users/neilkloot/Code/Batting Sensor Stats"
base_live_dir = os.path.join(BASE_DIR, "live_watch_sessions")

def compress_audio_file(audio_path):
    if not os.path.exists(audio_path):
        return
        
    orig_size = os.path.getsize(audio_path)
    if orig_size < 4.5 * 1024 * 1024:
        # Already small, skip
        return
        
    print(f"  🎵 Compressing audio: {os.path.basename(audio_path)} ({orig_size / 1024 / 1024:.1f}MB)...")
    temp_path = audio_path + ".tmp.m4a"
    cmd = [
        "ffmpeg", "-y", "-i", audio_path,
        "-ac", "1", "-ar", "16000", "-b:a", "24k", "-c:a", "aac",
        temp_path
    ]
    res = subprocess.run(cmd, capture_output=True)
    if res.returncode == 0 and os.path.exists(temp_path) and os.path.getsize(temp_path) > 0:
        new_size = os.path.getsize(temp_path)
        os.replace(temp_path, audio_path)
        print(f"  ✅ Compressed successfully: {orig_size / 1024 / 1024:.1f}MB → {new_size / 1024 / 1024:.1f}MB (saved {(orig_size-new_size)/1024/1024:.1f}MB)")
    else:
        print("  ⚠️ Warning: Audio compression failed. Retaining original.")
        if os.path.exists(temp_path):
            os.remove(temp_path)

def compress_csv_file(csv_path):
    gz_path = csv_path + ".gz"
    if os.path.exists(gz_path):
        # Already gzipped, delete raw csv if still there
        if os.path.exists(csv_path):
            os.remove(csv_path)
        return
        
    try:
        with open(csv_path, 'rb') as f_in:
            with gzip.open(gz_path, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
        os.remove(csv_path)
    except Exception as e:
        print(f"  ❌ Failed to compress {os.path.basename(csv_path)}: {e}")
        if os.path.exists(gz_path):
            os.remove(gz_path)

def migrate_session(session_dir):
    session_id = os.path.basename(session_dir)
    print(f"\n──────────────────────────────────────────────────")
    print(f"Processing session: {session_id}")
    
    # 1. Compress audio files
    for filename in os.listdir(session_dir):
        if filename.endswith(".m4a") or filename.endswith(".mp3"):
            compress_audio_file(os.path.join(session_dir, filename))
            
    # 2. Compress CSV files
    compressed_csvs = 0
    for filename in os.listdir(session_dir):
        if filename.startswith("Watch") and filename.endswith(".csv"):
            compress_csv_file(os.path.join(session_dir, filename))
            compressed_csvs += 1
    if compressed_csvs > 0:
        print(f"  🤐 Compressed {compressed_csvs} watch sensor CSVs losslessly.")
        
    # 3. Clean up segments directory
    segments_dir = os.path.join(session_dir, "segments")
    if os.path.exists(segments_dir) and os.path.isdir(segments_dir):
        file_count = len(os.listdir(segments_dir))
        shutil.rmtree(segments_dir)
        print(f"  🧹 Removed redundant segments/ folder (cleaned up {file_count} files).")

def main():
    if not os.path.exists(base_live_dir):
        print(f"❌ ERROR: base live watch sessions directory does not exist: {base_live_dir}")
        sys.exit(1)
        
    sessions = sorted([
        d for d in os.listdir(base_live_dir)
        if d.startswith("session-") and os.path.isdir(os.path.join(base_live_dir, d))
    ])
    
    print(f"🚀 Starting migration for {len(sessions)} sessions...")
    
    # Calculate starting footprint
    start_size_res = subprocess.run(["du", "-sh", base_live_dir], capture_output=True, text=True)
    start_size = start_size_res.stdout.split()[0] if start_size_res.returncode == 0 else "Unknown"
    
    start_files_res = subprocess.run(f"find '{base_live_dir}' -type f | wc -l", shell=True, capture_output=True, text=True)
    start_files = start_files_res.stdout.strip() if start_files_res.returncode == 0 else "Unknown"
    
    print(f"📊 Starting footprint: {start_size} across {start_files} files.")
    
    for session_id in sessions:
        migrate_session(os.path.join(base_live_dir, session_id))
        
    # Calculate ending footprint
    end_size_res = subprocess.run(["du", "-sh", base_live_dir], capture_output=True, text=True)
    end_size = end_size_res.stdout.split()[0] if end_size_res.returncode == 0 else "Unknown"
    
    end_files_res = subprocess.run(f"find '{base_live_dir}' -type f | wc -l", shell=True, capture_output=True, text=True)
    end_files = end_files_res.stdout.strip() if end_files_res.returncode == 0 else "Unknown"
    
    print(f"\n=================== Migration Complete ===================")
    print(f"📊 Starting footprint: {start_size} ({start_files} files)")
    print(f"📊 Ending footprint:   {end_size} ({end_files} files)")
    print(f"===========================================================")

if __name__ == "__main__":
    main()
