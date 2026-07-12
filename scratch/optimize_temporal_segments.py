#!/usr/bin/env python3
import os
import sys
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import accuracy_score

# ─── Configuration ────────────────────────────────────────────────────────────
BASE_DIR = "/Users/neilkloot/Code/Batting Sensor Stats"
PARQUET_DIR = os.path.join(BASE_DIR, "combined_sensor_data.parquet")
GT_ALIGNED_CSV = os.path.join(BASE_DIR, "combined_ground_truth_aligned.csv")

V_LOCAL = np.array([0.0, -1.0, 0.0])  # bat forearm unit vector

# ─── Quaternion math (exact port from SwingDetector.kt) ──────────────────────
def multiply_quats(q1, q2):
    x1, y1, z1, w1 = q1
    x2, y2, z2, w2 = q2
    return np.array([
        w1*x2 + x1*w2 + y1*z2 - z1*y2,
        w1*y2 - x1*z2 + y1*w2 + z1*x2,
        w1*z2 + x1*y2 - y1*x2 + z1*w2,
        w1*w2 - x1*x2 - y1*y2 - z1*z2,
    ])

def conjugate_quat(q):
    return np.array([-q[0], -q[1], -q[2], q[3]])

def rotate_vector(q, v):
    qx, qy, qz, qw = q
    vx, vy, vz = v
    tx = 2.0 * (qy*vz - qz*vy)
    ty = 2.0 * (qz*vx - qx*vz)
    tz = 2.0 * (qx*vy - qy*vx)
    return np.array([
        vx + qw*tx + (qy*tz - qz*ty),
        vy + qw*ty + (qz*tx - qx*tz),
        vz + qw*tz + (qx*ty - qy*tx),
    ])

def calc_relative_roll(q):
    x, y, z, w = q
    return np.degrees(np.arctan2(2.0 * (w*y + x*z), 1.0 - 2.0 * (y*y + z*z)))

def average_quats(qx_arr, qy_arr, qz_arr, qw_arr):
    if len(qx_arr) == 0:
        return np.array([0, 0, 0, 1.0])
    q0 = np.array([qx_arr[0], qy_arr[0], qz_arr[0], qw_arr[0]])
    s = q0.copy()
    for i in range(1, len(qx_arr)):
        qi = np.array([qx_arr[i], qy_arr[i], qz_arr[i], qw_arr[i]])
        dot = np.dot(q0, qi)
        sign = 1.0 if dot >= 0 else -1.0
        s += sign * qi
    norm = np.linalg.norm(s)
    return s / norm if norm > 0 else np.array([0, 0, 0, 1.0])

# ─── Load sensor data from Parquet ───────────────────────────────────────────
def load_parquet_sensors(session_id):
    sensors = {}
    for name in ["gyro", "accel", "gravity", "game_orient", "orient", "mag"]:
        path = os.path.join(PARQUET_DIR, f"sensor_type={name}", f"{session_id}.parquet")
        if os.path.exists(path):
            try:
                df = pd.read_parquet(path)
                if len(df) > 0:
                    sensors[name] = df
            except Exception:
                pass
    
    # Calculate vector magnitudes
    for name in ["gyro", "accel", "gravity", "mag"]:
        if name in sensors:
            df = sensors[name]
            df['mag_total'] = np.sqrt(df['x']**2 + df['y']**2 + df['z']**2)
            
    return sensors

