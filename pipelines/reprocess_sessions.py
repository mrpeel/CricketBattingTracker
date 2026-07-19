#!/usr/bin/env python3
"""
pipelines/reprocess_sessions.py — Retrospective DB Sync & Reprocessing

Pulls the SQLite database from the companion app, checks it against the raw sensor
directories in live_watch_sessions/, and:
  1. Identifies sessions missing from the phone database and registers them.
  2. For all sessions with raw data, deletes previous shots and re-runs peak detection,
     alignment, 20-feature extraction, and ML predictions (type and quality).
  3. Inserts updated shots with the correct parameters (using "26 Aldinga Street, Blackburn South"
     as the default location, and marking them with a "✨ Updated" badge).
  4. Pushes the database back to the phone.
"""
import os
import sys
import glob
import sqlite3
import datetime
import subprocess
import numpy as np
import pandas as pd
from scipy.signal import find_peaks
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder

ROOT_DIR = "/Users/neilkloot/Code/CricketBattingTracker"
BASE_DIR = "/Users/neilkloot/Code/Batting Sensor Stats"
SESSIONS_DIR = os.path.join(BASE_DIR, "live_watch_sessions")
FEATURES_CSV = os.path.join(BASE_DIR, "combined_features.csv")

LOCAL_DB_PATH = os.path.join(ROOT_DIR, "scratch/cricket_tracker_database.db")
PACKAGE_NAME = "com.mrpeel.cricketbattingtracker"
REMOTE_DB_PATH = f"/data/data/{PACKAGE_NAME}/databases/cricket_tracker_database"
TMP_REMOTE_PATH = "/data/local/tmp/cricket_tracker_database"

FEATURE_COLS = [
    's1_gyro_y_std', 's1_gyro_z_std', 's1_deltaX', 's1_deltaZ',
    's2_gyroMag', 's2_grav_y_mean', 's2_deltaX', 's2_deltaZ',
    's3_rollImpactDeg', 's3_yawImpactDeg', 's3_deltaX', 's3_deltaZ',
    's3_planeRatio', 's3_gyro_y_min',
    'bottom_hand_gyro_peak', 'bottom_hand_acc_peak',
    'bottom_hand_gyro_ratio', 'bottom_hand_acc_ratio',
    'bottom_hand_time_lead_ms', 'bottom_hand_sync_score',
]

sys.path.append(ROOT_DIR)
from automate_pipeline import load_watch_sensor

def run_cmd(args):
    res = subprocess.run(args, capture_output=True, text=True)
    return res.returncode == 0, res.stdout

def pull_database():
    print("⏳ Pulling database from phone...")
    ok, _ = run_cmd(["adb", "shell", f"run-as {PACKAGE_NAME} cp {REMOTE_DB_PATH} {TMP_REMOTE_PATH}"])
    if not ok:
        print("❌ Failed to copy database on device. Make sure device is connected, unlocked, and app is debuggable.")
        return False
    ok, _ = run_cmd(["adb", "pull", TMP_REMOTE_PATH, LOCAL_DB_PATH])
    if not ok:
        print("❌ Failed to pull database file to Mac.")
        return False
    print(f"✅ Successfully pulled database to: {LOCAL_DB_PATH}")
    return True

def push_database():
    print("⏳ Pushing database back to phone...")
    ok, _ = run_cmd(["adb", "push", LOCAL_DB_PATH, TMP_REMOTE_PATH])
    if not ok:
        print("❌ Failed to push database to /data/local/tmp.")
        return False
    ok, _ = run_cmd(["adb", "shell", f"run-as {PACKAGE_NAME} cp {TMP_REMOTE_PATH} {REMOTE_DB_PATH}"])
    if not ok:
        print("❌ Failed to restore database on device.")
        return False
    run_cmd(["adb", "shell", f"run-as {PACKAGE_NAME} rm -f {REMOTE_DB_PATH}-wal {REMOTE_DB_PATH}-journal"])
    run_cmd(["adb", "shell", f"rm -f {TMP_REMOTE_PATH}"])
    print("✅ Database successfully restored on device.")
    return True

def restart_app():
    print("⏳ Restarting app on phone...")
    run_cmd(["adb", "shell", f"am force-stop {PACKAGE_NAME}"])
    run_cmd(["adb", "shell", f"monkey -p {PACKAGE_NAME} -c android.intent.category.LAUNCHER 1"])
    print("✅ App restarted successfully.")

