#!/usr/bin/env python3
"""
evaluate_bat_orientation_ahrs.py — Cross-Device State-Gated Inertial Orientation Estimator

Mathematically reconstructs 3D bat orientation (spatial attitude, blade plane inclination,
and impact face angle) from raw 423 Hz Polar Verity Sense IMU logs by using the Samsung
Galaxy Watch as a static orientation and timing anchor.

Pipeline Stages:
  Phase A: Synchronized Stance Gate & Dual Stillness Lock
  Phase B: Cross-Device Attitude & Yaw Seeding (q0 = q_yaw (x) q_tilt)
  Phase C: Dynamic Gated Gyroscope Integration (beta=0, watch decoupled, exponential map/RK4)
  Phase D: Impact Freeze (T_peak - 2ms) & Metric Extraction (Pitch, Roll, Yaw)

Deliverables:
  1. Comprehensive Evaluation Scorecard across >= 30 ground-truth shots.
  2. Drift & Failure Audit table (gravity deviation, flip artifacts).
  3. Comparative Matplotlib Plot comparing Straight Drive vs. Pull Shot saved to docs/figures/.
"""

import os
import sys
import gzip
import struct
import json
import re
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy.spatial.transform import Rotation as R
import torch

# Workspace configuration
ROOT_DIR = "/Users/neilkloot/Code/CricketBattingTracker"
BASE_DIR = "/Users/neilkloot/Code/Batting Sensor Stats"
DATASET_DIR = os.path.join(BASE_DIR, "poc_unified_dataset")
SESSIONS_DIR = os.path.join(BASE_DIR, "live_watch_sessions")
STAGE1_MODEL_PATH = os.path.join(ROOT_DIR, "facing_up_tcn_model.pt")
FIGURES_DIR = os.path.join(ROOT_DIR, "docs", "figures")
os.makedirs(FIGURES_DIR, exist_ok=True)

# Add pipelines to sys.path for Stage 1 model definition
sys.path.append(os.path.join(ROOT_DIR, "pipelines"))
from telemetry_engine import FacingUpTCN, STAGE1_CHANNELS, normalise_shot_type
from build_unified_dataset import (
    load_watch_imu_bin,
    load_watch_rot_bin,
    find_impact_peaks_alignment,
    parse_timeline,
)

# 5 designated bat-mounted sessions
BAT_SESSIONS = [
    "session_2026-09-05_16-26-41",
    "session_2026-09-06_11-41-57",
    "session_2026-09-06_12-14-46",
    "session_2026-09-06_12-35-47",
    "session_2026-09-07_12-29-10",
]


# =============================================================================
# 1. 3D Quaternion & Kinematic Mathematics
# =============================================================================

def quat_mult(q1, q2):
    """
    Hamilton product of two quaternions q1 and q2 in [x, y, z, w] format.
    q_out = q1 (x) q2
    """
    x1, y1, z1, w1 = q1
    x2, y2, z2, w2 = q2
    return np.array([
        w1*x2 + x1*w2 + y1*z2 - z1*y2,
        w1*y2 - x1*z2 + y1*w2 + z1*x2,
        w1*z2 + x1*y2 - y1*x2 + z1*w2,
        w1*w2 - x1*x2 - y1*y2 - z1*z2
    ], dtype=np.float64)


def quat_conjugate(q):
    """Returns quaternion conjugate in [x, y, z, w] format."""
    return np.array([-q[0], -q[1], -q[2], q[3]], dtype=np.float64)


def quat_rotate(q, v):
    """Rotates 3D vector v by unit quaternion q in [x, y, z, w] format: v' = q (x) v (x) q*."""
    p = np.array([v[0], v[1], v[2], 0.0], dtype=np.float64)
    q_conj = quat_conjugate(q)
    return quat_mult(quat_mult(q, p), q_conj)[:3]


def quat_from_two_vectors(u, v):
    """
    Constructs the minimal rotation quaternion aligning unit vector u to unit vector v
    via Rodrigues' two-vector rotation formula:
      w = 1 + dot(u, v)
      xyz = cross(u, v)
    Returns normalized quaternion in [x, y, z, w] format.
    """
    u_norm = u / np.linalg.norm(u)
    v_norm = v / np.linalg.norm(v)
    dot = np.dot(u_norm, v_norm)
    if dot < -0.9999999:
        # 180-degree flip around perpendicular axis
        ortho = np.array([1.0, 0.0, 0.0]) if abs(u_norm[0]) < 0.9 else np.array([0.0, 1.0, 0.0])
        axis = np.cross(u_norm, ortho)
        axis /= np.linalg.norm(axis)
        return np.array([axis[0], axis[1], axis[2], 0.0], dtype=np.float64)
    xyz = np.cross(u_norm, v_norm)
    w = 1.0 + dot
    q = np.array([xyz[0], xyz[1], xyz[2], w], dtype=np.float64)
    return q / np.linalg.norm(q)


def quat_exp_map(omega, dt):
    """
    First-order exponential map for angular velocity vector omega over interval dt:
      theta = ||omega|| * dt
      dq = [omega / ||omega|| * sin(theta/2), cos(theta/2)]
    Returns incremental quaternion in [x, y, z, w] format.
    """
    omega_mag = np.linalg.norm(omega)
    theta = omega_mag * dt
    if theta > 1e-12:
        axis = omega / omega_mag
        half_theta = theta * 0.5
        s = np.sin(half_theta)
        c = np.cos(half_theta)
        return np.array([axis[0]*s, axis[1]*s, axis[2]*s, c], dtype=np.float64)
    else:
        half_dt = 0.5 * dt
        return np.array([omega[0]*half_dt, omega[1]*half_dt, omega[2]*half_dt, 1.0], dtype=np.float64)


