package com.mrpeel.cricketbattingtracker.ml

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * Verifies 100% Python <-> Kotlin parity for the High-Energy Stage 1 Bypass peak extractor
 * (mirrors pipelines/test_stage1_bypass_parity.py).
 */
class Stage1BypassParityTest {

    @Test
    fun recoversPlateauPeakWithOffsetShockwave() {
        val n = 3000
        val gyr = FloatArray(n) { 0f }
        val acc = FloatArray(n) { 9.8f }
        for (i in 0 until 100) {
            gyr[900 + i] = 0.5f + (13.5f * i / 99f)
        }
        for (i in 1000..1003) gyr[i] = 15.0f
        for (i in 0 until 56) {
            gyr[1004 + i] = 14.0f - (13.0f * i / 55f)
        }
        acc[1040] = 72.5f

        val res = TcnModelRunner.extractHighEnergyBypassPeaks(gyr, acc, emptyList())
        assertEquals(1, res.size)
        assertEquals(1001, res[0].anchorFrame)
        assertEquals(15.0f, res[0].peakGyro, 1e-3f)
        assertEquals(72.5f, res[0].peakAcc150, 1e-3f)
    }

    @Test
    fun rejectsPracticeSwingWithoutShockwave() {
        val n = 3000
        val gyr = FloatArray(n) { 0f }
        val acc = FloatArray(n) { 25.0f } // below 50 m/s^2
        for (i in 0 until 100) {
            gyr[900 + i] = 0.5f + (15.5f * i / 99f)
        }
        for (i in 1000..1003) gyr[i] = 18.0f
        for (i in 0 until 56) {
            gyr[1004 + i] = 16.0f - (15.0f * i / 55f)
        }

        val res = TcnModelRunner.extractHighEnergyBypassPeaks(gyr, acc, emptyList())
        assertTrue(res.isEmpty())
    }

    @Test
    fun respectsStage1ExclusionZone() {
        val n = 3000
        val gyr = FloatArray(n) { 0f }
        val acc = FloatArray(n) { 9.8f }
        for (i in 0 until 100) {
            gyr[900 + i] = 0.5f + (12.5f * i / 99f)
        }
        for (i in 1000..1003) gyr[i] = 14.0f
        for (i in 0 until 56) {
            gyr[1004 + i] = 13.0f - (12.0f * i / 55f)
        }
        acc[1001] = 85.0f

        val suppressed = TcnModelRunner.extractHighEnergyBypassPeaks(gyr, acc, listOf(1300))
        assertTrue(suppressed.isEmpty())

        val kept = TcnModelRunner.extractHighEnergyBypassPeaks(gyr, acc, listOf(1801))
        assertEquals(1, kept.size)
        assertEquals(1001, kept[0].anchorFrame)
    }

    @Test
    fun greedyDescendingHeightSuppressionPicksTallerPeak() {
        val n = 3000
        val gyr = FloatArray(n) { 0f }
        val acc = FloatArray(n) { 9.8f }
        for (i in 0 until 100) gyr[900 + i] = 1.0f + (10.0f * i / 99f)
        gyr[1000] = 12.0f
        for (i in 0 until 49) gyr[1001 + i] = 11.0f - (10.0f * i / 48f)

        for (i in 0 until 100) gyr[1300 + i] = 1.0f + (16.0f * i / 99f)
        gyr[1400] = 19.0f
        for (i in 0 until 49) gyr[1401 + i] = 17.0f - (16.0f * i / 48f)

        acc[1000] = 70.0f
        acc[1400] = 90.0f

        val res = TcnModelRunner.extractHighEnergyBypassPeaks(gyr, acc, emptyList())
        assertEquals(1, res.size)
        assertEquals(1400, res[0].anchorFrame)
        assertEquals(19.0f, res[0].peakGyro, 1e-3f)
    }

    @Test
    fun constantsMatchPythonParity() {
        assertEquals(10.0f, TcnModelRunner.BYPASS_MIN_GYRO_RAD_S, 1e-6f)
        assertEquals(50.0f, TcnModelRunner.BYPASS_MIN_ACC_SHOCKWAVE_MS2, 1e-6f)
        assertEquals(63, TcnModelRunner.BYPASS_SHOCKWAVE_HALF_WINDOW_FRAMES)
        assertEquals(0.14f, TcnModelRunner.BYPASS_MIN_BACKSWING_RAD, 1e-6f)
        assertEquals(635, TcnModelRunner.BYPASS_EXCLUSION_FRAMES)
    }
}
