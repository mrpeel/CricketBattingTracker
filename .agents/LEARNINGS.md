# Learnings: Pitch Analytix Pro

This document captures resolved bugs, architectural changes, key logical findings, and historical evaluation scorecards across development sessions.

---

## 💡 Technical Decisions & Discoveries

### 1. Kinematics Decisions
*   **Calibration Event**: Settled on a **5-tap signature** (5 sharp taps/peaks played within 2.0 seconds) to synchronize phone audio narration with watch sensors. This successfully avoids events occurring naturally during a session.
*   **Bat Radius**: Standardized bat radius at `0.68m` for rotational-to-linear speed calculation.
*   **Stroke Multipliers**: Implemented stroke-specific multipliers (`1.45x` for straight-bat shots like Defence/Drive/Push, and `1.30x` for cross-bat shots like Sweep/Pull) to model bat speed calculations.
*   **Facing-Up Gate (v2, May 26 2026)**: Replaced the legacy `gyro_std < 0.9` single-condition stance detector with a **4-condition facing-up gate** that requires all of the following simultaneously:
    1. `gyro_std < 1.5 rad/s` — bat not swinging
    2. `accel_std < 3.0 m/s²` — no foot-strike shock
    3. `ori_disp_mean < 3.0°` — quaternion angular displacement (bat orientation locked at guard angle)
    4. No `TYPE_STEP_DETECTOR` event in the last 2.0s — walking kill-switch
*   **Stance Optimization (May 29, 2026)**:
    *   **The Problem**: The original 4-condition gate parameters (1.5s duration, 1.0s window, `< 0.5°` orientation limit) resulted in a low shot recall of **55.1%** (missing 44.9% of shots). High-frequency IMU sensor noise on Wear OS devices creates a baseline sample-to-sample quaternion displacement of ~1.5° even when resting, making `< 0.5°` impossible to satisfy continuously. Bat taps and fidgets right before the backswing also reset the 1.5s gate timer.
    *   **The Solution (Option A)**:
        *   **Decoupled Windows**: Keep `gyro_std` and `accel_std` on a **1.0s window** to filter brief transients, but shorten `ori_disp_mean` to a **500ms window** so orientation changes clear from the buffer twice as fast.
        *   **Loosened Thresholds**: Loosen `g_lim` to `1.5 rad/s`, `a_lim` to `3.0 m/s²`, and `o_lim` to `3.0°` (Option A).
        *   **Shortened Duration**: Reduce stance lock requirement to **0.8s** to fit natural pre-swing stillness.
        *   **Result**: Recall increased from **55.1% to 92.8%** on physical logs while retaining robust walking rejection.
*   **Stance Break Tolerance (May 29, 2026)**:
    *   **The Problem**: The tightened thresholds (gyro_std < 0.9, accel_std < 1.5, ori_disp < 1.5°) and 1.2s lock duration were too sensitive. Fidgeting or rocking the bat slightly during guard reset the 1.2s timer completely, causing delayed/missed locks.
    *   **The Solution**: Implemented a 1.2-second break-tolerance window (`FACING_UP_BREAK_TOLERANCE_NS = 1.2s`). A 1.2s window is mathematically required because the 1.0s rolling standard deviation window lags physical disturbances (a 200ms rock keeps standard deviation elevated for 1.0s). If conditions fail temporarily during guard, the timer pauses and resumes if conditions recover within 1.2s.
    *   **Verification**: Unit tests `testBreakToleranceWindowRecovery` and `testBreakToleranceWindowExpiration` verified correctness.
*   **Android & Wear OS Discoveries**:
*   **Rotation Vector `qw` Reconstruction**: When Rotation Vector events return only 3 values `[qx, qy, qz]`, `qw` is dynamically reconstructed using:
    ```kotlin
    val qw = sqrt(max(0.0f, 1.0f - qx * qx - qy * qy - qz * qz))
    ```
