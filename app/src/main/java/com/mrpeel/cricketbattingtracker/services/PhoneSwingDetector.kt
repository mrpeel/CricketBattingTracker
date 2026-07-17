package com.mrpeel.cricketbattingtracker.services

import android.content.Context
import android.util.Log
import com.mrpeel.cricketbattingtracker.data.AppDatabase
import com.mrpeel.cricketbattingtracker.data.InningsEvent
import com.mrpeel.cricketbattingtracker.ml.GeneratedForest
import com.mrpeel.cricketbattingtracker.ml.SwingFeatures
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.io.File
import java.text.SimpleDateFormat
import java.util.Locale
import kotlin.math.*

object PhoneSwingDetector {
    private const val TAG = "PhoneSwingDetector"

    data class WatchRotSample(val timeNanos: Long, val elapsedSecs: Double, val qx: Float, val qy: Float, val qz: Float, val qw: Float)
    data class WatchIMUSample(val timeNanos: Long, val elapsedSecs: Double, val x: Float, val y: Float, val z: Float, val mag: Float)
    data class PolarSample(val phoneMs: Long, val sensorNs: Long, val x: Float, val y: Float, val z: Float, val mag: Float)

    data class TimeAlignment(
        val offsetMs: Double,    // Polar_phoneMs = watch_wallMs * (1 + driftRate) + offsetMs
        val driftRate: Double
    ) {
        fun watchToPolarMs(watchMs: Long): Long {
            return ((watchMs * (1.0 + driftRate)) + offsetMs).toLong()
        }
        fun polarToWatchMs(polarMs: Long): Long {
            return ((polarMs - offsetMs) / (1.0 + driftRate)).toLong()
        }
    }

