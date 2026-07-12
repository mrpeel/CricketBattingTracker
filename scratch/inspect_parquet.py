import pyarrow.parquet as pq
import os

parquet_path = "/Users/neilkloot/Code/Batting Sensor Stats/combined_sensor_data.parquet"
if os.path.exists(parquet_path):
    dataset = pq.ParquetDataset(parquet_path)
    print("Files in dataset:", len(dataset.files))
    if len(dataset.files) > 0:
        meta = pq.read_metadata(dataset.files[0])
        print("Schema:", meta.schema)
else:
    print("Parquet path not found")
