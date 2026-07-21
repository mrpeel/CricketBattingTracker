# Batting Dual-Hand Biomechanics & Classification Pipeline

This document details the biomechanical classification categories, dual-sensor feature extraction representations, architecture routing for variable data scenarios, and the offline processing pipeline implemented within the Pitch Analytix Pro companion phone application.

---

## 🏗️ Architectural Strategy: Variable Data Scenarios

To handle the structural realities of match days—where Bluetooth connectivity from the center of the ground back to the kit bag is unreliable—the application implements a **Dual-Model Routing Architecture**. This bypasses the classification degradation caused by passing dummy values (imputation skew) into a single combined neural network.

```
                  [ Zipped Session Data Received ]
                                 │
                   ┌─────────────┴─────────────┐
                   ▼                           ▼
       [ Polar Data Present? ]       [ Polar Data Absent? ]
                   │                           │
                   ▼                           ▼
         Route to Dual-Model                 Route to Top-Model
      (GeneratedDualForest.kt)             (GeneratedTopForest.kt)
```

### 1. Match-Day Mode: Watch-Only (`GeneratedTopForest.kt`)
*   **Trigger**: Polar directory or data log is absent upon session sync.
*   **Vector Shape**: 14-feature input tracking top-hand wrist kinematics exclusively.
*   **Behavior**: Classifies shots based entirely on the lead wrist's turnover, angular velocities, and plane orientation. It relies on a model trained on both legacy single-sensor sessions and the isolated top-hand streams of dual-sensor training data.

### 2. Net/Training Mode: Dual-Sensor (`GeneratedDualForest.kt`)
*   **Trigger**: Polar directory successfully synced alongside watch data.
*   **Vector Shape**: 26-feature input combining top-hand tracking with time-aligned segmented bottom-hand metrics.
*   **Behavior**: Unlocks deep biomechanical diagnostics, analyzing running acceleration ratios, transient grip dominance, and precise cross-hand timing leads to evaluate both shot classification and exact execution quality.

---

## 🤖 Machine Learning Models & Output Classes

All swing detection, segmentation, and classification run as an offline batch job on the Android phone app via two Random Forest classifiers determined by the data routing layer.

### 1. Shot Type Classifier
Classifies verified active swings into one of **8 output classes**:

*   **`DRIVE/DEFENCE`**
    *   *Top-Hand Biomechanics*: Radial-to-ulnar uncocking wrist movement aligned with a straight, vertical bat face. Keeps the face straight through impact.
    *   *Bottom-Hand Biomechanics*: Functions as a passive hinge and stabilization guide. Wrist stays relaxed and uncocked to prevent premature rolling of the blade.
    *   *Coordination & Timing*: Top hand completely dictates the downswing arc and path. The bottom hand follows smoothly with zero time-lead.
    *   *Force Ratio*: High top-hand dominance (typically **70:30** to **80:20** force split).
    *   *Shots*: Straight Drive, Cover Drive, Off Drive, On Drive, Forward Defensive, Back-foot Defensive.
*   **`GLANCE/FLICK`**
    *   *Top-Hand Biomechanics*: Guides the initial line of the ball before transitioning into a support pivot.
    *   *Bottom-Hand Biomechanics*: Active, rapid wrist flexion and forearm pronation occurring precisely at the point of impact to close the bat face.
    *   *Coordination & Timing*: The bottom hand operates with a late, high-velocity acceleration burst, snapping right at contact while the top hand maintains the axis.
    *   *Force Ratio*: Rapid dynamic shift from top-hand control during downswing to bottom-hand execution at contact (**40:60**).
    *   *Shots*: Flick Shot (off pads), Leg Glance, On-Glance.
*   **`CUT/PUNCH`**
    *   *Top-Hand Biomechanics*: Isometric rigid wrist lockdown in a flat horizontal plane. Short kinetic path, minimal forearm rotation.
    *   *Bottom-Hand Biomechanics*: Mirrors the top hand's rigid lockdown, providing a solid lateral punching force across the body.
    *   *Coordination & Timing*: Extreme synchronization. Both sensors register near-identical angular velocity profiles with near-zero millisecond variance.
    *   *Force Ratio*: Highly balanced kinetic distribution (**50:50**) to ensure linear control and blade stability.
    *   *Shots*: Square Cut, Cut, Back-foot Punch.