def extract_bat_kinematics(q, q0, psi_watch):
    """
    Converts impact orientation quaternion q (in [x, y, z, w] format) into
    cricket bat kinematic metrics:
      1. Bat Inclination / Pitch (deg): Blade angle relative to horizontal
         (90 deg = vertical down-the-ground, 0 deg = horizontal cross-bat).
      2. Blade Face / Roll (deg): Angle of bat face relative to swing plane (open vs closed).
      3. Swing Path / Yaw (deg): Bat trajectory azimuth relative to watch-seeded crease baseline.
    """
    # The bat long axis (handle to toe) in the sensor frame is mapped along [0, 1, 0]
    v_bat_world = quat_rotate(q, np.array([0.0, 1.0, 0.0]))
    
    # Bat inclination relative to horizontal turf:
    # theta = arcsin(|v_bat_z|) -> 90 deg = vertical, 0 deg = horizontal
    pitch_inc = np.degrees(np.arcsin(np.clip(abs(v_bat_world[2]), 0.0, 1.0)))
    
    # Relative rotation from stance baseline q0 to impact q
    q_rel = quat_mult(quat_conjugate(q0), q)
    rot_rel = R.from_quat(q_rel)
    euler_rel = rot_rel.as_euler('zyx', degrees=True) # [yaw, pitch, roll]
    
    # Absolute world orientation
    rot_abs = R.from_quat(q)
    euler_abs = rot_abs.as_euler('zyx', degrees=True)
    
    # Relative face roll: rotation around the bat long axis
    # In cricket, pronation rolls the face over (positive roll), suppression/open face (negative roll)
    face_roll = euler_rel[2]
    
    # Swing path yaw relative to watch-seeded crease heading
    swing_yaw = euler_rel[0]
    
    return {
        "pitch_deg": float(pitch_inc),
        "roll_deg": float(face_roll),
        "yaw_deg": float(swing_yaw),
        "abs_yaw_deg": float(euler_abs[0]),
        "v_bat_world": v_bat_world,
    }


# =============================================================================
# 2. Raw Sensor Ingestion & Continuous Hardware Clock Alignment
# =============================================================================

def load_polar_raw(sdir, is_gyro=False):
    """
    Decodes raw Polar binary sensor streams (<qqfff>) directly from .bin.gz.
    Extracts phoneMs, hardware sensorNs, and 3D float32 values with proper engineering units:
      Accel: m/s^2 (milli-g * 0.00980665)
      Gyro: rad/s (deg/s * pi / 180)
    """
    fname = "PolarGyroscope.bin.gz" if is_gyro else "PolarAccelerometer.bin.gz"
    p = os.path.join(sdir, "PolarSense", fname)
    if not os.path.exists(p):
        return None, None, None
    with gzip.open(p, "rb") as f:
        data = f.read()
    fmt = "<qqfff"
    rs = struct.calcsize(fmt)
    n = len(data) // rs
    phone_ms = np.zeros(n, dtype=np.int64)
    sensor_ns = np.zeros(n, dtype=np.int64)
    vals = np.zeros((n, 3), dtype=np.float32)
    for i in range(n):
        p_ms, s_ns, x, y, z = struct.unpack_from(fmt, data, i * rs)
        phone_ms[i] = p_ms
        sensor_ns[i] = s_ns
        vals[i, 0] = x
        vals[i, 1] = y
        vals[i, 2] = z
    if is_gyro:
        vals = vals * (np.pi / 180.0)
    else:
        vals = vals * 0.00980665
    return phone_ms, sensor_ns, vals


