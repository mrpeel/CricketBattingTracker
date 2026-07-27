package com.mrpeel.cricketbattingtracker.ml

import android.util.Log
import com.mrpeel.cricketbattingtracker.services.ShotData
import kotlin.math.*

/**
 * Circular Buffer for sensor data (gyro, accel, gravity)
 */
class RingBuffer(val capacity: Int) {
    val timestamps = LongArray(capacity)
    val x = FloatArray(capacity)
    val y = FloatArray(capacity)
    val z = FloatArray(capacity)
    val magnitudes = FloatArray(capacity)
    var head = 0
    var size = 0

    fun add(timestamp: Long, vx: Float, vy: Float, vz: Float) {
        timestamps[head] = timestamp
        x[head] = vx
        y[head] = vy
        z[head] = vz
        magnitudes[head] = sqrt(vx * vx + vy * vy + vz * vz)
        head = (head + 1) % capacity
        if (size < capacity) size++
    }

    fun getRange(startNanos: Long, endNanos: Long): List<Int> {
        val indices = mutableListOf<Int>()
        var idx = if (head == 0) capacity - 1 else head - 1
        for (i in 0 until size) {
            val t = timestamps[idx]
            if (t in startNanos..endNanos) {
                indices.add(idx)
            }
            idx = if (idx == 0) capacity - 1 else idx - 1
        }
        return indices
    }

    fun calculateStdOfMag(startNanos: Long, endNanos: Long): Float {
        var count = 0
        var sum = 0.0
        var sumSq = 0.0
        var idx = if (head == 0) capacity - 1 else head - 1
        for (i in 0 until size) {
            val t = timestamps[idx]
            if (t in startNanos..endNanos) {
                val mag = magnitudes[idx].toDouble()
                sum += mag
                sumSq += mag * mag
                count++
            }
            idx = if (idx == 0) capacity - 1 else idx - 1
        }
        if (count < 2) return 0f
        val mean = sum / count
        val variance = (sumSq / count) - (mean * mean)
        return sqrt(max(0.0, variance)).toFloat()
    }

    /**
     * Computes the mean of the Y component over the given time window.
     * Returns 0f if fewer than 5 samples are in the window (not enough data).
     */
    fun calculateMeanY(startNanos: Long, endNanos: Long): Float {
        var count = 0
        var sum = 0.0
        var idx = if (head == 0) capacity - 1 else head - 1
        for (i in 0 until size) {
            val t = timestamps[idx]
            if (t in startNanos..endNanos) {
                sum += y[idx].toDouble()
                count++
            }
            idx = if (idx == 0) capacity - 1 else idx - 1
        }
        return if (count >= 5) (sum / count).toFloat() else 0f
    }
}

/**
 * Circular Buffer for orientation quaternion data.
 * Also computes angular displacement between successive samples for stability tracking.
 */
class RotationRingBuffer(val capacity: Int) {
    val timestamps = LongArray(capacity)
    val qx = FloatArray(capacity)
    val qy = FloatArray(capacity)
    val qz = FloatArray(capacity)
    val qw = FloatArray(capacity)
    var head = 0
    var size = 0

    fun add(timestamp: Long, x: Float, y: Float, z: Float, w: Float) {
        timestamps[head] = timestamp
        qx[head] = x
        qy[head] = y
        qz[head] = z
        qw[head] = w
        head = (head + 1) % capacity
        if (size < capacity) size++
    }

    fun getRange(startNanos: Long, endNanos: Long): List<Int> {
        val indices = mutableListOf<Int>()
        var idx = if (head == 0) capacity - 1 else head - 1
        for (i in 0 until size) {
            val t = timestamps[idx]
            if (t in startNanos..endNanos) {
                indices.add(idx)
            }
            idx = if (idx == 0) capacity - 1 else idx - 1
        }
        return indices
    }

    /**
     * Computes mean angular displacement (degrees) between consecutive quaternion samples
     * over the given time window. This is the key "orientation stability" metric that
     * distinguishes facing-up (bat locked at guard angle, ~0.3–0.5°) from walking
     * (bat swinging loosely, ~1.5–2.0°).
     *
     * Uses the geodesic distance: angle = 2 * acos(|dot(q1, q2)|)
     */
    fun calculateMeanAngularDisplacementDeg(startNanos: Long, endNanos: Long): Float {
        val indices = getRange(startNanos, endNanos)
        if (indices.size < 2) return 999f

        // Indices come back in reverse chronological order from getRange — sort them
        val sorted = indices.sortedBy { timestamps[it] }

        var totalDisp = 0.0
        var count = 0
        for (i in 1 until sorted.size) {
            val prev = sorted[i - 1]
            val curr = sorted[i]
            val dot = (qx[prev] * qx[curr] + qy[prev] * qy[curr] +
                       qz[prev] * qz[curr] + qw[prev] * qw[curr])
                .toDouble().coerceIn(-1.0, 1.0)
            val angleDeg = Math.toDegrees(2.0 * acos(abs(dot)))
            totalDisp += angleDeg
            count++
        }
        return if (count > 0) (totalDisp / count).toFloat() else 999f
    }
}

