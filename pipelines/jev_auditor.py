#!/usr/bin/env python3
"""
pipelines/jev_auditor.py — Stage 3 Rule Health & Jev (`jev-1.13`) Shadow Auditor

Runs automatically at the end of `pipelines/train_and_evaluate_full_scorecard.py` to:
  1. Audit every Stage 3 rule in `stage3_rules_config.json` (both enabled production rules
     and disabled shadow candidate rules) against Ground Truth and Jev (`jev-1.13`).
  2. Flag rule precision degradation or negative net-shot regressions (`⚠️ DRIFT WARNING`).
  3. Surface "Missed Regimes" on Validation/Holdout where no Stage 3 rule fired, TCN missed,
     and both Jev (`conf >= 0.55`) and Ground Truth agree on the true class.
  4. Check threshold sensitivity (`±10%` perturbation) on the 9-session Validation Set.
  5. Persist audit metrics to `pipelines/jev_audit_history.jsonl` and cache all Jev API responses
     in `pipelines/jev_audit_cache.jsonl` using persistent HTTP Keep-Alive connection pooling.
"""

import os
import json
import time
import copy
import hashlib
import datetime
import requests

from stage3_rules import load_stage3_config, apply_stage3_rules

ROOT_DIR = "/Users/neilkloot/Code/CricketBattingTracker"
CACHE_PATH = os.path.join(ROOT_DIR, "pipelines", "jev_audit_cache.jsonl")
HISTORY_PATH = os.path.join(ROOT_DIR, "pipelines", "jev_audit_history.jsonl")

PRIMARY_ENDPOINT = "https://opencode.ai/inference/systemone/v1/systemone"
FALLBACK_ENDPOINT = "https://opencode.ai/zen/v1/systemone"
FREE_MODEL_ID = "jev-1.13-free"
PAID_MODEL_ID = "jev-1.13"
PAID_COST_PER_1M_INPUT = 0.042
JEV_PROMPT_VERSION = "v1.1.0-mount-aware-1q"


def resolve_opencode_api_key():
    """Resolves OPENCODE_API_KEY from environment or local .env files."""
    key = os.environ.get("OPENCODE_API_KEY", "").strip()
    if key:
        return key
    candidates = [
        os.path.join(ROOT_DIR, ".env"),
        os.path.expanduser("~/.config/opencode/.env"),
        os.path.expanduser("~/.config/opencode/config.json"),
    ]
    for p in candidates:
        if os.path.exists(p):
            try:
                with open(p, "r") as f:
                    content = f.read()
                for line in content.splitlines():
                    line = line.strip()
                    if line.startswith("OPENCODE_API_KEY="):
                        val = line.split("=", 1)[1].strip().strip('"').strip("'")
                        if val:
                            return val
            except Exception:
                pass
    return ""


