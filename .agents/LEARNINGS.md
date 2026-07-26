# Learnings: Pitch Analytix Pro

This document captures resolved bugs, architectural changes, key logical findings, and historical evaluation scorecards across development sessions.

---

## 💡 Technical Decisions & Discoveries

93. **Decoupled Two-Stage Narration Pipeline & Parser Overhaul (July 21, 2026)**:
    *   **The Problem**: The initial Stage 2 python parser had fragile string matching. It dropped valid narrations containing edge/miss events (e.g. `"Forward edge"`), failed to recognize bat switch announcements like `"Iron Bat"`, and relied on global string replacements (`.replace("touch", "cut")`) which corrupted shot categories.
    *   **The Solution**: Overhauled `process_and_format_events()` in `automate_pipeline.py`:
        *   **Regex-based Shot Matching**: Uses word-boundary regex (`\b(flick|click)\b`, `\b(pull|full)\b`) to prevent substring collisions.
        *   **Comprehensive Bat Inheritance**: Recognizes `"Iron Bat"` / `"Eye In"`, `"Gray Nicolls Giant"`, and `"Game Bat"`, persisting bat state across subsequent shots while ignoring round headers.
        *   **Edge & Defense Fallbacks**: Ensures edge and miss events (e.g. `"Forward edge"`) map to `Defence/Block` with `poor` or `miss` quality rather than being dropped.
    *   **Result**: Zero events dropped, exact bat tracking verified, and all 135 narration items cleanly generated into `narrations_raw.json`.


94. **Dual-Model Routing Architecture & 26-Feature Classification (July 21, 2026)**:
    *   **The Problem**: Single combined 20-feature model suffered from imputation skew during match-day watch-only sessions (where Polar data is absent). Furthermore, global Polar metrics lacked temporal segmentation across backswing, downswing, and follow-through phases.
    *   **The Solution**: Implemented a **Dual-Model Routing Architecture**:
        *   **Watch-Only Path (Match Day)**: Routes to `GeneratedTopForest.kt` (14 features) and `GeneratedTopQualityForest.kt` (14 features).
        *   **Dual-Sensor Path (Net Practice)**: Routes to `GeneratedDualForest.kt` (26 features) and `GeneratedDualQualityForest.kt` (26 features), adding 6 new segmented Polar metrics (`s1_bottom_gyro_mag`, `s1_bottom_deltaZ`, `s2_bottom_acc_mean`, `s2_dynamic_ratio_slope`, `s3_bottom_pronation_deg`, `s3_bottom_gyro_y_min`).
        *   **Kotlin & Pipeline Integration**: Transpiled all four models plus backward-compatible `GeneratedForest` and `GeneratedQualityForest` alias objects into `wear` and `app` modules. Updated `PhoneSwingDetector.kt` to extract segmented Polar features when Polar logs are present and route dynamically. Increased Gradle JVM heap memory (`org.gradle.jvmargs=-Xmx4096m`) to compile transpiled forest models without OOM errors.
    *   **Result**: All unit tests pass cleanly (`BUILD SUCCESSFUL`). `model_update_pipeline.py` executes end-to-end and outputs complete performance metrics in `model_update_analysis.md`.


95. **Session Directory Naming & Data Profile Breakdown Fix (July 21, 2026)**:
    *   **The Problem**:
        1. `compile_dataset.py` filtered session folders using `d.startswith("session-")`. Recent sessions (such as `session_2026-07-20_12-42-16`, containing 19 sweep shots) used an underscore `session_`, causing them to be excluded from dataset compilation and scorecards.
        2. `model_update_pipeline.py` Section 4 threw a `TypeError: '<' not supported between instances of 'float' and 'str'` when sorting profile values that included `NaN`.
    *   **The Solution**:
        1. Updated session directory listing logic in `compile_dataset.py`, `optimize_shot_enhancement.py`, and `score_phone_pipeline.py` to match both `session-` and `session_` prefixes.
        2. Updated `model_update_pipeline.py` Section 4 to handle Dual-Model Routing, filter `NaN` profiles before sorting, and render clean markdown tables.
    *   **Result**: Included July 20 and July 21 sessions, expanding 100Hz watch + Polar evaluated shots from 69 to 148 (including 20 sweeps with 100% classification accuracy). Section 4 now generates cleanly without errors.


96. **Android 16 KB Page Alignment Compatibility (July 21, 2026)**:
    *   **The Problem**: Android 15 / 16 KB page size testing devices showed a warning dialog: `ELF alignment check failed. The following libraries are not 16 KB-aligned: lib/arm64-v8a/libimage_processing_util_jni.so`.
    *   **Root Cause**: `useLegacyPackaging = true` in `app/build.gradle.kts` forced AGP to store dynamic `.so` files compressed without alignment. Furthermore, older CameraX versions (1.3.4) bundled JNI binaries compiled without 16 KB page boundary alignment.
    *   **The Solution**: Removed `useLegacyPackaging = true` from `app/build.gradle.kts` and upgraded CameraX dependencies to `1.4.1` (which provides native 16 KB page alignment for all JNI libraries).