*   **Partial Wake Lock**: Wear OS aggressively suspends background sensor listeners. We use a persistent Foreground Service with a `PARTIAL_WAKE_LOCK` to ensure continuous 50Hz sensor tracking when the watch face goes dark.
*   **Gravity Fallback**: When hardware gravity sensor is missing, a Low-Pass Filter (LPF) estimates gravity vectors from raw accelerometer data (active only when accel magnitude is under 15 m/s²).
*   **Unified Session Control via Message API**: Implemented bidirectional session control. Starting the companion app recording triggers a `/start_tracking` Wearable Message to start the watch foreground tracker, while stopping the phone recording triggers `/stop_tracking` to stop watch tracking and initiate telemetry sync.
*   **Foreground Audio Recording**: Configured `MediaRecorder` running within a foreground service of type `microphone` (`AudioRecordService`) to record AAC voice narrations at 44.1kHz. This prevents the OS from silencing the microphone when the screen is locked, and saves files directly in the app's external files directory for seamless ADB pull extraction.
*   **`TYPE_GAME_ROTATION_VECTOR` preferred over `TYPE_ROTATION_VECTOR` for bat orientation (May 26 2026)**:
    *   `TYPE_ROTATION_VECTOR` fuses accelerometer + gyroscope + **magnetometer** → subject to magnetic interference from metal bat springs, chain-link fences, and metallic sight screens.
    *   `TYPE_GAME_ROTATION_VECTOR` uses accelerometer + gyroscope **only** → immune to magnetic field distortion. Over shot timescales (< 5s) gyro drift is negligible (< 0.1°).
    *   `TYPE_ROTATION_VECTOR` is still logged to `WatchOrientation.csv` for long-term reference but is **no longer fed to `SwingDetector`**.
*   **`TYPE_STEP_DETECTOR` as definitive walking discriminant (May 26 2026)**:
    *   Runs on a dedicated hardware DSP co-processor — near-zero power (~0.001 mA).
    *   Fires exactly once per confirmed foot-strike step. Does **not** fire on bat swings (the DSP pedometer algorithm specifically recognises bilateral rhythmic gait, not unilateral impulses).
    *   At a walking cadence of ~90 steps/min, a step fires every ~0.67s. The 2.0s recency window virtually eliminates all walk-break false arms.
    *   Requires `android.permission.ACTIVITY_RECOGNITION` (already in manifest).
*   **`TYPE_LINEAR_ACCELERATION` is frequently null on Samsung Galaxy Watch** — compute it as `Accel - Gravity` from existing feeds rather than registering it as a separate sensor.
*   **`TYPE_STATIONARY_DETECT` / `TYPE_MOTION_DETECT` are NOT usable for cricket** — both have 5–10s latency and are often null on watch hardware. Our per-sample gyro std detection is far superior.
*   **Glanceable Stance Indicator (May 26, 2026)**:
    *   Exposed the `FACING_UP_LOCKED` state of `SwingDetector` to the Compose UI using a reactive callback (`onFacingUpChanged`) bound to `SessionManager.isFacingUp` StateFlow.
    *   Implemented a breathing pulse animation (fading neon-green badge background between `0.4f` and `1.0f` alpha every 800ms) to display "FACING UP" at the top of the watch screen.
    *   This provides a low-friction diagnostic tool for stance verification without needing to record shots or start a full batting session.

### 3. Pipeline Decisions & Bug Fixes
*   **Timeline Clock Alignment Bug**: Discovered that the watch writes timeline event timestamps (`Ts`) in Unix Epoch milliseconds, whereas sensor logs write timestamps in `SystemClock.elapsedRealtimeNanos()`. Resolved the misalignment in `automate_pipeline.py` by parsing the `SYSTEM_START` epoch timestamp from the timeline file to correctly project relative shot elapsed seconds.
*   **Stance and Guard Window Tuning**: Tuned the `SwingDetector` state machine parameters to mitigate phantom shots (false positives) while preserving recall:
    *   **Stance duration threshold** increased from 150ms to 300ms to filter transient dips in standard deviation during walking or adjusting guard.
    *   **Post-shot quiet guard window** increased from 1.5s to 2.5s (extending total impact-to-stance block from 2.5s to 3.5s) to suppress follow-through and recovery swings.
    *   Verification: Verified offline via high-fidelity python simulation on raw live session data, reducing phantom counts by 24% (from 59 to 45) while maintaining recall at 93.0% (66/71 matches).
