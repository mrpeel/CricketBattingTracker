package com.mrpeel.cricketbattingtracker.services

import android.content.Context
import android.util.Log
import com.mrpeel.cricketbattingtracker.data.AppDatabase
import com.mrpeel.cricketbattingtracker.data.InningsEvent
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.io.BufferedReader
import java.io.File
import java.io.FileInputStream
import java.io.InputStreamReader
import java.util.zip.GZIPInputStream
import kotlin.math.*

/**
 * Computes bottom-hand (Polar Sense) enhancement metrics for shots after
 * the watch timeline arrives at session end.
 *
 * Workflow:
 * 1. Parse TAP_SEQ events from the ingested timeline (watch-side tap detections)
 * 2. Match against Polar Sense tap sequences (phone-side detections from PolarSenseManager)
 * 3. Compute linear time alignment (offset + drift) between watch and Polar clocks
 * 4. For each shot, extract Polar features from ±1.0s window around the aligned impact time
 * 5. Update Room DB with bottom_hand_* columns
 */
object ShotEnhancementEngine {
    private const val TAG = "ShotEnhancement"

    /**
     * Enhance shots for the given innings with Polar Sense bottom-hand data.
     * Call after watch timeline ingestion completes.
     *
     * @param inningsId The innings to enhance
     * @param watchTapSequences TAP_SEQ events parsed from the watch timeline.
     *   Each entry is a Pair(wallClockMs, List<sensorNanos>) for the 5 taps.
     * @param context Application context for DB and file access
     */
    suspend fun enhance(
        inningsId: Long,
        watchTapSequences: List<Pair<Long, List<Long>>>,
        context: Context
    ) = withContext(Dispatchers.IO) {
        val polarTapSequences = PolarSenseManager.detectedTapSequences.value
        
        if (polarTapSequences.isEmpty()) {
            Log.d(TAG, "No Polar tap sequences detected — skipping enhancement")
            return@withContext
        }

        // Find the most recent Polar session directory
        val polarDir = findLatestPolarSessionDir(context)
        if (polarDir == null) {
            Log.d(TAG, "No Polar session data found — skipping enhancement")
            return@withContext
        }

        Log.d(TAG, "Starting enhancement for innings $inningsId with ${watchTapSequences.size} watch taps, ${polarTapSequences.size} Polar taps")

        // Step 1-2: Match tap sequences
        val alignment = matchTapSequences(watchTapSequences, polarTapSequences)
        if (alignment == null) {
            Log.w(TAG, "Failed to match any tap sequences — skipping enhancement")
            return@withContext
        }
        Log.d(TAG, "Alignment computed: offset=${alignment.offsetMs}ms, driftRate=${alignment.driftRate}")

        // Step 3: Load Polar sensor data
        val polarAcc = loadPolarCsv(polarDir, "PolarAccelerometer")
        val polarGyro = loadPolarCsv(polarDir, "PolarGyroscope")

        if (polarAcc.isEmpty()) {
            Log.w(TAG, "No Polar ACC data loaded — skipping enhancement")
            return@withContext
        }

        // Step 4-5: Enhance each shot
        val db = AppDatabase.getDatabase(context)
        val dao = db.inningsEventDao()
        val events = dao.getTimelineForInningsListSync(inningsId)

        var enhanced = 0
        for (event in events) {
            if (event.shotType == null || event.shotType == "Session Started" || event.shotType == "Session Ended") continue

            val watchTimestampMs = event.timestamp
            val polarTimeMs = alignment.watchToPolarMs(watchTimestampMs)

            val accWindow = extractWindow(polarAcc, polarTimeMs, 1000L) // ±1s
            val gyroWindow = extractWindow(polarGyro, polarTimeMs, 1000L)

            if (accWindow.isEmpty()) continue

            // Compute bottom-hand metrics
            val polarAccPeak = accWindow.maxOf { it.magnitude }
            val polarGyroPeak = if (gyroWindow.isNotEmpty()) gyroWindow.maxOf { it.magnitude } else 0f

            // Watch peaks (from existing event data)
            val watchAccPeak = event.impactForce ?: 0f  // stored as peak accel
            val watchGyroPeak = event.swing_feature_s2_gyro_mag ?: 0f

            val gyroRatio = if (watchGyroPeak > 0.01f) polarGyroPeak / watchGyroPeak else 0f
            val accRatio = if (watchAccPeak > 0.01f) polarAccPeak / watchAccPeak else 0f

            // Time lead: difference between watch peak time and Polar peak time
            val polarAccPeakTime = accWindow.maxByOrNull { it.magnitude }?.timestampMs ?: polarTimeMs
            val timeLeadMs = polarAccPeakTime - polarTimeMs  // positive = bottom hand leads

            // Sync score: 0-100, based on time proximity and ratio proximity to 1.0
            val timePenalty = min(1.0f, abs(timeLeadMs) / 500f)  // 0 at 0ms, 1.0 at 500ms+
            val ratioPenalty = min(1.0f, abs(gyroRatio - 1.0f))  // 0 at 1.0, 1.0 at 0.0 or 2.0
            val syncScore = ((1.0f - timePenalty * 0.6f - ratioPenalty * 0.4f) * 100f).coerceIn(0f, 100f)

            dao.updateBottomHandMetrics(
                eventId = event.id,
                gyroPeak = polarGyroPeak,
                accPeak = polarAccPeak,
                gyroRatio = gyroRatio,
                accRatio = accRatio,
                timeLeadMs = timeLeadMs,
                syncScore = syncScore
            )
            enhanced++
        }

        Log.d(TAG, "✅ Enhanced $enhanced shots with bottom-hand data for innings $inningsId")
    }

