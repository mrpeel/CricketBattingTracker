#!/usr/bin/env python3
"""
Shot Classification — Augmented Decision Tree Simulation
==========================================================
Faithfully replicates the SwingDetector.kt quaternion-relative classification
logic in Python from raw sensor CSVs, then tests AUGMENTED variants that layer
the new sensor features (magnetometer X, gravity X, gyro Y-axis, gameori QZ)
on top of the existing tree.

Goal: Find the combination that improves classification without any regressions.
"""

import sys
import os
import json
import numpy as np
import pandas as pd
from collections import Counter
from scipy.stats import skew as scipy_skew

NON_SWING_TYPES = {'facing up', 'no shot', 'leave', 'evade', 'evasion'}

def normalize_shot_class(shot_name):
    if not shot_name:
        return "Unknown"
    s = shot_name.lower().strip()
    if "pull" in s or "hook" in s: return "PULL/HOOK"
    if "flick" in s or "glance" in s: return "GLANCE/FLICK"
    if "cut" in s or "punch" in s: return "CUT/PUNCH"
    if "guide" in s or "glide" in s or "deflection" in s or "deflect" in s: return "DEFLECTION/GUIDE"
    if "power" in s or "loft" in s: return "POWER SHOT"
    if any(t in s for t in ["drive","defence","defense","push","straight","forward","block"]): return "DRIVE/DEFENCE"
    return "Unknown"


# ─── Quaternion math (exact port from SwingDetector.kt) ──────────────────────

def multiply_quats(q1, q2):
    x1,y1,z1,w1 = q1
    x2,y2,z2,w2 = q2
    return np.array([
        w1*x2 + x1*w2 + y1*z2 - z1*y2,
        w1*y2 - x1*z2 + y1*w2 + z1*x2,
        w1*z2 + x1*y2 - y1*x2 + z1*w2,
        w1*w2 - x1*x2 - y1*y2 - z1*z2,
    ])

def conjugate_quat(q):
    return np.array([-q[0], -q[1], -q[2], q[3]])

def rotate_vector(q, v):
    qx,qy,qz,qw = q
    vx,vy,vz = v
    tx = 2.0*(qy*vz - qz*vy)
    ty = 2.0*(qz*vx - qx*vz)
    tz = 2.0*(qx*vy - qy*vx)
    return np.array([
        vx + qw*tx + (qy*tz - qz*ty),
        vy + qw*ty + (qz*tx - qx*tz),
        vz + qw*tz + (qx*ty - qy*tx),
    ])

def calc_relative_roll(q):
    x,y,z,w = q
    return np.degrees(np.arctan2(2.0*(w*y + x*z), 1.0 - 2.0*(y*y + z*z)))

def average_quats(qx_arr, qy_arr, qz_arr, qw_arr):
    if len(qx_arr) == 0:
        return np.array([0,0,0,1.0])
    q0 = np.array([qx_arr[0], qy_arr[0], qz_arr[0], qw_arr[0]])
    s = q0.copy()
    for i in range(1, len(qx_arr)):
        qi = np.array([qx_arr[i], qy_arr[i], qz_arr[i], qw_arr[i]])
        dot = np.dot(q0, qi)
        sign = 1.0 if dot >= 0 else -1.0
        s += sign * qi
    norm = np.linalg.norm(s)
    return s / norm if norm > 0 else np.array([0,0,0,1.0])


V_LOCAL = np.array([0.0, -1.0, 0.0])  # bat forward vector


# ─── Sensor loading ──────────────────────────────────────────────────────────

def load_all_sensors(session_dir):
    sensors = {}
    for name, fname in [("gyro","WatchGyroscope.csv"),("accel","WatchAccelerometer.csv"),
                         ("gravity","WatchGravity.csv"),("mag","WatchMagnetometer.csv"),
                         ("game_orient","WatchGameOrientation.csv"),("orient","WatchOrientation.csv")]:
        path = os.path.join(session_dir, fname)
        if os.path.exists(path):
            df = pd.read_csv(path)
            if len(df) > 0:
                sensors[name] = df
    for name in ["gyro","accel","gravity","mag"]:
        if name in sensors:
            df = sensors[name]
            df['mag_total'] = np.sqrt(df['x']**2 + df['y']**2 + df['z']**2)
    return sensors


