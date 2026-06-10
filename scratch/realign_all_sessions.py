#!/usr/bin/env python3
import subprocess
import os

sessions = [
    "session-2026-05-30_15-04-41",
    "session-2026-05-31_10-06-52",
    "session-2026-05-31_14-12-10",
    "session-2026-06-01_12-23-38",
    "session-2026-06-05_12-29-59",
    "session-2026-06-07_14-34-24",
    "sessions/session-2026-06-08_12-22-26"
]

base_dir = "/Users/neilkloot/Code/Batting Sensor Stats/live_watch_sessions"

for session in sessions:
    session_dir = os.path.join(base_dir, session)
    print(f"\n======================================================================")
    print(f"  RUNNING PIPELINE ALIGNMENT ON: {session}")
    print(f"======================================================================\n")
    
    cmd = [
        "python3",
        "automate_pipeline.py",
        "--session-dir",
        session_dir
    ]
    
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode == 0:
        print(f"✅ Alignment successful for {session}!")
        # Print the summary from stdout
        summary_lines = []
        capture = False
        for line in res.stdout.splitlines():
            if "Summary" in line or "Accuracy Report" in line:
                capture = True
            if capture:
                summary_lines.append(line)
            if "===============================================================" in line and capture:
                break
        print("\n".join(summary_lines))
    else:
        print(f"❌ Alignment failed for {session}!")
        print("ERROR:")
        print(res.stderr)
