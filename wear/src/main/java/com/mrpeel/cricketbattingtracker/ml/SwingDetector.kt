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
}

class SwingDetector {
    private val TAG = "SwingDetector"

    private val IMPACT_SHOCK_THRESHOLD = 20.0f 
    private val WINDOW_PRE_NS = 600_000_000L  
    private val WINDOW_POST_NS = 600_000_000L 
    private val MIN_DISTANCE_NS = 800_000_000L 

    private val gyroBuffer = RingBuffer(250)
    private val accelBuffer = RingBuffer(250)
    private val gravBuffer = RingBuffer(250)

    private var lastImpactTime = 0L
    private var pendingImpactTime = 0L
    var onShotDetected: ((ShotData) -> Unit)? = null

    fun processGyro(values: FloatArray, timestamp: Long) {
        gyroBuffer.add(timestamp, values[0], values[1], values[2])
        checkPendingImpact(timestamp)
    }

    private val estimatedGravity = FloatArray(3)
    private var gravityFound = false

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

        // Stage 1: Detection
        if (mag >= IMPACT_SHOCK_THRESHOLD && timestamp - lastImpactTime > MIN_DISTANCE_NS) {
            if (pendingImpactTime == 0L) {
                pendingImpactTime = timestamp
                Log.d(TAG, "Potential Impact detected at $timestamp. Waiting for window to fill...")
            }
        }
        checkPendingImpact(timestamp)
    }

    fun processGravity(values: FloatArray, timestamp: Long) {
        gravityFound = true
        gravBuffer.add(timestamp, values[0], values[1], values[2])
        checkPendingImpact(timestamp)
    }

    private fun checkPendingImpact(currentTimestamp: Long) {
        if (pendingImpactTime != 0L && currentTimestamp >= pendingImpactTime + WINDOW_POST_NS) {
            Log.d(TAG, "Window full. Evaluating shot from $pendingImpactTime")
            evaluateShot(pendingImpactTime)
            pendingImpactTime = 0L
        }
    }

    private fun evaluateShot(impactTimestamp: Long) {
        lastImpactTime = impactTimestamp
        
        val startT = impactTimestamp - WINDOW_PRE_NS
        val endT = impactTimestamp + WINDOW_POST_NS
        
        val gIndices = gyroBuffer.getRange(startT, endT)
        val aIndices = accelBuffer.getRange(startT, endT)

        Log.d(TAG, "DEBUG: Eval window. Gyro: ${gIndices.size}, Accel: ${aIndices.size}")

        if (gIndices.isEmpty() || aIndices.isEmpty()) {
            Log.w(TAG, "Insufficient data in window (G:${gIndices.size}, A:${aIndices.size})")
            return
        }

        // 1. Basic Metrics
        val impactGyroIdx = gIndices.minByOrNull { abs(gyroBuffer.timestamps[it] - impactTimestamp) } ?: gIndices[0]
        val impactGyro = gyroBuffer.magnitudes[impactGyroIdx]
        val maxGyro = gIndices.map { gyroBuffer.magnitudes[it] }.maxOrNull() ?: 0f
        val maxShock = aIndices.map { accelBuffer.magnitudes[it] }.maxOrNull() ?: 0f
        
        // 2. Professional Analytics
        val efficiency = if (maxGyro > 0) (impactGyro / maxGyro * 100f) else 0f
        
        val preGIndices = gIndices.filter { gyroBuffer.timestamps[it] < impactTimestamp }
        val postGIndices = gIndices.filter { gyroBuffer.timestamps[it] > impactTimestamp }
        val preAIndices = aIndices.filter { accelBuffer.timestamps[it] < impactTimestamp }
        val postAIndices = aIndices.filter { accelBuffer.timestamps[it] > impactTimestamp }

        val backliftIdx = preGIndices.maxByOrNull { gyroBuffer.magnitudes[it] }
        val impactTimeMs = if (backliftIdx != null) (impactTimestamp - gyroBuffer.timestamps[backliftIdx]) / 1_000_000L else 0L

        // Bat angle = direction of gravity = quietest (min-mag) accel sample in pre-shot window.
        // The lowest-magnitude reading has least linear-accel contamination and best represents
        // the gravity vector. This is injectable via ADB and works on real hardware too.
        fun accelAngleY(indices: List<Int>): Float {
            if (indices.isEmpty()) return 0f
            val qi = indices.minByOrNull { accelBuffer.magnitudes[it] }!!
            val mag = accelBuffer.magnitudes[qi]
            return if (mag > 0f) acos((accelBuffer.y[qi] / mag).coerceIn(-1f, 1f)) * 57.3f else 0f
        }

        val impactAngle = accelAngleY(preAIndices)
        val followThroughAngle = accelAngleY(postAIndices)
        val backliftAngle = impactAngle  // same orientation at start

        val wristRollDeg = if (postGIndices.isNotEmpty()) {
            val avgRollVel = postGIndices.map { gyroBuffer.y[it] }.average().toFloat()
            avgRollVel * 0.6f * 57.3f
        } else 0f

        // 3. Classification & Shot-Specific Multipliers
        val snapRatio = if (preGIndices.isNotEmpty() && postGIndices.isNotEmpty()) {
            val preMean = preGIndices.map { gyroBuffer.magnitudes[it] }.average().toFloat()
            val postMax = postGIndices.map { gyroBuffer.magnitudes[it] }.maxOrNull() ?: 0f
            if (preMean > 0) postMax / preMean else 0f
        } else 0f

        var shotType = "UNKNOWN"
        var multiplier = 1.05f 

        if (maxGyro < 8.0f) {
            shotType = "DEFENCE"
            multiplier = 0.85f
        } else if (abs(wristRollDeg) > 60f) {
            shotType = "PULL SHOT"
            multiplier = 1.25f
        } else if (impactGyro > 14f) {
            shotType = "COVER DRIVE"
            multiplier = 1.15f
        } else if (impactAngle > 75f) {
            shotType = "SWEEP"
            multiplier = 0.95f
        } else if (snapRatio > 3.0f && abs(wristRollDeg) > 15f) {
            // ON-SIDE FLICK: late acceleration spike + some wrist involvement
            shotType = "ON-SIDE FLICK"
            multiplier = 1.05f
        } else if (abs(wristRollDeg) < 20f) {
            // PUSH: straight bat, minimal wrist, moderate speed
            shotType = "PUSH"
            multiplier = 0.9f
        } else {
            shotType = "ON-SIDE FLICK"
            multiplier = 1.05f
        }
        Log.d(TAG, "EVAL: Type=$shotType, MaxG=$maxGyro, Snap=$snapRatio, Roll=$wristRollDeg, Angle=$impactAngle")

        val finalSpeedKmh = impactGyro * 0.8f * 3.6f * multiplier
        val ratio = maxShock / finalSpeedKmh
        val sweetSpot = when {
            ratio < 2.5f -> "Excellent"
            ratio < 3.0f -> "Good"
            else -> "Poor"
        }

        Log.d(TAG, "SHOT: $shotType, Speed: $finalSpeedKmh, Efficiency: $efficiency, SS: $sweetSpot")

        onShotDetected?.invoke(ShotData(
            speedKmh = finalSpeedKmh,
            isHit = maxShock >= 5.0f,
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

    // calculateAngle kept for potential future use with hardware gravity sensor
    @Suppress("unused")
    private fun calculateAngle(idx: Int?): Float {
        if (idx == null) return 0f
        val mag = gravBuffer.magnitudes[idx]
        if (mag == 0f) return 0f
        return acos((gravBuffer.y[idx] / mag).coerceIn(-1f, 1f)) * 57.3f
    }
}