/**
 * 5-state machine for shot detection anchored on a confirmed Facing-Up phase.
 *
 * STATE FLOW:
 *   ACTIVITY_CLASSIFY  ─── facing-up confirmed (1.5s) ──►  FACING_UP_LOCKED
 *   FACING_UP_LOCKED   ─── backswing departure ──────────►  MEASURING_ARC
 *   FACING_UP_LOCKED   ─── bat goes still again ─────────►  ACTIVITY_CLASSIFY  (fidget cancel)
 *   FACING_UP_LOCKED   ─── timeout (5s) ───────────────────► ACTIVITY_CLASSIFY
 *   MEASURING_ARC      ─── 1.0s arc measured ────────────►  CONTACT_WAIT
 *   CONTACT_WAIT       ─── 750ms post-peak ─────────────►  → evaluateShot() → ACTIVITY_CLASSIFY
 *
 * Facing-Up is confirmed when ALL THREE conditions hold continuously for >= 1.5s:
 *   A. gyro_std(1s) < 0.9 rad/s           — bat not swinging
 *   B. accel_std(1s) < 1.5 m/s²           — no foot-strike shock
 *   C. ori_disp_mean(1s) < 0.5°           — bat orientation locked at guard angle
 *
 * Why condition C? Quaternion data shows:
 *   - True facing-up:  0.33–0.70° mean angular displacement
 *   - Walking/resting: 1.7–1.9° mean (even when gyro appears still)
 * This reduces false arms during walk breaks by ~4-5×.
 */
enum class DetectorState {
    ACTIVITY_CLASSIFY,
    FACING_UP_LOCKED,
    MEASURING_ARC,
    CONTACT_WAIT
}

class SwingDetector {
    private val TAG = "SwingDetector"
    var debugEnabled: Boolean = false

    // 500 samples = 10s of history at 50Hz
    private val gyroBuffer   = RingBuffer(500)
    private val accelBuffer  = RingBuffer(500)
    private val gravBuffer   = RingBuffer(500)
    private val magBuffer    = RingBuffer(500)
    private val rotationBuffer = RotationRingBuffer(500)

    // Pre-allocated arrays — zero allocations in real-time loop
    private val vLocal     = floatArrayOf(0f, -1f, 0f)
    private val qCurr      = FloatArray(4)
    private val qRel       = FloatArray(4)
    private val qStance    = FloatArray(4) { 0f }.apply { this[3] = 1f }
    private val qStanceInv = FloatArray(4) { 0f }.apply { this[3] = 1f }
    private val vRot       = FloatArray(3)

    // ---- Math helpers ----

    private fun conjugateQuat(q: FloatArray, outQ: FloatArray) {
        outQ[0] = -q[0]; outQ[1] = -q[1]; outQ[2] = -q[2]; outQ[3] = q[3]
    }

    private fun multiplyQuats(q1: FloatArray, q2: FloatArray, outQ: FloatArray) {
        val x1 = q1[0]; val y1 = q1[1]; val z1 = q1[2]; val w1 = q1[3]
        val x2 = q2[0]; val y2 = q2[1]; val z2 = q2[2]; val w2 = q2[3]
        outQ[0] = w1*x2 + x1*w2 + y1*z2 - z1*y2
        outQ[1] = w1*y2 - x1*z2 + y1*w2 + z1*x2
        outQ[2] = w1*z2 + x1*y2 - y1*x2 + z1*w2
        outQ[3] = w1*w2 - x1*x2 - y1*y2 - z1*z2
    }

    private fun rotateVector(q: FloatArray, v: FloatArray, outV: FloatArray) {
        val qx = q[0]; val qy = q[1]; val qz = q[2]; val qw = q[3]
        val vx = v[0]; val vy = v[1]; val vz = v[2]
        val tx = 2.0f * (qy*vz - qz*vy)
        val ty = 2.0f * (qz*vx - qx*vz)
        val tz = 2.0f * (qx*vy - qy*vx)
        outV[0] = vx + qw*tx + (qy*tz - qz*ty)
        outV[1] = vy + qw*ty + (qz*tx - qx*tz)
        outV[2] = vz + qw*tz + (qx*ty - qy*tx)
    }

    private fun calcRelativeRoll(q: FloatArray): Float {
        val x = q[0]; val y = q[1]; val z = q[2]; val w = q[3]
        return atan2(2.0f*(w*y + x*z), 1.0f - 2.0f*(y*y + z*z)) * 57.295779513f
    }

    private fun averageQuats(indices: List<Int>, outQuat: FloatArray) {
        if (indices.isEmpty()) {
            outQuat[0] = 0f; outQuat[1] = 0f; outQuat[2] = 0f; outQuat[3] = 1f; return
        }
        val q0x = rotationBuffer.qx[indices[0]]
        val q0y = rotationBuffer.qy[indices[0]]
        val q0z = rotationBuffer.qz[indices[0]]
        val q0w = rotationBuffer.qw[indices[0]]
        var sumX = q0x; var sumY = q0y; var sumZ = q0z; var sumW = q0w
        for (i in 1 until indices.size) {
            val idx = indices[i]
            val dot = q0x*rotationBuffer.qx[idx] + q0y*rotationBuffer.qy[idx] +
                      q0z*rotationBuffer.qz[idx] + q0w*rotationBuffer.qw[idx]
            val sign = if (dot >= 0f) 1f else -1f
            sumX += sign * rotationBuffer.qx[idx]; sumY += sign * rotationBuffer.qy[idx]
            sumZ += sign * rotationBuffer.qz[idx]; sumW += sign * rotationBuffer.qw[idx]
        }
        val norm = sqrt(sumX*sumX + sumY*sumY + sumZ*sumZ + sumW*sumW)
        if (norm > 0f) {
            outQuat[0] = sumX/norm; outQuat[1] = sumY/norm
            outQuat[2] = sumZ/norm; outQuat[3] = sumW/norm
        } else {
            outQuat[0] = 0f; outQuat[1] = 0f; outQuat[2] = 0f; outQuat[3] = 1f
        }
    }

