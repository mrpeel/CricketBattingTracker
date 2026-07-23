#!/usr/bin/env python3
"""
🏏 Pitch Analytix Pro: Data Collection & Narration Alignment Pipeline
Automates pulling sensor logs from the Wear OS watch, converting and aligning
the phone audio recording via a 5-tap calibration event, transcribing narrations
using Gemini, and slicing aligned training segments.
"""

import os
import sys
import json
import time
import datetime
import glob
import argparse
import subprocess
import wave
import re
import numpy as np
import pandas as pd
from scipy.signal import find_peaks

import gzip
import shutil


def parse_args():
    parser = argparse.ArgumentParser(description="Pitch Analytix Pro Data Collection Pipeline")
    parser.add_argument("--watch-ip", default="192.168.1.27:37129", help="ADB watch IP and port")
    parser.add_argument("--audio", help="Manual path to the local audio narration file (.m4a/.mp3)")
    parser.add_argument("--dest", default="/Users/neilkloot/Code/Batting Sensor Stats/live_watch_sessions", help="Base directory to save pulled logs")
    parser.add_argument("--manual-offset", type=float, help="Override offset detection and specify manual offset in seconds")
    parser.add_argument("--session-dir", help="Path to local pulled session directory (skips ADB watch pull)")
    parser.add_argument(
        "--model", default="gemini-3.5-flash",
        help="Gemini model to use for transcription (default: gemini-3.5-flash). "
             "The pipeline will NOT fall back to other models — if this model is unavailable it halts."
    )
    parser.add_argument(
        "--force-retranscribe", action="store_true",
        help="Delete any existing narrations_raw.json cache and re-run transcription from scratch."
    )
    parser.add_argument(
        "--save-segments", action="store_true",
        help="Export individual 6-second watch sensor CSV slices under the segments/ directory (default: False)."
    )
    return parser.parse_args()

def resolve_sensor_path(session_dir, baseName):
    path = os.path.join(session_dir, baseName)
    if os.path.exists(path + ".gz"):
        return path + ".gz"
    return path

def load_watch_sensor(session_dir, baseName):
    """Load watch sensor telemetry file in either binary (.bin/.bin.gz) or CSV (.csv/.csv.gz) formats."""
    # Strip extension from baseName to be safe
    baseName_clean = baseName.replace(".csv", "").replace(".bin", "")
    
    bin_path = os.path.join(session_dir, baseName_clean + ".bin")
    bin_gz_path = bin_path + ".gz"
    path_to_load = bin_gz_path if os.path.exists(bin_gz_path) else (bin_path if os.path.exists(bin_path) else None)
    
    if path_to_load:
        import gzip
        if path_to_load.endswith(".gz"):
            with gzip.open(path_to_load, "rb") as f:
                raw_bytes = f.read()
        else:
            with open(path_to_load, "rb") as f:
                raw_bytes = f.read()
                
        if "GameOrientation" in baseName_clean or "Orientation" in baseName_clean:
            # 28 bytes: Long (i8), Float (f4) x 5
            dtype = np.dtype([
                ('time', '<i8'),
                ('seconds_elapsed', '<f4'),
                ('qx', '<f4'),
                ('qy', '<f4'),
                ('qz', '<f4'),
                ('qw', '<f4')
            ])
        elif "Steps" in baseName_clean and "StepCounter" not in baseName_clean:
            # 12 bytes: Long (i8), Float (f4)
            dtype = np.dtype([
                ('time', '<i8'),
                ('seconds_elapsed', '<f4')
            ])
        elif "HeartRate" in baseName_clean:
            # 16 bytes: Long (i8), Float (f4) x 2
            dtype = np.dtype([
                ('time', '<i8'),
                ('seconds_elapsed', '<f4'),
                ('bpm', '<f4')
            ])
        elif "Barometer" in baseName_clean:
            # 16 bytes: Long (i8), Float (f4) x 2
            dtype = np.dtype([
                ('time', '<i8'),
                ('seconds_elapsed', '<f4'),
                ('pressure', '<f4')
            ])
        elif "StepCounter" in baseName_clean:
            # 16 bytes: Long (i8), Float (f4) x 2
            dtype = np.dtype([
                ('time', '<i8'),
                ('seconds_elapsed', '<f4'),
                ('steps', '<f4')
            ])
        else:
            # 24 bytes: Long (i8), Float (f4) x 4
            dtype = np.dtype([
                ('time', '<i8'),
                ('seconds_elapsed', '<f4'),
                ('x', '<f4'),
                ('y', '<f4'),
                ('z', '<f4')
            ])
            
        rec_size = dtype.itemsize
        num_recs = len(raw_bytes) // rec_size
        valid_bytes = raw_bytes[:num_recs * rec_size]
        
        arr = np.frombuffer(valid_bytes, dtype=dtype)
        df = pd.DataFrame(arr)
        df['time'] = df['time'].astype('int64')
        return df
        
    # Fallback to CSV
    csv_path = os.path.join(session_dir, baseName_clean + ".csv")
    csv_gz_path = csv_path + ".gz"
    path_to_load = csv_gz_path if os.path.exists(csv_gz_path) else (csv_path if os.path.exists(csv_path) else None)
    
    if path_to_load:
        return pd.read_csv(path_to_load)
        
    return pd.DataFrame()

def compress_audio_in_place(audio_path):
    if not audio_path or not os.path.exists(audio_path):
        return audio_path
    
    # Skip if file size is already very small (e.g. less than 4.5MB, meaning it's likely already compressed)
    if os.path.getsize(audio_path) < 4.5 * 1024 * 1024:
        print(f"ℹ️ Audio file is already small ({os.path.getsize(audio_path)/1024/1024:.2f}MB). Skipping compression.")
        return audio_path
        
    temp_path = audio_path + ".tmp.m4a"
    print(f"🎵 Compressing voice narration audio to speech-optimized 16kHz mono 24kbps AAC...")
    cmd = [
        "ffmpeg", "-y", "-i", audio_path,
        "-ac", "1", "-ar", "16000", "-b:a", "24k", "-c:a", "aac",
        temp_path
    ]
    res = subprocess.run(cmd, capture_output=True)
    if res.returncode == 0 and os.path.exists(temp_path) and os.path.getsize(temp_path) > 0:
        orig_size = os.path.getsize(audio_path)
        new_size = os.path.getsize(temp_path)
        os.replace(temp_path, audio_path)
        print(f"✅ Audio compressed successfully: {orig_size / 1024 / 1024:.2f}MB → {new_size / 1024 / 1024:.2f}MB")
    else:
        print("⚠️ Warning: FFmpeg audio compression failed or produced empty file. Retaining original.")
        if os.path.exists(temp_path):
            os.remove(temp_path)
    return audio_path