*   **ADB Offline Handling**: Scoped device-pull logic to look for local audio files when in offline `--session-dir` simulation mode.
*   **Biomechanical Classifier Transition (May 2026)**:
    *   Transitioned the classifier decision tree to target the 6 top-hand biomechanical classes: `DRIVE/DEFENCE`, `GLANCE/FLICK`, `CUT/PUNCH`, `PULL/HOOK`, `DEFLECTION/GUIDE`, and `POWER SHOT`.
    *   Split the legacy `CUT/PULL` class by classifying as `PULL/HOOK` if `rollImpactDeg <= -15.0f && deltaX >= 0.30f` (representing broad, closed-wrist leg-side pulls), falling back to `CUT/PUNCH` otherwise.
    *   Updated the stroke multipliers to align with the 6 biomechanical classes (`1.45f` for straight-bat/guided, `1.30f` for cross-bat/wristy/pull, and `1.40f` for power).
*   **Watch TrackerService Lifecycle Crash (May 25, 2026)**:
    *   Resolved a lateinit `UninitializedPropertyAccessException` crash on the watch inside `TrackerService.onDestroy()` caused by calling `healthServicesManager.stopTracking()` when health services were disabled in `onCreate()`.
    *   Added a Kotlin `::healthServicesManager.isInitialized` guard. This successfully restored the Wearable Data Layer sync, allowing timeline data to sync back to the phone companion database (e.g., InningsId 17).
*   **Pipeline Auto-Start Alignment Decision (May 26, 2026)**:
    *   Replaced the high-friction 5-tap calibration alignment with an automated clock offset sync based on the phone's audio narration filename date-time (e.g. `narration_20260525_122832.m4a`) and the watch timeline's `SYSTEM_START` timestamp.
    *   For the latest session, this derived a `-1.767s` offset, aligning all narrated events across the full 18-minute session without skipping any data.
    *   Tuned `normalize_shot_class` in `automate_pipeline.py` to match the 6 new biomechanical classes (`PULL/HOOK`, `GLANCE/FLICK`, etc.), ensuring the alignment scorecard accurately reflects the classifier's performance.
    *   Noted that Room Write-Ahead Log (WAL) mode requires pulling the SQLite main file, `-wal` file, and `-shm` file concurrently to verify complete data sync.
*   **Structured Audio Transcription Pipeline (May 29, 2026)**:
    *   Transitioned the audio narration transcription from free-form text and regular expression line parsing to a native Pydantic structured output model (`response_schema`) using the new `google-genai` client.
    *   Updated the transcription prompt to explicitly reference expected shot types from all 6 biomechanical classes (e.g., Straight Drive, Cover Drive, Traditional Sweep, Slog Sweep, Helicopter Shot, etc.).
    *   Configured the model pipeline to use the `gemini-3.5-flash` model as requested, with a dynamic fallback list (`gemini-2.0-flash` -> `gemini-2.5-flash`).
    *   This resolved all long-audio repetition loops and parsed 100% of the narrated shots (69/69 shots) correctly on the latest 20-minute batting session.
