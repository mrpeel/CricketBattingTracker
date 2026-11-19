#!/usr/bin/env python3
"""
Train & Export Self-Contained ONNX Impact Quality Models:
  1. app/src/main/assets/models/impact_quality_multimodal.onnx  (Audio + Polar + Physics)
  2. app/src/main/assets/models/impact_quality_polar.onnx       (Polar + Physics fallback)
  3. app/src/main/assets/models/impact_quality_config.json      (Exact 24x129 Mel filterbank + metadata)

Uses 5-fold Session-Out GroupKFold CV for honest out-of-fold validation before exporting
the full 3-seed ensemble with standardization buffers baked directly into the ONNX graphs.
"""
import os
import glob
import json
import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import torch
torch.set_num_threads(4)
import torch.nn as nn
import onnx
import onnxruntime as ort
from sklearn.model_selection import GroupKFold
from sklearn.metrics import roc_auc_score, average_precision_score

import sys
sys.path.append("/Users/neilkloot/Code/CricketBattingTracker/pipelines")
sys.path.append("/Users/neilkloot/.gemini/antigravity/brain/766dfdb4-468c-4bff-be59-4abcdec7eef1/scratch")
from build_unified_dataset import load_watch_imu_bin
from explore_acoustics_quality import get_sys_start_ms, align_polar_piecewise, align_audio_to_contacts
from deep_dive_acoustics import matched_concordance
from impact_quality_model import (
    MODEL_DIR,
    MULTIMODAL_ONNX_PATH,
    POLAR_ONNX_PATH,
    CONFIG_JSON_PATH,
    SAMPLE_RATE,
    PATCH_SAMPLES,
    POLAR_TAB_COLS,
    AUDIO_NORM_COLS,
    ALL_SNORM_COLS,
    MULTI_TAB_COLS,
    MEL_FB_24,
    extract_polar_patch_and_scalars,
    compute_log_mel_and_audio_scalars,
    decode_audio_16k,
)

SESSIONS_DIR = "/Users/neilkloot/Code/Batting Sensor Stats/live_watch_sessions"
CACHE_PATH = "/Users/neilkloot/.gemini/antigravity/brain/766dfdb4-468c-4bff-be59-4abcdec7eef1/scratch/train_impact_exact_cache.npz"
META_CACHE_PATH = "/Users/neilkloot/.gemini/antigravity/brain/766dfdb4-468c-4bff-be59-4abcdec7eef1/scratch/train_impact_exact_meta.parquet"


