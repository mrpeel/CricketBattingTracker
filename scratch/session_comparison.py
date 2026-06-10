#!/usr/bin/env python3
import os
import json

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

target_configs = ["Current (Tight)", "Production Kotlin", "New Optimized Kotlin"]

print("| Session Name | Current (Tight) Recall | Current (Tight) FP/min | Production Kotlin Recall | Production Kotlin FP/min | New Optimized Kotlin Recall | New Optimized Kotlin FP/min |")
print("| :--- | :---: | :---: | :---: | :---: | :---: | :---: |")

for s in sessions:
    short_name = s["name"].replace("session-", "")
    metrics_str = [short_name]
    for cfg in target_configs:
        m = s["configs"].get(cfg, {"recall": 0.0, "fp_min": 0.0})
        metrics_str.append(f"{m['recall']:.1f}%")
        metrics_str.append(f"{m['fp_min']:.2f}")
    print("| " + " | ".join(metrics_str) + " |")
