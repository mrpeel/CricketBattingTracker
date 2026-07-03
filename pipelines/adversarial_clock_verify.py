#!/usr/bin/env python3
import os
import re
import sys
import json
import argparse
import datetime
import numpy as np
import pandas as pd

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--session-dir", help="Path to the session directory")
    parser.add_argument("--sessions-base", default="/Users/neilkloot/Code/Batting Sensor Stats/live_watch_sessions", help="Base directory containing all sessions")
    return parser.parse_args()

def resolve_sensor_path(session_dir, baseName):
    path = os.path.join(session_dir, baseName)
    if os.path.exists(path + ".gz"):
        return path + ".gz"
    return path

def load_session_data(session_dir):
    timeline_path = os.path.join(session_dir, "latest_timeline.txt")
    narrations_path = os.path.join(session_dir, "narrations_raw.json")
    gt_aligned_path = os.path.join(session_dir, "ground_truth_aligned.csv")

    if not os.path.exists(timeline_path):
        raise FileNotFoundError(f"Missing latest_timeline.txt at {timeline_path}")
    if not os.path.exists(narrations_path):
        raise FileNotFoundError(f"Missing narrations_raw.json at {narrations_path}")

    session_id = os.path.basename(session_dir)
    parquet_path = "/Users/neilkloot/Code/Batting Sensor Stats/combined_sensor_data.parquet"
    
    # Load from Parquet database if available
    if os.path.exists(parquet_path):
        try:
            partition_dir = os.path.join(parquet_path, "sensor_type=gyro")
            df_gyro = pd.read_parquet(
                partition_dir,
                filters=[("session_id", "==", session_id)]
            )
            if len(df_gyro) == 0:
                raise ValueError(f"No gyro data found in Parquet database for session {session_id}")
        except Exception as e:
            print(f"⚠️ Failed to read from Parquet database ({e}), falling back to Gzip/CSV...")
            gyro_path = resolve_sensor_path(session_dir, "WatchGyroscope.csv")
            df_gyro = pd.read_csv(gyro_path)
    else:
        gyro_path = resolve_sensor_path(session_dir, "WatchGyroscope.csv")
        df_gyro = pd.read_csv(gyro_path)

    # Load gyro data to calculate duration and magnitude
    df_gyro['mag'] = np.sqrt(df_gyro['x']**2 + df_gyro['y']**2 + df_gyro['z']**2)
    start_time_ns = df_gyro.iloc[0]['time']
    gyro_duration = df_gyro.iloc[-1]['seconds_elapsed']

    # Load narrations
    with open(narrations_path, "r") as f:
        narrations = json.load(f)

    # Detect if MMSS format and convert to seconds
    if narrations:
        is_mmss = True
        for n in narrations:
            t = n['timestamp_seconds']
            sec_part = int(t) % 100
            if sec_part >= 60:
                is_mmss = False
                break
        max_t = max(n['timestamp_seconds'] for n in narrations)
        if max_t > gyro_duration:
            is_mmss = True
        if is_mmss:
            for n in narrations:
                t = n['timestamp_seconds']
                ival = int(t)
                frac = t - ival
                minutes = ival // 100
                seconds = ival % 100
                n['timestamp_seconds'] = float(minutes * 60 + seconds + frac)

    # Parse watch start and detections from timeline
    watch_start_ms = None
    watch_shots = []
    with open(timeline_path, "r") as f:
        for line in f:
            if "SYSTEM_START:" in line:
                m = re.search(r"Ts=(\d+)", line)
                if m:
                    watch_start_ms = int(m.group(1))
            elif line.startswith("Shot:"):
                m_ts = re.search(r"Ts=(\d+)", line)
                m_type = re.search(r"Type=([^,]+)", line)
                if m_ts:
                    watch_shots.append({
                        'ts': int(m_ts.group(1)),
                        'type': m_type.group(1) if m_type else "Unknown"
                    })

    # Load current offset if ground_truth_aligned.csv exists
    current_offset = None
    if os.path.exists(gt_aligned_path):
        try:
            df_gt = pd.read_csv(gt_aligned_path)
            # Find a shot (not Facing up) to compute current offset
            df_shots_only = df_gt[df_gt['shot_type'] != 'Facing up']
            if len(df_shots_only) > 0:
                row = df_shots_only.iloc[0]
                current_offset = row['sensor_narr_time_seconds'] - row['audio_time_seconds']
        except Exception as e:
            pass

    return df_gyro, narrations, watch_start_ms, watch_shots, current_offset, gyro_duration