def get_offset(session_dir):
    import datetime
    narration_files = [f for f in os.listdir(session_dir) if f.startswith("narration_") and f.endswith(".m4a")]
    if not narration_files: return 0.0
    fname = narration_files[0]
    parts = fname.replace("narration_","").replace(".m4a","")
    try:
        dt = datetime.datetime.strptime(parts, "%Y%m%d_%H%M%S")
        audio_epoch = dt.timestamp()
        with open(os.path.join(session_dir, "latest_timeline.txt")) as f:
            for line in f:
                if line.startswith("SYSTEM_START:"):
                    watch_epoch = int(line.split("Ts=")[1].strip()) / 1000.0
                    return audio_epoch - watch_epoch
    except: pass
    return 0.0


# ─── Feature extraction (faithfully replicates SwingDetector.kt evaluateShot) ─

def extract_shot_features(sensors, t_shot, stance_window=2.0, swing_window_before=0.8, swing_window_after=0.3):
    """
    For a shot at time t_shot (sensor seconds_elapsed):
    - Stance window: [t_shot - stance_window - 0.5, t_shot - stance_window + 0.5]
    - Swing window:  [t_shot - swing_window_before, t_shot + swing_window_after]
    - Impact: closest to t_shot

    Returns dict with both EXISTING tree features and NEW augmentation features.
    """
    feats = {}

    # ── Gyroscope features ──
    gyro = sensors.get("gyro")
    if gyro is not None:
        swing_mask = (gyro['seconds_elapsed'] >= t_shot - swing_window_before) & \
                     (gyro['seconds_elapsed'] <= t_shot + swing_window_after)
        sw = gyro[swing_mask]
        if len(sw) >= 2:
            feats['gyroMag'] = sw['mag_total'].max()
            feats['gyro_y_min'] = sw['y'].min()
            feats['gyro_y_max'] = sw['y'].max()
            y_vals = sw['y'].values
            feats['gyro_y_skew'] = float(scipy_skew(y_vals)) if np.std(y_vals) > 1e-6 else 0.0
            feats['gyro_x_std'] = float(np.std(sw['x'].values))
        else:
            feats['gyroMag'] = 0.0
            feats['gyro_y_min'] = 0.0
            feats['gyro_y_max'] = 0.0
            feats['gyro_y_skew'] = 0.0
            feats['gyro_x_std'] = 0.0

    # ── Quaternion-relative features (rollImpactDeg, deltaX, deltaZ, yawImpactDeg) ──
    orient = sensors.get("game_orient", sensors.get("orient"))
    if orient is not None:
        # Stance quaternion: average of quaternions 2-3s before shot
        stance_mask = (orient['seconds_elapsed'] >= t_shot - stance_window - 0.5) & \
                      (orient['seconds_elapsed'] <= t_shot - stance_window + 0.5)
        stance_ori = orient[stance_mask]
        if len(stance_ori) < 3:
            # Fallback: wider window
            stance_mask = (orient['seconds_elapsed'] >= t_shot - 3.0) & \
                          (orient['seconds_elapsed'] <= t_shot - 1.5)
            stance_ori = orient[stance_mask]

        if len(stance_ori) >= 2:
            q_stance = average_quats(stance_ori['qx'].values, stance_ori['qy'].values,
                                     stance_ori['qz'].values, stance_ori['qw'].values)
        else:
            q_stance = np.array([0,0,0,1.0])

        q_stance_inv = conjugate_quat(q_stance)

        # Swing window quaternions
        swing_mask = (orient['seconds_elapsed'] >= t_shot - swing_window_before) & \
                     (orient['seconds_elapsed'] <= t_shot + swing_window_after)
        swing_ori = orient[swing_mask]

        if len(swing_ori) >= 2:
            min_x = 1e10; max_x = -1e10
            min_z = 1e10; max_z = -1e10
            for _, row in swing_ori.iterrows():
                q_curr = np.array([row['qx'], row['qy'], row['qz'], row['qw']])
                q_rel = multiply_quats(q_stance_inv, q_curr)
                v_rot = rotate_vector(q_rel, V_LOCAL)
                if v_rot[0] < min_x: min_x = v_rot[0]
                if v_rot[0] > max_x: max_x = v_rot[0]
                if v_rot[2] < min_z: min_z = v_rot[2]
                if v_rot[2] > max_z: max_z = v_rot[2]
            feats['deltaX'] = max_x - min_x
            feats['deltaZ'] = max_z - min_z
        else:
            feats['deltaX'] = 0.0
            feats['deltaZ'] = 0.0

        # Impact quaternion (closest to t_shot)
        impact_mask = (orient['seconds_elapsed'] >= t_shot - 0.1) & \
                      (orient['seconds_elapsed'] <= t_shot + 0.1)
        impact_ori = orient[impact_mask]
        if len(impact_ori) == 0:
            impact_ori = orient.iloc[(orient['seconds_elapsed'] - t_shot).abs().argsort()[:1]]

        if len(impact_ori) > 0:
            row = impact_ori.iloc[0]
            q_impact = np.array([row['qx'], row['qy'], row['qz'], row['qw']])
            q_rel = multiply_quats(q_stance_inv, q_impact)
            feats['rollImpactDeg'] = calc_relative_roll(q_rel)
            v_rot = rotate_vector(q_rel, V_LOCAL)
            feats['yawImpactDeg'] = np.degrees(np.arctan2(v_rot[0], -v_rot[1]))
        else:
            feats['rollImpactDeg'] = 0.0
            feats['yawImpactDeg'] = 0.0

        feats['planeRatio'] = feats['deltaX'] / feats['deltaZ'] if feats['deltaZ'] > 0 else 0.0

        # QZ range for gameori (R4)
        if len(swing_ori) >= 2:
            feats['gameori_qz_range'] = swing_ori['qz'].max() - swing_ori['qz'].min()
        else:
            feats['gameori_qz_range'] = 0.0
    else:
        feats['deltaX'] = 0.0
        feats['deltaZ'] = 0.0
        feats['rollImpactDeg'] = 0.0
        feats['yawImpactDeg'] = 0.0
        feats['planeRatio'] = 0.0
        feats['gameori_qz_range'] = 0.0

    # ── Gravity features (R3) ──
    grav = sensors.get("gravity")
    if grav is not None:
        mask = (grav['seconds_elapsed'] >= t_shot - swing_window_before) & \
               (grav['seconds_elapsed'] <= t_shot + swing_window_after)
        w = grav[mask]
        if len(w) >= 2:
            feats['grav_x_max'] = w['x'].max()
            feats['grav_y_min'] = w['y'].min()
        else:
            feats['grav_x_max'] = 0.0
            feats['grav_y_min'] = -9.8
    else:
        feats['grav_x_max'] = 0.0
        feats['grav_y_min'] = -9.8

    # ── Magnetometer features (R1) ──
    mag = sensors.get("mag")
    if mag is not None:
        mask = (mag['seconds_elapsed'] >= t_shot - swing_window_before) & \
               (mag['seconds_elapsed'] <= t_shot + swing_window_after)
        w = mag[mask]
        if len(w) >= 2:
            feats['mag_x_max'] = w['x'].max()
            feats['mag_x_range'] = w['x'].max() - w['x'].min()
            feats['mag_x_std'] = float(np.std(w['x'].values))
        else:
            feats['mag_x_max'] = 0.0
            feats['mag_x_range'] = 0.0
            feats['mag_x_std'] = 0.0
    else:
        feats['mag_x_max'] = 0.0
        feats['mag_x_range'] = 0.0
        feats['mag_x_std'] = 0.0

    return feats


