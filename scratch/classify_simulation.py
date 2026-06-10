#!/usr/bin/env python3
"""
Shot Classification Simulation — Updated Classifier
=====================================================
Simulates the full SwingDetector pipeline on raw sensor data:
  1. Stance gate (H9 config) → FACING_UP_LOCKED
  2. Swing detection (gyro > 5.0 rad/s trigger)
  3. UPDATED shot classification incorporating the 4 recommendations:
     R1: Magnetometer X-axis features (mag_x_max, mag_x_range, mag_x_std)
     R2: Gyroscope Y-axis metrics (gyro_y_min, gyro_y_skew)
     R3: Gravity X-axis max (grav_x_max)
     R4: Game Orientation QZ range (gameori_qz_range)

Compares the CURRENT decision tree vs the UPDATED classifier against
ground truth labels for every shot.
"""

import sys
import os
import json
import numpy as np
import pandas as pd
from collections import Counter
from scipy.stats import skew as scipy_skew

# ─── Configuration ────────────────────────────────────────────────────────────
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
    return "Unknown"


def load_all_sensors(session_dir):
    """Load all sensor CSVs."""
    sensors = {}
    for name, fname in [
        ("gyro",        "WatchGyroscope.csv"),
        ("accel",       "WatchAccelerometer.csv"),
        ("gravity",     "WatchGravity.csv"),
        ("linacc",      "WatchLinearAcceleration.csv"),
        ("mag",         "WatchMagnetometer.csv"),
        ("game_orient", "WatchGameOrientation.csv"),
        ("orient",      "WatchOrientation.csv"),
    ]:
        path = os.path.join(session_dir, fname)
        if os.path.exists(path):
            df = pd.read_csv(path)
            if len(df) > 0:
                sensors[name] = df

    steps_path = os.path.join(session_dir, "WatchSteps.csv")
    if os.path.exists(steps_path):
        df = pd.read_csv(steps_path)
        if len(df) > 0:
            sensors["steps"] = df

    # Precompute magnitudes
    for name in ["gyro", "accel", "gravity", "linacc", "mag"]:
        if name in sensors:
            df = sensors[name]
            df['mag_total'] = np.sqrt(df['x']**2 + df['y']**2 + df['z']**2)

    return sensors


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


def extract_window_features(sensors, t_center, window_before=1.5, window_after=0.5):
    """
    Extract the classification features for a single shot event.
    Returns a dict of features used by both current and updated classifiers.
    """
    t_start = t_center - window_before
    t_end = t_center + window_after

    features = {}

    # ── Gyroscope features ──
    if "gyro" in sensors:
        df = sensors["gyro"]
        mask = (df['seconds_elapsed'] >= t_start) & (df['seconds_elapsed'] <= t_end)
        w = df[mask]
        if len(w) >= 2:
            features['gyro_mag_max'] = w['mag_total'].max()
            features['gyro_y_min'] = w['y'].min()
            features['gyro_y_max'] = w['y'].max()
            y_vals = w['y'].values
            features['gyro_y_skew'] = float(scipy_skew(y_vals)) if np.std(y_vals) > 1e-6 else 0.0
            features['gyro_y_std'] = float(np.std(y_vals))
            features['gyro_x_std'] = float(np.std(w['x'].values))
        else:
            features['gyro_mag_max'] = 0.0
            features['gyro_y_min'] = 0.0
            features['gyro_y_max'] = 0.0
            features['gyro_y_skew'] = 0.0
            features['gyro_y_std'] = 0.0
            features['gyro_x_std'] = 0.0

    # ── Gravity features ──
    if "gravity" in sensors:
        df = sensors["gravity"]
        mask = (df['seconds_elapsed'] >= t_start) & (df['seconds_elapsed'] <= t_end)
        w = df[mask]
        if len(w) >= 2:
            features['grav_x_max'] = w['x'].max()
            features['grav_y_min'] = w['y'].min()
            features['grav_x_mean'] = w['x'].mean()
        else:
            features['grav_x_max'] = 0.0
            features['grav_y_min'] = -9.8
            features['grav_x_mean'] = 0.0

    # ── Magnetometer features ──
    if "mag" in sensors:
        df = sensors["mag"]
        mask = (df['seconds_elapsed'] >= t_start) & (df['seconds_elapsed'] <= t_end)
        w = df[mask]
        if len(w) >= 2:
            features['mag_x_max'] = w['x'].max()
            features['mag_x_min'] = w['x'].min()
            features['mag_x_range'] = w['x'].max() - w['x'].min()
            features['mag_x_std'] = float(np.std(w['x'].values))
            features['mag_z_min'] = w['z'].min()
        else:
            features['mag_x_max'] = 0.0
            features['mag_x_min'] = 0.0
            features['mag_x_range'] = 0.0
            features['mag_x_std'] = 0.0
            features['mag_z_min'] = 0.0

    # ── Game Orientation features ──
    if "game_orient" in sensors:
        df = sensors["game_orient"]
        mask = (df['seconds_elapsed'] >= t_start) & (df['seconds_elapsed'] <= t_end)
        w = df[mask]
        if len(w) >= 2:
            features['gameori_qz_range'] = w['qz'].max() - w['qz'].min()
            features['gameori_qx_range'] = w['qx'].max() - w['qx'].min()
        else:
            features['gameori_qz_range'] = 0.0
            features['gameori_qx_range'] = 0.0

    # ── Accelerometer features (for shock / hit detection) ──
    if "accel" in sensors:
        df = sensors["accel"]
        mask = (df['seconds_elapsed'] >= t_start) & (df['seconds_elapsed'] <= t_end)
        w = df[mask]
        if len(w) >= 2:
            features['accel_mag_max'] = w['mag_total'].max()
            features['accel_z_skew'] = float(scipy_skew(w['z'].values)) if np.std(w['z'].values) > 1e-6 else 0.0
        else:
            features['accel_mag_max'] = 0.0
            features['accel_z_skew'] = 0.0

    return features


