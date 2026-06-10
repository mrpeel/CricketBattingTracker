#!/usr/bin/env python3
import os
import json
import numpy as np
import pandas as pd

def load_sensor_data(session_dir):
    gyro = pd.read_csv(os.path.join(session_dir, "WatchGyroscope.csv"))
    accel = pd.read_csv(os.path.join(session_dir, "WatchAccelerometer.csv"))
    gravity = pd.read_csv(os.path.join(session_dir, "WatchGravity.csv"))
    
    game_orient_path = os.path.join(session_dir, "WatchGameOrientation.csv")
    orient_path = os.path.join(session_dir, "WatchOrientation.csv")
    orient = pd.read_csv(game_orient_path) if os.path.exists(game_orient_path) else pd.read_csv(orient_path)
    
    steps_path = os.path.join(session_dir, "WatchSteps.csv")
    steps = pd.read_csv(steps_path) if os.path.exists(steps_path) else None
    
    gyro['mag'] = np.sqrt(gyro['x']**2 + gyro['y']**2 + gyro['z']**2)
    accel['mag'] = np.sqrt(accel['x']**2 + accel['y']**2 + accel['z']**2)
    
    return gyro, accel, gravity, orient, steps

def get_offset(session_dir):
    import datetime
    narration_files = [f for f in os.listdir(session_dir) if f.startswith("narration_") and f.endswith(".m4a")]
    if not narration_files:
        return 0.0
    fname = narration_files[0]
    parts = fname.replace("narration_", "").replace(".m4a", "")
    try:
        dt = datetime.datetime.strptime(parts, "%Y%m%d_%H%M%S")
        timeline_path = os.path.join(session_dir, "latest_timeline.txt")
        with open(timeline_path) as f:
            for line in f:
                if line.startswith("SYSTEM_START:"):
                    watch_epoch = int(line.split("Ts=")[1].strip()) / 1000.0
                    return dt.timestamp() - watch_epoch
    except:
        pass
    return 0.0

def precompute_rolling_stats(df_gyro, df_accel, df_gravity, df_orient, df_steps, sample_interval=0.1):
    max_t = df_gyro['seconds_elapsed'].max()
    sample_times = np.arange(1.0, max_t, sample_interval)
    
    gyro_t = df_gyro['seconds_elapsed'].values
    gyro_mag = df_gyro['mag'].values
    accel_t = df_accel['seconds_elapsed'].values
    accel_mag = df_accel['mag'].values
    grav_t = df_gravity['seconds_elapsed'].values
    grav_y = df_gravity['y'].values
    ori_t = df_orient['seconds_elapsed'].values
    ori_qx = df_orient['qx'].values
    ori_qy = df_orient['qy'].values
    ori_qz = df_orient['qz'].values
    ori_qw = df_orient['qw'].values
    
    step_times = df_steps['seconds_elapsed'].values if (df_steps is not None and len(df_steps) > 0) else np.array([])
    
    results = []
    for t in sample_times:
        # Gyro std (1s window)
        mask_g = (gyro_t >= t - 1.0) & (gyro_t <= t)
        g_std = np.std(gyro_mag[mask_g], ddof=0) if mask_g.sum() >= 2 else 0.0
        
        # Accel std (1s window)
        mask_a = (accel_t >= t - 1.0) & (accel_t <= t)
        a_std = np.std(accel_mag[mask_a], ddof=0) if mask_a.sum() >= 2 else 0.0
        
        # Ori disp (500ms window)
        mask_o = (ori_t >= t - 0.5) & (ori_t <= t)
        o_count = mask_o.sum()
        if o_count >= 2:
            idx = np.where(mask_o)[0]
            qx_w = ori_qx[idx]
            qy_w = ori_qy[idx]
            qz_w = ori_qz[idx]
            qw_w = ori_qw[idx]
            dots = qx_w[:-1]*qx_w[1:] + qy_w[:-1]*qy_w[1:] + qz_w[:-1]*qz_w[1:] + qw_w[:-1]*qw_w[1:]
            dots = np.clip(np.abs(dots), -1.0, 1.0)
            angles = np.degrees(2.0 * np.arccos(dots))
            o_disp = np.mean(angles)
        else:
            o_disp = 999.0
        
        # Gravity Y (1s mean)
        mask_gr = (grav_t >= t - 1.0) & (grav_t <= t)
        g_y = np.mean(grav_y[mask_gr]) if mask_gr.sum() > 0 else -9.8
        
        results.append({
            'time': t,
            'gyro_std': g_std,
            'accel_std': a_std,
            'ori_disp': o_disp,
            'grav_y': g_y,
        })
        
    df = pd.DataFrame(results)
    return df, step_times