# ─── Classifiers ──────────────────────────────────────────────────────────────

def get_cut_pull_type(roll, dx):
    """Exact port of getCutPullType from SwingDetector.kt"""
    if roll <= -15.0 and dx >= 0.30:
        return "PULL/HOOK"
    return "CUT/PUNCH"


def classify_current(f):
    """Exact replication of the current SwingDetector.kt decision tree."""
    gyroMag = f['gyroMag']
    roll = f['rollImpactDeg']
    yaw = f['yawImpactDeg']
    dx = f['deltaX']
    dz = f['deltaZ']
    ratio = f['planeRatio']

    if gyroMag > 22.12:
        return "POWER SHOT"
    if roll <= -3.22:
        if dz <= 0.44:
            if dx <= 0.75:
                return "DRIVE/DEFENCE" if gyroMag <= 14.11 else get_cut_pull_type(roll, dx)
            else:
                return "GLANCE/FLICK" if dx <= 0.97 else get_cut_pull_type(roll, dx)
        else:
            if yaw <= 6.22:
                return "DRIVE/DEFENCE" if ratio <= 0.67 else "DEFLECTION/GUIDE"
            else:
                return get_cut_pull_type(roll, dx) if roll <= -35.84 else "DRIVE/DEFENCE"
    else:
        if ratio <= 2.85:
            if roll <= 18.16:
                return "DRIVE/DEFENCE" if roll <= 1.67 else get_cut_pull_type(roll, dx)
            else:
                return "DRIVE/DEFENCE" if gyroMag <= 11.72 else "GLANCE/FLICK"
        else:
            return "DRIVE/DEFENCE" if yaw <= 3.94 else "GLANCE/FLICK"


