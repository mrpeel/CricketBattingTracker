#!/usr/bin/env python3
"""
Shot Classification Sensor Importance Analysis
===============================================
Analyses which sensor features are most important for classifying each of the
6 biomechanical shot classes:
  1. DRIVE/DEFENCE
  2. GLANCE/FLICK
  3. CUT/PUNCH
  4. PULL/HOOK
  5. DEFLECTION/GUIDE
  6. POWER SHOT

For each shot in the ground truth, extracts a feature vector from a time window
around the shot timestamp, then runs:
  - Random Forest multi-class classification with feature importances (MDI)
  - Permutation importance cross-validated
  - Per-class one-vs-rest feature analysis
  - Statistical comparison of feature distributions across classes
"""

import sys
import os
import json
import warnings
import numpy as np
import pandas as pd
from collections import Counter

warnings.filterwarnings("ignore")

# ─── Configuration ────────────────────────────────────────────────────────────
WINDOW_BEFORE_S = 1.5   # seconds before the shot impact to extract features
WINDOW_AFTER_S  = 0.5   # seconds after the shot impact

NON_SWING_TYPES = {'facing up', 'no shot', 'leave', 'evade', 'evasion'}

def normalize_shot_class(shot_name):
    if not shot_name:
        return "Unknown"
    s = shot_name.lower().strip()
    if "pull" in s or "hook" in s:
        return "PULL/HOOK"
    if "flick" in s or "glance" in s:
        return "GLANCE/FLICK"
    if "cut" in s or "punch" in s:
        return "CUT/PUNCH"
    if "guide" in s or "glide" in s or "deflection" in s or "deflect" in s:
        return "DEFLECTION/GUIDE"
    if "power" in s or "loft" in s:
        return "POWER SHOT"
    if any(t in s for t in ["drive", "defence", "defense", "push", "straight", "forward", "block"]):
        return "DRIVE/DEFENCE"
    if "sweep" in s:
        return "Sweep"
    return "Unknown"


def load_sensor_data(session_dir):
    """Load all available sensor CSVs."""
    sensors = {}

    # Core motion sensors (xyz)
    for name, fname in [
        ("gyro",    "WatchGyroscope.csv"),
        ("accel",   "WatchAccelerometer.csv"),
        ("gravity", "WatchGravity.csv"),
        ("linacc",  "WatchLinearAcceleration.csv"),
        ("mag",     "WatchMagnetometer.csv"),
    ]:
        path = os.path.join(session_dir, fname)
        if os.path.exists(path):
            df = pd.read_csv(path)
            if len(df) > 0:
                df['mag_total'] = np.sqrt(df['x']**2 + df['y']**2 + df['z']**2)
                sensors[name] = df

    # Quaternion sensors
    for name, fname in [
        ("game_orient", "WatchGameOrientation.csv"),
        ("orient",      "WatchOrientation.csv"),
    ]:
        path = os.path.join(session_dir, fname)
        if os.path.exists(path):
            df = pd.read_csv(path)
            if len(df) > 0:
                sensors[name] = df

    # Barometer
    baro_path = os.path.join(session_dir, "WatchBarometer.csv")
    if os.path.exists(baro_path):
        df = pd.read_csv(baro_path)
        if len(df) > 0:
            sensors["baro"] = df

    # Heart rate
    hr_path = os.path.join(session_dir, "WatchHeartRate.csv")
    if os.path.exists(hr_path):
        df = pd.read_csv(hr_path)
        if len(df) > 0:
            sensors["hr"] = df

    # Steps
    steps_path = os.path.join(session_dir, "WatchSteps.csv")
    if os.path.exists(steps_path):
        df = pd.read_csv(steps_path)
        if len(df) > 0:
            sensors["steps"] = df

    return sensors


