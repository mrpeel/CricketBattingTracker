package com.mrpeel.cricketbattingtracker.ml

import android.content.Context
import ai.onnxruntime.OnnxTensor
import ai.onnxruntime.OrtEnvironment
import ai.onnxruntime.OrtSession
import java.nio.FloatBuffer

/**
 * TcnModelRunner — ONNX Runtime Runner for Ultimate Advanced Baseline TCN Engine
 *
 * Runs 423 Hz hardware-accelerated continuous sequence inference over 26-channel sensor inputs
 * and returns frame-level shot detection and class predictions.
 */
class TcnModelRunner(private val context: Context) : AutoCloseable {

    private val ortEnv: OrtEnvironment = OrtEnvironment.getEnvironment()
    private var ortSession: OrtSession? = null

    // 26 Feature Normalisation Stats (Median and MAD)
    private val median = floatArrayOf(
        0.0454f, -0.1205f, 9.8105f,   // w_acc_x, y, z
        0.0012f, -0.0024f, 0.0005f,   // w_gyro_x, y, z
        0.0120f, -0.0540f, 9.8050f,   // w_acc_world_x, y, z
        0.0008f, -0.0015f, 0.0004f,   // w_gyro_world_x, y, z
        0.0000f, -9.8100f, 0.0000f,   // w_grav_x, y, z
        0.0000f,  0.0000f, 0.0000f, 1.0000f, // w_rot_qx, qy, qz, qw
        0.0100f, -0.0200f, 9.8100f,   // p_acc_x, y, z
        0.0000f,  0.0000f, 0.0000f,   // p_gyro_x, y, z
        0.0000f                        // has_polar
    )

    private val mad = floatArrayOf(
        0.5421f, 0.6120f, 0.7415f,
        0.1240f, 0.1510f, 0.1180f,
        0.4850f, 0.5210f, 0.6850f,
        0.1120f, 0.1380f, 0.1050f,
        0.2100f, 0.2500f, 0.2200f,
        0.1000f, 0.1000f, 0.1000f, 0.1000f,
        0.6500f, 0.7200f, 0.8100f,
        0.1500f, 0.1800f, 0.1400f,
        1.0000f
    )

    val classes = arrayOf(
        "no_shot", "pre_shot", "Pull", "Defence",
        "Flick", "Drive", "Glance", "Sweep", "Cut", "Slog"
    )

    init {
        try {
            val modelBytes = context.assets.open("models/tcn_ultimate_baseline.onnx").readBytes()
            ortSession = ortEnv.createSession(modelBytes, OrtSession.SessionOptions())
        } catch (e: Exception) {
            e.printStackTrace()
        }
    }

    data class DetectionResult(
        val frameIndex: Int,
        val timestampMs: Long,
        val predictedShotType: String,
        val confidence: Float
    )

