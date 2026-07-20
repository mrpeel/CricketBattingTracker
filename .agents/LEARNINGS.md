# Learnings: Pitch Analytix Pro

This document captures resolved bugs, architectural changes, key logical findings, and historical evaluation scorecards across development sessions.

---

## 💡 Technical Decisions & Discoveries

84. **Phone-Bound Batch Processing Architecture (July 17, 2026)**:
    *   **The Problem**: Real-time swing detection and Random Forest classification on the watch app consumed battery and were fragile during game days when the watch disconnected from the phone boundary. Additionally, the Polar Verity Sense's 16MB internal storage can only buffer high-frequency 416Hz IMU data for ~10 minutes, making offline Polar recording infeasible.
    *   **The Solution**: Transitioned the architecture to phone-side batch processing:
        *   **Watch**: Registers sensors at `SENSOR_DELAY_FASTEST`, disables active `SwingDetector` loops, and packages the raw session directory as a ZIP archive on stop, streaming it to the phone via GMS `ChannelClient` path `/raw_session_data`.
        *   **Phone**: `DataSyncListenerService` unzips watch logs, locates the latest Polar folder, and triggers `PhoneSwingDetector` to execute linear alignment regression, Polar impact peak detection (> 24.5 m/s²), stance look-back window geodesic search, feature extraction, Random Forest classification, and video clipping entirely offline.
        *   **Python Pipeline**: Modified `automate_pipeline.py` to pull consolidated watch + Polar folders directly from the phone companion app's path, bypassing slow watch Wi-Fi ADB.
        *   **Phone UI**: Added a circular progress loading indicator on the session details screen if raw logs are still unzipping and batch processing is in progress.
    *   **Result**: Watch battery usage is minimized, data alignment is preserved, and the system functions seamlessly offline on game days with processing consolidated on the phone.

85. **Custom Minimalist Navigation Vector Drawables (July 18, 2026)**:
    *   **The Problem**: The phone companion app's bottom navigation bar used generic emojis ("📊", "🎙️", "📋") which looked simple and unpolished, falling short of premium UI design aesthetics.
    *   **The Solution**: Created three high-fidelity, clean minimalist vector XML drawables in `res/drawable/` matching the user's uploaded spec:
        - `ic_dashboard.xml`: A side-facing cricket helmet with ear guards and jaw grill protection, combined with wave lines representing telemetry streams.
        - `ic_record.xml`: A geometric, faceted cricket ball outline detailing seams and facets, including a solid "REC" recording indicator.
        - `ic_history.xml`: A binder-ring calendar showing an internal trending line chart and a prominent swooping arrow extending out to represent progression history.
        Mapped these assets inside `MainActivity.kt` using Jetpack Compose's `Icon` and `painterResource`.
    *   **Result**: Bottom tab navigation renders with custom abstract vector lines, providing a highly premium, state-of-the-art look.

86. **Pipeline 2: 20-Feature RF Classifier with Inline Polar Integration (July 18, 2026)**:
    *   **The Problem**: The old RF used 14 watch-only features. Polar features were injected as post-hoc heuristic rule overrides in `PhoneSwingDetector.kt` (if DRIVE && gyroRatio > X → POWER DRIVE). This approach is brittle, untrainable, and discards discriminative Polar signal.
    *   **The Solution**: Expanded `SwingFeatures` to 20 features (14 watch + 6 Polar: `bottom_hand_gyro_peak`, `bottom_hand_acc_peak`, `bottom_hand_gyro_ratio`, `bottom_hand_acc_ratio`, `bottom_hand_time_lead_ms`, `bottom_hand_sync_score`). Polar fields default to `= 0f` in Kotlin so watch-only inference requires zero caller changes. The RF was trained on heterogeneous data (50Hz/100Hz watch, with/without Polar) with Polar features imputed to 0.0 for watch-only sessions. The heuristic override block in `PhoneSwingDetector.kt` was removed — `GeneratedForest.predict(featuresWithPolar)` is called directly.
    *   **Key Design Constraint**: The on-watch `SwingDetector.kt` constructs `SwingFeatures` with only 14 fields — Polar defaults to 0f automatically. This is intentional and correct: the watch classifies at 14-feature resolution and the phone re-classifies with the full 20 when Polar data is present.
    *   **Quality Classifier**: `train_quality_classifier.py` trains a 4-class RF (good/poor/miss/edge) on the same 20-feature vector. CV accuracy 69.7% but class recall for miss (9%) and poor (13%) is low due to severe class imbalance (816 good vs 64 miss). More labelled data for off-centre hits will improve recall.
    *   **Result**: BUILD SUCCESSFUL. `SwingDetectorGroundTruthTest` passes. `GeneratedForest.kt` retrained on 1,949 swings across 955 sessions; selected config 200 trees depth 8, CV accuracy 61.1%.