    // --- Data classes ---

    data class TimeAlignment(
        val offsetMs: Double,    // Polar_phoneMs = watch_wallMs * (1 + driftRate) + offsetMs
        val driftRate: Double    // ppm-scale drift
    ) {
        fun watchToPolarMs(watchMs: Long): Long {
            return ((watchMs * (1.0 + driftRate)) + offsetMs).toLong()
        }
    }

    data class SensorSample(
        val timestampMs: Long,
        val x: Float,
        val y: Float,
        val z: Float,
        val magnitude: Float
    )

    // --- Tap matching ---

    /**
     * Match watch TAP_SEQ events against Polar Sense tap sequences.
     * Uses inter-tap timing pattern correlation.
     */
    private fun matchTapSequences(
        watchTaps: List<Pair<Long, List<Long>>>,
        polarTaps: List<List<Long>>
    ): TimeAlignment? {
        if (watchTaps.isEmpty() || polarTaps.isEmpty()) return null

        // Convert watch taps to wall-clock anchor times
        // watchTaps: Pair(wallClockMs_at_detection, [sensorNano1..5])
        // For alignment, we use the wallClockMs as the watch reference
        // polarTaps: each is List<phoneClockMs> for 5 taps

        data class MatchedPair(val watchMs: Long, val polarMs: Long)
        val matches = mutableListOf<MatchedPair>()

        for (watchTap in watchTaps) {
            val watchAnchorMs = watchTap.first  // wall-clock ms at detection

            // Compute inter-tap intervals for this watch sequence (using wall-clock proportional to sensor intervals)
            val watchSensorNanos = watchTap.second
            if (watchSensorNanos.size != 5) continue
            val watchIntervals = (0 until 4).map {
                (watchSensorNanos[it + 1] - watchSensorNanos[it]) / 1_000_000.0  // ns -> ms
            }

            // Find best matching Polar sequence by inter-tap pattern similarity
            var bestPolarIdx = -1
            var bestError = Double.MAX_VALUE

            for (pIdx in polarTaps.indices) {
                val polarSeq = polarTaps[pIdx]
                if (polarSeq.size != 5) continue

                val polarIntervals = (0 until 4).map {
                    (polarSeq[it + 1] - polarSeq[it]).toDouble()  // already in ms
                }

                // Sum of absolute differences in inter-tap intervals
                val error = watchIntervals.zip(polarIntervals) { w, p -> abs(w - p) }.sum()

                if (error < bestError) {
                    bestError = error
                    bestPolarIdx = pIdx
                }
            }

            // Accept match if total interval error < 500ms (generous for 4 gaps)
            if (bestPolarIdx >= 0 && bestError < 500.0) {
                val polarSeq = polarTaps[bestPolarIdx]
                // Use the midpoint of each sequence as the anchor
                val watchMidMs = watchAnchorMs  // detection time ≈ time of 5th tap
                val polarMidMs = polarSeq[4]  // 5th tap phone clock

                matches.add(MatchedPair(watchMidMs, polarMidMs))
                Log.d(TAG, "Tap match: watch=${watchMidMs}ms ↔ polar=${polarMidMs}ms (error=${bestError}ms)")
            }
        }

        if (matches.isEmpty()) return null

        return if (matches.size == 1) {
            // Offset-only alignment
            val offset = matches[0].polarMs.toDouble() - matches[0].watchMs.toDouble()
            TimeAlignment(offsetMs = offset, driftRate = 0.0)
        } else {
            // Linear regression for offset + drift
            val watchTimes = matches.map { it.watchMs.toDouble() }.toDoubleArray()
            val polarTimes = matches.map { it.polarMs.toDouble() }.toDoubleArray()

            // Simple least-squares linear fit: polar = slope * watch + intercept
            val n = watchTimes.size
            val sumX = watchTimes.sum()
            val sumY = polarTimes.sum()
            val sumXY = watchTimes.zip(polarTimes) { x, y -> x * y }.sum()
            val sumX2 = watchTimes.sumOf { it * it }

            val slope = (n * sumXY - sumX * sumY) / (n * sumX2 - sumX * sumX)
            val intercept = (sumY - slope * sumX) / n

            val driftRate = slope - 1.0  // slope ≈ 1.0 + small drift
            TimeAlignment(offsetMs = intercept, driftRate = driftRate)
        }
    }

