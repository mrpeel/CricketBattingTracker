# Batting Dual-Hand Biomechanics & TCN Classification Pipeline

This document details the biomechanical classification categories, dual-sensor high-frequency feature representations, architectural routing for variable data scenarios, and the offline deep learning processing pipeline implemented within the Pitch Analytix Pro companion phone application.

---

## 🏗️ Architectural Strategy: Variable Data Scenarios

To handle the structural realities of match days—where Bluetooth connectivity from the center of the ground back to the kit bag is unreliable—the application implements a **Dual-TCN Routing Architecture** operating at a native sampling rate of **423 Hz**. This completely bypasses the data distortion caused by passing dummy values (imputation skew) into a single combined neural network.

                  [ Zipped Session Data Received ]
                                 │
                   ┌─────────────┴─────────────┐
                   ▼                           ▼
       [ Polar Data Present? ]       [ Polar Data Absent? ]
                   │                           │
                   ▼                           ▼
         Route to Dual-Sensor                  Route to Watch-Only
         (TCN_DualSensor.tflite)              (TCN_WatchOnly.tflite)

### 1. Match-Day Mode: Watch-Only (`TCN_WatchOnly.tflite`)
*   **Trigger**: Polar directory or data log is absent upon session sync.
*   **Input Tensor Shape**: `(Time, 6)` tracking the 3-axis gyroscope and 3-axis accelerometer of the top hand exclusively at 423 Hz.
*   **Behavior**: Detects and classifies shots based entirely on the lead wrist's turnover, angular velocities, and plane orientation signatures. 

### 2. Net/Training Mode: Dual-Sensor (`TCN_DualSensor.tflite`)
*   **Trigger**: Polar directory successfully synced alongside watch data.
*   **Input Tensor Shape**: `(Time, 12)` tracking both sensors simultaneously at 423 Hz.
*   **Behavior**: Unlocks deep biomechanical diagnostics by analyzing continuous dual-wrist kinematics, cross-sensor acceleration ratios, and sub-millisecond sequencing leads.

---

## 🤖 Deep Learning Architecture & Output Classes

All swing detection, segmentation, and classification run completely offline as a single-stage batch job on the Android phone app using a **10-Layer 1D Temporal Convolutional Network (TCN)** with non-causal padding (`padding='same'`) and a dilation array of D = [1, 2, 4, 8, 16, 32, 64, 128, 256, 512].

### 🧠 Hierarchical Skip-Head Feature Aggregation
To prevent the micro-kinematic 20ms wrist pronation signatures from being diluted across the wide 9.67-second receptive field, the classification head uses hierarchical skip connections to pull feature maps from distinct layers concurrently:
*   **Layer 5 (d=16)**: Extracts highly localized micro-kinematics (~150ms windows) capturing the raw impact shockwave and wrist snap.
*   **Layer 7 (d=64)**: Extracts swing-slot kinematics (~600ms windows) tracking the path from backswing transition down into the slot.
*   **Layer 10 (d=512)**: Extracts global macro-context (~9.67s windows) tracking pre-shot stance stability and follow-through completion.

---

## 🏏 Shot Type Biomechanical Classifications

The single-head unified TCN maps verified data arrays into one of **8 output classes**:

*   **`DRIVE/DEFENCE`**
    *   *Top-Hand Biomechanics*: Radial-to-ulnar uncocking wrist movement aligned with a straight, vertical bat face. Dictates the downswing arc and path.
    *   *Bottom-Hand Biomechanics*: Functions as a passive hinge and stabilization guide. Wrist stays relaxed and uncocked to prevent premature rolling of the blade.
    *   *Force Timing & Ratios*: Continuous, early top-hand force application throughout the downswing. Bottom-hand force is heavily delayed, presenting a low linear acceleration profile.
    *   *Shots*: Straight Drive, Cover Drive, Off Drive, On Drive, Forward Defensive, Back-foot Defensive.
*   **`GLANCE/FLICK`**
    *   *Top-Hand Biomechanics*: Guides the initial line of the ball before transitioning into a support pivot.
    *   *Bottom-Hand Biomechanics*: Active, rapid wrist flexion and forearm pronation occurring precisely at the point of impact to close the bat face.
    *   *Force Timing & Ratios*: Highly sequential. The top hand steers early, followed by an aggressive, ultra-brief spike of bottom-hand force concentrated entirely within the 30ms pre-impact window.
    *   *Shots*: Flick Shot (off pads), Leg Glance, On-Glance.
*   **`CUT/PUNCH`**
    *   *Top-Hand Biomechanics*: Isometric rigid wrist lockdown in a flat horizontal plane. Short kinetic path, minimal forearm rotation.
    *   *Bottom-Hand Biomechanics*: Mirrors the top hand's rigid lockdown, providing a solid lateral punching force across the body.
    *   *Force Timing & Ratios*: Symmetrical and concurrent. Both hands apply force simultaneously from the initiation of the downswing through to follow-through, resulting in perfectly overlapping linear acceleration profiles.
    *   *Shots*: Square Cut, Cut, Back-foot Punch.
