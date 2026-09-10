package com.mrpeel.cricketbattingtracker.ml

import org.junit.Assert.*
import org.junit.Test

class KinematicGuardTest {

    private val guard = KinematicGuard("BAT_HANDLE")

    @Test
    fun testCleanDelivery() {
        val numSamples = 846
        val pTimes = DoubleArray(numSamples) { i -> 9.0 + (i * 0.00236) }
        val pAcc = Array(3) { FloatArray(numSamples) }
        val pGyro = Array(3) { FloatArray(numSamples) }

        for (i in 0 until numSamples) {
            pAcc[1][i] = 9.81f
        }
        pAcc[0][423] = 250f // 25g impact

        val wTimes = DoubleArray(100) { j -> 9.0 + j * 0.02 }
        val wAcc = Array(3) { FloatArray(100) { 9.81f } }
        wAcc[0][50] = 35.0f // 3.5g watch shockwave
        val wGyroMag = FloatArray(100) { 0.5f }
        wGyroMag[50] = 8.0f

        val res = guard.evaluateShot(
            tImpactSec = 10.0,
            pTimesSec = pTimes,
            pAcc = pAcc,
            pGyro = pGyro,
            wTimesSec = wTimes,
            wAcc = wAcc,
            wGyrTimesSec = wTimes,
            wGyroMag = wGyroMag
        )

        assertTrue(res.isKinematicallyValid)
        assertFalse(res.isFallbackWatchOnly)
        assertEquals("CLEAN", res.anomalyReason)
        assertEquals("BAT_HANDLE", res.runtimeMountType)
    }

    @Test
    fun testZeroGDetachmentTriggersWatchFallback() {
        val numSamples = 846
        val pTimes = DoubleArray(numSamples) { i -> 9.0 + (i * 0.00236) }
        val pAcc = Array(3) { FloatArray(numSamples) }
        val pGyro = Array(3) { FloatArray(numSamples) }

        for (i in 0 until numSamples) {
            val t = pTimes[i]
            if (t in 10.1..10.25) {
                pAcc[1][i] = 0.5f // Detached sensor falling through air
            } else {
                pAcc[1][i] = 9.81f
            }
        }

        val wTimes = DoubleArray(100) { j -> 9.0 + j * 0.02 }
        val wAcc = Array(3) { FloatArray(100) { 9.81f } }
        val wGyroMag = FloatArray(100) { 0.5f }
        wGyroMag[50] = 7.5f // Genuine top-hand watch stroke

        val res = guard.evaluateShot(
            tImpactSec = 10.0,
            pTimesSec = pTimes,
            pAcc = pAcc,
            pGyro = pGyro,
            wTimesSec = wTimes,
            wAcc = wAcc,
            wGyrTimesSec = wTimes,
            wGyroMag = wGyroMag
        )

        assertFalse(res.isKinematicallyValid)
        assertTrue(res.isFallbackWatchOnly)
        assertEquals("FAULTED_ANOMALY", res.runtimeMountType)
        assertTrue(res.anomalyReason.contains("ZERO_G_FREE_FALL"))
    }

    @Test
    fun testUncoupledShockwaveDetachment() {
        val numSamples = 846
        val pTimes = DoubleArray(numSamples) { i -> 9.0 + (i * 0.00236) }
        val pAcc = Array(3) { FloatArray(numSamples) }
        val pGyro = Array(3) { FloatArray(numSamples) }

        for (i in 0 until numSamples) pAcc[1][i] = 9.81f
        pAcc[0][423] = 500f // > 50g shockwave on Polar

        val wTimes = DoubleArray(100) { j -> 9.0 + j * 0.02 }
        val wAcc = Array(3) { FloatArray(100) { 9.81f } } // Watch only 1g (uncoupled)
        val wGyroMag = FloatArray(100) { 0.1f }

        val res = guard.evaluateShot(
            tImpactSec = 10.0,
            pTimesSec = pTimes,
            pAcc = pAcc,
            pGyro = pGyro,
            wTimesSec = wTimes,
            wAcc = wAcc,
            wGyrTimesSec = wTimes,
            wGyroMag = wGyroMag
        )

        assertFalse(res.isKinematicallyValid)
        assertEquals("FAULTED_ANOMALY", res.runtimeMountType)
        assertTrue(res.anomalyReason.contains("UNCOUPLED_SHOCKWAVE"))
    }
}
