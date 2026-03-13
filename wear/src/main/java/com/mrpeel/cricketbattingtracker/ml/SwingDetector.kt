package com.mrpeel.cricketbattingtracker.ml

import android.hardware.SensorEvent
import android.util.Log
import kotlin.math.sqrt

// V1 Heuristic Swing and Impact Detection
class SwingDetector {
    private val TAG = "SwingDetector"
    
    // Thresholds (Will need tuning in nets)
    private val SWING_ANGULAR_VELOCITY_THRESHOLD = 5.0f // rad/s
    private val IMPACT_ACCELERATION_THRESHOLD = 30.0f // m/s^2
    
    // State machine
    private var isSwinging = false
    private var swingStartTime = 0L
    
    // Rolling buffers or simple state
    private var currentGyroMag = 0f
    private var currentAccelMag = 0f

    // Called when we detect a completed shot
    var onShotDetected: ((Float, Float) -> Unit)? = null // (maxBatSpeed, impactForce)

    private var maxAngularObserved = 0f
    private var maxImpactObserved = 0f

    fun processGyro(event: SensorEvent) {
        val x = event.values[0]
        val y = event.values[1]
        val z = event.values[2]
        currentGyroMag = sqrt(x * x + y * y + z * z)
        
        if (currentGyroMag > SWING_ANGULAR_VELOCITY_THRESHOLD) {
            if (!isSwinging) {
                isSwinging = true
                swingStartTime = event.timestamp
                maxAngularObserved = currentGyroMag
                maxImpactObserved = currentAccelMag
                Log.d(TAG, "Swing started!")
            } else {
                if (currentGyroMag > maxAngularObserved) maxAngularObserved = currentGyroMag
            }
        } else if (isSwinging && (event.timestamp - swingStartTime) > 1_000_000_000L) {
            // 1 second after swing start, angular velocity drops - swing is over
            Log.d(TAG, "Swing finished. Max angular: $maxAngularObserved, Max Impact: $maxImpactObserved")
            if (maxImpactObserved > 10.0f) { // Arbitrary small threshold to count as a "hit" vs "leave"
                onShotDetected?.invoke(maxAngularObserved, maxImpactObserved)
            }
            isSwinging = false
        }
    }

    fun processAccel(event: SensorEvent) {
        val x = event.values[0]
        val y = event.values[1]
        val z = event.values[2]
        currentAccelMag = sqrt(x * x + y * y + z * z)
        
        if (isSwinging) {
            if (currentAccelMag > maxImpactObserved) {
                maxImpactObserved = currentAccelMag
                Log.d(TAG, "Impact peak tracked: $maxImpactObserved")
            }
        }
    }
}
