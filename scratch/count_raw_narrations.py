import json
from collections import Counter

def normalize_shot_class(shot_name):
    if not shot_name:
        return "Unknown"
    s = shot_name.lower().strip()
    
    if "pull" in s or "hook" in s:
        return "PULL/HOOK"
    if "flick" in s or "glance" in s:
        return "GLANCE/FLICK"
    if "cut" in s or "punch" in s:
        return "CUT/PUNCH"
    if "guide" in s or "glide" in s or "deflection" in s or "deflect" in s:
        return "DEFLECTION/GUIDE"
    if "power" in s or "loft" in s:
        return "POWER SHOT"
    if "drive" in s or "defence" in s or "defense" in s or "push" in s or "straight" in s or "forward" in s or "block" in s:
        return "DRIVE/DEFENCE"
    if "sweep" in s:
        return "Sweep"
    if "miss" in s:
        return "Miss"
        
    return "Non-Swing/Setup"

path = "/Users/neilkloot/Code/Batting Sensor Stats/live_watch_sessions/session-2026-05-31_14-12-10/narrations_raw.json"
with open(path, "r") as f:
    data = json.load(f)

# Group shots
grouped_shots = [normalize_shot_class(item["shot_type"]) for item in data]
counter = Counter(grouped_shots)

print("--- Occurrences of Shot Classes ---")
for shot_class, count in counter.most_common():
    print(f"{shot_class}: {count}")
