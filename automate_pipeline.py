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
import aifc
import re
import numpy as np
import pandas as pd

def parse_args():
    parser = argparse.ArgumentParser(description="Pitch Analytix Pro Data Collection Pipeline")
    parser.add_argument("--watch-ip", default="192.168.1.27:37129", help="ADB watch IP and port")
    parser.add_argument("--audio", help="Manual path to the local audio narration file (.m4a/.mp3)")
    parser.add_argument("--dest", default="/Users/neilkloot/Code/Batting Sensor Stats/live_watch_sessions", help="Base directory to save pulled logs")
    parser.add_argument("--manual-offset", type=float, help="Override offset detection and specify manual offset in seconds")
    parser.add_argument("--session-dir", help="Path to local pulled session directory (skips ADB watch pull)")
    parser.add_argument("--local", default="true", help="Use local Whisper instead of Gemini ('true'/'false')")
    return parser.parse_args()

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
    watch_path = f"/storage/emulated/0/Android/data/com.mrpeel.cricketbattingtracker/files/sessions/{latest_session}/."
    subprocess.run(["adb", "-s", watch_ip, "pull", watch_path, local_session_dir], check=True)
    
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

def convert_to_aiff(m4a_path, aiff_path):
    print("Converting audio to AIFF using afconvert...")
    cmd = ["afconvert", "-f", "AIFF", "-d", "BEI16@44100", m4a_path, aiff_path]
    subprocess.run(cmd, check=True)

def load_audio_envelope(aiff_path, target_fps=100):
    with aifc.open(aiff_path, 'rb') as a:
        n_channels = a.getnchannels()
        framerate = a.getframerate()
        n_frames = a.getnframes()
        chunk_size = int(framerate / target_fps)
        
        envelope = []
        for _ in range(0, n_frames, chunk_size):
            frames = a.readframes(chunk_size)
            if not frames:
                break
            arr = np.frombuffer(frames, dtype='>i2')
            if len(arr) == 0:
                break
            if n_channels == 2:
                arr = arr.reshape(-1, 2)
                val = np.max(np.abs(arr))
            else:
                val = np.max(np.abs(arr))
            envelope.append(val)
    return np.array(envelope, dtype=np.float32), float(framerate) / chunk_size

def find_calibration_taps_audio(envelope, fps, duration_limit=2.0, num_taps=5):
    from scipy.signal import find_peaks
    # We look for 5 prominent peaks
    prominence = np.max(envelope) * 0.15
    peaks, _ = find_peaks(envelope, distance=int(0.12 * fps), prominence=prominence)
    
    for i in range(len(peaks) - num_taps + 1):
        window_peaks = peaks[i : i + num_taps]
        time_diff = (window_peaks[-1] - window_peaks[0]) / fps
        if time_diff <= duration_limit:
            return window_peaks / fps
    return None

def find_calibration_taps_sensor(gyro_path, duration_limit=2.0, num_taps=5):
    from scipy.signal import find_peaks
    if not os.path.exists(gyro_path):
        return None, None
        
    df = pd.read_csv(gyro_path)
    df['mag'] = np.sqrt(df['x']**2 + df['y']**2 + df['z']**2)
    
    prominence = np.max(df['mag']) * 0.15
    peaks, _ = find_peaks(df['mag'], distance=6, prominence=prominence)
    
    for i in range(len(peaks) - num_taps + 1):
        window_peaks = df.iloc[peaks[i : i + num_taps]]
        times = window_peaks['seconds_elapsed'].values
        time_diff = times[-1] - times[0]
        if time_diff <= duration_limit:
            return times, window_peaks['time'].values
    return None, None

