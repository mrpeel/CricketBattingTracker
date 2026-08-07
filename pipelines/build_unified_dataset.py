#!/usr/bin/env python3
"""
build_unified_dataset.py — Construct unified-row dataset for POC TCN model.

For each selected session:
  1. Load raw watch sensors from .bin.gz (Accelerometer, Gyroscope, Gravity,
     LinearAcceleration, Magnetometer, GameOrientation, Steps).
  2. Load raw polar sensors from .bin.gz OR .csv.gz (Accelerometer, Gyroscope,
     Magnetometer).
  3. Apply TAP_SEQ anchor-driven alignment (CV-filter watch TAP_SEQs, search
     polar ± 20s of each filtered watch drill, regression-fit alignment).
  4. Project all sensor streams onto a common relative-ms axis (anchor = watch
     SYSTEM_START wall ms; polar samples mapped via alignment).
  5. Resample to the per-session LOWEST resolution:
       - Polar present: 2ms (500Hz)
       - Watch only: 20ms (50Hz)
     Higher-rate polar samples are max-bucketed (peak preserve impacts).
     Lower-rate watch samples are forward-filled (last value carried).
  6. Per-row labels from narrations_raw.json:
       - [t-50ms,  t+300ms]   -> shot class (Pull, Defence, Flick, Drive, ...)
       - [t-1500ms, t-50ms]   -> pre_shot
       - otherwise           -> no_shot
  7. Save as parquet: session_<ts>_unified.parquet
"""
import gzip, struct, os, re, json, sys
import numpy as np
import pandas as pd

BASE = "/Users/neilkloot/Code/Batting Sensor Stats/live_watch_sessions"
OUTPUT_DIR = "/Users/neilkloot/Code/Batting Sensor Stats/poc_unified_dataset"
os.makedirs(OUTPUT_DIR, exist_ok=True)

import glob as _glob
# --- Session split (per architect 2026-07-28) ---
# Use ALL sessions except the holdout session_2026-07-18 (which has 114 mixed shots)
HOLDOUT = "session_2026-07-18_13-44-09"
def discover_sessions():
    all_dirs = sorted(os.path.basename(p) for p in _glob.glob(os.path.join(BASE, "session_2026-*")) if os.path.isdir(p))
    # Only include sessions that have narrations_raw.json and core watch sensors
    usable = []
    for s in all_dirs:
        np_ = os.path.join(BASE, s, "narrations_raw.json")
        w_gyr = os.path.join(BASE, s, "WatchGyroscope.bin.gz") or \
                os.path.join(BASE, s, "WatchGyroscope.csv.gz")
        if os.path.exists(np_) and (os.path.exists(w_gyr)):
            usable.append(s)
    return usable
TRAIN = [s for s in discover_sessions() if s != HOLDOUT]
SESSIONS = TRAIN + [HOLDOUT]

# --- Alignment parameters (validated earlier today) ---
TAP_CV_THRESHOLD = 0.10
TAP_DEDUP_MS = 1500
POLAR_SEARCH_WINDOW_MS = 20_000
POLAR_TAP_THRESHOLD = 12.0  # m/s^2
TAP_MIN_GAP_MS = 200
TAP_MAX_GAP_MS = 1500
TAP_MAX_SPAN_MS = 5000

# --- Label windows (relative to narrated impact time) ---
# Tightened pre_shot to 500ms (was 1500ms) after first POC showed over-labelling
# of between-stance activity as pre_shot. The 500ms immediately before the
# shot is the backswing build-up and is genuinely distinct from random stance.
LABEL_SHOT_BEFORE_MS = 50
LABEL_SHOT_AFTER_MS = 300
LABEL_PRE_BEFORE_MS = 500
LABEL_PRE_AFTER_MS = 50

# --- Label normalisation ---
def normalise_shot_type(st):
    s = (st or '').lower()
    if 'power drive' in s or 'lofted drive' in s:
        return 'POWER DRIVE'
    if 'pull' in s or 'hook' in s or 'full shot' in s or 'foot shot' in s or 'push up' in s or 'which shot' in s:
        return 'PULL/HOOK'
    if 'flick' in s or 'click' in s or 'quick' in s or 'glance' in s or 'leg glance' in s:
        return 'GLANCE/FLICK'
    if 'guide' in s or 'deflection' in s or 'steer' in s or 'glide' in s or 'square upper cut' in s:
        return 'DEFLECTION/GUIDE'
    if 'cover drive' in s or 'straight drive' in s or 'on drive' in s or 'off drive' in s or 'drive' in s or 'back foot' in s or 'forward defense' in s or 'back defense' in s or 'defence' in s or 'defense' in s:
        return 'DRIVE/DEFENCE'
    if 'cut' in s or 'punch' in s:
        return 'CUT/PUNCH'
    if 'slog' in s:
        return 'SLOG'
    if 'sweep' in s:
        return 'SWEEP'
    if 'leave' in s:
        return 'Leave'
    return None  # drop "No shot", "Facing up", "Evade", "Block", unknown

