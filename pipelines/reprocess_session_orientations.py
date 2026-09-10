#!/usr/bin/env python3
"""
pipelines/reprocess_session_orientations.py — Batch Reprocessing for 3D Bat & Wrist Orientations

1. Loads synchronized dual-sensor streams for physical batting sessions.
2. Evaluates physical sensor plausibility and detachment guards (KinematicGuard).
3. Reconstructs 3D orientation (attitude, blade pitch, face roll, swing yaw, wrist angle)
   using the State-Gated AHRS Orientation Estimator.
4. Enriches session unified Parquet files with continuous orientation quaternions.
5. Backfills ground_truth_aligned.csv with the 7 authoritative orientation & validity columns.
"""

import os
import sys
import argparse
import glob
import re
import numpy as np
import pandas as pd
from scipy.spatial.transform import Rotation as R

ROOT_DIR = "/Users/neilkloot/Code/CricketBattingTracker"
BASE_DIR = "/Users/neilkloot/Code/Batting Sensor Stats"
DATASET_DIR = os.path.join(BASE_DIR, "poc_unified_dataset")
SESSIONS_DIR = os.path.join(BASE_DIR, "live_watch_sessions")

sys.path.append(os.path.join(ROOT_DIR, "pipelines"))
from orientation_ahrs import StateGatedOrientationEstimator, load_polar_raw
from kinematic_guard import KinematicGuard, GuardResult
from build_unified_dataset import (
    load_watch_imu_bin,
    load_watch_rot_bin,
    find_impact_peaks_alignment,
    parse_timeline,
)


def load_session_streams(session_id):
    """Loads synchronized watch and Polar IMU streams with clock alignment."""
    sdir = os.path.join(SESSIONS_DIR, session_id)
    if not os.path.exists(sdir):
        return None

    w_acc = load_watch_imu_bin(os.path.join(sdir, "WatchAccelerometer.bin.gz"))
    w_gyro = load_watch_imu_bin(os.path.join(sdir, "WatchGyroscope.bin.gz"))
    w_rot = load_watch_rot_bin(os.path.join(sdir, "WatchOrientation.bin.gz")) or \
            load_watch_rot_bin(os.path.join(sdir, "WatchGameOrientation.bin.gz"))
            
    if not w_acc or not w_gyro or not w_rot:
        return None

    watch_start_ns = w_acc[0][0]
    sys_start, _ = parse_timeline(sdir, watch_start_ns, 0)
    if sys_start is None:
        m = re.match(r"session[-_](\d{4})-(\d{2})-(\d{2})_(\d{2})[-_](\d{2})[-_](\d{2})", session_id)
        if m:
            from datetime import datetime
            y, mo, d, h, mi, s = map(int, m.groups())
            sys_start = int(datetime(y, mo, d, h, mi, s).timestamp() * 1000)
        else:
            sys_start = 0

    w_t_acc_s = np.array([(s[0] - watch_start_ns) / 1e9 for s in w_acc], dtype=np.float64)
    w_acc_arr = np.array([[s[1], s[2], s[3]] for s in w_acc], dtype=np.float32)
    w_acc_mags = np.linalg.norm(w_acc_arr, axis=1)

    w_gyro_rel_s = np.array([(s[0] - watch_start_ns) / 1e9 for s in w_gyro], dtype=np.float64)
    w_gyro_arr = np.array([[s[1], s[2], s[3]] for s in w_gyro], dtype=np.float32)
    w_gyro_mags = np.linalg.norm(w_gyro_arr, axis=1)

    w_rot_rel_s = np.array([(s[0] - watch_start_ns) / 1e9 for s in w_rot], dtype=np.float64)
    w_rot_arr = np.array([[s[1], s[2], s[3], s[4]] for s in w_rot], dtype=np.float32)

    p_phone_a, p_sns_a, p_acc = load_polar_raw(sdir, is_gyro=False)
    p_phone_g, p_sns_g, p_gyro = load_polar_raw(sdir, is_gyro=True)
    if p_acc is None or p_gyro is None:
        return None

    # Compute Tier 3 Impact-Peak linear regression alignment
    p_acc_mags = np.linalg.norm(p_acc, axis=1)
    align = find_impact_peaks_alignment(w_gyro_rel_s * 1000.0, w_gyro_mags, p_phone_a, p_acc_mags, sys_start)
    if align is None or align.get('r_squared', 0) < 0.99:
        align_json = os.path.join(DATASET_DIR, f"{session_id}_sensor_alignment.json")
        if os.path.exists(align_json):
            import json
            with open(align_json) as f:
                rec = json.load(f)
                align = rec.get("alignment")

    if align is None:
        return None

    p_start_rel_s = ((p_phone_a[0] - sys_start - align['offsetMs']) / (1.0 + align['driftRate'])) / 1000.0
    p_end_rel_s = ((p_phone_a[-1] - sys_start - align['offsetMs']) / (1.0 + align['driftRate'])) / 1000.0
    duration_ns_a = p_sns_a[-1] - p_sns_a[0]
    p_t_acc_s = p_start_rel_s + (p_sns_a - p_sns_a[0]) / duration_ns_a * (p_end_rel_s - p_start_rel_s)

    duration_ns_g = p_sns_g[-1] - p_sns_g[0]
    p_t_gyr_s = p_start_rel_s + (p_sns_g - p_sns_g[0]) / duration_ns_g * (p_end_rel_s - p_start_rel_s)

    gt_csv = os.path.join(sdir, "ground_truth_aligned.csv")
    df_gt = pd.read_csv(gt_csv) if os.path.exists(gt_csv) else None

    # Configured mount mode
    mount_mode = "BAT_HANDLE"
    cfg_file = os.path.join(sdir, "session_config.json")
    if os.path.exists(cfg_file):
        try:
            import json
            with open(cfg_file, "r") as f:
                cfg = json.load(f)
                mount_mode = cfg.get("polar_mount_mode", "BAT_HANDLE").upper()
        except Exception:
            pass
    elif df_gt is not None and "polar_mount_mode" in df_gt.columns:
        valid_modes = df_gt["polar_mount_mode"].dropna()
        if not valid_modes.empty:
            mount_mode = valid_modes.iloc[0].upper()

    return {
        "session_id": session_id,
        "sdir": sdir,
        "mount_mode": mount_mode,
        "w_t_acc_s": w_t_acc_s,
        "w_acc_arr": w_acc_arr,
        "w_acc_mags": w_acc_mags,
        "w_gyro_rel_s": w_gyro_rel_s,
        "w_gyro_arr": w_gyro_arr,
        "w_gyro_mags": w_gyro_mags,
        "w_rot_rel_s": w_rot_rel_s,
        "w_rot_arr": w_rot_arr,
        "p_t_acc_s": p_t_acc_s,
        "p_acc": p_acc,
        "p_t_gyr_s": p_t_gyr_s,
        "p_gyro": p_gyro,
        "df_gt": df_gt,
    }


