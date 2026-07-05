# Learnings: Pitch Analytix Pro

This document captures resolved bugs, architectural changes, key logical findings, and historical evaluation scorecards across development sessions.

---

## 💡 Technical Decisions & Discoveries

53. **Parquet Integration & Adversarial Verification (July 3, 2026)**:
    *   **The Problem**: Reading from partitioned Parquet directories via Pandas (`pd.read_parquet(root_path, filters=...)`) forces Pandas to infer a unified schema across all partitioned subfolders. Because different sensor types contain completely different schemas (e.g. `gyro` has `x,y,z`, `game_orient` has `qx,qy,qz,qw`), this schema inference drops columns (like `qx`) or fails with `KeyError`.
    *   **The Solution**: Modified the Parquet loading code to target the partition subdirectories directly (`pd.read_parquet(os.path.join(root_path, "sensor_type=game_orient"), filters=[("session_id", "==", session_id)])`). This completely isolates the schema context of the target sensor type and reads files instantly.
    *   **Result**: All adversarial analysis tests ran and compiled successfully, generating a comprehensive alignment and stance gate performance report (`last_session_analysis_update.md`) across all 25 sessions.

54. **Validation Check Swing Filters Alignment (July 4, 2026)**:
    *   **The Problem**: After updating the clock synchronization algorithm to treat defenses, blocks, edges, and misses as alignment non-swings (which use the fallback path), the pipeline crashed during validation with a `RuntimeError: ❌ Alignment failed due to high fallback rate (49.4%).` This happened because the validation check's `active_swings` calculation still counted those low-energy shots as active swings, leading to a false high fallback rate calculation.
    *   **The Solution**: Modified `active_swings` in `automate_pipeline.py`'s validation block to filter out defenses, blocks, edges, and misses, aligning the validation check definitions with the clock offset search's peak matching filters.
    *   **Result**: Validated that `automate_pipeline.py` runs successfully on local session folders without crashing and accurately computes high-energy swing alignment fallback rates.

56. **Resolving Build Warnings & Deprecations (July 5, 2026)**:
    *   **The Problem**: Building the application triggered various compilation warnings in `MainActivity.kt` and `VideoRecordService.kt` related to deprecated API usage, unnecessary non-null assertions, unused method parameters, and deprecated overridden methods.
    *   **The Solution**:
        1. Fixed the unnecessary double bang `!!` on the non-null `bestLocation` Smart Cast.
        2. Added the `@Deprecated` annotation to the overridden deprecated `onStatusChanged` listener callback.
        3. Suppressed the deprecation warning on `getFromLocation()` in `cacheLocation()` using `@Suppress("DEPRECATION")`.
        4. Replaced the deprecated `Divider` layout composable with `HorizontalDivider`.
        5. Removed the unused `context` parameter from `VideoRecordScreen`.
        6. Suppressed the deprecation warnings on Bluetooth SCO APIs in `VideoRecordService.kt` and added proper SCO release cleanup in `onDestroy`.
    *   **Result**: The app builds cleanly with zero errors/warnings.

57. **High-Fidelity Shot Types Cards Layout (July 5, 2026)**:
    *   **The Problem**: The tabular layout for shot type distribution was prone to horizontal truncation and clipping under strict constraints, particularly on standard companion devices. Additionally, displaying raw angle metrics with inline letters (like `-1° S` or `51° L`) was cluttered.
    *   **The Solution**:
        1. Switched the distribution table to a list of individual type cards inside a new layout section titled **SHOT TYPES PLAYED**.
        2. Programmed four distinct baseline-aligned columns: `KM/H`, `EFF`, `FACE`, and `LAUNCH`.
        3. Configured `ShotTypeMetricCol` to display large values (e.g. max values or face/launch descriptions like `Open`, `Closed`, `Lofted`, `Ground`) adjacent to smaller secondary values (e.g. average values or absolute angles) aligned at the bottom baseline.
        4. Structured the launch angles to present absolute angles with their trajectories (e.g., `Ground 8°`, `Lofted 15°`), matching the sport-specific vocabulary and layout of the designs.
    *   **Result**: The app builds cleanly and fits exactly to the requested sporty designs.

