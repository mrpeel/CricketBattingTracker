# Architecture: Pitch Analytix Pro

This document maps directories, API structures, database schemas, and data flow diagrams.

---

## 🏗️ System Architecture (Current — Phone-Based Batch Processing)

> **IMPORTANT**: The on-watch `SwingDetector` classification path was retired in July 2026.
> The watch now records raw sensor data only. All shot detection and classification
> runs as a batch job on the Android phone after the session ends.

```
WATCH                        PHONE                               MAC / PIPELINE
─────────────────────        ──────────────────────────────────  ─────────────────────────────
TrackerService               DataSyncListenerService             compile_dataset.py
  7 sensor streams    ZIP      ↓ unzip watch session               combined_features.csv
  .bin.gz per sensor  ──────→  PhoneSwingDetector.kt             generate_kotlin_forest.py
                               ↓                                   → GeneratedForest.kt
Polar Verity Sense             1. load binary watch files              (wear/ + app/)
  418Hz IMU    BLE   ──────→   2. align Polar (linear regression)  train_quality_classifier.py
  accel + gyro                 3. detect shots (gyro prominence)     quality_classifier.pkl
                               4. extract 20 features              score_phone_pipeline.py
                               5. GeneratedForest.predict()          phone_pipeline_scorecard.md
                               6. → Room DB → Compose UI
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
1. LOAD       Binary sensor files → FloatArray streams
2. LOAD       Polar BLE stream → polarAcc[], polarGyro[] (if present)
3. ALIGN      Paired gyro peak regression → watchToPolarMs() drift correction
4. DETECT     Prominence-based peak detection on gyro magnitude → impact timestamps
5. EXTRACT    Per-shot 20-feature vector:
                Seg 1 (backswing):  s1_gyro_y_std, s1_gyro_z_std, s1_deltaX, s1_deltaZ
                Seg 2 (downswing):  s2_gyroMag, s2_grav_y_mean, s2_deltaX, s2_deltaZ
                Seg 3 (contact):    s3_rollImpactDeg, s3_yawImpactDeg, s3_deltaX, s3_deltaZ,
                                    s3_planeRatio, s3_gyro_y_min
                Polar (if present): bottom_hand_gyro_peak, bottom_hand_acc_peak,
                                    bottom_hand_gyro_ratio, bottom_hand_acc_ratio,
                                    bottom_hand_time_lead_ms, bottom_hand_sync_score
6. CLASSIFY   GeneratedForest.predict(SwingFeatures) → shot type string
              Polar fields default to 0f when absent — no separate code path needed
7. STORE      InningsEvent → Room DB → Compose UI
```

No heuristic post-classification overrides. The RF classifies directly from all 20 features.

---

## 🤖 Machine Learning Model

### GeneratedForest.kt — 20-Feature Random Forest

```kotlin
data class SwingFeatures(
    // 14 watch features (always populated)
    val s1_gyro_y_std: Float,      val s1_gyro_z_std: Float,
    val s1_deltaX: Float,          val s1_deltaZ: Float,
    val s2_gyroMag: Float,         val s2_grav_y_mean: Float,
    val s2_deltaX: Float,          val s2_deltaZ: Float,
    val s3_rollImpactDeg: Float,   val s3_yawImpactDeg: Float,
    val s3_deltaX: Float,          val s3_deltaZ: Float,
    val s3_planeRatio: Float,      val s3_gyro_y_min: Float,
    // 6 Polar features (= 0f when Polar absent)
    val bottom_hand_gyro_peak: Float = 0f,
    val bottom_hand_acc_peak: Float = 0f,
    val bottom_hand_gyro_ratio: Float = 0f,
    val bottom_hand_acc_ratio: Float = 0f,
    val bottom_hand_time_lead_ms: Float = 0f,
    val bottom_hand_sync_score: Float = 0f
)
```

| Parameter | Value |
|---|---|
| Trees | 200, max depth 8, balanced_subsample |
| Training set | 1,949 swings across 955 sessions (all 3 data profiles) |
| Polar imputation | 0.0 for watch-only — model trained heterogeneously |
| CV accuracy | 61.1% (training diagnostic) |
| Training-set fit | 84.8% (overfit indicator) |
| Output classes | CUT/PUNCH, DEFLECTION/GUIDE, DRIVE/DEFENCE, GLANCE/FLICK, POWER DRIVE, PULL/HOOK, SLOG, SWEEP |

Transpiled via `generate_kotlin_forest.py` (big-endian hex-packed binary tree nodes).
Both `wear/` and `app/` receive identical copies automatically.

### Quality Classifier (Python-only — quality_classifier.pkl)
Same 20-feature vector → 4 classes: `good`, `poor`, `miss`, `edge`.
Used by `reprocess_sessions.py` for retrospective re-scoring. Not in Kotlin.

---

## 🐍 Python Pipeline

| Script | Role |
|---|---|
| `augment_training_data.py` | Synthetic augmentation from real sensor windows |
| `evaluate_shot_alignment.py` | Polar-to-watch alignment health + timestamp refinement |
| `compile_dataset.py` | Builds `combined_features.csv` — reads `.bin.gz` or `.csv.gz`, adds `data_profile`, `watch_hz`, `quality`, 6 Polar features (0.0 if absent) |
| `generate_kotlin_forest.py` | Trains 20-feature RF, transpiles `GeneratedForest.kt` to both modules |
| `train_quality_classifier.py` | Trains good/poor/miss/edge classifier |
| `score_phone_pipeline.py` | **Authoritative scorecard** — reads combined CSVs, reports by session/class/profile |
| `model_update_pipeline.py` | Orchestrates all steps end-to-end |

### Authoritative Scorecard: score_phone_pipeline.py

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
├── pipelines/                      # Python ML pipeline (see table above)
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