def extract_xyz_features(df, t_start, t_end, prefix):
    """Extract statistical features from an xyz sensor within a time window."""
    mask = (df['seconds_elapsed'] >= t_start) & (df['seconds_elapsed'] <= t_end)
    window = df[mask]

    features = {}
    if len(window) < 2:
        # Not enough data, fill with NaN
        for suffix in ['x_mean', 'x_std', 'x_min', 'x_max', 'x_range',
                       'y_mean', 'y_std', 'y_min', 'y_max', 'y_range',
                       'z_mean', 'z_std', 'z_min', 'z_max', 'z_range',
                       'mag_mean', 'mag_std', 'mag_max', 'mag_peak',
                       'x_skew', 'y_skew', 'z_skew']:
            features[f"{prefix}_{suffix}"] = np.nan
        return features

    for axis in ['x', 'y', 'z']:
        vals = window[axis].values
        features[f"{prefix}_{axis}_mean"] = np.mean(vals)
        features[f"{prefix}_{axis}_std"] = np.std(vals, ddof=0)
        features[f"{prefix}_{axis}_min"] = np.min(vals)
        features[f"{prefix}_{axis}_max"] = np.max(vals)
        features[f"{prefix}_{axis}_range"] = np.max(vals) - np.min(vals)
        # Skewness
        if np.std(vals) > 1e-6:
            features[f"{prefix}_{axis}_skew"] = float(pd.Series(vals).skew())
        else:
            features[f"{prefix}_{axis}_skew"] = 0.0

    mag_vals = window['mag_total'].values
    features[f"{prefix}_mag_mean"] = np.mean(mag_vals)
    features[f"{prefix}_mag_std"] = np.std(mag_vals, ddof=0)
    features[f"{prefix}_mag_max"] = np.max(mag_vals)
    features[f"{prefix}_mag_peak"] = np.max(mag_vals) - np.mean(mag_vals)

    return features


def extract_quaternion_features(df, t_start, t_end, prefix):
    """Extract features from quaternion sensor data."""
    mask = (df['seconds_elapsed'] >= t_start) & (df['seconds_elapsed'] <= t_end)
    window = df[mask]

    features = {}
    if len(window) < 3:
        for suffix in ['angular_disp_mean', 'angular_disp_max', 'angular_disp_std',
                       'total_rotation_deg', 'qx_range', 'qy_range', 'qz_range', 'qw_range']:
            features[f"{prefix}_{suffix}"] = np.nan
        return features

    qx = window['qx'].values
    qy = window['qy'].values
    qz = window['qz'].values
    qw = window['qw'].values

    # Consecutive angular displacements
    dots = qx[:-1]*qx[1:] + qy[:-1]*qy[1:] + qz[:-1]*qz[1:] + qw[:-1]*qw[1:]
    dots = np.clip(np.abs(dots), 0.0, 1.0)
    angles_deg = np.degrees(2.0 * np.arccos(dots))

    features[f"{prefix}_angular_disp_mean"] = np.mean(angles_deg)
    features[f"{prefix}_angular_disp_max"] = np.max(angles_deg)
    features[f"{prefix}_angular_disp_std"] = np.std(angles_deg, ddof=0)
    features[f"{prefix}_total_rotation_deg"] = np.sum(angles_deg)

    # Quaternion component ranges
    features[f"{prefix}_qx_range"] = np.max(qx) - np.min(qx)
    features[f"{prefix}_qy_range"] = np.max(qy) - np.min(qy)
    features[f"{prefix}_qz_range"] = np.max(qz) - np.min(qz)
    features[f"{prefix}_qw_range"] = np.max(qw) - np.min(qw)

    return features


def extract_barometer_features(df, t_start, t_end):
    """Extract barometer features."""
    mask = (df['seconds_elapsed'] >= t_start) & (df['seconds_elapsed'] <= t_end)
    window = df[mask]

    features = {}
    if len(window) < 2:
        for s in ['baro_mean', 'baro_std', 'baro_range']:
            features[s] = np.nan
        return features

    p = window['pressure'].values
    features['baro_mean'] = np.mean(p)
    features['baro_std'] = np.std(p, ddof=0)
    features['baro_range'] = np.max(p) - np.min(p)
    return features


def extract_hr_features(df, t_start, t_end):
    """Extract heart rate features (wider window since HR is low-frequency)."""
    # Use a wider window for HR since sample rate is very low (~1Hz)
    mask = (df['seconds_elapsed'] >= t_start - 5.0) & (df['seconds_elapsed'] <= t_end + 5.0)
    window = df[mask]

    features = {}
    if len(window) < 1:
        features['hr_mean'] = np.nan
        return features

    features['hr_mean'] = np.mean(window['bpm'].values)
    return features