def classify_current(features):
    """
    Replicate the CURRENT SwingDetector decision tree logic.
    Uses: gyro_mag_max (as gyroMag proxy).
    Since we don't have the quaternion-derived rollImpactDeg / deltaX / deltaZ
    from the offline simulation, we approximate with available features.

    NOTE: The current tree is heavily dependent on rollImpactDeg and deltaX which
    are quaternion-stance-relative computations done inside SwingDetector.kt.
    We can't perfectly replicate those from raw CSVs without the full state machine.
    So we use a simplified version of the current logic based on gyro magnitude
    thresholds (the first branch of the tree).
    """
    gyro_mag = features.get('gyro_mag_max', 0.0)

    # The current tree's top-level split is gyroMag > 22.12 → POWER SHOT
    # Below that, it uses rollImpactDeg / deltaX which we can't compute here.
    # We'll use a rule-based approximation using gyro magnitude + gravity patterns.

    if gyro_mag > 22.12:
        return "POWER SHOT"

    # Without rollImpactDeg, approximate using gravity and gyro patterns
    grav_y_min = features.get('grav_y_min', -9.8)
    grav_x_max = features.get('grav_x_max', 0.0)
    gyro_y_min = features.get('gyro_y_min', 0.0)

    # Approximate: strong cross-bat wrist roll → PULL/HOOK or CUT/PUNCH
    if gyro_y_min < -4.0:
        if grav_x_max > 3.0:
            return "PULL/HOOK"
        else:
            return "CUT/PUNCH"

    # Moderate gyro and high arm → CUT/PUNCH
    if grav_y_min > -7.0:
        return "CUT/PUNCH"

    # Low arm, wristy → GLANCE/FLICK
    if grav_y_min < -8.5:
        return "GLANCE/FLICK"

    # Default
    return "DRIVE/DEFENCE"


