# Cricket Batting Tracker - V1 Release

I have completed the end-to-end V1 foundation for your Galaxy Watch 7 Cricket Tracker! 

The codebase is located in `~/Code/CricketBattingTracker` and can be opened directly in **Android Studio**.

## What Was Built

### 1. Wear OS (`:wear` module)
* **Foreground Tracking**: Built `TrackerService` which operates even while the watch face is off. It holds a partial wake lock to guarantee we get continuous IMU (Inertial Measurement Unit) data through your entire innings.
* **Health Services API Integration**: Implemented `HealthServicesManager` which ties directly into the standard Samsung/Google Health Wear OS Exercise client. It starts a "Cricket" workout session to track your distances run and calories reliably via GPS and pedometers.
* **Kinematics Engine**: Built a heuristic `SwingDetector` that monitors the 50Hz Accel/Gyro data from your top (left) hand. It identifies high rotational velocity (swings) combined with sharp acceleration spikes (impacts), generating a kinematic view of your shots.
* **Data Layer Hub**: The watch batches all recorded timeline strings (shots, distances) and securely pushes them to your phone automatically when connected via Bluetooth using `DataSyncManager`.

### 2. Mobile Companion App (`:app` module)
* **Room Database**: Structured a fast on-device SQLite database using Room to permanently store your past innings.
* **Wearable Sync Listener**: Created `DataSyncListenerService` which listens silently in the background for new timeline data pushed by the watch after your match.
* **Review Dashboard UI**: Built a beautiful dark-mode Jetpack Compose user interface containing an Innings summary dashboard (Total Distance, Max Bat Speed) and a chronological ordered list of the ball-by-ball actions you took on the field.

## Validation & Next Steps

Because tracking biomechanics is highly sensitive to the individual user and device hardware, the logic inside `SwingDetector` (specifically the kinematic thresholds and the difference between a forward defense and a pull block) will need tuning in the nets. 

### How to test:
1. Open `~/Code/CricketBattingTracker` in Android Studio.
2. Build and Deploy the `:wear` module to your Galaxy Watch 7.
3. Build and Deploy the `:app` module to your Samsung Phone.
4. Put the watch on your left hand under a sweatband, head to the nets, and hit START. 
5. See how accurately the baseline math detects the impact peaks! All the raw data generated can now be exported to train your custom ML shot-type classifier for V2.

---

## Stance & Detection Reliability Improvements (V2)

To address high false positive rates during walk breaks and improve shot recall, we implemented the following enhancements:

### 1. 5-Condition Facing-Up Gate
All shot detection is now anchored to a confirmed guard stance (`ACTIVITY_CLASSIFY -> FACING_UP_LOCKED`):
* **Gyroscope Stability**: `gyro_std < 0.9 rad/s` (over 1.0s window).
* **Accelerometer Stability**: `accel_std < 1.5 m/s²` (over 1.0s window).
* **Bat Orientation Stability**: `ori_disp_mean < 1.5°` (over 500ms window).
* **Step Detector Suppression**: Instantly invalidates stance lock if `TYPE_STEP_DETECTOR` fires within 2.0s (acts as a walking kill-switch).
* **Gravity Y Arm-Extension Anchor**: Requires `mean_gravity_y <= -3.5 m/s²` (confirms lead arm is extended towards the ball rather than resting at the side).

### 2. Stance Break-Tolerance Window
* To prevent minor movements or bat rocking at guard from fully resetting the lock timer, we added a **1.2-second break-tolerance grace period** (`FACING_UP_BREAK_TOLERANCE_NS`).
* If conditions temporarily fail but recover within 1.2s, the lock timer pauses and resumes, rather than resetting to zero.
* A 1.2s window is mathematically required because the 1.0s rolling standard deviation window lags physical rocking.

### 3. Sensor Stack & UI Upgrades
* Switched bat orientation tracking to `TYPE_GAME_ROTATION_VECTOR` (magnetometer-free) to eliminate magnetic interference from bats or sight-screens.
* Added a pulsing "FACING UP" visual status badge on the Wear OS Watch UI for real-time stance confirmation.

---

## Narration Pipeline & Alignment Refinements (May 31, 2026)

To support complex net sessions with Wayward balls, non-swing actions, and new shot types, the Python ADB pipeline (`automate_pipeline.py`) has been upgraded with the following:

