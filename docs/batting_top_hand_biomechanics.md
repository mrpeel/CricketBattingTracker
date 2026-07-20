# Batting Top-Hand Biomechanics & Classification Pipeline

This document details the biomechanical classification categories, feature extraction representation, and the offline processing pipeline implemented within the Pitch Analytix Pro companion phone application.

---

## 🤖 Machine Learning Models & Output Classes

All swing detection and classification runs as an offline batch job on the Android phone app via two Random Forest classifiers.

### 1. Shot Type Classifier ([GeneratedForest.kt](file:///Users/neilkloot/Code/CricketBattingTracker/app/src/main/java/com/mrpeel/cricketbattingtracker/ml/GeneratedForest.kt))
Classifies verified active swings into one of **8 output classes** using a 20-feature input vector:

*   **`DRIVE/DEFENCE`**
    *   *Biomechanics*: Radial-to-ulnar uncocking wrist movement aligned with a straight, vertical bat face. Keeps the face straight through impact.
    *   *Shots*: Straight Drive, Cover Drive, Off Drive, On Drive, Forward Defensive, Back-foot Defensive.
*   **`GLANCE/FLICK`**
    *   *Biomechanics*: Controlled wrist flexion and forearm pronation right at impact. Dynamically closes the bat face to direct the ball down and across the body.
    *   *Shots*: Flick Shot (off pads), Leg Glance, On-Glance.
*   **`CUT/PUNCH`**
    *   *Biomechanics*: Isometric rigid wrist lockdown in a flat horizontal plane. Short kinetic path, minimal forearm rotation, and hand positioning close to the body.
    *   *Shots*: Square Cut, Cut, Back-foot Punch.
*   **`PULL/HOOK`**
    *   *Biomechanics*: Broad horizontal/transverse circular arc starting with an extended lever, forcing rapid top-wrist pronation and a downward follow-through.
    *   *Shots*: Pull Shot, Hook Shot.
*   **`DEFLECTION/GUIDE`**
    *   *Biomechanics*: Supination and late wrist extension just before contact. Relies on the ball's pace, opening the blade angle to deflect behind the batsman.
    *   *Shots*: Late Cut, Square Upper Cut, Glide/Steer.
*   **`POWER DRIVE`**
    *   *Biomechanics*: Accelerated vertical downswing with high-velocity release and extensive post-impact follow-through to loft and elevate the drive.
    *   *Shots*: Lofted Straight/Cover Drive.
*   **`SLOG`**
    *   *Biomechanics*: High-velocity horizontal/vertical swing release targeting maximum power with a broad release arc.
    *   *Shots*: Slog, Helicopter Shot.
*   **`SWEEP`**
    *   *Biomechanics*: Low-to-ground crouching swing utilizing rotational torso torque and forearm roll.
    *   *Shots*: Traditional Sweep, Slog Sweep, Reverse Sweep/Switch Hit.

### 2. Shot Quality Classifier ([GeneratedQualityForest.kt](file:///Users/neilkloot/Code/CricketBattingTracker/app/src/main/java/com/mrpeel/cricketbattingtracker/ml/GeneratedQualityForest.kt))
Evaluates the execution quality of the swing based on the same 20-feature input vector, outputting one of **3 classes** mapped in the UI to specific descriptors and efficiency ratings:

| Classifier Output | UI Display | Swing Efficiency Rating |
| :--- | :--- | :--- |
| **`good`** | Excellent | 90% |
| **`poor`** | Poor | 60% |
| **`miss`** | Miss | 0% |

*Note: Legacy maps also register `edge` -> Edge (40% efficiency) for backward compatibility.*

---

## 📊 Extracted Kinematic Features ([SwingFeatures.kt](file:///Users/neilkloot/Code/CricketBattingTracker/app/src/main/java/com/mrpeel/cricketbattingtracker/ml/SwingFeatures.kt))

The models ingest a consolidated **20-feature vector** containing 14 top-hand (watch) features and 6 optional bottom-hand (Polar) features. When Polar sensor data is absent, the bottom-hand fields automatically default to `0f`.

### Top-Hand Wrist Features (Watch-Only)
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