87. **Dead Scorecard Antipattern — SwingDetectorGroundTruthTest (July 19, 2026)**:
    *   **The Problem**: `SwingDetectorGroundTruthTest.kt` was streaming raw sensor events through `SwingDetector.kt` (the retired on-watch classification path) and reporting its output as the system scorecard. This test was measuring a code path that no longer runs in production. All decisions about model quality were based on numbers from a phantom system.
    *   **Root Cause**: The architecture shifted from on-watch classification to phone-side batch processing (`PhoneSwingDetector.kt`), but the Kotlin test was never updated. It continued reporting "session_20260717: classification 0.23" which was meaningless — the on-watch path with 14 features and Polar=0f scoring a session that was designed for 20-feature phone-side processing.
    *   **Rule Established**: A test that exercises a retired code path is worse than no test — it actively misinforms. When the architecture changes, tests must change with it immediately. The authoritative evaluation must always exercise the path that runs in production.

88. **Authoritative Scorecard: score_phone_pipeline.py (July 19, 2026)**:
    *   **The Solution**: `score_phone_pipeline.py` reads `combined_features.csv` and `combined_ground_truth_aligned.csv` — both produced by `compile_dataset.py` from the actual phone pipeline outputs. It fits the 20-feature RF and reports training-set accuracy by session, shot class, and data profile. Writes `phone_pipeline_scorecard.md`.
    *   **Key Output**: Training-set fit 84.8% overall. Per-class: SWEEP 100%, SLOG 98%, DEFLECTION/GUIDE 90%, POWER DRIVE 88%, CUT/PUNCH 84%, GLANCE/FLICK 83%, DRIVE/DEFENCE 75%, PULL/HOOK 75%. Detection recall 100% (all labelled shots have predictions in the aligned CSV).
    *   **Slim Kotlin Tests**: `SwingDetectorGroundTruthTest.kt` reduced from 800 lines to 6 integrity tests (model deserialises, Polar defaults work, 20-feature path works, determinism, extreme values). Build time dropped from 41s to 15s.
    *   **CRITICAL RULE**: Accuracy figures from `phone_pipeline_scorecard.md` are **training-set fit** (the model was trained on this same data). They are diagnostic only. Authoritative generalisation accuracy requires held-out sessions not included in training. Never present training-set accuracy as model performance.

89. **Scipy Peak Prominence & 2-Stage Hysteresis Alignment (July 20, 2026)**:
    *   **The Problem**: Static amplitude watch gyro threshold (1.5 rad/s) suffered from a 94% false-positive rate on non-swings during dataset alignment, while missing slow defensive strokes or late-cuts if set higher.
    *   **The Solution**: Refactored `automate_pipeline.py` to use `scipy.signal.find_peaks` with prominence >= 0.5 rad/s. Implemented dynamic distance calculation `distance = max(3, int(fs * 0.1))` based on session sampling frequency to ensure a consistent 100ms spacing. Built a 2-stage window alignment search: primary threshold >= 4.00 rad/s to catch high-velocity swings, falling back to a recovery threshold >= 0.75 rad/s for slow/defensive shots.
    *   **Result**: Successfully aligned 35 sessions, identifying 5 low-confidence sessions (MAE >= 1.50s) to be manual-offset overridden or excluded from training.

90. **Shot-Specific expected lags & P75 Deviation Metric (July 20, 2026)**:
    *   **The Problem**: A static expected lag assumption of 2.5 seconds was skewed by follow-through durations (e.g. Straight/Power Drives having 3.5-4.5s lag) and crouched/rotational shots (e.g. Sweeps having under 2.0s lag). Further, using the average (MAE) was highly vulnerable to outliers from delayed user voice comments.
    *   **The Solution**: Modified `evaluate_shot_alignment.py` to map expected lag targets dynamically based on the shot category (e.g. 4.5s for Straight Drives, 2.0s for Sweeps, 3.5s for Power Drives). Replaced the mean absolute error with the 75th percentile of absolute deviations (`P75 Dev`) for the confidence thresholds, rendering the scoring robust to isolated late narrations.
    *   **Result**: Rebuilt the evaluation report with `P75 Dev` stats accurately flagging sequence-level matching anomalies without penalizing normal biomechanical narration delays. Additionally calibrated Polar-active sessions by adding a $+150$ms expected lag offset (compensating for bottom-hand physical lead over the wrist gyro) and dynamically relaxing the confidence thresholds (HIGH $\le 1.3$s, MEDIUM $\le 2.4$s) to eliminate false-positive LOW ratings on historical Polar logs.



