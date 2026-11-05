# Architecture: Pitch Analytix Pro

This document maps directories, sensor pipelines, machine learning architectures, database schemas, and data flow diagrams.

---

## 🏗️ System Architecture (Current — Multi-Tier TCN, 3D Bat Orientation AHRS & Live Coaching)

> **IMPORTANT**: The on-watch `SwingDetector` classification path was retired in July 2026.
> The watch records raw binary sensor streams (`.bin.gz`) only. All shot detection, Stage 1 stance gating,
> Stage 2 TCN window classification, 3D Bat Orientation AHRS, and kinematic validation
> run as an offline batch pipeline on the Android phone (`PhoneSwingDetector.kt`), complemented by
> real-time sub-80ms in-ear coaching (`LiveKinematicCoach.kt`) over Polar BLE during active sessions.

```
WATCH                        PHONE                               MAC / PIPELINE
─────────────────────        ──────────────────────────────────  ─────────────────────────────
TrackerService               DataSyncListenerService             pipelines/
  7 sensor streams    ZIP      ↓ unzip watch session (WakeLock)    train_and_evaluate_full_scorecard.py
  .bin.gz per sensor  ──────→  PhoneSwingDetector.kt (Mutex)       → tcn_ultimate_baseline.onnx
                               ↓                                   → facing_up_detector.onnx
Polar Verity Sense             1. load binary watch files          → tcn_norm_stats.json
  423Hz IMU    BLE   ──────→   2. align Polar & Mount Mode (WRIST / BAT_HANDLE)
  accel + gyro                 3. Stage 1 Stance (facing_up_detector.onnx) + 4.0s Scan Window
       │                       4. 300ms Backswing check (≥8°)
       ├─► LiveKinematicCoach  5. 3D Bat Orientation AHRS (OrientationAhrs.kt)
       │   (Real-time <80ms    6. Kinematic Detachment Guard (KinematicGuard.kt)
       │    Earcon + TTS)      7. Stage 2 TCN 208d Multi-Scale Inference & Binary FP Rejector (TcnModelRunner.kt)
       │                       8. Dual-Path Sweep Gate (+ Non-Bat Glance Mitigation) & BAT_HANDLE 3D AHRS Glance Disambiguation
                               9. → Atomic Swap into Room DB v12 (57 columns, auto-healing) → Compose UI
```

---

## ⌚ Watch Sensor Recording (TrackerService)

The watch no longer classifies shots. Its sole job is high-fidelity sensor recording and ZIP delivery with `syncWakeLock` protection and 3-attempt retry handover.

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
| `50hz_watch` | 50Hz | No | Watch-only sessions (`NONE`) |
| `50hz_watch_polar` | 50Hz | Yes | Watch + Polar Verity Sense (`WRIST` or `BAT_HANDLE`) |
| `100hz_watch_polar` | 100Hz | Yes | High-frequency watch + Polar (`WRIST` or `BAT_HANDLE`) |

---

## 📱 Phone-Side Batch Processing (PhoneSwingDetector.kt)

Triggered by `DataSyncListenerService` after unzipping the watch session ZIP, guarded by a single-flight per-innings `Mutex`.

```
1. LOAD       Binary sensor files → FloatArray streams (WatchAcc, WatchGyro, WatchRot)
2. LOAD       Polar BLE stream → polarAcc[], polarGyro[] + PolarMountMode (WRIST vs BAT_HANDLE)
3. ALIGN      Paired gyro peak regression / 1D cross-correlation → watchToPolarMs() drift correction
4. STAGE 1    Facing Up Stance Detection (facing_up_detector.onnx, dynamic batch 256, high=0.55, low=0.35, surge=1.8, sustain=200ms)
5. ANCHOR     4.0s single-shot stance peak anchoring (T_peak = argmax(||omega||))
6. ORIENT     3D Bat Orientation AHRS (OrientationAhrs.kt) → attitude, blade pitch, face roll, swing yaw
7. GUARD      Kinematic Detachment Guard (KinematicGuard.kt) → catches sensor tumble / separation (contiguous Δt ≤ 15ms)
8. STAGE 2    28-channel normalization + TCN inference (tcn_ultimate_baseline.onnx via TcnModelRunner.kt) with 208d multi-scale impact-core pooling & binary false-positive rejection (P(no_shot) >= 0.35)
9. GATING     Dual-Path Sweep Gate (with Non-Bat upright Glance mitigation) + Mount-Aware BAT_HANDLE Consistency Gate (Rule 1 Vertical Bat Guard + 3D AHRS Swing Yaw & Axial Roll Glance Disambiguation)
10. STORE     InningsEvent (57 columns) → Atomic transaction in Room DB v12 (with auto-repairing onOpen guard) → Compose UI
```