def is_real_shot(st):
    s = (st or '').lower()
    if any(k in s for k in ['facing up','no shot','leave','evade','block']): return False
    return True

# ---------- binary sensor parsers ----------
def load_watch_imu_bin(path):
    if not os.path.exists(path): return None
    fmt = "<qffff"; rs = struct.calcsize(fmt)
    out = []
    with gzip.open(path,'rb') as f: data = f.read()
    n = len(data)//rs
    for i in range(n):
        t,sec,x,y,z = struct.unpack_from(fmt, data, i*rs)
        out.append((t, x, y, z))
    return out

def load_watch_rot_bin(path):
    if not os.path.exists(path): return None
    fmt = "<qfffff"; rs = struct.calcsize(fmt)
    out = []
    with gzip.open(path,'rb') as f: data = f.read()
    n = len(data)//rs
    for i in range(n):
        t,sec,qx,qy,qz,qw = struct.unpack_from(fmt, data, i*rs)
        out.append((t, qx, qy, qz, qw))
    return out

def load_watch_steps_bin(path):
    if not os.path.exists(path): return []
    fmt = "<qf"; rs = struct.calcsize(fmt)
    out = []
    with gzip.open(path,'rb') as f: data = f.read()
    n = len(data)//rs
    for i in range(n):
        t, _ = struct.unpack_from(fmt, data, i*rs)
        out.append(t)
    return out

# ---------- polar loaders (binary <qqfff> or CSV ;) ----------
def convert_polar_units(x, y, z, is_gyro):
    if is_gyro:
        d2r = np.pi / 180.0
        return x*d2r, y*d2r, z*d2r
    else:
        g = 0.00980665
        return x*g, y*g, z*g

def load_polar_bin(path, is_gyro):
    if not os.path.exists(path): return None
    fmt = "<qqfff"; rs = struct.calcsize(fmt)
    out = []
    with gzip.open(path,'rb') as f: data = f.read()
    n = len(data)//rs
    for i in range(n):
        phoneMs, sensorNs, x, y, z = struct.unpack_from(fmt, data, i*rs)
        x, y, z = convert_polar_units(float(x), float(y), float(z), is_gyro)
        out.append((phoneMs, sensorNs, x, y, z))
    return out

def load_polar_csv(path, is_gyro):
    if not os.path.exists(path): return None
    out = []
    from datetime import datetime
    datefmt = "%Y-%m-%dT%H:%M:%S.%f"
    with gzip.open(path,'rt') as f:
        f.readline()  # skip header
        for line in f:
            parts = line.strip().split(';')
            if len(parts) < 5: continue
            try:
                phoneMs = int(datetime.strptime(parts[0], datefmt).timestamp() * 1000)
            except Exception:
                try: phoneMs = int(float(parts[0]))
                except Exception: continue
            try:
                sensorNs = int(parts[1])
                x = float(parts[2]); y = float(parts[3]); z = float(parts[4])
            except Exception:
                continue  # skip malformed rows (empty fields, non-numeric, etc.)
            x, y, z = convert_polar_units(x, y, z, is_gyro)
            out.append((phoneMs, sensorNs, x, y, z))
    return out

def load_polar(session_dir, name, is_gyro):
    bin_path = os.path.join(session_dir, "PolarSense", f"{name}.bin.gz")
    csv_path = os.path.join(session_dir, "PolarSense", f"{name}.csv.gz")
    if os.path.exists(bin_path): return load_polar_bin(bin_path, is_gyro)
    if os.path.exists(csv_path): return load_polar_csv(csv_path, is_gyro)
    return None

# ---------- timeline / TAP_SEQ ----------
def _count_tap_seqs(session_dir):
    path = os.path.join(session_dir, "latest_timeline.txt")
    if not os.path.exists(path): return 0
    with open(path) as f:
        return sum(1 for line in f if line.startswith("TAP_SEQ:"))

def parse_timeline(session_dir, watch_start_ns, watch_start_wall_ms):
    path = os.path.join(session_dir, "latest_timeline.txt")
    taps = []
    sys_start = None
    if not os.path.exists(path): return None, taps
    with open(path) as f:
        for line in f:
            if line.startswith("SYSTEM_START:"):
                m = re.search(r"Ts=(\d+)", line)
                if m: sys_start = int(m.group(1))
            elif line.startswith("TAP_SEQ:"):
                tm = re.findall(r"T\d=(\d+)", line)
                if len(tm) == 5:
                    tn = [int(x) for x in tm]
                    true_wall = watch_start_wall_ms + (tn[4] - watch_start_ns) // 1_000_000
                    taps.append((true_wall, tn))
    return sys_start, taps