    // --- Polar CSV loading ---

    private fun findLatestPolarSessionDir(context: Context): File? {
        val polarRoot = context.getExternalFilesDir("polar_sessions") ?: return null
        if (!polarRoot.exists()) return null

        return polarRoot.listFiles()
            ?.filter { it.isDirectory && it.name.startsWith("polar_session_") }
            ?.maxByOrNull { it.name }
    }

    /**
     * Load a Polar CSV file (semicolon-delimited).
     * Handles both .csv and .csv.gz files.
     * Format: "Phone timestamp;sensor timestamp [ns];X;Y;Z"
     */
    private fun loadPolarCsv(sessionDir: File, baseName: String): List<SensorSample> {
        val samples = mutableListOf<SensorSample>()

        // Find matching files (there may be multiple segments from reconnections)
        val files = sessionDir.listFiles()?.filter { file ->
            val name = file.name
            name.contains(baseName, ignoreCase = true) &&
                (name.endsWith(".csv") || name.endsWith(".csv.gz"))
        } ?: return samples

        val dateFormat = java.text.SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss.SSS", java.util.Locale.US)

        for (file in files) {
            try {
                val reader = if (file.name.endsWith(".gz")) {
                    BufferedReader(InputStreamReader(GZIPInputStream(FileInputStream(file))))
                } else {
                    BufferedReader(InputStreamReader(FileInputStream(file)))
                }

                reader.use { br ->
                    var isHeader = true
                    br.forEachLine { line ->
                        if (isHeader) {
                            isHeader = false
                            return@forEachLine
                        }
                        val parts = line.split(";")
                        if (parts.size >= 5) {
                            try {
                                val phoneTimestampStr = parts[0].trim()
                                val phoneMs = try {
                                    dateFormat.parse(phoneTimestampStr)?.time ?: 0L
                                } catch (e: Exception) {
                                    phoneTimestampStr.toLongOrNull() ?: 0L
                                }
                                val x = parts[2].trim().toFloat()
                                val y = parts[3].trim().toFloat()
                                val z = parts[4].trim().toFloat()
                                val mag = sqrt(x * x + y * y + z * z)
                                samples.add(SensorSample(phoneMs, x, y, z, mag))
                            } catch (e: NumberFormatException) {
                                // Skip malformed lines
                            }
                        }
                    }
                }
            } catch (e: Exception) {
                Log.e(TAG, "Error reading Polar CSV ${file.name}: ${e.message}")
            }
        }

        samples.sortBy { it.timestampMs }
        return samples
    }

    /** Extract samples within ±windowMs of the target timestamp. */
    private fun extractWindow(
        samples: List<SensorSample>,
        targetMs: Long,
        windowMs: Long
    ): List<SensorSample> {
        val start = targetMs - windowMs
        val end = targetMs + windowMs

        // Binary search for efficiency on sorted data
        var lo = samples.binarySearchBy(start) { it.timestampMs }
        if (lo < 0) lo = -(lo + 1)
        lo = lo.coerceAtLeast(0)

        val result = mutableListOf<SensorSample>()
        for (i in lo until samples.size) {
            val s = samples[i]
            if (s.timestampMs > end) break
            if (s.timestampMs >= start) result.add(s)
        }
        return result
    }
}
