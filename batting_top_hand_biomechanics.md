# Batting top-hand biomechanics

## Class 1 - Drive/Defence
**The Radial-to-Ulnar Uncocking Class (The Linear Extension)**
* **Defining Biomechanics:** The stroke begins during the backlift with the top wrist in radial deviation (cocked upward/toward the thumb). During the downswing, the dominant movement is a rapid, controlled transition into ulnar deviation (uncocking the wrist downwards) aligned with an extended lead elbow. The top-hand wrist remains locked laterally, preventing the bat face from closing or rolling, ensuring the face stays vertical and "straight" through the impact zone.
* **Shots in this Class:**
  * Straight Drive
  * Cover Drive  
  * Off Drive
  * On Drive
  * Forward Defensive
  * Back-foot Defensive

## Class 2 - Glance/Flicks
**The Pronation & Controlled Flexion Class (The Rolling Wrist)**
* **Defining Biomechanics:** This class relies on a combination of forearm pronation (rotating the radius bone over the ulna, turning the palm downward/backward) and active wrist flexion right at the moment of impact. Instead of staying locked along a straight line, the top wrist dynamically flexes to close the face of the bat, rolling over the ball to manipulate its trajectory downwards and across the body.
* **Shots in this Class:**
  * Flick Shot (off the pads)
  * Leg Glance
  * On-Glance
  * Traditional Sweep Shot

## Class 3 - Cut/Punch
**The Isometric Rigid Lever Class (Horizontal Alignment)**
* **Defining Biomechanics:** The top wrist stays locked and rigid in a flat horizontal plane, holding static radial-to-neutral deviation to withstand impact forces without buckling. Features a short kinetic path, minimal forearm rotation, and a flat trajectory while keeping the hands close to the body line.
* **Shots in this Class:**
  * Square Cut
  * Cut
  * Back-foot Punch (to the off-side)

## Class 4 - Pull/Hook
**Transverse-to-Vertical Roll**
* **Defining Biomechanics:** Starts with an extended horizontal lever but forces rapid top-wrist pronation and flexion to roll over the ball at release. Characterized by massive arm extension, a broad circular arc, and a distinct downward or high-to-low hand follow-through to control the ball's height.
* **Shots in this Class:**
  * Pull Shot
  * Hook Shot

## Class 5 - Deflection/Guide
**The Supination & Late Extension Class (The Open-Face Deflection)**
* **Defining Biomechanics:** This class is defined by late forearm supination (turning the palm upward/forward) combined with subtle wrist extension or radial deviation just before or during contact. Instead of driving through the ball, the top hand actively guides and opens the bat face, intentionally altering the angle of impact to use the ball's pace and deflect it behind the linear plane of the batter.
* **Shots in this Class:**
  * Late Cut
  * Square Upper Cut
  * Steer / Glide (to third man)

## Class 6 - Power Shot
**The Accelerated Extension-Flexion Class (The High-Velocity Release)**
* **Defining Biomechanics:** Common in modern power-hitting, this class features an extreme range of motion. It begins with severe radial deviation and extension during a high backlift. Upon downswing, it maximizes bat-head speed through a violent, whipping release of ulnar deviation, transitioning instantly into a full post-impact flexion and forearm rotation as the momentum forces a complete release of the hands. The wrist does not anchor the shot; it acts as the final "crack of the whip" to elevate the ball.
* **Shots in this Class:**
  * Lofted Straight/Cover Drive
  * Slog Sweep
  * Switch Hit / Reverse Sweep (where top/bottom hand roles mirror mid-swing)
  * Helicopter Shot

## State 7 - Facing Up
**The Static Isometric Baseline**
* **Defining Biomechanics:** The top hand experiences low-level, continuous isometric contraction to support the dead weight of the bat against gravity. The wrist is held in a position of slight radial deviation and mild pronation to angle the bat blade toward first slip and slightly upward. The state is structurally passive, showing high spatial angular consistency paired with a slow, ultra-low-frequency (0.5–2 Hz) micro-sway.
* **Activities in this Class:**
  * Stance / Waiting for delivery

## State 8 - Walking Around
**The Low-g Chaotic Drift**
* **Defining Biomechanics:** Characterized by a lack of muscle tension or fixed skeletal bracing. The top hand exhibits relaxed, passive manipulation with erratic, multi-axis rotational shifts. Forearm pronation and supination occur randomly as the player changes direction, gestures, or alters their grip while moving at low velocities.
* **Activities in this Class:**
  * Walking between overs
  * Adjusting equipment / Gardening the pitch
  * Moving into fielding positions

## State 9 - Running
**The High-g Periodic Cadence**
* **Defining Biomechanics:** The top hand and forearm act as a dynamic counterweight to the lower-body running stride. The wrist is locked isometrically in a neutral or slightly extended plane to hold the bat clear of the ground. The entire upper extremity experiences highly rhythmic, high-amplitude periodic acceleration spikes caused by foot-strike shocks traveling up the skeleton, tightly matching the user's running cadence (2–4 Hz spikes).
* **Activities in this Class:**
  * Running between wickets
  * Sprinting to field a ball


### Expanded Top-Hand Kinematics & State Matrix

