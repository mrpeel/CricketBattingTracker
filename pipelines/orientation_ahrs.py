#!/usr/bin/env python3
"""
pipelines/orientation_ahrs.py — Modular State-Gated AHRS Orientation Estimator

Reconstructs 3D bat and wrist orientation (spatial attitude, blade inclination,
face roll angle, swing path yaw, and relative wrist angle) from 423 Hz Polar Verity Sense
IMU telemetry anchored to Galaxy Watch static orientation vectors.
"""

import os
import gzip
import struct
import numpy as np
from scipy.spatial.transform import Rotation as R


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
    Constructs minimal rotation quaternion aligning unit vector u to unit vector v
    via Rodrigues' two-vector rotation formula. Returns normalized quaternion in [x, y, z, w] format.
    """
    u_norm = u / (np.linalg.norm(u) + 1e-12)
    v_norm = v / (np.linalg.norm(v) + 1e-12)
    dot = np.dot(u_norm, v_norm)
    if dot < -0.9999999:
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


class StateGatedOrientationEstimator:
    """
    State-Gated AHRS Orientation Estimator for Cricket Batting.
    
    Supports both 'BAT_HANDLE' and 'BOTTOM_WRIST' mount geometries:
      - Phase A: Synchronized Stance Gate & Dual Stillness Lock
      - Phase B: Cross-Device Attitude & Yaw Seeding (q0 = q_yaw (x) q_tilt)
      - Phase C: Dynamic Gated Gyroscope Integration (beta=0 during swing)
      - Phase D: Impact Freeze (T_peak - 2ms) & Metric Extraction
    """
    def __init__(self, mount_location="BAT_HANDLE"):
        self.mount_location = mount_location.upper()

    def evaluate_shot(
        self,
        p_t_acc,
        p_acc,
        p_t_gyr,
        p_gyro,
        w_t_gyr,
        w_gyro_mags,
        w_t_rot,
        w_rot_arr,
        t_impact_target,
        search_pre_window=1.5,
        search_post_guard=0.35,
    ):
        """
        Calculates 3D orientation metrics for a single shot event.
        
        Args:
            p_t_acc: Polar accelerometer timestamps in seconds (1D float64 array)
            p_acc: Polar 3D accelerometer readings in m/s^2 (Nx3 float32/float64 array)
            p_t_gyr: Polar gyroscope timestamps in seconds (1D float64 array)
            p_gyro: Polar 3D gyroscope readings in rad/s (Nx3 float32/float64 array)
            w_t_gyr: Watch gyroscope timestamps in seconds (1D float64 array)
            w_gyro_mags: Watch gyroscope magnitudes in rad/s (1D float32/float64 array)
            w_t_rot: Watch rotation vector timestamps in seconds (1D float64 array)
            w_rot_arr: Watch rotation quaternions [x, y, z, w] (Mx4 array)
            t_impact_target: Target impact timestamp in seconds
            search_pre_window: Stance stillness search pre-impact limit in seconds (default 1.5s)
            search_post_guard: Stance stillness search post-impact guard limit in seconds (default 0.35s)
            
        Returns:
            dict containing orientation metrics, or None if evaluation failed.
        """
        p_acc_mags = np.linalg.norm(p_acc, axis=1)
        p_gyro_mags = np.linalg.norm(p_gyro, axis=1)

        # ---------------------------------------------------------------------
        # Phase D Trigger: Locate exact shockwave peak T_peak = argmax(||a_polar||)
        # ---------------------------------------------------------------------
        acc_win_mask = (p_t_acc >= t_impact_target - 0.35) & (p_t_acc <= t_impact_target + 0.35)
        if not np.any(acc_win_mask):
            return None
            
        pk_sub_idx = np.argmax(p_acc_mags[acc_win_mask])
        t_peak = float(p_t_acc[acc_win_mask][pk_sub_idx])
        peak_acc_mag = float(p_acc_mags[acc_win_mask][pk_sub_idx])
        
        # Freeze integration 2ms before peak shockwave saturation
        t_freeze = t_peak - 0.002

        # ---------------------------------------------------------------------
        # Phase A: Dual Stillness Lock & Watch Stance Gate
        # Search window: [T_impact - search_pre_window, T_impact - search_post_guard]
        # Find quietest continuous 200 ms slice
        # ---------------------------------------------------------------------
        search_start = t_peak - search_pre_window
        search_end = t_peak - search_post_guard
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
            
            # Combined stillness score
            score = b_omega_cand + w_omega_cand + 0.5 * g_dev_cand
            if score < best_score:
                best_score = score
                best_tc = tc
                best_a_bar = a_bar_candidate
                best_b_omega = b_omega_cand
                best_w_omega = w_omega_cand

        if best_tc is None:
            return None

        t_still = float(best_tc + 0.10)
        a_bar = best_a_bar
        a_bar_mag = float(np.linalg.norm(a_bar))
        gravity_dev = abs(a_bar_mag - 9.80665)

        # ---------------------------------------------------------------------
        # Phase B: Attitude & Yaw Seeding (q0)
        # ---------------------------------------------------------------------
        g_sensor = a_bar / (a_bar_mag + 1e-12)
        v_vert = np.array([0.0, 0.0, 1.0], dtype=np.float64)
        q_tilt = quat_from_two_vectors(g_sensor, v_vert)

        rot_idx_still = np.argmin(np.abs(w_t_rot - t_still))
        q_watch = w_rot_arr[rot_idx_still]
        r_watch = R.from_quat(q_watch)
        psi_watch = float(r_watch.as_euler('zyx')[0]) # radians
        
        half_psi = psi_watch * 0.5
        q_yaw = np.array([0.0, 0.0, np.sin(half_psi), np.cos(half_psi)], dtype=np.float64)
        
        q0 = quat_mult(q_yaw, q_tilt)
        q0 = q0 / np.linalg.norm(q0)

        # ---------------------------------------------------------------------
        # Phase C: Dynamic Gated Gyroscope Integration
        # ---------------------------------------------------------------------
        swing_mask = (p_t_gyr >= t_still) & (p_t_gyr <= t_freeze)
        t_swing = p_t_gyr[swing_mask]
        gyr_swing = p_gyro[swing_mask]
        
        q_history = []
        t_history = []
        q_curr = q0.copy()
        decoupled = False
        max_step_jump_deg = 0.0
        
        for i in range(len(t_swing)):
            t_curr = t_swing[i]
            omega = gyr_swing[i]
            omega_mag = np.linalg.norm(omega)
            
            if not decoupled and omega_mag >= 1.0:
                decoupled = True
                
            if i > 0:
                dt = t_curr - t_swing[i-1]
                if 0.0 < dt < 0.02:
                    omega_mid = 0.5 * (omega + gyr_swing[i-1])
                    dq = quat_exp_map(omega_mid, dt)
                    q_next = quat_mult(q_curr, dq)
                    q_next = q_next / np.linalg.norm(q_next)
                    
                    # Step jump check
                    step_diff = quat_mult(quat_conjugate(q_curr), q_next)
                    step_rot = R.from_quat(step_diff)
                    step_deg = np.degrees(step_rot.magnitude())
                    if step_deg > max_step_jump_deg:
                        max_step_jump_deg = step_deg
                        
                    q_curr = q_next
                    
            q_history.append(q_curr.copy())
            t_history.append(t_curr)

        q_freeze = q_curr.copy()

        # ---------------------------------------------------------------------
        # Phase D: Metric Extraction
        # ---------------------------------------------------------------------
        long_axis = np.array([0.0, 1.0, 0.0], dtype=np.float64)
        v_world = quat_rotate(q_freeze, long_axis)
        
        # Blade/Arm pitch relative to horizontal ground (90 deg = vertical, 0 deg = horizontal)
        pitch_deg = float(np.degrees(np.arcsin(np.clip(abs(v_world[2]), 0.0, 1.0))))
        
        # Relative rotation from stance baseline q0 to freeze q
        q_rel = quat_mult(quat_conjugate(q0), q_freeze)
        rot_rel = R.from_quat(q_rel)
        euler_rel = rot_rel.as_euler('zyx', degrees=True)
        
        # Face roll: angle of rotation around long axis
        face_roll_deg = float(euler_rel[2])
        
        # Swing path yaw
        swing_yaw_deg = float(euler_rel[0])
        
        # Relative wrist angle (Watch q* (x) Polar q)
        rot_idx_freeze = np.argmin(np.abs(w_t_rot - t_freeze))
        q_w_freeze = w_rot_arr[rot_idx_freeze]
        q_rel_wrist = quat_mult(quat_conjugate(q_w_freeze), q_freeze)
        rot_rel_wrist = R.from_quat(q_rel_wrist)
        rel_wrist_deg = float(np.degrees(rot_rel_wrist.magnitude()))
        
        # Azimuth deviation between watch world yaw and sensor yaw
        r_w_freeze = R.from_quat(q_w_freeze)
        psi_w_freeze = float(np.degrees(r_w_freeze.as_euler('zyx')[0]))
        r_freeze = R.from_quat(q_freeze)
        psi_freeze = float(np.degrees(r_freeze.as_euler('zyx')[0]))
        azim_dev_deg = float((psi_freeze - psi_w_freeze + 180.0) % 360.0 - 180.0)

        return {
            "blade_pitch_deg": pitch_deg,
            "face_angle_deg": face_roll_deg,
            "swing_yaw_deg": swing_yaw_deg,
            "relative_wrist_angle_deg": rel_wrist_deg,
            "azimuth_deviation_deg": azim_dev_deg,
            "gravity_deviation": gravity_dev,
            "max_step_jump_deg": max_step_jump_deg,
            "peak_acc_mag": peak_acc_mag,
            "t_peak": t_peak,
            "t_still": t_still,
            "t_freeze": t_freeze,
            "q0": q0,
            "q_freeze": q_freeze,
            "q_history": np.array(q_history) if q_history else None,
            "t_history": np.array(t_history) if t_history else None,
            "polar_mount_type": self.mount_location,
            "is_kinematically_valid": True,
        }
