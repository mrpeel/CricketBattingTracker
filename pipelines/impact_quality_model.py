#!/usr/bin/env python3
"""
Shared Impact Quality Feature Extractor & ONNX Runtime Scorer (Python <-> Kotlin Parity).

Defines the exact 1:1 feature math shared with Kotlin:
  - AudioImpactDecoder.kt (200 Hz envelope, blind Polar-to-Audio RANSAC, 24x31 log-mel, 18 acoustic scalars + snorm)
  - ImpactQualityRunner.kt (8x68 Polar [ax, ay, az, amag, gx, gy, gz, gmag] over [-60ms, +100ms], 14 Polar physics scalars)

Two self-contained ONNX models in app/src/main/assets/models/:
  1. impact_quality_multimodal.onnx : inputs [spec_2ch (B,2,24,31), polar_8ch (B,8,68), tab_multi (B,43)] -> logits (B,3)
  2. impact_quality_polar.onnx      : inputs [polar_8ch (B,8,68), tab_polar (B,14)] -> logits (B,3)
  Logits correspond to [clean_vs_poor_edge (good+okay), middled_excellent (good), edge_risk (edge)].
"""
import os
import json
import math
import datetime
import re
import subprocess
import numpy as np
from scipy.signal import find_peaks

MODEL_DIR = "/Users/neilkloot/Code/CricketBattingTracker/app/src/main/assets/models"
MULTIMODAL_ONNX_PATH = os.path.join(MODEL_DIR, "impact_quality_multimodal.onnx")
POLAR_ONNX_PATH = os.path.join(MODEL_DIR, "impact_quality_polar.onnx")
CONFIG_JSON_PATH = os.path.join(MODEL_DIR, "impact_quality_config.json")

SAMPLE_RATE = 16000
N_FFT = 256
HOP_LEN = 80
PATCH_SAMPLES = 2720  # [-35ms, +135ms] @ 16 kHz -> 31 frames
N_MELS = 24
POLAR_GRID_LEN = 68   # [-60ms, +100ms] @ ~419 Hz

POLAR_TAB_COLS = [
    "g_pre_pk", "g_drop", "wide_dip_pct", "post_gyro_retention", "pre_to_post_drop",
    "axial_y_pk", "axial_y_span", "axial_y_jerk", "axial_y_ratio", "axial_y_post_rattle",
    "plane_wobble_deg", "acc_peak_imp", "acc_vib_std", "acc_vib_norm",
]

AUDIO_NORM_COLS = [
    "spec_e_core", "spec_e_dec1", "spec_e_dec2", "spec_dec_drop", "aud_per_speed",
    "sp_core_lo", "sp_core_mid", "sp_core_up", "sp_core_hi",
    "sp_dec1_up", "sp_dec1_hi", "sp_hi_lo_core", "sp_hi_lo_dec1", "sp_dec_slope",
    "aud_crest", "aud_snr_db", "aud_pk_core", "aud_tail_core_ratio",
]

POLAR_NORM_COLS = [
    "g_drop", "wide_dip_pct", "axial_y_ratio", "acc_vib_norm",
]

ALL_SNORM_COLS = AUDIO_NORM_COLS + POLAR_NORM_COLS

# Kept strictly aligned with build_clean_tabular / Kotlin ImpactQualityRunner
MULTI_TAB_COLS = (
    POLAR_TAB_COLS
    + AUDIO_NORM_COLS
    + [f"{c}_snorm" for c in ALL_SNORM_COLS]
)  # 14 + 18 + 22 = 54? Wait: let's keep exact deterministic ordering:
# 14 polar + 18 audio raw + 22 snorm = 54 floats!


