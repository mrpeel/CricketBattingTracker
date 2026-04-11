package com.mrpeel.cricketbattingtracker.ml

import org.junit.Assert.*
import org.junit.Before
import org.junit.Test

class SwingDetectorTest {

    private lateinit var detector: SwingDetector

    @Before
    fun setUp() {
        detector = SwingDetector()
    }

    @Test
    fun testValidCricketShotDetected() {
        var shotDetected = false
        var maxBatSpeed = 0f
        var impactForce = 0f

        detector.onShotDetected = { speed, force ->
            shotDetected = true
            maxBatSpeed = speed
            impactForce = force
        }

        // 1. Simulate idle state
        var time = 0L
        detector.processGyro(floatArrayOf(0f, 0f, 0f), time)
        detector.processAccel(floatArrayOf(0f, 0f, 9.8f), time)

        // 2. Simulate high rotational velocity (a swing)
        // Magnitude will be sqrt(5*5 + 5*5 + 0) = ~7.07 rad/s (Above 5.0 threshold)
        time += 100_000_000L // 100ms
        detector.processGyro(floatArrayOf(5f, 5f, 0f), time)

        // 3. Simulate high accelerometer spike (impact)
        // Magnitude will be sqrt(25*25 + 25*25 + 0) = ~35 m/s^2 (Above 30 threshold, and above 10 hit threshold)
        time += 100_000_000L // 100ms
        detector.processAccel(floatArrayOf(25f, 25f, 0f), time)

        // 4. Simulate the end of the swing > 1 second later
        time += 1_100_000_000L // 1.1s later
        detector.processGyro(floatArrayOf(0f, 0f, 0f), time)

        // Verify
        assertTrue("A valid cricket shot should have been detected", shotDetected)
        assertTrue("Bat speed should be > 7.0 rad/s", maxBatSpeed > 7.0f)
        assertTrue("Impact force should be > 35.0 m/s^2", impactForce > 35.0f)
    }

    @Test
    fun testFalsePositiveDefensiveBlock() {
        var shotDetected = false

        detector.onShotDetected = { _, _ ->
            shotDetected = true
        }

        var time = 0L
        
        // 1. Simulate very slow rotational velocity (a defensive push/leave)
        // Magnitude = 2.0 rad/s (Below 5.0 threshold)
        detector.processGyro(floatArrayOf(2f, 0f, 0f), time)

        // 2. Simulate impact spike
        time += 100_000_000L
        detector.processAccel(floatArrayOf(20f, 20f, 0f), time)

        // 3. End of the non-swing
        time += 1_100_000_000L
        detector.processGyro(floatArrayOf(0f, 0f, 0f), time)

        assertFalse("A slow block should NOT be detected as a swing", shotDetected)
    }
}