58. **Tightened Layouts and Timeline Column Alignment (July 5, 2026)**:
    *   **The Problem**: The "Shot Types Played" cards had excessive vertical padding and spacing, and the primary values were too large and bold. Additionally, the timeline shot cards had suboptimal horizontal spacing, with too much space allocated for the simple `EFF` metric (values <= 100%) and not enough space for `BLADE` and `LAUNCH` metrics, causing horizontal text wrapping and clipping.
    *   **The Solution**:
        1. Shrunk the vertical card padding in `ShotTypeSummary` to `10.dp` and removed the spacer between metrics headers and values.
        2. Configured the primary values in `ShotTypeMetricCol` to use `14.sp` `SemiBold` weight (down from `18.sp` `Bold`), and secondary values to use `10.sp` normal weight.
        3. Redistributed column weights inside the timeline card layout: decreased `EFF` weight to `0.6f` and expanded `BLADE` and `LAUNCH` weights to `1.5f` and `1.6f` respectively.
        4. Updated `BLADE` and `LAUNCH` values to show in the format `"{Description} (degrees)"` (e.g. `Closed (4°)`, `Lofted (15°)`), utilizing the wider column widths to handle the longest text combinations without wrapping.
    *   **Result**: Verified compilation, all tests pass, and layout renders cleanly with zero text wrap anomalies.

59. **Terminologies and Layout Constraints (July 5, 2026)**:
    *   **The Problem**:
        1. In the "Shot Types Played" cards, the values were still too large and bold, and there was excessive vertical spacing between column titles and values.
        2. The default ML class `"Square"` was confusing to the user, who wanted it shown as `"Full face"`.
        3. In the timeline cards, wide text values like `"FULL_FACE (0°)"` or `"Grounded (0°)"` were clipping on the right edge because the columns were still too narrow. When the second text wrapped, it pushed the first text to the second line because of `Alignment.Bottom`, making it look like the angle was missing.
    *   **The Solution**:
        1. Mapped both `"SQUARE"` and `"FULL_FACE"` classes to `"Full face"` (which is also much narrower in lowercase!).
        2. Updated `TimelineItem` layout to render `BLADE` and `LAUNCH` descriptions even if the corresponding angle is null, while including the degree angle in the format `"{Description} (degrees)"` when present.
        3. Increased `BLADE` column layout weight to `1.8f` and `LAUNCH` to `2.1f` (allocating 65% of the total card width to these two columns).
        4. Reduced the value text sizes inside "Shot Types Played" cards to `11.sp` `Medium` (primary) and `9.sp` `Normal` (secondary).
        5. Disabled default platform font padding (`includeFontPadding = false`) on all texts in `ShotTypeMetricCol` to completely eliminate excess vertical gaps.
    *   **Result**: Verified that the companion app builds and renders correctly with no text clipping.

60. **Negative Layout Offsets and Padding Tuning (July 5, 2026)**:
    *   **The Problem**: The vertical gap between the titles and values in both the "Shot Types Played" cards and the individual timeline shot cards was still too wide visually.
    *   **The Solution**:
        1. Applied `Modifier.offset(y = (-4).dp)` to the values row in `ShotTypeMetricCol`.
        2. Disabled default platform font padding (`includeFontPadding = false`) on the label and value texts in `MetricSmallCompact`.
        3. Applied `Modifier.offset(y = (-4).dp)` to the value text in `MetricSmallCompact` to pull it closer to its title.
    *   **Result**: The vertical gap was tightened further to remove vertical dead space, and compilation succeeded.