def compress_session_csvs(session_dir):
    print("\n🤐 Compressing raw session logs to Gzip...")
    compressed_count = 0
    for filename in os.listdir(session_dir):
        if filename.startswith("Watch") and (filename.endswith(".csv") or filename.endswith(".bin")):
            csv_path = os.path.join(session_dir, filename)
            gz_path = csv_path + ".gz"
            try:
                with open(csv_path, 'rb') as f_in:
                    with gzip.open(gz_path, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
                os.remove(csv_path)
                compressed_count += 1
                print(f"  Compressed and removed: {filename}")
            except Exception as e:
                print(f"  ❌ Failed to compress {filename}: {e}")
                if os.path.exists(gz_path):
                    os.remove(gz_path)
    polar_dir = os.path.join(session_dir, "PolarSense")
    if os.path.isdir(polar_dir):
        for filename in os.listdir(polar_dir):
            if filename.endswith(".csv") or filename.endswith(".bin"):
                csv_path = os.path.join(polar_dir, filename)
                gz_path = csv_path + ".gz"
                try:
                    with open(csv_path, 'rb') as f_in:
                        with gzip.open(gz_path, 'wb') as f_out:
                            shutil.copyfileobj(f_in, f_out)
                    os.remove(csv_path)
                    compressed_count += 1
                    print(f"  Compressed and removed: PolarSense/{filename}")
                except Exception as e:
                    print(f"  ❌ Failed to compress PolarSense/{filename}: {e}")
                    if os.path.exists(gz_path):
                        os.remove(gz_path)
    print(f"✅ Losslessly compressed {compressed_count} sensor logs.")

def append_to_combined_parquet(session_dir, parquet_dir):
    print("\n📦 Appending session sensor data to combined Parquet database...")
    import pyarrow as pa
    import pyarrow.parquet as pq
    
    session_id = os.path.basename(session_dir)
    sensor_mappings = [
        ("gyro",        "WatchGyroscope.csv"),
        ("accel",       "WatchAccelerometer.csv"),
        ("gravity",     "WatchGravity.csv"),
        ("linacc",      "WatchLinearAcceleration.csv"),
        ("mag",         "WatchMagnetometer.csv"),
        ("game_orient", "WatchGameOrientation.csv"),
        ("orient",      "WatchOrientation.csv"),
        ("steps",       "WatchSteps.csv")
    ]
    
    os.makedirs(parquet_dir, exist_ok=True)
    
    appended_count = 0
    for name, fname in sensor_mappings:
        try:
            df = load_watch_sensor(session_dir, fname)
            if df.empty:
                continue
                
            df['session_id'] = session_id
            table = pa.Table.from_pandas(df, preserve_index=False)
            
            sensor_type_dir = os.path.join(parquet_dir, f"sensor_type={name}")
            os.makedirs(sensor_type_dir, exist_ok=True)
            
            session_file = os.path.join(sensor_type_dir, f"{session_id}.parquet")
            pq.write_table(table, session_file, compression='snappy')
            appended_count += 1
            print(f"  Appended {name} ({len(df)} rows)")
        except Exception as e:
            print(f"  ❌ Error appending {name}: {e}")
            
    # Also append Polar Sense sensor data if present
    polar_dir = os.path.join(session_dir, "PolarSense")
    polar_mappings = [
        ("PolarAccelerometer", "PolarAccelerometer.csv"),
        ("PolarGyroscope",     "PolarGyroscope.csv"),
        ("PolarMagnetometer",  "PolarMagnetometer.csv")
    ]
    if os.path.isdir(polar_dir):
        for name, fname in polar_mappings:
            csv_path = os.path.join(polar_dir, fname)
            gz_path = csv_path + ".gz"
            path_to_load = gz_path if os.path.exists(gz_path) else (csv_path if os.path.exists(csv_path) else None)
            if not path_to_load:
                continue
            try:
                # Polar CSVs are semicolon-delimited
                df = pd.read_csv(path_to_load, sep=';')
                if len(df) == 0:
                    continue
                df['session_id'] = session_id
                table = pa.Table.from_pandas(df, preserve_index=False)
                sensor_type_dir = os.path.join(parquet_dir, f"sensor_type={name}")
                os.makedirs(sensor_type_dir, exist_ok=True)
                session_file = os.path.join(sensor_type_dir, f"{session_id}.parquet")
                pq.write_table(table, session_file, compression='snappy')
                appended_count += 1
                print(f"  Appended {name} ({len(df)} rows)")
            except Exception as e:
                print(f"  ❌ Error appending Polar sensor {name}: {e}")
            
    print(f"✅ Appended {appended_count} sensor datasets to Parquet database.")

def check_adb_devices():
    print("Checking connected ADB devices...")
    res = subprocess.run(["adb", "devices"], capture_output=True, text=True)
    lines = res.stdout.strip().split("\n")[1:]
    devices = []
    for line in lines:
        if not line.strip():
            continue
        parts = line.split()
        if len(parts) >= 2 and parts[1] == "device":
            devices.append(parts[0])
    return devices

def find_phone_device(devices):
    # Any connected device is treated as the phone
    if devices:
        return devices[0]
    return None

def pull_latest_session_from_phone(phone_id, dest_dir):
    print("Pulling latest session from Phone companion storage...")
    phone_base = "/sdcard/Android/data/com.mrpeel.cricketbattingtracker/files/watch_sessions"
    cmd = ["adb", "-s", phone_id, "shell", "ls", phone_base]
    res = subprocess.run(cmd, capture_output=True, text=True)
    incoming_base = "/sdcard/Android/data/com.mrpeel.cricketbattingtracker/files/watch_sessions_incoming"
    sessions = []
    if res.returncode == 0 and res.stdout.strip():
        sessions = [s.strip() for s in res.stdout.split("\n") if s.strip() and (s.startswith("session-") or s.startswith("session_"))]
        
    if not sessions:
        incoming_cmd = ["adb", "-s", phone_id, "shell", "ls", incoming_base]
        inc_res = subprocess.run(incoming_cmd, capture_output=True, text=True)
        if inc_res.returncode == 0 and "temp_session_raw.zip" in inc_res.stdout:
            print("⚠️ Found unprocessed raw session ZIP in incoming directory on phone. Pulling fallback...")
            phone_path = f"{incoming_base}/temp_session_raw.zip"
            now_str = datetime.datetime.now().strftime("session_%Y-%m-%d_%H-%M-%S")
            local_zip_path = os.path.join(dest_dir, now_str + ".zip")
            
            if os.path.exists(local_zip_path):
                if os.path.isdir(local_zip_path):
                    import shutil
                    shutil.rmtree(local_zip_path)
                else:
                    os.remove(local_zip_path)
                    
            print(f"📥 Pulling incoming watch session ZIP: {phone_path} → {local_zip_path}")
            subprocess.run(["adb", "-s", phone_id, "pull", phone_path, local_zip_path], check=True)
            
            local_session_dir = os.path.join(dest_dir, now_str)
            os.makedirs(local_session_dir, exist_ok=True)
            print(f"📦 Unzipping session file locally: {local_zip_path} → {local_session_dir}")
            import zipfile
            try:
                with zipfile.ZipFile(local_zip_path, 'r') as zip_ref:
                    zip_ref.extractall(local_session_dir)
            except zipfile.BadZipFile:
                print(f"❌ ERROR: The pulled raw session file is corrupt or incomplete (BadZipFile).")
                print("   This happens if the watch-to-phone data sync is still actively running or was aborted.")
                if os.path.exists(local_zip_path): os.remove(local_zip_path)
                if os.path.exists(local_session_dir):
                    import shutil
                    shutil.rmtree(local_session_dir)
                return None
            os.remove(local_zip_path)
            
            print("🧹 Cleaning raw incoming session on phone...")
            subprocess.run(["adb", "-s", phone_id, "shell", f"rm -rf {phone_path}"], check=True)
            return local_session_dir
            
        print("❌ ERROR: No session directories found on the Phone.")
        return None
        
    latest_session = sorted(sessions)[-1]
    phone_path = f"{phone_base}/{latest_session}"
    
    if phone_path.endswith(".zip"):
        local_zip_path = os.path.join(dest_dir, latest_session)
        if os.path.exists(local_zip_path):
            if os.path.isdir(local_zip_path):
                import shutil
                shutil.rmtree(local_zip_path)
            else:
                os.remove(local_zip_path)
        print(f"📥 Pulling latest phone-synced watch session ZIP: {phone_path} → {local_zip_path}")
        subprocess.run(["adb", "-s", phone_id, "pull", phone_path, local_zip_path], check=True)
        
        local_session_dir = os.path.join(dest_dir, latest_session.replace(".zip", ""))
        os.makedirs(local_session_dir, exist_ok=True)
        
        print(f"📦 Unzipping session file locally: {local_zip_path} → {local_session_dir}")
        import zipfile
        try:
            with zipfile.ZipFile(local_zip_path, 'r') as zip_ref:
                zip_ref.extractall(local_session_dir)
        except zipfile.BadZipFile:
            print(f"❌ ERROR: The pulled session file {latest_session} is corrupt or incomplete (BadZipFile).")
            print("   This happens if the watch-to-phone data sync is still actively running or was aborted.")
            if os.path.exists(local_zip_path): os.remove(local_zip_path)
            if os.path.exists(local_session_dir):
                import shutil
                shutil.rmtree(local_session_dir)
            return None
            
        os.remove(local_zip_path)
    else:
        local_session_dir = os.path.join(dest_dir, latest_session)
        os.makedirs(local_session_dir, exist_ok=True)
        print(f"📥 Pulling latest phone-synced watch session: {phone_path} → {local_session_dir}/")
        subprocess.run(["adb", "-s", phone_id, "pull", phone_path + "/.", local_session_dir], check=True)
    
    # Clean watch sessions directory on phone
    print("🧹 Cleaning raw session directory on phone to free space...")
    subprocess.run(["adb", "-s", phone_id, "shell", f"rm -rf {phone_path}"], check=True)
    
    return local_session_dir

def pull_audio_from_phone(phone_id, dest_dir):
    print(f"Searching connected phone ({phone_id}) for recent voice recordings...")
    paths = [
        "/sdcard/Recordings",
        "/sdcard/VoiceRecorder",
        "/sdcard/Music",
        "/sdcard/Download",
        "/sdcard/Android/data/com.mrpeel.cricketbattingtracker/files"
    ]
    
    audio_files = []
    for path in paths:
        # If accessing the app's package folder, use ls directly since find is blocked on Android 11+
        if "com.mrpeel.cricketbattingtracker" in path:
            cmd = ["adb", "-s", phone_id, "shell", f"ls '{path}' 2>/dev/null"]
            res = subprocess.run(cmd, capture_output=True, text=True)
            if res.returncode == 0 and res.stdout.strip():
                for line in res.stdout.split("\n"):
                    line = line.strip()
                    if line.endswith(".m4a") or line.endswith(".mp3"):
                        audio_files.append(os.path.join(path, line))
        else:
            cmd = ["adb", "-s", phone_id, "shell", f"find '{path}' -name '*.m4a' -o -name '*.mp3' 2>/dev/null"]
            res = subprocess.run(cmd, capture_output=True, text=True)
            if res.returncode == 0 and res.stdout.strip():
                for line in res.stdout.split("\n"):
                    if line.strip():
                        audio_files.append(line.strip())
                    
    if not audio_files:
        print("⚠️ No audio files found automatically on the phone.")
        return None
        
    print(f"Found {len(audio_files)} recordings on phone. Locating the most recent session file...")
    ref_file = os.path.join(dest_dir, "WatchGyroscope.csv")
    if not os.path.exists(ref_file):
        ref_file = os.path.join(dest_dir, "WatchGyroscope.csv.gz")
    if not os.path.exists(ref_file):
        ref_file = dest_dir
    # Try to parse the session start time from the session directory name
    # (e.g., session-2026-07-17_12-30-41)
    session_name = os.path.basename(dest_dir)
    session_time = None
    match = re.match(r"session[-_](\d{4}-\d{2}-\d{2})_(\d{2})[-_](\d{2})[-_](\d{2})", session_name)
    if match:
        try:
            date_str = match.group(1)
            h, m, s = match.group(2), match.group(3), match.group(4)
            dt = datetime.datetime.strptime(f"{date_str}_{h}-{m}-{s}", "%Y-%m-%d_%H-%M-%S")
            session_time = int(dt.timestamp())
            print(f"🕒 Parsed session start time from directory name: {dt} (timestamp: {session_time})")
        except Exception as e:
            print(f"⚠️ Failed to parse session start time from directory name: {e}")

    if session_time is None:
        session_time = int(os.path.getmtime(ref_file))


    newest_file = None
    newest_time = 0
    for f in audio_files:
        cmd = ["adb", "-s", phone_id, "shell", f"stat -c '%Y' '{f}' 2>/dev/null"]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode == 0 and res.stdout.strip():
            try:
                mtime = int(res.stdout.strip())
                # Ignore files not recorded within 2 hours of the session
                if abs(mtime - session_time) > 7200:
                    continue
                if mtime > newest_time:
                    newest_time = mtime
                    newest_file = f
            except:
                pass
                
    if not newest_file:
        print("ℹ️ No recent voice recording matching this session was found on the phone.")
        return None
        
    local_name = os.path.basename(newest_file)
    local_path = os.path.join(dest_dir, local_name)
    print(f"📥 Pulling phone audio file: {newest_file} → {local_path}")
    subprocess.run(["adb", "-s", phone_id, "pull", newest_file, local_path], check=True)
    return local_path

def pull_polar_from_phone(phone_id, session_dir):
    """Pull the most recent Polar Sense session from the phone and save to PolarSense/ subdirectory."""
    print(f"Searching connected phone ({phone_id}) for Polar Sense session data...")
    polar_base = "/sdcard/Android/data/com.mrpeel.cricketbattingtracker/files/polar_sessions"
    cmd = ["adb", "-s", phone_id, "shell", "ls", polar_base]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0 or not res.stdout.strip():
        print("⚠️ No Polar Sense session directories found on the phone.")
        return False

    sessions = [s.strip() for s in res.stdout.split("\n") if s.strip() and s.startswith("polar_session_")]
    if not sessions:
        print("⚠️ No polar_session_* directories found on the phone.")
        return False

    latest_session = sorted(sessions)[-1]
    polar_phone_path = f"{polar_base}/{latest_session}"
    local_polar_dir = os.path.join(session_dir, "PolarSense")
    os.makedirs(local_polar_dir, exist_ok=True)

    if polar_phone_path.endswith(".zip"):
        local_zip_path = os.path.join(session_dir, latest_session)
        if os.path.exists(local_zip_path):
            if os.path.isdir(local_zip_path):
                import shutil
                shutil.rmtree(local_zip_path)
            else:
                os.remove(local_zip_path)
                
        print(f"📥 Pulling Polar Sense ZIP: {polar_phone_path} → {local_zip_path}")
        pull_res = subprocess.run(
            ["adb", "-s", phone_id, "pull", polar_phone_path, local_zip_path],
            capture_output=True, text=True
        )
        if pull_res.returncode != 0:
            print(f"❌ Failed to pull Polar Sense ZIP: {pull_res.stderr.strip()}")
            return False
            
        print(f"📦 Unzipping Polar Sense files locally: {local_zip_path} → {local_polar_dir}")
        import zipfile
        with zipfile.ZipFile(local_zip_path, 'r') as zip_ref:
            zip_ref.extractall(local_polar_dir)
        os.remove(local_zip_path)
    else:
        print(f"📥 Pulling Polar Sense files: {polar_phone_path} → {local_polar_dir}/")
        pull_res = subprocess.run(
            ["adb", "-s", phone_id, "pull", polar_phone_path + "/.", local_polar_dir],
            capture_output=True, text=True
        )
        if pull_res.returncode != 0:
            print(f"❌ Failed to pull Polar Sense data: {pull_res.stderr.strip()}")
            return False

    pulled_files = [f for f in os.listdir(local_polar_dir) if os.path.isfile(os.path.join(local_polar_dir, f))]
    if not pulled_files:
        print("⚠️ Polar Sense directory pulled but contains no files.")
        return False

    print(f"✅ Pulled {len(pulled_files)} Polar Sense files from {latest_session}.")

    # Clean Polar session directory on phone after successful pull
    print("🧹 Cleaning Polar Sense session on phone...")
    subprocess.run(
        ["adb", "-s", phone_id, "shell", f"rm -rf {polar_phone_path}"],
        check=False
    )

    return True


# (Whisper local fallback functions removed to keep the pipeline clean and free of unused code/heuristics)


class ProgressSpinner:
    def __init__(self, message):
        self.message = message
        import threading
        self.stop_event = threading.Event()
        self.thread = threading.Thread(target=self._spin)

    def _spin(self):
        import time
        import sys
        start_time = time.time()
        spinner = ['|', '/', '-', '\\']
        idx = 0
        while not self.stop_event.is_set():
            elapsed = int(time.time() - start_time)
            sys.stdout.write(f"\r{self.message} [{spinner[idx % 4]}] {elapsed}s elapsed...")
            sys.stdout.flush()
            idx += 1
            time.sleep(0.5)
        # Clear the line when done
        sys.stdout.write("\r" + " " * (len(self.message) + 30) + "\r")
        sys.stdout.flush()

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop_event.set()
        self.thread.join()

def transcribe_audio_gemini(audio_path, preferred_model="gemini-3.5-flash"):
    """Transcribe audio using Gemini. Only the preferred_model is tried.
    If it is unavailable (quota / 429 / 503), one retry after 30 s is attempted.
    If both attempts fail the function raises GeminiUnavailableError so the
    caller can halt cleanly with resume instructions."""
    from google import genai
    from google.genai import types
    import re
    import json

    class GeminiUnavailableError(RuntimeError):
        pass

    # Normalise model name (strip 'models/' prefix if present)
    model_name = preferred_model.removeprefix("models/")

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        dotenv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
        if os.path.exists(dotenv_path):
            with open(dotenv_path, "r") as f:
                for line in f:
                    if line.startswith("GEMINI_API_KEY="):
                        api_key = line.split("=", 1)[1].strip()
                        break
    if not api_key:
        print("❌ ERROR: GEMINI_API_KEY environment variable is not set.")
        print("Please export it in your shell: export GEMINI_API_KEY='your_api_key'")
        sys.exit(1)

    client = genai.Client(api_key=api_key)

    # Verify that the requested model is actually available before uploading audio
    available = [m.name.removeprefix("models/") for m in client.models.list()]
    if model_name not in available:
        raise RuntimeError(
            f"❌ Model '{model_name}' is not available in your account.\n"
            f"   Available flash/pro models: {[m for m in available if 'flash' in m or 'pro' in m]}\n"
            f"   Re-run with --model <available-model> once it becomes accessible."
        )

    print(f"📤 Uploading {os.path.basename(audio_path)} to Gemini...")
    uploaded_file = client.files.upload(file=audio_path)
    print(f"File uploaded successfully. Storage URI: {uploaded_file.name}")

    print("Waiting for Gemini to process the audio file...")
    while uploaded_file.state.name == "PROCESSING":
        time.sleep(2)
        uploaded_file = client.files.get(name=uploaded_file.name)

    if uploaded_file.state.name == "FAILED":
        raise Exception("Gemini audio processing failed.")

    print("🎙️ Preparing prompt for raw transcript...")
    prompt_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "docs", "gemini_raw_transcript_prompt.md")
    if os.path.exists(prompt_path):
        with open(prompt_path, "r") as f:
            prompt = f.read().strip()
        print(f"📖 Loaded raw transcript prompt from {prompt_path}")
    else:
        raise RuntimeError(f"❌ Could not find raw transcript prompt at {prompt_path}")

    # --- Single-model strict call with one retry on quota/availability errors ---
    RETRY_WAIT_SECONDS = 30
    response = None
    last_err = None
    for attempt in range(1, 3):  # attempt 1, then attempt 2 after a wait
        try:
            msg = f"🎙️ Requesting raw transcription from {model_name} (attempt {attempt}/2)"
            with ProgressSpinner(msg):
                response = client.models.generate_content(
                    model=model_name,
                    contents=[uploaded_file, prompt]
                )
            print(f"✅ Transcription succeeded with {model_name}.")
            break
        except Exception as e:
            last_err = e
            err_str = str(e).lower()
            is_quota_err = any(k in err_str for k in ["429", "503", "quota", "unavailable", "overloaded", "resource exhausted"])
            if is_quota_err and attempt == 1:
                print(f"⚠️  {model_name} unavailable (attempt {attempt}): {e}")
                print(f"   ⏳ Waiting {RETRY_WAIT_SECONDS}s before retrying...")
                time.sleep(RETRY_WAIT_SECONDS)
            else:
                break

    if response is None:
        session_dir_hint = os.path.dirname(audio_path)
        raise RuntimeError(
            f"\n❌ TRANSCRIPTION FAILED — model '{model_name}' is unavailable or returned an error.\n"
            f"   Last error: {last_err}\n\n"
            f"   ℹ️  The pipeline has NOT fallen back to a different model.\n"
            f"   ℹ️  Your session data is safe. To resume once the model is available:\n"
            f"\n"
            f"   python3 automate_pipeline.py \\\n"
            f"     --session-dir \"{session_dir_hint}\" \\\n"
            f"     --audio \"{audio_path}\" \\\n"
            f"     --force-retranscribe \\\n"
            f"     --model {model_name}\n"
        )
    
    # Delete file from Cloud Storage
    try:
        client.files.delete(name=uploaded_file.name)
    except:
        pass
        
    return response.text

def parse_raw_transcript(raw_text):
    """Parse literal raw text transcript (Stage 2) with timestamp prefixes
    and map to standardised JSON schema."""
    lines = raw_text.splitlines()
    shot_events = []
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Match time prefix like "12.35:", "[12.35]:", "1:02.50:", etc.
        match = re.match(r"^\[?([\d\.:]+)\]?\s*:\s*(.*)$", line)
        if not match:
            # Try matching space instead of colon
            match = re.match(r"^\[?([\d\.:]+)\]?\s+(.*)$", line)
            
        if not match:
            continue
            
        time_str, text = match.groups()
        text = text.strip()
        
        # Convert time_str to seconds
        try:
            if ":" in time_str:
                parts = time_str.split(":")
                if len(parts) == 2:
                    time_sec = int(parts[0]) * 60 + float(parts[1])
                elif len(parts) == 3:
                    time_sec = int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
                else:
                    time_sec = float(time_str)
            else:
                time_sec = float(time_str)
        except ValueError:
            continue
            
        shot_events.append({
            "timestamp_seconds": time_sec,
            "text": text
        })
        
    return process_and_format_events(shot_events)

