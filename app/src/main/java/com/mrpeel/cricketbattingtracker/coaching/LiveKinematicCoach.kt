package com.mrpeel.cricketbattingtracker.coaching

import android.util.Log
import kotlinx.coroutines.*
import kotlin.math.PI
import kotlin.math.abs
import kotlin.math.acos
import kotlin.math.max
import kotlin.math.min
import kotlin.math.sqrt

/**
 * Shot-invariant diagnostic failure families grouping fundamental batting motor faults
 * measurable directly from 3D bat-handle kinematics without requiring shot-type classification.
 */
enum class FailureFamily(val title: String, val acousticTheme: String) {
    FAMILY_A_TIMING_DECELERATION("A. Downswing Timing & Continuity", "Power Drop & Stalled Transients"),
    FAMILY_B_PLANE_INSTABILITY("B. 3D Swing Plane Stability", "Pitch Bends & Scraping Sweeps"),
    FAMILY_C_FACE_INSTABILITY("C. Impact Wrist & Face Control", "Dissonant & Phase-Twisted Tones"),
    FAMILY_D_TEMPO_OVERCOMMIT("D. Tempo & Balance Envelope", "Detuned LFO Siren")
}

/**
 * Shot-invariant biomechanical fault identified in real time at ball contact.
 * All faults evaluate universal swing mechanics (velocity retention into impact, 3D swing plane
 * consistency, late wrist rescue jerk, and over-swinging loss of shape) that hold across every
 * cricket shot (Drives, Flicks, Cuts, Pulls, Sweeps, and Deflections).
 */
