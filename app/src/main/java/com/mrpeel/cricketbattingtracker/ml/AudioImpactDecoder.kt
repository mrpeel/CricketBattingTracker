package com.mrpeel.cricketbattingtracker.ml

import android.content.Context
import android.media.MediaCodec
import android.media.MediaExtractor
import android.media.MediaFormat
import android.util.Log
import java.io.File
import java.nio.ByteOrder
import java.text.SimpleDateFormat
import java.util.Locale
import kotlin.math.*

/**
 * Decodes session narration `.m4a` audio on-device with low peak RAM (< 5 MB),
 * performs blind Polar-to-audio RANSAC shock alignment, enforces the open-mic
 * confidence gate, and computes exact 24x31 log-mel patches + 18 acoustic scalars
 * matching `pipelines/impact_quality_model.py` 1:1.
 */
object AudioImpactDecoder {
    private const val TAG = "AudioImpactDecoder"

    const val SAMPLE_RATE = 16000
    const val N_FFT = 256
    const val HOP_LEN = 80
    const val PATCH_SAMPLES = 2720 // [-35ms, +135ms] @ 16 kHz -> 31 frames
    const val N_MELS = 24
    const val OPEN_MIC_BG_RMS_MIN = 0.001f

    data class AlignmentResult(
        val slope: Double,
        val intercept: Double,
        val nInliers: Int,
        val inlierRatio: Float,
        val medErrS: Float
    )

    data class AudioPatchAndScalars(
        val spec24x31: Array<FloatArray>,
        val scalars: Map<String, Float>
    )

    data class SessionAudioFeatures(
        val alignment: AlignmentResult,
        val patchesByShotIdx: Map<Int, AudioPatchAndScalars>,
        val medianBgRms: Float
    )

    // Exact match to numpy.hanning(256): denominator N - 1 = 255
    private val HANN_256 = FloatArray(N_FFT) { n ->
        (0.5 * (1.0 - cos(2.0 * PI * n / (N_FFT - 1)))).toFloat()
    }

    // Precomputed bit-reversal and twiddle tables for 256-point Radix-2 FFT
    private val BIT_REV_256 = IntArray(N_FFT).apply {
        for (i in 0 until N_FFT) {
            var x = i
            var r = 0
            for (b in 0 until 8) {
                r = (r shl 1) or (x and 1)
                x = x ushr 1
            }
            this[i] = r
        }
    }

    @Suppress("UNCHECKED_CAST")
    fun parseMelFilterbank(configJson: String): Array<FloatArray> {
        val root = Stage3RuleEngine.parseSimpleJsonMap(configJson)
        val fbArr = root["mel_filterbank_24x129"] as? List<*>
            ?: error("Missing mel_filterbank_24x129 in config JSON")
        return Array(fbArr.size) { m ->
            val row = fbArr[m] as List<*>
            FloatArray(row.size) { k -> (row[k] as Number).toFloat() }
        }
    }

    /**
     * Radix-2 256-point real FFT returning bins 0..128 power spectrum (+ 1e-12f).
     */
    fun rfft256Power(windowed: FloatArray): FloatArray {
        val re = DoubleArray(N_FFT)
        val im = DoubleArray(N_FFT)
        for (i in 0 until N_FFT) {
            re[BIT_REV_256[i]] = windowed[i].toDouble()
        }

        var len = 2
        while (len <= N_FFT) {
            val half = len ushr 1
            val angleStep = -2.0 * PI / len
            var start = 0
            while (start < N_FFT) {
                for (k in 0 until half) {
                    val angle = angleStep * k
                    val wr = cos(angle)
                    val wi = sin(angle)
                    val evenIdx = start + k
                    val oddIdx = evenIdx + half
                    val tr = wr * re[oddIdx] - wi * im[oddIdx]
                    val ti = wr * im[oddIdx] + wi * re[oddIdx]
                    re[oddIdx] = re[evenIdx] - tr
                    im[oddIdx] = im[evenIdx] - ti
                    re[evenIdx] = re[evenIdx] + tr
                    im[evenIdx] = im[evenIdx] + ti
                }
                start += len
            }
            len = len shl 1
        }

        val bins = N_FFT / 2 + 1 // 129
        return FloatArray(bins) { k ->
            (re[k] * re[k] + im[k] * im[k] + 1e-12).toFloat()
        }
    }

