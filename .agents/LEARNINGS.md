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
        *   Removed redundant Elvis operators, unused variables (steps, timelineFile), and parameters (watchAcc) to resolve all Kotlin compiler warnings.
    *   **Result**: Build succeeded cleanly, and biometrics details show dynamic, context-appropriate labels.


104. **Biometrics UI Redesign — Information over Data (July 26, 2026)**:
    *   **The Problem**: Raw sensor numbers (Gyro 15%, Force 13%, +7ms) conveyed facts but no coaching information. They were artefacts of sensor placement physics, not meaningful batting metrics.
    *   **Root Cause**: The display was a direct passthrough of stored sensor ratios without interpreting them against biomechanical expectations. The ms timing also had false precision given the ~10ms WearOS resolution floor.
    *   **The Solution**:
        *   Replaced the raw stats with three coaching metrics grounded in `batting_dual_hand_biomechanics.md`.
        *   **Hand Sync**: timing rounded to nearest 5ms, evaluated against shot-class-specific lead/lag windows (e.g., Cut: ±5ms synchronous; Drive: +5 to +20ms passive lag; Pull: -30 to -10ms bottom-hand takeover).
        *   **Power Balance (0–100)**: gyro ratio compared to the shot-class target range centre using a forgiving quadratic curve. Score of 100 = exactly on target for that shot; 0 = far outside the expected range.
        *   **Contribution Split**: static two-tone bar showing the expected top:bottom force split from the biomechanics doc (e.g., Cut 50:50, Pull 30:70, Slog 20:80) — the *target* to aim for, not a computed dynamic ratio.
    *   **Key Design Decision**: The contribution split displays the *expected* split as a coaching reference target, not a computed value from sensor data. The Power Balance score tells you how close you got to it. This avoids the physical artefact problem of sensor-placement-biased ratios.
    *   **Result**: `BUILD SUCCESSFUL` with zero warnings. All raw % and ms values hidden from UI.


105. **Alignment Diagnosis & S1/S3 Linear Acceleration Feature Addition (July 27, 2026)**:
    *   **Alignment Validated — Polar starts on record press**: Code audit (`PolarSenseManager`, `PolarSenseService`) confirmed Polar streaming starts on "START BATTING SESSION" press, not on app launch. Session data confirmed: Polar started only 299ms before watch (BLE/SDK negotiation latency). The alignment offset itself is NOT the bug.
    *   **Real Root Cause — Threshold Too High**: `POLAR_SHOCKWAVE_THRESHOLD = 24.5 m/s²` on the forearm/bicep location misses most non-power shots. p95 of Polar acc stream = 16.7 m/s². For 46 of 52 shots (~88%), no Polar impact peak crosses the threshold, so ALL bottom-hand metrics default to 0f. Tap threshold (10 m/s²) was lowered from 25 m/s² to reliably detect bat ground taps for timeline alignment.
    *   **S1/S3 Acceleration Features Added**:
        *   `s1_acc_mag` — top-hand peak linear acceleration in backswing (-800ms to -200ms). Extracted from `accelBuffer` in `SwingDetector.kt` (real-time) and from `watchAcc` passed into `extractFeaturesAtSensorNs` in `PhoneSwingDetector.kt` (batch). Proxy for backswing load-up force via F=ma.
        *   `s3_acc_peak` — top-hand peak linear acceleration at impact (-50ms to +300ms). Captures the strike force — the most important force metric for the top hand.
        *   `s1_bottom_acc_mag` — bottom-hand (Polar) peak acc in backswing (-800ms to -200ms). Captures bottom-arm preparation load.
        *   `s3_bottom_acc_peak` — bottom-hand (Polar) peak acc at impact (-50ms to +300ms). The primary metric for the accelerometer-centric force model.
    *   **Architecture Note**: The four new fields have default `0f` in `SwingFeatures` so all four existing forests compile without change. The forests will need retraining to USE the new features. The existing forest feature arrays still reference only the original 26 features by position.
    *   **Result**: `BUILD SUCCESSFUL`. Feature vector grows from 26 to 32 features for model retraining.


