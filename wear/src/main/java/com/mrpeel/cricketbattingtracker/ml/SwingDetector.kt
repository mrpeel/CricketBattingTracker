package com.mrpeel.cricketbattingtracker.ml

import android.util.Log
import com.mrpeel.cricketbattingtracker.services.ShotData
import kotlin.math.sqrt

/**
 * Primitive Circular Buffer for maintaining sliding historical windows of sensor data
 * without triggering Garbage Collection pauses.
 */
class RingBuffer(val capacity: Int) {
    val timestamps = LongArray(capacity)
    val magnitudes = FloatArray(capacity)
    var head = 0
    var size = 0

    fun add(timestamp: Long, mag: Float) {
        timestamps[head] = timestamp
        magnitudes[head] = mag
        head = (head + 1) % capacity
        if (size < capacity) size++
    }

    /** Calculates std dev of trailing values over the last [durationNanos] */
    fun getTrailingStdDev(durationNanos: Long, currentTimestamp: Long): Float {
        if (size < 2) return 0f
        val limitTime = currentTimestamp - durationNanos
        var count = 0
        var sum = 0f
        var sumSq = 0f

        var idx = if (head == 0) capacity - 1 else head - 1
        for (i in 0 until size) {
            val t = timestamps[idx]
            if (t < limitTime) break
            val v = magnitudes[idx]
            sum += v
            sumSq += v * v
            count++
            // Move backwards
            idx = if (idx == 0) capacity - 1 else idx - 1
        }

        if (count < 2) return 0f
        val mean = sum / count
        val variance = (sumSq / count) - (mean * mean)
        return if (variance > 0) sqrt(variance) else 0f
    }
}

/**
 * State-Machine physics-heuristic Swing and Contact Detector based directly on the 
 * Python data analysis pipeline constraints.
 */
class SwingDetector {
    private val TAG = "SwingDetector"

    private val QUIET_STD_THRESHOLD = 0.9f
    private val QUIET_MIN_DURATION_NS = (0.15 * 1_000_000_000L).toLong()
    private val MIN_SWING_PEAK = 5.0f
    private val MAX_SWING_LOOKAHEAD_NS = (5.5 * 1_000_000_000L).toLong()
    private val HIT_SHOCK_THRESHOLD = 12.0f
    private val CONTACT_PRE_NS = (0.45 * 1_000_000_000L).toLong()
    private val CONTACT_POST_NS = (0.75 * 1_000_000_000L).toLong()
    private val BAT_RADIUS = 0.8f
    private val RATIO_EXCELLENT = 2.5f
    private val RATIO_GOOD = 3.0f

    // 200 items at 50Hz = ~4 seconds of historical context.
    private val gyroBuffer = RingBuffer(200)
    private val accelBuffer = RingBuffer(200)

    var onShotDetected: ((ShotData) -> Unit)? = null

    private enum class State {
        IDLE_RECOVERY,
        STANCE_LOCKED,
        SWING_SEARCH,
        MEASURING_ARC,
        CONTACT_WAIT
    }

    private var currentState = State.IDLE_RECOVERY
    
    // Core trackers
    private var stanceLockTime = 0L
    private var swingSearchStartTime = 0L
    private var swingStartEventTime = 0L
    private var peakGyroTimestamp = 0L
    private var peakGyroValue = 0f

