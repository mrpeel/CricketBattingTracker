#!/usr/bin/env python3
"""
augment_training_data.py
========================
Generates synthetic IMU training variants from real Galaxy Watch session data.

For every real swing shot in the live_watch_sessions/ ground truth files, this
script produces 15 synthetic variants using four augmentation techniques:

  1. 3D Rotation       — wrist slip simulation (±15° on X/Y axes)
  2. Time Warping      — swing speed variation (±10% via cubic spline)
  3. Magnitude Scaling — force variation (class-aware asymmetric range)
  4. Gaussian Jitter   — overfitting prevention (σ = 0.5% of channel std)

Synthetic data is written to:
  /Users/neilkloot/Code/Batting Sensor Stats/augmented_training_data/

IMPORTANT: This data must NEVER be used for evaluation. Only compile_dataset.py
ingests it for training feature rows. SwingDetectorGroundTruthTest.kt and all
scorecard evaluation always runs on real live_watch_sessions/ data only.
"""

import os
import sys
import math
import numpy as np
import pandas as pd
from scipy.interpolate import CubicSpline

# ─── Configuration ────────────────────────────────────────────────────────────
BASE_DIR       = "/Users/neilkloot/Code/Batting Sensor Stats"
LIVE_DIR       = os.path.join(BASE_DIR, "live_watch_sessions")
AUG_DIR        = os.path.join(BASE_DIR, "augmented_training_data")

VARIANTS_PER_SHOT  = 15
# Conservative balancing: only fill deficit classes up to the majority class size.
# MAX_SYNTH_RATIO caps how much synthetic data any single class can receive
# relative to its own real count, preventing domain-gap overfitting.
MAX_SYNTH_RATIO    = 2     # max synthetic rows = 2 × real_count per class
SWING_BEFORE       = 0.8   # seconds before impact to slice
SWING_AFTER        = 0.3   # seconds after impact to slice
STANCE_BEFORE      = 2.0   # seconds before impact for stance quaternion window

NON_SWING_TYPES = {'facing up', 'no shot', 'leave', 'evade', 'evasion', 'miss'}

# Class-aware magnitude scaling ranges (gyro + accel axes only)
# Asymmetric to prevent boundary crossing between speed-discriminated classes.
# SLOG/POWER DRIVE: scale up only — never soften into Drive territory
# DRIVE/DEFENCE:    scale down only — never push into Power territory
SCALE_RANGES = {
    "SLOG":              (1.00, 1.20),
    "POWER DRIVE":       (1.00, 1.20),
    "DRIVE/DEFENCE":     (0.80, 1.00),
    "DEFLECTION/GUIDE":  (0.85, 1.05),
    # All spatially-discriminated classes get a tight symmetric range
    "PULL/HOOK":         (0.90, 1.10),
    "GLANCE/FLICK":      (0.90, 1.10),
    "CUT/PUNCH":         (0.90, 1.10),
    "SWEEP":             (0.90, 1.10),
}

# ─── Shot class normalisation ─────────────────────────────────────────────────
def normalize_shot_class(shot_name):
    if not shot_name:
        return "Unknown"
    s = shot_name.lower().strip()
    if "pull" in s or "hook" in s:
        return "PULL/HOOK"
    if "sweep" in s:
        return "SWEEP"
    if "flick" in s or "glance" in s:
        return "GLANCE/FLICK"
    if "cut" in s or "punch" in s:
        return "CUT/PUNCH"
    if "guide" in s or "glide" in s or "deflection" in s or "deflect" in s:
        return "DEFLECTION/GUIDE"
    if "power drive" in s:
        return "POWER DRIVE"
    if "slog" in s or "power shot" in s or "power hit" in s or "loft" in s:
        return "SLOG"
    if any(t in s for t in ["drive", "defence", "defense", "push", "straight", "forward", "block"]):
        return "DRIVE/DEFENCE"
    return "Unknown"

# ─── Quaternion helpers ───────────────────────────────────────────────────────
def quat_from_axis_angle(axis, angle_rad):
    """Create a unit quaternion [x, y, z, w] from an axis + angle."""
    ax = np.array(axis, dtype=float)
    ax = ax / np.linalg.norm(ax)
    s = math.sin(angle_rad / 2.0)
    return np.array([ax[0]*s, ax[1]*s, ax[2]*s, math.cos(angle_rad / 2.0)])

