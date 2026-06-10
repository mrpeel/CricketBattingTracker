#!/usr/bin/env python3
import re
from collections import defaultdict

log_path = "/Users/neilkloot/.gemini/antigravity/brain/2b0e7b71-5668-46cd-a61d-48994a7fdd70/.system_generated/tasks/task-142.log"

sessions = []
current_session = None

with open(log_path, "r") as f:
    for line in f:
        line = line.strip()
        if "REPORT —" in line:
            current_session = line.split("REPORT — ")[-1]
            sessions.append({
                "name": current_session,
                "configs": {}
            })
        elif line.startswith("|") and not "Configuration" in line and not ":---" in line:
            parts = [p.strip() for p in line.split("|")[1:-1]]
            if len(parts) >= 8:
                config_name = parts[0]
                detected = int(parts[1])
                tp = int(parts[2])
                fp = int(parts[3])
                fn = int(parts[4])
                recall = float(parts[5].replace("%", ""))
                precision = float(parts[6].replace("%", ""))
                fp_min = float(parts[7])
                
                sessions[-1]["configs"][config_name] = {
                    "detected": detected, "tp": tp, "fp": fp, "fn": fn,
                    "recall": recall, "precision": precision, "fp_min": fp_min
                }

# Now aggregate
aggregated = defaultdict(lambda: {"tp": 0, "fp": 0, "fn": 0, "detected": 0, "duration": 0.0})
durations = {
    "session-2026-05-30_15-04-41": 18.82,
    "session-2026-05-31_10-06-52": 1.11,
    "session-2026-05-31_14-12-10": 13.13,
    "session-2026-06-01_12-23-38": 17.99,
    "session-2026-06-05_12-29-59": 5.47,
    "session-2026-06-07_14-34-24": 12.15
}

total_dur = sum(durations.values())

for s in sessions:
    dur = durations.get(s["name"], 0.0)
    for cfg_name, metrics in s["configs"].items():
        aggregated[cfg_name]["tp"] += metrics["tp"]
        aggregated[cfg_name]["fp"] += metrics["fp"]
        aggregated[cfg_name]["fn"] += metrics["fn"]
        aggregated[cfg_name]["detected"] += metrics["detected"]
        aggregated[cfg_name]["duration"] += dur

print("| Configuration | Total TP | Total FP | Total FN | Total Swings | Recall % | FPs / Min |")
print("| :--- | :---: | :---: | :---: | :---: | :---: | :---: |")
for cfg_name, data in sorted(aggregated.items(), key=lambda x: x[1]["tp"]/(x[1]["tp"]+x[1]["fn"]) if (x[1]["tp"]+x[1]["fn"])>0 else 0, reverse=True):
    tp, fp, fn = data["tp"], data["fp"], data["fn"]
    total = tp + fn
    recall = 100.0 * tp / total if total > 0 else 0.0
    fp_min = fp / total_dur
    print(f"| {cfg_name:<30} | {tp:^8} | {fp:^8} | {fn:^8} | {total:^12} | {recall:>7.1f}% | {fp_min:>9.2f} |")
