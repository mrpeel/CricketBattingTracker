# Active Context: Pitch Analytix Pro

This file defines the system objectives, feature backlog catalog, active technical approach, and verification methods.

---

## 🎯 System Objectives
*   **Active Phase**: Shot Detection Reliability — Random Forest Integration
*   **High-Level Vision**: Pitch Analytix Pro is a professional-grade cricket training companion utilizing Wear OS IMU sensors, local kinematics heuristics, mobile dashboards, and cloud transcription pipelines.
*   **"The Digital Pavilion" UI Spec**:
    *   **Background**: `#000000` (True Black for OLED screen battery conservation) / `#001B3D` (Deep Navy accents).
    *   **Primary Color**: `#58FF63` (Neon Green - High visibility, active tracking status).
    *   **Secondary Color**: `#BCD2FE` (Light Blue - Secondary metrics and averages).
    *   **Typography**: `Space Grotesk` (Modern, geometric, glanceable).
    *   **Roundness**: `Round Four` (Circular watch-optimized shapes).

---

## 🛠️ Technical Approach
*   **Wear OS Smartwatch**: Runs a foreground tracking service (`TrackerService`) with a partial wake lock to guarantee continuous raw sensor logging at `SENSOR_DELAY_FASTEST` speed (up to 15 standard Wear OS physical and virtual sensors). When the session ends, the watch packages the entire session directory into a single ZIP file and syncs it to the companion phone app using GMS `ChannelClient` under the `/raw_session_data` path.
*   **Companion Android App**: Uses a Room SQLite database for offline storage. Receives raw sensor ZIP files via GMS `ChannelClient`, unzips them, and runs an offline batch analysis processor (`PhoneSwingDetector`). This performs clock alignment matching, peak impact detection, stance look-back checking, 30-feature extraction (incorporating linear acceleration force features), Dual-Model Random Forest classification (routing to `GeneratedTopForest` or `GeneratedDualForest` depending on Polar presence), and video clipping entirely offline on the phone.
*   **Python Automation Pipeline**: ADB automation (`automate_pipeline.py`) pulls consolidated watch + Polar session logs directly from the phone companion app's sync folder. Transcribes audio narration using the Gemini API and Snaps transcripts to maximum gyroscope magnitude peaks.

---

## 📋 Feature Catalog & Backlog

