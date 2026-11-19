package com.mrpeel.cricketbattingtracker.ml

import android.content.Context
import android.util.Log
import ai.onnxruntime.OnnxTensor
import ai.onnxruntime.OrtEnvironment
import ai.onnxruntime.OrtSession
import java.io.File
import java.nio.FloatBuffer
import kotlin.math.*

/**
 * ImpactQualityRunner — Self-contained ONNX Impact Quality & Sweet-Spot Inference Engine
 *
 * Parity partner to `pipelines/impact_quality_model.py` and `pipelines/train_impact_quality_models.py`:
 *   1. `impact_quality_multimodal.onnx` (Audio 2x24x31 + Polar 8x68 + 54 normalized physics scalars)
 *   2. `impact_quality_polar.onnx` (Polar 8x68 + 14 Polar physics scalars fallback when audio is absent/gated)
 */
class ImpactQualityRunner(
    private val context: Context? = null,
    multimodalModelBytes: ByteArray? = null,
    polarModelBytes: ByteArray? = null,
    configJsonContent: String? = null
) : AutoCloseable {

    companion object {
        private const val TAG = "ImpactQualityRunner"
        const val POLAR_GRID_LEN = 68

        val POLAR_TAB_COLS = listOf(
            "g_pre_pk", "g_drop", "wide_dip_pct", "post_gyro_retention", "pre_to_post_drop",
            "axial_y_pk", "axial_y_span", "axial_y_jerk", "axial_y_ratio", "axial_y_post_rattle",
            "plane_wobble_deg", "acc_peak_imp", "acc_vib_std", "acc_vib_norm"
        )

        val AUDIO_NORM_COLS = listOf(
            "spec_e_core", "spec_e_dec1", "spec_e_dec2", "spec_dec_drop", "aud_per_speed",
            "sp_core_lo", "sp_core_mid", "sp_core_up", "sp_core_hi",
            "sp_dec1_up", "sp_dec1_hi", "sp_hi_lo_core", "sp_hi_lo_dec1", "sp_dec_slope",
            "aud_crest", "aud_snr_db", "aud_pk_core", "aud_tail_core_ratio"
        )

        val ALL_SNORM_COLS = AUDIO_NORM_COLS + listOf(
            "g_drop", "wide_dip_pct", "axial_y_ratio", "acc_vib_norm"
        )

        fun mapProbsToQuality(pClean: Float, pMiddled: Float, pEdge: Float): Triple<String, String, Float> {
            val rawScore = 100.0f * (0.55f * pClean + 0.45f * pMiddled) * (1.0f - 0.55f * pEdge)
            val score = rawScore.coerceIn(0.0f, 100.0f)
            val (qual, sweet) = when {
                pEdge >= 0.56f && pClean < 0.52f -> "edge" to "Edge"
                pMiddled >= 0.52f && pClean >= 0.56f -> "good" to "Excellent"
                pClean >= 0.44f -> "okay" to "Good"
                else -> "poor" to "Poor"
            }
            return Triple(qual, sweet, score)
        }

        private fun sigmoid(x: Float): Float = (1.0 / (1.0 + exp(-x.toDouble()))).toFloat()

        private fun linearInterp(gridX: DoubleArray, x: DoubleArray, y: FloatArray): FloatArray {
            val out = FloatArray(gridX.size)
            val n = x.size
            for (i in gridX.indices) {
                val gx = gridX[i]
                if (gx <= x[0]) {
                    out[i] = y[0]
                } else if (gx >= x[n - 1]) {
                    out[i] = y[n - 1]
                } else {
                    var lo = 0
                    var hi = n - 1
                    while (hi - lo > 1) {
                        val mid = (lo + hi) ushr 1
                        if (x[mid] <= gx) lo = mid else hi = mid
                    }
                    val dx = x[hi] - x[lo]
                    val t = if (dx > 1e-12) ((gx - x[lo]) / dx).toFloat() else 0f
                    out[i] = y[lo] + t * (y[hi] - y[lo])
                }
            }
            return out
        }

        private fun sliceMean(arr: FloatArray, start: Int, end: Int): Float {
            var acc = 0.0
            for (i in start until end) acc += arr[i]
            return (acc / (end - start)).toFloat()
        }

        private fun popStd(arr: DoubleArray): Float {
            if (arr.isEmpty()) return 0f
            val mu = arr.average()
            var acc = 0.0
            for (v in arr) {
                val d = v - mu
                acc += d * d
            }
            return sqrt(acc / arr.size).toFloat()
        }

        private fun numpyPercentile(sortedVals: DoubleArray, q: Double): Double {
            if (sortedVals.size == 1) return sortedVals[0]
            val pos = (q / 100.0) * (sortedVals.size - 1)
            val lo = floor(pos).toInt()
            val hi = ceil(pos).toInt()
            val frac = pos - lo
            return sortedVals[lo] + frac * (sortedVals[hi] - sortedVals[lo])
        }

        /**
         * Extract (8, 68) Polar tensor and 14 scalar physics features around impact peak t=0.
         * Input times `ptA`/`ptG` must be in seconds relative to Polar acc shock peak (covering [-0.085, +0.125]).
         * Acc values are m/s^2 and gyro values are rad/s.
         */
        fun extractPolarPatchAndScalars(
            ptA: DoubleArray,
            pAccX: FloatArray,
            pAccY: FloatArray,
            pAccZ: FloatArray,
            ptG: DoubleArray,
            pGyrX: FloatArray,
            pGyrY: FloatArray,
            pGyrZ: FloatArray
        ): Pair<Array<FloatArray>, Map<String, Float>>? {
            val aIdxs = (ptA.indices).filter { ptA[it] >= -0.085 && ptA[it] <= 0.125 }
            val gIdxs = (ptG.indices).filter { ptG[it] >= -0.085 && ptG[it] <= 0.125 }
            if (aIdxs.size < 16 || gIdxs.size < 16) return null

            val subTa = DoubleArray(aIdxs.size) { ptA[aIdxs[it]] }
            val ax = FloatArray(aIdxs.size) { pAccX[aIdxs[it]] }
            val ay = FloatArray(aIdxs.size) { pAccY[aIdxs[it]] }
            val az = FloatArray(aIdxs.size) { pAccZ[aIdxs[it]] }
            val amag = FloatArray(aIdxs.size) { k -> sqrt(ax[k] * ax[k] + ay[k] * ay[k] + az[k] * az[k]) }

            val subTg = DoubleArray(gIdxs.size) { ptG[gIdxs[it]] }
            val gx = FloatArray(gIdxs.size) { pGyrX[gIdxs[it]] }
            val gy = FloatArray(gIdxs.size) { pGyrY[gIdxs[it]] }
            val gz = FloatArray(gIdxs.size) { pGyrZ[gIdxs[it]] }
            val gmag = FloatArray(gIdxs.size) { k -> sqrt(gx[k] * gx[k] + gy[k] * gy[k] + gz[k] * gz[k]) }

            val gridT = DoubleArray(POLAR_GRID_LEN) { i -> -0.060 + i * (0.160 / (POLAR_GRID_LEN - 1)) }
            val polMat = arrayOf(
                linearInterp(gridT, subTa, ax),
                linearInterp(gridT, subTa, ay),
                linearInterp(gridT, subTa, az),
                linearInterp(gridT, subTa, amag),
                linearInterp(gridT, subTg, gx),
                linearInterp(gridT, subTg, gy),
                linearInterp(gridT, subTg, gz),
                linearInterp(gridT, subTg, gmag)
            )
            return polMat to computePolarScalarsFromMatrix(polMat)
        }

        fun computePolarScalarsFromMatrix(polMat: Array<FloatArray>): Map<String, Float> {
            val aMag = polMat[3]
            val gy = polMat[5]
            val gMag = polMat[7]

            val gPreMean = sliceMean(gMag, 0, 21)
            var gPrePk = Float.NEGATIVE_INFINITY
            for (i in 0 until 21) if (gMag[i] > gPrePk) gPrePk = gMag[i]
            var gPre24Max = Float.NEGATIVE_INFINITY
            for (i in 0 until 25) if (gMag[i] > gPre24Max) gPre24Max = gMag[i]
            var gImpMin = Float.POSITIVE_INFINITY
            for (i in 18 until 40) if (gMag[i] < gImpMin) gImpMin = gMag[i]
            val gPostMean = sliceMean(gMag, 34, 68)

            val gDrop = (gPreMean - gPostMean) / (gPreMean + 1e-6f)
            val wideDipPct = (gPre24Max - gImpMin) / (gPre24Max + 1e-6f)
            val postGyroRetention = sliceMean(gMag, 34, 55) / (gPre24Max + 1e-6f)
            val gEarlyMean = sliceMean(gMag, 4, 21)
            val preToPostDrop = (gEarlyMean - sliceMean(gMag, 34, 60)) / (gEarlyMean + 1e-6f)

            var axialYPk = 0f
            var gyImpMax = Float.NEGATIVE_INFINITY
            var gyImpMin = Float.POSITIVE_INFINITY
            var axialYJerk = 0f
            for (i in 20 until 36) {
                val v = gy[i]
                if (abs(v) > axialYPk) axialYPk = abs(v)
                if (v > gyImpMax) gyImpMax = v
                if (v < gyImpMin) gyImpMin = v
                if (i > 20) {
                    val d = abs(gy[i] - gy[i - 1])
                    if (d > axialYJerk) axialYJerk = d
                }
            }
            val axialYSpan = gyImpMax - gyImpMin
            val axialYRatio = axialYSpan / (gPrePk + 1e-6f)

            val gyPostDiffs = DoubleArray(31) { k -> (gy[36 + k + 1] - gy[36 + k]).toDouble() }
            val axialYPostRattle = popStd(gyPostDiffs)

            // 3D Swing plane wobble in [-45ms, -5ms] -> indices 6..23
            val uPre = Array(18) { col ->
                val idx = 6 + col
                val x = polMat[4][idx].toDouble()
                val y = polMat[5][idx].toDouble()
                val z = polMat[6][idx].toDouble()
                val n = sqrt(x * x + y * y + z * z) + 1e-6
                doubleArrayOf(x / n, y / n, z / n)
            }
            var mx = 0.0; var my = 0.0; var mz = 0.0
            for (u in uPre) { mx += u[0]; my += u[1]; mz += u[2] }
            mx /= 18.0; my /= 18.0; mz /= 18.0
            val mNorm = sqrt(mx * mx + my * my + mz * mz) + 1e-6
            mx /= mNorm; my /= mNorm; mz /= mNorm
            var degSum = 0.0
            for (u in uPre) {
                val dot = (u[0] * mx + u[1] * my + u[2] * mz).coerceIn(-1.0, 1.0)
                degSum += Math.toDegrees(acos(dot))
            }
            val planeWobbleDeg = (degSum / 18.0).toFloat()

            var accPeakImp = Float.NEGATIVE_INFINITY
            for (i in 17 until 38) if (aMag[i] > accPeakImp) accPeakImp = aMag[i]
            val aPostSlice = DoubleArray(36) { k -> aMag[32 + k].toDouble() }
            val accVibStd = popStd(aPostSlice)
            val accVibNorm = accVibStd / (gPrePk + 1e-6f)

            return mapOf(
                "g_pre_pk" to gPrePk,
                "g_drop" to gDrop,
                "wide_dip_pct" to wideDipPct,
                "post_gyro_retention" to postGyroRetention,
                "pre_to_post_drop" to preToPostDrop,
                "axial_y_pk" to axialYPk,
                "axial_y_span" to axialYSpan,
                "axial_y_jerk" to axialYJerk,
                "axial_y_ratio" to axialYRatio,
                "axial_y_post_rattle" to axialYPostRattle,
                "plane_wobble_deg" to planeWobbleDeg,
                "acc_peak_imp" to accPeakImp,
                "acc_vib_std" to accVibStd,
                "acc_vib_norm" to accVibNorm
            )
        }
    }

    data class PolarShotInput(
        val shotIndex: Int,
        val contactRelTimeS: Double,
        val polMat: Array<FloatArray>,
        val polarScalars: Map<String, Float>
    )

    data class ImpactQualityPrediction(
        val score: Float,
        val edgeRisk: Float,
        val source: String,
        val contactDipPct: Float,
        val handleRattleRadS: Float,
        val audSnrDb: Float?,
        val predictedQuality: String,
        val sweetSpotLabel: String
    )

    private val ortEnv: OrtEnvironment = OrtEnvironment.getEnvironment()
    private var multimodalSession: OrtSession? = null
    private var polarSession: OrtSession? = null
    var melFilterbank: Array<FloatArray>? = null
        private set

    init {
        try {
            val cfgText = configJsonContent ?: context?.assets?.open("models/impact_quality_config.json")?.bufferedReader()?.use { it.readText() }
            if (cfgText != null) {
                melFilterbank = AudioImpactDecoder.parseMelFilterbank(cfgText)
            }

            val mBytes = multimodalModelBytes ?: context?.assets?.open("models/impact_quality_multimodal.onnx")?.readBytes()
            if (mBytes != null) {
                multimodalSession = ortEnv.createSession(mBytes, OrtSession.SessionOptions())
            }

            val pBytes = polarModelBytes ?: context?.assets?.open("models/impact_quality_polar.onnx")?.readBytes()
            if (pBytes != null) {
                polarSession = ortEnv.createSession(pBytes, OrtSession.SessionOptions())
            }
        } catch (e: Exception) {
            Log.e(TAG, "Error initializing ImpactQualityRunner: ${e.message}")
        }
    }

    fun scoreSessionShots(
        shots: List<PolarShotInput>,
        audioFile: File?,
        sessionStartWallMs: Long
    ): Map<Int, ImpactQualityPrediction> {
        val out = LinkedHashMap<Int, ImpactQualityPrediction>()
        if (shots.isEmpty()) return out

        val mSess = multimodalSession
        val fb = melFilterbank
        var audioResult: AudioImpactDecoder.SessionAudioFeatures? = null
        if (mSess != null && fb != null && audioFile != null && audioFile.exists() && shots.size >= 3) {
            val timesMap = shots.associate { it.shotIndex to it.contactRelTimeS }
            val gPreMap = shots.associate { it.shotIndex to (it.polarScalars["g_pre_pk"] ?: 1f) }
            audioResult = AudioImpactDecoder.extractAlignedSessionAudio(
                audioFile = audioFile,
                polarContactTimesByShotIdx = timesMap,
                gPrePkByShotIdx = gPreMap,
                sessionStartWallMs = sessionStartWallMs,
                melFb = fb
            )
        }

        // 1. Multimodal branch for shots covered by aligned open-mic audio
        if (mSess != null && audioResult != null && audioResult.patchesByShotIdx.size >= 3) {
            val validShots = shots.filter { audioResult.patchesByShotIdx.containsKey(it.shotIndex) }
            val n = validShots.size
            val nMels = AudioImpactDecoder.N_MELS
            val nFrames = 31

            // Session median spectrogram (24 x 31)
            val specMed = Array(nMels) { FloatArray(nFrames) }
            val tmpVals = DoubleArray(n)
            for (m in 0 until nMels) {
                for (t in 0 until nFrames) {
                    for (i in 0 until n) {
                        tmpVals[i] = audioResult.patchesByShotIdx[validShots[i].shotIndex]!!.spec24x31[m][t].toDouble()
                    }
                    tmpVals.sort()
                    specMed[m][t] = numpyPercentile(tmpVals, 50.0).toFloat()
                }
            }

            // Combined scalars & session snorm (median / IQR)
            val combinedScalars = validShots.map { sh ->
                val map = LinkedHashMap<String, Float>(sh.polarScalars)
                map.putAll(audioResult.patchesByShotIdx[sh.shotIndex]!!.scalars)
                map
            }
            val snormMed = HashMap<String, Float>()
            val snormIqr = HashMap<String, Float>()
            for (col in ALL_SNORM_COLS) {
                val vals = DoubleArray(n) { i -> (combinedScalars[i][col] ?: 0f).toDouble() }
                val sorted = vals.sortedArray()
                val med = numpyPercentile(sorted, 50.0)
                var iqr = numpyPercentile(sorted, 75.0) - numpyPercentile(sorted, 25.0)
                if (iqr <= 1e-6) iqr = popStd(vals) + 1e-6
                snormMed[col] = med.toFloat()
                snormIqr[col] = maxOf(iqr, 1e-6).toFloat()
            }

            val specBuf = FloatBuffer.allocate(n * 2 * nMels * nFrames)
            val polBuf = FloatBuffer.allocate(n * 8 * POLAR_GRID_LEN)
            val tabDim = POLAR_TAB_COLS.size + AUDIO_NORM_COLS.size + ALL_SNORM_COLS.size // 54
            val tabBuf = FloatBuffer.allocate(n * tabDim)

            for (i in 0 until n) {
                val sh = validShots[i]
                val sp = audioResult.patchesByShotIdx[sh.shotIndex]!!.spec24x31
                // Ch 0: raw spec; Ch 1: session-median-centered spec
                for (m in 0 until nMels) {
                    for (t in 0 until nFrames) specBuf.put(sp[m][t])
                }
                for (m in 0 until nMels) {
                    for (t in 0 until nFrames) specBuf.put(sp[m][t] - specMed[m][t])
                }
                for (ch in 0 until 8) {
                    for (g in 0 until POLAR_GRID_LEN) polBuf.put(sh.polMat[ch][g])
                }
                val row = combinedScalars[i]
                for (c in POLAR_TAB_COLS) tabBuf.put(row[c] ?: 0f)
                for (c in AUDIO_NORM_COLS) tabBuf.put(row[c] ?: 0f)
                for (c in ALL_SNORM_COLS) {
                    val v = row[c] ?: 0f
                    tabBuf.put((v - (snormMed[c] ?: 0f)) / ((snormIqr[c] ?: 1f) + 1e-6f))
                }
            }
            specBuf.rewind(); polBuf.rewind(); tabBuf.rewind()

            val specTensor = OnnxTensor.createTensor(ortEnv, specBuf, longArrayOf(n.toLong(), 2L, nMels.toLong(), nFrames.toLong()))
            val polTensor = OnnxTensor.createTensor(ortEnv, polBuf, longArrayOf(n.toLong(), 8L, POLAR_GRID_LEN.toLong()))
            val tabTensor = OnnxTensor.createTensor(ortEnv, tabBuf, longArrayOf(n.toLong(), tabDim.toLong()))
            specTensor.use { st ->
                polTensor.use { pt ->
                    tabTensor.use { tt ->
                        mSess.run(mapOf("spec_2ch" to st, "polar_8ch" to pt, "tab_multi" to tt)).use { res ->
                            @Suppress("UNCHECKED_CAST")
                            val logits = res[0].value as Array<FloatArray>
                            for (k in 0 until n) {
                                val sh = validShots[k]
                                val sc = combinedScalars[k]
                                val pClean = sigmoid(logits[k][0])
                                val pMid = sigmoid(logits[k][1])
                                val pEdge = sigmoid(logits[k][2])
                                val (qual, sweet, score) = mapProbsToQuality(pClean, pMid, pEdge)
                                out[sh.shotIndex] = ImpactQualityPrediction(
                                    score = score,
                                    edgeRisk = pEdge,
                                    source = "MULTIMODAL",
                                    contactDipPct = (sc["wide_dip_pct"] ?: 0f) * 100f,
                                    handleRattleRadS = sc["axial_y_post_rattle"] ?: 0f,
                                    audSnrDb = sc["aud_snr_db"],
                                    predictedQuality = qual,
                                    sweetSpotLabel = sweet
                                )
                            }
                        }
                    }
                }
            }
        }

        // 2. Polar-only ONNX fallback for remaining shots (no audio or gated/quiet audio)
        val pSess = polarSession
        val remShots = shots.filter { !out.containsKey(it.shotIndex) }
        if (pSess != null && remShots.isNotEmpty()) {
            val n = remShots.size
            val polBuf = FloatBuffer.allocate(n * 8 * POLAR_GRID_LEN)
            val tabBuf = FloatBuffer.allocate(n * POLAR_TAB_COLS.size)
            for (sh in remShots) {
                for (ch in 0 until 8) {
                    for (g in 0 until POLAR_GRID_LEN) polBuf.put(sh.polMat[ch][g])
                }
                for (c in POLAR_TAB_COLS) tabBuf.put(sh.polarScalars[c] ?: 0f)
            }
            polBuf.rewind(); tabBuf.rewind()

            val polTensor = OnnxTensor.createTensor(ortEnv, polBuf, longArrayOf(n.toLong(), 8L, POLAR_GRID_LEN.toLong()))
            val tabTensor = OnnxTensor.createTensor(ortEnv, tabBuf, longArrayOf(n.toLong(), POLAR_TAB_COLS.size.toLong()))
            polTensor.use { pt ->
                tabTensor.use { tt ->
                    pSess.run(mapOf("polar_8ch" to pt, "tab_polar" to tt)).use { res ->
                        @Suppress("UNCHECKED_CAST")
                        val logits = res[0].value as Array<FloatArray>
                        for (k in 0 until n) {
                            val sh = remShots[k]
                            val sc = sh.polarScalars
                            val pClean = sigmoid(logits[k][0])
                            val pMid = sigmoid(logits[k][1])
                            val pEdge = sigmoid(logits[k][2])
                            val (qual, sweet, score) = mapProbsToQuality(pClean, pMid, pEdge)
                            out[sh.shotIndex] = ImpactQualityPrediction(
                                score = score,
                                edgeRisk = pEdge,
                                source = "POLAR",
                                contactDipPct = (sc["wide_dip_pct"] ?: 0f) * 100f,
                                handleRattleRadS = sc["axial_y_post_rattle"] ?: 0f,
                                audSnrDb = null,
                                predictedQuality = qual,
                                sweetSpotLabel = sweet
                            )
                        }
                    }
                }
            }
        }

        return out
    }

    override fun close() {
        try { multimodalSession?.close() } catch (_: Exception) {}
        try { polarSession?.close() } catch (_: Exception) {}
    }
}