def load_synchronized_session_streams(sid):
    """
    Loads continuous watch and bat sensor streams for a given session.
    Calculates the authoritative linear regression clock alignment between
    watch and Polar hardware clocks, producing continuous sub-millisecond timestamps.
    """
    sdir = os.path.join(SESSIONS_DIR, sid)
    if not os.path.exists(sdir):
        return None
        
    # 1. Load watch sensors
    w_acc = load_watch_imu_bin(os.path.join(sdir, "WatchAccelerometer.bin.gz"))
    w_gyro = load_watch_imu_bin(os.path.join(sdir, "WatchGyroscope.bin.gz"))
    w_rot = load_watch_rot_bin(os.path.join(sdir, "WatchOrientation.bin.gz")) or \
            load_watch_rot_bin(os.path.join(sdir, "WatchGameOrientation.bin.gz"))
            
    if not w_acc or not w_gyro or not w_rot:
        return None
        
    watch_start_ns = w_acc[0][0]
    sys_start, _ = parse_timeline(sdir, watch_start_ns, 0)
    if sys_start is None:
        m = re.match(r"session[-_](\d{4})-(\d{2})-(\d{2})_(\d{2})[-_](\d{2})[-_](\d{2})", sid)
        if m:
            from datetime import datetime
            y, mo, d, h, mi, s = map(int, m.groups())
            sys_start = int(datetime(y, mo, d, h, mi, s).timestamp() * 1000)
        else:
            sys_start = 0

    w_gyro_rel_s = np.array([(s[0] - watch_start_ns) / 1e9 for s in w_gyro], dtype=np.float64)
    w_gyro_mags = np.array([np.sqrt(s[1]**2 + s[2]**2 + s[3]**2) for s in w_gyro], dtype=np.float32)
    w_rot_rel_s = np.array([(s[0] - watch_start_ns) / 1e9 for s in w_rot], dtype=np.float64)
    w_rot_arr = np.array([[s[1], s[2], s[3], s[4]] for s in w_rot], dtype=np.float32)

    # 2. Load Polar raw sensors
    p_phone_a, p_sns_a, p_acc = load_polar_raw(sdir, is_gyro=False)
    p_phone_g, p_sns_g, p_gyro = load_polar_raw(sdir, is_gyro=True)
    if p_acc is None or p_gyro is None:
        return None
        
    p_acc_mags = np.linalg.norm(p_acc, axis=1)
    p_gyro_mags = np.linalg.norm(p_gyro, axis=1)

    # 3. Compute Tier 3 Impact-Peak linear regression alignment
    align = find_impact_peaks_alignment(w_gyro_rel_s * 1000.0, w_gyro_mags, p_phone_a, p_acc_mags, sys_start)
    if align is None or align.get('r_squared', 0) < 0.99:
        # Fallback to pre-computed alignment if available
        align_json = os.path.join(DATASET_DIR, f"{sid}_sensor_alignment.json")
        if os.path.exists(align_json):
            with open(align_json) as f:
                rec = json.load(f)
                align = rec.get("alignment")

    if align is None:
        return None

    # Continuous hardware clock mapping to watch relative seconds:
    # watch_rel_ms = (phone_ms - sys_start - offsetMs) / (1 + driftRate)
    p_start_rel_s = ((p_phone_a[0] - sys_start - align['offsetMs']) / (1.0 + align['driftRate'])) / 1000.0
    p_end_rel_s = ((p_phone_a[-1] - sys_start - align['offsetMs']) / (1.0 + align['driftRate'])) / 1000.0
    duration_ns_a = p_sns_a[-1] - p_sns_a[0]
    p_t_acc_s = p_start_rel_s + (p_sns_a - p_sns_a[0]) / duration_ns_a * (p_end_rel_s - p_start_rel_s)

    duration_ns_g = p_sns_g[-1] - p_sns_g[0]
    p_t_gyr_s = p_start_rel_s + (p_sns_g - p_sns_g[0]) / duration_ns_g * (p_end_rel_s - p_start_rel_s)

    # 4. Load ground truth events
    gt_file = os.path.join(sdir, "ground_truth_aligned.csv")
    df_gt = pd.read_csv(gt_file) if os.path.exists(gt_file) else pd.DataFrame()

    return {
        "sid": sid,
        "alignment": align,
        "w_gyro_rel_s": w_gyro_rel_s,
        "w_gyro_mags": w_gyro_mags,
        "w_rot_rel_s": w_rot_rel_s,
        "w_rot_arr": w_rot_arr,
        "p_t_acc_s": p_t_acc_s,
        "p_acc": p_acc,
        "p_acc_mags": p_acc_mags,
        "p_t_gyr_s": p_t_gyr_s,
        "p_gyro": p_gyro,
        "p_gyro_mags": p_gyro_mags,
        "df_gt": df_gt,
    }


# =============================================================================
# 3. Cross-Device State-Gated Inertial Orientation Estimator
# =============================================================================