| Feature ID | Feature Name | Description | Status | Verification Method |
|---|---|---|---|---|
| B-001 | Pull Shot Precision | Reduce false positive rate on Pull shot classification | Backlog | `SwingDetectorGroundTruthTest` |
| B-002 | Cover Drive Recall | Improve recall of Cover Drive shots | Backlog | `SwingDetectorGroundTruthTest` |
| B-003 | Speed Calibration | Fix speed anomalies on low-speed Cover Drives/Flicks | Backlog | `SwingDetectorGroundTruthTest` |
| B-004 | Active Watch Data | Implement active sensor logging for short-off-side/full-length | Backlog | Session collection check |
| B-013 | Power Shot Precision | Reduce POWER SHOT → PULL/HOOK misclassification. Session-2026-06-15 was ~90% power shots and scored only 40% accuracy, exposing severe underrepresentation of this class in training data. Retrain after collecting more power shot sessions. | Backlog | `SwingDetectorGroundTruthTest` |
| B-023 | Stance Gate Staggering & Timing Sweep | Implement Option 3 stance duration compression and twitch injection sweeps under stressed stance simulation. | **Completed** | Grid sweep successfully completes in < 2 mins via 50x precomputation cache |
| B-024 | TinyML Stance Gate | Compile and deploy depth-4 Decision Tree classifier into SwingDetector.kt stance gate, reducing FPs by 22% globally. | **Completed** | Simulation evaluations showing F1 improvement to 0.3948 on stressed dataset |
| B-025 | 6x Synthetic Shot Classifier Augmentation | Scale training variants per shot to 90 and cap to 18x, retraining Random Forest to 86.22% CV accuracy. | **Completed** | Scikit-learn cross validation metrics and watch transpilation successful |
| B-026 | Video Capture Config & Viewfinder | Integrate camera facing flip, linear zoom control slider, target frame rate selector, and live preview viewfinders. | **Completed** | Gradle assembleDebug builds successfully and camera parameter bindings validated |
| B-027 | Phone-Bound Batch Processing | Remove real-time detection on watch and move facing up, stance lock, feature extraction, and RF classification entirely to the Phone companion app. | **Completed** | Local file unzipping, database write checks, and Python pipeline phone pull verification |
| B-028 | Base Data Transparency & Telemetry Overhaul | Add explicit phase start/end nanoseconds and seconds, export all 26 sensor features, calculate physical efficiency, dynamic reaction time, and downswing-constrained Polar peak matching. | **Completed** | Regenerated ground_truth_aligned.csv and combined_ground_truth_aligned.csv with 57 columns and eliminated post-shot tap artifacts |
| B-029 | Deepgram Ground Truth Re-alignment & Retraining | Rebuild all 42 session ground truth files using Deepgram Nova-3 narrations, retrain and transpile Dual-Model Random Forests to Kotlin. | **Completed** | 100% session alignment success (4,070 GT rows), 95% accuracy on 100Hz Watch+Polar, unit tests passed |
| B-030 | Linear Acc Features & 30-Feature Expansion | Add s1_acc_mag, s3_acc_peak, s1_bottom_acc_mag, s3_bottom_acc_peak to SwingFeatures and PhoneSwingDetector to support force proxies. | **Completed** | SwingFeatures data structure updated to 30 fields, and PhoneSwingDetector values validated |
| B-031 | 423Hz Unified Dataset & 100% Impact Alignment | Build 44 parquet sessions at 423 Hz with world-frame quaternion rotation vectors and 100% Tier 3 Impact-Peak alignment ($R^2 > 0.9999$). | **Completed** | 100% alignment across 44 sessions, 439 impact anchors matched on holdout session |
| B-032 | 8-Run Systematic Ablation Study | Evaluate Downsampling (200Hz), Derived Data (+Jerk), and Multi-Task Dual-Head Network independently, in pairs, and all 3 combined. | **Completed** | Downsampling to 200Hz proved statistically significant ($53.76\%$). Run A+C achieved 54.01% classification accuracy. |
| B-033 | Model Architecture Benchmark Suite | Benchmark 5 neural network backbones (TCN, 1D ResNet, Conv-LSTM, InceptionTime, Temporal Transformer) on continuous IMU streams. | **Completed** | Conv-LSTM achieved 74.52% candidate window classification accuracy; Transformer achieved 65.69%. |
| B-034 | Decoupled 2-Stage TCN + Conv-LSTM Pipeline | Decouple 423Hz TCN Detection Engine (92.1% recall) from 1.8s Conv-LSTM Window Classifier (48.15% accuracy). | **Completed** | Captured 52 physical shots correctly (45.61% coverage), outperforming production Random Forest by +73% with zero false alarms. |
| B-035 | Dual Holdout Retraining & Scorecard | Retrain Advanced TCN model holding out `session_2026-07-18_13-44-09` & `session_2026-08-01_10-18-20`. | **Completed** | Evaluated 47 physical sessions: 91.7% Recall, 84.1% Accuracy across full dataset, exported ONNX to Android app. |
| B-036 | Production ONNX Quality Gate & Holdout Optimization | Enforce strict Precision $\ge 75\%$ Quality Gate on ONNX export; deploy Jitter Augmentation ($\pm 30\text{ms}$) & Asymmetric Focal Loss (3.0x `POWER DRIVE` boost). | **Completed** | Passed Quality Gate (Precision: 78.3%, Holdout Acc: 53.7%, PULL/HOOK holdout acc: 46.7%, ONNX updated). |
| B-037 | Dynamic Inverse-Frequency Loss Weighting | Replace manual scalar multipliers with standard dynamic inverse-frequency weighting ($N / (K \cdot N_c)$). | **Completed** | Passed Quality Gate (Precision: 78.3%). Boosted POWER DRIVE holdout accuracy from 10.5% to 42.1% (+31.6%), exported ONNX. |


---

## 🔖 Current Session State (session-2026-07-05_16-27-16)
*   **Session Directory**: `/Users/neilkloot/Code/Batting Sensor Stats/live_watch_sessions/session-2026-07-05_16-27-16`
*   **Audio File**: `narration_20260705_162710.m4a`
*   **Status**: Successfully aligned session using the multi-point regression sync-tap detector. Matched all 3 rounds of sync taps, calculating a starting offset of -18.828s and a drift rate of +0.0176452 (+1.76% speed correction). Verified that late-session shots align perfectly.



---

## 🧪 Verification & Testing

### 1. Automated Verification
*   **Kinematics Unit Tests**: Run `SwingDetectorTest` to verify math helpers, ring buffer logic, and state transitions.
*   **Ground Truth Scorecard**: Run [SwingDetectorGroundTruthTest.kt](file:///Users/neilkloot/Code/CricketBattingTracker/wear/src/test/java/com/mrpeel/cricketbattingtracker/ml/SwingDetectorGroundTruthTest.kt) to generate the performance scorecard against physical batting session datasets.

### 2. Manual E2E Simulation
*   **Launch Emulators**: Run `test/start_emulators.sh` to boot Phone and Wear AVD targets.
*   **Visible E2E Script**: Execute `test/run_visible_e2e.sh` to compile, deploy both apps, simulate shots, and verify synchronization.

### 3. Live Session Verification
*   Deploy `wear` debug APK to physical watch: `./deploy_physical.sh`
*   Record a session with `ENABLE_RAW_LOGGING=true` to get all 7 CSV files including `WatchGameOrientation.csv` and `WatchSteps.csv`
*   Run `automate_pipeline.py` and compare detection count to narrated shot count