enum class LiveShotFault(
    val shotName: String,
    val failureDescription: String,
    val cue: String,
    val family: FailureFamily?,
    val acousticDesign: String,
    val acousticIntuition: String,
    val biomechanicalFix: String
) {
    // ── Family A: Downswing Timing & Continuity ──
    EARLY_PEAK_DECELERATION(
        shotName = "Checked / Decelerating Swing",
        failureDescription = "Bat peaked early in downswing and lost >32% speed before contact.",
        cue = "Swing through",
        family = FailureFamily.FAMILY_A_TIMING_DECELERATION,
        acousticDesign = "Tape-Stop / Power-Down Drop (600 Hz -> 150 Hz rapid pitch & volume drop, 200 ms)",
        acousticIntuition = "Acoustic deceleration directly mirrors your bat losing angular velocity before ball contact.",
        biomechanicalFix = "Regardless of what shot you play, peak bat speed should occur right into ball contact (~95% retention). Slowing down by >32% before impact happens when you commit too early, reach out in front of your eyeline, or get jammed by the bounce. Wait for the ball to enter your hitting zone and accelerate right through contact."
    ),
    STALLED_REACH_PUSH(
        shotName = "Reaching / Stalled Hand Push",
        failureDescription = "Hands pushed out flatly toward the ball without accelerating through contact.",
        cue = "Let it come",
        family = FailureFamily.FAMILY_A_TIMING_DECELERATION,
        acousticDesign = "Dry Woodblock Double-Rap (800 Hz filtered noise burst, 40 ms gap, 120 ms total)",
        acousticIntuition = "Sounds rigid, brittle, and pushed—the acoustic opposite of a whip-like swing or soft absorption.",
        biomechanicalFix = "Your bat speed plateaued and pushed into contact with stiff arms rather than whipping smoothly through the ball or absorbing it behind your eyes. Let the ball travel deeper toward your front knee before releasing your hands."
    ),

    // ── Family B: 3D Swing Plane Stability ──
    MID_SWING_PLANE_LOOP(
        shotName = "Late Line/Length Adjustment (Mid-Swing Loop)",
        failureDescription = "Picked up line/length late; 3D swing axis shifted >22° in final 45 ms.",
        cue = "Watch the ball",
        family = FailureFamily.FAMILY_B_PLANE_INSTABILITY,
        acousticDesign = "Inverted 'U' Pitch Bend (700 Hz -> 350 Hz -> 800 Hz, 240 ms)",
        acousticIntuition = "Mirrors the bat dipping off its initial downswing path and looping back to find the ball.",
        biomechanicalFix = "A >22° shift in your 3D swing axis in the final 45 ms happens when you pick up the line or length late and have to redirect the bat mid-downswing. Watch the ball closely out of the release point to read the line and length early, then commit to that single path through the shot."
    ),
    OUT_OF_PLANE_WIPE(
        shotName = "Early Shoulder Rotation (Wiping Across)",
        failureDescription = "Front shoulder rotated open early, pulling bat >16.5° off-plane across the ball.",
        cue = "Head to the ball",
        family = FailureFamily.FAMILY_B_PLANE_INSTABILITY,
        acousticDesign = "Metallic Scrape / High-Q Bandpass Sweep (2200 Hz -> 700 Hz noise sweep, 200 ms)",
        acousticIntuition = "Sounds like the blade casting and scraping obliquely across the seam of the ball.",
        biomechanicalFix = "Your swing plane drifted by >16.5° in the final 45 ms while the handle twisted across the trajectory. This happens when your front shoulder rotates open too early and pulls your hands across the line. Keep your head moving toward the ball so your lead shoulder stays aligned through contact."
    ),

    // ── Family C: Impact Wrist & Face Control ──
    LATE_WRIST_RESCUE(
        shotName = "Jerky Last-Second Wrist Snap",
        failureDescription = "Violent wrist jerk (>55% of swing speed) in final 30 ms while off-plane.",
        cue = "Roll smoothly",
        family = FailureFamily.FAMILY_C_FACE_INSTABILITY,
        acousticDesign = "Tight Dissonant Minor-Second Buzz (500 Hz + 530 Hz dual tone, 200 ms)",
        acousticIntuition = "The beating frequencies sound 'crossed' and pinched, mirroring a sudden jerky wrist snap.",
        biomechanicalFix = "Active wrist work on a flick or pull is great when rolled progressively through the hitting zone. This fault only triggers when your wrists jerk violently in the final 30 ms while the swing plane is shifting (>12°). Avoid snatching at the ball late—roll your wrists smoothly through the arc."
    ),
    IMPACT_FACE_TWIST(
        shotName = "Loose Grip / Bat Twisting at Impact",
        failureDescription = "Grip too loose at contact; bat twisted sharply (>5.5 rad/s) with speed loss.",
        cue = "Tighten grip",
        family = FailureFamily.FAMILY_C_FACE_INSTABILITY,
        acousticDesign = "Brassy High-to-Low 'Crack' (1400 Hz -> 500 Hz sawtooth drop with fast decay, 180 ms)",
        acousticIntuition = "Sounds harsh and over-twisted, mimicking the bat twisting in a loose grip at contact.",
        biomechanicalFix = "The bat handle experienced a sharp axial twist spike right at impact alongside velocity loss because your grip was too loose at the moment of contact, allowing the ball to turn the bat in your hands. Firm up your grip through ball contact so the face stays square."
    ),

    // ── Family D: Tempo & Balance Envelope ──
    OVERSWING_LOSS_OF_SHAPE(
        shotName = "Over-Swinging (Loss of Shape)",
        failureDescription = "Swinging at >31 rad/s while losing plane stability (>14.5°) or decelerating.",
        cue = "Hold your shape",
        family = FailureFamily.FAMILY_D_TEMPO_OVERCOMMIT,
        acousticDesign = "Wobbly Detuned Siren (600 Hz with heavy ±80 Hz LFO wobble, 250 ms)",
        acousticIntuition = "Sounds 'out of balance' and spinning off-axis, matching torso/head drift from over-hitting.",
        biomechanicalFix = "High bat speed is great when the swing stays on-plane and accelerates through contact. This fault only triggers when extreme effort (>31 rad/s) causes your swing plane to wobble (>14.5°) or decelerate before contact because your torso spun ahead of your hands. Swing at 85–90% effort with a still head and let clean timing generate power."
    ),

    // ── Clean Hit ──
    CLEAN_STROKE(
        shotName = "Clean Stroke",
        failureDescription = "Accelerating through contact on a stable 3D swing plane.",
        cue = "Solid",
        family = null,
        acousticDesign = "Crystal Harmonic Dual Chime (880 Hz + 1760 Hz decay, 150 ms)",
        acousticIntuition = "Clear, pure harmonic tone confirming smooth acceleration and plane stability.",
        biomechanicalFix = "Maintain this balanced swing plane and acceleration through the ball."
    )
}

/**
 * Snapshot of shot-invariant kinematic metrics extracted from the [-200ms, 0ms] pre-impact window.
 */
data class ShotInvariantMetrics(
    val peakGyroRadS: Float,
    val speedKmh: Float,
    val velocityRetention: Float,
    val accelSlope: Float,
    val planeWobbleDeg: Float,
    val twistSpikeRatio: Float,
    val axialJerkRadS: Float
)