def process_and_format_events(shot_events):
    formatted_shots = []
    current_bat = None
    shot_counter = 1
    
    for event in shot_events:
        full_text = event["text"].strip()
        text_lower = full_text.lower()
        
        # 1. Bat Recognition (Check for bat switch announcements)
        if any(w in text_lower for w in ["iron bat", "eye in", "thin bat", "light bat"]):
            current_bat = "Eye In"
        elif any(w in text_lower for w in ["giant", "nicolls", "nichs", "heavy bat"]):
            current_bat = "Gray Nicolls Giant"
        elif any(w in text_lower for w in ["game bat", "game day bat", "normal bat", "standard bat"]):
            current_bat = "Game bat"
            
        # If the line is ONLY a bat switch announcement or round header (e.g. "Round one, Iron Bat", "End of round"), skip shot creation
        if any(header in text_lower for header in ["round ", "end of round", "end of session"]) and not any(s in text_lower for s in ["drive", "cut", "flick", "pull", "shot", "defense", "defence", "facing"]):
            continue

        # 2. Shot Type Mapping
        shot_type = None
        
        # Stance / Non-swing events
        if "facing up" in text_lower or "ready" in text_lower or "facing" in text_lower:
            shot_type = "Facing up"
        elif "no shot" in text_lower:
            shot_type = "No shot"
        elif "leave" in text_lower or "left" in text_lower:
            shot_type = "Leave"
        elif "evade" in text_lower or "evasion" in text_lower or "ducked" in text_lower or "swayed" in text_lower:
            shot_type = "Evade"
            
        # Specific stroke types
        elif "power drive" in text_lower:
            shot_type = "Power drive"
        elif "cover drive" in text_lower or "cover" in text_lower:
            shot_type = "Cover drive"
        elif "straight drive" in text_lower or "straight" in text_lower:
            shot_type = "Straight drive"
        elif "off drive" in text_lower:
            shot_type = "Off drive"
        elif "on drive" in text_lower:
            shot_type = "On drive"
        elif "slog" in text_lower or "power shot" in text_lower or "power hit" in text_lower or "lofted" in text_lower:
            shot_type = "Slog"
        elif re.search(r"\b(pull|full)\b", text_lower):
            shot_type = "Pull shot"
        elif "hook" in text_lower:
            shot_type = "Hook shot"
        elif re.search(r"\b(flick|click)\b", text_lower):
            shot_type = "Flick"
        elif "glance" in text_lower:
            shot_type = "Leg glance"
        elif re.search(r"\b(sweep|sweet)\b", text_lower):
            shot_type = "Sweep"
        elif re.search(r"\b(cut|square cut|late cut)\b", text_lower):
            shot_type = "Cut shot"
        elif "punch" in text_lower:
            shot_type = "Punch"
        elif "push" in text_lower:
            shot_type = "Push"
        elif "guide" in text_lower or "glide" in text_lower or "steer" in text_lower:
            shot_type = "Guide"
        elif any(d in text_lower for d in ["defense", "defence", "defensive", "block", "forward edge"]):
            shot_type = "Defence/Block"
            
        # Fallback for generic/ambiguous shot utterances (e.g. "Edge", "Good", "Missed")
        if shot_type is None:
            if any(q in text_lower for q in ["good", "okay", "ok", "poor", "excellent", "perfect", "edge", "edged", "miss", "missed"]):
                shot_type = "Defence/Block"
            else:
                # Unrecognized administrative utterance — skip
                continue
                
        # 3. Determine Shot Number
        is_swing = shot_type not in ["Facing up", "No shot", "Leave", "Evade"]
        if is_swing:
            shot_num = shot_counter
            shot_counter += 1
        else:
            shot_num = None
            
        # 4. Quality Rating Extraction
        quality = "good"
        if any(q in text_lower for q in ["excellent", "perfect", "nailed", "smoked"]):
            quality = "excellent"
        elif any(q in text_lower for q in ["poor", "bad", "edge", "edged"]):
            quality = "poor"
        elif any(q in text_lower for q in ["miss", "missed", "beaten"]):
            quality = "miss"
        elif any(q in text_lower for q in ["okay", "ok", "decent", "average"]):
            quality = "okay"
            
        formatted_shots.append({
            "timestamp_seconds": event["timestamp_seconds"],
            "shot_number": shot_num,
            "shot_type": shot_type,
            "quality": quality,
            "bat": current_bat,
            "narrated_text": full_text
        })
        
    return formatted_shots

