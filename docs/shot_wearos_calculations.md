# WearOS Real-Time Kinematics Architecture

This document describes the architectural translation of the batch-processed Python pipeline into a streaming, real-time, memory-efficient state machine for the WearOS smartwatch.

## 1. Paradigm Shift: Batch vs. Streaming

The Python pipeline loads entire sessions and analyzes them with the benefit of hindsight — looking forward and backward in time globally to align peaks and apply broad filtering windows. 

A WearOS application must analyze the data as it streams in, operating with:
- **No hindsight:** If you need to look 0.5s before a swing peak, you must have buffered that data.
- **Batched Sensors:** Android sensors are delivered in small batches. Relying on strict fixed intervals is dangerous; logic must be driven by timestamps.
- **Resource Constraints:** We cannot store infinite arrays. We need fixed-size ring buffers, utilizing primitive float arrays (not object allocations) to avoid Garbage Collection stuttering which drops frames.
- **Shot-Type Agnosticism:** We proved shot-type inference in real-time is unreliable. The watch app must succeed without knowing what shot was played, relying on our tightened uniform time windows to reject noise.

## 2. Sensor Pipeline & Buffering

We need to capture the contact window (`-0.45s` to `+0.75s` around the swing peak), but the swing peak timestamp (`T_peak`) is only finalized 1 second *after* the swing begins. Therefore, the app needs to hold onto historical accelerometer data for roughly 2.5 seconds. 

### Implementation:
Use a **Circular/Ring Buffer** (length ~150-200 frames for 50Hz sensor data).

**Required Buffers:**
1. `GyroBuffer`: Stores the `x, y, z` and `magnitude` for at least the last 1.0 seconds (to compute standard deviations).
2. `AccelBuffer`: Stores the `x, y, z` and `magnitude` for the last 2.5 seconds (to allow backward search once `T_peak` is found).

## 3. The Core State Machine

Instead of mapping the whole file, the watch runs a state machine evaluated on every incoming sensor event.

### State 1: `IDLE_RECOVERY`
- **Objective:** Detect the "facing-up" / pre-delivery stance.
- **Logic:** Calculate the standard deviation of the Gyroscope magnitude over the trailing 0.5 seconds in the ring buffer.
- **Transition Rule:** If `gyro_std < QUIET_STD_THRESHOLD (0.9 rad/s)` for more than `0.15` continuous seconds, transition to **`STATE_STANCE_LOCKED`**.

### State 2: `STATE_STANCE_LOCKED`
- **Objective:** Wait for the batter to move out of the stance.
- **Logic:** Continue monitoring the trailing standard deviation.
- **Transition Rule:** When `gyro_std >= 0.9` (batter initiates a movement), record `T_exit = current_timestamp`. Transition immediately to **`STATE_SWING_SEARCH`**. 

### State 3: `STATE_SWING_SEARCH`
- **Objective:** Identify the initiation of the bat swing.
- **Logic:** Monitor the live incoming `gyro_magnitude`.
- **Transition Rules:**
  - **Match:** If `gyro_magnitude > MIN_SWING_PEAK (5.0 rad/s)`, record `T_swing_start = current_timestamp`. Transition to **`STATE_MEASURING_ARC`**.
  - **Timeout:** If `current_timestamp - T_exit > MAX_SWING_LOOKAHEAD (5.5s)`, the batter likely fidgeted or readjusted without swinging. Transition back to **`IDLE_RECOVERY`**.

### State 4: `STATE_MEASURING_ARC`
- **Objective:** Find the absolute highest rotational speed (the swing peak).
- **Logic:** Maintain a tracker for `peak_gyro` and its timestamp `T_peak`. Update it as long as values exceed the current highest.
- **Transition Rule:** When `current_timestamp >= T_swing_start + 1.0s`, the swing has finished rotating. Lock in the absolute maximum value tracked as `T_peak` and `peak_gyro`. Transition to **`STATE_CONTACT_WAIT`**.

### State 5: `STATE_CONTACT_WAIT`
- **Objective:** Wait until the full trailing tail of the contact window exists in the buffer.
- **Logic:** Do nothing but buffer the data. 
- **Transition Rule:** When `current_timestamp >= T_peak + CONTACT_POST (0.75s)`, we now have the full context in our Ring Buffer! Transition to **`STATE_EVALUATION`**.

### State 6: `STATE_EVALUATION` (Instantaneous)
- **Objective:** Scan the buffer and calculate shot metrics. 
- **Logic:** 
  1. Iterate over the `AccelBuffer`.
  2. Extract data points occurring between `T_peak - 0.45s` and `T_peak + 0.75s`.
  3. Find `max(accel_magnitude)` in this subset. This is `peak_acc`.
  4. If `peak_acc >= HIT_SHOCK_THRESHOLD (12.0 m/s²)` -> The shot is a **HIT** (Bat, Edge, or Pad). Otherwise, it is a **MISS**. 
  5. Process the final kinematic evaluations (see Section 4).
  6. Dispath data to the WearOS UI layer.
  7. Transition back to **`IDLE_RECOVERY`**.

---

## 4. Metrics Extraction Logic

Once the hit/miss classification is made, generate the data package:

**1. Bat Speed:**
```kotlin
val batSpeedKmh = peak_gyro * BAT_RADIUS (0.8) * 3.6
```

**2. Sweet Spot Rating (Hits Only):**
The validation proved that assessing the shock-to-power relative ratio (`peak_acc / batSpeedKmh`) neutralizes the variances between gentle pushes and full swings.
```kotlin
val vibrationRatio = peak_acc / batSpeedKmh
val rating = when {
    vibrationRatio < RATIO_EXCELLENT (2.5) -> "Excellent"
    vibrationRatio < RATIO_GOOD (3.0) -> "Good"
    else -> "Poor"
}
```

## 5. Handling Deduplication in Real Time

In Python, we removed "duplicate" shots by enforcing an arbitrary time gap (`INTER_SHOT_GAPS = 1.8s` for flicks). In real-time WearOS, we avoid this completely through **Architecture Design**:

1. Once a shot is tracked, the State Machine forcibly returns to `IDLE_RECOVERY`. 
2. Because it requires `gyro_std < 0.9` for *0.15 continuous seconds*, follow-through wobbles and bat-twirling automatically prevent the machine from locking a new stance.
3. As observed in the Python tests, the narrowed contact window (`-0.45s to +0.75s`) filters out follow-through vibrations. We do not need an arbitrary 1.8 second blackout timer because the stance-lock mechanic naturally protects the pipeline.

## 6. Implementation Cautions
- **Sensor Suspension (CRITICAL)**: Wear OS aggressively optimizes battery by suspending sensor listeners if the screen goes to sleep or the arm drops. Data analysis has proven this will cause massive (minutes-long) blackouts in the datastream where swings are completely lost. You MUST implement a `PARTIAL_WAKE_LOCK` combined with a persistent **Foreground Service** (like Strava) to ensure the `SensorManager` is never throttled or suspended during a live session.
- Android's `SensorEvent.timestamp` is in nanoseconds since boot (`SystemClock.elapsedRealtimeNanos()`), not Unix epoch time. All time-math (`+ 0.75s`, `- 0.45s`) must be calculated strictly against the native sensor system clock.
- **Do not perform heavy math on the `onSensorChanged` main thread**. When pushing into the Circular Buffer, keep it O(1). The `STATE_EVALUATION` step should preferably run in an async coroutine/worker, allowing the ring buffer to continue recording un-interrupted.
