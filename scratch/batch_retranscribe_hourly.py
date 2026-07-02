import os
import subprocess
import time
import sys

BASE_DIR = "/Users/neilkloot/Code/Batting Sensor Stats/live_watch_sessions"
PIPELINE_SCRIPT = "/Users/neilkloot/Code/CricketBattingTracker/automate_pipeline.py"
WAIT_TIME_SECONDS = 3600 # 1 hour
MODEL_NAME = "gemini-2.5-flash"

def main():
    if not os.path.exists(BASE_DIR):
        print(f"❌ Base directory does not exist: {BASE_DIR}")
        sys.exit(1)
        
    all_sessions = []
    for d in os.listdir(BASE_DIR):
        if d.startswith("session-") and os.path.isdir(os.path.join(BASE_DIR, d)):
            all_sessions.append(d)
                
    all_sessions.sort()
    
    if not all_sessions:
        print("❌ No sessions found.")
        sys.exit(1)
        
    last_session = all_sessions[-1]
    sessions = all_sessions[:-1]
    
    print(f"📂 Found {len(all_sessions)} total sessions.")
    print(f"ℹ️ Dynamically excluding the latest session: {last_session}")
    print(f"📂 {len(sessions)} previous sessions to check/re-transcribe:")
    
    # Filter sessions to only those that do not have a valid narrations_raw.json
    sessions_to_process = []
    for s in sessions:
        raw_json_path = os.path.join(BASE_DIR, s, "narrations_raw.json")
        if os.path.exists(raw_json_path) and os.path.getsize(raw_json_path) > 100:
            print(f"  - {s} (⏭️  Skipping - already successfully transcribed)")
        else:
            sessions_to_process.append(s)
            print(f"  - {s} (🔄 Ready to process)")
            
    if not sessions_to_process:
        print("\n🎉 All previous sessions already have valid narrations_raw.json. Nothing to do!")
        sys.exit(0)
        
    print(f"\n⏳ Total sessions left to process: {len(sessions_to_process)}")
    print(f"⏳ Total wait time will be approximately {len(sessions_to_process) - 1} hours.")
    
    print("\nStarting batch re-transcription process...")
    
    for idx, session in enumerate(sessions_to_process):
        session_dir = os.path.join(BASE_DIR, session)
        
        # Find the .m4a audio file in the session folder
        audio_file = None
        for f in os.listdir(session_dir):
            if f.endswith(".m4a"):
                audio_file = os.path.join(session_dir, f)
                break
                
        if not audio_file:
            print(f"⚠️  [{idx+1}/{len(sessions_to_process)}] No audio file found in {session}, skipping...")
            continue
            
        print(f"\n🚀 [{idx+1}/{len(sessions_to_process)}] Processing: {session}")
        print(f"   Audio: {os.path.basename(audio_file)}")
        print(f"   Model: {MODEL_NAME}")
        
        cmd = [
            "python3", PIPELINE_SCRIPT,
            "--audio", audio_file,
            "--session-dir", session_dir,
            "--force-retranscribe",
            "--model", MODEL_NAME
        ]
        
        start_time = time.time()
        try:
            subprocess.run(cmd, check=True)
            print(f"✅ Finished re-transcribing {session}")
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to process {session} with {MODEL_NAME}: {e}")
            print("🛑 Stopping batch run immediately on failure to prevent empty narration cache files.")
            sys.exit(1)
            
        if idx < len(sessions_to_process) - 1:
            print(f"⏳ Session processed in {time.time() - start_time:.1f}s.")
            print(f"⏳ Sleeping 1 hour ({WAIT_TIME_SECONDS} seconds) before starting the next session...")
            time.sleep(WAIT_TIME_SECONDS)
            
    print("\n🎉 Batch re-transcription complete!")

if __name__ == "__main__":
    main()