    /**
     * Entry point to process a completed watch + Polar session batch.
     */
    suspend fun processSession(
        inningsId: Long,
        watchDir: File,
        polarDir: File,
        context: Context
    ) = withContext(Dispatchers.IO) {
        Log.d(TAG, "Starting phone-bound batch processing for innings $inningsId...")

        // 1. Load watch data
        val watchAcc = parseWatchIMUCsv(File(watchDir, "WatchAccelerometer.csv"))
        val watchGyro = parseWatchIMUCsv(File(watchDir, "WatchGyroscope.csv"))
        val watchGrav = parseWatchIMUCsv(File(watchDir, "WatchGravity.csv"))
        val watchRot = parseWatchRotCsv(File(watchDir, "WatchGameOrientation.csv").let { 
            if (it.exists()) it else File(watchDir, "WatchOrientation.csv") 
        })
        val timelineFile = File(watchDir, "latest_timeline.txt")

        if (watchAcc.isEmpty() || watchRot.isEmpty()) {
            Log.e(TAG, "Watch raw files are missing or empty — skipping processing")
            return@withContext
        }

        // 2. Parse watch tap sequences from latest_timeline.txt
        val watchTapSequences = parseWatchTapSequences(timelineFile)
        Log.d(TAG, "Parsed ${watchTapSequences.size} watch tap sequences")

        // 3. Parse Polar Sense raw data
        val polarAccFile = polarDir.listFiles()?.firstOrNull { it.name.contains("PolarAccelerometer") }
        val polarGyroFile = polarDir.listFiles()?.firstOrNull { it.name.contains("PolarGyroscope") }

        if (polarAccFile == null) {
            Log.e(TAG, "Polar Accelerometer CSV not found — skipping processing")
            return@withContext
        }

        val polarAcc = parsePolarCsv(polarAccFile, isGyro = false)
        val polarGyro = parsePolarCsv(polarGyroFile ?: File(polarDir, "PolarGyroscope.csv"), isGyro = true)
        Log.d(TAG, "Loaded ${polarAcc.size} Polar ACC samples, ${polarGyro.size} Polar GYRO samples")

        // 4. Determine Polar tap sequences (try PolarSenseManager, fallback to parsing raw peaks)
        var polarTapSequences = PolarSenseManager.detectedTapSequences.value
        if (polarTapSequences.isEmpty()) {
            polarTapSequences = detectPolarTapSequences(polarAcc)
            Log.d(TAG, "Detected ${polarTapSequences.size} Polar tap sequences from raw data")
        }

        // 5. Align watch and phone clocks
        val alignment = matchTapSequences(watchTapSequences, polarTapSequences)
        if (alignment == null) {
            Log.e(TAG, "Failed to match tap sequences for clock alignment — skipping processing")
            return@withContext
        }
        Log.d(TAG, "Clock Alignment computed: offset=${alignment.offsetMs}ms, drift=${alignment.driftRate}")

        // 6. Detect physical impacts in Polar Sense accelerometer (peaks > 24.5 m/s² = ~2.5g)
        val impactPeaks = detectImpactPeaks(polarAcc, threshold = 24.5f)
        Log.d(TAG, "Detected ${impactPeaks.size} physical impacts from Polar sensor")

        val database = AppDatabase.getDatabase(context)
        val dao = database.inningsEventDao()

        // Clear existing mock events for this innings except metadata
        dao.deleteTimelineForInningsSync(inningsId)

        // Write "Session Started" marker
        val watchStartMs = watchAcc.first().timeNanos / 1_000_000L
        dao.insertEvent(InningsEvent(
            inningsId = inningsId,
            timestamp = watchStartMs,
            description = "Session Started",
            location = "Net Practice"
        ))

        var shotCount = 0
        var maxSpeed = 0f

        // 7. Extract features and classify each shot
        for (polarPeakTimeMs in impactPeaks) {
            val watchTimeMs = alignment.polarToWatchMs(polarPeakTimeMs)
            val watchTimeNanos = watchTimeMs * 1_000_000L

            // Extract stance look-back window [t - 3.0s, t - 1.0s]
            val stanceStart = watchTimeNanos - 3_000_000_000L
            val stanceEnd = watchTimeNanos - 1_000_000_000L
            val stanceRotSamples = watchRot.filter { it.timeNanos in stanceStart..stanceEnd }

            if (stanceRotSamples.size < 10) continue

            // Find the most stable 0.8s window
            val qStance = findMostStableStance(stanceRotSamples, windowSizeNanos = 800_000_000L) ?: continue
            val qStanceInv = FloatArray(4).apply { conjugateQuat(qStance, this) }

            // Extract swing segments
            val tStart = watchTimeNanos - 800_000_000L
            val tSplit1 = watchTimeNanos - 200_000_000L
            val tSplit2 = watchTimeNanos - 50_000_000L
            val tEnd = watchTimeNanos + 300_000_000L

            // --- Segment 1: Footwork [tStart, tSplit1] ---
            val (s1DeltaX, s1DeltaZ) = getDisplacement(watchRot, tStart, tSplit1, qStanceInv)
            val s1GyroYStd = getGyroStd(watchGyro, tStart, tSplit1, isY = true)
            val s1GyroZStd = getGyroStd(watchGyro, tStart, tSplit1, isY = false)

            // --- Segment 2: Height & Intent [tSplit1, tSplit2] ---
            val (s2DeltaX, s2DeltaZ) = getDisplacement(watchRot, tSplit1, tSplit2, qStanceInv)
            val s2GyroMag = getGyroPeak(watchGyro, tSplit1, tSplit2)
            val s2GravYMean = getGravityMeanY(watchGrav, tSplit1, tSplit2)

            // --- Segment 3: Release & Roll [tSplit2, tEnd] ---
            val (s3DeltaX, s3DeltaZ) = getDisplacement(watchRot, tSplit2, tEnd, qStanceInv)
            val s3PlaneRatio = if (s3DeltaZ > 0f) s3DeltaX / s3DeltaZ else 0f
            val s3GyroYMin = getGyroMinY(watchGyro, tSplit2, tEnd)

            // Relative roll and yaw at impact
            val impactRot = findClosestRotation(watchRot, tSplit2)
            var s3RollImpactDeg = 0f
            var s3YawImpactDeg = 0f
            val qRel = FloatArray(4)
            val vRot = FloatArray(3)
            val vLocal = floatArrayOf(0f, -1f, 0f)
            
            if (impactRot != null) {
                val qCurr = floatArrayOf(impactRot.qx, impactRot.qy, impactRot.qz, impactRot.qw)
                multiplyQuats(qStanceInv, qCurr, qRel)
                rotateVector(qRel, vLocal, vRot)
                s3RollImpactDeg = calcRelativeRoll(qRel)
                s3YawImpactDeg = atan2(vRot[0], -vRot[1]) * 57.29578f
            }

            // Run Random Forest classifier
            val features = SwingFeatures(
                s1_gyro_y_std = s1GyroYStd,
                s1_gyro_z_std = s1GyroZStd,
                s1_deltaX = s1DeltaX,
                s1_deltaZ = s1DeltaZ,
                s2_gyroMag = s2GyroMag,
                s2_grav_y_mean = s2GravYMean,
                s2_deltaX = s2DeltaX,
                s2_deltaZ = s2DeltaZ,
                s3_rollImpactDeg = s3RollImpactDeg,
                s3_yawImpactDeg = s3YawImpactDeg,
                s3_deltaX = s3DeltaX,
                s3_deltaZ = s3DeltaZ,
                s3_planeRatio = s3PlaneRatio,
                s3_gyro_y_min = s3GyroYMin
            )
            var shotType = GeneratedForest.predict(features)

            // 8. Extract Polar features for bottom-hand refinement
            val polarAccWin = polarAcc.filter { it.phoneMs in (polarPeakTimeMs - 1000L)..(polarPeakTimeMs + 1000L) }
            val polarGyroWin = polarGyro.filter { it.phoneMs in (polarPeakTimeMs - 1000L)..(polarPeakTimeMs + 1000L) }

            val pAccPeak = if (polarAccWin.isNotEmpty()) polarAccWin.maxOf { it.mag } else 0f
            val pGyroPeak = if (polarGyroWin.isNotEmpty()) polarGyroWin.maxOf { it.mag } else 0f
            val watchGyroPeak = getGyroPeak(watchGyro, watchTimeNanos - 1_000_000_000L, watchTimeNanos + 1_000_000_000L)
            
            val gyroRatio = if (watchGyroPeak > 0.01f) pGyroPeak / watchGyroPeak else 0f
            val accRatio = if (watchAcc.isNotEmpty()) {
                val wAccPeak = watchAcc.filter { it.timeNanos in (watchTimeNanos - 1_000_000_000L)..(watchTimeNanos + 1_000_000_000L) }.maxOfOrNull { it.mag } ?: 1f
                pAccPeak / wAccPeak
            } else 0f

            // Refinement rules using ShotEnhancementConfig
            if (shotType == "DRIVE/DEFENCE") {
                if (gyroRatio > ShotEnhancementConfig.DRIVE_TO_POWER_GYRO_RATIO && pAccPeak > ShotEnhancementConfig.DRIVE_TO_POWER_ACC_PEAK) {
                    shotType = "POWER DRIVE"
                }
            } else if (shotType == "GLANCE/FLICK") {
                if (gyroRatio < ShotEnhancementConfig.FLICK_TO_GUIDE_GYRO_RATIO && pGyroPeak < ShotEnhancementConfig.FLICK_TO_GUIDE_GYRO_PEAK) {
                    shotType = "DEFLECTION/GUIDE"
                }
            } else if (shotType == "PULL/HOOK") {
                if (gyroRatio > ShotEnhancementConfig.PULL_TO_SLOG_GYRO_RATIO && pGyroPeak > ShotEnhancementConfig.PULL_TO_SLOG_GYRO_PEAK) {
                    shotType = "SLOG"
                }
            }

            // Sync score: 0-100 based on peaks alignment
            val pAccPeakTime = polarAccWin.maxByOrNull { it.mag }?.phoneMs ?: polarPeakTimeMs
            val timeLeadMs = pAccPeakTime - polarPeakTimeMs
            val timePenalty = min(1.0f, abs(timeLeadMs) / 500f)
            val ratioPenalty = min(1.0f, abs(gyroRatio - 1.0f))
            val syncScore = ((1.0f - timePenalty * 0.6f - ratioPenalty * 0.4f) * 100f).coerceIn(0f, 100f)

            // Speed calculation
            val multiplier = when (shotType) {
                "DRIVE/DEFENCE", "DEFLECTION/GUIDE" -> 1.45f
                "GLANCE/FLICK", "SWEEP", "CUT/PUNCH", "PULL/HOOK" -> 1.30f
                "SLOG", "POWER DRIVE" -> 1.40f
                else -> 1.30f
            }
            val finalSpeedKmh = s2GyroMag * 0.68f * 3.6f * multiplier
            
            // Hit / miss validation
            val isHit = pAccPeak >= 12.0f
            val sweetSpot = if (isHit) {
                when {
                    pAccPeak / finalSpeedKmh < 2.5f -> "Excellent"
                    pAccPeak / finalSpeedKmh < 3.0f -> "Good"
                    else -> "Poor"
                }
            } else "Miss"

            // Save to database
            val dbEvent = InningsEvent(
                inningsId = inningsId,
                timestamp = watchTimeMs,
                description = if (isHit) "$shotType ($sweetSpot)" else "Play and Miss",
                batSpeed = finalSpeedKmh,
                impactForce = pAccPeak,
                impactTimeMs = abs(timeLeadMs),
                shotType = shotType,
                efficiency = (pGyroPeak / max(0.01f, s2GyroMag) * 100f).coerceIn(0f, 100f),
                backliftAngle = 0f,
                followThroughAngle = 0f,
                wristRollDeg = s3RollImpactDeg,
                location = "Net Practice",
                bladeAngle = 0f,
                bladeClass = "N/A",
                launchAngle = 0f,
                launchClass = "N/A",
                bottom_hand_gyro_peak = pGyroPeak,
                bottom_hand_acc_peak = pAccPeak,
                bottom_hand_gyro_ratio = gyroRatio,
                bottom_hand_acc_ratio = accRatio,
                bottom_hand_time_lead_ms = timeLeadMs,
                bottom_hand_sync_score = syncScore,
                swing_feature_s1_gyro_y_std = s1GyroYStd,
                swing_feature_s1_gyro_z_std = s1GyroZStd,
                swing_feature_s1_delta_x = s1DeltaX,
                swing_feature_s1_delta_z = s1DeltaZ,
                swing_feature_s2_gyro_mag = s2GyroMag,
                swing_feature_s2_grav_y_mean = s2GravYMean,
                swing_feature_s2_delta_x = s2DeltaX,
                swing_feature_s2_delta_z = s2DeltaZ,
                swing_feature_s3_roll_deg = s3RollImpactDeg,
                swing_feature_s3_yaw_deg = s3YawImpactDeg,
                swing_feature_s3_delta_x = s3DeltaX,
                swing_feature_s3_delta_z = s3DeltaZ,
                swing_feature_s3_plane_ratio = s3PlaneRatio,
                swing_feature_s3_gyro_y_min = s3GyroYMin
            )
            dao.insertEvent(dbEvent)

            shotCount++
            if (finalSpeedKmh > maxSpeed) maxSpeed = finalSpeedKmh
        }

        // Write "Session Ended" marker
        val watchEndMs = watchAcc.last().timeNanos / 1_000_000L
        dao.insertEvent(InningsEvent(
            inningsId = inningsId,
            timestamp = watchEndMs,
            description = "Session Ended",
            location = "Net Practice"
        ))

        val prefs = context.getSharedPreferences("pitch_analytix_prefs", Context.MODE_PRIVATE)
        prefs.edit().putBoolean("processed_innings_$inningsId", true).apply()

        Log.d(TAG, "Processed $shotCount shots. Max Speed: $maxSpeed km/h. Syncing metadata...")
    }

