# Architecture: Pitch Analytix Pro

This document maps directories, API structures, database schemas, and data flow diagrams.

---

## 🏗️ System Architecture (Current — Multi-Tier TCN & 3D Bat Orientation AHRS)

> **IMPORTANT**: The on-watch `SwingDetector` classification path was retired in July 2026.
> The watch records raw sensor data only. All shot detection, Stage 1 stance gating,
> Stage 2 TCN window classification, 3D Bat Orientation AHRS, and kinematic validation
> run as an offline batch pipeline on the Android phone (`PhoneSwingDetector.kt`).

```
WATCH                        PHONE                               MAC / PIPELINE
─────────────────────        ──────────────────────────────────  ─────────────────────────────
TrackerService               DataSyncListenerService             pipelines/
  7 sensor streams    ZIP      ↓ unzip watch session               train_and_evaluate_full_scorecard.py
  .bin.gz per sensor  ──────→  PhoneSwingDetector.kt               → tcn_ultimate_baseline.onnx
                               ↓                                   → facing_up_detector.onnx
Polar Verity Sense             1. load binary watch files          → tcn_norm_stats.json
  418Hz IMU    BLE   ──────→   2. align Polar & Mount Mode (WRIST / BAT_HANDLE)
  accel + gyro                 3. Stage 1 Stance (facing_up_detector.onnx) + 4.0s Scan Window
                               4. 300ms Backswing check (≥8°)
                               5. 3D Bat Orientation AHRS (OrientationAhrs.kt)
                               6. Kinematic Detachment Guard (KinematicGuard.kt)
                               7. Stage 2 TCN 208d Multi-Scale Inference & Binary FP Rejector (TcnModelRunner.kt)
                               8. Dual-Path Sweep Gate & Biomechanical Consistency (Gate 1 removed)
                               9. → Room DB v12 (57 columns, auto-healing) → Compose UI
```


---

## ⌚ Watch Sensor Recording (TrackerService)

The watch no longer classifies shots. Its sole job is high-fidelity sensor recording and ZIP delivery.

| Sensor | Constant | Rate | Binary File |
|---|---|---|---|
| Accelerometer | `TYPE_ACCELEROMETER` | 50Hz or 100Hz | `WatchAccelerometer.bin.gz` |
| Gyroscope | `TYPE_GYROSCOPE` | 50Hz or 100Hz | `WatchGyroscope.bin.gz` |
| Gravity | `TYPE_GRAVITY` | 50Hz | `WatchGravity.bin.gz` |
| Game Rotation Vector | `TYPE_GAME_ROTATION_VECTOR` | 50Hz | `WatchGameOrientation.bin.gz` |
| Rotation Vector | `TYPE_ROTATION_VECTOR` | 50Hz | `WatchOrientation.bin.gz` |
| Magnetometer | `TYPE_MAGNETIC_FIELD` | 50Hz | `WatchMagnetometer.bin.gz` |
| Step Detector | `TYPE_STEP_DETECTOR` | Event | `WatchSteps.bin.gz` |

### Binary Sensor Format
Fixed-width little-endian binary records per row, GZIP-compressed:
- `int64` nanosecond timestamp
- `float32 × N` sensor values (N=3 for XYZ, N=4 for quaternions)
- `float32` seconds_elapsed

Legacy `.csv.gz` files preserved alongside `.bin.gz`. Python loads via `load_watch_sensor()` (auto-detects format). Kotlin reads via `BinarySensorDecoder`.

### Data Profiles
| Profile | Watch Hz | Polar | Description |
|---|---|---|---|
| `50hz_watch` | 50Hz | No | Watch-only sessions |
| `50hz_watch_polar` | 50Hz | Yes | Watch + Polar Verity Sense |
| `100hz_watch_polar` | 100Hz | Yes | High-frequency watch + Polar |

---

## 📱 Phone-Side Batch Processing (PhoneSwingDetector.kt)

Triggered by `DataSyncListenerService` after unzipping the watch session ZIP.