*   **Bluetooth Audio Microphone Routing — Async Wait + Device Pinning (May 29, 2026)**:
    *   **The Root Race Condition**: The previous fix called `setCommunicationDevice()` / `startBluetoothSco()` — both of which are **asynchronous** — and then immediately started `MediaRecorder`. The BT SCO/LE channel had not actually opened yet, so the recorder silently fell through to the phone's built-in mic.
    *   **The Fix (commit 91caa70)**:
        *   Converted `startRecordingFlow()` to a `suspend fun` running on `Dispatchers.Main`.
        *   **API 31+**: After `setCommunicationDevice()`, suspend via `OnCommunicationDeviceChangedListener` (up to 1500ms timeout) waiting for the route confirmation callback. On timeout, clear the route and fall back to built-in mic.
        *   **API < 31**: After `startBluetoothSco()`, suspend via `ACTION_SCO_AUDIO_STATE_UPDATED` broadcast until `SCO_AUDIO_STATE_CONNECTED` fires.
        *   Called `MediaRecorder.setPreferredDevice(bluetoothDevice)` (API 28+) to pin the recorder to the confirmed device handle — without this, the OS can silently fall back to built-in mic even after routing is set.
        *   All failure paths (permission denied, no BT device, timeout) degrade gracefully to built-in mic with descriptive log lines.
    *   **Key Insight**: `setCommunicationDevice()` returning `true` only means the *request was accepted*, not that the route is *active*. The `OnCommunicationDeviceChangedListener` callback is the only reliable confirmation that audio is actually flowing through the BT device.
*   **Audio Decompression File Size Reduction (May 29, 2026)**:
    *   **The Problem**: The Python pipeline script was always running `afconvert` to decompress the AAC `.m4a` file into an uncompressed `.aiff` file (expanding file sizes by ~6x, e.g. 18MB to 103MB) in order to use the standard Python `aifc` module for 5-tap calibration peak analysis.
    *   **The Fix**: Deferred the AIFF conversion so it only runs if the auto-start metadata timestamp sync is unavailable or fails. Since auto-sync succeeded on today's session, the large AIFF file was never created, saving massive disk space.


### 4. ⚠️ CRITICAL: Root Cause of False Positive Shot Detections (May 26, 2026)

Empirical analysis of `session-2026-05-26_12-28-05` (72 GT shots, 113 watch-detected) proved the original stance detection was fundamentally broken:

| Signal | Facing Up (pre-shot 3s window) | Walking (break periods) | Separation |
|---|---|---|---|
| `gyro_std(1s) < 0.9` | 71% samples | 59% samples | **+12%** — nearly useless |
| `accel_std(1s) < 1.5` | 55% | 30% | +25% |
| `ori_disp_mean(1s) < 0.5°` | 42% | 19% | +23% |
| All 3 combined | 40% | 17% | +23% — still significant FP |
| **All 3 + step gate (no step in 2s)** | **~85%** (est.) | **< 1%** (est.) | **+85%** |

**Root cause**: Walk break periods contain long **stationary-resting windows of 10+ seconds** (player stops, looks at phone, adjusts gloves, etc.). These are indistinguishable from guard stance using wrist motion signals alone. The step detector is the only sensor that definitively separates "walking then stopping" from "genuinely facing up at guard."

**Key quaternion finding**: Mean angular displacement `ori_disp_mean` during true facing-up is **0.33–0.70°** (bat locked at guard angle). During walk/rest breaks it averages **1.7–1.9°** (bat swinging loosely). This 3–5× difference is the most discriminative wrist-motion feature, but still insufficient alone.

### 5. ⚠️ CRITICAL: Gemini Audio Transcription Brittleness (May 26, 2026)

This is a major unresolved issue that MUST be addressed before the audio transcription pipeline is considered reliable.

**Root Cause**: `gemini-2.5-flash` exhibits a **catastrophic repetition/hallucination loop** when asked to transcribe long audio files (> ~5 minutes). The model enters a generative loop producing hundreds of fake timestamps with identical content (e.g., 200+ lines of `"shot four cap"` or `"Okay."`). Every prompting strategy tested suffered from this:

