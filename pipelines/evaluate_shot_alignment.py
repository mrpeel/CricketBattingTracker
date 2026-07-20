#!/usr/bin/env python3
"""
Pipeline 1: Shot Alignment Evaluation

For each session with ground truth narrations:
  - Re-derives best-available impact timestamps (Polar 500Hz if available, else watch gyro)
  - Updates ground_truth_aligned.csv with improved impact_time_seconds
  - Audits 1st pass peak detection rates per quality class across threshold sweep
  - Audits 2nd pass missed shot recovery
  - Compares three peak detection algorithms
  - Writes alignment_pipeline_report.md

This script modifies ground_truth_aligned.csv for sessions where Polar data
yields a higher-confidence impact timestamp. Narration data (shot_type, quality)
is never modified.
"""
import os
import sys
import json
import glob
import datetime
import numpy as np
import pandas as pd
from scipy.signal import find_peaks

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from automate_pipeline import load_watch_sensor

# ─── Configuration ────────────────────────────────────────────────────────────
BASE_DIR = "/Users/neilkloot/Code/Batting Sensor Stats"
SESSIONS_DIR = os.path.join(BASE_DIR, "live_watch_sessions")
REPORT_PATH = os.path.join(os.path.dirname(__file__), "..", "alignment_pipeline_report.md")

POLAR_ACC_THRESHOLD_MPS2 = 24.5   # m/s² — same threshold used in automate_pipeline.py
WATCH_GYRO_THRESHOLD = 1.5        # rad/s — current 1st pass threshold
THRESHOLD_SWEEP = np.arange(0.5, 4.1, 0.25)   # rad/s sweep range

# Quality class buckets for auditing
QUALITY_MAP = {
    "good":       ["good", "okay", "ok"],
    "excellent":  ["excellent", "perfect"],
    "poor":       ["poor", "bad"],
    "edge":       ["edge", "edged"],
    "miss":       ["miss", "missed"],
}
# Non-swing types: shot never happened, no bat swing occurred
# NOTE: quality (poor/edge/miss) is about HOW the shot was played, not WHETHER it happened
# Only shot_type drives the non-swing classification for alignment purposes
NON_SWING_TYPES = {"facing up", "no shot", "leave", "evade", "evasion"}

# ─── Helpers ──────────────────────────────────────────────────────────────────

def classify_quality(quality_str):
    """Map raw quality text to one of our 5 quality buckets."""
    q = (quality_str or "").lower().strip()
    for bucket, keywords in QUALITY_MAP.items():
        if any(kw in q for kw in keywords):
            return bucket
    return "good"  # default

def is_non_swing(shot_type):
    """Returns True if this narration event represents no bat-ball contact.
    Uses shot_type only — quality is about HOW the shot was played, not WHETHER it happened.
    Poor/edge/miss quality shots are still shots; they should still have gyro peaks."""
    st = (shot_type or "").lower()
    return any(t in st for t in NON_SWING_TYPES)

def measure_gyro_hz(df_gyro, n_samples=500):
    """Estimate sampling rate from first n_samples rows."""
    sub = df_gyro.head(n_samples)
    if len(sub) < 2:
        return 50.0
    duration = sub['seconds_elapsed'].iloc[-1] - sub['seconds_elapsed'].iloc[0]
    return (len(sub) - 1) / duration if duration > 0 else 50.0

def load_polar_acc(session_dir):
    """Load and normalise Polar accelerometer data to m/s²."""
    polar_dir = os.path.join(session_dir, "PolarSense")
    if not os.path.isdir(polar_dir):
        return None
    files = sorted(glob.glob(os.path.join(polar_dir, "*[aA][cC][cC]*.csv*")))
    if not files:
        return None
    frames = []
    for fpath in files:
        try:
            df = pd.read_csv(fpath, sep=';')
            if len(df.columns) >= 5:
                df.columns = ['phone_timestamp', 'sensor_ns', 'x', 'y', 'z'] + list(df.columns[5:])
                df['sensor_ns'] = pd.to_numeric(df['sensor_ns'], errors='coerce')
                df['x'] = pd.to_numeric(df['x'], errors='coerce') * 0.00980665  # mg → m/s²
                df['y'] = pd.to_numeric(df['y'], errors='coerce') * 0.00980665
                df['z'] = pd.to_numeric(df['z'], errors='coerce') * 0.00980665
                df = df.dropna(subset=['sensor_ns', 'x', 'y', 'z'])
                frames.append(df)
        except Exception:
            pass
    if not frames:
        return None
    combined = pd.concat(frames, ignore_index=True).sort_values('sensor_ns').reset_index(drop=True)
    t0 = combined['sensor_ns'].iloc[0]
    combined['seconds_elapsed'] = (combined['sensor_ns'] - t0) / 1e9
    combined['mag'] = np.sqrt(combined['x']**2 + combined['y']**2 + combined['z']**2)
    return combined