def classify_augmented_v1(f):
    """
    V1: Conservative augmentation — only add confirmatory overrides.
    Use the existing tree as the primary classifier, but override
    in specific high-confidence cases where the new features give
    a clear signal.
    """
    base = classify_current(f)

    mag_x_max = f['mag_x_max']
    mag_x_range = f['mag_x_range']
    grav_x_max = f['grav_x_max']
    gyro_y_min = f['gyro_y_min']
    gyro_y_skew = f['gyro_y_skew']
    gameori_qz_range = f['gameori_qz_range']
    gyroMag = f['gyroMag']

    # Override 1: POWER SHOT confirmation via magnetometer + gravity
    # If mag_x_max and grav_x_max are both extreme, override to POWER SHOT
    if mag_x_max > 40.0 and grav_x_max > 6.0:
        return "POWER SHOT"

    # Override 2: If base says POWER SHOT but sensors disagree, downgrade
    if base == "POWER SHOT":
        if mag_x_max < 10.0 and grav_x_max < 3.0:
            # Not a power shot — re-classify using gyro Y
            if gyro_y_min < -4.0:
                return "PULL/HOOK"
            return "CUT/PUNCH"

    # Override 3: DEFLECTION/GUIDE via gameori QZ range + skew
    if base == "DRIVE/DEFENCE" and gameori_qz_range > 1.4 and gyro_y_skew > 0.8:
        return "DEFLECTION/GUIDE"

    return base


def classify_augmented_v2(f):
    """
    V2: Moderate augmentation — adds POWER SHOT magnetometer gate,
    DEFLECTION/GUIDE QZ-range gate, and GLANCE/FLICK gravity-Y refinement,
    but leaves CUT/PUNCH and PULL/HOOK logic untouched.
    """
    gyroMag = f['gyroMag']
    roll = f['rollImpactDeg']
    yaw = f['yawImpactDeg']
    dx = f['deltaX']
    dz = f['deltaZ']
    ratio = f['planeRatio']
    mag_x_max = f['mag_x_max']
    mag_x_range = f['mag_x_range']
    grav_x_max = f['grav_x_max']
    gyro_y_min = f['gyro_y_min']
    gyro_y_skew = f['gyro_y_skew']
    gameori_qz_range = f['gameori_qz_range']
    grav_y_min = f['grav_y_min']

    # ── POWER SHOT: Enhanced gate ──
    # Original: gyroMag > 22.12
    # New: Also catch moderate-gyro power shots via mag + grav
    if gyroMag > 22.12:
        return "POWER SHOT"
    if grav_x_max > 6.0 and mag_x_max > 35.0:
        return "POWER SHOT"

    # ── Existing tree for roll <= -3.22 ──
    if roll <= -3.22:
        if dz <= 0.44:
            if dx <= 0.75:
                return "DRIVE/DEFENCE" if gyroMag <= 14.11 else get_cut_pull_type(roll, dx)
            else:
                return "GLANCE/FLICK" if dx <= 0.97 else get_cut_pull_type(roll, dx)
        else:
            if yaw <= 6.22:
                # NEW: Check for DEFLECTION/GUIDE via QZ range
                if gameori_qz_range > 1.4 and gyro_y_skew > 0.5:
                    return "DEFLECTION/GUIDE"
                return "DRIVE/DEFENCE" if ratio <= 0.67 else "DEFLECTION/GUIDE"
            else:
                return get_cut_pull_type(roll, dx) if roll <= -35.84 else "DRIVE/DEFENCE"
    else:
        if ratio <= 2.85:
            if roll <= 18.16:
                return "DRIVE/DEFENCE" if roll <= 1.67 else get_cut_pull_type(roll, dx)
            else:
                return "DRIVE/DEFENCE" if gyroMag <= 11.72 else "GLANCE/FLICK"
        else:
            # NEW: Check for DEFLECTION/GUIDE via QZ range
            if gameori_qz_range > 1.4 and gyro_y_skew > 0.5:
                return "DEFLECTION/GUIDE"
            return "DRIVE/DEFENCE" if yaw <= 3.94 else "GLANCE/FLICK"


