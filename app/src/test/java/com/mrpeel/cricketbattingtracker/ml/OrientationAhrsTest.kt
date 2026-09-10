package com.mrpeel.cricketbattingtracker.ml

import org.junit.Assert.*
import org.junit.Test
import kotlin.math.*

class OrientationAhrsTest {

    @Test
    fun testQuaternionIdentityAndRotation() {
        val qId = floatArrayOf(0f, 0f, 0f, 1f)
        val v = floatArrayOf(1f, 2f, 3f)
        val vRot = OrientationAhrs.quatRotate(qId, v)
        assertEquals(1f, vRot[0], 1e-4f)
        assertEquals(2f, vRot[1], 1e-4f)
        assertEquals(3f, vRot[2], 1e-4f)
    }

    @Test
    fun testQuaternion90DegZRotation() {
        // 90 deg around z-axis: [0, 0, sin(45 deg), cos(45 deg)]
        val halfAngle = Math.toRadians(45.0).toFloat()
        val q = floatArrayOf(0f, 0f, sin(halfAngle), cos(halfAngle))
        val v = floatArrayOf(1f, 0f, 0f)
        val vRot = OrientationAhrs.quatRotate(q, v)
        assertEquals(0f, vRot[0], 1e-4f)
        assertEquals(1f, vRot[1], 1e-4f)
        assertEquals(0f, vRot[2], 1e-4f)
    }

    @Test
    fun testTwoVectorAlignment() {
        val u = floatArrayOf(0f, 0f, 9.81f)
        val v = floatArrayOf(0f, 0f, 1f)
        val q = OrientationAhrs.quatFromTwoVectors(u, v)
        val uRot = OrientationAhrs.quatRotate(q, floatArrayOf(0f, 0f, 1f))
        assertEquals(0f, uRot[0], 1e-4f)
        assertEquals(0f, uRot[1], 1e-4f)
        assertEquals(1f, uRot[2], 1e-4f)
    }

    @Test
    fun testExpMapSmallAngle() {
        val omega = floatArrayOf(0.1f, 0f, 0f)
        val dt = 0.01f
        val dq = OrientationAhrs.quatExpMap(omega, dt)
        val mag = sqrt(dq[0]*dq[0] + dq[1]*dq[1] + dq[2]*dq[2] + dq[3]*dq[3])
        assertEquals(1.0f, mag, 1e-4f)
    }

    @Test
    fun testEulerZYXConversion() {
        // Identity quaternion -> 0, 0, 0
        val qId = floatArrayOf(0f, 0f, 0f, 1f)
        val euler = OrientationAhrs.quatToEulerZYX(qId)
        assertEquals(0f, euler[0], 1e-3f) // yaw
        assertEquals(0f, euler[1], 1e-3f) // pitch
        assertEquals(0f, euler[2], 1e-3f) // roll
    }

    @Test
    fun testFullEvaluateShotSimulation() {
        val estimator = OrientationAhrs(mountLocation = "BAT_HANDLE")
        val numSamples = 846
        val pTimes = DoubleArray(numSamples) { i -> 9.0 + (i * 0.00236) }
        val pAcc = Array(3) { FloatArray(numSamples) }
        val pGyro = Array(3) { FloatArray(numSamples) }

        // Fill resting 1g gravity in Z (simulating vertical bat resting on pitch: 9.81 m/s2 in Y or Z)
        for (i in 0 until numSamples) {
            pAcc[1][i] = 9.81f // Bat long axis along Y
            pGyro[0][i] = 0.01f
        }

        // Add impact peak at sample 423 (~10.0s)
        pAcc[0][423] = 150f
        pAcc[1][423] = 200f
        pGyro[0][423] = 12.0f

        val wTimes = DoubleArray(100) { j -> 9.0 + j * 0.02 }
        val wGyroMag = FloatArray(100) { 0.02f }
        val wRotTimes = DoubleArray(100) { j -> 9.0 + j * 0.02 }
        val wRot = Array(4) { FloatArray(100) }
        for (j in 0 until 100) {
            wRot[3][j] = 1.0f // Identity
        }

        val result = estimator.evaluateShot(
            tImpactSec = 10.0,
            pTimesSec = pTimes,
            pAcc = pAcc,
            pGyro = pGyro,
            wTimesSec = wTimes,
            wGyroMag = wGyroMag,
            wRotTimesSec = wRotTimes,
            wRot = wRot
        )

        assertNotNull(result)
        result?.let {
            assertTrue(it.isKinematicallyValid)
            assertTrue(it.bladePitchDeg in 0f..90f)
            assertTrue(it.gravityDeviation < 1.0f)
        }
    }
}
