#!/usr/bin/env python3
"""
pipelines/stage3_rules.py — Shared Stage 3 Post-Classification Rule Engine (Python <-> Kotlin Parity)

Provides:
  1. Closed-form hierarchical probability recovery (`recover_hierarchical_probs`) from the
     9-class Stage 2 TCN output vector `q_mid`, matching `BatPlaneGeometryThreeFamilyTCN.forward`.
  2. Candidate-window feature extraction (`extract_candidate_stage3_features`) directly from the
     423 Hz unified Parquet DataFrame with zero ground-truth leakage.
  3. Configurable Stage 3 rule evaluation (`apply_stage3_rules`) returning `(final_pred_cls, fired_rules)`
     driven by `pipelines/stage3_rules_config.json`.
"""

import os
import json
import copy
import math
import numpy as np

ROOT_DIR = "/Users/neilkloot/Code/CricketBattingTracker"
DEFAULT_CONFIG_PATH = os.path.join(ROOT_DIR, "pipelines", "stage3_rules_config.json")

_CACHED_CONFIG = None


def load_stage3_config(config_path=None, force_reload=False):
    """Loads the shared Stage 3 JSON configuration."""
    global _CACHED_CONFIG
    if config_path is None and _CACHED_CONFIG is not None and not force_reload:
        return copy.deepcopy(_CACHED_CONFIG)

    path = config_path or DEFAULT_CONFIG_PATH
    with open(path, "r") as f:
        cfg = json.load(f)

    if config_path is None:
        _CACHED_CONFIG = copy.deepcopy(cfg)
    return cfg


def recover_hierarchical_probs(q_mid):
    """
    Recovers exact hierarchical probabilities from the 9-class TCN probability vector q_mid:
      q[0] = P(no_shot)
      q[1] = 0.0 (pre_shot)
      q[2] = P(is_shot) * P(fam_cross) * P(sub1_pull)
      q[3] = P(is_shot) * P(fam_vert)  * P(sub0_drive)
      q[4] = P(is_shot) * P(fam_vert)  * P(sub0_glance)
      q[5] = P(is_shot) * P(fam_cross) * P(sub1_cut)
      q[6] = P(is_shot) * P(fam_vert)  * P(sub0_defl)
      q[7] = P(is_shot) * (P(fam_vert) + 0.85 * P(fam_cross)) * P(sub0_pd)
      q[8] = P(is_shot) * P(fam_sweep)
    """
    q0 = float(q_mid[0])
    q2 = float(q_mid[2])
    q3 = float(q_mid[3])
    q4 = float(q_mid[4])
    q5 = float(q_mid[5])
    q6 = float(q_mid[6])
    q7 = float(q_mid[7])
    q8 = float(q_mid[8])

    k_vert = q3 + q4 + q6
    a1_cross = q2 + q5
    a2_sweep = q8
    b_coef = k_vert + q7 - 0.85 * a1_cross
    disc = max(0.0, b_coef * b_coef + 3.4 * a1_cross * k_vert)
    a0_vert = 0.5 * (b_coef + math.sqrt(disc))

    denom_fam = a0_vert + a1_cross + a2_sweep + 1e-12
    p_fam_vert = a0_vert / denom_fam
    p_fam_cross = a1_cross / denom_fam
    p_fam_sweep = a2_sweep / denom_fam

    p_sub0_drive = q3 / (a0_vert + 1e-12)
    p_sub0_pd = q7 / (a0_vert + 0.85 * a1_cross + 1e-12)
    p_sub0_glance = q4 / (a0_vert + 1e-12)
    p_sub0_defl = q6 / (a0_vert + 1e-12)

    p_sub1_pull = q2 / (a1_cross + 1e-12)
    p_sub1_cut = q5 / (a1_cross + 1e-12)

    return {
        "p_no_shot": q0,
        "p_is_shot": 1.0 - q0,
        "p_fam_vert": float(p_fam_vert),
        "p_fam_cross": float(p_fam_cross),
        "p_fam_sweep": float(p_fam_sweep),
        "p_sub0_drive": float(p_sub0_drive),
        "p_sub0_pd": float(p_sub0_pd),
        "p_sub0_glance": float(p_sub0_glance),
        "p_sub0_defl": float(p_sub0_defl),
        "p_sub1_pull": float(p_sub1_pull),
        "p_sub1_cut": float(p_sub1_cut),
    }


