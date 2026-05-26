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

def transcribe_audio_gemini(audio_path):
    from google import genai
    from google.genai import types
    import re
    
    api_key = os.environ.get("GEMINI_API_KEY")
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
        
    print("🎙️ Requesting full transcription from Gemini...")
    prompt = (
        "This is an audio file of a cricket batting practice. The batsman narrates his shots. "
        "He narrates carefully in the format 'Shot [number], [optional shot type] [shot rating]'. "
        "Please provide a complete, word-for-word transcription of the entire audio file from start to finish. "
        "Write it as a chronological list of narrations. For each narration, provide:\n"
        "1. The timestamp (in MM:SS format or MM:SS:cc format, e.g. 01:23 or 01:23:45) when the narration begins.\n"
        "2. The exact text spoken.\n\n"
        "Ensure you transcribe every single shot from Shot 1 to the final shot (which should be around Shot 69 or 72)."
    )
    
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=[uploaded_file, prompt]
    )
    
    # Delete file from Cloud Storage
    try:
        client.files.delete(name=uploaded_file.name)
    except:
        pass
        
    text_transcript = response.text
    print("Parsing transcription text into structured JSON...")
    
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
    shot_events = []
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
        shot_type = "Defence/Block"
        if "cover drive" in text_lower:
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
            
    # 3. Process Audio to AIFF for peak alignment
    aiff_path = os.path.join(session_dir, "audio_narration.aiff")
    convert_to_aiff(audio_path, aiff_path)
    
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
        
    # 5. Call Gemini to transcribe & parse shot timings (or load local cache if exists)
    narrations_cache_path = os.path.join(session_dir, "narrations_raw.json")
    if os.path.exists(narrations_cache_path):
        print(f"📖 Loading cached transcriptions from {narrations_cache_path}...")
        with open(narrations_cache_path, "r") as f:
            narrations = json.load(f)
    else:
        try:
            narrations = transcribe_audio_gemini(audio_path)
            print(f"Successfully transcribed {len(narrations)} narrations.")
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
    print("\nAligning spoken narrations with physical movements...")
    for shot in narrations:
        audio_t = shot['timestamp_seconds']
        sensor_narr_t = audio_t + offset
        
        # Search window in raw sensor data: [sensor_narr_t - 6.0, sensor_narr_t]
        window = df_gyro[(df_gyro['seconds_elapsed'] >= sensor_narr_t - 6.0) & (df_gyro['seconds_elapsed'] <= sensor_narr_t)]
        if len(window) == 0:
            print(f"   ⚠️ Skipping narration '{shot['narrated_text']}' at {audio_t:.1f}s: No sensor data in window.")
            continue
            
        # Find peak gyro magnitude (impact time)
        idx_max = window['mag'].idxmax()
        impact_row = df_gyro.loc[idx_max]
        impact_t = impact_row['seconds_elapsed']
        impact_ns = impact_row['time']
        
        print(f"   🔗 '{shot['narrated_text']}' ({audio_t:.1f}s audio) ➔ Swing at {impact_t:.2f}s sensor (rel) / {impact_ns} (ns)")
        
        aligned_shots.append({
            'shot_index': len(aligned_shots) + 1,
            'shot_number': shot.get('shot_number', len(aligned_shots) + 1),
            'audio_time_seconds': audio_t,
            'sensor_narr_time_seconds': sensor_narr_t,
            'impact_time_seconds': impact_t,
            'impact_timestamp_ns': impact_ns,
            'impact_gyro_mag': impact_row['mag'],
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
    df_orient = pd.read_csv(orient_path)
    
    for idx, row in df_aligned.iterrows():
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
        
    print(f"✅ Saved {len(df_aligned)} segments to {segments_dir}/")
    
    # 8. Compare with watch-detected shots in latest_timeline.txt
    timeline_path = os.path.join(session_dir, "latest_timeline.txt")
    if os.path.exists(timeline_path):
        compare_with_timeline(timeline_path, df_aligned, start_time_ms)
        
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
