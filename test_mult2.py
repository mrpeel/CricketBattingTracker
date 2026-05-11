import pandas as pd
df = pd.read_csv('/Users/neilkloot/Code/Batting Sensor Stats/analysis_outputs/ground_truth_labeled_shots.csv')
df = df.dropna(subset=['bat_true_speed_kmh', 'wrist_gyro_mag'])

df = df[df['bat_true_speed_kmh'] > 20.0]

df['ideal_speed'] = df['bat_true_speed_kmh']
# Use the exact formula in sync_ground_truth.py: w_mag * 0.645 * 3.6 * 1.10
df['base_speed'] = df['wrist_gyro_mag'] * 0.645 * 3.6
df['ideal_snap'] = df['ideal_speed'] / df['base_speed']

for cat in df['shot_category'].unique():
    subset = df[df['shot_category'] == cat]
    print(f"{cat}: Ideal Snap Multiplier = {subset['ideal_snap'].median():.2f} (mean {subset['ideal_snap'].mean():.2f})")