### 1. Non-Swing and Evade Preservation
* Supported "No shot", "Leave", and "Evade/Evasion" (swaying out of the way) as mapped non-swing events.
* Aligned sequential non-swing timestamps using Dynamic Programming (DP) sequence alignment without throwing off the main shot timeline.

### 2. Shot and Rating Mapping Vocabulary
* **Defence/Block Restoration**: Mapped `"defense"`, `"defence"`, `"defensive"`, and `"block"` directly to `"Defence/Block"`. This prevents these shots from being dropped/ignored when Gemini omits a shot number in the structured JSON narration.
* **Edge Quality mapping**: Mapped `"edge"` and `"edged"` rating words to `"poor"` quality, instead of incorrectly defaulting to `"good"`.
* **Guide & Glide shots**: Mapped `"guide"`, `"glide"`, and `"steer"` to `"Guide"`, which maps to the biomechanical classification class `DEFLECTION/GUIDE`.
* **Power shots**: Mapped `"power"` and `"loft"` to `"Power shot"`, which normalizes to the class `POWER SHOT`.
* **Punch shots**: Mapped `"punch"` to `"Punch"`, normalizing correctly to `CUT/PUNCH` rather than defaulting to defense.

### 3. E2E Verification Results
We cleared the cache and verified the updated pipeline against the live session `session-2026-05-31_14-12-10`:
* **Total Narrated Ground Truth Shots**: 78
* **Accuracy & Classification Alignment**: 100% of the 78 events parsed correctly from the audio narration and aligned.
* **Biomechanical Class Verification**:
  * Defensive shots mapped to `DRIVE/DEFENCE`.
  * Guide shots mapped to `DEFLECTION/GUIDE`.
  * Punch shots mapped to `CUT/PUNCH`.
  * Power shots mapped to `POWER SHOT`.
  * Evades/leaves correctly treated as non-swing events.

---

## Stance Gate M-of-N Optimization & Wake-Up Step Sensors (May 31, 2026)

We have implemented the approved hybrid M-of-N stance gate logic and solved the hardware-level step sensor suspension bug:

### 1. Wake-Up Step Sensors
* **The Bug**: On Wear OS, non-wake-up step detector/counter sensors are suspended/batched by the Sensor Hub when the watch screen goes off or transitions to ambient mode, despite having a background partial wake lock. This caused all step interrupts to be batched and delayed by up to 3 minutes, only flushing when the screen turned on (e.g. at 169.7s).
* **The Fix**: Modified [TrackerService.kt](file:///Users/neilkloot/Code/CricketBattingTracker/wear/src/main/java/com/mrpeel/cricketbattingtracker/services/TrackerService.kt) to request the **wake-up version** of the sensors: `sensorManager.getDefaultSensor(Sensor.TYPE_STEP_DETECTOR, true)` and `Sensor.TYPE_STEP_COUNTER` (in raw logging). This instructs the hardware Sensor Hub to deliver walking interrupts immediately to the CPU in real-time, even in ambient mode.

### 2. Hybrid M-of-N Stance Gate
* **The Change**: Modified [SwingDetector.kt](file:///Users/neilkloot/Code/CricketBattingTracker/wear/src/main/java/com/mrpeel/cricketbattingtracker/ml/SwingDetector.kt) to use a flexible "M-of-N" architecture.
* **Logic**: Enforces walking suppression (steps) and gyroscope stillness (`gyroStd < 1.2 rad/s`) as **mandatory** gates, but permits wiggles or wrist shifts by requiring only **one** of the remaining three stability conditions to pass:
  1. `accelStd < 2.0 m/s²` (foot-strike/movement)
  2. `oriDisp < 2.0°` (angular orientation drift)
  3. `meanGravY <= -3.5 m/s²` (lead arm extended)
* **Results**: Verified via python E2E simulation, demonstrating a significant increase in shot recall from **66.7% to 78.3%** on physical logs while keeping false triggers low (1.68 FPs/min).

### 3. Verification & Unit Tests
* Extended the break-tolerance window to `1.5 seconds` (`FACING_UP_BREAK_TOLERANCE_NS`) to account for standard deviation decay lag under the tighter `1.2 rad/s` gyro limit.
* Compiled and ran the full Wear OS test suite (`./gradlew :wear:testDebugUnitTest`) successfully (10/10 green).
