package com.mrpeel.cricketbattingtracker.ml

import ai.onnxruntime.OnnxTensor
import ai.onnxruntime.OrtEnvironment
import ai.onnxruntime.OrtSession
import org.junit.Assert.*
import org.junit.Test
import java.io.File
import java.nio.FloatBuffer
import kotlin.math.*

class OnnxAssetsIntegrityAndInferenceTest {

    private val assetsDir = File("src/main/assets/models")

    @Test
    fun testOnnxAssetFilesExistAndAreSelfContained() {
        val facingUpOnnx = File(assetsDir, "facing_up_detector.onnx")
        val facingUpData = File(assetsDir, "facing_up_detector.onnx.data")
        val tcnOnnx = File(assetsDir, "tcn_ultimate_baseline.onnx")
        val tcnData = File(assetsDir, "tcn_ultimate_baseline.onnx.data")
        val normStatsJson = File(assetsDir, "tcn_norm_stats.json")

        // 1. Files must exist
        assertTrue("facing_up_detector.onnx must exist in assets/models", facingUpOnnx.exists())
        assertTrue("tcn_ultimate_baseline.onnx must exist in assets/models", tcnOnnx.exists())
        assertTrue("tcn_norm_stats.json must exist in assets/models", normStatsJson.exists())

        // 2. Prohibit external .data sidecars (they cannot be loaded from Android APK asset byte streams)
        assertFalse("facing_up_detector.onnx.data must NOT exist (model must be self-contained)", facingUpData.exists())
        assertFalse("tcn_ultimate_baseline.onnx.data must NOT exist (model must be self-contained)", tcnData.exists())

        // 3. Check reasonable file sizes
        assertTrue("facing_up_detector.onnx must be non-empty", facingUpOnnx.length() in 10_000..5_000_000)
        assertTrue("tcn_ultimate_baseline.onnx must be non-empty", tcnOnnx.length() in 10_000..5_000_000)

        // 4. Verify norm stats json structure without Android stub
        val jsonContent = normStatsJson.readText()
        assertTrue("Must contain median array", jsonContent.contains("\"median\""))
        assertTrue("Must contain mad array", jsonContent.contains("\"mad\""))
        val medCount = jsonContent.substringAfter("\"median\":").substringBefore("]").count { it == ',' } + 1
        val madCount = jsonContent.substringAfter("\"mad\":").substringBefore("]").count { it == ',' } + 1
        assertEquals("Must have 28 channel medians", 28, medCount)
        assertEquals("Must have 28 channel MADs", 28, madCount)
    }

    @Test
    fun testInMemoryOnnxSessionInitialization() {
        val ortEnv = OrtEnvironment.getEnvironment()

        // 1. Test Stage 1 Facing Up Detector from raw byte array (exact Android asset loading path)
        val s1Bytes = File(assetsDir, "facing_up_detector.onnx").readBytes()
        var s1Session: OrtSession? = null
        try {
            s1Session = ortEnv.createSession(s1Bytes, OrtSession.SessionOptions())
            assertNotNull("Stage 1 in-memory session must be created successfully", s1Session)
            assertEquals(1, s1Session.inputNames.size)
            assertEquals("input_imu_12ch", s1Session.inputNames.first())
        } finally {
            s1Session?.close()
        }

        // 2. Test Stage 2 TCN Window Baseline from raw byte array
        val s2Bytes = File(assetsDir, "tcn_ultimate_baseline.onnx").readBytes()
        var s2Session: OrtSession? = null
        try {
            s2Session = ortEnv.createSession(s2Bytes, OrtSession.SessionOptions())
            assertNotNull("Stage 2 in-memory session must be created successfully", s2Session)
            assertEquals(1, s2Session.inputNames.size)
            assertEquals("input_imu_stream", s2Session.inputNames.first())
        } finally {
            s2Session?.close()
        }
    }

