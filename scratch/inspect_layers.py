#!/usr/bin/env python3
import os
import zipfile
import json

src_model = "/Users/neilkloot/Code/Batting Sensor Stats/cricshot10k/Models/Efficientnetv2-s_GRU_128_NEEDS_CROPPED_SEGMENTED_SHOTS.keras"
with zipfile.ZipFile(src_model, 'r') as zip_ref:
    config_bytes = zip_ref.read("config.json")
    config = json.loads(config_bytes.decode("utf-8"))

print("Sequential layers:")
for idx, layer in enumerate(config["config"]["layers"]):
    print(f"Layer {idx}: {layer['class_name']} (name: {layer['config'].get('name')})")
    if layer['class_name'] == 'TimeDistributed':
        inner = layer['config']['layer']
        print(f"  Wraps: {inner['class_name']} (name: {inner['config'].get('name')})")
    elif layer['class_name'] == 'GRU':
        print(f"  Units: {layer['config'].get('units')}, Return Sequences: {layer['config'].get('return_sequences')}")
    elif layer['class_name'] == 'Dense':
        print(f"  Units: {layer['config'].get('units')}, Activation: {layer['config'].get('activation')}")
