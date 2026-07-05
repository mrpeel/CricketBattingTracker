import os
import sys
import numpy as np
import pandas as pd

sys.path.append("/Users/neilkloot/Code/CricketBattingTracker/pipelines")
import adversarial_facing_up_search
from stance_decision_tree_rules import predict_stance

def simulate_tinyml_detector_for_session(session_dir, step_recency_s=1.0,
                                         facing_up_min_duration_s=0.8, facing_up_break_tolerance_s=1.5):
    """
    Simulates the Facing Up state machine gate using the trained TinyML Decision Tree predict_stance()
    instead of hardcoded independent physical thresholds.
    """
    df_gyro = adversarial_facing_up_search.load_parquet_or_csv(session_dir, "gyro")
    df_accel = adversarial_facing_up_search.load_parquet_or_csv(session_dir, "accel")
    df_grav = adversarial_facing_up_search.load_parquet_or_csv(session_dir, "gravity")
    df_orient = adversarial_facing_up_search.load_parquet_or_csv(session_dir, "game_orient")
    if df_orient is None:
        df_orient = adversarial_facing_up_search.load_parquet_or_csv(session_dir, "orient")
    df_steps = adversarial_facing_up_search.load_parquet_or_csv(session_dir, "steps")
    
    if df_gyro is None or df_accel is None or df_grav is None or df_orient is None:
        return [], 0.0
        
    precomputed = adversarial_facing_up_search.get_precomputed_features(df_gyro, df_accel, df_grav, df_orient, df_steps)
    
    n_samples = len(df_gyro)
    gyro_t = df_gyro['seconds_elapsed'].values
    gyro_mag = df_gyro['mag'].values
    
    STATE_ACTIVITY_CLASSIFY = 0
    STATE_FACING_UP_LOCKED = 1
    STATE_MEASURING_ARC = 2
    STATE_CONTACT_WAIT = 3
    
    state = STATE_ACTIVITY_CLASSIFY
    facing_up_gate_start = 0
    facing_up_gate_active = False
    facing_up_break_start = 0
    facing_up_locked_at = 0
    last_shot_end_time = 0
    
    detected_shots = []
    
    gyro_std_arr = precomputed['gyro_std']
    accel_std_arr = precomputed['accel_std']
    ori_disp_arr = precomputed['ori_disp']
    mean_grav_y_arr = precomputed['mean_grav_y']
    step_age_arr = precomputed['step_age']
    
    step_recency_ns = int(step_recency_s * 1e9)
    facing_up_min_duration_ns = int(facing_up_min_duration_s * 1e9)
    facing_up_break_tolerance_ns = int(facing_up_break_tolerance_s * 1e9)
    backswing_timeout_ns = 10000000000
    backswing_trigger_rad_s = 5.0
    post_shot_guard_ns = 1500000000
    
    for i in range(n_samples):
        t_ns = int(gyro_t[i] * 1e9)
        sec = gyro_t[i]
        g_mag = gyro_mag[i]
        
        if state == STATE_ACTIVITY_CLASSIFY:
            if t_ns <= last_shot_end_time + post_shot_guard_ns:
                continue
                
            # Input features for Decision Tree stance classifier
            sa = min(step_age_arr[i] / 1e9, 10.0)
            stance_ok = predict_stance(
                gyro_std_arr[i],
                accel_std_arr[i],
                ori_disp_arr[i],
                mean_grav_y_arr[i],
                sa
            ) == 1
            
            # The tree output replaces all threshold gates
            all_conditions_met = stance_ok
            
            if all_conditions_met:
                if not facing_up_gate_active:
                    facing_up_gate_active = True
                    facing_up_gate_start = t_ns
                    facing_up_break_start = 0
                else:
                    if facing_up_break_start != 0:
                        break_duration = t_ns - facing_up_break_start
                        facing_up_gate_start += break_duration
                        facing_up_break_start = 0
                    held_for = t_ns - facing_up_gate_start
                    if held_for >= facing_up_min_duration_ns:
                        facing_up_locked_at = t_ns
                        state = STATE_FACING_UP_LOCKED
            else:
                if facing_up_gate_active:
                    if facing_up_break_start == 0:
                        facing_up_break_start = t_ns
                    elif (t_ns - facing_up_break_start) > facing_up_break_tolerance_ns:
                        facing_up_gate_active = False
                        facing_up_break_start = 0
                        
        elif state == STATE_FACING_UP_LOCKED:
            steps_ok = step_age_arr[i] > step_recency_ns
            if not steps_ok:
                state = STATE_ACTIVITY_CLASSIFY
                facing_up_gate_active = False
                facing_up_break_start = 0
                continue
                
            elapsed = t_ns - facing_up_locked_at
            if elapsed > backswing_timeout_ns:
                state = STATE_ACTIVITY_CLASSIFY
                facing_up_gate_active = False
                facing_up_break_start = 0
                continue
                
            if g_mag >= backswing_trigger_rad_s:
                state = STATE_MEASURING_ARC
                swing_start_time = t_ns
                peak_gyro = g_mag
                peak_gyro_time = t_ns
                
        elif state == STATE_MEASURING_ARC:
            if g_mag > peak_gyro:
                peak_gyro = g_mag
                peak_gyro_time = t_ns
            if (t_ns - swing_start_time) >= 1000000000:
                state = STATE_CONTACT_WAIT
                
        elif state == STATE_CONTACT_WAIT:
            if (t_ns - peak_gyro_time) >= 750000000:
                detected_shots.append(sec)
                last_shot_end_time = peak_gyro_time + 1000000000
                state = STATE_ACTIVITY_CLASSIFY
                facing_up_gate_active = False
                facing_up_break_start = 0
                
    return detected_shots, gyro_t.max()

