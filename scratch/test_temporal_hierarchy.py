#!/usr/bin/env python3
import os
import sys
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import classification_report, accuracy_score

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

# ─── Segmented Feature Extraction ────────────────────────────────────────────
def extract_segmented_features(sensors, t_shot):
    feats = {}
    
    # Identify orientation dataframe
    orient = sensors.get("game_orient", sensors.get("orient"))
    
    # Compute stance reference quaternion
    q_stance = np.array([0, 0, 0, 1.0])
    if orient is not None:
        stance_ori = orient[(orient['seconds_elapsed'] >= t_shot - 3.0) & 
                            (orient['seconds_elapsed'] <= t_shot - 1.5)]
        if len(stance_ori) >= 2:
            q_stance = average_quats(stance_ori['qx'].values, stance_ori['qy'].values, 
                                     stance_ori['qz'].values, stance_ori['qw'].values)
                                     
    q_stance_inv = conjugate_quat(q_stance)
    
    # Helper to calculate deltaX and deltaZ for a specific time range
    def get_displacement_feats(t_start, t_end, prefix):
        if orient is None:
            return {f"{prefix}_deltaX": 0.0, f"{prefix}_deltaZ": 0.0}
        sub = orient[(orient['seconds_elapsed'] >= t_start) & (orient['seconds_elapsed'] <= t_end)]
        if len(sub) >= 2:
            min_x, max_x = 1e10, -1e10
            min_z, max_z = 1e10, -1e10
            for _, row in sub.iterrows():
                q_curr = np.array([row['qx'], row['qy'], row['qz'], row['qw']])
                q_rel = multiply_quats(q_stance_inv, q_curr)
                v_rot = rotate_vector(q_rel, V_LOCAL)
                if v_rot[0] < min_x: min_x = v_rot[0]
                if v_rot[0] > max_x: max_x = v_rot[0]
                if v_rot[2] < min_z: min_z = v_rot[2]
                if v_rot[2] > max_z: max_z = v_rot[2]
            return {
                f"{prefix}_deltaX": max_x - min_x,
                f"{prefix}_deltaZ": max_z - min_z
            }
        return {f"{prefix}_deltaX": 0.0, f"{prefix}_deltaZ": 0.0}

    # ─── Segment 1: Footwork [-0.8s, -0.3s] ───────────────────────────────
    t1_start, t1_end = t_shot - 0.8, t_shot - 0.3
    s1_feats = {}
    
    # Gyro/Accel Stds in Seg 1
    for s_name in ["gyro", "accel"]:
        df_s = sensors.get(s_name)
        if df_s is not None:
            sub = df_s[(df_s['seconds_elapsed'] >= t1_start) & (df_s['seconds_elapsed'] <= t1_end)]
            if len(sub) >= 2:
                s1_feats[f"seg1_{s_name}_x_std"] = float(np.std(sub['x'].values))
                s1_feats[f"seg1_{s_name}_y_std"] = float(np.std(sub['y'].values))
                s1_feats[f"seg1_{s_name}_z_std"] = float(np.std(sub['z'].values))
            else:
                s1_feats[f"seg1_{s_name}_x_std"] = 0.0
                s1_feats[f"seg1_{s_name}_y_std"] = 0.0
                s1_feats[f"seg1_{s_name}_z_std"] = 0.0
        else:
            s1_feats[f"seg1_{s_name}_x_std"] = 0.0
            s1_feats[f"seg1_{s_name}_y_std"] = 0.0
            s1_feats[f"seg1_{s_name}_z_std"] = 0.0
            
    # Displacement in Seg 1
    s1_feats.update(get_displacement_feats(t1_start, t1_end, "seg1"))
    
    # ─── Segment 2: Intent & Height [-0.3s, 0.0s] ─────────────────────────
    t2_start, t2_end = t_shot - 0.3, t_shot
    s2_feats = {}
    
    # Gyro/Accel Max/Mean in Seg 2
    gyro = sensors.get("gyro")
    if gyro is not None:
        sub = gyro[(gyro['seconds_elapsed'] >= t2_start) & (gyro['seconds_elapsed'] <= t2_end)]
        s2_feats["seg2_gyroMag"] = sub['mag_total'].max() if len(sub) > 0 else 0.0
    else:
        s2_feats["seg2_gyroMag"] = 0.0
        
    accel = sensors.get("accel")
    if accel is not None:
        sub = accel[(accel['seconds_elapsed'] >= t2_start) & (accel['seconds_elapsed'] <= t2_end)]
        s2_feats["seg2_accel_mag_max"] = sub['mag_total'].max() if len(sub) > 0 else 0.0
    else:
        s2_feats["seg2_accel_mag_max"] = 0.0
        
    # Gravity Y/Z mean in Seg 2 (torso lean/arm extension)
    grav = sensors.get("gravity")
    if grav is not None:
        sub = grav[(grav['seconds_elapsed'] >= t2_start) & (grav['seconds_elapsed'] <= t2_end)]
        if len(sub) >= 2:
            s2_feats["seg2_grav_y_mean"] = sub['y'].mean()
            s2_feats["seg2_grav_z_mean"] = sub['z'].mean()
            s2_feats["seg2_grav_x_max"] = sub['x'].max()
        else:
            s2_feats["seg2_grav_y_mean"] = -9.8
            s2_feats["seg2_grav_z_mean"] = 0.0
            s2_feats["seg2_grav_x_max"] = 0.0
    else:
        s2_feats["seg2_grav_y_mean"] = -9.8
        s2_feats["seg2_grav_z_mean"] = 0.0
        s2_feats["seg2_grav_x_max"] = 0.0
        
    s2_feats.update(get_displacement_feats(t2_start, t2_end, "seg2"))
    
    # ─── Segment 3: Shot Selection [0.0s, +0.3s] ──────────────────────────
    t3_start, t3_end = t_shot, t_shot + 0.3
    s3_feats = {}
    
    # Roll and Yaw at Impact
    if orient is not None:
        impact_ori = orient[(orient['seconds_elapsed'] >= t_shot - 0.05) & 
                            (orient['seconds_elapsed'] <= t_shot + 0.05)]
        if len(impact_ori) == 0:
            impact_ori = orient.iloc[(orient['seconds_elapsed'] - t_shot).abs().argsort()[:1]]
        if len(impact_ori) > 0:
            row = impact_ori.iloc[0]
            q_impact = np.array([row['qx'], row['qy'], row['qz'], row['qw']])
            q_rel = multiply_quats(q_stance_inv, q_impact)
            s3_feats['seg3_rollImpactDeg'] = calc_relative_roll(q_rel)
            v_rot = rotate_vector(q_rel, V_LOCAL)
            s3_feats['seg3_yawImpactDeg'] = np.degrees(np.arctan2(v_rot[0], -v_rot[1]))
        else:
            s3_feats['seg3_rollImpactDeg'] = 0.0
            s3_feats['seg3_yawImpactDeg'] = 0.0
    else:
        s3_feats['seg3_rollImpactDeg'] = 0.0
        s3_feats['seg3_yawImpactDeg'] = 0.0
        
    # Gyro min/max in Seg 3
    if gyro is not None:
        sub = gyro[(gyro['seconds_elapsed'] >= t3_start) & (gyro['seconds_elapsed'] <= t3_end)]
        if len(sub) >= 2:
            s3_feats['seg3_gyro_y_min'] = sub['y'].min()
            s3_feats['seg3_gyro_y_max'] = sub['y'].max()
        else:
            s3_feats['seg3_gyro_y_min'] = 0.0
            s3_feats['seg3_gyro_y_max'] = 0.0
    else:
        s3_feats['seg3_gyro_y_min'] = 0.0
        s3_feats['seg3_gyro_y_max'] = 0.0
        
    s3_feats.update(get_displacement_feats(t3_start, t3_end, "seg3"))
    s3_feats['seg3_planeRatio'] = s3_feats['seg3_deltaX'] / s3_feats['seg3_deltaZ'] if s3_feats['seg3_deltaZ'] > 0 else 0.0
    
    # Mag in Seg 3
    mag = sensors.get("mag")
    if mag is not None:
        sub = mag[(mag['seconds_elapsed'] >= t3_start) & (mag['seconds_elapsed'] <= t3_end)]
        s3_feats["seg3_mag_x_max"] = sub['x'].max() if len(sub) > 0 else 0.0
    else:
        s3_feats["seg3_mag_x_max"] = 0.0
        
    return s1_feats, s2_feats, s3_feats

