#!/usr/bin/env python3
import os
import sys
import argparse
import numpy as np
import pandas as pd

def main():
    parser = argparse.ArgumentParser(description="Export little-endian binary telemetry files (.bin/.bin.gz) to standard human-readable CSVs.")
    parser.add_argument("--session-dir", required=True, help="Path to the session directory containing binary files.")
    parser.add_argument("--output-dir", help="Optional output directory. Defaults to the same session directory.")
    args = parser.parse_args()

    session_dir = args.session_dir
    output_dir = args.output_dir if args.output_dir else session_dir

    if not os.path.isdir(session_dir):
        print(f"❌ ERROR: Session directory does not exist: {session_dir}")
        sys.exit(1)

    os.makedirs(output_dir, exist_ok=True)
    
    bin_files = []
    for f in os.listdir(session_dir):
        if f.endswith(".bin") or f.endswith(".bin.gz"):
            bin_files.append(f)

    if not bin_files:
        print("⚠️ No binary files (.bin or .bin.gz) found in the session directory.")
        sys.exit(0)

    print(f"📂 Found {len(bin_files)} binary files. Exporting to human-readable CSV...")

    for fname in bin_files:
        bin_path = os.path.join(session_dir, fname)
        base_name = fname.replace(".bin.gz", "").replace(".bin", "")
        csv_path = os.path.join(output_dir, base_name + ".csv")
        
        # Load the binary data using little-endian structured NumPy dtypes
        import gzip
        try:
            if bin_path.endswith(".gz"):
                with gzip.open(bin_path, "rb") as f:
                    raw_bytes = f.read()
            else:
                with open(bin_path, "rb") as f:
                    raw_bytes = f.read()
            
            if "GameOrientation" in base_name or "Orientation" in base_name:
                dtype = np.dtype([
                    ('time', '<i8'),
                    ('seconds_elapsed', '<f4'),
                    ('qx', '<f4'),
                    ('qy', '<f4'),
                    ('qz', '<f4'),
                    ('qw', '<f4')
                ])
                header = ["time", "seconds_elapsed", "qx", "qy", "qz", "qw"]
            elif "Steps" in base_name and "StepCounter" not in base_name:
                dtype = np.dtype([
                    ('time', '<i8'),
                    ('seconds_elapsed', '<f4')
                ])
                header = ["time", "seconds_elapsed"]
            elif "HeartRate" in base_name:
                dtype = np.dtype([
                    ('time', '<i8'),
                    ('seconds_elapsed', '<f4'),
                    ('bpm', '<f4')
                ])
                header = ["time", "seconds_elapsed", "bpm"]
            elif "Barometer" in base_name:
                dtype = np.dtype([
                    ('time', '<i8'),
                    ('seconds_elapsed', '<f4'),
                    ('pressure', '<f4')
                ])
                header = ["time", "seconds_elapsed", "pressure"]
            elif "StepCounter" in base_name:
                dtype = np.dtype([
                    ('time', '<i8'),
                    ('seconds_elapsed', '<f4'),
                    ('steps', '<f4')
                ])
                header = ["time", "seconds_elapsed", "steps"]
            else:
                dtype = np.dtype([
                    ('time', '<i8'),
                    ('seconds_elapsed', '<f4'),
                    ('x', '<f4'),
                    ('y', '<f4'),
                    ('z', '<f4')
                ])
                header = ["time", "seconds_elapsed", "x", "y", "z"]

            rec_size = dtype.itemsize
            num_recs = len(raw_bytes) // rec_size
            valid_bytes = raw_bytes[:num_recs * rec_size]
            
            arr = np.frombuffer(valid_bytes, dtype=dtype)
            df = pd.DataFrame(arr)
            df['time'] = df['time'].astype('int64')
            
            # Format elapsed floats to 6 decimals for matching original format standard
            float_cols = [col for col in df.columns if col != 'time']
            for col in float_cols:
                df[col] = df[col].map(lambda val: round(float(val), 6))
                
            df.to_csv(csv_path, index=False)
            print(f"  Exported: {fname} ➔ {os.path.basename(csv_path)} ({len(df)} records)")
        except Exception as e:
            print(f"  ❌ Failed to export {fname}: {e}")

    print("✅ Export completed successfully.")

if __name__ == "__main__":
    main()
