#!/usr/bin/env python3
import os
import time
import pandas as pd

PARQUET_PATH = "/Users/neilkloot/Code/Batting Sensor Stats/combined_sensor_data.parquet"

def test_sensor(name):
    sensor_dir = os.path.join(PARQUET_PATH, f"sensor_type={name}")
    if not os.path.exists(sensor_dir):
        print(f"⚠️ Sensor type '{name}' not found in Parquet directory.")
        return
        
    print(f"\n⏱️ Loading complete '{name}' sensor dataset across all sessions...")
    start_time = time.time()
    
    # Load all sessions for this sensor in one call
    df = pd.read_parquet(sensor_dir)
    
    end_time = time.time()
    elapsed = end_time - start_time
    
    print(f"📊 Rows loaded:   {len(df):,}")
    print(f"📦 Memory usage:  {df.memory_usage(deep=True).sum() / 1024 / 1024:.2f} MB")
    print(f"⏱️ Loading time:  {elapsed:.3f} seconds")
    
    # Show sample data
    print("\nSample Data:")
    print(df.head(3))
    print("...")

def main():
    if not os.path.exists(PARQUET_PATH):
        print(f"❌ ERROR: Parquet database directory does not exist: {PARQUET_PATH}")
        return
        
    test_sensor("gyro")
    test_sensor("game_orient")

if __name__ == "__main__":
    main()