def run_clock_verification(df_gyro, narrations, watch_start_ms, watch_shots, current_offset, gyro_duration, search_center=0.0):
    timeline_start = watch_start_ms if watch_start_ms is not None else df_gyro.iloc[0]['time']
    for shot in watch_shots:
        shot['rel_time'] = (shot['ts'] - timeline_start) / 1000.0
    watch_times = np.array([s['rel_time'] for s in watch_shots])

    if len(watch_times) == 0 or not narrations:
        return {
            "status": "error",
            "message": "No watch detections or narrations available for alignment."
        }

    def evaluate_offset(o):
        all_candidates = []
        for i, shot in enumerate(narrations):
            audio_t = shot['timestamp_seconds']
            sensor_narr_t = audio_t + o
            shot_type_lower = shot['shot_type'].lower()
            rating_lower = shot['rating'].lower() if shot.get('rating') else ""
            is_non_swing = (
                any(term in shot_type_lower for term in ["no shot", "leave", "facing up", "evade", "defense", "defence", "block", "miss"]) or
                any(term in rating_lower for term in ["poor", "edge", "edged", "miss"])
            )
            
            cands = []
            if is_non_swing:
                cands.append({
                    'time': sensor_narr_t - 2.5,
                    'mag': 1.0,
                    'is_fallback': True
                })
            else:
                window = df_gyro[(df_gyro['seconds_elapsed'] >= sensor_narr_t - 6.0) & (df_gyro['seconds_elapsed'] <= sensor_narr_t + 7.0)]
                peaks = []
                if len(window) > 0:
                    sorted_samples = window.sort_values(by='mag', ascending=False)
                    for _, row in sorted_samples.iterrows():
                        pt = row['seconds_elapsed']
                        pmag = row['mag']
                        if pmag >= 3.0:
                            if not any(abs(pt - p['time']) < 1.0 for p in peaks):
                                peaks.append({
                                    'time': pt,
                                    'mag': pmag,
                                    'is_fallback': False
                                })
                                if len(peaks) >= 5:
                                    break
                cands.extend(peaks)
                cands.append({
                    'time': sensor_narr_t - 2.5,
                    'mag': 1.0,
                    'is_fallback': True
                })
            all_candidates.append(cands)

        def calculate_candidate_score(cand, sensor_narr_t_val):
            t = cand['time']
            mag = cand['mag']
            is_fallback = cand['is_fallback']
            if is_fallback:
                return -3.0
            lag = sensor_narr_t_val - t
            if lag < -7.0:
                return -999999.0
            elif lag < 0.0:
                return np.log(mag) - ((lag - 2.5) ** 2) / 4.5 - 5.0
            else:
                return np.log(mag) - ((lag - 2.5) ** 2) / 4.5

        # DP Table
        M = len(narrations)
        dp = []
        parent = []
        
        first_narr_t = narrations[0]['timestamp_seconds'] + o
        dp.append([calculate_candidate_score(cand, first_narr_t) for cand in all_candidates[0]])
        parent.append([-1] * len(all_candidates[0]))
        
        for i in range(1, M):
            sensor_narr_t_val = narrations[i]['timestamp_seconds'] + o
            dp_i = []
            parent_i = []
            for j, cand in enumerate(all_candidates[i]):
                best_score = -999999.0
                best_k = -1
                score_j = calculate_candidate_score(cand, sensor_narr_t_val)
                
                prev_type_lower = narrations[i-1]['shot_type'].lower()
                prev_rating_lower = narrations[i-1]['rating'].lower() if narrations[i-1].get('rating') else ""
                prev_is_non_swing = (
                    any(term in prev_type_lower for term in ["no shot", "leave", "facing up", "evade", "defense", "defence", "block", "miss"]) or
                    any(term in prev_rating_lower for term in ["poor", "edge", "edged", "miss"])
                )
                curr_type_lower = narrations[i]['shot_type'].lower()
                curr_rating_lower = narrations[i]['rating'].lower() if narrations[i].get('rating') else ""
                curr_is_non_swing = (
                    any(term in curr_type_lower for term in ["no shot", "leave", "facing up", "evade", "defense", "defence", "block", "miss"]) or
                    any(term in curr_rating_lower for term in ["poor", "edge", "edged", "miss"])
                )
                min_gap = 0.5 if (prev_is_non_swing or curr_is_non_swing) else 1.5
                
                for k, prev_cand in enumerate(all_candidates[i-1]):
                    if prev_cand['time'] < cand['time'] - min_gap:
                        val = dp[i-1][k] + score_j
                        if val > best_score:
                            best_score = val
                            best_k = k
                            
                if best_k == -1:
                    for k, prev_cand in enumerate(all_candidates[i-1]):
                        if prev_cand['time'] < cand['time']:
                            val = dp[i-1][k] + score_j
                            if val > best_score:
                                best_score = val
                                best_k = k
                if best_k == -1:
                    best_k = 0
                    best_score = dp[i-1][0] + score_j
                    
                dp_i.append(best_score)
                parent_i.append(best_k)
            dp.append(dp_i)
            parent.append(parent_i)
            
        best_j = int(np.argmax(dp[M-1]))
        chosen_indices = [best_j]
        for i in range(M-1, 0, -1):
            best_j = parent[i][best_j]
            chosen_indices.append(best_j)
        chosen_indices.reverse()
        
        detected = 0
        errors = []
        matched_details = []
        for i, shot in enumerate(narrations):
            shot_type_lower = shot['shot_type'].lower()
            rating_lower = shot['rating'].lower() if shot.get('rating') else ""
            is_non_swing = (
                any(term in shot_type_lower for term in ["no shot", "leave", "facing up", "evade", "defense", "defence", "block", "miss"]) or
                any(term in rating_lower for term in ["poor", "edge", "edged", "miss"])
            )
            if is_non_swing:
                continue
            chosen_cand = all_candidates[i][chosen_indices[i]]
            impact_t = chosen_cand['time']
            
            diffs = np.abs(watch_times - impact_t)
            min_diff = np.min(diffs)
            if min_diff <= 3.0:
                detected += 1
                errors.append(min_diff)
                matched_details.append((i, shot['shot_type'], impact_t, min_diff))
                
        mae = np.mean(errors) if errors else 999.0
        return detected, mae, matched_details

    # Coarse search: ±2.5s range at 0.5s increments (10 evaluations)
    coarse_range = 2.5
    sweep_offsets = np.arange(search_center - coarse_range, search_center + coarse_range + 0.01, 0.5)
    
    results = []
    best_matches = -1
    best_offset = None
    best_mae = 999.0

    for o in sweep_offsets:
        det, mae, _ = evaluate_offset(o)
        results.append((o, det, mae))
        if det > best_matches:
            best_matches = det
            best_offset = o
            best_mae = mae
        elif det == best_matches and mae < best_mae:
            best_offset = o
            best_mae = mae

    # Fine search: ±0.5s range around the best coarse offset at 0.01s increments (100 evaluations)
    fine_range = 0.5
    fine_sweep_offsets = np.arange(best_offset - fine_range, best_offset + fine_range + 0.001, 0.01)
    
    fine_results = []
    for o in fine_sweep_offsets:
        det, mae, details = evaluate_offset(o)
        fine_results.append((o, det, mae, details))
        if det > best_matches:
            best_matches = det
            best_offset = o
            best_mae = mae
        elif det == best_matches and mae < best_mae:
            best_offset = o
            best_mae = mae

    all_sweep = sorted(list(set([(r[0], r[1], r[2]) for r in results] + [(fr[0], fr[1], fr[2]) for fr in fine_results])), key=lambda x: x[0])

    # Find local peaks
    peaks = []
    for i in range(1, len(all_sweep) - 1):
        prev_m = all_sweep[i-1][1]
        curr_m = all_sweep[i][1]
        next_m = all_sweep[i+1][1]
        prev_mae = all_sweep[i-1][2]
        curr_mae = all_sweep[i][2]
        next_mae = all_sweep[i+1][2]
        
        if curr_m > prev_m and curr_m > next_m:
            peaks.append(all_sweep[i])
        elif curr_m == prev_m and curr_m == next_m:
            if curr_mae < prev_mae and curr_mae < next_mae:
                peaks.append(all_sweep[i])

    peaks = sorted(peaks, key=lambda x: (-x[1], x[2]))
    
    curr_matches, curr_mae, curr_details = -1, 999.0, []
    if current_offset is not None:
        curr_matches, curr_mae, curr_details = evaluate_offset(current_offset)

    return {
        "status": "success",
        "current_offset": current_offset,
        "current_matches": curr_matches,
        "current_mae": curr_mae,
        "best_offset": best_offset,
        "best_matches": best_matches,
        "best_mae": best_mae,
        "peaks": peaks[:5],
        "all_sweep": all_sweep
    }