def build_exact_dataset(force_rebuild=False):
    if not force_rebuild and os.path.exists(CACHE_PATH) and os.path.exists(META_CACHE_PATH):
        d = np.load(CACHE_PATH)
        mdf = pd.read_parquet(META_CACHE_PATH)
        print(f"Loaded exact feature cache: {len(mdf)} shots across {mdf['session_id'].nunique()} sessions.")
        return d["specs"], d["polars"], mdf

    session_dirs = sorted(glob.glob(os.path.join(SESSIONS_DIR, "session_*")))
    specs, polars, meta_rows = [], [], []

    for sdir in session_dirs:
        sid = os.path.basename(sdir)
        cfg_file = os.path.join(sdir, "session_config.json")
        if not os.path.exists(cfg_file):
            cfg_file = os.path.join(sdir, "PolarSense", "session_config.json")
        mount = "WRIST"
        if os.path.exists(cfg_file):
            try:
                mount = str(json.load(open(cfg_file)).get("polar_mount_mode", "WRIST")).upper()
            except Exception:
                pass
        if mount != "BAT_HANDLE":
            continue

        gt_csv = os.path.join(sdir, "ground_truth_aligned.csv")
        audios = sorted(glob.glob(os.path.join(sdir, "narration_*.m4a")))
        w_acc_f = os.path.join(sdir, "WatchAccelerometer.bin.gz")
        if not (os.path.exists(gt_csv) and audios and os.path.exists(w_acc_f)):
            continue

        df = pd.read_csv(gt_csv)
        valid = df[["audio_time_seconds", "sensor_narr_time_seconds"]].dropna()
        if len(valid) < 5:
            continue
        slope0, intercept0 = np.polyfit(valid["audio_time_seconds"], valid["sensor_narr_time_seconds"], 1)

        w_acc = load_watch_imu_bin(w_acc_f)
        if not w_acc:
            continue
        w0 = w_acc[0][0]
        w_t_acc = np.array([(x[0] - w0) / 1e9 for x in w_acc])
        w_m_acc = np.linalg.norm(np.array([[x[1], x[2], x[3]] for x in w_acc]), axis=1)

        pol = align_polar_piecewise(sdir, w_t_acc, w_m_acc)
        if pol is None:
            continue
        pt_a, p_acc, pt_g, p_gyro = pol
        pa_mag = np.linalg.norm(p_acc, axis=1)

        swings = df[
            (~df["shot_type"].astype(str).str.lower().str.contains("no shot|leave|facing up|evade", na=False))
            & (~df["is_fallback"].astype(bool))
        ].copy()
        if len(swings) < 5:
            continue

        y_aud = decode_audio_16k(audios[0])
        records, contact_times = [], []
        for _, row in swings.iterrows():
            t_w = float(row["impact_time_seconds"])
            mw = (w_t_acc >= t_w - 0.15) & (w_t_acc <= t_w + 0.15)
            tw_acc = float(w_t_acc[mw][np.argmax(w_m_acc[mw])]) if np.any(mw) else t_w
            mp = (pt_a >= tw_acc - 0.12) & (pt_a <= tw_acc + 0.12)
            if np.any(mp) and (pt_a[mp][-1] - pt_a[mp][0] > 0.05) and pa_mag[mp].max() >= 35.0:
                t_c = float(pt_a[mp][np.argmax(pa_mag[mp])])
            else:
                t_c = tw_acc
            contact_times.append(t_c)
            records.append((row, t_c))

        contact_times = np.array(contact_times)
        hit_mask = np.array([str(r[0]["quality"]).lower() != "miss" for r in records])
        if np.sum(hit_mask) < 5:
            continue

        res = align_audio_to_contacts(
            y_aud, SAMPLE_RATE, contact_times[hit_mask],
            swings["audio_time_seconds"].to_numpy()[hit_mask],
            slope0, intercept0,
        )
        if res is None or res[0] is None:
            continue
        a, b, dists = res[0]
        med_err_ms = float(np.median(dists) * 1000.0)
        in30_pct = float(np.mean(dists <= 0.030) * 100.0)
        if med_err_ms > 20.0 or in30_pct < 60.0:
            print(f"Skipping poorly aligned audio session {sid} (med={med_err_ms:.1f}ms, in30={in30_pct:.1f}%)")
            continue

        sess_rows = []
        sess_specs, sess_pols = [], []
        for row, t_c in records:
            pol_mat, pol_sc = extract_polar_patch_and_scalars(pt_a, p_acc, pt_g, p_gyro, t_c)
            if pol_mat is None:
                continue
            t_aud = a * t_c + b
            i0 = int(round((t_aud - 0.035) * SAMPLE_RATE))
            i1 = i0 + PATCH_SAMPLES
            if i0 < 0 or i1 > len(y_aud):
                continue
            seg_aud = y_aud[i0:i1]
            bg0 = max(0, int(round((t_aud - 0.250) * SAMPLE_RATE)))
            bg1 = max(bg0 + 1, int(round((t_aud - 0.060) * SAMPLE_RATE)))
            spec, aud_sc = compute_log_mel_and_audio_scalars(seg_aud, y_aud[bg0:bg1], pol_sc["g_pre_pk"])

            meta = {
                "session_id": sid,
                "shot_index": int(row["shot_index"]),
                "quality": str(row["quality"]).lower().strip(),
                "bat_name": str(row.get("bat_name", "UNKNOWN")),
                "shot_type": str(row["shot_type"]),
            }
            meta.update(pol_sc)
            meta.update(aud_sc)
            sess_rows.append(meta)
            sess_specs.append(spec)
            sess_pols.append(pol_mat)

        if sess_rows:
            # Compute exact 1:1 session snorm matching Kotlin & inference
            sdf = pd.DataFrame(sess_rows)
            for col in ALL_SNORM_COLS:
                vals = sdf[col].to_numpy(dtype=np.float64)
                med = float(np.median(vals))
                iqr = float(np.percentile(vals, 75) - np.percentile(vals, 25))
                if iqr <= 1e-6:
                    iqr = float(np.std(vals)) + 1e-6
                sdf[f"{col}_snorm"] = (vals - med) / (max(iqr, 1e-6) + 1e-6)
            meta_rows.extend(sdf.to_dict("records"))
            specs.extend(sess_specs)
            polars.extend(sess_pols)

    specs = np.stack(specs, axis=0).astype(np.float32)
    polars = np.stack(polars, axis=0).astype(np.float32)
    mdf = pd.DataFrame(meta_rows)
    np.savez_compressed(CACHE_PATH, specs=specs, polars=polars)
    mdf.to_parquet(META_CACHE_PATH, index=False)
    print(f"Built exact dataset cache: {len(mdf)} shots across {mdf['session_id'].nunique()} sessions.")
    return specs, polars, mdf