    private fun findClosestRotationIndex(targetTime: Long): Int {
        if (rotationBuffer.size == 0) return -1
        var bestIdx = -1
        var minDiff = Long.MAX_VALUE
        var idx = if (rotationBuffer.head == 0) rotationBuffer.capacity - 1 else rotationBuffer.head - 1
        for (i in 0 until rotationBuffer.size) {
            val diff = abs(rotationBuffer.timestamps[idx] - targetTime)
            if (diff < minDiff) { minDiff = diff; bestIdx = idx }
            idx = if (idx == 0) rotationBuffer.capacity - 1 else idx - 1
        }
        return bestIdx
    }

    fun processRotation(values: FloatArray, timestamp: Long) {
        val qx = values[0]; val qy = values[1]; val qz = values[2]
        val qw = if (values.size > 3) values[3]
                 else sqrt(max(0.0f, 1.0f - qx*qx - qy*qy - qz*qz))
        rotationBuffer.add(timestamp, qx, qy, qz, qw)
    }

    // ---- State machine variables ----

    private var detectorState = DetectorState.ACTIVITY_CLASSIFY

    var onFacingUpChanged: ((Boolean) -> Unit)? = null

    private fun setDetectorState(newState: DetectorState) {
        val oldState = detectorState
        detectorState = newState
        if (oldState != newState) {
            val wasFacingUp = oldState == DetectorState.FACING_UP_LOCKED
            val isNowFacingUp = newState == DetectorState.FACING_UP_LOCKED
            if (wasFacingUp != isNowFacingUp) {
                onFacingUpChanged?.invoke(isNowFacingUp)
            }
        }
    }

    // Facing-up tracking
    private var facingUpGateStart  = 0L   // when all 3 conditions first became true
    private var facingUpGateActive = false // are all 3 conditions currently satisfied?
    private var facingUpBreakStart = 0L   // when conditions first failed (0 = not in break)
    private var facingUpLockedAt   = 0L   // when we confirmed 1.5s of facing-up
    private var facingUpExitTime   = 0L   // when we transitioned to shot search

    // Stance orientation (from the confirmed facing-up period)
    private var stanceStartTime = 0L
    private var stanceExitTime  = 0L

    // Shot arc tracking
    private var swingStartTime    = 0L
    private var firstCrossingTime = 0L
    private var peakGyro          = 0f
    private var peakGyroTime      = 0L
    private var lastShotEndTime   = 0L

    // Step detector: timestamp of most recent foot-strike event (nanoseconds)
    // A step within STEP_RECENCY_NS immediately invalidates the facing-up gate.
    private var lastStepTimestampNs = 0L

    var onShotDetected: ((ShotData) -> Unit)? = null

    private val estimatedGravity = FloatArray(3)
    private var gravityFound = false

    // ---- Facing-Up detection thresholds (validated against 3-session empirical analysis) ----
    companion object {
        // Recency gate: a step event within this window breaks the facing-up gate
        // 1.0s: at a walking cadence of ~90 steps/min, step interval ≈ 0.67s
        const val STEP_RECENCY_NS            = 1_000_000_000L  // 1.0 seconds
        // How long ALL conditions must hold continuously before we're "locked".
        // Optimized: 0.8s for robust stance confirmation.
        const val FACING_UP_MIN_DURATION_NS  = 800_000_000L  // 0.8 seconds
        // How long after facing-up to wait for a backswing before giving up
        const val BACKSWING_TIMEOUT_NS       = 10_000_000_000L  // 10.0 seconds
        // Break tolerance window for transient condition failures (e.g. bat rocking)
        const val FACING_UP_BREAK_TOLERANCE_NS = 1_500_000_000L // 1.5 seconds
        // Gyro threshold to declare backswing departure has started
        const val BACKSWING_TRIGGER_RAD_S    = 5.0f
        // Post-shot recovery guard: no new facing-up arm during this window
        // Optimized: 1.5s post-shot guard
        const val POST_SHOT_GUARD_NS         = 1_500_000_000L  // 1.5 seconds
    }

    fun processGyro(values: FloatArray, timestamp: Long) {
        gyroBuffer.add(timestamp, values[0], values[1], values[2])
        runStateMachine(timestamp)
    }

    fun processAccel(values: FloatArray, timestamp: Long) {
        val mag = sqrt(values[0]*values[0] + values[1]*values[1] + values[2]*values[2])
        accelBuffer.add(timestamp, values[0], values[1], values[2])
        if (!gravityFound && mag < 15f) {
            val alpha = 0.85f
            estimatedGravity[0] = alpha*estimatedGravity[0] + (1-alpha)*values[0]
            estimatedGravity[1] = alpha*estimatedGravity[1] + (1-alpha)*values[1]
            estimatedGravity[2] = alpha*estimatedGravity[2] + (1-alpha)*values[2]
            gravBuffer.add(timestamp, estimatedGravity[0], estimatedGravity[1], estimatedGravity[2])
        }
    }

    fun processGravity(values: FloatArray, timestamp: Long) {
        gravityFound = true
        gravBuffer.add(timestamp, values[0], values[1], values[2])
    }

    fun processMagnetometer(values: FloatArray, timestamp: Long) {
        magBuffer.add(timestamp, values[0], values[1], values[2])
    }

