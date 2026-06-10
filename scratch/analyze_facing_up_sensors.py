import os
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.tree import DecisionTreeClassifier, export_text
from sklearn.model_selection import GridSearchCV

# Session path
session_dir = "/Users/neilkloot/Code/Batting Sensor Stats/live_watch_sessions/sessions/session-2026-05-31_10-06-52"

# 1. Define Labeled Intervals (Facing Up = 1, Walking/Rest/Intro = 0)
# Derived from ground_truth_aligned.csv and energy peaks
stance_windows = [
    (2.99, 12.13),   # Stance 1 -> Swing 1
    (19.89, 23.29),  # Stance 2 -> Swing 2
    (30.79, 34.56),  # Stance 3 -> Swing 3
    (43.40, 46.09),  # Stance 4 -> Swing 4
    (53.79, 57.30)   # Stance 5 -> Swing 5
]

def get_label(t):
    for start, end in stance_windows:
        if start <= t <= end:
            return 1
    return 0

# 2. Load all CSV data files
csv_files = {
    'gyro': 'WatchGyroscope.csv',
    'accel': 'WatchAccelerometer.csv',
    'gravity': 'WatchGravity.csv',
    'linaccel': 'WatchLinearAcceleration.csv',
    'game_orient': 'WatchGameOrientation.csv',
    'baro': 'WatchBarometer.csv',
    'mag': 'WatchMagnetometer.csv',
    'steps': 'WatchSteps.csv'
}

data = {}
for key, fname in csv_files.items():
    path = os.path.join(session_dir, fname)
    if os.path.exists(path):
        data[key] = pd.read_csv(path)
        print(f"Loaded {fname} with {len(data[key])} rows.")
    else:
        data[key] = None
        print(f"⚠️ Warning: {fname} missing.")

# Add magnitude columns
for key in ['gyro', 'accel', 'linaccel', 'mag']:
    df = data[key]
    if df is not None:
        df['mag'] = np.sqrt(df['x']**2 + df['y']**2 + df['z']**2)

# Helper: calculate mean quaternion displacement
def calculate_quat_displacement(q_slice):
    if len(q_slice) < 2:
        return 0.0
    qx = q_slice['qx'].values
    qy = q_slice['qy'].values
    qz = q_slice['qz'].values
    qw = q_slice['qw'].values
    dots = qx[:-1]*qx[1:] + qy[:-1]*qy[1:] + qz[:-1]*qz[1:] + qw[:-1]*qw[1:]
    dots = np.clip(np.abs(dots), -1.0, 1.0)
    angles = np.degrees(2.0 * np.arccos(dots))
    return np.mean(angles)

# 3. Sliding window feature extraction (1.0s window, 100ms step)
min_t = 2.0
max_t = 60.0
time_grid = np.arange(min_t, max_t, 0.1)

features_list = []
labels_list = []