```
1. LOAD       Binary sensor files → FloatArray streams (WatchAcc, WatchGyro, WatchRot)
2. LOAD       Polar BLE stream → polarAcc[], polarGyro[] + PolarMountMode (WRIST vs BAT_HANDLE)
3. ALIGN      Paired gyro peak regression / 1D cross-correlation → watchToPolarMs() drift correction
4. STAGE 1    Facing Up Stance Detection (facing_up_detector.onnx, dynamic batch 256)
5. ANCHOR     4.0s single-shot stance peak anchoring (T_peak = argmax(||omega||))
6. ORIENT     3D Bat Orientation AHRS (OrientationAhrs.kt) → attitude, blade pitch, face roll, swing yaw
7. GUARD      Kinematic Detachment Guard (KinematicGuard.kt) → catches sensor tumble / separation
8. STAGE 2    28-channel normalization + TCN inference (tcn_ultimate_baseline.onnx via TcnModelRunner.kt) with 208d multi-scale impact-core pooling & binary false-positive rejection (P(no_shot) >= 0.35)
9. GATING     Dual-Path Sweep Gate + Mount-Aware Biomechanical Physical Consistency Gate (Rule 1; Gate 1 removed)
10. STORE     InningsEvent (57 columns) → Room DB v12 (with auto-repairing onOpen guard) → Compose UI
```

---

## 🤖 Machine Learning Model Architecture

### Primary Production Model: BatPlaneGeometryThreeFamilyTCN (tcn_ultimate_baseline.onnx)
- **Backbone**: 10-layer Dilated Temporal Convolutional Network with non-causal padding and 208-dimensional multi-scale impact-core feature pooling:
  - Core L5 [16d], Core L7 [64d], Proj Core L10 [64d] (sliced over $\pm 175$ frames / ~827ms around impact peak), combined with Global L7 [64d] context: $16 + 64 + 64 + 64 = 208\text{d}$.
- **Heads**:
  - `head_reject` (Binary Rejection MLP: $208\text{d} \rightarrow 64\text{d} \rightarrow 2\text{d}$): Learned false-positive rejection ($P(\text{no\_shot}) \ge 0.35$).
  - `head_family` (Macro Family Gate: $208\text{d} \rightarrow 64\text{d} \rightarrow 3\text{d}$): Vertical (0), Cross-Bat (1), Floor/Sweep (2).
  - `head_sub0` (Vertical Sub-Classifier: $208\text{d} \rightarrow 64\text{d} \rightarrow 4\text{d}$): `DRIVE/DEFENCE`, `POWER DRIVE`, `GLANCE/FLICK`, `DEFLECTION/GUIDE`.
  - `head_sub1` (Cross-Bat Sub-Classifier: $208\text{d} \rightarrow 64\text{d} \rightarrow 2\text{d}$): `PULL/HOOK/SLOG`, `CUT/PUNCH`.
- **Soft-Routing Calibration**:
  - Power Drive: $\text{effective\_pd\_fam} = p_{\text{fam}}[0] + 0.85 \cdot p_{\text{fam}}[1]$ (allows high angular momentum and wrist roll without cross-bat collapse).
- **Normalization**: 28-channel median/MAD normalization stats defined in `app/src/main/assets/models/tcn_norm_stats.json`.
- **Runtime Engine**: `TcnModelRunner.kt` executing ONNX opset 18 via Microsoft ONNX Runtime Android SDK with deterministic tensor lifecycle closing.

### Legacy / Fallback Classifier: 30-Feature Random Forest (GeneratedForest.kt)
Historical model (transpiled via `generate_kotlin_forest.py`). Retained for historical baseline testing and lightweight comparisons:

```kotlin
data class SwingFeatures(
    // ── Watch / top-hand features (16 fields, always populated) ──
    val s1_gyro_y_std: Float,
    val s1_gyro_z_std: Float,
    val s1_deltaX: Float,
    val s1_deltaZ: Float,
    val s1_acc_mag: Float,          // Peak linear acceleration magnitude in backswing
    val s2_gyroMag: Float,
    val s2_grav_y_mean: Float,
    val s2_deltaX: Float,
    val s2_deltaZ: Float,
    val s3_rollImpactDeg: Float,
    val s3_yawImpactDeg: Float,
    val s3_deltaX: Float,
    val s3_deltaZ: Float,
    val s3_planeRatio: Float,
    val s3_gyro_y_min: Float,
    val s3_acc_peak: Float,         // Peak linear acceleration magnitude at impact
    // ── Polar / bottom-hand features (14 fields, default 0f when Polar absent) ──
    val bottom_hand_gyro_peak: Float = 0f,
    val bottom_hand_acc_peak: Float = 0f,
    val bottom_hand_gyro_ratio: Float = 0f,
    val bottom_hand_acc_ratio: Float = 0f,
    val bottom_hand_time_lead_ms: Float = 0f,
    val bottom_hand_sync_score: Float = 0f,
    val s1_bottom_gyro_mag: Float = 0f,
    val s1_bottom_deltaZ: Float = 0f,
    val s1_bottom_acc_mag: Float = 0f,  // Peak Polar acc magnitude in backswing
    val s2_bottom_acc_mean: Float = 0f,
    val s2_dynamic_ratio_slope: Float = 0f,
    val s3_bottom_pronation_deg: Float = 0f,
    val s3_bottom_gyro_y_min: Float = 0f,
    val s3_bottom_acc_peak: Float = 0f  // Peak Polar acc magnitude at impact
)
```

| Parameter | Value |
|---|---|
| Trees | 200, max depth 8, balanced_subsample |
| Routing Models | `GeneratedTopForest` (Watch-only) vs `GeneratedDualForest` (Dual-sensor net practice) |
| Quality Models | `GeneratedTopQualityForest` (Watch-only) vs `GeneratedDualQualityForest` (Dual-sensor) |
| Output Classes | CUT/PUNCH, DEFLECTION/GUIDE, DRIVE/DEFENCE, GLANCE/FLICK, POWER DRIVE, PULL/HOOK, SLOG, SWEEP |

Transpiled via `generate_kotlin_forest.py` (big-endian hex-packed binary tree nodes).
Both `wear/` and `app/` receive identical copies automatically.

### Quality Classifiers (transpiled as GeneratedTopQualityForest / GeneratedDualQualityForest)
Uses the same 30-feature vector (with Polar defaulted to 0f when absent) to predict shot quality across 4 classes: `good`, `poor`, `miss`, `edge`. Runs offline in Kotlin on the phone app during session reprocessing.

---

## 🐍 Python Pipeline

| Script | Role |
|---|---|
| `augment_training_data.py` | Synthetic augmentation from real sensor windows |
| `evaluate_shot_alignment.py` | Polar-to-watch alignment health + timestamp refinement |
| `compile_dataset.py` | Builds `combined_features.csv` — reads `.bin.gz` or `.csv.gz`, adds `data_profile`, `watch_hz`, `quality`, and all top/polar features |
| `generate_kotlin_forest.py` | Trains Dual-Model Random Forests (Top/Dual for both Shot Type and Quality) and transpiles Kotlin classes directly to both modules |
| `train_quality_classifier.py` | Trains good/poor/miss/edge RF quality classifier |
| `score_phone_pipeline.py` | **Authoritative scorecard** — reads combined CSVs, reports by session/class/profile |
| `train_and_evaluate_full_scorecard.py` | **Master TCN Training & Evaluation** — Stratified 4-way split (12 holdout, 7 val, 13 quarantine, 53 train), Layer-wise Discriminative LR ($1.5 \times 10^{-4}$ L1-7, $5.0 \times 10^{-4}$ L8-10+Heads), Validation Macro-F1 Early Stopping (`patience=16`), exports self-contained ONNX opset 18 model (`dynamo=False`) |
| `model_update_pipeline.py` | Orchestrates all steps end-to-end |

