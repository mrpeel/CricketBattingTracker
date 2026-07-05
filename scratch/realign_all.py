import os
import subprocess
import sys

BASE_DIR = "/Users/neilkloot/Code/Batting Sensor Stats/live_watch_sessions"
PIPELINE_SCRIPT = "/Users/neilkloot/Code/CricketBattingTracker/automate_pipeline.py"

def main():
    if not os.path.exists(BASE_DIR):
        print(f"❌ Base directory does not exist: {BASE_DIR}")
        sys.exit(1)
        
    all_sessions = sorted([
        d for d in os.listdir(BASE_DIR) 
        if d.startswith("session-") and os.path.isdir(os.path.join(BASE_DIR, d))
    ])
    
    print(f"📂 Found {len(all_sessions)} sessions to realign.")
    
    failed_sessions = []
    
    for idx, session in enumerate(all_sessions):
        session_dir = os.path.join(BASE_DIR, session)
        audio_file = None
        for f in os.listdir(session_dir):
            if f.endswith(".m4a"):
                audio_file = os.path.join(session_dir, f)
                break
                
        if not audio_file:
            print(f"⚠️  [{idx+1}/{len(all_sessions)}] No audio file found in {session}, skipping...")
            continue
            
        print(f"\n🚀 [{idx+1}/{len(all_sessions)}] Realigning session: {session}")
        
        # Run without --force-retranscribe so it loads cached narrations_raw.json
        cmd = [
            "python3", PIPELINE_SCRIPT,
            "--audio", audio_file,
            "--session-dir", session_dir
        ]
        
        try:
            subprocess.run(cmd, check=True)
            print(f"✅ Successfully realigned {session}")
        except subprocess.CalledProcessError as e:
            print(f"❌ Alignment validation failed for {session}!")
            # Ensure the csv is deleted so it doesn't skew unit test evaluations
            aligned_csv = os.path.join(session_dir, "ground_truth_aligned.csv")
            if os.path.exists(aligned_csv):
                os.remove(aligned_csv)
            failed_sessions.append(session)
            
    print("\n" + "="*80)
    success_count = len(all_sessions) - len(failed_sessions)
    print(f"📊 Realign Batch Summary:")
    print(f"   Success: {success_count}/{len(all_sessions)}")
    print(f"   Failed:  {len(failed_sessions)}/{len(all_sessions)}")
    
    if failed_sessions:
        print("\n❌ Failed sessions (ground_truth_aligned.csv removed):")
        for fs in failed_sessions:
            print(f"  - {fs}")
        sys.exit(1)
    else:
        print("\n🎉 All sessions successfully realigned and validated with 0 errors!")
    print("="*80 + "\n")

if __name__ == "__main__":
    main()