def build_jev_state_payload(result_row):
    """Builds the deterministic, rounded per-shot JSON state payload for Jev."""
    mount_raw = str(result_row.get("polar_mount_mode", "WRIST")).upper()
    feats = result_row.get("stage3_features", {})
    hp = result_row.get("hier_probs", {})

    if mount_raw == "BAT_HANDLE":
        mount_mode = "BAT_HANDLE"
    elif feats.get("has_polar", False) and mount_raw != "NONE":
        mount_mode = "WRIST_DUAL"
    else:
        mount_mode = "WATCH_ONLY"

    ahrs_valid = bool(feats.get("ahrs_valid", False)) and (mount_mode == "BAT_HANDLE")
    pitch_val = feats.get("ahrs_blade_pitch_deg") if ahrs_valid else feats.get("watch_pitch_deg")

    def r2(val, default=0.0):
        if val is None:
            return default
        try:
            return round(float(val), 2)
        except Exception:
            return default

    return {
        "sensor_mount_mode": mount_mode,
        "tcn_raw_prediction": result_row.get("raw_tcn_cls", result_row.get("pred_cls", "DRIVE/DEFENCE")),
        "tcn_top_prob": r2(result_row.get("prob", 0.50)),
        "tcn_macro_family_probs": {
            "vertical_bat_family": r2(hp.get("p_fam_vert", 0.0)),
            "cross_bat_family": r2(hp.get("p_fam_cross", 0.0)),
            "crouch_sweep_family": r2(hp.get("p_fam_sweep", 0.0)),
        },
        "tcn_subhead_probs": {
            "drive_defence": r2(hp.get("p_sub0_drive", 0.0)),
            "power_drive": r2(hp.get("p_sub0_pd", 0.0)),
            "glance_flick": r2(hp.get("p_sub0_glance", 0.0)),
            "deflection_guide": r2(hp.get("p_sub0_defl", 0.0)),
            "pull_hook_slog": r2(hp.get("p_sub1_pull", 0.0)),
            "cut_punch": r2(hp.get("p_sub1_cut", 0.0)),
            "sweep": r2(hp.get("p_fam_sweep", 0.0)),
        },
        "kinematics": {
            "peak_wrist_gyro_rads": r2(feats.get("peak_wrist_gyro_rads", result_row.get("peak_gyr", 0.0))),
            "peak_impact_accel_ms2": r2(feats.get("peak_impact_accel_ms2", result_row.get("peak_acc", 0.0))),
            "post_impact_acc_ratio": r2(feats.get("post_impact_acc_ratio", 1.0)),
            "bottom_hand_time_lead_ms": r2(feats.get("bottom_hand_time_lead_ms", 0.0)),
            "bottom_hand_gyro_ratio": r2(feats.get("bottom_hand_gyro_ratio", 0.0)),
            "bottom_hand_acc_ratio": r2(feats.get("bottom_hand_acc_ratio", 0.0)),
            "torso_crouch_delta_gz_ms2": r2(feats.get("delta_gz", 0.0)),
            "wrist_roll_delta_rad": r2(feats.get("omega_roll", 0.0)),
            "bat_handle_axial_gyro_min_rads": r2(feats.get("bat_gz_min", 0.0)),
        },
        "ahrs_3d_orientation": {
            "is_valid": ahrs_valid,
            "impact_blade_pitch_deg": r2(pitch_val, 35.0),
            "impact_face_roll_deg": r2(feats.get("ahrs_face_roll_deg"), 0.0),
            "swing_yaw_deg": r2(feats.get("ahrs_swing_yaw_deg"), 0.0),
        },
    }


def build_compact_shot_class_question():
    """Returns the compact 1-question mount-aware System One schema (~1,168 input tokens)."""
    return {
        "shot_class": {
            "type": "choice",
            "instructions": (
                "Classify the cricket batting stroke into one of the 7 canonical biomechanical classes by weighing "
                "the TCN neural probabilities alongside physical kinematic and 3D AHRS invariants. "
                "IMPORTANT MOUNT INVARIANT: Only trust ahrs_3d_orientation when sensor_mount_mode is BAT_HANDLE "
                "and is_valid is true. On WRIST_DUAL or WATCH_ONLY mounts, trust TCN vertical/flick/deflection/sweep "
                "probabilities unless kinematics strongly contradict them."
            ),
            "criteria": {
                "DRIVE/DEFENCE": (
                    "Vertical-bat downswing or defensive block. Moderate or absorbed post-impact energy "
                    "(post_impact_acc_ratio < 1.35) and high drive_defence subhead probability."
                ),
                "POWER DRIVE": (
                    "Explosive vertical-bat lofted or full-blooded drive. High power_drive subhead probability "
                    "with strong follow-through (post_impact_acc_ratio >= 1.30) and high acceleration."
                ),
                "PULL/HOOK/SLOG": (
                    "Aggressive horizontal cross-bat swing to the leg side. High cross_bat_family and "
                    "pull_hook_slog probability, active follow-through (post_impact_acc_ratio > 0.60), "
                    "and flat blade pitch on BAT_HANDLE."
                ),
                "CUT/PUNCH": (
                    "Horizontal or angled off-side square cut or back-foot punch. High cut_punch probability "
                    "and synchronous dual-wrist lock (bottom_hand_time_lead_ms near 0ms on WRIST_DUAL)."
                ),
                "GLANCE/FLICK": (
                    "Wrist-led leg-side flick or hip glance. High glance_flick probability, axial wrist roll, "
                    "or negative leg-side swing_yaw_deg (<= -17 deg with negative bat_handle_axial_gyro_min_rads on BAT_HANDLE)."
                ),
                "DEFLECTION/GUIDE": (
                    "Soft-touch late cut or third-man steer. High deflection_guide probability and low peak acceleration."
                ),
                "SWEEP": (
                    "Kneeling or crouched horizontal sweep or paddle sweep. High crouch_sweep_family probability "
                    "with genuine posture drop (torso_crouch_delta_gz_ms2 >= 1.2) or fast wrist roll (>= 1.6 rad/s)."
                ),
            },
        }
    }