def main():
    args = parse_args()
    
    # 1. Connect and pull session files
    phone_id = None
    if args.session_dir:
        session_dir = args.session_dir
        print(f"Using local session directory: {session_dir}")
    else:
        devices = check_adb_devices()
        phone_id = find_phone_device(devices)
        if not phone_id:
            print("❌ ERROR: No phone device connected or authorized.")
            sys.exit(1)
            
        session_dir = pull_latest_session_from_phone(phone_id, args.dest)
        if not session_dir:
            sys.exit(1)
        
    # 2. Get/Pull Audio Narration file
    audio_path = args.audio
    if not audio_path:
        # Check if there is already an audio file in the session directory
        local_audios = glob.glob(os.path.join(session_dir, "*.m4a")) + glob.glob(os.path.join(session_dir, "*.mp3"))
        if local_audios:
            audio_path = local_audios[0]
            print(f"📖 Found local audio narration file in session directory: {audio_path}")
        else:
            if phone_id:
                audio_path = pull_audio_from_phone(phone_id, session_dir)
                pull_polar_from_phone(phone_id, session_dir)
            if not audio_path:
                print("⚠️ Phone device not detected or audio not found on phone.")
            
    if not audio_path:
        # Prompt user
        print("\nCould not automatically find audio recording.")
        audio_path = input("Please enter the path to the local audio file (.m4a/.mp3): ").strip()
        if not os.path.exists(audio_path):
            print("❌ ERROR: File does not exist.")
            sys.exit(1)
            
    # Compress voice narration to speech-optimized mono 16kHz 24kbps AAC
    audio_path = compress_audio_in_place(audio_path)
            
    # 4. Load Gyroscope sensor file (needed for MMSS conversion and offset alignment)
    df_gyro = load_watch_sensor(session_dir, "WatchGyroscope")
    if df_gyro.empty:
        print(f"❌ ERROR: Gyroscope sensor file missing or empty in session log.")
        sys.exit(1)
        
    df_gyro['mag'] = np.sqrt(df_gyro['x']**2 + df_gyro['y']**2 + df_gyro['z']**2)
    start_time_ns = df_gyro.iloc[0]['time']
    start_time_ms = int(start_time_ns / 1_000_000)
    gyro_duration = df_gyro.iloc[-1]['seconds_elapsed']

    # Precalculate all raw gyroscope peaks in the session using scipy find_peaks with prominence >= 0.5 rad/s.
    # Set peak distance to ~0.1s minimum gap based on sampling frequency.
    print("📈 Precalculating gyroscope sensor peaks via scipy prominence...")
    times = df_gyro['seconds_elapsed'].to_numpy()
    mags = df_gyro['mag'].to_numpy()
    
    # Calculate sample rate (fs) to dynamically scale distance parameter
    total_time = times[-1] - times[0]
    fs = len(df_gyro) / total_time if total_time > 0 else 50.0
    peak_distance = max(3, int(fs * 0.1))  # 100ms minimum spacing
    
    peak_indices, _ = find_peaks(mags, prominence=0.5, distance=peak_distance)
    session_peaks = []
    for idx in peak_indices:
        session_peaks.append({
            'time': float(times[idx]),
            'mag': float(mags[idx]),
            'is_fallback': False
        })
    print(f"   Found {len(session_peaks)} prominence peaks (prominence >= 0.5 rad/s, min spacing={peak_distance} samples).")


    # 5. Call Gemini to transcribe (Stage 1) and parse (Stage 2) shot timings
    raw_transcript_path = os.path.join(session_dir, "raw_transcript.txt")
    narrations_cache_path = os.path.join(session_dir, "narrations_raw.json")

    # --force-retranscribe: delete stale raw transcript cache and parsed cache so transcription always re-runs
    if getattr(args, "force_retranscribe", False):
        if os.path.exists(raw_transcript_path):
            print(f"🗑️  --force-retranscribe set: deleting existing raw transcript {raw_transcript_path}")
            os.remove(raw_transcript_path)
        if os.path.exists(narrations_cache_path):
            print(f"🗑️  --force-retranscribe set: deleting existing cache {narrations_cache_path}")
            os.remove(narrations_cache_path)

    raw_text = None
    if os.path.exists(raw_transcript_path):
        print(f"📖 Loading cached raw transcript from {raw_transcript_path}...")
        with open(raw_transcript_path, "r", encoding="utf-8") as f:
            raw_text = f.read()
    else:
        preferred_model = getattr(args, "model", "gemini-3.5-flash")
        try:
            raw_text = transcribe_audio_gemini(audio_path, preferred_model=preferred_model)
            print(f"Successfully transcribed raw audio via Gemini ({preferred_model}).")
        except RuntimeError as e:
            print(e)
            sys.exit(1)
        except Exception as e:
            print(f"❌ Gemini transcription failed unexpectedly: {e}")
            sys.exit(1)

        # Save Stage 1 raw transcript
        with open(raw_transcript_path, "w", encoding="utf-8") as f:
            f.write(raw_text)

    # Stage 2: Parse raw transcript to produce structured JSON
    print("Parsing raw transcript...")
    narrations = parse_raw_transcript(raw_text)
    
    # Write parsed narrations to session dir
    with open(narrations_cache_path, "w") as f:
        json.dump(narrations, f, indent=2)

    # Detect and convert mixed M.SS / raw seconds timestamps to actual elapsed seconds
    if narrations:
        max_raw = 0.0
        has_drops = False
        for i in range(len(narrations)):
            t = narrations[i]['timestamp_seconds']
            max_raw = max(max_raw, t)
            if i > 0 and t < narrations[i-1]['timestamp_seconds']:
                has_drops = True
                
        # All timestamps are treated directly as raw elapsed seconds, as requested by the prompt.
        print("💡 Timestamps parsed directly as raw seconds since start.")

    # 6. Clock Offset Calibration Alignment (with automatic grid search)
    # NOTE: All optimisation is performed against raw gyroscope sensor peaks ONLY.
    # latest_timeline.txt and on-device watch detections are NOT used as a reference.
    baseline_offset = None
    audio_filename = os.path.basename(audio_path)
    match = re.search(r"narration_(\d{8})_(\d{6})", audio_filename)

    # Derive a coarse baseline offset from the audio filename timestamp vs watch startup epoch.
    # This is used only as the centre of the grid search — NOT as a validation signal.
    watch_start_ms = None
    timeline_path = os.path.join(session_dir, "latest_timeline.txt")
    if os.path.exists(timeline_path):
        try:
            with open(timeline_path, "r") as f:
                for line in f:
                    if "SYSTEM_START:" in line:
                        m = re.search(r"Ts=(\d+)", line)
                        if m:
                            watch_start_ms = int(m.group(1))
                            break
        except Exception as e:
            print(f"⚠️ Error reading timeline for SYSTEM_START: {e}")

    if match and watch_start_ms is not None:
        date_str, time_str = match.groups()
        try:
            dt = datetime.datetime.strptime(f"{date_str}_{time_str}", "%Y%m%d_%H%M%S")
            audio_start_epoch = dt.timestamp()
            watch_start_epoch = watch_start_ms / 1000.0
            baseline_offset = audio_start_epoch - watch_start_epoch
            print(f"🎯 Auto-start synchronization: filename baseline offset calculated!")
            print(f"   Audio Start Time:  {dt} (Epoch: {audio_start_epoch:.3f}s)")
            print(f"   Watch Start Time:  {datetime.datetime.fromtimestamp(watch_start_epoch)} (Epoch: {watch_start_epoch:.3f}s)")
            print(f"   Calculated Baseline Clock Offset: {baseline_offset:+.3f}s")
        except Exception as e:
            print(f"⚠️ Failed to parse auto-start times: {e}")
            baseline_offset = 0.0
    else:
        baseline_offset = 0.0

    offset = args.manual_offset
    drift_rate = 0.0

    # 6a. Try Sync Tap Alignment (5 taps in < 5 seconds)
    sync_tap_offset = None
    sync_tap_drift_rate = 0.0
    
    df_acc = load_watch_sensor(session_dir, "WatchAccelerometer")
    if offset is None and not df_acc.empty:
        temp_wav = None
        try:
            print("🔍 Scanning for sync tap sequences (5 taps in < 5s) in sensor and audio logs...")
            # 1. Read accelerometer data
            acc_times = df_acc['seconds_elapsed'].to_numpy()
            acc_mags = np.sqrt(df_acc['x']**2 + df_acc['y']**2 + df_acc['z']**2)
            
            # Find candidate accel peaks above 18.0 m/s^2
            candidate_indices = np.where(acc_mags >= 18.0)[0]
            local_peaks = []
            for idx in candidate_indices:
                t = acc_times[idx]
                mag = acc_mags[idx]
                # Filter to local maximum in +/- 0.15s
                w_start = np.searchsorted(acc_times, t - 0.15)
                w_end = np.searchsorted(acc_times, t + 0.15, side='right')
                if mag >= np.max(acc_mags[w_start:w_end]):
                    if not any(abs(t - p[0]) < 0.2 for p in local_peaks):
                        local_peaks.append((t, mag))
            
            # Look for all non-overlapping 5-peak sequences in < 5s separated by [0.3s, 1.5s]
            accel_sequences = []
            i = 0
            while i < len(local_peaks) - 4:
                seq = local_peaks[i:i+5]
                seq_times = [p[0] for p in seq]
                if (seq_times[-1] - seq_times[0]) <= 5.0:
                    valid = True
                    for j in range(1, 5):
                        gap = seq_times[j] - seq_times[j-1]
                        if gap < 0.3 or gap > 1.5:
                            valid = False
                            break
                    if valid:
                        # Ensure this sequence doesn't overlap/adjacent within 10s of the last added sequence
                        if len(accel_sequences) == 0 or (seq_times[0] - accel_sequences[-1][0]) > 10.0:
                            accel_sequences.append(seq_times)
                            i += 5 # Skip past this sequence
                            continue
                i += 1
            
            # 2. Look for all non-overlapping 5 acoustic peaks in audio recording
            audio_sequences = []
            
            # Convert entire M4A to WAV for analysis
            temp_wav = os.path.join(session_dir, "sync_temp.wav")
            # Run ffmpeg to extract the entire duration
            subprocess.run([
                "ffmpeg", "-y", "-i", audio_path,
                "-ac", "1", "-ar", "16000", temp_wav
            ], check=True, capture_output=True)

            if os.path.exists(temp_wav):
                import wave
                with wave.open(temp_wav, "rb") as wav:
                    params = wav.getparams()
                    frames = wav.readframes(params.nframes)
                    samples = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
                    fps = params.framerate
                
                hop_length = int(fps * 0.02) # 20ms
                win_length = int(fps * 0.04) # 40ms
                rms = []
                times = []
                for start in range(0, len(samples) - win_length, hop_length):
                    win = samples[start:start+win_length]
                    rms.append(np.sqrt(np.mean(win**2)))
                    times.append(start / fps)
                
                rms = np.array(rms)
                times = np.array(times)
                
                if len(rms) > 0 and np.max(rms) > 0:
                    rms = rms / np.max(rms) # normalize
                    
                # Find peaks above normalized energy threshold
                threshold = 0.25
                cand_aud_indices = np.where(rms >= threshold)[0]
                aud_peaks = []
                for idx in cand_aud_indices:
                    t = times[idx]
                    val = rms[idx]
                    w_start = np.searchsorted(times, t - 0.15)
                    w_end = np.searchsorted(times, t + 0.15, side='right')
                    if val >= np.max(rms[w_start:w_end]):
                        if not any(abs(t - p) < 0.3 for p in aud_peaks):
                            aud_peaks.append(t)
                            
                # Search for all non-overlapping 5 peaks in < 5s with gaps in [0.3s, 1.5s]
                i = 0
                while i < len(aud_peaks) - 4:
                    seq = aud_peaks[i:i+5]
                    if (seq[-1] - seq[0]) <= 5.0:
                        valid = True
                        for j in range(1, 5):
                            gap = seq[j] - seq[j-1]
                            if gap < 0.3 or gap > 1.5:
                                valid = False
                                break
                        if valid:
                            audio_sequences.append(seq)
                            i += 5 # Skip past this sequence to avoid overlapping matches
                            continue
                    i += 1
            
            print(f"   Detected {len(accel_sequences)} accelerometer sync sequences.")
            print(f"   Detected {len(audio_sequences)} audio sync sequences.")
            
            # Match sequences sequentially using dynamic offset projection with pattern validation
            matched_pairs = []
            current_offset = baseline_offset
            used_acc_sequences = set()
            
            for aud_seq in audio_sequences:
                aud_t = aud_seq[0]
                projected_sensor_t = aud_t + current_offset
                
                # Find the closest accelerometer sequence within +/- 30.0s of projection
                best_match = None
                best_diff = 30.0
                for acc_seq in accel_sequences:
                    acc_t = acc_seq[0]
                    acc_seq_tuple = tuple(acc_seq)
                    if acc_seq_tuple in used_acc_sequences:
                        continue
                        
                    diff = abs(acc_t - projected_sensor_t)
                    if diff < best_diff:
                        # Validate the pattern gaps match:
                        gaps_acc = [acc_seq[j] - acc_seq[j-1] for j in range(1, 5)]
                        gaps_aud = [aud_seq[j] - aud_seq[j-1] for j in range(1, 5)]
                        gap_diffs = [abs(gaps_acc[j] - gaps_aud[j]) for j in range(4)]
                        max_gap_diff = max(gap_diffs)
                        mae_gaps = sum(gap_diffs) / 4.0
                        
                        if max_gap_diff <= 0.15 and mae_gaps <= 0.10:
                            best_diff = diff
                            best_match = acc_seq
                
                if best_match is not None:
                    matched_pairs.append((aud_seq, best_match))
                    used_acc_sequences.add(tuple(best_match))
                    # Update local tracking offset for the next sequence projection
                    current_offset = best_match[0] - aud_t
            
            matched_count = len(matched_pairs)
            if matched_count > 0:
                print(f"🎯 Sync taps DETECTED!")
                for idx, (aud_seq, acc_seq) in enumerate(matched_pairs):
                    print(f"   Sequence {idx+1}:")
                    print(f"      Accelerometer taps: {[f'{x:.2f}s' for x in acc_seq]}")
                    print(f"      Audio transient taps: {[f'{x:.2f}s' for x in aud_seq]}")
                
                # If we have multiple sync tap sequences, compute drift and offset using linear regression
                if matched_count >= 2:
                    x_pts = [] # Audio times
                    y_pts = [] # Sensor times
                    for aud_seq, acc_seq in matched_pairs:
                        x_pts.append(aud_seq[0])
                        y_pts.append(acc_seq[0])
                    
                    x_arr = np.array(x_pts)
                    y_arr = np.array(y_pts)
                    
                    # Slope (1 + drift_rate), Intercept (offset)
                    slope, intercept = np.polyfit(x_arr, y_arr, 1)
                    sync_tap_drift_rate = slope - 1.0
                    sync_tap_offset = intercept
                    
                    print(f"🎯 Multi-Point Regression Calibration:")
                    print(f"   Calculated Offset:     {sync_tap_offset:+.3f}s")
                    print(f"   Calculated Drift Rate:  {sync_tap_drift_rate:+.7f} ({sync_tap_drift_rate*100:+.4f}% speed correction)")
                else:
                    # Single point fallback: drift_rate = 0.0, offset = first accel tap - first audio tap
                    sync_tap_offset = matched_pairs[0][1][0] - matched_pairs[0][0][0]
                    sync_tap_drift_rate = 0.0
                    print(f"🎯 Single-Point Fallback Calibration:")
                    print(f"   Calculated Offset:     {sync_tap_offset:+.3f}s (Drift rate forced to 0.0)")
            else:
                if len(accel_sequences) == 0:
                    print("   ❌ Accelerometer sync tap sequences NOT found.")
                if len(audio_sequences) == 0:
                    print("   ❌ Audio acoustic sync tap sequences NOT found.")
                else:
                    print("   ❌ No accelerometer sequence matched the audio sequences near the baseline offset.")
        except Exception as e:
            print(f"⚠️ Error trying sync tap alignment: {e}")
        finally:
            if temp_wav and os.path.exists(temp_wav):
                try:
                    os.remove(temp_wav)
                except:
                    pass
 
    if offset is not None:
        print(f"🎯 Using manual clock offset override: {offset:+.3f}s")
    elif sync_tap_offset is not None:
        offset = sync_tap_offset
        drift_rate = sync_tap_drift_rate
        print(f"🎯 Using sync tap alignment offset: {offset:+.3f}s, drift rate: {drift_rate:+.7f} (skipping grid search optimization)")
    else:
        if narrations:
            search_center = baseline_offset if baseline_offset is not None else 0.0
            search_range = 2.5
            print(f"🔍 Starting clock offset and drift optimization grid search against raw gyroscope peaks")
            print(f"   (center={search_center:+.3f}s, range=\u00b1{search_range}s)")
            print(f"   ⚠️  Scoring is based ONLY on raw sensor peak matches — no watch detections used.")

            # Filter the globally precalculated prominence peaks for grid search candidates >= 3.0 rad/s
            print("📈 Filtering gyroscope sensor peaks for grid search candidates >= 3.0 rad/s...")
            precalculated_peaks = [p for p in session_peaks if p['mag'] >= 3.0]
            print(f"   Found {len(precalculated_peaks)} candidate peaks >= 3.0 rad/s.")

            def evaluate_offset_and_drift(o, d):
                """Score an (offset, drift) pair by counting how many active shots
                align to a real gyroscope peak (non-fallback). This is purely
                sensor-driven — no latest_timeline.txt or watch detections involved."""
                all_candidates = []
                for i, shot in enumerate(narrations):
                    audio_t = shot['timestamp_seconds']
                    sensor_narr_t = audio_t * (1 + d) + o
                    shot_type_lower = shot['shot_type'].lower()
                    is_non_swing = any(term in shot_type_lower for term in ["no shot", "leave", "facing up", "evade"])

                    cands = []
                    if is_non_swing:
                        cands.append({
                            'time': sensor_narr_t - 2.5,
                            'mag': 1.0,
                            'is_fallback': True
                        })
                    else:
                        # Find peaks within [sensor_narr_t - 6.0, sensor_narr_t + 7.0] from precalculated_peaks
                        window_peaks = [
                            p for p in precalculated_peaks
                            if sensor_narr_t - 6.0 <= p['time'] <= sensor_narr_t + 7.0
                        ]
                        # Sort by mag descending and take top 5
                        window_peaks = sorted(window_peaks, key=lambda x: x['mag'], reverse=True)[:5]
                        cands.extend(window_peaks)
                        cands.append({
                            'time': sensor_narr_t - 2.5,
                            'mag': 1.0,
                            'is_fallback': True
                        })
                    all_candidates.append(cands)

                def calculate_candidate_score(cand, sensor_narr_t):
                    t = cand['time']
                    mag = cand['mag']
                    is_fallback = cand['is_fallback']
                    if is_fallback:
                        return -3.0
                    lag = sensor_narr_t - t
                    if lag < -7.0:
                        return -999999.0
                    elif lag < 0.0:
                        return np.log(mag) - ((lag - 2.5) ** 2) / 4.5 - 5.0
                    else:
                        return np.log(mag) - ((lag - 2.5) ** 2) / 4.5

                # DP alignment
                M = len(narrations)
                dp = []
                parent = []

                first_narr_t = narrations[0]['timestamp_seconds'] * (1 + d) + o
                dp.append([calculate_candidate_score(cand, first_narr_t) for cand in all_candidates[0]])
                parent.append([-1] * len(all_candidates[0]))

                for i in range(1, M):
                    sensor_narr_t = narrations[i]['timestamp_seconds'] * (1 + d) + o
                    dp_i = []
                    parent_i = []
                    for j, cand in enumerate(all_candidates[i]):
                        best_score = -999999.0
                        best_k = -1
                        score_j = calculate_candidate_score(cand, sensor_narr_t)

                        prev_type_lower = narrations[i-1]['shot_type'].lower()
                        prev_is_non_swing = any(term in prev_type_lower for term in ["no shot", "leave", "facing up", "evade"])
                        curr_type_lower = narrations[i]['shot_type'].lower()
                        curr_is_non_swing = any(term in curr_type_lower for term in ["no shot", "leave", "facing up", "evade"])
                        min_gap = 0.5 if (prev_is_non_swing or curr_is_non_swing) else 1.5

                        for k, prev_cand in enumerate(all_candidates[i-1]):
                            if prev_cand['time'] < cand['time'] - min_gap:
                                val = dp[i-1][k] + score_j
                                if val > best_score:
                                    best_score = val
                                    best_k = k

                        if best_k == -1:
                            for k, prev_cand in enumerate(all_candidates[i-1]):
                                if prev_cand['time'] < cand['time']:
                                    val = dp[i-1][k] + score_j
                                    if val > best_score:
                                        best_score = val
                                        best_k = k
                        if best_k == -1:
                            best_k = 0
                            best_score = dp[i-1][0] + score_j

                        dp_i.append(best_score)
                        parent_i.append(best_k)
                    dp.append(dp_i)
                    parent.append(parent_i)

                best_j = int(np.argmax(dp[M-1]))
                chosen_indices = [best_j]
                for i in range(M-1, 0, -1):
                    best_j = parent[i][best_j]
                    chosen_indices.append(best_j)
                chosen_indices.reverse()

                # Score = count of active shots that matched a REAL gyroscope peak (not fallback)
                # MAE = average lag from narration timestamp to matched peak for non-fallbacks
                real_peak_matches = 0
                lags = []
                for i, shot in enumerate(narrations):
                    shot_type_lower = shot['shot_type'].lower()
                    is_non_swing = any(term in shot_type_lower for term in ["no shot", "leave", "facing up", "evade"])
                    if is_non_swing:
                        continue
                    chosen_cand = all_candidates[i][chosen_indices[i]]
                    if not chosen_cand['is_fallback']:
                        real_peak_matches += 1
                        sensor_narr_t = shot['timestamp_seconds'] * (1 + d) + o
                        lags.append(abs(sensor_narr_t - chosen_cand['time']))

                mae = np.mean(lags) if lags else 999.0
                return real_peak_matches, mae

            # Coarse grid search
            coarse_offsets = np.arange(search_center - search_range, search_center + search_range + 0.1, 1.0)
            coarse_drifts = np.arange(-0.008, 0.0081, 0.001)
            best_matches = -1
            best_offset = search_center
            best_drift = 0.0
            best_mae = 999.0

            for d in coarse_drifts:
                for o in coarse_offsets:
                    det, mae = evaluate_offset_and_drift(o, d)
                    if det > best_matches or (det == best_matches and mae < best_mae):
                        best_matches = det
                        best_offset = o
                        best_drift = d
                        best_mae = mae

            # Fine grid search
            fine_offsets = np.arange(best_offset - 1.2, best_offset + 1.21, 0.1)
            fine_drifts = np.arange(best_drift - 0.001, best_drift + 0.0011, 0.0002)
            for d in fine_drifts:
                for o in fine_offsets:
                    det, mae = evaluate_offset_and_drift(o, d)
                    if det > best_matches or (det == best_matches and mae < best_mae):
                        best_matches = det
                        best_offset = o
                        best_drift = d
                        best_mae = mae

            offset = best_offset
            drift_rate = best_drift

            active_shot_count = sum(1 for s in narrations if not any(
                term in s['shot_type'].lower() for term in ["no shot", "leave", "facing up", "evade"]
            ))
            print(f"🎯 Clock offset and drift optimized against raw gyroscope peaks:")
            if baseline_offset is not None:
                print(f"   Filename baseline offset:  {baseline_offset:+.3f}s")
            print(f"   Optimized offset:          {offset:+.3f}s")
            print(f"   Optimized drift rate:      {drift_rate:+.6f} ({drift_rate * 100:.3f}% speed correction)")
            print(f"   Gyro peak matches:         {best_matches}/{active_shot_count} active shots (MAE: {best_mae:.3f}s)")
            if active_shot_count > 0:
                match_pct = best_matches / active_shot_count * 100
                print(f"   Gyro match rate:           {match_pct:.1f}%")
                if match_pct < 50:
                    print(f"   ⚠️  WARNING: Less than 50% of active shots matched a real gyro peak.")
                    print(f"      This may indicate a transcription timing problem or a corrupt session.")
        else:
            if baseline_offset is not None:
                offset = baseline_offset
                print(f"⚠️ No narrations available. Using baseline filename offset: {offset:+.3f}s")
            else:
                print("⚠️ WARNING: No narrations and no filename timestamp available for offset.")
                inp = input("Please enter manual clock offset (seconds) or 0 to skip: ").strip()
                try:
                    offset = float(inp)
                except:
                    offset = 0.0

    # Filter narrations to exclude out-of-bounds events relative to active watch data logging
    filtered_narrations = []
    for shot in narrations:
        audio_t = shot['timestamp_seconds']
        sensor_narr_t = audio_t * (1 + drift_rate) + offset
        if -5.0 <= sensor_narr_t <= gyro_duration + 5.0:
            filtered_narrations.append(shot)
        else:
            print(f"   🚫 Excluding shot '{shot['narrated_text']}' at {audio_t:.1f}s (estimated sensor: {sensor_narr_t:.1f}s) - outside watch logging range [0.0, {gyro_duration:.1f}s]")
    narrations = filtered_narrations

    if len(narrations) == 0:
        print("\n" + "="*80)
        print("❌ ALIGNMENT ERROR: Zero active shots found within watch logging duration after filtering!")
        print(f"   Watch recorded for only {gyro_duration:.1f} seconds, but all narrated shots fall outside this window.")
        print("="*80 + "\n")
        raise RuntimeError(f"❌ Alignment failed: Zero narrated shots overlap with the watch logging duration [0.0, {gyro_duration:.1f}s].")

    # 7. Perform Dynamic Programming Sequence Alignment
    aligned_shots = []
    
    # Build candidate lists
    all_candidates = []
    for i, shot in enumerate(narrations):
        audio_t = shot['timestamp_seconds']
        sensor_narr_t = audio_t * (1 + drift_rate) + offset
        shot_type_lower = shot['shot_type'].lower()
        is_non_swing = any(term in shot_type_lower for term in ["no shot", "leave", "facing up", "evade"])
        
        cands = []
        if is_non_swing:
            cands.append({
                'time': sensor_narr_t - 2.5,
                'mag': 1.0,
                'is_fallback': True
            })
        else:
            # 2-stage threshold filter based on globally precalculated prominence peaks in the window
            window_peaks = [
                p for p in session_peaks
                if sensor_narr_t - 6.0 <= p['time'] <= sensor_narr_t + 7.0 and p['mag'] >= 0.75
            ]
            peaks = sorted(window_peaks, key=lambda x: x['mag'], reverse=True)[:5]
                    
            cands.extend(peaks)
            cands.append({
                'time': sensor_narr_t - 2.5,
                'mag': 1.0,
                'is_fallback': True
            })
        all_candidates.append(cands)
        
    def calculate_candidate_score(cand, sensor_narr_t):
        t = cand['time']
        mag = cand['mag']
        is_fallback = cand['is_fallback']
        if is_fallback:
            return -3.0
        lag = sensor_narr_t - t
        if lag < -7.0:
            return -999999.0
        elif lag < 0.0:
            return np.log(mag) - ((lag - 2.5) ** 2) / 4.5 - 5.0
        else:
            return np.log(mag) - ((lag - 2.5) ** 2) / 4.5

    # DP Table
    M = len(narrations)
    dp = []
    parent = []
    
    # Initialize first step
    first_narr_t = narrations[0]['timestamp_seconds'] * (1 + drift_rate) + offset
    dp.append([calculate_candidate_score(cand, first_narr_t) for cand in all_candidates[0]])
    parent.append([-1] * len(all_candidates[0]))
    
    for i in range(1, M):
        sensor_narr_t = narrations[i]['timestamp_seconds'] * (1 + drift_rate) + offset
        dp_i = []
        parent_i = []
        for j, cand in enumerate(all_candidates[i]):
            best_score = -999999.0
            best_k = -1
            score_j = calculate_candidate_score(cand, sensor_narr_t)
            
            # Enforce chronological order with min gap
            # Swing-to-swing gap: 1.5s. Non-swing gap: 0.5s.
            prev_type_lower = narrations[i-1]['shot_type'].lower()
            prev_is_non_swing = any(term in prev_type_lower for term in ["no shot", "leave", "facing up", "evade"])
            curr_type_lower = narrations[i]['shot_type'].lower()
            curr_is_non_swing = any(term in curr_type_lower for term in ["no shot", "leave", "facing up", "evade"])
            min_gap = 0.5 if (prev_is_non_swing or curr_is_non_swing) else 1.5
            
            for k, prev_cand in enumerate(all_candidates[i-1]):
                if prev_cand['time'] < cand['time'] - min_gap:
                    val = dp[i-1][k] + score_j
                    if val > best_score:
                        best_score = val
                        best_k = k
                        
            # Dynamic relaxation if no path is valid
            if best_k == -1:
                for k, prev_cand in enumerate(all_candidates[i-1]):
                    if prev_cand['time'] < cand['time']:
                        val = dp[i-1][k] + score_j
                        if val > best_score:
                            best_score = val
                            best_k = k
            if best_k == -1:
                # Force fallback to the first candidate of the previous step
                best_k = 0
                best_score = dp[i-1][0] + score_j
                
            dp_i.append(best_score)
            parent_i.append(best_k)
        dp.append(dp_i)
        parent.append(parent_i)
        
    # Backtrack
    best_j = int(np.argmax(dp[M-1]))
    chosen_indices = [best_j]
    for i in range(M-1, 0, -1):
        best_j = parent[i][best_j]
        chosen_indices.append(best_j)
    chosen_indices.reverse()
    
    print("\nAligning spoken narrations with physical movements...")
    for i, shot in enumerate(narrations):
        audio_t = shot['timestamp_seconds']
        sensor_narr_t = audio_t * (1 + drift_rate) + offset
        chosen_cand = all_candidates[i][chosen_indices[i]]
        impact_t = chosen_cand['time']
        
        closest_row = df_gyro.iloc[(df_gyro['seconds_elapsed'] - impact_t).abs().argsort()[:1]]
        impact_row = closest_row.iloc[0]
        impact_t = impact_row['seconds_elapsed']
        impact_ns = impact_row['time']
        gyro_mag = impact_row['mag'] if not chosen_cand['is_fallback'] else chosen_cand['mag']
        
        if chosen_cand['is_fallback']:
            print(f"   💨 '{shot['narrated_text']}' ({audio_t:.1f}s audio) ➔ Fallback at {impact_t:.2f}s sensor (rel) / {impact_ns} (ns)")
        else:
            print(f"   🔗 '{shot['narrated_text']}' ({audio_t:.1f}s audio) ➔ Swing at {impact_t:.2f}s sensor (rel) / {impact_ns} (ns)")
            
        aligned_shots.append({
            'shot_index': len(aligned_shots) + 1,
            'shot_number': shot.get('shot_number'),
            'audio_time_seconds': audio_t,
            'sensor_narr_time_seconds': sensor_narr_t,
            'impact_time_seconds': impact_t,
            'impact_timestamp_ns': impact_ns,
            'impact_gyro_mag': gyro_mag,
            'is_fallback': bool(chosen_cand['is_fallback']),
            'shot_type': shot['shot_type'],
            'quality': shot['quality'],
            'narrated_text': shot['narrated_text']
        })
        
    # Validation Check:
    active_swings = [
        s for s in aligned_shots 
        if not any(term in s['shot_type'].lower() for term in ["no shot", "leave", "facing up", "evade"])
        and s['sensor_narr_time_seconds'] >= -5.0 
        and s['sensor_narr_time_seconds'] <= gyro_duration + 5.0
    ]
    if len(aligned_shots) == 0:
        raise RuntimeError("❌ Alignment failed: Zero shots parsed or aligned.")
    if len(active_swings) == 0:
        print("\n" + "="*80)
        print("⚠️ Warning: Zero attacking active swings found within watch logging duration.")
        print("   Proceeding since sync taps or fallback shots were aligned.")
        print("="*80 + "\n")
        
    fallback_swings = [s for s in active_swings if s['is_fallback']]
    fallback_rate = len(fallback_swings) / len(active_swings) if len(active_swings) > 0 else 0.0
    
    print(f"\n📊 Alignment Validation check:")
    print(f"   Active swings:         {len(active_swings)}")
    print(f"   Fallback alignments:   {len(fallback_swings)} ({fallback_rate * 100:.1f}%)")
    
    if fallback_rate > 0.25:
        # High fallback rate indicates a clock mismatch, bad alignment, or broken parser!
        aligned_csv_path = os.path.join(session_dir, "ground_truth_aligned.csv")
        if os.path.exists(aligned_csv_path):
            os.remove(aligned_csv_path)
            
        print("\n" + "="*80)
        print("❌ ALIGNMENT ERROR: High fallback rate detected during physical peak matching!")
        print(f"   {fallback_rate * 100:.1f}% of active swings were mapped to fallback wiggles.")
        print("   This indicates that the clock offset optimization failed or the timeline is corrupted.")
        print("="*80 + "\n")
        raise RuntimeError(
            f"❌ Alignment failed due to high fallback rate ({fallback_rate * 100:.1f}%). "
            f"Expected fallback rate to be <= 25%."
        )

    df_aligned = pd.DataFrame(aligned_shots)
    aligned_csv_path = os.path.join(session_dir, "ground_truth_aligned.csv")
    df_aligned.to_csv(aligned_csv_path, index=False)
    print(f"\n✅ Ground-truth aligned file saved: {aligned_csv_path}")
    
    # 7. Extract training segments (6-second window around each impact)
    df_accel = load_watch_sensor(session_dir, "WatchAccelerometer")
    df_gravity = load_watch_sensor(session_dir, "WatchGravity")
    
    # Load Game Rotation Vector or fallback orientation
    df_orient = load_watch_sensor(session_dir, "WatchGameOrientation")
    if df_orient.empty:
        df_orient = load_watch_sensor(session_dir, "WatchOrientation")
        print("📖 Loaded WatchOrientation for bat orientation (fallback)")
    else:
        print("📖 Loaded WatchGameOrientation for bat orientation")
        
    df_steps = load_watch_sensor(session_dir, "WatchSteps")
    if df_steps.empty:
        df_steps = None
    else:
        print("📖 Loaded WatchSteps for walking steps check")
        
    print("📈 Computing Blade and Launch angles at impact...")
    df_aligned = add_angle_stats_to_aligned_shots(df_aligned, df_orient)
    # Overwrite the CSV with new columns
    df_aligned.to_csv(aligned_csv_path, index=False)
    print(f"✅ Updated aligned file with angle stats: {aligned_csv_path}")

    # Enrich aligned shots with Polar Sense bottom-hand biomechanics features
    add_polar_features_to_aligned_shots(session_dir, offset=offset, watch_start_epoch=watch_start_epoch)
        
    steps_path = resolve_sensor_path(session_dir, "WatchSteps.csv")
    if os.path.exists(steps_path):
        df_steps = pd.read_csv(steps_path)
        print(f"📖 Loaded {os.path.basename(steps_path)} for walking steps check")
    else:
        df_steps = None
        
    # Run Stance Diagnostics for Facing up events
    stance_events_count = 0
    for idx, row in df_aligned.iterrows():
        if row['shot_type'] == "Facing up":
            run_stance_diagnostics(
                row['narrated_text'],
                row['audio_time_seconds'],
                row['impact_time_seconds'],
                df_gyro, df_accel, df_gravity, df_orient, df_steps
            )
            stance_events_count += 1
    if stance_events_count == 0:
        print("ℹ️ No 'Facing up' stance events found in this session.")
    
    save_segments = getattr(args, "save_segments", False)
    if save_segments:
        print("\nExporting 6-second training segments (3s before, 3s after impact)...")
        segments_dir = os.path.join(session_dir, "segments")
        os.makedirs(segments_dir, exist_ok=True)
        segments_saved = 0
        for idx, row in df_aligned.iterrows():
            if row['shot_type'] == "Facing up":
                continue
                
            t_impact = row['impact_time_seconds']
            shot_name = row['shot_type'].lower().replace(" ", "_").replace("/", "_")
            qual_name = row['quality'].lower().replace(" ", "_").replace("/", "_")
            
            t_start = t_impact - 3.0
            t_end = t_impact + 3.0
            
            g_slice = df_gyro[(df_gyro['seconds_elapsed'] >= t_start) & (df_gyro['seconds_elapsed'] <= t_end)]
            a_slice = df_accel[(df_accel['seconds_elapsed'] >= t_start) & (df_accel['seconds_elapsed'] <= t_end)]
            gr_slice = df_gravity[(df_gravity['seconds_elapsed'] >= t_start) & (df_gravity['seconds_elapsed'] <= t_end)]
            o_slice = df_orient[(df_orient['seconds_elapsed'] >= t_start) & (df_orient['seconds_elapsed'] <= t_end)]
            
            prefix = f"seg_{idx+1:02d}_{shot_name}_{qual_name}"
            g_slice.to_csv(os.path.join(segments_dir, f"{prefix}_WatchGyroscope.csv"), index=False)
            a_slice.to_csv(os.path.join(segments_dir, f"{prefix}_WatchAccelerometer.csv"), index=False)
            gr_slice.to_csv(os.path.join(segments_dir, f"{prefix}_WatchGravity.csv"), index=False)
            o_slice.to_csv(os.path.join(segments_dir, f"{prefix}_WatchOrientation.csv"), index=False)
            segments_saved += 1
            
        print(f"✅ Saved {segments_saved} training segments to {segments_dir}/")
    else:
        print("\nℹ️ Skipping segment CSV exports (to prevent file count bloat). Use --save-segments to export.")

    # Append raw watch sensor logs to the combined Parquet database
    combined_parquet_dir = os.path.join(args.dest, "..", "combined_sensor_data.parquet")
    append_to_combined_parquet(session_dir, os.path.abspath(combined_parquet_dir))
    
    # Losslessly compress all raw Watch*.csv files to Watch*.csv.gz and delete original CSVs
    compress_session_csvs(session_dir)