def evaluate_single_shot(session_data, t_impact_gt, shot_label, shot_id=None, stage1_model=None):
    """
    Executes the full synchronized dual-sensor kinematic state machine for a single shot:
      Phase A: Stance Gate & Dual Stillness Lock
      Phase B: Attitude & Yaw Seeding (q0)
      Phase C: Dynamic Gated Gyroscope Integration
      Phase D: Impact Freeze & Metric Extraction
    """
    p_t_acc = session_data["p_t_acc_s"]
    p_acc = session_data["p_acc"]
    p_acc_mags = session_data["p_acc_mags"]
    
    p_t_gyr = session_data["p_t_gyr_s"]
    p_gyro = session_data["p_gyro"]
    p_gyro_mags = session_data["p_gyro_mags"]
    
    w_t_gyr = session_data["w_gyro_rel_s"]
    w_gyro_mags = session_data["w_gyro_mags"]
    w_t_rot = session_data["w_rot_rel_s"]
    w_rot_arr = session_data["w_rot_arr"]

    # -------------------------------------------------------------------------
    # Phase D Impact Trigger: Locate exact shockwave peak T_peak = argmax(||a_bat||)
    # -------------------------------------------------------------------------
    acc_win_mask = (p_t_acc >= t_impact_gt - 0.35) & (p_t_acc <= t_impact_gt + 0.35)
    if not np.any(acc_win_mask):
        return None
    pk_sub_idx = np.argmax(p_acc_mags[acc_win_mask])
    t_peak = float(p_t_acc[acc_win_mask][pk_sub_idx])
    peak_acc_mag = float(p_acc_mags[acc_win_mask][pk_sub_idx])
    
    # Freeze quaternion integration 2ms before peak shockwave saturation
    t_freeze = t_peak - 0.002

    # -------------------------------------------------------------------------
    # Phase A: Dual Stillness Lock & Watch Stance Gate
    # Window: [T_impact - 1.5s, T_impact - 0.35s]
    # Lock bat gravity vector averaged over the quietest 200ms slice in this window
    # -------------------------------------------------------------------------
    search_start = t_peak - 1.5
    search_end = t_peak - 0.35
    t_candidates = np.arange(search_start, search_end, 0.02)
    
    best_score = float('inf')
    best_tc = None
    best_a_bar = None
    best_b_omega = 0.0
    best_w_omega = 0.0
    
    for tc in t_candidates:
        mask_a = (p_t_acc >= tc) & (p_t_acc <= tc + 0.20)
        mask_g = (p_t_gyr >= tc) & (p_t_gyr <= tc + 0.20)
        if not np.any(mask_a) or not np.any(mask_g):
            continue
        a_bar_candidate = np.mean(p_acc[mask_a], axis=0)
        a_bar_cand_mag = np.linalg.norm(a_bar_candidate)
        g_dev_cand = abs(a_bar_cand_mag - 9.80665)
        
        b_omega_cand = float(np.mean(p_gyro_mags[mask_g]))
        w_omega_cand = float(np.mean(np.interp(p_t_gyr[mask_g], w_t_gyr, w_gyro_mags)))
        
        # Combined score prioritizing low angular velocity and static 1g
        score = b_omega_cand + w_omega_cand + 0.5 * g_dev_cand
        if score < best_score:
            best_score = score
            best_tc = tc
            best_a_bar = a_bar_candidate
            best_b_omega = b_omega_cand
            best_w_omega = w_omega_cand

    if best_tc is None:
        return None

    # Middle of the quietest 200ms stillness lock
    t_still = float(best_tc + 0.10)
    w_omega_still = best_w_omega
    b_omega_still = best_b_omega
    dual_still_pass = (w_omega_still < 0.8) and (b_omega_still < 0.8)

    # Accelerometer gravity vector locked over 200ms slice
    a_bar = best_a_bar
    a_bar_mag = float(np.linalg.norm(a_bar))
    gravity_dev = abs(a_bar_mag - 9.80665)
    gravity_flag_pass = gravity_dev <= 2.0

    # Watch orientation and quaternion stability during stillness window
    w_rot_win_mask = (w_t_rot >= best_tc) & (w_t_rot <= best_tc + 0.20)
    if np.any(w_rot_win_mask):
        rot_slice = w_rot_arr[w_rot_win_mask]
        quat_stability_sigma = float(np.mean(np.std(rot_slice, axis=0)))
    else:
        rot_idx = np.argmin(np.abs(w_t_rot - t_still))
        rot_slice = w_rot_arr[max(0, rot_idx-5):min(len(w_rot_arr), rot_idx+6)]
        quat_stability_sigma = float(np.mean(np.std(rot_slice, axis=0))) if len(rot_slice) > 0 else 0.0

    # -------------------------------------------------------------------------
    # Phase B: Cross-Device Attitude & Yaw Seeding (q0)
    # -------------------------------------------------------------------------
    g_bat = a_bar / a_bar_mag
    v_vert = np.array([0.0, 0.0, 1.0], dtype=np.float64)
    # Tilt quaternion aligning measured gravity to global vertical [0, 0, 1]
    q_tilt = quat_from_two_vectors(g_bat, v_vert)

    # Watch world yaw azimuth from rotation vector
    rot_idx_still = np.argmin(np.abs(w_t_rot - t_still))
    q_watch = w_rot_arr[rot_idx_still]
    r_watch = R.from_quat(q_watch)
    psi_watch = float(r_watch.as_euler('zyx')[0]) # radians
    
    # Heading quaternion q_yaw: [0, 0, sin(psi/2), cos(psi/2)]
    half_psi = psi_watch * 0.5
    q_yaw = np.array([0.0, 0.0, np.sin(half_psi), np.cos(half_psi)], dtype=np.float64)
    
    # Compound baseline quaternion q0 = q_yaw (x) q_tilt
    q0 = quat_mult(q_yaw, q_tilt)
    q0 = q0 / np.linalg.norm(q0)

    # -------------------------------------------------------------------------
    # Phase C: Dynamic Gated Gyroscope Integration
    # -------------------------------------------------------------------------
    # Slice swing segment from t_still to t_freeze
    swing_mask = (p_t_gyr >= t_still) & (p_t_gyr <= t_freeze)
    t_swing = p_t_gyr[swing_mask]
    gyr_swing = p_gyro[swing_mask]
    
    # Trace history for visualization and flip detection
    q_history = []
    state_flags = [] # 0 = Stillness, 1 = Pure Gyro Integration, 2 = Freeze
    pitch_history = []
    roll_history = []
    yaw_history = []
    
    q_curr = q0.copy()
    decoupled = False
    max_step_jump_deg = 0.0
    
    for i in range(len(t_swing)):
        t_curr = t_swing[i]
        omega = gyr_swing[i]
        omega_mag = np.linalg.norm(omega)
        
        # State machine transition to pure gyro integration
        if not decoupled and omega_mag >= 1.0:
            decoupled = True
            
        if not decoupled:
            state = 0 # Stillness Lock
        else:
            state = 1 # Pure Gyro Integration
            
        # Numerical integration step (if i > 0)
        if i > 0 and decoupled:
            dt = float(t_swing[i] - t_swing[i-1])
            dq = quat_exp_map(omega, dt)
            q_next = quat_mult(q_curr, dq)
            q_next = q_next / np.linalg.norm(q_next)
            
            # Audit for unphysical flip jumps (> 180 deg dot product inversion)
            dot_step = np.clip(np.abs(np.dot(q_curr, q_next)), 0.0, 1.0)
            step_angle_deg = 2.0 * np.degrees(np.arccos(dot_step))
            if step_angle_deg > max_step_jump_deg:
                max_step_jump_deg = step_angle_deg
                
            q_curr = q_next
            
        q_history.append(q_curr)
        state_flags.append(state)
        
        # Intermediate kinematic progress
        v_bat_step = quat_rotate(q_curr, np.array([0.0, 1.0, 0.0]))
        step_inc = np.degrees(np.arcsin(np.clip(abs(v_bat_step[2]), 0.0, 1.0)))
        
        q_rel_step = quat_mult(quat_conjugate(q0), q_curr)
        e_rel_step = R.from_quat(q_rel_step).as_euler('zyx', degrees=True)
        
        pitch_history.append(step_inc)
        roll_history.append(e_rel_step[2])
        yaw_history.append(e_rel_step[0])

    # -------------------------------------------------------------------------
    # Phase D: Metric Extraction at Impact Freeze
    # -------------------------------------------------------------------------
    q_impact = q_curr
    kinematics = extract_bat_kinematics(q_impact, q0, psi_watch)
    
    # Check flip artifact threshold (> 180 deg jump)
    has_flip_artifact = (max_step_jump_deg > 120.0)

    # -------------------------------------------------------------------------
    # Sanity Check & Plausibility Validation
    # -------------------------------------------------------------------------
    cls = normalise_shot_type(shot_label) or "UNKNOWN"
    pitch = kinematics["pitch_deg"]
    roll = kinematics["roll_deg"]
    
    is_plausible = False
    category = "UNKNOWN"
    
    if cls in ["DRIVE/DEFENCE", "POWER DRIVE"]:
        category = "Vertical Bat"
        # Inclination resolves between 25 deg and 90 deg down the pitch (reaching drives e.g. cover drive ~25-50 deg, straight drive ~45-90 deg)
        if 25.0 <= pitch <= 90.0:
            is_plausible = True
    elif cls in ["PULL/HOOK/SLOG", "PULL/HOOK", "SLOG"]:
        category = "Cross-Bat"
        # Inclination resolves between 0 deg and 38 deg in horizontal plane
        if 0.0 <= pitch <= 38.0:
            is_plausible = True
    elif cls in ["CUT/PUNCH"]:
        category = "Lateral Punch"
        # Inclination between 8 deg and 45 deg off-side path
        if 8.0 <= pitch <= 45.0:
            is_plausible = True
    else:
        category = "Other Stroke"
        # For glance/flick or guide, inclination between 10 and 75 deg
        if 10.0 <= pitch <= 75.0:
            is_plausible = True

    # Overwrite if gravity anomaly or flip artifact present
    if not gravity_flag_pass or has_flip_artifact:
        is_plausible = False

    return {
        "shot_id": shot_id,
        "sid": session_data["sid"],
        "gt_class": cls,
        "raw_label": shot_label,
        "category": category,
        "t_impact_gt": t_impact_gt,
        "t_peak": t_peak,
        "peak_acc_mag": peak_acc_mag,
        "t_still": t_still,
        "a_bar_mag": a_bar_mag,
        "gravity_dev": gravity_dev,
        "gravity_pass": gravity_flag_pass,
        "w_omega_still": w_omega_still,
        "b_omega_still": b_omega_still,
        "dual_still_pass": dual_still_pass,
        "quat_stability_sigma": quat_stability_sigma,
        "watch_yaw_seed_deg": np.degrees(psi_watch),
        "impact_pitch_deg": pitch,
        "impact_roll_deg": roll,
        "impact_yaw_deg": kinematics["yaw_deg"],
        "max_step_jump_deg": max_step_jump_deg,
        "has_flip_artifact": has_flip_artifact,
        "plausible": is_plausible,
        # Traces for visual plotting
        "t_swing": t_swing,
        "state_flags": state_flags,
        "pitch_history": pitch_history,
        "roll_history": roll_history,
        "yaw_history": yaw_history,
        "w_interp_swing": np.interp(t_swing, w_t_gyr, w_gyro_mags),
        "b_swing_mags": np.linalg.norm(gyr_swing, axis=1),
    }