def get_polar_watch_offset(session_dir):
    """
    Retrieve the watch→polar time mapping function from the existing aligned CSV.
    Returns (slope, intercept) such that polar_t = watch_t * slope + intercept.
    Falls back to (1.0, 0.0) if not available.
    """
    aligned_path = os.path.join(session_dir, "ground_truth_aligned.csv")
    if not os.path.exists(aligned_path):
        return 1.0, 0.0
    df = pd.read_csv(aligned_path)
    # Check if Polar features are already present and valid
    if 'bottom_hand_acc_peak' not in df.columns:
        return 1.0, 0.0
    # Use shots that have both watch impact time and Polar features to estimate offset
    has_polar = df['bottom_hand_acc_peak'].notna()
    if has_polar.sum() < 3:
        return 1.0, 0.0
    # The existing pipeline already wrote the best offset to the CSV; we re-derive
    # it by checking the tap-sequence alignment that was already computed.
    # For now, return identity — the Polar timestamps in the aligned CSV were already
    # corrected in add_polar_features_to_aligned_shots(). The Polar acc search
    # below works in polar-time space using the seconds_elapsed from t0.
    return 1.0, 0.0


# ─── Core: Improved Impact Timestamp Derivation ───────────────────────────────

def refine_impact_timestamps(session_dir, df_aligned, df_gyro, df_polar_acc, polar_slope, polar_intercept):
    """
    For each shot in df_aligned, attempt to refine impact_time_seconds using
    Polar acc > 24.5 m/s² when available. Falls back to watch gyro.

    Returns: updated df_aligned, list of per-shot dicts with audit info.
    """
    audit_rows = []
    new_impact_times = []
    new_impact_ns = []
    refined_count = 0

    gyro_times = df_gyro['seconds_elapsed'].values
    gyro_mags  = df_gyro['mag'].values
    gyro_ns    = df_gyro['time'].values

    polar_times = df_polar_acc['seconds_elapsed'].values if df_polar_acc is not None else None
    polar_mags  = df_polar_acc['mag'].values if df_polar_acc is not None else None

    for _, row in df_aligned.iterrows():
        old_t = float(row['impact_time_seconds'])
        old_ns = int(row['impact_timestamp_ns'])
        shot_type = str(row.get('shot_type', ''))
        quality   = str(row.get('quality', ''))
        is_ns     = is_non_swing(shot_type)

        method = "watch_gyro"
        best_t = old_t
        best_ns = old_ns
        polar_peak_mag = np.nan
        polar_delta_ms = np.nan

        if df_polar_acc is not None and not is_ns:
            # Map watch impact time to polar time space
            polar_t_est = old_t * polar_slope + polar_intercept
            p_start = polar_t_est - 1.0
            p_end   = polar_t_est + 1.0
            mask = (polar_times >= p_start) & (polar_times <= p_end)
            if mask.any():
                win_mags  = polar_mags[mask]
                win_times = polar_times[mask]
                peak_idx  = np.argmax(win_mags)
                if win_mags[peak_idx] >= POLAR_ACC_THRESHOLD_MPS2:
                    # Found a valid Polar peak — convert back to watch time space
                    polar_peak_t = win_times[peak_idx]
                    watch_peak_t = (polar_peak_t - polar_intercept) / polar_slope
                    # Find closest gyro sample to this refined watch time for ns timestamp
                    close_idx = np.argmin(np.abs(gyro_times - watch_peak_t))
                    best_t  = float(gyro_times[close_idx])
                    best_ns = int(gyro_ns[close_idx])
                    polar_peak_mag  = float(win_mags[peak_idx])
                    polar_delta_ms  = (watch_peak_t - old_t) * 1000.0
                    method = "polar_acc"
                    refined_count += 1

        # Watch gyro fallback: if no Polar, snap to nearest gyro peak > WATCH_GYRO_THRESHOLD
        if method == "watch_gyro" and not is_ns:
            win_start = old_t - 1.0
            win_end   = old_t + 1.0
            mask = (gyro_times >= win_start) & (gyro_times <= win_end)
            if mask.any():
                win_mags  = gyro_mags[mask]
                win_times = gyro_times[mask]
                win_ns    = gyro_ns[mask]
                peak_idx  = np.argmax(win_mags)
                if win_mags[peak_idx] >= WATCH_GYRO_THRESHOLD:
                    best_t  = float(win_times[peak_idx])
                    best_ns = int(win_ns[peak_idx])

        new_impact_times.append(round(best_t, 6))
        new_impact_ns.append(best_ns)
        audit_rows.append({
            'shot_type':      shot_type,
            'quality':        quality,
            'quality_bucket': classify_quality(quality),
            'is_non_swing':   is_ns,
            'method':         method,
            'old_impact_t':   old_t,
            'new_impact_t':   best_t,
            'delta_ms':       polar_delta_ms,
            'polar_peak_mag': polar_peak_mag,
        })

    df_aligned = df_aligned.copy()
    df_aligned['impact_time_seconds'] = new_impact_times
    df_aligned['impact_timestamp_ns'] = new_impact_ns
    return df_aligned, audit_rows, refined_count