61. **Multi-Point Acoustic Sync Tap Drift Optimization (July 5, 2026)**:
    *   **The Problem**: Clocks on separate smart devices drift relative to each other over long recording sessions. A single start-point sync tap is sufficient to calculate the initial clock offset, but does not capture dynamic clock drift across multiple rounds. Additionally, speech recognition (Gemini Flash) drops the word "tap" due to bat ground hits masking the vocal track.
    *   **The Solution**:
        1. Implemented a local Python acoustic transient detector in `automate_pipeline.py` that processes the full narration audio duration.
        2. Extracted all non-overlapping 5-tap sequences from both the audio WAV file and the watch accelerometer spikes.
        3. Enforced a 10-second sequence deduplication check on the accelerometer peaks to drop adjacent rebound/wiggle sequences.
        4. Matched the sequences sequentially using a dynamic offset projection step (using a broadened `30.0s` search window).
        5. Calculated the precise offset and drift rate using linear regression (`np.polyfit`) across the matched coordinates.
    *   **Result**: Bypassed Gemini's transcription issues entirely. Successfully matched all 3 rounds of sync taps on `session-2026-07-05_16-27-16` (offsets of `-14.58s`, `-17.00s`, and `+0.36s`), calculating a starting offset of `-18.828s` and a clock drift rate of `+0.0176452` (`+1.7645%` speed correction factor, correcting roughly 1.06 seconds of drift per minute). All late-session shots align cleanly.
















62. **Synthetic IMU Data Augmentation Pipeline (July 5, 2026)**:
    *   **The Problem**: Backlog items B-013 (SLOG ~40% accuracy), B-001 (Pull Shot FP), and B-002 (Cover Drive recall) were caused by insufficient and imbalanced training data. Collecting new real sessions is slow and watch position varies.
    *   **The Solution**: Built `scratch/augment_training_data.py` - a standalone two-pass augmentation script. Pass 1 counts real shots per class. Pass 2 generates exactly CAP_MULTIPLIER=3 x real_count synthetic variants per class. Proportional cap prevents DRIVE/DEFENCE (467 real, 1401 synthetic) from dominating while boosting sparse classes (SLOG: 91 real, 273 synthetic). Four techniques on raw sensor windows: 3D Rotation (+-15 deg, correct quaternion composition), Time Warp (+-10% spline), class-aware asymmetric Magnitude Scaling (SLOG/POWER DRIVE scale-up only; DRIVE/DEFENCE scale-down only to prevent boundary crossing), Gaussian Jitter (sigma=0.5%). Magnetometer excluded. Synthetic data stored outside repo and never used for evaluation.
    *   **Key Finding - 15x multiplier overcorrected**: First attempt with flat 15x (22,005 variants) caused severe regressions (DRIVE/DEFENCE -29%, PULL/HOOK -26.6%) despite improving SLOG to 87.5%. The 3x proportional cap resolved this.
    *   **testCutPunch Fix**: New model correctly reclassified old test parameters (roll -25 to -5 deg, deltaX 0.2-0.4) as DRIVE/DEFENCE. Updated to real CUT/PUNCH biomechanics (roll approx -130 deg, deltaX approx 1.5, deltaZ approx 1.1).
    *   **Result**: CV accuracy 0.6317 to 0.7834 (+15.2pp). Training: 880 real + 3090 synthetic. All 12 unit tests pass, 0 RF alignment mismatches.

63. **Facing Up Stance Staggering & Timing Sweep (July 5, 2026)**:
    *   **The Problem**: Rule-based Stance Detector (Facing Up) parameter sweep was repeating the same results on unstressed data. We needed to test timing robustness (MinDur and BreakTolerance) under twitches and quick-prep swing periods.
    *   **The Solution**: Implemented Option 3 (Stance Timing Staggering & Twitch Injection) inside pipelines/adversarial_facing_up_search.py and pipelines/adversarial_analysis.py. Added apply_stance_stress_to_session_cache applying random 0.15s transient motion twitches (gyro std=4.0, accel std=5.0) and stance compression (0.5s-1.5s noise injection) to session cache data in-memory.
    *   **Performance Optimization**: Python-based std-of-mag row checks took 1.24s per call. Sweep grid expansion (4,608 configurations) would have taken 95 minutes. Added get_precomputed_features cache keyed on id(df_gyro), bringing run times down to 26ms per call (50x speedup); entire grid sweep finishes in under 2 minutes.
    *   **Finding**: On target session, timing stress degraded F1 from 0.336 to 0.195. While target search preferred 0.5s minimum stance duration to capture fast swings, validation across all 26 sessions showed 0.8s minimum duration remains optimal to suppress transient false positives globally. Retained MinDur=0.8s and BreakTol=1.5s.