def run_stance_diagnostics(narrated_text, audio_t, t_stance, df_gyro, df_accel, df_gravity, df_orient, df_steps):
    t_start = t_stance
    t_end = t_stance + 1.5
    
    # gyro std
    g_win = df_gyro[(df_gyro['seconds_elapsed'] >= t_start) & (df_gyro['seconds_elapsed'] <= t_end)]
    if len(g_win) >= 2:
        g_mags = np.sqrt(g_win['x']**2 + g_win['y']**2 + g_win['z']**2)
        gyro_std = np.std(g_mags, ddof=0)
    else:
        gyro_std = 0.0
        
    # accel std
    a_win = df_accel[(df_accel['seconds_elapsed'] >= t_start) & (df_accel['seconds_elapsed'] <= t_end)]
    if len(a_win) >= 2:
        a_mags = np.sqrt(a_win['x']**2 + a_win['y']**2 + a_win['z']**2)
        accel_std = np.std(a_mags, ddof=0)
    else:
        accel_std = 0.0
        
    # ori_disp
    if df_orient is not None and len(df_orient) > 0:
        o_win = df_orient[(df_orient['seconds_elapsed'] >= t_start) & (df_orient['seconds_elapsed'] <= t_end)]
        if len(o_win) >= 2:
            o_win = o_win.sort_values(by='seconds_elapsed')
            qx = o_win['qx'].values
            qy = o_win['qy'].values
            qz = o_win['qz'].values
            qw = o_win['qw'].values
            dots = qx[:-1]*qx[1:] + qy[:-1]*qy[1:] + qz[:-1]*qz[1:] + qw[:-1]*qw[1:]
            dots = np.clip(np.abs(dots), -1.0, 1.0)
            angles = np.degrees(2.0 * np.arccos(dots))
            ori_disp = np.mean(angles)
        else:
            ori_disp = 999.0
    else:
        ori_disp = 0.0
        
    # steps
    if df_steps is not None and len(df_steps) > 0:
        s_win = df_steps[(df_steps['seconds_elapsed'] >= t_start - 2.0) & (df_steps['seconds_elapsed'] <= t_end)]
        steps_count = len(s_win)
    else:
        steps_count = 0
        
    # mean gravity Y
    if df_gravity is not None and len(df_gravity) > 0:
        gr_win = df_gravity[(df_gravity['seconds_elapsed'] >= t_start) & (df_gravity['seconds_elapsed'] <= t_end)]
        grav_y = np.mean(gr_win['y']) if len(gr_win) > 0 else 0.0
    else:
        grav_y = -9.8
        
    # ── Gate constants — must stay in sync with SwingDetector.kt ────────────
    # Mandatory gates (both must pass)
    GYRO_STD_MAX  = 1.2   # FACING_UP_GYRO_STD_MAX     = 1.2f rad/s
    # Flexible gates (MIN_FLEXIBLE of 3 must pass)
    ACCEL_STD_MAX = 3.25  # FACING_UP_ACCEL_STD_MAX    = 3.25f m/s²
    ORI_DISP_MAX  = 2.5   # FACING_UP_ORI_DISP_MAX_DEG = 2.5f degrees
    GRAV_Y_MIN    = -6.0  # FACING_UP_GRAVITY_Y_MIN    = -6.0f m/s²
    MIN_FLEXIBLE  = 3     # FACING_UP_MIN_FLEXIBLE_CONDITIONS = 3

    # Mandatory gate evaluations
    gyro_ok  = gyro_std < GYRO_STD_MAX
    steps_ok = steps_count == 0

    # Flexible gate evaluations (accel OR ori OR arm_extended)
    accel_ok = accel_std < ACCEL_STD_MAX
    ori_ok   = ori_disp < ORI_DISP_MAX
    # arm_extended: fail-open (0.0) when gravity data is absent (matches Kotlin sentinel)
    arm_ok   = grav_y <= GRAV_Y_MIN or grav_y == 0.0

    flexible_count = int(accel_ok) + int(ori_ok) + int(arm_ok)
    passed = gyro_ok and steps_ok and (flexible_count >= MIN_FLEXIBLE)
    status_emoji = "🟢 SUCCESS" if passed else "🔴 FAILED"

    print("\n=================== Stance Check Alignment Analysis ===================")
    print(f"Stance Event: '{narrated_text}'")
    print(f"Time:         {audio_t:.1f}s (audio) ➔ Stance aligned at {t_stance:.2f}s sensor (rel)")
    print(f"  [MANDATORY] Gyro Std:  {gyro_std:.2f} rad/s  (Limit: < {GYRO_STD_MAX})   ➔ {'PASS' if gyro_ok else 'FAIL'}")
    print(f"  [MANDATORY] Steps:     {steps_count} events   (Limit: 0 in last 1.0s) ➔ {'PASS' if steps_ok else 'FAIL'}")
    print(f"  [FLEXIBLE]  Accel Std: {accel_std:.2f} m/s²   (Limit: < {ACCEL_STD_MAX}) ➔ {'PASS' if accel_ok else 'FAIL'}")
    print(f"  [FLEXIBLE]  Ori Disp:  {ori_disp:.2f} deg     (Limit: < {ORI_DISP_MAX})   ➔ {'PASS' if ori_ok else 'FAIL'}")
    print(f"  [FLEXIBLE]  Gravity Y: {grav_y:.2f} m/s²  (Limit: <= {GRAV_Y_MIN})  ➔ {'PASS' if arm_ok else 'FAIL'}")
    print(f"  Flexible gates passed: {flexible_count}/{MIN_FLEXIBLE} required")
    print(f"STATUS: {status_emoji} ({'All conditions met' if passed else 'Stance lock would fail'})")
    if not passed:
        fails = []
        if not gyro_ok:  fails.append(f"[MANDATORY] Gyro Std ({gyro_std:.2f} >= {GYRO_STD_MAX})")
        if not steps_ok: fails.append(f"[MANDATORY] Steps ({steps_count} event(s) in last 1.0s)")
        if flexible_count < MIN_FLEXIBLE:
            flex_fails = []
            if not accel_ok: flex_fails.append(f"Accel ({accel_std:.2f} >= {ACCEL_STD_MAX})")
            if not ori_ok:   flex_fails.append(f"Ori ({ori_disp:.2f} >= {ORI_DISP_MAX})")
            if not arm_ok:   flex_fails.append(f"GravY ({grav_y:.2f} > {GRAV_Y_MIN})")
            fails.append(f"[FLEXIBLE] Only {flexible_count}/{MIN_FLEXIBLE} passed: failing={', '.join(flex_fails)}")
        print(f"  Failed: {'; '.join(fails)}")
    print("-----------------------------------------------------------------------")