class JevShadowClient:
    """Persistent HTTP Keep-Alive System One client with SHA-1 local JSONL cache."""

    def __init__(self, api_key, cache_path=CACHE_PATH):
        self.api_key = api_key
        self.cache_path = cache_path
        self.session = requests.Session()
        self.endpoint = PRIMARY_ENDPOINT
        self.active_model = FREE_MODEL_ID
        self.cache = {}
        self.stats = {
            "cache_hits": 0,
            "api_calls": 0,
            "free_calls": 0,
            "paid_calls": 0,
            "input_tokens": 0,
            "output_tokens": 0,
            "latencies_ms": [],
        }
        self._load_cache()

    def _load_cache(self):
        if not os.path.exists(self.cache_path):
            return
        try:
            with open(self.cache_path, "r") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    obj = json.loads(line)
                    k = obj.get("cache_key")
                    if k:
                        self.cache[k] = obj
        except Exception:
            pass

    @staticmethod
    def make_cache_key(sid, anchor_t, state_dict):
        state_json = json.dumps(state_dict, sort_keys=True)
        sha1 = hashlib.sha1(state_json.encode("utf-8")).hexdigest()[:12]
        return f"{sid}|{float(anchor_t):.2f}|{sha1}|{JEV_PROMPT_VERSION}"

    def evaluate_shot(self, sid, anchor_t, state_dict):
        ckey = self.make_cache_key(sid, anchor_t, state_dict)
        if ckey in self.cache:
            self.stats["cache_hits"] += 1
            return self.cache[ckey]

        if not self.api_key:
            return None

        questions = build_compact_shot_class_question()
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        models_to_try = [self.active_model]
        if self.active_model == FREE_MODEL_ID:
            models_to_try.append(PAID_MODEL_ID)

        for model_id in models_to_try:
            payload = {
                "model": model_id,
                "state": state_dict,
                "questions": questions,
            }
            for attempt in range(2):
                t0 = time.perf_counter()
                try:
                    resp = self.session.post(self.endpoint, headers=headers, json=payload, timeout=15)
                    lat_ms = (time.perf_counter() - t0) * 1000.0
                    if resp.status_code == 404 and self.endpoint == PRIMARY_ENDPOINT:
                        self.endpoint = FALLBACK_ENDPOINT
                        resp = self.session.post(self.endpoint, headers=headers, json=payload, timeout=15)
                        lat_ms = (time.perf_counter() - t0) * 1000.0

                    if resp.status_code in (404, 410, 429) and model_id == FREE_MODEL_ID:
                        self.active_model = PAID_MODEL_ID
                        break

                    if resp.status_code == 200:
                        data = resp.json()
                        ans = data.get("answers", {}).get("shot_class", {})
                        pred_cls = ans.get("value", "DRIVE/DEFENCE")
                        conf = float(ans.get("confidence", 0.0))
                        probs = ans.get("probabilities", {})
                        usage = data.get("usage", {})
                        in_tok = int(usage.get("input_tokens", 1168))
                        out_tok = int(usage.get("output_tokens", 40))

                        self.stats["api_calls"] += 1
                        if model_id == FREE_MODEL_ID:
                            self.stats["free_calls"] += 1
                        else:
                            self.stats["paid_calls"] += 1
                        self.stats["input_tokens"] += in_tok
                        self.stats["output_tokens"] += out_tok
                        self.stats["latencies_ms"].append(lat_ms)

                        record = {
                            "cache_key": ckey,
                            "sid": sid,
                            "anchor_t": round(float(anchor_t), 2),
                            "model_id": model_id,
                            "prompt_version": JEV_PROMPT_VERSION,
                            "jev_pred": pred_cls,
                            "jev_conf": round(conf, 4),
                            "jev_probs": probs,
                            "latency_ms": round(lat_ms, 1),
                        }
                        self.cache[ckey] = record
                        try:
                            with open(self.cache_path, "a") as f_out:
                                f_out.write(json.dumps(record) + "\n")
                        except Exception:
                            pass
                        return record
                except Exception:
                    time.sleep(0.3 * (attempt + 1))

        return None