def clean_and_normalize(text):
    pre_mappings = {
        r"\bboard\s+defens(e|ive)\b": "forward defensive",
        r"\btouch\s+shot\b": "push",
        r"\bwe're\s+going\s+to\b": "forward defensive",
        r"\b(space|place|lacing|racing|lacing) up\b": "facing up",
        r"\bpuncture\b": "punch shot",
        r"\byorka\b": "yorker",
        r"\b(yorker's own|yorka zone)\b": "yorker zone",
        r"\bmid-wet\b": "midwicket",
        r"\bnichs\b": "Nicolls",
        r"\b(me run|me on)\b": "mid-on",
        r"\bmidweek\b": "midwicket",
        r"\bcarre сол\b": "finished",
        r"\bcrook\b": "flick",
        r"\b(half|have)\b": "off",
        r"\b(offside|off-side)\b": "off side",
        r"\b(onside|on-side)\b": "on side",
        r"\b(4|four|for|force|fall|5|five)\s+defens(e|ive)\b": "forward defensive",
        r"\bto forward defensive\b": "two forward defensive",
        r"\ball to\b": "all two",
        r"\bto backward defense\b": "two backward defense",
        r"\bback with defens(e|ive)\b": "back-foot defensive",
        r"\bbackward defens(e|ive)\b": "back-foot defensive",
        r"\bi could defens(e|ive)\b": "back-foot defensive",
        r"\bso to\b": "so two",
        r"\bwell\s+(\d+|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty)\b": r"ball \1",
        r"\bbowl\s+(\d+|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty)\b": r"ball \1",
        r"\bfor\s+(\d+|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty)\b": r"ball \1",
        r"\ball\s+defense\b": "forward defensive",
        r"\bcatch up\b": "facing up",
        r"\brobert guide\b": "glide",
        r"\bsmeat it\b": "smashed it",
    }
    
    cleaned = text.lower()
    for pattern, replacement in pre_mappings.items():
        cleaned = re.sub(pattern, replacement, cleaned)
    return cleaned

def word_to_num(word):
    mapping = {
        "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
        "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15, "sixteen": 16, "seventeen": 17,
        "eighteen": 18, "nineteen": 19, "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60, "seventy": 70,
    }
    if word.isdigit():
        return int(word)
    return mapping.get(word.lower(), None)

