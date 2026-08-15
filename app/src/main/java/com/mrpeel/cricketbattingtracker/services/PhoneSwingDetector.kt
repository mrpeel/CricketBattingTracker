package com.mrpeel.cricketbattingtracker.services

import android.content.Context
import android.util.Log
import com.mrpeel.cricketbattingtracker.data.AppDatabase
import com.mrpeel.cricketbattingtracker.data.InningsEvent
import com.mrpeel.cricketbattingtracker.ml.GeneratedForest
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.io.File
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.text.SimpleDateFormat
import java.util.Locale
import kotlin.math.*

object PhoneSwingDetector {
    private const val TAG = "PhoneSwingDetector"

    data class WatchRotSample(val timeNanos: Long, val elapsedSecs: Double, val qx: Float, val qy: Float, val qz: Float, val qw: Float)
    data class WatchIMUSample(val timeNanos: Long, val elapsedSecs: Double, val x: Float, val y: Float, val z: Float, val mag: Float)
    data class PolarSample(val phoneMs: Long, val sensorNs: Long, val x: Float, val y: Float, val z: Float, val mag: Float)

    sealed class WatchSensorEvent(val timestampNanos: Long) {
        class Accel(ts: Long, val values: FloatArray) : WatchSensorEvent(ts)
        class Gyro(ts: Long, val values: FloatArray) : WatchSensorEvent(ts)
        class Gravity(ts: Long, val values: FloatArray) : WatchSensorEvent(ts)
        class Rotation(ts: Long, val values: FloatArray) : WatchSensorEvent(ts)
        class Step(ts: Long) : WatchSensorEvent(ts)
    }

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
        polarDir: File?,
        context: Context
    ): Boolean = withContext(Dispatchers.IO) {
        Log.d(TAG, "Starting phone-bound two-pass batch processing for innings $inningsId...")

        // 1. Load watch data
        val watchAcc = loadWatchIMU(watchDir, "WatchAccelerometer")
        val watchGyro = loadWatchIMU(watchDir, "WatchGyroscope")
        val watchGrav = loadWatchIMU(watchDir, "WatchGravity")
        val watchRot = loadWatchRot(watchDir)


        if (watchAcc.isEmpty() || watchRot.isEmpty()) {
            Log.e(TAG, "Watch raw files are missing or empty — skipping processing")
            return@withContext false
        }

        val database = AppDatabase.getDatabase(context)
        val dao = database.inningsEventDao()
        dao.deleteTimelineForInningsSync(inningsId)


        val watchStartWallMs = parseSessionStartWallMs(watchDir)
        val watchStartSensorNs = watchAcc.first().timeNanos

        dao.insertEvent(InningsEvent(
            inningsId = inningsId,
            timestamp = watchStartWallMs,
            description = "Session Started",
            location = "Net Practice"
        ))

        // A. Load Polar data if available
        var alignment: TimeAlignment? = null
        var polarAcc: List<PolarSample> = emptyList()
        var polarGyro: List<PolarSample> = emptyList()

        if (polarDir != null && polarDir.exists()) {
            val timelineFile = File(watchDir, "latest_timeline.txt")
            val watchTapSequences = parseWatchTapSequences(timelineFile, watchStartSensorNs, watchStartWallMs)
            
            val polarAccFile = polarDir.listFiles()?.firstOrNull { it.name.contains("PolarAccelerometer") }
            val polarGyroFile = polarDir.listFiles()?.firstOrNull { it.name.contains("PolarGyroscope") }
            
            if (polarAccFile != null && polarGyroFile != null) {
                polarAcc = parsePolarCsv(polarAccFile, isGyro = false)
                polarGyro = parsePolarCsv(polarGyroFile, isGyro = true)
                
                var polarTapSequences = PolarSenseManager.detectedTapSequences.value
                if (polarTapSequences.isEmpty()) {
                    polarTapSequences = detectPolarTapSequences(polarAcc)
                }
                alignment = matchTapSequences(watchTapSequences, polarTapSequences)
                if (alignment == null && polarAcc.isNotEmpty() && watchStartWallMs > 0L) {
                    val polarStartMs = polarAcc.first().phoneMs
                    val fallbackOffset = (polarStartMs - watchStartWallMs).toDouble()
                    alignment = TimeAlignment(offsetMs = fallbackOffset, driftRate = 0.0)
                    Log.i(TAG, "Tap alignment fallback: using session start wall-clock offset (${fallbackOffset / 1000f}s)")
                }
            }
        }

        // 2. Build uniform 423 Hz multi-sensor matrix (28 channels x numFrames)
        val watchEndSensorNs = watchAcc.last().timeNanos
        val durationSec = (watchEndSensorNs - watchStartSensorNs) / 1_000_000_000.0
        val numFrames = kotlin.math.max(200, (durationSec * 423.0).toInt())
        val sensorMatrix = Array(28) { FloatArray(numFrames) }
        val timestampsMs = LongArray(numFrames)

        var accIdx = 0; var gyroIdx = 0; var gravIdx = 0; var rotIdx = 0
        var pAccIdx = 0; var pGyroIdx = 0

        for (i in 0 until numFrames) {
            val tNs = watchStartSensorNs + (i * 1_000_000_000.0 / 423.0).toLong()
            val tWallMs = watchStartWallMs + (i * 1000.0 / 423.0).toLong()
            timestampsMs[i] = tWallMs

            // Watch Acc
            while (accIdx < watchAcc.size - 1 && watchAcc[accIdx + 1].timeNanos <= tNs) accIdx++
            val ax = watchAcc[accIdx].x; val ay = watchAcc[accIdx].y; val az = watchAcc[accIdx].z
            sensorMatrix[0][i] = ax; sensorMatrix[1][i] = ay; sensorMatrix[2][i] = az

            // Watch Gyro
            while (gyroIdx < watchGyro.size - 1 && watchGyro[gyroIdx + 1].timeNanos <= tNs) gyroIdx++
            val gx = watchGyro[gyroIdx].x; val gy = watchGyro[gyroIdx].y; val gz = watchGyro[gyroIdx].z
            sensorMatrix[3][i] = gx; sensorMatrix[4][i] = gy; sensorMatrix[5][i] = gz

            // Watch Grav
            if (watchGrav.isNotEmpty()) {
                while (gravIdx < watchGrav.size - 1 && watchGrav[gravIdx + 1].timeNanos <= tNs) gravIdx++
                sensorMatrix[12][i] = watchGrav[gravIdx].x
                sensorMatrix[13][i] = watchGrav[gravIdx].y
                sensorMatrix[14][i] = watchGrav[gravIdx].z
            } else {
                sensorMatrix[12][i] = 0f; sensorMatrix[13][i] = -9.81f; sensorMatrix[14][i] = 0f
            }

            // Watch Rot
            var qx = 0f; var qy = 0f; var qz = 0f; var qw = 1f
            if (watchRot.isNotEmpty()) {
                while (rotIdx < watchRot.size - 1 && watchRot[rotIdx + 1].timeNanos <= tNs) rotIdx++
                qx = watchRot[rotIdx].qx; qy = watchRot[rotIdx].qy; qz = watchRot[rotIdx].qz; qw = watchRot[rotIdx].qw
            }
            sensorMatrix[15][i] = qx; sensorMatrix[16][i] = qy; sensorMatrix[17][i] = qz; sensorMatrix[18][i] = qw

            // World coords rotation
            val aw = rotateVectorQuat(qx, qy, qz, qw, ax, ay, az)
            sensorMatrix[6][i] = aw[0]; sensorMatrix[7][i] = aw[1]; sensorMatrix[8][i] = aw[2]

            val gw = rotateVectorQuat(qx, qy, qz, qw, gx, gy, gz)
            sensorMatrix[9][i] = gw[0]; sensorMatrix[10][i] = gw[1]; sensorMatrix[11][i] = gw[2]

            // Polar channels
            if (alignment != null && polarAcc.isNotEmpty() && polarGyro.isNotEmpty()) {
                val pMs = alignment.watchToPolarMs(tWallMs)
                while (pAccIdx < polarAcc.size - 1 && polarAcc[pAccIdx + 1].phoneMs <= pMs) pAccIdx++
                sensorMatrix[19][i] = polarAcc[pAccIdx].x
                sensorMatrix[20][i] = polarAcc[pAccIdx].y
                sensorMatrix[21][i] = polarAcc[pAccIdx].z

                while (pGyroIdx < polarGyro.size - 1 && polarGyro[pGyroIdx + 1].phoneMs <= pMs) pGyroIdx++
                sensorMatrix[22][i] = polarGyro[pGyroIdx].x
                sensorMatrix[23][i] = polarGyro[pGyroIdx].y
                sensorMatrix[24][i] = polarGyro[pGyroIdx].z

                sensorMatrix[25][i] = 1.0f
            } else {
                sensorMatrix[19][i] = 0f; sensorMatrix[20][i] = 0f; sensorMatrix[21][i] = 0f
                sensorMatrix[22][i] = 0f; sensorMatrix[23][i] = 0f; sensorMatrix[24][i] = 0f
                sensorMatrix[25][i] = 0.0f
            }
        }

        // Derived Channels 26 & 27:
        // Channel 26: post_impact_acc_ratio (window = 127 frames / 300ms)
        val wAccMags = FloatArray(numFrames) { k ->
            val ax = sensorMatrix[0][k]; val ay = sensorMatrix[1][k]; val az = sensorMatrix[2][k]
            kotlin.math.sqrt(ax * ax + ay * ay + az * az)
        }
        for (i in 0 until numFrames) {
            val preStart = kotlin.math.max(0, i - 127)
            var preMax = 0f
            for (k in preStart..i) if (wAccMags[k] > preMax) preMax = wAccMags[k]

            val postEnd = kotlin.math.min(numFrames - 1, i + 127)
            var postMax = 0f
            for (k in i..postEnd) if (wAccMags[k] > postMax) postMax = wAccMags[k]

            sensorMatrix[26][i] = postMax / (preMax + 1e-5f)
        }

        // Channel 27: wrist_gyro_roll_delta (window = 63 frames / 150ms)
        for (i in 0 until numFrames) {
            val winEnd = kotlin.math.min(numFrames - 1, i + 63)
            var rollSum = 0f
            for (k in i..winEnd) rollSum += sensorMatrix[3][k]
            sensorMatrix[27][i] = rollSum * (1.0f / 423.0f)
        }

        // 3. Run Stage 1 & Stage 2 TCN Inference
        val tcnRunner = com.mrpeel.cricketbattingtracker.ml.TcnModelRunner(context)
        val detectedShots = try {
            tcnRunner.runInference(sensorMatrix, timestampsMs)
        } catch (e: Exception) {
            Log.e(TAG, "TCN inference failed, falling back", e)
            emptyList()
        } finally {
            tcnRunner.close()
        }

        Log.d(TAG, "TCN Detection produced ${detectedShots.size} candidate shots")

        val hasPolarData = alignment != null && polarAcc.isNotEmpty() && polarGyro.isNotEmpty()
        
        var finalDetectedList = detectedShots
        if (finalDetectedList.isEmpty()) {
            Log.w(TAG, "TCN produced 0 candidate detections. Executing kinematic fallback candidate extractor...")
            val fallbackDetections = mutableListOf<com.mrpeel.cricketbattingtracker.ml.TcnModelRunner.DetectionResult>()
            val watchPeaksSensorNs = detectWatchImpactPeaks(watchGyro, threshold = ShotEnhancementConfig.WATCH_SHOCKWAVE_THRESHOLD)
            for (targetSensorNs in watchPeaksSensorNs) {
                if (verifySwingBackwards(targetSensorNs, watchGyro, watchRot)) {
                    val features = extractFeaturesAtSensorNs(
                        targetSensorNs = targetSensorNs,
                        watchGyro = watchGyro,
                        watchGrav = watchGrav,
                        watchRot = watchRot,
                        watchAcc = watchAcc
                    )
                    val predShotType = if (hasPolarData) {
                        com.mrpeel.cricketbattingtracker.ml.GeneratedDualForest.predict(features)
                    } else {
                        com.mrpeel.cricketbattingtracker.ml.GeneratedTopForest.predict(features)
                    }
                    val relShotMs = (targetSensorNs - watchStartSensorNs) / 1_000_000L
                    val shotWallMs = watchStartWallMs + relShotMs
                    fallbackDetections.add(
                        com.mrpeel.cricketbattingtracker.ml.TcnModelRunner.DetectionResult(
                            frameIndex = 0,
                            timestampMs = shotWallMs,
                            predictedShotType = predShotType,
                            confidence = 0.85f
                        )
                    )
                }
            }
            finalDetectedList = fallbackDetections
        }

        val finalShots = mutableListOf<InningsEvent>()

        for (det in finalDetectedList) {
            val shotWallMs = det.timestampMs
            val relShotMs = shotWallMs - watchStartWallMs
            val targetSensorNs = watchStartSensorNs + (relShotMs * 1_000_000L)
            val finalShotType = det.predictedShotType

            var bottomGyroPeak: Float? = null
            var bottomAccPeak: Float? = null
            var bottomGyroRatio: Float? = null
            var bottomAccRatio: Float? = null
            var bottomTimeLeadMs: Long? = null
            var bottomSyncScore: Float? = null
            var s1BottomGyroMag = 0f
            var s1BottomDeltaZ = 0f
            var s1BottomAccMag = 0f
            var s2BottomAccMean = 0f
            var s2DynamicRatioSlope = 0f
            var s3BottomPronationDeg = 0f
            var s3BottomGyroYMin = 0f
            var s3BottomAccPeak = 0f

            if (hasPolarData && alignment != null) {
                val polarPeakTimeMs = alignment.watchToPolarMs(shotWallMs)
                val polarAccWin = polarAcc.filter { it.phoneMs in (polarPeakTimeMs - 200L)..(polarPeakTimeMs + 100L) }
                val polarGyroWin = polarGyro.filter { it.phoneMs in (polarPeakTimeMs - 200L)..(polarPeakTimeMs + 100L) }

                val pAccPeak = if (polarAccWin.isNotEmpty()) polarAccWin.maxOf { it.mag } else 0f
                val pGyroPeak = if (polarGyroWin.isNotEmpty()) polarGyroWin.maxOf { it.mag } else 0f
                val watchGyroPeak = getGyroPeak(watchGyro, targetSensorNs - 200_000_000L, targetSensorNs + 100_000_000L)
                val gyroRatio = if (watchGyroPeak > 0.01f) pGyroPeak / watchGyroPeak else 0f
                val accRatio = if (watchAcc.isNotEmpty()) {
                    val wAccPeak = watchAcc.filter { it.timeNanos in (targetSensorNs - 200_000_000L)..(targetSensorNs + 100_000_000L) }.maxOfOrNull { it.mag } ?: 1f
                    pAccPeak / wAccPeak
                } else 0f

                val pAccPeakTime = polarAccWin.maxByOrNull { it.mag }?.phoneMs ?: polarPeakTimeMs
                val timeLeadMs = pAccPeakTime - polarPeakTimeMs
                val timePenalty = kotlin.math.min(1.0f, kotlin.math.abs(timeLeadMs) / 200f)
                val ratioPenalty = kotlin.math.min(1.0f, kotlin.math.abs(gyroRatio - 1.0f))
                val syncScore = ((1.0f - timePenalty * 0.6f - ratioPenalty * 0.4f) * 100f).coerceIn(0f, 100f)

                bottomGyroPeak = pGyroPeak
                bottomAccPeak = pAccPeak
                bottomGyroRatio = gyroRatio
                bottomAccRatio = accRatio
                bottomTimeLeadMs = timeLeadMs
                bottomSyncScore = syncScore

                // Segmented Polar extraction
                val s1Gyro = polarGyro.filter { it.phoneMs in (polarPeakTimeMs - 800L)..(polarPeakTimeMs - 200L) }
                if (s1Gyro.isNotEmpty()) {
                    s1BottomGyroMag = s1Gyro.maxOf { it.mag }
                    s1BottomDeltaZ = s1Gyro.maxOf { it.z } - s1Gyro.minOf { it.z }
                }

                // S1 bottom-hand acc (backswing: -800ms to -200ms)
                val s1AccBottom = polarAcc.filter { it.phoneMs in (polarPeakTimeMs - 800L)..(polarPeakTimeMs - 200L) }
                if (s1AccBottom.isNotEmpty()) {
                    s1BottomAccMag = s1AccBottom.maxOf { it.mag }
                }

                val s2Acc = polarAcc.filter { it.phoneMs in (polarPeakTimeMs - 200L)..(polarPeakTimeMs - 50L) }
                if (s2Acc.isNotEmpty()) {
                    s2BottomAccMean = s2Acc.map { it.mag }.average().toFloat()
                }

                val s2Gyro = polarGyro.filter { it.phoneMs in (polarPeakTimeMs - 200L)..(polarPeakTimeMs - 50L) }
                if (s2Gyro.size >= 2 && watchGyroPeak > 0.01f) {
                    val gStart = s2Gyro.first().mag
                    val gEnd = s2Gyro.last().mag
                    val dtSec = (s2Gyro.last().phoneMs - s2Gyro.first().phoneMs) / 1000f + 1e-4f
                    s2DynamicRatioSlope = ((gEnd - gStart) / dtSec) / watchGyroPeak
                }

                val s3Gyro = polarGyro.filter { it.phoneMs in (polarPeakTimeMs - 50L)..(polarPeakTimeMs + 300L) }
                if (s3Gyro.isNotEmpty()) {
                    var trapz = 0f
                    for (i in 1 until s3Gyro.size) {
                        val dt = (s3Gyro[i].phoneMs - s3Gyro[i-1].phoneMs) / 1000f
                        trapz += 0.5f * (s3Gyro[i].y + s3Gyro[i-1].y) * dt
                    }
                    s3BottomPronationDeg = trapz * (180f / Math.PI.toFloat())
                    s3BottomGyroYMin = s3Gyro.minOf { it.y }
                }

                // S3 bottom-hand acc peak (impact/follow-through: -50ms to +300ms)
                val s3AccBottom = polarAcc.filter { it.phoneMs in (polarPeakTimeMs - 50L)..(polarPeakTimeMs + 300L) }
                if (s3AccBottom.isNotEmpty()) {
                    s3BottomAccPeak = s3AccBottom.maxOf { it.mag }
                }
            }

            // 32-Feature extraction
            val features = extractFeaturesAtSensorNs(
                targetSensorNs = targetSensorNs,
                watchGyro = watchGyro,
                watchGrav = watchGrav,
                watchRot = watchRot,
                watchAcc = watchAcc,
                bottomGyroPeak = bottomGyroPeak ?: 0f,
                bottomAccPeak = bottomAccPeak ?: 0f,
                bottomGyroRatio = bottomGyroRatio ?: 0f,
                bottomAccRatio = bottomAccRatio ?: 0f,
                bottomTimeLeadMs = bottomTimeLeadMs ?: 0L,
                bottomSyncScore = bottomSyncScore ?: 0f,
                s1BottomGyroMag = s1BottomGyroMag,
                s1BottomDeltaZ = s1BottomDeltaZ,
                s1BottomAccMag = s1BottomAccMag,
                s2BottomAccMean = s2BottomAccMean,
                s2DynamicRatioSlope = s2DynamicRatioSlope,
                s3BottomPronationDeg = s3BottomPronationDeg,
                s3BottomGyroYMin = s3BottomGyroYMin,
                s3BottomAccPeak = s3BottomAccPeak
            )

            val predictedQuality = if (hasPolarData) {
                com.mrpeel.cricketbattingtracker.ml.GeneratedDualQualityForest.predict(features)
            } else {
                com.mrpeel.cricketbattingtracker.ml.GeneratedTopQualityForest.predict(features)
            }

            val finalSweetSpot = when (predictedQuality) {
                "good" -> "Excellent"
                "poor" -> "Poor"
                "miss" -> "Miss"
                "edge" -> "Edge"
                else -> "Good"
            }

            val accSpikeWin = watchAcc.filter { it.timeNanos in (targetSensorNs - 150_000_000L)..(targetSensorNs + 100_000_000L) }
            val accImpactNs = if (accSpikeWin.isNotEmpty()) accSpikeWin.maxByOrNull { it.mag }?.timeNanos ?: targetSensorNs else targetSensorNs
            val downswingGyroWin = watchGyro.filter { it.timeNanos in (targetSensorNs - 300_000_000L)..(targetSensorNs + 100_000_000L) }
            val maxDownswingGyro = if (downswingGyroWin.isNotEmpty()) downswingGyroWin.maxOf { it.mag } else 0.01f
            val gyroAtImpact = if (downswingGyroWin.isNotEmpty()) downswingGyroWin.minByOrNull { kotlin.math.abs(it.timeNanos - accImpactNs) }?.mag ?: maxDownswingGyro else maxDownswingGyro
            val finalEfficiency = if (maxDownswingGyro > 0.1f) kotlin.math.min(100f, (gyroAtImpact / maxDownswingGyro) * 100f) else 90f
            val finalPeakAccel = if (bottomAccPeak != null && bottomAccPeak > 0f) bottomAccPeak else (accSpikeWin.maxOfOrNull { it.mag } ?: 15f)
            val batSpeedKmh = maxDownswingGyro * 4.5f
            val bladeAndLaunch = calculateBladeAndLaunch(targetSensorNs, watchRot, finalShotType)

            finalShots.add(InningsEvent(
                inningsId = inningsId,
                timestamp = shotWallMs,
                description = "$finalShotType ($finalSweetSpot)",
                batSpeed = batSpeedKmh,
                impactForce = finalPeakAccel,
                impactTimeMs = 350L,
                shotType = finalShotType,
                efficiency = finalEfficiency,
                location = "Net Practice",
                bladeAngle = bladeAndLaunch.bladeAngle,
                bladeClass = bladeAndLaunch.bladeClass,
                launchAngle = bladeAndLaunch.launchAngle,
                launchClass = bladeAndLaunch.launchClass,
                bottom_hand_gyro_peak = bottomGyroPeak,
                bottom_hand_acc_peak = bottomAccPeak,
                bottom_hand_gyro_ratio = bottomGyroRatio,
                bottom_hand_acc_ratio = bottomAccRatio,
                bottom_hand_time_lead_ms = bottomTimeLeadMs,
                bottom_hand_sync_score = bottomSyncScore,
                swing_feature_s1_gyro_y_std = features.s1_gyro_y_std,
                swing_feature_s1_gyro_z_std = features.s1_gyro_z_std,
                swing_feature_s1_delta_x = features.s1_deltaX,
                swing_feature_s1_delta_z = features.s1_deltaZ,
                swing_feature_s2_gyro_mag = features.s2_gyroMag,
                swing_feature_s2_grav_y_mean = features.s2_grav_y_mean,
                swing_feature_s2_delta_x = features.s2_deltaX,
                swing_feature_s2_delta_z = features.s2_deltaZ,
                swing_feature_s3_roll_deg = features.s3_rollImpactDeg,
                swing_feature_s3_yaw_deg = features.s3_yawImpactDeg,
                swing_feature_s3_delta_x = features.s3_deltaX,
                swing_feature_s3_delta_z = features.s3_deltaZ,
                swing_feature_s3_plane_ratio = features.s3_planeRatio,
                swing_feature_s3_gyro_y_min = features.s3_gyro_y_min
            ))
        }

        var shotCount = 0
        var maxSpeed = 0f

        for (dbEvent in finalShots) {
            dao.insertEvent(dbEvent)
            shotCount++
            val speed = dbEvent.batSpeed ?: 0f
            if (speed > maxSpeed) {
                maxSpeed = speed
            }
        }

        // Write "Session Ended" marker
        val watchEndMs = watchAcc.last().timeNanos / 1_000_000L
        val sessionEndWallMs = watchStartWallMs + (watchEndMs - (watchStartSensorNs / 1_000_000L))
        dao.insertEvent(InningsEvent(
            inningsId = inningsId,
            timestamp = sessionEndWallMs,
            description = "Session Ended",
            location = "Net Practice"
        ))

        // Set processed flag
        val prefs = context.getSharedPreferences("pitch_analytix_prefs", Context.MODE_PRIVATE)
        prefs.edit().putBoolean("processed_innings_$inningsId", true).apply()

        Log.d(TAG, "Processed $shotCount shots. Max Speed: $maxSpeed km/h. Syncing metadata...")
        true
    }

    suspend fun processWatchOnlySession(
        inningsId: Long,
        watchDir: File,
        context: Context
    ): Boolean {
        return processSession(inningsId, watchDir, null, context)
    }

    private fun parseWatchStepsCsv(file: File): List<Long> {
        val list = mutableListOf<Long>()
        if (!file.exists()) return list
        try {
            file.forEachLine { line ->
                val parts = line.split(",")
                if (parts.size >= 2) {
                    val ts = parts[0].trim().toLongOrNull()
                    if (ts != null) {
                        list.add(ts)
                    }
                }
            }
        } catch (e: Exception) {
            Log.e(TAG, "Failed to parse steps CSV: ${e.message}")
        }
        return list
    }

    // --- Biomechanical stability and rotation math ---

    private fun extractFeaturesAtSensorNs(
        targetSensorNs: Long,
        watchGyro: List<WatchIMUSample>,
        watchGrav: List<WatchIMUSample>,
        watchRot: List<WatchRotSample>,
        watchAcc: List<WatchIMUSample> = emptyList(),
        bottomGyroPeak: Float = 0f,
        bottomAccPeak: Float = 0f,
        bottomGyroRatio: Float = 0f,
        bottomAccRatio: Float = 0f,
        bottomTimeLeadMs: Long = 0L,
        bottomSyncScore: Float = 0f,
        s1BottomGyroMag: Float = 0f,
        s1BottomDeltaZ: Float = 0f,
        s1BottomAccMag: Float = 0f,
        s2BottomAccMean: Float = 0f,
        s2DynamicRatioSlope: Float = 0f,
        s3BottomPronationDeg: Float = 0f,
        s3BottomGyroYMin: Float = 0f,
        s3BottomAccPeak: Float = 0f
    ): com.mrpeel.cricketbattingtracker.ml.SwingFeatures {
        val stanceStart = targetSensorNs - 2_500_000_000L
        val stanceEnd = targetSensorNs - 1_000_000_000L
        val stanceRots = watchRot.filter { it.timeNanos in stanceStart..stanceEnd }
        val qStance = findMostStableStance(stanceRots.ifEmpty { watchRot.take(5) }, 800_000_000L)
            ?: floatArrayOf(0f, 0f, 0f, 1f)
        val qStanceInv = FloatArray(4)
        conjugateQuat(qStance, qStanceInv)

        val tStart = targetSensorNs - 800_000_000L
        val tSplit1 = targetSensorNs - 200_000_000L
        val tSplit2 = targetSensorNs - 50_000_000L
        val tEnd = targetSensorNs + 300_000_000L

        val (s1Dx, s1Dz) = getDisplacement(watchRot, tStart, tSplit1, qStanceInv)
        val s1GyroYStd = getGyroStd(watchGyro, tStart, tSplit1, isY = true)
        val s1GyroZStd = getGyroStd(watchGyro, tStart, tSplit1, isY = false)
        // Top-hand linear acceleration in backswing (F=ma proxy for load-up force)
        val s1AccMag = watchAcc
            .filter { it.timeNanos in tStart..tSplit1 }
            .maxOfOrNull { it.mag } ?: 0f

        val (s2Dx, s2Dz) = getDisplacement(watchRot, tSplit1, tSplit2, qStanceInv)
        val s2GyroMag = getGyroPeak(watchGyro, tSplit1, tSplit2)
        val s2GravYMean = getGravityMeanY(watchGrav, tSplit1, tSplit2)

        val (s3Dx, s3Dz) = getDisplacement(watchRot, tSplit2, tEnd, qStanceInv)
        val s3PlaneRatio = if (s3Dz > 0f) s3Dx / s3Dz else 0f
        val s3GyroYMin = getGyroMinY(watchGyro, tSplit2, tEnd)
        // Top-hand linear acceleration at impact (F=ma proxy for strike force)
        val s3AccPeak = watchAcc
            .filter { it.timeNanos in tSplit2..tEnd }
            .maxOfOrNull { it.mag } ?: 0f

        val impactRot = findClosestRotation(watchRot, tSplit2)
        var s3RollImpactDeg = 0f
        var s3YawImpactDeg = 0f
        if (impactRot != null) {
            val qCurr = floatArrayOf(impactRot.qx, impactRot.qy, impactRot.qz, impactRot.qw)
            val qRel = FloatArray(4)
            val vLocal = floatArrayOf(0f, -1f, 0f)
            val vRot = FloatArray(3)
            multiplyQuats(qStanceInv, qCurr, qRel)
            rotateVector(qRel, vLocal, vRot)
            s3RollImpactDeg = calcRelativeRoll(qRel)
            s3YawImpactDeg = atan2(vRot[0], -vRot[1]) * 57.29578f
        }

        return com.mrpeel.cricketbattingtracker.ml.SwingFeatures(
            s1_gyro_y_std = s1GyroYStd,
            s1_gyro_z_std = s1GyroZStd,
            s1_deltaX = s1Dx,
            s1_deltaZ = s1Dz,
            s1_acc_mag = s1AccMag,
            s2_gyroMag = s2GyroMag,
            s2_grav_y_mean = s2GravYMean,
            s2_deltaX = s2Dx,
            s2_deltaZ = s2Dz,
            s3_rollImpactDeg = s3RollImpactDeg,
            s3_yawImpactDeg = s3YawImpactDeg,
            s3_deltaX = s3Dx,
            s3_deltaZ = s3Dz,
            s3_planeRatio = s3PlaneRatio,
            s3_gyro_y_min = s3GyroYMin,
            s3_acc_peak = s3AccPeak,
            bottom_hand_gyro_peak = bottomGyroPeak,
            bottom_hand_acc_peak = bottomAccPeak,
            bottom_hand_gyro_ratio = bottomGyroRatio,
            bottom_hand_acc_ratio = bottomAccRatio,
            bottom_hand_time_lead_ms = bottomTimeLeadMs.toFloat(),
            bottom_hand_sync_score = bottomSyncScore,
            s1_bottom_gyro_mag = s1BottomGyroMag,
            s1_bottom_deltaZ = s1BottomDeltaZ,
            s1_bottom_acc_mag = s1BottomAccMag,
            s2_bottom_acc_mean = s2BottomAccMean,
            s2_dynamic_ratio_slope = s2DynamicRatioSlope,
            s3_bottom_pronation_deg = s3BottomPronationDeg,
            s3_bottom_gyro_y_min = s3BottomGyroYMin,
            s3_bottom_acc_peak = s3BottomAccPeak
        )
    }

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

    private fun rotateVectorQuat(qx: Float, qy: Float, qz: Float, qw: Float, vx: Float, vy: Float, vz: Float): FloatArray {
        val tx = 2.0f * (qy * vz - qz * vy)
        val ty = 2.0f * (qz * vx - qx * vz)
        val tz = 2.0f * (qx * vy - qy * vx)
        val rx = vx + qw * tx + (qy * tz - qz * ty)
        val ry = vy + qw * ty + (qz * tx - qx * tz)
        val rz = vz + qw * tz + (qx * ty - qy * tx)
        return floatArrayOf(rx, ry, rz)
    }

    private fun calcRelativeRoll(q: FloatArray): Float {
        val x = q[0]; val y = q[1]; val z = q[2]; val w = q[3]
        return atan2(2.0f*(w*y + x*z), 1.0f - 2.0f*(y*y + z*z)) * 57.29578f
    }

    data class BladeAndLaunch(
        val bladeAngle: Float,
        val bladeClass: String,
        val launchAngle: Float,
        val launchClass: String
    )

    private fun calculateBladeAndLaunch(
        targetSensorNs: Long,
        watchRot: List<WatchRotSample>,
        shotType: String
    ): BladeAndLaunch {
        if (watchRot.isEmpty()) {
            return BladeAndLaunch(0f, "FULL_FACE", 0f, "FLAT")
        }

        val stanceStart = targetSensorNs - 2_500_000_000L
        val stanceEnd = targetSensorNs - 1_000_000_000L
        val stanceRots = watchRot.filter { it.timeNanos in stanceStart..stanceEnd }
        val qStance = findMostStableStance(stanceRots.ifEmpty { watchRot.take(5) }, 800_000_000L)
            ?: floatArrayOf(0f, 0f, 0f, 1f)
        val qStanceInv = FloatArray(4)
        conjugateQuat(qStance, qStanceInv)

        val impactRot = findClosestRotation(watchRot, targetSensorNs - 50_000_000L)
            ?: findClosestRotation(watchRot, targetSensorNs)
            ?: return BladeAndLaunch(0f, "FULL_FACE", 0f, "FLAT")

        val qCurr = floatArrayOf(impactRot.qx, impactRot.qy, impactRot.qz, impactRot.qw)
        val qRel = FloatArray(4)
        multiplyQuats(qStanceInv, qCurr, qRel)

        val rollImpact = calcRelativeRoll(qRel)

        val isHorizontalBat = shotType.contains("CUT", ignoreCase = true) ||
                              shotType.contains("PULL", ignoreCase = true) ||
                              shotType.contains("SWEEP", ignoreCase = true) ||
                              shotType.contains("SLOG", ignoreCase = true)

        val targetYaw = when {
            shotType.contains("COVER", ignoreCase = true) -> -45f
            shotType.contains("ON DRIVE", ignoreCase = true) -> 15f
            shotType.contains("CUT", ignoreCase = true) -> 40f
            shotType.contains("PULL", ignoreCase = true) || shotType.contains("SLOG", ignoreCase = true) -> 55f
            shotType.contains("SWEEP", ignoreCase = true) -> 65f
            shotType.contains("GLANCE", ignoreCase = true) || shotType.contains("FLICK", ignoreCase = true) -> 75f
            else -> 0f
        }

        val vFaceRel = FloatArray(3)
        val localX = floatArrayOf(1f, 0f, 0f)
        rotateVector(qRel, localX, vFaceRel)
        val yawFaceRel = atan2(vFaceRel[1], vFaceRel[0]) * 57.29578f
        var bAngle = yawFaceRel - targetYaw
        bAngle = ((bAngle + 180f) % 360f + 360f) % 360f - 180f

        val bladeClass = when {
            bAngle <= -15f -> "OPEN"
            bAngle >= 15f -> "CLOSED"
            else -> "FULL_FACE"
        }

        val launchAngle = if (isHorizontalBat) {
            rollImpact
        } else {
            val vFaceWorld = FloatArray(3)
            rotateVector(qCurr, localX, vFaceWorld)
            -asin(vFaceWorld[2].coerceIn(-1f, 1f)) * 57.29578f
        }

        val launchClass = when {
            launchAngle < -45f -> "HIGH_LOFT"
            launchAngle < -35f -> "POWER_ZONE"
            launchAngle < -15f -> "LOFTED"
            launchAngle < 0f -> "FLAT"
            else -> "INTO_GROUND"
        }

        return BladeAndLaunch(bAngle, bladeClass, launchAngle, launchClass)
    }

    // --- Parser helpers ---

    private fun getInputStream(file: File): java.io.InputStream {
        val fis = file.inputStream()
        return if (file.name.endsWith(".gz")) {
            java.util.zip.GZIPInputStream(fis)
        } else {
            fis
        }
    }

    private fun loadWatchIMU(watchDir: File, baseName: String): List<WatchIMUSample> {
        val binFile = File(watchDir, "$baseName.bin")
        if (binFile.exists()) return parseWatchIMUBin(binFile)
        val binGzFile = File(watchDir, "$baseName.bin.gz")
        if (binGzFile.exists()) return parseWatchIMUBin(binGzFile)
        
        val csvFile = File(watchDir, "$baseName.csv")
        if (csvFile.exists()) return parseWatchIMUCsv(csvFile)
        val csvGzFile = File(watchDir, "$baseName.csv.gz")
        if (csvGzFile.exists()) return parseWatchIMUCsvGz(csvGzFile)
        return emptyList()
    }

    private fun parseWatchIMUBin(file: File): List<WatchIMUSample> {
        val list = mutableListOf<WatchIMUSample>()
        if (!file.exists()) return list
        try {
            getInputStream(file).use { input ->
                val bytes = input.readBytes()
                val buffer = ByteBuffer.wrap(bytes).order(ByteOrder.LITTLE_ENDIAN)
                while (buffer.remaining() >= 24) {
                    val t = buffer.long
                    val sec = buffer.float.toDouble()
                    val x = buffer.float
                    val y = buffer.float
                    val z = buffer.float
                    val mag = sqrt(x*x + y*y + z*z)
                    list.add(WatchIMUSample(t, sec, x, y, z, mag))
                }
            }
        } catch (e: Exception) {
            Log.e(TAG, "Failed to parse IMU binary file ${file.name}: ${e.message}")
        }
        return list.sortedBy { it.timeNanos }
    }

    private fun parseWatchIMUCsvGz(file: File): List<WatchIMUSample> {
        val list = mutableListOf<WatchIMUSample>()
        try {
            java.io.BufferedReader(java.io.InputStreamReader(java.util.zip.GZIPInputStream(file.inputStream()))).use { br ->
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
        } catch (e: Exception) {
            Log.e(TAG, "Failed to parse IMU CSV.GZ file ${file.name}: ${e.message}")
        }
        return list.sortedBy { it.timeNanos }
    }

    private fun loadWatchRot(watchDir: File): List<WatchRotSample> {
        val baseNames = listOf("WatchGameOrientation", "WatchOrientation")
        for (base in baseNames) {
            val binFile = File(watchDir, "$base.bin")
            if (binFile.exists()) return parseWatchRotBin(binFile)
            val binGzFile = File(watchDir, "$base.bin.gz")
            if (binGzFile.exists()) return parseWatchRotBin(binGzFile)
            
            val csvFile = File(watchDir, "$base.csv")
            if (csvFile.exists()) return parseWatchRotCsv(csvFile)
            val csvGzFile = File(watchDir, "$base.csv.gz")
            if (csvGzFile.exists()) return parseWatchRotCsvGz(csvGzFile)
        }
        return emptyList()
    }

    private fun parseWatchRotBin(file: File): List<WatchRotSample> {
        val list = mutableListOf<WatchRotSample>()
        if (!file.exists()) return list
        try {
            getInputStream(file).use { input ->
                val bytes = input.readBytes()
                val buffer = ByteBuffer.wrap(bytes).order(ByteOrder.LITTLE_ENDIAN)
                while (buffer.remaining() >= 28) {
                    val t = buffer.long
                    val sec = buffer.float.toDouble()
                    val qx = buffer.float
                    val qy = buffer.float
                    val qz = buffer.float
                    val qw = buffer.float
                    list.add(WatchRotSample(t, sec, qx, qy, qz, qw))
                }
            }
        } catch (e: Exception) {
            Log.e(TAG, "Failed to parse rotation binary file ${file.name}: ${e.message}")
        }
        return list.sortedBy { it.timeNanos }
    }

    private fun parseWatchRotCsvGz(file: File): List<WatchRotSample> {
        val list = mutableListOf<WatchRotSample>()
        try {
            java.io.BufferedReader(java.io.InputStreamReader(java.util.zip.GZIPInputStream(file.inputStream()))).use { br ->
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
        } catch (e: Exception) {
            Log.e(TAG, "Failed to parse Rot CSV.GZ file ${file.name}: ${e.message}")
        }
        return list.sortedBy { it.timeNanos }
    }

    private fun loadWatchSteps(watchDir: File): List<Long> {
        val binFile = File(watchDir, "WatchSteps.bin")
        if (binFile.exists()) return parseWatchStepsBin(binFile)
        val binGzFile = File(watchDir, "WatchSteps.bin.gz")
        if (binGzFile.exists()) return parseWatchStepsBin(binGzFile)
        
        val csvFile = File(watchDir, "WatchSteps.csv")
        if (csvFile.exists()) return parseWatchStepsCsv(csvFile)
        val csvGzFile = File(watchDir, "WatchSteps.csv.gz")
        if (csvGzFile.exists()) return parseWatchStepsCsvGz(csvGzFile)
        return emptyList()
    }

    private fun parseWatchStepsBin(file: File): List<Long> {
        val list = mutableListOf<Long>()
        if (!file.exists()) return list
        try {
            getInputStream(file).use { input ->
                val bytes = input.readBytes()
                val buffer = ByteBuffer.wrap(bytes).order(ByteOrder.LITTLE_ENDIAN)
                while (buffer.remaining() >= 12) {
                    val t = buffer.long
                    buffer.float
                    list.add(t)
                }
            }
        } catch (e: Exception) {
            Log.e(TAG, "Failed to parse steps binary file ${file.name}: ${e.message}")
        }
        return list
    }

    private fun parseWatchStepsCsvGz(file: File): List<Long> {
        val list = mutableListOf<Long>()
        try {
            java.io.BufferedReader(java.io.InputStreamReader(java.util.zip.GZIPInputStream(file.inputStream()))).use { br ->
                var isHeader = true
                br.forEachLine { line ->
                    if (isHeader) { isHeader = false; return@forEachLine }
                    val parts = line.split(",")
                    if (parts.size >= 2) {
                        val ts = parts[0].trim().toLongOrNull()
                        if (ts != null) {
                            list.add(ts)
                        }
                    }
                }
            }
        } catch (e: Exception) {
            Log.e(TAG, "Failed to parse Steps CSV.GZ file ${file.name}: ${e.message}")
        }
        return list
    }

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

        if (file.name.endsWith(".bin") || file.name.contains(".bin")) {
            try {
                val stream = if (file.name.endsWith(".gz")) {
                    java.util.zip.GZIPInputStream(file.inputStream())
                } else {
                    file.inputStream()
                }
                stream.use { input ->
                    val bytes = ByteArray(28)
                    val buffer = ByteBuffer.wrap(bytes).order(ByteOrder.LITTLE_ENDIAN)
                    while (true) {
                        var bytesRead = 0
                        while (bytesRead < 28) {
                            val r = input.read(bytes, bytesRead, 28 - bytesRead)
                            if (r == -1) break
                            bytesRead += r
                        }
                        if (bytesRead < 28) break
                        buffer.rewind()
                        val phoneMs = buffer.long
                        val sensorNs = buffer.long
                        var x = buffer.float
                        var y = buffer.float
                        var z = buffer.float

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
                return list.sortedBy { it.phoneMs }
            } catch (e: Exception) {
                Log.e(TAG, "Failed to parse binary Polar file ${file.name}: ${e.message}, falling back to CSV parser")
            }
        }

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

    private fun parseWatchTapSequences(file: File, watchStartSensorNs: Long, watchStartWallMs: Long): List<Pair<Long, List<Long>>> {
        val list = mutableListOf<Pair<Long, List<Long>>>()
        if (!file.exists()) return list
        file.bufferedReader().use { br ->
            br.forEachLine { line ->
                if (line.startsWith("TAP_SEQ:")) {
                    try {
                        val tapNanos = mutableListOf<Long>()
                        for (i in 1..5) {
                            val tMatch = Regex("T$i=(\\d+)").find(line)
                            tMatch?.groupValues?.get(1)?.toLongOrNull()?.let { tapNanos.add(it) }
                        }
                        if (tapNanos.size == 5) {
                            val trueWallMs = watchStartWallMs + (tapNanos[4] - watchStartSensorNs) / 1_000_000L
                            list.add(Pair(trueWallMs, tapNanos))
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
        val tapThreshold = 10.0f // m/s^2 — lowered from 25.0 to reliably detect bat ground taps at the forearm/bicep
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

    private fun calculateProminence(mags: FloatArray, peakIdx: Int): Float {
        val peakVal = mags[peakIdx]
        
        // Find left boundary (first index left of peakIdx where mags[idx] > peakVal)
        var leftBoundary = 0
        for (j in peakIdx - 1 downTo 0) {
            if (mags[j] > peakVal) {
                leftBoundary = j
                break
            }
        }
        
        // Find right boundary (first index right of peakIdx where mags[idx] > peakVal)
        var rightBoundary = mags.size - 1
        for (j in peakIdx + 1 until mags.size) {
            if (mags[j] > peakVal) {
                rightBoundary = j
                break
            }
        }
        
        // Find left minimum in [leftBoundary, peakIdx]
        var leftMin = peakVal
        for (j in leftBoundary..peakIdx) {
            if (mags[j] < leftMin) {
                leftMin = mags[j]
            }
        }
        
        // Find right minimum in [peakIdx, rightBoundary]
        var rightMin = peakVal
        for (j in peakIdx..rightBoundary) {
            if (mags[j] < rightMin) {
                rightMin = mags[j]
            }
        }
        
        return peakVal - max(leftMin, rightMin)
    }

    private fun detectWatchImpactPeaks(
        samples: List<WatchIMUSample>,
        threshold: Float
    ): List<Long> {
        // Strong-gate-only path. The prominence recovery gate was removed because at the
        // session's low noise floor (gyro p50 ≈ 1.1 rad/s, p95 ≈ 5.0 rad/s) the recovery
        // path dominated candidate generation, replacing one over-count problem with another.
        // H9-tightened verifySwingBackwards does the structural filtering downstream.
        if (samples.isEmpty()) return emptyList()

        val mags = FloatArray(samples.size) { samples[it].mag }
        val candidatePeaks = mutableListOf<WatchIMUSample>()

        for (i in samples.indices) {
            val mag = mags[i]
            val prevMag = if (i > 0) mags[i - 1] else 0f
            val nextMag = if (i < samples.size - 1) mags[i + 1] else 0f
            if (mag >= prevMag && mag >= nextMag) {
                if (mag >= threshold) {
                    candidatePeaks.add(samples[i])
                }
            }
        }

        candidatePeaks.sortByDescending { it.mag }

        val peaks = mutableListOf<Long>()
        val minGapMs = 1500L
        for (p in candidatePeaks) {
            if (peaks.none { abs((p.timeNanos - it) / 1_000_000L) < minGapMs }) {
                peaks.add(p.timeNanos)
            }
        }
        return peaks.sorted()
    }

    private fun verifySwingBackwards(
        impactSensorNs: Long,
        watchGyro: List<WatchIMUSample>,
        watchRot: List<WatchRotSample>
    ): Boolean {
        // 1. Verify Backswing
        val backswingStart = impactSensorNs - 1_500_000_000L
        val backswingEnd = impactSensorNs - 150_000_000L
        val bsGyroSamples = watchGyro.filter { it.timeNanos in backswingStart..backswingEnd }
        if (bsGyroSamples.isEmpty()) return false
        val peakGyro = bsGyroSamples.maxOf { it.mag }
        if (peakGyro < 2.0f) return false  // Require meaningful backswing
        
        // 2. Verify Stance
        val stanceStart = impactSensorNs - 2_500_000_000L
        val stanceEnd = impactSensorNs - 1_000_000_000L
        val stanceRotSamples = watchRot.filter { it.timeNanos in stanceStart..stanceEnd }
        if (stanceRotSamples.size >= 5) {
            val meanQx = stanceRotSamples.map { it.qx }.average().toFloat()
            val meanQy = stanceRotSamples.map { it.qy }.average().toFloat()
            val meanQz = stanceRotSamples.map { it.qz }.average().toFloat()
            val meanQw = stanceRotSamples.map { it.qw }.average().toFloat()
            
            var devSum = 0f
            for (s in stanceRotSamples) {
                devSum += (s.qx - meanQx).pow(2) + (s.qy - meanQy).pow(2) + (s.qz - meanQz).pow(2) + (s.qw - meanQw).pow(2)
            }
            val stdDev = sqrt(devSum / stanceRotSamples.size)
            if (stdDev > 0.45f) return false  // Filter out running/fidgeting
        }
        
        return true
    }

    private fun parseSessionStartWallMs(watchDir: File): Long {
        val timelineFile = File(watchDir, "latest_timeline.txt")
        if (timelineFile.exists()) {
            try {
                var startTs: Long? = null
                timelineFile.forEachLine { line ->
                    if (startTs == null && line.startsWith("SYSTEM_START:")) {
                        val regex = Regex("Ts=(\\d+)")
                        val match = regex.find(line)
                        if (match != null) {
                            startTs = match.groupValues[1].toLongOrNull()
                        }
                    }
                }
                if (startTs != null) return startTs!!
            } catch (e: Exception) {
                Log.e(TAG, "Failed parsing latest_timeline.txt for SYSTEM_START", e)
            }
        }

        val folderName = watchDir.name
        val regex = Regex("session[-_](\\d{4})-(\\d{2})-(\\d{2})_(\\d{2})[-_](\\d{2})[-_](\\d{2})")
        val match = regex.find(folderName)
        if (match != null) {
            try {
                val (year, month, day, hour, min, sec) = match.destructured
                val cal = java.util.Calendar.getInstance()
                cal.set(year.toInt(), month.toInt() - 1, day.toInt(), hour.toInt(), min.toInt(), sec.toInt())
                cal.set(java.util.Calendar.MILLISECOND, 0)
                return cal.timeInMillis
            } catch (e: Exception) {
                Log.e(TAG, "Failed parsing timestamp from folder name: $folderName", e)
            }
        }
        return if (watchDir.lastModified() > 0) watchDir.lastModified() else System.currentTimeMillis()
    }
}