*   **`PULL/HOOK`**
    *   *Top-Hand Biomechanics*: Broad horizontal/transverse circular arc acting as the rotational anchor. Pulls across the chest causing massive axial rollover/pronation.
    *   *Bottom-Hand Biomechanics*: Functions as a linear engine. Rapid elbow extension drives the handle forward dynamically across the line of the ball.
    *   *Force Timing & Ratios*: Overlapping sequential rollout. The top hand initiates the wide rotational arc (generating high gyro velocity), but the bottom hand triggers an intense linear punch (generating dominant accelerometer peaks) mid-downswing.
    *   *Shots*: Pull Shot, Hook Shot.
*   **`DEFLECTION/GUIDE`**
    *   *Top-Hand Biomechanics*: Forearm supination and late wrist extension just before contact to open the blade angle.
    *   *Bottom-Hand Biomechanics*: Kept loose with minimal grip tension (finger-only control), offering virtually zero structural resistance.
    *   *Force Timing & Ratios*: Single-source top-hand dominance. The bottom hand remains entirely passive with a flat, near-zero acceleration and rotation profile across all phases.
    *   *Shots*: Late Cut, Square Upper Cut, Glide/Steer.
*   **`POWER DRIVE`**
    *   *Top-Hand Biomechanics*: Accelerated vertical downswing with high-velocity release and extensive post-impact extension.
    *   *Bottom-Hand Biomechanics*: Explosive upward linear acceleration through the hitting zone, driving upward to loft and elevate the ball.
    *   *Force Timing & Ratios*: Kinetic whip effect. The top hand pulls the bat down the slot to build momentum, while the bottom hand fires an explosive acceleration burst that peaks directly at impact and sustains heavily into the follow-through.
    *   *Shots*: Lofted Straight/Cover Drive.
*   **`SLOG`**
    *   *Top-Hand Biomechanics*: High-velocity swing release serving primarily as the rotational anchor point.
    *   *Bottom-Hand Biomechanics*: Maximum violent wrist release, driving absolute angular acceleration through a broad, unrestricted hitting arc.
    *   *Force Timing & Ratios*: Co-explosive, early-loaded firing. Both hands apply maximum force almost simultaneously right from the transition point at the top of the backswing.
    *   *Shots*: Slog, Helicopter Shot.
*   **`SWEEP`**
    *   *Top-Hand Biomechanics*: Low-to-ground crouching swing utilizing rotational torso torque.
    *   *Bottom-Hand Biomechanics*: Extends low across the front knee, driving a wide horizontal sweep arc.
    *   *Force Timing & Ratios*: Phase-locked rotation. Both hands apply continuous, coupled, and highly synchronized force profiles, acting as an extension of the torso's core rotation.
    *   *Shots*: Traditional Sweep, Slog Sweep, Reverse Sweep/Switch Hit.

---

## ⏱️ Dual-Hand Timing Windows Reference

The time delta (Delta_t = Time_bottom - Time_top) isolates the exact sequencing behavior of the hands at 423 Hz:

*   **Synchronous Window (-5ms to +5ms)**
    *   *Shots*: CUT/PUNCH
    *   *Telemetry*: Near-zero variance. Both wrists lock and fire symmetrically to slap the ball laterally.
*   **Passive/Guided Lag Window (+5ms to +20ms)**
    *   *Shots*: DRIVE/DEFENCE
    *   *Telemetry*: A tight, consistent trailing lag. The bottom hand follows smoothly behind the path established by the top hand.
*   **Intentional/Deflective Lag Window (+15ms to +40ms)**
    *   *Shots*: DEFLECTION/GUIDE
    *   *Telemetry*: Extended lag. The bottom hand grip stays loose, letting the top hand independently supinate to angle the blade face late.
*   **Active Lead/Snap Window (-10ms to -30ms)**
    *   *Shots*: GLANCE/FLICK, PULL/HOOK, SLOG
    *   *Telemetry*: The bottom hand peaks *before* the top hand's rotational turnover window, actively pulling the bat handle through the hitting arc.

---

## 📊 High-Frequency Kinematic Representation

To ensure spatial transformations do not confuse the TCN, all raw 3-axis accelerometer channels are converted to a decoupled **Vector Linear Acceleration Magnitude (a_mag)** stream before hitting the feature aggregation head. This isolates pure kinetic intensity independent of sensor orientation:

a_mag = sqrt(a_x^2 + a_y^2 + a_z^2)

### Dual-Hand Kinematic Profiling Matrix (Raw Sensor Realities)

Unlike coaches' theoretical force splits, the model evaluates shots using raw kinematic signatures that reflect anatomical realities (such as the pull shot's low gyro / high acceleration profile):