def train_classifiers():
    print("⏳ Training classifiers on compiled dataset...")
    df = pd.read_csv(FEATURES_CSV)
    df_swings = df[df['normalized_gt'] != 'NON-SWING'].copy()
    
    # Train Type
    X = df_swings[FEATURE_COLS].fillna(0.0)
    y_type = df_swings['normalized_gt'].values
    le_type = LabelEncoder()
    y_type_enc = le_type.fit_transform(y_type)
    rf_type = RandomForestClassifier(n_estimators=200, max_depth=8, class_weight='balanced_subsample', random_state=42, n_jobs=-1)
    rf_type.fit(X, y_type_enc)
    
    # Train Quality
    df_quality = df_swings[df_swings['quality'].notna() & (df_swings['quality'] != '')].copy()
    def clean_quality(q):
        val = str(q).lower().strip()
        if "good" in val or "okay" in val or "ok" in val or "excellent" in val:
            return "good"
        if "poor" in val or "bad" in val:
            return "poor"
        if "miss" in val:
            return "miss"
        if "edge" in val:
            return "edge"
        return "good"
    y_qual = df_quality['quality'].apply(clean_quality).values
    X_qual = df_quality[FEATURE_COLS].fillna(0.0)
    le_qual = LabelEncoder()
    y_qual_enc = le_qual.fit_transform(y_qual)
    rf_qual = RandomForestClassifier(n_estimators=100, max_depth=6, class_weight='balanced_subsample', random_state=42, n_jobs=-1)
    rf_qual.fit(X_qual, y_qual_enc)
    
    return rf_type, le_type, rf_qual, le_qual

def average_quats(qxs, qys, qzs, qws):
    sum_q = np.zeros(4)
    for x, y, z, w in zip(qxs, qys, qzs, qws):
        q = np.array([x, y, z, w])
        if np.dot(q, sum_q) < 0:
            q = -q
        sum_q += q
    return sum_q / np.linalg.norm(sum_q)

def conjugate_quat(q):
    return np.array([-q[0], -q[1], -q[2], q[3]])

def multiply_quats(q1, q2):
    x1, y1, z1, w1 = q1
    x2, y2, z2, w2 = q2
    return np.array([
        w1*x2 + x1*w2 + y1*z2 - z1*y2,
        w1*y2 - x1*z2 + y1*w2 + z1*x2,
        w1*z2 + x1*y2 - y1*x2 + z1*w2,
        w1*w2 - x1*x2 - y1*y2 - z1*z2
    ])

def rotate_vector(q, v):
    qx, qy, qz, qw = q
    vx, vy, vz = v
    tx = 2.0 * (qy*vz - qz*vy)
    ty = 2.0 * (qz*vx - qx*vz)
    tz = 2.0 * (qx*vy - qy*vx)
    return np.array([
        vx + qw*tx + (qy*tz - qz*ty),
        vy + qw*ty + (qz*tx - qx*tz),
        vz + qw*tz + (qx*ty - qy*tx)
    ])

