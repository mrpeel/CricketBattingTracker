#!/usr/bin/env python3
"""
Deep Stance Gate Diagnostic Analysis
=====================================
Analyses the facing-up gate conditions across an entire session to understand
why shot detection recall is low. Checks the 5 stance conditions at every
narrated shot timestamp to see whether the watch could have been in
FACING_UP_LOCKED state prior to each shot.

Output:
  1. Per-shot stance gate analysis (all 5 conditions at t_impact - 2.0s)
  2. Aggregate statistics on which conditions are failing most often
  3. Timeline heatmap showing where the stance gate was open vs. locked
"""

import sys
import os
import json
import numpy as np
import pandas as pd
from collections import Counter

def load_sensor_data(session_dir):
    """Load all sensor CSVs."""
    gyro = pd.read_csv(os.path.join(session_dir, "WatchGyroscope.csv"))
    accel = pd.read_csv(os.path.join(session_dir, "WatchAccelerometer.csv"))
    gravity = pd.read_csv(os.path.join(session_dir, "WatchGravity.csv"))
    
    game_orient_path = os.path.join(session_dir, "WatchGameOrientation.csv")
    orient_path = os.path.join(session_dir, "WatchOrientation.csv")
    orient = pd.read_csv(game_orient_path) if os.path.exists(game_orient_path) else pd.read_csv(orient_path)
    
    steps_path = os.path.join(session_dir, "WatchSteps.csv")
    steps = pd.read_csv(steps_path) if os.path.exists(steps_path) else None
    
    gyro['mag'] = np.sqrt(gyro['x']**2 + gyro['y']**2 + gyro['z']**2)
    
    return gyro, accel, gravity, orient, steps

def evaluate_stance_at_time(t_center, window_s, df_gyro, df_accel, df_gravity, df_orient, df_steps):
    """
    Evaluate the 5 stance gate conditions in a window [t_center - window_s, t_center].
    This represents whether the watch could have been in FACING_UP_LOCKED 
    in the window_s seconds BEFORE the shot.
    
    Returns dict with values and pass/fail for each condition.
    """
    t_start = t_center - window_s
    t_end = t_center
    
    # 1. Gyro std (1s window)
    g_win = df_gyro[(df_gyro['seconds_elapsed'] >= t_end - 1.0) & (df_gyro['seconds_elapsed'] <= t_end)]
    if len(g_win) >= 2:
        g_mags = np.sqrt(g_win['x']**2 + g_win['y']**2 + g_win['z']**2)
        gyro_std = np.std(g_mags, ddof=0)
    else:
        gyro_std = 0.0
    
    # 2. Accel std (1s window)
    a_win = df_accel[(df_accel['seconds_elapsed'] >= t_end - 1.0) & (df_accel['seconds_elapsed'] <= t_end)]
    if len(a_win) >= 2:
        a_mags = np.sqrt(a_win['x']**2 + a_win['y']**2 + a_win['z']**2)
        accel_std = np.std(a_mags, ddof=0)
    else:
        accel_std = 0.0
    
    # 3. Orientation displacement (500ms window)
    o_win = df_orient[(df_orient['seconds_elapsed'] >= t_end - 0.5) & (df_orient['seconds_elapsed'] <= t_end)]
    if len(o_win) >= 2:
        o_win = o_win.sort_values(by='seconds_elapsed')
        qx, qy, qz, qw = o_win['qx'].values, o_win['qy'].values, o_win['qz'].values, o_win['qw'].values
        dots = qx[:-1]*qx[1:] + qy[:-1]*qy[1:] + qz[:-1]*qz[1:] + qw[:-1]*qw[1:]
        dots = np.clip(np.abs(dots), -1.0, 1.0)
        angles = np.degrees(2.0 * np.arccos(dots))
        ori_disp = np.mean(angles)
    else:
        ori_disp = 999.0
    
    # 4. Steps (1.0s lookback)
    if df_steps is not None and len(df_steps) > 0:
        s_win = df_steps[(df_steps['seconds_elapsed'] >= t_end - 1.0) & (df_steps['seconds_elapsed'] <= t_end)]
        steps_count = len(s_win)
    else:
        steps_count = 0
    
    # 5. Gravity Y
    gr_win = df_gravity[(df_gravity['seconds_elapsed'] >= t_end - 1.0) & (df_gravity['seconds_elapsed'] <= t_end)]
    grav_y = np.mean(gr_win['y']) if len(gr_win) > 0 else -9.8
    
    # Evaluate pass/fail
    gyro_ok = gyro_std < 1.2
    accel_ok = accel_std < 2.0
    ori_ok = ori_disp < 2.0
    steps_ok = steps_count == 0
    grav_ok = grav_y <= -3.5
    
    # Hybrid M-of-N: gyro and steps are mandatory, plus at least 1 of accel, ori, gravity
    flex_passed = int(accel_ok) + int(ori_ok) + int(grav_ok)
    all_pass = gyro_ok and steps_ok and (flex_passed >= 1)
    
    return {
        'gyro_std': gyro_std, 'gyro_ok': gyro_ok,
        'accel_std': accel_std, 'accel_ok': accel_ok,
        'ori_disp': ori_disp, 'ori_ok': ori_ok,
        'steps_count': steps_count, 'steps_ok': steps_ok,
        'grav_y': grav_y, 'grav_ok': grav_ok,
        'all_pass': all_pass
    }