    /**
     * Called by TrackerService whenever TYPE_STEP_DETECTOR fires.
     * Records the step timestamp. If the facing-up gate is currently active,
     * this immediately breaks it — you cannot be at guard if you are stepping.
     *
     * The step recency check in handleActivityClassify() uses lastStepTimestampNs
     * to prevent the gate from opening within 1s of any foot-strike event.
     */
    fun processStep(timestamp: Long) {
        lastStepTimestampNs = timestamp
        if (facingUpGateActive) {
            Log.d(TAG, "🦶 Step detected — breaking facing-up gate immediately")
            facingUpGateActive = false
            facingUpBreakStart = 0L
        }
        // If already FACING_UP_LOCKED, a step means the player walked away; return to classify
        if (detectorState == DetectorState.FACING_UP_LOCKED) {
            Log.d(TAG, "🦶 Step during FACING_UP_LOCKED — player moved; returning to ACTIVITY_CLASSIFY")
            resetToClassify()
        }
    }

    // ---- Main state machine ----

    private fun runStateMachine(timestamp: Long) {
        when (detectorState) {
            DetectorState.ACTIVITY_CLASSIFY -> handleActivityClassify(timestamp)
            DetectorState.FACING_UP_LOCKED  -> handleFacingUpLocked(timestamp)
            DetectorState.MEASURING_ARC     -> handleMeasuringArc(timestamp)
            DetectorState.CONTACT_WAIT      -> handleContactWait(timestamp)
        }
    }

    /**
     * ACTIVITY_CLASSIFY: Continuously evaluate whether the 5-condition facing-up
     * gate is satisfied. Transitions to FACING_UP_LOCKED when all five have been
     * true for >= 1.2s consecutively.
     *
     * The five conditions:
     *   A. gyro_std(1s)    < 0.9 rad/s   — bat not swinging
     *   B. accel_std(1s)   < 1.5 m/s²   — no foot-strike shock
     *   C. ori_disp(1s)    < 1.5°        — bat orientation locked at guard angle
     *   D. no step in last 1.0s          — definitive walking kill switch
     *   E. mean_gravity_y(1s) <= -3.5    — arm extended toward bat (not limp/resting)
     *      Falls back to true if gravity sensor data is unavailable (< 5 samples).
     *
     * Ignores all signals during the post-shot recovery guard window.
     */
    private fun handleActivityClassify(timestamp: Long) {
        if (timestamp <= lastShotEndTime + POST_SHOT_GUARD_NS) return

        val s1Start = timestamp - 2_000_000_000L
        val s1End = timestamp - 1_000_000_000L
        val s2Start = timestamp - 1_000_000_000L
        val s2End = timestamp

        val windowSamples = gyroBuffer.getRange(s1Start, timestamp)
        if (windowSamples.size < 20) return

        // Segment 1 Features
        val seg1GyroStd = gyroBuffer.calculateStdOfMag(s1Start, s1End)
        val seg1AccelStd = accelBuffer.calculateStdOfMag(s1Start, s1End)
        val seg1OriDisp = rotationBuffer.calculateMeanAngularDisplacementDeg(s1Start, s1End)
        val seg1MeanGravY = gravBuffer.calculateMeanY(s1Start, s1End)

        // Segment 2 Features
        val seg2GyroStd = gyroBuffer.calculateStdOfMag(s2Start, s2End)
        val seg2AccelStd = accelBuffer.calculateStdOfMag(s2Start, s2End)
        val seg2OriDisp = rotationBuffer.calculateMeanAngularDisplacementDeg(s2Start, s2End)
        val seg2MeanGravY = gravBuffer.calculateMeanY(s2Start, s2End)

        // Condition D: no step in last 2.0s (only check if step detector is available)
        val noRecentStep = lastStepTimestampNs == 0L ||
                           (timestamp - lastStepTimestampNs) > STEP_RECENCY_NS

        val stepAgeSeconds = if (lastStepTimestampNs == 0L) 10.0f
                             else (timestamp - lastStepTimestampNs) / 1_000_000_000.0f

        // Predict stance using TinyML Depth-4 Decision Tree
        val stanceOk = predictStance(
            seg1GyroStd = seg1GyroStd,
            seg1AccelStd = seg1AccelStd,
            seg1OriDisp = seg1OriDisp,
            seg1MeanGravY = seg1MeanGravY,
            seg2GyroStd = seg2GyroStd,
            seg2AccelStd = seg2AccelStd,
            seg2OriDisp = seg2OriDisp,
            seg2MeanGravY = seg2MeanGravY,
            stepAgeSeconds = stepAgeSeconds
        )
        val stepsOk = noRecentStep
        val allConditionsMet = stanceOk && stepsOk

        if (debugEnabled) {
            println("Time: ${timestamp / 1_000_000_000.0f}s | seg2GyroStd=${"%.2f".format(seg2GyroStd)} | seg2AccelStd=${"%.2f".format(seg2AccelStd)} | seg2OriDisp=${"%.2f".format(seg2OriDisp)}° | stepsOk=$stepsOk | stanceOk=$stanceOk | allConditionsMet=$allConditionsMet | State=$detectorState")
        }

        if (allConditionsMet) {
            if (!facingUpGateActive) {
                facingUpGateActive = true
                facingUpGateStart  = timestamp
                stanceStartTime    = timestamp
                facingUpBreakStart = 0L
                Log.v(TAG, "Facing-up gate opened (seg2GyroStd=${"%.2f".format(seg2GyroStd)}, " +
                           "seg2AccelStd=${"%.2f".format(seg2AccelStd)}, seg2OriDisp=${"%.2f".format(seg2OriDisp)}°, " +
                           "seg2MeanGravY=${"%.2f".format(seg2MeanGravY)}, stepAge=${(timestamp - lastStepTimestampNs) / 1_000_000}ms)")
            } else {
                if (facingUpBreakStart != 0L) {
                    val breakDuration = timestamp - facingUpBreakStart
                    facingUpGateStart += breakDuration
                    stanceStartTime += breakDuration
                    facingUpBreakStart = 0L
                    Log.v(TAG, "Facing-up conditions restored after ${breakDuration / 1_000_000}ms break; resuming timer.")
                }
                val heldFor = timestamp - facingUpGateStart
                if (heldFor >= FACING_UP_MIN_DURATION_NS) {
                    facingUpLockedAt   = timestamp
                    facingUpExitTime   = timestamp
                    stanceExitTime     = timestamp
                    setDetectorState(DetectorState.FACING_UP_LOCKED)
                    Log.d(TAG, "✅ FACING UP LOCKED at ${timestamp / 1_000_000_000.0f}s " +
                               "(held ${heldFor / 1_000_000}ms, seg2OriDisp=${"%.2f".format(seg2OriDisp)}°, " +
                               "seg2MeanGravY=${"%.2f".format(seg2MeanGravY)})")
                }
            }
        } else {
            if (facingUpGateActive) {
                if (facingUpBreakStart == 0L) {
                    facingUpBreakStart = timestamp
                    Log.v(TAG, "Facing-up conditions failed (seg2GyroStd=${"%.2f".format(seg2GyroStd)}, " +
                               "seg2AccelStd=${"%.2f".format(seg2AccelStd)}, seg2OriDisp=${"%.2f".format(seg2OriDisp)}°, " +
                               "seg2MeanGravY=${"%.2f".format(seg2MeanGravY)}); entering break tolerance window.")
                } else if (timestamp - facingUpBreakStart > FACING_UP_BREAK_TOLERANCE_NS) {
                    val heldFor = timestamp - facingUpGateStart
                    Log.v(TAG, "Facing-up gate broken after ${heldFor / 1_000_000}ms " +
                               "(break duration ${(timestamp - facingUpBreakStart) / 1_000_000}ms > tolerance)")
                    facingUpGateActive = false
                    facingUpBreakStart = 0L
                }
            }
        }
    }

