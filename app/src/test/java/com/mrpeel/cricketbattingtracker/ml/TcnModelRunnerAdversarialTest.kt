package com.mrpeel.cricketbattingtracker.ml

import org.junit.Assert.*
import org.junit.Test
import java.io.File
import kotlin.math.*

class TcnModelRunnerAdversarialTest {

    private val assetsDir = File("src/main/assets/models")

    private fun createRunner(): TcnModelRunner {
        val s1Bytes = File(assetsDir, "facing_up_detector.onnx").readBytes()
        val s2Bytes = File(assetsDir, "tcn_ultimate_baseline.onnx").readBytes()
        val statsContent = File(assetsDir, "tcn_norm_stats.json").readText()
        return TcnModelRunner(
            context = null,
            s1ModelBytes = s1Bytes,
            s2ModelBytes = s2Bytes,
            statsJsonContent = statsContent
        )
    }

    @Test
    fun testSubWindowLengthInputsReturnsEmptySafely() {
        val runner = createRunner()
        try {
            val numFrames = 200 // Less than required 423 frames
            val matrix = Array(28) { FloatArray(numFrames) }
            val timestamps = LongArray(numFrames) { it * 10L }

            val results = runner.runInference(matrix, timestamps)
            assertTrue("Sub-window length input must return empty without throwing", results.isEmpty())
        } finally {
            runner.close()
        }
    }

    @Test
    fun testNanAndInfinitySanitizationInSensorMatrix() {
        val runner = createRunner()
        try {
            val numFrames = 600
            val matrix = Array(28) { FloatArray(numFrames) }
            val timestamps = LongArray(numFrames) { 1700000000000L + it * 2L }

            // Fill baseline resting stance
            for (i in 0 until numFrames) {
                matrix[13][i] = -9.81f // Gravity Y
                matrix[18][i] = 1.0f  // Unit quaternion qw
            }

            // Intersperse violent swing motion
            for (i in 250..290) {
                matrix[0][i] = 25.0f // High acc X
                matrix[3][i] = 8.5f  // High gyro X
            }

            // Adversarial injection: Scatter NaNs and Infinities across channels
            matrix[0][100] = Float.NaN
            matrix[1][105] = Float.POSITIVE_INFINITY
            matrix[3][260] = Float.NaN
            matrix[13][270] = Float.NEGATIVE_INFINITY
            matrix[26][280] = Float.NaN // post-impact ratio channel

            val results = runner.runInference(matrix, timestamps)
            assertNotNull(results)

            // Any detected shots must have strictly finite, non-NaN values
            for (shot in results) {
                assertFalse("Confidence must not be NaN", shot.confidence.isNaN())
                assertFalse("Confidence must not be infinite", shot.confidence.isInfinite())
                assertTrue("Confidence must be in [0, 1]", shot.confidence in 0f..1f)
                assertFalse("Peak acc must not be NaN", shot.peakAcc.isNaN())
                assertFalse("Peak gyro must not be NaN", shot.peakGyro.isNaN())
                assertFalse("Post impact ratio must not be NaN", shot.postImpactRatio.isNaN())
                assertNotEquals("no_shot", shot.predictedShotType)
            }
        } finally {
            runner.close()
        }
    }

    @Test
    fun testExtremeKinematicSaturation() {
        val runner = createRunner()
        try {
            val numFrames = 600
            val matrix = Array(28) { FloatArray(numFrames) }
            val timestamps = LongArray(numFrames) { 1700000000000L + it * 2L }

            // Fill baseline resting stance
            for (i in 0 until numFrames) {
                matrix[13][i] = -9.81f
                matrix[18][i] = 1.0f
            }

            // Extreme saturation: 1000g acceleration (~9810 m/s2) and 200 rad/s gyro
            for (i in 250..290) {
                matrix[0][i] = 9810.0f
                matrix[1][i] = 5000.0f
                matrix[3][i] = 200.0f
            }

            val results = runner.runInference(matrix, timestamps)
            assertNotNull(results)
            for (shot in results) {
                assertFalse("Confidence must be finite", shot.confidence.isNaN())
                assertTrue("Confidence must be valid", shot.confidence in 0f..1f)
            }
        } finally {
            runner.close()
        }
    }

    @Test
    fun testGate25DegenerateQuaternionsDoNotCrash() {
        val runner = createRunner()
        try {
            val numFrames = 600
            val matrix = Array(28) { FloatArray(numFrames) }
            val timestamps = LongArray(numFrames) { 1700000000000L + it * 2L }

            // Resting stance
            for (i in 0 until numFrames) {
                matrix[13][i] = -9.81f
            }

            // Swing motion
            for (i in 250..290) {
                matrix[0][i] = 30.0f
                matrix[3][i] = 10.0f
            }

            // Degenerate quaternions: All zeros [0, 0, 0, 0] and NaNs
            for (i in 0 until numFrames) {
                matrix[15][i] = 0f
                matrix[16][i] = 0f
                matrix[17][i] = 0f
                matrix[18][i] = 0f
            }
            matrix[15][270] = Float.NaN
            matrix[16][270] = Float.NaN

            // Run in BAT_HANDLE mode to trigger Gate 2.5
            val results = runner.runInference(matrix, timestamps, polarMountMode = "BAT_HANDLE")
            assertNotNull(results)
            // Must complete without throwing IllegalArgumentException or NaN exceptions
        } finally {
            runner.close()
        }
    }
}