    // --- Biomechanical stability and rotation math ---

    private fun findMostStableStance(samples: List<WatchRotSample>, windowSizeNanos: Long): FloatArray? {
        var bestQuat: FloatArray? = null
        var minVariance = Double.MAX_VALUE

        // Slide window by 50ms (50,000,000ns)
        val startTime = samples.first().timeNanos
        val endTime = samples.last().timeNanos

        var t = startTime
        while (t + windowSizeNanos <= endTime) {
            val winSamples = samples.filter { it.timeNanos in t..(t + windowSizeNanos) }
            if (winSamples.size >= 5) {
                // Compute average displacement
                var totalDisp = 0.0
                var count = 0
                for (i in 1 until winSamples.size) {
                    val prev = winSamples[i - 1]
                    val curr = winSamples[i]
                    val dot = (prev.qx * curr.qx + prev.qy * curr.qy + prev.qz * curr.qz + prev.qw * curr.qw).toDouble().coerceIn(-1.0, 1.0)
                    totalDisp += Math.toDegrees(2.0 * acos(abs(dot)))
                    count++
                }
                val avgDisp = totalDisp / count
                if (avgDisp < minVariance) {
                    minVariance = avgDisp
                    // Average components
                    val sumX = winSamples.map { it.qx }.sum()
                    val sumY = winSamples.map { it.qy }.sum()
                    val sumZ = winSamples.map { it.qz }.sum()
                    val sumW = winSamples.map { it.qw }.sum()
                    val norm = sqrt(sumX*sumX + sumY*sumY + sumZ*sumZ + sumW*sumW)
                    bestQuat = floatArrayOf(sumX/norm, sumY/norm, sumZ/norm, sumW/norm)
                }
            }
            t += 50_000_000L
        }

        return bestQuat
    }