class ImpactBranchNet(nn.Module):
    def __init__(self, n_tab, use_audio=True):
        super().__init__()
        self.use_audio = use_audio
        if use_audio:
            self.aud_net = nn.Sequential(
                nn.Conv2d(2, 16, kernel_size=3, padding=1),
                nn.BatchNorm2d(16),
                nn.GELU(),
                nn.MaxPool2d(2),
                nn.Conv2d(16, 32, kernel_size=3, padding=1),
                nn.BatchNorm2d(32),
                nn.GELU(),
                nn.MaxPool2d(2),
                nn.Conv2d(32, 48, kernel_size=3, padding=1),
                nn.BatchNorm2d(48),
                nn.GELU(),
                nn.AvgPool2d(kernel_size=(3, 4), stride=(3, 3)),
                nn.Flatten(),
            )
        self.pol_net = nn.Sequential(
            nn.Conv1d(8, 24, kernel_size=5, padding=2),
            nn.BatchNorm1d(24),
            nn.GELU(),
            nn.MaxPool1d(2),
            nn.Conv1d(24, 48, kernel_size=5, padding=2),
            nn.BatchNorm1d(48),
            nn.GELU(),
            nn.MaxPool1d(2),
            nn.Conv1d(48, 48, kernel_size=3, padding=1),
            nn.BatchNorm1d(48),
            nn.GELU(),
            nn.AvgPool1d(kernel_size=5, stride=4),
            nn.Flatten(),
        )
        self.tab_net = nn.Sequential(
            nn.Linear(n_tab, 64),
            nn.LayerNorm(64),
            nn.GELU(),
            nn.Dropout(0.25),
            nn.Linear(64, 48),
            nn.GELU(),
        )
        in_dim = (48 * 4 if use_audio else 0) + 48 * 4 + 48
        self.head = nn.Sequential(
            nn.Dropout(0.30),
            nn.Linear(in_dim, 64),
            nn.GELU(),
            nn.Dropout(0.20),
            nn.Linear(64, 3),  # [clean_vs_pe, good_vs_rest, edge_vs_rest]
        )

    def forward(self, polar_norm, tab_norm, spec_norm=None):
        zp = self.pol_net(polar_norm)
        zt = self.tab_net(tab_norm)
        if self.use_audio:
            za = self.aud_net(spec_norm)
            h = torch.cat([za, zp, zt], dim=1)
        else:
            h = torch.cat([zp, zt], dim=1)
        return self.head(h)


