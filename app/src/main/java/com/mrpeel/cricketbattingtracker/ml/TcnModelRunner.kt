package com.mrpeel.cricketbattingtracker.ml

import android.content.Context
import ai.onnxruntime.OnnxTensor
import ai.onnxruntime.OrtEnvironment
import ai.onnxruntime.OrtSession
import java.nio.FloatBuffer
import kotlin.math.*

/**
 * TcnModelRunner — ONNX Runtime Runner for Hierarchical Multi-Tier Telemetry Engine
 *
 * Implements:
 *   1. Stage 1 Stance State Machine (facing_up_detector.onnx):
 *      Sliding 423-frame window inference with 200ms sustain guard (P >= 0.70 entry, P < 0.40 or w >= 1.0 rad/s exit).
 *   2. Deduplication & Peak Anchoring ("1 Stance = Max 1 Shot"):
 *      Scans [T_exit, T_exit + 3.5s] for single highest peak T_peak = argmax(||w_gyro||),
 *      verifying motion floor (w >= 1.0 rad/s or a >= 14.0 m/s2) and 300ms backswing displacement delta_theta >= 0.14 rad.
 *   3. Stage 2 28-Channel TCN Window Classifier (tcn_ultimate_baseline.onnx):
 *      Extracts 2,048-sample window, normalizes with median/MAD, and evaluates 10-class logits.
 *   4. Biomechanical Post-Classification Gates:
 *      - Power Drive Gate: Reclassifies to DRIVE/DEFENCE if post_impact_acc_ratio < 1.35.
 *      - Calibrated Dual-Path Sweep Gate: Evaluates kneeling crouch tilt vs standing paddle roll.
 *      - Dynamic Class-Aware NMS: 2.4s refractory window for SWEEP, 1.8s for other classes.
 */
class TcnModelRunner(private val context: Context) : AutoCloseable {

    private val ortEnv: OrtEnvironment = OrtEnvironment.getEnvironment()
    private var stage1Session: OrtSession? = null
    private var stage2Session: OrtSession? = null

    // 28 Feature Normalisation Stats (Median and MAD)
    var median = floatArrayOf(
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

    var mad = floatArrayOf(
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

    var classes = arrayOf(
        "no_shot", "pre_shot", "PULL/HOOK/SLOG", "DRIVE/DEFENCE",
        "GLANCE/FLICK", "CUT/PUNCH", "DEFLECTION/GUIDE", "POWER DRIVE", "SWEEP"
    )

    // Stage 1 indices within 28-channel matrix:
    // [w_acc_x, w_acc_y, w_acc_z, w_gyro_x, w_gyro_y, w_gyro_z, w_grav_x, w_grav_y, w_grav_z, p_acc_x, p_acc_y, p_acc_z]
    val stage1ChannelIndices = intArrayOf(0, 1, 2, 3, 4, 5, 12, 13, 14, 19, 20, 21)

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
            val clsJson = statsJson.optJSONArray("classes")
            if (clsJson != null && clsJson.length() > 0) {
                classes = Array(clsJson.length()) { i -> clsJson.getString(i) }
            }
        } catch (e: Exception) {
            e.printStackTrace()
        }

        try {
            val s1Bytes = context.assets.open("models/facing_up_detector.onnx").readBytes()
            stage1Session = ortEnv.createSession(s1Bytes, OrtSession.SessionOptions())
        } catch (e: Exception) {
            e.printStackTrace()
        }

        try {
            val s2Bytes = context.assets.open("models/tcn_ultimate_baseline.onnx").readBytes()
            stage2Session = ortEnv.createSession(s2Bytes, OrtSession.SessionOptions())
        } catch (e: Exception) {
            e.printStackTrace()
        }
    }

    data class DetectionResult(
        val frameIndex: Int,
        val timestampMs: Long,
        val predictedShotType: String,
        val confidence: Float,
        val peakAcc: Float = 0f,
        val peakGyro: Float = 0f,
        val postImpactRatio: Float = 0f
    )

    data class CandidateAnchor(
        val tier: String,
        val anchorFrame: Int,
        val anchorTimestampMs: Long,
        val peakAcc: Float,
        val peakGyro: Float,
        val exitFrame: Int,
        val deltaThetaBackswing: Float
    )