def verify_session_clock(session_dir):
    try:
        df_gyro, narrations, watch_start_ms, watch_shots, current_offset, gyro_duration = load_session_data(session_dir)
        center = current_offset if current_offset is not None else 0.0
        res = run_clock_verification(df_gyro, narrations, watch_start_ms, watch_shots, current_offset, gyro_duration, center)
        if res['status'] == 'success':
            swing_narrations = [n for n in narrations if n['shot_type'] != "Facing up"]
            res['total_narrated'] = len(swing_narrations)
        return res
    except Exception as e:
        return {"status": "error", "message": str(e)}

def main():
    args = parse_args()
    if args.session_dir:
        # Run for single session
        session_dir = args.session_dir
        print(f"Running clock offset sweep for session: {os.path.basename(session_dir)}")
        try:
            res = verify_session_clock(session_dir)
            if res['status'] == 'success':
                print(f"Current Offset: {res['current_offset']}s -> Matches: {res['current_matches']}, MAE: {res['current_mae']:.3f}s")
                print(f"Best Offset Found: {res['best_offset']:.3f}s -> Matches: {res['best_matches']}, MAE: {res['best_mae']:.3f}s")
                print("Top Peaks:")
                for p in res['peaks']:
                    print(f"  Offset: {p[0]:.3f}s, Matches: {p[1]}, MAE: {p[2]:.3f}s")
            else:
                print(f"Error: {res['message']}")
        except Exception as e:
            print(f"Exception: {e}")
            import traceback
            traceback.print_exc()
    else:
        # Run for all sessions
        sessions = [os.path.join(args.sessions_base, d) for d in sorted(os.listdir(args.sessions_base)) 
                    if d.startswith("session-") and os.path.isdir(os.path.join(args.sessions_base, d))]
        print(f"Running clock offset verification across all {len(sessions)} sessions...")
        for s_dir in sessions:
            res = verify_session_clock(s_dir)
            s_name = os.path.basename(s_dir)
            if res['status'] == 'success':
                print(f"Session {s_name}: Best Offset = {res['best_offset']:.3f}s, Matches = {res['best_matches']}, MAE = {res['best_mae']*1000:.1f}ms (Current = {res['current_offset']}s)")
            else:
                print(f"Session {s_name}: Error: {res['message']}")

if __name__ == "__main__":
    main()