    private fun getDisplacement(rotations: List<WatchRotSample>, tStart: Long, tEnd: Long, qStanceInv: FloatArray): Pair<Float, Float> {
        val sub = rotations.filter { it.timeNanos in tStart..tEnd }
        if (sub.size < 2) return Pair(0f, 0f)

        var minX = Float.MAX_VALUE; var maxX = -Float.MAX_VALUE
        var minZ = Float.MAX_VALUE; var maxZ = -Float.MAX_VALUE
        val qCurr = FloatArray(4)
        val qRel = FloatArray(4)
        val vLocal = floatArrayOf(0f, -1f, 0f)
        val vRot = FloatArray(3)

        for (s in sub) {
            qCurr[0] = s.qx; qCurr[1] = s.qy; qCurr[2] = s.qz; qCurr[3] = s.qw
            multiplyQuats(qStanceInv, qCurr, qRel)
            rotateVector(qRel, vLocal, vRot)
            if (vRot[0] < minX) minX = vRot[0]; if (vRot[0] > maxX) maxX = vRot[0]
            if (vRot[2] < minZ) minZ = vRot[2]; if (vRot[2] > maxZ) maxZ = vRot[2]
        }
        return Pair(maxX - minX, maxZ - minZ)
    }

    private fun getGyroStd(gyros: List<WatchIMUSample>, tStart: Long, tEnd: Long, isY: Boolean): Float {
        val sub = gyros.filter { it.timeNanos in tStart..tEnd }
        if (sub.size < 2) return 0f
        val vals = sub.map { if (isY) it.y else it.z }
        val mean = vals.average()
        return sqrt(vals.map { (it - mean).pow(2) }.average()).toFloat()
    }