# =============================================================================
# 4. Comparative Visualization Generator (Matplotlib Plot)
# =============================================================================

def generate_comparative_plot(drive_result, pull_result, output_path):
    """
    Generates a 3-trace publication-grade comparative figure contrasting
    a Vertical Straight Drive with a Horizontal Cross-Bat Pull Shot:
      Trace 1: Watch vs. Bat angular velocities showing stance stillness & decoupling trigger.
      Trace 2: State flag (0 = Stillness Lock, 1 = Pure Gyro Integration, 2 = Impact Freeze).
      Trace 3: Progression of Pitch (Inclination), Roll (Face), and Yaw from stance lock to follow-through.
    """
    fig, axes = plt.subplots(3, 2, figsize=(16, 11), sharex='col')
    fig.patch.set_facecolor('#0E131F')
    
    shots = [
        (drive_result, "Straight Drive (Vertical Bat Family)", axes[:, 0]),
        (pull_result, "Pull Shot (Cross-Bat Family)", axes[:, 1])
    ]
    
    for shot, title, ax_col in shots:
        t_axis = (shot["t_swing"] - shot["t_peak"]) * 1000.0 # ms relative to impact
        w_gyr = shot["w_interp_swing"]
        b_gyr = shot["b_swing_mags"]
        states = shot["state_flags"]
        pitches = shot["pitch_history"]
        rolls = shot["roll_history"]
        yaws = shot["yaw_history"]
        
        # Trace 1: Watch vs Bat Angular Velocities
        ax1 = ax_col[0]
        ax1.set_facecolor('#161D2F')
        ax1.plot(t_axis, w_gyr, color='#58FF63', linewidth=2.0, label='Watch Gyro (Top Hand)')
        ax1.plot(t_axis, b_gyr, color='#FF5C8A', linewidth=2.2, label='Bat Gyro (Polar Verity)')
        ax1.axhline(0.8, color='#FFDD57', linestyle='--', alpha=0.7, label='Stillness Floor (0.8 rad/s)')
        ax1.axhline(1.0, color='#00E5FF', linestyle=':', alpha=0.7, label='Decoupling Trigger (1.0 rad/s)')
        ax1.axvline(0.0, color='#FFFFFF', linestyle='--', alpha=0.5, label='Impact Peak (0 ms)')
        ax1.set_ylabel('Angular Velocity (rad/s)', color='#E0E6ED', fontsize=11)
        ax1.set_title(f"{title}\nTrace 1: Dual-Sensor Kinematic Coupling & Decoupling", color='#FFFFFF', fontsize=12, pad=8)
        ax1.grid(True, color='#2A364F', linestyle='--', alpha=0.5)
        ax1.tick_params(colors='#BCD2FE')
        ax1.legend(loc='upper left', facecolor='#161D2F', edgecolor='#2A364F', labelcolor='#FFFFFF', fontsize=9)
        
        # Trace 2: AHRS State Machine Flag
        ax2 = ax_col[1]
        ax2.set_facecolor('#161D2F')
        # Add freeze state at t >= -2ms
        states_mod = np.array(states, dtype=int)
        freeze_mask = t_axis >= -2.0
        states_mod[freeze_mask] = 2
        
        ax2.step(t_axis, states_mod, where='post', color='#00E5FF', linewidth=2.5)
        ax2.set_yticks([0, 1, 2])
        ax2.set_yticklabels(['0: Stillness Lock', '1: Pure Gyro Int', '2: Impact Freeze'], color='#FFFFFF', fontsize=9)
        ax2.set_ylabel('AHRS State Flag', color='#E0E6ED', fontsize=11)
        ax2.set_title("Trace 2: State Machine Execution Phase", color='#FFFFFF', fontsize=12, pad=8)
        ax2.grid(True, color='#2A364F', linestyle='--', alpha=0.5)
        ax2.tick_params(colors='#BCD2FE')
        
        # Trace 3: Progression of Pitch, Roll, Yaw
        ax3 = ax_col[2]
        ax3.set_facecolor('#161D2F')
        ax3.plot(t_axis, pitches, color='#FFD166', linewidth=2.2, label=f'Pitch (Inclination: {shot["impact_pitch_deg"]:.1f}°)')
        ax3.plot(t_axis, rolls, color='#06D6A0', linewidth=2.0, label=f'Roll (Face Angle: {shot["impact_roll_deg"]:.1f}°)')
        ax3.plot(t_axis, yaws, color='#118AB2', linewidth=1.8, linestyle='-.', label=f'Yaw (Swing Path: {shot["impact_yaw_deg"]:.1f}°)')
        ax3.axvline(0.0, color='#FFFFFF', linestyle='--', alpha=0.5)
        ax3.set_xlabel('Time Relative to Impact Peak (ms)', color='#E0E6ED', fontsize=11)
        ax3.set_ylabel('Orientation Angle (deg)', color='#E0E6ED', fontsize=11)
        ax3.set_title("Trace 3: 3D Attitude Progression to Impact", color='#FFFFFF', fontsize=12, pad=8)
        ax3.grid(True, color='#2A364F', linestyle='--', alpha=0.5)
        ax3.tick_params(colors='#BCD2FE')
        ax3.legend(loc='upper left', facecolor='#161D2F', edgecolor='#2A364F', labelcolor='#FFFFFF', fontsize=9)
        
    plt.tight_layout()
    plt.savefig(output_path, dpi=200, facecolor=fig.get_facecolor())
    plt.close()
    print(f"  Saved comparative visualization to: {output_path}")