def transcribe_audio_local(audio_path):
    import whisper
    import difflib
    
    print(f"🎙️ Loading local Whisper 'base' model...")
    model = whisper.load_model("base")
    
    print(f"🎙️ Transcribing {os.path.basename(audio_path)} locally...")
    result = model.transcribe(audio_path, verbose=False)
    
    segments = result.get("segments", [])
    print(f"✅ Generated {len(segments)} transcription segments locally.")
    
    # Step 1: Merge segments using event duration limit of 7.0s
    num_pattern = r"\b(?:shot|ball|round)?\s*(\d+|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty|thirty|forty|fifty|sixty|seventy)\b"
    
    grouped_segments = []
    for s in segments:
        text = s["text"].strip()
        if not text:
            continue
        cleaned = clean_and_normalize(text)
        has_num = re.search(num_pattern, cleaned) is not None
        is_facing_up_start = "facing up" in cleaned
        
        if not grouped_segments:
            grouped_segments.append({
                "start": s["start"],
                "end": s["end"],
                "text": cleaned,
                "has_num": has_num
            })
        else:
            prev = grouped_segments[-1]
            elapsed = s["start"] - prev["start"]
            is_prev_facing_up = "facing up" in prev["text"]
            
            # Merge if elapsed <= 7.0s, current is not a new shot number, and neither is a "facing up" start/end
            if elapsed <= 7.0 and not has_num and not is_facing_up_start and not is_prev_facing_up:
                prev["text"] = (prev["text"] + " " + cleaned).strip()
                prev["end"] = s["end"]
            else:
                grouped_segments.append({
                    "start": s["start"],
                    "end": s["end"],
                    "text": cleaned,
                    "has_num": has_num
                })
                
    glossary = {
        "Actions": ["facing up"],
        "Shots": [
            "Straight Drive", "Cover Drive", "Off Drive", "On Drive", 
            "Forward Defensive", "Forward Defense", "Back-foot Defensive", "Back-foot Defense", 
            "Flick Shot", "Glance", "Leg Glance", "On-Glance", "Traditional Sweep Shot", "Sweep", 
            "Square Cut", "Cut", "Back-foot Punch", "Punch", "Pull Shot", "Hook Shot", 
            "Late Cut", "Steer", "Glide", "push", "Slog", "Big hit", "Hit over cow", 
            "Hit over cow corner", "Slog Sweep", "Switch Hit", "Reverse Sweep",
            "no shot", "leave"
        ],
        "Quality": [
            "Good", "great", "middled it", "nailed it", "smoked it", "smashed it", 
            "excellent", "OK", "Okay", "average", "poor", "edge", "edged", "miss", 
            "play and miss", "mishit", "toe", "toed", "hit high", "hit high on bat"
        ],
        "Admin": [
            "machine jam", "Gray Nicolls", "Nichs", "Eye in bat", "Game bat", "Game day bat", "finished"
        ]
    }
    
    flat_shots = [s.lower() for s in glossary["Shots"]]
    flat_qualities = [q.lower() for q in glossary["Quality"]]
    flat_admins = [a.lower() for a in glossary["Admin"]]
    
    raw_events = []
    
    for segment in grouped_segments:
        start_time = segment["start"]
        end_time = segment["end"]
        cleaned_text = segment["text"]
        
        # Split text into sub-clauses ONLY if it contains multiple shot indices
        matches = list(re.finditer(num_pattern, cleaned_text))
        
        sub_segments = []
        if len(matches) > 1:
            last_idx = 0
            for idx, m in enumerate(matches):
                start_idx = m.start()
                if idx > 0:
                    sub_text = cleaned_text[last_idx:start_idx].strip()
                    if sub_text:
                        sub_segments.append((start_time + (last_idx / len(cleaned_text)) * (end_time - start_time), sub_text))
                last_idx = start_idx
            sub_text = cleaned_text[last_idx:].strip()
            if sub_text:
                sub_segments.append((start_time + (last_idx / len(cleaned_text)) * (end_time - start_time), sub_text))
        else:
            sub_segments.append((start_time, cleaned_text))
            
        for t_val, txt in sub_segments:
            shot_num = None
            m_num = re.search(num_pattern, txt)
            if m_num:
                val = word_to_num(m_num.group(1))
                if val is not None:
                    shot_num = val
                    
            matched_shot = None
            matched_quality = None
            matched_admin = None
            
            for term in flat_shots:
                if term in txt:
                    matched_shot = term
                    break
            if not matched_shot:
                closest = difflib.get_close_matches(txt, flat_shots, n=1, cutoff=0.7)
                if closest:
                    matched_shot = closest[0]
                    
            for term in flat_qualities:
                if term in txt:
                    matched_quality = term
                    break
            if not matched_quality:
                closest = difflib.get_close_matches(txt, flat_qualities, n=1, cutoff=0.7)
                if closest:
                    matched_quality = closest[0]
                    
            for term in flat_admins:
                if term in txt:
                    matched_admin = term
                    break
                    
            # Handle delayed rating appending logic
            if shot_num is None and matched_shot is None and matched_quality is not None and matched_admin is None:
                if len(txt.split()) <= 3 and raw_events:
                    prev_ev = raw_events[-1]
                    time_diff = t_val - prev_ev["timestamp_seconds"]
                    if time_diff <= 10.0:
                        prev_ev["text"] = (prev_ev["text"] + " " + txt).strip()
                        prev_ev["quality"] = matched_quality
                        print(f"   📝 Appended delayed quality '{matched_quality}' to shot: '{prev_ev['text']}' (diff={time_diff:.1f}s)")
                        continue
                    else:
                        print(f"   🗑️ Discarding delayed quality '{matched_quality}' at {t_val:.1f}s (diff={time_diff:.1f}s > 10s)")
                        continue
                    
            # Require either shot number, shot type, admin action, or explicit "facing up"
            # to filter out quality-only false positive events
            if shot_num is not None or matched_shot is not None or matched_admin is not None or "facing up" in txt:
                is_duplicate = False
                for prev_ev in raw_events[-2:]:
                    prev_txt = prev_ev["text"]
                    time_diff = abs(t_val - prev_ev["timestamp_seconds"])
                    if time_diff <= 3.5:
                        if prev_txt == txt:
                            is_duplicate = True
                            break
                        if len(txt) > 5 and len(prev_txt) > 5:
                            ratio = difflib.SequenceMatcher(None, txt, prev_txt).ratio()
                            if ratio > 0.85:
                                is_duplicate = True
                                break
                if is_duplicate:
                    continue
                    
                raw_events.append({
                    "timestamp_seconds": t_val,
                    "shot_number": shot_num,
                    "shot_type": matched_shot,
                    "quality": matched_quality,
                    "text": txt
                })

    formatted_shots = []
    last_num = 0
    for ev in raw_events:
        num = ev["shot_number"]
        
        if num is not None:
            if num <= last_num:
                # Ignore sequence numbers that jump backwards (phonetic slips or setup talk)
                num = None
                
        is_facing_up = "facing up" in ev["text"].lower() and ev["shot_type"] is None
        
        if is_facing_up:
            s_type = "Facing up"
            num = None
            # Extract quality if present
            quality = "good"
            raw_qual = ev["quality"]
            if raw_qual:
                raw_qual_lower = raw_qual.lower()
                if any(w in raw_qual_lower for w in ["okay", "ok", "decent"]):
                    quality = "okay"
                elif any(w in raw_qual_lower for w in ["poor", "bad", "average"]):
                    quality = "poor"
        else:
            if ev["shot_type"] is None and num is None:
                # Discard events with no shot number and no shot type that are not stance checks
                continue
                
            if num is not None:
                if num > last_num + 5:
                    mod_num = num % 100
                    if abs(mod_num - last_num) <= 5:
                        num = mod_num
                    elif num > 100:
                        num = last_num + 1
                last_num = num
            else:
                last_num += 1
                num = last_num
                
            s_type = "Defence/Block"
            quality = "good"
            
            raw_shot = ev["shot_type"]
            if raw_shot:
                raw_shot_lower = raw_shot.lower()
                if "cover drive" in raw_shot_lower:
                    s_type = "Cover drive"
                elif "straight drive" in raw_shot_lower:
                    s_type = "Straight drive"
                elif "off drive" in raw_shot_lower:
                    s_type = "Off drive"
                elif "on drive" in raw_shot_lower:
                    s_type = "On drive"
                elif "pull" in raw_shot_lower:
                    s_type = "Pull shot"
                elif "hook" in raw_shot_lower:
                    s_type = "Hook shot"
                elif "cut" in raw_shot_lower:
                    s_type = "Cut shot"
                elif "flick" in raw_shot_lower:
                    s_type = "Flick"
                elif "glance" in raw_shot_lower:
                    s_type = "Leg glance"
                elif "sweep" in raw_shot_lower:
                    s_type = "Sweep"
                elif "push" in raw_shot_lower:
                    s_type = "Push"
                elif "no shot" in raw_shot_lower:
                    s_type = "No shot"
                elif "leave" in raw_shot_lower:
                    s_type = "Leave"
                    
            raw_qual = ev["quality"]
            if raw_qual:
                raw_qual_lower = raw_qual.lower()
                if any(w in raw_qual_lower for w in ["excellent", "perfect", "nailed it", "smoked it", "smashed it", "middled it", "great"]):
                    quality = "excellent"
                elif any(w in raw_qual_lower for w in ["poor", "bad", "average", "toe", "toed", "edge", "edged", "mishit", "hit high"]):
                    quality = "poor"
                elif any(w in raw_qual_lower for w in ["miss", "play and miss"]):
                    quality = "miss"
                elif any(w in raw_qual_lower for w in ["okay", "ok", "decent"]):
                    quality = "okay"
                    
        formatted_shots.append({
            "timestamp_seconds": ev["timestamp_seconds"],
            "shot_number": num,
            "shot_type": s_type,
            "quality": quality,
            "narrated_text": ev["text"]
        })
        
    return formatted_shots