    /**
     * Exact Kotlin mirror of `impact_quality_model.compute_log_mel_and_audio_scalars`.
     * `segAud` must have length >= PATCH_SAMPLES (2720), `bgSeg` covers [-250ms, -60ms].
     */
    fun computeLogMelAndAudioScalars(
        segAud: FloatArray,
        bgSeg: FloatArray,
        gPrePk: Float,
        melFb: Array<FloatArray>
    ): AudioPatchAndScalars {
        val numFrames = (PATCH_SAMPLES - N_FFT) / HOP_LEN + 1 // 31
        val spec = Array(N_MELS) { FloatArray(numFrames) }
        val windowed = FloatArray(N_FFT)

        var frameIdx = 0
        var start = 0
        while (start <= PATCH_SAMPLES - N_FFT && frameIdx < numFrames) {
            for (i in 0 until N_FFT) {
                windowed[i] = segAud[start + i] * HANN_256[i]
            }
            val pwr = rfft256Power(windowed)
            for (m in 0 until N_MELS) {
                val weights = melFb[m]
                var sum = 0.0
                for (k in weights.indices) {
                    sum += weights[k] * pwr[k]
                }
                spec[m][frameIdx] = ln((sum + 1e-10).toFloat())
            }
            frameIdx++
            start += HOP_LEN
        }

        var bgSqSum = 0.0
        if (bgSeg.isNotEmpty()) {
            for (v in bgSeg) bgSqSum += v * v
        }
        val bgRms = if (bgSeg.isNotEmpty()) {
            sqrt(bgSqSum / bgSeg.size).toFloat() + 1e-6f
        } else {
            1e-4f
        }

        var audPkCore = 0f
        var coreSqSum = 0.0
        for (i in 480 until 1120) {
            val av = abs(segAud[i])
            if (av > audPkCore) audPkCore = av
            coreSqSum += segAud[i] * segAud[i]
        }
        val audCoreRms = sqrt(coreSqSum / 640.0).toFloat() + 1e-6f

        var tailSqSum = 0.0
        for (i in 1120 until 2080) {
            tailSqSum += segAud[i] * segAud[i]
        }
        val audTailRms = sqrt(tailSqSum / 960.0).toFloat() + 1e-6f

        val audCrest = audPkCore / audCoreRms
        val audSnrDb = 20f * log10((audPkCore + 1e-6f) / bgRms)
        val audTailCoreRatio = audTailRms / audCoreRms

        fun sliceMean(mStart: Int, mEnd: Int, tStart: Int, tEnd: Int): Float {
            var acc = 0.0
            var count = 0
            for (m in mStart until mEnd) {
                for (t in tStart until tEnd) {
                    acc += spec[m][t]
                    count++
                }
            }
            return (acc / count).toFloat()
        }

        val specECore = sliceMean(0, 24, 5, 12)
        val specEDec1 = sliceMean(0, 24, 12, 19)
        val specEDec2 = sliceMean(0, 24, 19, 31)
        val specDecDrop = specECore - specEDec2
        val audPerSpeed = (specECore + specEDec1) - 2f * ln(gPrePk + 1f)

        val spCoreLo = sliceMean(0, 6, 5, 12)
        val spCoreMid = sliceMean(6, 12, 5, 12)
        val spCoreUp = sliceMean(12, 18, 5, 12)
        val spCoreHi = sliceMean(18, 24, 5, 12)
        val spDec1Up = sliceMean(12, 18, 12, 19)
        val spDec1Hi = sliceMean(18, 24, 12, 19)
        val spDec1Lo = sliceMean(0, 6, 12, 19)
        val spDec2Up = sliceMean(12, 18, 19, 31)

        val scalars = mapOf(
            "aud_bg_rms" to bgRms,
            "spec_e_core" to specECore,
            "spec_e_dec1" to specEDec1,
            "spec_e_dec2" to specEDec2,
            "spec_dec_drop" to specDecDrop,
            "aud_per_speed" to audPerSpeed,
            "sp_core_lo" to spCoreLo,
            "sp_core_mid" to spCoreMid,
            "sp_core_up" to spCoreUp,
            "sp_core_hi" to spCoreHi,
            "sp_dec1_up" to spDec1Up,
            "sp_dec1_hi" to spDec1Hi,
            "sp_hi_lo_core" to (spCoreHi - spCoreLo),
            "sp_hi_lo_dec1" to (spDec1Hi - spDec1Lo),
            "sp_dec_slope" to (spCoreUp - spDec2Up),
            "aud_crest" to audCrest,
            "aud_snr_db" to audSnrDb,
            "aud_pk_core" to audPkCore,
            "aud_tail_core_ratio" to audTailCoreRatio
        )
        return AudioPatchAndScalars(spec, scalars)
    }