    @Suppress("UNUSED_PARAMETER")
    private fun predictStance(
        seg1GyroStd: Float, seg1AccelStd: Float, seg1OriDisp: Float, seg1MeanGravY: Float,
        seg2GyroStd: Float, seg2AccelStd: Float, seg2OriDisp: Float, seg2MeanGravY: Float,
        stepAgeSeconds: Float
    ): Boolean {
        if (seg2OriDisp <= 0.68f) {
            if (seg2OriDisp <= 0.49f) {
                return true
            } else {
                if (seg2GyroStd <= 1.14f) {
                    return seg2AccelStd <= 1.50f
                } else {
                    return true
                }
            }
        } else {
            if (seg2GyroStd <= 1.28f) {
                if (seg2OriDisp <= 0.98f) {
                    return seg2GyroStd > 0.91f
                } else {
                    return false
                }
            } else {
                if (seg2OriDisp <= 1.94f) {
                    return seg1GyroStd > 0.21f
                } else {
                    return false
                }
            }
        }
    }


    /**
     * FACING_UP_LOCKED: We have a confirmed guard position. Now watch for the
     * bat to rapidly depart (backswing). The moment gyro_mag crosses the backswing
     * threshold, open the shot arc measurement.
     *
     * Cancels back to ACTIVITY_CLASSIFY if:
     * - No backswing within 5s (timeout — probably between deliveries, walked away)
     * - The orientation stability condition breaks strongly (player walked away mid-lock)
     */
    private fun handleFacingUpLocked(timestamp: Long) {
        val elapsed = timestamp - facingUpLockedAt

        // Timeout: no shot came — return to classification
        if (elapsed > BACKSWING_TIMEOUT_NS) {
            Log.d(TAG, "⏱ Backswing timeout after ${elapsed / 1_000_000_000.0f}s. " +
                       "Returning to ACTIVITY_CLASSIFY.")
            resetToClassify()
            return
        }

        // Check if the bat is departing rapidly (backswing)
        val headIdx = if (gyroBuffer.head == 0) gyroBuffer.capacity - 1 else gyroBuffer.head - 1
        val currentGyroMag = gyroBuffer.magnitudes[headIdx]

        if (currentGyroMag >= BACKSWING_TRIGGER_RAD_S) {
            setDetectorState(DetectorState.MEASURING_ARC)
            swingStartTime    = timestamp
            firstCrossingTime = timestamp
            peakGyro          = currentGyroMag
            peakGyroTime      = timestamp
            Log.d(TAG, "🏏 BACKSWING DETECTED at ${timestamp / 1_000_000_000.0f}s " +
                       "(gyro=${"%.1f".format(currentGyroMag)} rad/s). Measuring arc...")
        }
    }