def transcribe_audio_gemini(audio_path):
    from google import genai
    from google.genai import types
    import re
    
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
        narrated_text: str

    class NarrationList(BaseModel):
        narrations: List[NarrationItem]

    print("🎙️ Preparing prompt with biomechanics constraints...")
    prompt_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gemini_narration_prompt.md")
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
            "2. \"[Number] [Shot Type] [Rating]\" (for example: \"One, push shot, good\" or \"Twelve, pull shot, excellent\").\n\n"
            "The audio contains long periods of silence, ball impact noises, and background sounds. Ignore all silence and background noise.\n\n"
            "Search the entire audio file for all spoken narrations matching the pattern.\n"
            "The batsman may refer to the following expected shot types (grouped by biomechanical class):\n"
            "- Drive/Defence: \"Straight Drive\", \"Cover Drive\", \"Off Drive\", \"On Drive\", \"Forward Defensive\", \"Back-foot Defensive\", \"Push Shot\" (or \"Push\")\n"
            "- Glance/Flicks: \"Flick Shot\", \"Leg Glance\", \"On-Glance\", \"Traditional Sweep Shot\" (or \"Sweep\")\n"
            "- Cut/Punch: \"Square Cut\", \"Cut\", \"Back-foot Punch\"\n"
            "- Pull/Hook: \"Pull Shot\", \"Hook Shot\"\n"
            "- Deflection/Guide: \"Late Cut\", \"Square Upper Cut\", \"Steer / Glide\"\n"
            "- Power Shot: \"Lofted Straight Drive\", \"Lofted Cover Drive\", \"Slog Sweep\", \"Switch Hit\", \"Reverse Sweep\", \"Helicopter Shot\"\n\n"
            "The batsman will rate the shot quality using one of these rating words:\n"
            "\"Excellent\", \"Good\", \"Poor\", \"Miss\", \"Okay\", \"Decent\"\n\n"
            "Scan the audio carefully from start to finish to capture every single one of the shots played (up to approximately Shot 69 or 72). "
            "Do not skip shots, do not hallucinate repetitive entries in silence, and output only the matching list."
        )
    schema_instruction = (
        "\n\nOutput the result as a JSON object matching the response schema: a list of narration items. "
        "Each item must contain `timestamp_seconds` (float, e.g. 3.45 or 12.18), `shot_number` (int, or null for stance/admin/non-numbered events), "
        "`shot_type` (str, e.g. 'Facing up', 'Cover Drive', 'Cut', 'Leg Glance', etc.), `rating` (str, e.g. 'good', 'ok', or null), "
        "and `narrated_text` (str, the exact transcribed text of the utterance)."
    )
    prompt = prompt_base + schema_instruction
    
    models_to_try = ['gemini-3.5-flash', 'gemini-2.0-flash', 'gemini-2.5-flash']
    response = None
    last_err = None
    for model_name in models_to_try:
        try:
            print(f"🎙️ Requesting structured transcription from {model_name}...")
            response = client.models.generate_content(
                model=model_name,
                contents=[uploaded_file, prompt],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=NarrationList,
                ),
            )
            print(f"✅ Success with {model_name}!")
            break
        except Exception as e:
            print(f"⚠️ {model_name} failed: {e}")
            last_err = e
            
    if response is None:
        raise Exception(f"All Gemini models failed. Last error: {last_err}")
    
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
                    "texts": [item.get("narrated_text", "")]
                })
            parsed_structured = True
            print(f"✅ Successfully parsed {len(shot_events)} shots via Pydantic response_schema.")
    except Exception as e:
        print(f"⚠️ Failed to parse structured JSON ({e}). Falling back to line-by-line regex...")
        
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
                    "texts": [text]
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
        
    formatted_shots = []
    for event in shot_events:
        full_text = " ".join(event["texts"])
        text_lower = full_text.lower()
        
        # Map shot type
        shot_type = None
        if "facing up" in text_lower:
            shot_type = "Facing up"
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
        elif "poor" in text_lower or "bad" in text_lower:
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
            
    # 4. Calibration Alignment
    offset = args.manual_offset
    if offset is None:
        # Attempt auto-start time synchronization
        print("🔍 Attempting auto-start timestamp synchronization...")
        audio_filename = os.path.basename(audio_path)
        match = re.search(r"narration_(\d{8})_(\d{6})", audio_filename)
        
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
                offset = audio_start_epoch - watch_start_epoch
                print(f"🎯 Auto-start synchronization successful!")
                print(f"   Audio Start Time:  {dt} (Epoch: {audio_start_epoch:.3f}s)")
                print(f"   Watch Start Time:  {datetime.datetime.fromtimestamp(watch_start_epoch)} (Epoch: {watch_start_epoch:.3f}s)")
                print(f"   Calculated Clock Offset: {offset:+.3f}s (Sensor = Audio {offset:+.3f}s)")
            except Exception as e:
                print(f"⚠️ Failed to parse auto-start times: {e}")
                offset = None

        if offset is None:
            print("🔍 Auto-start sync unavailable. Detecting calibration events (5-tap signature)...")
            # Convert to AIFF only when needed for peak detection
            aiff_path = os.path.join(session_dir, "audio_narration.aiff")
            convert_to_aiff(audio_path, aiff_path)
            envelope, fps = load_audio_envelope(aiff_path)
            audio_taps = find_calibration_taps_audio(envelope, fps)
            
            gyro_path = os.path.join(session_dir, "WatchGyroscope.csv")
            sensor_taps, _ = find_calibration_taps_sensor(gyro_path)
            
            if audio_taps is not None and sensor_taps is not None:
                # Sync off the first tap
                offset = sensor_taps[0] - audio_taps[0]
                print(f"🎯 Auto-calibration successful!")
                print(f"   Audio taps (sec):  {audio_taps}")
                print(f"   Sensor taps (sec): {sensor_taps}")
                print(f"   Calculated Clock Offset: {offset:+.3f}s (Sensor = Audio {offset:+.3f}s)")
            else:
                print("⚠️ WARNING: Could not automatically detect the 5-tap calibration sequence.")
                if audio_taps is None:
                    print("   - Failed to find 5 peaks in audio.")
                if sensor_taps is None:
                    print("   - Failed to find 5 peaks in watch gyroscope.")
                
                # Fallback to manual offset input
                inp = input("Please enter manual clock offset (seconds) or 0 to skip: ").strip()
                try:
                    offset = float(inp)
                except:
                    offset = 0.0
    else:
        print(f"🎯 Using manual clock offset: {offset:+.3f}s")
        
    # 5. Call local Whisper or Gemini to transcribe & parse shot timings (or load local cache if exists)
    narrations_cache_path = os.path.join(session_dir, "narrations_raw.json")
    if os.path.exists(narrations_cache_path):
        print(f"📖 Loading cached transcriptions from {narrations_cache_path}...")
        with open(narrations_cache_path, "r") as f:
            narrations = json.load(f)
    else:
        use_local = getattr(args, "local", "true").lower() == "true"
        narrations = None
        
        if use_local:
            try:
                narrations = transcribe_audio_local(audio_path)
                print(f"Successfully transcribed {len(narrations)} narrations locally via Whisper.")
            except Exception as e:
                print(f"⚠️ Local Whisper transcription failed: {e}. Falling back to Gemini...")
                
        if narrations is None:
            try:
                narrations = transcribe_audio_gemini(audio_path)
                print(f"Successfully transcribed {len(narrations)} narrations via Gemini.")
            except Exception as e:
                print(f"❌ Gemini transcription failed: {e}")
                sys.exit(1)
            
        # Write raw narrations to session dir
        with open(narrations_cache_path, "w") as f:
            json.dump(narrations, f, indent=2)
        
    # 6. Perform alignment with raw sensor logs
    gyro_path = os.path.join(session_dir, "WatchGyroscope.csv")
    accel_path = os.path.join(session_dir, "WatchAccelerometer.csv")
    gravity_path = os.path.join(session_dir, "WatchGravity.csv")
    orient_path = os.path.join(session_dir, "WatchOrientation.csv")
    
    if not os.path.exists(gyro_path):
        print("❌ ERROR: Gyroscope sensor file missing from session log.")
        sys.exit(1)
        
    df_gyro = pd.read_csv(gyro_path)
    df_gyro['mag'] = np.sqrt(df_gyro['x']**2 + df_gyro['y']**2 + df_gyro['z']**2)
    start_time_ns = df_gyro.iloc[0]['time']
    start_time_ms = int(start_time_ns / 1_000_000)
    gyro_duration = df_gyro.iloc[-1]['seconds_elapsed']

    # Detect and convert MMSS.mmm timestamps to actual elapsed seconds if needed
    if narrations:
        is_mmss = True
        for n in narrations:
            t = n['timestamp_seconds']
            sec_part = int(t) % 100
            if sec_part >= 60:
                is_mmss = False
                break
                
        max_t = max(n['timestamp_seconds'] for n in narrations)
        if max_t > gyro_duration:
            is_mmss = True
            
        if is_mmss:
            print("💡 Detected that Gemini timestamps are in MMSS.mmm format. Converting to actual elapsed seconds...")
            for n in narrations:
                t = n['timestamp_seconds']
                ival = int(t)
                frac = t - ival
                minutes = ival // 100
                seconds = ival % 100
                n['timestamp_seconds'] = float(minutes * 60 + seconds + frac)

    aligned_shots = []
    
    # Build candidate lists
    all_candidates = []
    for i, shot in enumerate(narrations):
        audio_t = shot['timestamp_seconds']
        sensor_narr_t = audio_t + offset
        is_non_swing = any(term in shot['shot_type'].lower() for term in ["no shot", "leave", "facing up"])
        
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
    first_narr_t = narrations[0]['timestamp_seconds'] + offset
    dp.append([calculate_candidate_score(cand, first_narr_t) for cand in all_candidates[0]])
    parent.append([-1] * len(all_candidates[0]))
    
    for i in range(1, M):
        sensor_narr_t = narrations[i]['timestamp_seconds'] + offset
        dp_i = []
        parent_i = []
        for j, cand in enumerate(all_candidates[i]):
            best_score = -999999.0
            best_k = -1
            score_j = calculate_candidate_score(cand, sensor_narr_t)
            
            # Enforce chronological order with min gap
            # Swing-to-swing gap: 1.5s. Non-swing gap: 0.5s.
            prev_is_non_swing = any(term in narrations[i-1]['shot_type'].lower() for term in ["no shot", "leave", "facing up"])
            curr_is_non_swing = any(term in narrations[i]['shot_type'].lower() for term in ["no shot", "leave", "facing up"])
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
        sensor_narr_t = audio_t + offset
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
            'shot_type': shot['shot_type'],
            'quality': shot['quality'],
            'narrated_text': shot['narrated_text']
        })
        
    df_aligned = pd.DataFrame(aligned_shots)
    aligned_csv_path = os.path.join(session_dir, "ground_truth_aligned.csv")
    df_aligned.to_csv(aligned_csv_path, index=False)
    print(f"\n✅ Ground-truth aligned file saved: {aligned_csv_path}")
    
    # 7. Extract training segments (6-second window around each impact)
    print("\nExporting 6-second training segments (3s before, 3s after impact)...")
    segments_dir = os.path.join(session_dir, "segments")
    os.makedirs(segments_dir, exist_ok=True)
    
    df_accel = pd.read_csv(accel_path)
    df_gravity = pd.read_csv(gravity_path)
    
    # Load Game Rotation Vector or fallback orientation
    game_orient_path = os.path.join(session_dir, "WatchGameOrientation.csv")
    if os.path.exists(game_orient_path):
        df_orient = pd.read_csv(game_orient_path)
        print("📖 Loaded WatchGameOrientation.csv for bat orientation")
    else:
        df_orient = pd.read_csv(orient_path)
        print("📖 Loaded WatchOrientation.csv for bat orientation (fallback)")
        
    steps_path = os.path.join(session_dir, "WatchSteps.csv")
    if os.path.exists(steps_path):
        df_steps = pd.read_csv(steps_path)
        print("📖 Loaded WatchSteps.csv for walking steps check")
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
    
    # 8. Compare with watch-detected shots in latest_timeline.txt
    timeline_path = os.path.join(session_dir, "latest_timeline.txt")
    if os.path.exists(timeline_path):
        compare_with_timeline(timeline_path, df_aligned, start_time_ms)
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
    gyro_ok = gyro_std < 0.9
    accel_ok = accel_std < 1.5
    ori_ok = ori_disp < 1.5
    steps_ok = steps_count == 0
    grav_ok = grav_y <= -3.5 or grav_y == 0.0
    
    passed = gyro_ok and accel_ok and ori_ok and steps_ok and grav_ok
    status_emoji = "🟢 SUCCESS" if passed else "🔴 FAILED"
    
    print("\n=================== Stance Check Alignment Analysis ===================")
    print(f"Stance Event: '{narrated_text}'")
    print(f"Time:         {audio_t:.1f}s (audio) ➔ Stance aligned at {t_stance:.2f}s sensor (rel)")
    print(f"  1. Gyro Std:    {gyro_std:.2f} rad/s  (Limit: < 0.9)  ➔ {'PASS' if gyro_ok else 'FAIL'}")
    print(f"  2. Accel Std:   {accel_std:.2f} m/s²   (Limit: < 1.5)  ➔ {'PASS' if accel_ok else 'FAIL'}")
    print(f"  3. Ori Disp:    {ori_disp:.2f} deg    (Limit: < 1.5)  ➔ {'PASS' if ori_ok else 'FAIL'}")
    print(f"  4. Steps:       {steps_count} steps     (Limit: 0)      ➔ {'PASS' if steps_ok else 'FAIL'}")
    print(f"  5. Gravity Y:   {grav_y:.2f} m/s²  (Limit: <= -3.5)➔ {'PASS' if grav_ok else 'FAIL'}")
    print(f"STATUS: {status_emoji} ({'All conditions met' if passed else 'Stance lock would fail'})")
    if not passed:
        fails = []
        if not gyro_ok: fails.append(f"Gyro Std ({gyro_std:.2f} >= 0.9)")
        if not accel_ok: fails.append(f"Accel Std ({accel_std:.2f} >= 1.5)")
        if not ori_ok: fails.append(f"Ori Disp ({ori_disp:.2f} >= 1.5)")
        if not steps_ok: fails.append(f"Steps count ({steps_count} > 0)")
        if not grav_ok: fails.append(f"Gravity Y ({grav_y:.2f} > -3.5)")
        print(f"  Failed condition(s): {', '.join(fails)}")
    print("-----------------------------------------------------------------------")

def normalize_shot_class(shot_name):
    if not shot_name:
        return "Unknown"
    s = shot_name.lower().strip()
    
    # Map to the 6 biomechanical classes + Miss + Sweep
    if "pull" in s or "hook" in s:
        return "PULL/HOOK"
    if "flick" in s or "glance" in s:
        return "GLANCE/FLICK"
    if "cut" in s or "punch" in s:
        return "CUT/PUNCH"
    if "guide" in s or "deflection" in s or "deflect" in s:
        return "DEFLECTION/GUIDE"
    if "power" in s or "loft" in s:
        return "POWER SHOT"
    if "drive" in s or "defence" in s or "defense" in s or "push" in s or "straight" in s or "forward" in s or "block" in s:
        return "DRIVE/DEFENCE"
    if "sweep" in s:
        return "Sweep"
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

if __name__ == "__main__":
    main()