def extract_candidate_stage3_features(df_parquet, channels_12, f_peak, polar_mount_mode="WRIST"):
    """
    Extracts all kinematic and 3D AHRS features required by Stage 3 rules and the Jev auditor
    directly from the 423 Hz Parquet DataFrame and 12-channel array at anchor frame f_peak.
    """
    num_samples = len(df_parquet)
    f_peak = int(min(max(0, f_peak), num_samples - 1))

    # 1. Sweep crouch & wrist-roll window: [f_peak - 211 : f_peak + 1] (500ms prior at 423 Hz)
    f_start = max(0, f_peak - 211)
    gx_win = channels_12[f_start : f_peak + 1, 6] if channels_12.shape[1] > 6 else np.zeros(f_peak + 1 - f_start)
    gy_win = channels_12[f_start : f_peak + 1, 7] if channels_12.shape[1] > 7 else np.zeros(f_peak + 1 - f_start)
    gz_win = channels_12[f_start : f_peak + 1, 8] if channels_12.shape[1] > 8 else np.zeros(f_peak + 1 - f_start)

    delta_gz = float(np.ptp(gz_win)) if len(gz_win) > 0 else 0.0
    denom = np.sqrt(gx_win**2 + gy_win**2 + 1e-6)
    pitch_deg_arr = np.rad2deg(np.arctan2(gz_win, denom))
    delta_pitch = float(np.ptp(pitch_deg_arr)) if len(pitch_deg_arr) > 0 else 0.0

    w_roll_win = channels_12[f_start : f_peak + 1, 3] if channels_12.shape[1] > 3 else np.zeros(f_peak + 1 - f_start)
    omega_roll = float(np.max(np.abs(w_roll_win))) if len(w_roll_win) > 0 else 0.0

    # Impact gravity z mean in [f_peak - 20 : f_peak + 20] (w_grav_z = channels_12[:, 8])
    imp_s = max(0, f_peak - 20)
    imp_e = min(num_samples, f_peak + 20)
    imp_gz = float(np.mean(channels_12[imp_s:imp_e, 8])) if (channels_12.shape[1] > 8 and imp_e > imp_s) else 6.0

    # Post-impact acceleration ratio & wrist roll delta from Parquet
    post_ratio = float(df_parquet["post_impact_acc_ratio"].iloc[f_peak]) if "post_impact_acc_ratio" in df_parquet.columns else 1.0
    wrist_roll_delta = float(df_parquet["wrist_gyro_roll_delta"].iloc[f_peak]) if "wrist_gyro_roll_delta" in df_parquet.columns else omega_roll
    has_polar = float(df_parquet["has_polar"].iloc[f_peak]) > 0.5 if "has_polar" in df_parquet.columns else False

    # 2. Watch rotation vector pitch (w_rot_q* at f_peak, matching TcnModelRunner.kt sensorMatrix[15..18])
    watch_pitch_deg = None
    if "w_rot_qx" in df_parquet.columns:
        wqx = float(df_parquet["w_rot_qx"].iloc[f_peak])
        wqy = float(df_parquet["w_rot_qy"].iloc[f_peak])
        wqz = float(df_parquet["w_rot_qz"].iloc[f_peak])
        wqw = float(df_parquet["w_rot_qw"].iloc[f_peak])
        if (wqx * wqx + wqy * wqy + wqz * wqz + wqw * wqw) > 0.5:
            wvz = 2.0 * (wqy * wqz - wqx * wqw)
            watch_pitch_deg = float(np.rad2deg(np.arcsin(np.clip(abs(wvz), 0.0, 1.0))))

    # 3. 3D Polar AHRS quaternion features at f_peak (p_rot_q* in Parquet)
    ahrs_valid = False
    ahrs_blade_pitch_deg = None
    ahrs_face_roll_deg = None
    ahrs_swing_yaw_deg = None
    bat_gz_min = 0.0

    if "b_gyro_z" in df_parquet.columns:
        bgz_slice = df_parquet["b_gyro_z"].iloc[max(0, f_peak - 106) : min(num_samples, f_peak + 106)].values
        if len(bgz_slice) > 0:
            bat_gz_min = float(np.min(bgz_slice))

    if "p_rot_qx" in df_parquet.columns:
        qx = float(df_parquet["p_rot_qx"].iloc[f_peak])
        qy = float(df_parquet["p_rot_qy"].iloc[f_peak])
        qz = float(df_parquet["p_rot_qz"].iloc[f_peak])
        qw = float(df_parquet["p_rot_qw"].iloc[f_peak])
        if (qx * qx + qy * qy + qz * qz + qw * qw) > 0.5:
            ahrs_valid = True
            # Long axis [0, 1, 0] rotated by q_freeze -> v_world[2] = 2*(qy*qz + qx*qw)
            bvz = 2.0 * (qy * qz + qx * qw)
            ahrs_blade_pitch_deg = float(np.rad2deg(np.arcsin(np.clip(abs(bvz), 0.0, 1.0))))

            f_still = f_peak
            f_min_scan = max(0, f_peak - 635)
            qx_col = df_parquet["p_rot_qx"].values
            qy_col = df_parquet["p_rot_qy"].values
            qz_col = df_parquet["p_rot_qz"].values
            qw_col = df_parquet["p_rot_qw"].values
            while f_still > f_min_scan:
                prev_idx = f_still - 1
                if (qx_col[prev_idx] ** 2 + qy_col[prev_idx] ** 2 + qz_col[prev_idx] ** 2 + qw_col[prev_idx] ** 2) > 0.5:
                    f_still = prev_idx
                else:
                    break
            qx0, qy0, qz0, qw0 = float(qx_col[f_still]), float(qy_col[f_still]), float(qz_col[f_still]), float(qw_col[f_still])
            qrx = qw0 * qx - qx0 * qw - qy0 * qz + qz0 * qy
            qry = qw0 * qy + qx0 * qz - qy0 * qw - qz0 * qx
            qrz = qw0 * qz - qx0 * qy + qy0 * qx - qz0 * qw
            qrw = qw0 * qw + qx0 * qx + qy0 * qy + qz0 * qz

            ahrs_swing_yaw_deg = float(np.rad2deg(np.arctan2(2.0 * (qrw * qrz - qrx * qry), 1.0 - 2.0 * (qry * qry + qrz * qrz))))
            ahrs_face_roll_deg = float(np.rad2deg(np.arctan2(2.0 * (qrw * qrx - qry * qrz), 1.0 - 2.0 * (qrx * qrx + qry * qry))))

    # 4. Dual-sensor kinematics in [-200ms, +100ms] ([-85, +42] frames around f_peak, matching PhoneSwingDetector.kt)
    win_lo = max(0, f_peak - 85)
    win_hi = min(num_samples, f_peak + 43)
    w_acc_win = channels_12[win_lo:win_hi, 0:3]
    w_gyr_win = channels_12[win_lo:win_hi, 3:6]
    w_acc_mags = np.linalg.norm(w_acc_win, axis=1) if len(w_acc_win) > 0 else np.array([1.0])
    w_gyr_mags = np.linalg.norm(w_gyr_win, axis=1) if len(w_gyr_win) > 0 else np.array([0.01])
    w_acc_peak = float(np.max(w_acc_mags))
    w_gyr_peak = float(np.max(w_gyr_mags))

    bottom_hand_gyro_ratio = 0.0
    bottom_hand_acc_ratio = 0.0
    bottom_hand_time_lead_ms = 0.0

    if has_polar and all(c in df_parquet.columns for c in ("p_acc_x", "p_acc_y", "p_acc_z", "p_gyro_x", "p_gyro_y", "p_gyro_z")):
        p_acc_win = df_parquet[["p_acc_x", "p_acc_y", "p_acc_z"]].iloc[win_lo:win_hi].values
        p_gyr_win = df_parquet[["p_gyro_x", "p_gyro_y", "p_gyro_z"]].iloc[win_lo:win_hi].values
        if len(p_acc_win) > 0:
            p_acc_mags = np.linalg.norm(p_acc_win, axis=1)
            p_gyr_mags = np.linalg.norm(p_gyr_win, axis=1)
            p_acc_peak_idx = int(np.argmax(p_acc_mags))
            p_acc_peak = float(p_acc_mags[p_acc_peak_idx])
            p_gyr_peak = float(np.max(p_gyr_mags))
            if w_gyr_peak > 0.01:
                bottom_hand_gyro_ratio = float(p_gyr_peak / w_gyr_peak)
            if w_acc_peak > 0.01:
                bottom_hand_acc_ratio = float(p_acc_peak / w_acc_peak)
            p_peak_frame = win_lo + p_acc_peak_idx
            if "t_ms" in df_parquet.columns:
                bottom_hand_time_lead_ms = float(df_parquet["t_ms"].iloc[p_peak_frame] - df_parquet["t_ms"].iloc[f_peak])
            else:
                bottom_hand_time_lead_ms = float((p_peak_frame - f_peak) * (1000.0 / 423.0))

    return {
        "delta_gz": delta_gz,
        "delta_pitch": delta_pitch,
        "omega_roll": omega_roll,
        "imp_gz": imp_gz,
        "post_impact_acc_ratio": post_ratio,
        "wrist_roll_delta_rad": wrist_roll_delta,
        "has_polar": has_polar,
        "watch_pitch_deg": watch_pitch_deg,
        "ahrs_valid": ahrs_valid,
        "ahrs_blade_pitch_deg": ahrs_blade_pitch_deg,
        "ahrs_face_roll_deg": ahrs_face_roll_deg,
        "ahrs_swing_yaw_deg": ahrs_swing_yaw_deg,
        "bat_gz_min": bat_gz_min,
        "peak_wrist_gyro_rads": w_gyr_peak,
        "peak_impact_accel_ms2": w_acc_peak,
        "bottom_hand_gyro_ratio": bottom_hand_gyro_ratio,
        "bottom_hand_acc_ratio": bottom_hand_acc_ratio,
        "bottom_hand_time_lead_ms": bottom_hand_time_lead_ms,
    }