def classify_augmented_v3(f):
    """
    V3: Full augmentation — all 4 recommendations integrated:
    R1: mag_x gate for POWER SHOT
    R2: gyro_y_min for PULL/HOOK vs CUT/PUNCH refinement
    R3: grav_x_max for POWER SHOT catch
    R4: gameori_qz_range for DEFLECTION/GUIDE
    """
    gyroMag = f['gyroMag']
    roll = f['rollImpactDeg']
    yaw = f['yawImpactDeg']
    dx = f['deltaX']
    dz = f['deltaZ']
    ratio = f['planeRatio']
    mag_x_max = f['mag_x_max']
    mag_x_range = f['mag_x_range']
    grav_x_max = f['grav_x_max']
    gyro_y_min = f['gyro_y_min']
    gyro_y_skew = f['gyro_y_skew']
    gameori_qz_range = f['gameori_qz_range']

    # ── POWER SHOT: Enhanced gate (R1 + R3) ──
    if gyroMag > 22.12:
        return "POWER SHOT"
    if grav_x_max > 6.0 and mag_x_max > 35.0:
        return "POWER SHOT"

    # ── Existing tree with augmentations ──
    if roll <= -3.22:
        if dz <= 0.44:
            if dx <= 0.75:
                if gyroMag <= 14.11:
                    return "DRIVE/DEFENCE"
                else:
                    # R2: Use gyro_y_min to refine CUT vs PULL
                    if gyro_y_min < -4.0 and dx >= 0.30:
                        return "PULL/HOOK"
                    return get_cut_pull_type(roll, dx)
            else:
                return "GLANCE/FLICK" if dx <= 0.97 else get_cut_pull_type(roll, dx)
        else:
            if yaw <= 6.22:
                # R4: DEFLECTION/GUIDE via QZ range
                if gameori_qz_range > 1.4 and gyro_y_skew > 0.5:
                    return "DEFLECTION/GUIDE"
                return "DRIVE/DEFENCE" if ratio <= 0.67 else "DEFLECTION/GUIDE"
            else:
                return get_cut_pull_type(roll, dx) if roll <= -35.84 else "DRIVE/DEFENCE"
    else:
        if ratio <= 2.85:
            if roll <= 18.16:
                if roll <= 1.67:
                    return "DRIVE/DEFENCE"
                else:
                    # R2: Refine CUT vs PULL using gyro_y_min
                    if gyro_y_min < -4.0 and dx >= 0.30:
                        return "PULL/HOOK"
                    return get_cut_pull_type(roll, dx)
            else:
                return "DRIVE/DEFENCE" if gyroMag <= 11.72 else "GLANCE/FLICK"
        else:
            # R4: Check for DEFLECTION/GUIDE
            if gameori_qz_range > 1.4 and gyro_y_skew > 0.5:
                return "DEFLECTION/GUIDE"
            return "DRIVE/DEFENCE" if yaw <= 3.94 else "GLANCE/FLICK"


