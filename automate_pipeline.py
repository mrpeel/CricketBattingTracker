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
    print("\n🤐 Compressing raw session CSV files to Gzip...")
    compressed_count = 0
    for filename in os.listdir(session_dir):
        if filename.startswith("Watch") and filename.endswith(".csv"):
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
    print(f"✅ Losslessly compressed {compressed_count} watch sensor logs.")

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
        csv_path = os.path.join(session_dir, fname)
        gz_path = csv_path + ".gz"
        path_to_load = gz_path if os.path.exists(gz_path) else (csv_path if os.path.exists(csv_path) else None)
        if not path_to_load:
            continue
            
        try:
            df = pd.read_csv(path_to_load)
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
            print(f"  ❌ Error appending {name}: {e}")
            
    print(f"✅ Appended {appended_count} sensor datasets to Parquet database.")

def check_adb_devices(watch_ip):
    print("Checking connected ADB devices...")
    subprocess.run(["adb", "connect", watch_ip], capture_output=True)
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

def find_phone_device(devices, watch_ip):
    # Any connected device that is not the watch is treated as the phone
    for d in devices:
        if d != watch_ip:
            return d
    return None

def pull_latest_watch_session(watch_ip, dest_dir):
    print("Pulling latest session from Wear OS watch...")
    cmd = ["adb", "-s", watch_ip, "shell", "ls", "/storage/emulated/0/Android/data/com.mrpeel.cricketbattingtracker/files/sessions"]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0 or not res.stdout.strip():
        print("❌ ERROR: No session directories found on the watch.")
        return None
        
    sessions = [s.strip() for s in res.stdout.split("\n") if s.strip() and s.startswith("session-")]
    if not sessions:
        print("❌ ERROR: No session folders starting with 'session-' found.")
        return None
        
    latest_session = sorted(sessions)[-1]
    local_session_dir = os.path.join(dest_dir, latest_session)
    os.makedirs(local_session_dir, exist_ok=True)
    
    print(f"📥 Pulling files for {latest_session} to {local_session_dir}...")
    watch_path = f"/storage/emulated/0/Android/data/com.mrpeel.cricketbattingtracker/files/sessions/{latest_session}"
    subprocess.run(["adb", "-s", watch_ip, "pull", watch_path, dest_dir], check=True)
    
    # Pull latest timeline
    timeline_local = os.path.join(local_session_dir, "latest_timeline.txt")
    print("📥 Pulling latest_timeline.txt...")
    subprocess.run(["adb", "-s", watch_ip, "pull", "/sdcard/Android/data/com.mrpeel.cricketbattingtracker/files/latest_timeline.txt", timeline_local], check=False)
    
    # Clean watch directory
    print("🧹 Cleaning raw session directory on watch to free space...")
    subprocess.run(["adb", "-s", watch_ip, "shell", f"rm -rf /storage/emulated/0/Android/data/com.mrpeel.cricketbattingtracker/files/sessions/{latest_session}"], check=True)
    
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
        cmd = ["adb", "-s", phone_id, "shell", f"find {path} -name '*.m4a' -o -name '*.mp3' 2>/dev/null"]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode == 0 and res.stdout.strip():
            for line in res.stdout.split("\n"):
                if line.strip():
                    audio_files.append(line.strip())
                    
    if not audio_files:
        print("⚠️ No audio files found automatically on the phone.")
        return None
        
    print(f"Found {len(audio_files)} recordings on phone. Locating the most recent...")
    newest_file = None
    newest_time = 0
    for f in audio_files:
        cmd = ["adb", "-s", phone_id, "shell", f"stat -c '%Y' '{f}' 2>/dev/null"]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode == 0 and res.stdout.strip():
            try:
                mtime = int(res.stdout.strip())
                if mtime > newest_time:
                    newest_time = mtime
                    newest_file = f
            except:
                pass
                
    if not newest_file:
        return None
        
    local_name = os.path.basename(newest_file)
    local_path = os.path.join(dest_dir, local_name)
    print(f"📥 Pulling phone audio file: {newest_file} → {local_path}")
    subprocess.run(["adb", "-s", phone_id, "pull", newest_file, local_path], check=True)
    return local_path


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

    whisper_segments = None

    print(f"📤 Uploading {os.path.basename(audio_path)} to Gemini...")
    uploaded_file = client.files.upload(file=audio_path)
    print(f"File uploaded successfully. Storage URI: {uploaded_file.name}")

    print("Waiting for Gemini to process the audio file...")
    while uploaded_file.state.name == "PROCESSING":
        time.sleep(2)
        uploaded_file = client.files.get(name=uploaded_file.name)

    if uploaded_file.state.name == "FAILED":
        raise Exception("Gemini audio processing failed.")

    from pydantic import BaseModel
    from typing import List, Optional

    class NarrationItem(BaseModel):
        timestamp_seconds: float
        shot_number: Optional[int] = None
        shot_type: str
        rating: Optional[str] = None
        bat: Optional[str] = None
        narrated_text: str

    class NarrationList(BaseModel):
        narrations: List[NarrationItem]

    print("🎙️ Preparing prompt with biomechanics constraints...")
    prompt_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "docs", "gemini_narration_prompt.md")
    if os.path.exists(prompt_path):
        with open(prompt_path, "r") as f:
            prompt_base = f.read().strip()
        print(f"📖 Loaded narration transcription prompt from {prompt_path}")
    else:
        prompt_base = (
            "You are an expert audio transcription assistant.\n"
            "Analyze the provided audio recording of a cricket batting practice.\n"
            "The batsman narrates his shots after playing them, speaking clearly in one of these formats:\n"
            "1. \"Shot [number] [Shot Type] [Rating]\" (for example: \"Shot 1 Cover drive Excellent\" or \"Shot 12 Pull shot Good\").\n"
            "2. \"[Number] [Shot Type] [Rating]\" (for example: \"One, push shot, good\" or \"Twelve, pull shot, excellent\").\n"
            "3. For a normal shot, the expected flow of audio is: \"facing up\" -> gap to play shot -> {shot type} {shot rating}.\n"
            "4. For balls where no shot is played, the expected flow of audio is: \"facing up\" -> \"no shot\", \"leave\", or \"evade\".\n\n"
            "The audio contains long periods of silence, ball impact noises, and background sounds. Ignore all silence and background noise.\n\n"
            "Search the entire audio file for all spoken narrations matching the pattern.\n"
            "The batsman may refer to the following expected shot types (grouped by biomechanical class):\n"
            "- Drive/Defence: \"Straight Drive\", \"Cover Drive\", \"Off Drive\", \"On Drive\", \"Forward Defensive\", \"Back-foot Defensive\", \"Push Shot\" (or \"Push\")\n"
            "- Glance/Flicks: \"Flick Shot\", \"Leg Glance\", \"On-Glance\", \"Traditional Sweep Shot\" (or \"Sweep\")\n"
            "- Cut/Punch: \"Square Cut\", \"Cut\", \"Back-foot Punch\"\n"
            "- Pull/Hook: \"Pull Shot\", \"Hook Shot\"\n"
            "- Deflection/Guide: \"Late Cut\", \"Square Upper Cut\", \"Steer / Glide\", \"Guide\"\n"
            "- Slog: \"Lofted Straight Drive\", \"Lofted Cover Drive\", \"Slog Sweep\", \"Switch Hit\", \"Reverse Sweep\", \"Helicopter Shot\", \"Slog\", \"Power shot\"\n"
            "- Power Drive: \"Power drive\"\n"
            "- Balls with no shot played: \"No shot\", \"Leave\", \"Evade\", \"Evasion\"\n\n"
            "The batter uses three types of bats and narrates when he changes or selects them:\n"
            "- 'Gray Nicolls Giant' (or 'Giant', heavy bat)\n"
            "- 'Eye in bat' (or 'Eye In', thin light bat)\n"
            "- 'Game bat' (or 'Game day bat', normal bat)\n\n"
            "The batsman will rate the shot quality using one of these rating words:\n"
            "\"Excellent\", \"Good\", \"Poor\", \"Miss\", \"Okay\", \"Decent\", \"Edge\", \"Edged\"\n\n"
            "## Phonetic Corrections:\n"
            "- **CRITICAL**: The batter will never narrate \"touch shot\" or \"touch\". If you hear \"touch shot\" or \"touch\", this is a phonetic mishearing of \"cut shot\" or \"cut\". Always transcribe it as \"Cut\" or \"Square Cut\" depending on context.\n"
            "- **CRITICAL**: If you see or hear \"how are you\", \"how are you?\", \"how are you good\", or similar in the Whisper text, this is a phonetic mishearing of \"Power drive\". Always transcribe it as \"Power drive\" (e.g. \"Power drive Good\" or \"Power drive Okay\").\n"
            "- If you hear \"division\" or \"defensive\", ensure it maps to one of the defensive categories (e.g. \"Forward Defensive\" or \"Back-foot Defensive\").\n"
            "- If you hear \"EB giant\", this is a mishearing of \"Facing up\" or metadata phrase. Ensure it matches expected terms.\n\n"
            "Scan the audio carefully from start to finish to capture every single one of the shots played (up to approximately Shot 69 or 72). "
            "Do not skip shots, do not hallucinate repetitive entries in silence, and output only the matching list."
        )
    schema_instruction = (
        "\n\nOutput the result as a JSON object matching the response schema: a list of narration items. "
        "Each item must contain `timestamp_seconds` (float, e.g. 3.45 or 12.18), `shot_number` (int, or null for stance/admin/non-numbered events), "
        "`shot_type` (str, e.g. 'Facing up', 'Cover Drive', 'Cut', 'Leg Glance', etc.), `rating` (str, e.g. 'good', 'ok', or null), "
        "`bat` (str, e.g. 'Gray Nicolls Giant', 'Eye In', 'Game bat', or null), and `narrated_text` (str, the exact transcribed text of the utterance)."
    )

    prompt = prompt_base + schema_instruction

    # --- Single-model strict call with one retry on quota/availability errors ---
    RETRY_WAIT_SECONDS = 30
    response = None
    last_err = None
    for attempt in range(1, 3):  # attempt 1, then attempt 2 after a wait
        try:
            msg = f"🎙️ Requesting structured transcription from {model_name} (attempt {attempt}/2)"
            with ProgressSpinner(msg):
                response = client.models.generate_content(
                    model=model_name,
                    contents=[uploaded_file, prompt],
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=NarrationList,
                    ),
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
                # Non-quota error, or second attempt also failed — halt immediately
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
        
    text_transcript = response.text
    print("Parsing transcription text...")
    
    shot_events = []
    parsed_structured = False
    
    try:
        data = json.loads(text_transcript)
        items = data.get("narrations", [])
        if items:
            for item in items:
                shot_num_raw = item.get("shot_number")
                shot_events.append({
                    "shot_number": int(shot_num_raw) if shot_num_raw is not None else None,
                    "timestamp_seconds": float(item.get("timestamp_seconds", 0.0)),
                    "texts": [item.get("narrated_text", "")],
                    "bat": item.get("bat")
                })
            parsed_structured = True
            print(f"✅ Successfully parsed {len(shot_events)} shots via Pydantic response_schema.")
    except Exception as e:
        print(f"⚠️ Failed to parse structured JSON ({e}). Attempting robust regex recovery...")
        try:
            blocks = re.findall(r'\{[^{}]+\}', text_transcript)
            items = []
            for b in blocks:
                if "timestamp_seconds" in b and "shot_type" in b:
                    t_match = re.search(r'"timestamp_seconds"\s*:\s*([\d\.]+)', b)
                    n_match = re.search(r'"shot_number"\s*:\s*(\d+)', b)
                    st_match = re.search(r'"shot_type"\s*:\s*"([^"]*)"', b)
                    bat_match = re.search(r'"bat"\s*:\s*"([^"]*)"', b)
                    txt_match = re.search(r'"narrated_text"\s*:\s*"([^"]*)"', b)
                    
                    if t_match and st_match:
                        items.append({
                            "timestamp_seconds": float(t_match.group(1)),
                            "shot_number": int(n_match.group(1)) if n_match else None,
                            "shot_type": st_match.group(1),
                            "bat": bat_match.group(1) if bat_match else None,
                            "narrated_text": txt_match.group(1) if txt_match else ""
                        })
            if items:
                for item in items:
                    shot_num_raw = item.get("shot_number")
                    shot_events.append({
                        "shot_number": int(shot_num_raw) if shot_num_raw is not None else None,
                        "timestamp_seconds": float(item.get("timestamp_seconds", 0.0)),
                        "texts": [item.get("narrated_text", "")],
                        "bat": item.get("bat")
                    })
                parsed_structured = True
                print(f"✅ Successfully recovered {len(shot_events)} shots via robust regex object parser.")
        except Exception as recovery_err:
            print(f"❌ Robust recovery parser also failed: {recovery_err}")
            
    if not parsed_structured:
        # Fallback to legacy regex parsing
        def extract_time_and_text(line):
            m_time = re.search(r"\b(\d{1,2}):(\d{2})(?::(\d{2}))?(?:\.(\d+))?\b", line)
            if not m_time:
                return None, None
                
            minutes = int(m_time.group(1))
            seconds = int(m_time.group(2))
            centiseconds = int(m_time.group(3)) if m_time.group(3) else 0
            if m_time.group(4):
                decimals = float(f"0.{m_time.group(4)}")
                time_sec = minutes * 60 + seconds + decimals
            else:
                time_sec = minutes * 60 + seconds + centiseconds / 100.0
                
            end_idx = m_time.end()
            text = line[end_idx:].strip()
            text = re.sub(r"^[-\s:\]\.]+", "", text).strip()
            
            return time_sec, text
            
        lines = text_transcript.split('\n')
        current_shot = None
        
        for line in lines:
            time_sec, text = extract_time_and_text(line)
            if time_sec is None:
                continue
                
            # Check if this line starts a new Shot
            shot_match = re.search(r"\b[Ss]hot\s+(\d+)\b", text)
            if shot_match:
                shot_num = int(shot_match.group(1))
                if current_shot:
                    shot_events.append(current_shot)
                current_shot = {
                    "shot_number": shot_num,
                    "timestamp_seconds": time_sec,
                    "texts": [text],
                    "bat": None
                }
            else:
                if current_shot:
                    if time_sec - current_shot["timestamp_seconds"] <= 8.0:
                        current_shot["texts"].append(text)
                    else:
                        shot_events.append(current_shot)
                        current_shot = None
                        
        if current_shot:
            shot_events.append(current_shot)
        
    return format_gemini_shots(shot_events)

