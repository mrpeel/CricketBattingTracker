package com.mrpeel.cricketbattingtracker.ml

import org.junit.Assert.*
import org.junit.Test
import kotlin.math.*

class OrientationAhrsAdversarialTest {

    @Test
    fun testEmptyWatchRotationDoesNotThrowException() {
        val ahrs = OrientationAhrs("BAT_HANDLE")
        val numSamples = 200
        val pTimes = DoubleArray(numSamples) { it * (1.0 / 423.0) }
        val pAcc = arrayOf(
            FloatArray(numSamples) { 0f },
            FloatArray(numSamples) { -9.81f },
            FloatArray(numSamples) { 0f }
        )
        val pGyro = arrayOf(
            FloatArray(numSamples) { 0.1f },
            FloatArray(numSamples) { 0.1f },
            FloatArray(numSamples) { 0.1f }
        )

        // Empty watch rotation arrays
        val res = ahrs.evaluateShot(
            tImpactSec = 0.30,
            pTimesSec = pTimes,
            pAcc = pAcc,
            pGyro = pGyro,
            wTimesSec = DoubleArray(0),
            wGyroMag = FloatArray(0),
            wRotTimesSec = DoubleArray(0),
            wRot = arrayOf(FloatArray(0), FloatArray(0), FloatArray(0), FloatArray(0))
        )

        // Must return null gracefully rather than throwing IndexOutOfBoundsException
        assertNull("Empty watch rotation stream must return null without crashing", res)
    }

    @Test
    fun testMismatchedWatchRotationDimensions() {
        val ahrs = OrientationAhrs("BAT_HANDLE")
        val numSamples = 200
        val pTimes = DoubleArray(numSamples) { it * (1.0 / 423.0) }
        val pAcc = arrayOf(FloatArray(numSamples) { 0f }, FloatArray(numSamples) { -9.81f }, FloatArray(numSamples) { 0f })
        val pGyro = arrayOf(FloatArray(numSamples) { 0.1f }, FloatArray(numSamples) { 0.1f }, FloatArray(numSamples) { 0.1f })

        // wRot only has 3 channels instead of 4 (qx, qy, qz, qw)
        val res = ahrs.evaluateShot(
            tImpactSec = 0.30,
            pTimesSec = pTimes,
            pAcc = pAcc,
            pGyro = pGyro,
            wTimesSec = DoubleArray(10) { it * 0.05 },
            wGyroMag = FloatArray(10) { 0.1f },
            wRotTimesSec = DoubleArray(10) { it * 0.05 },
            wRot = arrayOf(FloatArray(10), FloatArray(10), FloatArray(10)) // Missing qw!
        )

        assertNull("Malformed wRot dimensions must return null without throwing", res)
    }

    @Test
    fun testZeroGravityStillnessDegeneracy() {
        val ahrs = OrientationAhrs("BAT_HANDLE")
        val numSamples = 200
        val pTimes = DoubleArray(numSamples) { it * (1.0 / 423.0) }
        // Complete zero-G during stillness search (accel = 0)
        val pAcc = arrayOf(FloatArray(numSamples) { 0f }, FloatArray(numSamples) { 0f }, FloatArray(numSamples) { 0f })
        val pGyro = arrayOf(FloatArray(numSamples) { 0.05f }, FloatArray(numSamples) { 0.05f }, FloatArray(numSamples) { 0.05f })

        val wTimes = DoubleArray(50) { it * 0.02 }
        val wRot = arrayOf(
            FloatArray(50) { 0f },
            FloatArray(50) { 0f },
            FloatArray(50) { 0f },
            FloatArray(50) { 1f }
        )

        val res = ahrs.evaluateShot(
            tImpactSec = 0.35,
            pTimesSec = pTimes,
            pAcc = pAcc,
            pGyro = pGyro,
            wTimesSec = wTimes,
            wGyroMag = FloatArray(50) { 0.05f },
            wRotTimesSec = wTimes,
            wRot = wRot
        )

        // Must reject zero gravity and return null instead of NaN quaternions
        assertNull("Zero gravity during stillness lock must return null", res)
    }

    @Test
    fun testAntiParallelGravityRodriguesOrthogonalBranch() {
        // u = [0, 0, -1], v = [0, 0, 1] -> dot = -1.0 (exact anti-parallel)
        val u = floatArrayOf(0f, 0f, -1f)
        val v = floatArrayOf(0f, 0f, 1f)
        val q = OrientationAhrs.quatFromTwoVectors(u, v)

        // Result must be non-NaN, non-infinite, and have unit norm
        for (comp in q) {
            assertFalse("Component must not be NaN", comp.isNaN())
            assertFalse("Component must not be Infinite", comp.isInfinite())
        }
        val norm = sqrt(q[0]*q[0] + q[1]*q[1] + q[2]*q[2] + q[3]*q[3])
        assertEquals("Quaternion must be unit length", 1.0f, norm, 1e-4f)

        // Rotating u by q must produce v = [0, 0, 1]
        val rotated = OrientationAhrs.quatRotate(q, u)
        assertEquals(0f, rotated[0], 1e-4f)
        assertEquals(0f, rotated[1], 1e-4f)
        assertEquals(1f, rotated[2], 1e-4f)
    }

    @Test
    fun testAzimuthModuloWrappingBoundary() {
        // Test edge-case angular differences around +/-180 deg seam
        fun wrapAzimuth(rawDiff: Float): Float {
            return ((((rawDiff + 180f) % 360f + 360f) % 360f) - 180f)
        }

        // 1. -350 deg -> should wrap to +10 deg
        assertEquals(10f, wrapAzimuth(-350f), 1e-4f)

        // 2. -190 deg -> should wrap to +170 deg
        assertEquals(170f, wrapAzimuth(-190f), 1e-4f)

        // 3. +190 deg -> should wrap to -170 deg
        assertEquals(-170f, wrapAzimuth(190f), 1e-4f)

        // 4. +350 deg -> should wrap to -10 deg
        assertEquals(-10f, wrapAzimuth(350f), 1e-4f)

        // 5. -180 deg and +180 deg boundaries
        assertEquals(-180f, wrapAzimuth(180f), 1e-4f)
        assertEquals(-180f, wrapAzimuth(-180f), 1e-4f)

        // Assert all test outputs are strictly within [-180, 180]
        for (testAngle in -720..720 step 15) {
            val wrapped = wrapAzimuth(testAngle.toFloat())
            assertTrue("Angle $testAngle wrapped to $wrapped must be >= -180", wrapped >= -180f)
            assertTrue("Angle $testAngle wrapped to $wrapped must be <= 180", wrapped <= 180f)
        }
    }

    @Test
    fun testQuatExpMapWithExtremeZeroAndHighOmega() {
        // 1. Zero angular velocity
        val qZero = OrientationAhrs.quatExpMap(floatArrayOf(0f, 0f, 0f), 0.01f)
        assertEquals(0f, qZero[0], 1e-6f)
        assertEquals(0f, qZero[1], 1e-6f)
        assertEquals(0f, qZero[2], 1e-6f)
        assertEquals(1f, qZero[3], 1e-6f)

        // 2. Extreme angular velocity (100 rad/s)
        val qFast = OrientationAhrs.quatExpMap(floatArrayOf(100f, 0f, 0f), 0.00236f)
        val norm = sqrt(qFast[0]*qFast[0] + qFast[1]*qFast[1] + qFast[2]*qFast[2] + qFast[3]*qFast[3])
        assertEquals(1.0f, norm, 1e-4f)
    }
}