for t in time_grid:
    w_start = t - 1.0
    w_end = t
    
    label = get_label(t)
    features = {'time': t}
    
    # Gyroscope features (1.0s window)
    if data['gyro'] is not None:
        slice_df = data['gyro'][(data['gyro']['seconds_elapsed'] >= w_start) & (data['gyro']['seconds_elapsed'] <= w_end)]
        features['gyro_std'] = np.std(slice_df['mag']) if len(slice_df) >= 2 else 0.0
        features['gyro_mean'] = np.mean(slice_df['mag']) if len(slice_df) > 0 else 0.0
        features['gyro_max'] = np.max(slice_df['mag']) if len(slice_df) > 0 else 0.0
        
    # Accelerometer features (1.0s window)
    if data['accel'] is not None:
        slice_df = data['accel'][(data['accel']['seconds_elapsed'] >= w_start) & (data['accel']['seconds_elapsed'] <= w_end)]
        features['accel_std'] = np.std(slice_df['mag']) if len(slice_df) >= 2 else 0.0
        features['accel_mean'] = np.mean(slice_df['mag']) if len(slice_df) > 0 else 0.0
        features['accel_range'] = (np.max(slice_df['mag']) - np.min(slice_df['mag'])) if len(slice_df) > 0 else 0.0
        
    # Linear Acceleration features (1.0s window)
    if data['linaccel'] is not None:
        slice_df = data['linaccel'][(data['linaccel']['seconds_elapsed'] >= w_start) & (data['linaccel']['seconds_elapsed'] <= w_end)]
        features['linaccel_std'] = np.std(slice_df['mag']) if len(slice_df) >= 2 else 0.0
        features['linaccel_mean'] = np.mean(slice_df['mag']) if len(slice_df) > 0 else 0.0
        features['linaccel_max'] = np.max(slice_df['mag']) if len(slice_df) > 0 else 0.0
        
    # Gravity features (1.0s window)
    if data['gravity'] is not None:
        slice_df = data['gravity'][(data['gravity']['seconds_elapsed'] >= w_start) & (data['gravity']['seconds_elapsed'] <= w_end)]
        features['gravity_y_mean'] = np.mean(slice_df['y']) if len(slice_df) > 0 else 0.0
        features['gravity_z_mean'] = np.mean(slice_df['z']) if len(slice_df) > 0 else 0.0
        
    # Game Orientation features (quaternion angular displacement)
    if data['game_orient'] is not None:
        slice_df = data['game_orient'][(data['game_orient']['seconds_elapsed'] >= w_start) & (data['game_orient']['seconds_elapsed'] <= w_end)]
        features['ori_disp_mean'] = calculate_quat_displacement(slice_df)
        
    # Steps features (2.0s recency window)
    if data['steps'] is not None:
        slice_df = data['steps'][(data['steps']['seconds_elapsed'] >= t - 2.0) & (data['steps']['seconds_elapsed'] <= t)]
        features['steps_count'] = len(slice_df)
    else:
        features['steps_count'] = 0
        
    # Barometer features (1.0s window)
    if data['baro'] is not None:
        slice_df = data['baro'][(data['baro']['seconds_elapsed'] >= w_start) & (data['baro']['seconds_elapsed'] <= w_end)]
        features['baro_std'] = np.std(slice_df['pressure']) if len(slice_df) >= 2 else 0.0
        features['baro_range'] = (np.max(slice_df['pressure']) - np.min(slice_df['pressure'])) if len(slice_df) > 0 else 0.0
        
    # Magnetometer features (1.0s window)
    if data['mag'] is not None:
        slice_df = data['mag'][(data['mag']['seconds_elapsed'] >= w_start) & (data['mag']['seconds_elapsed'] <= w_end)]
        features['mag_std'] = np.std(slice_df['mag']) if len(slice_df) >= 2 else 0.0
        features['mag_mean'] = np.mean(slice_df['mag']) if len(slice_df) > 0 else 0.0
        
    features_list.append(features)
    labels_list.append(label)

df_feat = pd.DataFrame(features_list)
X = df_feat.drop(columns=['time'])
y = np.array(labels_list)

print(f"\nExtracted features dataset: {X.shape[0]} samples, {X.shape[1]} features.")
print(f"Stance locked count: {np.sum(y == 1)}, Stance open count: {np.sum(y == 0)}")

# 4. Feature Importance Analysis
rf = RandomForestClassifier(n_estimators=100, random_state=42)
rf.fit(X, y)

importances = pd.Series(rf.feature_importances_, index=X.columns).sort_values(ascending=False)
print("\n=================== Random Forest Feature Importances ===================")
print(importances.to_string())

# 5. Decision Tree for Rules Extraction
dt = DecisionTreeClassifier(max_depth=3, random_state=42)
dt.fit(X, y)
print("\n=================== Extracted Stance Rules (Decision Tree) ===================")
print(export_text(dt, feature_names=list(X.columns)))

# 6. Grid Search over heuristic threshold bounds
print("Running Grid Search to find optimal thresholds for top wrist & kinematic signals...")
best_f1 = 0
best_config = None

# Grid parameters based on top features
g_stds = np.arange(0.3, 2.0, 0.1)     # Gyro Std threshold
a_stds = np.arange(0.5, 3.5, 0.25)    # Accel Std threshold
o_disps = np.arange(0.3, 3.5, 0.25)   # Ori Disp threshold
g_ys = np.arange(-9.0, -1.0, 0.5)     # Gravity Y threshold (should be <= value)

