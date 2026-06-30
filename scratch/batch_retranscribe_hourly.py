import os
import subprocess
import time
import sys

BASE_DIR = "/Users/neilkloot/Code/Batting Sensor Stats/live_watch_sessions"
PIPELINE_SCRIPT = "/Users/neilkloot/Code/CricketBattingTracker/automate_pipeline.py"
EXCLUDE_SESSION = "session-2026-06-29_12-21-45"
WAIT_TIME_SECONDS = 3600 # 1 hour

def main():
    if not os.path.exists(BASE_DIR):
        print(f"❌ Base directory does not exist: {BASE_DIR}")
        sys.exit(1)
        
    sessions = []
    for d in os.listdir(BASE_DIR):
        if d.startswith("session-") and os.path.isdir(os.path.join(BASE_DIR, d)):
            if d != EXCLUDE_SESSION:
                sessions.append(d)
                
    sessions.sort()
    
    print(f"📂 Found {len(sessions)} previous sessions to re-transcribe (excluding {EXCLUDE_SESSION}):")
    for s in sessions:
        print(f"  - {s}")
    print(f"⏳ Total execution time will be approximately {len(sessions) - 1} hours.")
    
    print("\nStarting batch re-transcription process...")
    
    for idx, session in enumerate(sessions):
        session_dir = os.path.join(BASE_DIR, session)
        
        audio_file = None
        for f in os.listdir(session_dir):
            if f.endswith(".m4a"):
                audio_file = os.path.join(session_dir, f)
                break
                
        if not audio_file:
            print(f"⚠️  [{idx+1}/{len(sessions)}] No audio file found in {session}, skipping...")
            continue
            
        print(f"\n🚀 [{idx+1}/{len(sessions)}] Processing: {session}")
        print(f"   Audio: {os.path.basename(audio_file)}")
        
        cmd = [
            "python3", PIPELINE_SCRIPT,
            "--audio", audio_file,
            "--session-dir", session_dir,
            "--force-retranscribe",
            "--model", "gemini-2.5-flash"
        ]
        
        start_time = time.time()
        try:
            subprocess.run(cmd, check=True)
            print(f"✅ Finished re-transcribing {session}")
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to process {session}: {e}")
            
        if idx < len(sessions) - 1:
            print(f"⏳ Session processed in {time.time() - start_time:.1f}s.")
            print(f"⏳ Sleeping 1 hour ({WAIT_TIME_SECONDS} seconds) before starting the next session...")
            time.sleep(WAIT_TIME_SECONDS)
            
    print("\n🎉 Batch re-transcription complete!")

if __name__ == "__main__":
    main()