*   **`PULL/HOOK`**
    *   *Top-Hand Biomechanics*: Broad horizontal/transverse circular arc starting with an extended lever.
    *   *Bottom-Hand Biomechanics*: Highly aggressive internal rotation and pronation, actively pulling the bat across the line of the ball and forcing a downward follow-through.
    *   *Coordination & Timing*: Top hand initiates the wide swing path, but the bottom hand takes over kinetic acceleration mid-downswing, leading the impact window.
    *   *Force Ratio*: Heavily bottom-hand dominant (**30:70**) to generate cross-bat velocity and force the ball downward.
    *   *Shots*: Pull Shot, Hook Shot.
*   **`DEFLECTION/GUIDE`**
    *   *Top-Hand Biomechanics*: Forearm supination and late wrist extension just before contact to open the blade angle.
    *   *Bottom-Hand Biomechanics*: Kept completely loose with minimal grip tension (finger-only control), offering virtually zero structural resistance.
    *   *Coordination & Timing*: The bottom hand exhibits an intentional lag, allowing the top hand to manipulate the face angle independently against the ball's incoming pace.
    *   *Force Ratio*: Absolute top-hand dominance (**90:10**).
    *   *Shots*: Late Cut, Square Upper Cut, Glide/Steer.
*   **`POWER DRIVE`**
    *   *Top-Hand Biomechanics*: Accelerated vertical downswing with high-velocity release and extensive post-impact extension.
    *   *Bottom-Hand Biomechanics*: Explosive upward linear acceleration through the hitting zone, driving upward to loft and elevate the ball.
    *   *Coordination & Timing*: Classic kinetic whip effect. The top hand pulls the bat down into the slot, immediately followed by an explosive bottom-hand acceleration peak at or a split-second after impact.
    *   *Force Ratio*: Transitions from top-hand guidance down the slot to bottom-hand acceleration through impact (**45:55**).
    *   *Shots*: Lofted Straight/Cover Drive.
*   **`SLOG`**
    *   *Top-Hand Biomechanics*: High-velocity swing release serving primarily as the rotational anchor point.
    *   *Bottom-Hand Biomechanics*: Maximum violent wrist release, driving absolute angular acceleration through a broad, unrestricted hitting arc.
    *   *Coordination & Timing*: Both hands accelerate concurrently from the top of the backswing, with the bottom hand hitting its acceleration peak early to force maximum release velocity.
    *   *Force Ratio*: Total bottom-hand dominance (**20:80**).
    *   *Shots*: Slog, Helicopter Shot.
*   **`SWEEP`**
    *   *Top-Hand Biomechanics*: Low-to-ground crouching swing utilizing rotational torso torque.
    *   *Bottom-Hand Biomechanics*: Extends low across the front knee, driving a wide horizontal sweep arc. For the Reverse Sweep, roles invert dynamically.
    *   *Coordination & Timing*: Highly coupled rotational tracking; both hands move in a locked horizontal plane relative to the lowered torso.
    *   *Force Ratio*: Moderately bottom-hand heavy (**40:60**) to counter gravity at a low swing plane.
    *   *Shots*: Traditional Sweep, Slog Sweep, Reverse Sweep/Switch Hit.

### 2. Shot Quality Classifier
Evaluates the execution quality of the swing based on the feature input vector, outputting one of **3 classes** mapped in the UI to specific descriptors and efficiency ratings:

| Classifier Output | UI Display | Swing Efficiency Rating |
| :--- | :--- | :--- |
| **`good`** | Excellent | 90% |
| **`poor`** | Poor | 60% |
| **`miss`** | Miss | 0% |

---

## 📊 Extracted Kinematic Features (`SwingFeatures.kt`)

The features are systematically extracted into one of two configurations depending on hardware presence. When Polar data is available, it is segmented across time-domain phase boundaries anchored by the top-hand watch device.

### Top-Hand Wrist Features (14 Features - Present in Both Models)
*   **Segment 1 (Backswing)**:
    *   `s1_gyro_y_std`: Standard deviation of gyroscope Y-axis.
    *   `s1_gyro_z_std`: Standard deviation of gyroscope Z-axis.
    *   `s1_deltaX`: Angular displacement/rotation around X-axis.
    *   `s1_deltaZ`: Angular displacement/rotation around Z-axis.
*   **Segment 2 (Downswing)**:
    *   `s2_gyroMag`: Peak magnitude of the gyroscope vector.
    *   `s2_grav_y_mean`: Average Y-axis gravity component (defines absolute bat orientation).
    *   `s2_deltaX`: Downswing rotation around X-axis.
    *   `s2_deltaZ`: Downswing rotation around Z-axis.
*   **Segment 3 (Contact & Follow-through)**:
    *   `s3_rollImpactDeg`: Estimated roll angle at impact.
    *   `s3_yawImpactDeg`: Estimated yaw angle at impact.
    *   `s3_deltaX`: Follow-through rotation around X-axis.
    *   `s3_deltaZ`: Follow-through rotation around Z-axis.
    *   `s3_planeRatio`: Straightness/flatness ratio of the swing plane.
    *   `s3_gyro_y_min`: Minimum gyroscope Y-axis reading (wrist release velocity).

