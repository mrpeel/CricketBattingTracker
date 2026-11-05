# Active Context: Pitch Analytix Pro

This file defines the current system objectives, active technical architecture summary, recent feature backlog (`B-110`+), current benchmark state, and verification procedures. For older completed features (`B-001` through `B-116`), consult [.agents/change_logfile.md](file:///Users/neilkloot/Code/CricketBattingTracker/.agents/change_logfile.md).

---

## 🎯 System Objectives
* **Active Phase**: Multi-Tier 10-Layer TCN Telemetry, 3D Bat Orientation AHRS & Real-Time In-Ear Biomechanical Coaching
* **High-Level Vision**: Pitch Analytix Pro is a professional-grade cricket training companion utilizing Wear OS IMU sensors, Polar Verity Sense 423 Hz bat/wrist telemetry, offline ONNX TCN inference, 3D state-gated AHRS bat reconstruction, and sub-80ms real-time acoustic/TTS coaching.
* **"The Digital Pavilion" UI Spec**:
  * **Background**: `#000000` (True Black for OLED screen battery conservation) / `#001B3D` (Deep Navy accents).
  * **Primary Color**: `#58FF63` (Neon Green — High visibility, active tracking status).
  * **Secondary Color**: `#BCD2FE` (Light Blue — Secondary metrics and averages).
  * **Typography**: `Space Grotesk` (Modern, geometric, glanceable).
  * **Roundness**: `Round Four` (Circular watch-optimized shapes).

---

## 🛠️ Technical Approach
* **Wear OS Smartwatch (`:wear`)**: Runs a foreground tracking service ([TrackerService.kt](file:///Users/neilkloot/Code/CricketBattingTracker/wear/src/main/java/com/mrpeel/cricketbattingtracker/services/TrackerService.kt)) with a partial wake lock to record 7 raw sensor streams (`WatchAccelerometer`, `WatchGyroscope`, `WatchGravity`, `WatchGameOrientation`, `WatchOrientation`, `WatchMagnetometer`, `WatchSteps`) in GZIP-compressed fixed-width binary format (`.bin.gz`). When the session ends, `TrackerService` holds `syncWakeLock`, packages the session into a ZIP archive, and transmits it to the phone via GMS `ChannelClient` (`/raw_session_data`) with automatic 3-attempt retry and pending-session recovery.
* **Companion Android App (`:app`)**:
  * **Live Session & In-Ear Coaching**: [PolarSenseService.kt](file:///Users/neilkloot/Code/CricketBattingTracker/app/src/main/java/com/mrpeel/cricketbattingtracker/services/PolarSenseService.kt) ingests 423 Hz Polar Verity Sense BLE IMU streams (`WRIST` or `BAT_HANDLE` mount mode) and feeds [LiveKinematicCoach.kt](file:///Users/neilkloot/Code/CricketBattingTracker/app/src/main/java/com/mrpeel/cricketbattingtracker/coaching/LiveKinematicCoach.kt), which diagnoses 7 shot-invariant biomechanical flaws within `[-220ms, 0ms]` pre-impact and triggers sub-5ms procedural PCM earcons ([EarconAudioPlayer.kt](file:///Users/neilkloot/Code/CricketBattingTracker/app/src/main/java/com/mrpeel/cricketbattingtracker/coaching/EarconAudioPlayer.kt)) and 2-syllable Bluetooth TTS cues ([LiveCoachingTtsManager.kt](file:///Users/neilkloot/Code/CricketBattingTracker/app/src/main/java/com/mrpeel/cricketbattingtracker/coaching/LiveCoachingTtsManager.kt)).
  * **Offline Batch Inference**: [DataSyncListenerService.kt](file:///Users/neilkloot/Code/CricketBattingTracker/app/src/main/java/com/mrpeel/cricketbattingtracker/services/DataSyncListenerService.kt) acquires a partial wake lock, unzips the watch session, and invokes [PhoneSwingDetector.kt](file:///Users/neilkloot/Code/CricketBattingTracker/app/src/main/java/com/mrpeel/cricketbattingtracker/services/PhoneSwingDetector.kt) under a single-flight per-innings `Mutex`. `PhoneSwingDetector` aligns Watch + Polar streams, runs Stage 1 Stance Detection (`facing_up_detector.onnx`), reconstructs 3D bat angles via [OrientationAhrs.kt](file:///Users/neilkloot/Code/CricketBattingTracker/app/src/main/java/com/mrpeel/cricketbattingtracker/ml/OrientationAhrs.kt), validates attachment via [KinematicGuard.kt](file:///Users/neilkloot/Code/CricketBattingTracker/app/src/main/java/com/mrpeel/cricketbattingtracker/ml/KinematicGuard.kt), runs Stage 2 10-layer TCN classification + binary FP rejection (`tcn_ultimate_baseline.onnx` via [TcnModelRunner.kt](file:///Users/neilkloot/Code/CricketBattingTracker/app/src/main/java/com/mrpeel/cricketbattingtracker/ml/TcnModelRunner.kt)), and atomically writes 57-column `InningsEvent` records to Room SQLite v12 ([AppDatabase.kt](file:///Users/neilkloot/Code/CricketBattingTracker/app/src/main/java/com/mrpeel/cricketbattingtracker/data/AppDatabase.kt)).
* **Python Automation & ML Pipeline (`pipelines/`)**: [automate_pipeline.py](file:///Users/neilkloot/Code/CricketBattingTracker/automate_pipeline.py) pulls watch + Polar session logs via ADB, transcribes audio narration via Gemini / Deepgram, aligns clock drift against IMU impact peaks, compiles 423 Hz unified Parquet files ([build_unified_dataset.py](file:///Users/neilkloot/Code/CricketBattingTracker/pipelines/build_unified_dataset.py)), and syncs processed ground truth back to the phone Room database ([reprocess_sessions.py](file:///Users/neilkloot/Code/CricketBattingTracker/pipelines/reprocess_sessions.py)). Model training and authoritative multi-tier scorecard evaluation run via [train_and_evaluate_full_scorecard.py](file:///Users/neilkloot/Code/CricketBattingTracker/pipelines/train_and_evaluate_full_scorecard.py).

---

## 📋 Recent Feature Backlog (`B-110` – `B-116`)
*(See [.agents/change_logfile.md](file:///Users/neilkloot/Code/CricketBattingTracker/.agents/change_logfile.md) for historical features `B-001` through `B-109`.)*

| Feature ID | Feature Name | Summary | Status | Verification |
|---|---|---|---|---|
| B-110 | Session Start Time Hierarchy & Mid-Session Bat Switch Reconciliation | Enforce 4-tier start-time hierarchy (`session_config.json` -> `latest_timeline.txt` -> regex -> mtime) across Python and Kotlin, fixing ~24 min sync-timestamp skew that overwrote mid-session bat switches. | **Completed** | 108 Android/Wear tests, 8/8 Python tests; verified 3-round bat partitioning in `session_2026-10-17_11-47-47`. |
| B-111 | Real-Time In-Ear Kinematic Coaching Engine & "Timing" Rebranding | Built sub-80ms Bluetooth TTS coaching (`LiveCoachingTtsManager`, `LiveKinematicCoach`), extracted first-class `edge` quality state across 325 historical edges, and rebranded UI "EFFICIENCY" to "TIMING". | **Completed** | 120/120 Android/Wear unit tests (`LiveKinematicCoachTest`), 8/8 Python tests, 16 KB aligned release APKs. |
| B-112 | Procedural Earcon Acoustic Synthesis Engine, 3-Stage Training System & Biomechanical Playbook UI | Built 22.05 kHz 16-bit PCM synth (`EarconAudioPlayer.kt`) with 10 failure earcons + 1 crystal chime (<5ms latency), post-impact audio timeline ($T+300\text{ms}$ earcon, $T+550\text{ms}$ cue), 3 coaching stages, and `BiomechanicalCoachingPlaybookCard.kt`. | **Completed** | 125/125 Android/Wear unit tests, 8/8 Python tests, 16 KB aligned release APKs. |
| B-113 | Historical Session Recovery, Pending State Resolution & Pipeline Auto-Sync | Resolved indefinite processing spinner on interrupted sessions, enhanced `InningsViewModel.retryLocalProcessing` to discover `temp_processing_*` / `temp_sync_polar_*`, and wired auto-DB push into `automate_pipeline.py`. | **Completed** | 96 sessions verified on physical device (`59011FDCR000R5`), 125/125 unit tests passed. |
| B-114 | Joint 9-Class Hierarchical Loss, Cross-Family Power Drive Calibration & Stratified Benchmark Rebalancing | Trained TCN with joint 9-class `NLLLoss` + cross-family PD suppression, on-the-fly kinematic augmentation (25% Polar dropout), automatic window cache metadata verification, and stratified 9-val / 12-holdout splits. | **Completed** | Holdout (12 sessions, 714 GT): 🏆 **92.44% Recall**, 🏆 **91.67% Precision**, 🏆 **92.05% F1**, 🏆 **84.09% Classification Accuracy** (`POWER DRIVE` 84.44%, `GLANCE/FLICK` 79.84%). |
| B-115 | Shot-Invariant Real-Time Kinematic Coaching Engine & Pre-Impact Windowing Fix | Replaced shot-guessing waterfall in `LiveKinematicCoach.kt` with 7 shot-invariant biomechanical diagnostics strictly within `[-220ms, 0ms]` pre-impact (`GYRO_TO_KMH = 3.4f`). Documented in `docs/biomechanical_coaching_reference.md`. | **Completed** | Eliminated 100% of false shot-specific calls and stale stance-tap triggers across 1,289 `BAT_HANDLE` shots; all unit tests passed. |
| B-116 | Single-Flight Per-Innings Mutex, Atomic DB Replacement & Processing UI Concurrency Guard | Added per-innings `Mutex` and `processingInnings: StateFlow<Set<Long>>` in `PhoneSwingDetector`, atomic `database.withTransaction { delete; insert }` replacement, and UI concurrency guards in `MainActivity.kt` / `InningsViewModel.kt`. | **Completed** | 124 Android unit tests passed, 8/8 Python AHRS & Guard tests passed. |
| B-117 | Shared Stage 3 JSON Rule Engine, Non-Bat Sweep Regression Fix & Jev Training-Pipeline Shadow Auditor | Centralised Stage 3 post-classification gates into `stage3_rules_config.json` (`v1.1.0`), `pipelines/stage3_rules.py`, and `Stage3RuleEngine.kt` (fixing Kotlin `w_grav_z` channel 14 index and disabling `non_bat_sweep_to_glance` which hurt 17 sweeps), plus integrated `pipelines/jev_auditor.py` into `train_and_evaluate_full_scorecard.py`. | **Completed** | Holdout (12 sessions, 714 GT): 🏆 **92.02% Recall**, 🏆 **92.28% Precision**, 🏆 **92.15% F1**, 🏆 **85.69% Classification Accuracy** (`SWEEP` 94.34%, `POWER DRIVE` 91.11%, `PULL/HOOK/SLOG` 88.19%); `Stage3RuleEngineParityTest` passed. |

---

## 🔖 Current Benchmark & System State
* **Authoritative Multi-Tier TCN Scorecard ([full_dataset_training_scorecard.md](file:///Users/neilkloot/Code/CricketBattingTracker/full_dataset_training_scorecard.md))**:
  * **Holdout Test Set (12 Stratified Sessions, 714 Physical GT Shots)**:
    * **Detection Recall**: 🏆 **92.02%** (657 / 714)
    * **Detection Precision**: 🏆 **92.28%** (657 / 712)
    * **Detection F1**: 🏆 **92.15%**
    * **Overall Classification Accuracy**: 🏆 **85.69%** (563 / 657) — `SWEEP`: 94.34%, `POWER DRIVE`: 91.11%, `PULL/HOOK/SLOG`: 88.19%, `DEFLECTION/GUIDE`: 85.94%, `GLANCE/FLICK`: 85.48%, `CUT/PUNCH`: 82.81%, `DRIVE/DEFENCE`: 81.11%.
  * **Clean Benchmark Total (91 Sessions, 5,287 Physical GT Shots)**:
    * **Global Recall**: 🏆 **89.99%** (4,758 / 5,287)
    * **Global Precision**: 🏆 **92.41%** (4,758 / 5,149)
    * **Global F1**: 🏆 **91.18%**
    * **Full Classification Accuracy**: 🏆 **93.30%** (4,439 / 4,758)
* **Live In-Ear Biomechanical Coaching ([docs/biomechanical_coaching_reference.md](file:///Users/neilkloot/Code/CricketBattingTracker/docs/biomechanical_coaching_reference.md))**:
  * 7 shot-invariant pre-impact (`[-220ms, 0ms]`) detectors active for `BAT_HANDLE` mode + 3 wrist-mode detectors, paired with 10 procedural 22.05 kHz PCM earcons and 2-syllable TTS motor cues across 3 progressive training stages.

---

## 🧪 Verification & Testing

### 1. Automated Unit Tests
* **Android & Wear OS Unit Tests**:
  ```bash
  ./gradlew :app:testDebugUnitTest :wear:testDebugUnitTest
  ```
  Covers `TcnModelRunner`, `PhoneSwingDetector`, `OrientationAhrs`, `KinematicGuard`, `LiveKinematicCoach`, `BiomechanicalUiMapper`, and `AppDatabaseMigrationTest` (including Room v12 schema self-healing and `reprocess_sessions.py` DDL parity).
* **Python AHRS & Kinematic Guard Unit Tests**:
  ```bash
  PYTHONPATH=pipelines python3 -m unittest pipelines/test_ahrs_and_guard.py
  ```

### 2. Authoritative Model Evaluation
* **Multi-Tier TCN Holdout & Full Dataset Scorecard**:
  ```bash
  python3 pipelines/train_and_evaluate_full_scorecard.py --eval-only
  ```
  Generates [full_dataset_training_scorecard.md](file:///Users/neilkloot/Code/CricketBattingTracker/full_dataset_training_scorecard.md) and checks the Production Quality Gate.

### 3. Release Packaging & Physical Deployment
* **Assemble 16 KB Page-Aligned Release APKs**:
  ```bash
  ./gradlew :app:assembleRelease :wear:assembleRelease
  ```
* **Deploy to Connected Watch & Phone**:
  ```bash
  ./deploy_physical.sh
  ```