97. **Cross-Sensor Timestamp Reference Frame Mismatch & Telemetry Resolution (July 21, 2026)**:
    *   **The Problem**: Phone app displayed corrupted bio-metric ratios (e.g. 13% for 105 km/h Pull Shot), 0/100 Sync Score, missing `REACT` (`impactTimeMs`) reaction time, and incorrect clock times (1:01 PM).
    *   **Root Cause**:
        1. In `PhoneSwingDetector.kt`, `wTimeMs` (epoch ms, e.g. `1.75e12`) had boot-time nanos subtracted (`5.48e8 ms`), producing a 55-year timestamp discrepancy (`1.75e18 ns`) where `getGyroPeak` found zero watch samples, defaulting ratios to 13–18%.
        2. `reprocess_sessions.py` omitted `impactTimeMs` from its SQL `INSERT INTO innings_events` statement.
        3. Sync Score penalized unphysiological ratio variations ($|1.0 - \text{ratio}|$) and collapsed to 0/100.
        4. Companion app defaulted session start time to `System.currentTimeMillis()` (phone sync time) when `latest_timeline.txt` lacked `SYSTEM_START`.
    *   **The Solution**:
        1. Unified candidate impact lookups in `PhoneSwingDetector.kt` using `targetSensorNs` relative to `watchStartSensorNs`.
        2. Added directory name timestamp parser `parseSessionStartWallMs(watchDir)` for fallback start times in both `PhoneSwingDetector.kt` and `DataSyncListenerService.kt`.
        3. Removed arbitrary Sync Score gauge from `MainActivity.kt` UI, expanding Hand Timing, Gyro Ratio, and Force Ratio cleanly.
        4. Included `impactTimeMs` in `reprocess_sessions.py` SQL insertion and `PhoneSwingDetector.kt` `InningsEvent` population.
    *   **Result**: Ratios, clock times, and reaction time metrics are accurate and consistent.


98. **Variable Scope Pollution in Python Alignment Pipeline (July 22, 2026)**:
    *   **The Problem**: The Polar features extraction pipeline (`add_polar_features_to_aligned_shots` in `automate_pipeline.py`) was generating `NaN` metrics for all shots after index 0 across the entire dataset. Only the very first shot had valid bottom-hand ratios.
    *   **Root Cause**: Inside the shot processing loop, a local variable for the segment 2 dynamic ratio slope calculation was defined as `slope`. Because Python does not have block scope, reassigning `slope` inside the loop re-declared and polluted the outer scope's alignment `slope` variable. In subsequent iterations, the watch-to-polar mapping formula used the corrupted dynamic slope, projecting shots into negative/out-of-bounds timestamps and triggering the default `NaN` assignment check.
    *   **The Solution**: Renamed the loop-local variable to `s2_slope` and refactored the trapezoidal integration logic to use `numpy.trapezoid` or `numpy.trapz` fallbacks. Successfully reprocessed all historical Polar datasets, recovering 100% feature coverage across all sessions.


99. **Phase Nanosecond Timings, 26-Feature Export & Downswing Polar Peak Matching (July 22, 2026)**:
    *   **The Problem**:
        1. Reprocessed session details showed flat `90%` efficiency and flat `350ms` reaction time across every shot, while bottom-to-top hand timing lag showed unphysiological values up to `+861ms` (bottom hand 861ms behind watch impact on a 104 km/h Pull shot).
        2. Ground truth alignment CSV files lacked explicit nanosecond phase start/end boundaries and missing feature columns needed for first-principles verification.
    *   **Root Cause**:
        1. `reprocess_sessions.py` and `PhoneSwingDetector.kt` hardcoded efficiency to `90.0%` for `quality == "good"` string predictions instead of physical ratio $\frac{\text{impactGyro}}{\text{maxGyro}}$. `reaction_time_ms` defaulted to `350ms` when candidate slices lacked stance locks.
        2. `automate_pipeline.py` searched for Polar peak magnitudes across an unconstrained $\pm 1000\text{ms}$ ($\pm 1.0$s) window around impact. When players tapped their bat or adjusted their stance $+861\text{ms}$ *after* impact, the search grabbed that post-shot tap as the peak, reporting $+861\text{ms}$ lag and tiny ratios ($13\% / 9\%$) evaluated on the tap instead of the actual stroke downswing.
    *   **The Solution**:
        1. Added explicit phase start/end nanoseconds (`s1_start_ns`, `s1_end_ns`, `s2_start_ns`, `s2_end_ns`, `s3_start_ns`, `s3_end_ns`) and seconds to `ground_truth_aligned.csv` and `combined_ground_truth_aligned.csv`.
        2. Exported all 26 sensor features as explicit columns in both CSV files.
        3. Constrained Polar peak search window to the actual downswing phase ($[-200\text{ms}, +100\text{ms}]$), eliminating post-shot tap artifacts and restoring physical hand timing lead ($\pm 190\text{ms}$).
        4. Replaced hardcoded efficiency and 350ms defaults with true physical efficiency $\frac{\text{impact\_gyro\_mag}}{\text{gyroMag}} \times 100\%$ and dynamic reaction time from backswing onset.
    *   **Result**: Regenerated all 38 session datasets (3,606 rows), verified all 57 columns in `combined_ground_truth_aligned.csv`, and confirmed physical telemetry values in SQLite `innings_events`.