### Bottom-Hand Features (12 Features - Present in Dual-Sensor Model Only)
*   **Global Summary Metrics**:
    *   `bottom_hand_gyro_peak`: Peak gyroscope magnitude on bottom hand.
    *   `bottom_hand_acc_peak`: Peak accelerometer magnitude on bottom hand.
    *   `bottom_hand_gyro_ratio`: Ratio of bottom-hand peak gyro to top-hand peak gyro ($\text{Gyro}_{\text{bottom}} / \text{Gyro}_{\text{top}}$).
    *   `bottom_hand_acc_ratio`: Ratio of bottom-hand peak accelerometer to top-hand peak accelerometer ($\text{Acc}_{\text{bottom}} / \text{Acc}_{\text{top}}$).
    *   `bottom_hand_time_lead_ms`: Relative lead/lag (in milliseconds) of bottom-hand peak impact shockwave over top-hand peak shockwave ($\text{Time}_{\text{bottom}} - \text{Time}_{\text{top}}$).
    *   `bottom_hand_sync_score`: Weighted alignment metric ($1.0 - \text{timePenalty} \times 0.6 - \text{ratioPenalty} \times 0.4$) mapped to a $[0, 100]$ score.
*   **Segmented Metrics (Time-Aligned to Watch Phase Boundaries)**:
    *   `s1_bottom_gyro_mag`: Total angular activity of the bottom hand during backswing (detects over-active lifting).
    *   `s1_bottom_deltaZ`: Lateral angular rotation of bottom hand during backswing.
    *   `s2_bottom_acc_mean`: Average linear acceleration of bottom hand during downswing phase.
    *   `s2_dynamic_ratio_slope`: Rate of change of the bottom-to-top gyro ratio during downswing (isolates premature hand takeover).
    *   `s3_bottom_pronation_deg`: Calculated forearm roll of the bottom hand during follow-through.
    *   `s3_bottom_gyro_y_min`: Minimum gyroscope Y-axis reading on bottom hand during follow-through.

---

## 🔬 Classification & Diagnostic Reference Targets

To optimize Random Forest boundary splits and generate constructive coaching metrics during dual-sensor practice sessions, the pipeline cross-references these targets:

### Dual-Hand Kinematic Profiling Matrix

| Shot Class | Target `bottom_hand_gyro_ratio` | Target `bottom_hand_time_lead_ms` | Primary Kinematic Identifier |
| :--- | :--- | :--- | :--- |
| **`DRIVE/DEFENCE`** | $0.45 \text{ to } 0.70$ | $+5\text{ms} \text{ to } +20\text{ms}$ (Lagging) | Low ratio paired with strict top-hand plane alignment (`s3_planeRatio` $\ge 0.92$). |
| **`GLANCE/FLICK`** | $1.20 \text{ to } 1.55$ | $-15\text{ms} \text{ to } -5\text{ms}$ (Leading) | Sharp bottom-hand acceleration spike right before contact. |
| **`CUT/PUNCH`** | $0.90 \text{ to } 1.10$ | $-5\text{ms} \text{ to } +5\text{ms}$ (Synchronous) | Locked ratios near 1.0 with high overall accelerometer magnitude. |
| **`PULL/HOOK`** | $1.40 \text{ to } 1.80$ | $-30\text{ms} \text{ to } -10\text{ms}$ (Leading) | High gyro ratio combined with massive horizontal Z-axis rotation. |
| **`DEFLECTION/GUIDE`**| $0.15 \text{ to } 0.40$ | $+15\text{ms} \text{ to } +40\text{ms}$ (Lagging) | Near-zero bottom hand output; top hand executes late opening roll. |
| **`POWER DRIVE`** | $1.10 \text{ to } 1.35$ | $-10\text{ms} \text{ to } 0\text{ms}$ (Simultaneous) | High acceleration peaks on both sensors with extended follow-through. |
| **`SLOG`** | $\ge 1.75$ | $-25\text{ms} \text{ to } -5\text{ms}$ (Leading) | Massive bottom-hand velocity dominance across all axes. |
| **`SWEEP`** | $1.05 \text{ to } 1.30$ | $-10\text{ms} \text{ to } +5\text{ms}$ (Synchronous) | Horizontal tracking profile matching a low `s2_grav_y_mean`. |

