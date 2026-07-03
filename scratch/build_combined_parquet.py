#!/usr/bin/env python3
import os
import sys
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

BASE_DIR = "/Users/neilkloot/Code/Batting Sensor Stats"
base_live_dir = os.path.join(BASE_DIR, "live_watch_sessions")
parquet_dir = os.path.join(BASE_DIR, "combined_sensor_data.parquet")

sensor_mappings = [
    ("gyro",        "WatchGyroscope.csv"),
    ("accel",       "WatchAccelerometer.csv"),
    ("gravity",     "WatchGravity.csv"),
    ("linacc",      "WatchLinearAcceleration.csv"),
    ("mag",         "WatchMagnetometer.csv"),
    ("game_orient", "WatchGameOrientation.csv"),
    ("orient",      "WatchOrientation.csv"),
    ("steps",       "WatchSteps.csv")
]

def main():
    if not os.path.exists(base_live_dir):
        print(f"❌ ERROR: base live watch sessions directory does not exist: {base_live_dir}")
        sys.exit(1)
        
    sessions = sorted([
        d for d in os.listdir(base_live_dir)
        if d.startswith("session-") and os.path.isdir(os.path.join(base_live_dir, d))
    ])
    
    print(f"🚀 Building combined Parquet database for {len(sessions)} sessions...")
    print(f"📂 Output directory: {parquet_dir}")
    
    os.makedirs(parquet_dir, exist_ok=True)
    
    total_rows = 0
    
    for name, fname in sensor_mappings:
        print(f"\nProcessing sensor type: {name}...")
        sensor_type_dir = os.path.join(parquet_dir, f"sensor_type={name}")
        os.makedirs(sensor_type_dir, exist_ok=True)
        
        sensor_rows = 0
        for session_id in sessions:
            session_dir = os.path.join(base_live_dir, session_id)
            csv_path = os.path.join(session_dir, fname)
            gz_path = csv_path + ".gz"
            
            path_to_load = gz_path if os.path.exists(gz_path) else (csv_path if os.path.exists(csv_path) else None)
            if not path_to_load:
                continue
                
            try:
                df = pd.read_csv(path_to_load)
                if len(df) == 0:
                    continue
                    
                # Add metadata column
                df['session_id'] = session_id
                
                # Convert to PyArrow Table
                table = pa.Table.from_pandas(df, preserve_index=False)
                
                # Write to its partitioned session file
                session_file = os.path.join(sensor_type_dir, f"{session_id}.parquet")
                pq.write_table(table, session_file, compression='snappy')
                
                sensor_rows += len(df)
                total_rows += len(df)
            except Exception as e:
                print(f"  ❌ Error processing {session_id} for {name}: {e}")
                
        print(f"  ✅ Compiled {sensor_rows} rows for {name}")
        
    print(f"\n=================== Combined Parquet Build Complete ===================")
    print(f"📊 Total sensor events compiled: {total_rows:,}")
    print(f"📂 Parquet database size:        {subprocess.run(['du', '-sh', parquet_dir], capture_output=True, text=True).stdout.split()[0]}")
    print(f"=======================================================================")

if __name__ == "__main__":
    import subprocess
    main()