    /**
     * Stance State Machine Tracker with configurable sustain guard.
     */
    class StanceTracker(
        val highThresh: Float = 0.70f,
        val lowThresh: Float = 0.40f,
        val motionSurgeW: Float = 1.0f,
        val sustainMs: Int = 200
    ) {
        var state: String = "IDLE"
            private set
        var sustainCount: Int = 0
            private set

        fun processStep(prob: Float, wMag: Float, dtMs: Int = 100): Pair<String, Boolean> {
            return when (state) {
                "IDLE" -> {
                    if (prob >= highThresh) {
                        sustainCount += dtMs
                        if (sustainCount >= sustainMs) {
                            state = "FACING_UP"
                        }
                    } else {
                        sustainCount = 0
                    }
                    Pair(state, false)
                }
                "FACING_UP" -> {
                    if (prob < lowThresh || wMag >= motionSurgeW) {
                        state = "STANCE_EXIT"
                        sustainCount = 0
                        Pair("STANCE_EXIT", true)
                    } else {
                        Pair("FACING_UP", false)
                    }
                }
                "STANCE_EXIT" -> {
                    if (prob < lowThresh || wMag >= motionSurgeW) {
                        state = "IDLE"
                    } else if (prob >= highThresh) {
                        sustainCount += dtMs
                        if (sustainCount >= sustainMs) {
                            state = "FACING_UP"
                        }
                    }
                    Pair(state, false)
                }
                else -> Pair("IDLE", false)
            }
        }
    }

    /**
     * Checks if ONNX model sessions are initialized and ready.
     */
    fun isReady(): Boolean = stage2Session != null