# We require steps count = 0 as a mandatory kill switch
for g_th in g_stds:
    for a_th in a_stds:
        for o_th in o_disps:
            for gy_th in g_ys:
                # Evaluate condition
                pred = (
                    (X['gyro_std'] < g_th) &
                    (X['accel_std'] < a_th) &
                    (X['ori_disp_mean'] < o_th) &
                    (X['gravity_y_mean'] <= gy_th) &
                    (X['steps_count'] == 0)
                ).astype(int)
                
                tp = np.sum((pred == 1) & (y == 1))
                fp = np.sum((pred == 1) & (y == 0))
                fn = np.sum((pred == 0) & (y == 1))
                tn = np.sum((pred == 0) & (y == 0))
                
                prec = tp / (tp + fp) if (tp + fp) > 0 else 0
                rec = tp / (tp + fn) if (tp + fn) > 0 else 0
                f1 = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0
                
                if f1 > best_f1:
                    best_f1 = f1
                    best_config = {
                        'gyro_std_limit': g_th,
                        'accel_std_limit': a_th,
                        'ori_disp_limit': o_th,
                        'gravity_y_limit': gy_th,
                        'precision': prec,
                        'recall': rec,
                        'f1_score': f1,
                        'tp': tp, 'fp': fp, 'fn': fn, 'tn': tn
                    }

print("\n=================== Best Heuristic Threshold Combination ===================")
for k, v in best_config.items():
    if isinstance(v, float):
        print(f"  {k}: {v:.4f}")
    else:
        print(f"  {k}: {v}")

# 7. Evaluate alternative sensor addition (Linear Acceleration, Barometer, Magnetometer)
# Check if adding Linear Acceleration std or Barometer std improves performance.
print("\n=================== Evaluating Alternative Sensor Extensions ===================")

# Config A: Current Stack (Gyro, Accel, Ori Disp, Gravity Y, Steps)
# Config B: Current Stack + Linear Acceleration (linaccel_std < lin_th)
best_f1_lin = 0
best_lin_config = None
for lin_th in np.arange(0.2, 2.0, 0.1):
    pred = (
        (X['gyro_std'] < best_config['gyro_std_limit']) &
        (X['accel_std'] < best_config['accel_std_limit']) &
        (X['ori_disp_mean'] < best_config['ori_disp_limit']) &
        (X['gravity_y_mean'] <= best_config['gravity_y_limit']) &
        (X['linaccel_std'] < lin_th) &
        (X['steps_count'] == 0)
    ).astype(int)
    tp = np.sum((pred == 1) & (y == 1))
    fp = np.sum((pred == 1) & (y == 0))
    fn = np.sum((pred == 0) & (y == 1))
    prec = tp / (tp + fp) if (tp + fp) > 0 else 0
    rec = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0
    if f1 > best_f1_lin:
        best_f1_lin = f1
        best_lin_config = {'threshold': lin_th, 'f1': f1, 'precision': prec, 'recall': rec}

print(f"Adding Linear Acceleration Std limit (linaccel_std < {best_lin_config['threshold']:.2f}):")
print(f"  F1 Score: {best_lin_config['f1']:.4f} (Diff: {best_lin_config['f1'] - best_config['f1_score']:.4f})")
print(f"  Precision: {best_lin_config['precision']:.4f}, Recall: {best_lin_config['recall']:.4f}")

# Config C: Current Stack + Barometer std (baro_std < baro_th)
best_f1_baro = 0
best_baro_config = None
for baro_th in np.arange(0.01, 0.2, 0.01):
    pred = (
        (X['gyro_std'] < best_config['gyro_std_limit']) &
        (X['accel_std'] < best_config['accel_std_limit']) &
        (X['ori_disp_mean'] < best_config['ori_disp_limit']) &
        (X['gravity_y_mean'] <= best_config['gravity_y_limit']) &
        (X['baro_std'] < baro_th) &
        (X['steps_count'] == 0)
    ).astype(int)
    tp = np.sum((pred == 1) & (y == 1))
    fp = np.sum((pred == 1) & (y == 0))
    fn = np.sum((pred == 0) & (y == 1))
    prec = tp / (tp + fp) if (tp + fp) > 0 else 0
    rec = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0
    if f1 > best_f1_baro:
        best_f1_baro = f1
        best_baro_config = {'threshold': baro_th, 'f1': f1, 'precision': prec, 'recall': rec}

print(f"Adding Barometer Pressure Std limit (baro_std < {best_baro_config['threshold']:.3f}):")
print(f"  F1 Score: {best_baro_config['f1']:.4f} (Diff: {best_baro_config['f1'] - best_config['f1_score']:.4f})")
print(f"  Precision: {best_baro_config['precision']:.4f}, Recall: {best_baro_config['recall']:.4f}")