def extract_step_features(df, t_shot):
    """Extract step-related features."""
    features = {}
    if df is None or len(df) == 0:
        features['steps_in_2s'] = 0
        features['steps_in_5s'] = 0
        features['time_since_last_step'] = 999.0
        return features

    step_t = df['seconds_elapsed'].values
    features['steps_in_2s'] = int(np.sum((step_t >= t_shot - 2.0) & (step_t <= t_shot)))
    features['steps_in_5s'] = int(np.sum((step_t >= t_shot - 5.0) & (step_t <= t_shot)))

    # Time since last step before shot
    prior = step_t[step_t <= t_shot]
    features['time_since_last_step'] = (t_shot - prior[-1]) if len(prior) > 0 else 999.0

    return features


def extract_features_for_shot(sensors, t_shot):
    """Extract all features for a single shot at time t_shot (sensor time)."""
    t_start = t_shot - WINDOW_BEFORE_S
    t_end = t_shot + WINDOW_AFTER_S

    features = {}

    # XYZ sensors
    for name, prefix in [("gyro", "gyro"), ("accel", "accel"), ("gravity", "grav"),
                          ("linacc", "linacc"), ("mag", "mag")]:
        if name in sensors:
            features.update(extract_xyz_features(sensors[name], t_start, t_end, prefix))

    # Quaternion sensors
    for name, prefix in [("game_orient", "gameori"), ("orient", "orient")]:
        if name in sensors:
            features.update(extract_quaternion_features(sensors[name], t_start, t_end, prefix))

    # Barometer
    if "baro" in sensors:
        features.update(extract_barometer_features(sensors["baro"], t_start, t_end))

    # Heart rate
    if "hr" in sensors:
        features.update(extract_hr_features(sensors["hr"], t_start, t_end))

    # Steps
    features.update(extract_step_features(sensors.get("steps"), t_shot))

    # Derived / composite features
    if "gyro" in sensors and "accel" in sensors:
        # Gyro peak relative to accel peak (ratio)
        gyro_peak = features.get("gyro_mag_peak", 0)
        accel_peak = features.get("accel_mag_peak", 0)
        features["gyro_accel_peak_ratio"] = gyro_peak / (accel_peak + 0.01)

    if "grav" in sensors:
        # Gravity Y at impact (arm elevation proxy)
        grav_df = sensors["grav"]
        mask = (grav_df['seconds_elapsed'] >= t_shot - 0.1) & (grav_df['seconds_elapsed'] <= t_shot + 0.1)
        grav_near = grav_df[mask]
        if len(grav_near) > 0:
            features["grav_y_at_impact"] = np.mean(grav_near['y'].values)
            features["grav_x_at_impact"] = np.mean(grav_near['x'].values)
            features["grav_z_at_impact"] = np.mean(grav_near['z'].values)
        else:
            features["grav_y_at_impact"] = np.nan
            features["grav_x_at_impact"] = np.nan
            features["grav_z_at_impact"] = np.nan

    return features


def get_offset(session_dir):
    """Calculate audio-to-sensor clock offset."""
    import datetime
    narration_files = [f for f in os.listdir(session_dir) if f.startswith("narration_") and f.endswith(".m4a")]
    if not narration_files:
        return 0.0

    fname = narration_files[0]
    parts = fname.replace("narration_", "").replace(".m4a", "")
    try:
        dt = datetime.datetime.strptime(parts, "%Y%m%d_%H%M%S")
        audio_epoch = dt.timestamp()

        timeline_path = os.path.join(session_dir, "latest_timeline.txt")
        with open(timeline_path) as f:
            for line in f:
                if line.startswith("SYSTEM_START:"):
                    watch_epoch = int(line.split("Ts=")[1].strip()) / 1000.0
                    return audio_epoch - watch_epoch
    except:
        pass
    return 0.0