| Strategy | Result |
|---|---|
| Structured JSON schema (`response_schema`) | Hallucinated repeated shots, mis-numbered |
| Plain text chronological transcript | Hallucinated 200+ "Okay." entries in a silence gap |
| Zero-temperature strict format system instruction | Hallucinated 116 shots with identical text "Oh, that's a good shot." |
| Simple natural prompt | Hallucinated `"shot four cap"` every second for 7 minutes |
| Audio chunking (3-min chunks) | Chunks 0 & 2+ reset shot numbering to Shot 1; missing shots in middle chunks |
| `gemini-2.5-pro` | 429 quota exhausted (free tier limit) |
| `gemini-2.0-flash` | 429 quota exhausted (free tier limit) |

**What works in practice:**
*   The `complete_transcript.txt` from the previous session run (produced by an earlier prompt iteration) was a usable word-for-word transcript and successfully parsed 72 shot narrations.
*   The existing `narrations_raw.json` cache file for `session-2026-05-26_12-28-05` correctly contains **72 shot narrations** (Shot 1 – Shot 72) with accurate timestamps derived from that transcript.
*   The real-world session only contained **69 shots per user count** (not 72). The discrepancy warrants investigation, but Shots 70–72 may be from a final set narrated after the user considered the main session over.

**Pending Action (B-007)**:
*   Implement Whisper-based local transcription with word-level timestamps, then send only the extracted text (not audio) to Gemini for shot classification.

---

## 📈 SwingDetector Performance Evaluation Scorecard