100. **Kotlin Named Parameter Mismatch in PhoneSwingDetector.kt (July 25, 2026)**:
    *   **The Problem**: `./deploy_physical.sh` failed during Kotlin compilation with `Cannot find a parameter with this name: offset_ms` and `drift_rate` in `PhoneSwingDetector.kt:106`.
    *   **Root Cause**: Fallback `TimeAlignment` instantiation used snake_case parameter names (`offset_ms`, `drift_rate`) matching python pipeline naming instead of camelCase (`offsetMs`, `driftRate`) defined on the Kotlin data class.
    *   **The Solution**: Updated `PhoneSwingDetector.kt` to use `TimeAlignment(offsetMs = fallbackOffset, driftRate = 0.0)`.
    *   **Result**: Gradle build succeeded (`BUILD SUCCESSFUL in 33s`) and APK deployed to physical device.


102. **Deepgram Ground Truth Re-alignment & Dual-Model RF Retraining (July 26, 2026)**:
    *   **The Problem**: Transitioning from Gemini audio narrations to Deepgram Nova-3 required rebuilding all session ground truth CSV files and retraining all Random Forest classifiers on the newly aligned, timing-accurate dataset. Single-point sync-tap sessions previously forced `drift_rate = 0.0`, causing clock drift over 18+ minute sessions and alignment failures (e.g. 32.7% fallback rate on `session_2026-06-27_14-12-40`).
    *   **The Solution**:
        *   Updated `automate_pipeline.py` to trigger 2D grid search centered at `sync_tap_offset` whenever single-point calibration occurs (`sync_tap_drift_rate == 0.0`), resolving drift across long sessions and achieving 100% alignment success across all 42 sessions.
        *   Updated `augment_training_data.py` to match both `session-` and `session_` folder prefixes, generating 1,098 synthetic variants across all shot classes.
        *   Executed end-to-end retraining via `model_update_pipeline.py`, transpiling all 4 Dual-Model Random Forests (`GeneratedTopForest`, `GeneratedDualForest`, `GeneratedTopQualityForest`, `GeneratedDualQualityForest`) directly to `:wear` and `:app` modules.
    *   **Result**: 42/42 sessions successfully re-aligned (4,070 GT rows, 3,148 feature rows). Dual-Model classifier achieved **95% accuracy** on 100Hz Watch + Polar sessions (`100hz_watch_polar`), **87%** on 50Hz Watch + Polar, and **76%** on Watch-only sessions. All Gradle unit tests passed cleanly.


103. **Shot-Class-Specific Biomechanics Baselines & Redundant Elvis Warnings (July 26, 2026)**:
    *   **The Problem**: Grip dominance and wrist action labels were static and incorrect across shots (e.g. both a Cut and a Drive registering as "Top Hand Dominant" and "Locked Wrist"). Furthermore, watch-only sessions incorrectly displayed the bottom-hand biometrics card with placeholder 0s.
    *   **Root Cause**: The app used flat global thresholds (e.g. `< 0.85` for Top Hand) which ignored different kinematic baselines (e.g. Pull shots have a median ratio of `0.12`, while Cover Drives have `0.61`). Additionally, `PhoneSwingDetector.kt` defaulted bottom hand metrics to `0` instead of `null` when Polar data was absent, and the UI check did not filter out zeros.
    *   **The Solution**:
        *   Updated `PhoneSwingDetector.kt` to default bottom hand metrics to `null` when Polar data is absent.
        *   Updated `MainActivity.kt` to hide the biometric section if `bottom_hand_gyro_ratio` is null or `0f` (guarding legacy data).
        *   Mapped shot types to baseline median ratios from the dataset and evaluated dominance and wrist whippiness relative to those baselines.
        *   Removed redundant Elvis operators inside smart-cast scopes to resolve Kotlin compiler warnings.
    *   **Result**: Build succeeded cleanly, and biometrics details show dynamic, context-appropriate labels.