def main():
    if not os.path.exists(GT_ALIGNED_CSV):
        print(f"❌ ERROR: {GT_ALIGNED_CSV} not found.")
        return
        
    df_gt = pd.read_csv(GT_ALIGNED_CSV)
    df_swings_gt = df_gt[(df_gt['normalized_gt'] != 'NON-SWING') & (df_gt['session_date'] != 'synthetic')].copy()
    
    print(f"🎬 Caching raw sensor sequences for {len(df_swings_gt)} real-world shots...")
    
    session_sensor_cache = {}
    shot_data_cache = []
    
    for idx, row in df_swings_gt.iterrows():
        session_id = row['session_id']
        t_shot = float(row['impact_time_seconds'])
        shot_class = row['normalized_gt']
        
        if session_id not in session_sensor_cache:
            session_sensor_cache[session_id] = load_parquet_sensors(session_id)
            
        sensors = session_sensor_cache[session_id]
        if not sensors or "gyro" not in sensors:
            continue
            
        orient = sensors.get("game_orient", sensors.get("orient"))
        
        q_stance = np.array([0, 0, 0, 1.0])
        if orient is not None:
            stance_ori = orient[(orient['seconds_elapsed'] >= t_shot - 3.0) & 
                                (orient['seconds_elapsed'] <= t_shot - 1.5)]
            if len(stance_ori) >= 2:
                q_stance = average_quats(stance_ori['qx'].values, stance_ori['qy'].values, 
                                         stance_ori['qz'].values, stance_ori['qw'].values)
        
        q_stance_inv = conjugate_quat(q_stance)
        
        t_start_cache = t_shot - 1.5
        t_end_cache = t_shot + 0.6
        
        shot_sensors = {}
        for name in ["gyro", "accel", "gravity", "mag"]:
            df_s = sensors.get(name)
            if df_s is not None:
                sub = df_s[(df_s['seconds_elapsed'] >= t_start_cache) & (df_s['seconds_elapsed'] <= t_end_cache)].copy()
                shot_sensors[name] = sub
                
        if orient is not None:
            sub_ori = orient[(orient['seconds_elapsed'] >= t_start_cache) & (orient['seconds_elapsed'] <= t_end_cache)].copy()
            rot_xs, rot_zs, times = [], [], []
            for _, o_row in sub_ori.iterrows():
                q_curr = np.array([o_row['qx'], o_row['qy'], o_row['qz'], o_row['qw']])
                q_rel = multiply_quats(q_stance_inv, q_curr)
                v_rot = rotate_vector(q_rel, V_LOCAL)
                rot_xs.append(v_rot[0])
                rot_zs.append(v_rot[2])
                times.append(o_row['seconds_elapsed'])
            shot_sensors["orient_rotated"] = pd.DataFrame({
                'seconds_elapsed': times,
                'rx': rot_xs,
                'rz': rot_zs,
                'qx': sub_ori['qx'].values,
                'qy': sub_ori['qy'].values,
                'qz': sub_ori['qz'].values,
                'qw': sub_ori['qw'].values
            })
            
        shot_data_cache.append({
            't_shot': t_shot,
            'shot_class': shot_class,
            'sensors': shot_sensors,
            'q_stance_inv': q_stance_inv
        })
        
    print(f"✅ Pre-computation complete. Sweeping temporal configurations (N=2, 3, 4 segments)...")
    
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    y = np.array([s['shot_class'] for s in shot_data_cache])
    
    grid_results = []
    
    # Pre-extract displacement and roll helper
    def extract_segment_features(s, bounds):
        t_shot = s['t_shot']
        sensors = s['sensors']
        q_inv = s['q_stance_inv']
        gyro = sensors.get("gyro")
        grav = sensors.get("gravity")
        ori_rot = sensors.get("orient_rotated")
        
        feats = {}
        
        for i in range(len(bounds) - 1):
            t_s, t_e = bounds[i], bounds[i+1]
            prefix = f"s{i+1}"
            
            # Displacement features
            dx, dz = 0.0, 0.0
            if ori_rot is not None:
                sub = ori_rot[(ori_rot['seconds_elapsed'] >= t_shot + t_s) & 
                              (ori_rot['seconds_elapsed'] <= t_shot + t_e)]
                if len(sub) >= 2:
                    dx = sub['rx'].max() - sub['rx'].min()
                    dz = sub['rz'].max() - sub['rz'].min()
            feats[f"{prefix}_deltaX"] = dx
            feats[f"{prefix}_deltaZ"] = dz
            feats[f"{prefix}_planeRatio"] = dx / dz if dz > 0 else 0.0
            
            # Gyro stats
            gyro_mag_max = 0.0
            gyro_y_std = 0.0
            gyro_y_min = 0.0
            if gyro is not None:
                sub = gyro[(gyro['seconds_elapsed'] >= t_shot + t_s) & 
                           (gyro['seconds_elapsed'] <= t_shot + t_e)]
                if len(sub) > 0:
                    gyro_mag_max = sub['mag_total'].max()
                    gyro_y_min = sub['y'].min()
                    if len(sub) >= 2:
                        gyro_y_std = float(np.std(sub['y'].values))
            feats[f"{prefix}_gyroMag"] = gyro_mag_max
            feats[f"{prefix}_gyro_y_std"] = gyro_y_std
            feats[f"{prefix}_gyro_y_min"] = gyro_y_min
            
            # Gravity stats
            grav_y_mean = -9.8
            if grav is not None:
                sub = grav[(grav['seconds_elapsed'] >= t_shot + t_s) & 
                           (grav['seconds_elapsed'] <= t_shot + t_e)]
                if len(sub) > 0:
                    grav_y_mean = sub['y'].mean()
            feats[f"{prefix}_grav_y_mean"] = grav_y_mean
            
            # Roll/Yaw at split point (end of this segment)
            if ori_rot is not None:
                impact_sub = ori_rot[(ori_rot['seconds_elapsed'] >= t_shot + t_e - 0.05) & 
                                     (ori_rot['seconds_elapsed'] <= t_shot + t_e + 0.05)]
                if len(impact_sub) > 0:
                    row = impact_sub.iloc[0]
                    q_rel = multiply_quats(q_inv, np.array([row['qx'], row['qy'], row['qz'], row['qw']]))
                    feats[f"{prefix}_roll"] = calc_relative_roll(q_rel)
                    v_rot = rotate_vector(q_rel, V_LOCAL)
                    feats[f"{prefix}_yaw"] = np.degrees(np.arctan2(v_rot[0], -v_rot[1]))
                else:
                    feats[f"{prefix}_roll"] = 0.0
                    feats[f"{prefix}_yaw"] = 0.0
            else:
                feats[f"{prefix}_roll"] = 0.0
                feats[f"{prefix}_yaw"] = 0.0
                
        return feats

    # ─── 1. Evaluate N=2 Segments ──────────────────────────────────────────────
    print("\n--- Sweeping N=2 Segments ---")
    t_start_grid = [-1.2, -1.0, -0.8]
    t_split1_grid = [-0.4, -0.2, 0.0]
    t_end_grid = [0.3, 0.4, 0.5]
    
    for t_s in t_start_grid:
        for t_sp1 in t_split1_grid:
            for t_e in t_end_grid:
                bounds = [t_s, t_sp1, t_e]
                X_feats = [extract_segment_features(s, bounds) for s in shot_data_cache]
                df_X = pd.DataFrame(X_feats).fillna(0.0)
                
                accs = []
                for train_idx, test_idx in cv.split(df_X, y):
                    clf = RandomForestClassifier(n_estimators=50, max_depth=8, class_weight='balanced_subsample', random_state=42, n_jobs=-1)
                    clf.fit(df_X.iloc[train_idx], y[train_idx])
                    accs.append(accuracy_score(y[test_idx], clf.predict(df_X.iloc[test_idx])))
                grid_results.append({'N': 2, 'bounds': bounds, 'accuracy': np.mean(accs)})

    # ─── 2. Evaluate N=3 Segments ──────────────────────────────────────────────
    print("--- Sweeping N=3 Segments ---")
    t_start_grid = [-1.0, -0.8]
    t_split1_grid = [-0.4, -0.3, -0.2]
    t_split2_grid = [-0.05, 0.0, 0.05]
    t_end_grid = [0.3, 0.4, 0.5]
    
    for t_s in t_start_grid:
        for t_sp1 in t_split1_grid:
            for t_sp2 in t_split2_grid:
                for t_e in t_end_grid:
                    bounds = [t_s, t_sp1, t_sp2, t_e]
                    X_feats = [extract_segment_features(s, bounds) for s in shot_data_cache]
                    df_X = pd.DataFrame(X_feats).fillna(0.0)
                    
                    accs = []
                    for train_idx, test_idx in cv.split(df_X, y):
                        clf = RandomForestClassifier(n_estimators=50, max_depth=8, class_weight='balanced_subsample', random_state=42, n_jobs=-1)
                        clf.fit(df_X.iloc[train_idx], y[train_idx])
                        accs.append(accuracy_score(y[test_idx], clf.predict(df_X.iloc[test_idx])))
                    grid_results.append({'N': 3, 'bounds': bounds, 'accuracy': np.mean(accs)})

    # ─── 3. Evaluate N=4 Segments ──────────────────────────────────────────────
    print("--- Sweeping N=4 Segments ---")
    t_start_grid = [-1.0, -0.8]
    t_split1_grid = [-0.5, -0.3]
    t_split2_grid = [-0.2, -0.1]
    t_split3_grid = [0.0, 0.1]
    t_end_grid = [0.3, 0.5]
    
    for t_s in t_start_grid:
        for t_sp1 in t_split1_grid:
            for t_sp2 in t_split2_grid:
                for t_sp3 in t_split3_grid:
                    for t_e in t_end_grid:
                        bounds = [t_s, t_sp1, t_sp2, t_sp3, t_e]
                        X_feats = [extract_segment_features(s, bounds) for s in shot_data_cache]
                        df_X = pd.DataFrame(X_feats).fillna(0.0)
                        
                        accs = []
                        for train_idx, test_idx in cv.split(df_X, y):
                            clf = RandomForestClassifier(n_estimators=50, max_depth=8, class_weight='balanced_subsample', random_state=42, n_jobs=-1)
                            clf.fit(df_X.iloc[train_idx], y[train_idx])
                            accs.append(accuracy_score(y[test_idx], clf.predict(df_X.iloc[test_idx])))
                        grid_results.append({'N': 4, 'bounds': bounds, 'accuracy': np.mean(accs)})

    df_res = pd.DataFrame(grid_results).sort_values(by='accuracy', ascending=False)
    
    print("\n========================================================")
    print("TOP 10 SEGMENT COUNT CONFIGURATIONS (REAL DATA CV)")
    print("========================================================")
    for idx, row in df_res.head(10).reset_index().iterrows():
        b_str = ", ".join(f"{b:.2f}s" for b in row['bounds'])
        print(f"Rank {idx+1:2d} | N={row['N']} | Bounds: [{b_str}] -> Acc: {row['accuracy']*100:.2f}%")
    print("========================================================\n")
    
    best = df_res.iloc[0]
    best_b_str = ", ".join(f"{b:.2f}s" for b in best['bounds'])
    print(f"🏆 Best Configuration: N={best['N']} segments, Bounds: [{best_b_str}] with Accuracy: {best['accuracy']*100:.2f}%")

if __name__ == "__main__":
    main()
