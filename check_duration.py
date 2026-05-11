import pandas as pd
import subprocess

w_df = pd.read_csv('/Users/neilkloot/Code/Batting Sensor Stats/ground_truth/2026_05_02/Pull shots/Wrist_pull_shots-2026-05-02_02-15-11/WatchGyroscope.csv')
sensor_dur = w_df['seconds_elapsed'].max()
print(f"Sensor duration: {sensor_dur} s")

# Get audio duration using ffprobe or afinfo
result = subprocess.run(['afinfo', '/Users/neilkloot/Code/Batting Sensor Stats/ground_truth/2026_05_02/Pull shots/Pull shots.m4a'], capture_output=True, text=True)
for line in result.stdout.split('\n'):
    if 'estimated duration' in line:
        print(line.strip())