def build_dataset(session_dir):
    """Build the feature matrix and labels from ground truth + sensor data."""
    sensors = load_sensor_data(session_dir)
    offset = get_offset(session_dir)

    # Load ground truth
    narr_path = os.path.join(session_dir, "narrations_raw.json")
    with open(narr_path) as f:
        narrations = json.load(f)

    # Use aligned CSV if available for more precise impact timestamps
    aligned_path = os.path.join(session_dir, "ground_truth_aligned.csv")
    use_aligned = os.path.exists(aligned_path)
    aligned_df = None
    if use_aligned:
        aligned_df = pd.read_csv(aligned_path)

    shots = []
    for i, n in enumerate(narrations):
        st = n.get('shot_type', '')
        if st.lower() in NON_SWING_TYPES:
            continue

        shot_class = normalize_shot_class(st)
        if shot_class in ("Unknown", "Miss", "Sweep"):
            continue

        # Get the best timestamp for this shot
        audio_time = n['timestamp_seconds']

        if use_aligned and aligned_df is not None:
            # Try to find the matching row in aligned CSV
            matched = aligned_df[
                (aligned_df['shot_type'] == st) &
                (abs(aligned_df['audio_time_seconds'] - audio_time) < 1.0)
            ]
            if len(matched) > 0:
                # Use sensor-aligned time
                sensor_time = matched.iloc[0]['sensor_narr_time_seconds']
            else:
                sensor_time = audio_time + offset
        else:
            sensor_time = audio_time + offset

        features = extract_features_for_shot(sensors, sensor_time)
        features['shot_class'] = shot_class
        features['shot_type_raw'] = st
        features['sensor_time'] = sensor_time
        shots.append(features)

    df = pd.DataFrame(shots)
    return df