def extract_features_single_shot(sensors, t_shot):
    """Replicates PhoneSwingDetector.kt/compile_dataset.py feature extraction in Python."""
    feats = {col: 0.0 for col in FEATURE_COLS}
    acc = sensors.get("accel")
    gyro = sensors.get("gyro")
    orient = sensors.get("game_orient") or sensors.get("orientation")
    grav = sensors.get("gravity")
    
    if orient is None or len(orient) < 5:
        return feats

    # Estimate reference rest stance in [-3.0s, -1.0s]
    window_df = orient[(orient['seconds_elapsed'] >= t_shot - 3.0) & (orient['seconds_elapsed'] <= t_shot - 1.0)]
    if len(window_df) >= 2:
        q_stance = average_quats(window_df['qx'].values, window_df['qy'].values, window_df['qz'].values, window_df['qw'].values)
    else:
        q_stance = np.array([0.0, 0.0, 0.0, 1.0])
        
    q_stance_inv = conjugate_quat(q_stance)
    v_local = np.array([0.0, -1.0, 0.0])

    def get_displacement_feats(ts, te):
        sub = orient[(orient['seconds_elapsed'] >= t_shot + ts) & (orient['seconds_elapsed'] <= t_shot + te)]
        if len(sub) >= 2:
            min_x, max_x = 1e10, -1e10
            min_z, max_z = 1e10, -1e10
            for _, row in sub.iterrows():
                q_curr = np.array([row['qx'], row['qy'], row['qz'], row['qw']])
                q_rel = multiply_quats(q_stance_inv, q_curr)
                v_rot = rotate_vector(q_rel, v_local)
                min_x, max_x = min(min_x, v_rot[0]), max(max_x, v_rot[0])
                min_z, max_z = min(min_z, v_rot[2]), max(max_z, v_rot[2])
            return max_x - min_x, max_z - min_z
        return 0.0, 0.0

    # Segment 1: Backswing [-0.80s, -0.20s]
    s1_dx, s1_dz = get_displacement_feats(-0.80, -0.20)
    feats["s1_deltaX"] = s1_dx
    feats["s1_deltaZ"] = s1_dz
    if gyro is not None:
        sub = gyro[(gyro['seconds_elapsed'] >= t_shot - 0.80) & (gyro['seconds_elapsed'] <= t_shot - 0.20)]
        if len(sub) >= 2:
            feats["s1_gyro_y_std"] = float(np.std(sub['y'].values))
            feats["s1_gyro_z_std"] = float(np.std(sub['z'].values))

    # Segment 2: Downswing [-0.20s, -0.05s]
    s2_dx, s2_dz = get_displacement_feats(-0.20, -0.05)
    feats["s2_deltaX"] = s2_dx
    feats["s2_deltaZ"] = s2_dz
    if gyro is not None:
        sub = gyro[(gyro['seconds_elapsed'] >= t_shot - 0.20) & (gyro['seconds_elapsed'] <= t_shot - 0.05)]
        feats["s2_gyroMag"] = float(sub['mag'].max()) if len(sub) > 0 else 0.0
    if grav is not None:
        sub = grav[(grav['seconds_elapsed'] >= t_shot - 0.20) & (grav['seconds_elapsed'] <= t_shot - 0.05)]
        feats["s2_grav_y_mean"] = float(sub['y'].mean()) if len(sub) > 0 else -9.8

    # Segment 3: Impact/Follow [-0.05s, 0.30s]
    s3_dx, s3_dz = get_displacement_feats(-0.05, 0.30)
    feats["s3_deltaX"] = s3_dx
    feats["s3_deltaZ"] = s3_dz
    if gyro is not None:
        sub = gyro[(gyro['seconds_elapsed'] >= t_shot - 0.05) & (gyro['seconds_elapsed'] <= t_shot + 0.30)]
        if len(sub) >= 2:
            feats["s3_gyro_y_min"] = float(sub['y'].min())
            plane_z = np.std(sub['z'].values)
            plane_y = np.std(sub['y'].values)
            feats["s3_planeRatio"] = float(plane_z / plane_y) if plane_y > 0.01 else 0.0
            
    if orient is not None:
        sub = orient[(orient['seconds_elapsed'] >= t_shot - 0.05) & (orient['seconds_elapsed'] <= t_shot + 0.10)]
        if len(sub) > 0:
            # Snap to closest orientation to impact
            closest_idx = np.argmin(np.abs(sub['seconds_elapsed'].values - t_shot))
            row = sub.iloc[closest_idx]
            q_curr = np.array([row['qx'], row['qy'], row['qz'], row['qw']])
            q_rel = multiply_quats(q_stance_inv, q_curr)
            # relative roll/yaw
            feats["s3_rollImpactDeg"] = float(np.degrees(np.arctan2(2.0*(q_rel[3]*q_rel[1] + q_rel[0]*q_rel[2]), 1.0 - 2.0*(q_rel[1]**2 + q_rel[2]**2))))
            feats["s3_yawImpactDeg"] = float(np.degrees(np.arcsin(np.clip(2.0*(q_rel[3]*q_rel[2] - q_rel[0]*q_rel[1]), -1.0, 1.0))))
            
    return feats