    fun processGyro(values: FloatArray, timestamp: Long) {
        val mag = sqrt(values[0] * values[0] + values[1] * values[1] + values[2] * values[2])
        gyroBuffer.add(timestamp, mag)

        val trailingStdDev = gyroBuffer.getTrailingStdDev((0.5 * 1_000_000_000L).toLong(), timestamp)

        when (currentState) {
            State.IDLE_RECOVERY -> {
                if (trailingStdDev < QUIET_STD_THRESHOLD) {
                    if (stanceLockTime == 0L) {
                        stanceLockTime = timestamp
                    } else if (timestamp - stanceLockTime >= QUIET_MIN_DURATION_NS) {
                        currentState = State.STANCE_LOCKED
                        Log.d(TAG, "Entered STANCE_LOCKED")
                    }
                } else {
                    stanceLockTime = 0L
                }
            }
            State.STANCE_LOCKED -> {
                if (trailingStdDev >= QUIET_STD_THRESHOLD) {
                    swingSearchStartTime = timestamp
                    currentState = State.SWING_SEARCH
                    Log.d(TAG, "Entered SWING_SEARCH")
                }
            }
            State.SWING_SEARCH -> {
                if (timestamp - swingSearchStartTime > MAX_SWING_LOOKAHEAD_NS) {
                    Log.d(TAG, "Swing search timeout, back to IDLE")
                    resetState()
                } else if (mag >= MIN_SWING_PEAK) {
                    currentState = State.MEASURING_ARC
                    swingStartEventTime = timestamp
                    peakGyroValue = mag
                    peakGyroTimestamp = timestamp
                    Log.d(TAG, "Entered MEASURING_ARC. Peak=$mag")
                }
            }
            State.MEASURING_ARC -> {
                if (mag > peakGyroValue) {
                    peakGyroValue = mag
                    peakGyroTimestamp = timestamp
                }
                if (timestamp - swingStartEventTime >= 1_000_000_000L) {
                    currentState = State.CONTACT_WAIT
                    Log.d(TAG, "Entered CONTACT_WAIT. Final Peak computed.")
                }
            }
            State.CONTACT_WAIT -> {
                if (timestamp >= peakGyroTimestamp + CONTACT_POST_NS) {
                    evaluateShot()
                }
            }
        }
    }

    fun processAccel(values: FloatArray, timestamp: Long) {
        val mag = sqrt(values[0] * values[0] + values[1] * values[1] + values[2] * values[2])
        accelBuffer.add(timestamp, mag)

        // Safety check to execute evaluation if Accel stream triggers timeline
        if (currentState == State.CONTACT_WAIT && timestamp >= peakGyroTimestamp + CONTACT_POST_NS) {
            evaluateShot()
        }
    }

    private fun resetState() {
        currentState = State.IDLE_RECOVERY
        stanceLockTime = 0L
        peakGyroValue = 0f
        peakGyroTimestamp = 0L
    }

    private fun evaluateShot() {
        val startLoc = peakGyroTimestamp - CONTACT_PRE_NS
        val endLoc = peakGyroTimestamp + CONTACT_POST_NS
        
        var maxAcc = 0f
        var count = 0
        
        var idx = if (accelBuffer.head == 0) accelBuffer.capacity - 1 else accelBuffer.head - 1
        for (i in 0 until accelBuffer.size) {
            val t = accelBuffer.timestamps[idx]
            if (t in startLoc..endLoc) {
                val a = accelBuffer.magnitudes[idx]
                if (a > maxAcc) maxAcc = a
                count++
            } else if (t < startLoc) {
                break 
            }
            idx = if (idx == 0) accelBuffer.capacity - 1 else idx - 1
        }
        
        val batSpeedKmh = peakGyroValue * BAT_RADIUS * 3.6f
        val isHit = maxAcc >= HIT_SHOCK_THRESHOLD
        
        var sweetSpot = "N/A"
        if (isHit && batSpeedKmh > 0) {
            val ratio = maxAcc / batSpeedKmh
            sweetSpot = when {
                ratio < RATIO_EXCELLENT -> "Excellent"
                ratio < RATIO_GOOD -> "Good"
                else -> "Poor"
            }
        }
        
        Log.d(TAG, "Evaluated window ($count samples). Acc=$maxAcc, Hit=$isHit, SS=$sweetSpot")
        
        onShotDetected?.invoke(ShotData(
            speedKmh = batSpeedKmh,
            isHit = isHit,
            peakAccel = maxAcc,
            sweetSpot = sweetSpot
        ))
        
        resetState()
    }
}
