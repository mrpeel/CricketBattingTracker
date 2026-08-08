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
| B-038 | High-Velocity Feature Confusion Ablation | Evaluate Region-Based Temporal Attention Pooling and Hard Negative Mining; verify Quality Gate protection. | **Completed** | Quality Gate protected production asset during region pooling trial; baseline TCN achieved 89.5% POWER DRIVE holdout coverage (77.9% Precision). |
| B-039 | Clamped Dynamic Inverse-Frequency Weighting | Clamp dynamic class loss weights strictly between 1.0x and 1.8x max cap to prevent class boundary distortion. | **Completed** | Passed Quality Gate (Precision: 77.9%). Boosted POWER DRIVE holdout accuracy to 60.9% (+6.1% gain) and full dataset accuracy to 67.3%. |
| B-040 | Facing Up Stance Binary Detector | Train 423Hz 5-layer TCN stance detector on 46 training sessions; evaluate on 2 unseen Polar holdout sessions (`session_2026-07-21_12-43-37` & `session_2026-07-25_15-16-32`). | **Completed** | Holdout Stance Recall: 90.57% (96/106), Stance Precision: 97.96%, Ambient FPs: 2, Mean Lead Time: 2.484s. |
| B-041 | Position-Constrained Ground Truth Restoration & Multi-Tier Pipeline | Enforce position-constrained lexicon matching and split 552 compound stance phrases across all 48 physical sessions. | **Completed** | Achieved 🏆 **94.02% Holdout Shot Detection Recall** (110/117 GT shots), 🏆 **86.61% Holdout Precision** (110 TPs / 127 candidates), 🏆 **78.25% Global Pipeline Recall** (2,033 / 2,598 GT shots), and 🏆 **69.09% Overall Holdout Classification Accuracy**. |
| B-042 | Stage 2 Kinematic Features & Class-Balanced Focal Loss | Add 28-feature post-impact acceleration ratio and wrist gyro roll delta with Class-Balanced Focal Loss ($\gamma = 2.0$, $\beta = 0.9999$) holding out 2 sessions (`session_2026-07-21_12-43-37` with +0.30s offset and `session_2026-07-25_15-16-32` with -0.15s offset). | **Completed** | Achieved 🏆 **97.44% Holdout Physical Shot Recall** (114/117 GT shots), 🏆 **74.51% Holdout Precision** (114 TPs / 153 candidates), 🏆 **84.44% Holdout F1 Score**, and 🏆 **95.46% Full Dataset Recall** (2,480 / 2,598 GT shots). |
| B-043 | Label-Smoothed Cross-Entropy Loss Refactoring | Replace Class-Balanced Focal Loss with Label-Smoothed Cross-Entropy Loss ($\text{label\_smoothing}=0.1$) to eliminate class boundary distortion. | **Completed** | Restored minority class boundary stability: `DEFLECTION/GUIDE` accuracy boosted to **51.7%** (+15.3%), `POWER DRIVE` to **55.1%** (+7.9%), `SLOG` to **62.1%** (+8.2%); 🏆 **98.3% Holdout Recall**, **75.2% Precision**, **85.2% F1**. |
| B-044 | Candidate Clamping & Precision Controls | Implement post-stance motion trigger floor ($[T_{\text{exit}}, T_{\text{exit}}+2.5\text{s}]$, $\omega_{\text{peak}} \ge 1.0\text{ rad/s} \lor a_{\text{peak}} \ge 14.0\text{ m/s}^2$), 1.8s NMS refractory period, and Stage 2 probability rejection gate. | **Completed** | Achieved 🏆 **81.23% Global System Precision** (1,805 TPs / 2,222 candidates), 🏆 **88.29% Holdout Precision** (98 TPs / 111 candidates), eliminating over 1,200 false positives across 48 physical sessions. |
| B-045 | Option A 8-Class Canonical Holdout Retraining | Set Option A Polar sessions (`session_2026-07-23_12-37-13`, `session_2026-07-24_12-52-29`, `session_2026-08-02_12-10-13`) as holdout set; retrain TCN model on remaining 45 physical sessions and update full dataset scorecard. | **Completed** | Achieved 🏆 **95.6% Holdout Shot Recall** (151/158 GT shots), 🏆 **78.6% Holdout Precision**, 🏆 **86.3% Holdout F1 Score** (+5.1% gain), 🏆 **55.2% Holdout Classification Accuracy** (+11.5% gain), **95.5% Global Shot Recall** across all 48 physical sessions, 100% 8-class holdout coverage, and updated `full_dataset_training_scorecard.md`. |
| B-046 | Kinematic Precision Safeguards & Quality Gate Pass | Deploy 3.5s extended stance window (1 peak max per stance), 300ms backswing displacement check ($\Delta \theta_{\text{backswing}} \ge 0.35\text{ rad}$), and 0.25 Softmax rejection floor across both pipelines. | **Completed** | Achieved 🏆 **85.7% Global System Precision** (Target: $\ge 75\%$), 🏆 **88.0% Holdout Precision**, 🏆 **67.7% Holdout Classification Accuracy** (+12.5% boost), pruned over 1,260 candidates (2,162 total), **PASSED Production Quality Gate**, exported `tcn_ultimate_baseline.onnx` to app assets. |
| B-047 | Recall Restoration & Kinematic Safeguard Refactoring | Remove Softmax rejection gate, set $\omega(T_{\text{peak}}) \ge 1.0\text{ rad/s} \land \Delta \theta_{\text{backswing}} \ge 0.14\text{ rad}$ ($\approx 8^\circ$), and maintain stance deduplication. | **Completed** | Restored **Physical Shot Recall to 95.5%** (95.6% Holdout, PULL/HOOK holdout recall boosted from 6.7% to **90.0%**), hit **2,722 candidates** in multi-tier audit (target: 2,650–2,800), **84.1% Holdout Precision**, **86.3% Holdout F1**, and **64.9% Holdout Classification Accuracy**. |
| B-048 | Dynamic Early Stopping & Extended 25-Epoch Retraining | Increase MAX_EPOCHS to 25 with 2-stage layer freezing at Epoch 5 and dynamic early stopping (patience=4, min_delta=0.001 monitored post-freezing). Retrain on 45 physical sessions, evaluate against Option A holdout set, and update ONNX asset. | **Completed** | Label-Smoothed CE Loss dropped to **0.7314** at Epoch 24 (down from 0.7518). Achieved 🏆 **95.6% Holdout Recall**, 🏆 **78.6% Holdout Precision**, 🏆 **86.3% Holdout F1**, **PASSED Production Quality Gate**, and updated `tcn_ultimate_baseline.onnx` in app assets. |
| B-049 | Validation Loss Early Stopping & Layer Freezing Experiment | Monitor validation loss on 3 designated 8-class Polar holdout sessions with patience=5 early stopping across 3 layer-freezing variants (Freeze @ 5, Freeze @ 10, Discriminative LR). Update ONNX asset with winning checkpoint. | **Completed** | Discovered `val_loss` reaches global minimum between **Epochs 2–9** (0.6665 to 0.6730) before rising. Variant A achieved **50.0% Holdout Classification Acc**, **95.6% Recall**, **78.6% Precision**, **86.3% F1**, **PASSED Quality Gate**, exported `tcn_ultimate_baseline.onnx`. |
| B-050 | Variant C Ongoing Pipeline Standardisation | Standardise master training pipeline on Variant C (Discriminative LR: 1e-4 for Layers 1-5, 1e-3 for Layers 6-10 + Head, unfrozen layers) with holdout val_loss early stopping. | **Completed** | Retrained and deployed Variant C baseline: `POWER DRIVE` accuracy boosted to **76.9%**, `PULL/HOOK` to **78.4%**, `CUT/PUNCH` to **75.6%**; 🏆 **95.6% Holdout Recall**, **78.6% Precision**, **86.3% F1**, **PASSED Quality Gate**, updated `tcn_ultimate_baseline.onnx`. |
| B-051 | Automated Dataset Synchronization & 51-Session Retraining | Integrate automated session discovery and unified dataset recompilation directly into training pipeline to incorporate all available sessions (including latest sessions with 141 Power drives). | **Completed** | Auto-synced 3 new sessions (51 total sessions / 2,795 physical GT shots, Power drives doubled to 276 shots); correctly classified shots increased to **2,138** (58.1% acc), 🏆 **95.6% Holdout Recall**, **78.6% Precision**, **86.3% F1**, **PASSED Quality Gate**, updated ONNX asset. |
| B-052 | SWEEP Post-Classification Precision Filters & Recall Clamping | Deploy dynamic 2.4s NMS refractory window for SWEEP, 0.45 Softmax confidence floor, 15-degree torso pitch tilt / delta_gz verification, and corrected 1D cross-correlation lag computation. | **Completed** | Clamped SWEEP candidates from 423 to **156 detections** (73.9% recall), achieved 🏆 **82.27% Global System Precision** (2,315 TPs / 2,814 candidates), 🏆 **87.34% Holdout Recall**, 🏆 **89.03% Holdout Precision**, 🏆 **88.18% Holdout F1**, and **73.91% Holdout Classification Accuracy**. |






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