    /**
     * Exact Kotlin mirror of `impact_quality_model.blind_align_audio_to_polar`.
     * `env` holds 200 Hz peak-abs values (1 bin per 5 ms).
     */
    fun blindAlignEnvelopeToPolar(
        env: FloatArray,
        polarContactTimes: DoubleArray,
        initOffsetS: Double,
        searchRadiusS: Double = 25.0
    ): AlignmentResult? {
        val nB = env.size
        if (nB < 20 || polarContactTimes.size < 3) return null

        val sortedEnv = env.clone().also { it.sort() }
        val medEnv = sortedEnv[nB / 2] + 1e-6f
        val heightThresh = maxOf(0.03f, 3.5f * medEnv)
        val promThresh = maxOf(0.02f, 2.5f * medEnv)
        val minDist = 40

        // Local maxima passing height + prominence (bounded window for speed & parity)
        val rawPeaks = mutableListOf<Pair<Int, Float>>()
        for (i in 1 until nB - 1) {
            val v = env[i]
            if (v >= heightThresh && v >= env[i - 1] && v > env[i + 1]) {
                var leftMin = v
                var k = i - 1
                while (k >= 0 && env[k] <= v) {
                    if (env[k] < leftMin) leftMin = env[k]
                    k--
                }
                var rightMin = v
                k = i + 1
                while (k < nB && env[k] <= v) {
                    if (env[k] < rightMin) rightMin = env[k]
                    k++
                }
                val prom = v - maxOf(leftMin, rightMin)
                if (prom >= promThresh) {
                    rawPeaks.add(i to v)
                }
            }
        }
        if (rawPeaks.size < 3) return null

        // Enforce min distance=40 keeping highest peaks first (matching scipy.signal.find_peaks)
        val occupied = BooleanArray(nB)
        val selectedIndices = mutableListOf<Int>()
        for ((idx, _) in rawPeaks.sortedByDescending { it.second }) {
            if (!occupied[idx]) {
                selectedIndices.add(idx)
                val lo = maxOf(0, idx - minDist + 1)
                val hi = minOf(nB - 1, idx + minDist - 1)
                for (j in lo..hi) occupied[j] = true
            }
        }
        selectedIndices.sort()
        val audPksT = DoubleArray(selectedIndices.size) { k -> (selectedIndices[k] + 0.5) * 0.005 }
        if (audPksT.size < 3) return null

        val shifts = mutableListOf<Double>()
        for (tc in polarContactTimes) {
            val pred = tc + initOffsetS
            for (pt in audPksT) {
                if (pt >= pred - searchRadiusS && pt <= pred + searchRadiusS) {
                    shifts.add(pt - tc)
                }
            }
        }
        if (shifts.isEmpty()) return null

        val minShift = shifts.min() - 0.05
        val maxShift = shifts.max() + 0.06
        val binWidth = 0.025
        val numBins = floor((maxShift - minShift) / binWidth).toInt()
        if (numBins < 2) return null

        val hist = IntArray(numBins)
        for (s in shifts) {
            val b = ((s - minShift) / binWidth).toInt()
            if (b in 0 until numBins) hist[b]++
        }
        val topBins = (0 until numBins).sortedByDescending { hist[it] }.take(6)

        var bestResult: AlignmentResult? = null
        var bestInl = -1
        var bestErr = Double.MAX_VALUE

        for (tb in topBins) {
            var a = 1.0
            var b = minShift + (tb + 0.5) * binWidth
            for (iter in 0 until 5) {
                val xs = mutableListOf<Double>()
                val ys = mutableListOf<Double>()
                for (tc in polarContactTimes) {
                    val p = a * tc + b
                    var minD = Double.MAX_VALUE
                    var bestY = 0.0
                    for (pt in audPksT) {
                        val d = abs(pt - p)
                        if (d < minD) {
                            minD = d
                            bestY = pt
                        }
                    }
                    if (minD < 0.050) {
                        xs.add(tc)
                        ys.add(bestY)
                    }
                }
                if (xs.size >= 4) {
                    val mx = xs.average()
                    val my = ys.average()
                    var num = 0.0
                    var den = 0.0
                    for (i in xs.indices) {
                        val dx = xs[i] - mx
                        num += dx * (ys[i] - my)
                        den += dx * dx
                    }
                    if (den > 1e-12) {
                        val aNew = num / den
                        val bNew = my - aNew * mx
                        if (abs(aNew - 1.0) < 0.02) {
                            a = aNew
                            b = bNew
                        }
                    }
                }
            }

            val dists = DoubleArray(polarContactTimes.size) { i ->
                val p = a * polarContactTimes[i] + b
                var minD = Double.MAX_VALUE
                for (pt in audPksT) {
                    val d = abs(pt - p)
                    if (d < minD) minD = d
                }
                minD
            }
            val inl = dists.count { it <= 0.025 }
            val sortedDists = dists.sortedArray()
            val medE = sortedDists[sortedDists.size / 2]
            if (inl > bestInl || (inl == bestInl && medE < bestErr)) {
                bestInl = inl
                bestErr = medE
                bestResult = AlignmentResult(
                    slope = a,
                    intercept = b,
                    nInliers = inl,
                    inlierRatio = inl.toFloat() / polarContactTimes.size.toFloat(),
                    medErrS = medE.toFloat()
                )
            }
        }
        return bestResult
    }