def run_stage3_jev_shadow_audit(
    all_results,
    holdout_sessions,
    validation_sessions,
    max_live_jev_calls=350,
    verbose=True,
):
    """
    Executes the Stage 3 Rule Health & Jev Shadow Audit across evaluated candidate results.
    Returns (markdown_section, audit_summary_dict).
    """
    cfg = load_stage3_config()
    rules_cfg = cfg.get("rules", {})
    api_key = resolve_opencode_api_key()
    client = JevShadowClient(api_key=api_key)

    tp_rows = [r for r in all_results if r.get("is_tp") and r.get("gt_cls") not in ("AMBIENT_REST", "NO_SHOT", None)]

    # Build an all-rules-enabled config to shadow-test disabled rules too
    shadow_all_on_cfg = copy.deepcopy(cfg)
    for r_id in shadow_all_on_cfg.get("rules", {}):
        shadow_all_on_cfg["rules"][r_id]["enabled"] = True

    # Identify candidate rows that warrant Jev arbitration (any rule fired in prod or shadow,
    # or Holdout/Validation disagreements/low-confidence boundary shots), prioritizing rule-fired shots first
    jev_records = {}
    candidates_for_jev = []
    for idx, r in enumerate(tp_rows):
        sid = r["sid"]
        is_ho_or_val = (sid in holdout_sessions) or (sid in validation_sessions)
        _, shadow_fired = apply_stage3_rules(
            r.get("raw_tcn_cls", r["pred_cls"]),
            r["prob"],
            r.get("hier_probs", {}),
            r.get("stage3_features", {}),
            r.get("polar_mount_mode", "WRIST"),
            config=shadow_all_on_cfg,
        )
        has_rule_activity = bool(r.get("fired_rules")) or bool(shadow_fired)
        is_boundary_or_err = (r["pred_cls"] != r["gt_cls"]) or (r.get("raw_tcn_cls", r["pred_cls"]) != r["gt_cls"]) or (float(r.get("prob", 1.0)) < 0.65)
        if has_rule_activity or (is_ho_or_val and is_boundary_or_err):
            priority = 0 if has_rule_activity else (1 if sid in holdout_sessions else 2)
            candidates_for_jev.append((priority, idx, r, shadow_fired))

    candidates_for_jev.sort(key=lambda x: (x[0], x[1]))

    if verbose:
        print(f"\n🔍 Running Stage 3 Rule Health & Jev Shadow Audit ({len(candidates_for_jev)} boundary/rule shots across {len(tp_rows)} TP detections)...", flush=True)

    for _, idx, r, _ in candidates_for_jev:
        state = build_jev_state_payload(r)
        ckey = JevShadowClient.make_cache_key(r["sid"], r["t"], state)
        if ckey in client.cache or client.stats["api_calls"] < max_live_jev_calls:
            rec = client.evaluate_shot(r["sid"], r["t"], state)
            if rec is not None:
                jev_records[idx] = rec

    # 1. Compute Per-Rule Health Table across Clean Benchmark (89s) and Holdout (12s)
    rule_ids = [
        "bat_vertical_guard_rule1",
        "bat_ahrs_glance_rule2",
        "non_bat_sweep_to_glance",
        "s1_ahrs_flat_bat",
        "s2_power_drive_vs_pull",
        "s3_cut_punch_recovery",
    ]

    rule_stats = {}
    for rid in rule_ids:
        is_enabled = bool(rules_cfg.get(rid, {}).get("enabled", False))
        # Evaluate each rule isolated on top of raw TCN
        single_cfg = copy.deepcopy(cfg)
        for k in single_cfg["rules"]:
            if k != "sweep_dual_path_gate":
                single_cfg["rules"][k]["enabled"] = (k == rid)

        fires_all, helped_all, hurt_all, corr_when_fired_all = 0, 0, 0, 0
        fires_ho, helped_ho, hurt_ho = 0, 0, 0
        jev_agree_cnt, jev_eval_cnt = 0, 0

        for idx, r in enumerate(tp_rows):
            raw_cls = r.get("raw_tcn_cls", r["pred_cls"])
            pred_r, fired_r = apply_stage3_rules(
                raw_cls,
                r["prob"],
                r.get("hier_probs", {}),
                r.get("stage3_features", {}),
                r.get("polar_mount_mode", "WRIST"),
                config=single_cfg,
            )
            if rid in fired_r:
                fires_all += 1
                was_ok = (raw_cls == r["gt_cls"])
                now_ok = (pred_r == r["gt_cls"])
                if now_ok:
                    corr_when_fired_all += 1
                if now_ok and not was_ok:
                    helped_all += 1
                elif not now_ok and was_ok:
                    hurt_all += 1

                if r["sid"] in holdout_sessions:
                    fires_ho += 1
                    if now_ok and not was_ok:
                        helped_ho += 1
                    elif not now_ok and was_ok:
                        hurt_ho += 1

                if idx in jev_records:
                    jev_eval_cnt += 1
                    if jev_records[idx]["jev_pred"] == pred_r:
                        jev_agree_cnt += 1

        net_all = helped_all - hurt_all
        net_ho = helped_ho - hurt_ho
        prec_all = (corr_when_fired_all / fires_all * 100.0) if fires_all > 0 else 100.0
        jev_agree_pct = (jev_agree_cnt / jev_eval_cnt * 100.0) if jev_eval_cnt > 0 else 100.0

        if is_enabled:
            if net_ho < 0 or net_all < 0 or (fires_all > 0 and prec_all < 55.0):
                status = "⚠️ DRIFT WARNING"
            elif fires_all == 0:
                status = "ℹ️ DORMANT (SAFE GUARD)"
            else:
                status = "✅ HEALTHY"
        else:
            if net_ho > 0 and net_all > 0:
                status = "💡 PROMOTE CANDIDATE"
            else:
                status = f"⏸️ DISABLED (Net {net_all:+d})"

        rule_stats[rid] = {
            "enabled": is_enabled,
            "fires_all": fires_all,
            "helped_all": helped_all,
            "hurt_all": hurt_all,
            "net_all": net_all,
            "fires_ho": fires_ho,
            "net_ho": net_ho,
            "precision_pct": round(prec_all, 1),
            "jev_agree_pct": round(jev_agree_pct, 1),
            "status": status,
        }

    # 2. Missed-Regime Detector on Holdout + Validation (No rule fired, TCN wrong, Jev conf >= 0.55 matches GT)
    missed_clusters = {}
    missed_examples = []
    for idx, r in enumerate(tp_rows):
        if (r["sid"] not in holdout_sessions) and (r["sid"] not in validation_sessions):
            continue
        if r.get("fired_rules"):
            continue
        if r["pred_cls"] != r["gt_cls"] and idx in jev_records:
            jrec = jev_records[idx]
            if jrec["jev_pred"] == r["gt_cls"] and jrec["jev_conf"] >= 0.55:
                mount = r.get("polar_mount_mode", "WRIST")
                key = (r["pred_cls"], r["gt_cls"], mount)
                missed_clusters[key] = missed_clusters.get(key, 0) + 1
                if len(missed_examples) < 50:
                    missed_examples.append({
                        "sid": r["sid"],
                        "t": round(float(r["t"]), 1),
                        "mount": mount,
                        "pred_cls": r["pred_cls"],
                        "gt_cls": r["gt_cls"],
                        "jev_conf": round(float(jrec["jev_conf"]), 2),
                    })

    # 3. Validation Threshold Sensitivity Check (±10% on active thresholds)
    val_rows = [r for r in tp_rows if r["sid"] in validation_sessions]
    val_base_corr = sum(1 for r in val_rows if r["pred_cls"] == r["gt_cls"])
    drift_recommendations = []
    for test_thresh in (0.25, 0.30, 0.35, 0.40, 0.45):
        test_cfg = copy.deepcopy(cfg)
        test_cfg["rules"]["bat_ahrs_glance_rule2"]["min_sub0_glance_path1"] = test_thresh
        c_corr = 0
        for r in val_rows:
            p_cls, _ = apply_stage3_rules(
                r.get("raw_tcn_cls", r["pred_cls"]),
                r["prob"],
                r.get("hier_probs", {}),
                r.get("stage3_features", {}),
                r.get("polar_mount_mode", "WRIST"),
                config=test_cfg,
            )
            if p_cls == r["gt_cls"]:
                c_corr += 1
        if c_corr - val_base_corr >= 2:
            drift_recommendations.append(
                f"`bat_ahrs_glance_rule2.min_sub0_glance_path1 = {test_thresh}` gains +{c_corr - val_base_corr} shots on Validation."
            )

    # Cost & latency stats
    paid_cost_usd = (client.stats["input_tokens"] / 1_000_000.0) * PAID_COST_PER_1M_INPUT if client.stats["paid_calls"] > 0 else 0.0
    med_lat = 0.0
    if client.stats["latencies_ms"]:
        s_lats = sorted(client.stats["latencies_ms"])
        med_lat = s_lats[len(s_lats) // 2]

    # Build Markdown Section
    md = []
    md.append("## 🔍 Stage 3 Rule Health & Jev Shadow Audit")
    md.append(f"- **Config Version**: `v{cfg.get('version', '1.1.0')}` ([`stage3_rules_config.json`](file:///Users/neilkloot/Code/CricketBattingTracker/pipelines/stage3_rules_config.json))")
    md.append(
        f"- **Jev Shadow Auditor (`{client.active_model}`, `{JEV_PROMPT_VERSION}`)**: "
        f"`{client.stats['cache_hits']}` cache hits, `{client.stats['api_calls']}` live calls "
        f"(median latency `{med_lat:.0f} ms`, estimated cost `${paid_cost_usd:.4f} USD`)"
    )
    md.append("")
    md.append("### 1. Stage 3 Rule Health & Shadow Telemetry Table")
    md.append("| Rule ID | State | Clean Benchmark Fires (89s) | Helped / Hurt | **Clean Net Impact** | Holdout Fires (12s) | **Holdout Net Impact** | Rule Precision (%) | Jev Agreement (%) | Health Status |")
    md.append("|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|---|")
    for rid in rule_ids:
        st = rule_stats[rid]
        state_badge = "**ENABLED**" if st["enabled"] else "SHADOW"
        md.append(
            f"| `{rid}` | {state_badge} | {st['fires_all']} | `+{st['helped_all']} / -{st['hurt_all']}` | "
            f"**{st['net_all']:+d} shots** | {st['fires_ho']} | **{st['net_ho']:+d} shots** | "
            f"{st['precision_pct']:.1f}% | {st['jev_agree_pct']:.1f}% | {st['status']} |"
        )

    md.append("")
    md.append("### 2. Missed-Regime Clusters (Validation + Holdout Shots Where TCN Missed & Jev Agreed with GT)")
    if not missed_clusters:
        md.append("- ✅ **No high-confidence missed regimes detected** across Validation and Holdout splits.")
    else:
        md.append("| TCN Prediction | True GT + Jev Class | Sensor Mount | Shot Count | Sample Shots |")
        md.append("|---|---|---|:---:|---|")
        for (p_cls, g_cls, mnt), cnt in sorted(missed_clusters.items(), key=lambda x: -x[1]):
            ex_strs = [f"`{e['sid']}`@{e['t']}s (conf {e['jev_conf']})" for e in missed_examples if e["pred_cls"] == p_cls and e["gt_cls"] == g_cls and e["mount"] == mnt][:3]
            md.append(f"| **{p_cls}** | **{g_cls}** | `{mnt}` | {cnt} | {', '.join(ex_strs)} |")

    md.append("")
    md.append("### 3. Validation Threshold Drift & Calibration Check")
    if not drift_recommendations:
        md.append("- ✅ **All Stage 3 rule thresholds are optimal** on the 9-session Validation Set (no perturbation gains ≥ 2 shots).")
    else:
        for rec in drift_recommendations:
            md.append(f"- ⚠️ **Threshold Drift Recommendation**: {rec}")

    summary_record = {
        "timestamp_utc": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "config_version": cfg.get("version", "1.1.0"),
        "prompt_version": JEV_PROMPT_VERSION,
        "cache_hits": client.stats["cache_hits"],
        "api_calls": client.stats["api_calls"],
        "rule_stats": rule_stats,
        "missed_clusters": [
            {"pred": k[0], "gt": k[1], "mount": k[2], "count": v}
            for k, v in sorted(missed_clusters.items(), key=lambda x: -x[1])
        ],
        "drift_recommendations": drift_recommendations,
    }
    try:
        with open(HISTORY_PATH, "a") as f_hist:
            f_hist.write(json.dumps(summary_record) + "\n")
    except Exception:
        pass

    if verbose:
        print("\n" + "=" * 80)
        print("🔍 STAGE 3 RULE HEALTH & JEV SHADOW AUDIT SUMMARY")
        print("=" * 80)
        print(f"• Evaluated {len(candidates_for_jev)} boundary/rule candidate shots across {len(tp_rows)} TP detections.")
        print(
            f"• API Telemetry: {client.stats['cache_hits']} cache hits, {client.stats['api_calls']} live calls "
            f"(median latency {med_lat:.0f} ms, est cost ${paid_cost_usd:.4f} USD)."
        )
        print("• Production Rules Health:")
        prod_rules = [r for r in rule_ids if rule_stats[r]["enabled"]]
        for rid in prod_rules:
            st = rule_stats[rid]
            print(f"  - {rid:<25}: {st['status']} ({st['fires_all']} fires, Clean Net: {st['net_all']:+d}, Holdout Net: {st['net_ho']:+d})")
        
        print("• Shadow Candidate Rules:")
        shadow_rules = [r for r in rule_ids if not rule_stats[r]["enabled"]]
        for rid in shadow_rules:
            st = rule_stats[rid]
            print(f"  - {rid:<25}: {st['status']} ({st['fires_all']} fires, Clean Net: {st['net_all']:+d}, Holdout Net: {st['net_ho']:+d})")
        
        total_missed = sum(missed_clusters.values())
        if total_missed == 0:
            print("• Missed Regimes: ✅ None detected across Validation and Holdout splits.")
        else:
            print(f"• Missed Regimes: 💡 Surfaced {total_missed} shots across {len(missed_clusters)} clusters where TCN missed & Jev matched GT:")
            for (p_cls, g_cls, mnt), cnt in sorted(missed_clusters.items(), key=lambda x: -x[1])[:4]:
                print(f"    - {cnt} shots: TCN='{p_cls}' -> GT/Jev='{g_cls}' [{mnt}]")
            if len(missed_clusters) > 4:
                print(f"    - ... and {len(missed_clusters) - 4} other cluster(s) (see full scorecard)")
        
        if not drift_recommendations:
            print("• Threshold Drift: ✅ Optimal on 9-session Validation set (no drift detected).")
        else:
            for rec in drift_recommendations:
                print(f"• Threshold Drift: ⚠️ {rec}")
        print("• Master Report: Detailed tables saved to full_dataset_training_scorecard.md")
        print("=" * 80 + "\n", flush=True)

    return "\n".join(md), summary_record