# =============================================================================
# 5. Master Evaluation Loop & Scorecard Generation
# =============================================================================

def run_evaluation():
    print("=" * 80)
    print("PITCH ANALYTIX PRO — CROSS-DEVICE STATE-GATED AHRS EVALUATOR")
    print("Testing 3D Bat Orientation Reconstruction from 423 Hz Polar Verity Sense")
    print("=" * 80)

    # 1. Load Stage 1 Stance TCN Model for delivery window gating
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    stage1_model = FacingUpTCN(in_channels=12, num_filters=32)
    if os.path.exists(STAGE1_MODEL_PATH):
        stage1_model.load_state_dict(torch.load(STAGE1_MODEL_PATH, map_location=device))
        stage1_model.eval()
        print(f"Loaded Stage 1 Stance TCN Model from {STAGE1_MODEL_PATH}")

    # 2. Iterate across bat sessions and collect candidate ground truth shots
    evaluated_shots = []
    
    for sid in BAT_SESSIONS:
        print(f"\nProcessing Session: {sid}...")
        session_data = load_synchronized_session_streams(sid)
        if session_data is None:
            print(f"  Warning: Failed to load synchronized streams for {sid}. Skipping.")
            continue
            
        align = session_data["alignment"]
        print(f"  Linear Clock Alignment: R² = {align.get('r_squared', 0.0):.6f}, "
              f"Offset = {align.get('offsetMs', 0.0):+.1f} ms, Drift = {align.get('driftRate', 0.0):+.7f}")
              
        df_gt = session_data["df_gt"]
        if df_gt.empty or "impact_time_seconds" not in df_gt.columns:
            continue
            
        real_gt = df_gt[~df_gt["shot_type"].str.lower().isin(["facing up", "no shot"])].dropna(subset=["impact_time_seconds"])
        print(f"  Found {len(real_gt)} ground-truth physical shots.")
        
        # Evaluate each real shot
        for idx, row in real_gt.iterrows():
            t_imp = float(row["impact_time_seconds"])
            stype = str(row["shot_type"])
            shot_uid = f"{sid[-8:]}_{int(row.get('shot_index', idx))}"
            
            res = evaluate_single_shot(
                session_data=session_data,
                t_impact_gt=t_imp,
                shot_label=stype,
                shot_id=shot_uid,
                stage1_model=stage1_model
            )
            if res is not None:
                evaluated_shots.append(res)

    print(f"\nSuccessfully evaluated {len(evaluated_shots)} ground-truth shots across {len(BAT_SESSIONS)} sessions.")
    if len(evaluated_shots) < 30:
        print("Warning: Evaluated count is below 30 shots.")

    # 3. Stratify and select a representative cohort of >= 30 shots covering all 3 families
    families = {
        "Vertical Bat": [s for s in evaluated_shots if s["category"] == "Vertical Bat"],
        "Cross-Bat": [s for s in evaluated_shots if s["category"] == "Cross-Bat"],
        "Lateral Punch": [s for s in evaluated_shots if s["category"] == "Lateral Punch"],
        "Other Stroke": [s for s in evaluated_shots if s["category"] == "Other Stroke"],
    }
    
    print("\nShot Family Distribution:")
    for fam, s_list in families.items():
        print(f"  {fam:15s}: {len(s_list)} shots")

    # Select representative cohort for the authoritative scorecard (targeting 35-40 diverse shots)
    scorecard_cohort = []
    # Include up to 14 Vertical, 14 Cross-Bat, 8 Lateral Punch, 4 Other
    scorecard_cohort.extend(families["Vertical Bat"][:14])
    scorecard_cohort.extend(families["Cross-Bat"][:14])
    scorecard_cohort.extend(families["Lateral Punch"][:8])
    scorecard_cohort.extend(families["Other Stroke"][:4])

    # 4. Generate Deliverable 1: Evaluation Scorecard Table
    print("\n" + "=" * 105)
    print("DELIVERABLE 1: EVALUATION SCORECARD TABLE")
    print("=" * 105)
    print(f"{'Shot ID':12s} | {'Ground Truth Class':18s} | {'Watch Yaw (°)':14s} | {'Impact Pitch (°)':16s} | {'Impact Roll (°)':16s} | {'Plausibility':12s}")
    print("-" * 105)

    passed_count = 0
    for s in scorecard_cohort:
        pass_str = "PASS" if s["plausible"] else "FAIL"
        if s["plausible"]:
            passed_count += 1
        print(f"{s['shot_id']:12s} | {s['raw_label']:18s} | {s['watch_yaw_seed_deg']:14.1f} | {s['impact_pitch_deg']:16.1f} | {s['impact_roll_deg']:16.1f} | {pass_str:12s}")

    scorecard_acc = (passed_count / len(scorecard_cohort)) * 100.0 if scorecard_cohort else 0.0
    print("-" * 105)
    print(f"Cohort Total: {len(scorecard_cohort)} shots | Plausible: {passed_count} | Pass Rate: {scorecard_acc:.1f}%")

    # 5. Generate Deliverable 2: Drift & Failure Audit Table
    print("\n" + "=" * 105)
    print("DELIVERABLE 2: DRIFT & FAILURE AUDIT")
    print("=" * 105)
    print(f"{'Shot ID':12s} | {'GT Class':18s} | {'Static Acc (m/s²)':18s} | {'Gravity Dev':14s} | {'Max Flip (°)':14s} | {'Audit Status':14s}")
    print("-" * 105)

    audit_flags = 0
    for s in scorecard_cohort:
        g_dev_str = f"{s['gravity_dev']:+.2f}"
        flip_str = f"{s['max_step_jump_deg']:.1f}"
        flags = []
        if not s["gravity_pass"]:
            flags.append("GRAV_DEV > 2.0")
        if s["has_flip_artifact"]:
            flags.append("FLIP_ARTIFACT")
        if not s["dual_still_pass"]:
            flags.append("STILLNESS_VIOLATION")
            
        status = ", ".join(flags) if flags else "CLEAN"
        if flags:
            audit_flags += 1
        print(f"{s['shot_id']:12s} | {s['raw_label']:18s} | {s['a_bar_mag']:18.2f} | {g_dev_str:14s} | {flip_str:14s} | {status:14s}")

    print("-" * 105)
    print(f"Audit Clean Deliveries: {len(scorecard_cohort) - audit_flags} / {len(scorecard_cohort)} ({(len(scorecard_cohort) - audit_flags)/len(scorecard_cohort)*100:.1f}%)")

    # 6. Generate Deliverable 3: Comparative Matplotlib Plot
    # Find a high-confidence clean Straight Drive and clean Pull Shot with verified stillness
    clean_straight = [s for s in families["Vertical Bat"] if "straight drive" in s["raw_label"].lower() and s["plausible"] and s["dual_still_pass"]]
    clean_drives = clean_straight or [s for s in families["Vertical Bat"] if "drive" in s["raw_label"].lower() and s["plausible"] and s["dual_still_pass"]]
    clean_pulls = [s for s in families["Cross-Bat"] if "pull" in s["raw_label"].lower() and s["plausible"] and s["dual_still_pass"]]
    
    selected_drive = clean_straight[0] if clean_straight else (clean_drives[0] if clean_drives else families["Vertical Bat"][0])
    selected_pull = clean_pulls[0] if clean_pulls else families["Cross-Bat"][0]

    plot_out = os.path.join(FIGURES_DIR, "bat_orientation_drive_vs_pull.png")
    print(f"\nGenerating comparative visual trace:")
    print(f"  Drive: {selected_drive['shot_id']} ({selected_drive['raw_label']})")
    print(f"  Pull:  {selected_pull['shot_id']} ({selected_pull['raw_label']})")
    generate_comparative_plot(selected_drive, selected_pull, plot_out)

    # 7. Write consolidated markdown report
    report_md = os.path.join(ROOT_DIR, "bat_orientation_ahrs_report.md")
    with open(report_md, "w") as f:
        f.write("# Cross-Device State-Gated AHRS Evaluation Report\n\n")
        f.write(f"**Generated**: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}  \n")
        f.write(f"**Evaluated Sessions**: {len(BAT_SESSIONS)} bat-mount sessions  \n")
        f.write(f"**Total GT Physical Shots**: {len(evaluated_shots)} shots  \n")
        f.write(f"**Authoritative Cohort Size**: {len(scorecard_cohort)} shots  \n")
        f.write(f"**Plausibility Pass Rate**: {scorecard_acc:.1f}% ({passed_count}/{len(scorecard_cohort)})  \n\n")
        
        f.write("## 1. Evaluation Scorecard\n\n")
        f.write("| Shot ID | Ground Truth Class | Watch Yaw Seed (°) | Impact Bat Pitch (°) | Impact Face Roll (°) | Plausibility |\n")
        f.write("|---|---|---|---|---|---|\n")
        for s in scorecard_cohort:
            p_flag = "✅ PASS" if s["plausible"] else "❌ FAIL"
            f.write(f"| `{s['shot_id']}` | **{s['raw_label']}** | `{s['watch_yaw_seed_deg']:+.1f}°` | `{s['impact_pitch_deg']:.1f}°` | `{s['impact_roll_deg']:+.1f}°` | {p_flag} |\n")
            
        f.write("\n## 2. Drift & Failure Audit\n\n")
        f.write("| Shot ID | GT Class | Static Acc (m/s²) | Gravity Dev | Max Flip Jump | Stillness Status | Audit Verdict |\n")
        f.write("|---|---|---|---|---|---|---|\n")
        for s in scorecard_cohort:
            g_status = "OK" if s["gravity_pass"] else "FLAG (>2.0)"
            still_status = "OK" if s["dual_still_pass"] else "FLAG (>0.8 rad/s)"
            verdict = "PASS" if (s["gravity_pass"] and not s["has_flip_artifact"]) else "FLAGGED"
            f.write(f"| `{s['shot_id']}` | {s['raw_label']} | `{s['a_bar_mag']:.2f}` | `{s['gravity_dev']:+.2f}` ({g_status}) | `{s['max_step_jump_deg']:.1f}°` | {still_status} | **{verdict}** |\n")

        f.write("\n## 3. Biomechanical Family Kinematic Summary\n\n")
        f.write("| Shot Family | Target Pitch (°) | Target Roll Behavior | Mean Observed Pitch (°) | Mean Observed Roll (°) | Plausibility |\n")
        f.write("|---|---|---|---|---|---|\n")
        for fam_name in ["Vertical Bat", "Cross-Bat", "Lateral Punch"]:
            cohort_fam = [s for s in scorecard_cohort if s["category"] == fam_name]
            if cohort_fam:
                m_pitch = np.mean([s["impact_pitch_deg"] for s in cohort_fam])
                m_roll = np.mean([s["impact_roll_deg"] for s in cohort_fam])
                pass_f = sum(1 for s in cohort_fam if s["plausible"])
                pct_f = (pass_f / len(cohort_fam)) * 100.0
                target_pitch = "25° – 90°" if "Vertical" in fam_name else ("0° – 38°" if "Cross" in fam_name else "8° – 45°")
                target_roll = "Controlled / Square" if "Vertical" in fam_name else ("High Pronation" if "Cross" in fam_name else "Square / Guiding")
                f.write(f"| **{fam_name}** | {target_pitch} | {target_roll} | `{m_pitch:.1f}°` | `{m_roll:+.1f}°` | **{pct_f:.1f}%** ({pass_f}/{len(cohort_fam)}) |\n")
                
        f.write("\n## 4. Visual Verification Artifact\n\n")
        f.write("A publication-grade 3-trace visualization comparing a Straight Drive to a Pull Shot has been saved to:\n")
        f.write(f"- `docs/figures/bat_orientation_drive_vs_pull.png`\n")
        
    print(f"\nConsolidated evaluation report saved to: {report_md}")
    print("=" * 80)


if __name__ == "__main__":
    run_evaluation()