def run_importance_analysis(df):
    """Run feature importance analysis using Random Forest."""
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.preprocessing import LabelEncoder
    from sklearn.model_selection import cross_val_score, StratifiedKFold
    from sklearn.inspection import permutation_importance

    # Separate features and labels
    label_col = 'shot_class'
    meta_cols = ['shot_class', 'shot_type_raw', 'sensor_time']
    feature_cols = [c for c in df.columns if c not in meta_cols]

    X = df[feature_cols].copy()
    y = df[label_col].values

    # Drop features with all NaN
    nan_cols = X.columns[X.isna().all()]
    X = X.drop(columns=nan_cols)
    feature_cols = list(X.columns)

    # Fill remaining NaN with column median
    X = X.fillna(X.median())

    le = LabelEncoder()
    y_enc = le.fit_transform(y)
    class_names = le.classes_

    print(f"\n{'='*80}")
    print(f"  FEATURE IMPORTANCE ANALYSIS — {len(X)} shots, {len(feature_cols)} features, {len(class_names)} classes")
    print(f"{'='*80}")
    print(f"\nClass distribution:")
    for cn in class_names:
        count = np.sum(y == cn)
        print(f"  {cn:<20s}: {count} shots ({100*count/len(y):.1f}%)")

    # Random Forest
    rf = RandomForestClassifier(n_estimators=500, max_depth=10, random_state=42,
                                class_weight='balanced', n_jobs=-1)

    # Cross-validated accuracy
    cv = StratifiedKFold(n_splits=min(5, min(Counter(y).values())), shuffle=True, random_state=42)
    try:
        scores = cross_val_score(rf, X, y_enc, cv=cv, scoring='f1_weighted')
        print(f"\nCross-validated Weighted F1: {scores.mean():.3f} ± {scores.std():.3f}")
    except Exception as e:
        print(f"\nCross-validation error (small dataset): {e}")

    # Fit on full dataset for importance
    rf.fit(X, y_enc)
    train_acc = rf.score(X, y_enc)
    print(f"Training Accuracy: {train_acc:.3f}")

    # 1. MDI (Mean Decrease Impurity) importances
    mdi_importances = pd.Series(rf.feature_importances_, index=feature_cols)
    mdi_importances = mdi_importances.sort_values(ascending=False)

    print(f"\n{'─'*80}")
    print(f"  TOP 30 FEATURES — Mean Decrease Impurity (MDI)")
    print(f"{'─'*80}")
    print(f"{'Rank':<5} {'Feature':<45} {'Importance':>12}")
    print(f"{'─'*5} {'─'*45} {'─'*12}")
    for rank, (feat, imp) in enumerate(mdi_importances.head(30).items(), 1):
        print(f"{rank:<5} {feat:<45} {imp:>12.4f}")

    # 2. Permutation importance
    try:
        perm_imp = permutation_importance(rf, X, y_enc, n_repeats=20, random_state=42, n_jobs=-1)
        perm_importances = pd.Series(perm_imp.importances_mean, index=feature_cols)
        perm_importances = perm_importances.sort_values(ascending=False)

        print(f"\n{'─'*80}")
        print(f"  TOP 30 FEATURES — Permutation Importance")
        print(f"{'─'*80}")
        print(f"{'Rank':<5} {'Feature':<45} {'Importance':>12} {'Std':>8}")
        print(f"{'─'*5} {'─'*45} {'─'*12} {'─'*8}")
        for rank, (feat, imp) in enumerate(perm_importances.head(30).items(), 1):
            std = perm_imp.importances_std[feature_cols.index(feat)]
            print(f"{rank:<5} {feat:<45} {imp:>12.4f} {std:>8.4f}")
    except Exception as e:
        print(f"\nPermutation importance error: {e}")
        perm_importances = mdi_importances

    # 3. Per-class analysis using one-vs-rest feature importance
    print(f"\n{'='*80}")
    print(f"  PER-CLASS FEATURE IMPORTANCE (One-vs-Rest)")
    print(f"{'='*80}")

    per_class_results = {}
    for cls_name in class_names:
        y_binary = (y == cls_name).astype(int)

        # Skip if fewer than 3 samples
        if y_binary.sum() < 3:
            print(f"\n  {cls_name}: Too few samples ({y_binary.sum()}), skipping.")
            continue

        rf_binary = RandomForestClassifier(n_estimators=300, max_depth=8, random_state=42,
                                           class_weight='balanced', n_jobs=-1)
        rf_binary.fit(X, y_binary)

        imp = pd.Series(rf_binary.feature_importances_, index=feature_cols).sort_values(ascending=False)
        per_class_results[cls_name] = imp

        print(f"\n{'─'*70}")
        print(f"  {cls_name} ({y_binary.sum()} shots) — Top 15 discriminating features")
        print(f"{'─'*70}")
        print(f"{'Rank':<5} {'Feature':<45} {'Importance':>12}")
        for rank, (feat, val) in enumerate(imp.head(15).items(), 1):
            print(f"{rank:<5} {feat:<45} {val:>12.4f}")

    # 4. Statistical feature distribution comparison
    print(f"\n{'='*80}")
    print(f"  SENSOR GROUP IMPORTANCE SUMMARY")
    print(f"{'='*80}")

    # Group features by sensor
    sensor_groups = {
        'Gyroscope': [c for c in feature_cols if c.startswith('gyro_')],
        'Accelerometer': [c for c in feature_cols if c.startswith('accel_')],
        'Gravity': [c for c in feature_cols if c.startswith('grav_')],
        'Linear Acceleration': [c for c in feature_cols if c.startswith('linacc_')],
        'Magnetometer': [c for c in feature_cols if c.startswith('mag_')],
        'Game Orientation': [c for c in feature_cols if c.startswith('gameori_')],
        'Orientation': [c for c in feature_cols if c.startswith('orient_')],
        'Barometer': [c for c in feature_cols if c.startswith('baro_')],
        'Heart Rate': [c for c in feature_cols if c.startswith('hr_')],
        'Steps': [c for c in feature_cols if c.startswith('step')],
        'Derived': [c for c in feature_cols if c.startswith('gyro_accel')],
    }

    group_imp = {}
    print(f"\n{'Sensor Group':<25} {'Num Features':>13} {'Sum MDI':>10} {'Avg MDI':>10} {'Max MDI':>10}")
    print(f"{'─'*25} {'─'*13} {'─'*10} {'─'*10} {'─'*10}")
    for group_name, cols in sorted(sensor_groups.items()):
        if not cols:
            continue
        imps = [mdi_importances.get(c, 0) for c in cols]
        s = sum(imps)
        avg = s / len(imps) if imps else 0
        mx = max(imps) if imps else 0
        group_imp[group_name] = s
        print(f"{group_name:<25} {len(cols):>13} {s:>10.4f} {avg:>10.4f} {mx:>10.4f}")

    # 5. Per-class key feature mean values
    print(f"\n{'='*80}")
    print(f"  KEY FEATURE MEAN VALUES PER CLASS")
    print(f"{'='*80}")

    # Select top 10 overall features
    top_features = mdi_importances.head(10).index.tolist()
    print(f"\n{'Feature':<35}", end="")
    for cn in class_names:
        print(f"{cn:>15}", end="")
    print()
    print(f"{'─'*35}", end="")
    for _ in class_names:
        print(f"{'─'*15}", end="")
    print()

    for feat in top_features:
        print(f"{feat:<35}", end="")
        for cn in class_names:
            cls_mask = y == cn
            vals = X.loc[cls_mask, feat]
            print(f"{vals.mean():>15.3f}", end="")
        print()

    return mdi_importances, perm_importances, per_class_results, class_names, feature_cols, rf