    fun parseAudioStartWallMs(audioFile: File): Long? {
        val baseName = audioFile.nameWithoutExtension
        val metaFile = File(audioFile.parentFile, "$baseName.meta.json")
        if (metaFile.exists()) {
            try {
                val obj = Stage3RuleEngine.parseSimpleJsonMap(metaFile.readText())
                val v = (obj["start_wall_ms"] as? Number)?.toLong() ?: -1L
                if (v > 0L) return v
            } catch (_: Exception) { }
        }
        val m = Regex("""narration_(\d{8})_(\d{6})\.m4a$""").find(audioFile.name)
        if (m != null) {
            return try {
                val sdf = SimpleDateFormat("yyyyMMddHHmmss", Locale.US)
                sdf.parse(m.groupValues[1] + m.groupValues[2])?.time
            } catch (_: Exception) {
                null
            }
        }
        return null
    }

    fun findMatchingNarrationAudio(
        context: Context,
        sessionStartWallMs: Long,
        sessionEndWallMs: Long
    ): File? {
        val rootDir = context.getExternalFilesDir(null) ?: return null
        val files = rootDir.listFiles()?.filter {
            it.isFile && it.name.startsWith("narration_") && it.name.endsWith(".m4a") && it.length() > 4096L
        } ?: return null
        if (files.isEmpty()) return null

        var bestFile: File? = null
        var bestScore = Long.MAX_VALUE
        for (f in files) {
            val startMs = parseAudioStartWallMs(f) ?: continue
            // Exact overlap check: audio start should be within [-10 min, sessionEnd + 60s]
            // Prefer files whose start_wall_ms is closest to sessionStartWallMs and before sessionEndWallMs
            if (startMs <= sessionEndWallMs + 60_000L && startMs >= sessionStartWallMs - 600_000L) {
                val diff = abs(startMs - sessionStartWallMs)
                if (diff < bestScore) {
                    bestScore = diff
                    bestFile = f
                }
            }
        }
        return bestFile
    }

