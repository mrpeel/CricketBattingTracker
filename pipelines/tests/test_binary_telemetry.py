import os
import unittest
import numpy as np
import pandas as pd
import tempfile
import struct
import shutil

# Add parent dir to path so we can import automate_pipeline
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from automate_pipeline import load_watch_sensor

class TestBinaryTelemetry(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_imu_binary_write_and_read(self):
        # Create dummy little-endian structured records
        # Layout: Long (time), Float (sec), Float (x), Float (y), Float (z)
        ts = 1718392182000
        sec = 1.234
        x, y, z = 9.81, -0.15, 1.56
        
        bin_path = os.path.join(self.temp_dir, "WatchAccelerometer.bin")
        with open(bin_path, "wb") as f:
            f.write(struct.pack("<qffff", ts, sec, x, y, z))
            
        df = load_watch_sensor(self.temp_dir, "WatchAccelerometer")
        self.assertFalse(df.empty)
        self.assertEqual(len(df), 1)
        self.assertEqual(df.iloc[0]['time'], ts)
        self.assertAlmostEqual(df.iloc[0]['seconds_elapsed'], sec, places=5)
        self.assertAlmostEqual(df.iloc[0]['x'], x, places=5)
        self.assertAlmostEqual(df.iloc[0]['y'], y, places=5)
        self.assertAlmostEqual(df.iloc[0]['z'], z, places=5)

    def test_orientation_binary_write_and_read(self):
        # Layout: Long, Float, Float, Float, Float, Float
        ts = 1718392183000
        sec = 2.345
        qx, qy, qz, qw = 0.707, 0.0, 0.0, 0.707
        
        bin_path = os.path.join(self.temp_dir, "WatchGameOrientation.bin")
        with open(bin_path, "wb") as f:
            f.write(struct.pack("<qfffff", ts, sec, qx, qy, qz, qw))
            
        df = load_watch_sensor(self.temp_dir, "WatchGameOrientation")
        self.assertFalse(df.empty)
        self.assertEqual(len(df), 1)
        self.assertEqual(df.iloc[0]['time'], ts)
        self.assertAlmostEqual(df.iloc[0]['seconds_elapsed'], sec, places=5)
        self.assertAlmostEqual(df.iloc[0]['qx'], qx, places=5)
        self.assertAlmostEqual(df.iloc[0]['qy'], qy, places=5)
        self.assertAlmostEqual(df.iloc[0]['qz'], qz, places=5)
        self.assertAlmostEqual(df.iloc[0]['qw'], qw, places=5)

    def test_steps_binary_write_and_read(self):
        # Layout: Long, Float
        ts = 1718392184000
        sec = 3.456
        
        bin_path = os.path.join(self.temp_dir, "WatchSteps.bin")
        with open(bin_path, "wb") as f:
            f.write(struct.pack("<qf", ts, sec))
            
        df = load_watch_sensor(self.temp_dir, "WatchSteps")
        self.assertFalse(df.empty)
        self.assertEqual(len(df), 1)
        self.assertEqual(df.iloc[0]['time'], ts)
        self.assertAlmostEqual(df.iloc[0]['seconds_elapsed'], sec, places=5)

    def test_corrupt_truncated_file(self):
        # Write 1.5 samples of accelerometer (36 bytes total: 24 byte sample + 12 byte garbage)
        bin_path = os.path.join(self.temp_dir, "WatchAccelerometer.bin")
        with open(bin_path, "wb") as f:
            f.write(struct.pack("<qffff", 1000, 0.1, 1.0, 2.0, 3.0))
            f.write(struct.pack("<qf", 2000, 0.2)) # Truncated
            
        df = load_watch_sensor(self.temp_dir, "WatchAccelerometer")
        self.assertEqual(len(df), 1) # Only 1 complete record should parse
        self.assertEqual(df.iloc[0]['time'], 1000)

if __name__ == "__main__":
    unittest.main()