def add_angle_stats_to_aligned_shots(df_aligned, df_orient):
    def multiply_quats(q1, q2):
        x1, y1, z1, w1 = q1
        x2, y2, z2, w2 = q2
        return np.array([
            w1*x2 + x1*w2 + y1*z2 - z1*y2,
            w1*y2 - x1*z2 + y1*w2 + z1*x2,
            w1*z2 + x1*y2 - y1*x2 + z1*w2,
            w1*w2 - x1*x2 - y1*y2 - z1*z2,
        ])

    def conjugate_quat(q):
        return np.array([-q[0], -q[1], -q[2], q[3]])

    def rotate_vector(q, v):
        qx, qy, qz, qw = q
        vx, vy, vz = v
        tx = 2.0 * (qy*vz - qz*vy)
        ty = 2.0 * (qz*vx - qx*vz)
        tz = 2.0 * (qx*vy - qy*vx)
        return np.array([
            vx + qw*tx + (qy*tz - qz*ty),
            vy + qw*ty + (qz*tx - qx*tz),
            vz + qw*tz + (qx*ty - qy*tx),
        ])

    def calc_relative_roll(q):
        x, y, z, w = q
        return np.degrees(np.arctan2(2.0 * (w*y + x*z), 1.0 - 2.0 * (y*y + z*z)))

    def classify_blade(angle):
        if angle <= -15.0: return "OPEN"
        if angle >= 15.0: return "CLOSED"
        return "FULL_FACE"

    def classify_launch(angle):
        if angle < -45.0: return "HIGH_LOFT"
        if angle < -35.0: return "POWER_ZONE"
        if angle < -15.0: return "LOFTED"
        if angle < 0.0: return "FLAT"
        return "INTO_GROUND"

    canonical_targets = {
        "COVER_DRIVE": -45.0,
        "STRAIGHT_DRIVE": 0.0,
        "ON_DRIVE": 15.0,
        "DEFENCE/BLOCK": 0.0,
        "CUT/PUNCH": 40.0,
        "GLANCE/FLICK": 75.0,
        "PULL/HOOK": 55.0,
        "SWEEP": 65.0,
    }

    blade_angles = []
    blade_classes = []
    launch_angles = []
    launch_classes = []

    for idx, row in df_aligned.iterrows():
        shot_type = row['shot_type']
        t_shot = row['impact_time_seconds']
        shot_class = normalize_shot_class(shot_type)
        
        # Check for non-swing types
        is_non_swing = shot_class == "Unknown" or shot_type.lower().strip() in ["facing up", "no shot", "leave", "evade", "evasion"]
        if is_non_swing or df_orient is None or len(df_orient) == 0:
            blade_angles.append(np.nan)
            blade_classes.append("N/A")
            launch_angles.append(np.nan)
            launch_classes.append("N/A")
            continue

        # 1. Get stance quat
        stance_ori = df_orient[(df_orient['seconds_elapsed'] >= t_shot - 2.5) & 
                               (df_orient['seconds_elapsed'] <= t_shot - 1.5)]
        if len(stance_ori) < 2:
            stance_ori = df_orient[(df_orient['seconds_elapsed'] >= t_shot - 3.5) & 
                                   (df_orient['seconds_elapsed'] <= t_shot - 1.5)]

        if len(stance_ori) >= 2:
            q0 = np.array([stance_ori.iloc[0]['qx'], stance_ori.iloc[0]['qy'], stance_ori.iloc[0]['qz'], stance_ori.iloc[0]['qw']])
            s = q0.copy()
            for i in range(1, len(stance_ori)):
                row_ori = stance_ori.iloc[i]
                qi = np.array([row_ori['qx'], row_ori['qy'], row_ori['qz'], row_ori['qw']])
                dot = np.dot(q0, qi)
                sign = 1.0 if dot >= 0 else -1.0
                s += sign * qi
            q_stance = s / np.linalg.norm(s)
        else:
            q_stance = np.array([0.0, 0.0, 0.0, 1.0])

        q_stance_inv = conjugate_quat(q_stance)

        # 2. Get impact quat
        impact_ori = df_orient.iloc[(df_orient['seconds_elapsed'] - t_shot).abs().argsort()[:1]]
        if len(impact_ori) > 0:
            row_impact = impact_ori.iloc[0]
            q_impact = np.array([row_impact['qx'], row_impact['qy'], row_impact['qz'], row_impact['qw']])
        else:
            q_impact = np.array([0.0, 0.0, 0.0, 1.0])

        # Relative rotation
        q_rel = multiply_quats(q_stance_inv, q_impact)

        # Relative roll
        roll_impact = calc_relative_roll(q_rel)

        # Target reference yaw
        target_yaw = canonical_targets.get(shot_class, 0.0)
        is_horizontal_bat = shot_class in ["CUT/PUNCH", "PULL/HOOK", "SWEEP"]
        if is_horizontal_bat:
            if shot_class == "CUT/PUNCH":
                target_yaw = 40.0
            elif shot_class == "PULL/HOOK":
                target_yaw = 55.0
            elif shot_class == "SWEEP":
                target_yaw = 65.0
        else:
            if "cover drive" in shot_type.lower():
                target_yaw = -45.0
            elif "straight drive" in shot_type.lower():
                target_yaw = 0.0
            elif "on drive" in shot_type.lower():
                target_yaw = 15.0

        # Relative face normal vector (local X rotated by q_rel)
        v_face_rel = rotate_vector(q_rel, np.array([1.0, 0.0, 0.0]))
        # Horizontal angle of the bat face relative to the stance setup
        yaw_face_rel = np.degrees(np.arctan2(v_face_rel[1], v_face_rel[0]))
        
        # Blade angle is deviation
        b_angle = yaw_face_rel - target_yaw
        # Normalize to -180 to 180 to avoid wrap-around anomalies
        b_angle = (b_angle + 180) % 360 - 180
        
        blade_angles.append(round(b_angle, 1))
        blade_classes.append(classify_blade(b_angle))

        # Launch Angle
        if is_horizontal_bat:
            l_angle = roll_impact
        else:
            v_face_world = rotate_vector(q_impact, np.array([1.0, 0.0, 0.0]))
            l_angle = -np.degrees(np.arcsin(v_face_world[2]))
            
        launch_angles.append(round(l_angle, 1))
        launch_classes.append(classify_launch(l_angle))

    df_aligned['blade_angle_deg'] = blade_angles
    df_aligned['blade_class'] = blade_classes
    df_aligned['launch_angle_deg'] = launch_angles
    df_aligned['launch_class'] = launch_classes
    return df_aligned