    private fun getGyroPeak(gyros: List<WatchIMUSample>, tStart: Long, tEnd: Long): Float {
        val sub = gyros.filter { it.timeNanos in tStart..tEnd }
        return if (sub.isNotEmpty()) sub.maxOf { it.mag } else 0f
    }

    private fun getGyroMinY(gyros: List<WatchIMUSample>, tStart: Long, tEnd: Long): Float {
        val sub = gyros.filter { it.timeNanos in tStart..tEnd }
        return if (sub.isNotEmpty()) sub.minOf { it.y } else 0f
    }

    private fun getGravityMeanY(gravs: List<WatchIMUSample>, tStart: Long, tEnd: Long): Float {
        val sub = gravs.filter { it.timeNanos in tStart..tEnd }
        return if (sub.isNotEmpty()) sub.map { it.y }.average().toFloat() else -9.8f
    }

    private fun findClosestRotation(rotations: List<WatchRotSample>, targetTime: Long): WatchRotSample? {
        return rotations.minByOrNull { abs(it.timeNanos - targetTime) }
    }

    // --- Quaternion and vector rotation helpers ---

    private fun conjugateQuat(q: FloatArray, outQ: FloatArray) {
        outQ[0] = -q[0]; outQ[1] = -q[1]; outQ[2] = -q[2]; outQ[3] = q[3]
    }