# ─── Stage B: 1st Pass Threshold Sweep ────────────────────────────────────────

def audit_threshold_sweep(df_aligned, df_gyro):
    """
    For each threshold in THRESHOLD_SWEEP, count what percentage of shots in each
    quality class have a gyro peak >= threshold within ±2.5s of their impact time.
    Returns: dict[threshold] → dict[quality_bucket] → {"found": int, "total": int}
    """
    gyro_times = df_gyro['seconds_elapsed'].values
    gyro_mags  = df_gyro['mag'].values

    results = {}
    for thr in THRESHOLD_SWEEP:
        thr_key = round(float(thr), 2)
        bucket_counts = {b: {"found": 0, "total": 0} for b in list(QUALITY_MAP.keys()) + ["non_swing"]}
        for _, row in df_aligned.iterrows():
            shot_type = str(row.get('shot_type', ''))
            quality   = str(row.get('quality', ''))
            impact_t  = float(row['impact_time_seconds'])
            mask = (gyro_times >= impact_t - 2.5) & (gyro_times <= impact_t + 2.5)
            found = mask.any() and gyro_mags[mask].max() >= thr

            if is_non_swing(shot_type):
                # For non-swings we DON'T want to find a peak: track false positive rate
                bucket_counts["non_swing"]["total"] += 1
                if found:
                    bucket_counts["non_swing"]["found"] += 1
            else:
                bucket = classify_quality(quality)
                bucket_counts[bucket]["total"] += 1
                if found:
                    bucket_counts[bucket]["found"] += 1
        results[thr_key] = bucket_counts
    return results


# ─── Stage C: 2nd Pass Missed Shot Recovery ───────────────────────────────────