| Shot Class | Target bottom_hand_gyro_ratio (Gyro_bot / Gyro_top) | Target bottom_hand_acc_ratio (Acc_bot / Acc_top) | Target bottom_hand_time_lead_ms (Delta_t) | Primary Biomechanical Identifier |
| :--- | :--- | :--- | :--- | :--- |
| **`DRIVE/DEFENCE`** | 0.45 to 0.70 | <= 0.60 | +5ms to +20ms | Low gyro ratio, low linear acceleration, passive trailing lag. |
| **`GLANCE/FLICK`** | >= 1.20 | >= 1.10 | -5ms to -15ms | High gyro velocity spike leading right before contact. |
| **`CUT/PUNCH`** | 0.90 to 1.10 | 0.85 to 1.15 | -5ms to +5ms | Balanced, perfectly synchronous 1.0 ratios on both channels. |
| **`PULL/HOOK`** | <= 0.22 | >= 1.20 | -12ms to -25ms | Low gyro (linear punch) paired with dominant acceleration lead. |
| **`DEFLECTION/GUIDE`**| 0.15 to 0.40 | <= 0.25 | +15ms to +40ms | Passive bottom hand; top hand executes late opening roll. |
| **`POWER DRIVE`** | >= 1.10 | >= 1.10 | -10ms to 0ms | Double acceleration peaks with extended follow-through. |
| **`SLOG`** | >= 1.75 | >= 1.50 | -25ms to -5ms | Massive bottom-hand velocity dominance across all axes. |
| **`SWEEP`** | 1.05 to 1.30 | 0.90 to 1.20 | -10ms to +5ms | Phase-locked horizontal plane rotation tracking torso torque. |

---

## 📈 Actionable UI Coaching Diagnostics

The app presentation layer translates these raw multi-sensor cross-correlations into direct, plain-English coaching metrics:

### 1. Swing Sequencing (Timing Metric)
*   **`Perfect Snap`**: The bottom hand cleared the arc beautifully ahead of the wrist turnover.
*   **`Dragged Blade`**: The bottom hand severely lagged behind the rotation of your shoulders, leaving the bat face trailing.
*   **`Late Release`**: Hands pushed along a linear path late instead of snapping smoothly through the arc.
*   **`Clean Extension`**: Top hand completely dominated the vertical path, keeping the downswing tracking down the slot.
*   **`Early Wrist Snap`**: The bottom hand closed the bat face prematurely before reaching the line of the ball.

### 2. Power Pattern (Grip Dominance Index)
*   **`Explosive Punch`**: High linear handle acceleration. Clean, optimal force application through a cross-bat shot.
*   **`Weak Bottom Hand`**: The shot lacked punching power; trailing arm failed to drive through the horizontal plane.
*   **`Top-Hand Control`**: Perfect passive hinge behavior, keeping the ball grounded on a vertical drive.
*   **`Hard Bottom Hand`**: The bottom hand choked the handle mid-downswing, risking a closed blade and an airborne mistiming.

---

## ⚙️ Companion App Processing Pipeline (`PhoneSwingDetector.kt`)

### Step 1: Clock Drift Alignment
If a Polar log is present, the app matches sync-tap sequences from the start of the session using a linear regression model:
Polar_phoneMs = watch_wallMs * (1 + driftRate) + offsetMs
This aligns both devices to sub-millisecond precision, validating the accuracy of the `bottom_hand_time_lead_ms` feature.

### Step 2: Continuous Stream TCN Inference
The raw 423 Hz data stream is continuously fed through the 10-layer non-causal TCN. The network evaluates the global temporal context out of the data buffer without needing destructive pre-segmentation slicing.

### Step 3: Hierarchical Feature Aggregation
When the TCN's detection head flags an active impact peak, the pipeline executes skip-head aggregation—extracting feature maps concurrently from Layer 5, Layer 7, and Layer 10 around the peak timestamp.

### Step 4: Inference Routing
*   If both sensor logs are verified, the 26-feature aggregated dual-sensor vector is evaluated by `TCN_DualSensor.tflite` to output the shot class and generate the advanced UI metrics (Swing Sequencing and Power Pattern).
*   If the Polar log is absent, the 14-feature watch-only vector routes automatically to `TCN_WatchOnly.tflite` for clean match-day classification.

### Step 5: Non-Maximum Suppression (NMS)
Detections are sorted chronologically. If multiple impact events register within a 5.0-second window, only the candidate with the highest estimated bat speed is preserved, filtering out equipment adjustments and false alarms.

---

## 🏃 Non-Shot Baseline States

These states are filtered out by the phone app's stance gate validation and pre-shot checks, avoiding false positives:

*   **Facing Up (Stance)**
    *   *Biomechanics*: Static isometric baseline supporting the weight of the bat. Characterized by stable gravity vectors and gentle 0.5--2 Hz micro-oscillations on both sensors. Used to calibrate the orientation matrix.
*   **Walking Around**
    *   *Biomechanics*: Low-g, multi-axis, non-rhythmic drift as the player shifts grip, taps the crease asynchronously, or adjusts equipment.
*   **Running (Between Wickets)**
    *   *Biomechanics*: High-g, highly rhythmic periodic acceleration spikes matching running cadence (2--4 Hz spikes) detected symmetrically across both arms.