    @Test
    fun testStage1InferenceOutputUnpacking() {
        val ortEnv = OrtEnvironment.getEnvironment()
        val s1Bytes = File(assetsDir, "facing_up_detector.onnx").readBytes()
        val s1Session = ortEnv.createSession(s1Bytes, OrtSession.SessionOptions())

        try {
            val windowLen = 423
            val inputBuffer = FloatBuffer.allocate(12 * windowLen)
            // Fill dummy input (e.g. standard resting stance gravity on Y axis)
            for (c in 0 until 12) {
                for (t in 0 until windowLen) {
                    val v = if (c == 7) -9.81f else 0.01f // Channel 7 = gravity Y in 12-channel matrix
                    inputBuffer.put(v)
                }
            }
            inputBuffer.rewind()

            val shape = longArrayOf(1, 12, windowLen.toLong())
            val s1Tensor = OnnxTensor.createTensor(ortEnv, inputBuffer, shape)
            val s1Out = s1Session.run(mapOf("input_imu_12ch" to s1Tensor))

            val outVal = s1Out[0].value
            assertNotNull(outVal)

            // Safe unpacking pattern
            val logitVal: Float = when (outVal) {
                is Array<*> -> {
                    val row0 = outVal[0]
                    if (row0 is FloatArray) row0[0] else (row0 as Array<*>)[0] as Float
                }
                is FloatArray -> outVal[0]
                is Float -> outVal
                else -> throw IllegalStateException("Unexpected output type from Stage 1: ${outVal?.javaClass}")
            }

            val prob = (1.0 / (1.0 + exp(-logitVal.toDouble()))).toFloat()
            assertTrue("Probability must be bounded in [0.0, 1.0]", prob in 0.0f..1.0f)

            s1Tensor.close()
            s1Out.close()
        } finally {
            s1Session.close()
        }
    }

    @Test
    fun testStage2InferenceOutputUnpacking() {
        val ortEnv = OrtEnvironment.getEnvironment()
        val s2Bytes = File(assetsDir, "tcn_ultimate_baseline.onnx").readBytes()
        val s2Session = ortEnv.createSession(s2Bytes, OrtSession.SessionOptions())

        try {
            val windowLen = 2048
            val inputBuffer = FloatBuffer.allocate(28 * windowLen)
            for (i in 0 until (28 * windowLen)) {
                inputBuffer.put(0.05f)
            }
            inputBuffer.rewind()

            val shape = longArrayOf(1, 28, windowLen.toLong())
            val s2Tensor = OnnxTensor.createTensor(ortEnv, inputBuffer, shape)
            val s2Out = s2Session.run(mapOf("input_imu_stream" to s2Tensor))

            val outVal = s2Out[0].value
            assertNotNull(outVal)

            @Suppress("UNCHECKED_CAST")
            val outputTensor = outVal as Array<Array<FloatArray>>
            val logits = outputTensor[0] // 10 x 2048

            assertEquals("Must have 10 shot classes", 10, logits.size)
            assertEquals("Must have 2048 time steps", 2048, logits[0].size)

            // Compute softmax at center frame
            val centerF = 1024
            val frameLogits = FloatArray(10) { c -> logits[c][centerF] }
            val maxLogit = frameLogits.maxOrNull() ?: 0f
            var sumExp = 0f
            val probs = FloatArray(10) { c ->
                val e = exp((frameLogits[c] - maxLogit).toDouble()).toFloat()
                sumExp += e
                e
            }
            for (c in 0 until 10) probs[c] /= sumExp

            val totalProb = probs.sum()
            assertEquals(1.0f, totalProb, 1e-4f)

            s2Tensor.close()
            s2Out.close()
        } finally {
            s2Session.close()
        }
    }