def filter_real_tap_sequences(taps):
    """CV≤0.10 + dedup 1500ms"""
    if not taps: return taps
    annotated = []
    for wall, seq in taps:
        gaps = np.array([(seq[j+1]-seq[j])/1e6 for j in range(4)], dtype=float)
        mean = gaps.mean()
        cv = float(gaps.std()/mean) if abs(mean) > 1e-6 else 0.0
        annotated.append({'wall':wall, 'seq':seq, 'cv':cv})
    annotated.sort(key=lambda a: a['cv'])
    kept = []
    for a in annotated:
        if a['cv'] > TAP_CV_THRESHOLD: continue
        if any(abs(a['wall']-k['wall']) < TAP_DEDUP_MS for k in kept): continue
        kept.append(a)
    kept.sort(key=lambda a: a['wall'])
    return [(a['wall'], a['seq']) for a in kept]

def find_polar_taps_near_anchor(polar_phone_times, polar_mags, anchor_wall_ms):
    """Search polar acc stream in ±20s of anchor, return 5-tap seq (phoneMs list)
    or None."""
    lo = np.searchsorted(polar_phone_times, anchor_wall_ms - POLAR_SEARCH_WINDOW_MS)
    hi = np.searchsorted(polar_phone_times, anchor_wall_ms + POLAR_SEARCH_HALF_MS)
    if hi <= lo + 5: return None
    win_phone = polar_phone_times[lo:hi+1]
    win_mags = polar_mags[lo:hi+1]
    cand = np.where(win_mags >= POLAR_TAP_THRESHOLD)[0]
    local_peaks = []
    for idx in cand:
        s_ms = win_phone[idx]
        ws = np.searchsorted(win_phone, s_ms-150)
        we = np.searchsorted(win_phone, s_ms+150)
        winmax = win_mags[ws:we+1].max() if we>ws else win_mags[idx]
        if win_mags[idx] >= winmax:
            if not any(abs(s_ms - p) < TAP_MIN_GAP_MS for p in local_peaks):
                local_peaks.append(float(s_ms))
    i = 0
    while i <= len(local_peaks) - 5:
        seq = local_peaks[i:i+5]
        span = seq[-1] - seq[0]
        if span <= TAP_MAX_SPAN_MS:
            ok = True
            for j in range(1,5):
                g = seq[j]-seq[j-1]
                if g < TAP_MIN_GAP_MS or g > TAP_MAX_GAP_MS:
                    ok = False; break
            if ok: return seq
        i += 1
    return None

POLAR_SEARCH_HALF_MS = POLAR_SEARCH_WINDOW_MS

def align_polar_to_watch(watch_taps, polar_phone_times, polar_acc_mags):
    """Returns alignment dict with confidence metrics, or None.
    Confidence:
      method:   'anchor_regression' | 'wall_clock_fallback' | 'anchor_single'
      n_anchors: number of watch drills matched to a polar 5-tap sequence
      r_squared: regression R² (only for anchor_regression with >=2 matches)
      confidence: 'high' (n>=3 and r2>=0.99) | 'medium' (n>=2) | 'low' (n<=1 or r2<0.95)
    """
def rotate_vectors_quat(q_arr, v_arr):
    """Vectorized quaternion rotation: rotates 3D vectors v_arr by quaternions q_arr."""
    qx = q_arr[:, 0]; qy = q_arr[:, 1]; qz = q_arr[:, 2]; qw = q_arr[:, 3]
    vx = v_arr[:, 0]; vy = v_arr[:, 1]; vz = v_arr[:, 2]
    
    tx = 2.0 * (qy * vz - qz * vy)
    ty = 2.0 * (qz * vx - qx * vz)
    tz = 2.0 * (qx * vy - qy * vx)
    
    rx = vx + qw * tx + (qy * tz - qz * ty)
    ry = vy + qw * ty + (qz * tx - qx * tz)
    rz = vz + qw * tz + (qx * ty - qy * vx)
    
    return np.column_stack([rx, ry, rz]).astype(np.float32)