---

## 🎧 Real-Time In-Ear Biomechanical Coaching (`coaching/`)

Runs live during batting sessions inside `PolarSenseService` when a Polar Verity Sense is connected:
- **[LiveKinematicCoach.kt](file:///Users/neilkloot/Code/CricketBattingTracker/app/src/main/java/com/mrpeel/cricketbattingtracker/coaching/LiveKinematicCoach.kt)**: Evaluates a strictly bounded `[-220ms, 0ms]` pre-impact ring buffer upon impact detection ($A_{\text{mag}} > 10\text{g}$, $\omega > 5.5\text{ rad/s}$, 1800ms cooldown). Diagnoses 7 shot-invariant `BAT_HANDLE` flaws (`EARLY_PEAK_DECELERATION`, `STALLED_REACH_PUSH`, `MID_SWING_PLANE_LOOP`, `OUT_OF_PLANE_WIPE`, `LATE_WRIST_RESCUE`, `IMPACT_FACE_TWIST`, `OVERSWING_LOSS_OF_SHAPE`) and 3 `WRIST` flaws.
- **[EarconAudioPlayer.kt](file:///Users/neilkloot/Code/CricketBattingTracker/app/src/main/java/com/mrpeel/cricketbattingtracker/coaching/EarconAudioPlayer.kt)**: Procedural 22.05 kHz 16-bit PCM synthesizer generating 10 distinct failure earcons + 1 crystal chime in memory via `AudioTrack(MODE_STATIC)` (<5ms latency).
- **[LiveCoachingTtsManager.kt](file:///Users/neilkloot/Code/CricketBattingTracker/app/src/main/java/com/mrpeel/cricketbattingtracker/coaching/LiveCoachingTtsManager.kt)**: Schedules post-impact audio ($T+0..300\text{ms}$ silence for bat-ball crack, $T+300..520\text{ms}$ earcon, $T+550..1050\text{ms}$ 2-syllable TTS cue at $1.25\times$ speed, $T+1100\text{ms}+$ mic open for narration) across 3 progressive training stages (`STAGE_1_CALIBRATION`, `STAGE_2_FLOW_STATE`, `STAGE_3_SILENT_DIAGNOSTIC`).
- Full biomechanical specifications and thresholds are documented in [docs/biomechanical_coaching_reference.md](file:///Users/neilkloot/Code/CricketBattingTracker/docs/biomechanical_coaching_reference.md).

---

## 🤖 Machine Learning Model Architecture

### Primary Production Model: BatPlaneGeometryThreeFamilyTCN (`tcn_ultimate_baseline.onnx`)
- **Backbone**: 10-layer Dilated Temporal Convolutional Network with non-causal padding and 208-dimensional multi-scale impact-core feature pooling:
  - Core L5 [16d], Core L7 [64d], Proj Core L10 [64d] (sliced over $\pm 175$ frames / `[849, 1199]` around impact peak), combined with Global L7 [64d] context: $16 + 64 + 64 + 64 = 208\text{d}$.
- **Heads**:
  - `head_reject` (Binary Rejection MLP: $208\text{d} \rightarrow 64\text{d} \rightarrow 2\text{d}$): Learned false-positive rejection ($P(\text{no\_shot}) \ge 0.35$).
  - `head_family` (Macro Family Gate: $208\text{d} \rightarrow 64\text{d} \rightarrow 3\text{d}$): Vertical (0), Cross-Bat (1), Floor/Sweep (2).
  - `head_sub0` (Vertical Sub-Classifier: $208\text{d} \rightarrow 64\text{d} \rightarrow 4\text{d}$): `DRIVE/DEFENCE`, `POWER DRIVE`, `GLANCE/FLICK`, `DEFLECTION/GUIDE`.
  - `head_sub1` (Cross-Bat Sub-Classifier: $208\text{d} \rightarrow 64\text{d} \rightarrow 2\text{d}$): `PULL/HOOK/SLOG`, `CUT/PUNCH`.
- **Soft-Routing & Closed-Form Sub-Head Recovery**:
  - Power Drive: $\text{effective\_pd\_fam} = p_{\text{fam}}[0] + 0.85 \cdot p_{\text{fam}}[1]$ (allows high angular momentum and wrist roll without cross-bat collapse).
  - Closed-form quadratic inversion recovers exact $P_{\text{sub0}}(\text{Glance})$ and $P_{\text{fam}}(\text{Sweep})$ from the 9-class post-softmax probabilities at the center frame $t_{\text{mid}}$ for downstream mount-aware Glance/Flick disambiguation.
- **Training Strategy**: Joint 9-class `NLLLoss` + cross-family Power Drive suppression + hierarchical sub-head loss, trained with on-the-fly kinematic augmentation ($\pm 18$ frame jitter, scaling, noise, 25% Polar channel dropout) and layer-wise discriminative learning rates (`1.5e-4` on L1–7, `5e-4` on L8–10 + Heads).
- **Normalization**: 28-channel median/MAD normalization stats defined in `app/src/main/assets/models/tcn_norm_stats.json`.
- **Runtime Engine**: [TcnModelRunner.kt](file:///Users/neilkloot/Code/CricketBattingTracker/app/src/main/java/com/mrpeel/cricketbattingtracker/ml/TcnModelRunner.kt) executing ONNX opset 18 via Microsoft ONNX Runtime Android SDK with deterministic tensor lifecycle closing.

### Secondary / Quality Classifiers: 30-Feature Random Forest (`GeneratedForest.kt`)
- Used for shot quality prediction (`good`, `poor`, `miss`, `edge` via `GeneratedTopQualityForest` / `GeneratedDualQualityForest`) and legacy baseline comparisons. Transpiled via `pipelines/generate_kotlin_forest.py`.

---

## 🐍 Python Pipeline (`pipelines/`)

| Script | Role |
|---|---|
| `automate_pipeline.py` (root) | Pulls watch + Polar sessions via ADB, transcribes audio narration via Gemini/Deepgram, solves 2D clock drift alignment, and auto-triggers `reprocess_sessions.py`. |
| `build_unified_dataset.py` | 423 Hz grid resampling, Tier 3 impact peak alignment ($R^2 > 0.9999$), and mount-aware channel routing (`p_*` vs `b_*`) into unified Parquet files. |
| `reprocess_session_orientations.py` | Calibrates BLE batching latency (0.25s–0.68s), runs `OrientationAhrs` and `KinematicGuard` across sessions, and backfills continuous `p_rot_qx..w` and aligned `b_acc_*`/`b_gyro_*` into Parquets and `ground_truth_aligned.csv`. |
| `reprocess_sessions.py` | Rebuilds the 57-column Room v12 SQLite database (`scratch/cricket_tracker_database.db`) from processed ground-truth/TCN outputs and pushes it to the connected Android phone. |
| `telemetry_engine.py` | Core Python Stage 1 + Stage 2 TCN inference engine, closed-form sub-head recovery, and mount-aware biomechanical consistency gates (1:1 parity with `TcnModelRunner.kt`). |
| `train_and_evaluate_full_scorecard.py` | **Master TCN Training & Authoritative Scorecard** — Trains `BatPlaneGeometryThreeFamilyTCN` on stratified splits (`dataset_splits.json`), evaluates the 12-session Holdout Test Set & Clean Benchmark, writes `full_dataset_training_scorecard.md`, and exports `tcn_ultimate_baseline.onnx` (`dynamo=False`). |
| `test_ahrs_and_guard.py` | Unit test suite for Python 3D AHRS and Kinematic Detachment Guard. |

---

## 📂 Workspace Layout

```
├── AGENTS.md                       # Root agent rules & system invariants
├── .agents/                        # Progressive-disclosure docs & workspace skills
│   ├── ACTIVE_CONTEXT.md           # Active phase, recent backlog (B-110+), current benchmark
│   ├── ARCHITECTURE.md             # System architecture & pipeline reference
│   ├── LEARNINGS.md                # Domain-indexed invariants & failure traps
│   ├── change_logfile.md           # Full feature archive (B-001 through B-116)
│   ├── archive/LEARNINGS_ARCHIVE.md # Historical post-mortems (#1 through #207)
│   └── skills/                     # Auto-discovered Antigravity procedural skills
├── app/                            # Android companion phone app
│   └── src/main/java/.../
│       ├── coaching/               # LiveKinematicCoach, EarconAudioPlayer, LiveCoachingTtsManager
│       ├── data/                   # Room DB v12 (AppDatabase, InningsEvent [57 cols])
│       ├── ml/                     # TcnModelRunner, OrientationAhrs, KinematicGuard, GeneratedForest
│       ├── services/               # DataSyncListenerService, PhoneSwingDetector, PolarSenseService
│       └── ui/                     # Compose screens, BiomechanicalUiMapper, Playbook cards
├── wear/                           # Wear OS watch app
│   └── src/main/java/.../
│       ├── ml/                     # SwingDetector (timing reference), GeneratedForest
│       └── services/               # TrackerService (7 sensors → .bin.gz + ZIP sync)
├── pipelines/                      # Python ML, AHRS & database reprocessing scripts
├── docs/                           # Biomechanical coaching reference & ML reports
│   └── biomechanical_coaching_reference.md
├── full_dataset_training_scorecard.md # Authoritative TCN holdout & benchmark scorecard
└── automate_pipeline.py            # End-to-end ADB pull, transcription & alignment orchestrator
```

---

## 🔗 Key Code Linkages

### Phone App (`:app`)
- **[PhoneSwingDetector.kt](file:///Users/neilkloot/Code/CricketBattingTracker/app/src/main/java/com/mrpeel/cricketbattingtracker/services/PhoneSwingDetector.kt)**: Offline batch pipeline — binary load $\rightarrow$ Polar align $\rightarrow$ Stage 1 stance $\rightarrow$ 3D AHRS $\rightarrow$ Kinematic Guard $\rightarrow$ Stage 2 TCN $\rightarrow$ atomic Room v12 swap.
- **[TcnModelRunner.kt](file:///Users/neilkloot/Code/CricketBattingTracker/app/src/main/java/com/mrpeel/cricketbattingtracker/ml/TcnModelRunner.kt)**: Stage 1 & Stage 2 ONNX inference runner, 208d impact-core pooling, `head_reject` gating, closed-form sub-head inversion, and mount-aware consistency gates.
- **[OrientationAhrs.kt](file:///Users/neilkloot/Code/CricketBattingTracker/app/src/main/java/com/mrpeel/cricketbattingtracker/ml/OrientationAhrs.kt)** & **[KinematicGuard.kt](file:///Users/neilkloot/Code/CricketBattingTracker/app/src/main/java/com/mrpeel/cricketbattingtracker/ml/KinematicGuard.kt)**: 3D bat/wrist attitude estimation and sensor detachment detection.
- **[LiveKinematicCoach.kt](file:///Users/neilkloot/Code/CricketBattingTracker/app/src/main/java/com/mrpeel/cricketbattingtracker/coaching/LiveKinematicCoach.kt)** & **[EarconAudioPlayer.kt](file:///Users/neilkloot/Code/CricketBattingTracker/app/src/main/java/com/mrpeel/cricketbattingtracker/coaching/EarconAudioPlayer.kt)**: Real-time pre-impact flaw diagnosis and procedural PCM acoustic feedback.
- **[AppDatabase.kt](file:///Users/neilkloot/Code/CricketBattingTracker/app/src/main/java/com/mrpeel/cricketbattingtracker/data/AppDatabase.kt)** & **[InningsEvent.kt](file:///Users/neilkloot/Code/CricketBattingTracker/app/src/main/java/com/mrpeel/cricketbattingtracker/data/InningsEvent.kt)**: Room v12 schema (57 columns) with self-healing `onOpen` integrity guard.

### Watch App (`:wear`)
- **[TrackerService.kt](file:///Users/neilkloot/Code/CricketBattingTracker/wear/src/main/java/com/mrpeel/cricketbattingtracker/services/TrackerService.kt)**: 7 sensor streams $\rightarrow$ `.bin.gz` + session ZIP via GMS `ChannelClient` with `syncWakeLock`.