def add_polar_features_to_aligned_shots(session_dir, offset=None, watch_start_epoch=None):
    """Align Polar Sense ACC/GYRO data with watch data via 5-tap sequences or phone timestamp fallback,
    then compute bottom-hand biomechanics features for each aligned shot."""
    polar_dir = os.path.join(session_dir, "PolarSense")
    if not os.path.isdir(polar_dir):
        print("\nℹ️ No PolarSense/ directory found. Skipping Polar feature extraction.")
        return

    aligned_csv_path = os.path.join(session_dir, "ground_truth_aligned.csv")
    if not os.path.exists(aligned_csv_path):
        print("⚠️ ground_truth_aligned.csv not found. Skipping Polar feature extraction.")
        return

    # 1. Discover Polar ACC and GYRO CSV/BIN files (case-insensitive globbing)
    polar_acc_files = sorted(glob.glob(os.path.join(polar_dir, "*[aA][cC][cC]*.csv*")) +
                             glob.glob(os.path.join(polar_dir, "*[aA][cC][cC]*.bin*")))
    polar_gyro_files = sorted(glob.glob(os.path.join(polar_dir, "*[gG][yY][rR][oO]*.csv*")) +
                              glob.glob(os.path.join(polar_dir, "*[gG][yY][rR][oO]*.bin*")))

    polar_acc_files = sorted(list(set(polar_acc_files)))
    polar_gyro_files = sorted(list(set(polar_gyro_files)))

    if not polar_acc_files and not polar_gyro_files:
        print("⚠️ No Polar ACC or GYRO data files found in PolarSense/. Skipping.")
        return

    print(f"\n📡 Processing Polar Sense data ({len(polar_acc_files)} ACC, {len(polar_gyro_files)} GYRO files)...")

    def load_polar_csv_segments(file_list, sensor_type):
        """Load and concatenate Polar CSV/BIN segments.
        Handles both .csv/.csv.gz and .bin/.bin.gz files."""
        frames = []
        dtype = np.dtype([
            ('phone_ms', '<i8'),
            ('sensor_ns', '<i8'),
            ('x', '<f4'),
            ('y', '<f4'),
            ('z', '<f4')
        ])
        
        for fpath in file_list:
            try:
                if ".bin" in fpath:
                    # Parse binary Polar Sense format (28-byte records)
                    if fpath.endswith(".gz"):
                        with gzip.open(fpath, 'rb') as f:
                            data = f.read()
                    else:
                        with open(fpath, 'rb') as f:
                            data = f.read()
                    
                    arr = np.frombuffer(data, dtype=dtype)
                    df = pd.DataFrame({
                        'phone_timestamp': arr['phone_ms'] / 1000.0,
                        'sensor_ns': arr['sensor_ns'],
                        'x': arr['x'].astype(float),
                        'y': arr['y'].astype(float),
                        'z': arr['z'].astype(float)
                    })
                else:
                    # Fallback to semicolon CSV format
                    df = pd.read_csv(fpath, sep=';')
                    if len(df.columns) >= 5:
                        df.columns = ['phone_timestamp', 'sensor_ns', 'x', 'y', 'z'] + list(df.columns[5:])
                        local_offset = datetime.datetime.now().astimezone().utcoffset().total_seconds()
                        dt = pd.to_datetime(df['phone_timestamp'], errors='coerce')
                        valid_mask = dt.notna()
                        df = df[valid_mask].copy()
                        dt = dt[valid_mask]
                        df['phone_timestamp'] = dt.map(lambda x: x.timestamp()) - local_offset
                        
                        df['sensor_ns'] = pd.to_numeric(df['sensor_ns'], errors='coerce')
                        df['x'] = pd.to_numeric(df['x'], errors='coerce')
                        df['y'] = pd.to_numeric(df['y'], errors='coerce')
                        df['z'] = pd.to_numeric(df['z'], errors='coerce')

                # Normalize units to standard Android metrics (mps^2 and rad/s)
                if sensor_type == 'ACC':
                    # Convert milli-g to m/s^2: 1 mg = 0.00980665 m/s^2 (binary logs also write mg)
                    df['x'] *= 0.00980665
                    df['y'] *= 0.00980665
                    df['z'] *= 0.00980665
                elif sensor_type == 'GYRO':
                    # Convert degrees/sec to radians/sec: 1 dps = pi / 180 rad/s
                    dps_to_rad = np.pi / 180.0
                    df['x'] *= dps_to_rad
                    df['y'] *= dps_to_rad
                    df['z'] *= dps_to_rad

                df = df.dropna(subset=['phone_timestamp', 'sensor_ns', 'x', 'y', 'z'])
                frames.append(df)
            except Exception as e:
                print(f"  ⚠️ Failed to load {os.path.basename(fpath)}: {e}")
        if not frames:
            return None
        combined = pd.concat(frames, ignore_index=True)
        combined = combined.sort_values('sensor_ns').reset_index(drop=True)
        # Compute seconds elapsed from first sample
        t0 = combined['sensor_ns'].iloc[0]
        combined['seconds_elapsed'] = (combined['sensor_ns'] - t0) / 1e9
        combined['mag'] = np.sqrt(combined['x']**2 + combined['y']**2 + combined['z']**2)
        return combined

    df_polar_acc = load_polar_csv_segments(polar_acc_files, 'ACC')
    df_polar_gyro = load_polar_csv_segments(polar_gyro_files, 'GYRO')

    if df_polar_acc is None:
        print("⚠️ Could not load Polar accelerometer data. Skipping Polar features.")
        return

    print(f"  Polar ACC: {len(df_polar_acc)} samples, {df_polar_acc['seconds_elapsed'].iloc[-1]:.1f}s duration")
    if df_polar_gyro is not None:
        print(f"  Polar GYRO: {len(df_polar_gyro)} samples, {df_polar_gyro['seconds_elapsed'].iloc[-1]:.1f}s duration")

    # 2. Load watch accelerometer for tap detection
    df_watch_acc = load_watch_sensor(session_dir, "WatchAccelerometer")
    if df_watch_acc.empty:
        print("⚠️ WatchAccelerometer file not found. Skipping Polar alignment.")
        return

    watch_acc_times = df_watch_acc['seconds_elapsed'].to_numpy()
    watch_acc_mags = np.sqrt(df_watch_acc['x']**2 + df_watch_acc['y']**2 + df_watch_acc['z']**2)

    # 3. Detect 5-tap sequences in watch accelerometer (peaks >= 18 m/s²)
    def find_tap_sequences(times, mags, threshold, min_gap=0.2, max_gap=1.5, max_span=5.0):
        """Find non-overlapping 5-tap sequences from peak data."""
        candidate_indices = np.where(mags >= threshold)[0]
        local_peaks = []
        for idx in candidate_indices:
            t = times[idx]
            mag = mags[idx]
            w_start = np.searchsorted(times, t - 0.15)
            w_end = np.searchsorted(times, t + 0.15, side='right')
            if mag >= np.max(mags[w_start:w_end]):
                if not any(abs(t - p[0]) < min_gap for p in local_peaks):
                    local_peaks.append((t, mag))

        sequences = []
        i = 0
        while i < len(local_peaks) - 4:
            seq = local_peaks[i:i+5]
            seq_times = [p[0] for p in seq]
            if (seq_times[-1] - seq_times[0]) <= max_span:
                valid = True
                for j in range(1, 5):
                    gap = seq_times[j] - seq_times[j-1]
                    if gap < min_gap or gap > max_gap:
                        valid = False
                        break
                if valid:
                    if len(sequences) == 0 or (seq_times[0] - sequences[-1][0]) > 10.0:
                        sequences.append(seq_times)
                        i += 5
                        continue
            i += 1
        return sequences

    watch_tap_seqs = find_tap_sequences(watch_acc_times, watch_acc_mags, threshold=18.0)

    # 4. Detect 5-tap sequences in Polar accelerometer (peaks >= 2500 mg = 2.5 g)
    # Polar ACC is in mg, so 2500mg threshold
    polar_acc_times = df_polar_acc['seconds_elapsed'].to_numpy()
    polar_acc_mags = df_polar_acc['mag'].to_numpy()
    polar_tap_seqs = find_tap_sequences(polar_acc_times, polar_acc_mags, threshold=24.5)

    print(f"  Watch tap sequences detected: {len(watch_tap_seqs)}")
    print(f"  Polar tap sequences detected: {len(polar_tap_seqs)}")

    use_fallback = False
    matched_pairs = []

    if not watch_tap_seqs or not polar_tap_seqs:
        use_fallback = True
    else:
        # 5. Match sequences by inter-tap timing pattern
        def inter_tap_pattern(seq):
            return [seq[j+1] - seq[j] for j in range(len(seq)-1)]

        polar_t0_phone = df_polar_acc['phone_timestamp'].iloc[0]
        expected_offset = watch_start_epoch - offset - polar_t0_phone if (watch_start_epoch is not None and offset is not None) else 0.0

        used_polar = set()
        for w_seq in watch_tap_seqs:
            w_pattern = inter_tap_pattern(w_seq)
            best_match = None
            best_score = float('inf')
            for p_idx, p_seq in enumerate(polar_tap_seqs):
                if p_idx in used_polar:
                    continue
                # Enforce clock offset constraint (taps must be within 3.0s of expected offset)
                diff = p_seq[0] - w_seq[0]
                if abs(diff - expected_offset) > 3.0:
                    continue
                p_pattern = inter_tap_pattern(p_seq)
                # Score = sum of absolute differences in inter-tap intervals
                score = sum(abs(w - p) for w, p in zip(w_pattern, p_pattern))
                if score < best_score:
                    best_score = score
                    best_match = (p_idx, p_seq)
            # Accept match if cumulative pattern error < 1.0s total
            if best_match is not None and best_score < 1.0:
                matched_pairs.append((w_seq, best_match[1]))
                used_polar.add(best_match[0])
        
        if not matched_pairs:
            use_fallback = True

    if use_fallback:
        if offset is not None and watch_start_epoch is not None:
            polar_t0_phone = df_polar_acc['phone_timestamp'].iloc[0]
            polar_drift_rate = 0.0
            polar_offset = watch_start_epoch - offset - polar_t0_phone
            slope = 1.0
            intercept = polar_offset
            print(f"  ⚠️ No tap sequence matches found. Falling back to phone-timestamp alignment: offset {polar_offset:+.3f}s")
        else:
            print("⚠️ No tap sequences found for Polar-Watch alignment and no clock offset available. Skipping.")
            return
    else:
        print(f"  Matched {len(matched_pairs)} tap sequence pair(s).")
        for idx, (w_seq, p_seq) in enumerate(matched_pairs):
            print(f"    Pair {idx+1}: Watch [{', '.join(f'{t:.2f}s' for t in w_seq)}] ↔ Polar [{', '.join(f'{t:.2f}s' for t in p_seq)}]")

        # 6. Compute linear alignment (watch_time → polar_time)
        if len(matched_pairs) >= 2:
            x_pts = [w_seq[0] for w_seq, _ in matched_pairs]
            y_pts = [p_seq[0] for _, p_seq in matched_pairs]
            x_arr = np.array(x_pts)
            y_arr = np.array(y_pts)
            slope, intercept = np.polyfit(x_arr, y_arr, 1)
            polar_drift_rate = slope - 1.0
            polar_offset = intercept
            print(f"  🎯 Multi-Point Polar Alignment: offset={polar_offset:+.3f}s, drift={polar_drift_rate:+.7f}")
        else:
            polar_offset = matched_pairs[0][1][0] - matched_pairs[0][0][0]
            polar_drift_rate = 0.0
            slope = 1.0
            intercept = polar_offset
            print(f"  🎯 Single-Point Polar Alignment: offset={polar_offset:+.3f}s (drift forced to 0.0)")

    def watch_to_polar_time(watch_t):
        return watch_t * slope + intercept

    # 7. For each shot, extract Polar window features and append to ground_truth_aligned.csv
    df_aligned = pd.read_csv(aligned_csv_path)

    s1_start_ns_list = []
    s1_end_ns_list = []
    s1_start_sec_list = []
    s1_end_sec_list = []
    s2_start_ns_list = []
    s2_end_ns_list = []
    s2_start_sec_list = []
    s2_end_sec_list = []
    s3_start_ns_list = []
    s3_end_ns_list = []
    s3_start_sec_list = []
    s3_end_sec_list = []
    efficiency_list = []
    reaction_time_ms_list = []

    bottom_hand_gyro_peak = []
    bottom_hand_acc_peak = []
    bottom_hand_gyro_ratio = []
    bottom_hand_acc_ratio = []
    bottom_hand_time_lead_ms = []
    bottom_hand_sync_score = []
    s1_bottom_gyro_mag = []
    s1_bottom_deltaZ = []
    s2_bottom_acc_mean = []
    s2_dynamic_ratio_slope = []
    s3_bottom_pronation_deg = []
    s3_bottom_gyro_y_min = []

    polar_duration = df_polar_acc['seconds_elapsed'].iloc[-1]

    # Load Watch Gyro & Accel for full swing calculations
    df_watch_acc = load_watch_sensor(session_dir, "WatchAccelerometer")
    df_watch_gyro = load_watch_sensor(session_dir, "WatchGyroscope")
    watch_acc_times = df_watch_acc['seconds_elapsed'].to_numpy() if not df_watch_acc.empty else np.array([])
    watch_acc_mags = np.sqrt(df_watch_acc['x']**2 + df_watch_acc['y']**2 + df_watch_acc['z']**2).to_numpy() if not df_watch_acc.empty else np.array([])
    watch_gyro_times = df_watch_gyro['seconds_elapsed'].to_numpy() if not df_watch_gyro.empty else np.array([])
    watch_gyro_mags = np.sqrt(df_watch_gyro['x']**2 + df_watch_gyro['y']**2 + df_watch_gyro['z']**2).to_numpy() if not df_watch_gyro.empty else np.array([])

    for idx, row in df_aligned.iterrows():
        impact_t = float(row['impact_time_seconds'])
        impact_ns = int(row['impact_timestamp_ns']) if ('impact_timestamp_ns' in row and pd.notna(row['impact_timestamp_ns'])) else int(impact_t * 1e9)

        # Compute phase start/end nanoseconds and seconds
        s1_start_sec = round(impact_t - 0.80, 6)
        s1_end_sec = round(impact_t - 0.20, 6)
        s1_start_ns = impact_ns - 800_000_000
        s1_end_ns = impact_ns - 200_000_000

        s2_start_sec = round(impact_t - 0.20, 6)
        s2_end_sec = round(impact_t - 0.05, 6)
        s2_start_ns = impact_ns - 200_000_000
        s2_end_ns = impact_ns - 50_000_000

        s3_start_sec = round(impact_t - 0.05, 6)
        s3_end_sec = round(impact_t + 0.30, 6)
        s3_start_ns = impact_ns - 50_000_000
        s3_end_ns = impact_ns + 300_000_000

        s1_start_ns_list.append(s1_start_ns)
        s1_end_ns_list.append(s1_end_ns)
        s1_start_sec_list.append(s1_start_sec)
        s1_end_sec_list.append(s1_end_sec)
        s2_start_ns_list.append(s2_start_ns)
        s2_end_ns_list.append(s2_end_ns)
        s2_start_sec_list.append(s2_start_sec)
        s2_end_sec_list.append(s2_end_sec)
        s3_start_ns_list.append(s3_start_ns)
        s3_end_ns_list.append(s3_end_ns)
        s3_start_sec_list.append(s3_start_sec)
        s3_end_sec_list.append(s3_end_sec)

        # Dynamic Physical Efficiency: ratio of gyro at accel impact spike time to max downswing gyro
        acc_mask = (watch_acc_times >= impact_t - 0.15) & (watch_acc_times <= impact_t + 0.10) if len(watch_acc_times) > 0 else np.array([])
        if np.any(acc_mask):
            impact_acc_t = float(watch_acc_times[acc_mask][np.argmax(watch_acc_mags[acc_mask])])
        else:
            impact_acc_t = impact_t

        gyro_mask = (watch_gyro_times >= impact_t - 0.30) & (watch_gyro_times <= impact_t + 0.10) if len(watch_gyro_times) > 0 else np.array([])
        if np.any(gyro_mask):
            gyro_sub_times = watch_gyro_times[gyro_mask]
            gyro_sub_mags = watch_gyro_mags[gyro_mask]
            max_downswing_gyro = float(np.max(gyro_sub_mags))
            gyro_at_impact_idx = np.argmin(np.abs(gyro_sub_times - impact_acc_t))
            impact_gyro = float(gyro_sub_mags[gyro_at_impact_idx])
            eff = round(min(100.0, (impact_gyro / max_downswing_gyro) * 100.0), 1) if max_downswing_gyro > 0.1 else 90.0
        else:
            eff = 90.0
        efficiency_list.append(eff)

        # Reaction time: backswing onset (gyro >= 1.0 rad/s) to impact peak
        onset_mask = (watch_gyro_times >= impact_t - 0.80) & (watch_gyro_times <= impact_t) & (watch_gyro_mags >= 1.0) if len(watch_gyro_times) > 0 else np.array([])
        if np.any(onset_mask):
            onset_t = float(watch_gyro_times[onset_mask][0])
            react_ms = int(round((impact_t - onset_t) * 1000.0))
            react_ms = max(150, min(800, react_ms))
        else:
            react_ms = 350
        reaction_time_ms_list.append(react_ms)

        polar_t = watch_to_polar_time(impact_t)

        # Check if the mapped Polar time falls within the Polar data range
        if polar_t < -1.0 or polar_t > polar_duration + 1.0:
            bottom_hand_gyro_peak.append(np.nan)
            bottom_hand_acc_peak.append(np.nan)
            bottom_hand_gyro_ratio.append(np.nan)
            bottom_hand_acc_ratio.append(np.nan)
            bottom_hand_time_lead_ms.append(np.nan)
            bottom_hand_sync_score.append(np.nan)
            s1_bottom_gyro_mag.append(np.nan)
            s1_bottom_deltaZ.append(np.nan)
            s2_bottom_acc_mean.append(np.nan)
            s2_dynamic_ratio_slope.append(np.nan)
            s3_bottom_pronation_deg.append(np.nan)
            s3_bottom_gyro_y_min.append(np.nan)
            continue

        # Extract constrained downswing Polar window [-0.20s, +0.10s] around impact
        p_start = polar_t - 0.20
        p_end = polar_t + 0.10

        # Polar ACC window
        acc_win = df_polar_acc[(df_polar_acc['seconds_elapsed'] >= p_start) & (df_polar_acc['seconds_elapsed'] <= p_end)]
        if len(acc_win) > 0:
            p_acc_peak = float(acc_win['mag'].max())
            p_acc_peak_t = float(acc_win.loc[acc_win['mag'].idxmax(), 'seconds_elapsed'])
        else:
            p_acc_peak = np.nan
            p_acc_peak_t = np.nan

        # Polar GYRO window
        if df_polar_gyro is not None:
            gyro_win = df_polar_gyro[(df_polar_gyro['seconds_elapsed'] >= p_start) & (df_polar_gyro['seconds_elapsed'] <= p_end)]
            if len(gyro_win) > 0:
                p_gyro_peak = float(gyro_win['mag'].max())
                p_gyro_peak_t = float(gyro_win.loc[gyro_win['mag'].idxmax(), 'seconds_elapsed'])
            else:
                p_gyro_peak = np.nan
                p_gyro_peak_t = np.nan
        else:
            p_gyro_peak = np.nan
            p_gyro_peak_t = np.nan

        bottom_hand_gyro_peak.append(round(p_gyro_peak, 2) if not np.isnan(p_gyro_peak) else np.nan)
        bottom_hand_acc_peak.append(round(p_acc_peak, 2) if not np.isnan(p_acc_peak) else np.nan)

        # Ratios: Polar peak / watch peak at impact
        watch_gyro_mag = row.get('impact_gyro_mag', np.nan)
        if not np.isnan(p_gyro_peak) and not np.isnan(watch_gyro_mag) and watch_gyro_mag > 0:
            bottom_hand_gyro_ratio.append(round(p_gyro_peak / watch_gyro_mag, 3))
        else:
            bottom_hand_gyro_ratio.append(np.nan)

        # For acc ratio, watch accel peak in downswing window [-0.20s, +0.10s]
        watch_acc_win_mask = (watch_acc_times >= impact_t - 0.20) & (watch_acc_times <= impact_t + 0.10) if len(watch_acc_times) > 0 else np.array([])
        if np.any(watch_acc_win_mask):
            watch_acc_peak = float(np.max(watch_acc_mags[watch_acc_win_mask]))
        else:
            watch_acc_peak = np.nan

        if not np.isnan(p_acc_peak) and not np.isnan(watch_acc_peak) and watch_acc_peak > 0:
            bottom_hand_acc_ratio.append(round(p_acc_peak / watch_acc_peak, 3))
        else:
            bottom_hand_acc_ratio.append(np.nan)

        # Time lead: how many ms the Polar acc peak leads the watch impact (positive = Polar before watch)
        if not np.isnan(p_acc_peak_t):
            time_lead = (polar_t - p_acc_peak_t) * 1000.0
            bottom_hand_time_lead_ms.append(round(time_lead, 1))
        else:
            bottom_hand_time_lead_ms.append(np.nan)

        # Sync score: 1.0 - abs(time_lead)/500, clamped to [0, 1]
        if not np.isnan(p_acc_peak_t):
            sync = max(0.0, 1.0 - abs(polar_t - p_acc_peak_t) / 0.5)
            bottom_hand_sync_score.append(round(sync, 3))
        else:
            bottom_hand_sync_score.append(np.nan)

        # --- Segmented Polar Features ---
        # Segment 1: Backswing [-0.80s, -0.20s]
        s1_acc = df_polar_acc[(df_polar_acc['seconds_elapsed'] >= polar_t - 0.80) & (df_polar_acc['seconds_elapsed'] <= polar_t - 0.20)]
        s1_gyro = df_polar_gyro[(df_polar_gyro['seconds_elapsed'] >= polar_t - 0.80) & (df_polar_gyro['seconds_elapsed'] <= polar_t - 0.20)] if df_polar_gyro is not None else pd.DataFrame()
        if len(s1_gyro) > 0:
            s1_bottom_gyro_mag.append(round(float(s1_gyro['mag'].max()), 2))
            s1_bottom_deltaZ.append(round(float(s1_gyro['z'].max() - s1_gyro['z'].min()), 2))
        else:
            s1_bottom_gyro_mag.append(np.nan)
            s1_bottom_deltaZ.append(np.nan)

        # Segment 2: Downswing [-0.20s, -0.05s]
        s2_acc = df_polar_acc[(df_polar_acc['seconds_elapsed'] >= polar_t - 0.20) & (df_polar_acc['seconds_elapsed'] <= polar_t - 0.05)]
        s2_gyro = df_polar_gyro[(df_polar_gyro['seconds_elapsed'] >= polar_t - 0.20) & (df_polar_gyro['seconds_elapsed'] <= polar_t - 0.05)] if df_polar_gyro is not None else pd.DataFrame()
        if len(s2_acc) > 0:
            s2_bottom_acc_mean.append(round(float(s2_acc['mag'].mean()), 2))
        else:
            s2_bottom_acc_mean.append(np.nan)

        if len(s2_gyro) >= 2 and not np.isnan(watch_gyro_mag) and watch_gyro_mag > 0:
            g_start = s2_gyro['mag'].iloc[0]
            g_end = s2_gyro['mag'].iloc[-1]
            s2_slope = (g_end - g_start) / (s2_gyro['seconds_elapsed'].iloc[-1] - s2_gyro['seconds_elapsed'].iloc[0] + 1e-5)
            s2_dynamic_ratio_slope.append(round(float(s2_slope / watch_gyro_mag), 3))
        else:
            s2_dynamic_ratio_slope.append(np.nan)

        # Segment 3: Follow-through [-0.05s, +0.30s]
        s3_gyro = df_polar_gyro[(df_polar_gyro['seconds_elapsed'] >= polar_t - 0.05) & (df_polar_gyro['seconds_elapsed'] <= polar_t + 0.30)] if df_polar_gyro is not None else pd.DataFrame()
        if len(s3_gyro) > 0:
            trapz_func = getattr(np, 'trapezoid', getattr(np, 'trapz', None))
            pronation = trapz_func(s3_gyro['y'].values, s3_gyro['seconds_elapsed'].values) * (180.0 / np.pi) if (len(s3_gyro) >= 2 and trapz_func is not None) else 0.0
            s3_bottom_pronation_deg.append(round(float(pronation), 2))
            s3_bottom_gyro_y_min.append(round(float(s3_gyro['y'].min()), 2))
        else:
            s3_bottom_pronation_deg.append(np.nan)
            s3_bottom_gyro_y_min.append(np.nan)

    # Export phase timings & physical metrics
    df_aligned['s1_start_ns'] = s1_start_ns_list
    df_aligned['s1_end_ns'] = s1_end_ns_list
    df_aligned['s1_start_sec'] = s1_start_sec_list
    df_aligned['s1_end_sec'] = s1_end_sec_list

    df_aligned['s2_start_ns'] = s2_start_ns_list
    df_aligned['s2_end_ns'] = s2_end_ns_list
    df_aligned['s2_start_sec'] = s2_start_sec_list
    df_aligned['s2_end_sec'] = s2_end_sec_list

    df_aligned['s3_start_ns'] = s3_start_ns_list
    df_aligned['s3_end_ns'] = s3_end_ns_list
    df_aligned['s3_start_sec'] = s3_start_sec_list
    df_aligned['s3_end_sec'] = s3_end_sec_list

    df_aligned['efficiency'] = efficiency_list
    df_aligned['reaction_time_ms'] = reaction_time_ms_list

    # Export Polar features
    df_aligned['bottom_hand_gyro_peak'] = bottom_hand_gyro_peak
    df_aligned['bottom_hand_acc_peak'] = bottom_hand_acc_peak
    df_aligned['bottom_hand_gyro_ratio'] = bottom_hand_gyro_ratio
    df_aligned['bottom_hand_acc_ratio'] = bottom_hand_acc_ratio
    df_aligned['bottom_hand_time_lead_ms'] = bottom_hand_time_lead_ms
    df_aligned['bottom_hand_sync_score'] = bottom_hand_sync_score
    df_aligned['s1_bottom_gyro_mag'] = s1_bottom_gyro_mag
    df_aligned['s1_bottom_deltaZ'] = s1_bottom_deltaZ
    df_aligned['s2_bottom_acc_mean'] = s2_bottom_acc_mean
    df_aligned['s2_dynamic_ratio_slope'] = s2_dynamic_ratio_slope
    df_aligned['s3_bottom_pronation_deg'] = s3_bottom_pronation_deg
    df_aligned['s3_bottom_gyro_y_min'] = s3_bottom_gyro_y_min

    df_aligned.to_csv(aligned_csv_path, index=False)

    valid_count = df_aligned['bottom_hand_acc_peak'].notna().sum()
    total_count = len(df_aligned)
    print(f"\n✅ Polar Sense features & Phase Timings appended to ground_truth_aligned.csv ({valid_count}/{total_count} shots with Polar data)")