### BatPlaneGeometryThreeFamilyTCN Model Architecture
- **Backbone**: 10-layer Dilated Temporal Convolutional Network with non-causal padding and 208-dimensional multi-scale impact-core feature pooling (Core L5, Core L7, Proj Core L10, Global L7).
- **Training Strategy**: Layer-Wise Discriminative Learning Rate:
  - TCN Layers 1–7: `lr = 1.5e-4` (preserves low-level and mid-level temporal representations).
  - TCN Layers 8–10 & Multi-Task Heads: `lr = 5e-4`.
  - Loss: Binary Rejection Cross-Entropy Loss + Weighted Macro Family & Sub-Classifier CE with label smoothing.
- **Early Stopping & Checkpoint Selection**: Monitored on `val_macro_f1` across 7 designated validation sessions with `patience = 16` epochs, `min_delta = 0.001`, `TOTAL_EPOCHS = 28`. Reloads highest Validation Macro-F1 checkpoint.
- **Production Asset**: ONNX opset 18 model at `app/src/main/assets/models/tcn_ultimate_baseline.onnx` (`input_imu_stream` -> `output_logits`, 7.1 MB, embedded weights). Evaluated via `TcnModelRunner.kt`.

### Authoritative Scorecard: score_phone_pipeline.py & train_and_evaluate_full_scorecard.py

Reads `combined_features.csv` + `combined_ground_truth_aligned.csv`.
Replaces the retired `SwingDetectorGroundTruthTest` session replay (which tested the dead on-watch path).
Writes `phone_pipeline_scorecard.md`.

**CRITICAL**: Accuracy figures are training-set fit (diagnostic only). Real generalisation accuracy requires held-out sessions.

---

## 🧪 Kotlin Tests (SwingDetectorGroundTruthTest.kt)

6 model integrity tests only. Session replay was removed — it tested dead code.

| Test | Checks |
|---|---|
| `testModelPredictsPullShot` | Model deserialises, returns valid class |
| `testModelPredictsdriveShot` | Second class path |
| `testPolarDefaultsWatchOnlyPath` | 14-field watch-only call backward compat |
| `testFullTwentyFeaturePolarPath` | 20-field phone-path compiles + predicts |
| `testPredictionIsDeterministic` | Same input → same output × 3 |
| `testAllEightClassesRegistered` | Extreme values don't crash; NUM_TREES in bounds |

Build time: ~15s.

---

## 📂 Workspace Layout

```
├── .agents/                        # Agent memory & rules
├── app/                            # Android companion phone app
│   └── src/main/java/.../
│       ├── data/                   # Room DB (InningsEvent, HeartRateEvent)
│       ├── ml/                     # GeneratedForest.kt (auto-synced from wear/)
│       └── services/               # DataSyncListenerService, PhoneSwingDetector.kt
├── wear/                           # Wear OS watch app
│   └── src/main/java/.../
│       ├── ml/                     # GeneratedForest.kt (source), SwingFeatures
│       └── services/               # TrackerService (7 sensors → .bin.gz)
├── pipelines/                      # Python ML pipeline (see table below)
│   ├── build_unified_dataset.py    # 423Hz grid resampling & Tier 3 impact peak alignment (R² > 0.9999)
│   ├── run_advanced_baseline_tests.py # Ultimate Advanced Baseline TCN (98.2% recall, 64.8% acc, 64.0% coverage)
│   ├── run_ablation_study.py       # 8-run systematic ablation study (Downsampling, Derived, Multi-Task)
│   ├── run_model_architecture_benchmark.py # 5-model backbone suite (TCN, ResNet-18, Conv-LSTM, Inception, Transformer)
│   ├── train_decoupled_pipeline.py # Decoupled 2-Model Pipeline (Stage 1 TCN + Stage 2 1.8s Conv-LSTM)
│   └── eval_rf_holdout.py          # Production Random Forest holdout evaluation audit
├── docs/                           # System documentation & ML experiment reports
│   └── ml_experiments_summary_2026-07-30.md # Master ML research & scorecard summary
├── phone_pipeline_scorecard.md     # Authoritative model performance
├── model_update_analysis.md        # Before/after retraining comparison
└── automate_pipeline.py            # Audio-sensor alignment (Gemini transcription)
```