def multiply_quats(q1, q2):
    x1, y1, z1, w1 = q1
    x2, y2, z2, w2 = q2
    return np.array([
        w1*x2 + x1*w2 + y1*z2 - z1*y2,
        w1*y2 - x1*z2 + y1*w2 + z1*x2,
        w1*z2 + x1*y2 - y1*x2 + z1*w2,
        w1*w2 - x1*x2 - y1*y2 - z1*z2,
    ])

def rotation_matrix_from_euler(rx_deg, ry_deg):
    """3×3 rotation matrix from X-then-Y Euler angles (degrees)."""
    rx = math.radians(rx_deg)
    ry = math.radians(ry_deg)
    Rx = np.array([
        [1,             0,              0],
        [0,  math.cos(rx), -math.sin(rx)],
        [0,  math.sin(rx),  math.cos(rx)],
    ])
    Ry = np.array([
        [ math.cos(ry), 0, math.sin(ry)],
        [0,             1,            0],
        [-math.sin(ry), 0, math.cos(ry)],
    ])
    return Ry @ Rx

# ─── Sensor loading ───────────────────────────────────────────────────────────
def load_sensors(session_dir):
    """Load the 4 augmentable sensor streams from a live session directory."""
    sensors = {}
    for name, fname in [
        ("gyro",        "WatchGyroscope.csv"),
        ("accel",       "WatchAccelerometer.csv"),
        ("gravity",     "WatchGravity.csv"),
        ("game_orient", "WatchGameOrientation.csv"),
    ]:
        gz = os.path.join(session_dir, fname + ".gz")
        plain = os.path.join(session_dir, fname)
        if os.path.exists(gz):
            df = pd.read_csv(gz)
            if len(df) > 0:
                sensors[name] = df
        elif os.path.exists(plain):
            df = pd.read_csv(plain)
            if len(df) > 0:
                sensors[name] = df
    return sensors

# ─── Window slicing ───────────────────────────────────────────────────────────
def slice_window(df, t_center, before, after):
    """Return rows within [t_center-before, t_center+after]."""
    mask = (df['seconds_elapsed'] >= t_center - before) & \
           (df['seconds_elapsed'] <= t_center + after)
    return df[mask].copy().reset_index(drop=True)

# ─── Augmentation techniques ──────────────────────────────────────────────────

def apply_rotation(windows, rx_deg, ry_deg):
    """
    Apply a 3D rotation (X then Y Euler angles) to gyro, accel, gravity
    x/y/z columns, and compose the rotation quaternion into game_orient.
    """
    R = rotation_matrix_from_euler(rx_deg, ry_deg)
    augmented = {}

    for name in ("gyro", "accel", "gravity"):
        if name not in windows:
            continue
        df = windows[name].copy()
        xyz = df[['x', 'y', 'z']].values  # shape (N, 3)
        rotated = (R @ xyz.T).T
        df['x'] = rotated[:, 0]
        df['y'] = rotated[:, 1]
        df['z'] = rotated[:, 2]
        augmented[name] = df

    if "game_orient" in windows:
        df = windows["game_orient"].copy()
        # Build quaternion for this rotation: compose around Y axis then X
        q_rot = quat_from_axis_angle([0, 1, 0], math.radians(ry_deg))
        q_rot = multiply_quats(q_rot, quat_from_axis_angle([1, 0, 0], math.radians(rx_deg)))
        q_rot = q_rot / np.linalg.norm(q_rot)
        rows_qx, rows_qy, rows_qz, rows_qw = [], [], [], []
        for _, row in df.iterrows():
            q_orig = np.array([row['qx'], row['qy'], row['qz'], row['qw']])
            q_new  = multiply_quats(q_rot, q_orig)
            q_new  = q_new / np.linalg.norm(q_new)
            rows_qx.append(q_new[0])
            rows_qy.append(q_new[1])
            rows_qz.append(q_new[2])
            rows_qw.append(q_new[3])
        df['qx'] = rows_qx
        df['qy'] = rows_qy
        df['qz'] = rows_qz
        df['qw'] = rows_qw
        augmented["game_orient"] = df

    return augmented