def normalize_shot_class(shot_name):

    if not shot_name:
        return "Unknown"
    s = shot_name.lower().strip()
    
    # Map to biomechanical classes. SWEEP is horizontal-bat; GLANCE/FLICK are vertical-bat.
    # Must be checked before the combined rule to keep them distinct.
    if "sweep" in s:
        return "SWEEP"
    if "flick" in s or "glance" in s:
        return "GLANCE/FLICK"
    if "cut" in s or "punch" in s:
        return "CUT/PUNCH"
    if "guide" in s or "glide" in s or "deflection" in s or "deflect" in s:
        return "DEFLECTION/GUIDE"
    if "power drive" in s:
        return "POWER DRIVE"
    if "slog" in s or "power shot" in s or "power hit" in s or "loft" in s:
        return "SLOG"
    if "drive" in s or "defence" in s or "defense" in s or "push" in s or "straight" in s or "forward" in s or "block" in s:
        return "DRIVE/DEFENCE"
    if "miss" in s:
        return "Miss"
        
    return "Unknown"

def compare_with_timeline(timeline_path, df_aligned, start_time_ms):
    timeline_shots = []
    timeline_start = None
    
    # Try to find SYSTEM_START timestamp in the timeline file
    with open(timeline_path, "r") as f:
        for line in f:
            if "SYSTEM_START:" in line:
                m = re.search(r"Ts=(\d+)", line)
                if m:
                    timeline_start = int(m.group(1))
                    break
                    
    # Fallback to start_time_ms if SYSTEM_START is missing
    if timeline_start is None:
        timeline_start = start_time_ms
        print(f"⚠️ SYSTEM_START not found in timeline. Using sensor start time: {start_time_ms}")
    else:
        print(f"🎯 Found SYSTEM_START in timeline: {timeline_start} ms")
        
    with open(timeline_path, "r") as f:
        for line in f:
            if line.startswith("Shot:"):
                m_type = re.search(r"Type=([^,]+)", line)
                m_spd = re.search(r"Spd=([0-9.]+)", line)
                m_ts = re.search(r"Ts=(\d+)", line)
                if m_ts:
                    ts = int(m_ts.group(1))
                    rel_t = (ts - timeline_start) / 1000.0
                    timeline_shots.append({
                        'ts_ms': ts,
                        'rel_time_seconds': rel_t,
                        'shot_type': m_type.group(1) if m_type else "Unknown",
                        'speed': float(m_spd.group(1)) if m_spd else 0.0
                    })
                    
    df_timeline = pd.DataFrame(timeline_shots)
    if len(df_timeline) == 0:
        print("⚠️ No shots detected by watch in timeline.")
        return
        
    matches = []
    for idx, row in df_aligned.iterrows():
        if row['shot_type'] == "Facing up":
            continue
            
        t_impact = row['impact_time_seconds']
        df_timeline['diff'] = np.abs(df_timeline['rel_time_seconds'] - t_impact)
        closest = df_timeline.loc[df_timeline['diff'].idxmin()]
        
        gt_norm = normalize_shot_class(row['shot_type'])
        if closest['diff'] <= 3.0:
            watch_norm = normalize_shot_class(closest['shot_type'])
            matches.append({
                'GT_Num': row.get('shot_number', row['shot_index']),
                'GT_Shot': row['shot_type'],
                'GT_Class': gt_norm,
                'GT_Time': f"{t_impact:.2f}s",
                'Watch_Shot': closest['shot_type'],
                'Watch_Class': watch_norm,
                'Watch_Time': f"{closest['rel_time_seconds']:.2f}s",
                'Diff': f"{closest['diff']:.2f}s",
                'Status': "✅ MATCH" if gt_norm == watch_norm else "❌ MISMATCH"
            })
        else:
            matches.append({
                'GT_Num': row.get('shot_number', row['shot_index']),
                'GT_Shot': row['shot_type'],
                'GT_Class': gt_norm,
                'GT_Time': f"{t_impact:.2f}s",
                'Watch_Shot': "None",
                'Watch_Class': "None",
                'Watch_Time': "-",
                'Diff': "-",
                'Status': "❓ UNDETECTED"
            })
            
    df_matches = pd.DataFrame(matches)
    print("\n=================== Session Accuracy Report ===================")
    print(df_matches.to_string(index=False))
    
    total = len(df_matches)
    matches_count = len(df_matches[df_matches['Status'] == "✅ MATCH"])
    mismatch_count = len(df_matches[df_matches['Status'] == "❌ MISMATCH"])
    undetected_count = len(df_matches[df_matches['Status'] == "❓ UNDETECTED"])
    
    print("\n------------------------- Summary -------------------------")
    print(f"Total Ground Truth (Narrated) Shots: {total}")
    print(f"Correctly Classified by Watch:       {matches_count} ({matches_count/total*100:.1f}%)")
    print(f"Misclassified by Watch:             {mismatch_count} ({mismatch_count/total*100:.1f}%)")
    print(f"Undetected by Watch:                 {undetected_count} ({undetected_count/total*100:.1f}%)")
    print("===============================================================")
    
    # Append raw watch sensor logs to the combined Parquet database
    combined_parquet_dir = os.path.join(args.dest, "..", "combined_sensor_data.parquet")
    append_to_combined_parquet(session_dir, os.path.abspath(combined_parquet_dir))
    
    # Losslessly compress all raw Watch*.csv files to Watch*.csv.gz and delete original CSVs
    compress_session_csvs(session_dir)

if __name__ == "__main__":
    main()