    private class ResampledStreamSink(
        private val srcRate: Int,
        private val targetRate: Int,
        private val channels: Int,
        private val onSample: (idx: Long, value: Float) -> Unit
    ) {
        private var hasPrev = false
        private var prevVal = 0f
        private var srcPos = 0L
        private var targetIdx = 0L
        private val ratio = srcRate.toDouble() / targetRate.toDouble()

        fun pushPcm16(samples: ShortArray, count: Int) {
            val frameCount = count / channels
            for (f in 0 until frameCount) {
                var sum = 0f
                val base = f * channels
                for (c in 0 until channels) {
                    sum += samples[base + c] / 32768f
                }
                val curr = sum / channels
                if (!hasPrev) {
                    prevVal = curr
                    hasPrev = true
                    while (targetIdx * ratio <= 0.0) {
                        onSample(targetIdx, curr)
                        targetIdx++
                    }
                    srcPos = 0L
                    continue
                }
                val nextPos = srcPos + 1L
                while (true) {
                    val exactSrc = targetIdx * ratio
                    if (exactSrc > nextPos.toDouble()) break
                    val alpha = (exactSrc - srcPos.toDouble()).toFloat().coerceIn(0f, 1f)
                    val interp = prevVal + alpha * (curr - prevVal)
                    onSample(targetIdx, interp)
                    targetIdx++
                }
                prevVal = curr
                srcPos = nextPos
            }
        }
    }