/**
 * Real-time shot-invariant kinematic impact evaluator running on the 416Hz Polar bat sensor stream.
 *
 * Evaluates universal biomechanical invariants over the [-220ms, 0ms] downswing window:
 *   1. Downswing Velocity Retention (omega_impact / omega_peak) & Pre-Impact Acceleration Slope
 *   2. 3D Swing Plane Stability (mean angular deviation of unit rotation axis in final 45ms)
 *   3. Normalized Late Axial Wrist Spike & Sample-to-Sample Axial Jerk
 *   4. Over-Swing Shape Envelope (extreme angular rate combined with plane wobble or deceleration)
 *
 * Enforces the Post-Impact Audio Timeline:
 *   T + 0 to 300 ms: Silence (lets you hear the real acoustic crack off the bat)
 *   T + 300 to 520 ms: Earcon plays (~200 ms)
 *   T + 550 to 1050 ms: TTS cue (at 1.25x speed) or Bat Speed plays
 *   T + 1100 ms onwards: Mic channel completely clear for narration
 */
class LiveKinematicCoach(
    private val audioFeedback: LiveCoachingAudioFeedback? = null,
    private val coroutineScope: CoroutineScope = CoroutineScope(Dispatchers.Default + SupervisorJob()),
    private val syncExecutionForTesting: Boolean = false
) {
    companion object {
        private const val TAG = "LiveKinematicCoach"

        // Minimum time between evaluated shots (cooldown in ms)
        const val IMPACT_COOLDOWN_MS = 1800L

        // Impact detection thresholds on the bat handle sensor
        const val ACC_IMPACT_THRESHOLD_G = 10.0f      // Sharp acceleration spike (> 10g)
        const val MIN_SWING_GYRO_RAD_S = 5.5f         // Active swing angular rate threshold in pre-impact window
        const val DOWNSWING_WINDOW_MS = 220L          // Strictly evaluate downswing within 220ms before impact
        private const val DEG_TO_RAD = (PI / 180.0).toFloat()
        private const val RAD_TO_DEG = (180.0 / PI).toFloat()
        const val GYRO_TO_KMH = 3.4f                  // Calibrated bat-handle rad/s to sweet-spot km/h factor

        // Post-impact delivery schedule
        const val SILENCE_DELAY_MS = 300L             // T+0 to 300ms: Silence for physical acoustic crack
        const val TTS_AFTER_EARCON_DELAY_MS = 250L    // T+550ms: Cue fires after earcon finishes
    }

    var lastImpactTimeMs = 0L
        private set

    // Tracks previous fault for Stage 3 (Silent Diagnostic) repetition detection
    var lastDiagnosedFault: LiveShotFault? = null
        private set

    // Ring buffers for recent gyroscope telemetry (128 samples = ~307ms at 416Hz)
    private val bufferSize = 128
    private val gyroX = FloatArray(bufferSize)
    private val gyroY = FloatArray(bufferSize)     // Long-axis handle roll / twist
    private val gyroZ = FloatArray(bufferSize)     // Lateral face angle rate
    private val gyroMags = FloatArray(bufferSize)
    private val gyroTimestamps = LongArray(bufferSize)
    private var bufferIndex = 0
    private var sampleCount = 0

    /**
     * Ingests a raw 3-axis accelerometer sample from the Polar bat handle sensor.
     * Impact is only triggered if the recent [-220ms, 0ms] gyroscope window contains an active swing
     * (>= 5.5 rad/s), preventing stationary stance taps from firing false coaching cues.
     */
    fun processAccSample(
        phoneMs: Long,
        @Suppress("UNUSED_PARAMETER") sensorNs: Long = 0L,
        x: Float,
        y: Float,
        z: Float
    ) {
        val magG = sqrt(x * x + y * y + z * z) / 1000.0f
        val now = if (phoneMs > 0L) phoneMs else System.currentTimeMillis()

        if (magG >= ACC_IMPACT_THRESHOLD_G && (lastImpactTimeMs == 0L || now - lastImpactTimeMs > IMPACT_COOLDOWN_MS)) {
            val metrics = extractPreImpactMetrics(phoneMs)
            if (metrics != null && metrics.peakGyroRadS >= MIN_SWING_GYRO_RAD_S) {
                lastImpactTimeMs = now
                evaluateImpact(now, magG, metrics)
            }
        }
    }

    /**
     * Ingests a raw 3-axis gyroscope sample from the Polar bat handle sensor.
     */
    fun processGyroSample(
        phoneMs: Long = 0L,
        @Suppress("UNUSED_PARAMETER") sensorNs: Long = 0L,
        x: Float,
        y: Float,
        z: Float
    ) {
        val gxRad = x * DEG_TO_RAD
        val gyRad = y * DEG_TO_RAD
        val gzRad = z * DEG_TO_RAD
        val gyroRadS = sqrt(gxRad * gxRad + gyRad * gyRad + gzRad * gzRad)

        val idx = bufferIndex % bufferSize
        gyroX[idx] = gxRad
        gyroY[idx] = gyRad
        gyroZ[idx] = gzRad
        gyroMags[idx] = gyroRadS
        gyroTimestamps[idx] = phoneMs
        bufferIndex++
        sampleCount++
    }

    /**
     * Extracts shot-invariant biomechanical metrics strictly from the [-220ms, 0ms] pre-impact window.
     */
    private fun extractPreImpactMetrics(impactPhoneMs: Long): ShotInvariantMetrics? {
        val available = min(sampleCount, bufferSize)
        if (available < 6) return null

        // Collect samples in chronological order within the [-220ms, 0ms] downswing window (up to 85 samples)
        val maxLookback = min(available, 85)
        val validIndices = IntArray(maxLookback)
        var count = 0

        for (i in maxLookback - 1 downTo 0) {
            val ringIdx = (bufferIndex - 1 - i + bufferSize * 2) % bufferSize
            val ts = gyroTimestamps[ringIdx]
            if (impactPhoneMs <= 0L || ts <= 0L || (impactPhoneMs - ts) in 0L..DOWNSWING_WINDOW_MS) {
                validIndices[count++] = ringIdx
            }
        }

        if (count < 6) return null

        // 1. Peak Downswing Angular Velocity & Impact Velocity Retention
        var peakGyro = 0.0f
        for (i in 0 until count) {
            val g = gyroMags[validIndices[i]]
            if (g > peakGyro) peakGyro = g
        }
        if (peakGyro < MIN_SWING_GYRO_RAD_S) return null

        val impactWindow = min(count, 4)
        var impactGyroSum = 0.0f
        for (i in count - impactWindow until count) {
            impactGyroSum += gyroMags[validIndices[i]]
        }
        val impactGyro = impactGyroSum / impactWindow
        val velocityRetention = (impactGyro / peakGyro).coerceIn(0.0f, 1.0f)

        // 2. Pre-Impact Acceleration Slope over final ~40ms (up to 17 samples)
        val slopeWin = min(count, 17)
        val edgeCount = max(1, min(4, slopeWin / 3))
        var earlySum = 0.0f
        var lateSum = 0.0f
        val startSlopeIdx = count - slopeWin
        for (i in 0 until edgeCount) {
            earlySum += gyroMags[validIndices[startSlopeIdx + i]]
            lateSum += gyroMags[validIndices[count - edgeCount + i]]
        }
        val accelSlope = ((lateSum / edgeCount) - (earlySum / edgeCount)) / peakGyro

        // 3. 3D Swing Plane Stability (mean angular wobble of unit rotation vector in final ~45ms = 18 samples)
        val planeWin = min(count, 18)
        val startPlaneIdx = count - planeWin
        var meanUx = 0.0f
        var meanUy = 0.0f
        var meanUz = 0.0f
        var validVectors = 0

        for (i in startPlaneIdx until count) {
            val idx = validIndices[i]
            val mag = gyroMags[idx]
            if (mag >= 2.0f) {
                meanUx += gyroX[idx] / mag
                meanUy += gyroY[idx] / mag
                meanUz += gyroZ[idx] / mag
                validVectors++
            }
        }

        var planeWobbleDeg = 0.0f
        if (validVectors >= 3) {
            val normMean = sqrt(meanUx * meanUx + meanUy * meanUy + meanUz * meanUz)
            if (normMean > 1e-4f) {
                meanUx /= normMean
                meanUy /= normMean
                meanUz /= normMean
                var angleSumDeg = 0.0f
                for (i in startPlaneIdx until count) {
                    val idx = validIndices[i]
                    val mag = gyroMags[idx]
                    if (mag >= 2.0f) {
                        val dot = ((gyroX[idx] / mag) * meanUx +
                                   (gyroY[idx] / mag) * meanUy +
                                   (gyroZ[idx] / mag) * meanUz).coerceIn(-1.0f, 1.0f)
                        angleSumDeg += acos(dot) * RAD_TO_DEG
                    }
                }
                planeWobbleDeg = angleSumDeg / validVectors
            }
        }

        // 4. Late Axial Wrist Twist Spike & Sample-to-Sample Axial Jerk in final ~30ms (13 samples)
        val twistWin = min(count, 13)
        val startTwistIdx = count - twistWin
        var minY = Float.MAX_VALUE
        var maxY = -Float.MAX_VALUE
        var maxAxialJerk = 0.0f
        var prevY = gyroY[validIndices[startTwistIdx]]

        for (i in startTwistIdx until count) {
            val y = gyroY[validIndices[i]]
            if (y < minY) minY = y
            if (y > maxY) maxY = y
            if (i > startTwistIdx) {
                val jerk = abs(y - prevY)
                if (jerk > maxAxialJerk) maxAxialJerk = jerk
            }
            prevY = y
        }

        val twistDelta = if (maxY >= minY) maxY - minY else 0.0f
        val twistSpikeRatio = twistDelta / peakGyro

        return ShotInvariantMetrics(
            peakGyroRadS = peakGyro,
            speedKmh = peakGyro * GYRO_TO_KMH,
            velocityRetention = velocityRetention,
            accelSlope = accelSlope,
            planeWobbleDeg = planeWobbleDeg,
            twistSpikeRatio = twistSpikeRatio,
            axialJerkRadS = maxAxialJerk
        )
    }

    private fun evaluateImpact(impactTimeMs: Long, peakAccG: Float, metrics: ShotInvariantMetrics) {
        val fault = diagnoseShotInvariant(metrics)
        Log.i(
            TAG,
            "⚡ Evaluated Shot at ${impactTimeMs}ms: speed=%.1f km/h (%.1f rad/s), acc=%.1f g, retention=%.2f, slope=%.2f, wobble=%.1f°, twistRatio=%.2f, jerk=%.1f -> $fault"
                .format(
                    metrics.speedKmh,
                    metrics.peakGyroRadS,
                    peakAccG,
                    metrics.velocityRetention,
                    metrics.accelSlope,
                    metrics.planeWobbleDeg,
                    metrics.twistSpikeRatio,
                    metrics.axialJerkRadS
                )
        )

        dispatchScheduledFeedback(fault, metrics.speedKmh)
    }

    /**
     * Evaluates universal, shot-invariant biomechanical rules.
     * Never guesses the shot type; diagnoses only objective mechanical breakdowns that apply
     * identically to Drives, Flicks, Cuts, Pulls, Sweeps, and Deflections.
     */
    fun diagnoseShotInvariant(metrics: ShotInvariantMetrics): LiveShotFault {
        val peakGyro = metrics.peakGyroRadS
        val retention = metrics.velocityRetention
        val slope = metrics.accelSlope
        val wobble = metrics.planeWobbleDeg
        val twistRatio = metrics.twistSpikeRatio
        val jerk = metrics.axialJerkRadS

        // 1. Over-Swinging / Loss of Shape:
        // Extreme angular velocity (> 31 rad/s) that causes the swing plane to wobble (> 14.5°)
        // or decelerate before contact (retention < 0.80). Fast swings that stay on-plane are Clean!
        if (peakGyro > 31.0f && (wobble > 14.5f || retention < 0.80f)) {
            return LiveShotFault.OVERSWING_LOSS_OF_SHAPE
        }

        // 2. Checked / Decelerating Swing:
        // Active stroke (>= 13.5 rad/s, excluding intentional soft dead-bat blocks) where bat speed
        // peaks too early and drops by >32% before impact (retention < 0.68) or strongly decelerates (slope < -0.22).
        if (peakGyro >= 13.5f && (retention < 0.68f || slope < -0.22f)) {
            return LiveShotFault.EARLY_PEAK_DECELERATION
        }

        // 3. Reaching / Stalled Hand Push:
        // Moderate swing (9.5..16.0 rad/s) where hands push out and stall into impact.
        if (peakGyro in 9.5f..16.0f && retention in 0.68f..0.78f && slope < -0.12f) {
            return LiveShotFault.STALLED_REACH_PUSH
        }

        // 4. Mid-Swing Plane Loop / Redirect:
        // 3D rotation axis shifts by > 22° in the final 45ms before impact.
        if (wobble > 22.0f) {
            return LiveShotFault.MID_SWING_PLANE_LOOP
        }

        // 5. Out-of-Plane Cast / Wipe Across:
        // Swing plane drifts (> 16.5°) while twisting across the line before impact.
        if (wobble > 16.5f && twistRatio > 0.38f) {
            return LiveShotFault.OUT_OF_PLANE_WIPE
        }

        // 6. Last-Millisecond Wrist Flip / Rescue:
        // Sudden late wrist roll (> 55% of peak speed in 30ms) combined with plane shift (> 12°).
        // Smooth wrist roll on a Flick or Pull stays on-plane (wobble ~6°-9°) and is never penalized.
        if (twistRatio > 0.55f && wobble > 12.0f) {
            return LiveShotFault.LATE_WRIST_RESCUE
        }

        // 7. Unstable Face / High-Torque Impact Twist:
        // Sharp axial handle jerk (> 5.5 rad/s between samples) alongside velocity loss at impact.
        if (jerk > 5.5f && retention < 0.82f) {
            return LiveShotFault.IMPACT_FACE_TWIST
        }

        // Controlled technical envelope -> Clean stroke
        return LiveShotFault.CLEAN_STROKE
    }

    /**
     * Executes the Post-Impact Audio Schedule:
     * T+0 to 300ms: Silence (hear natural physical acoustic crack)
     * T+300 to 520ms: Earcon plays (~200ms)
     * T+550 to 1050ms: Voice cue or speed integer (depending on mode)
     * T+1100ms onwards: Silence, mic channel prioritized
     */
    private fun dispatchScheduledFeedback(fault: LiveShotFault, speedKmh: Float) {
        val feedback = audioFeedback ?: return
        if (!feedback.isEnabled) return

        val mode = feedback.coachingMode
        val isRepeatFault = (fault != LiveShotFault.CLEAN_STROKE && fault == lastDiagnosedFault)
        lastDiagnosedFault = fault

        if (syncExecutionForTesting) {
            deliverNow(feedback, mode, fault, speedKmh, isRepeatFault)
            return
        }

        coroutineScope.launch {
            // T + 0 to 300 ms: Silence for the natural crack of the bat
            delay(SILENCE_DELAY_MS)

            when (mode) {
                CoachingMode.STAGE_1_CALIBRATION -> {
                    // Earcon at T+300ms
                    feedback.playEarcon(fault)

                    // TTS Cue at T+550ms
                    delay(TTS_AFTER_EARCON_DELAY_MS)
                    if (fault == LiveShotFault.CLEAN_STROKE) {
                        feedback.speak("${speedKmh.toInt()}")
                    } else {
                        feedback.speak(fault.cue)
                    }
                }
                CoachingMode.STAGE_2_FLOW_STATE -> {
                    // Earcon at T+300ms
                    feedback.playEarcon(fault)

                    // On success only: speak speed integer after chime
                    if (fault == LiveShotFault.CLEAN_STROKE) {
                        delay(TTS_AFTER_EARCON_DELAY_MS)
                        feedback.speak("${speedKmh.toInt()}")
                    }
                    // On failure: Earcon only! Complete silence by T+520ms
                }
                CoachingMode.STAGE_3_SILENT_DIAGNOSTIC -> {
                    // Only plays earcon if the same fault occurs twice in a row
                    if (isRepeatFault) {
                        feedback.playEarcon(fault)
                    }
                    // Voice cues always disabled in Stage 3
                }
            }
        }
    }

    /**
     * Synchronous execution path used for unit testing assertion verifications.
     */
    fun deliverNow(
        feedback: LiveCoachingAudioFeedback,
        mode: CoachingMode,
        fault: LiveShotFault,
        speedKmh: Float,
        isRepeatFault: Boolean
    ) {
        when (mode) {
            CoachingMode.STAGE_1_CALIBRATION -> {
                feedback.playEarcon(fault)
                if (fault == LiveShotFault.CLEAN_STROKE) {
                    feedback.speak("${speedKmh.toInt()}")
                } else {
                    feedback.speak(fault.cue)
                }
            }
            CoachingMode.STAGE_2_FLOW_STATE -> {
                feedback.playEarcon(fault)
                if (fault == LiveShotFault.CLEAN_STROKE) {
                    feedback.speak("${speedKmh.toInt()}")
                }
            }
            CoachingMode.STAGE_3_SILENT_DIAGNOSTIC -> {
                if (isRepeatFault) {
                    feedback.playEarcon(fault)
                }
            }
        }
    }
}