### Bottom-Hand Features (Polar Verity Sense)
*   `bottom_hand_gyro_peak`: Peak gyroscope magnitude on bottom hand.
*   `bottom_hand_acc_peak`: Peak accelerometer magnitude on bottom hand.
*   `bottom_hand_gyro_ratio`: Ratio of bottom-hand peak gyro to top-hand peak gyro.
*   `bottom_hand_acc_ratio`: Ratio of bottom-hand peak accelerometer to top-hand peak accelerometer.
*   `bottom_hand_time_lead_ms`: Relative lead/lag (in milliseconds) of bottom-hand peak impact over top-hand peak.
*   `bottom_hand_sync_score`: Weighted alignment metric ($1.0 - \text{timePenalty} \times 0.6 - \text{ratioPenalty} \times 0.4$) mapped to a $[0, 100]$ score.

---

## ⚙️ Companion App Processing Pipeline ([PhoneSwingDetector.kt](file:///Users/neilkloot/Code/CricketBattingTracker/app/src/main/java/com/mrpeel/cricketbattingtracker/services/PhoneSwingDetector.kt))

Processing runs entirely offline on the companion phone after the watch delivers a zipped session folder containing the binary logs.

### Step 1: Clock Drift Alignment
If a Polar directory is present, the app matches sync-tap sequences recorded at the start of the session (using physical bat ground taps). A linear regression models the relation:
$$\text{Polar\_phoneMs} = \text{watch\_wallMs} \times (1 + \text{driftRate}) + \text{offsetMs}$$
This aligns the sub-millisecond timelines of the two devices.

### Step 2: Pass 1 — Peak Shockwave Candidates
Candidate swing locations are generated by scanning for peaks:
*   **Polar Active**: Scans Polar accelerometer data for peaks exceeding `POLAR_SHOCKWAVE_THRESHOLD`.
*   **Watch Only**: Scans watch gyroscope data for peaks exceeding `WATCH_SHOCKWAVE_THRESHOLD` ($4.00\text{ rad/s}$) or peaks crossing a secondary recovery threshold ($0.75\text{ rad/s}$) if they exhibit a topological prominence $\ge 0.50\text{ rad/s}$.

### Step 3: Backward Kinematics Validation
Each candidate peak must satisfy two backward-looking criteria to filter out walking/equipment adjustments:
1.  **Backswing Validation**: Gyroscope magnitude must peak $\ge 4.0\text{ rad/s}$ in the window $[-1.5\text{s}, -0.15\text{s}]$ before the impact peak.
2.  **Stance/Stillness Validation**: The standard deviation of the orientation quaternions must remain rigid ($\le 0.12$) over the window $[-2.5\text{s}, -1.0\text{s}]$ before the impact peak.

### Step 4: Random Forest Inference
If a candidate passes validation, a $3.0$-second window ($2.5$s lookback, $0.5$s look-ahead) is streamed into a local `SwingDetector` workspace to extract features. The 20 features are passed to `GeneratedForest` and `GeneratedQualityForest` to classify the shot type and quality.

### Step 5: Pass 2 — Fallback Gap Scan (Misses)
To capture misses or swings that failed the strict stance/backswing validation in Pass 1, a standard forward-pass of the 4-state `SwingDetector` machine runs over the entire watch data. Any detected swings that do not overlap within $2.0$ seconds of a Pass 1 shot are registered as a **"Miss"** with $0\%$ efficiency.

### Step 6: Non-Maximum Suppression (NMS)
Finally, all candidates from Pass 1 and Pass 2 are sorted chronologically. If multiple detections occur within a $5.0$-second window, only the candidate with the highest estimated bat speed is preserved.

---

## 🏃 Non-Shot Baseline States

These states are filtered out by the phone app's stance gate validation and pre-shot checks, avoiding false positives:

*   **Facing Up (Stance)**
    *   *Biomechanics*: Static isometric baseline supporting the weight of the bat. Characterized by stable gravity vectors and gentle $0.5\text{--}2\text{ Hz}$ micro-oscillations. Used to calibrate the orientation matrix.
*   **Walking Around**
    *   *Biomechanics*: Low-g, multi-axis, non-rhythmic drift as the player shifts grip or adjusts equipment.
*   **Running (Between Wickets)**
    *   *Biomechanics*: High-g, highly rhythmic periodic acceleration spikes matching running cadence ($2\text{--}4\text{ Hz}$ spikes).