    private fun multiplyQuats(q1: FloatArray, q2: FloatArray, outQ: FloatArray) {
        val x1 = q1[0]; val y1 = q1[1]; val z1 = q1[2]; val w1 = q1[3]
        val x2 = q2[0]; val y2 = q2[1]; val z2 = q2[2]; val w2 = q2[3]
        outQ[0] = w1*x2 + x1*w2 + y1*z2 - z1*y2
        outQ[1] = w1*y2 - x1*z2 + y1*w2 + z1*x2
        outQ[2] = w1*z2 + x1*y2 - y1*x2 + z1*w2
        outQ[3] = w1*w2 - x1*x2 - y1*y2 - z1*z2
    }

    private fun rotateVector(q: FloatArray, v: FloatArray, outV: FloatArray) {
        val qx = q[0]; val qy = q[1]; val qz = q[2]; val qw = q[3]
        val vx = v[0]; val vy = v[1]; val vz = v[2]
        val tx = 2.0f * (qy*vz - qz*vy)
        val ty = 2.0f * (qz*vx - qx*vz)
        val tz = 2.0f * (qx*vy - qy*vx)
        outV[0] = vx + qw*tx + (qy*tz - qz*ty)
        outV[1] = vy + qw*ty + (qz*tx - qx*tz)
        outV[2] = vz + qw*tz + (qx*ty - qy*tx)
    }

    private fun calcRelativeRoll(q: FloatArray): Float {
        val x = q[0]; val y = q[1]; val z = q[2]; val w = q[3]
        return atan2(2.0f*(w*y + x*z), 1.0f - 2.0f*(y*y + z*z)) * 57.29578f
    }

    // --- Parser helpers ---

    private fun parseWatchIMUCsv(file: File): List<WatchIMUSample> {
        val list = mutableListOf<WatchIMUSample>()
        if (!file.exists()) return list
        file.bufferedReader().use { br ->
            var isHeader = true
            br.forEachLine { line ->
                if (isHeader) { isHeader = false; return@forEachLine }
                val parts = line.split(",")
                if (parts.size >= 5) {
                    val t = parts[0].toLongOrNull() ?: return@forEachLine
                    val sec = parts[1].toDoubleOrNull() ?: 0.0
                    val x = parts[2].toFloatOrNull() ?: 0f
                    val y = parts[3].toFloatOrNull() ?: 0f
                    val z = parts[4].toFloatOrNull() ?: 0f
                    val mag = sqrt(x*x + y*y + z*z)
                    list.add(WatchIMUSample(t, sec, x, y, z, mag))
                }
            }
        }
        return list.sortedBy { it.timeNanos }
    }

    private fun parseWatchRotCsv(file: File): List<WatchRotSample> {
        val list = mutableListOf<WatchRotSample>()
        if (!file.exists()) return list
        file.bufferedReader().use { br ->
            var isHeader = true
            br.forEachLine { line ->
                if (isHeader) { isHeader = false; return@forEachLine }
                val parts = line.split(",")
                if (parts.size >= 6) {
                    val t = parts[0].toLongOrNull() ?: return@forEachLine
                    val sec = parts[1].toDoubleOrNull() ?: 0.0
                    val qx = parts[2].toFloatOrNull() ?: 0f
                    val qy = parts[3].toFloatOrNull() ?: 0f
                    val qz = parts[4].toFloatOrNull() ?: 0f
                    val qw = parts[5].toFloatOrNull() ?: 1f
                    list.add(WatchRotSample(t, sec, qx, qy, qz, qw))
                }
            }
        }
        return list.sortedBy { it.timeNanos }
    }