# ─── Main Execution ──────────────────────────────────────────────────────────
def main():
    if not os.path.exists(GT_ALIGNED_CSV):
        print(f"❌ ERROR: {GT_ALIGNED_CSV} not found.")
        return
        
    df_gt = pd.read_csv(GT_ALIGNED_CSV)
    df_swings_gt = df_gt[(df_gt['normalized_gt'] != 'NON-SWING') & (df_gt['session_date'] != 'synthetic')].copy()
    
    print(f"🎬 Processing {len(df_swings_gt)} real-world shots across sessions...")
    
    # Cache sensor data per session to avoid repeated Parquet reads
    session_sensor_cache = {}
    
    all_feats = []
    y = []
    
    for idx, row in df_swings_gt.iterrows():
        session_id = row['session_id']
        t_impact = float(row['impact_time_seconds'])
        shot_class = row['normalized_gt']
        
        if session_id not in session_sensor_cache:
            print(f"  Loading Parquet data for: {session_id}")
            session_sensor_cache[session_id] = load_parquet_sensors(session_id)
            
        sensors = session_sensor_cache[session_id]
        if not sensors or "gyro" not in sensors:
            continue
            
        s1, s2, s3 = extract_segmented_features(sensors, t_impact)
        
        # Combine all features for the flat model
        combined = {}
        combined.update(s1)
        combined.update(s2)
        combined.update(s3)
        combined["session_id"] = session_id
        
        all_feats.append(combined)
        y.append(shot_class)
        
    df_features = pd.DataFrame(all_feats)
    y = np.array(y)
    
    # Feature group keys
    seg1_cols = [c for c in df_features.columns if c.startswith("seg1_")]
    seg2_cols = [c for c in df_features.columns if c.startswith("seg2_")]
    seg3_cols = [c for c in df_features.columns if c.startswith("seg3_")]
    all_cols = seg1_cols + seg2_cols + seg3_cols
    
    # Fill NAs
    df_features[all_cols] = df_features[all_cols].fillna(df_features[all_cols].median())
    
    print(f"\n✅ Feature Extraction Complete. Feature set size: {df_features.shape}")
    print(f"  Segment 1 Features: {seg1_cols}")
    print(f"  Segment 2 Features: {seg2_cols}")
    print(f"  Segment 3 Features: {seg3_cols}")
    
    # Cross Validation
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    
    flat_preds = []
    video_preds = []
    opt_preds = []
    gts = []
    
    for fold, (train_idx, test_idx) in enumerate(cv.split(df_features, y)):
        X_train, y_train = df_features.iloc[train_idx], y[train_idx]
        X_test, y_test = df_features.iloc[test_idx], y[test_idx]
        
        gts.extend(y_test)
        
        # ─── Flat Baseline (uses all features) ───
        flat_clf = RandomForestClassifier(n_estimators=100, max_depth=8, class_weight='balanced_subsample', random_state=42)
        flat_clf.fit(X_train[all_cols], y_train)
        flat_preds.extend(flat_clf.predict(X_test[all_cols]))
        
        # ─── Video-Inspired Temporal Hierarchy ───
        # Step 1: FF vs BF (uses seg1_cols only)
        def map_ff_bf(val):
            if val in ["PULL/HOOK", "CUT/PUNCH", "DEFLECTION/GUIDE", "SLOG"]:
                return "BF"
            return "FF"
        y_train_ff_bf = np.array([map_ff_bf(val) for val in y_train])
        clf_ff_bf = RandomForestClassifier(n_estimators=100, max_depth=8, class_weight='balanced_subsample', random_state=42)
        clf_ff_bf.fit(X_train[seg1_cols], y_train_ff_bf)
        
        # Step 2a: FF Branch (uses seg2_cols only)
        ff_mask = (y_train_ff_bf == "FF")
        y_train_ff_def_att = np.array(["Defensive" if val == "DRIVE/DEFENCE" else "Attacking" for val in y_train[ff_mask]])
        clf_ff_def_att = RandomForestClassifier(n_estimators=100, max_depth=8, class_weight='balanced_subsample', random_state=42)
        clf_ff_def_att.fit(X_train[ff_mask][seg2_cols], y_train_ff_def_att)
        
        # Step 3a: FF Attacking leaf (uses seg3_cols only)
        ff_att_mask = ff_mask & (y_train != "DRIVE/DEFENCE")
        clf_ff_att_leaf = RandomForestClassifier(n_estimators=100, max_depth=8, class_weight='balanced_subsample', random_state=42)
        if sum(ff_att_mask) > 0:
            clf_ff_att_leaf.fit(X_train[ff_att_mask][seg3_cols], y_train[ff_att_mask])
            
        # Step 2b: BF Branch (uses seg2_cols only)
        bf_mask = (y_train_ff_bf == "BF")
        y_train_bf_high_low = np.array(["High" if val in ["PULL/HOOK", "SLOG"] else "Low" for val in y_train[bf_mask]])
        clf_bf_high_low = RandomForestClassifier(n_estimators=100, max_depth=8, class_weight='balanced_subsample', random_state=42)
        clf_bf_high_low.fit(X_train[bf_mask][seg2_cols], y_train_bf_high_low)
        
        # Step 3b: BF High leaf (uses seg3_cols only)
        bf_high_mask = bf_mask & np.isin(y_train, ["PULL/HOOK", "SLOG"])
        clf_bf_high_leaf = RandomForestClassifier(n_estimators=100, max_depth=8, class_weight='balanced_subsample', random_state=42)
        if sum(bf_high_mask) > 0:
            clf_bf_high_leaf.fit(X_train[bf_high_mask][seg3_cols], y_train[bf_high_mask])
            
        # Step 3c: BF Low leaf (uses seg3_cols only)
        bf_low_mask = bf_mask & np.isin(y_train, ["CUT/PUNCH", "DEFLECTION/GUIDE"])
        clf_bf_low_leaf = RandomForestClassifier(n_estimators=100, max_depth=8, class_weight='balanced_subsample', random_state=42)
        if sum(bf_low_mask) > 0:
            clf_bf_low_leaf.fit(X_train[bf_low_mask][seg3_cols], y_train[bf_low_mask])
            
        # Inference for Video-Inspired Temporal Hierarchy
        v_fold_preds = []
        for _, row in X_test.iterrows():
            row_df = pd.DataFrame([row])
            ff_bf = clf_ff_bf.predict(row_df[seg1_cols])[0]
            if ff_bf == "FF":
                def_att = clf_ff_def_att.predict(row_df[seg2_cols])[0]
                if def_att == "Defensive":
                    v_fold_preds.append("DRIVE/DEFENCE")
                else:
                    v_fold_preds.append(clf_ff_att_leaf.predict(row_df[seg3_cols])[0] if sum(ff_att_mask) > 0 else "DRIVE/DEFENCE")
            else: # BF
                high_low = clf_bf_high_low.predict(row_df[seg2_cols])[0]
                if high_low == "High":
                    v_fold_preds.append(clf_bf_high_leaf.predict(row_df[seg3_cols])[0] if sum(bf_high_mask) > 0 else "PULL/HOOK")
                else:
                    v_fold_preds.append(clf_bf_low_leaf.predict(row_df[seg3_cols])[0] if sum(bf_low_mask) > 0 else "CUT/PUNCH")
        video_preds.extend(v_fold_preds)
        
        # ─── Watch-Kinematics-Optimized Temporal Hierarchy ───
        # Step 1: High Velocity (uses seg2_cols only, since velocity/swing is built in Seg 2 leading to contact)
        high_vel_classes = ["SLOG", "PULL/HOOK", "POWER DRIVE", "SWEEP"]
        y_train_vel = np.array(["High" if val in high_vel_classes else "Low" for val in y_train])
        clf_vel = RandomForestClassifier(n_estimators=100, max_depth=8, class_weight='balanced_subsample', random_state=42)
        clf_vel.fit(X_train[seg2_cols], y_train_vel)
        
        # Step 2a: High Vel -> Offside/Vertical vs Legside/Horizontal (uses seg2_cols only)
        high_mask = (y_train_vel == "High")
        y_train_high_plane = np.array(["Vertical" if val in ["POWER DRIVE", "PULL/HOOK"] else "Horizontal" for val in y_train[high_mask]])
        clf_high_plane = RandomForestClassifier(n_estimators=100, max_depth=8, class_weight='balanced_subsample', random_state=42)
        clf_high_plane.fit(X_train[high_mask][seg2_cols], y_train_high_plane)
        
        # Step 3a: High-Vertical leaf (uses seg3_cols only for specific contact/roll paths)
        high_vert_mask = high_mask & np.isin(y_train, ["POWER DRIVE", "PULL/HOOK"])
        clf_high_vert = RandomForestClassifier(n_estimators=100, max_depth=8, class_weight='balanced_subsample', random_state=42)
        if sum(high_vert_mask) > 0:
            clf_high_vert.fit(X_train[high_vert_mask][seg3_cols], y_train[high_vert_mask])
            
        # Step 3b: High-Horizontal leaf (uses seg3_cols only)
        high_horiz_mask = high_mask & np.isin(y_train, ["SLOG", "SWEEP"])
        clf_high_horiz = RandomForestClassifier(n_estimators=100, max_depth=8, class_weight='balanced_subsample', random_state=42)
        if sum(high_horiz_mask) > 0:
            clf_high_horiz.fit(X_train[high_horiz_mask][seg3_cols], y_train[high_horiz_mask])
            
        # Step 2b: Low/Medium Vel -> Closed/Flick vs Open/Cut (uses seg2_cols only)
        low_mask = (y_train_vel == "Low")
        y_train_low_plane = np.array(["Closed" if val in ["GLANCE/FLICK", "DRIVE/DEFENCE"] else "Open" for val in y_train[low_mask]])
        clf_low_plane = RandomForestClassifier(n_estimators=100, max_depth=8, class_weight='balanced_subsample', random_state=42)
        clf_low_plane.fit(X_train[low_mask][seg2_cols], y_train_low_plane)
        
        # Step 3c: Low-Closed leaf (uses seg3_cols only)
        low_closed_mask = low_mask & np.isin(y_train, ["GLANCE/FLICK", "DRIVE/DEFENCE"])
        clf_low_closed = RandomForestClassifier(n_estimators=100, max_depth=8, class_weight='balanced_subsample', random_state=42)
        if sum(low_closed_mask) > 0:
            clf_low_closed.fit(X_train[low_closed_mask][seg3_cols], y_train[low_closed_mask])
            
        # Step 3d: Low-Open leaf (uses seg3_cols only)
        low_open_mask = low_mask & np.isin(y_train, ["CUT/PUNCH", "DEFLECTION/GUIDE"])
        clf_low_open = RandomForestClassifier(n_estimators=100, max_depth=8, class_weight='balanced_subsample', random_state=42)
        if sum(low_open_mask) > 0:
            clf_low_open.fit(X_train[low_open_mask][seg3_cols], y_train[low_open_mask])
            
        # Inference for Watch-Kinematics-Optimized Temporal Hierarchy
        o_fold_preds = []
        for _, row in X_test.iterrows():
            row_df = pd.DataFrame([row])
            vel = clf_vel.predict(row_df[seg2_cols])[0]
            if vel == "High":
                plane = clf_high_plane.predict(row_df[seg2_cols])[0]
                if plane == "Vertical":
                    o_fold_preds.append(clf_high_vert.predict(row_df[seg3_cols])[0] if sum(high_vert_mask) > 0 else "PULL/HOOK")
                else:
                    o_fold_preds.append(clf_high_horiz.predict(row_df[seg3_cols])[0] if sum(high_horiz_mask) > 0 else "SLOG")
            else: # Low
                plane = clf_low_plane.predict(row_df[seg2_cols])[0]
                if plane == "Closed":
                    o_fold_preds.append(clf_low_closed.predict(row_df[seg3_cols])[0] if sum(low_closed_mask) > 0 else "DRIVE/DEFENCE")
                else:
                    o_fold_preds.append(clf_low_open.predict(row_df[seg3_cols])[0] if sum(low_open_mask) > 0 else "CUT/PUNCH")
        opt_preds.extend(o_fold_preds)

    # ─── Report Results ───
    print("\n========================================================")
    print("TEMPORAL HIERARCHICAL CLASSIFIER EVALUATION RESULTS")
    print("========================================================")
    print(f"Flat Baseline (All Segments) Accuracy      : {accuracy_score(gts, flat_preds)*100:.2f}%")
    print(f"Video-Inspired Temporal Hierarchy Accuracy : {accuracy_score(gts, video_preds)*100:.2f}%")
    print(f"Watch-Optimized Temporal Hierarchy Accuracy: {accuracy_score(gts, opt_preds)*100:.2f}%")
    print("========================================================\n")
    
    print("Flat Baseline Classification Report:")
    print(classification_report(gts, flat_preds, zero_division=0))
    print("--------------------------------------------------------\n")
    
    print("Video-Inspired Temporal Hierarchy Classification Report:")
    print(classification_report(gts, video_preds, zero_division=0))
    print("--------------------------------------------------------\n")
    
    print("Watch-Optimized Temporal Hierarchy Classification Report:")
    print(classification_report(gts, opt_preds, zero_division=0))

if __name__ == "__main__":
    main()