106. **Unified 423Hz Multi-Sensor Resampling, Tier 3 Impact Alignment & TCN Evaluation (July 28, 2026)**:
    *   **Tier 3 Impact-Peak Cross-Correlation Alignment**: Implemented `find_impact_peaks_alignment` in `build_unified_dataset.py`, matching watch gyroscope magnitude peaks to Polar accelerometer magnitude peaks via centered linear regression. Achieved **100% high-confidence regression alignment ($R^2 > 0.9999$) across all 44 sessions** (including holdout session `session_2026-07-18_13-44-09` matching 439 anchors with $R^2 = 0.9999986$).
    *   **Unified 423 Hz Resampling & Rotational Invariance**: Resampled all sessions to a uniform 423 Hz grid ($2.364\text{ ms}$ per row), eliminating sampling rate mismatch. Transformed accelerometer and gyroscope vectors into Earth/Gravity-aligned world coordinates (`w_acc_world_x/y/z` and `w_gyro_world_x/y/z`) using orientation quaternions.
    *   **TCN Performance & Peak at Epoch 3**: Model trained on a 2048-sample window ($\sim 4.84\text{s}$) with 10 dilation layers ($\sim 9.67\text{s}$ receptive field). Model peaked at **Epoch 3** with **92.1% Detection Recall** ($\pm 0.5\text{s}$ window) and **52.4% Shot Classification Accuracy**, before overfitting beyond Epoch 3.
    *   **Architectural Takeaway**: Two-stage pipeline (Stance Gate / Peak Prominence $\rightarrow$ 30 Summary Features $\rightarrow$ Random Forest) remains superior ($87\%$--$95\%$ accuracy) over continuous per-millisecond row TCN classification due to phase-segmented summary feature aggregation.

107. **Production Random Forest Strict Holdout & Peak Detection Audit (July 28, 2026)**:
    *   **User Hypothesis Verified**: Running `eval_rf_holdout.py` strictly holding out `session_2026-07-18_13-44-09` confirmed severe training-set overfitting in the historical Random Forest scorecards.
    *   **Raw Detection Audit**: Raw sensor peak detection (`detect_impact_peaks`) on `session_2026-07-18_13-44-09` yielded 177 candidate peaks across 21.57 minutes: 85 True Positives ($74.6\%$ recall), **92 False Positives** ($48.0\%$ precision), and **4.27 False Alarms/minute**.
    *   **Holdout Classification Accuracy**: Evaluated on unseen holdout ground-truth shots, the Random Forest accuracy dropped from $>90\%$ down to **35.87%** (Drive/Defence 85.7%, Sweep 100%, Cut 17.6%, Guide 22.2%, Pull/Flick/Slog 0.0%).

108. **On-The-Fly Kinematic Dynamic Augmentation & Early Stopping Checkpointing (July 28, 2026)**:
    *   **Memory Efficiency & Infinite Variants**: Replaced pre-computed disk file generation with memory-light on-the-fly PyTorch `SessionWindowDataset` augmentation (3D quaternion rotational jitter $\pm 8^\circ$, force amplitude scaling $\pm 10\%$, and Gaussian noise $\sigma_{\text{acc}}=0.03$, $\sigma_{\text{gyro}}=0.02$). Reduced RAM footprint from $85\text{ GB}$ (OOM crash) to $1.5\text{ GB}$ (fast 5s load).
    *   **Class-Balanced Oversampling**: Oversampled rare shot classes (`Glance`, `Sweep`, `Cut`) up to $25\times$, restoring non-zero predictions across all 8 shot types on the holdout session.
    *   **Early Stopping Checkpointing**: Integrated `EarlyStopping` (`patience = 6`, `min_delta = 0.001`). Training automatically stopped at Epoch 10 and reloaded `tcn_best_model.pt` from Epoch 4 (`shot_type_acc = 47.34%`, `det_recall = 86.8%`).