def find_impact_peaks_alignment(w_gyro_rel, w_gyro_mags, polar_phone_times, polar_acc_mags, sys_start_ms):
    """Tier 3 alignment: Cross-correlate watch gyro peaks with Polar acc peaks."""
    from scipy.signal import find_peaks
    if len(w_gyro_mags) == 0 or len(polar_acc_mags) == 0:
        return None
    w_pks_idx, _ = find_peaks(w_gyro_mags, height=3.5, distance=75)
    if len(w_pks_idx) < 3:
        w_pks_idx, _ = find_peaks(w_gyro_mags, height=2.0, distance=50)
    if len(w_pks_idx) < 3:
        return None
    w_pks_ms = np.array([w_gyro_rel[i] for i in w_pks_idx])

    p_pks_idx, _ = find_peaks(polar_acc_mags, height=12.0, distance=200)
    if len(p_pks_idx) < 3:
        p_pks_idx, _ = find_peaks(polar_acc_mags, height=8.0, distance=100)
    if len(p_pks_idx) < 3:
        return None
    p_pks_ms = np.array([polar_phone_times[i] - sys_start_ms for i in p_pks_idx])

    init_offset = float(polar_phone_times[0] - sys_start_ms)
    matches = []
    for w_t in w_pks_ms:
        exp_p = w_t + init_offset
        diffs = np.abs(p_pks_ms - exp_p)
        best_i = np.argmin(diffs)
        if diffs[best_i] < 3000.0:  # within 3s window
            matches.append((w_t, p_pks_ms[best_i]))

    if len(matches) < 3:
        return None
    w_m = np.array([m[0] for m in matches], dtype=float)
    p_m = np.array([m[1] for m in matches], dtype=float)

    n = len(w_m); sx = w_m.sum(); sy = p_m.sum(); sxy = (w_m * p_m).sum(); sx2 = (w_m ** 2).sum()
    denom = (n * sx2 - sx * sx)
    if abs(denom) < 1e-9:
        return None
    slope = (n * sxy - sx * sy) / denom
    intercept = (sy - slope * sx) / n
    pred = slope * w_m + intercept
    ss_res = float(((p_m - pred) ** 2).sum())
    ss_tot = float(((p_m - p_m.mean()) ** 2).sum())
    r2 = 1.0 - (ss_res / ss_tot) if ss_tot > 0 else 0.0

    if r2 < 0.90:
        return None
    return {
        'offsetMs': float(intercept),
        'driftRate': float(slope - 1.0),
        'method': 'impact_peak_regression',
        'n_anchors': n,
        'r_squared': float(r2),
        'confidence': 'high' if r2 >= 0.99 else 'medium',
        'anchor_pairs_ms': [[float(m[0]), float(m[1])] for m in matches[:10]],
    }

def align_polar_to_watch(watch_taps, polar_phone_times, polar_acc_mags, w_gyro_rel=None, w_gyro_mags=None, sys_start_ms=0):
    """Returns alignment dict with confidence metrics, or None."""
    if polar_phone_times is None or len(polar_phone_times) == 0:
        return None
    matches = []
    if watch_taps:
        for w_wall_ms, _ in watch_taps:
            polar_seq = find_polar_taps_near_anchor(polar_phone_times, polar_acc_mags, w_wall_ms)
            if polar_seq is not None:
                matches.append((w_wall_ms - sys_start_ms, polar_seq[-1] - sys_start_ms))
    if len(matches) >= 2:
        w = np.array([m[0] for m in matches], dtype=float)
        p = np.array([m[1] for m in matches], dtype=float)
        n = len(w); sx=w.sum(); sy=p.sum(); sxy=(w*p).sum(); sx2=(w**2).sum()
        denom = (n*sx2 - sx*sx)
        if abs(denom) > 1e-9:
            slope = (n*sxy - sx*sy) / denom
            intercept = (sy - slope*sx) / n
            pred = slope * w + intercept
            ss_res = float(((p - pred)**2).sum())
            ss_tot = float(((p - p.mean())**2).sum())
            r2 = 1.0 - (ss_res / ss_tot) if ss_tot > 0 else 0.0
            conf = 'high' if (n >= 3 and r2 >= 0.99) else ('medium' if n >= 2 else 'low')
            return {
                'offsetMs': float(intercept),
                'driftRate': float(slope - 1.0),
                'method': 'anchor_regression',
                'n_anchors': n,
                'r_squared': float(r2),
                'confidence': conf,
                'anchor_pairs_ms': [[float(m[0]), float(m[1])] for m in matches],
            }
    if len(matches) == 1:
        return {
            'offsetMs': float(matches[0][1] - matches[0][0]),
            'driftRate': 0.0,
            'method': 'anchor_single',
            'n_anchors': 1,
            'r_squared': None,
            'confidence': 'medium',
            'anchor_pairs_ms': [[float(m[0]), float(m[1])] for m in matches],
        }

    # Tier 3: Impact-Peak Cross-Correlation
    if w_gyro_rel is not None and w_gyro_mags is not None:
        impact_align = find_impact_peaks_alignment(w_gyro_rel, w_gyro_mags, polar_phone_times, polar_acc_mags, sys_start_ms)
        if impact_align is not None:
            return impact_align

    # Ultimate fallback if no anchors or peaks match
    return fallback_wall_clock_alignment(polar_phone_times, sys_start_ms)

def fallback_wall_clock_alignment(polar_phone_times, sys_start_ms):
    """Used when no usable anchors or impact peaks exist but polar data is present."""
    if polar_phone_times is None or len(polar_phone_times) == 0:
        return None
    polar_start = float(polar_phone_times[0])
    return {
        'offsetMs': polar_start - sys_start_ms,
        'driftRate': 0.0,
        'method': 'wall_clock_fallback',
        'n_anchors': 0,
        'r_squared': None,
        'confidence': 'low',
        'anchor_pairs_ms': [],
    }