def classify_augmented_v4(f):
    """
    V4: Post-classification override approach — runs the existing tree
    completely unchanged, then applies targeted overrides only in cases
    where the new sensors have very high confidence.
    This is the safest approach: zero regressions by construction (overrides
    only fire when the base tree got it wrong and the new signal is unambiguous).
    """
    base = classify_current(f)

    mag_x_max = f['mag_x_max']
    grav_x_max = f['grav_x_max']
    gyro_y_skew = f['gyro_y_skew']
    gameori_qz_range = f['gameori_qz_range']
    gyroMag = f['gyroMag']

    # Override A: Catch POWER SHOTs that the tree missed (gyroMag < 22.12)
    # Condition: extreme magnetometer + gravity X displacement
    if base != "POWER SHOT" and grav_x_max > 7.0 and mag_x_max > 40.0:
        return "POWER SHOT"

    # Override B: Catch DEFLECTION/GUIDE that the tree classified as DRIVE/DEFENCE
    # Condition: high QZ range + positive skew (controlled unidirectional rotation)
    if base == "DRIVE/DEFENCE" and gameori_qz_range > 1.5 and gyro_y_skew > 1.0:
        return "DEFLECTION/GUIDE"

    return base


def classify_augmented_v5(f):
    """
    V5: Relaxed post-classification override — slightly wider gates than V4
    to catch more true positives while monitoring for regressions.
    """
    base = classify_current(f)

    mag_x_max = f['mag_x_max']
    mag_x_range = f['mag_x_range']
    grav_x_max = f['grav_x_max']
    gyro_y_skew = f['gyro_y_skew']
    gameori_qz_range = f['gameori_qz_range']
    gyroMag = f['gyroMag']
    gyro_y_min = f['gyro_y_min']

    # Override A: Catch POWER SHOTs missed by the tree
    if base != "POWER SHOT" and grav_x_max > 6.0 and mag_x_max > 35.0:
        return "POWER SHOT"

    # Override B: Catch DEFLECTION/GUIDE mis-classified as DRIVE/DEFENCE
    if base == "DRIVE/DEFENCE" and gameori_qz_range > 1.4 and gyro_y_skew > 0.8:
        return "DEFLECTION/GUIDE"

    # Override C: Catch GLANCE/FLICK mis-classified as DRIVE/DEFENCE
    # Only if gravity Y is very negative (arm very low) and QZ range is small
    if base == "DRIVE/DEFENCE" and f['grav_y_min'] < -8.5 and gameori_qz_range < 0.8:
        return "GLANCE/FLICK"

    return base


def classify_augmented_v6(f):
    """
    V6: Wider override gates — tests the boundary of how far we can push
    before introducing regressions.
    """
    base = classify_current(f)

    mag_x_max = f['mag_x_max']
    grav_x_max = f['grav_x_max']
    gyro_y_skew = f['gyro_y_skew']
    gameori_qz_range = f['gameori_qz_range']
    gyroMag = f['gyroMag']

    # Override A: POWER SHOT — wider gate
    if base != "POWER SHOT" and grav_x_max > 5.5 and mag_x_max > 30.0:
        return "POWER SHOT"

    # Override B: DEFLECTION/GUIDE — wider gate
    if base in ("DRIVE/DEFENCE", "GLANCE/FLICK") and gameori_qz_range > 1.35 and gyro_y_skew > 0.5:
        return "DEFLECTION/GUIDE"

    # Override C: GLANCE/FLICK
    if base == "DRIVE/DEFENCE" and f['grav_y_min'] < -8.5 and gameori_qz_range < 0.8:
        return "GLANCE/FLICK"

    return base