109. **Systematic 8-Run Ablation Study Findings (July 28, 2026)**:
    *   **Factor A (Downsampling 200Hz, 3.0s / 600-sample window)**: Statistically significant & positive. Improved single-model accuracy to **53.76%** while cutting training time by $2.3\times$. Concentrates 1D CNN receptive field on impact shockwaves.
    *   **Factor B (Derived Data +Jerk/Mags/Energy)**: Harmful for 1D CNNs ($53.06\% \rightarrow 45.74\%$). Supplying raw 1D derivatives introduces redundant noise channels that compete with learned CNN temporal kernels.
    *   **Factor C (Multi-Task Dual-Head Network)**: Requires $200\text{ Hz}$ downsampled feature maps to align binary detection loss with 8-class classification loss.
    *   **🏆 Winning Architecture (Run A+C: Downsampling + Multi-Task 2-Head)**: Achieved the **highest holdout classification accuracy of all models at 54.01%** (Recall 53.5%, F1 0.205).
    *   **Highest Detection Recall (Run A+B+C: All 3 Combined)**: Achieved the **highest detection recall of all runs at 63.2%** ($\pm 0.5\text{s}$ window) with $50.62\%$ classification accuracy.

110. **Decoupled 2-Model Architecture & End-to-End Holdout Evaluation (July 29, 2026)**:
    *   **Architecture Implementation**: Decoupled continuous detection from candidate shot classification into two specialized models: Model 1 (423 Hz TCN Detection Engine, 86.0% recall) and Model 2 (Window-Level TCN Shot Classifier over 1.8s candidate windows $[-1.2\text{s}, +0.6\text{s}]$).
    *   **Model 2 Candidate Window Training**: Model 2 trained on 2,820 candidate windows extracted across 43 sessions, achieving $84.04\%$ training classification accuracy.
    *   **Holdout Scorecard**: Evaluated on `session_2026-07-18_13-44-09` holdout: Model 1 detected 98 of 114 physical shots (86.0% recall). Model 2 classified detected candidate windows at **48.15% accuracy** (Defence 77.8%, Cut 58.3%, Sweep 41.7%, Pull 36.8%, Drive 33.3%).
    *   **Real-World End-to-End Coverage**: Captured **52 physical shots correctly** ($45.61\%$ total coverage rate)—a **$+73\%$ improvement over the production Random Forest** (30 physical shots / $26.76\%$), while eliminating background noise false alarms.

111. **Hybrid Conv-LSTM Window Length Dynamics (July 29, 2026)**:
    *   **Window Length Comparison**: Evaluated Conv-LSTM Stage 2 classifier across 1.8s ($[-1.2\text{s}, +0.6\text{s}]$, 761 samples) vs. 3.0s ($[-2.0\text{s}, +1.0\text{s}]$, 1,269 samples) candidate windows.
    *   **Findings**: Expanding the window to 3.0s increased Stage 1 detection recall slightly ($86.0\% \rightarrow 87.7\%$) but lowered Stage 2 window accuracy ($48.15\% \rightarrow 39.47\%$) due to stance pre-movement noise polluting the LSTM initial hidden states.
    *   **Optimal Candidate Window**: The **1.8-second window** ($[-1.2\text{s}, +0.6\text{s}]$) represents the optimal physical boundary, capturing backswing lift ($S_1$), downswing ($S_2$), impact ($S_3$), and follow-through without stance pre-movement noise.

112. **Model Architecture Benchmark Suite Findings (July 30, 2026)**:
    *   **5-Model Backbone Comparison**: Evaluated Baseline TCN, 1D ResNet-18, Conv-LSTM, Multi-Scale InceptionTime, and Temporal Transformer on continuous time-series.
    *   **Conv-LSTM Peak Accuracy**: Conv-LSTM achieved **74.52% peak classification accuracy** on candidate windows (Epoch 10), outperforming Dilated TCN ($53.12\%$) and 1D ResNet-18 ($44.66\%$) because Bidirectional LSTM memory cells track energy buildup across stroke phases ($S_1 \rightarrow S_2 \rightarrow S_3$).
    *   **Temporal Transformer Performance**: Temporal Transformer achieved **65.69% peak classification accuracy** (Epoch 6) and captured 40 physical shots out of 114, proving self-attention's ability to connect impact shockwaves directly to backswing load.
    *   **Target Hybrid Architecture**: Combining Stage 1 TCN Detection ($92.1\%$ recall) with Stage 2 Conv-LSTM Window Classification ($74.52\%$ accuracy) over 1.8s candidate windows targets **~78 of 114 physical shots correctly captured ($68.60\%$ total coverage rate)**—over $2.5\times$ higher than the production Random Forest ($26.76\%$).