    /**
     * Executes the complete Multi-Tier Telemetry Pipeline on continuous 423 Hz sensor data (28 x N).
     */
    fun runInference(sensorMatrix: Array<FloatArray>, timestampsMs: LongArray): List<DetectionResult> {
        val s2Session = stage2Session ?: return emptyList()
        val numFeatures = sensorMatrix.size
        val numFrames = if (numFeatures > 0) sensorMatrix[0].size else 0

        if (numFeatures < 28 || numFrames < 423) return emptyList()

        val wAccMag = FloatArray(numFrames)
        val wGyroMag = FloatArray(numFrames)
        for (i in 0 until numFrames) {
            val ax = sensorMatrix[0][i]; val ay = sensorMatrix[1][i]; val az = sensorMatrix[2][i]
            wAccMag[i] = sqrt(ax * ax + ay * ay + az * az)

            val gx = sensorMatrix[3][i]; val gy = sensorMatrix[4][i]; val gz = sensorMatrix[5][i]
            wGyroMag[i] = sqrt(gx * gx + gy * gy + gz * gz)
        }

        // =========================================================================
        // 1. Stage 1: Facing Up Stance Tracking (facing_up_detector.onnx)
        // =========================================================================
        val windowLenS1 = 423
        val strideS1 = 42 // ~100ms
        val s1Probs = mutableListOf<Float>()
        val s1MidFrames = mutableListOf<Int>()
        val s1MaxWMags = mutableListOf<Float>()

        val s1Session = stage1Session
        if (s1Session != null) {
            val startIndices = (0 until (numFrames - windowLenS1) step strideS1).toList()
            val totalWindows = startIndices.size
            val batchSize = 256
            val s1InputBuffer = FloatBuffer.allocate(batchSize * 12 * windowLenS1)

            for (bStart in 0 until totalWindows step batchSize) {
                val bEnd = min(totalWindows, bStart + batchSize)
                val currentBatchCount = bEnd - bStart

                s1InputBuffer.clear()
                for (b in bStart until bEnd) {
                    val startIdx = startIndices[b]
                    val endIdx = startIdx + windowLenS1
                    s1MidFrames.add(startIdx + windowLenS1 / 2)

                    var maxW = 0f
                    for (k in startIdx until endIdx) {
                        if (wGyroMag[k] > maxW) maxW = wGyroMag[k]
                    }
                    s1MaxWMags.add(maxW)

                    for (cIdx in stage1ChannelIndices) {
                        val channelData = sensorMatrix[cIdx]
                        for (k in startIdx until endIdx) {
                            s1InputBuffer.put(channelData[k])
                        }
                    }
                }
                s1InputBuffer.rewind()

                val s1Shape = longArrayOf(currentBatchCount.toLong(), 12, windowLenS1.toLong())
                var s1Tensor: OnnxTensor? = null
                var s1Out: OrtSession.Result? = null

                try {
                    s1Tensor = OnnxTensor.createTensor(ortEnv, s1InputBuffer, s1Shape)
                    s1Out = s1Session.run(mapOf("input_imu_12ch" to s1Tensor))
                    val outVal = s1Out[0].value

                    when (outVal) {
                        is FloatArray -> {
                            for (i in 0 until currentBatchCount) {
                                val logitVal = if (i < outVal.size) outVal[i] else 0f
                                val p = (1.0 / (1.0 + exp(-logitVal.toDouble()))).toFloat()
                                s1Probs.add(p)
                            }
                        }
                        is Array<*> -> {
                            for (i in 0 until currentBatchCount) {
                                val row = if (i < outVal.size) outVal[i] else null
                                val logitVal = when (row) {
                                    is FloatArray -> if (row.isNotEmpty()) row[0] else 0f
                                    is Array<*> -> if (row.isNotEmpty()) ((row[0] as? Float) ?: 0f) else 0f
                                    is Float -> row
                                    else -> 0f
                                }
                                val p = (1.0 / (1.0 + exp(-logitVal.toDouble()))).toFloat()
                                s1Probs.add(p)
                            }
                        }
                        is Float -> {
                            val p = (1.0 / (1.0 + exp(-outVal.toDouble()))).toFloat()
                            s1Probs.add(p)
                        }
                        else -> {
                            for (i in 0 until currentBatchCount) s1Probs.add(0.15f)
                        }
                    }
                } catch (e: Exception) {
                    // Fallback heuristic if batch ONNX execution fails
                    for (b in bStart until bEnd) {
                        val startIdx = startIndices[b]
                        val endIdx = startIdx + windowLenS1
                        val maxW = s1MaxWMags.getOrElse(b) { 0f }
                        var gySum = 0f
                        for (k in startIdx until endIdx) gySum += sensorMatrix[13][k]
                        val meanGy = gySum / windowLenS1
                        val p = if (maxW < 1.0f && meanGy <= -3.0f) 0.85f else 0.15f
                        s1Probs.add(p)
                    }
                } finally {
                    try { s1Tensor?.close() } catch (_: Exception) {}
                    try { s1Out?.close() } catch (_: Exception) {}
                }
            }
        } else {
            // Kinematic fallback for Stage 1 if session is unavailable
            for (startIdx in 0 until (numFrames - windowLenS1) step strideS1) {
                val endIdx = startIdx + windowLenS1
                s1MidFrames.add(startIdx + windowLenS1 / 2)
                var maxW = 0f
                var gySum = 0f
                for (k in startIdx until endIdx) {
                    if (wGyroMag[k] > maxW) maxW = wGyroMag[k]
                    gySum += sensorMatrix[13][k]
                }
                s1MaxWMags.add(maxW)
                val meanGy = gySum / windowLenS1
                val prob = if (maxW < 1.0f && meanGy <= -3.0f) 0.85f else 0.15f
                s1Probs.add(prob)
            }
        }

        // =========================================================================
        // 2. Stage 1 Stance State Machine Tracking (200ms sustain guard)
        // =========================================================================
        val sm = StanceTracker(highThresh = 0.70f, lowThresh = 0.40f, motionSurgeW = 1.0f, sustainMs = 200)
        val stanceExitFrames = mutableListOf<Int>()

        for (i in 0 until s1Probs.size) {
            val p = s1Probs[i]
            val w = s1MaxWMags[i]
            val midF = s1MidFrames[i]

            val wasFacingUp = (sm.state == "FACING_UP")
            val (_, exited) = sm.processStep(p, w, dtMs = 100)

            if (exited && wasFacingUp) {
                stanceExitFrames.add(midF)
            }
        }

        // =========================================================================
        // 3. 1-Shot per Stance Deduplication & Peak Anchoring within [T_exit, T_exit + 3.5s]
        // =========================================================================
        val candidateWindows = mutableListOf<CandidateAnchor>()
        val postStanceLookaheadFrames = (3.5 * 423).toInt() // 1480 frames (~3.5s)

        for (fExit in stanceExitFrames) {
            val fScanEnd = min(numFrames, fExit + postStanceLookaheadFrames)
            if (fScanEnd <= fExit + 10) continue

            // Find ONLY the single highest kinetic motion peak (T_peak = argmax ||w_gyro||)
            var maxGyroVal = 0f
            var peakF = fExit
            for (k in fExit until fScanEnd) {
                if (wGyroMag[k] > maxGyroVal) {
                    maxGyroVal = wGyroMag[k]
                    peakF = k
                }
            }

            val peakAcc = wAccMag[peakF]
            val peakGyr = wGyroMag[peakF]

            // Kinematic Backswing Displacement Check over preceding 300ms (127 frames at 423 Hz)
            val fPre300ms = max(0, peakF - 127)
            var sumGyro = 0f
            for (k in fPre300ms..peakF) {
                sumGyro += wGyroMag[k]
            }
            val deltaThetaBackswing = sumGyro * (1.0f / 423.0f)

            // Kinematic Motion Floor: (w >= 1.0 rad/s OR a >= 14.0 m/s2) AND delta_theta >= 0.14 rad (~8 deg)
            val passesMotionFloor = (peakGyr >= 1.0f || peakAcc >= 14.0f) && (deltaThetaBackswing >= 0.14f)
            if (passesMotionFloor) {
                val tier = if (peakAcc >= 30.0f) "TIER_1_HIGH" else "TIER_3_SOFT_TOUCH"
                val tMs = timestampsMs.getOrElse(peakF) { 0L }
                candidateWindows.add(
                    CandidateAnchor(
                        tier = tier,
                        anchorFrame = peakF,
                        anchorTimestampMs = tMs,
                        peakAcc = peakAcc,
                        peakGyro = peakGyr,
                        exitFrame = fExit,
                        deltaThetaBackswing = deltaThetaBackswing
                    )
                )
            }
        }

        if (candidateWindows.isEmpty()) {
            return emptyList()
        }

        // =========================================================================
        // 4. Stage 2: 2,048-Sample 28-Channel Windowed TCN Classification
        // =========================================================================
        val windowLen = 2048
        val inputBuffer = FloatBuffer.allocate(numFeatures * windowLen)
        val candidatePredictions = mutableListOf<Pair<String, Float>>()

        for (cand in candidateWindows) {
            val anchorF = cand.anchorFrame
            var startF = max(0, anchorF - 1024)
            var endF = startF + windowLen
            if (endF > numFrames) {
                endF = numFrames
                startF = max(0, endF - windowLen)
            }
            val cOffset = anchorF - startF

            inputBuffer.clear()
            for (c in 0 until numFeatures) {
                val medVal = median.getOrElse(c) { 0f }
                val madVal = if (mad.getOrElse(c) { 1f } < 1e-3f) 1f else mad[c]
                val channelData = sensorMatrix[c]

                for (k in 0 until windowLen) {
                    val frameIdx = startF + k
                    val rawVal = if (frameIdx < endF) channelData[frameIdx] else 0f
                    val normVal = (rawVal - medVal) / madVal
                    inputBuffer.put(normVal)
                }
            }
            inputBuffer.rewind()

            val shape = longArrayOf(1, numFeatures.toLong(), windowLen.toLong())
            var inputTensor: OnnxTensor? = null
            var results: OrtSession.Result? = null

            try {
                inputTensor = OnnxTensor.createTensor(ortEnv, inputBuffer, shape)
                results = s2Session.run(mapOf("input_imu_stream" to inputTensor))

                @Suppress("UNCHECKED_CAST")
                val outputTensor = results[0].value as Array<Array<FloatArray>>
                val logits = outputTensor[0] // numClasses x windowLen
                val numClasses = logits.size

                val wStart = max(0, cOffset - 42)
                val wEnd = min(windowLen - 1, cOffset + 42)

                var maxShotProb = 0f
                var topShotIdx = 3 // default to DRIVE/DEFENCE

                for (t in wStart..wEnd) {
                    val frameLogits = FloatArray(numClasses) { c -> logits[c][t] }
                    val maxLogit = frameLogits.maxOrNull() ?: 0f
                    var sumExp = 0f
                    val probs = FloatArray(numClasses) { c ->
                        val e = exp((frameLogits[c] - maxLogit).toDouble()).toFloat()
                        sumExp += e
                        e
                    }
                    for (c in 0 until numClasses) probs[c] /= sumExp

                    for (c in 2 until numClasses) {
                        if (probs[c] > maxShotProb) {
                            maxShotProb = probs[c]
                            topShotIdx = c
                        }
                    }
                }
                val predClass = if (topShotIdx < classes.size) classes[topShotIdx] else "DRIVE/DEFENCE"
                candidatePredictions.add(Pair(predClass, maxShotProb))
            } catch (e: Exception) {
                candidatePredictions.add(Pair("DRIVE/DEFENCE", 0.50f))
            } finally {
                try { inputTensor?.close() } catch (_: Exception) {}
                try { results?.close() } catch (_: Exception) {}
            }
        }

        // =========================================================================
        // 5. Post-Classification Biomechanical Rules & Dynamic Class-Aware NMS
        // =========================================================================
        val finalDetections = mutableListOf<DetectionResult>()
        var lastAcceptedFrame = -99999
        var lastWasSweep = false

        for (i in 0 until candidateWindows.size) {
            val cand = candidateWindows[i]
            val anchorF = cand.anchorFrame
            val (rawPredClass, topProb) = candidatePredictions[i]
            var predShotType = rawPredClass

            val postImpactRatio = sensorMatrix[26][anchorF]

            // Gate 1: Power Drive Post-Impact Acceleration Ratio Gate (< 1.35 -> DRIVE/DEFENCE)
            if (predShotType == "POWER DRIVE" && postImpactRatio < 1.35f) {
                predShotType = "DRIVE/DEFENCE"
            }

            // Gate 2: Calibrated Dual-Path Sweep Gate
            if (predShotType == "SWEEP") {
                val fStart = max(0, anchorF - 211) // 500ms at 423 Hz
                var minGz = Float.MAX_VALUE; var maxGz = -Float.MAX_VALUE
                var minPitch = Float.MAX_VALUE; var maxPitch = -Float.MAX_VALUE
                var maxRollVel = 0f

                for (k in fStart..anchorF) {
                    val gx = sensorMatrix[12][k]
                    val gy = sensorMatrix[13][k]
                    val gz = sensorMatrix[14][k]

                    if (gz < minGz) minGz = gz
                    if (gz > maxGz) maxGz = gz

                    val denom = sqrt((gx * gx + gy * gy + 1e-6).toDouble()).toFloat()
                    val pitchDeg = Math.toDegrees(atan2(gz.toDouble(), denom.toDouble())).toFloat()
                    if (pitchDeg < minPitch) minPitch = pitchDeg
                    if (pitchDeg > maxPitch) maxPitch = pitchDeg

                    val roll = abs(sensorMatrix[3][k])
                    if (roll > maxRollVel) maxRollVel = roll
                }

                val deltaGz = maxGz - minGz
                val deltaPitch = maxPitch - minPitch

                // Path 1: Kneeling / Slog Sweep (Crouch Tilt >= 10 deg OR delta_gz >= 1.2 m/s2, Softmax floor >= 0.30)
                val isPath1 = (deltaPitch >= 10.0f || deltaGz >= 1.2f) && (topProb >= 0.30f)

                // Path 2: Standing Paddle / Fine Lap Sweep (Wrist Roll >= 1.6 rad/s and Softmax floor >= 0.35)
                val isPath2 = (maxRollVel >= 1.6f) && (topProb >= 0.35f)

                if (!isPath1 && !isPath2) {
                    predShotType = "no_shot"
                }
            }

            // Gate 3: Dynamic Class-Aware NMS (2.4s for SWEEP, 1.8s for standard classes)
            val isSweep = (predShotType == "SWEEP")
            val reqRefractoryFrames = if (lastWasSweep || isSweep) 1015 else 761 // 2.4s vs 1.8s at 423 Hz

            if (anchorF - lastAcceptedFrame < reqRefractoryFrames) {
                continue
            }

            if (predShotType == "no_shot" || predShotType == "pre_shot") {
                continue
            }

            lastAcceptedFrame = anchorF
            lastWasSweep = isSweep

            finalDetections.add(
                DetectionResult(
                    frameIndex = anchorF,
                    timestampMs = cand.anchorTimestampMs,
                    predictedShotType = predShotType,
                    confidence = topProb,
                    peakAcc = cand.peakAcc,
                    peakGyro = cand.peakGyro,
                    postImpactRatio = postImpactRatio
                )
            )
        }

        return finalDetections
    }

    override fun close() {
        try {
            stage1Session?.close()
        } catch (e: Exception) {
            e.printStackTrace()
        }
        stage1Session = null

        try {
            stage2Session?.close()
        } catch (e: Exception) {
            e.printStackTrace()
        }
        stage2Session = null

        try {
            ortEnv.close()
        } catch (e: Exception) {
            e.printStackTrace()
        }
    }
}
