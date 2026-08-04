# Plan: Shot Detection Over-Count (session_2026-07-27_12-47-20)

**Status**: Proposed — awaiting architect approval
**Author**: Executor (OpenCode)
**Date**: 2026-07-27
**Target Phase**: Shot Detection Reliability (active)

---

## 1. Problem Statement

`session_2026-07-27_12-47-20` has **59 narrated batting shots** (excluding "Facing up" / "No shot"). The companion app reported **180 detected shots** with an implausible class distribution:

| Class | Reported | Plausible |
|---|---|---|
| PULL/HOOK | 62 | ~31 |
| DEFLECTION/GUIDE | 46 | 0 (no such shots narrated) |
| DRIVE/DEFENCE | 46 | ~18 |
| GLANCE/FLICK | 18 | ~9 |
| CUT/PUNCH | 4 | 0 |
| SLOG | 2 | 0 |
| **Total** | **178–180** | **~59** |

DEFLECTION/GUIDE being a "low-intensity" shot class is the smoking gun: random bat wrist movements are being recognised as shots, and the same physical swing is being emitted twice (once by Pass-1 Polar, once by Pass-2 watch gyro) with timestamps offset enough that the 5 s NMS does not merge them.

`PhoneSwingDetector.kt` was faithfully ported to Python and re-run on this session's raw binary files (see `/var/folders/dy/h6y7bk_53h90fnr14jv83krw0000gn/T/opencode/repro_phone_detector.py`). Reproduction results:

| Stage | Count | Comment |
|---|---|---|
| Narrated actual batting shots | 59 | Gold truth |
| Watch gyro peaks (`mag ≥ 4.0`, →1.5 s apart) | 216 | Threshold sits **below p95 (5.0 rad/s)** of the session gyro stream |
| Watch gyro peaks after `verifySwingBackwards` | 116 | Backwards verify rejects only ~45% |
| Watch gyro peaks after 5 s NMS | 90 | Already 1.5× narrated count |
| Polar acc peaks (`mag ≥ 24.5 m/s²`) | 190 | p95 Polar = 17.84 m/s²; acc coupling on forearm still pushes many swing peaks above |
| Pass-1 polar shots confirming (degenerate alignment) | ~0..90 | Depends on whether live tap capture was available |
| **Combined Pass-1 + Pass-2 (user's count)** | **≈180** | Pass-1 timestamps land >5 s away from Pass-2 timestamps → no NMS merge → doubling |

---

## 2. Root Causes (verified)

### RC-1 — `detectWatchImpactPeaks` lost its prominence gate
`PhoneSwingDetector.kt:1150` defines `calculateProminence()` but it is **never called**. The documented behaviour (see `docs/batting_top_hand_biomechanics.md:97`, `docs/batting_dual_hand_biomechanics.md:200`, `.agents/archive/LEARNINGS_ARCHIVE.md:32`) is:

> Scans watch gyroscope data for peaks exceeding `WATCH_SHOCKWAVE_THRESHOLD` (4.00 rad/s) **OR** peaks crossing a secondary recovery threshold (0.75 rad/s) if they exhibit a topological prominence ≥ 0.50 rad/s.

The current code (`PhoneSwingDetector.kt:1190–1224`) only implements the first branch. Result: every local maximum above 4 rad/s qualifies, even if it is part of a long high-plateau (e.g. continuous bat waggle, frozen at the top of the backlift).

### RC-2 — `WATCH_SHOCKWAVE_THRESHOLD = 4.0` is below session p95
The session's watch gyro magnitude p95 is **5.0 rad/s**. A primary threshold sitting below p95 admits ≈5% of all samples as candidate peaks — far too sensitive. `optimize_shot_enhancement.py` was supposed to re-derive this; its current value in `ShotEnhancementConfig.kt:9` (4.0000) and the latest `pipelines/optimize_shot_enhancement.py:186` (18.0 thus 5.0… both contradict docs).

### RC-3 — `verifySwingBackwards` is too permissive
Current thresholds (`PhoneSwingDetector.kt:1226–1258`):
- Backswing window [−1500 ms, −150 ms] requires `peakGyro ≥ 3.0 rad/s`
- Stance window [−2500 ms, −1000 ms] requires ≥5 rotation samples with quaternion `stdDev ≤ 0.30`

Compare with the watch-side live stance gate (`SwingDetector.kt` H9 hybrid M-of-N): `gyro_std(1 s) < 1.2 rad/s`, **plus** no step event, **plus** ≥1 of (accel_std < 2.0, orientation displacement < 2°, gravity_y ≤ −3.5), held ≥ 1.2 s. The Kotlin phone batch verifier has none of this; the quaternion stdDev of 0.30 ≈ 17° of accumulated drift is far too lax.

### RC-4 — `detectPolarTapSequences` fallback threshold is 10 m/s²
`PhoneSwingDetector.kt:1029` hardcodes `tapThreshold = 10.0 m/s²` — below the **p50** of the forearm Polar acc stream (10.04 m/s²). Half of all samples clear it. Swing pulse peaks (which occur every few seconds during net practice) easily produce 5 fake "taps" within the 200–1500 ms gap window. This produces hundreds of bogus tap "sequences" from which `matchTapSequences` cannot reliably recover the real alignment — `bestErr < 500 ms` over 5 intervals is also far too loose (100 ms / interval average error would suffice).

The live `PolarSenseManager.kt:86` correctly uses `TAP_THRESHOLD_MG = 2500f` (≈ 24.5 m/s²). The fallback must match.

### RC-5 — Pass-1 and Pass-2 are detected independently and only joined by 5 s NMS
When alignment drift mis-projects a Polar impact to a watch sensor-ns that is more than 5 s away from the real impact (degenerate regression per RC-4, or even small alignment error compounded over an 18-minute session), the same physical swing survives in BOTH Pass-1 and Pass-2.

---

## 3. Architect clarification (2026-07-27)

> "If the polar sense tap detection isn't working because there is no polar sense data (most of the earlier sessions) then skipping it makes sense. If it's missing on session with polar sense data, it must be worked out. The taps are done with both hands every time, so if it's not being detected, there is something wrong with the detection. If 5 sharp taps with the bat can be detected with the top hand, it makes no sense that they aren't detected with the bottom hand. Both hands are on the bat."

This means: when Polar data IS present but live taps are absent at processing time, we **fix** the live tap detection pathway (the `PolarSenseManager.tapThreshold` may be too high for the forearm coupling, or the live capture was reset/lost), we **do NOT** silently skip Pass-1.

## 4. Implementation Plan

### Phase A — Restore prominence gate (+tighten watch threshold)
**Files**: `app/src/main/java/com/mrpeel/cricketbattingtracker/services/PhoneSwingDetector.kt`, `app/src/main/java/com/mrpeel/cricketbattingtracker/services/ShotEnhancementConfig.kt`

1. Re-introduce the dual-criteria `detectWatchImpactPeaks`:
   - Strong gate: `mag ≥ WATCH_SHOCKWAVE_THRESHOLD`
   - Recovery gate: `mag ≥ 0.75 && calculateProminence(mags, i) ≥ 0.50`
   - Existing 1.5 s greedy merging-by-magnitude is preserved.
2. Tune `WATCH_SHOCKWAVE_THRESHOLD`. Run `pipelines/optimize_shot_enhancement.py` end-to-end on `combined_features.csv` and accept the new optimised value. Manual sanity check: must exceed session p95 + 1 σ (i.e. > 6.0 rad/s for today's session).
3. Add a quick Python `score_phone_pipeline.py` re-run after the change to confirm per-session candidate counts drop ≤ ~1.15× narrated across all 42 historical sessions.

### Phase B — Tighten `verifySwingBackwards` to mirror H9
**Files**: `app/src/main/java/com/mrpeel/cricketbattingtracker/services/PhoneSwingDetector.kt`

1. Replace `peakGyro ≥ 3.0` with the H9 mandatory gate: `gyro_std over the 1.0 s stance window < 1.2 rad/s` AND no step event in the 1.0 s pre-impact (use existing `loadWatchSteps`).
2. Replace quaternion-only `stdDev ≤ 0.30` with the M-of-3 H9 flexible gate (≥1 of):
   - `gravity_y ≤ −3.5` (loaded from `watchGrav`)
   - `accel_std < 2.0 m/s²` (loaded from `watchAcc`)
   - Orientation displacement (max inter-sample `2·acos(|q·q|)`) < 2.0° over the stance window
3. Require stance to hold continuously for ≥ 1.0 s before the candidate (gate walks: count consecutive sub-windows where mandatory+flexible gate holds).
4. Update the Python port in `/tmp/.../repro_phone_detector.py` to match, re-run on today's session, verify ≤ ~65 candidates after Phase A+B.

### Phase C — Polar alignment rescue
**Files**: `app/src/main/java/com/mrpeel/cricketbattingtracker/services/PhoneSwingDetector.kt`, `app/src/main/java/com/mrpeel/cricketbattingtracker/services/PolarSenseManager.kt`

1. Raise `detectPolarTapSequences` fallback `tapThreshold` 10.0 → 24.5 m/s² (mirror `PolarSenseManager.TAP_THRESHOLD_MG`).
2. Tighten `matchTapSequences` aggregated error `< 500 ms` → `< 250 ms` (sum of 4 inter-tap interval deltas; ~62.5 ms / tap).
3. **Polar data present but no live tap sequences**: (per architect clarification) do NOT silently skip Pass-1. Instead:
   - Investigate the bottom-hand tap detection failure — examine this session's Polar accelerometer magnitudes at the 8 watch TAP_SEQ timestamps (already extracted by `parseWatchTapSequences`). Search ±300 ms around each watch tap for a Polar acc peak.
   - If Polar peak magnitude at those moments is ≥ 24.5 m/s² but `PolarSenseManager.detectedTapSequences.value` was empty → the live capture path dropped/never-cached them. Fix `PolarSenseManager.checkForTapSequence` state retention across service lifecycle, and add logcat breadcrumb `POLAR_TAP_DEBUG`.
   - If Polar peak magnitudes at watch-tap moments are below 24.5 m/s² (forearm coupling actually softer than wrist for ground taps) → admit the truth: **lower** `TAP_THRESHOLD_MG` empirically (grid sweep 2.0 to 2.5 G with 0.1 G step, validate against TAP_SEQ windows in known-good sessions) rather than perma-skip Pass-1. Document the physics in `LEARNINGS.md`.
4. **Polar data absent** (pure watch-only sessions): skip Pass-1 cleanly (current behaviour — no change needed).

### Phase D — Cross-pass deduplication
**Files**: `app/src/main/java/com/mrpeel/cricketbattingtracker/services/PhoneSwingDetector.kt`

1. After Pass-1 confirms promptshots and Pass-2 confirms watchshots, run a direct cross-pass match **before** the 5 s NMS:
   - For each Pass-2 shot, project its sensor-ns to wall-ms.
   - Find the Pass-1 shot with `|t_pass1 − t_pass2| ≤ 250 ms`.
   - Mark the Pass-2 entry as suppressed — keep Pass-1 record (it has the real Polar force features).
   - This eliminates the doubling artefact regardless of alignment drift quality.
2. Keep the existing 5 s NMS as the final dedup between unrelated shots.
3. Add an internal `Log.i(TAG, "Cross-pass dedup: $pass1Count + $pass2Count → $finalCount")` for future debugging.

### Phase E — Regression test + scorecard
**Files**: `pipelines/score_phone_pipeline.py` (existing), test sessions

1. Re-process today's session end-to-end with the new Kotlin path (use `reprocess_sessions.py` against an emulator or a tiny unit harness that calls `PhoneSwingDetector.processSession` with a faked context + DB file path).
2. Re-run `score_phone_pipeline.py` across all 42 historical sessions on the updated `combined_features.csv`.
3. Publish the scorecard deltas into `phone_pipeline_scorecard.md`.
4. **Acceptance criteria** (Test-Debater audit, all must hold before state migration):
   - Today's session: detected count ∈ [55, 65]; zero DEFLECTION/GUIDE; PULL/HOOK ≤ 35.
   - Historical aggregate: mean per-session over-count vs narrated ≤ +8 %, worst session ≤ +20 %.
   - No session regresses in shot-type F1 below its current scorecard baseline.
   - Manual adversarial sample: feed a 10-minute "no batting, walking around with watch" recording through `PhoneSwingDetector` — must produce **0** confirmed shots ( afirm the tightened stance gate rejects grip-changes / walking).

## 5. Out of scope (explicit non-goals)

- Retraining the random forest (`GeneratedDualForest` / `GeneratedTopForest`). This work is purely on the **detection + deduplication** stage.
- Changing `SwingDetector.kt` (the on-watch real-time state machine). Watch-side classification was retired in July 2026 per `ARCHITECTURE.md:9-11`.
- Phone UI changes. The dashboard will re-query the same Room DB; lowered counts flow through naturally.

## 6. Cleanup protocol

After Phase E passes the acceptance criteria, **delete this plan file** (no plan proliferation). Summarise the resolutions as a new entry (#106) in `.agents/LEARNINGS.md` and update ACTIVE_CONTEXT.md item B-001 status.

## 7. Open questions (for architect)

- Q1: In Phase C, if empirically the Polar forearm requires a tap threshold below 24.5 m/s², are we comfortable polluting the live capture with a lower threshold (risk: false-positive taps during actual swings in match-day sessions)? Or should we keep `PolarSenseManager` tight and instead expand the offline fallback path's tolerance selectively (only when invoked from `PhoneSwingDetector`)?
- Q2: Do you want this gated behind a new feature flag `B-031_ShotCountPrecision` in ACTIVE_CONTEXT, or modify the existing B-001 backlog entry in place?