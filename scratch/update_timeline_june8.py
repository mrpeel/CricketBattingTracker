#!/usr/bin/env python3
import re
import os

log_path = "/Users/neilkloot/.gemini/antigravity/brain/2b0e7b71-5668-46cd-a61d-48994a7fdd70/.system_generated/tasks/task-2149.log"
timeline_dest = "/Users/neilkloot/Code/Batting Sensor Stats/live_watch_sessions/sessions/session-2026-06-08_12-22-26/latest_timeline.txt"

# SYSTEM_START from original timeline
system_start = 1780885314683

detections = []

# Parse the log file
with open(log_path, "r") as f:
    for line in f:
        # e.g., "      Det 0: secs=5.637611, type=DRIVE/DEFENCE, speed=19.628933, isHit=true"
        m = re.search(r"Det \d+:\s+secs=([0-9.]+),\s+type=([^,]+),\s+speed=([0-9.]+),\s+isHit=(\w+)", line)
        if m:
            secs = float(m.group(1))
            shot_type = m.group(2).strip()
            speed = float(m.group(3))
            is_hit = m.group(4).strip() == "true"
            detections.append((secs, shot_type, speed, is_hit))

print(f"Parsed {len(detections)} detections from gradle test logs.")

# Write the new timeline file
with open(timeline_dest, "w") as f:
    f.write(f"SYSTEM_START: Ts={system_start}\n")
    for secs, shot_type, speed, is_hit in detections:
        ts = system_start + int(secs * 1000)
        # Construct a timeline shot line
        # Shot: Type=DRIVE/DEFENCE, Spd=24.57224, Hit=true, Acc=17.006403, SS=Excellent, Eff=62.617718, BL=99.796555, FT=84.14695, ItMs=0, Wr=-99.29527, Ts=1780885327384
        hit_str = "true" if is_hit else "false"
        f.write(f"Shot: Type={shot_type}, Spd={speed:.6f}, Hit={hit_str}, Acc=15.0, SS=Excellent, Eff=50.0, BL=90.0, FT=90.0, ItMs=0, Wr=0.0, Ts={ts}\n")
    f.write("SYSTEM_END: Ts=1780886300000\n")

print(f"Successfully generated new timeline at: {timeline_dest}")