def simulate_state_machine_with_diagnostics(gyro_std_max, accel_std_max, ori_disp_max_deg, grav_y_max, step_window_s, lock_duration_s, min_motion_conditions, gyro_mandatory, df_stats, step_times, gyro_times, gyro_mags, shot_times, post_shot_guard_s=2.5):
    times = df_stats['time'].values
    gyro_std = df_stats['gyro_std'].values
    accel_std = df_stats['accel_std'].values
    ori_disp = df_stats['ori_disp'].values
    grav_y = df_stats['grav_y'].values
    
    state = 0 # 0=CLASSIFY, 1=LOCKED, 2=MEASURING_ARC/CONTACT_WAIT
    gate_active = False
    gate_start_time = 0.0
    break_start_time = 0.0
    locked_time = 0.0
    swing_start_time = 0.0
    last_shot_end_time = -100.0
    
    detections = [] # list of dicts with 'time', 'type'
    state_timeline = [] # list of (t, state, gate_active)
    
    for idx, t in enumerate(times):
        # 1. Apply post-shot guard window
        if t <= last_shot_end_time + post_shot_guard_s:
            state_timeline.append((t, state, gate_active, "guard"))
            continue
            
        # 2. CLASSIFY state
        if state == 0:
            if len(step_times) > 0:
                steps_in_window = np.sum((step_times >= t - step_window_s) & (step_times <= t))
                has_steps = (steps_in_window > 0)
            else:
                has_steps = False
                
            if has_steps:
                gate_active = False
                break_start_time = 0.0
                state_timeline.append((t, state, gate_active, "step_kill"))
            else:
                c_gyro = gyro_std[idx] < gyro_std_max
                c_accel = accel_std[idx] < accel_std_max
                c_ori = ori_disp[idx] < ori_disp_max_deg
                c_grav = grav_y[idx] <= grav_y_max
                
                mandatory_ok = c_gyro if gyro_mandatory else True
                
                if not mandatory_ok:
                    all_met = False
                else:
                    conditions_met = int(c_gyro) + int(c_accel) + int(c_ori) + int(c_grav)
                    all_met = (conditions_met >= min_motion_conditions)
                
                if all_met:
                    if not gate_active:
                        gate_active = True
                        gate_start_time = t
                        break_start_time = 0.0
                    else:
                        if break_start_time > 0.0:
                            break_dur = t - break_start_time
                            gate_start_time += break_dur
                            break_start_time = 0.0
                        held_for = t - gate_start_time
                        if held_for >= lock_duration_s:
                            state = 1
                            locked_time = t
                else:
                    if gate_active:
                        if break_start_time == 0.0:
                            break_start_time = t
                        elif t - break_start_time > 1.2: # 1.2s break tolerance
                            gate_active = False
                            break_start_time = 0.0
                state_timeline.append((t, state, gate_active, "eval"))
                
        # 3. FACING_UP_LOCKED state
        elif state == 1:
            if t - locked_time > 8.0:
                state = 0
                gate_active = False
                break_start_time = 0.0
                state_timeline.append((t, state, gate_active, "timeout"))
                continue
                
            if len(step_times) > 0:
                steps_in_window = np.sum((step_times >= t - step_window_s) & (step_times <= t))
                if steps_in_window > 0:
                    state = 0
                    gate_active = False
                    break_start_time = 0.0
                    state_timeline.append((t, state, gate_active, "step_break"))
                    continue
            
            mask_gyro = (gyro_times >= t - 0.1) & (gyro_times <= t)
            max_gyro = np.max(gyro_mags[mask_gyro]) if mask_gyro.sum() > 0 else 0.0
            
            if max_gyro >= 5.0:
                state = 2
                swing_start_time = t
                
            state_timeline.append((t, state, gate_active, "locked"))
            
        # 4. MEASURING_ARC & CONTACT_WAIT (1.75s)
        elif state == 2:
            if t - swing_start_time >= 1.75:
                detections.append(swing_start_time)
                last_shot_end_time = t
                state = 0
                gate_active = False
                break_start_time = 0.0
            state_timeline.append((t, state, gate_active, "measuring"))
            
    return detections, pd.DataFrame(state_timeline, columns=['time', 'state', 'gate_active', 'reason'])