class ExportableEnsembleWrapper(nn.Module):
    """Wraps normalization stats + N trained seeds cleanly into one self-contained ONNX module."""
    def __init__(self, models, p_mu, p_sd, t_med, t_mu, t_sd, sp_mu=None, sp_sd=None, use_audio=True):
        super().__init__()
        self.use_audio = use_audio
        self.models = nn.ModuleList(models)
        self.register_buffer("p_mu", torch.tensor(p_mu, dtype=torch.float32))
        self.register_buffer("p_sd", torch.tensor(p_sd, dtype=torch.float32))
        self.register_buffer("t_med", torch.tensor(t_med, dtype=torch.float32))
        self.register_buffer("t_mu", torch.tensor(t_mu, dtype=torch.float32))
        self.register_buffer("t_sd", torch.tensor(t_sd, dtype=torch.float32))
        if use_audio:
            self.register_buffer("sp_mu", torch.tensor(sp_mu, dtype=torch.float32))
            self.register_buffer("sp_sd", torch.tensor(sp_sd, dtype=torch.float32))

    def forward(self, *args):
        if self.use_audio:
            spec_raw, polar_raw, tab_raw = args
            sp_n = (spec_raw - self.sp_mu) / self.sp_sd
        else:
            polar_raw, tab_raw = args
            sp_n = None
        pol_n = (polar_raw - self.p_mu) / self.p_sd
        tab_clean = torch.where(torch.isnan(tab_raw), self.t_med, tab_raw)
        tab_n = (tab_clean - self.t_mu) / self.t_sd
        out = 0.0
        for m in self.models:
            out = out + m(pol_n, tab_n, sp_n)
        return out / float(len(self.models))


def fit_ensemble(spec_2ch, polars, tab, Y, use_audio=True, seeds=(42, 43, 44), epochs=34):
    p_mu = polars.mean(axis=(0, 2), keepdims=True)
    p_sd = polars.std(axis=(0, 2), keepdims=True) + 1e-6
    Xp = torch.tensor((polars - p_mu) / p_sd, dtype=torch.float32)

    t_med = np.nanmedian(tab, axis=0, keepdims=True)
    t_fill = np.where(np.isnan(tab), t_med, tab)
    t_mu = t_fill.mean(axis=0, keepdims=True)
    t_sd = t_fill.std(axis=0, keepdims=True) + 1e-6
    Xt = torch.tensor((t_fill - t_mu) / t_sd, dtype=torch.float32)

    if use_audio:
        sp_mu = spec_2ch.mean(axis=(0, 2, 3), keepdims=True)
        sp_sd = spec_2ch.std(axis=(0, 2, 3), keepdims=True) + 1e-6
        Xs = torch.tensor((spec_2ch - sp_mu) / sp_sd, dtype=torch.float32)
    else:
        sp_mu = sp_sd = Xs = None

    Yt = torch.tensor(Y, dtype=torch.float32)
    pw = [(len(Y) - Y[:, j].sum()) / (Y[:, j].sum() + 1e-6) for j in range(3)]
    crit = nn.BCEWithLogitsLoss(pos_weight=torch.tensor(pw, dtype=torch.float32))

    models = []
    bs = 128
    n = len(Y)
    for seed in seeds:
        torch.manual_seed(seed)
        net = ImpactBranchNet(n_tab=tab.shape[1], use_audio=use_audio)
        opt = torch.optim.AdamW(net.parameters(), lr=2.5e-3, weight_decay=2e-2)
        sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=epochs)
        net.train()
        for _ in range(epochs):
            perm = torch.randperm(n)
            for i in range(0, n, bs):
                idx = perm[i : i + bs]
                pb = Xp[idx] + 0.04 * torch.randn_like(Xp[idx])
                tb = Xt[idx] + 0.03 * torch.randn_like(Xt[idx])
                sb = (Xs[idx] + 0.06 * torch.randn_like(Xs[idx])) if use_audio else None
                opt.zero_grad()
                loss = crit(net(pb, tb, sb), Yt[idx])
                loss.backward()
                opt.step()
            sched.step()
        net.eval()
        models.append(net)

    return ExportableEnsembleWrapper(models, p_mu, p_sd, t_med, t_mu, t_sd, sp_mu, sp_sd, use_audio=use_audio).eval()