def format_gemini_shots(shot_events):
    formatted_shots = []
    current_bat = None
    for event in shot_events:
        full_text = " ".join(event["texts"])
        text_lower = full_text.lower()
        
        # Phonetic correction post-processing fallback
        if "touch shot" in text_lower:
            text_lower = text_lower.replace("touch shot", "cut shot")
        if "touch" in text_lower:
            text_lower = text_lower.replace("touch", "cut")
            
        # Map Whisper mishearings of "Power hit" (e.g. "Now I hit", "Now hit", "How I hit", "How we hit", "How're you")
        # and bowling machine hum hallucinations to "power drive"
        if any(w in text_lower for w in ["now i hit", "now hit", "how i hit", "how we hit", "how to hit", "how we got", "now we hit"]):
            text_lower = "power drive"
        elif "how" in text_lower and any(w in text_lower for w in ["you", "are", "okay", "good"]):
            text_lower = "power drive"
            
        # Determine bat for this event
        event_bat = event.get("bat")
        if event_bat:
            event_bat_lower = event_bat.lower()
            if "giant" in event_bat_lower or "nicolls" in event_bat_lower or "nichs" in event_bat_lower:
                current_bat = "Gray Nicolls Giant"
            elif "eye in" in event_bat_lower:
                current_bat = "Eye In"
            elif "game" in event_bat_lower:
                current_bat = "Game bat"
        else:
            # Fallback to checking text_lower
            if any(w in text_lower for w in ["giant", "nicolls", "nichs"]):
                current_bat = "Gray Nicolls Giant"
            elif "eye in" in text_lower:
                current_bat = "Eye In"
            elif any(w in text_lower for w in ["game bat", "game day bat", "normal game bat"]):
                current_bat = "Game bat"
                
        # Map shot type
        shot_type = None
        if "facing up" in text_lower:
            shot_type = "Facing up"
        elif "no shot" in text_lower:
            shot_type = "No shot"
        elif "leave" in text_lower:
            shot_type = "Leave"
        elif "evade" in text_lower or "evasion" in text_lower:
            shot_type = "Evade"
        elif "guide" in text_lower or "glide" in text_lower or "steer" in text_lower:
            shot_type = "Guide"
        elif "power drive" in text_lower:
            shot_type = "Power drive"
        elif "slog" in text_lower or "power shot" in text_lower or "power hit" in text_lower or "loft" in text_lower:
            shot_type = "Slog"
        elif "cover drive" in text_lower:
            shot_type = "Cover drive"
        elif "straight drive" in text_lower:
            shot_type = "Straight drive"
        elif "off drive" in text_lower:
            shot_type = "Off drive"
        elif "on drive" in text_lower:
            shot_type = "On drive"
        elif "pull" in text_lower or "full" in text_lower:
            shot_type = "Pull shot"
        elif "hook" in text_lower:
            shot_type = "Hook shot"
        elif "cut" in text_lower:
            shot_type = "Cut shot"
        elif "flick" in text_lower:
            shot_type = "Flick"
        elif "glance" in text_lower:
            shot_type = "Leg glance"
        elif "sweep" in text_lower:
            shot_type = "Sweep"
        elif "push" in text_lower:
            shot_type = "Push"
        elif "punch" in text_lower:
            shot_type = "Punch"
        elif "defense" in text_lower or "defence" in text_lower or "defensive" in text_lower or "block" in text_lower:
            shot_type = "Defence/Block"
        elif "half" in text_lower or "have" in text_lower:
            shot_type = "Off drive"
            
        if shot_type is None:
            if event["shot_number"] is not None:
                shot_type = "Defence/Block"
            else:
                continue
            
        # Map quality
        quality = "good"
        if "excellent" in text_lower or "perfect" in text_lower:
            quality = "excellent"
        elif "poor" in text_lower or "bad" in text_lower or "edge" in text_lower or "edged" in text_lower:
            quality = "poor"
        elif "miss" in text_lower or "no" in text_lower:
            quality = "miss"
        elif "okay" in text_lower or "decent" in text_lower or "so, so" in text_lower:
            quality = "okay"
            
        formatted_shots.append({
            "timestamp_seconds": event["timestamp_seconds"],
            "shot_number": event["shot_number"],
            "shot_type": shot_type,
            "quality": quality,
            "bat": current_bat,
            "narrated_text": full_text
        })
        
    return formatted_shots