def apply_time_warp(windows, warp_factor):
    """
    Stretch or compress the time axis by warp_factor using cubic spline
    interpolation, then resample back to the original number of rows.
    Factor > 1.0 slows the shot down; < 1.0 speeds it up.
    Clipped to ±10% of original duration.
    """
    augmented = {}
    for name, df in windows.items():
        if len(df) < 4:
            augmented[name] = df.copy()
            continue

        t_orig  = df['seconds_elapsed'].values
        t_min, t_max = t_orig[0], t_orig[-1]
        duration = t_max - t_min

        # New warped time axis (same start, compressed/stretched end)
        t_warped = t_min + np.linspace(0, duration * warp_factor, len(t_orig))

        # Spline-interpolate each data column back onto original time grid
        df_out = df.copy()
        data_cols = [c for c in df.columns if c not in ('time', 'seconds_elapsed')]
        for col in data_cols:
            cs = CubicSpline(t_warped, df[col].values, extrapolate=True)
            df_out[col] = cs(t_orig)

        augmented[name] = df_out
    return augmented


def apply_magnitude_scale(windows, scale, normalized_class):
    """
    Multiply gyro and accel x/y/z amplitudes by scale.
    Gravity is left unchanged (it reflects gravitational field, not bat force).
    game_orient quaternions are left unchanged (orientation is unit-norm).
    The scale value passed in is already drawn from the class-aware range.
    """
    augmented = {}
    for name, df in windows.items():
        df_out = df.copy()
        if name in ("gyro", "accel"):
            df_out['x'] = df['x'] * scale
            df_out['y'] = df['y'] * scale
            df_out['z'] = df['z'] * scale
        augmented[name] = df_out
    return augmented


def apply_jitter(windows, rng):
    """
    Add independent Gaussian noise to all data channels.
    σ = 0.5% of each channel's standard deviation.
    """
    augmented = {}
    for name, df in windows.items():
        df_out = df.copy()
        data_cols = [c for c in df.columns if c not in ('time', 'seconds_elapsed')]
        for col in data_cols:
            sigma = 0.005 * float(np.std(df[col].values))
            if sigma > 0:
                noise = rng.normal(0, sigma, size=len(df))
                df_out[col] = df[col].values + noise
            # Re-normalise quaternion rows after jitter
            if name == "game_orient" and col == 'qw':
                norms = np.sqrt(
                    df_out['qx']**2 + df_out['qy']**2 +
                    df_out['qz']**2 + df_out['qw']**2
                )
                norms = norms.replace(0, 1)
                df_out['qx'] /= norms
                df_out['qy'] /= norms
                df_out['qz'] /= norms
                df_out['qw'] /= norms
        augmented[name] = df_out
    return augmented

# ─── Output helpers ───────────────────────────────────────────────────────────
SENSOR_OUTNAMES = {
    "gyro":        "WatchGyroscope.csv",
    "accel":       "WatchAccelerometer.csv",
    "gravity":     "WatchGravity.csv",
    "game_orient": "WatchGameOrientation.csv",
}

def write_variant(variant_dir, windows, gt_row, normalized_class, t_impact):
    """Write one synthetic variant to disk."""
    os.makedirs(variant_dir, exist_ok=True)

    for sensor_name, df in windows.items():
        out_path = os.path.join(variant_dir, SENSOR_OUTNAMES[sensor_name])
        df.to_csv(out_path, index=False)

    # Synthetic ground_truth_aligned.csv — single shot row, timestamp anchored
    # to centre of the window (SWING_BEFORE seconds after window start)
    gt_out = pd.DataFrame([{
        "shot_index":              1,
        "shot_number":             gt_row.get("shot_number", ""),
        "audio_time_seconds":      t_impact,
        "sensor_narr_time_seconds": t_impact,
        "impact_time_seconds":     SWING_BEFORE,  # window was re-zeroed
        "impact_timestamp_ns":     0,
        "impact_gyro_mag":         gt_row.get("impact_gyro_mag", 0.0),
        "is_fallback":             False,
        "shot_type":               gt_row.get("shot_type", normalized_class),
        "quality":                 gt_row.get("quality", "good"),
        "narrated_text":           f"[SYNTHETIC] {normalized_class}",
        "blade_angle_deg":         gt_row.get("blade_angle_deg", ""),
        "blade_class":             gt_row.get("blade_class", ""),
        "launch_angle_deg":        gt_row.get("launch_angle_deg", ""),
        "launch_class":            gt_row.get("launch_class", ""),
    }])
    gt_out.to_csv(os.path.join(variant_dir, "ground_truth_aligned.csv"), index=False)


