import pandas as pd
df = pd.read_csv('/Users/neilkloot/Code/Batting Sensor Stats/analysis_outputs/ground_truth_labeled_shots.csv')
df = df.dropna(subset=['bat_true_speed_kmh', 'wrist_gyro_mag'])

# Ignore misses and anomalies where bat speed is tiny
df = df[df['bat_true_speed_kmh'] > 20.0]

df['ideal_speed'] = df['bat_true_speed_kmh']
df['base_speed_no_snap'] = df['wrist_gyro_mag'] * 0.8 * 3.6
df['ideal_snap'] = df['ideal_speed'] / df['base_speed_no_snap']

for cat in df['shot_category'].unique():
    subset = df[df['shot_category'] == cat]
    print(f"{cat}: Ideal Snap Multiplier = {subset['ideal_snap'].median():.2f} (mean {subset['ideal_snap'].mean():.2f})")