def main():
    args = parse_args()
    
    # 1. Connect and pull watch session files
    if args.session_dir:
        session_dir = args.session_dir
        print(f"Using local session directory: {session_dir}")
    else:
        devices = check_adb_devices(args.watch_ip)
        if args.watch_ip not in devices:
            print(f"❌ ERROR: Watch {args.watch_ip} is not connected or authorized.")
            sys.exit(1)
            
        session_dir = pull_latest_watch_session(args.watch_ip, args.dest)
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
            if 'devices' in locals():
                phone_id = find_phone_device(devices, args.watch_ip)
                if phone_id:
                    audio_path = pull_audio_from_phone(phone_id, session_dir)
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
    gyro_path = resolve_sensor_path(session_dir, "WatchGyroscope.csv")
    accel_path = resolve_sensor_path(session_dir, "WatchAccelerometer.csv")
    gravity_path = resolve_sensor_path(session_dir, "WatchGravity.csv")
    orient_path = resolve_sensor_path(session_dir, "WatchOrientation.csv")
    
    if not os.path.exists(gyro_path):
        print(f"❌ ERROR: Gyroscope sensor file missing from session log: {gyro_path}")
        sys.exit(1)
        
    df_gyro = pd.read_csv(gyro_path)
    df_gyro['mag'] = np.sqrt(df_gyro['x']**2 + df_gyro['y']**2 + df_gyro['z']**2)
    start_time_ns = df_gyro.iloc[0]['time']
    start_time_ms = int(start_time_ns / 1_000_000)
    gyro_duration = df_gyro.iloc[-1]['seconds_elapsed']

    # 5. Call local Whisper or Gemini to transcribe & parse shot timings (or load local cache if exists)
    narrations_cache_path = os.path.join(session_dir, "narrations_raw.json")

    # --force-retranscribe: delete stale cache so transcription always re-runs
    if getattr(args, "force_retranscribe", False) and os.path.exists(narrations_cache_path):
        print(f"🗑️  --force-retranscribe set: deleting existing cache {narrations_cache_path}")
        os.remove(narrations_cache_path)

    if os.path.exists(narrations_cache_path):
        print(f"📖 Loading cached transcriptions from {narrations_cache_path}...")
        with open(narrations_cache_path, "r") as f:
            narrations = json.load(f)
    else:
        preferred_model = getattr(args, "model", "gemini-3.5-flash")
        try:
            narrations = transcribe_audio_gemini(audio_path, preferred_model=preferred_model)
            print(f"Successfully transcribed {len(narrations)} narrations via Gemini ({preferred_model}).")
        except RuntimeError as e:
            # RuntimeError from our guard includes full resume instructions
            print(e)
            sys.exit(1)
        except Exception as e:
            print(f"❌ Gemini transcription failed unexpectedly: {e}")
            sys.exit(1)

        # Write raw narrations to session dir
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

    if offset is not None:
        print(f"🎯 Using manual clock offset override: {offset:+.3f}s")
    else:
        if narrations:
            search_center = baseline_offset if baseline_offset is not None else 0.0
            search_range = 2.5
            print(f"🔍 Starting clock offset and drift optimization grid search against raw gyroscope peaks")
            print(f"   (center={search_center:+.3f}s, range=\u00b1{search_range}s)")
            print(f"   ⚠️  Scoring is based ONLY on raw sensor peak matches — no watch detections used.")

            # Precalculate all raw gyroscope peaks in the session to avoid slow pandas queries in the loop.
            # A peak is defined as a local maximum with mag >= 3.0 in a 1.0s window.
            print("📈 Precalculating gyroscope sensor peaks...")
            times = df_gyro['seconds_elapsed'].to_numpy()
            mags = df_gyro['mag'].to_numpy()
            
            precalculated_peaks = []
            candidate_indices = np.where(mags >= 3.0)[0]
            for idx in candidate_indices:
                t = times[idx]
                mag = mags[idx]
                w_start = np.searchsorted(times, t - 0.5)
                w_end = np.searchsorted(times, t + 0.5, side='right')
                if mag >= np.max(mags[w_start:w_end]):
                    # Avoid duplicate/near peaks
                    if not any(abs(t - p['time']) < 1.0 for p in precalculated_peaks):
                        precalculated_peaks.append({
                            'time': t,
                            'mag': mag,
                            'is_fallback': False
                        })
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
                    rating_lower = shot['rating'].lower() if shot.get('rating') else ""
                    is_non_swing = (
                        any(term in shot_type_lower for term in ["no shot", "leave", "facing up", "evade", "defense", "defence", "block", "miss"]) or
                        any(term in rating_lower for term in ["poor", "edge", "edged", "miss"])
                    )

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
                        prev_rating_lower = narrations[i-1]['rating'].lower() if narrations[i-1].get('rating') else ""
                        prev_is_non_swing = (
                            any(term in prev_type_lower for term in ["no shot", "leave", "facing up", "evade", "defense", "defence", "block", "miss"]) or
                            any(term in prev_rating_lower for term in ["poor", "edge", "edged", "miss"])
                        )
                        curr_type_lower = narrations[i]['shot_type'].lower()
                        curr_rating_lower = narrations[i]['rating'].lower() if narrations[i].get('rating') else ""
                        curr_is_non_swing = (
                            any(term in curr_type_lower for term in ["no shot", "leave", "facing up", "evade", "defense", "defence", "block", "miss"]) or
                            any(term in curr_rating_lower for term in ["poor", "edge", "edged", "miss"])
                        )
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
                    rating_lower = shot['rating'].lower() if shot.get('rating') else ""
                    is_non_swing = (
                        any(term in shot_type_lower for term in ["no shot", "leave", "facing up", "evade", "defense", "defence", "block", "miss"]) or
                        any(term in rating_lower for term in ["poor", "edge", "edged", "miss"])
                    )
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
        rating_lower = shot['rating'].lower() if shot.get('rating') else ""
        is_non_swing = (
            any(term in shot_type_lower for term in ["no shot", "leave", "facing up", "evade", "defense", "defence", "block", "miss"]) or
            any(term in rating_lower for term in ["poor", "edge", "edged", "miss"])
        )
        
        cands = []
        if is_non_swing:
            cands.append({
                'time': sensor_narr_t - 2.5,
                'mag': 1.0,
                'is_fallback': True
            })
        else:
            window = df_gyro[(df_gyro['seconds_elapsed'] >= sensor_narr_t - 6.0) & (df_gyro['seconds_elapsed'] <= sensor_narr_t + 7.0)]
            peaks = []
            if len(window) > 0:
                sorted_samples = window.sort_values(by='mag', ascending=False)
                for _, row in sorted_samples.iterrows():
                    pt = row['seconds_elapsed']
                    pmag = row['mag']
                    if pmag < 1.5:
                        continue
                    if not any(abs(pt - p['time']) < 1.0 for p in peaks):
                        peaks.append({
                            'time': pt,
                            'mag': pmag,
                            'is_fallback': False
                        })
                        if len(peaks) >= 5:
                            break
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
            prev_rating_lower = narrations[i-1]['rating'].lower() if narrations[i-1].get('rating') else ""
            prev_is_non_swing = (
                any(term in prev_type_lower for term in ["no shot", "leave", "facing up", "evade", "defense", "defence", "block", "miss"]) or
                any(term in prev_rating_lower for term in ["poor", "edge", "edged", "miss"])
            )
            curr_type_lower = narrations[i]['shot_type'].lower()
            curr_rating_lower = narrations[i]['rating'].lower() if narrations[i].get('rating') else ""
            curr_is_non_swing = (
                any(term in curr_type_lower for term in ["no shot", "leave", "facing up", "evade", "defense", "defence", "block", "miss"]) or
                any(term in curr_rating_lower for term in ["poor", "edge", "edged", "miss"])
            )
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
        if not (
            any(term in s['shot_type'].lower() for term in ["no shot", "leave", "facing up", "evade", "defense", "defence", "block", "miss"]) or
            any(term in (s['quality'] or '').lower() for term in ["poor", "edge", "edged", "miss"])
        )
        and s['sensor_narr_time_seconds'] >= -5.0 
        and s['sensor_narr_time_seconds'] <= gyro_duration + 5.0
    ]
    if len(active_swings) == 0:
        print("\n" + "="*80)
        print("❌ ALIGNMENT ERROR: Zero active swings found within watch logging duration!")
        print("   This indicates that the watch tracking and the audio recording do not overlap.")
        print("="*80 + "\n")
        raise RuntimeError("❌ Alignment failed: Zero active swings overlap with the watch logging duration.")
        
    fallback_swings = [s for s in active_swings if s['is_fallback']]
    fallback_rate = len(fallback_swings) / len(active_swings)
    
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
    df_accel = pd.read_csv(accel_path)
    df_gravity = pd.read_csv(gravity_path)
    
    # Load Game Rotation Vector or fallback orientation
    game_orient_path = resolve_sensor_path(session_dir, "WatchGameOrientation.csv")
    if os.path.exists(game_orient_path):
        df_orient = pd.read_csv(game_orient_path)
        print(f"📖 Loaded {os.path.basename(game_orient_path)} for bat orientation")
    else:
        df_orient = pd.read_csv(orient_path)
        print(f"📖 Loaded {os.path.basename(orient_path)} for bat orientation (fallback)")
        
    print("📈 Computing Blade and Launch angles at impact...")
    df_aligned = add_angle_stats_to_aligned_shots(df_aligned, df_orient)
    # Overwrite the CSV with new columns
    df_aligned.to_csv(aligned_csv_path, index=False)
    print(f"✅ Updated aligned file with angle stats: {aligned_csv_path}")
        
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
        
    # Check conditions
    gyro_ok = gyro_std < 1.6
    accel_ok = accel_std < 3.25
    ori_ok = ori_disp < 3.05
    steps_ok = steps_count == 0
    grav_ok = grav_y <= -6.0 or grav_y == 0.0
    
    passed = gyro_ok and accel_ok and ori_ok and steps_ok and grav_ok
    status_emoji = "🟢 SUCCESS" if passed else "🔴 FAILED"
    
    print("\n=================== Stance Check Alignment Analysis ===================")
    print(f"Stance Event: '{narrated_text}'")
    print(f"Time:         {audio_t:.1f}s (audio) ➔ Stance aligned at {t_stance:.2f}s sensor (rel)")
    print(f"  1. Gyro Std:    {gyro_std:.2f} rad/s  (Limit: < 1.6)  ➔ {'PASS' if gyro_ok else 'FAIL'}")
    print(f"  2. Accel Std:   {accel_std:.2f} m/s²   (Limit: < 3.25) ➔ {'PASS' if accel_ok else 'FAIL'}")
    print(f"  3. Ori Disp:    {ori_disp:.2f} deg    (Limit: < 3.05) ➔ {'PASS' if ori_ok else 'FAIL'}")
    print(f"  4. Steps:       {steps_count} steps     (Limit: 0)      ➔ {'PASS' if steps_ok else 'FAIL'}")
    print(f"  5. Gravity Y:   {grav_y:.2f} m/s²  (Limit: <= -6.0)➔ {'PASS' if grav_ok else 'FAIL'}")
    print(f"STATUS: {status_emoji} ({'All conditions met' if passed else 'Stance lock would fail'})")
    if not passed:
        fails = []
        if not gyro_ok: fails.append(f"Gyro Std ({gyro_std:.2f} >= 1.6)")
        if not accel_ok: fails.append(f"Accel Std ({accel_std:.2f} >= 3.25)")
        if not ori_ok: fails.append(f"Ori Disp ({ori_disp:.2f} >= 3.05)")
        if not steps_ok: fails.append(f"Steps count ({steps_count} > 0)")
        if not grav_ok: fails.append(f"Gravity Y ({grav_y:.2f} > -6.0)")
        print(f"  Failed condition(s): {', '.join(fails)}")
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