### 📈 Analytical Diagnostics for Shot Improvement (UI Stats)
*   **Grip Dominance Index (GDI)**: Evaluates whether a player is "too bottom-handed" during vertical-bat shots. If a `DRIVE/DEFENCE` shot registers a `bottom_hand_gyro_ratio` $> 0.85$, the app triggers an efficiency deduction and coaching warning: *"Bottom hand dominant on vertical drive. Risk of aerial mistiming."*
*   **Wrist Snap Efficiency (WSE)**: Calculates the rate of change of the bottom hand's gyroscope magnitude during `GLANCE/FLICK` and `PULL/HOOK` shots. Higher acceleration curves inside the 50ms pre-impact window yield a higher power/placement efficiency rating.
*   **False-Positive Impact Filtering**: By correlating shockwave peaks between the top-hand watch and bottom-hand Polar, the app isolates true bat-ball contact from environmental vibrations (e.g., ball striking leg pads, running, or equipment taps). A valid shot requires a cross-sensor peak prominence match where $\Delta t \le 40\text{ms}$.

---

## ⚙️ Companion App Processing Pipeline (`PhoneSwingDetector.kt`)

### Step 1: Clock Drift Alignment
If a Polar directory is present, the app matches sync-tap sequences recorded at the start of the session (using physical bat ground taps). A linear regression models the relation:
$$\text{Polar\_phoneMs} = \text{watch\_wallMs} \times (1 + \text{driftRate}) + \text{offsetMs}$$
This aligns the sub-millisecond timelines of the two devices, ensuring cross-sensor lead/lag calculations are accurate down to single-digit millisecond resolutions.

### Step 2: Pass 1 — Peak Shockwave Candidates
Candidate swing locations are generated by scanning for peaks:
*   **Polar Active**: Scans Polar accelerometer data for peaks exceeding `POLAR_SHOCKWAVE_THRESHOLD`.
*   **Watch Only**: Scans watch gyroscope data for peaks exceeding `WATCH_SHOCKWAVE_THRESHOLD` ($4.00\text{ rad/s}$) or peaks crossing a secondary recovery threshold ($0.75\text{ rad/s}$) if they exhibit a topological prominence $\ge 0.50\text{ rad/s}$.

### Step 3: Backward Kinematics Validation
Each candidate peak must satisfy two backward-looking criteria to filter out walking/equipment adjustments:
1.  **Backswing Validation**: Gyroscope magnitude must peak $\ge 4.0\text{ rad/s}$ in the window $[-1.5\text{s}, -0.15\text{s}]$ before the impact peak.
2.  **Stance/Stillness Validation**: The standard deviation of the orientation quaternions must remain rigid ($\le 0.12$) over the window $[-2.5\text{s}, -1.0\text{s}]$ before the impact peak.

### Step 4: Feature Segmentation & Inference Routing
If a candidate passes validation, a $3.0$-second window ($2.5$s lookback, $0.5$s look-ahead) is streamed into the workspace.
*   The system uses the watch's kinematics to determine the absolute timestamps for boundaries of Segments $1$, $2$, and $3$.
*   If Polar data is active, the app projects these identical timestamps onto the aligned Polar timeline to extract segmented features (`s1_bottom_gyro_mag`, etc.).
*   The payload routes to the corresponding classification forest based on sensor data presence.

### Step 5: Pass 2 — Fallback Gap Scan (Misses)
To capture misses or swings that failed the strict stance/backswing validation in Pass 1, a standard forward-pass of the 4-state `SwingDetector` machine runs over the watch data. Any detected swings that do not overlap within $2.0$ seconds of a Pass 1 shot are registered as a **"Miss"** with $0\%$ efficiency.

### Step 6: Non-Maximum Suppression (NMS)
Finally, all candidates from Pass 1 and Pass 2 are sorted chronologically. If multiple detections occur within a $5.0$-second window, only the candidate with the highest estimated bat speed is preserved.

---

## 🏃 Non-Shot Baseline States

These states are filtered out by the phone app's stance gate validation and pre-shot checks, avoiding false positives:

*   **Facing Up (Stance)**
    *   *Biomechanics*: Static isometric baseline supporting the weight of the bat. Characterized by stable gravity vectors and gentle $0.5\text{--}2\text{ Hz}$ micro-oscillations on both sensors. Used to calibrate the orientation matrix.
*   **Walking Around**
    *   *Biomechanics*: Low-g, multi-axis, non-rhythmic drift as the player shifts grip, taps the crease asynchronously, or adjusts equipment.
*   **Running (Between Wickets)**
    *   *Biomechanics*: High-g, highly rhythmic periodic acceleration spikes matching running cadence ($2\text{--}4\text{ Hz}$ spikes) detected symmetrically across both arms.