def run_cv_and_export(specs, polars, mdf):
    os.makedirs(MODEL_DIR, exist_ok=True)
    sess_bg = mdf[mdf["quality"] != "miss"].groupby("session_id")["aud_bg_rms"].median()
    open_mic_sids = set(sess_bg[sess_bg >= 0.001].index)

    active_mask = mdf["quality"].isin(["good", "okay", "poor", "edge"]).to_numpy()
    open_mask = active_mask & mdf["session_id"].isin(open_mic_sids).to_numpy()

    # Build session-centered 2ch spectrogram for all shots
    spec_cent = np.zeros_like(specs)
    for sid, idxs in mdf.groupby("session_id").groups.items():
        idx_arr = np.array(list(idxs))
        med = np.median(specs[idx_arr], axis=0, keepdims=True)
        spec_cent[idx_arr] = specs[idx_arr] - med
    spec_2ch = np.stack([specs, spec_cent], axis=1)

    for tag, mask, tab_cols, use_audio, onnx_out in [
        ("POLAR-ONLY (all 34 BAT_HANDLE)", active_mask, POLAR_TAB_COLS, False, POLAR_ONNX_PATH),
        ("MULTIMODAL (29 Open-Mic)", open_mask, MULTI_TAB_COLS, True, MULTIMODAL_ONNX_PATH),
    ]:
        sub_idx = np.where(mask)[0]
        q = mdf.loc[sub_idx, "quality"].to_numpy()
        groups = mdf.loc[sub_idx, "session_id"].to_numpy()
        Y = np.stack([
            np.isin(q, ["good", "okay"]).astype(np.float32),
            (q == "good").astype(np.float32),
            (q == "edge").astype(np.float32),
        ], axis=1)

        s_sub = spec_2ch[sub_idx]
        p_sub = polars[sub_idx]
        t_sub = mdf.loc[sub_idx, tab_cols].to_numpy(dtype=np.float32)

        gkf = GroupKFold(n_splits=5)
        oof_probs = np.zeros((len(sub_idx), 3), dtype=np.float32)
        for tr, va in gkf.split(sub_idx, Y[:, 0], groups):
            wrapper = fit_ensemble(
                s_sub[tr] if use_audio else None, p_sub[tr], t_sub[tr], Y[tr],
                use_audio=use_audio, seeds=(42, 43, 44), epochs=34,
            )
            with torch.no_grad():
                if use_audio:
                    logits = wrapper(torch.tensor(s_sub[va]), torch.tensor(p_sub[va]), torch.tensor(t_sub[va]))
                else:
                    logits = wrapper(torch.tensor(p_sub[va]), torch.tensor(t_sub[va]))
                oof_probs[va] = torch.sigmoid(logits).numpy()

        sub_meta = mdf.loc[sub_idx].reset_index(drop=True)
        m_gp = np.isin(q, ["good", "poor", "edge"])
        auc_gp = roc_auc_score((q[m_gp] == "good").astype(int), oof_probs[m_gp, 1])
        mc_gp, np_gp = matched_concordance(sub_meta, oof_probs[:, 1], "good", ("poor", "edge"))

        m_cl = np.isin(q, ["good", "okay", "poor", "edge"])
        auc_cl = roc_auc_score(np.isin(q[m_cl], ["good", "okay"]).astype(int), oof_probs[m_cl, 0])
        meta_cl = sub_meta.copy()
        meta_cl["quality"] = np.where(meta_cl["quality"].isin(["good", "okay"]), "clean", meta_cl["quality"])
        mc_cl, np_cl = matched_concordance(meta_cl, oof_probs[:, 0], "clean", ("poor", "edge"))

        m_ed = np.isin(q, ["good", "okay", "edge"])
        auc_ed = roc_auc_score((q[m_ed] == "edge").astype(int), oof_probs[m_ed, 2])
        ap_ed = average_precision_score((q[m_ed] == "edge").astype(int), oof_probs[m_ed, 2])

        # Monotonicity across quality tiers
        score_100 = 100.0 * (0.55 * oof_probs[:, 0] + 0.45 * oof_probs[:, 1]) * (1.0 - 0.55 * oof_probs[:, 2])
        tier_means = {qt: float(np.mean(score_100[q == qt])) for qt in ["good", "okay", "poor", "edge"]}

        print(f"\n=== 5-Fold Session-Out OOF: {tag} (n={len(sub_idx)}) ===")
        print(f"  Good vs Poor/Edge   : AUC={auc_gp:.3f} | Matched={mc_gp:.3f} ({np_gp} pairs)")
        print(f"  Clean vs Poor/Edge  : AUC={auc_cl:.3f} | Matched={mc_cl:.3f} ({np_cl} pairs)")
        print(f"  Edge vs Good/Okay   : AUC={auc_ed:.3f} | AP={ap_ed:.3f}")
        print(f"  Mean Score (0..100) : good={tier_means['good']:.1f} > okay={tier_means['okay']:.1f} > poor={tier_means['poor']:.1f} > edge={tier_means['edge']:.1f}")

        # Train final production ensemble on 100% of subset and export ONNX
        full_wrapper = fit_ensemble(
            s_sub if use_audio else None, p_sub, t_sub, Y,
            use_audio=use_audio, seeds=(42, 43, 44), epochs=34,
        )
        full_wrapper.eval()

        if use_audio:
            dummy = (
                torch.randn(1, 2, 24, 31),
                torch.randn(1, 8, 68),
                torch.randn(1, len(tab_cols)),
            )
            in_names = ["spec_2ch", "polar_8ch", "tab_multi"]
            dyn_axes = {"spec_2ch": {0: "batch"}, "polar_8ch": {0: "batch"}, "tab_multi": {0: "batch"}, "logits": {0: "batch"}}
        else:
            dummy = (
                torch.randn(1, 8, 68),
                torch.randn(1, len(tab_cols)),
            )
            in_names = ["polar_8ch", "tab_polar"]
            dyn_axes = {"polar_8ch": {0: "batch"}, "tab_polar": {0: "batch"}, "logits": {0: "batch"}}

        # Export cleanly with dynamo=False and save self-contained single protobuf file
        torch.onnx.export(
            full_wrapper,
            dummy,
            onnx_out,
            input_names=in_names,
            output_names=["logits"],
            dynamic_axes=dyn_axes,
            opset_version=17,
            do_constant_folding=True,
            dynamo=False,
        )
        # Ensure zero external data files
        data_sidecar = onnx_out + ".data"
        if os.path.exists(data_sidecar):
            model_proto = onnx.load(onnx_out, load_external_data=True)
            onnx.save_model(model_proto, onnx_out, save_as_external_data=False)
            os.remove(data_sidecar)

        # Verify PyTorch <-> ONNXRuntime exact parity
        with torch.no_grad():
            if use_audio:
                pt_out = full_wrapper(torch.tensor(s_sub[:8]), torch.tensor(p_sub[:8]), torch.tensor(t_sub[:8])).numpy()
                feed = {"spec_2ch": s_sub[:8], "polar_8ch": p_sub[:8], "tab_multi": t_sub[:8]}
            else:
                pt_out = full_wrapper(torch.tensor(p_sub[:8]), torch.tensor(t_sub[:8])).numpy()
                feed = {"polar_8ch": p_sub[:8], "tab_polar": t_sub[:8]}
        ort_sess = ort.InferenceSession(onnx_out, providers=["CPUExecutionProvider"])
        ort_out = ort_sess.run(None, feed)[0]
        max_diff = float(np.max(np.abs(pt_out - ort_out)))
        sz_kb = os.path.getsize(onnx_out) / 1024.0
        print(f"  Exported {os.path.basename(onnx_out)} ({sz_kb:.1f} KB, self-contained={not os.path.exists(data_sidecar)}, PT<->ORT max diff={max_diff:.2e})")

    # Save exact 24x129 Mel filterbank and config JSON for Kotlin parity
    cfg = {
        "sample_rate": SAMPLE_RATE,
        "n_fft": 256,
        "hop_len": 80,
        "patch_samples": PATCH_SAMPLES,
        "n_mels": 24,
        "polar_grid_len": 68,
        "open_mic_bg_rms_min": 0.001,
        "polar_tab_cols": POLAR_TAB_COLS,
        "audio_norm_cols": AUDIO_NORM_COLS,
        "all_snorm_cols": ALL_SNORM_COLS,
        "multi_tab_cols": MULTI_TAB_COLS,
        "mel_filterbank_24x129": MEL_FB_24.tolist(),
    }
    with open(CONFIG_JSON_PATH, "w") as f:
        json.dump(cfg, f)
    print(f"\nSaved config & Mel filterbank to {CONFIG_JSON_PATH} ({os.path.getsize(CONFIG_JSON_PATH)/1024:.1f} KB)")


if __name__ == "__main__":
    specs, polars, mdf = build_exact_dataset()
    run_cv_and_export(specs, polars, mdf)