def audit_missed_shot_recovery(df_aligned, df_gyro):
    """
    For shots that are missed at the standard threshold (1.5 rad/s),
    test whether lowering the threshold to 0.75 rad/s, OR using peak prominence,
    would recover them.
    """
    gyro_times = df_gyro['seconds_elapsed'].values
    gyro_mags  = df_gyro['mag'].values

    missed_standard = []
    for _, row in df_aligned.iterrows():
        shot_type = str(row.get('shot_type', ''))
        if is_non_swing(shot_type):
            continue
        impact_t = float(row['impact_time_seconds'])
        mask = (gyro_times >= impact_t - 2.5) & (gyro_times <= impact_t + 2.5)
        found = mask.any() and gyro_mags[mask].max() >= WATCH_GYRO_THRESHOLD
        if not found:
            missed_standard.append(row)

    recovery_results = {
        "missed_at_standard":   len(missed_standard),
        "recovered_at_0.75":    0,
        "recovered_prominence": 0,
        "unrecoverable":        0,
    }

    # Pre-compute prominence peaks over the whole session
    peak_indices, peak_props = find_peaks(gyro_mags, prominence=0.5, distance=10)
    peak_times_prom = gyro_times[peak_indices]

    for row in missed_standard:
        impact_t = float(row['impact_time_seconds'])
        mask = (gyro_times >= impact_t - 2.5) & (gyro_times <= impact_t + 2.5)

        # Test lower threshold
        recovered_low = mask.any() and gyro_mags[mask].max() >= 0.75
        # Test prominence detector
        near_prom = np.any((peak_times_prom >= impact_t - 2.5) & (peak_times_prom <= impact_t + 2.5))

        if recovered_low:
            recovery_results["recovered_at_0.75"] += 1
        elif near_prom:
            recovery_results["recovered_prominence"] += 1
        else:
            recovery_results["unrecoverable"] += 1

    return recovery_results, missed_standard


# ─── Stage D: Algorithm Comparison ───────────────────────────────────────────

def compare_algorithms(df_aligned, df_gyro):
    """
    Compare 3 peak detection methods for how many swing shots they correctly detect.
    Returns per-algorithm detection rates.
    """
    gyro_times = df_gyro['seconds_elapsed'].values
    gyro_mags  = df_gyro['mag'].values

    swing_rows = [row for _, row in df_aligned.iterrows()
                  if not is_non_swing(str(row.get('shot_type','')))]

    # Method 1: Threshold (current)
    m1 = sum(1 for row in swing_rows
             if (mask := (gyro_times >= float(row['impact_time_seconds'])-2.5) &
                          (gyro_times <= float(row['impact_time_seconds'])+2.5)).any()
                and gyro_mags[mask].max() >= WATCH_GYRO_THRESHOLD)

    # Method 2: scipy peak prominence (prominence >= 0.5, min distance 5 samples)
    prom_idx, _ = find_peaks(gyro_mags, prominence=0.5, distance=5)
    prom_times  = gyro_times[prom_idx]
    m2 = sum(1 for row in swing_rows
             if np.any((prom_times >= float(row['impact_time_seconds'])-2.5) &
                       (prom_times <= float(row['impact_time_seconds'])+2.5)))

    # Method 3: Short-time RMS envelope + threshold
    window_samples = max(3, int(len(gyro_mags) / len(gyro_times) * 0.1))  # ~0.1s window
    rms = np.sqrt(np.convolve(gyro_mags**2,
                              np.ones(window_samples)/window_samples, mode='same'))
    rms_threshold = np.percentile(rms, 80)   # top 20% of RMS signal
    env_idx, _ = find_peaks(rms, height=rms_threshold, distance=5)
    env_times   = gyro_times[env_idx]
    m3 = sum(1 for row in swing_rows
             if np.any((env_times >= float(row['impact_time_seconds'])-2.5) &
                       (env_times <= float(row['impact_time_seconds'])+2.5)))

    n = len(swing_rows)
    return {
        "n_swing_shots": n,
        "threshold_found": m1, "threshold_rate": m1/n if n else 0.0,
        "prominence_found": m2, "prominence_rate": m2/n if n else 0.0,
        "envelope_found": m3, "envelope_rate": m3/n if n else 0.0,
    }


# ─── Session Alignment Confidence ─────────────────────────────────────────────