    /**
     * Executes ONNX TCN inference on 26-channel continuous 423 Hz sensor data (26 x T).
     */
    fun runInference(sensorMatrix: Array<FloatArray>, timestampsMs: LongArray): List<DetectionResult> {
        val session = ortSession ?: return emptyList()
        val numFeatures = sensorMatrix.size
        val numFrames = sensorMatrix[0].size

        if (numFeatures != 26 || numFrames == 0) return emptyList()

        // 1. Flatten and Normalize input (1, 26, T)
        val inputBuffer = FloatBuffer.allocate(numFeatures * numFrames)
        for (c in 0 until numFeatures) {
            val medVal = median.getOrElse(c) { 0f }
            val madVal = if (mad.getOrElse(c) { 1f } < 1e-3f) 1f else mad[c]
            val channelData = sensorMatrix[c]
            for (t in 0 until numFrames) {
                val normVal = (channelData[t] - medVal) / madVal
                inputBuffer.put(normVal)
            }
        }
        inputBuffer.rewind()

        val shape = longArrayOf(1, numFeatures.toLong(), numFrames.toLong())
        val inputTensor = OnnxTensor.createTensor(ortEnv, inputBuffer, shape)

        // 2. Run ONNX Session
        val results = try {
            session.run(mapOf("input_imu_stream" to inputTensor))
        } catch (e: Exception) {
            e.printStackTrace()
            return emptyList()
        }

        // 3. Extract Logits (1, 10, T)
        val outputTensor = results[0].value as Array<Array<FloatArray>>
        val logits = outputTensor[0] // 10 x T

        // 4. Find contiguous shot detection regions with physical post-filters
        val rawDetections = mutableListOf<DetectionResult>()
        var inShot = false
        var shotStartFrame = 0
        var maxConfidence = 0f
        var bestShotType = "no_shot"
        var bestFrameIndex = 0
        var maxGyroMag = 0f

        for (t in 0 until numFrames) {
            // Compute Softmax across 10 classes for frame t
            val frameLogits = FloatArray(10) { c -> logits[c][t] }
            val maxLogit = frameLogits.maxOrNull() ?: 0f
            var sumExp = 0f
            val probs = FloatArray(10) { c ->
                val e = kotlin.math.exp((frameLogits[c] - maxLogit).toDouble()).toFloat()
                sumExp += e
                e
            }
            for (c in 0 until 10) probs[c] /= sumExp

            // Sum probabilities for physical shot classes (indices 2..9)
            var isShotProb = 0f
            var topShotIdx = 2
            var topShotProb = 0f
            for (c in 2 until 10) {
                isShotProb += probs[c]
                if (probs[c] > topShotProb) {
                    topShotProb = probs[c]
                    topShotIdx = c
                }
            }

            // Calculate watch gyro magnitude at frame t
            val gx = sensorMatrix[3][t]
            val gy = sensorMatrix[4][t]
            val gz = sensorMatrix[5][t]
            val gyroMag = kotlin.math.sqrt((gx * gx + gy * gy + gz * gz).toDouble()).toFloat()

            if (isShotProb >= 0.70f) {
                if (!inShot) {
                    inShot = true
                    shotStartFrame = t
                    maxConfidence = topShotProb
                    bestShotType = classes[topShotIdx]
                    bestFrameIndex = t
                    maxGyroMag = gyroMag
                } else {
                    if (gyroMag > maxGyroMag) maxGyroMag = gyroMag
                    if (topShotProb > maxConfidence) {
                        maxConfidence = topShotProb
                        bestShotType = classes[topShotIdx]
                        bestFrameIndex = t
                    }
                }
            } else {
                if (inShot) {
                    inShot = false
                    val durationMs = (t - shotStartFrame) * (1000.0f / 423.0f)
                    if (durationMs >= 100f && maxGyroMag >= 4.0f) {
                        val tMs = timestampsMs.getOrElse(bestFrameIndex) { 0L }
                        rawDetections.add(DetectionResult(bestFrameIndex, tMs, bestShotType, maxConfidence))
                    }
                }
            }
        }

        if (inShot) {
            val durationMs = (numFrames - shotStartFrame) * (1000.0f / 423.0f)
            if (durationMs >= 100f && maxGyroMag >= 4.0f) {
                val tMs = timestampsMs.getOrElse(bestFrameIndex) { 0L }
                rawDetections.add(DetectionResult(bestFrameIndex, tMs, bestShotType, maxConfidence))
            }
        }

        // 5. Non-Maximum Suppression (NMS) — min 1.5s gap between physical shots
        val nmsDetections = mutableListOf<DetectionResult>()
        for (det in rawDetections.sortedBy { it.timestampMs }) {
            if (nmsDetections.isEmpty() || (det.timestampMs - nmsDetections.last().timestampMs) >= 1500L) {
                nmsDetections.add(det)
            }
        }

        inputTensor.close()
        results.close()

        return nmsDetections
    }

    override fun close() {
        ortSession?.close()
        ortEnv.close()
    }
}
