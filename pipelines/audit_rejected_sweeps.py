#!/usr/bin/env python3
"""
pipelines/audit_rejected_sweeps.py — Diagnostic Script for Rejected SWEEP Ground-Truth Shots

Audits all 51 physical sessions to determine why ground-truth SWEEP shots were rejected by post-filters:
1. Rejection Count by Torso Tilt Check (delta_pitch < 15 deg and delta_gz < 2.0 m/s^2)
2. Rejection Count by Softmax Floor (P(SWEEP) < 0.45)
3. Rejection Count by 2.4s NMS (suppressed by adjacent peak within 2.4s)
4. Other causes (e.g., candidate anchor extraction, different class prediction)
"""

import os
import sys
import json
import pickle
import numpy as np
import pandas as pd
import torch

from run_multitier_pipeline import (
    ROOT_DIR, BASE_DIR, DATASET_PATH, STAGE1_MODEL_PATH, STAGE2_MODEL_PATH, STATS_PATH,
    UNIFIED_PARQUET_DIR, SESSIONS_DIR, HOLDOUT_SESSIONS, FEATURES, CLASSES, SHOT_CLASSES,
    FacingUpTCN, Stage2TCNClassifier, StanceTracker, estimate_session_clock_offset,
    predict_candidate_batch_unleaked, normalise_shot_type
)

