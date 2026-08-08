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

        // 4. STAGE 1: Peak Motion Candidate Extraction with 300ms Backswing Displacement Check
        val candidateAnchors = mutableListOf<Int>()
        val nFrames = numFrames

        // Sliding scan over 423 Hz frames for motion bursts (gyro >= 1.0 rad/s)
        var tIdx = 127
        while (tIdx < nFrames - 42) {
            val gx = sensorMatrix[3][tIdx]; val gy = sensorMatrix[4][tIdx]; val gz = sensorMatrix[5][tIdx]
            val gyroMag = kotlin.math.sqrt((gx * gx + gy * gy + gz * gz).toDouble()).toFloat()

            if (gyroMag >= 1.0f) {
                // Find local peak within 1.5s window
                val winEnd = kotlin.math.min(nFrames - 1, tIdx + 634)
                var peakFrame = tIdx
                var maxGyr = gyroMag
                for (k in tIdx..winEnd) {
                    val kx = sensorMatrix[3][k]; val ky = sensorMatrix[4][k]; val kz = sensorMatrix[5][k]
                    val kmag = kotlin.math.sqrt((kx * kx + ky * ky + kz * kz).toDouble()).toFloat()
                    if (kmag > maxGyr) {
                        maxGyr = kmag
                        peakFrame = k
                    }
                }

                // 300ms Backswing Displacement Check (127 frames at 423 Hz): delta_theta >= 0.14 rad (~8 deg)
                val preStart = kotlin.math.max(0, peakFrame - 127)
                var sumGyro = 0f
                for (k in preStart..peakFrame) {
                    val kx = sensorMatrix[3][k]; val ky = sensorMatrix[4][k]; val kz = sensorMatrix[5][k]
                    sumGyro += kotlin.math.sqrt((kx * kx + ky * ky + kz * kz).toDouble()).toFloat()
                }
                val deltaThetaBackswing = sumGyro * (1.0f / 423.0f)

                if (deltaThetaBackswing >= 0.14f) {
                    candidateAnchors.add(peakFrame)
                }
                tIdx = peakFrame + 423 // Jump 1.0s ahead
            } else {
                tIdx += 21 // Step 50ms
            }
        }

        if (candidateAnchors.isEmpty()) {
            inputTensor.close()
            results.close()
            return emptyList()
        }

        // 5. STAGE 2: Ultimate TCN Classification & Post-Classification Precision Filters
        val detections = mutableListOf<DetectionResult>()
        var lastAcceptedFrame = -99999
        var lastWasSweep = false

        for (f in candidateAnchors) {
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

            var predShotType = classes[topShotIdx]

            // Filter 1: Class-Specific Softmax Confidence Floor for SWEEP (< 0.45 -> no_shot)
            if (predShotType == "SWEEP" && maxShotProb < 0.45f) {
                predShotType = "no_shot"
            }

            // Filter 2: Torso Pitch / Tilt Verification for SWEEP (>= 15 deg tilt drop or delta_gz >= 2.0 m/s2)
            if (predShotType == "SWEEP") {
                val fStart = kotlin.math.max(0, f - 211) // 500ms at 423 Hz
                var minGz = Float.MAX_VALUE; var maxGz = -Float.MAX_VALUE
                var minPitch = Float.MAX_VALUE; var maxPitch = -Float.MAX_VALUE

                for (k in fStart..f) {
                    val gx = if (numFeatures > 12) sensorMatrix[12][k] else 0f
                    val gy = if (numFeatures > 13) sensorMatrix[13][k] else -9.81f
                    val gz = if (numFeatures > 14) sensorMatrix[14][k] else 0f

                    if (gz < minGz) minGz = gz
                    if (gz > maxGz) maxGz = gz

                    val denom = kotlin.math.sqrt((gx * gx + gy * gy + 1e-6).toDouble()).toFloat()
                    val pitchDeg = Math.toDegrees(kotlin.math.atan2(gz.toDouble(), denom.toDouble())).toFloat()
                    if (pitchDeg < minPitch) minPitch = pitchDeg
                    if (pitchDeg > maxPitch) maxPitch = pitchDeg
                }

                val deltaGz = maxGz - minGz
                val deltaPitch = maxPitch - minPitch

                // Discard standing wrist shift lacking crouching/kneeling posture
                if (deltaPitch < 15.0f && deltaGz < 2.0f) {
                    predShotType = "no_shot"
                }
            }

            // Filter 3: Dynamic Class-Aware NMS (2.4s refractory window for SWEEP, 1.8s for standard classes)
            val isSweep = (predShotType == "SWEEP")
            val reqRefractoryFrames = if (lastWasSweep || isSweep) 1015 else 761 // 2.4s vs 1.8s at 423 Hz

            if (f - lastAcceptedFrame < reqRefractoryFrames) {
                continue
            }

            if (predShotType == "no_shot") {
                continue
            }

            lastAcceptedFrame = f
            lastWasSweep = isSweep

            val tMs = timestampsMs.getOrElse(f) { 0L }
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