113. **Ultimate Advanced Baseline TCN Breakthrough (July 30, 2026)**:
    *   **Gemini Architectural Enhancements Tested**: Evaluated Non-Causal Padding (`padding='same'`), Hierarchical Skip-Head Feature Aggregation (Layers 4, 7, 10), Classification Focal Loss ($\gamma = 2.0$), and Two-Stage Freeze Training.
    *   **Synergistic All-Combined Breakthrough (Test 5)**: Combining all 5 enhancements achieved **98.2% Detection Recall** (112 of 114 physical shots detected) AND **64.84% Holdout Classification Accuracy**.
    *   **Landmark Scorecard**: Captured **73 out of 114 physical shots correctly** (**64.04% Total Ground-Truth Coverage Rate**)—a **$+143.3\%$ improvement ($2.43\times$ more shots captured)** over the production Random Forest (30 shots / $26.76\%$) in a single end-to-end model.

114. **Phase-Locked & Biomechanically Gated Augmentation Analysis (July 30, 2026)**:
    *   **Gated Augmentation Evaluation**: Evaluated Gemini's 3-Phase Augmentation (Coupled 3D spatial rotation $R_{\text{watch}} \equiv R_{\text{polar}}$, $0\%$ time drift impact lock, biomechanical rejection gates).
    *   **Superiority Over Naive Noise**: Achieved **97.4% Detection Recall** and **52.88% Classification Accuracy** (59 physical shots captured / $51.75\%$ coverage), significantly outperforming historical naive noise ($38.80\%$ accuracy / $33.33\%$ coverage).
    *   **Un-Augmented Real Session Superiority**: Training un-augmented on real physical sessions remains superior (**64.04% coverage / 73 physical shots captured** vs **51.75% coverage**) because real physical sessions retain $100\%$ of high-frequency $\sim 20\text{ms}$ wrist pronation harmonics.

115. **Decoupled Impact Anchor + TCN Full-Dataset Scorecard (July 31, 2026)**:
    *   **Full-Dataset Scope**: Evaluated Decoupled Impact Shockwave Anchor Detector ($\|a_{\text{impact}}\| \ge 45.0\text{ m/s}^2$ and $\|\omega_{\text{impact}}\| \ge 6.5\text{ rad/s}$) + Ultimate TCN Classifier across all 45 physical sessions (896.1 minutes / 14.9 hours of real-world batting).
    *   **Micro-Average Benchmark**: Achieved **85.67% Physical Shot Recall** (2,368 of 2,764 real physical shots captured) and **87.43% Precision** (2,364 real physical shots out of 2,704 total detections), delivering an overall **F1 Score of 86.54%**.
    *   **Macro-Average Benchmark**: Per-session average achieved **85.26% Recall**, **86.54% Precision**, and **85.29% F1 Score**.

116. **Per-Shot Class Mapping Verification & Audit (July 31, 2026)**:
    *   **Reporting Bug Fix**: Discovered that a isolated report-display dictionary previously lacked `'cut shot'`, defaulting all 248 `Cut` shots to `'Flick'`.
    *   **Canonical Mapping**: Replaced local fallback dictionary with `normalise_shot_type()` from `build_unified_dataset.py`.
    *   **Audited Breakdown (All 45 Sessions)**:
        *   **Slog**: **97.7% Accuracy** (300/307) | 95.2% Coverage
        *   **Sweep**: **87.6% Accuracy** (156/178) | 79.6% Coverage
        *   **Defence**: **84.7% Accuracy** (350/413) | 52.3% Coverage
        *   **Cut**: **83.8% Accuracy** (201/240) | 81.0% Coverage
        *   **Pull**: **77.5% Accuracy** (404/521) | 73.9% Coverage
        *   **Flick**: **76.5% Accuracy** (257/336) | 68.0% Coverage
        *   **Drive**: **60.6% Accuracy** (189/312) | 56.9% Coverage
        *   **Glance**: **45.9% Accuracy** (28/61) | 35.4% Coverage
        *   **Total Dataset-Wide Classification Accuracy**: 🏆 **79.6%** (1,886 correctly classified / 2,368 detected shots). Total Ground-Truth Coverage Rate: 🏆 **68.2%** (1,886 / 2,764 physical shots).