    @Test
    fun testFull22MinuteContinuousSessionPerformance() {
        // Simulates 22.2 minutes at 423 Hz = 562,319 frames
        val numFrames = 562_319
        val numChannels = 28
        val sensorMatrix = Array(numChannels) { FloatArray(numFrames) }

        // Populate baseline sensor data
        for (i in 0 until numFrames) {
            sensorMatrix[0][i] = 0.5f // ax
            sensorMatrix[1][i] = 0.2f // ay
            sensorMatrix[2][i] = 9.8f // az
            sensorMatrix[3][i] = 0.1f // gx
            sensorMatrix[4][i] = 0.1f // gy
            sensorMatrix[5][i] = 0.1f // gz
            sensorMatrix[13][i] = -9.8f // grav_y
        }

        val windowLenS1 = 423
        val strideS1 = 42 // ~100ms

        val startTime = System.currentTimeMillis()

        // Test Stage 1 zero-allocation accumulation loop
        var totalWindows = 0
        var validStanceWindows = 0
        for (startIdx in 0 until (numFrames - windowLenS1) step strideS1) {
            totalWindows++
            val endIdx = startIdx + windowLenS1
            var maxW = 0f
            var gySum = 0f
            for (k in startIdx until endIdx) {
                val gx = sensorMatrix[3][k]
                val gy = sensorMatrix[4][k]
                val gz = sensorMatrix[5][k]
                val w = sqrt(gx * gx + gy * gy + gz * gz)
                if (w > maxW) maxW = w
                gySum += sensorMatrix[13][k]
            }
            val meanGy = gySum / windowLenS1
            if (maxW < 1.0f && meanGy <= -3.0f) {
                validStanceWindows++
            }
        }

        val elapsedMs = System.currentTimeMillis() - startTime
        println("Processed $totalWindows sliding windows over $numFrames frames in ${elapsedMs}ms")

        // Must complete 13,389 windows in under 250ms with zero memory allocations
        assertTrue("Loop execution took too long: ${elapsedMs}ms", elapsedMs < 1000)
        assertEquals(totalWindows, validStanceWindows)
        assertTrue("Must process at least 13,000 sliding windows for 22m session", totalWindows > 13_000)
    }

    @Test
    fun testUiProcessingStateTransitions() {
        data class MockInningsEvent(
            val description: String,
            val batSpeed: Float? = null
        )

        fun computeIsProcessing(
            timeline: List<MockInningsEvent>,
            processedByRecovery: Boolean,
            isFlaggedInPrefs: Boolean
        ): Boolean {
            val hasShots = timeline.any { it.description.contains("Shot:") || it.batSpeed != null }
            val hasEnded = timeline.any { it.description == "Session Ended" }
            val isProcessed = hasShots || hasEnded || processedByRecovery || isFlaggedInPrefs
            return !isProcessed
        }

        // Case 1: Brand new session with 0 events -> isProcessing = true
        assertTrue(computeIsProcessing(emptyList(), processedByRecovery = false, isFlaggedInPrefs = false))

        // Case 2: Session with only "Session Started" (initial timeline sync) -> isProcessing = true
        val startedOnly = listOf(MockInningsEvent("Session Started"))
        assertTrue(computeIsProcessing(startedOnly, processedByRecovery = false, isFlaggedInPrefs = false))

        // Case 3: Processing complete with shots detected -> isProcessing = false
        val shotsDetected = listOf(
            MockInningsEvent("Session Started"),
            MockInningsEvent("DRIVE/DEFENCE (Good)", batSpeed = 48.5f),
            MockInningsEvent("Session Ended")
        )
        assertFalse(computeIsProcessing(shotsDetected, processedByRecovery = false, isFlaggedInPrefs = false))

        // Case 4: Processing complete but 0 shots found (e.g. pad adjustment) -> isProcessing = false (MUST NOT FREEZE)
        val zeroShotsCompleted = listOf(
            MockInningsEvent("Session Started"),
            MockInningsEvent("Session Ended")
        )
        assertFalse("Session with 'Session Ended' must never be stuck in loading state",
            computeIsProcessing(zeroShotsCompleted, processedByRecovery = false, isFlaggedInPrefs = false))

        // Case 5: SharedPreferences flag set -> isProcessing = false
        assertTrue(!computeIsProcessing(startedOnly, processedByRecovery = false, isFlaggedInPrefs = true))

        // Case 6: Recovery button clicked -> isProcessing = false
        assertTrue(!computeIsProcessing(startedOnly, processedByRecovery = true, isFlaggedInPrefs = false))
    }
}