    private fun streamDecodeAudio(audioFile: File, onMono16kSample: (idx: Long, value: Float) -> Unit): Boolean {
        val extractor = MediaExtractor()
        var codec: MediaCodec? = null
        try {
            extractor.setDataSource(audioFile.absolutePath)
            var trackIndex = -1
            var format: MediaFormat? = null
            for (i in 0 until extractor.trackCount) {
                val f = extractor.getTrackFormat(i)
                val mime = f.getString(MediaFormat.KEY_MIME) ?: continue
                if (mime.startsWith("audio/")) {
                    trackIndex = i
                    format = f
                    break
                }
            }
            if (trackIndex < 0 || format == null) return false
            extractor.selectTrack(trackIndex)

            val mime = format.getString(MediaFormat.KEY_MIME) ?: return false
            var sampleRate = format.getInteger(MediaFormat.KEY_SAMPLE_RATE)
            var channels = format.getInteger(MediaFormat.KEY_CHANNEL_COUNT)

            codec = MediaCodec.createDecoderByType(mime)
            codec.configure(format, null, null, 0)
            codec.start()

            var sink = ResampledStreamSink(sampleRate, SAMPLE_RATE, channels, onMono16kSample)
            val info = MediaCodec.BufferInfo()
            var inputDone = false
            var outputDone = false

            while (!outputDone) {
                if (!inputDone) {
                    val inIdx = codec.dequeueInputBuffer(10_000L)
                    if (inIdx >= 0) {
                        val buf = codec.getInputBuffer(inIdx)
                        val sampleSize = if (buf != null) extractor.readSampleData(buf, 0) else -1
                        if (sampleSize < 0) {
                            codec.queueInputBuffer(inIdx, 0, 0, 0L, MediaCodec.BUFFER_FLAG_END_OF_STREAM)
                            inputDone = true
                        } else {
                            codec.queueInputBuffer(inIdx, 0, sampleSize, extractor.sampleTime, 0)
                            extractor.advance()
                        }
                    }
                }

                val outIdx = codec.dequeueOutputBuffer(info, 10_000L)
                if (outIdx == MediaCodec.INFO_OUTPUT_FORMAT_CHANGED) {
                    val outFmt = codec.outputFormat
                    val newRate = if (outFmt.containsKey(MediaFormat.KEY_SAMPLE_RATE)) outFmt.getInteger(MediaFormat.KEY_SAMPLE_RATE) else sampleRate
                    val newCh = if (outFmt.containsKey(MediaFormat.KEY_CHANNEL_COUNT)) outFmt.getInteger(MediaFormat.KEY_CHANNEL_COUNT) else channels
                    if (newRate != sampleRate || newCh != channels) {
                        sampleRate = newRate
                        channels = newCh
                        sink = ResampledStreamSink(sampleRate, SAMPLE_RATE, channels, onMono16kSample)
                    }
                } else if (outIdx >= 0) {
                    val outBuf = codec.getOutputBuffer(outIdx)
                    if (outBuf != null && info.size > 0) {
                        outBuf.position(info.offset)
                        outBuf.limit(info.offset + info.size)
                        val shortBuf = outBuf.order(ByteOrder.LITTLE_ENDIAN).asShortBuffer()
                        val shorts = ShortArray(shortBuf.remaining())
                        shortBuf.get(shorts)
                        sink.pushPcm16(shorts, shorts.size)
                    }
                    codec.releaseOutputBuffer(outIdx, false)
                    if ((info.flags and MediaCodec.BUFFER_FLAG_END_OF_STREAM) != 0) {
                        outputDone = true
                    }
                }
            }
            return true
        } catch (e: Exception) {
            Log.e(TAG, "Failed decoding audio ${audioFile.name}: ${e.message}")
            return false
        } finally {
            try { codec?.stop() } catch (_: Exception) {}
            try { codec?.release() } catch (_: Exception) {}
            try { extractor.release() } catch (_: Exception) {}
        }
    }

