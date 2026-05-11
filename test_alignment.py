import pandas as pd
import numpy as np
from scipy.signal import find_peaks

w_df = pd.read_csv('/Users/neilkloot/Code/Batting Sensor Stats/ground_truth/2026_05_02/Cover drives /Wrist_cover_drives-2026-05-02_02-40-41/WatchGyroscope.csv')
w_df['mag'] = np.sqrt(w_df['x']**2 + w_df['y']**2 + w_df['z']**2)

peak_indices, _ = find_peaks(w_df['mag'], height=10.0, distance=200)
peaks = w_df.iloc[peak_indices].copy()

print(f"Number of peaks > 10.0 rad/s: {len(peaks)}")
print("Peak times:")
for _, row in peaks.iterrows():
    print(f"{row['seconds_elapsed']:.2f}s (Mag: {row['mag']:.1f})")

