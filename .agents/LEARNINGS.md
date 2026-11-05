# Active Learnings & System Invariants: Pitch Analytix Pro

This document is a fast-lookup engineering reference of **active architectural invariants, train–serve parity rules, and resolved failure traps** across the Pitch Analytix Pro codebase.
For detailed chronological post-mortems and historical experiment logs (`#1` through `#207`), see [.agents/archive/LEARNINGS_ARCHIVE.md](file:///Users/neilkloot/Code/CricketBattingTracker/.agents/archive/LEARNINGS_ARCHIVE.md).

---

## 🗄️ 1. Room SQLite Database & Reprocessing Invariants

### 1.1 Room v12 Schema & Identity Hash Parity (`AppDatabase.kt` ↔ `reprocess_sessions.py`)
* **The Trap**: `pipelines/reprocess_sessions.py` builds/updates the SQLite database offline and pushes it to the phone. If `reprocess_sessions.py` writes the Room v12 identity hash (`36946e68af413e8cc2fca0555e69b534`) into `room_master_table` without matching the exact 57-column DDL of `innings_events`, Room skips migration AND validation on startup, crashing immediately with `IllegalArgumentException: column '...' does not exist` when `InningsEventDao` runs `SELECT *`.
* **Invariants**:
  1. `InningsEvent.kt`, `AppDatabase.kt` (`MIGRATION_11_12` + `ensureSchemaIntegrity`), and `pipelines/reprocess_sessions.py` (`CREATE TABLE` and `INSERT INTO innings_events`) must maintain exact 57-column parity and identity hash `36946e68af413e8cc2fca0555e69b534`.
  2. `AppDatabase.kt` includes a self-healing `onOpen` guard (`ensureSchemaIntegrity`) that inspects `PRAGMA table_info(innings_events)` and runs `ALTER TABLE` for any missing columns before DAOs execute.
  3. Always run `./gradlew :app:testDebugUnitTest --tests "com.mrpeel.cricketbattingtracker.data.AppDatabaseMigrationTest"` after touching any database column or `reprocess_sessions.py`.

### 1.2 Single-Flight Per-Innings Concurrency & Atomic Timeline Replacement (`PhoneSwingDetector.kt`)
* **The Trap**: `PhoneSwingDetector.processSession` can be triggered concurrently by `DataSyncListenerService` (when the watch ZIP arrives), `MainActivity` Session Details auto-recovery `LaunchedEffect`, and the manual "Retry Sync" button. Previously, deleting the innings timeline at the *start* of `processSession` and inserting minutes later caused overlapping runs to triplicate shots (e.g., 193 shots for 65 physical deliveries) while leaving the UI thinking the session was empty/unprocessed.
* **Invariants**:
  1. `PhoneSwingDetector` guards each innings with a per-innings `Mutex` (`tryLock`) and publishes in-flight IDs via `processingInnings: StateFlow<Set<Long>>`. Concurrent callers wait on the active run rather than re-running inference.
  2. Never delete an innings timeline before replacement events are ready. Build all output `InningsEvent` objects in memory first, then swap them inside a single `database.withTransaction { delete; insert start/shots/end }`.
  3. `MainActivity.kt` and `InningsViewModel.kt` observe `processingInnings` to show a progress spinner and suppress duplicate auto-recovery triggers.

### 1.3 Authoritative 4-Tier Session Start-Time Hierarchy
* **The Trap**: Wear OS `TrackerService` zips and transfers the session only *after* the session finishes (~15–25 minutes after start). Using the directory name (`session_YYYY-MM-DD_HH-mm-ss`, which reflects sync arrival time) as `session_start_ms` shifts all computed shot wall timestamps forward by ~24 minutes, placing every delivery after the final mid-session bat switch and overwriting all shots with the last bat used.
* **Invariant**: Both Python (`automate_pipeline.py`, `reprocess_sessions.py`, `build_unified_dataset.py`) and Kotlin (`PhoneSwingDetector.kt`, `DataSyncListenerService.kt`, `InningsViewModel.kt`) MUST resolve `session_start_ms` in strict priority order:
  1. `session_config.json` $\rightarrow$ `start_time_ms`
  2. `latest_timeline.txt` $\rightarrow$ `SYSTEM_START: Ts=`
  3. Directory name regex (`session_YYYY-MM-DD_HH-mm-ss`)
  4. Directory `mtime`

---

## 🧠 2. Stage 1 & Stage 2 TCN Inference & Train–Serve Parity

### 2.1 Bat-Mount Mode (`BAT_HANDLE`) Polar Channel Clamping
* **The Trap**: Stage 1 Stance Detection (`facing_up_detector.onnx`) and Stage 2 TCN wrist channels (`sensorMatrix[19..24]`: `p_acc_x..z`, `p_gyro_x..z`) were trained on trailing-wrist kinematics. Passing raw bat-handle accelerometer/gyroscope samples into channels `19..24` during `BAT_HANDLE` sessions collapses Stage 1 stance probabilities (dropping stance exits from 120 to 17).
* **Invariant**: When `polarMountMode == "BAT_HANDLE"`, clamp `sensorMatrix[19..24]` (`p_acc_*` and `p_gyro_*`) to `0.0f` while keeping `sensorMatrix[25]` (`has_polar`) at `1.0f` (or `0.0f` after detachment) across both `build_unified_dataset.py` and `PhoneSwingDetector.kt`. True bat-handle telemetry is stored separately in `b_acc_*` / `b_gyro_*` for 3D AHRS and biomechanical coaching.

### 2.2 Stage 1 Relaxed Stance Gate & Stage 2 Learned FP Rejection (`head_reject`)
* **Invariants**:
  1. **Stage 1 Parameters** (`telemetry_engine.py` & `TcnModelRunner.kt`): `high_thresh = 0.55`, `low_thresh = 0.35`, `motion_surge_w = 1.8 rad/s` (allows bat taps without premature stance exit), `sustain_ms = 200ms`, scan window `4.0s` (`1692` frames at 423 Hz).
  2. **Stage 2 Multi-Scale Impact-Core Pooling (208d)**: Slices $\pm 175$ frames (`[849, 1199]`) around the center impact peak across Core L5 (16d), Core L7 (64d), and Projected Core L10 (64d), concatenated with Global L7 (64d).
  3. **Binary False-Positive Rejection (`head_reject`)**: Candidates with $P(\text{no\_shot}) \ge 0.35$ are rejected as `NO_SHOT` in both `telemetry_engine.py` and `TcnModelRunner.kt`.

### 2.3 Joint 9-Class Hierarchical Training & Power Drive Soft-Routing ($\alpha = 0.85$)
* **The Trap**:
  1. Training `Head 1` (Family), `Head 2A` (Vertical), and `Head 2B` (Cross-Bat) strictly in isolation with teacher forcing caused `Head 2B` (never exposed to Power Drives) to saturate at `p_sub1[Pull] = 0.963` on high-energy swings, crushing Power Drive predictions at inference time.
  2. An obsolete heuristic in `TcnModelRunner.kt` ("Gate 1": `postImpactRatio < 1.35f -> DRIVE/DEFENCE`) demoted 100% of real Power Drives on device because physical Power Drives have mean `post_impact_acc_ratio` of `0.92–0.95`.
* **Invariants**:
  1. **Power Drive Soft-Routing**: `effective_pd_fam = p_fam[:, 0] + 0.85 * p_fam[:, 1]` in `BatPlaneGeometryThreeFamilyTCN.forward()`. Never re-introduce Gate 1 (`postImpactRatio < 1.35f`) in `TcnModelRunner.kt`.
  2. **Joint 9-Class Loss**: `train_and_evaluate_full_scorecard.py` must train with joint 9-class `NLLLoss` on `F.log_softmax(model(xb)[:, :, 1024], dim=1)` plus cross-family Power Drive suppression alongside sub-head losses, with on-the-fly kinematic augmentation (including 25% Polar channel dropout so Watch-Only representations are learned for all classes).
  3. **Cache Invalidation**: `load_or_extract_candidate_windows` validates `candidate_windows_meta.json` (session list + norm stats) before reusing `.pt` window caches.
  4. **ONNX Export**: Always export `tcn_ultimate_baseline.onnx` with `dynamo=False` and opset 18 so weights are embedded inside a single self-contained `.onnx` file (no external `.data` file).

### 2.4 Mount-Aware Consistency Gates, Shared Stage 3 Config & Jev Shadow Auditor
* **The Trap**:
  1. Applying blade pitch rules (`pitch <= 40° -> PULL` or `s1_ahrs_flat_bat` `< 20° -> PULL`) to wrist-mounted sessions (`WRIST`) or even `BAT_HANDLE` sessions destroys `DRIVE/DEFENCE` accuracy (`-24` shots on the 12-session Holdout Test Set) because the lead forearm naturally pitches at $15^\circ\text{--}35^\circ$ and reaching/cover drives angle at $15^\circ\text{--}45^\circ$.
  2. Checking `p_sub0_glance >= 0.55` inside `SWEEP` predictions (`non_bat_sweep_to_glance`) corrupted 17 genuine Sweep shots (`-13` net shots across the Clean Benchmark, `-3` on Holdout) because `head_sub0` (the vertical-bat subhead) is inactive when `head_family` selects Family 2 (`SWEEP`) and defaults its conditional softmax weight onto `GLANCE/FLICK`.
  3. In the 28-channel `sensorMatrix` in `TcnModelRunner.kt`, `w_grav_z` is channel `14` (`sensorMatrix[14]`), whereas in the 12-channel `STAGE1_CHANNELS` array it is index `8` (`channels_12[:, 8]`). Reading `sensorMatrix[8]` in Kotlin inadvertently read `w_acc_world_z`.
* **Invariants**:
  1. **Single Shared Stage 3 JSON Configuration (`stage3_rules_config.json`)**: All Stage 3 thresholds and `enabled` flags live in `pipelines/stage3_rules_config.json` (synced to `app/src/main/assets/models/stage3_rules_config.json`), evaluated identically by `pipelines/stage3_rules.py` and `Stage3RuleEngine.kt`, and verified by `Stage3RuleEngineParityTest.kt`.
  2. **Closed-Form Sub-Head Probability Recovery**: Both `stage3_rules.py::recover_hierarchical_probs` and `Stage3RuleEngine.recoverHierarchicalProbs` recover all macro family (`p_fam[0..2]`) and subhead (`p_sub0[0..3]`, `p_sub1[0..1]`) probabilities via exact quadratic inversion of the 9-class softmax output at center frame $t_{\text{mid}}$.
  3. **Active Production Stage 3 Rules (`v1.1.0`)**:
     * `sweep_dual_path_gate` (`enabled: true`): Kneeling crouch tilt ($\Delta\text{pitch} \ge 10^\circ$ or $\Delta g_z \ge 1.2\text{ m/s}^2$ at $P \ge 0.30$) or standing paddle wrist roll ($\omega_{\text{roll}} \ge 1.6\text{ rad/s}$ at $P \ge 0.35$).
     * `bat_vertical_guard_rule1` (`enabled: true`, `BAT_HANDLE` only): Watch pitch $\ge 65^\circ$ prevents vertical shots from flipping to `PULL/HOOK/SLOG` or `CUT/PUNCH`.
     * `bat_ahrs_glance_rule2` (`enabled: true`, `BAT_HANDLE` only): 3D AHRS `swingYawDeg <= -17.0°`, axial handle roll `batGzMin <= -11.5 rad/s`, and `pSub0Glance >= 0.35` (or `swingYawDeg <= -50.0°` with `pSub0Glance >= 0.50`) disambiguates vertical-bat predictions to `GLANCE/FLICK`.
     * `non_bat_sweep_to_glance` (`enabled: false`): Disabled after holdout/benchmark validation showed net `-13` shots (`+4 / -17`).
  4. **Jev (`jev-1.13`) Shadow Auditor (`pipelines/jev_auditor.py`)**: Runs automatically on every `train_and_evaluate_full_scorecard.py` evaluation (using persistent `requests.Session()` connection pooling and SHA-1 state caching in `pipelines/jev_audit_cache.jsonl`) to track per-rule precision/net-shot health and surface missed regimes in `full_dataset_training_scorecard.md`.
  5. **NaN / Inf Sanitization**: `TcnModelRunner.kt` sanitizes all non-finite inputs and Softmax outputs (`isNaN() || isInfinite() -> 0f`) to prevent silent IEEE-754 fallback to `DRIVE/DEFENCE`.

---

## 📐 3. 3D Bat Orientation AHRS & Kinematic Detachment Guard

### 3.1 State-Gated AHRS & BLE Batching Latency Alignment (`OrientationAhrs`)
* **The Trap**: Standard continuous Madgwick/Mahony filters collapse under $15\text{g}\text{--}50\text{g}$ centripetal and impact shockwaves. Furthermore, offline Polar timestamps (`timestamp_ns` from phone arrival) lag watch sensor time by $+250\text{ms}$ to $+680\text{ms}$ due to BLE packet batching; uncalibrated integration misses the $\pm 350\text{ms}$ impact window.
* **Invariants**:
  1. **BLE Latency Calibration**: `reprocess_session_orientations.py` aligns watch gyro peaks ($>8.0\text{ rad/s}$) with Polar crystal-clock acceleration peaks ($>30.0\text{ m/s}^2$) to subtract median BLE batching latency before integrating `OrientationAhrs`.
  2. **4-Phase State-Gated Integration**:
     * Phase A: Lock static gravity over the quietest 200ms pre-impact slice ($[T_{\text{impact}}-1.5\text{s}, T_{\text{impact}}-0.35\text{s}]$, $\|\omega\| < 0.8\text{ rad/s}$).
     * Phase B: Seed tilt via Rodrigues' formula and world yaw $\psi_{\text{watch}}$ from the watch quaternion.
     * Phase C: Pure dead-reckoning gyro integration ($\beta = 0$) once downswing begins ($\|\omega_{\text{bat}}\| \ge 1.0\text{ rad/s}$).
     * Phase D: Freeze quaternion integration at $T_{\text{peak}} - 2\text{ms}$ to shield orientation from impact shockwave saturation.
  3. **Python–Kotlin Euler & Modulo Parity**: `OrientationAhrs.quatToEulerZYX` uses extrinsic `'zyx'` matching `scipy.spatial.transform.Rotation.as_euler('zyx')` (`sinyCosp = 2f * (w * z - x * y)`). Kotlin angle wrapping must use mathematical modulo `(((diff + 180) % 360 + 360) % 360) - 180` because Kotlin `%` preserves negative signs.
  4. **Attack Angle Gating**: `launchAngle` ("ATTACK ANGLE" in UI) is computed strictly for `BAT_HANDLE` sessions with valid AHRS orientation, returning `null` for `WRIST` or `NONE` modes.

### 3.2 Kinematic Detachment Guard & Contiguous Interval Check (`KinematicGuard`)
* **The Trap**:
  1. BLE packet drops during follow-through create ~146ms timestamp gaps. Naive duration checks (`t_now - t_start`) accumulated missing BLE gap time as continuous $20\text{ rad/s}$ ballistic tumble, triggering false detachment warnings.
  2. Lumping AHRS stillness search timeouts (`ahrsRes == null` during rapid-fire play) into `is_kinematically_valid = false` caused false `⚠️ SENSOR DETACHED` badges on healthy sensors.
* **Invariants**:
  1. **Contiguous Frame Check**: Both `kinematic_guard.py` and `KinematicGuard.kt` enforce $\Delta t = t_i - t_{i-1} \le 15\text{ms}$. Any gap $>15\text{ms}$ resets the tumble/free-fall duration accumulator (`curr_start = None`).
  2. **Decoupled Stillness Timeout**: If a sensor is physically healthy (`guard.isKinematicallyValid == true`) but lacks a 200ms quiet stance lock (`ahrsRes == null`), keep `is_kinematically_valid = true` and leave only the 3D orientation angles `null`.
  3. **In-Session Detachment Degradation**: If a bat sensor detaches mid-session (`polar_detachment_time_s` in `session_config.json` or caught by `KinematicGuard`), downstream deliveries degrade gracefully to Watch-Only (`has_polar = 0.0f`, bat channels clamped to `0.0f`) rather than dropping shots.

---

## 🎧 4. Real-Time Coaching, UI & Hardware Streaming Invariants

### 4.1 Shot-Invariant Pre-Impact Windowing (`LiveKinematicCoach.kt`)
* **The Trap**:
  1. Guessing shot type in real time from raw peak thresholds caused false shot-specific calls (e.g., calling off-side cut faults during leg-side sessions).
  2. Tracking `maxDownswingGyroRadS` across an unbounded `isSwingActive` flag allowed routine stance taps ($10\text{--}12\text{ rad/s}$) to poison the next delivery's deceleration ratio ($1 - \omega_{\text{impact}} / \omega_{\text{max}}$).
* **Invariants**:
  1. All real-time coaching rules in `LiveKinematicCoach.kt` are **100% shot-invariant** (`EARLY_PEAK_DECELERATION`, `STALLED_REACH_PUSH`, `MID_SWING_PLANE_LOOP`, `OUT_OF_PLANE_WIPE`, `LATE_WRIST_RESCUE`, `IMPACT_FACE_TWIST`, `OVERSWING_LOSS_OF_SHAPE`) and evaluated strictly within the `[-220ms, 0ms]` pre-impact ring buffer window.
  2. Bat-handle rotational-to-linear speed conversion uses empirically calibrated `GYRO_TO_KMH = 3.4f` ($R_{\text{eff}} \approx 0.94\text{m}$ from chest/shoulder pivot).
  3. **Post-Impact Audio Timeline**: $T+0..300\text{ms}$ silence (preserves physical bat-ball crack) $\rightarrow$ $T+300..520\text{ms}$ procedural PCM earcon (`EarconAudioPlayer.kt`) $\rightarrow$ $T+550..1050\text{ms}$ 2-syllable TTS cue at $1.25\times$ speed (`LiveCoachingTtsManager.kt`) $\rightarrow$ $T+1100\text{ms}+$ Bluetooth mic open for user narration.
  4. Any changes to coaching thresholds, cues, or earcons MUST be synchronized with [docs/biomechanical_coaching_reference.md](file:///Users/neilkloot/Code/CricketBattingTracker/docs/biomechanical_coaching_reference.md).

### 4.2 Plain-English Bat-Mount UI & Lexicon Rules
* **Invariants**:
  1. In `BAT_HANDLE` mode, `BiomechanicalUiMapper.kt` must use plain-English coaching actions starting with `"Action: "` and must NEVER emit the 11 banned two-handed wrist-mode jargon terms (`"choked"`, `"lever transfer"`, `"kinetic chain"`, `"rotational downswing"`, `"pronation"`, `"supination"`, `"isometric"`, `"bottom hand"`, `"trailing arm"`, `"bottom wrist"`, `"multi-wrist"`), enforced by `BiomechanicalUiMapperTest.kt`.
  2. Canonical shot taxonomy uses `"PULL/HOOK/SLOG"` (never legacy `"SLOG"` or `"PULL/HOOK"`). Australian ASR mistranscription `"foot shot"` maps to `"Flick shot"` (`GLANCE/FLICK`).

### 4.3 Android Service Lifecycle, WakeLocks & Thread Safety
* **Invariants**:
  1. **WakeLocks**: `TrackerService.kt` (`:wear`) holds `syncWakeLock` across session zipping and `ChannelClient` transfer; `DataSyncListenerService.kt` (`:app`) holds `PhoneBatchProcessingWakeLock` (10-min timeout) across unzip and ONNX batch inference so Android App Standby never freezes mid-session processing.
  2. **RxJava Stream Thread Safety (`PolarSenseService.kt`)**: Allocate dedicated `ByteBuffer` instances and synchronize disk writes per sensor stream (`onAccSample`, `onGyroSample`, `onMagSample`) to prevent concurrent RxJava worker `BufferOverflowException`.
  3. **SharedPreferences Persistence (`BatSessionManager.kt`)**: Both `PolarSenseService` and `DataSyncListenerService` must call `BatSessionManager.initialize(this)` in `onCreate()`, and preference writes must use synchronous `.commit()` so mount mode (`WRIST` vs `BAT_HANDLE`) is never lost across service processes.