def classify_updated(features):
    """
    UPDATED classifier incorporating all 4 recommendations:
    R1: Magnetometer X-axis (mag_x_max, mag_x_range, mag_x_std)
    R2: Gyroscope Y-axis (gyro_y_min, gyro_y_skew)
    R3: Gravity X-axis max (grav_x_max)
    R4: Game Orientation QZ range (gameori_qz_range)

    Decision tree designed from the mean-value analysis:
    - POWER SHOT: gyro_mag > 22 OR (grav_x_max > 5.0 AND mag_x_max > 30)
    - PULL/HOOK: gyro_y_min < -4.0 AND grav_x_max > 2.5
    - CUT/PUNCH: grav_y_min > -7.0 AND mag_z_min is characteristic
    - DEFLECTION/GUIDE: gameori_qz_range > 1.4 AND gyro_y_skew > 0.8
    - GLANCE/FLICK: grav_y_min < -8.3 AND gyro_x_std is moderate
    - DRIVE/DEFENCE: default (straight bat, low wrist roll)
    """
    gyro_mag = features.get('gyro_mag_max', 0.0)
    gyro_y_min = features.get('gyro_y_min', 0.0)
    gyro_y_skew = features.get('gyro_y_skew', 0.0)
    gyro_y_std = features.get('gyro_y_std', 0.0)
    gyro_x_std = features.get('gyro_x_std', 0.0)
    grav_x_max = features.get('grav_x_max', 0.0)
    grav_y_min = features.get('grav_y_min', -9.8)
    mag_x_max = features.get('mag_x_max', 0.0)
    mag_x_range = features.get('mag_x_range', 0.0)
    mag_x_std = features.get('mag_x_std', 0.0)
    mag_z_min = features.get('mag_z_min', 0.0)
    gameori_qz_range = features.get('gameori_qz_range', 0.0)
    accel_z_skew = features.get('accel_z_skew', 0.0)

    # ── POWER SHOT (most distinct class) ──
    # From analysis: gyro_mag peak > 22, OR extreme lateral arm (grav_x > 5.0)
    # + massive magnetometer displacement (mag_x_max > 30)
    if gyro_mag > 22.0:
        # Confirm with magnetometer & gravity if available
        if mag_x_max > 25.0 or grav_x_max > 5.0:
            return "POWER SHOT"
        # High gyro alone could also be a hard pull; check wrist roll direction
        if gyro_y_min < -5.0 and grav_x_max < 3.0:
            return "PULL/HOOK"
        return "POWER SHOT"  # default high-gyro

    # ── Check for extreme magnetometer + gravity (power shot with moderate gyro) ──
    if grav_x_max > 5.5 and mag_x_max > 30.0:
        return "POWER SHOT"

    # ── PULL/HOOK ──
    # Strong negative gyro Y (wrist roll), moderate lateral gravity
    if gyro_y_min < -3.5:
        if grav_x_max > 2.0:
            return "PULL/HOOK"
        # Strong wrist roll but low lateral arm → could be hard cut
        if grav_y_min > -7.0:
            return "CUT/PUNCH"
        return "PULL/HOOK"

    # ── DEFLECTION/GUIDE ──
    # High QZ range (bat face rotation / supination), positive gyro_y_skew (controlled, one-direction)
    if gameori_qz_range > 1.35 and gyro_y_skew > 0.5:
        return "DEFLECTION/GUIDE"

    # ── CUT/PUNCH ──
    # Arm stays high (grav_y_min is least negative), moderate wrist action
    # From analysis: CUT/PUNCH has grav_y_min = -6.56 (highest of all classes)
    if grav_y_min > -7.2:
        # Distinguish from DRIVE/DEFENCE using magnetometer Z
        if mag_z_min < -20.0 or mag_x_range > 40.0:
            return "CUT/PUNCH"
        # Low gyro with high arm → likely a block/push
        if gyro_mag < 8.0:
            return "DRIVE/DEFENCE"
        return "CUT/PUNCH"

    # ── GLANCE/FLICK ──
    # Arm drops lowest (grav_y_min most negative: -8.79), oscillating wrist
    if grav_y_min < -8.2:
        if gyro_x_std > 2.0 or gameori_qz_range < 0.9:
            return "GLANCE/FLICK"
        # Could be a controlled guide with low arm
        if gameori_qz_range > 1.3:
            return "DEFLECTION/GUIDE"
        return "GLANCE/FLICK"

    # ── DRIVE/DEFENCE (default) ──
    # Straight bat: lowest wrist roll (gyro_y_min ~ -1.58),
    # moderate orientation, mid-range gravity
    return "DRIVE/DEFENCE"


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 classify_simulation.py <session_dir>")
        sys.exit(1)

    session_dir = sys.argv[1]
    session_name = os.path.basename(session_dir)

    print(f"\n{'#'*80}")
    print(f"  SHOT CLASSIFICATION SIMULATION — CURRENT vs UPDATED")
    print(f"  Session: {session_name}")
    print(f"{'#'*80}")

    # Load data
    print("\n► Loading sensor data...")
    sensors = load_all_sensors(session_dir)
    offset = get_offset(session_dir)
    print(f"  Clock offset: {offset:.3f}s")

    # Load ground truth
    narr_path = os.path.join(session_dir, "narrations_raw.json")
    with open(narr_path) as f:
        narrations = json.load(f)

    # Load aligned CSV for precise timestamps
    aligned_path = os.path.join(session_dir, "ground_truth_aligned.csv")
    aligned_df = pd.read_csv(aligned_path) if os.path.exists(aligned_path) else None

    # Build shot list
    shots = []
    for n in narrations:
        st = n.get('shot_type', '')
        if st.lower() in NON_SWING_TYPES:
            continue
        gt_class = normalize_shot_class(st)
        if gt_class in ("Unknown", "Miss", "Sweep"):
            continue

        audio_time = n['timestamp_seconds']
        sensor_time = audio_time + offset

        # Try aligned CSV for better timestamp
        if aligned_df is not None:
            matched = aligned_df[
                (aligned_df['shot_type'] == st) &
                (abs(aligned_df['audio_time_seconds'] - audio_time) < 1.0)
            ]
            if len(matched) > 0:
                sensor_time = matched.iloc[0]['sensor_narr_time_seconds']

        features = extract_window_features(sensors, sensor_time)

        current_pred = classify_current(features)
        updated_pred = classify_updated(features)

        shots.append({
            'shot_num': len(shots) + 1,
            'time': sensor_time,
            'raw_type': st,
            'gt_class': gt_class,
            'current_pred': current_pred,
            'updated_pred': updated_pred,
            'gyro_mag': features.get('gyro_mag_max', 0),
            'gyro_y_min': features.get('gyro_y_min', 0),
            'gyro_y_skew': features.get('gyro_y_skew', 0),
            'grav_x_max': features.get('grav_x_max', 0),
            'grav_y_min': features.get('grav_y_min', 0),
            'mag_x_max': features.get('mag_x_max', 0),
            'mag_x_range': features.get('mag_x_range', 0),
            'gameori_qz': features.get('gameori_qz_range', 0),
        })

    # ── Print shot-by-shot results ──
    print(f"\n{'='*130}")
    print(f"  SHOT-BY-SHOT CLASSIFICATION RESULTS ({len(shots)} shots)")
    print(f"{'='*130}")
    print(f"{'#':<4} {'Raw Type':<20} {'GT Class':<18} {'CURRENT':<18} {'UPDATED':<18} {'GyMag':>6} {'GyYmin':>7} {'GyYskw':>7} {'GrXmax':>7} {'MgXmax':>7} {'QZrng':>6}")
    print(f"{'─'*4} {'─'*20} {'─'*18} {'─'*18} {'─'*18} {'─'*6} {'─'*7} {'─'*7} {'─'*7} {'─'*7} {'─'*6}")

    for s in shots:
        cur_mark = "✓" if s['current_pred'] == s['gt_class'] else "✗"
        upd_mark = "✓" if s['updated_pred'] == s['gt_class'] else "✗"

        print(f"{s['shot_num']:<4} {s['raw_type']:<20} {s['gt_class']:<18} "
              f"{cur_mark} {s['current_pred']:<16} {upd_mark} {s['updated_pred']:<16} "
              f"{s['gyro_mag']:>6.1f} {s['gyro_y_min']:>7.2f} {s['gyro_y_skew']:>7.2f} "
              f"{s['grav_x_max']:>7.2f} {s['mag_x_max']:>7.1f} {s['gameori_qz']:>6.2f}")

    # ── Compute accuracy metrics ──
    print(f"\n{'='*80}")
    print(f"  OVERALL ACCURACY COMPARISON")
    print(f"{'='*80}")

    current_correct = sum(1 for s in shots if s['current_pred'] == s['gt_class'])
    updated_correct = sum(1 for s in shots if s['updated_pred'] == s['gt_class'])
    total = len(shots)

    print(f"\n  {'Metric':<30} {'CURRENT':>12} {'UPDATED':>12} {'Delta':>10}")
    print(f"  {'─'*30} {'─'*12} {'─'*12} {'─'*10}")
    print(f"  {'Overall Accuracy':<30} {100*current_correct/total:>11.1f}% {100*updated_correct/total:>11.1f}% {100*(updated_correct-current_correct)/total:>+9.1f}%")

    # ── Per-class metrics ──
    classes = sorted(set(s['gt_class'] for s in shots))
    print(f"\n{'='*80}")
    print(f"  PER-CLASS ACCURACY")
    print(f"{'='*80}")
    print(f"\n  {'Class':<20} {'Count':>6} {'CURRENT':>12} {'UPDATED':>12} {'Delta':>10}")
    print(f"  {'─'*20} {'─'*6} {'─'*12} {'─'*12} {'─'*10}")

    for cls in classes:
        cls_shots = [s for s in shots if s['gt_class'] == cls]
        n = len(cls_shots)
        cur_acc = sum(1 for s in cls_shots if s['current_pred'] == cls)
        upd_acc = sum(1 for s in cls_shots if s['updated_pred'] == cls)
        delta = upd_acc - cur_acc
        print(f"  {cls:<20} {n:>6} {cur_acc:>7}/{n:<3} ({100*cur_acc/n:>4.0f}%) "
              f"{upd_acc:>5}/{n:<3} ({100*upd_acc/n:>4.0f}%) {delta:>+9}")

    # ── Confusion Matrix — CURRENT ──
    print(f"\n{'='*80}")
    print(f"  CONFUSION MATRIX — CURRENT CLASSIFIER")
    print(f"{'='*80}")
    print_confusion_matrix(shots, 'current_pred', classes)

    # ── Confusion Matrix — UPDATED ──
    print(f"\n{'='*80}")
    print(f"  CONFUSION MATRIX — UPDATED CLASSIFIER")
    print(f"{'='*80}")
    print_confusion_matrix(shots, 'updated_pred', classes)

    # ── Per-class precision/recall ──
    print(f"\n{'='*80}")
    print(f"  PRECISION / RECALL / F1 COMPARISON")
    print(f"{'='*80}")
    print(f"\n  {'Class':<20} {'─── CURRENT ───':^30} {'─── UPDATED ───':^30}")
    print(f"  {'':20} {'Prec':>8} {'Recall':>8} {'F1':>8}    {'Prec':>8} {'Recall':>8} {'F1':>8}")
    print(f"  {'─'*20} {'─'*8} {'─'*8} {'─'*8} {'':>4} {'─'*8} {'─'*8} {'─'*8}")

    for cls in classes:
        for pred_key, label in [('current_pred', 'cur'), ('updated_pred', 'upd')]:
            tp = sum(1 for s in shots if s['gt_class'] == cls and s[pred_key] == cls)
            fp = sum(1 for s in shots if s['gt_class'] != cls and s[pred_key] == cls)
            fn = sum(1 for s in shots if s['gt_class'] == cls and s[pred_key] != cls)
            prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
            rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
            f1 = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0.0
            if label == 'cur':
                print(f"  {cls:<20} {prec:>8.2f} {rec:>8.2f} {f1:>8.2f}", end="    ")
                cur_metrics = (prec, rec, f1)
            else:
                print(f"{prec:>8.2f} {rec:>8.2f} {f1:>8.2f}")

    # ── Summary of changes ──
    print(f"\n{'='*80}")
    print(f"  CHANGE SUMMARY — Where Updated Classifier Differs")
    print(f"{'='*80}")
    changes = [(s['shot_num'], s['raw_type'], s['gt_class'], s['current_pred'], s['updated_pred'])
               for s in shots if s['current_pred'] != s['updated_pred']]
    if changes:
        print(f"\n  {'#':<4} {'Raw Type':<20} {'GT Class':<18} {'CURRENT':<18} {'UPDATED':<18} {'Result'}")
        print(f"  {'─'*4} {'─'*20} {'─'*18} {'─'*18} {'─'*18} {'─'*10}")
        for num, raw, gt, cur, upd in changes:
            cur_ok = "✓" if cur == gt else "✗"
            upd_ok = "✓" if upd == gt else "✗"
            result = "IMPROVED" if (upd == gt and cur != gt) else ("REGRESSED" if (cur == gt and upd != gt) else "CHANGED")
            print(f"  {num:<4} {raw:<20} {gt:<18} {cur_ok} {cur:<16} {upd_ok} {upd:<16} {result}")
        improved = sum(1 for _, _, gt, cur, upd in changes if upd == gt and cur != gt)
        regressed = sum(1 for _, _, gt, cur, upd in changes if cur == gt and upd != gt)
        print(f"\n  Net: {improved} improved, {regressed} regressed, {len(changes) - improved - regressed} changed (neither was correct)")
    else:
        print("\n  No classification changes between current and updated.")

    print(f"\n{'#'*80}")
    print(f"  SIMULATION COMPLETE")
    print(f"{'#'*80}\n")


def print_confusion_matrix(shots, pred_key, classes):
    """Print a confusion matrix."""
    # Header
    print(f"\n  {'Predicted →':>20}", end="")
    for cls in classes:
        abbr = cls[:8]
        print(f" {abbr:>8}", end="")
    print()
    print(f"  {'Actual ↓':>20}", end="")
    for _ in classes:
        print(f" {'────────':>8}", end="")
    print()

    for actual_cls in classes:
        abbr = actual_cls[:8]
        print(f"  {abbr:>20}", end="")
        for pred_cls in classes:
            count = sum(1 for s in shots if s['gt_class'] == actual_cls and s[pred_key] == pred_cls)
            if count > 0:
                marker = f"[{count}]" if actual_cls == pred_cls else f" {count} "
                print(f" {marker:>8}", end="")
            else:
                print(f" {'·':>8}", end="")
        print()


if __name__ == "__main__":
    main()