def watch_to_polar_ms(alignment, watch_rel_ms, sys_start_ms):
    if alignment is None: return watch_rel_ms
    return int(watch_rel_ms * (1.0 + alignment['driftRate']) + alignment['offsetMs'] + sys_start_ms)

def polar_to_watch_ms(alignment, polar_phone_time, sys_start_ms):
    if alignment is None: return float(polar_phone_time - sys_start_ms)
    polar_rel_raw = float(polar_phone_time - sys_start_ms)
    return (polar_rel_raw - alignment['offsetMs']) / (1.0 + alignment['driftRate'])


# ---------- resampling helpers ----------
def forward_fill_to_grid(src_times_ms, src_values, grid_ms):
    """src_times_ms: sorted ascending relative ms. src_values: (N, C) array.
    grid_ms: target relative ms grid. Returns (grid_size, C) array."""
    src_times = np.asarray(src_times_ms, dtype=np.float64)
    src = np.asarray(src_values, dtype=np.float32)
    if src.ndim == 1: src = src[:, None]
    out = np.zeros((len(grid_ms), src.shape[1]), dtype=np.float32)
    if len(src_times) == 0: return out
    # idx of largest src_time <= grid
    idx = np.searchsorted(src_times, grid_ms, side='right') - 1
    valid = idx >= 0
    out_row_idxs = np.where(valid)[0]
    out[out_row_idxs] = src[idx[out_row_idxs]]
    # rows with no prior sample stay 0
    return out

def max_bucket_to_grid(src_times_ms, src_values, grid_ms):
    raise NotImplementedError("not used")

