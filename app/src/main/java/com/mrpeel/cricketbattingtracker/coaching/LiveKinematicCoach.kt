package com.mrpeel.cricketbattingtracker.coaching

import android.util.Log
import kotlinx.coroutines.*
import kotlin.math.PI
import kotlin.math.abs
import kotlin.math.sqrt

/**
 * Diagnostic failure families grouping common batting motor faults.
 */
enum class FailureFamily(val title: String, val acousticTheme: String) {
    FAMILY_A_UPWARD_LOOP("A. Upward Loop / Scoop", "Rising Pitch Glissando"),
    FAMILY_B_REACHING_HARD("B. Reaching / Hard Hands", "Sharp Percussive Transients"),
    FAMILY_C_EARLY_ROLL_SLICE("C. Early Roll / Slicing Across", "Harsh / Phase-Twisted Tones"),
    FAMILY_D_MOMENTUM_COLLAPSE("D. Momentum / Shape Collapse", "Power Drop / Detuning")
}

/**
 * Diagnostic fault identified in real time at contact.
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
    // ── Family A: Upward Loop / Scoop ──
    PULL_SKIED(
        shotName = "Pull Shot Skied / Top Edge",
        failureDescription = "Underneath the ball with open face and backward-leaning spine.",
        cue = "Stay tall",
        family = FailureFamily.FAMILY_A_UPWARD_LOOP,
        acousticDesign = "Fast Rising Whistle (400 Hz -> 1200 Hz sine sweep over 220 ms)",
        acousticIntuition = "The rapid upward pitch sweep mirrors the +8° upward attack angle and the ball sailing into the air.",
        biomechanicalFix = "It is easy to drop the back hip and lean back to \"launch\" it. Once the spine tilts backward, your swing plane automatically tilts upward (>+8°). Your sternum needs to move forward toward the pitch of the ball, keeping the hands higher than the bat head."
    ),
    DRIVE_SCOOP(
        shotName = "Drive Bottom-Hand Scoop",
        failureDescription = "Bottom wrist flicking upward at impact, lifting toe of the bat.",
        cue = "Head to pitch",
        family = FailureFamily.FAMILY_A_UPWARD_LOOP,
        acousticDesign = "Two-Step Rising Blip (350 Hz -> 900 Hz square-wave jump, 180 ms)",
        acousticIntuition = "The sharp low-to-high jump mimics the sudden +Z bottom-wrist flick lifting the toe of the bat at impact.",
        biomechanicalFix = "When the upward wrist flick happens (+Z jerk), it is almost always because your head and weight stopped moving forward before the hands arrived, forcing you to reach for the ball. When you reach, the bottom wrist has to flick up to meet the ball."
    ),
    PUNCH_SCOOP(
        shotName = "Back Foot Punch Upward Scoop",
        failureDescription = "Hands dropping below bounce line and scooping upward.",
        cue = "High hands",
        family = FailureFamily.FAMILY_A_UPWARD_LOOP,
        acousticDesign = "Inverted 'U' Pitch Bend (700 Hz -> 350 Hz -> 800 Hz, 240 ms)",
        acousticIntuition = "Mirrors the exact hand path fault: hands dropping below bounce height and scooping back up.",
        biomechanicalFix = "Scooping a back-foot punch happens when your hands drop below the bounce height during the backlift transition, forcing an upward loop to meet the ball. Your hands must get up to chest height before the downswing begins so you can hit down the vertical plane."
    ),

    // ── Family B: Reaching / Hard Hands ──
    DEFENSE_HARD_HANDS(
        shotName = "Defense \"Hard Hands\" / Poking",
        failureDescription = "Rigid bottom-hand thrusting forward into impact with high bat speed.",
        cue = "Behind the knee",
        family = FailureFamily.FAMILY_B_REACHING_HARD,
        acousticDesign = "Dry Woodblock Double-Rap (800 Hz filtered noise burst, 40 ms gap, 120 ms total)",
        acousticIntuition = "Sounds rigid, brittle, and \"hard\"—the exact acoustic opposite of a soft, dead-bat absorption.",
        biomechanicalFix = "Your hands are out in front of your center of mass (nose/front knee), meaning your arms are extended and rigid at contact. True soft hands come from letting the ball hit the bat behind the vertical line of your eyes, with slightly bent elbows that can flex on impact."
    ),
    GLIDE_PUSHED(
        shotName = "Glide / Steer Pushed Hard",
        failureDescription = "Pushing hands forward away from eyeline on deflection.",
        cue = "Give with it",
        family = FailureFamily.FAMILY_B_REACHING_HARD,
        acousticDesign = "Springy Forward \"Boing/Push\" (300 Hz -> 480 Hz resonant filter sweep, 180 ms)",
        acousticIntuition = "Sounds like pushing against a spring rather than letting the ball recoil off a dead face.",
        biomechanicalFix = "You are generating positive linear work with your arms (ax/az push) instead of letting the ball do the work. To fix this, the hands must act as a hydraulic damper—actually giving way slightly toward the slips at the moment of impact."
    ),

    // ── Family C: Early Roll / Slicing Across ──
    CUT_OVERHIT(
        shotName = "Cut Shot Over-Hit / Face Blown Open",
        failureDescription = "Swinging too hard out in front; face blows open (+18.7°).",
        cue = "Behind point",
        family = FailureFamily.FAMILY_C_EARLY_ROLL_SLICE,
        acousticDesign = "Brassy High-to-Low \"Crack\" (1400 Hz -> 500 Hz sawtooth drop with fast decay, 180 ms)",
        acousticIntuition = "Sounds aggressive and over-cooked, mimicking the bat face blowing open from an early shoulder spin.",
        biomechanicalFix = "Your front shoulder is flying open early, pulling the hands out in front of your eyeline. When you contact the ball in front of your front hip, the wrists are forced into radial extension (face open). You need the hands to stay tucked near the back shoulder until the ball passes your front hip, allowing top-of-bounce contact."
    ),
    FLICK_LEADING_EDGE(
        shotName = "Flick / Glance Leading Edge",
        failureDescription = "Rolling wrists 50-100ms prematurely before ball contacts bat.",
        cue = "Show the face",
        family = FailureFamily.FAMILY_C_EARLY_ROLL_SLICE,
        acousticDesign = "Tight Dissonant Minor-Second Buzz (500 Hz + 530 Hz dual tone, 200 ms)",
        acousticIntuition = "The beating frequencies sound \"crossed\" and pinched, mirroring bat face closing 50-100 ms early across the line.",
        biomechanicalFix = "Closing the face 50–100 ms early means your bottom hand is taking over before the bat reaches the ball's line, causing the bat path to cut across the ball's trajectory. You need to present the full maker's name down the line of the ball, rotating the forearms only after contact."
    ),
    DRIVE_SLICE(
        shotName = "Drive Sliced Outside-In (Thick Edge)",
        failureDescription = "Outside-in bat path casting across delivery line; thick outside edge.",
        cue = "Lead with toe",
        family = FailureFamily.FAMILY_C_EARLY_ROLL_SLICE,
        acousticDesign = "Metallic Scrape / High-Q Bandpass Sweep (2200 Hz -> 700 Hz noise sweep, 200 ms)",
        acousticIntuition = "Literally sounds like a thick outside edge slicing across the seam of the ball.",
        biomechanicalFix = "The violent handle torque (ΔGy > 6.0 rad/s) is a compensatory rescue move. Your front foot or front shoulder has likely planted either too closed (blocking your hands, forcing an out-to-in loop) or your head fell to the off-side. Focus on your bat path tracking inside the line of the ball."
    ),

    // ── Family D: Momentum / Shape Collapse ──
    PULL_CHOKED(
        shotName = "Pull Shot Choked / Aborted",
        failureDescription = "Decelerating hands >35% before contact; looping miscue.",
        cue = "Clear the hip",
        family = FailureFamily.FAMILY_D_MOMENTUM_COLLAPSE,
        acousticDesign = "Tape-Stop / Power-Down Drop (600 Hz -> 150 Hz rapid pitch & volume drop, 200 ms)",
        acousticIntuition = "Acoustic deceleration directly mirrors your >35% pre-impact bat deceleration.",
        biomechanicalFix = "Deceleration (>35%) mid-swing happens when you get \"jammed\"—the ball is closer to your body than your footwork allowed for, or you committed to a horizontal swing on a ball that didn't bounce. You need to clear the front hip early to create a rotational slot for your hands."
    ),
    POWER_DRIVE_OVERSWING(
        shotName = "Power Drive Over-Swing (Loss of Shape)",
        failureDescription = "Swinging >100 km/h; head and shoulder pulling off line.",
        cue = "Freeze the head",
        family = FailureFamily.FAMILY_D_MOMENTUM_COLLAPSE,
        acousticDesign = "Wobbly Detuned Siren (600 Hz with heavy ±80 Hz LFO wobble, 250 ms)",
        acousticIntuition = "Sounds \"out of balance\" and spinning off-axis, matching your >100 km/h head/torso drift.",
        biomechanicalFix = "At >100 km/h, your torso rotation is outrunning your arms (spinning off the ball). To generate high bat speed without losing shape, the power must come from ground force and late wrist snap against a braced front side, keeping your head anchored over the front knee."
    ),

    // ── Clean Hit ──
    CLEAN_STROKE(
        shotName = "Clean Stroke",
        failureDescription = "Within controlled technical envelope; centered impact.",
        cue = "Solid",
        family = null,
        acousticDesign = "Crystal Harmonic Dual Chime (880 Hz + 1760 Hz decay, 150 ms)",
        acousticIntuition = "Clear, pure harmonic tone confirming controlled mechanical envelope and centered impact.",
        biomechanicalFix = "Maintain this balanced shape and timing."
    )
}

/**
 * Lightweight real-time kinematic impact evaluator running on the 416Hz bat sensor stream.
 * Detects ball contact within 20ms and evaluates shot-specific diagnostic rules within ~80ms.
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
        const val MIN_SWING_GYRO_RAD_S = 5.5f         // Active swing angular rate threshold
        private const val DEG_TO_RAD = (PI / 180.0).toFloat()
        private const val GYRO_TO_KMH = 4.5f                  // Linear tip speed conversion factor

        // Post-impact delivery schedule
        const val SILENCE_DELAY_MS = 300L             // T+0 to 300ms: Silence for physical acoustic crack
        const val TTS_AFTER_EARCON_DELAY_MS = 250L    // T+550ms: Cue fires after earcon finishes
    }

    var lastImpactTimeMs = 0L
        private set

    // Tracks previous fault for Stage 3 (Silent Diagnostic) repetition detection
    var lastDiagnosedFault: LiveShotFault? = null
        private set

    // Ring buffers for recent sensor telemetry (~100 samples = ~240ms at 416Hz)
    private val bufferSize = 100
    private val gyroMags = FloatArray(bufferSize)
    private val gyroY = FloatArray(bufferSize)     // Long-axis handle roll / twist
    private val gyroZ = FloatArray(bufferSize)     // Lateral face angle rate
    private val accMags = FloatArray(bufferSize)
    private val sampleTimestamps = LongArray(bufferSize)
    private var bufferIndex = 0
    private var sampleCount = 0

    // Downswing tracking
    private var maxDownswingGyroRadS = 0.0f
    private var isSwingActive = false

    /**
     * Ingests a raw 3-axis accelerometer sample from the Polar bat handle sensor.
     */
    fun processAccSample(
        phoneMs: Long,
        @Suppress("UNUSED_PARAMETER") sensorNs: Long = 0L,
        x: Float,
        y: Float,
        z: Float
    ) {
        val magG = sqrt(x * x + y * y + z * z) / 1000.0f
        val idx = bufferIndex % bufferSize
        accMags[idx] = magG
        sampleTimestamps[idx] = phoneMs

        val now = if (phoneMs > 0L) phoneMs else System.currentTimeMillis()
        if (magG >= ACC_IMPACT_THRESHOLD_G && isSwingActive && (lastImpactTimeMs == 0L || now - lastImpactTimeMs > IMPACT_COOLDOWN_MS)) {
            if (maxDownswingGyroRadS >= MIN_SWING_GYRO_RAD_S) {
                lastImpactTimeMs = now
                isSwingActive = false
                evaluateImpact(now, maxDownswingGyroRadS, magG)
                maxDownswingGyroRadS = 0.0f
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
        val gyroRadS = sqrt(x * x + y * y + z * z) * DEG_TO_RAD
        val gyroYRadS = y * DEG_TO_RAD
        val gyroZRadS = z * DEG_TO_RAD

        val idx = bufferIndex % bufferSize
        gyroMags[idx] = gyroRadS
        gyroY[idx] = gyroYRadS
        gyroZ[idx] = gyroZRadS
        sampleTimestamps[idx] = phoneMs
        bufferIndex++
        sampleCount++

        if (gyroRadS >= MIN_SWING_GYRO_RAD_S) {
            isSwingActive = true
            if (gyroRadS > maxDownswingGyroRadS) {
                maxDownswingGyroRadS = gyroRadS
            }
        } else if (gyroRadS < 2.0f && !isSwingActive) {
            maxDownswingGyroRadS = 0.0f
        }
    }

    private fun evaluateImpact(impactTimeMs: Long, peakGyroRadS: Float, peakAccG: Float) {
        val speedKmh = peakGyroRadS * GYRO_TO_KMH

        val windowSamples = kotlin.math.min(sampleCount, 30)
        var minY = Float.MAX_VALUE
        var maxY = -Float.MAX_VALUE
        var meanZ = 0.0f
        for (i in 0 until windowSamples) {
            val ringIdx = (bufferIndex - 1 - i + bufferSize) % bufferSize
            val y = gyroY[ringIdx]
            if (y < minY) minY = y
            if (y > maxY) maxY = y
            meanZ += gyroZ[ringIdx]
        }
        val twistDeltaRadS = if (maxY >= minY) maxY - minY else 0.0f
        val zRotationRate = if (windowSamples > 0) meanZ / windowSamples else 0.0f

        val fault = diagnoseShot(speedKmh, peakGyroRadS, twistDeltaRadS, zRotationRate)
        Log.i(TAG, "⚡ Evaluated Shot at ${impactTimeMs}ms: speed=%.1f km/h, acc=%.1f g, twist=%.1f rad/s, zRate=%.1f -> $fault"
            .format(speedKmh, peakAccG, twistDeltaRadS, zRotationRate))

        dispatchScheduledFeedback(fault, speedKmh)
    }

    /**
     * Applies empirical failure rules across the entire batting repertoire.
     */
    fun diagnoseShot(
        speedKmh: Float,
        @Suppress("UNUSED_PARAMETER") gyroRadS: Float = 0f,
        twistDeltaRadS: Float,
        zRotationRate: Float
    ): LiveShotFault {
        // 1. Power Drive Over-Swing (> 100 km/h) -> "Freeze the head"
        if (speedKmh > 100.0f) {
            return LiveShotFault.POWER_DRIVE_OVERSWING
        }

        // 2. Drive Outside-In Slicing (vertical bat drive, massive handle twist jerk) -> "Lead with toe"
        if (speedKmh in 68.0f..98.0f && twistDeltaRadS > 6.0f && abs(zRotationRate) < 2.0f) {
            return LiveShotFault.DRIVE_SLICE
        }

        // 3. Pull Shot Skied / Top Edge (horizontal plane with upward attack angle & high roll) -> "Stay tall"
        if (speedKmh in 55.0f..95.0f && abs(zRotationRate) > 2.8f && twistDeltaRadS > 4.5f) {
            return LiveShotFault.PULL_SKIED
        }

        // 4. Drive Bottom-Hand Scoop (vertical drive, bottom wrist lifting upward, moderate twist) -> "Head to pitch"
        if (speedKmh in 60.0f..95.0f && zRotationRate > 3.0f && twistDeltaRadS < 4.5f) {
            return LiveShotFault.DRIVE_SCOOP
        }

        // 5. Pull Shot Choked / Aborted (checked pull, decelerating) -> "Clear the hip"
        if (speedKmh in 35.0f..54.0f && abs(zRotationRate) > 2.2f && twistDeltaRadS in 1.5f..4.0f) {
            return LiveShotFault.PULL_CHOKED
        }

        // 6. Back Foot Punch Upward Scoop (moderate back foot speed 50-65 km/h) -> "High hands"
        if (speedKmh in 50.0f..65.0f && zRotationRate in 2.2f..3.5f && twistDeltaRadS > 3.5f) {
            return LiveShotFault.PUNCH_SCOOP
        }

        // 7. Cut Shot Over-Hit / Face Open (high speed > 65 km/h with lateral roll) -> "Behind point"
        if (speedKmh > 65.0f && twistDeltaRadS > 4.0f) {
            return LiveShotFault.CUT_OVERHIT
        }

        // 8. Defense "Hard Hands" / Poking (downswing block played too fast) -> "Behind the knee"
        if (speedKmh in 30.0f..48.0f && twistDeltaRadS < 2.5f && abs(zRotationRate) < 1.5f) {
            return LiveShotFault.DEFENSE_HARD_HANDS
        }

        // 9. Glide / Steer Pushed Hard -> "Give with it"
        if (speedKmh in 36.0f..48.0f && abs(zRotationRate) in 1.5f..3.0f && twistDeltaRadS < 3.5f) {
            return LiveShotFault.GLIDE_PUSHED
        }

        // 10. Flick / Glance Leading Edge (face closed prematurely) -> "Show the face"
        if (speedKmh in 45.0f..70.0f && zRotationRate < -2.0f && twistDeltaRadS > 3.0f) {
            return LiveShotFault.FLICK_LEADING_EDGE
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