def get_alignment_confidence(session_dir, df_aligned, df_gyro):
    """
    Derive alignment confidence metrics from the existing aligned CSV.

    The MAE metric measures: |impact_time - (sensor_narr_time - 2.5)|.
    A correctly aligned shot should have impact ~2.5s BEFORE the narration,
    so a MAE near 0 means the impact was snapped precisely to the expected lag.
    High MAE (>1.5s) indicates the DP alignment is using fallback positions.
    """
    swing_rows = df_aligned[~df_aligned.apply(
        lambda r: is_non_swing(str(r.get('shot_type',''))), axis=1)]

    fallback_rate = float(swing_rows['is_fallback'].mean()) if 'is_fallback' in swing_rows.columns else np.nan
    gyro_times = df_gyro['seconds_elapsed'].values
    gyro_mags  = df_gyro['mag'].values

    lags = []  # deviation from expected shot-specific lag
    matched = 0
    for _, row in swing_rows.iterrows():
        t = float(row['impact_time_seconds'])
        mask = (gyro_times >= t - 2.5) & (gyro_times <= t + 2.5)
        if mask.any() and gyro_mags[mask].max() >= WATCH_GYRO_THRESHOLD:
            matched += 1
            # Expected: shot-specific lag before narration
            narr_t = float(row.get('sensor_narr_time_seconds', t + 2.5))
            shot_type = row.get('shot_type', '')
            
            # Shot-specific expected lag based on biomechanics
            st = str(shot_type).lower()
            if "straight drive" in st:
                expected_lag = 4.5
            elif "power drive" in st:
                expected_lag = 3.5
            elif "sweep" in st:
                expected_lag = 2.0
            elif "push" in st or "punch" in st:
                expected_lag = 3.0
            elif "slog" in st or "cut" in st or "guide" in st or "pull" in st:
                expected_lag = 2.8
            elif "flick" in st or "cover drive" in st or "on drive" in st:
                expected_lag = 2.7
            else:
                expected_lag = 2.5
                
            expected_impact = narr_t - expected_lag
            lags.append(abs(t - expected_impact))

    match_rate = matched / len(swing_rows) if len(swing_rows) > 0 else 0.0
    mae = float(np.mean(lags)) if lags else 999.0
    p75_dev = float(np.percentile(lags, 75)) if lags else 999.0
    
    # Confidence: high match rate + small 75th percentile deviation from expected lag
    confidence = "HIGH"   if (match_rate >= 0.85 and p75_dev < 1.0) else \
                 "MEDIUM" if (match_rate >= 0.70 and p75_dev < 2.0) else "LOW"

    return {
        "match_rate": match_rate,
        "mae_s": mae,
        "p75_dev": p75_dev,
        "fallback_rate": fallback_rate,
        "confidence": confidence,
        "n_swings": len(swing_rows),
    }


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    print("=" * 70)
    print("Pipeline 1: Shot Alignment Evaluation")
    print(f"Started: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    sessions = sorted([
        d for d in os.listdir(SESSIONS_DIR)
        if d.startswith("session") and os.path.isdir(os.path.join(SESSIONS_DIR, d))
    ])

    # Aggregated results
    all_session_results = []
    all_threshold_results = {}   # thr → quality_bucket → {found, total} (summed across sessions)
    all_algo_results = {"threshold": 0, "prominence": 0, "envelope": 0, "total": 0}
    all_recovery = {"missed_at_standard": 0, "recovered_at_0.75": 0,
                    "recovered_prominence": 0, "unrecoverable": 0}
    all_refined = 0
    all_polar_sessions = 0
    sessions_processed = 0
    low_confidence = []

    for session_id in sessions:
        session_dir = os.path.join(SESSIONS_DIR, session_id)
        aligned_path = os.path.join(session_dir, "ground_truth_aligned.csv")
        if not os.path.exists(aligned_path):
            continue

        print(f"\n📁 {session_id}")

        # Load data
        df_gyro = load_watch_sensor(session_dir, "WatchGyroscope")
        if df_gyro.empty:
            print("  ⚠️  No gyro data — skipping")
            continue
        df_gyro['mag'] = np.sqrt(df_gyro['x']**2 + df_gyro['y']**2 + df_gyro['z']**2)

        df_aligned = pd.read_csv(aligned_path)
        if df_aligned.empty:
            continue

        # Ensure 'is_fallback' column exists (older sessions may not have it)
        if 'is_fallback' not in df_aligned.columns:
            df_aligned['is_fallback'] = False

        watch_hz = measure_gyro_hz(df_gyro)
        df_polar_acc = load_polar_acc(session_dir)
        has_polar = df_polar_acc is not None

        data_profile = "50hz_watch"
        if has_polar:
            data_profile = "100hz_watch_polar" if watch_hz >= 90 else "50hz_watch_polar"
            all_polar_sessions += 1

        # Stage A: alignment confidence
        conf = get_alignment_confidence(session_dir, df_aligned, df_gyro)
        if conf["confidence"] == "LOW":
            low_confidence.append(session_id)
        print(f"  Alignment: {conf['confidence']} (match={conf['match_rate']:.0%}, P75 Dev={conf['p75_dev']:.2f}s, MAE={conf['mae_s']:.2f}s, fallback={conf['fallback_rate']:.0%})")

        # Polar offset — use identity if not available (polar features already in aligned CSV)
        polar_slope, polar_intercept = 1.0, 0.0

        # Stage: Refine impact timestamps
        df_updated, audit_rows, refined = refine_impact_timestamps(
            session_dir, df_aligned, df_gyro, df_polar_acc, polar_slope, polar_intercept)
        all_refined += refined

        # Write updated ground_truth_aligned.csv
        df_updated.to_csv(aligned_path, index=False)
        if refined > 0:
            print(f"  ✅ Refined {refined} impact timestamps using Polar 500Hz data")

        # Stage B: Threshold sweep
        thr_results = audit_threshold_sweep(df_updated, df_gyro)
        for thr, buckets in thr_results.items():
            if thr not in all_threshold_results:
                all_threshold_results[thr] = {b: {"found": 0, "total": 0}
                                               for b in buckets}
            for b, counts in buckets.items():
                all_threshold_results[thr][b]["found"] += counts["found"]
                all_threshold_results[thr][b]["total"] += counts["total"]

        # Stage C: 2nd pass recovery
        recovery, _ = audit_missed_shot_recovery(df_updated, df_gyro)
        for k in all_recovery:
            all_recovery[k] += recovery[k]

        # Stage D: Algorithm comparison
        algo = compare_algorithms(df_updated, df_gyro)
        all_algo_results["threshold"]  += algo["threshold_found"]
        all_algo_results["prominence"] += algo["prominence_found"]
        all_algo_results["envelope"]   += algo["envelope_found"]
        all_algo_results["total"]      += algo["n_swing_shots"]

        all_session_results.append({
            "session_id":   session_id,
            "data_profile": data_profile,
            "watch_hz":     round(watch_hz),
            "has_polar":    has_polar,
            "n_swings":     conf["n_swings"],
            "match_rate":   conf["match_rate"],
            "mae_s":        conf["mae_s"],
            "p75_dev":      conf["p75_dev"],
            "fallback_rate": conf["fallback_rate"],
            "confidence":   conf["confidence"],
            "polar_refined": refined,
        })
        sessions_processed += 1

    # ─── Write Report ─────────────────────────────────────────────────────────
    print(f"\n\n{'='*70}")
    print(f"Writing report to: {REPORT_PATH}")

    total_shots = all_algo_results["total"]

    with open(REPORT_PATH, "w") as f:
        f.write("# Shot Alignment Pipeline Report\n\n")
        f.write(f"**Generated:** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"**Sessions Processed:** {sessions_processed}  |  "
                f"**With Polar:** {all_polar_sessions}  |  "
                f"**Total Swing Shots:** {total_shots}  |  "
                f"**Polar Timestamp Refinements:** {all_refined}\n\n")

        # Section 1: Session confidence table
        f.write("## 1. Per-Session Alignment Confidence\n\n")
        f.write("| Session | Profile | Hz | Swings | Match Rate | P75 Dev (s) | MAE (s) | Fallback | Confidence | Polar Refined |\n")
        f.write("|---|---|---|---|---|---|---|---|---|---|\n")
        for r in all_session_results:
            f.write(f"| {r['session_id']} | {r['data_profile']} | {r['watch_hz']} "
                    f"| {r['n_swings']} | {r['match_rate']:.0%} | {r['p75_dev']:.2f} | {r['mae_s']:.2f} "
                    f"| {r['fallback_rate']:.0%} | {r['confidence']} "
                    f"| {'✅ ' + str(r['polar_refined']) if r['polar_refined'] > 0 else '—'} |\n")

        if low_confidence:
            f.write(f"\n> [!WARNING]\n> **Low-confidence sessions requiring manual review:** "
                    f"{', '.join(low_confidence)}\n\n")

        # Section 2: Threshold sweep
        f.write("## 2. 1st Pass Detection — Threshold Sensitivity\n\n")
        f.write("Detection rate (%) for each shot quality class at each gyro threshold.\n"
                "**Non-swing column = false positive rate (lower is better).**\n"
                "Current threshold highlighted with `→`.\n\n")
        quality_cols = ["excellent", "good", "poor", "edge", "miss", "non_swing"]
        f.write("| Threshold (rad/s) | Excellent | Good | Poor | Edge | Miss | Non-Swing (FP) |\n")
        f.write("|---|---|---|---|---|---|---|\n")
        for thr in sorted(all_threshold_results.keys()):
            buckets = all_threshold_results[thr]
            marker = " ←" if abs(thr - WATCH_GYRO_THRESHOLD) < 0.01 else ""
            row_parts = [f"**{thr:.2f}**{marker}"]
            for b in quality_cols:
                bc = buckets.get(b, {"found": 0, "total": 0})
                pct = bc["found"] / bc["total"] if bc["total"] > 0 else 0.0
                row_parts.append(f"{pct:.0%} ({bc['found']}/{bc['total']})")
            f.write("| " + " | ".join(row_parts) + " |\n")

        # Recommended threshold from sweep
        # Pick threshold that maximises (good_rate + excellent_rate) while keeping poor_rate >= 40%
        best_thr = WATCH_GYRO_THRESHOLD
        best_score = -1.0
        for thr, buckets in all_threshold_results.items():
            g = buckets.get("good", {})
            e = buckets.get("excellent", {})
            p = buckets.get("poor", {})
            ns = buckets.get("non_swing", {})
            g_rate  = g["found"]/g["total"] if g["total"] > 0 else 0.0
            e_rate  = e["found"]/e["total"] if e["total"] > 0 else 0.0
            p_rate  = p["found"]/p["total"] if p["total"] > 0 else 0.0
            fp_rate = ns["found"]/ns["total"] if ns["total"] > 0 else 1.0
            # Score: maximise good+excellent recall, penalise FP rate
            score = (g_rate + e_rate) / 2.0 - fp_rate * 0.5
            if score > best_score:
                best_score = score
                best_thr = thr

        f.write(f"\n**Recommended threshold: `{best_thr:.2f} rad/s`** "
                f"(selected to maximise good/excellent recall while minimising false positives)\n\n")

        # Section 3: 2nd pass recovery
        f.write("## 3. 2nd Pass Missed Shot Recovery\n\n")
        total_missed = all_recovery["missed_at_standard"]
        f.write(f"**Total shots missed at standard threshold ({WATCH_GYRO_THRESHOLD} rad/s):** {total_missed}\n\n")
        if total_missed > 0:
            f.write("| Recovery Method | Shots Recovered | Rate |\n")
            f.write("|---|---|---|\n")
            f.write(f"| Lowered threshold (0.75 rad/s) | {all_recovery['recovered_at_0.75']} "
                    f"| {all_recovery['recovered_at_0.75']/total_missed:.0%} |\n")
            f.write(f"| Peak prominence detector | {all_recovery['recovered_prominence']} "
                    f"| {all_recovery['recovered_prominence']/total_missed:.0%} |\n")
            f.write(f"| Unrecoverable (no signal at any threshold) | {all_recovery['unrecoverable']} "
                    f"| {all_recovery['unrecoverable']/total_missed:.0%} |\n\n")

        total_recoverable = all_recovery["recovered_at_0.75"] + all_recovery["recovered_prominence"]
        if total_missed > 0:
            f.write(f"**Total potentially recoverable missed shots: {total_recoverable}/{total_missed} "
                    f"({total_recoverable/total_missed:.0%})**\n\n")

        # Section 4: Algorithm comparison
        f.write("## 4. Peak Detection Algorithm Comparison\n\n")
        f.write(f"Results across all sessions ({total_shots} swing shots).\n\n")
        f.write("| Algorithm | Detected | Rate | Notes |\n")
        f.write("|---|---|---|---|\n")
        if total_shots > 0:
            f.write(f"| Threshold + DP (current) | {all_algo_results['threshold']} "
                    f"| {all_algo_results['threshold']/total_shots:.1%} | `{WATCH_GYRO_THRESHOLD} rad/s` |\n")
            f.write(f"| Peak Prominence (scipy) | {all_algo_results['prominence']} "
                    f"| {all_algo_results['prominence']/total_shots:.1%} | prominence ≥ 0.5 rad/s |\n")
            f.write(f"| Envelope RMS Detector | {all_algo_results['envelope']} "
                    f"| {all_algo_results['envelope']/total_shots:.1%} | 0.1s RMS window, top 20% |\n\n")

        # Recommendation
        best_algo_count = max(all_algo_results['threshold'],
                              all_algo_results['prominence'],
                              all_algo_results['envelope'])
        if all_algo_results['threshold'] == best_algo_count:
            best_algo = "current threshold + DP system"
        elif all_algo_results['prominence'] == best_algo_count:
            best_algo = "scipy peak prominence"
        else:
            best_algo = "RMS envelope detector"

        f.write(f"**Recommended algorithm: `{best_algo}`**\n\n")

        if all_algo_results['threshold'] == best_algo_count:
            f.write("> [!NOTE]\n> The current threshold + DP alignment system performs well. "
                    f"Consider adjusting the detection threshold to `{best_thr:.2f} rad/s` "
                    f"based on the sensitivity sweep above.\n\n")
        else:
            f.write("> [!IMPORTANT]\n> A different algorithm outperformed the current system. "
                    "Consider replacing the peak detection step in `automate_pipeline.py` "
                    f"with the `{best_algo}` approach.\n\n")

        # Section 5: Polar timestamp refinement summary
        f.write("## 5. Polar Timestamp Refinement Summary\n\n")
        f.write(f"Impact timestamps refined using 500Hz Polar accelerometer: **{all_refined} shots** "
                f"across {all_polar_sessions} Polar sessions.\n\n")
        f.write("Polar data at 500Hz provides ±2ms timestamp resolution vs. ±20ms from the 50Hz watch gyro. "
                "The updated `ground_truth_aligned.csv` files now contain the best available impact "
                "timestamps for all sessions.\n\n")

        # Section 6: Action summary
        f.write("## 6. Recommended Actions\n\n")
        actions = []
        if best_thr != WATCH_GYRO_THRESHOLD:
            actions.append(f"Update `WATCH_GYRO_THRESHOLD` in `automate_pipeline.py` from "
                           f"`{WATCH_GYRO_THRESHOLD}` to `{best_thr:.2f}` rad/s")
        if all_algo_results['threshold'] != best_algo_count:
            actions.append(f"Consider replacing threshold-based peak detection with `{best_algo}` "
                           "in `automate_pipeline.py`")
        if low_confidence:
            actions.append(f"Manually review low-confidence sessions and consider re-running "
                           f"`automate_pipeline.py`: {', '.join(low_confidence)}")
        if total_recoverable > 0:
            actions.append(f"Consider adopting a 2-stage detection threshold: "
                           f"primary={best_thr:.2f} rad/s, recovery=0.75 rad/s "
                           f"for shots initially missed (potential recovery: {total_recoverable} shots)")
        if not actions:
            actions.append("No changes required — current alignment system is performing well.")
        for i, a in enumerate(actions, 1):
            f.write(f"{i}. {a}\n")

    # Save optimized config for generate_kotlin_forest.py to sync to Android
    config_out = os.path.join(BASE_DIR, "optimized_detection_config.json")
    try:
        with open(config_out, "w") as jf:
            json.dump({"WATCH_GYRO_THRESHOLD": float(best_thr)}, jf)
        print(f"✅ Saved optimized watch gyro threshold to {config_out}")
    except Exception as e:
        print(f"⚠️ Failed to save optimized watch gyro threshold: {e}")

    print(f"\n✅ Alignment evaluation complete.")
    print(f"   Sessions processed: {sessions_processed}")
    print(f"   Polar timestamp refinements: {all_refined}")
    print(f"   Low-confidence sessions: {len(low_confidence)}")
    print(f"   Report written to: {REPORT_PATH}")

if __name__ == "__main__":
    main()