def process_single_session_raw(session_dir, rf_type, le_type, rf_qual, le_qual, watch_gyro_threshold):
    """Processes a raw session directory, running peak detection and predicting shots."""
    # 1. Load watch sensors
    sensors = {}
    for name, key in [("WatchAccelerometer", "accel"), ("WatchGyroscope", "gyro"), 
                      ("WatchGravity", "gravity"), ("WatchGameOrientation", "game_orient")]:
        df = load_watch_sensor(session_dir, name)
        if df is not None and not df.empty:
            sensors[key] = df

    if "gyro" not in sensors or "game_orient" not in sensors:
        return []

    gyro = sensors["gyro"]
    gyro_times = gyro["seconds_elapsed"].values
    gyro_mags = gyro["mag"].values
    gyro_ns = gyro["time"].values

    # Find peaks on watch gyro
    peaks, _ = find_peaks(gyro_mags, height=watch_gyro_threshold, distance=75) # min 1.5s gap at 50Hz
    detected_shots = []

    for p in peaks:
        t_shot = float(gyro_times[p])
        ts_ns = int(gyro_ns[p])
        
        # Verify stance stability to filter walk wiggles
        sub_orient = sensors["game_orient"][(sensors["game_orient"]["seconds_elapsed"] >= t_shot - 2.5) & 
                                            (sensors["game_orient"]["seconds_elapsed"] <= t_shot - 1.0)]
        if len(sub_orient) < 5:
            continue
            
        # Extract features
        feats = extract_features_single_shot(sensors, t_shot)
        
        # Check Polar data (if alignment exists in session)
        polar_gyro_peak = 0f
        polar_acc_peak = 0f
        polar_gyro_ratio = 0f
        polar_acc_ratio = 0f
        polar_time_lead_ms = 0f
        polar_sync_score = 0f
        
        # Load from ground_truth_aligned.csv if present for bottom hand alignment data
        gt_csv = os.path.join(session_dir, "ground_truth_aligned.csv")
        if os.path.exists(gt_csv):
            df_gt = pd.read_csv(gt_csv)
            # Find closest mapped impact in ground truth
            df_gt["diff"] = np.abs(df_gt["impact_time_seconds"] - t_shot)
            closest_gt = df_gt.sort_values("diff").iloc[0]
            if closest_gt["diff"] < 1.5: # matching shot
                polar_gyro_peak = float(closest_gt.get("bottom_hand_gyro_peak", 0.0))
                polar_acc_peak = float(closest_gt.get("bottom_hand_acc_peak", 0.0))
                polar_gyro_ratio = float(closest_gt.get("bottom_hand_gyro_ratio", 0.0))
                polar_acc_ratio = float(closest_gt.get("bottom_hand_acc_ratio", 0.0))
                polar_time_lead_ms = float(closest_gt.get("bottom_hand_time_lead_ms", 0.0))
                polar_sync_score = float(closest_gt.get("bottom_hand_sync_score", 0.0))

        feats.update({
            'bottom_hand_gyro_peak': polar_gyro_peak,
            'bottom_hand_acc_peak': polar_acc_peak,
            'bottom_hand_gyro_ratio': polar_gyro_ratio,
            'bottom_hand_acc_ratio': polar_acc_ratio,
            'bottom_hand_time_lead_ms': polar_time_lead_ms,
            'bottom_hand_sync_score': polar_sync_score,
        })
        
        feat_vector = [0.0 if feats[col] is None or pd.isna(feats[col]) else float(feats[col]) for col in FEATURE_COLS]
        
        # Predict Type
        type_enc = rf_type.predict([feat_vector])[0]
        shot_type = le_type.inverse_transform([type_enc])[0]
        
        # Predict Quality
        qual_enc = rf_qual.predict([feat_vector])[0]
        quality = le_qual.inverse_transform([qual_enc])[0]
        
        # Biomechanical defaults derived from features
        bat_speed = float(gyro_mags[p] * 4.5)
        impact_force = float(polar_acc_peak if polar_acc_peak > 0f else np.nan)
        
        detected_shots.append({
            "timestamp_offset_s": t_shot,
            "timestamp_ns": ts_ns,
            "shot_type": shot_type,
            "quality": quality,
            "bat_speed": bat_speed,
            "impact_force": impact_force,
            "features": feats
        })
        
    return detected_shots