def reprocess_session(session_id):
    """Reprocesses orientation and kinematic validity for a single session."""
    print(f"\n🏏 Reprocessing 3D Orientation: {session_id} ...")
    streams = load_session_streams(session_id)
    if streams is None:
        print(f"⚠️ Unable to load synchronized streams for {session_id}")
        return False

    df_gt = streams["df_gt"]
    if df_gt is None or df_gt.empty:
        print(f"⚠️ No ground truth CSV found for {session_id}")
        return False

    mount_mode = streams["mount_mode"]
    guard = KinematicGuard(configured_mount_mode=mount_mode)
    estimator = StateGatedOrientationEstimator(mount_location=mount_mode)

    blade_pitch_list = []
    face_angle_list = []
    swing_yaw_list = []
    rel_wrist_list = []
    azim_dev_list = []
    mount_type_list = []
    kin_valid_list = []

    shot_quaternions = [] # list of (t_still, t_freeze, q_history, t_history)

    faulted_count = 0
    valid_count = 0

    for idx, row in df_gt.iterrows():
        t_impact = row.get("impact_time_seconds")
        if pd.isna(t_impact):
            t_impact = row.get("sensor_narr_time_seconds", 0.0)
        t_impact = float(t_impact)

        # 1. Run AHRS first to check stillness & metrics
        ahrs_res = estimator.evaluate_shot(
            p_t_acc=streams["p_t_acc_s"],
            p_acc=streams["p_acc"],
            p_t_gyr=streams["p_t_gyr_s"],
            p_gyro=streams["p_gyro"],
            w_t_gyr=streams["w_gyro_rel_s"],
            w_gyro_mags=streams["w_gyro_mags"],
            w_t_rot=streams["w_rot_rel_s"],
            w_rot_arr=streams["w_rot_arr"],
            t_impact_target=t_impact
        )

        # 2. Run Kinematic Guard
        guard_res = guard.evaluate_shot(
            t_impact=t_impact,
            p_t_acc=streams["p_t_acc_s"],
            p_acc=streams["p_acc"],
            p_t_gyr=streams["p_t_gyr_s"],
            p_gyro=streams["p_gyro"],
            w_t_acc=streams["w_t_acc_s"],
            w_acc=streams["w_acc_arr"],
            w_t_gyr=streams["w_gyro_rel_s"],
            w_gyro_mags=streams["w_gyro_mags"],
            ahrs_result=ahrs_res
        )

        if not guard_res.is_kinematically_valid:
            faulted_count += 1
            kin_valid_list.append(False)
            mount_type_list.append("FAULTED_ANOMALY")
            blade_pitch_list.append(np.nan)
            face_angle_list.append(np.nan)
            swing_yaw_list.append(np.nan)
            rel_wrist_list.append(np.nan)
            azim_dev_list.append(np.nan)
            print(f"  🚨 Shot #{idx+1} (t={t_impact:.2f}s): {guard_res.anomaly_reason} -> FAULTED_ANOMALY (Fallback Watch-Only: {guard_res.is_fallback_watch_only})")
        elif ahrs_res is None:
            # Sensor is physically sound and attached; only 3D orientation attitude was unseeded
            valid_count += 1
            kin_valid_list.append(True)
            mount_type_list.append(mount_mode)
            blade_pitch_list.append(np.nan)
            face_angle_list.append(np.nan)
            swing_yaw_list.append(np.nan)
            rel_wrist_list.append(np.nan)
            azim_dev_list.append(np.nan)
            print(f"  ℹ️ Shot #{idx+1} (t={t_impact:.2f}s): STANCE_STILLNESS_NOT_FOUND (Sensor valid, orientation unseeded)")
        else:
            valid_count += 1
            kin_valid_list.append(True)
            mount_type_list.append(mount_mode)
            blade_pitch_list.append(ahrs_res["blade_pitch_deg"])
            face_angle_list.append(ahrs_res["face_angle_deg"])
            swing_yaw_list.append(ahrs_res["swing_yaw_deg"])
            rel_wrist_list.append(ahrs_res["relative_wrist_angle_deg"])
            azim_dev_list.append(ahrs_res["azimuth_deviation_deg"])
            if ahrs_res["q_history"] is not None and len(ahrs_res["q_history"]) > 0:
                shot_quaternions.append((ahrs_res["t_history"], ahrs_res["q_history"]))

    # Update ground_truth_aligned.csv
    df_gt["blade_pitch_deg"] = blade_pitch_list
    df_gt["face_angle_deg"] = face_angle_list
    df_gt["swing_yaw_deg"] = swing_yaw_list
    df_gt["relative_wrist_angle_deg"] = rel_wrist_list
    df_gt["azimuth_deviation_deg"] = azim_dev_list
    df_gt["polar_mount_type"] = mount_type_list
    df_gt["is_kinematically_valid"] = kin_valid_list

    gt_csv = os.path.join(streams["sdir"], "ground_truth_aligned.csv")
    df_gt.to_csv(gt_csv, index=False)
    print(f"  ✅ Updated {gt_csv} ({valid_count} valid shots, {faulted_count} anomalies)")

    # Update unified parquet if exists
    parquet_path = os.path.join(DATASET_DIR, f"{session_id}_unified.parquet")
    if os.path.exists(parquet_path):
        df_pq = pd.read_parquet(parquet_path)
        # Create continuous orientation columns
        n_rows = len(df_pq)
        p_rot_qx = np.zeros(n_rows, dtype=np.float32)
        p_rot_qy = np.zeros(n_rows, dtype=np.float32)
        p_rot_qz = np.zeros(n_rows, dtype=np.float32)
        p_rot_qw = np.zeros(n_rows, dtype=np.float32)

        time_arr = df_pq["time"].values if "time" in df_pq.columns else np.arange(n_rows) / 423.0

        for t_hist, q_hist in shot_quaternions:
            if len(t_hist) < 2:
                continue
            t_min, t_max = t_hist[0], t_hist[-1]
            mask = (time_arr >= t_min) & (time_arr <= t_max)
            if np.any(mask):
                sub_times = time_arr[mask]
                # Interpolate quaternions via Slerp or linear normalized
                sub_qx = np.interp(sub_times, t_hist, q_hist[:, 0])
                sub_qy = np.interp(sub_times, t_hist, q_hist[:, 1])
                sub_qz = np.interp(sub_times, t_hist, q_hist[:, 2])
                sub_qw = np.interp(sub_times, t_hist, q_hist[:, 3])
                norms = np.sqrt(sub_qx**2 + sub_qy**2 + sub_qz**2 + sub_qw**2) + 1e-12
                p_rot_qx[mask] = (sub_qx / norms).astype(np.float32)
                p_rot_qy[mask] = (sub_qy / norms).astype(np.float32)
                p_rot_qz[mask] = (sub_qz / norms).astype(np.float32)
                p_rot_qw[mask] = (sub_qw / norms).astype(np.float32)

        df_pq["p_rot_qx"] = p_rot_qx
        df_pq["p_rot_qy"] = p_rot_qy
        df_pq["p_rot_qz"] = p_rot_qz
        df_pq["p_rot_qw"] = p_rot_qw
        df_pq.to_parquet(parquet_path, index=False)
        print(f"  ✅ Updated {parquet_path} with continuous p_rot_q* channels")

    return True


def main():
    parser = argparse.ArgumentParser(description="Batch reprocess 3D bat & wrist orientations.")
    parser.add_argument("--session", type=str, help="Specific session ID to reprocess")
    parser.add_argument("--all", action="store_true", help="Reprocess all available physical sessions")
    args = parser.parse_args()

    if args.session:
        reprocess_session(args.session)
    elif args.all:
        sessions = sorted([os.path.basename(p) for p in glob.glob(os.path.join(SESSIONS_DIR, "session_*")) if os.path.isdir(p)])
        print(f"Found {len(sessions)} sessions to reprocess.")
        successes = 0
        for s in sessions:
            if reprocess_session(s):
                successes += 1
        print(f"\n🎉 Successfully reprocessed {successes}/{len(sessions)} sessions.")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