| State / Shot Class | Linear Acceleration ($a$) Profile | Angular Velocity ($\omega$ / Gyro) Profile | Classifier Identification Trick (Top-Hand Only) |
| :--- | :--- | :--- | :--- |
| **Facing Up (Stance)** | **Near Zero.** Minimal linear movement. | **Ultra-Low Frequency.** Steady, static tilt vector with a gentle 0.5–2 Hz micro-sway. | Look for a 2–4 second baseline window of absolute stillness or rhythmic sway right before a spike. |
| **Walking Around** | Low-g, random, disconnected drifting. | Erratic, slow rotational shifts as the player looks around or adjusts equipment. | Non-rhythmic, low-amplitude noise across all axes. No distinct peak forces. |
| **Running (Between Wickets)** | **High-g, highly rhythmic periodic spikes** (vertical and forward axes). | Moderate, rhythmic swinging matching running cadence. | High-frequency cadence matching foot strikes (2–4 Hz spikes) that persist for several seconds. |
| **1. Drive/Defence** <br>*(Straight/Cover Drive)* | Moderate-to-high linear acceleration on a single downward vector. | Sharp, clean angular spike on a single plane; **abrupt deceleration** at contact. | Linear downswing followed by an immediate impact shockwave, with zero rotational wrist rollover. |
| **2. Glance/Flicks** <br>*(Flick / Sweep)* | Moderate, tight linear path close to the body. | **Explosive, late rotational spike** right at the impact timestamp. | Look for rapid forearm pronation (roll) that peaks precisely during or immediately after the deceleration shockwave. |
| **3. Cut/Punch** <br>*(Square/Late Cut)* | High, short linear burst moving laterally across the body. | **Isometric lockdown.** Gyro shifts rapidly in space but the relative wrist angle remains completely rigid. | A brief, violent horizontal slash where spatial orientation changes fast, but the wrist axis shows zero flex. |
| **4. Pull/Hook** <br>*(Pull / Hook Shot)* | **Massive, sustained linear acceleration** over a broad, sweeping arc. | High angular velocity that transitions from a horizontal plane to a sharp downward/low roll. | Huge, sweeping g-forces on the horizontal plane coupled with late high-to-low forearm rotation. |
| **5. Deflection/Guide** <br>*(Late Cut / Glide)* | Very low linear acceleration; passive path. | Sudden, late angular tilt change right before the ball arrives. | The hand remains relatively still, but the gyro registers a sharp, deliberate opening of the blade angle just before impact. |
| **6. Power Shot** <br>*(Slog Sweep / Lofted Drive)* | **Off-the-charts, explosive peak linear acceleration.** | Violent, unrestricted angular velocity that continues on a **low-to-high vertical arc**. | Peak velocity occurs *after* impact as the hands release overhead. Total absence of high-to-low capping or braking forces. |

## Classifier logic decision tree

 [ STAGE 1: THE BASELINE FILTER ]
Check a rolling 3-second window of data.
 ├── IF Linear Acceleration (a) ≈ 0 AND Gyro has a 0.5-2 Hz micro-oscillation:
 │    └── LABEL: "Facing Up (Stance)" -> Use this to lock the baseline gravity vector.
 ├── IF Low-g, chaotic, non-rhythmic, multi-axis changes present:
 │    └── LABEL: "Walking Around"
 └── IF High-g, highly rhythmic, periodic spikes (2-4 Hz cadence) persist for greater than 1.5 seconds:
      └── LABEL: "Running Between Wickets"


[ STAGE 2: THE SHOT WINDOW TRIGGER ]
If the state is NOT Stance, Walking, or Running, watch for a sudden, massive departure 
from the baseline gravity vector (The Backlift).
 └── IF Linear Acceleration (a) spikes past a defined high-velocity threshold:
      └── OPEN: "Shot Window" (Capture data from t-minus 200ms to t-plus 600ms around peak impact shockwave)

[ STAGE 3: SHOT CLASS DIFFERENTIATION ]
Analyze the kinematic signature exclusively within the captured "Shot Window":

 ├── PATH A: Low-to-Moderate Linear Acceleration
 │    └── IF Linear Acceleration is low AND Gyro shows a sharp, late opening/tilt change right at impact:
 │         └── CLASSIFY: "5. The Deflectors"
 │
 ├── PATH B: High Linear Acceleration along a Vertical Plane
 │    ├── IF Gyro shows zero rotational roll + an abrupt, sharp deceleration spike at impact:
 │    │    └── CLASSIFY: "1. The 'V' Drivers"
 │    └── IF Gyro shows violent, unrestricted low-to-high angular velocity with peak acceleration AFTER impact:
 │         └── CLASSIFY: "6. The Power Launchers"
 │
 └── PATH C: High Linear Acceleration along a Horizontal/Transverse Plane
      ├── IF Gyro registers rapid, active forearm pronation (high-to-low wrist roll) right at impact:
      │    └── CLASSIFY: "4. The Extended Pullers"
      ├── IF Gyro registers a late, explosive rotational spike close to the body line on a tight path:
      │    └── CLASSIFY: "2. The Wristy Manipulators"
      └── IF Gyro shows absolute isometric lockdown (zero rotational wrist roll through the entirety of the slash):
           └── CLASSIFY: "3. The Pocket Cutters"