def reindex_time(windows, t_impact):
    """
    Re-zero the seconds_elapsed column so the window starts at 0.0.
    The impact point (t_impact) was at SWING_BEFORE in the original session;
    after slicing the window starts at t_impact - SWING_BEFORE.
    """
    reindexed = {}
    for name, df in windows.items():
        df_out = df.copy()
        t_start = df['seconds_elapsed'].iloc[0]
        df_out['seconds_elapsed'] = df['seconds_elapsed'] - t_start
        reindexed[name] = df_out
    return reindexed

# ─── Main ─────────────────────────────────────────────────────────────────────
def main():
    rng = np.random.default_rng(seed=42)

    # Clear files inside the augmented data directory (avoiding deleting the directory itself
    # to bypass macOS directory lock/indexing race conditions)
    if os.path.exists(AUG_DIR):
        import time
        for root, dirs, files in os.walk(AUG_DIR, topdown=False):
            for name in files:
                path = os.path.join(root, name)
                for attempt in range(5):
                    try:
                        os.remove(path)
                        break
                    except OSError:
                        time.sleep(0.1)
            for name in dirs:
                path = os.path.join(root, name)
                for attempt in range(5):
                    try:
                        os.rmdir(path)
                        break
                    except OSError:
                        time.sleep(0.1)
    else:
        os.makedirs(AUG_DIR)

    # Safety marker — prevents accidental evaluation use
    with open(os.path.join(AUG_DIR, "README.txt"), "w") as f:
        f.write(
            "SYNTHETIC DATA — DO NOT USE FOR EVALUATION\n"
            "===========================================\n"
            "This directory contains programmatically augmented IMU sensor windows\n"
            "derived from real Galaxy Watch sessions.\n\n"
            "These files are consumed ONLY by pipelines/compile_dataset.py to add\n"
            "training feature rows to combined_features.csv.\n\n"
            "SwingDetectorGroundTruthTest.kt and model evaluation ALWAYS use\n"
            "real live_watch_sessions/ data. Never add paths from this directory\n"
            "to TRUSTWORTHY_SESSIONS or the Kotlin test session list.\n"
        )

    # Discover all live sessions that have sensor + GT data
    sessions = sorted([
        d for d in os.listdir(LIVE_DIR)
        if d.startswith("session-") and
           os.path.isdir(os.path.join(LIVE_DIR, d)) and
           os.path.exists(os.path.join(LIVE_DIR, d, "ground_truth_aligned.csv"))
    ])

    print(f"Found {len(sessions)} live sessions to augment from.")

    # ── Pass 1: Collect all usable shot windows grouped by class ──────────────
    # We need the real count per class BEFORE generating anything so the cap
    # is computed relative to actual data representation, not a fixed multiplier.
    from collections import defaultdict
    shots_by_class = defaultdict(list)  # class -> [(session_id, windows_zeroed, gt_row_dict, t_impact, shot_idx)]

    for session_id in sessions:
        session_dir = os.path.join(LIVE_DIR, session_id)
        gt_path = os.path.join(session_dir, "ground_truth_aligned.csv")

        df_gt = pd.read_csv(gt_path)
        sensors = load_sensors(session_dir)

        if "gyro" not in sensors:
            print(f"  ⚠️  {session_id}: no gyro CSV — skipping.")
            continue

        for idx, gt_row in df_gt.iterrows():
            shot_type = str(gt_row.get("shot_type", ""))

            if any(t in shot_type.lower() for t in NON_SWING_TYPES):
                continue

            normalized = normalize_shot_class(shot_type)
            if normalized == "Unknown":
                continue

            t_impact = float(gt_row["impact_time_seconds"])
            shot_idx = int(gt_row["shot_index"]) if "shot_index" in gt_row else idx

            # Slice raw sensor windows for this shot
            windows_raw = {}
            for name, df in sensors.items():
                sliced = slice_window(df, t_impact, SWING_BEFORE, SWING_AFTER)
                if len(sliced) >= 4:
                    windows_raw[name] = sliced

            if "gyro" not in windows_raw:
                continue

            windows_zeroed = reindex_time(windows_raw, t_impact)
            shots_by_class[normalized].append(
                (session_id, windows_zeroed, gt_row.to_dict(), t_impact, shot_idx)
            )

    # Conservative deficit-only balancing:
    # Only augment classes that have fewer real shots than the majority class.
    # Cap each class at MAX_SYNTH_RATIO × its own real count to prevent
    # domain-gap overfitting where synthetic patterns drown out real data.
    max_real = max(len(shots_by_class[cls]) for cls in shots_by_class.keys())

    # Print real class distribution and target synthetic totals
    print("\n  Real shot counts per class and deficit-only balancing targets:")
    for cls in sorted(shots_by_class.keys()):
        real_count = len(shots_by_class[cls])
        deficit = max(0, max_real - real_count)
        capped = min(deficit, real_count * MAX_SYNTH_RATIO)
        ratio = capped / real_count if real_count > 0 else 0.0
        print(f"    {cls:<25} {real_count:>4} real → target {capped:>5} synthetic ({ratio:>5.1f}x multiplier)")

    # ── Pass 2: Generate dynamic variants to perfectly balance all classes ─────
    class_counts = {}
    total_variants = 0

    for cls in sorted(shots_by_class.keys()):
        shot_list  = shots_by_class[cls]
        real_count = len(shot_list)
        deficit = max(0, max_real - real_count)
        target_synthetic = min(deficit, real_count * MAX_SYNTH_RATIO)

        if target_synthetic == 0:
            class_counts[cls] = 0
            continue

        scale_lo, scale_hi = SCALE_RANGES.get(cls, (0.90, 1.10))
        safe_cls = cls.replace("/", "_").replace(" ", "_")

        # Determine dynamic variants per shot for this class
        class_variants_per_shot = int(math.ceil(target_synthetic / real_count)) if real_count > 0 else 0

        generated = 0

        for (session_id, windows_zeroed, gt_row, t_impact, shot_idx) in shot_list:
            if generated >= target_synthetic:
                break

            remaining       = target_synthetic - generated
            n_for_this_shot = min(class_variants_per_shot, remaining)

            for v_idx in range(n_for_this_shot):
                rx_deg = rng.uniform(-15, 15)
                ry_deg = rng.uniform(-15, 15)
                warp   = rng.uniform(0.90, 1.10)
                scale  = rng.uniform(scale_lo, scale_hi)

                w = apply_rotation(windows_zeroed, rx_deg, ry_deg)
                w = apply_time_warp(w, warp)
                w = apply_magnitude_scale(w, scale, cls)
                w = apply_jitter(w, rng)

                variant_name = (
                    f"{safe_cls}__{session_id}"
                    f"__shot{shot_idx:03d}__aug{v_idx:02d}"
                )
                variant_dir = os.path.join(AUG_DIR, variant_name)
                write_variant(variant_dir, w, gt_row, cls, t_impact)

                generated      += 1
                total_variants += 1

        class_counts[cls] = generated

    # ─── Summary ───
    print("\n" + "="*60)
    print(f"  Augmentation complete: {total_variants} synthetic variants written")
    print(f"  Output directory: {AUG_DIR}")
    print("="*60)
    print(f"  {'Shot Class':<25}  {'Real':>6}  {'Synthetic':>9}  {'Ratio':>6}")
    print(f"  {'-'*25}  {'-'*6}  {'-'*9}  {'-'*6}")
    for cls in sorted(class_counts.keys()):
        real  = len(shots_by_class[cls])
        synth = class_counts[cls]
        ratio = synth / real if real > 0 else 0
        print(f"  {cls:<25}  {real:>6}  {synth:>9}  {ratio:>5.1f}x")
    print("="*60)


if __name__ == "__main__":
    main()
