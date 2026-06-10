import pandas as pd
import numpy as np

gyro_path = "/Users/neilkloot/Code/Batting Sensor Stats/live_watch_sessions/sessions/session-2026-06-05_12-29-59/WatchGyroscope.csv"
df = pd.read_csv(gyro_path)
df['mag'] = np.sqrt(df['x']**2 + df['y']**2 + df['z']**2)

print("=== Total Gyro samples ===")
print(len(df))

# Find local maxima with mag > 1.5
peaks = []
for i in range(1, len(df)-1):
    prev_mag = df.iloc[i-1]['mag']
    curr_mag = df.iloc[i]['mag']
    next_mag = df.iloc[i+1]['mag']
    if curr_mag > 1.5 and curr_mag > prev_mag and curr_mag > next_mag:
        peaks.append({
            'time': df.iloc[i]['seconds_elapsed'],
            'mag': curr_mag,
            'x': df.iloc[i]['x'],
            'y': df.iloc[i]['y'],
            'z': df.iloc[i]['z']
        })

print("\n=== Detected Gyro Peaks (mag > 1.5) ===")
for p in sorted(peaks, key=lambda x: x['time']):
    print(f"Time: {p['time']:.3f}s | Mag: {p['mag']:.3f} | X={p['x']:.2f}, Y={p['y']:.2f}, Z={p['z']:.2f}")
