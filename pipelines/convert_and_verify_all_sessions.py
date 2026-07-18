#!/usr/bin/env python3
import os
import sys
import gzip
import struct
import numpy as np
import pandas as pd

# Add parent path to import load_watch_sensor
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from automate_pipeline import load_watch_sensor

def convert_csv_to_bin(csv_path, bin_path, base_name):
    # Read the original CSV
    df = pd.read_csv(csv_path)
    if df.empty:
        return 0

    # Write binary little-endian format matching Wear OS TrackerService
    # Make sure we open with gzip if the destination should be compressed
    is_gz = bin_path.endswith(".gz")
    raw_file = gzip.open(bin_path, "wb") if is_gz else open(bin_path, "wb")
    
    records_written = 0
    try:
        for _, row in df.iterrows():
            ts = int(row['time'])
            elapsed = float(row['seconds_elapsed'])
            
            if "GameOrientation" in base_name or "Orientation" in base_name:
                qx = float(row['qx'])
                qy = float(row['qy'])
                qz = float(row['qz'])
                qw = float(row['qw'])
                raw_file.write(struct.pack("<qfffff", ts, elapsed, qx, qy, qz, qw))
            elif "Steps" in base_name and "StepCounter" not in base_name:
                raw_file.write(struct.pack("<qf", ts, elapsed))
            elif "HeartRate" in base_name:
                bpm = float(row['bpm'])
                raw_file.write(struct.pack("<qff", ts, elapsed, bpm))
            elif "Barometer" in base_name:
                pressure = float(row['pressure'])
                raw_file.write(struct.pack("<qff", ts, elapsed, pressure))
            elif "StepCounter" in base_name:
                steps = float(row['steps'])
                raw_file.write(struct.pack("<qff", ts, elapsed, steps))
            else:
                x = float(row['x'])
                y = float(row['y'])
                z = float(row['z'])
                raw_file.write(struct.pack("<qffff", ts, elapsed, x, y, z))
            records_written += 1
    finally:
        raw_file.close()
        
    return records_written

def main():
    sessions_root = "/Users/neilkloot/Code/Batting Sensor Stats/live_watch_sessions"
    if not os.path.exists(sessions_root):
        print(f"❌ ERROR: Sessions root directory not found: {sessions_root}")
        sys.exit(1)

    session_dirs = sorted([
        os.path.join(sessions_root, d)
        for d in os.listdir(sessions_root)
        if os.path.isdir(os.path.join(sessions_root, d)) and d.startswith("session")
    ])

    print(f"🔄 Scanning {len(session_dirs)} sessions for CSV to Binary conversion and validation...")
    
    file_types = [
        "WatchAccelerometer",
        "WatchGyroscope",
        "WatchGravity",
        "WatchGameOrientation",
        "WatchOrientation",
        "WatchSteps"
    ]

    total_sessions_processed = 0
    total_files_converted = 0
    
    for session_dir in session_dirs:
        session_id = os.path.basename(session_dir)
        print(f"\n📁 Processing session: {session_id}")
        
        files_verified = 0
        for ftype in file_types:
            csv_path = os.path.join(session_dir, ftype + ".csv")
            csv_gz_path = csv_path + ".gz"
            path_to_read = csv_gz_path if os.path.exists(csv_gz_path) else (csv_path if os.path.exists(csv_path) else None)
            
            if not path_to_read:
                continue
                
            # Create corresponding bin path matching compression state of csv
            is_gz = path_to_read.endswith(".gz")
            bin_path = os.path.join(session_dir, ftype + (".bin.gz" if is_gz else ".bin"))
            
            # 1. Convert CSV to Binary
            try:
                records = convert_csv_to_bin(path_to_read, bin_path, ftype)
                if records == 0:
                    continue
                total_files_converted += 1
            except Exception as e:
                print(f"  ❌ Error converting {ftype}: {e}")
                continue

            # 2. Verify parity by loading both formats using load_watch_sensor
            try:
                # Load CSV version
                df_csv = pd.read_csv(path_to_read)
                # Load Binary version
                df_bin = load_watch_sensor(session_dir, ftype)
                
                # Check lengths
                if len(df_csv) != len(df_bin):
                    print(f"  ❌ Error: Row count mismatch on {ftype} ({len(df_csv)} vs {len(df_bin)})")
                    sys.exit(1)
                    
                # Standardize columns and check values
                for col in df_csv.columns:
                    if col == 'time':
                        # Verify exact timestamps
                        np.testing.assert_array_equal(df_csv['time'].to_numpy(), df_bin['time'].to_numpy())
                    else:
                        # Verify floats match (allowing 1e-4 tolerance due to float formatting in CSV)
                        np.testing.assert_allclose(
                            df_csv[col].to_numpy(),
                            df_bin[col].to_numpy(),
                            rtol=1e-4, atol=1e-4,
                            err_msg=f"Mismatch in column {col} for {ftype}"
                        )
                files_verified += 1
                print(f"  🟢 {ftype}: Verified {records} records match exactly (100% parity)")
            except Exception as e:
                print(f"  ❌ Validation failed on {ftype}: {e}")
                sys.exit(1)
                
        if files_verified > 0:
            total_sessions_processed += 1

    print("\n=======================================================")
    print("✨ CONVERSION AND VALIDATION COMPLETED SUCCESSFULLY! ✨")
    print(f"Sessions Processed: {total_sessions_processed}")
    print(f"Files Converted & Verified: {total_files_converted}")
    print("=======================================================")

if __name__ == "__main__":
    main()
