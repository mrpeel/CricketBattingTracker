#!/usr/bin/env python3
import os
import zipfile
import json

src_model = "/Users/neilkloot/Code/Batting Sensor Stats/cricshot10k/Models/Efficientnetv2-s_GRU_128_NEEDS_CROPPED_SEGMENTED_SHOTS.keras"
with zipfile.ZipFile(src_model, 'r') as zip_ref:
    config_bytes = zip_ref.read("config.json")
    config = json.loads(config_bytes.decode("utf-8"))

print(json.dumps(config, indent=2)[:3000])