def build_mel_filterbank(sr=SAMPLE_RATE, n_fft=N_FFT, n_mels=N_MELS, fmin=80.0, fmax=7800.0):
    def hz2mel(f):
        return 2595.0 * np.log10(1.0 + f / 700.0)

    def mel2hz(m):
        return 700.0 * (10.0 ** (m / 2595.0) - 1.0)

    mels = np.linspace(hz2mel(fmin), hz2mel(fmax), n_mels + 2)
    hz = mel2hz(mels)
    bins = np.floor((n_fft + 1) * hz / sr).astype(int)
    fb = np.zeros((n_mels, n_fft // 2 + 1), dtype=np.float32)
    for m in range(1, n_mels + 1):
        f0, f1, f2 = int(bins[m - 1]), int(bins[m]), int(bins[m + 1])
        if f1 > f0:
            for k in range(f0, f1):
                fb[m - 1, k] = (k - f0) / float(f1 - f0)
        if f2 > f1:
            for k in range(f1, f2):
                fb[m - 1, k] = (f2 - k) / float(f2 - f1)
    return fb


MEL_FB_24 = build_mel_filterbank()
HANN_256 = np.hanning(N_FFT).astype(np.float32)


def extract_polar_patch_and_scalars(pt_a, p_acc, pt_g, p_gyro, t_c):
    """
    Extract (8, 68) Polar tensor and 14 scalar physics features around t_c (seconds).
    p_acc is in m/s^2, p_gyro is in rad/s. Returns (pol_mat, scalars_dict) or (None, None) if sparse.
    """
    grid_t = np.linspace(t_c - 0.060, t_c + 0.100, POLAR_GRID_LEN)
    in_a = (pt_a >= t_c - 0.085) & (pt_a <= t_c + 0.125)
    in_g = (pt_g >= t_c - 0.085) & (pt_g <= t_c + 0.125)
    if np.sum(in_a) < 16 or np.sum(in_g) < 16:
        return None, None

    pa_mag = np.linalg.norm(p_acc[in_a], axis=1)
    pg_mag = np.linalg.norm(p_gyro[in_g], axis=1)
    pol_mat = np.zeros((8, POLAR_GRID_LEN), dtype=np.float32)
    for ch in range(3):
        pol_mat[ch] = np.interp(grid_t, pt_a[in_a], p_acc[in_a, ch])
        pol_mat[4 + ch] = np.interp(grid_t, pt_g[in_g], p_gyro[in_g, ch])
    pol_mat[3] = np.interp(grid_t, pt_a[in_a], pa_mag)
    pol_mat[7] = np.interp(grid_t, pt_g[in_g], pg_mag)

    scalars = compute_polar_scalars_from_matrix(pol_mat)
    return pol_mat, scalars


def compute_polar_scalars_from_matrix(pol_mat):
    """Exact mirror of Kotlin ImpactQualityRunner.computePolarScalars(polMat)."""
    a_mag = pol_mat[3]
    gy = pol_mat[5]
    g_mag = pol_mat[7]

    g_pre_win = g_mag[0:21]      # [-60ms, -12ms]
    g_pre24_max = float(np.max(g_mag[0:25]))
    g_imp_min = float(np.min(g_mag[18:40]))
    g_pre_mean = float(np.mean(g_pre_win))
    g_post_mean = float(np.mean(g_mag[34:68]))
    g_pre_pk = float(np.max(g_pre_win))

    g_drop = (g_pre_mean - g_post_mean) / (g_pre_mean + 1e-6)
    wide_dip_pct = (g_pre24_max - g_imp_min) / (g_pre24_max + 1e-6)
    post_gyro_retention = float(np.mean(g_mag[34:55])) / (g_pre24_max + 1e-6)
    pre_to_post_drop = (float(np.mean(g_mag[4:21])) - float(np.mean(g_mag[34:60]))) / (float(np.mean(g_mag[4:21])) + 1e-6)

    gy_imp = gy[20:36]
    gy_post = gy[36:68]
    axial_y_pk = float(np.max(np.abs(gy_imp)))
    axial_y_span = float(np.max(gy_imp) - np.min(gy_imp))
    axial_y_jerk = float(np.max(np.abs(np.diff(gy_imp))))
    axial_y_ratio = axial_y_span / (g_pre_pk + 1e-6)
    axial_y_post_rattle = float(np.std(np.diff(gy_post)))

    # 3D Swing plane wobble in [-45ms, -5ms] -> indices 6:24
    gvec_pre = pol_mat[4:7, 6:24]
    gnorm = np.linalg.norm(gvec_pre, axis=0, keepdims=True) + 1e-6
    u_pre = gvec_pre / gnorm
    u_mean = np.mean(u_pre, axis=1, keepdims=True)
    u_mean = u_mean / (np.linalg.norm(u_mean) + 1e-6)
    dots = np.clip(np.sum(u_pre * u_mean, axis=0), -1.0, 1.0)
    plane_wobble_deg = float(np.mean(np.degrees(np.arccos(dots))))

    acc_peak_imp = float(np.max(a_mag[17:38]))
    acc_vib_std = float(np.std(a_mag[32:68]))
    acc_vib_norm = acc_vib_std / (g_pre_pk + 1e-6)

    return {
        "g_pre_pk": g_pre_pk,
        "g_drop": g_drop,
        "wide_dip_pct": wide_dip_pct,
        "post_gyro_retention": post_gyro_retention,
        "pre_to_post_drop": pre_to_post_drop,
        "axial_y_pk": axial_y_pk,
        "axial_y_span": axial_y_span,
        "axial_y_jerk": axial_y_jerk,
        "axial_y_ratio": axial_y_ratio,
        "axial_y_post_rattle": axial_y_post_rattle,
        "plane_wobble_deg": plane_wobble_deg,
        "acc_peak_imp": acc_peak_imp,
        "acc_vib_std": acc_vib_std,
        "acc_vib_norm": acc_vib_norm,
    }


def compute_log_mel_and_audio_scalars(seg_aud, bg_seg, g_pre_pk):
    """
    Given seg_aud (2720 samples covering [-35ms, +135ms] @ 16kHz) and bg_seg ([-250ms, -60ms]):
    Returns (spec (24, 31), scalars_dict).
    """
    frames = []
    for start in range(0, PATCH_SAMPLES - N_FFT + 1, HOP_LEN):
        w = seg_aud[start : start + N_FFT] * HANN_256
        pwr = (np.abs(np.fft.rfft(w)) ** 2).astype(np.float32) + 1e-12
        mel = np.log(np.dot(MEL_FB_24, pwr) + 1e-10)
        frames.append(mel)
    spec = np.stack(frames, axis=1).astype(np.float32)  # (24, 31)

    bg_rms = float(np.sqrt(np.mean(bg_seg ** 2))) + 1e-6 if len(bg_seg) > 0 else 1e-4
    # Patch offsets: i=0 is -35ms -> -5ms is sample 480, +35ms is 1120, +95ms is 2080
    core_w = seg_aud[480:1120]
    tail_w = seg_aud[1120:2080]
    aud_pk_core = float(np.max(np.abs(core_w)))
    aud_core_rms = float(np.sqrt(np.mean(core_w ** 2))) + 1e-6
    aud_tail_rms = float(np.sqrt(np.mean(tail_w ** 2))) + 1e-6
    aud_crest = aud_pk_core / aud_core_rms
    aud_snr_db = float(20.0 * np.log10((aud_pk_core + 1e-6) / bg_rms))
    aud_tail_core_ratio = aud_tail_rms / aud_core_rms

    spec_e_core = float(np.mean(spec[:, 5:12]))
    spec_e_dec1 = float(np.mean(spec[:, 12:19]))
    spec_e_dec2 = float(np.mean(spec[:, 19:31]))
    spec_dec_drop = spec_e_core - spec_e_dec2
    aud_per_speed = (spec_e_core + spec_e_dec1) - 2.0 * float(np.log(g_pre_pk + 1.0))

    sp_core_lo = float(np.mean(spec[0:6, 5:12]))
    sp_core_mid = float(np.mean(spec[6:12, 5:12]))
    sp_core_up = float(np.mean(spec[12:18, 5:12]))
    sp_core_hi = float(np.mean(spec[18:24, 5:12]))
    sp_dec1_up = float(np.mean(spec[12:18, 12:19]))
    sp_dec1_hi = float(np.mean(spec[18:24, 12:19]))
    sp_dec1_lo = float(np.mean(spec[0:6, 12:19]))
    sp_dec2_up = float(np.mean(spec[12:18, 19:31]))

    scalars = {
        "aud_bg_rms": bg_rms,
        "spec_e_core": spec_e_core,
        "spec_e_dec1": spec_e_dec1,
        "spec_e_dec2": spec_e_dec2,
        "spec_dec_drop": spec_dec_drop,
        "aud_per_speed": aud_per_speed,
        "sp_core_lo": sp_core_lo,
        "sp_core_mid": sp_core_mid,
        "sp_core_up": sp_core_up,
        "sp_core_hi": sp_core_hi,
        "sp_dec1_up": sp_dec1_up,
        "sp_dec1_hi": sp_dec1_hi,
        "sp_hi_lo_core": sp_core_hi - sp_core_lo,
        "sp_hi_lo_dec1": sp_dec1_hi - sp_dec1_lo,
        "sp_dec_slope": sp_core_up - sp_dec2_up,
        "aud_crest": aud_crest,
        "aud_snr_db": aud_snr_db,
        "aud_pk_core": aud_pk_core,
        "aud_tail_core_ratio": aud_tail_core_ratio,
    }
    return spec, scalars


def parse_audio_start_ms(m4a_path, session_dir=None):
    base = os.path.splitext(os.path.basename(m4a_path))[0]
    meta_path = os.path.join(os.path.dirname(m4a_path), base + ".meta.json")
    if os.path.exists(meta_path):
        try:
            with open(meta_path, "r") as f:
                v = json.load(f).get("start_wall_ms")
                if v:
                    return int(v)
        except Exception:
            pass
    m = re.search(r"narration_(\d{8})_(\d{6})\.m4a$", os.path.basename(m4a_path))
    if m:
        dt = datetime.datetime.strptime(m.group(1) + m.group(2), "%Y%m%d%H%M%S")
        return int(dt.timestamp() * 1000)
    return None


def decode_audio_16k(m4a_path):
    raw = subprocess.check_output(
        ["ffmpeg", "-v", "quiet", "-i", m4a_path, "-f", "f32le", "-ac", "1", "-ar", str(SAMPLE_RATE), "-"]
    )
    return np.frombuffer(raw, dtype=np.float32)


def blind_align_audio_to_polar(y, polar_contact_times, init_offset_s, search_r=25.0):
    """
    Blindly align audio track to Polar contact timestamps without requiring ground truth narration timestamps.
    Returns (slope, intercept, n_inliers, inlier_ratio, med_err_s) or None.
    """
    hop = int(SAMPLE_RATE * 0.005)
    n_b = len(y) // hop
    if n_b < 20 or len(polar_contact_times) < 3:
        return None
    env = np.max(np.abs(y[: n_b * hop]).reshape(n_b, hop), axis=1)
    env_t = (np.arange(n_b) + 0.5) * 0.005
    med_env = float(np.median(env)) + 1e-6
    pk_idx, _ = find_peaks(
        env,
        height=max(0.03, 3.5 * med_env),
        distance=40,
        prominence=max(0.02, 2.5 * med_env),
    )
    aud_pks_t = env_t[pk_idx]
    if len(aud_pks_t) < 3:
        return None

    shifts = []
    for tc in polar_contact_times:
        pred = tc + init_offset_s
        m = (aud_pks_t >= pred - search_r) & (aud_pks_t <= pred + search_r)
        for pt in aud_pks_t[m]:
            shifts.append(pt - tc)
    if not shifts:
        return None

    bins = np.arange(min(shifts) - 0.05, max(shifts) + 0.06, 0.025)
    if len(bins) < 3:
        return None
    hist, edges = np.histogram(shifts, bins=bins)
    top_bins = np.argsort(hist)[::-1][:6]

    best_model = None
    best_inl = -1
    best_err = 1e9
    for tb in top_bins:
        a = 1.0
        b = 0.5 * (edges[tb] + edges[tb + 1])
        for _ in range(5):
            xs, ys = [], []
            for tc in polar_contact_times:
                p = a * tc + b
                d = np.abs(aud_pks_t - p)
                j = int(np.argmin(d))
                if d[j] < 0.050:
                    xs.append(tc)
                    ys.append(aud_pks_t[j])
            if len(xs) >= 4:
                a_new, b_new = np.polyfit(xs, ys, 1)
                if abs(a_new - 1.0) < 0.02:
                    a, b = float(a_new), float(b_new)
        dists = np.array([np.min(np.abs(aud_pks_t - (a * tc + b))) for tc in polar_contact_times])
        inl = int(np.sum(dists <= 0.025))
        med_e = float(np.median(dists))
        if inl > best_inl or (inl == best_inl and med_e < best_err):
            best_inl = inl
            best_err = med_e
            best_model = (a, b, inl, float(inl) / len(polar_contact_times), med_e)
    return best_model


def map_probs_to_quality(p_clean, p_middled, p_edge):
    """
    Map [p_clean, p_middled, p_edge] probabilities -> (quality_tag, sweet_spot_label, score_0_100).
    Must stay identical between Python reprocess_sessions.py and Kotlin ImpactQualityRunner.kt!
    """
    raw_score = 100.0 * (0.55 * float(p_clean) + 0.45 * float(p_middled)) * (1.0 - 0.55 * float(p_edge))
    score = max(0.0, min(100.0, raw_score))

    if p_edge >= 0.56 and p_clean < 0.52:
        qual = "edge"
        sweet = "Edge"
    elif p_middled >= 0.52 and p_clean >= 0.56:
        qual = "good"
        sweet = "Excellent"
    elif p_clean >= 0.44:
        qual = "okay"
        sweet = "Good"
    else:
        qual = "poor"
        sweet = "Poor"
    return qual, sweet, score


def score_session_shots_onnx(
    shots_polar,
    audio_path=None,
    session_start_ms=None,
    gt_slope_intercept=None,
):
    """
    Score a list of shots for one session using self-contained ONNX impact models.
    shots_polar: list of dicts with keys:
      - t_c: float (seconds relative to session watch start, aligned to Polar shock peak)
      - pol_mat: np.ndarray (8, 68) or None
      - scalars: dict of 14 polar scalars or None
    Returns list of dicts per shot index:
      {impact_quality_score, impact_edge_risk, impact_quality_source,
       polar_contact_dip_pct, handle_rattle_rad_s, impact_aud_snr_db,
       predicted_quality, sweet_spot}
    """
    import onnxruntime as ort

    n = len(shots_polar)
    results = [None] * n
    if n == 0:
        return results

    valid_polar_idxs = [i for i, sp in enumerate(shots_polar) if sp is not None and sp.get("pol_mat") is not None]
    if not valid_polar_idxs:
        return results

    # Attempt audio decoding & alignment if audio_path exists and enough Polar contacts exist
    use_audio_model = False
    aud_y = None
    aud_a, aud_b = 1.0, 0.0
    if audio_path and os.path.exists(audio_path) and os.path.exists(MULTIMODAL_ONNX_PATH):
        try:
            aud_y = decode_audio_16k(audio_path)
            if gt_slope_intercept is not None:
                aud_a, aud_b = gt_slope_intercept
                use_audio_model = True
            elif session_start_ms is not None:
                aud_start_ms = parse_audio_start_ms(audio_path)
                if aud_start_ms is not None and len(valid_polar_idxs) >= 3:
                    init_off_s = (session_start_ms - aud_start_ms) / 1000.0
                    contact_ts = np.array([shots_polar[i]["t_c"] for i in valid_polar_idxs], dtype=np.float64)
                    al_res = blind_align_audio_to_polar(aud_y, contact_ts, init_off_s)
                    if al_res is not None:
                        aud_a, aud_b, inl, inl_ratio, med_e = al_res
                        if inl >= 3 and inl_ratio >= 0.45 and med_e <= 0.030:
                            use_audio_model = True
        except Exception:
            use_audio_model = False

    # Extract audio patches & scalars where available
    aud_patches = {}
    aud_scalars_map = {}
    if use_audio_model and aud_y is not None:
        bg_list = []
        for i in valid_polar_idxs:
            t_c = shots_polar[i]["t_c"]
            t_aud = aud_a * t_c + aud_b
            i0 = int(round((t_aud - 0.035) * SAMPLE_RATE))
            i1 = i0 + PATCH_SAMPLES
            if i0 >= 0 and i1 <= len(aud_y):
                seg = aud_y[i0:i1]
                bg0 = max(0, int(round((t_aud - 0.250) * SAMPLE_RATE)))
                bg1 = max(bg0 + 1, int(round((t_aud - 0.060) * SAMPLE_RATE)))
                bg_seg = aud_y[bg0:bg1]
                spec, asc = compute_log_mel_and_audio_scalars(seg, bg_seg, shots_polar[i]["scalars"]["g_pre_pk"])
                aud_patches[i] = spec
                aud_scalars_map[i] = asc
                bg_list.append(asc["aud_bg_rms"])
        # Open-mic gate: skip muted/gated audio (< 0.001 median bg rms) -> safely fall back to POLAR model
        if len(bg_list) < 3 or float(np.median(bg_list)) < 0.001:
            use_audio_model = False

    if use_audio_model and len(aud_patches) >= 3 and os.path.exists(MULTIMODAL_ONNX_PATH):
        # Compute session medians for spectrogram centering and scalar snorm
        valid_aud_idxs = [i for i in valid_polar_idxs if i in aud_patches]
        spec_stack = np.stack([aud_patches[i] for i in valid_aud_idxs], axis=0)
        spec_med = np.median(spec_stack, axis=0, keepdims=True)  # (1, 24, 31)

        combined_scalars = {}
        for i in valid_aud_idxs:
            d = dict(shots_polar[i]["scalars"])
            d.update(aud_scalars_map[i])
            combined_scalars[i] = d

        snorm_med, snorm_iqr = {}, {}
        for col in ALL_SNORM_COLS:
            vals = np.array([combined_scalars[i][col] for i in valid_aud_idxs], dtype=np.float64)
            med = float(np.median(vals))
            iqr = float(np.percentile(vals, 75) - np.percentile(vals, 25))
            if iqr <= 1e-6:
                iqr = float(np.std(vals)) + 1e-6
            snorm_med[col] = med
            snorm_iqr[col] = max(iqr, 1e-6)

        sess = ort.InferenceSession(MULTIMODAL_ONNX_PATH, providers=["CPUExecutionProvider"])
        spec_batch, pol_batch, tab_batch = [], [], []
        for i in valid_aud_idxs:
            sp = aud_patches[i]
            sp_c = sp - spec_med[0]
            spec_batch.append(np.stack([sp, sp_c], axis=0))
            pol_batch.append(shots_polar[i]["pol_mat"])
            row = combined_scalars[i]
            vec = [row[c] for c in POLAR_TAB_COLS] + [row[c] for c in AUDIO_NORM_COLS]
            vec += [(row[c] - snorm_med[c]) / (snorm_iqr[c] + 1e-6) for c in ALL_SNORM_COLS]
            tab_batch.append(vec)

        logits = sess.run(
            None,
            {
                "spec_2ch": np.asarray(spec_batch, dtype=np.float32),
                "polar_8ch": np.asarray(pol_batch, dtype=np.float32),
                "tab_multi": np.asarray(tab_batch, dtype=np.float32),
            },
        )[0]
        probs = 1.0 / (1.0 + np.exp(-logits))
        for k, i in enumerate(valid_aud_idxs):
            qual, sweet, score = map_probs_to_quality(probs[k, 0], probs[k, 1], probs[k, 2])
            sc = combined_scalars[i]
            results[i] = {
                "impact_quality_score": float(score),
                "impact_edge_risk": float(probs[k, 2]),
                "impact_quality_source": "MULTIMODAL",
                "polar_contact_dip_pct": float(sc["wide_dip_pct"] * 100.0),
                "handle_rattle_rad_s": float(sc["axial_y_post_rattle"]),
                "impact_aud_snr_db": float(sc["aud_snr_db"]),
                "predicted_quality": qual,
                "sweet_spot": sweet,
            }

    # Score any remaining shots that lack valid audio patches using Polar-only ONNX
    rem_idxs = [i for i in valid_polar_idxs if results[i] is None]
    if rem_idxs and os.path.exists(POLAR_ONNX_PATH):
        sess_p = ort.InferenceSession(POLAR_ONNX_PATH, providers=["CPUExecutionProvider"])
        pol_batch = np.asarray([shots_polar[i]["pol_mat"] for i in rem_idxs], dtype=np.float32)
        tab_batch = np.asarray(
            [[shots_polar[i]["scalars"][c] for c in POLAR_TAB_COLS] for i in rem_idxs],
            dtype=np.float32,
        )
        logits = sess_p.run(None, {"polar_8ch": pol_batch, "tab_polar": tab_batch})[0]
        probs = 1.0 / (1.0 + np.exp(-logits))
        for k, i in enumerate(rem_idxs):
            qual, sweet, score = map_probs_to_quality(probs[k, 0], probs[k, 1], probs[k, 2])
            sc = shots_polar[i]["scalars"]
            results[i] = {
                "impact_quality_score": float(score),
                "impact_edge_risk": float(probs[k, 2]),
                "impact_quality_source": "POLAR",
                "polar_contact_dip_pct": float(sc["wide_dip_pct"] * 100.0),
                "handle_rattle_rad_s": float(sc["axial_y_post_rattle"]),
                "impact_aud_snr_db": None,
                "predicted_quality": qual,
                "sweet_spot": sweet,
            }

    return results


def resolve_session_start_ms(session_dir):
    for cp in [os.path.join(session_dir, "session_config.json"), os.path.join(session_dir, "PolarSense", "session_config.json")]:
        if os.path.exists(cp):
            try:
                v = json.load(open(cp)).get("start_time_ms")
                if v:
                    return int(v)
            except Exception:
                pass
    tl = os.path.join(session_dir, "latest_timeline.txt")
    if os.path.exists(tl):
        try:
            with open(tl, "r") as f:
                for line in f:
                    if "SYSTEM_START:" in line:
                        m = re.search(r"Ts=(\d+)", line)
                        if m:
                            return int(m.group(1))
        except Exception:
            pass
    return None


def align_polar_piecewise_to_watch(session_dir, w_t_acc, w_m_acc, sys_start_ms=None):
    """
    Piecewise Polar-to-watch shock-peak alignment using PolarAccelerometer/Gyroscope .bin.gz.
    Returns (pt_a_corr, p_acc, pt_g_corr, p_gyro) in watch-relative seconds, or None.
    """
    from orientation_ahrs import load_polar_raw

    if sys_start_ms is None:
        sys_start_ms = resolve_session_start_ms(session_dir)
    p_ms_a, p_sns_a, p_acc = load_polar_raw(session_dir, is_gyro=False)
    p_ms_g, p_sns_g, p_gyro = load_polar_raw(session_dir, is_gyro=True)
    if p_acc is None or p_gyro is None or sys_start_ms is None or len(p_ms_a) < 50:
        return None

    def piecewise_t(p_ms, p_sns):
        p_t_raw = (p_ms - sys_start_ms) / 1000.0
        gaps = np.where((np.diff(p_ms) > 500) | (np.diff(p_sns) < 0) | (np.diff(p_sns) > 5e8))[0] + 1
        segs = np.split(np.arange(len(p_ms)), gaps)
        t_out = np.zeros(len(p_ms), dtype=np.float64)
        for seg in segs:
            if len(seg) < 10:
                t_out[seg] = p_t_raw[seg]
            else:
                s_sec = (p_sns[seg] - p_sns[seg[0]]) / 1e9
                sl, ic = np.polyfit(s_sec, p_t_raw[seg], 1)
                t_out[seg] = sl * s_sec + ic
        return t_out, segs

    pt_a, segs_a = piecewise_t(p_ms_a, p_sns_a)
    pt_g, _ = piecewise_t(p_ms_g, p_sns_g)
    pa_mag = np.linalg.norm(p_acc, axis=1)

    wp, _ = find_peaks(w_m_acc, height=30.0, distance=40)
    pp, _ = find_peaks(pa_mag, height=40.0, distance=150)
    if len(wp) < 3 or len(pp) < 3:
        return None

    dts_all = []
    for i in wp:
        tw = w_t_acc[i]
        m = (pt_a[pp] >= tw - 1.8) & (pt_a[pp] <= tw + 1.8)
        if np.any(m):
            cands = pt_a[pp][m]
            dts_all.append(cands[np.argmin(np.abs(cands - tw))] - tw)
    if len(dts_all) < 3:
        return None
    global_dt = float(np.median(dts_all))

    pt_a_corr = pt_a.copy()
    pt_g_corr = pt_g.copy()
    for seg in segs_a:
        t0, t1 = pt_a[seg[0]] - global_dt, pt_a[seg[-1]] - global_dt
        seg_dts = []
        for i in wp:
            tw = w_t_acc[i]
            if tw < t0 - 0.5 or tw > t1 + 0.5:
                continue
            m = (pt_a[seg] >= tw + global_dt - 0.25) & (pt_a[seg] <= tw + global_dt + 0.25)
            if np.any(m) and pa_mag[seg][m].max() > 40.0:
                tp = pt_a[seg][m][np.argmax(pa_mag[seg][m])]
                seg_dts.append(tp - tw)
        dt_use = float(np.median(seg_dts)) if len(seg_dts) >= 3 else global_dt
        pt_a_corr[seg] -= dt_use
        mg = (pt_g >= pt_a[seg[0]] - 0.5) & (pt_g <= pt_a[seg[-1]] + 0.5)
        pt_g_corr[mg] = pt_g[mg] - dt_use

    return pt_a_corr, p_acc, pt_g_corr, p_gyro


def score_session_directory_impact_quality(
    session_dir,
    shot_timestamps_s,
    shot_detached_flags=None,
    w_t_acc=None,
    w_m_acc=None,
    session_start_ms=None,
    gt_slope_intercept=None,
):
    """
    Convenience wrapper for pipelines/reprocess_sessions.py:
    Aligns Polar 423 Hz logs + optional narration_*.m4a audio and scores every active bat-handle shot.
    """
    import glob

    n = len(shot_timestamps_s)
    if n == 0:
        return [None] * n

    if session_start_ms is None:
        session_start_ms = resolve_session_start_ms(session_dir)

    pol_aligned = None
    if w_t_acc is not None and w_m_acc is not None and len(w_t_acc) > 10:
        pol_aligned = align_polar_piecewise_to_watch(session_dir, w_t_acc, w_m_acc, sys_start_ms=session_start_ms)
    if pol_aligned is None:
        return [None] * n

    pt_a, p_acc, pt_g, p_gyro = pol_aligned
    pa_mag = np.linalg.norm(p_acc, axis=1)

    shots_polar = []
    for idx, t_shot in enumerate(shot_timestamps_s):
        if shot_detached_flags is not None and shot_detached_flags[idx]:
            shots_polar.append(None)
            continue
        m_pk = (pt_a >= t_shot - 0.12) & (pt_a <= t_shot + 0.12)
        if np.any(m_pk):
            t_c = float(pt_a[m_pk][np.argmax(pa_mag[m_pk])])
        else:
            t_c = float(t_shot)
        pol_mat, scalars = extract_polar_patch_and_scalars(pt_a, p_acc, pt_g, p_gyro, t_c)
        if pol_mat is None:
            shots_polar.append(None)
        else:
            shots_polar.append({"t_c": t_c, "pol_mat": pol_mat, "scalars": scalars})

    audio_candidates = sorted(glob.glob(os.path.join(session_dir, "narration_*.m4a")))
    audio_path = audio_candidates[0] if audio_candidates else None

    return score_session_shots_onnx(
        shots_polar,
        audio_path=audio_path,
        session_start_ms=session_start_ms,
        gt_slope_intercept=gt_slope_intercept,
    )