def main():
    target = "/Users/neilkloot/Code/Batting Sensor Stats/live_watch_sessions/session-2026-07-05_16-27-16"
    sessions_base = "/Users/neilkloot/Code/Batting Sensor Stats/live_watch_sessions"
    
    # ── Target Session Evaluation ──
    print("Evaluating TinyML Stance Gate on stressed Target Session...")
    shot_times, offset = adversarial_facing_up_search.load_shot_times(target)
    
    # Ensure cache has the stressed stance data
    adversarial_facing_up_search.apply_stance_stress_to_session_cache(target, shot_times)
    
    det, dur = simulate_tinyml_detector_for_session(target, step_recency_s=1.0, facing_up_min_duration_s=0.8, facing_up_break_tolerance_s=1.5)
    rec, f_p, fp_m, f1 = adversarial_facing_up_search.evaluate_detections(det, shot_times, dur)
    print(f"\nTinyML Gate Target Session Results:")
    print(f"  Recall   : {rec:.2%}")
    print(f"  Total FPs: {f_p} ({fp_m:.2f} FP/min)")
    print(f"  F1 Score : {f1:.4f}")
    print("------------------------------------------")
    
    # ── Rule-Based Baseline (Target Session) ──
    det_base, dur_base = adversarial_facing_up_search.simulate_detector_for_session(
        target, 1.2, 3.25, 2.5, -6.0, 3, True, True, 1.0, 0.8, 1.5
    )
    rec_base, f_p_base, fp_m_base, f1_base = adversarial_facing_up_search.evaluate_detections(det_base, shot_times, dur_base)
    print(f"Rule-Based Gate Target Session Results (Baseline):")
    print(f"  Recall   : {rec_base:.2%}")
    print(f"  Total FPs: {f_p_base} ({fp_m_base:.2f} FP/min)")
    print(f"  F1 Score : {f1_base:.4f}")
    print("==========================================\n")
    
    # ── Cross-Session Validation ──
    all_sessions = adversarial_facing_up_search.load_all_sessions(sessions_base)
    print(f"Running cross-session validation across all {len(all_sessions)} sessions...")
    session_data = []
    for s_path in all_sessions:
        s_shots, s_off = adversarial_facing_up_search.load_shot_times(s_path)
        if len(s_shots) > 0:
            session_data.append((s_path, s_shots))
            # Apply stressed stance data to cache
            adversarial_facing_up_search.apply_stance_stress_to_session_cache(s_path, s_shots)
            
    recalls, fps, f1s = [], [], []
    for s_path, s_shots in session_data:
        det, dur = simulate_tinyml_detector_for_session(s_path, step_recency_s=1.0, facing_up_min_duration_s=0.8, facing_up_break_tolerance_s=1.5)
        rec, f_p, fp_m, f1_val = adversarial_facing_up_search.evaluate_detections(det, s_shots, dur)
        recalls.append(rec)
        fps.append(f_p)
        f1s.append(f1_val)
        
    print(f"\nTinyML Gate Cross-Session Validation Summary:")
    print(f"  Avg Recall: {np.mean(recalls):.2%}")
    print(f"  Total FPs : {np.sum(fps)}")
    print(f"  Avg F1    : {np.mean(f1s):.4f}")
    
    # ── Rule-Based Baseline (Cross-Session) ──
    recalls_b, fps_b, f1s_b = [], [], []
    for s_path, s_shots in session_data:
        det, dur = adversarial_facing_up_search.simulate_detector_for_session(
            s_path, 1.2, 3.25, 2.5, -6.0, 3, True, True, 1.0, 0.8, 1.5
        )
        rec, f_p, fp_m, f1_val = adversarial_facing_up_search.evaluate_detections(det, s_shots, dur)
        recalls_b.append(rec)
        fps_b.append(f_p)
        f1s_b.append(f1_val)
        
    print(f"\nRule-Based Gate Cross-Session Validation Summary (Baseline):")
    print(f"  Avg Recall: {np.mean(recalls_b):.2%}")
    print(f"  Total FPs : {np.sum(fps_b)}")
    print(f"  Avg F1    : {np.mean(f1s_b):.4f}")

if __name__ == "__main__":
    main()