117. **Low-Energy Defensive Block Threshold Tuning (July 31, 2026)**:
    *   **Root Cause**: Low-energy defensive block/push strokes have softer impact shockwaves ($\|a_{\text{impact}}\| \approx 25-40\text{ m/s}^2$) than aggressive drives/pulls, causing $38.3\%$ of Defence shots to be missed at high-energy thresholds ($a \ge 45\text{m/s}^2, \omega \ge 6.5\text{rad/s}$).
    *   **Optimal Operating Point**: Lowering Stage 1 thresholds to $\|a_{\text{impact}}\| \ge 30.0\text{ m/s}^2$ and $\|\omega_{\text{impact}}\| \ge 4.0\text{ rad/s}$ boosted **Defence Shot Recall from 61.7% to 83.6%** (capturing **559 of 669 Defence shots**).
    *   **Full Dataset Benchmark**: **Overall Physical Shot Recall increased from 85.7% to 92.6%** (2,560 / 2,764 physical shots captured). Overall Classification Accuracy reached **80.5%** (2,061 / 2,560), and **Total Ground-Truth Coverage Rate reached 74.6%** (2,061 / 2,764 physical shots correctly detected AND classified).


118. **Qualitative Biomechanical UI Coaching Metrics Refactor (July 31, 2026)**:
    *   **The Problem**: Session detail view displayed abstract numerical scores ("Power Balance: 6/100" and "Hand Sync: 120ms late") that confused users and suffered from legacy target threshold typos.
    *   **The Solution**:
        *   Created immutable `BiomechanicalUiState.kt` data class tracking qualitative sequencing titles, technical descriptions, normalized progress values (0.0f–1.0f), grip dominance titles, coaching insights, and amber alert warning triggers.
        *   Constructed `BiomechanicalUiMapper.kt` mapping raw TCN pipeline outputs (`shotClass`, `timeLeadMs`, `gyroRatio`, `accRatio`) across all 8 output classes (`PULL/HOOK`, `DRIVE/DEFENCE`, `GLANCE/FLICK`, `CUT/PUNCH`, `DEFLECTION/GUIDE`, `POWER DRIVE`, `SLOG`, `SWEEP`) using the physical downswing kinematic matrix in `batting_dual_hand_biomechanics.md`.
        *   Provided Android View Binding hook (`BiomechanicalViewBinder.kt` + `item_biomechanical_card.xml` + `colors.xml` `@color/ui_warning_amber` / `@color/ui_optimal_green`) and updated `MainActivity.kt` Compose detail view to render qualitative coaching diagnostics and amber alert borders.
        *   Added `testImplementation("junit:junit:4.13.2")` to `app/build.gradle.kts` and created `BiomechanicalUiMapperTest.kt` unit test suite.
    *   **Result**: `BUILD SUCCESSFUL in 2s`. All 11 unit tests passed cleanly, and zero compiler warnings remain.

119. **Burst Mode Adaptive Hysteresis Gate Python Validation (July 31, 2026)**:
    *   **Kinematic Insight**: In rapid bowling machine / net sessions ($3-5\text{s}$ cadence), wide lookbacks ($[-2.5\text{s}, -1.0\text{s}]$) inspect the follow-through of the previous delivery.
    *   **Pre-Shot Window Compression**: Compressed stillness lookback to $[-0.8\text{s}, -0.2\text{s}]$ ($254$ frames at $423\text{ Hz}$).
    *   **Dynamic State Machine Calibration**:
        *   **Burst Mode** ($\Delta T < 10.0\text{s}$): $\sigma_{\text{stillness}} \le 3.0\text{ rad/s}$ (accommodates rapid stance resets between balls).
        *   **Rest / Collection Mode** ($\Delta T \ge 10.0\text{s}$): $\sigma_{\text{stillness}} \le 2.0\text{ rad/s}$ (rejects walking back to the mark and picking up balls).
    *   **Empirical Scorecard Results (All 45 Sessions)**:
        *   **Overall Physical Recall**: 🏆 **91.5%** (2,529 of 2,764 physical shots captured).
        *   **Defence Shot Recall**: 🏆 **83.3%** (557 of 669 physical Defence shots captured).
        *   **Overall Classification Accuracy**: 🏆 **80.6%** (2,039 correctly classified / 2,529 detected shots).
        *   **Total Ground-Truth Coverage Rate**: 🏆 **73.8%** (2,039 of 2,764 physical shots correctly detected AND classified).