def apply_stage3_rules(raw_pred_cls, top_prob, hier_probs, features, polar_mount_mode="WRIST", config=None):
    """
    Applies the configured Stage 3 post-classification gates and disambiguation rules.
    Returns (final_pred_cls, fired_rules).
    """
    if config is None:
        config = load_stage3_config()
    rules_cfg = config.get("rules", {})

    pred_cls = raw_pred_cls
    fired_rules = []

    p_sub0_glance = float(hier_probs.get("p_sub0_glance", 0.0))
    p_fam_sweep = float(hier_probs.get("p_fam_sweep", 0.0))
    p_fam_cross = float(hier_probs.get("p_fam_cross", 0.0))
    p_sub1_pull = float(hier_probs.get("p_sub1_pull", 0.0))
    p_sub1_cut = float(hier_probs.get("p_sub1_cut", 0.0))

    # 1. Calibrated Dual-Path Sweep Gate & Non-Bat Sweep->Glance Mitigation
    if pred_cls == "SWEEP":
        sg_cfg = rules_cfg.get("sweep_dual_path_gate", {})
        if sg_cfg.get("enabled", True):
            delta_pitch = float(features.get("delta_pitch", 0.0))
            delta_gz = float(features.get("delta_gz", 0.0))
            omega_roll = float(features.get("omega_roll", 0.0))

            is_path1 = (
                delta_pitch >= float(sg_cfg.get("path1_delta_pitch_deg", 10.0))
                or delta_gz >= float(sg_cfg.get("path1_delta_gz_ms2", 1.2))
            ) and (top_prob >= float(sg_cfg.get("path1_min_prob", 0.30)))

            is_path2 = (
                omega_roll >= float(sg_cfg.get("path2_min_roll_rads", 1.6))
                and top_prob >= float(sg_cfg.get("path2_min_prob", 0.35))
            )

            if not (is_path1 or is_path2):
                pred_cls = "NO_SHOT"
                fired_rules.append("sweep_dual_path_reject")

        if pred_cls == "SWEEP" and polar_mount_mode != "BAT_HANDLE":
            nb_cfg = rules_cfg.get("non_bat_sweep_to_glance", {})
            if nb_cfg.get("enabled", True):
                imp_gz = float(features.get("imp_gz", 6.0))
                delta_gz = float(features.get("delta_gz", 0.0))
                max_crouch = nb_cfg.get("max_crouch_delta_gz_ms2", 999.0)
                crouch_ok = True if max_crouch is None else (delta_gz < float(max_crouch))
                if (
                    p_sub0_glance >= float(nb_cfg.get("min_sub0_glance", 0.55))
                    and imp_gz < float(nb_cfg.get("max_imp_gz_ms2", 5.5))
                    and p_fam_sweep < float(nb_cfg.get("max_fam_sweep", 0.72))
                    and crouch_ok
                ):
                    pred_cls = "GLANCE/FLICK"
                    fired_rules.append("non_bat_sweep_to_glance")

    # 2. BAT_HANDLE Consistency Gates (Rule 1: Vertical Bat Guard, Rule 2: 3D AHRS Yaw + Axial Roll Glance)
    if polar_mount_mode == "BAT_HANDLE" and pred_cls not in ("NO_SHOT", "no_shot"):
        r1_cfg = rules_cfg.get("bat_vertical_guard_rule1", {})
        if r1_cfg.get("enabled", True):
            wpitch_deg = features.get("watch_pitch_deg")
            if wpitch_deg is not None and float(wpitch_deg) >= float(r1_cfg.get("min_watch_pitch_deg", 65.0)):
                if pred_cls in ("PULL/HOOK/SLOG", "CUT/PUNCH"):
                    post_ratio = float(features.get("post_impact_acc_ratio", 1.0))
                    pred_cls = "POWER DRIVE" if post_ratio >= float(r1_cfg.get("power_drive_post_ratio", 1.35)) else "DRIVE/DEFENCE"
                    fired_rules.append("bat_vertical_guard_rule1")

        r2_cfg = rules_cfg.get("bat_ahrs_glance_rule2", {})
        if r2_cfg.get("enabled", True) and pred_cls in ("DRIVE/DEFENCE", "POWER DRIVE"):
            if features.get("ahrs_valid") and features.get("ahrs_swing_yaw_deg") is not None:
                swing_yaw_deg = float(features["ahrs_swing_yaw_deg"])
                bat_gz_min = float(features.get("bat_gz_min", 0.0))
                path1 = (
                    swing_yaw_deg <= float(r2_cfg.get("yaw_deg_path1", -17.0))
                    and bat_gz_min <= float(r2_cfg.get("bat_gz_min_path1", -11.5))
                    and p_sub0_glance >= float(r2_cfg.get("min_sub0_glance_path1", 0.25))
                )
                path2 = (
                    swing_yaw_deg <= float(r2_cfg.get("yaw_deg_path2", -50.0))
                    and p_sub0_glance >= float(r2_cfg.get("min_sub0_glance_path2", 0.50))
                )
                if path1 or path2:
                    pred_cls = "GLANCE/FLICK"
                    fired_rules.append("bat_ahrs_glance_rule2")

    # 3. Candidate Rule S1: 3D AHRS Flat-Bat Conflict (BAT_HANDLE only)
    s1_cfg = rules_cfg.get("s1_ahrs_flat_bat", {})
    if s1_cfg.get("enabled", False) and polar_mount_mode == "BAT_HANDLE" and pred_cls not in ("NO_SHOT", "no_shot"):
        if features.get("ahrs_valid") and features.get("ahrs_blade_pitch_deg") is not None:
            bpitch = float(features["ahrs_blade_pitch_deg"])
            if bpitch < float(s1_cfg.get("max_blade_pitch_deg", 20.0)) and pred_cls in ("DRIVE/DEFENCE", "POWER DRIVE", "GLANCE/FLICK"):
                post_ratio = float(features.get("post_impact_acc_ratio", 1.0))
                syaw = float(features.get("ahrs_swing_yaw_deg") or 0.0)
                if post_ratio >= float(s1_cfg.get("min_post_impact_ratio_pull", 0.65)):
                    pred_cls = "PULL/HOOK/SLOG"
                    fired_rules.append("s1_ahrs_flat_bat")
                elif syaw <= float(s1_cfg.get("max_yaw_deg_glance", -20.0)):
                    pred_cls = "GLANCE/FLICK"
                    fired_rules.append("s1_ahrs_flat_bat")

    # 4. Candidate Rule S2: Power Drive vs Pull/Hook/Slog Arbitrator
    s2_cfg = rules_cfg.get("s2_power_drive_vs_pull", {})
    if s2_cfg.get("enabled", False) and pred_cls == "POWER DRIVE":
        if (
            p_fam_cross >= float(s2_cfg.get("min_fam_cross", 0.55))
            and p_sub1_pull >= float(s2_cfg.get("min_sub1_pull", 0.75))
        ):
            bpitch = features.get("ahrs_blade_pitch_deg")
            pitch_ok = True
            if polar_mount_mode == "BAT_HANDLE" and features.get("ahrs_valid") and bpitch is not None:
                pitch_ok = float(bpitch) <= float(s2_cfg.get("max_blade_pitch_deg", 35.0))
            if pitch_ok:
                pred_cls = "PULL/HOOK/SLOG"
                fired_rules.append("s2_power_drive_vs_pull")

    # 5. Candidate Rule S3: Cut/Punch Dual-Wrist Lock Recovery
    s3_cfg = rules_cfg.get("s3_cut_punch_recovery", {})
    if s3_cfg.get("enabled", False) and pred_cls in ("DRIVE/DEFENCE", "POWER DRIVE", "PULL/HOOK/SLOG"):
        if features.get("has_polar", False) and polar_mount_mode == "WRIST":
            t_lead = abs(float(features.get("bottom_hand_time_lead_ms", 999.0)))
            if (
                p_sub1_cut >= float(s3_cfg.get("min_sub1_cut", 0.65))
                and p_fam_cross >= float(s3_cfg.get("min_fam_cross", 0.30))
                and t_lead <= float(s3_cfg.get("max_abs_time_lead_ms", 15.0))
            ):
                pred_cls = "CUT/PUNCH"
                fired_rules.append("s3_cut_punch_recovery")

    return pred_cls, fired_rules
