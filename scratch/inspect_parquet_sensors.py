import pyarrow.parquet as pq
import os

parquet_path = "/Users/neilkloot/Code/Batting Sensor Stats/combined_sensor_data.parquet"
for sensor_name in ["gyro", "accel", "game_orient", "gravity"]:
    sensor_dir = os.path.join(parquet_path, f"sensor_type={sensor_name}")
    if os.path.exists(sensor_dir):
        files = [f for f in os.listdir(sensor_dir) if f.endswith(".parquet")]
        if files:
            meta = pq.read_metadata(os.path.join(sensor_dir, files[0]))
            print(f"Sensor: {sensor_name}, Columns: {meta.schema.names}")