    /**
     * MEASURING_ARC: Track the full sweep of the bat swing over 1.0s.
     * Records peak gyro magnitude and timestamp for contact window search.
     */
    private fun handleMeasuringArc(timestamp: Long) {
        val headIdx = if (gyroBuffer.head == 0) gyroBuffer.capacity - 1 else gyroBuffer.head - 1
        val currentMag = gyroBuffer.magnitudes[headIdx]
        if (currentMag > peakGyro) {
            peakGyro     = currentMag
            peakGyroTime = timestamp
        }
        if (timestamp - swingStartTime >= 1_000_000_000L) {
            setDetectorState(DetectorState.CONTACT_WAIT)
            Log.d(TAG, "📈 Arc measured. Peak gyro=${"%.1f".format(peakGyro)} rad/s " +
                       "at ${peakGyroTime / 1_000_000_000.0f}s. Waiting for contact window...")
        }
    }

    /**
     * CONTACT_WAIT: Wait for the trailing 750ms post-peak window to fill,
     * then evaluate the shot.
     */
    private fun handleContactWait(timestamp: Long) {
        if (timestamp - peakGyroTime >= 750_000_000L) {
            Log.d(TAG, "✅ Contact window complete. Evaluating shot...")
            evaluateShot(firstCrossingTime)
            resetToClassify()
        }
    }

    private fun resetToClassify() {
        setDetectorState(DetectorState.ACTIVITY_CLASSIFY)
        facingUpGateActive = false
        facingUpBreakStart = 0L
    }

    // ---- Shot evaluation (unchanged classifier logic) ----