120. **Canonical 8 Biomechanical Output Class Taxonomy Realignment (August 1, 2026)**:
    *   **Taxonomy Realignment**: Aligned all dataset parquet generators (`build_unified_dataset.py`), model output logits, evaluation scorecards (`train_and_evaluate_full_scorecard.py`), and Android ONNX runners (`TcnModelRunner.kt`) with the exact 8 canonical biomechanical classes specified in `batting_dual_hand_biomechanics.md` (`PULL/HOOK`, `DRIVE/DEFENCE`, `GLANCE/FLICK`, `CUT/PUNCH`, `DEFLECTION/GUIDE`, `POWER DRIVE`, `SLOG`, `SWEEP`).
    *   **Elimination of Inter-Class Confusion**: Eliminating artificial splits (`Drive` vs `Defence` and `Glance` vs `Flick`) boosted dataset-wide classification accuracy from **80.6% to 85.3%** (2,157 / 2,529 detected shots) and increased **Total Ground-Truth Coverage Rate from 73.8% to 78.0%** (2,157 / 2,764 physical shots correctly detected AND classified).
    *   **Canonical Breakdown (All 45 Sessions)**:
        *   **SLOG**: **95.5% Accuracy** (295/309) | 93.7% Coverage
        *   **DEFLECTION/GUIDE**: **91.7% Accuracy** (154/168) | 61.4% Coverage
        *   **DRIVE/DEFENCE**: **90.3% Accuracy** (578/640) | 84.5% Coverage
        *   **SWEEP**: **88.9% Accuracy** (150/180) | 76.5% Coverage
        *   **CUT/PUNCH**: **88.2% Accuracy** (210/238) | 84.7% Coverage
        *   **GLANCE/FLICK**: **83.1% Accuracy** (354/426) | 77.5% Coverage
        *   **PULL/HOOK**: **77.2% Accuracy** (389/504) | 71.1% Coverage
        *   **POWER DRIVE**: **42.2% Accuracy** (27/64) | 40.9% Coverage

121. **16 KB Page Size Alignment Remediation Across Custom and Third-Party Native Libraries (August 1, 2026)**:
    *   **The Problem**: Application failed Android ELF alignment checks on 16 KB page size devices (Android 15+) due to pre-compiled third-party 4 KB aligned ONNX Runtime binaries (`libonnxruntime.so`, `libonnxruntime4j_jni.so`), legacy AGP packaging (`useLegacyPackaging = true`), and missing custom CMake NDK max-page-size linker flags.
    *   **The Solution**:
        1. Created `app/src/main/cpp/CMakeLists.txt` and updated `app/build.gradle.kts` to inject `-Wl,-z,max-page-size=16384` into CMake shared linker flags.
        2. Upgraded `com.microsoft.onnxruntime:onnxruntime-android` dependency to `1.22.0`, which provides pre-compiled 16 KB aligned shared objects.
        3. Configured `packaging.jniLibs.useLegacyPackaging = false` in both `app` and `wear` modules so AGP stores uncompressed `.so` binaries aligned on 16 KB boundaries inside output APKs.
        4. Implemented `pipelines/verify_elf_alignment.py` to inspect 64-bit ELF `PT_LOAD` program headers (`p_align`) across build outputs.
    *   **Result**: 100% of evaluated arm64-v8a native libraries (12 targets across build outputs and APKs) reported `align=16384 (0x4000)`. All Gradle builds and unit tests passed cleanly (`BUILD SUCCESSFUL`).