def main():
    session_dir = "/Users/neilkloot/Code/Batting Sensor Stats/live_watch_sessions/session-2026-06-01_12-23-38"
    gyro, accel, gravity, orient, steps = load_sensor_data(session_dir)
    # Simulate Kotlin Production
    # Force offset to 0.0 since start message is sent instantly
    offset = 0.0
    
    with open(os.path.join(session_dir, "narrations_raw.json")) as f:
        narrations = json.load(f)
        
    shot_times = []
    shot_types = []
    for n in narrations:
        st = n.get('shot_type', '')
        if any(term in st.lower() for term in ['facing up', 'no shot', 'leave', 'evade']):
            continue
        shot_times.append(n['timestamp_seconds'] + offset)
        shot_types.append(st)
        
    # Precompute rolling stats
    df_stats, step_times = precompute_rolling_stats(gyro, accel, gravity, orient, steps, sample_interval=0.1)
    gyro_times = gyro['seconds_elapsed'].values
    gyro_mags = gyro['mag'].values
    
    # Simulate Kotlin Production
    # gyro_std < 1.2, accel_std < 2.0, ori_disp < 2.0, grav_y <= -3.5 (flexible 1 of 3)
    detections, timeline = simulate_state_machine_with_diagnostics(
        gyro_std_max=1.2,
        accel_std_max=2.0,
        ori_disp_max_deg=2.0,
        grav_y_max=-3.5,
        step_window_s=1.0,
        lock_duration_s=1.2,
        min_motion_conditions=2, # mandatory gyro + 1 flexible
        gyro_mandatory=True,
        df_stats=df_stats,
        step_times=step_times,
        gyro_times=gyro_times,
        gyro_mags=gyro_mags,
        shot_times=shot_times
    )
    
    print(f"Total simulated detections: {len(detections)}")
    print(f"Total ground truth shots: {len(shot_times)}")
    
    # Matching
    matched = []
    missed = []
    for st, s_type in zip(shot_times, shot_types):
        best_d = None
        min_diff = 4.0
        for d in detections:
            diff = abs(d - st + 1.2) # swing detection logs at swing start which is ~1.2s before impact
            if diff < min_diff:
                min_diff = diff
                best_d = d
        if best_d is not None:
            matched.append((st, s_type, best_d, min_diff))
        else:
            missed.append((st, s_type))
            
    print(f"TP Matches: {len(matched)}")
    print(f"Missed: {len(missed)}")
    
    print("\n--- ANALYSIS OF MISSED SHOTS ---")
    for st, s_type in missed:
        print(f"\nMissed shot {s_type} at relative time {st:.1f}s (Narration time {st - offset:.1f}s):")
        
        # Check timeline state around shot time [st - 4.0, st]
        t_slice = timeline[(timeline['time'] >= st - 4.0) & (timeline['time'] <= st)]
        states = t_slice['state'].values
        reasons = t_slice['reason'].values
        times = t_slice['time'].values
        
        # 1. Did it lock?
        locked_indices = np.where(states == 1)[0]
        measuring_indices = np.where(states == 2)[0]
        
        # Check if there was a lock
        if len(locked_indices) > 0:
            lock_t = times[locked_indices[0]]
            print(f"  - Stance gate did lock successfully at {lock_t:.1f}s.")
            # Did it trigger a backswing?
            # Find gyro mag in the window [lock_t, st]
            gyro_slice = gyro[(gyro['seconds_elapsed'] >= lock_t) & (gyro['seconds_elapsed'] <= st)]
            if len(gyro_slice) > 0:
                max_g = gyro_slice['mag'].max()
                print(f"  - Max gyro mag in locked state was {max_g:.2f} rad/s (backswing trigger requires >= 5.0).")
                if max_g < 5.0:
                    print(f"  - FAILURE REASON: Gyro magnitude never crossed the backswing trigger threshold of 5.0 rad/s!")
            else:
                print("  - No gyro data found in locked state window.")
        elif len(measuring_indices) > 0:
            print(f"  - State was MEASURING/WAIT at the shot time (already in a swing/measuring state).")
            print(f"  - FAILURE REASON: Fidget Lockout / Double Trigger! The watch was busy measuring a previous trigger.")
        else:
            print("  - Stance gate NEVER locked in the 4 seconds leading up to the shot.")
            # Why did it not lock?
            # Let's inspect the failing conditions in [st - 3.0, st - 1.2]
            window_slice = df_stats[(df_stats['time'] >= st - 3.0) & (df_stats['time'] <= st - 1.2)]
            if len(window_slice) > 0:
                mean_gyro_std = window_slice['gyro_std'].mean()
                mean_accel_std = window_slice['accel_std'].mean()
                mean_ori_disp = window_slice['ori_disp'].mean()
                mean_grav_y = window_slice['grav_y'].mean()
                
                print(f"  - Rolling metrics in pre-shot window:")
                print(f"    * gyro_std = {mean_gyro_std:.2f} (limit < 1.2)")
                print(f"    * accel_std = {mean_accel_std:.2f} (limit < 2.0)")
                print(f"    * ori_disp = {mean_ori_disp:.2f}° (limit < 2.0°)")
                print(f"    * grav_y = {mean_grav_y:.2f} (limit <= -3.5)")
                
                reasons_fail = []
                if mean_gyro_std >= 1.2: reasons_fail.append("Gyro Std too high (wrist moving)")
                
                flex_passed = 0
                if mean_accel_std < 2.0: flex_passed += 1
                else: reasons_fail.append("Accel Std too high")
                
                if mean_ori_disp < 2.0: flex_passed += 1
                else: reasons_fail.append("Ori Disp too high")
                
                if mean_grav_y <= -3.5: flex_passed += 1
                else: reasons_fail.append("Gravity Y too high")
                
                if flex_passed < 1:
                    reasons_fail.append("Flexible conditions failed (0 of 3 passed, requires >= 1)")
                    
                print(f"  - FAILURE REASON: Stance gate failed to lock because: {', '.join(reasons_fail)}")
            else:
                print("  - No sensor data in pre-shot window.")

if __name__ == "__main__":
    main()