    private fun parsePolarCsv(file: File, isGyro: Boolean): List<PolarSample> {
        val list = mutableListOf<PolarSample>()
        if (!file.exists()) return list
        val dateFormat = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss.SSS", Locale.US)
        
        val reader = if (file.name.endsWith(".gz")) {
            java.io.BufferedReader(java.io.InputStreamReader(java.util.zip.GZIPInputStream(file.inputStream())))
        } else {
            file.bufferedReader()
        }
        
        reader.use { br ->
            var isHeader = true
            br.forEachLine { line ->
                if (isHeader) { isHeader = false; return@forEachLine }
                val parts = line.split(";")
                if (parts.size >= 5) {
                    val phoneTimestampStr = parts[0].trim()
                    val phoneMs = try {
                        dateFormat.parse(phoneTimestampStr)?.time ?: 0L
                    } catch (e: Exception) {
                        phoneTimestampStr.toLongOrNull() ?: 0L
                    }
                    val sensorNs = parts[1].trim().toLongOrNull() ?: return@forEachLine
                    var x = parts[2].trim().toFloatOrNull() ?: 0f
                    var y = parts[3].trim().toFloatOrNull() ?: 0f
                    var z = parts[4].trim().toFloatOrNull() ?: 0f
                    
                    if (isGyro) {
                        val dpsToRad = (Math.PI / 180.0).toFloat()
                        x *= dpsToRad
                        y *= dpsToRad
                        z *= dpsToRad
                    } else {
                        x *= 0.00980665f
                        y *= 0.00980665f
                        z *= 0.00980665f
                    }
                    
                    val mag = sqrt(x*x + y*y + z*z)
                    list.add(PolarSample(phoneMs, sensorNs, x, y, z, mag))
                }
            }
        }
        return list.sortedBy { it.sensorNs }
    }

    private fun parseWatchTapSequences(file: File): List<Pair<Long, List<Long>>> {
        val list = mutableListOf<Pair<Long, List<Long>>>()
        if (!file.exists()) return list
        file.bufferedReader().use { br ->
            br.forEachLine { line ->
                if (line.startsWith("TAP_SEQ:")) {
                    try {
                        val tsMatch = Regex("Ts=(\\d+)").find(line)
                        val wallClockMs = tsMatch?.groupValues?.get(1)?.toLongOrNull() ?: 0L
                        
                        val tapNanos = mutableListOf<Long>()
                        for (i in 1..5) {
                            val tMatch = Regex("T$i=(\\d+)").find(line)
                            tMatch?.groupValues?.get(1)?.toLongOrNull()?.let { tapNanos.add(it) }
                        }
                        if (tapNanos.size == 5 && wallClockMs > 0) {
                            list.add(Pair(wallClockMs, tapNanos))
                        }
                    } catch (e: Exception) {
                        Log.e(TAG, "Failed to parse TAP_SEQ line: $line", e)
                    }
                }
            }
        }
        return list
    }

    private fun detectPolarTapSequences(samples: List<PolarSample>): List<List<Long>> {
        val tapThreshold = 25.0f // m/s^2 magnitude
        val minGapMs = 200L
        val maxGapMs = 1500L
        val maxSpanMs = 5000L

        val candidateIndices = samples.indices.filter { samples[it].mag >= tapThreshold }
        val localPeaks = mutableListOf<PolarSample>()

        for (idx in candidateIndices) {
            val sample = samples[idx]
            val wStart = samples.binarySearchBy(sample.phoneMs - 150L) { it.phoneMs }.let { if (it < 0) -(it + 1) else it }
            val wEnd = samples.binarySearchBy(sample.phoneMs + 150L) { it.phoneMs }.let { if (it < 0) -(it + 1) else it }
            val maxInWindow = samples.subList(wStart, min(wEnd + 1, samples.size)).maxOf { it.mag }
            
            if (sample.mag >= maxInWindow) {
                if (localPeaks.none { abs(sample.phoneMs - it.phoneMs) < minGapMs }) {
                    localPeaks.add(sample)
                }
            }
        }

        val sequences = mutableListOf<List<Long>>()
        var i = 0
        while (i < localPeaks.size - 4) {
            val seq = localPeaks.subList(i, i + 5)
            val totalSpan = seq.last().phoneMs - seq.first().phoneMs
            if (totalSpan <= maxSpanMs) {
                var valid = true
                for (j in 1 until 5) {
                    val gap = seq[j].phoneMs - seq[j - 1].phoneMs
                    if (gap < minGapMs || gap > maxGapMs) {
                        valid = false; break
                    }
                }
                if (valid) {
                    sequences.add(seq.map { it.phoneMs })
                    i += 5
                    continue
                }
            }
            i++
        }
        return sequences
    }

