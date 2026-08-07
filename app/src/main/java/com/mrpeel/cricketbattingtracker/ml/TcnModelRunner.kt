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

    // 28 Feature Normalisation Stats (Median and MAD)
    private var median = floatArrayOf(
        -3.5674f, -7.4101f, 2.0494f,
        0.0098f, 0.0073f, -0.0073f,
        -0.0014f, 0.0014f, 8.7044f,
        0.0018f, 0.0015f, -0.0070f,
        -3.3984f, -7.4914f, 2.6434f,
        -0.3185f, 0.2123f, 0.0267f, 0.5375f,
        0.0000f, 0.0000f, 0.0000f,
        0.0000f, 0.0000f, 0.0000f,
        0.0000f,
        0.9994f, 0.0011f
    )

    private var mad = floatArrayOf(
        2.7868f, 2.0997f, 1.6783f,
        0.4459f, 0.3238f, 0.4423f,
        0.9576f, 0.9604f, 3.1259f,
        0.3847f, 0.3812f, 0.5516f,
        2.3361f, 1.7059f, 1.5655f,
        0.2251f, 0.3283f, 0.5596f, 0.2013f,
        1.0000f, 1.0000f, 1.0000f,
        1.0000f, 1.0000f, 1.0000f,
        1.0000f,
        0.1034f, 0.0595f
    )

    val classes = arrayOf(
        "no_shot", "pre_shot", "PULL/HOOK", "DRIVE/DEFENCE",
        "GLANCE/FLICK", "CUT/PUNCH", "DEFLECTION/GUIDE", "POWER DRIVE", "SLOG", "SWEEP"
    )

    init {
        try {
            val statsBytes = context.assets.open("models/tcn_norm_stats.json").readBytes()
            val statsJson = org.json.JSONObject(String(statsBytes))
            val medJson = statsJson.getJSONArray("median")
            val madJson = statsJson.getJSONArray("mad")
            if (medJson.length() > 0 && madJson.length() > 0) {
                median = FloatArray(medJson.length()) { i -> medJson.getDouble(i).toFloat() }
                mad = FloatArray(madJson.length()) { i -> madJson.getDouble(i).toFloat() }
            }
        } catch (e: Exception) {
            e.printStackTrace()
        }
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
     * Executes ONNX TCN inference on continuous 423 Hz sensor data (N x T).
     */
    fun runInference(sensorMatrix: Array<FloatArray>, timestampsMs: LongArray): List<DetectionResult> {
        val session = ortSession ?: return emptyList()
        val numFeatures = sensorMatrix.size
        val numFrames = sensorMatrix[0].size

        if ((numFeatures != 28 && numFeatures != 26) || numFrames == 0) return emptyList()

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

        // 4. STAGE 1: Physical Impact Shockwave Peak Detection (Acc >= 30.0 m/s2, Gyro >= 4.0 rad/s for Defence Recall)
        val impactFrames = mutableListOf<Int>()
        for (t in 0 until numFrames) {
            val ax = sensorMatrix[0][t]; val ay = sensorMatrix[1][t]; val az = sensorMatrix[2][t]
            val gx = sensorMatrix[3][t]; val gy = sensorMatrix[4][t]; val gz = sensorMatrix[5][t]
            val accMag = kotlin.math.sqrt((ax * ax + ay * ay + az * az).toDouble()).toFloat()
            val gyroMag = kotlin.math.sqrt((gx * gx + gy * gy + gz * gz).toDouble()).toFloat()

            if (accMag >= 30.0f && gyroMag >= 4.0f) {
                impactFrames.add(t)
            }
        }

        if (impactFrames.isEmpty()) {
            inputTensor.close()
            results.close()
            return emptyList()
        }

        // Cluster impact frames within 1.5s (423 frames at 423 Hz) into single physical shot anchors
        val anchors = mutableListOf<Int>()
        var cluster = mutableListOf(impactFrames[0])
        for (idx in 1 until impactFrames.size) {
            if (impactFrames[idx] - impactFrames[idx - 1] <= 423) {
                cluster.add(impactFrames[idx])
            } else {
                val peakFrame = cluster.maxByOrNull { t ->
                    val ax = sensorMatrix[0][t]; val ay = sensorMatrix[1][t]; val az = sensorMatrix[2][t]
                    ax * ax + ay * ay + az * az
                } ?: cluster[0]
                anchors.add(peakFrame)
                cluster = mutableListOf(impactFrames[idx])
            }
        }
        if (cluster.isNotEmpty()) {
            val peakFrame = cluster.maxByOrNull { t ->
                val ax = sensorMatrix[0][t]; val ay = sensorMatrix[1][t]; val az = sensorMatrix[2][t]
                ax * ax + ay * ay + az * az
            } ?: cluster[0]
            anchors.add(peakFrame)
        }

        // 5. STAGE 2: Ultimate TCN Shot Type Classification over Anchored Windows
        val detections = mutableListOf<DetectionResult>()
        for (f in anchors) {
            val wStart = kotlin.math.max(0, f - 42)
            val wEnd = kotlin.math.min(numFrames - 1, f + 42)

            var maxShotProb = 0f
            var topShotIdx = 2

            for (t in wStart..wEnd) {
                val frameLogits = FloatArray(10) { c -> logits[c][t] }
                val maxLogit = frameLogits.maxOrNull() ?: 0f
                var sumExp = 0f
                val probs = FloatArray(10) { c ->
                    val e = kotlin.math.exp((frameLogits[c] - maxLogit).toDouble()).toFloat()
                    sumExp += e
                    e
                }
                for (c in 0 until 10) probs[c] /= sumExp

                for (c in 2 until 10) {
                    if (probs[c] > maxShotProb) {
                        maxShotProb = probs[c]
                        topShotIdx = c
                    }
                }
            }

            val tMs = timestampsMs.getOrElse(f) { 0L }
            val predShotType = classes[topShotIdx]
            detections.add(DetectionResult(f, tMs, predShotType, maxShotProb))
        }

        inputTensor.close()
        results.close()

        return detections
    }

    override fun close() {
        ortSession?.close()
        ortEnv.close()
    }
}