    /**
     * Two-pass low-memory extractor:
     *   Pass 1 builds 200 Hz envelope (~1 MB) & aligns blindly to Polar contact times.
     *   Pass 2 buffers ONLY [-250ms, +135ms] slices around aligned contacts (~2.5 MB)
     *   and enforces the open-mic background floor.
     */
    fun extractAlignedSessionAudio(
        audioFile: File,
        polarContactTimesByShotIdx: Map<Int, Double>,
        gPrePkByShotIdx: Map<Int, Float>,
        sessionStartWallMs: Long,
        melFb: Array<FloatArray>
    ): SessionAudioFeatures? {
        if (polarContactTimesByShotIdx.size < 3) return null
        val audStartMs = parseAudioStartWallMs(audioFile) ?: return null
        val initOffsetS = (sessionStartWallMs - audStartMs) / 1000.0

        // Pass 1: Build 200 Hz envelope (1 bin per 80 target samples = 5ms)
        val envBins = ArrayList<Float>(120_000)
        var currBin = 0L
        var currMax = 0f
        var totalSamples = 0L

        val pass1Ok = streamDecodeAudio(audioFile) { idx, value ->
            totalSamples = idx + 1L
            val b = idx / HOP_LEN
            val av = abs(value)
            if (b == currBin) {
                if (av > currMax) currMax = av
            } else {
                envBins.add(currMax)
                while (envBins.size < b.toInt()) envBins.add(0f)
                currBin = b
                currMax = av
            }
        }
        if (!pass1Ok || totalSamples < PATCH_SAMPLES) return null
        if (currMax > 0f) envBins.add(currMax)

        val envArr = FloatArray(envBins.size) { envBins[it] }
        val sortedEntries = polarContactTimesByShotIdx.entries.sortedBy { it.key }
        val contactArr = DoubleArray(sortedEntries.size) { k -> sortedEntries[k].value }

        val alignment = blindAlignEnvelopeToPolar(envArr, contactArr, initOffsetS) ?: return null
        if (alignment.nInliers < 3 || alignment.inlierRatio < 0.45f || alignment.medErrS > 0.030f) {
            Log.i(TAG, "Audio alignment did not pass gate: inl=${alignment.nInliers}, ratio=${alignment.inlierRatio}, err=${alignment.medErrS}")
            return null
        }

        // Compute tiny extraction windows for each shot
        data class WindowSpec(
            val shotIdx: Int,
            val i0: Long,
            val bg0: Long,
            val bg1: Long,
            val segBuf: FloatArray,
            val bgBuf: FloatArray
        )
        val windows = mutableListOf<WindowSpec>()
        for ((shotIdx, tc) in sortedEntries) {
            val tAud = alignment.slope * tc + alignment.intercept
            val i0 = round((tAud - 0.035) * SAMPLE_RATE).toLong()
            val i1 = i0 + PATCH_SAMPLES
            if (i0 >= 0L && i1 <= totalSamples) {
                val bg0 = maxOf(0L, round((tAud - 0.250) * SAMPLE_RATE).toLong())
                val bg1 = maxOf(bg0 + 1L, round((tAud - 0.060) * SAMPLE_RATE).toLong())
                windows.add(
                    WindowSpec(
                        shotIdx = shotIdx,
                        i0 = i0,
                        bg0 = bg0,
                        bg1 = minOf(totalSamples, bg1),
                        segBuf = FloatArray(PATCH_SAMPLES),
                        bgBuf = FloatArray((minOf(totalSamples, bg1) - bg0).toInt())
                    )
                )
            }
        }
        if (windows.size < 3) return null

        // Pass 2: Sequential copy into small per-shot buffers
        val sortedWins = windows.sortedBy { it.bg0 }
        var firstActiveIdx = 0
        streamDecodeAudio(audioFile) { idx, value ->
            while (firstActiveIdx < sortedWins.size && idx >= sortedWins[firstActiveIdx].i0 + PATCH_SAMPLES) {
                firstActiveIdx++
            }
            for (k in firstActiveIdx until sortedWins.size) {
                val w = sortedWins[k]
                if (idx < w.bg0) break
                if (idx in w.bg0 until w.bg1) {
                    w.bgBuf[(idx - w.bg0).toInt()] = value
                }
                if (idx in w.i0 until (w.i0 + PATCH_SAMPLES)) {
                    w.segBuf[(idx - w.i0).toInt()] = value
                }
            }
        }

        val patchesByShotIdx = LinkedHashMap<Int, AudioPatchAndScalars>()
        val bgList = mutableListOf<Float>()
        for (w in windows) {
            val gPrePk = gPrePkByShotIdx[w.shotIdx] ?: 1f
            val res = computeLogMelAndAudioScalars(w.segBuf, w.bgBuf, gPrePk, melFb)
            patchesByShotIdx[w.shotIdx] = res
            bgList.add(res.scalars["aud_bg_rms"] ?: 0f)
        }
        if (bgList.size < 3) return null
        val sortedBg = bgList.sorted()
        val medianBg = sortedBg[sortedBg.size / 2]
        if (medianBg < OPEN_MIC_BG_RMS_MIN) {
            Log.i(TAG, "Audio gated/muted (median bg rms=$medianBg < $OPEN_MIC_BG_RMS_MIN) -> falling back to Polar model")
            return null
        }

        return SessionAudioFeatures(alignment, patchesByShotIdx, medianBg)
    }
}