### Key Data Files (/Users/neilkloot/Code/Batting Sensor Stats/)
```
live_watch_sessions/session-YYYY-MM-DD_HH-MM-SS/
    WatchAccelerometer.bin.gz       ← new binary format
    WatchGyroscope.bin.gz
    WatchAccelerometer.csv.gz       ← legacy, kept for reference
    ground_truth_aligned.csv        ← narrated GT + impact timestamps + Polar features
    latest_timeline.txt             ← shot timeline from phone app

combined_features.csv               ← 20-feature training set (all sessions)
combined_ground_truth_aligned.csv   ← GT + predicted_shot_type cross-ref
quality_classifier.pkl              ← good/poor/miss/edge RF
quality_le.pkl                      ← quality label encoder
```

---

## 🔗 Key Code Linkages

### Watch App (`:wear`)
- **[TrackerService.kt](file:///Users/neilkloot/Code/CricketBattingTracker/wear/src/main/java/com/mrpeel/cricketbattingtracker/services/TrackerService.kt)**: 7 sensor streams → `.bin.gz` + session ZIP via GMS ChannelClient
- **[SwingDetector.kt](file:///Users/neilkloot/Code/CricketBattingTracker/wear/src/main/java/com/mrpeel/cricketbattingtracker/ml/SwingDetector.kt)**: 4-state machine retained on watch for timing reference; classification on watch is lower-fidelity (14 features, no Polar)
- **[GeneratedForest.kt](file:///Users/neilkloot/Code/CricketBattingTracker/wear/src/main/java/com/mrpeel/cricketbattingtracker/ml/GeneratedForest.kt)**: 20-feature transpiled RF (source copy)

### Phone App (`:app`)
- **[PhoneSwingDetector.kt](file:///Users/neilkloot/Code/CricketBattingTracker/app/src/main/java/com/mrpeel/cricketbattingtracker/services/PhoneSwingDetector.kt)**: Full batch pipeline — binary load → Polar align → detect → 20-feature extract → classify
- **[DataSyncListenerService.kt](file:///Users/neilkloot/Code/CricketBattingTracker/app/src/main/java/com/mrpeel/cricketbattingtracker/services/DataSyncListenerService.kt)**: Receives ZIP, triggers PhoneSwingDetector
- **[GeneratedForest.kt](file:///Users/neilkloot/Code/CricketBattingTracker/app/src/main/java/com/mrpeel/cricketbattingtracker/ml/GeneratedForest.kt)**: Auto-synced copy from `wear/`


---

## ⌚ SwingDetector State Machine (Reference — Still Active on Watch)

The watch still runs the 4-state machine for real-time timing reference, but its
classification output is superseded by the phone-side batch processing.

```
ACTIVITY_CLASSIFY → FACING_UP_LOCKED (H9 hybrid gate ≥ 1.2s)
FACING_UP_LOCKED  → MEASURING_ARC    (gyro_mag > 5.0 rad/s)
MEASURING_ARC     → CONTACT_WAIT     (swing duration ≥ 1.0s)
CONTACT_WAIT      → ACTIVITY_CLASSIFY (T_peak + 0.75s → evaluateShot())
```

**H9 Hybrid M-of-N Stance Gate**:
- Mandatory: `gyro_std(1s) < 1.2 rad/s` + no step event in 1.0s
- Flexible (≥1 of 3): `accel_std < 2.0`, `ori_disp < 2.0°`, `gravity_y ≤ -3.5`
- Must hold ≥ 1.2s; 1.5s break tolerance; 2.5s post-shot guard

Empirical validation (session-2026-05-31): Pre-shot TP 78.3%, Walk FP 1.68/min.