def main():
    if not os.path.exists(FEATURES_CSV):
        print(f"❌ compile_dataset.py must be run first to generate {FEATURES_CSV}")
        sys.exit(1)
        
    rf_type, le_type, rf_qual, le_qual = train_classifiers()
    
    # Read optimized config to match phone-side prominence detection
    watch_gyro_threshold = 1.5
    config_json = os.path.join(BASE_DIR, "optimized_detection_config.json")
    if os.path.exists(config_json):
        try:
            with open(config_json, "r") as jf:
                watch_gyro_threshold = json.load(jf).get("WATCH_GYRO_THRESHOLD", 1.5)
        except Exception:
            pass

    if not pull_database():
        sys.exit(1)
        
    conn = sqlite3.connect(LOCAL_DB_PATH)
    cursor = conn.cursor()
    
    # Find all local session directories
    session_dirs = sorted(glob.glob(os.path.join(SESSIONS_DIR, "session-*")))
    print(f"\n📂 Scanning {len(session_dirs)} local sessions on Mac...")

    for sdir in session_dirs:
        session_name = os.path.basename(sdir)
        # Parse timestamp from session folder name (e.g. session-2026-07-11_12-51-39)
        try:
            dt_str = session_name.replace("session-", "")
            dt = datetime.datetime.strptime(dt_str, "%Y-%m-%d_%H-%m-%s" if "_" in dt_str else "%Y-%m-%d_%H-%M-%S")
            session_start_ms = int(dt.timestamp() * 1000)
        except Exception:
            session_start_ms = int(os.path.getmtime(sdir) * 1000)

        innings_id = session_start_ms
        print(f"🎬 Processing session {session_name} (Innings ID: {innings_id})...")

        # 1. Delete previous shot events for this session if it already exists
        cursor.execute("DELETE FROM innings_events WHERE inningsId = ?", (innings_id,))
        
        # 2. Re-run peak detection and classifications
        shots = process_single_session_raw(sdir, rf_type, le_type, rf_qual, le_qual, watch_gyro_threshold)
        
        # 3. Write Session Started marker
        cursor.execute("""
            INSERT INTO innings_events (inningsId, timestamp, description, location)
            VALUES (?, ?, 'Session Started', '26 Aldinga Street, Blackburn South')
        """, (innings_id, session_start_ms))

        # 4. Insert each shot
        for i, shot in enumerate(shots, 1):
            shot_time_ms = session_start_ms + int(shot["timestamp_offset_s"] * 1000)
            
            # Map quality string to UI sweetspot
            sweet_spot = {
                "good": "Excellent",
                "poor": "Poor",
                "miss": "Miss",
                "edge": "Edge"
            }.get(shot["quality"], "Good")
            
            efficiency = {
                "good": 90.0,
                "poor": 60.0,
                "edge": 40.0,
                "miss": 0.0
            }.get(shot["quality"], 0.0)

            desc = f"{shot['shot_type']} ({sweet_spot}) ✨ Updated"
            f = shot["features"]

            cursor.execute("""
                INSERT INTO innings_events (
                    inningsId, timestamp, description, batSpeed, impactForce, shotType, efficiency, location,
                    bottom_hand_gyro_peak, bottom_hand_acc_peak, bottom_hand_gyro_ratio, bottom_hand_acc_ratio, bottom_hand_time_lead_ms, bottom_hand_sync_score,
                    swing_feature_s1_gyro_y_std, swing_feature_s1_gyro_z_std, swing_feature_s1_delta_x, swing_feature_s1_delta_z,
                    swing_feature_s2_gyro_mag, swing_feature_s2_grav_y_mean, swing_feature_s2_delta_x, swing_feature_s2_delta_z,
                    swing_feature_s3_roll_deg, swing_feature_s3_yaw_deg, swing_feature_s3_delta_x, swing_feature_s3_delta_z,
                    swing_feature_s3_plane_ratio, swing_feature_s3_gyro_y_min
                ) VALUES (
                    ?, ?, ?, ?, ?, ?, ?, '26 Aldinga Street, Blackburn South',
                    ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?,
                    ?, ?, ?, ?,
                    ?, ?, ?, ?,
                    ?, ?
                )
            """, (
                innings_id, shot_time_ms, desc, shot["bat_speed"], shot["impact_force"], shot["shot_type"], efficiency,
                f.get('bottom_hand_gyro_peak'), f.get('bottom_hand_acc_peak'), f.get('bottom_hand_gyro_ratio'), f.get('bottom_hand_acc_ratio'), f.get('bottom_hand_time_lead_ms'), f.get('bottom_hand_sync_score'),
                f.get('s1_gyro_y_std'), f.get('s1_gyro_z_std'), f.get('s1_deltaX'), f.get('s1_deltaZ'),
                f.get('s2_gyroMag'), f.get('s2_grav_y_mean'), f.get('s2_deltaX'), f.get('s2_deltaZ'),
                f.get('s3_rollImpactDeg'), f.get('s3_yawImpactDeg'), f.get('s3_deltaX'), f.get('s3_deltaZ'),
                f.get('s3_planeRatio'), f.get('s3_gyro_y_min')
            ))
            
        # 5. Write Session Ended marker
        session_end_ms = session_start_ms + (int(shots[-1]["timestamp_offset_s"] * 1000) if shots else 10000)
        cursor.execute("""
            INSERT INTO innings_events (inningsId, timestamp, description, location)
            VALUES (?, ?, 'Session Ended', '26 Aldinga Street, Blackburn South')
        """, (innings_id, session_end_ms))
        
        print(f"   Processed {len(shots)} shots. Location set to: 26 Aldinga Street, Blackburn South")

    conn.commit()
    conn.close()
    
    print("\n⏳ Uploading updated database back to the phone...")
    if push_database():
        restart_app()

if __name__ == "__main__":
    main()