def main():
    print("================================================================================")
    print("       DIAGNOSTIC AUDIT OF REJECTED GROUND-TRUTH SWEEP SHOTS (51 SESSIONS)")
    print("================================================================================")
    
    device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
    print(f"Device: {device}")
    
    with open(DATASET_PATH, "rb") as f:
        dataset = pickle.load(f)
    sessions_data = dataset["sessions_data"]
    
    stage1_model = FacingUpTCN(in_channels=12, num_filters=32).to(device)
    stage1_model.load_state_dict(torch.load(STAGE1_MODEL_PATH, map_location=device))
    stage1_model.eval()

    stage2_model = Stage2TCNClassifier(in_ch=len(FEATURES), num_classes=10).to(device)
    stage2_model.load_state_dict(torch.load(STAGE2_MODEL_PATH, map_location=device))
    stage2_model.eval()

    with open(STATS_PATH, "r") as f:
        norm_stats = json.load(f)

    total_gt_sweeps = 0
    detected_sweeps = 0
    
    rejection_reasons = {
        "tilt_check": 0,
        "softmax_floor": 0,
        "nms_suppression": 0,
        "classified_other": 0,
        "no_candidate_anchor": 0,
    }
    
    audit_log = []
    
    for sid, sess_data in sessions_data.items():
        t_grid = sess_data["t_grid"]
        channels = sess_data["channels"]  # (N, 12)
        num_samples = len(t_grid)
        w_acc_mag = np.linalg.norm(channels[:, 0:3], axis=1)
        w_gyr_mag = np.linalg.norm(channels[:, 3:6], axis=1)
        
        parquet_path = os.path.join(UNIFIED_PARQUET_DIR, f"{sid}_unified.parquet")
        df_parquet = pd.read_parquet(parquet_path) if os.path.exists(parquet_path) else None

        # 1. Stage 1 Stance Windows
        window_len = 423
        stride = 42
        windows = []
        t_mids = []
        w_mags = []
        for start_idx in range(0, num_samples - window_len, stride):
            end_idx = start_idx + window_len
            windows.append(channels[start_idx:end_idx])
            t_mids.append(t_grid[start_idx + window_len // 2])
            w_mags.append(np.max(w_gyr_mag[start_idx:end_idx]))

        if not windows:
            continue

        s1_probs = []
        with torch.no_grad():
            for b in range(0, len(windows), 512):
                b_win = np.array(windows[b:b+512], dtype=np.float32)
                b_tensor = torch.tensor(b_win, dtype=torch.float32).to(device)
                b_logits = stage1_model(b_tensor)
                b_p = torch.sigmoid(b_logits).squeeze(-1).cpu().numpy()
                s1_probs.extend(b_p)

        sm = StanceTracker(sustain_ms=300)
        stance_exits = []
        for i in range(len(s1_probs)):
            was_fu = (sm.state == "FACING_UP")
            _, exited = sm.process_step(s1_probs[i], w_mags[i], dt_ms=100)
            if exited and was_fu:
                stance_exits.append(t_mids[i])

        # Candidate Window Extraction
        candidate_windows = []
        for t_exit in stance_exits:
            f_exit = int(np.searchsorted(t_grid, t_exit))
            f_scan_end = min(num_samples, int(np.searchsorted(t_grid, t_exit + 3.5)))
            if f_scan_end <= f_exit + 10:
                continue

            win_gyr = w_gyr_mag[f_exit:f_scan_end]
            win_acc = w_acc_mag[f_exit:f_scan_end]
            peak_offset = np.argmax(win_gyr)
            peak_f = f_exit + peak_offset
            t_peak = t_grid[peak_f]

            f_pre_300ms = max(0, peak_f - 127)
            delta_theta_backswing = float(np.sum(w_gyr_mag[f_pre_300ms : peak_f + 1]) * (1.0 / 423.0))

            tier = "TIER_1_HIGH" if win_acc[peak_offset] >= 30.0 else "TIER_3_SOFT_TOUCH"
            if win_gyr[peak_offset] >= 1.0 and delta_theta_backswing >= 0.14:
                candidate_windows.append({
                    "tier": tier,
                    "anchor_t": t_peak,
                    "anchor_f": peak_f,
                    "peak_acc": win_acc[peak_offset],
                    "peak_gyr": win_gyr[peak_offset],
                })

        candidate_windows.sort(key=lambda c: c["anchor_t"])

        # Ground Truth Alignment
        gt_path = os.path.join(SESSIONS_DIR, sid, "ground_truth_aligned.csv")
        gt_events = []
        if os.path.exists(gt_path):
            df_gt = pd.read_csv(gt_path)
            for _, row in df_gt.iterrows():
                c_name = normalise_shot_type(str(row.get("shot_type", "")))
                t_sec = float(row.get("sensor_narr_time_seconds", 0.0))
                if c_name:
                    gt_events.append({"t": t_sec, "cls": c_name, "raw": str(row.get("shot_type", ""))})

        dt_offset = estimate_session_clock_offset(gt_events, t_grid, w_gyr_mag)
        aligned_gt = [{"t": g["t"] + dt_offset, "cls": g["cls"], "raw": g["raw"]} for g in gt_events]
        gt_sweeps = [g for g in aligned_gt if g["cls"] == "SWEEP"]
        total_gt_sweeps += len(gt_sweeps)

        if not candidate_windows:
            for g in gt_sweeps:
                rejection_reasons["no_candidate_anchor"] += 1
                audit_log.append({"sid": sid, "gt_t": g["t"], "reason": "no_candidate_anchor"})
            continue

        # Stage 2 Predictions
        candidate_anchors = [c["anchor_f"] for c in candidate_windows]
        preds = predict_candidate_batch_unleaked(df_parquet, candidate_anchors, stage2_model, norm_stats, device)

        # Trace each candidate through the filter logic
        accepted_candidates = []
        last_accepted_t = -999.0
        last_was_sweep = False

        for i_cand, c in enumerate(candidate_windows):
            t_cand = c["anchor_t"]
            pred_cls, top_prob = preds[i_cand]
            f_peak = c["anchor_f"]
            
            # Check kinematics
            f_start = max(0, f_peak - 211)
            gx_win = channels[f_start : f_peak + 1, 6] if channels.shape[1] > 6 else np.zeros(f_peak + 1 - f_start)
            gy_win = channels[f_start : f_peak + 1, 7] if channels.shape[1] > 7 else np.zeros(f_peak + 1 - f_start)
            gz_win = channels[f_start : f_peak + 1, 8] if channels.shape[1] > 8 else np.zeros(f_peak + 1 - f_start)
            
            delta_gz = float(np.ptp(gz_win))
            denom = np.sqrt(gx_win**2 + gy_win**2 + 1e-6)
            pitch_deg = np.rad2deg(np.arctan2(gz_win, denom))
            delta_pitch = float(np.ptp(pitch_deg))

            # Wrist roll velocity (channel 3 = gyro_x / roll)
            w_roll_win = channels[f_start : f_peak + 1, 3] if channels.shape[1] > 3 else np.zeros(f_peak + 1 - f_start)
            omega_roll = float(np.max(np.abs(w_roll_win)))

            initial_pred_cls = pred_cls
            rejected_by = None

            # Filter 1: Softmax floor for SWEEP (< 0.45 -> NO_SHOT)
            if pred_cls == "SWEEP" and top_prob < 0.45:
                pred_cls = "NO_SHOT"
                rejected_by = "softmax_floor"

            # Filter 2: Tilt check for SWEEP
            if pred_cls == "SWEEP" and (delta_pitch < 15.0 and delta_gz < 2.0):
                pred_cls = "NO_SHOT"
                rejected_by = "tilt_check"

            # Filter 3: Dynamic NMS (2.4s for SWEEP, 1.8s for others)
            req_gap = 2.4 if (last_was_sweep or pred_cls == "SWEEP") else 1.8
            if (t_cand - last_accepted_t) < req_gap:
                if initial_pred_cls == "SWEEP" and rejected_by is None:
                    rejected_by = "nms_suppression"
                continue

            if pred_cls == "NO_SHOT":
                continue

            last_accepted_t = t_cand
            last_was_sweep = (pred_cls == "SWEEP")
            accepted_candidates.append({
                "t": t_cand, "pred_cls": pred_cls, "prob": top_prob,
                "delta_pitch": delta_pitch, "delta_gz": delta_gz, "omega_roll": omega_roll
            })

        # Match GT sweeps to candidates
        for g in gt_sweeps:
            matched_cand = next((c for c in accepted_candidates if abs(c["t"] - g["t"]) <= 1.5), None)
            if matched_cand is not None:
                if matched_cand["pred_cls"] == "SWEEP":
                    detected_sweeps += 1
                else:
                    rejection_reasons["classified_other"] += 1
                    audit_log.append({
                        "sid": sid, "gt_t": g["t"], "reason": f"classified_as_{matched_cand['pred_cls']}",
                        "prob": matched_cand["prob"]
                    })
            else:
                # Find the nearest unaccepted candidate window
                nearest_cand_idx = None
                min_dist = 999.0
                for i_c, c in enumerate(candidate_windows):
                    d = abs(c["anchor_t"] - g["t"])
                    if d < min_dist:
                        min_dist = d
                        nearest_cand_idx = i_c

                if min_dist <= 1.5 and nearest_cand_idx is not None:
                    c = candidate_windows[nearest_cand_idx]
                    p_cls, p_prob = preds[nearest_cand_idx]
                    f_peak = c["anchor_f"]
                    f_start = max(0, f_peak - 211)
                    gx_win = channels[f_start : f_peak + 1, 6] if channels.shape[1] > 6 else np.zeros(f_peak + 1 - f_start)
                    gy_win = channels[f_start : f_peak + 1, 7] if channels.shape[1] > 7 else np.zeros(f_peak + 1 - f_start)
                    gz_win = channels[f_start : f_peak + 1, 8] if channels.shape[1] > 8 else np.zeros(f_peak + 1 - f_start)
                    delta_gz = float(np.ptp(gz_win))
                    pitch_deg = np.rad2deg(np.arctan2(gz_win, np.sqrt(gx_win**2 + gy_win**2 + 1e-6)))
                    delta_pitch = float(np.ptp(pitch_deg))
                    w_roll_win = channels[f_start : f_peak + 1, 3] if channels.shape[1] > 3 else np.zeros(f_peak + 1 - f_start)
                    omega_roll = float(np.max(np.abs(w_roll_win)))

                    if p_cls == "SWEEP":
                        if p_prob < 0.45:
                            rejection_reasons["softmax_floor"] += 1
                            audit_log.append({"sid": sid, "gt_t": g["t"], "reason": "softmax_floor", "prob": p_prob, "delta_pitch": delta_pitch, "delta_gz": delta_gz, "omega_roll": omega_roll})
                        elif delta_pitch < 15.0 and delta_gz < 2.0:
                            rejection_reasons["tilt_check"] += 1
                            audit_log.append({"sid": sid, "gt_t": g["t"], "reason": "tilt_check", "prob": p_prob, "delta_pitch": delta_pitch, "delta_gz": delta_gz, "omega_roll": omega_roll})
                        else:
                            rejection_reasons["nms_suppression"] += 1
                            audit_log.append({"sid": sid, "gt_t": g["t"], "reason": "nms_suppression", "prob": p_prob, "delta_pitch": delta_pitch, "delta_gz": delta_gz, "omega_roll": omega_roll})
                    else:
                        rejection_reasons["classified_other"] += 1
                        audit_log.append({"sid": sid, "gt_t": g["t"], "reason": f"predicted_{p_cls}", "prob": p_prob})
                else:
                    rejection_reasons["no_candidate_anchor"] += 1
                    audit_log.append({"sid": sid, "gt_t": g["t"], "reason": "no_candidate_anchor"})

    missed_sweeps = total_gt_sweeps - detected_sweeps
    print(f"\n📊 SWEEP AUDIT SUMMARY ACROSS ALL 51 SESSIONS:")
    print(f"--------------------------------------------------------------------------------")
    print(f"  • Total Ground-Truth SWEEP Shots       : {total_gt_sweeps}")
    print(f"  • Detected & Correctly Filtered SWEEP  : {detected_sweeps} ({detected_sweeps/total_gt_sweeps*100.0:.1f}% recall)")
    print(f"  • Missed / Filtered Ground-Truth SWEEP : {missed_sweeps}")
    print(f"--------------------------------------------------------------------------------")
    print(f"🔍 BREAKDOWN OF REJECTION REASONS:")
    print(f"  1. Torso Tilt Check (delta_pitch < 15° & delta_gz < 2.0 m/s²) : {rejection_reasons['tilt_check']} shots")
    print(f"  2. Softmax Floor (P(SWEEP) < 0.45)                            : {rejection_reasons['softmax_floor']} shots")
    print(f"  3. 2.4s NMS Suppression (adjacent peak refractory)             : {rejection_reasons['nms_suppression']} shots")
    print(f"  4. Classified as Other Shot Type                              : {rejection_reasons['classified_other']} shots")
    print(f"  5. No Candidate Anchor Extracted (Stance / Motion Burst)      : {rejection_reasons['no_candidate_anchor']} shots")
    print(f"--------------------------------------------------------------------------------")

    df_log = pd.DataFrame(audit_log)
    print(f"\nSample of missed shots with kinematic parameters:")
    sample = df_log[df_log["reason"].isin(["tilt_check", "softmax_floor"])].head(10)
    print(sample.to_string())

if __name__ == "__main__":
    main()
