# Biomechanical Flaws, Coaching Notes & Audio Feedback Reference

> **Single Source of Truth**: This document catalogues the complete set of real-time shot-invariant audio cues, procedural acoustic earcons, per-shot timeline coaching notes, longitudinal repertoire diagnostics, and corrective training drills active in **Pitch Analytix Pro**.
>
> **Maintenance Rule**: Whenever thresholds, coaching text, earcons, or diagnostic rules are modified in [`LiveKinematicCoach.kt`](file:///Users/neilkloot/Code/CricketBattingTracker/app/src/main/java/com/mrpeel/cricketbattingtracker/coaching/LiveKinematicCoach.kt), [`EarconAudioPlayer.kt`](file:///Users/neilkloot/Code/CricketBattingTracker/app/src/main/java/com/mrpeel/cricketbattingtracker/coaching/EarconAudioPlayer.kt), [`BiomechanicalUiMapper.kt`](file:///Users/neilkloot/Code/CricketBattingTracker/app/src/main/java/com/mrpeel/cricketbattingtracker/ui/biomechanics/BiomechanicalUiMapper.kt), or [`DiagnosticRulesEngine.kt`](file:///Users/neilkloot/Code/CricketBattingTracker/app/src/main/java/com/mrpeel/cricketbattingtracker/analytics/DiagnosticRulesEngine.kt), this file must be updated in lockstep.

---

## 🏗️ Architectural Separation: Real-Time Shot-Invariant Audio vs. Post-Session Shot-Specific Analysis

Because the Wear OS watch logs 423 Hz sensor data locally during a session and only transfers its ZIP archive when the session ends, **live in-ear coaching** and **post-session analysis** operate on different sensor streams with distinct responsibilities:

| Pipeline | When It Runs | Sensors Used | Biomechanical Scope |
| :--- | :--- | :--- | :--- |
| **1. Live In-Ear Audio Coaching** ([`LiveKinematicCoach.kt`](file:///Users/neilkloot/Code/CricketBattingTracker/app/src/main/java/com/mrpeel/cricketbattingtracker/coaching/LiveKinematicCoach.kt)) | **Real-Time** ($T+300\text{ ms}$ after ball contact) | **Polar Bat Sensor ONLY** (416 Hz BLE stream to phone) | **100% Shot-Invariant Biomechanics.** Never guesses what shot was played. Evaluates universal swing laws across the `[-220ms, 0ms]` pre-impact window: downswing velocity retention, 3D swing plane stability, late wrist rescue jerk, and over-swinging loss of shape. |
| **2. Post-Session Timeline & Repertoire Insights** ([`PhoneSwingDetector.kt`](file:///Users/neilkloot/Code/CricketBattingTracker/app/src/main/java/com/mrpeel/cricketbattingtracker/services/PhoneSwingDetector.kt), [`TcnModelRunner.kt`](file:///Users/neilkloot/Code/CricketBattingTracker/app/src/main/java/com/mrpeel/cricketbattingtracker/ml/TcnModelRunner.kt)) | **Offline** (after watch finishes ZIP sync at session end) | **Watch (423 Hz) + Polar (423 Hz)** + 3D AHRS Quaternions | **Shot-Specific Biomechanics.** Runs the **10-Layer Multi-Tier TCN (`tcn_ultimate_baseline.onnx`)** + 3D AHRS Orientation gates to classify the 8 canonical shot types, then maps shot-specific coaching via [`BiomechanicalUiMapper.kt`](file:///Users/neilkloot/Code/CricketBattingTracker/app/src/main/java/com/mrpeel/cricketbattingtracker/ui/biomechanics/BiomechanicalUiMapper.kt) and longitudinal drills via [`DiagnosticRulesEngine.kt`](file:///Users/neilkloot/Code/CricketBattingTracker/app/src/main/java/com/mrpeel/cricketbattingtracker/analytics/DiagnosticRulesEngine.kt). |

---

## 🎧 Part 1: Real-Time Shot-Invariant In-Ear Audio Coaching & Procedural Earcons

**Source Files**:
* [`LiveKinematicCoach.kt`](file:///Users/neilkloot/Code/CricketBattingTracker/app/src/main/java/com/mrpeel/cricketbattingtracker/coaching/LiveKinematicCoach.kt)
* [`EarconAudioPlayer.kt`](file:///Users/neilkloot/Code/CricketBattingTracker/app/src/main/java/com/mrpeel/cricketbattingtracker/coaching/EarconAudioPlayer.kt)
* [`LiveCoachingTtsManager.kt`](file:///Users/neilkloot/Code/CricketBattingTracker/app/src/main/java/com/mrpeel/cricketbattingtracker/coaching/LiveCoachingTtsManager.kt)
* [`BiomechanicalCoachingPlaybookCard.kt`](file:///Users/neilkloot/Code/CricketBattingTracker/app/src/main/java/com/mrpeel/cricketbattingtracker/ui/insights/BiomechanicalCoachingPlaybookCard.kt)

### 1.1 Impact Gate & Pre-Impact Window Extraction (`[-220ms, 0ms]`)
When the Polar Verity Sense streams accelerometer and gyroscope samples (`PolarSenseService.kt`), an impact evaluation is triggered only when:
1. **Accelerometer Spike**: `magG >= 10.0g` (`ACC_IMPACT_THRESHOLD_G = 10.0f`)
2. **Cooldown**: At least `1800 ms` since the previous evaluated impact (`IMPACT_COOLDOWN_MS = 1800L`)
3. **Active Downswing Strictly Inside `[-220ms, 0ms]`**: The gyroscope ring buffer within the `220 ms` window immediately preceding the impact must have `peakGyroRadS >= 5.5 rad/s` (`MIN_SWING_GYRO_RAD_S = 5.5f`). *Practice swings or waggles older than 220 ms are ignored, preventing stationary stance taps from triggering false cues.*

### 1.2 Shot-Invariant Kinematic Metrics (`ShotInvariantMetrics`)
Across all 1,289 empirical bat-mounted shots (spanning all 15 shot types: Drives, Flicks, Glances, Cuts, Punches, Pulls, Slogs, Sweeps, Guides, and Defenses), the following 6 metrics are invariant to the shot played:

1. **`peakGyroRadS` & `speedKmh`**:
   * Peak 3D angular velocity magnitude $\omega_{\text{peak}} = \max \|\vec{\omega}(t)\|$ (in `rad/s`) inside `[-220ms, 0ms]`.
   * Converted to sweet-spot linear speed via `speedKmh = peakGyroRadS * 3.4f` (`GYRO_TO_KMH = 3.4f`, calibrated so the median bat-handle angular velocity of `20.6 rad/s` matches the `70 km/h` timeline bat speed).
2. **`velocityRetention` ($\omega_{\text{impact}} / \omega_{\text{peak}}$)**:
   * Ratio of mean angular velocity over the final 4 samples (~10 ms) at impact to $\omega_{\text{peak}}$ in the downswing.
   * **Empirical Shot-Invariance**: Median `velocityRetention` is **`0.94–0.97`** across every single shot class in cricket. Dropping below `0.68` on an active stroke means the batter peaked early and decelerated/checked their swing before hitting the ball.
3. **`accelSlope` ($\Delta\omega / \omega_{\text{peak}}$)**:
   * Normalized velocity change across the final `17` samples (~40 ms) before impact: $(\bar{\omega}_{\text{last 4}} - \bar{\omega}_{\text{first 4}}) / \omega_{\text{peak}}$. Positive values indicate accelerating through the ball; strongly negative values (`< -0.22`) indicate pre-impact deceleration.
4. **`planeWobbleDeg` (3D Swing Plane Stability)**:
   * Mean angular deviation (in degrees) between the instantaneous unit rotation axis $\hat{u}(t) = \vec{\omega}(t) / \|\vec{\omega}(t)\|$ and the mean unit rotation axis $\bar{u}$ over the final `18` samples (~45 ms) before contact:
     $$\text{planeWobbleDeg} = \frac{1}{N} \sum_{t} \arccos\!\left(\hat{u}(t) \cdot \bar{u}\right) \times \frac{180}{\pi}$$
   * **Empirical Shot-Invariance**: Because deviation is measured relative to the stroke's *own* active plane, it is completely independent of whether the swing is vertical (Drive: $0^\circ$), diagonal (Flick/Cut: $45^\circ$), or horizontal (Pull/Sweep: $75^\circ$). Across all 15 shot classes, median `planeWobbleDeg` is **`6.2°–9.8°`**. It only exceeds `16.5°–22.0°` when the batter loops, steers, or changes plane mid-downswing.
5. **`twistSpikeRatio` ($\Delta \omega_y / \omega_{\text{peak}}$)**:
   * Axial handle roll range ($\max(\omega_y) - \min(\omega_y)$) over the final `13` samples (~30 ms) divided by `peakGyroRadS`. Normalizing by swing speed and pairing with `planeWobbleDeg > 12°` ensures that smooth, natural forearm pronation on a **Flick** or **Pull** (where `planeWobbleDeg` is ~6.5°) is **never** flagged as a fault.
6. **`axialJerkRadS` ($\max |\Delta \omega_y|$)**:
   * Maximum sample-to-sample axial handle roll jump (in `rad/s`) in the final 30 ms before impact, capturing sudden blade twist/instability at contact.

### 1.3 Post-Impact Audio Delivery Timeline
To avoid masking the physical sound of the ball hitting the bat or interfering with voice narration (`AudioRecordService`), audio playback follows a strict millisecond schedule after impact ($T = 0\text{ ms}$):
* **$T + 0\text{ to }300\text{ ms}$**: **Complete Silence** (`SILENCE_DELAY_MS = 300L`) — preserves the natural acoustic crack of ball on willow.
* **$T + 300\text{ to }520\text{ ms}$**: **Procedural Earcon Plays** (~120–250 ms duration, 22.05 kHz 16-bit mono PCM via `AudioTrack.MODE_STATIC`).
* **$T + 550\text{ to }1050\text{ ms}$**: **Spoken TTS Cue** (2-syllable motor cue at `1.25x` speech rate) or **Bat Speed Integer** (`"${speedKmh.toInt()}"`).
* **$T + 1100\text{ ms}$ onwards**: Audio channel closes; Bluetooth microphone is clear for user ground-truth voice narration.

### 1.4 Three-Stage Training System (`CoachingMode`)
| Stage Mode | Fault Behavior | Clean Stroke (`CLEAN_STROKE`) Behavior | Purpose |
| :--- | :--- | :--- | :--- |
| **Stage 1: Calibration** (`STAGE_1_CALIBRATION`) | Plays **Fault Earcon** ($T+300\text{ms}$) + speaks **Voice Cue** ($T+550\text{ms}$) | Plays **Crystal Chime** ($T+300\text{ms}$) + speaks **Bat Speed Integer** ($T+550\text{ms}$) | Builds the Pavlovian mental link between each acoustic earcon and its physical correction. |
| **Stage 2: Flow State** (`STAGE_2_FLOW_STATE`) | Plays **Fault Earcon ONLY** ($T+300\text{ms}$, silent by $T+520\text{ms}$) | Plays **Crystal Chime** ($T+300\text{ms}$) + speaks **Bat Speed Integer** ($T+550\text{ms}$) | Zero verbal clutter during faults; instant 0.2s acoustic feedback. |
| **Stage 3: Silent Diagnostic** (`STAGE_3_SILENT_DIAGNOSTIC`) | Plays **Fault Earcon ONLY if the exact same fault occurs twice in a row** (`isRepeatFault`) | **Completely Silent** | Filters out one-off anomalies; only interrupts when a technical flaw repeats consecutively. |

### 1.5 Shot-Invariant Evaluation Order & Thresholds (`diagnoseShotInvariant`)
Rules are evaluated in the following `1 -> 8` order:

| Priority | Enum (`LiveShotFault`) | Family | Trigger Condition (`diagnoseShotInvariant`) | Spoken Cue (TTS) | Procedural Earcon Synthesis (`EarconAudioPlayer.kt`) |
| :---: | :--- | :--- | :--- | :--- | :--- |
| **1** | `OVERSWING_LOSS_OF_SHAPE` | D. Tempo & Balance Envelope | `peakGyroRadS > 31.0f && (planeWobbleDeg > 14.5f \|\| velocityRetention < 0.80f)` | **`"Hold your shape"`** | **Wobbly Detuned Siren**: $600\text{ Hz}$ sine with $\pm 80\text{ Hz}$ LFO wobble at $8\text{ Hz}$ over $250\text{ ms}$ |
| **2** | `EARLY_PEAK_DECELERATION` | A. Downswing Timing & Continuity | `peakGyroRadS >= 13.5f && (velocityRetention < 0.68f \|\| accelSlope < -0.22f)` | **`"Swing through"`** | **Tape-Stop / Power-Down Drop**: Exponential pitch drop $600\text{ Hz} \rightarrow 150\text{ Hz}$ with $(1-t)^{1.5}$ amplitude decay over $200\text{ ms}$ |
| **3** | `STALLED_REACH_PUSH` | A. Downswing Timing & Continuity | `peakGyroRadS in 9.5f..16.0f && velocityRetention in 0.68f..0.78f && accelSlope < -0.12f` | **`"Let it come"`** | **Dry Woodblock Double-Rap**: Two $40\text{ ms}$ bursts of $800\text{ Hz}$ tone + noise separated by a $40\text{ ms}$ gap ($120\text{ ms}$ total) |
| **4** | `MID_SWING_PLANE_LOOP` | B. 3D Swing Plane Stability | `planeWobbleDeg > 22.0f` | **`"Watch the ball"`** | **Inverted 'U' Pitch Bend**: Sine bend $700\text{ Hz} \rightarrow 350\text{ Hz} \rightarrow 800\text{ Hz}$ over $240\text{ ms}$ |
| **5** | `OUT_OF_PLANE_WIPE` | B. 3D Swing Plane Stability | `planeWobbleDeg > 16.5f && twistSpikeRatio > 0.38f` | **`"Head to the ball"`** | **Metallic Scrape**: Ring-modulated white noise $\times$ sine carrier sweeping $2200\text{ Hz} \rightarrow 700\text{ Hz}$ over $200\text{ ms}$ |
| **6** | `LATE_WRIST_RESCUE` | C. Impact Wrist & Face Control | `twistSpikeRatio > 0.55f && planeWobbleDeg > 12.0f` | **`"Roll smoothly"`** | **Tight Dissonant Minor-Second Buzz**: Clipped dual-tone $500\text{ Hz} + 530\text{ Hz}$ beating wave over $200\text{ ms}$ |
| **7** | `IMPACT_FACE_TWIST` | C. Impact Wrist & Face Control | `axialJerkRadS > 5.5f && velocityRetention < 0.82f` | **`"Tighten grip"`** | **Brassy High-to-Low "Crack"**: Sawtooth wave drop $1400\text{ Hz} \rightarrow 500\text{ Hz}$ with fast exponential decay over $180\text{ ms}$ |
| **8** | `CLEAN_STROKE` | *None (Clean Hit)* | *Fallback when no fault rule (1–7) triggers* | **`"${speedKmh.toInt()}"`** *(or `"Solid"` in static catalog)* | **Crystal Harmonic Dual Chime**: Pure harmonic $880\text{ Hz} (65\%) + 1760\text{ Hz} (35\%)$ chime over $150\text{ ms}$ |

### 1.6 Detailed Playbook Coaching Notes & Acoustic Intuition (All 7 Shot-Invariant Faults)

#### Family A: Downswing Timing & Continuity (*Acoustic Theme: Power Drop & Stalled Transients*)
1. **`EARLY_PEAK_DECELERATION` — Checked / Decelerating Swing**
   * **Spoken Cue**: `"Swing through"`
   * **Failure Description**: Bat peaked early in downswing and lost >32% speed before contact.
   * **Acoustic Intuition**: Tape-stop pitch & volume drop ($600 \rightarrow 150\text{ Hz}$) directly mirrors your bat losing angular velocity before ball contact.
   * **Coaching Note & Biomechanical Fix**: *"Regardless of what shot you play, peak bat speed should occur right into ball contact (~95% retention). Slowing down by >32% before impact happens when you commit too early, reach out in front of your eyeline, or get jammed by the bounce. Wait for the ball to enter your hitting zone and accelerate right through contact."*

2. **`STALLED_REACH_PUSH` — Reaching / Stalled Hand Push**
   * **Spoken Cue**: `"Let it come"`
   * **Failure Description**: Hands pushed out flatly toward the ball without accelerating through contact.
   * **Acoustic Intuition**: Dry woodblock double-rap sounds rigid, brittle, and pushed—the acoustic opposite of a whip-like swing or soft absorption.
   * **Coaching Note & Biomechanical Fix**: *"Your bat speed plateaued and pushed into contact with stiff arms rather than whipping smoothly through the ball or absorbing it behind your eyes. Let the ball travel deeper toward your front knee before releasing your hands."*

#### Family B: 3D Swing Plane Stability (*Acoustic Theme: Pitch Bends & Scraping Sweeps*)
3. **`MID_SWING_PLANE_LOOP` — Late Line/Length Adjustment (Mid-Swing Loop)**
   * **Spoken Cue**: `"Watch the ball"`
   * **Failure Description**: Picked up line/length late; 3D swing axis shifted >22° in final 45 ms.
   * **Acoustic Intuition**: Inverted 'U' pitch bend ($700 \rightarrow 350 \rightarrow 800\text{ Hz}$) mirrors the bat dipping off its initial downswing path and looping back to find the ball.
   * **Coaching Note & Biomechanical Fix**: *"A >22° shift in your 3D swing axis in the final 45 ms happens when you pick up the line or length late and have to redirect the bat mid-downswing. Watch the ball closely out of the release point to read the line and length early, then commit to that single path through the shot."*

4. **`OUT_OF_PLANE_WIPE` — Early Shoulder Rotation (Wiping Across)**
   * **Spoken Cue**: `"Head to the ball"`
   * **Failure Description**: Front shoulder rotated open early, pulling bat >16.5° off-plane across the ball.
   * **Acoustic Intuition**: Metallic bandpass scrape ($2200 \rightarrow 700\text{ Hz}$) sounds like the blade casting and scraping obliquely across the seam of the ball.
   * **Coaching Note & Biomechanical Fix**: *"Your swing plane drifted by >16.5° in the final 45 ms while the handle twisted across the trajectory. This happens when your front shoulder rotates open too early and pulls your hands across the line. Keep your head moving toward the ball so your lead shoulder stays aligned through contact."*

#### Family C: Impact Wrist & Face Control (*Acoustic Theme: Dissonant & Phase-Twisted Tones*)
5. **`LATE_WRIST_RESCUE` — Jerky Last-Second Wrist Snap**
   * **Spoken Cue**: `"Roll smoothly"`
   * **Failure Description**: Violent wrist jerk (>55% of swing speed) in final 30 ms while off-plane.
   * **Acoustic Intuition**: Tight minor-second buzz ($500 + 530\text{ Hz}$) creates beating frequencies that sound "crossed" and pinched, mirroring a sudden jerky wrist snap.
   * **Coaching Note & Biomechanical Fix**: *"Active wrist work on a flick or pull is great when rolled progressively through the hitting zone. This fault only triggers when your wrists jerk violently in the final 30 ms while the swing plane is shifting (>12°). Avoid snatching at the ball late—roll your wrists smoothly through the arc."*

6. **`IMPACT_FACE_TWIST` — Loose Grip / Bat Twisting at Impact**
   * **Spoken Cue**: `"Tighten grip"`
   * **Failure Description**: Grip too loose at contact; bat twisted sharply (>5.5 rad/s) with speed loss.
   * **Acoustic Intuition**: Brassy sawtooth drop ($1400 \rightarrow 500\text{ Hz}$) sounds harsh and over-twisted, mimicking the bat twisting in a loose grip at contact.
   * **Coaching Note & Biomechanical Fix**: *"The bat handle experienced a sharp axial twist spike right at impact alongside velocity loss because your grip was too loose at the moment of contact, allowing the ball to turn the bat in your hands. Firm up your grip through ball contact so the face stays square."*

#### Family D: Tempo & Balance Envelope (*Acoustic Theme: Detuned LFO Siren*)
7. **`OVERSWING_LOSS_OF_SHAPE` — Over-Swinging (Loss of Shape)**
   * **Spoken Cue**: `"Hold your shape"`
   * **Failure Description**: Swinging at >31 rad/s while losing plane stability (>14.5°) or decelerating.
   * **Acoustic Intuition**: Wobbly detuned siren ($600 \pm 80\text{ Hz}$) sounds "out of balance" and spinning off-axis, matching torso/head drift from over-hitting.
   * **Coaching Note & Biomechanical Fix**: *"High bat speed is great when the swing stays on-plane and accelerates through contact. This fault only triggers when extreme effort (>31 rad/s) causes your swing plane to wobble (>14.5°) or decelerate before contact because your torso spun ahead of your hands. Swing at 85–90% effort with a still head and let clean timing generate power."*

---

## 📱 Part 2: Post-Session Shot Timeline Card Coaching (`BiomechanicalUiMapper.kt`)

**Source File**: [`BiomechanicalUiMapper.kt`](file:///Users/neilkloot/Code/CricketBattingTracker/app/src/main/java/com/mrpeel/cricketbattingtracker/ui/biomechanics/BiomechanicalUiMapper.kt)

When a session is processed offline by `PhoneSwingDetector.kt` and `TcnModelRunner.kt`, each shot card on the Timeline displays two progress bars and a coaching note based on:
* `shotClass`: TCN-classified canonical stroke (`PULL/HOOK/SLOG`, `DRIVE/DEFENCE`, `POWER DRIVE`, `CUT/PUNCH`, `GLANCE/FLICK`, `DEFLECTION/GUIDE`, `SWEEP`)
* `timeLeadMs` ($\Delta t$): Bottom-hand / Bat peak time minus Top-hand watch impact time (ms)
* `gyroRatio`: Polar peak angular velocity $\div$ Watch peak angular velocity
* `accRatio`: Polar peak linear acceleration $\div$ Watch peak linear acceleration
* `polarMountMode`: `"BAT_HANDLE"`, `"WRIST"`, or `null`/`"NONE"`

### 2.1 Bat-Mounted Sensor Mode (`polarMountMode == "BAT_HANDLE"`)
Card section headers dynamically display: **`BAT TIMING & RELEASE`**, **`BAT SPEED & FLOW`**, and **`COACHING ACTION`**. All two-handed wrist jargon is replaced with plain-English bat flow cues:

| Shot Class | Metric | Condition | Title (Slider %) | Description | Warning? | Coaching Action (`coachingInsight`) |
| :--- | :--- | :--- | :--- | :--- | :---: | :--- |
| **`PULL/HOOK`** | Timing | `-25..+5 ms` | **Fast Blade Whip** (90%) | The bat whipped through the hitting zone with great timing, meeting the ball cleanly out in front. | No | *"Action: Keep that aggressive hip turn and let the bat follow through over your shoulder."* |
| | Timing | `> +5 ms` | **Bat Dragging Behind** (20%) | Your body turned but the bat lagged behind your hands, causing you to slice or hit under the ball. | **Yes (Amber)** | *"Action: Commit your bat into the swing as you turn — let the bat head whip around your body."* |
| | Timing | `< -25 ms` | **Early Swing** (40%) | You swung the bat through too early before the ball arrived, hitting across the line. | No | *"Action: Wait for the ball to reach chest height before pulling through."* |
| | Speed/Flow | `gyroRatio >= 1.30` | **Full Power Arc** (90%) | Fast, uninterrupted bat acceleration through the hitting zone. | No | *(Uses Timing Action)* |
| | Speed/Flow | `gyroRatio < 1.00` | **Checked Swing** (30%) | You checked your swing, losing bat speed and power into contact. | No | If not warning: *"Action: Swing freely through the line without tightening your shoulders."* |
| | Speed/Flow | `1.00..1.29` | **Controlled Swing** (65%) | Good steady bat speed through the horizontal arc. | No | *(Uses Timing Action)* |
| **`DRIVE/DEFENCE`** | Timing | `-15..+10 ms` | **Clean Pendulum Flow** (85%) | The bat swung smoothly through the line of your hands, meeting the ball right under your eyes. | No | *"Action: Great shape. Keep that relaxed tempo and let the bat flow down the ground."* |
| | Timing | `> +10 ms` | **Bat Lagging Behind Hands** (25%) | Your hands pushed out ahead of the bat, leaving the blade trailing behind and opening the face. | **Yes (Amber)** | *"Action: Lead with your front elbow and let the bat follow down the line — don't push your hands out ahead."* |
| | Timing | `< -15 ms` | **Early Wrist Flick** (35%) | You flicked the bat out too early, closing the blade before reaching the ball. | No | *"Action: Keep your top hand firm and wait for the ball to get under your eyes before swinging through."* |
| | Speed/Flow | `gyroRatio >= 1.15` | **Crisp Bat Flow** (85%) | Smooth bat acceleration through the line of the ball. | No | *(Uses Timing Action)* |
| | Speed/Flow | `gyroRatio < 0.95` | **Pushed with Stiff Arms** (30%) | The shot was pushed with rigid arms rather than swung with smooth bat flow. | No | If not warning: *"Action: Relax your grip and shoulders so the bat swings freely like a pendulum."* |
| | Speed/Flow | `0.95..1.14` | **Controlled Downswing** (65%) | Balanced bat speed through the vertical line. | No | *(Uses Timing Action)* |
| **`POWER DRIVE`** | Timing | `-15..+5 ms` | **Power Loft Timing** (90%) | Bat accelerated smoothly through the ball, creating natural lift and clean power. | No | *"Action: Great power. Finish high into your follow-through to maximize distance."* |
| | Timing | `> +5 ms` | **Stalled Lift** (25%) | Hands reached forward without bat head speed, keeping the shot grounded or mistimed. | **Yes (Amber)** | *"Action: Swing up and through the line of the ball into a high follow-through."* |
| | Timing | `< -15 ms` | **Early Power Release** (45%) | Bat released early before reaching the hitting slot, losing peak velocity. | No | *"Action: Hold your shape slightly longer before accelerating up through contact."* |
| | Speed/Flow | `gyroRatio >= 1.30` | **Explosive Blade Speed** (90%) | High bat acceleration lifting the ball cleanly with great carry. | No | *(Uses Timing Action)* |
| | Speed/Flow | `gyroRatio < 1.05` | **Under-Powered** (30%) | Swing lacked bat acceleration through the ball. | No | If not warning: *"Action: Commit to hitting through the line with full arm extension."* |
| | Speed/Flow | `1.05..1.29` | **Solid Drive Speed** (65%) | Good positive acceleration through impact. | No | *(Uses Timing Action)* |
| **`CUT/PUNCH`** | Timing | `-10..+10 ms` | **Crisp Square Slap** (85%) | Bat and hands met the ball together with sharp timing, cutting down on the ball. | No | *"Action: Excellent contact point. Keep hitting down on the ball through point."* |
| | Timing | `> +10 ms` | **Bat Trailing Hands** (20%) | Hands pushed toward point before the bat got there, leaving the blade face open. | **Yes (Amber)** | *"Action: Wait for the ball to get closer, then snap the bat down and through."* |
| | Timing | `< -10 ms` | **Early Reach** (45%) | Reached out too early for the ball outside off stump. | No | *"Action: Let the ball come to you before playing the cut."* |
| | Speed/Flow | `gyroRatio >= 1.10` | **Sharp Blade Snap** (85%) | Fast bat acceleration through the point boundary. | No | *(Uses Timing Action)* |
| | Speed/Flow | `gyroRatio < 0.90` | **Guarded Push** (30%) | Pushed gently rather than hitting firmly through the ball. | No | If not warning: *"Action: Get on your back foot and hit firmly down through the ball."* |
| | Speed/Flow | `0.90..1.09` | **Controlled Cut** (60%) | Steady bat speed through the square drive line. | No | *(Uses Timing Action)* |
| **`GLANCE/FLICK`** | Timing | `-15..0 ms` | **Crisp Wrist Roll** (90%) | Bat timed the ball off the pads cleanly, rolling the wrists over impact. | No | *"Action: Clean deflection. Keep working the ball off your front pad into the gaps."* |
| | Timing | `> +5 ms` | **Late Blade** (20%) | Bat arrived late to the ball, risking an inside edge onto the stumps. | **Yes (Amber)** | *"Action: Get your bat down earlier and meet the ball in front of your front pad."* |
| | Timing | `< -15 or 0..5 ms` | **Early Flick** (40%) | Closed the bat face too early before ball contact. | No | *"Action: Wait for the ball to reach your pad before rolling your wrists."* |
| | Speed/Flow | `gyroRatio >= 1.10` | **Sharp Deflection** (85%) | Quick bat acceleration working the ball into the leg-side gap. | No | *(Uses Timing Action)* |
| | Speed/Flow | `gyroRatio < 0.90` | **Passive Touch** (35%) | Bat was stationary or pushed gently without active wrist snap. | No | If not warning: *"Action: Work the ball off your legs with a positive roll of the bat."* |
| | Speed/Flow | `0.90..1.09` | **Controlled Glance** (65%) | Good touch working the ball off the pads. | No | *(Uses Timing Action)* |
| **`DEFLECTION/GUIDE`** | Timing | `+10..+35 ms` | **Soft-Hand Guide** (85%) | Bat relaxed naturally behind the hands to run the ball off the open face. | No | *"Action: Perfect soft touch to run the ball down to third man."* |
| | Timing | `< +5 ms` | **Pushed Hard at Ball** (25%) | Pushed the bat firmly into the ball instead of letting the ball glance off the face. | **Yes (Amber)** | *"Action: Soften your hands and let the pace of the ball deflect off the blade."* |
| | Timing | `5..9 or >35 ms` | **Late Glide** (55%) | Steered the ball behind square with decent timing. | No | *"Action: Keep your hands relaxed right through contact."* |
| | Speed/Flow | `gyroRatio <= 0.85` | **Controlled Soft Hands** (85%) | Great soft touch, absorbing the ball's speed to drop it into the gap. | No | *(Uses Timing Action)* |
| | Speed/Flow | `gyroRatio > 1.15` | **Swung Too Hard** (25%) | Swung into the ball instead of guiding it, risking an edge to the slips. | No | If not warning: *"Action: Relax your grip and play with softer hands down to third man."* |
| | Speed/Flow | `0.86..1.15` | **Firm Deflection** (60%) | Controlled touch behind square. | No | *(Uses Timing Action)* |
| **`SLOG`** | Timing | `-20..+5 ms` | **Full Arc Commitment** (90%) | The bat swung through with maximum speed and clean timing right into contact. | No | *"Action: Great aggressive swing. Keep your head still and swing through the line."* |
| | Timing | `> +5 ms` | **Hesitant Swing** (25%) | Hands drifted forward and bat lagged, losing loft and power. | **Yes (Amber)** | *"Action: Commit to your swing path with a full, free-flowing swing."* |
| | Timing | `< -20 ms` | **Rushed Swing** (45%) | Swung across the line too early before the ball arrived. | No | *"Action: Keep your eyes on the ball and swing through its full arc."* |
| | Speed/Flow | `gyroRatio >= 1.40` | **High Bat Speed** (95%) | Fast bat acceleration through the hitting zone. | No | *(Uses Timing Action)* |
| | Speed/Flow | `gyroRatio < 1.15` | **Restricted Swing** (30%) | Restricted swing arc, losing power. | No | If not warning: *"Action: Keep your arms extended and swing freely through the line."* |
| | Speed/Flow | `1.15..1.39` | **Solid Power** (70%) | Good bat speed through the arc. | No | *(Uses Timing Action)* |
| **`SWEEP`** | Timing | `-15..+5 ms` | **Clean Low Sweep** (85%) | The bat swung low and level across the front knee right on time. | No | *"Action: Keep your head over your front knee and follow through along the turf."* |
| | Timing | `> +5 ms` | **Bat Trailed Body** (25%) | Torso turned but the bat was left behind, hitting across the top of the ball. | **Yes (Amber)** | *"Action: Bring the bat through with your head and shoulders as one unit."* |
| | Timing | `< -15 ms` | **Early Sweep** (45%) | Swept early before the ball pitched. | No | *"Action: Wait for the ball to pitch before committing your blade to the sweep."* |
| | Speed/Flow | `gyroRatio >= 1.10` | **Full Sweep Flow** (85%) | Solid bat flow along the horizontal plane. | No | *(Uses Timing Action)* |
| | Speed/Flow | `gyroRatio < 0.90` | **Arm Poke** (30%) | Poked with the arms rather than sweeping cleanly. | No | If not warning: *"Action: Get down low on your front knee and swing the blade in a wide, level arc."* |
| | Speed/Flow | `0.90..1.09` | **Controlled Sweep** (65%) | Good horizontal blade path across the stumps. | No | *(Uses Timing Action)* |

### 2.2 Dual-Wrist Sensor Mode (`polarMountMode == "WRIST"`)
When the Polar sensor is worn on the trailing (bottom) wrist, card section headers display **`SWING SEQUENCING`**, **`POWER PATTERN`**, and **`COACHING INSIGHT`**:

| Shot Class | Sequencing Rules (`timeLeadMs`) | Power Pattern Rules (`gyroRatio`, `accRatio`) | Coaching Insight |
| :--- | :--- | :--- | :--- |
| **`PULL/HOOK`** | • `-30..-10 ms`: **Perfect Snap** (85%)<br>• `> +40 ms`: **Dragged Blade** (15%, ⚠️ Warning)<br>• `0..+40 ms`: **Late Release** (35%)<br>• Other: **Slight Lag** (50%) | • `acc >= 1.20 && gyro <= 0.22`: **Explosive Punch** (90%)<br>• `acc < 0.80`: **Weak Bottom Hand** (25%)<br>• Other: **Moderate Drive** (60%) | *"Rotate hips early and ensure bottom wrist snaps through the arc before contact for maximum pull shot power."* |
| **`DRIVE/DEFENCE`** | • `+5..+20 ms`: **Clean Extension** (80%)<br>• `< 0 ms`: **Early Wrist Snap** (20%)<br>• Other: **Dragged Blade** (30%, ⚠️ Warning) | • `gyro > 0.85`: **Hard Bottom Hand** (15%, ⚠️ Warning)<br>• `gyro in 0.45..0.70`: **Top-Hand Control** (85%)<br>• Other: **Sub-optimal Grip** (50%) | *"Keep your bottom hand grip light to maintain top-hand control down the slot and prevent closing the face."* |
| **`GLANCE/FLICK`** | • `-15..-5 ms`: **Perfect Timing** (90%)<br>• `> +10 ms`: **Delayed Snap** (20%, ⚠️ Warning)<br>• Other: **Early Flick** (40%) | • `gyro >= 1.20`: **Dynamic Wrist Snap** (85%)<br>• `< 1.20`: **Passive Deflection** (35%) | *"Time the bottom wrist pronation precisely at impact line to glance off pads cleanly."* |
| **`CUT/PUNCH`** | • `-5..+5 ms`: **Synchronous Wrist Lock** (85%)<br>• `> +20 ms`: **Lagging Cut Face** (20%, ⚠️ Warning)<br>• Other: **Asynchronous Release** (45%) | • `gyro in 0.90..1.10 && acc in 0.85..1.15`: **Balanced Punch** (90%)<br>• `acc < 0.70`: **Weak Lateral Drive** (30%)<br>• Other: **Uneven Power Split** (50%) | *"Maintain an isometric rigid wrist lock across both hands through impact for a square, controlled cut."* |
| **`DEFLECTION/GUIDE`** | • `+15..+40 ms`: **Intentional Lag** (85%)<br>• `< +10 ms`: **Rushed Blade Face** (30%)<br>• Other: **Extended Lag** (50%) | • `gyro in 0.15..0.40 && acc <= 0.25`: **Loose Grip Deflection** (85%)<br>• `gyro > 0.50`: **Overactive Trailing Hand** (20%, ⚠️ Warning)<br>• Other: **Passive Support** (60%) | *"Keep bottom hand grip tension loose (finger-only) to let top hand flex blade angle open late."* |
| **`POWER DRIVE`** | • `-10..0 ms`: **Explosive Release** (90%)<br>• `> +15 ms`: **Stalled Extension** (25%, ⚠️ Warning)<br>• Other: **Slight Timing Drift** (50%) | • `gyro >= 1.10 && acc >= 1.10`: **Lofted Drive Acceleration** (90%)<br>• `acc < 0.90`: **Insufficient Vertical Lift** (30%)<br>• Other: **Solid Drive Acceleration** (65%) | *"Drive upward with bottom-hand linear acceleration through the hitting zone into full follow-through extension."* |
| **`SLOG`** | • `-25..-5 ms`: **Co-Explosive Snap** (90%)<br>• `> 0 ms`: **Hesitant Arc** (25%, ⚠️ Warning)<br>• Other: **Unbalanced Release** (45%) | • `gyro >= 1.75 && acc >= 1.50`: **Maximum Release** (95%)<br>• `gyro < 1.30`: **Restricted Arc Power** (30%)<br>• Other: **High Arc Velocity** (70%) | *"Unleash continuous bottom-hand wrist snap from top of backswing through an unrestricted hitting arc."* |
| **`SWEEP`** | • `-10..+5 ms`: **Phase-Locked Torque** (85%)<br>• `> +15 ms`: **Uncoupled Rotation** (25%, ⚠️ Warning)<br>• Other: **Asymmetrical Sweep Arc** (50%) | • `gyro in 1.05..1.30 && acc in 0.90..1.20`: **Torso-Linked Sweep** (85%)<br>• `acc < 0.70`: **Arm-Only Sweep** (25%, ⚠️ Warning)<br>• Other: **Guided Horizontal Sweep** (60%) | *"Crouch low over front knee and drive sweep arc using torso rotational torque rather than arm-only pulling."* |

---

## 📊 Part 3: Longitudinal Repertoire Diagnostics & Corrective Drills (`DiagnosticRulesEngine.kt`)

**Source Files**:
* [`DiagnosticRulesEngine.kt`](file:///Users/neilkloot/Code/CricketBattingTracker/app/src/main/java/com/mrpeel/cricketbattingtracker/analytics/DiagnosticRulesEngine.kt)
* [`BiomechanicsAggregator.kt`](file:///Users/neilkloot/Code/CricketBattingTracker/app/src/main/java/com/mrpeel/cricketbattingtracker/analytics/BiomechanicsAggregator.kt)

Across all stored dual-sensor sessions (for any canonical shot class with $N \ge 5$ shots), the Insights Dashboard evaluates 6 longitudinal fault gates and ranks the top 1–2 primary flaws by fault rate:

### 3.1 Longitudinal Diagnostic Fault Matrix
| Fault Code | Shot Class | Title & Identified Pattern | Trigger Gate | Optimal Target Kinematics | Primary Technical Flaw & Quantified Impact | Linked Drill |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`FAULT_PULL_LAG`** | `PULL/HOOK/SLOG` | **Chronically Dragged Blade on Pull**<br>*(Persistent Dragged Blade on Pull Shots)* | `median(timeLeadMs) > +10 ms` **OR** `> 40%` of shots have `timeLeadMs > 0 ms` | `-30 ms to -10 ms` active snap lead | **Flaw**: Bat face trails shoulders; bottom hand fails to clear arc ahead of turnover.<br>**Impact**: +12 to 18 km/h bat speed & lower aerial mistime risk. | `DRILL_PULL_TEE_SLAPS` |
| **`FAULT_PULL_POWER`** | `PULL/HOOK/SLOG` | **Insufficient Bottom-Hand Linear Punch**<br>*(Passive Trailing Bottom Arm on Pull Shots)* | `median(accRatio) < 1.00` | `accRatio >= 1.20x` linear punch | **Flaw**: Trailing arm fails to punch horizontally through contact.<br>**Impact**: +15% exit velocity via active linear arm punch. | `DRILL_PULL_TEE_SLAPS` |
| **`FAULT_DRIVE_TAKEOVER`** | `DRIVE/DEFENCE` | **Bottom-Hand Takeover on Drives**<br>*(Dominant Bottom Wrist Overpowering Vertical Drives)* | `median(gyroRatio) > 0.75` **OR** `> 30%` of shots have `gyroRatio > 0.85` | `gyroRatio 0.45x to 0.65x` (Passive Top-Hand Guide) | **Flaw**: Bottom hand chokes downswing, forcing closed face and high aerial risk.<br>**Impact**: Increases grounded wagon-wheel placement control by +25%. | `DRILL_DROP_DRIVES` |
| **`FAULT_CUT_ASYNC`** | `CUT/PUNCH` | **Delayed Bottom-Wrist Lock on Cut**<br>*(Asynchronous Dual-Wrist Lock on Cut Shots)* | `median(timeLeadMs) > +10 ms` **OR** `median(accRatio) < 0.75` | `-5 ms to +5 ms` synchronous lock (`accRatio >= 0.85x`) | **Flaw**: Hands disconnect at impact; blade face trails lateral punch plane.<br>**Impact**: Prevents open-face edges; increases square punching power by +10 km/h. | `DRILL_WALL_PUNCH` |
| **`FAULT_SWEEP_ARMS`** | `SWEEP` | **Arm-Dominated Sweep Rotation**<br>*(Uncoupled Arm Drag on Sweep Strokes)* | `median(accRatio) < 0.80` **OR** `median(timeLeadMs) > +12 ms` | `accRatio >= 0.90x` linked to torso torque (`<= +5 ms`) | **Flaw**: Arms dragging independently rather than linking to core torso turn.<br>**Impact**: Enhances ball-striking consistency and placement torque across front knee. | `DRILL_CORE_SWEEPS` |
| **`FAULT_FLICK_EARLY`** | `GLANCE/FLICK` | **Premature Wrist Roll on Flick**<br>*(Early Wrist Roll Closing Blade on Pad Flicks)* | `median(timeLeadMs) < -20 ms` **OR** `median(gyroRatio) < 1.00` | `-15 ms to -5 ms` wrist snap (`gyroRatio >= 1.20x`) | **Flaw**: Premature wrist roll closing blade before impact line.<br>**Impact**: Sharpens pad-clearance angle; eliminates leading-edge risks to mid-on. | `DRILL_PAD_CLEARANCE` |

### 3.2 Prescriptive Corrective Drill Catalogue
1. **`DRILL_PULL_TEE_SLAPS` — Single-Hand Trailing Arm Tee Slaps**
   * **Target Faults**: `FAULT_PULL_LAG`, `FAULT_PULL_POWER`
   * **Setup**: Batting tee placed at hip height on middle/leg stump line.
   * **Execution**: Grip handle with bottom hand only; start with open chest and drive the blade horizontally through the ball, exaggerating full arm extension and forearm pronation.
   * **Biomechanical Focus**: Forces the bottom arm to accelerate through the hitting plane (`accRatio >= 1.20`) rather than acting as a passive passenger.
   * **Prescription**: 3 sets of 12 reps before open net sessions.

2. **`DRILL_DROP_DRIVES` — Split-Grip Top-Hand Drop Drives**
   * **Target Faults**: `FAULT_DRIVE_TAKEOVER`
   * **Setup**: Self-drop or gentle coach drop on off-stump half-volley length.
   * **Execution**: Position bottom hand with thumb and forefinger lightly resting against the top of the handle grip (loose "O" grip); execute high-elbow vertical drives down the ground.
   * **Biomechanical Focus**: Neutralizes bottom-hand wrist takeover (`gyroRatio` target: `0.45 to 0.65`) to ensure the top hand governs blade path.
   * **Prescription**: 4 sets of 10 drives (focusing strictly on grounded straight/cover drives).

3. **`DRILL_WALL_PUNCH` — Lateral Isometric Wall Punch**
   * **Target Faults**: `FAULT_CUT_ASYNC`
   * **Setup**: Position stance sideways against a padded wall or firm tackle bag at point/cover-point line.
   * **Execution**: Take backlift and snap both wrists simultaneously into impact against the pad, holding an isometric wrist lock for 2 seconds upon contact.
   * **Biomechanical Focus**: Calibrates simultaneous cross-wrist kinetic lock (synchronous `-5ms <= Δt <= +5ms`).
   * **Prescription**: 3 sets of 8 holds.

4. **`DRILL_CORE_SWEEPS` — Medicine Ball / Heavy-Bat Core Sweeps**
   * **Target Faults**: `FAULT_SWEEP_ARMS`
   * **Setup**: Deep front-knee crouch on pitch.
   * **Execution**: Holding a light medicine ball or heavy training bat with both hands locked in front of torso, rotate core through the horizontal arc without letting arms extend independently.
   * **Biomechanical Focus**: Couples dual-wrist movement to pelvis and thoracic rotational torque.
   * **Prescription**: 3 sets of 10 sweeps per side.

5. **`DRILL_PAD_CLEARANCE` — Leading-Wrist Pad Clearance Drills**
   * **Target Faults**: `FAULT_FLICK_EARLY`
   * **Setup**: Coach drop or bowling machine on middle/leg stump half-volley.
   * **Execution**: Hold wrist cock until bat reaches front pad line before releasing bottom-wrist snap through mid-wicket.
   * **Biomechanical Focus**: Delays wrist turnover until the exact impact plane (`-15ms <= Δt <= -5ms`) with active pronation (`gyroRatio >= 1.00`).
   * **Prescription**: 3 sets of 12 flicks.

---

## 🧭 Part 4: Offline 3D AHRS & TCN Biomechanical Consistency Gates (`TcnModelRunner.kt`)

**Source Files**:
* [`TcnModelRunner.kt`](file:///Users/neilkloot/Code/CricketBattingTracker/app/src/main/java/com/mrpeel/cricketbattingtracker/ml/TcnModelRunner.kt)
* [`OrientationAhrs.kt`](file:///Users/neilkloot/Code/CricketBattingTracker/app/src/main/java/com/mrpeel/cricketbattingtracker/ml/OrientationAhrs.kt)
* [`PhoneSwingDetector.kt`](file:///Users/neilkloot/Code/CricketBattingTracker/app/src/main/java/com/mrpeel/cricketbattingtracker/services/PhoneSwingDetector.kt)

During offline post-session processing, the 10-layer TCN (`BatPlaneGeometryThreeFamilyTCN`) combines learned probabilities with physical 3D AHRS orientation gates:

1. **Learned False-Positive Rejection Gate (`head_reject`)**:
   * Rejects non-shot movements if `p_shot < 0.35`.
2. **Gate 2.5 Rule 1 — Bat-Mount Vertical Pitch Gate (`BAT_HANDLE` only)**:
   * If `polarMountMode == "BAT_HANDLE"` and the TCN predicts `PULL/HOOK/SLOG`, but 3D AHRS `bladePitch` is strictly vertical (`0.1° < bladePitch <= 40.0°`), the prediction is overridden to `DRIVE/DEFENCE` (or `POWER DRIVE` if high velocity).
3. **Phase 5 Glance/Flick 3D AHRS Disambiguation**:
   * **Bat-Handle Mode (`BAT_HANDLE`)**: Disambiguates vertical-bat predictions (`DRIVE/DEFENCE`, `POWER DRIVE`) into `GLANCE/FLICK` when 3D AHRS shows leg-side swing yaw (`swingYawDeg <= -17.0°`) combined with rapid axial handle roll (`batGzMin <= -11.5 rad/s`).
   * **Wrist / Watch-Only Mode (`WRIST` / `NONE`)**: Rescues upright high-roll pad flicks misclassified as `SWEEP` when closed-form sub-head probability $P_{\text{sub0}}(\text{Glance}) \ge 0.55$, impact $G_z < 5.5\text{ m/s}^2$, and $P_{\text{fam}}(\text{Sweep}) < 0.72$.
4. **Attack Angle Gating**:
   * `launchAngle` (displayed in UI as **`ATTACK ANGLE`**) is computed and displayed **exclusively** for `BAT_HANDLE` sessions with kinematically valid AHRS (`isKinematicallyValid == true`). It returns `null` for `WRIST` and `NONE` sessions so wrist inclination is never misrepresented as blade attack angle.
