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
        "no_shot", "pre_shot", "PULL/HOOK", "DRIVE/DEFENCE",
        "GLANCE/FLICK", "CUT/PUNCH", "DEFLECTION/GUIDE", "POWER DRIVE", "SLOG", "SWEEP"
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