    private fun detectImpactPeaks(samples: List<PolarSample>, threshold: Float): List<Long> {
        val peaks = mutableListOf<Long>()
        val minGapMs = 1500L
        
        val candidates = samples.indices.filter { samples[it].mag >= threshold }
        for (idx in candidates) {
            val s = samples[idx]
            // Ensure local maximum within +-500ms
            val wStart = samples.binarySearchBy(s.phoneMs - 500L) { it.phoneMs }.let { if (it < 0) -(it + 1) else it }
            val wEnd = samples.binarySearchBy(s.phoneMs + 500L) { it.phoneMs }.let { if (it < 0) -(it + 1) else it }
            val maxInWindow = samples.subList(wStart, min(wEnd + 1, samples.size)).maxOf { it.mag }
            
            if (s.mag >= maxInWindow) {
                if (peaks.none { abs(s.phoneMs - it) < minGapMs }) {
                    peaks.add(s.phoneMs)
                }
            }
        }
        return peaks
    }

    private fun matchTapSequences(
        watchTaps: List<Pair<Long, List<Long>>>,
        polarTaps: List<List<Long>>
    ): TimeAlignment? {
        if (watchTaps.isEmpty() || polarTaps.isEmpty()) return null

        val matches = mutableListOf<Pair<Long, Long>>()

        for (wIdx in watchTaps.indices) {
            val watchAnchorMs = watchTaps[wIdx].first
            val watchSeq = watchTaps[wIdx].second
            val watchIntervals = (0 until 4).map { (watchSeq[it + 1] - watchSeq[it]) / 1_000_000.0 }

            var bestPolarIdx = -1
            var bestError = Double.MAX_VALUE

            for (pIdx in polarTaps.indices) {
                val polarSeq = polarTaps[pIdx]
                if (polarSeq.size != 5) continue
                val polarIntervals = (0 until 4).map { (polarSeq[it + 1] - polarSeq[it]).toDouble() }

                val error = watchIntervals.zip(polarIntervals) { w, p -> abs(w - p) }.sum()
                if (error < bestError) {
                    bestError = error
                    bestPolarIdx = pIdx
                }
            }

            if (bestPolarIdx >= 0 && bestError < 500.0) {
                val polarSeq = polarTaps[bestPolarIdx]
                matches.add(Pair(watchAnchorMs, polarSeq[4]))
            }
        }

        if (matches.isEmpty()) return null

        return if (matches.size == 1) {
            val offset = matches[0].second.toDouble() - matches[0].first.toDouble()
            TimeAlignment(offsetMs = offset, driftRate = 0.0)
        } else {
            val watchTimes = matches.map { it.first.toDouble() }.toDoubleArray()
            val polarTimes = matches.map { it.second.toDouble() }.toDoubleArray()
            val n = watchTimes.size
            val sumX = watchTimes.sum()
            val sumY = polarTimes.sum()
            val sumXY = watchTimes.zip(polarTimes) { x, y -> x * y }.sum()
            val sumX2 = watchTimes.sumOf { it * it }

            val slope = (n * sumXY - sumX * sumY) / (n * sumX2 - sumX * sumX)
            val intercept = (sumY - slope * sumX) / n
            TimeAlignment(offsetMs = intercept, driftRate = slope - 1.0)
        }
    }
}