def generate_recommendations(mdi_importances, perm_importances, per_class_results, class_names):
    """Generate actionable recommendations based on the analysis."""
    print(f"\n{'='*80}")
    print(f"  RECOMMENDATIONS FOR SHOT CLASSIFICATION SENSOR LOGIC")
    print(f"{'='*80}")

    # Identify consistently important features (top 10 in both MDI and perm)
    mdi_top = set(mdi_importances.head(15).index)
    perm_top = set(perm_importances.head(15).index)
    consensus_top = mdi_top & perm_top

    print(f"\n1. CONSENSUS IMPORTANT FEATURES (Top-15 in both MDI and Permutation):")
    for feat in sorted(consensus_top):
        print(f"   ✓ {feat}")

    # Features that appear in MDI but not perm (possibly correlated / noisy)
    mdi_only = mdi_top - perm_top
    if mdi_only:
        print(f"\n2. POTENTIALLY REDUNDANT FEATURES (High MDI but low permutation importance):")
        for feat in sorted(mdi_only):
            print(f"   ⚠ {feat}")

    # Per-class distinguishing features
    print(f"\n3. BEST DISCRIMINATING FEATURES PER CLASS:")
    for cls_name in class_names:
        if cls_name in per_class_results:
            top3 = per_class_results[cls_name].head(3)
            feats = ", ".join([f"{f} ({v:.4f})" for f, v in top3.items()])
            print(f"   {cls_name:<20s}: {feats}")

    # Sensor groups that are most/least valuable
    print(f"\n4. SENSOR UTILIZATION RECOMMENDATIONS:")

    # Check if magnetometer or barometer contribute anything useful
    mag_feats = [f for f in mdi_importances.index if f.startswith('mag_')]
    mag_total = sum(mdi_importances[f] for f in mag_feats)
    print(f"   • Magnetometer total MDI: {mag_total:.4f}", end="")
    if mag_total < 0.05:
        print(" ← Low value, consider removing from classification logic")
    else:
        print(" ← Contributes meaningfully")

    baro_feats = [f for f in mdi_importances.index if f.startswith('baro_')]
    baro_total = sum(mdi_importances[f] for f in baro_feats)
    print(f"   • Barometer total MDI:    {baro_total:.4f}", end="")
    if baro_total < 0.02:
        print(" ← Negligible, safe to exclude")
    else:
        print(" ← Has some value")

    hr_feats = [f for f in mdi_importances.index if f.startswith('hr_')]
    hr_total = sum(mdi_importances[f] for f in hr_feats)
    print(f"   • Heart Rate total MDI:   {hr_total:.4f}", end="")
    if hr_total < 0.02:
        print(" ← Negligible, safe to exclude")
    else:
        print(" ← Has some value")

    step_feats = [f for f in mdi_importances.index if f.startswith('step')]
    step_total = sum(mdi_importances[f] for f in step_feats)
    print(f"   • Steps total MDI:        {step_total:.4f}", end="")
    if step_total < 0.02:
        print(" ← Expected: steps are for stance gate, not classification")
    else:
        print(" ← Interesting, steps contribute to classification")


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 shot_classification_sensor_importance.py <session_dir>")
        sys.exit(1)

    session_dir = sys.argv[1]
    session_name = os.path.basename(session_dir)

    print(f"\n{'#'*80}")
    print(f"  SHOT CLASSIFICATION SENSOR IMPORTANCE ANALYSIS")
    print(f"  Session: {session_name}")
    print(f"{'#'*80}")

    # Build dataset
    print("\n► Building feature matrix from sensor data...")
    df = build_dataset(session_dir)
    print(f"  Extracted {len(df)} shot feature vectors with {len(df.columns)} columns")

    # Show class distribution
    print(f"\n  Shot class distribution:")
    for cls, count in df['shot_class'].value_counts().items():
        raw_types = df[df['shot_class'] == cls]['shot_type_raw'].value_counts()
        raw_str = ", ".join([f"{t}({c})" for t, c in raw_types.items()])
        print(f"    {cls:<20s}: {count:>3} shots  [{raw_str}]")

    # Run analysis
    mdi_imp, perm_imp, per_class, class_names, feat_cols, model = run_importance_analysis(df)

    # Generate recommendations
    generate_recommendations(mdi_imp, perm_imp, per_class, class_names)

    print(f"\n{'#'*80}")
    print(f"  ANALYSIS COMPLETE")
    print(f"{'#'*80}\n")


if __name__ == "__main__":
    main()