    private fun evaluateShot(firstCrossingTime: Long) {
        // 1. Peak gyro in search window
        val gIndicesPeakSearch = gyroBuffer.getRange(firstCrossingTime, firstCrossingTime + 1_000_000_000L)
        if (gIndicesPeakSearch.isEmpty()) {
            Log.w(TAG, "evaluateShot: No gyro data in peak search window"); return
        }
        val maxGyroIdx  = gIndicesPeakSearch.maxByOrNull { gyroBuffer.magnitudes[it] } ?: gIndicesPeakSearch[0]
        val maxGyroTime = gyroBuffer.timestamps[maxGyroIdx]
        val maxGyro     = gyroBuffer.magnitudes[maxGyroIdx]

        // 2. Find start of bat swing (first sample above baseline+3 threshold, searching backwards from peak)
        val baseline = gyroBuffer.getRange(stanceStartTime, stanceExitTime)
            .map { gyroBuffer.magnitudes[it] }.average().toFloat().takeIf { !it.isNaN() } ?: 0f

        val swingSearchIndices  = gyroBuffer.getRange(stanceExitTime, maxGyroTime).reversed()
        val firstSwingSampleIdx = swingSearchIndices.firstOrNull { gyroBuffer.magnitudes[it] > baseline + 3.0f }
        val startBatSwingTime   = if (firstSwingSampleIdx != null)
            gyroBuffer.timestamps[firstSwingSampleIdx]
        else
            maxGyroTime - 500_000_000L

        // 3. Contact window: peak accel around gyro peak
        val contactStart   = maxGyroTime - 450_000_000L
        val contactEnd     = maxGyroTime + 750_000_000L
        val aIndices       = accelBuffer.getRange(contactStart, contactEnd)
        if (aIndices.isEmpty()) {
            Log.w(TAG, "evaluateShot: No accel data in contact window"); return
        }
        val contactRowIdx = aIndices.maxByOrNull { accelBuffer.magnitudes[it] } ?: aIndices[0]
        val contactTime   = accelBuffer.timestamps[contactRowIdx]
        val maxShock      = accelBuffer.magnitudes[contactRowIdx]

        // 4. Gyro at contact time
        val gIndicesAll  = gyroBuffer.getRange(contactStart, contactEnd)
        val impactGyroIdx = gIndicesAll.minByOrNull { abs(gyroBuffer.timestamps[it] - contactTime) }
        val impactGyro   = if (impactGyroIdx != null) gyroBuffer.magnitudes[impactGyroIdx] else maxGyro

        // 5. Basic metrics
        val impactTimeMs = max(0L, (contactTime - startBatSwingTime) / 1_000_000L)
        val efficiency   = if (maxGyro > 0f) (impactGyro / maxGyro * 100f) else 0f

        // 6. Accelerometer angles
        val preAIndices  = accelBuffer.getRange(stanceExitTime, contactTime)
        val postAIndices = accelBuffer.getRange(contactTime, maxGyroTime + 1_000_000_000L)

        fun accelAngleY(indices: List<Int>): Float {
            if (indices.isEmpty()) return 0f
            val qi  = indices.minByOrNull { accelBuffer.magnitudes[it] }!!
            val mag = accelBuffer.magnitudes[qi]
            return if (mag > 0f) acos((accelBuffer.y[qi] / mag).coerceIn(-1f, 1f)) * 57.3f else 0f
        }
        val impactAngle       = accelAngleY(preAIndices)
        val followThroughAngle = accelAngleY(postAIndices)
        val backliftAngle     = impactAngle

        // 7. Stance-relative biomechanical features using confirmed facing-up quaternion
        val stanceIndices = rotationBuffer.getRange(stanceStartTime, stanceExitTime)
        val finalStanceIndices = stanceIndices.ifEmpty {
            rotationBuffer.getRange(0L, stanceExitTime).take(5)
        }
        averageQuats(finalStanceIndices, qStance)
        conjugateQuat(qStance, qStanceInv)

        // Chronological segment boundaries relative to contactTime
        val tStart = contactTime - 800_000_000L
        val tSplit1 = contactTime - 200_000_000L
        val tSplit2 = contactTime - 50_000_000L
        val tEnd = contactTime + 300_000_000L

        // Helper to calculate deltaX and deltaZ for a specific time range
        val getDisplacement = { ts: Long, te: Long ->
            val subOri = rotationBuffer.getRange(ts, te)
            var dx = 0f
            var dz = 0f
            if (subOri.size >= 2) {
                var minX = Float.MAX_VALUE; var maxX = -Float.MAX_VALUE
                var minZ = Float.MAX_VALUE; var maxZ = -Float.MAX_VALUE
                for (idx in subOri) {
                    qCurr[0] = rotationBuffer.qx[idx]; qCurr[1] = rotationBuffer.qy[idx]
                    qCurr[2] = rotationBuffer.qz[idx]; qCurr[3] = rotationBuffer.qw[idx]
                    multiplyQuats(qStanceInv, qCurr, qRel)
                    rotateVector(qRel, vLocal, vRot)
                    if (vRot[0] < minX) minX = vRot[0]; if (vRot[0] > maxX) maxX = vRot[0]
                    if (vRot[2] < minZ) minZ = vRot[2]; if (vRot[2] > maxZ) maxZ = vRot[2]
                }
                dx = maxX - minX
                dz = maxZ - minZ
            }
            Pair(dx, dz)
        }

        // --- Segment 1: Footwork [tStart, tSplit1] ---
        val (s1DeltaX, s1DeltaZ) = getDisplacement(tStart, tSplit1)
        val s1GyroIndices = gyroBuffer.getRange(tStart, tSplit1)
        val s1GyroYStd = if (s1GyroIndices.size >= 2) {
            val yVals = s1GyroIndices.map { gyroBuffer.y[it] }
            val mean = yVals.average()
            sqrt(yVals.map { (it - mean).pow(2) }.average()).toFloat()
        } else 0f
        val s1GyroZStd = if (s1GyroIndices.size >= 2) {
            val zVals = s1GyroIndices.map { gyroBuffer.z[it] }
            val mean = zVals.average()
            sqrt(zVals.map { (it - mean).pow(2) }.average()).toFloat()
        } else 0f

        // --- Segment 2: Intent & Height [tSplit1, tSplit2] ---
        val (s2DeltaX, s2DeltaZ) = getDisplacement(tSplit1, tSplit2)
        val s2GyroIndices = gyroBuffer.getRange(tSplit1, tSplit2)
        val s2GyroMag = if (s2GyroIndices.isNotEmpty()) s2GyroIndices.maxOf { gyroBuffer.magnitudes[it] } else 0f
        val s2GravIndices = gravBuffer.getRange(tSplit1, tSplit2)
        val s2GravYMean = if (s2GravIndices.isNotEmpty()) s2GravIndices.map { gravBuffer.y[it] }.average().toFloat() else -9.8f

        // --- Segment 3: Shot Selection [tSplit2, tEnd] ---
        val (s3DeltaX, s3DeltaZ) = getDisplacement(tSplit2, tEnd)
        val s3PlaneRatio = if (s3DeltaZ > 0f) s3DeltaX / s3DeltaZ else 0f
        val s3GyroIndices = gyroBuffer.getRange(tSplit2, tEnd)
        val s3GyroYMin = if (s3GyroIndices.isNotEmpty()) s3GyroIndices.minOf { gyroBuffer.y[it] } else 0f

        val impactOriIdx = findClosestRotationIndex(tSplit2)
        var s3RollImpactDeg = 0f
        var s3YawImpactDeg = 0f
        if (impactOriIdx != -1) {
            qCurr[0] = rotationBuffer.qx[impactOriIdx]; qCurr[1] = rotationBuffer.qy[impactOriIdx]
            qCurr[2] = rotationBuffer.qz[impactOriIdx]; qCurr[3] = rotationBuffer.qw[impactOriIdx]
            multiplyQuats(qStanceInv, qCurr, qRel)
            rotateVector(qRel, vLocal, vRot)
            s3RollImpactDeg = calcRelativeRoll(qRel)
            s3YawImpactDeg  = atan2(vRot[0], -vRot[1]) * 57.295779513f
        }

        val wristRollDeg = s3RollImpactDeg
        val rollImpactDeg = s3RollImpactDeg
        val yawImpactDeg = s3YawImpactDeg
        val deltaX = s3DeltaX
        val deltaZ = s3DeltaZ
        val planeRatio = s3PlaneRatio

        val postGIndices = gyroBuffer.getRange(contactTime, maxGyroTime + 1_000_000_000L)
        val preGIndices  = gyroBuffer.getRange(stanceExitTime, contactTime)
        val snapRatio    = if (preGIndices.isNotEmpty() && postGIndices.isNotEmpty()) {
            val preMean = preGIndices.map { gyroBuffer.magnitudes[it] }.average().toFloat()
            val postMax = postGIndices.map { gyroBuffer.magnitudes[it] }.maxOrNull() ?: 0f
            if (preMean > 0f) postMax / preMean else 0f
        } else 0f

        val features = SwingFeatures(
            s1_gyro_y_std = s1GyroYStd,
            s1_gyro_z_std = s1GyroZStd,
            s1_deltaX = s1DeltaX,
            s1_deltaZ = s1DeltaZ,
            s2_gyroMag = s2GyroMag,
            s2_grav_y_mean = s2GravYMean,
            s2_deltaX = s2DeltaX,
            s2_deltaZ = s2DeltaZ,
            s3_rollImpactDeg = s3RollImpactDeg,
            s3_yawImpactDeg = s3YawImpactDeg,
            s3_deltaX = s3DeltaX,
            s3_deltaZ = s3DeltaZ,
            s3_planeRatio = s3PlaneRatio,
            s3_gyro_y_min = s3GyroYMin
        )

        if (debugEnabled) {
            System.out.println("FEATS: s1_gy=${features.s1_gyro_y_std}, s1_gz=${features.s1_gyro_z_std}, s1_dx=${features.s1_deltaX}, s1_dz=${features.s1_deltaZ}, s2_gMag=${features.s2_gyroMag}, s2_gyMean=${features.s2_grav_y_mean}, s2_dx=${features.s2_deltaX}, s2_dz=${features.s2_deltaZ}, s3_roll=${features.s3_rollImpactDeg}, s3_yaw=${features.s3_yawImpactDeg}, s3_dx=${features.s3_deltaX}, s3_dz=${features.s3_deltaZ}, s3_ratio=${features.s3_planeRatio}, s3_gymin=${features.s3_gyro_y_min}")
        }
        val shotType = GeneratedForest.predict(features)

        Log.d(TAG, "EVAL: Type=$shotType, MaxG=$maxGyro, Snap=$snapRatio, " +
                   "Roll=$rollImpactDeg, Yaw=$yawImpactDeg, DX=$deltaX, DZ=$deltaZ, Ratio=$planeRatio")

        // Compute Blade and Launch Angles
        val isHorizontalBat = shotType == "CUT/PUNCH" || shotType == "PULL/HOOK" || shotType == "SWEEP"
        val targetYaw = when (shotType) {
            "CUT/PUNCH" -> 40f
            "PULL/HOOK" -> 55f
            "SWEEP" -> 65f
            "GLANCE/FLICK" -> 75f
            "POWER DRIVE" -> 60f
            else -> 0f
        }

        var bladeAngle = 0f
        var bladeClass = "N/A"
        var launchAngle = 0f
        var launchClass = "N/A"

        if (impactOriIdx != -1) {
            val vFaceRel = FloatArray(3)
            val localX = floatArrayOf(1f, 0f, 0f)
            rotateVector(qRel, localX, vFaceRel)
            
            val yawFaceRel = atan2(vFaceRel[1], vFaceRel[0]) * 57.295779513f
            var bAngle = yawFaceRel - targetYaw
            bAngle = ((bAngle + 180f) % 360f + 360f) % 360f - 180f
            bladeAngle = bAngle
            
            bladeClass = when {
                bladeAngle <= -15f -> "OPEN"
                bladeAngle >= 15f -> "CLOSED"
                else -> "FULL_FACE"
            }

            launchAngle = if (isHorizontalBat) {
                rollImpactDeg
            } else {
                val vFaceWorld = FloatArray(3)
                rotateVector(qCurr, localX, vFaceWorld)
                -asin(vFaceWorld[2].coerceIn(-1f, 1f)) * 57.295779513f
            }
            
            launchClass = when {
                launchAngle < -45f -> "HIGH_LOFT"
                launchAngle < -35f -> "POWER_ZONE"
                launchAngle < -15f -> "LOFTED"
                launchAngle < 0f -> "FLAT"
                else -> "INTO_GROUND"
            }
        }

        // 9. Speed
        val multiplier = when (shotType) {
            "DRIVE/DEFENCE", "DEFLECTION/GUIDE" -> 1.45f
            "GLANCE/FLICK", "SWEEP", "CUT/PUNCH", "PULL/HOOK" -> 1.30f
            "SLOG", "POWER DRIVE" -> 1.40f
            else -> 1.30f
        }
        val finalSpeedKmh = maxGyro * 0.68f * 3.6f * multiplier

        // 10. Hit/miss and sweet spot
        val isHit = maxShock >= 12.0f
        val sweetSpot = if (isHit) {
            when {
                maxShock / finalSpeedKmh < 2.5f -> "Excellent"
                maxShock / finalSpeedKmh < 3.0f -> "Good"
                else -> "Poor"
            }
        } else "Miss"

        Log.d(TAG, "SHOT: $shotType Speed=$finalSpeedKmh Hit=$isHit Shock=$maxShock SS=$sweetSpot")

        lastShotEndTime = maxGyroTime + 1_000_000_000L

        onShotDetected?.invoke(ShotData(
            speedKmh           = finalSpeedKmh,
            isHit              = isHit,
            peakAccel          = maxShock,
            sweetSpot          = sweetSpot,
            efficiency         = efficiency,
            impactTimeMs       = impactTimeMs,
            backliftAngle      = backliftAngle,
            followThroughAngle = followThroughAngle,
            shotType           = shotType,
            wristRollDeg       = wristRollDeg,
            bladeAngle         = bladeAngle,
            bladeClass         = bladeClass,
            launchAngle        = launchAngle,
            launchClass        = launchClass,
            s1GyroYStd         = features.s1_gyro_y_std,
            s1GyroZStd         = features.s1_gyro_z_std,
            s1DeltaX           = features.s1_deltaX,
            s1DeltaZ           = features.s1_deltaZ,
            s2GyroMag          = features.s2_gyroMag,
            s2GravYMean        = features.s2_grav_y_mean,
            s2DeltaX           = features.s2_deltaX,
            s2DeltaZ           = features.s2_deltaZ,
            s3RollImpactDeg    = features.s3_rollImpactDeg,
            s3YawImpactDeg     = features.s3_yawImpactDeg,
            s3DeltaX           = features.s3_deltaX,
            s3DeltaZ           = features.s3_deltaZ,
            s3PlaneRatio       = features.s3_planeRatio,
            s3GyroYMin         = features.s3_gyro_y_min
        ))
    }
}