Evaluated against ground truth datasets (from batting sessions) using [SwingDetectorGroundTruthTest.kt](file:///Users/neilkloot/Code/CricketBattingTracker/wear/src/test/java/com/mrpeel/cricketbattingtracker/ml/SwingDetectorGroundTruthTest.kt) and local pipeline runs:

| Session | GT | Detected | TP | FP | FN | Precision | Recall | F1 | Class. Acc. | Hit/Miss Agr. | Speed MAE |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **Pull shots** | 24 | 31 | 23 | 8 | 1 | 0.74 | 0.96 | 0.84 | 0.09 | 0.96 | 12.40 km/h |
| **Cover drives** | 14 | 8 | 7 | 1 | 7 | 0.88 | 0.50 | 0.64 | 0.33 | 0.86 | 9.52 km/h |
| **On drives & flicks** | 26 | 30 | 25 | 5 | 1 | 0.83 | 0.96 | 0.89 | 0.70 | 0.92 | 22.53 km/h |
| **Short off side** | 25 | 0 | 0 | 0 | 25 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | N/A (No active watch data) |
| **full_toss** | 27 | 39 | 26 | 13 | 1 | 0.67 | 0.96 | 0.79 | 0.00 | 0.96 | N/A |
| **full_length** | 23 | 0 | 0 | 0 | 23 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | N/A (No active watch data) |
| **live_session_1** | 71 | 111 | 49 | 62 | 22 | 0.44 | 0.69 | 0.54 | 0.35 | 0.90 | N/A |
| **session_20260526 (v1)** | 72 | 113 | 9 | 58 | 5 | 0.13 | 0.13 | 0.13 | 0.13 | 0.93 | N/A |
| **session_20260526 (v2 — pending)** | 72 | — | — | — | — | — | — | — | — | — | — |

*v2 results pending next physical session deployment*

### Key Backlog Insights:
1.  **False Positive Root Cause Confirmed**: The 113 detections vs 72 GT shots (57% FP) on `session_20260526` was caused by the `gyro_std` stance gate arming during walking breaks. The 4-condition facing-up gate + step detector is expected to eliminate most of these.
2.  **Cut/Punch vs Pull/Hook Isolation**: The new 6-class model successfully isolates pulls from cuts/back foot punches. In `live_session_1`, pull shots are now matching correctly as `PULL/HOOK`.
3.  **Live Session Accuracy**: Incorporating the 6-class top-hand biomechanical model yields 35% Shot Classification Accuracy on `live_session_1` and 90% Hit/Miss Agreement.
4.  **Telemetry Gaps**: "Short off side" and "Full length" sessions continue to show 0% recall due to lacking active watch sensor data in the historical folders.
5.  **Transcription Pipeline Reliability**: The current Gemini-based transcription pipeline is brittle at 18-min file lengths. An alternative approach (Whisper + Gemini for classification only) should be evaluated to make the pipeline robust and quota-independent.
6.  **Local Whisper Pipeline & Segment Grouping (May 30, 2026)**:
    *   **The Problem**: Whisper transcribes speech in very short segments separated by pauses. This caused consecutive segments like "all three forward defense" and "poor" to be treated as separate Ground Truth events, inflating the GT shot count from ~100 to 224+ and mis-aligning the sequence indices.
    *   **The Solution**: Implemented a segment merging algorithm in `transcribe_audio_local` that groups adjacent Whisper segments if the start-to-start elapsed time is <= 7.0 seconds and the current segment does not introduce a new shot number.
    *   **Phonetic and Digit Slip Correction**: Added phonetic pre-mappings like `backward defense` -> `back-foot defensive`, `well {num}` -> `ball {num}`, `so to` -> `so two`, `catch up` -> `facing up`, etc.
    *   **Filtering & Sequence Correction**: Required that each event contains either a shot number, shot type, or admin action (eliminating conversational quality-only events like "that'll be good"). Additionally ignored sequence numbers that jump backwards (e.g. "so two backward defense" matched as 2 when the count was at 10).
    *   **Result**: GT shot count for the active 18-minute session dropped from 224 to 109, and successfully matched all 22 watch-detected events within 1.0 seconds of error.
7.  **E2E Stance Gate Simulation & Fidget Lockout (May 30, 2026)**:
    *   **The Findings**: Simulating the Wear OS `SwingDetector` state machine at 10Hz proved that "Steps Only" or the proposed hybrid "2 of 4 loose metrics" strategy generates **2.71 to 3.24 FPs/minute** in match-play. This corresponds to **325 to 388 false shots** over a 2-hour innings, because standing still at the non-striker's end or during over breaks satisfies the loose motion gates, locking them open.
    *   **Fidget Lockout Discovery**: A crucial discovery is that loose configurations (like Steps Only or 2-of-4 loose metrics) do not achieve 100% recall and can even *decrease* recall compared to tight configs. If the gate is too loose, it locks on minor pre-shot fidgets/adjustments, keeping the watch busy in `MEASURING_ARC` or `CONTACT_WAIT` (or the post-shot guard window, total 4.25s) when the real shot is actually played. Thus, the real shot is completely masked and missed.
    *   **Trade-off**: The `M3: Moderate (3 of 4)` config (gyro < 1.2, accel < 2.0, ori_disp < 2.0°, grav_y <= -2.5, steps mandatory) provides the best mathematical compromise, recovering 68.1% of match-play shots (vs 25.3% current) with 2.07 FPs/min.
8.  **Full Watch Sensor Stack Background Logging (May 31, 2026)**:
    *   **The Problem**: Logging 15 sensors concurrently at 50Hz (generating ~750 lines/second) on the main Wear OS UI thread causes thread starvation, frame drops, and watchdog crashes.
    *   **The Solution**: Created a nested `SensorConfig` mapping of 15 standard sensors to dynamic CSV filenames and headers. Offloaded listener callbacks, string formatting, and buffered file writes to a dedicated `HandlerThread` (`SensorLoggingThread`) running in the background.
    *   **Dynamic Registration**: The service dynamically registers listeners and initializes file writers only for sensors physically supported by the watch/emulator hardware. Unsupported sensors (e.g. uncalibrated gyroscope on the emulator AVD) degrade gracefully without throwing NullPointerExceptions.
    *   **Performance Verification**: Successfully tested via compilation (`./gradlew :wear:assembleDebug`), unit tests, and visible E2E simulation. The emulator dynamically logged 11 files (such as `WatchGameOrientation.csv` with safe quaternion-W reconstruction, and `WatchMagnetometerUncalibrated.csv` with bias field values) in the background with zero lag.