def scan_stance_gate_timeline(df_gyro, df_accel, df_gravity, df_orient, df_steps, sample_interval=1.0):
    """
    Scan the entire session at `sample_interval` second intervals
    and evaluate the stance gate at each point. This gives us a timeline
    of when the stance gate would have been openable.
    """
    max_t = df_gyro['seconds_elapsed'].max()
    timestamps = np.arange(2.0, max_t, sample_interval)
    
    results = []
    for t in timestamps:
        r = evaluate_stance_at_time(t, 1.5, df_gyro, df_accel, df_gravity, df_orient, df_steps)
        r['time'] = t
        results.append(r)
    
    return pd.DataFrame(results)

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 stance_diagnostic.py <session_dir> [offset_seconds]")
        sys.exit(1)
    
    session_dir = sys.argv[1]
    offset = float(sys.argv[2]) if len(sys.argv) > 2 else None
    
    session_name = os.path.basename(session_dir)
    print(f"\n{'='*80}")
    print(f"  DEEP STANCE GATE DIAGNOSTIC ANALYSIS")
    print(f"  Session: {session_name}")
    print(f"{'='*80}\n")
    
    # Load sensor data
    df_gyro, df_accel, df_gravity, df_orient, df_steps = load_sensor_data(session_dir)
    session_duration = df_gyro['seconds_elapsed'].max()
    print(f"Session duration: {session_duration:.1f}s ({session_duration/60:.1f} min)")
    print(f"Gyro samples: {len(df_gyro)}, Accel: {len(df_accel)}, Gravity: {len(df_gravity)}, Orient: {len(df_orient)}")
    if df_steps is not None:
        print(f"Step events: {len(df_steps)}")
    
    # Calculate offset if not provided
    if offset is None:
        narration_files = [f for f in os.listdir(session_dir) if f.startswith("narration_") and f.endswith(".m4a")]
        if narration_files:
            import datetime
            fname = narration_files[0]
            # Parse narration_YYYYMMDD_HHMMSS.m4a
            parts = fname.replace("narration_", "").replace(".m4a", "")
            try:
                dt = datetime.datetime.strptime(parts, "%Y%m%d_%H%M%S")
                audio_epoch = dt.timestamp()
                
                timeline_path = os.path.join(session_dir, "latest_timeline.txt")
                with open(timeline_path) as f:
                    for line in f:
                        if line.startswith("SYSTEM_START:"):
                            watch_epoch = int(line.split("Ts=")[1].strip()) / 1000.0
                            offset = audio_epoch - watch_epoch
                            print(f"Auto-offset: {offset:+.3f}s")
                            break
            except:
                offset = 0.0
        else:
            offset = 0.0
    
    # Load narrations
    narr_path = os.path.join(session_dir, "narrations_raw.json")
    if not os.path.exists(narr_path):
        print(f"No narrations_raw.json found - cannot do per-shot analysis.")
        sys.exit(1)
    
    with open(narr_path) as f:
        narrations = json.load(f)
    
    print(f"\nTotal narrated events: {len(narrations)}")
    
    # Load timeline for watch shot events
    timeline_path = os.path.join(session_dir, "latest_timeline.txt")
    watch_shots = []
    start_ts = None
    with open(timeline_path) as f:
        for line in f:
            line = line.strip()
            if line.startswith("SYSTEM_START:"):
                start_ts = int(line.split("Ts=")[1]) / 1000.0
            elif line.startswith("Shot:"):
                ts_part = line.split("Ts=")[-1].strip()
                ts_ms = int(ts_part) / 1000.0
                rel_t = ts_ms - start_ts if start_ts else 0
                watch_shots.append(rel_t)
    
    print(f"Watch-detected shots: {len(watch_shots)}")
    
    # =========================================================================
    # PART 1: Per-shot stance gate analysis
    # =========================================================================
    print(f"\n{'='*80}")
    print("  PART 1: PRE-SHOT STANCE GATE ANALYSIS (2.5s before each narrated shot)")
    print(f"{'='*80}\n")
    
    # We check the gate at t_impact - 1.5s (the stance must be locked for 0.8-1.2s before the backswing)
    # The backswing happens ~0.5-1.0s before impact, so stance check should be at t_impact - ~2.0s
    check_offsets = [2.0, 2.5, 3.0]  # Check at multiple pre-shot windows
    
    results_by_shot = []
    for i, shot in enumerate(narrations):
        audio_t = shot['timestamp_seconds']
        sensor_t = audio_t + offset
        shot_type = shot.get('shot_type', 'Unknown')
        
        # Skip non-swing events
        if any(term in shot_type.lower() for term in ['facing up', 'no shot', 'leave']):
            continue
        
        best_result = None
        for check_offset in check_offsets:
            t_check = sensor_t - check_offset
            if t_check < 0:
                continue
            result = evaluate_stance_at_time(t_check, 1.5, df_gyro, df_accel, df_gravity, df_orient, df_steps)
            if result['all_pass']:
                best_result = result
                best_result['check_offset'] = check_offset
                break
        
        if best_result is None:
            # Use the 2.5s offset as the representative failure
            t_check = sensor_t - 2.5
            best_result = evaluate_stance_at_time(t_check, 1.5, df_gyro, df_accel, df_gravity, df_orient, df_steps)
            best_result['check_offset'] = 2.5
        
        best_result['shot_index'] = i + 1
        best_result['shot_type'] = shot_type
        best_result['sensor_time'] = sensor_t
        best_result['narrated_text'] = shot.get('narrated_text', '')[:60]
        
        # Check if watch detected this shot (within 3s)
        matched = any(abs(wt - sensor_t + 2.5) < 3.0 for wt in watch_shots)
        best_result['watch_detected'] = matched
        
        results_by_shot.append(best_result)
    
    # Print per-shot table
    print(f"{'#':>3} {'Type':<18} {'SensorT':>8} {'GyroStd':>8} {'AccStd':>8} {'OriDsp':>8} {'Steps':>5} {'GravY':>7} {'Gate':>6} {'Watch':>7}")
    print("-" * 100)
    
    for r in results_by_shot:
        gate_str = "✅ OPEN" if r['all_pass'] else "❌ SHUT"
        watch_str = "✅ DET" if r['watch_detected'] else "❌ MISS"
        
        gyro_flag = "" if r['gyro_ok'] else "⚠"
        acc_flag = "" if r['accel_ok'] else "⚠"
        ori_flag = "" if r['ori_ok'] else "⚠"
        step_flag = "" if r['steps_ok'] else "⚠"
        grav_flag = "" if r['grav_ok'] else "⚠"
        
        print(f"{r['shot_index']:>3} {r['shot_type']:<18} {r['sensor_time']:>7.1f}s "
              f"{r['gyro_std']:>6.2f}{gyro_flag:<2} {r['accel_std']:>6.2f}{acc_flag:<2} "
              f"{r['ori_disp']:>6.2f}{ori_flag:<2} {r['steps_count']:>3}{step_flag:<2} "
              f"{r['grav_y']:>6.2f}{grav_flag:<1} {gate_str} {watch_str}")
    
    # =========================================================================
    # PART 2: Aggregate failure statistics
    # =========================================================================
    print(f"\n{'='*80}")
    print("  PART 2: AGGREGATE STANCE GATE FAILURE ANALYSIS")
    print(f"{'='*80}\n")
    
    total = len(results_by_shot)
    gate_open = sum(1 for r in results_by_shot if r['all_pass'])
    gate_shut = total - gate_open
    
    gyro_fail = sum(1 for r in results_by_shot if not r['gyro_ok'])
    accel_fail = sum(1 for r in results_by_shot if not r['accel_ok'])
    ori_fail = sum(1 for r in results_by_shot if not r['ori_ok'])
    steps_fail = sum(1 for r in results_by_shot if not r['steps_ok'])
    grav_fail = sum(1 for r in results_by_shot if not r['grav_ok'])
    
    watch_det = sum(1 for r in results_by_shot if r['watch_detected'])
    gate_open_and_det = sum(1 for r in results_by_shot if r['all_pass'] and r['watch_detected'])
    gate_shut_and_det = sum(1 for r in results_by_shot if not r['all_pass'] and r['watch_detected'])
    gate_open_and_miss = sum(1 for r in results_by_shot if r['all_pass'] and not r['watch_detected'])
    gate_shut_and_miss = sum(1 for r in results_by_shot if not r['all_pass'] and not r['watch_detected'])
    
    print(f"Total swing-type shots analyzed: {total}")
    print(f"Stance gate OPEN (all conditions met):  {gate_open} ({100*gate_open/total:.1f}%)")
    print(f"Stance gate SHUT (one+ conditions fail): {gate_shut} ({100*gate_shut/total:.1f}%)")
    print()
    print("Per-condition failure breakdown:")
    print(f"  1. Gyro Std >= 1.2 rad/s:     {gyro_fail:>3} / {total} ({100*gyro_fail/total:.1f}%)")
    print(f"  2. Accel Std >= 2.0 m/s²:     {accel_fail:>3} / {total} ({100*accel_fail/total:.1f}%)")
    print(f"  3. Ori Disp >= 2.0 deg:       {ori_fail:>3} / {total} ({100*ori_fail/total:.1f}%)")
    print(f"  4. Steps > 0 in last 1.0s:    {steps_fail:>3} / {total} ({100*steps_fail/total:.1f}%)")
    print(f"  5. Gravity Y > -3.5 m/s²:     {grav_fail:>3} / {total} ({100*grav_fail/total:.1f}%)")
    
    # Exclusive failure analysis (which condition is the SOLE cause)
    sole_fail_counts = Counter()
    multi_fail_counts = Counter()
    for r in results_by_shot:
        if r['all_pass']:
            continue
        fails = []
        if not r['gyro_ok']: fails.append('gyro')
        if not r['accel_ok']: fails.append('accel')
        if not r['ori_ok']: fails.append('ori')
        if not r['steps_ok']: fails.append('steps')
        if not r['grav_ok']: fails.append('grav_y')
        if len(fails) == 1:
            sole_fail_counts[fails[0]] += 1
        else:
            multi_fail_counts[tuple(sorted(fails))] += 1
    
    print(f"\nSole-cause failures (only 1 condition failed):")
    for condition, count in sole_fail_counts.most_common():
        print(f"  {condition}: {count} shots")
    
    print(f"\nMulti-condition failures (2+ conditions failed simultaneously):")
    for conditions, count in multi_fail_counts.most_common(10):
        print(f"  {' + '.join(conditions)}: {count} shots")
    
    print(f"\nWatch detection vs Stance Gate correlation:")
    print(f"  Gate OPEN  & Watch DETECTED:  {gate_open_and_det}")
    print(f"  Gate OPEN  & Watch MISSED:    {gate_open_and_miss}")
    print(f"  Gate SHUT  & Watch DETECTED:  {gate_shut_and_det}")
    print(f"  Gate SHUT  & Watch MISSED:    {gate_shut_and_miss}")
    
    if gate_open > 0:
        print(f"\n  Watch recall when gate OPEN:  {gate_open_and_det}/{gate_open} ({100*gate_open_and_det/gate_open:.1f}%)")
    if gate_shut > 0:
        print(f"  Watch recall when gate SHUT:  {gate_shut_and_det}/{gate_shut} ({100*gate_shut_and_det/gate_shut:.1f}%)")
    
    # =========================================================================
    # PART 3: Gravity Y distribution analysis
    # =========================================================================
    print(f"\n{'='*80}")
    print("  PART 3: GRAVITY Y DISTRIBUTION (pre-shot windows)")
    print(f"{'='*80}\n")
    
    grav_values = [r['grav_y'] for r in results_by_shot]
    grav_arr = np.array(grav_values)
    
    print(f"  Mean:   {np.mean(grav_arr):>7.2f} m/s²")
    print(f"  Median: {np.median(grav_arr):>7.2f} m/s²")
    print(f"  Std:    {np.std(grav_arr):>7.2f} m/s²")
    print(f"  Min:    {np.min(grav_arr):>7.2f} m/s²")
    print(f"  Max:    {np.max(grav_arr):>7.2f} m/s²")
    print(f"  P10:    {np.percentile(grav_arr, 10):>7.2f} m/s²")
    print(f"  P25:    {np.percentile(grav_arr, 25):>7.2f} m/s²")
    print(f"  P75:    {np.percentile(grav_arr, 75):>7.2f} m/s²")
    print(f"  P90:    {np.percentile(grav_arr, 90):>7.2f} m/s²")
    
    # Histogram of gravity Y ranges
    bins = [(-15, -8), (-8, -6), (-6, -4), (-4, -3.5), (-3.5, -2), (-2, 0), (0, 5)]
    print(f"\n  Gravity Y distribution (threshold at -3.5 m/s²):")
    for lo, hi in bins:
        count = np.sum((grav_arr >= lo) & (grav_arr < hi))
        bar = "█" * count
        marker = " ← THRESHOLD" if lo == -3.5 else ""
        print(f"    [{lo:>5.1f}, {hi:>5.1f}): {count:>3} {bar}{marker}")
    
    # =========================================================================
    # PART 4: Stance gate timeline scan
    # =========================================================================
    print(f"\n{'='*80}")
    print("  PART 4: STANCE GATE TIMELINE SCAN (sampled every 2s)")
    print(f"{'='*80}\n")
    
    timeline_df = scan_stance_gate_timeline(df_gyro, df_accel, df_gravity, df_orient, df_steps, sample_interval=2.0)
    
    total_samples = len(timeline_df)
    gate_open_samples = timeline_df['all_pass'].sum()
    
    print(f"Total timeline samples: {total_samples} (over {session_duration:.0f}s)")
    print(f"Stance gate OPEN:  {gate_open_samples} ({100*gate_open_samples/total_samples:.1f}%)")
    print(f"Stance gate SHUT:  {total_samples - gate_open_samples} ({100*(total_samples - gate_open_samples)/total_samples:.1f}%)")
    
    print(f"\nPer-condition pass rate across entire session:")
    print(f"  1. Gyro Std < 1.2:   {timeline_df['gyro_ok'].sum():>4} / {total_samples} ({100*timeline_df['gyro_ok'].mean():.1f}%)")
    print(f"  2. Accel Std < 2.0:  {timeline_df['accel_ok'].sum():>4} / {total_samples} ({100*timeline_df['accel_ok'].mean():.1f}%)")
    print(f"  3. Ori Disp < 2.0:   {timeline_df['ori_ok'].sum():>4} / {total_samples} ({100*timeline_df['ori_ok'].mean():.1f}%)")
    print(f"  4. Steps == 0:       {timeline_df['steps_ok'].sum():>4} / {total_samples} ({100*timeline_df['steps_ok'].mean():.1f}%)")
    print(f"  5. Grav Y <= -3.5:   {timeline_df['grav_ok'].sum():>4} / {total_samples} ({100*timeline_df['grav_ok'].mean():.1f}%)")
    
    # Print condensed timeline visualization
    print(f"\n  Timeline (O=open, X=shut, each char = 10s):")
    chunk_size = 5  # 5 samples * 2s = 10s per character
    chars = []
    for start in range(0, len(timeline_df), chunk_size):
        chunk = timeline_df.iloc[start:start+chunk_size]
        pct = chunk['all_pass'].mean()
        if pct >= 0.8:
            chars.append('O')
        elif pct >= 0.4:
            chars.append('o')
        elif pct >= 0.1:
            chars.append('.')
        else:
            chars.append('X')
    
    # Print in rows of 60 chars (= 600s = 10 min per row)
    for row_start in range(0, len(chars), 60):
        row = ''.join(chars[row_start:row_start+60])
        t_start_s = row_start * 10
        t_end_s = min((row_start + 60) * 10, session_duration)
        print(f"  {t_start_s:>5.0f}s |{row}| {t_end_s:.0f}s")
    
    print(f"\n  Legend: O = mostly open (80%+), o = mixed (40-80%), . = rarely (10-40%), X = shut (<10%)")
    print()
    
    # =========================================================================
    # PART 5: Summary and Recommendations
    # =========================================================================
    print(f"\n{'='*80}")
    print("  PART 5: ROOT CAUSE SUMMARY & RECOMMENDATIONS")
    print(f"{'='*80}\n")
    
    # Identify the primary blocker
    fail_rates = {
        'Gyro Std (< 1.2 rad/s)': gyro_fail / total * 100,
        'Accel Std (< 2.0 m/s²)': accel_fail / total * 100,
        'Ori Disp (< 2.0 deg)': ori_fail / total * 100,
        'Steps (== 0)': steps_fail / total * 100,
        'Gravity Y (<= -3.5 m/s²)': grav_fail / total * 100,
    }
    
    sorted_fails = sorted(fail_rates.items(), key=lambda x: x[1], reverse=True)
    
    print("Condition failure rate ranking (highest = most blocking):")
    for i, (name, rate) in enumerate(sorted_fails, 1):
        bar = "█" * int(rate / 2)
        print(f"  {i}. {name:<30} {rate:>5.1f}% {bar}")
    
    print(f"\nOverall: The stance gate was SHUT for {100*gate_shut/total:.0f}% of narrated shots.")
    if grav_fail > total * 0.5:
        print("⚠️  PRIMARY BLOCKER: Gravity Y condition is failing for the majority of shots.")
        print("   This suggests the player's watch arm orientation during stance is different")
        print("   from what the threshold expects (arm extended toward first slip).")
        print("   RECOMMENDATION: Consider loosening the Gravity Y threshold or using")
        print("   a percentile-based adaptive threshold.")
    if steps_fail > total * 0.3:
        print("⚠️  SIGNIFICANT BLOCKER: Step events are being detected near shot times.")
        print("   This could indicate the player is shuffling feet at guard.")
    if ori_fail > total * 0.3:
        print("⚠️  SIGNIFICANT BLOCKER: Bat orientation displacement is too high.")
        print("   The player may be fidgeting with the bat at guard.")

if __name__ == "__main__":
    main()
