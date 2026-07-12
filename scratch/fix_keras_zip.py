#!/usr/bin/env python3
import os
import zipfile
import json
import shutil

src_model = "/Users/neilkloot/Code/Batting Sensor Stats/cricshot10k/Models/Efficientnetv2-s_GRU_128_NEEDS_CROPPED_SEGMENTED_SHOTS.keras"
backup_model = "/Users/neilkloot/Code/Batting Sensor Stats/cricshot10k/Models/Efficientnetv2-s_GRU_128_NEEDS_CROPPED_SEGMENTED_SHOTS.keras.backup"
temp_dir = "scratch/keras_temp"

if not os.path.exists(backup_model):
    print(f"Creating backup of the model at {backup_model}...")
    shutil.copyfile(src_model, backup_model)

if os.path.exists(temp_dir):
    shutil.rmtree(temp_dir)
os.makedirs(temp_dir)

print("Extracting model archive...")
with zipfile.ZipFile(src_model, 'r') as zip_ref:
    zip_ref.extractall(temp_dir)

config_path = os.path.join(temp_dir, "config.json")
if os.path.exists(config_path):
    print("Loading config.json...")
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    # We want to recursively inspect the config dictionary and convert string numbers in shapes/batch_shapes to integers
    def fix_shapes(d):
        if isinstance(d, dict):
            for k, v in d.items():
                if k in ["shape", "batch_shape", "batch_input_shape"] and isinstance(v, list):
                    new_shape = []
                    for dim in v:
                        if isinstance(dim, str) and dim.isdigit():
                            new_shape.append(int(dim))
                        else:
                            new_shape.append(dim)
                    d[k] = new_shape
                    print(f"Fixed shape key '{k}': {v} -> {new_shape}")
                else:
                    fix_shapes(v)
        elif isinstance(d, list):
            for item in d:
                fix_shapes(item)

    fix_shapes(config)
    
    # Write back corrected config
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)
    print("Saved corrected config.json")
    
    # Re-zip the archive
    print("Re-packing model archive...")
    os.remove(src_model)
    with zipfile.ZipFile(src_model, 'w', zipfile.ZIP_DEFLATED) as zip_out:
        for root, dirs, files in os.walk(temp_dir):
            for file in files:
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, temp_dir)
                zip_out.write(full_path, rel_path)
    print("Model patched successfully!")
else:
    print("❌ config.json not found in model archive.")

# Clean up
shutil.rmtree(temp_dir)
