package com.mrpeel.cricketbattingtracker.ml

import org.junit.Assert.*
import org.junit.Test

class KinematicGuardAdversarialTest {

    @Test
    fun testEmptyOrZeroLengthArrays() {
        val guard = KinematicGuard("BAT_HANDLE")

        val res = guard.evaluateShot(
            tImpactSec = 1.0,
            pTimesSec = DoubleArray(0),
            pAcc = arrayOf(FloatArray(0), FloatArray(0), FloatArray(0)),
            pGyro = arrayOf(FloatArray(0), FloatArray(0), FloatArray(0))
        )

        assertFalse("Empty polar telemetry must be invalid", res.isKinematicallyValid)
        assertFalse("Should not trigger watch-only fallback without swing telemetry", res.isFallbackWatchOnly)
        assertEquals("NO_POLAR_TELEMETRY", res.anomalyReason)
        assertEquals("FAULTED_ANOMALY", res.runtimeMountType)
    }

    @Test
    fun testMismatchedArrayDimensionsDoNotCrash() {
        val guard = KinematicGuard("BAT_HANDLE")
        val numSamples = 50
        val pTimes = DoubleArray(numSamples) { it * 0.00236 }

        // pAcc only has 2 channels instead of 3 (XYZ)
        val res = guard.evaluateShot(
            tImpactSec = 0.05,
            pTimesSec = pTimes,
            pAcc = arrayOf(FloatArray(numSamples), FloatArray(numSamples)), // Missing Z!
            pGyro = arrayOf(FloatArray(numSamples), FloatArray(numSamples), FloatArray(numSamples))
        )

        assertFalse("Mismatched channels must return invalid without crashing", res.isKinematicallyValid)
        assertEquals("NO_POLAR_TELEMETRY", res.anomalyReason)
    }

    @Test
    fun testPacketLossGapsResetTumbleDurationAccumulation() {
        val guard = KinematicGuard("BAT_HANDLE")
        // 100 samples with 25ms gaps between each (> 15ms threshold)
        val numSamples = 100
        val pTimes = DoubleArray(numSamples) { it * 0.025 }
        val pAcc = arrayOf(FloatArray(numSamples) { 0f }, FloatArray(numSamples) { -9.81f }, FloatArray(numSamples) { 0f })
        // Tumble angular velocity (25 rad/s across X and Y)
        val pGyro = arrayOf(FloatArray(numSamples) { 25f }, FloatArray(numSamples) { 25f }, FloatArray(numSamples) { 5f })

        val res = guard.evaluateShot(
            tImpactSec = 0.5,
            pTimesSec = pTimes,
            pAcc = pAcc,
            pGyro = pGyro
        )

        // Because every frame is separated by 25ms (> 15ms packet loss limit), spin duration resets
        // and must NOT falsely accumulate to >= 120ms!
        assertTrue("Packet loss gaps must prevent false tumble trigger", res.isKinematicallyValid)
        assertEquals("CLEAN", res.anomalyReason)
    }

    @Test
    fun testTrueContinuousTumbleTriggersDetachmentAndWatchFallback() {
        val guard = KinematicGuard("BAT_HANDLE")
        // 100 samples with 2.36ms contiguous sampling (423 Hz)
        val numSamples = 100
        val pTimes = DoubleArray(numSamples) { 1.0 + it * 0.00236 }
        val pAcc = arrayOf(FloatArray(numSamples) { 0f }, FloatArray(numSamples) { -9.81f }, FloatArray(numSamples) { 0f })
        // Severe 25 rad/s tumble across 2 axes for 100 * 2.36ms = 236ms (> 120ms threshold)
        val pGyro = arrayOf(FloatArray(numSamples) { 25f }, FloatArray(numSamples) { 25f }, FloatArray(numSamples) { 5f })

        // Watch gyro showing an active swing (w >= 3.5 rad/s)
        val wTimes = DoubleArray(20) { 1.0 + it * 0.02 }
        val wGyroMag = FloatArray(20) { 8.5f }

        val res = guard.evaluateShot(
            tImpactSec = 1.0,
            pTimesSec = pTimes,
            pAcc = pAcc,
            pGyro = pGyro,
            wGyrTimesSec = wTimes,
            wGyroMag = wGyroMag
        )

        assertFalse("Genuine 236ms tumble must be caught as detachment", res.isKinematicallyValid)
        assertTrue("Must trigger fallback to watch-only since watch recorded swing", res.isFallbackWatchOnly)
        assertTrue("Reason must mention tumble", res.anomalyReason.contains("BALLISTIC_FREE_FLIGHT_TUMBLE"))
        assertEquals("FAULTED_ANOMALY", res.runtimeMountType)
    }

    @Test
    fun testImpactTimestampOutsideSampleBoundsEvaluatesSafely() {
        val guard = KinematicGuard("BAT_HANDLE")
        val numSamples = 50
        val pTimes = DoubleArray(numSamples) { 10.0 + it * 0.00236 }
        val pAcc = arrayOf(FloatArray(numSamples) { 0f }, FloatArray(numSamples) { -9.81f }, FloatArray(numSamples) { 0f })
        val pGyro = arrayOf(FloatArray(numSamples) { 0.1f }, FloatArray(numSamples) { 0.1f }, FloatArray(numSamples) { 0.1f })

        // Target impact timestamp is 500 seconds in the future
        val res = guard.evaluateShot(
            tImpactSec = 500.0,
            pTimesSec = pTimes,
            pAcc = pAcc,
            pGyro = pGyro
        )

        // Must finish evaluation cleanly without out-of-bounds errors
        assertTrue("Desynced impact timestamp must evaluate safely", res.isKinematicallyValid)
        assertEquals("CLEAN", res.anomalyReason)
    }

    @Test
    fun testUncoupledShockwaveMismatchedWatchDimensions() {
        val guard = KinematicGuard("BAT_HANDLE")
        val numSamples = 50
        val pTimes = DoubleArray(numSamples) { it * 0.00236 }
        // Polar impact shockwave > 45g (500 m/s2)
        val pAcc = arrayOf(FloatArray(numSamples) { 0f }, FloatArray(numSamples) { 500f }, FloatArray(numSamples) { 0f })
        val pGyro = arrayOf(FloatArray(numSamples) { 1f }, FloatArray(numSamples) { 1f }, FloatArray(numSamples) { 1f })

        // Watch acc array has mismatched length (2 elements when wTimes has 5)
        val wTimes = DoubleArray(5) { it * 0.02 }
        val wAcc = arrayOf(FloatArray(2), FloatArray(2), FloatArray(2))

        val res = guard.evaluateShot(
            tImpactSec = 0.05,
            pTimesSec = pTimes,
            pAcc = pAcc,
            pGyro = pGyro,
            wTimesSec = wTimes,
            wAcc = wAcc
        )

        // Must handle the dimension mismatch defensively without ArrayIndexOutOfBoundsException
        assertNotNull(res)
    }
}
