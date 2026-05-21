package com.mrpeel.cricketbattingtracker.ml

import android.util.Log
import com.mrpeel.cricketbattingtracker.services.ShotData
import kotlin.math.*

/**
 * Circular Buffer for sensor data
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
}

/**
 * Circular Buffer for orientation quaternion data
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
}

enum class DetectorState {
    SEARCHING_STANCE,
    SWING_SEARCH,
    MEASURING_ARC,
    CONTACT_WAIT
}

class SwingDetector {
    private val TAG = "SwingDetector"

    // Increase capacity to 500 (10 seconds of history at 50Hz)
    private val gyroBuffer = RingBuffer(500)
    private val accelBuffer = RingBuffer(500)
    private val gravBuffer = RingBuffer(500)
    private val rotationBuffer = RotationRingBuffer(500)

    // Pre-allocated FloatArrays to ensure zero allocations during real-time loops
    private val vLocal = floatArrayOf(0f, -1f, 0f)
    private val qCurr = FloatArray(4)
    private val qRel = FloatArray(4)
    private val qStance = FloatArray(4) { 0f }.apply { this[3] = 1f }
    private val qStanceInv = FloatArray(4) { 0f }.apply { this[3] = 1f }
    private val vRot = FloatArray(3)

    // Math helper functions
    private fun conjugateQuat(q: FloatArray, outQ: FloatArray) {
        outQ[0] = -q[0]
        outQ[1] = -q[1]
        outQ[2] = -q[2]
        outQ[3] = q[3]
    }

    private fun multiplyQuats(q1: FloatArray, q2: FloatArray, outQ: FloatArray) {
        val x1 = q1[0]
        val y1 = q1[1]
        val z1 = q1[2]
        val w1 = q1[3]

        val x2 = q2[0]
        val y2 = q2[1]
        val z2 = q2[2]
        val w2 = q2[3]

        outQ[0] = w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2
        outQ[1] = w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2
        outQ[2] = w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2
        outQ[3] = w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2
    }

    private fun rotateVector(q: FloatArray, v: FloatArray, outV: FloatArray) {
        val qx = q[0]
        val qy = q[1]
        val qz = q[2]
        val qw = q[3]

        val vx = v[0]
        val vy = v[1]
        val vz = v[2]

        val tx = 2.0f * (qy * vz - qz * vy)
        val ty = 2.0f * (qz * vx - qx * vz)
        val tz = 2.0f * (qx * vy - qy * vx)

        outV[0] = vx + qw * tx + (qy * tz - qz * ty)
        outV[1] = vy + qw * ty + (qz * tx - qx * tz)
        outV[2] = vz + qw * tz + (qx * ty - qy * tx)
    }

    private fun calcRelativeRoll(q: FloatArray): Float {
        val x = q[0]
        val y = q[1]
        val z = q[2]
        val w = q[3]
        val roll = atan2(2.0f * (w * y + x * z), 1.0f - 2.0f * (y * y + z * z))
        return roll * 57.295779513f
    }

    private fun averageQuats(indices: List<Int>, outQuat: FloatArray) {
        if (indices.isEmpty()) {
            outQuat[0] = 0f
            outQuat[1] = 0f
            outQuat[2] = 0f
            outQuat[3] = 1f
            return
        }
        val q0x = rotationBuffer.qx[indices[0]]
        val q0y = rotationBuffer.qy[indices[0]]
        val q0z = rotationBuffer.qz[indices[0]]
        val q0w = rotationBuffer.qw[indices[0]]

        var sumX = q0x
        var sumY = q0y
        var sumZ = q0z
        var sumW = q0w

        for (i in 1 until indices.size) {
            val idx = indices[i]
            val qx = rotationBuffer.qx[idx]
            val qy = rotationBuffer.qy[idx]
            val qz = rotationBuffer.qz[idx]
            val qw = rotationBuffer.qw[idx]

            val dot = q0x * qx + q0y * qy + q0z * qz + q0w * qw
            val sign = if (dot >= 0f) 1f else -1f

            sumX += sign * qx
            sumY += sign * qy
            sumZ += sign * qz
            sumW += sign * qw
        }

        val norm = sqrt(sumX * sumX + sumY * sumY + sumZ * sumZ + sumW * sumW)
        if (norm > 0f) {
            outQuat[0] = sumX / norm
            outQuat[1] = sumY / norm
            outQuat[2] = sumZ / norm
            outQuat[3] = sumW / norm
        } else {
            outQuat[0] = 0f
            outQuat[1] = 0f
            outQuat[2] = 0f
            outQuat[3] = 1f
        }
    }

    private fun findClosestRotationIndex(targetTime: Long): Int {
        if (rotationBuffer.size == 0) return -1
        var bestIdx = -1
        var minDiff = Long.MAX_VALUE
        var idx = if (rotationBuffer.head == 0) rotationBuffer.capacity - 1 else rotationBuffer.head - 1
        for (i in 0 until rotationBuffer.size) {
            val diff = abs(rotationBuffer.timestamps[idx] - targetTime)
            if (diff < minDiff) {
                minDiff = diff
                bestIdx = idx
            }
            idx = if (idx == 0) rotationBuffer.capacity - 1 else idx - 1
        }
        return bestIdx
    }

    fun processRotation(values: FloatArray, timestamp: Long) {
        val qx = values[0]
        val qy = values[1]
        val qz = values[2]
        val qw = if (values.size > 3) values[3] else sqrt(max(0.0f, 1.0f - qx * qx - qy * qy - qz * qz))
        rotationBuffer.add(timestamp, qx, qy, qz, qw)
    }

    // State machine variables
    private var detectorState = DetectorState.SEARCHING_STANCE
    private var isInStance = false
    private var stanceStartTime = 0L
    private var stanceExitTime = 0L
    private var swingStartTime = 0L
    private var firstCrossingTime = 0L
    private var peakGyro = 0f
    private var peakGyroTime = 0L
    private var lastShotEndTime = 0L

    var onShotDetected: ((ShotData) -> Unit)? = null

    private val estimatedGravity = FloatArray(3)
    private var gravityFound = false

    fun processGyro(values: FloatArray, timestamp: Long) {
        gyroBuffer.add(timestamp, values[0], values[1], values[2])
        runStateMachine(timestamp)
    }

    fun processAccel(values: FloatArray, timestamp: Long) {
        val mag = sqrt(values[0] * values[0] + values[1] * values[1] + values[2] * values[2])
        accelBuffer.add(timestamp, values[0], values[1], values[2])

        // If hardware gravity is missing, estimate it from accel using low-pass filter.
        // Only update the estimate when NOT in a high-G event (to avoid impact corrupting gravity).
        if (!gravityFound && mag < 15f) {
            val alpha = 0.85f
            estimatedGravity[0] = alpha * estimatedGravity[0] + (1 - alpha) * values[0]
            estimatedGravity[1] = alpha * estimatedGravity[1] + (1 - alpha) * values[1]
            estimatedGravity[2] = alpha * estimatedGravity[2] + (1 - alpha) * values[2]
            gravBuffer.add(timestamp, estimatedGravity[0], estimatedGravity[1], estimatedGravity[2])
        }
    }

    fun processGravity(values: FloatArray, timestamp: Long) {
        gravityFound = true
        gravBuffer.add(timestamp, values[0], values[1], values[2])
    }

    private fun runStateMachine(timestamp: Long) {
        when (detectorState) {
            DetectorState.SEARCHING_STANCE -> {
                // Ignore new stance search if we are in the 1.5s guard window after the last shot
                if (timestamp <= lastShotEndTime + 1_500_000_000L) {
                    return
                }

                // Compute rolling std over the last 500ms
                val windowStart = timestamp - 500_000_000L
                val std = gyroBuffer.calculateStdOfMag(windowStart, timestamp)

                // Require at least 10 samples to ensure stable std calculation
                val samplesInWindow = gyroBuffer.getRange(windowStart, timestamp).size
                if (samplesInWindow >= 10) {
                    if (std < 0.9f) {
                        if (!isInStance) {
                            isInStance = true
                            stanceStartTime = timestamp
                        }
                    } else {
                        if (isInStance) {
                            val duration = timestamp - stanceStartTime
                            if (duration >= 150_000_000L) { // 150ms
                                detectorState = DetectorState.SWING_SEARCH
                                stanceExitTime = timestamp
                                Log.d(TAG, "Stance exit detected at $stanceExitTime. Duration: ${duration / 1_000_000} ms. Searching swing...")
                            }
                            isInStance = false
                        }
                    }
                }
            }
            DetectorState.SWING_SEARCH -> {
                // Timeout after 5.5s
                if (timestamp - stanceExitTime > 5_500_000_000L) {
                    Log.d(TAG, "Swing search timed out. Returning to SEARCHING_STANCE")
                    detectorState = DetectorState.SEARCHING_STANCE
                    isInStance = false
                    return
                }

                val headIdx = if (gyroBuffer.head == 0) gyroBuffer.capacity - 1 else gyroBuffer.head - 1
                val currentMag = gyroBuffer.magnitudes[headIdx]
                if (currentMag >= 5.0f) {
                    detectorState = DetectorState.MEASURING_ARC
                    swingStartTime = timestamp
                    firstCrossingTime = timestamp
                    peakGyro = currentMag
                    peakGyroTime = timestamp
                    Log.d(TAG, "Swing initiated at $firstCrossingTime. Measuring swing arc...")
                }
            }
            DetectorState.MEASURING_ARC -> {
                val headIdx = if (gyroBuffer.head == 0) gyroBuffer.capacity - 1 else gyroBuffer.head - 1
                val currentMag = gyroBuffer.magnitudes[headIdx]
                if (currentMag > peakGyro) {
                    peakGyro = currentMag
                    peakGyroTime = timestamp
                }

                // Wait 1.0s to measure full arc
                if (timestamp - swingStartTime >= 1_000_000_000L) {
                    detectorState = DetectorState.CONTACT_WAIT
                    Log.d(TAG, "Swing peak locked at $peakGyroTime. Peak gyro: $peakGyro. Waiting for contact window...")
                }
            }
            DetectorState.CONTACT_WAIT -> {
                // Wait until trailing contact window (750ms post-peak) is filled
                if (timestamp - peakGyroTime >= 750_000_000L) {
                    Log.d(TAG, "Contact window filled. Evaluating shot...")
                    evaluateShot(firstCrossingTime)
                    detectorState = DetectorState.SEARCHING_STANCE
                    isInStance = false
                }
            }
        }
    }

    private fun evaluateShot(firstCrossingTime: Long) {
        // 1. Find peak gyro in peak search window [firstCrossingTime, firstCrossingTime + 1s]
        val gIndicesPeakSearch = gyroBuffer.getRange(firstCrossingTime, firstCrossingTime + 1_000_000_000L)
        if (gIndicesPeakSearch.isEmpty()) {
            Log.w(TAG, "evaluateShot: No gyro data in peak search window")
            return
        }
        val maxGyroIdx = gIndicesPeakSearch.maxByOrNull { gyroBuffer.magnitudes[it] } ?: gIndicesPeakSearch[0]
        val maxGyroTime = gyroBuffer.timestamps[maxGyroIdx]
        val maxGyro = gyroBuffer.magnitudes[maxGyroIdx]

        // 2. Find start of the bat swing
        val baseline = gyroBuffer.getRange(stanceStartTime, stanceExitTime)
            .map { gyroBuffer.magnitudes[it] }
            .average()
            .toFloat()
            .takeIf { !it.isNaN() } ?: 0f

        val swingSearchIndices = gyroBuffer.getRange(stanceExitTime, maxGyroTime).reversed()
        val threshold = baseline + 3.0f
        val firstSwingSampleIdx = swingSearchIndices.firstOrNull { gyroBuffer.magnitudes[it] > threshold }
        val startBatSwingTime = if (firstSwingSampleIdx != null) {
            gyroBuffer.timestamps[firstSwingSampleIdx]
        } else {
            maxGyroTime - 500_000_000L
        }

        // 3. Search contact window around peak gyro
        val contactStart = maxGyroTime - 450_000_000L
        val contactEnd = maxGyroTime + 750_000_000L
        val aIndices = accelBuffer.getRange(contactStart, contactEnd)
        if (aIndices.isEmpty()) {
            Log.w(TAG, "evaluateShot: No accel data in contact window")
            return
        }
        val contactRowIdx = aIndices.maxByOrNull { accelBuffer.magnitudes[it] } ?: aIndices[0]
        val contactTime = accelBuffer.timestamps[contactRowIdx]
        val maxShock = accelBuffer.magnitudes[contactRowIdx]

        // 4. Find gyro magnitude at contact time
        val gIndicesAll = gyroBuffer.getRange(contactStart, contactEnd)
        val impactGyroIdx = gIndicesAll.minByOrNull { abs(gyroBuffer.timestamps[it] - contactTime) }
        val impactGyro = if (impactGyroIdx != null) gyroBuffer.magnitudes[impactGyroIdx] else maxGyro

        // 5. Basic metrics calculations
        val impactTimeMs = max(0L, (contactTime - startBatSwingTime) / 1_000_000L)
        val efficiency = if (maxGyro > 0f) (impactGyro / maxGyro * 100f) else 0f

        // 6. Accelerometer angles (backlift, follow-through, impact)
        val preAIndices = accelBuffer.getRange(stanceExitTime, contactTime)
        val postAIndices = accelBuffer.getRange(contactTime, maxGyroTime + 1_000_000_000L)

        fun accelAngleY(indices: List<Int>): Float {
            if (indices.isEmpty()) return 0f
            val qi = indices.minByOrNull { accelBuffer.magnitudes[it] }!!
            val mag = accelBuffer.magnitudes[qi]
            return if (mag > 0f) acos((accelBuffer.y[qi] / mag).coerceIn(-1f, 1f)) * 57.3f else 0f
        }

        val impactAngle = accelAngleY(preAIndices)
        val followThroughAngle = accelAngleY(postAIndices)
        val backliftAngle = impactAngle

        // 7. Calculate Stance-Relative Biomechanical Features (Option A)
        // Find stance orientation average
        val stanceIndices = rotationBuffer.getRange(stanceStartTime, stanceExitTime)
        val finalStanceIndices = if (stanceIndices.isEmpty()) {
            rotationBuffer.getRange(0L, stanceExitTime).take(5)
        } else {
            stanceIndices
        }
        averageQuats(finalStanceIndices, qStance)
        conjugateQuat(qStance, qStanceInv)

        // Compute swing plane delta X and Z
        val swingOriIndices = rotationBuffer.getRange(startBatSwingTime, contactTime)
        var deltaX = 0f
        var deltaZ = 0f
        if (swingOriIndices.size >= 2) {
            var minX = Float.MAX_VALUE
            var maxX = -Float.MAX_VALUE
            var minZ = Float.MAX_VALUE
            var maxZ = -Float.MAX_VALUE

            for (idx in swingOriIndices) {
                qCurr[0] = rotationBuffer.qx[idx]
                qCurr[1] = rotationBuffer.qy[idx]
                qCurr[2] = rotationBuffer.qz[idx]
                qCurr[3] = rotationBuffer.qw[idx]

                multiplyQuats(qStanceInv, qCurr, qRel)
                rotateVector(qRel, vLocal, vRot)

                if (vRot[0] < minX) minX = vRot[0]
                if (vRot[0] > maxX) maxX = vRot[0]
                if (vRot[2] < minZ) minZ = vRot[2]
                if (vRot[2] > maxZ) maxZ = vRot[2]
            }
            deltaX = maxX - minX
            deltaZ = maxZ - minZ
        }

        // Relative orientation and roll/yaw at impact
        val impactOriIdx = findClosestRotationIndex(contactTime)
        var rollImpactDeg = 0f
        var yawImpactDeg = 0f
        if (impactOriIdx != -1) {
            qCurr[0] = rotationBuffer.qx[impactOriIdx]
            qCurr[1] = rotationBuffer.qy[impactOriIdx]
            qCurr[2] = rotationBuffer.qz[impactOriIdx]
            qCurr[3] = rotationBuffer.qw[impactOriIdx]

            multiplyQuats(qStanceInv, qCurr, qRel)
            rotateVector(qRel, vLocal, vRot)

            rollImpactDeg = calcRelativeRoll(qRel)
            yawImpactDeg = atan2(vRot[0], -vRot[1]) * 57.295779513f
        }

        // Wrist roll feature to output (using biomechanical roll at impact)
        val wristRollDeg = rollImpactDeg

        val postGIndices = gyroBuffer.getRange(contactTime, maxGyroTime + 1_000_000_000L)
        val preGIndices = gyroBuffer.getRange(stanceExitTime, contactTime)
        val snapRatio = if (preGIndices.isNotEmpty() && postGIndices.isNotEmpty()) {
            val preMean = preGIndices.map { gyroBuffer.magnitudes[it] }.average().toFloat()
            val postMax = postGIndices.map { gyroBuffer.magnitudes[it] }.maxOrNull() ?: 0f
            if (preMean > 0f) postMax / preMean else 0f
        } else 0f

        // 8. Hybrid Biomechanical-ML Classifier (Depth-4 Decision Tree)
        var shotType = "UNKNOWN"
        val gyroMag = maxGyro

        if (gyroMag < 8.0f && deltaZ <= 0.40f) {
            shotType = "DEFENCE"
        } else {
            if (rollImpactDeg <= -13.92f) {
                if (gyroMag <= 28.48f) {
                    if (gyroMag <= 17.40f) {
                        shotType = if (yawImpactDeg <= 78.05f) "COVER DRIVE" else "ON-SIDE FLICK"
                    } else {
                        shotType = "PULL SHOT"
                    }
                } else { // gyroMag > 28.48f
                    if (yawImpactDeg <= 64.80f) {
                        shotType = if (gyroMag <= 29.61f) "ON-SIDE FLICK" else "PULL SHOT"
                    } else {
                        shotType = "ON-SIDE FLICK"
                    }
                }
            } else { // rollImpactDeg > -13.92f
                if (deltaZ <= 0.40f) {
                    if (deltaX <= 0.08f) {
                        shotType = "COVER DRIVE"
                    } else { // deltaX > 0.08f
                        shotType = if (deltaZ <= 0.03f) "PUSH" else "ON-SIDE FLICK"
                    }
                } else { // deltaZ > 0.40f
                    shotType = if (deltaX <= 1.16f) "COVER DRIVE" else "ON-SIDE FLICK"
                }
            }
        }

        Log.d(TAG, "EVAL: Type=$shotType, MaxG=$gyroMag, Snap=$snapRatio, Roll=$rollImpactDeg, Angle=$yawImpactDeg, DX=$deltaX, DZ=$deltaZ")

        // Shot Type Multipliers (Straight-bat: 1.45f, Cross-bat: 1.30f)
        val multiplier = if (shotType in listOf("COVER DRIVE", "DEFENCE", "PUSH")) 1.45f else 1.30f

        // Final Speed in km/h based on approved 0.68m bat radius
        val finalSpeedKmh = maxGyro * 0.68f * 3.6f * multiplier

        val isHit = maxShock >= 12.0f
        val sweetSpot = if (isHit) {
            val ratio = maxShock / finalSpeedKmh
            when {
                ratio < 2.5f -> "Excellent"
                ratio < 3.0f -> "Good"
                else -> "Poor"
            }
        } else {
            "Miss"
        }

        Log.d(TAG, "SHOT: $shotType, Speed: $finalSpeedKmh, Hit: $isHit, Shock: $maxShock, SS: $sweetSpot")

        // Record last shot end time to block stance search for a 1.5s recovery guard window
        lastShotEndTime = maxGyroTime + 1_000_000_000L

        onShotDetected?.invoke(ShotData(
            speedKmh = finalSpeedKmh,
            isHit = isHit,
            peakAccel = maxShock,
            sweetSpot = sweetSpot,
            efficiency = efficiency,
            impactTimeMs = impactTimeMs,
            backliftAngle = backliftAngle,
            followThroughAngle = followThroughAngle,
            shotType = shotType,
            wristRollDeg = wristRollDeg
        ))
    }
}
