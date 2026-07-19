#!/usr/bin/env python3
"""
pipelines/reprocess_sessions.py — Retrospective DB Re-Scoring Pipeline

Pulls the companion app's SQLite database from the connected phone via ADB,
re-scores all historical shots using the current retrained 20-feature Shot Type
and Shot Quality models, flags updated shots with a "✨ Updated" badge, and pushes
the database back to the phone.
"""
import os
import sys
import sqlite3
import subprocess
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder

ROOT_DIR = "/Users/neilkloot/Code/CricketBattingTracker"
BASE_DIR = "/Users/neilkloot/Code/Batting Sensor Stats"
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

def run_cmd(args):
    res = subprocess.run(args, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"⚠️ Command failed: {' '.join(args)}")
        print(res.stderr)
        return False, res.stderr
    return True, res.stdout

def pull_database():
    print("⏳ Pulling database from phone...")
    # Copy DB to /data/local/tmp as a bridge (adb pulled run-as can fail permission checks)
    ok, err = run_cmd(["adb", "shell", f"run-as {PACKAGE_NAME} cp {REMOTE_DB_PATH} {TMP_REMOTE_PATH}"])
    if not ok:
        print("❌ Failed to copy database on device. Make sure device is connected, unlocked, and app is debuggable.")
        return False
    ok, err = run_cmd(["adb", "pull", TMP_REMOTE_PATH, LOCAL_DB_PATH])
    if not ok:
        print("❌ Failed to pull database file to Mac.")
        return False
    print(f"✅ Successfully pulled database to: {LOCAL_DB_PATH}")
    return True

def push_database():
    print("⏳ Pushing database back to phone...")
    ok, err = run_cmd(["adb", "push", LOCAL_DB_PATH, TMP_REMOTE_PATH])
    if not ok:
        print("❌ Failed to push database to /data/local/tmp.")
        return False
    # Copy DB back to app container with proper permissions
    ok, err = run_cmd(["adb", "shell", f"run-as {PACKAGE_NAME} cp {TMP_REMOTE_PATH} {REMOTE_DB_PATH}"])
    if not ok:
        print("❌ Failed to restore database on device.")
        return False
    # Delete temporary bridge files
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
    print("⏳ Training 20-feature Shot Type and Quality Random Forest models...")
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

def reprocess():
    if not os.path.exists(FEATURES_CSV):
        print(f"❌ compile_dataset.py must be run first to generate {FEATURES_CSV}")
        sys.exit(1)
        
    rf_type, le_type, rf_qual, le_qual = train_classifiers()
    
    if not pull_database():
        sys.exit(1)
        
    conn = sqlite3.connect(LOCAL_DB_PATH)
    cursor = conn.cursor()
    
    # Fetch shots that have extracted features
    cursor.execute("""
        SELECT id, shotType, 
               swing_feature_s1_gyro_y_std, swing_feature_s1_gyro_z_std, 
               swing_feature_s1_delta_x, swing_feature_s1_delta_z, 
               swing_feature_s2_gyro_mag, swing_feature_s2_grav_y_mean, 
               swing_feature_s2_delta_x, swing_feature_s2_delta_z, 
               swing_feature_s3_roll_deg, swing_feature_s3_yaw_deg, 
               swing_feature_s3_delta_x, swing_feature_s3_delta_z, 
               swing_feature_s3_plane_ratio, swing_feature_s3_gyro_y_min,
               bottom_hand_gyro_peak, bottom_hand_acc_peak, 
               bottom_hand_gyro_ratio, bottom_hand_acc_ratio, 
               bottom_hand_time_lead_ms, bottom_hand_sync_score
        FROM innings_events
        WHERE shotType IS NOT NULL 
          AND shotType != 'Session Started' 
          AND shotType != 'Session Ended'
          AND swing_feature_s1_gyro_y_std IS NOT NULL
    """)
    rows = cursor.fetchall()
    print(f"📊 Found {len(rows)} shots in companion database to re-score.")
    
    updated_count = 0
    for r in rows:
        row_id = r[0]
        # Construct feature vector matching FEATURE_COLS order
        features = [
            r[2], r[3], r[4], r[5],  # s1
            r[6], r[7], r[8], r[9],  # s2
            r[10], r[11], r[12], r[13], r[14], r[15],  # s3
            r[16] or 0.0, r[17] or 0.0, r[18] or 0.0, r[19] or 0.0, r[20] or 0.0, r[21] or 0.0  # Polar
        ]
        # Impute NaNs to 0.0
        features = [0.0 if x is None or pd.isna(x) else float(x) for x in features]
        
        # Predict Type
        type_pred_enc = rf_type.predict([features])[0]
        shot_type = le_type.inverse_transform([type_pred_enc])[0]
        
        # Predict Quality
        qual_pred_enc = rf_qual.predict([features])[0]
        quality = le_qual.inverse_transform([qual_pred_enc])[0]
        
        # Map quality to UI fields
        sweet_spot = {
            "good": "Excellent",
            "poor": "Poor",
            "miss": "Miss",
            "edge": "Edge"
        }.get(quality, "Good")
        
        efficiency = {
            "good": 90.0,
            "poor": 60.0,
            "edge": 40.0,
            "miss": 0.0
        }.get(quality, 0.0)
        
        description = f"{shot_type} ({sweet_spot}) ✨ Updated"
        
        cursor.execute("""
            UPDATE innings_events
            SET shotType = ?,
                efficiency = ?,
                description = ?
            WHERE id = ?
        """, (shot_type, efficiency, description, row_id))
        updated_count += 1

    conn.commit()
    conn.close()
    
    print(f"✅ Successfully re-scored {updated_count} shots in local database.")
    
    if push_database():
        restart_app()

if __name__ == "__main__":
    reprocess()