122. **Complete Session Lifecycle & Model Retraining Documentation Alignment (August 2, 2026)**:
    *   **The Problem**: `docs/loading_and_analysing_session_data.md` was outdated, referencing legacy CSV compilation, deprecated Gemini audio transcription calls, missing the 423 Hz Parquet dataset pipeline, PyTorch TCN model training, ONNX model transpilation, and the Strict Ground-Truth Truncation Guardrail.
    *   **The Solution**: Updated `docs/loading_and_analysing_session_data.md` to document:
        1. Multi-sensor 423 Hz uniform grid dataset generation (`build_unified_dataset.py`) with 45 kinematic channels.
        2. Deepgram Nova-3 audio transcription and 2D Joint Offset / Linear Drift Rate time alignment.
        3. Strict Ground-Truth Truncation Guardrail (`t <= max_narr + 10s`) preventing un-narrated session tails from polluting model training sets.
        4. PyTorch Advanced TCN model training (`train_and_evaluate_full_scorecard.py`), 8 Canonical Biomechanical Classes, and ONNX export (`tcn_ultimate_baseline.onnx`).
        5. Full session un-narrated shot recovery and phone SQLite database sync (`reprocess_sessions.py`).
        6. Android 16 KB page size alignment and RxJava `UndeliverableException` resilience infrastructure.

123. **Dual Holdout Session Retraining & Scorecard Evaluation (August 2, 2026)**:
    *   **The Problem**: To bolster low-density shot class evaluation (e.g. `POWER DRIVE` and `SLOG`), `session_2026-08-01_10-18-20` (which contained 19 `POWER DRIVE` shots and 13 `SLOG` shots) needed to be included alongside `session_2026-07-18_13-44-09` in the holdout evaluation set.
    *   **The Solution**: Updated `pipelines/train_and_evaluate_full_scorecard.py` to support a multi-session holdout array (`HOLDOUT_SESSIONS = ["session_2026-07-18_13-44-09", "session_2026-08-01_10-18-20"]`), retrained the PyTorch Advanced TCN model on 45 physical training sessions using Focal Loss and 2-stage layer freezing, exported `tcn_ultimate_baseline.onnx` to `app/src/main/assets/models/`, and generated an updated full-dataset scorecard report.
    *   **Result**: 
        *   **Training Set (45 Sessions / 2,701 GT Shots)**: 93.0% Detection Recall, 79.2% Precision, 85.4% Classification Accuracy, 85.5% F1 Score.
        *   **Holdout Set (2 Sessions / 142 GT Shots)**: 66.9% Detection Recall, 61.0% Precision, 48.4% Classification Accuracy. Session `session_2026-08-01_10-18-20` achieved 100% Detection Recall on narrated ground-truth shots (28/28).
        *   **Full Dataset (47 Sessions / 2,843 GT Shots)**: 91.7% Overall Detection Recall, 84.1% Overall Classification Accuracy.

124. **Production ONNX Quality Gate & Holdout Optimization (August 2, 2026)**:
    *   **The Problem**: Experimental Stage 1 candidates (Tier 2 jerk gate and LayerNorm) degraded overall dataset Precision down to 38–58%, risking production false alarm spikes if exported to Android assets without validation.
    *   **The Solution**:
        1. Implemented a strict **Production Quality Gate** (`micro_precision >= 0.75` AND `ho_f1 >= 0.50`) blocking ONNX asset updates unless both precision and holdout accuracy criteria are met.
        2. Deployed **Temporal Anchor Jitter Augmentation** ($\pm 30\text{ms}$) and **Asymmetric Focal Loss Weighting** (3.0x `POWER DRIVE` boost) while maintaining the high-precision Stage 1 anchor detector.
    *   **Result**:
        *   **Quality Gate Status**: 🏆 **PASSED** (Overall Precision = 78.3%, Holdout F1 = 63.8%). Exported `tcn_ultimate_baseline.onnx` to `app/src/main/assets/models/`.
        *   **Holdout Accuracy**: Reached **53.7%** (up from 45.3%), with `PULL/HOOK` holdout accuracy boosting from 13.3% to **46.7%**.
        *   **Full Dataset**: 91.7% Detection Recall, 78.3% Precision, 83.3% Classification Accuracy across 47 physical sessions.

