# ---------- main per-session builder ----------
def build_session(session_name, verbose=True):
    session_dir = os.path.join(BASE, session_name)
    if verbose: print(f"\n=== {session_name} ===")

    # ---- watch sensors ----
    w_acc  = load_watch_imu_bin(os.path.join(session_dir, "WatchAccelerometer.bin.gz"))
    w_gyro = load_watch_imu_bin(os.path.join(session_dir, "WatchGyroscope.bin.gz"))
    w_grav = load_watch_imu_bin(os.path.join(session_dir, "WatchGravity.bin.gz"))
    w_lin  = load_watch_imu_bin(os.path.join(session_dir, "WatchLinearAcceleration.bin.gz"))
    w_mag  = load_watch_imu_bin(os.path.join(session_dir, "WatchMagnetometer.bin.gz"))
    w_rot  = load_watch_rot_bin(os.path.join(session_dir, "WatchGameOrientation.bin.gz")) \
             or load_watch_rot_bin(os.path.join(session_dir, "WatchOrientation.bin.gz"))
    w_steps = load_watch_steps_bin(os.path.join(session_dir, "WatchSteps.bin.gz"))
    if w_acc is None or w_gyro is None or w_rot is None:
        print(f"  MISSING CORE WATCH SENSORS")
        return None
    if verbose:
        print(f"  watch: acc={len(w_acc)} gyro={len(w_gyro)} grav={len(w_grav or [])} "
              f"lin={len(w_lin or [])} mag={len(w_mag or [])} rot={len(w_rot)} steps={len(w_steps)}")

    # ---- polar sensors ----
    p_acc  = load_polar(session_dir, "PolarAccelerometer", is_gyro=False)
    p_gyro = load_polar(session_dir, "PolarGyroscope",     is_gyro=True)
    p_mag  = load_polar(session_dir, "PolarMagnetometer",  is_gyro=False)
    has_polar = (p_acc is not None and len(p_acc) > 0)
    if verbose: print(f"  polar: acc={len(p_acc or [])} gyro={len(p_gyro or [])} mag={len(p_mag or [])} has_polar={has_polar}")

    # ---- watch relative ms & gyro mags for alignment ----
    watch_start_ns = w_acc[0][0]
    sys_start, _ = parse_timeline(session_dir, watch_start_ns, 0)
    if sys_start is None:
        m = re.match(r"session[-_](\d{4})-(\d{2})-(\d{2})_(\d{2})[-_](\d{2})[-_](\d{2})", session_name)
        if m:
            from datetime import datetime
            y,mo,d,h,mi,s = map(int, m.groups())
            sys_start = int(datetime(y,mo,d,h,mi,s).timestamp() * 1000)
        else:
            sys_start = 0
    _, watch_taps = parse_timeline(session_dir, watch_start_ns, sys_start)
    watch_taps = filter_real_tap_sequences(watch_taps)

    w_gyro_rel = np.array([(s[0] - watch_start_ns) / 1e6 for s in w_gyro], dtype=np.float64)
    w_gyro_mags = np.array([np.sqrt(s[1]**2 + s[2]**2 + s[3]**2) for s in w_gyro], dtype=np.float32)

    alignment = None
    if has_polar:
        polar_phone_times = np.array([s[0] for s in p_acc], dtype=np.int64)
        polar_acc_mags = np.array([np.sqrt(s[2]**2 + s[3]**2 + s[4]**2) for s in p_acc])
        alignment = align_polar_to_watch(watch_taps, polar_phone_times.astype(np.float64), polar_acc_mags,
                                         w_gyro_rel=w_gyro_rel, w_gyro_mags=w_gyro_mags, sys_start_ms=sys_start)

    alignment_record = {
        'session': session_name,
        'has_polar': bool(has_polar),
        'watch_start_sensor_ns': int(watch_start_ns),
        'watch_start_wall_ms': int(sys_start),
        'n_tap_seqs_in_timeline': int(_count_tap_seqs(session_dir)),
        'n_filtered_tap_seqs': len(watch_taps),
        'alignment': alignment,
    }
    align_path = os.path.join(OUTPUT_DIR, f"{session_name}_sensor_alignment.json")
    with open(align_path, 'w') as f:
        json.dump(alignment_record, f, indent=2)
    if verbose:
        print(f"  alignment: method={alignment.get('method') if alignment else 'none'}  "
              f"confidence={alignment.get('confidence') if alignment else 'none'}  "
              f"n_anchors={alignment.get('n_anchors') if alignment else 'n/a'}  "
              f"r2={alignment.get('r_squared') if alignment else 'n/a'}")
        print(f"  saved {align_path}")

    # ---- enforce uniform 423Hz grid ----
    grid_hz = 423
    grid_dt_ms = 1000.0 / grid_hz
    if verbose: print(f"  grid_hz={grid_hz}  grid_dt_ms={grid_dt_ms:.3f}")

    # ---- build grid (relative ms) ----
    end_ms_watch = (w_acc[-1][0] - watch_start_ns) / 1e6
    end_ms = end_ms_watch
    if has_polar:
        p_acc_rel = np.array([polar_to_watch_ms(alignment, int(s[0]), sys_start) for s in p_acc], dtype=np.float64)
        end_ms_polar = p_acc_rel[-1] if len(p_acc_rel) > 0 else 0.0
        end_ms = max(end_ms, end_ms_polar)
    else:
        p_acc_rel = None

    n_rows = int(end_ms / grid_dt_ms) + 1
    if verbose: print(f"  session duration: {end_ms:.0f}ms  ->  {n_rows} rows at {grid_hz} Hz")
    grid_ms = np.arange(n_rows, dtype=np.float64) * grid_dt_ms

    # ---- project watch sensors to relative ms ----
    def to_watch_rel_ms(t_ns_list):
        return [(t - watch_start_ns) / 1e6 for t in t_ns_list]

    w_acc_rel = to_watch_rel_ms([s[0] for s in w_acc])
    w_grav_rel = to_watch_rel_ms([s[0] for s in w_grav]) if w_grav else []
    w_lin_rel  = to_watch_rel_ms([s[0] for s in w_lin]) if w_lin else []
    w_mag_rel  = to_watch_rel_ms([s[0] for s in w_mag]) if w_mag else []
    w_rot_rel  = to_watch_rel_ms([s[0] for s in w_rot])

    w_acc_arr = np.array([[s[1], s[2], s[3]] for s in w_acc], dtype=np.float32)
    w_gyro_arr = np.array([[s[1], s[2], s[3]] for s in w_gyro], dtype=np.float32)
    w_grav_arr = np.array([[s[1], s[2], s[3]] for s in w_grav], dtype=np.float32) if w_grav else None
    w_lin_arr  = np.array([[s[1], s[2], s[3]] for s in w_lin], dtype=np.float32) if w_lin else None
    w_mag_arr  = np.array([[s[1], s[2], s[3]] for s in w_mag], dtype=np.float32) if w_mag else None
    w_rot_arr  = np.array([[s[1], s[2], s[3], s[4]] for s in w_rot], dtype=np.float32)

    w_acc_grid  = forward_fill_to_grid(w_acc_rel,  w_acc_arr,  grid_ms)
    w_gyro_grid = forward_fill_to_grid(w_gyro_rel, w_gyro_arr, grid_ms)
    w_grav_grid = forward_fill_to_grid(w_grav_rel, w_grav_arr, grid_ms) if w_grav_arr is not None else np.zeros((n_rows, 3), np.float32)
    w_lin_grid  = forward_fill_to_grid(w_lin_rel,  w_lin_arr,  grid_ms) if w_lin_arr  is not None else np.zeros((n_rows, 3), np.float32)
    w_mag_grid  = forward_fill_to_grid(w_mag_rel,  w_mag_arr,  grid_ms) if w_mag_arr  is not None else np.zeros((n_rows, 3), np.float32)
    w_rot_grid  = forward_fill_to_grid(w_rot_rel,  w_rot_arr,  grid_ms)

    # ---- compute rotationally invariant world-frame vectors ----
    w_acc_world_grid  = rotate_vectors_quat(w_rot_grid, w_acc_grid)
    w_gyro_world_grid = rotate_vectors_quat(w_rot_grid, w_gyro_grid)


    # step events: project as cumulative count at each grid row
    step_rel_ms = [(t - watch_start_ns) / 1e6 for t in w_steps]
    step_cum = np.zeros(n_rows, dtype=np.int32)
    if step_rel_ms:
        step_idx = np.searchsorted(grid_ms, np.array(step_rel_ms))
        for idx in step_idx:
            if 0 <= idx < n_rows:
                step_cum[idx:] += 1

    # ---- polar streams ----
    if has_polar:
        p_acc_arr  = np.array([[s[2], s[3], s[4]] for s in p_acc],  dtype=np.float32)
        p_gyro_arr = np.array([[s[2], s[3], s[4]] for s in p_gyro], dtype=np.float32) if p_gyro else None
        p_mag_arr  = np.array([[s[2], s[3], s[4]] for s in p_mag],  dtype=np.float32) if p_mag else None

        if p_gyro is not None:
            p_gyro_rel = np.array([polar_to_watch_ms(alignment, int(s[0]), sys_start) for s in p_gyro], dtype=np.float64)
        else:
            p_gyro_rel = None

        if p_mag is not None:
            p_mag_rel = np.array([polar_to_watch_ms(alignment, int(s[0]), sys_start) for s in p_mag], dtype=np.float64)
        else:
            p_mag_rel = None

        p_acc_grid  = forward_fill_to_grid(p_acc_rel,  p_acc_arr,  grid_ms)
        p_gyro_grid = forward_fill_to_grid(p_gyro_rel, p_gyro_arr, grid_ms) if p_gyro_arr is not None else np.zeros((n_rows,3),np.float32)
        p_mag_grid  = forward_fill_to_grid(p_mag_rel,  p_mag_arr,  grid_ms) if p_mag_arr  is not None else np.zeros((n_rows,3),np.float32)
    else:
        p_acc_grid  = np.zeros((n_rows,3), np.float32)
        p_gyro_grid = np.zeros((n_rows,3), np.float32)
        p_mag_grid  = np.zeros((n_rows,3), np.float32)

    # ---- build DataFrame ----
    df = pd.DataFrame()
    df['t_ms'] = grid_ms
    df['session_id'] = session_name
    df['has_polar'] = int(has_polar)
    df['w_acc_x'] = w_acc_grid[:,0]; df['w_acc_y'] = w_acc_grid[:,1]; df['w_acc_z'] = w_acc_grid[:,2]
    df['w_gyro_x'] = w_gyro_grid[:,0]; df['w_gyro_y'] = w_gyro_grid[:,1]; df['w_gyro_z'] = w_gyro_grid[:,2]
    df['w_acc_world_x'] = w_acc_world_grid[:,0]; df['w_acc_world_y'] = w_acc_world_grid[:,1]; df['w_acc_world_z'] = w_acc_world_grid[:,2]
    df['w_gyro_world_x'] = w_gyro_world_grid[:,0]; df['w_gyro_world_y'] = w_gyro_world_grid[:,1]; df['w_gyro_world_z'] = w_gyro_world_grid[:,2]
    df['w_grav_x'] = w_grav_grid[:,0]; df['w_grav_y'] = w_grav_grid[:,1]; df['w_grav_z'] = w_grav_grid[:,2]
    df['w_lin_x'] = w_lin_grid[:,0]; df['w_lin_y'] = w_lin_grid[:,1]; df['w_lin_z'] = w_lin_grid[:,2]
    df['w_mag_x'] = w_mag_grid[:,0]; df['w_mag_y'] = w_mag_grid[:,1]; df['w_mag_z'] = w_mag_grid[:,2]
    df['w_rot_qx'] = w_rot_grid[:,0]; df['w_rot_qy'] = w_rot_grid[:,1]; df['w_rot_qz'] = w_rot_grid[:,2]; df['w_rot_qw'] = w_rot_grid[:,3]
    df['p_acc_x'] = p_acc_grid[:,0]; df['p_acc_y'] = p_acc_grid[:,1]; df['p_acc_z'] = p_acc_grid[:,2]
    df['p_gyro_x'] = p_gyro_grid[:,0]; df['p_gyro_y'] = p_gyro_grid[:,1]; df['p_gyro_z'] = p_gyro_grid[:,2]
    df['p_mag_x'] = p_mag_grid[:,0]; df['p_mag_y'] = p_mag_grid[:,1]; df['p_mag_z'] = p_mag_grid[:,2]
    df['step_cum'] = step_cum

    # ---- Derived Kinematic Channels ----
    w_gyro_mag = np.linalg.norm(w_gyro_grid, axis=1).astype(np.float32)
    w_acc_mag  = np.linalg.norm(w_acc_grid, axis=1).astype(np.float32)
    w_jerk_mag = np.concatenate([[0.0], np.abs(np.diff(w_gyro_mag))]).astype(np.float32)
    w_gyro_energy = (w_gyro_grid[:,0]**2 + w_gyro_grid[:,1]**2 + w_gyro_grid[:,2]**2).astype(np.float32)
    p_acc_mag  = np.linalg.norm(p_acc_grid, axis=1).astype(np.float32)
    p_gyro_mag = np.linalg.norm(p_gyro_grid, axis=1).astype(np.float32)

    df['w_gyro_mag'] = w_gyro_mag
    df['w_acc_mag']  = w_acc_mag
    df['w_jerk_mag'] = w_jerk_mag
    df['w_gyro_energy'] = w_gyro_energy
    df['p_acc_mag']  = p_acc_mag
    df['p_gyro_mag'] = p_gyro_mag

    # ---- Kinematic Features ----
    w_300ms = 127
    pre_max = pd.Series(w_acc_mag).rolling(window=w_300ms, min_periods=1).max().values
    post_max = pd.Series(w_acc_mag[::-1]).rolling(window=w_300ms, min_periods=1).max().values[::-1]
    df['post_impact_acc_ratio'] = (post_max / (pre_max + 1e-5)).astype(np.float32)

    w_150ms = 63
    dt = 1.0 / 423.0
    w_gyro_x = w_gyro_grid[:, 0]
    df['wrist_gyro_roll_delta'] = (pd.Series(w_gyro_x[::-1]).rolling(window=w_150ms, min_periods=1).sum().values[::-1] * dt).astype(np.float32)

    # ---- labels ----
    narr_path = os.path.join(session_dir, "narrations_raw.json")
    narr = json.load(open(narr_path))
    labels = np.array(['no_shot'] * n_rows, dtype=object)
    n_shots = 0
    for e in narr:
        if not is_real_shot(e.get('shot_type')): continue
        cls = normalise_shot_type(e.get('shot_type'))
        if cls is None: continue
        shot_t_ms = float(e['timestamp_seconds']) * 1000.0
        # shot window
        i_shot_lo = int((shot_t_ms - LABEL_SHOT_BEFORE_MS) / grid_dt_ms)
        i_shot_hi = int((shot_t_ms + LABEL_SHOT_AFTER_MS) / grid_dt_ms) + 1
        i_shot_lo = max(0, i_shot_lo); i_shot_hi = min(n_rows, i_shot_hi)
        # pre-shot window (don't overwrite an already-shot label - shot wins)
        i_pre_lo = int((shot_t_ms - LABEL_PRE_BEFORE_MS) / grid_dt_ms)
        i_pre_hi = int((shot_t_ms - LABEL_PRE_AFTER_MS) / grid_dt_ms) + 1
        i_pre_lo = max(0, i_pre_lo); i_pre_hi = min(n_rows, i_pre_hi)
        # Apply pre_shot only where label is currently no_shot
        mask_pre = labels[i_pre_lo:i_pre_hi] == 'no_shot'
        labels[i_pre_lo:i_pre_hi][mask_pre] = 'pre_shot'
        labels[i_shot_lo:i_shot_hi] = cls
        n_shots += 1
    df['label'] = labels
    if verbose: print(f"  labelled {n_shots} shots  -- label distribution:")
    if verbose:
        from collections import Counter
        print(f"  {Counter(labels)}")

    # ---- Strict Ground-Truth Guardrail: Truncate training dataset at max narration time + 10s ----
    if narr:
        valid_narr_times = [float(e['timestamp_seconds']) * 1000.0 for e in narr if 'timestamp_seconds' in e]
        if valid_narr_times:
            max_narr_ms = max(valid_narr_times) + 10000.0
            df = df[df['t_ms'] <= max_narr_ms].copy()
            if verbose: print(f"  🛡️ Ground Truth Guardrail: Truncated parquet dataset to max narration time ({max_narr_ms/1000.0:.1f}s / {len(df)} rows)")

    # ---- save parquet ----
    out_path = os.path.join(OUTPUT_DIR, f"{session_name}_unified.parquet")
    df.to_parquet(out_path, engine='pyarrow', compression='zstd')
    if verbose: print(f"  saved {out_path}  ({len(df)} rows, {df.shape[1]} cols, {os.path.getsize(out_path)/1024/1024:.1f} MB)")
    return out_path

def main():
    for s in SESSIONS:
        build_session(s)
    print("\nDONE")

if __name__ == "__main__":
    main()