package com.mrpeel.cricketbattingtracker.ml

import org.junit.Assert.*
import org.junit.Test
import java.io.File
import kotlin.math.PI
import kotlin.math.exp
import kotlin.math.sin

class ImpactQualityRunnerTest {

    private val assetsDir = File("../app/src/main/assets/models").takeIf { it.exists() }
        ?: File("src/main/assets/models")

    @Test
    fun testImpactOnnxAssetsExistSelfContainedAndRunInference() {
        val multiFile = File(assetsDir, "impact_quality_multimodal.onnx")
        val polarFile = File(assetsDir, "impact_quality_polar.onnx")
        val cfgFile = File(assetsDir, "impact_quality_config.json")

        assertTrue("impact_quality_multimodal.onnx must exist", multiFile.exists())
        assertTrue("impact_quality_polar.onnx must exist", polarFile.exists())
        assertTrue("impact_quality_config.json must exist", cfgFile.exists())

        assertFalse("impact_quality_multimodal.onnx.data must NOT exist", File(assetsDir, "impact_quality_multimodal.onnx.data").exists())
        assertFalse("impact_quality_polar.onnx.data must NOT exist", File(assetsDir, "impact_quality_polar.onnx.data").exists())

        val runner = ImpactQualityRunner(
            context = null,
            multimodalModelBytes = multiFile.readBytes(),
            polarModelBytes = polarFile.readBytes(),
            configJsonContent = cfgFile.readText()
        )

        try {
            val fb = runner.melFilterbank
            assertNotNull("Mel filterbank must parse from config", fb)
            assertEquals(24, fb!!.size)
            assertEquals(129, fb[0].size)

            // Synthetic Polar impact window [-100ms, +140ms] at ~420Hz (101 samples)
            val n = 101
            val pt = DoubleArray(n) { i -> -0.100 + i * 0.0024 }
            val ax = FloatArray(n) { i -> if (kotlin.math.abs(pt[i]) < 0.01) 180f else 5f }
            val ay = FloatArray(n) { 2f }
            val az = FloatArray(n) { -9.8f }
            val gx = FloatArray(n) { i ->
                when {
                    pt[i] < 0.0 -> 18.0f
                    pt[i] < 0.045 -> 13.0f
                    else -> 13.5f
                }
            }
            val gy = FloatArray(n) { i -> if (pt[i] >= 0.0 && i % 2 == 0) 0.3f else -0.2f }
            val gz = FloatArray(n) { 1.0f }

            val extracted = ImpactQualityRunner.extractPolarPatchAndScalars(pt, ax, ay, az, pt, gx, gy, gz)
            assertNotNull(extracted)
            val (polMat, polScalars) = extracted!!
            assertEquals(8, polMat.size)
            assertEquals(ImpactQualityRunner.POLAR_GRID_LEN, polMat[0].size)
            assertEquals(14, polScalars.size)
            assertTrue((polScalars["wide_dip_pct"] ?: 0f) > 0.15f)

            val preds = runner.scoreSessionShots(
                shots = listOf(ImpactQualityRunner.PolarShotInput(0, 5.0, polMat, polScalars)),
                audioFile = null,
                sessionStartWallMs = 1_700_000_000_000L
            )
            assertEquals(1, preds.size)
            val pred = preds[0]!!
            assertEquals("POLAR", pred.source)
            assertTrue(pred.score in 0f..100f)
            assertTrue(pred.edgeRisk in 0f..1f)
            assertTrue(pred.contactDipPct > 15f)
        } finally {
            runner.close()
        }
    }

    @Test
    fun testAudioLogMelAndBlindEnvelopeAlignmentParity() {
        val cfgFile = File(assetsDir, "impact_quality_config.json")
        val fb = AudioImpactDecoder.parseMelFilterbank(cfgFile.readText())

        val segAud = FloatArray(AudioImpactDecoder.PATCH_SAMPLES) { idx ->
            val t = idx / AudioImpactDecoder.SAMPLE_RATE.toDouble()
            // Simulated crisp wooden bat crack around sample 600 (~+2.5ms)
            val rel = idx - 600
            if (rel in 0..800) {
                (0.45 * exp(-rel / 180.0) * sin(2.0 * PI * 1850.0 * t)).toFloat()
            } else {
                0.002f * sin(2.0 * PI * 120.0 * t).toFloat()
            }
        }
        val bgSeg = FloatArray(1600) { i -> 0.002f * sin(2.0 * PI * 120.0 * i / 16000.0).toFloat() }

        val audioRes = AudioImpactDecoder.computeLogMelAndAudioScalars(segAud, bgSeg, 18.5f, fb)
        assertEquals(24, audioRes.spec24x31.size)
        assertEquals(31, audioRes.spec24x31[0].size)
        assertEquals(19, audioRes.scalars.size) // aud_bg_rms + 18 normalized scalars
        assertTrue((audioRes.scalars["aud_snr_db"] ?: 0f) > 20f)

        // Synthetic 200Hz envelope over 60 seconds with 6 sharp bat cracks at tAud = 1.0002 * tc + 3.25
        val env = FloatArray(12_000) { 0.002f }
        val contactTimes = doubleArrayOf(5.0, 12.0, 19.5, 28.0, 36.5, 45.0)
        for (tc in contactTimes) {
            val tAud = 1.0002 * tc + 3.25
            val bin = kotlin.math.round(tAud / 0.005).toInt()
            env[bin] = 0.60f
            env[bin + 1] = 0.30f
        }
        val al = AudioImpactDecoder.blindAlignEnvelopeToPolar(env, contactTimes, initOffsetS = 2.5)
        assertNotNull(al)
        assertEquals(6, al!!.nInliers)
        assertTrue(al.inlierRatio > 0.99f)
        assertTrue(al.medErrS < 0.010f)
    }

    @Test
    fun testMapProbsToQualityTiers() {
        val edge = ImpactQualityRunner.mapProbsToQuality(pClean = 0.30f, pMiddled = 0.15f, pEdge = 0.72f)
        assertEquals("edge", edge.first)
        assertEquals("Edge", edge.second)

        val good = ImpactQualityRunner.mapProbsToQuality(pClean = 0.80f, pMiddled = 0.70f, pEdge = 0.05f)
        assertEquals("good", good.first)
        assertEquals("Excellent", good.second)
        assertTrue(good.third > 65f)

        val poor = ImpactQualityRunner.mapProbsToQuality(pClean = 0.25f, pMiddled = 0.10f, pEdge = 0.20f)
        assertEquals("poor", poor.first)
        assertEquals("Poor", poor.second)
    }
}