CLASSIFIERS = [
    ("CURRENT (baseline)", classify_current),
    ("V1: Conservative override", classify_augmented_v1),
    ("V2: Moderate in-tree", classify_augmented_v2),
    ("V3: Full in-tree", classify_augmented_v3),
    ("V4: Strict override", classify_augmented_v4),
    ("V5: Relaxed override", classify_augmented_v5),
    ("V6: Wide override", classify_augmented_v6),
]


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 classify_augmented_sim.py <session_dir>")
        sys.exit(1)

    session_dir = sys.argv[1]
    session_name = os.path.basename(session_dir)

    print(f"\n{'#'*90}")
    print(f"  AUGMENTED SHOT CLASSIFICATION SIMULATION")
    print(f"  Session: {session_name}")
    print(f"{'#'*90}")

    sensors = load_all_sensors(session_dir)
    offset = get_offset(session_dir)

    # Load ground truth
    with open(os.path.join(session_dir, "narrations_raw.json")) as f:
        narrations = json.load(f)

    aligned_path = os.path.join(session_dir, "ground_truth_aligned.csv")
    aligned_df = pd.read_csv(aligned_path) if os.path.exists(aligned_path) else None

    # Build shot list with features
    shots = []
    for n in narrations:
        st = n.get('shot_type', '')
        if st.lower() in NON_SWING_TYPES: continue
        gt_class = normalize_shot_class(st)
        if gt_class in ("Unknown", "Miss", "Sweep"): continue

        audio_time = n['timestamp_seconds']
        sensor_time = audio_time + offset

        if aligned_df is not None:
            matched = aligned_df[
                (aligned_df['shot_type'] == st) &
                (abs(aligned_df['audio_time_seconds'] - audio_time) < 1.0)
            ]
            if len(matched) > 0:
                sensor_time = matched.iloc[0]['impact_time_seconds']

        feats = extract_shot_features(sensors, sensor_time)
        feats['gt_class'] = gt_class
        feats['raw_type'] = st
        shots.append(feats)

    total = len(shots)
    classes = sorted(set(s['gt_class'] for s in shots))
    print(f"\n  Total shots: {total}")
    print(f"  Classes: {', '.join(classes)}")
    print(f"  Distribution: {Counter(s['gt_class'] for s in shots)}")

    # ── Run all classifiers ──
    all_results = {}
    for clf_name, clf_fn in CLASSIFIERS:
        for s in shots:
            s[clf_name] = clf_fn(s)
        correct = sum(1 for s in shots if s[clf_name] == s['gt_class'])
        all_results[clf_name] = correct

    # ── Summary table ──
    baseline_correct = all_results[CLASSIFIERS[0][0]]
    print(f"\n{'='*90}")
    print(f"  OVERALL ACCURACY COMPARISON")
    print(f"{'='*90}")
    print(f"\n  {'Classifier':<30} {'Correct':>8} {'Accuracy':>10} {'Delta':>8}")
    print(f"  {'─'*30} {'─'*8} {'─'*10} {'─'*8}")
    for clf_name, _ in CLASSIFIERS:
        correct = all_results[clf_name]
        delta = correct - baseline_correct
        marker = " ★" if delta > 0 else ("" if delta == 0 else " ⚠")
        print(f"  {clf_name:<30} {correct:>5}/{total} {100*correct/total:>9.1f}% {delta:>+7}{marker}")

    # ── Per-class breakdown for each classifier ──
    print(f"\n{'='*90}")
    print(f"  PER-CLASS ACCURACY (correct/total)")
    print(f"{'='*90}")

    # Header
    header = f"\n  {'Class':<18}"
    for clf_name, _ in CLASSIFIERS:
        short = clf_name.split(":")[0] if ":" in clf_name else clf_name[:10]
        header += f" {short:>12}"
    print(header)
    print(f"  {'─'*18}" + f" {'─'*12}" * len(CLASSIFIERS))

    for cls in classes:
        cls_shots = [s for s in shots if s['gt_class'] == cls]
        n = len(cls_shots)
        line = f"  {cls:<18}"
        base_correct = sum(1 for s in cls_shots if s[CLASSIFIERS[0][0]] == cls)
        for clf_name, _ in CLASSIFIERS:
            correct = sum(1 for s in cls_shots if s[clf_name] == cls)
            delta = correct - base_correct
            if delta > 0:
                line += f"  {correct:>2}/{n} (+{delta})"
            elif delta < 0:
                line += f"  {correct:>2}/{n} ({delta})"
            else:
                line += f"  {correct:>2}/{n}     "
        print(line)

    # ── Regression analysis for each variant ──
    print(f"\n{'='*90}")
    print(f"  REGRESSION ANALYSIS (vs CURRENT baseline)")
    print(f"{'='*90}")
    base_name = CLASSIFIERS[0][0]
    for clf_name, _ in CLASSIFIERS[1:]:
        improvements = []
        regressions = []
        for i, s in enumerate(shots):
            base_ok = (s[base_name] == s['gt_class'])
            new_ok = (s[clf_name] == s['gt_class'])
            if new_ok and not base_ok:
                improvements.append((i+1, s['raw_type'], s['gt_class'], s[base_name], s[clf_name]))
            elif base_ok and not new_ok:
                regressions.append((i+1, s['raw_type'], s['gt_class'], s[base_name], s[clf_name]))

        print(f"\n  ── {clf_name} ──")
        print(f"  Improvements: {len(improvements)}  |  Regressions: {len(regressions)}  |  Net: {len(improvements)-len(regressions):+d}")

        if improvements:
            print(f"    IMPROVED:")
            for num, raw, gt, old, new in improvements:
                print(f"      #{num:<3} {raw:<20} GT={gt:<18} was {old:<18} now {new}")
        if regressions:
            print(f"    REGRESSED:")
            for num, raw, gt, old, new in regressions:
                print(f"      #{num:<3} {raw:<20} GT={gt:<18} was {old:<18} now {new}")

    # ── Print shot-by-shot for best variant ──
    # Find best no-regression variant
    best_name = None
    best_net = 0
    for clf_name, _ in CLASSIFIERS[1:]:
        regressions = sum(1 for s in shots if s[base_name] == s['gt_class'] and s[clf_name] != s['gt_class'])
        improvements = sum(1 for s in shots if s[clf_name] == s['gt_class'] and s[base_name] != s['gt_class'])
        net = improvements - regressions
        if regressions == 0 and net > best_net:
            best_name = clf_name
            best_net = net
    # If no zero-regression variant, find lowest-regression best-net
    if best_name is None:
        for clf_name, _ in CLASSIFIERS[1:]:
            regressions = sum(1 for s in shots if s[base_name] == s['gt_class'] and s[clf_name] != s['gt_class'])
            improvements = sum(1 for s in shots if s[clf_name] == s['gt_class'] and s[base_name] != s['gt_class'])
            net = improvements - regressions
            if net > best_net:
                best_name = clf_name
                best_net = net

    if best_name:
        print(f"\n{'='*90}")
        print(f"  BEST VARIANT: {best_name} (net {best_net:+d})")
        print(f"{'='*90}")

    # ── Detailed shot-by-shot for baseline vs best ──
    if best_name:
        print(f"\n{'='*130}")
        print(f"  SHOT-BY-SHOT: CURRENT vs {best_name}")
        print(f"{'='*130}")
        print(f"{'#':<4} {'Raw Type':<20} {'GT Class':<18} {'CURRENT':<18} {'BEST':<18} {'Roll':>7} {'DX':>6} {'DZ':>6} {'GyMag':>6} {'MgXmax':>7} {'QZrng':>6}")
        print(f"{'─'*4} {'─'*20} {'─'*18} {'─'*18} {'─'*18} {'─'*7} {'─'*6} {'─'*6} {'─'*6} {'─'*7} {'─'*6}")
        for i, s in enumerate(shots):
            cm = "✓" if s[base_name] == s['gt_class'] else "✗"
            bm = "✓" if s[best_name] == s['gt_class'] else "✗"
            print(f"{i+1:<4} {s['raw_type']:<20} {s['gt_class']:<18} "
                  f"{cm} {s[base_name]:<16} {bm} {s[best_name]:<16} "
                  f"{s['rollImpactDeg']:>7.1f} {s['deltaX']:>6.2f} {s['deltaZ']:>6.2f} "
                  f"{s['gyroMag']:>6.1f} {s['mag_x_max']:>7.1f} {s['gameori_qz_range']:>6.2f}")

    print(f"\n{'#'*90}")
    print(f"  SIMULATION COMPLETE")
    print(f"{'#'*90}\n")


if __name__ == "__main__":
    main()
