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
        val steps = loadWatchSteps(watchDir)

        if (watchAcc.isEmpty() || watchRot.isEmpty()) {
            Log.e(TAG, "Watch raw files are missing or empty — skipping processing")
            return@withContext false
        }

        val database = AppDatabase.getDatabase(context)
        val dao = database.inningsEventDao()
        dao.deleteTimelineForInningsSync(inningsId)

        val timelineFile = File(watchDir, "latest_timeline.txt")
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
            }
        }

        // B. PASS 1: Identify Candidates from Shockwaves
        // Candidate pairs: Pair(targetSensorNs, polarPhoneMs?)
        data class CandidateShot(val targetSensorNs: Long, val polarPhoneMs: Long?)
        val candidateShots = mutableListOf<CandidateShot>()

        if (alignment != null && polarAcc.isNotEmpty()) {
            // Find impact peaks in Polar ACC
            val polarPeaks = detectImpactPeaks(polarAcc, threshold = ShotEnhancementConfig.POLAR_SHOCKWAVE_THRESHOLD)
            for (pPeak in polarPeaks) {
                val watchWallMs = alignment.polarToWatchMs(pPeak)
                val relOffsetMs = watchWallMs - watchStartWallMs
                val targetSensorNs = watchStartSensorNs + (relOffsetMs * 1_000_000L)
                candidateShots.add(CandidateShot(targetSensorNs, pPeak))
            }
        } else {
            // Find impact peaks in Watch Gyro
            val watchPeaksSensorNs = detectWatchImpactPeaks(watchGyro, threshold = ShotEnhancementConfig.WATCH_SHOCKWAVE_THRESHOLD)
            for (ns in watchPeaksSensorNs) {
                candidateShots.add(CandidateShot(ns, null))
            }
        }

        // C. Filter Pass 1 Candidates through Backward Verification & Run SwingDetector
        val confirmedPass1Shots = mutableListOf<InningsEvent>()

        for (cand in candidateShots) {
            val targetSensorNs = cand.targetSensorNs
            val polarPeakTimeMs = cand.polarPhoneMs

            // Validate backward-looking stance and swing signatures
            if (verifySwingBackwards(targetSensorNs, watchGyro, watchRot)) {
                // Feed event chunk for this window [targetSensorNs - 2.5s, targetSensorNs + 0.5s]
                val tStart = targetSensorNs - 2_500_000_000L
                val tEnd = targetSensorNs + 500_000_000L
                
                // Stream window events to SwingDetector
                val windowEvents = mutableListOf<WatchSensorEvent>()
                watchAcc.filter { it.timeNanos in tStart..tEnd }.forEach { windowEvents.add(WatchSensorEvent.Accel(it.timeNanos, floatArrayOf(it.x, it.y, it.z))) }
                watchGyro.filter { it.timeNanos in tStart..tEnd }.forEach { windowEvents.add(WatchSensorEvent.Gyro(it.timeNanos, floatArrayOf(it.x, it.y, it.z))) }
                watchGrav.filter { it.timeNanos in tStart..tEnd }.forEach { windowEvents.add(WatchSensorEvent.Gravity(it.timeNanos, floatArrayOf(it.x, it.y, it.z))) }
                watchRot.filter { it.timeNanos in tStart..tEnd }.forEach { windowEvents.add(WatchSensorEvent.Rotation(it.timeNanos, floatArrayOf(it.qx, it.qy, it.qz, it.qw))) }
                windowEvents.sortBy { it.timestampNanos }

                var detectedShot: ShotData? = null
                val tempDetector = com.mrpeel.cricketbattingtracker.ml.SwingDetector()
                tempDetector.onShotDetected = { shot ->
                    detectedShot = shot
                }
                
                windowEvents.forEach { event ->
                    when (event) {
                        is WatchSensorEvent.Accel -> tempDetector.processAccel(event.values, event.timestampNanos)
                        is WatchSensorEvent.Gyro -> tempDetector.processGyro(event.values, event.timestampNanos)
                        is WatchSensorEvent.Gravity -> tempDetector.processGravity(event.values, event.timestampNanos)
                        is WatchSensorEvent.Rotation -> tempDetector.processRotation(event.values, event.timestampNanos)
                        is WatchSensorEvent.Step -> tempDetector.processStep(event.timestampNanos)
                    }
                }

                val shot = detectedShot
                if (shot != null) {
                    var bottomGyroPeak = 0f
                    var bottomAccPeak = 0f
                    var bottomGyroRatio = 0f
                    var bottomAccRatio = 0f
                    var bottomTimeLeadMs = 0L
                    var bottomSyncScore = 0f
                    var s1BottomGyroMag = 0f
                    var s1BottomDeltaZ = 0f
                    var s2BottomAccMean = 0f
                    var s2DynamicRatioSlope = 0f
                    var s3BottomPronationDeg = 0f
                    var s3BottomGyroYMin = 0f

                    val hasPolarData = alignment != null && polarAcc.isNotEmpty() && polarGyro.isNotEmpty() && polarPeakTimeMs != null

                    // Extract Polar telemetry if available
                    if (hasPolarData && polarPeakTimeMs != null) {
                        val polarAccWin = polarAcc.filter { it.phoneMs in (polarPeakTimeMs - 1000L)..(polarPeakTimeMs + 1000L) }
                        val polarGyroWin = polarGyro.filter { it.phoneMs in (polarPeakTimeMs - 1000L)..(polarPeakTimeMs + 1000L) }

                        val pAccPeak = if (polarAccWin.isNotEmpty()) polarAccWin.maxOf { it.mag } else 0f
                        val pGyroPeak = if (polarGyroWin.isNotEmpty()) polarGyroWin.maxOf { it.mag } else 0f
                        val watchGyroPeak = getGyroPeak(watchGyro, targetSensorNs - 1_000_000_000L, targetSensorNs + 1_000_000_000L)
                        val gyroRatio = if (watchGyroPeak > 0.01f) pGyroPeak / watchGyroPeak else 0f
                        val accRatio = if (watchAcc.isNotEmpty()) {
                            val wAccPeak = watchAcc.filter { it.timeNanos in (targetSensorNs - 1_000_000_000L)..(targetSensorNs + 1_000_000_000L) }.maxOfOrNull { it.mag } ?: 1f
                            pAccPeak / wAccPeak
                        } else 0f

                        val pAccPeakTime = polarAccWin.maxByOrNull { it.mag }?.phoneMs ?: polarPeakTimeMs
                        val timeLeadMs = pAccPeakTime - polarPeakTimeMs
                        val timePenalty = min(1.0f, abs(timeLeadMs) / 500f)
                        val ratioPenalty = min(1.0f, abs(gyroRatio - 1.0f))
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
                    }

                    // 26-Feature classification
                    val features = com.mrpeel.cricketbattingtracker.ml.SwingFeatures(
                        s1_gyro_y_std       = shot.s1GyroYStd,
                        s1_gyro_z_std       = shot.s1GyroZStd,
                        s1_deltaX           = shot.s1DeltaX,
                        s1_deltaZ           = shot.s1DeltaZ,
                        s2_gyroMag          = shot.s2GyroMag,
                        s2_grav_y_mean      = shot.s2GravYMean,
                        s2_deltaX           = shot.s2DeltaX,
                        s2_deltaZ           = shot.s2DeltaZ,
                        s3_rollImpactDeg    = shot.s3RollImpactDeg,
                        s3_yawImpactDeg     = shot.s3YawImpactDeg,
                        s3_deltaX           = shot.s3DeltaX,
                        s3_deltaZ           = shot.s3DeltaZ,
                        s3_planeRatio       = shot.s3PlaneRatio,
                        s3_gyro_y_min       = shot.s3GyroYMin,
                        bottom_hand_gyro_peak   = bottomGyroPeak,
                        bottom_hand_acc_peak    = bottomAccPeak,
                        bottom_hand_gyro_ratio  = bottomGyroRatio,
                        bottom_hand_acc_ratio   = bottomAccRatio,
                        bottom_hand_time_lead_ms = bottomTimeLeadMs.toFloat(),
                        bottom_hand_sync_score  = bottomSyncScore,
                        s1_bottom_gyro_mag      = s1BottomGyroMag,
                        s1_bottom_deltaZ        = s1BottomDeltaZ,
                        s2_bottom_acc_mean      = s2BottomAccMean,
                        s2_dynamic_ratio_slope  = s2DynamicRatioSlope,
                        s3_bottom_pronation_deg = s3BottomPronationDeg,
                        s3_bottom_gyro_y_min   = s3BottomGyroYMin
                    )

                    val finalShotType = if (hasPolarData) {
                        com.mrpeel.cricketbattingtracker.ml.GeneratedDualForest.predict(features)
                    } else {
                        com.mrpeel.cricketbattingtracker.ml.GeneratedTopForest.predict(features)
                    }
                    val predictedQuality = if (hasPolarData) {
                        com.mrpeel.cricketbattingtracker.ml.GeneratedDualQualityForest.predict(features)
                    } else {
                        com.mrpeel.cricketbattingtracker.ml.GeneratedTopQualityForest.predict(features)
                    }

                    // Map RF predicted quality to UI properties
                    val finalSweetSpot = when (predictedQuality) {
                        "good" -> "Excellent"
                        "poor" -> "Poor"
                        "miss" -> "Miss"
                        "edge" -> "Edge"
                        else -> "Good"
                    }
                    val finalEfficiency = when (predictedQuality) {
                        "good" -> 90f
                        "poor" -> 60f
                        "edge" -> 40f
                        else -> 0f
                    }
                    val finalPeakAccel = if (bottomAccPeak > 0f) bottomAccPeak else shot.peakAccel

                    val relShotMs = (targetSensorNs - watchStartSensorNs) / 1_000_000L
                    val shotWallMs = watchStartWallMs + relShotMs
                    val reactionTimeMs = if (shot.impactTimeMs > 0L) shot.impactTimeMs else 350L

                    confirmedPass1Shots.add(InningsEvent(
                        inningsId = inningsId,
                        timestamp = shotWallMs,
                        description = "$finalShotType ($finalSweetSpot)",
                        batSpeed = shot.speedKmh,
                        impactForce = finalPeakAccel,
                        impactTimeMs = reactionTimeMs,
                        shotType = finalShotType,
                        efficiency = finalEfficiency,
                        backliftAngle = shot.backliftAngle,
                        followThroughAngle = shot.followThroughAngle,
                        wristRollDeg = shot.wristRollDeg,
                        bladeAngle = shot.bladeAngle,
                        bladeClass = shot.bladeClass,
                        launchAngle = shot.launchAngle,
                        launchClass = shot.launchClass,
                        location = "Net Practice",
                        bottom_hand_gyro_peak = bottomGyroPeak,
                        bottom_hand_acc_peak = bottomAccPeak,
                        bottom_hand_gyro_ratio = bottomGyroRatio,
                        bottom_hand_acc_ratio = bottomAccRatio,
                        bottom_hand_time_lead_ms = bottomTimeLeadMs,
                        bottom_hand_sync_score = bottomSyncScore,
                        swing_feature_s1_gyro_y_std = shot.s1GyroYStd,
                        swing_feature_s1_gyro_z_std = shot.s1GyroZStd,
                        swing_feature_s1_delta_x = shot.s1DeltaX,
                        swing_feature_s1_delta_z = shot.s1DeltaZ,
                        swing_feature_s2_gyro_mag = shot.s2GyroMag,
                        swing_feature_s2_grav_y_mean = shot.s2GravYMean,
                        swing_feature_s2_delta_x = shot.s2DeltaX,
                        swing_feature_s2_delta_z = shot.s2DeltaZ,
                        swing_feature_s3_roll_deg = shot.s3RollImpactDeg,
                        swing_feature_s3_yaw_deg = shot.s3YawImpactDeg,
                        swing_feature_s3_delta_x = shot.s3DeltaX,
                        swing_feature_s3_delta_z = shot.s3DeltaZ,
                        swing_feature_s3_plane_ratio = shot.s3PlaneRatio,
                        swing_feature_s3_gyro_y_min = shot.s3GyroYMin
                    ))
                }
            }
        }

        // D. PASS 2: Find gaps and run state machine for Misses
        val confirmedPass2Shots = mutableListOf<InningsEvent>()
        
        // Combine all watch events for fallback pass
        val allEvents = mutableListOf<WatchSensorEvent>()
        watchAcc.forEach { allEvents.add(WatchSensorEvent.Accel(it.timeNanos, floatArrayOf(it.x, it.y, it.z))) }
        watchGyro.forEach { allEvents.add(WatchSensorEvent.Gyro(it.timeNanos, floatArrayOf(it.x, it.y, it.z))) }
        watchGrav.forEach { allEvents.add(WatchSensorEvent.Gravity(it.timeNanos, floatArrayOf(it.x, it.y, it.z))) }
        watchRot.forEach { allEvents.add(WatchSensorEvent.Rotation(it.timeNanos, floatArrayOf(it.qx, it.qy, it.qz, it.qw))) }
        steps.forEach { allEvents.add(WatchSensorEvent.Step(it)) }
        allEvents.sortBy { it.timestampNanos }

        // Find shots using standard forward state machine run
        val forwardDetector = com.mrpeel.cricketbattingtracker.ml.SwingDetector()
        val forwardShots = mutableListOf<ShotData>()
        forwardDetector.onShotDetected = { shot ->
            forwardShots.add(shot)
        }
        allEvents.forEach { event ->
            when (event) {
                is WatchSensorEvent.Accel -> forwardDetector.processAccel(event.values, event.timestampNanos)
                is WatchSensorEvent.Gyro -> forwardDetector.processGyro(event.values, event.timestampNanos)
                is WatchSensorEvent.Gravity -> forwardDetector.processGravity(event.values, event.timestampNanos)
                is WatchSensorEvent.Rotation -> forwardDetector.processRotation(event.values, event.timestampNanos)
                is WatchSensorEvent.Step -> forwardDetector.processStep(event.timestampNanos)
            }
        }

        for (fShot in forwardShots) {
            val relativePass2Ms = fShot.impactTimeMs
            // Only add if it's not close to any Pass 1 shot (min gap of 2 seconds)
            val isOverlap = confirmedPass1Shots.any { Math.abs((it.timestamp - watchStartWallMs) - relativePass2Ms) < 2000L }
            if (!isOverlap) {
                val fShotWallMs = watchStartWallMs + relativePass2Ms
                confirmedPass2Shots.add(InningsEvent(
                    inningsId = inningsId,
                    timestamp = fShotWallMs,
                    description = "${fShot.shotType} (Miss)",
                    batSpeed = fShot.speedKmh,
                    impactForce = fShot.peakAccel,
                    impactTimeMs = fShot.impactTimeMs,
                    shotType = fShot.shotType,
                    efficiency = 0f,
                    backliftAngle = fShot.backliftAngle,
                    followThroughAngle = fShot.followThroughAngle,
                    wristRollDeg = fShot.wristRollDeg,
                    bladeAngle = fShot.bladeAngle,
                    bladeClass = fShot.bladeClass,
                    launchAngle = fShot.launchAngle,
                    launchClass = fShot.launchClass,
                    location = "Net Practice",
                    swing_feature_s1_gyro_y_std = fShot.s1GyroYStd,
                    swing_feature_s1_gyro_z_std = fShot.s1GyroZStd,
                    swing_feature_s1_delta_x = fShot.s1DeltaX,
                    swing_feature_s1_delta_z = fShot.s1DeltaZ,
                    swing_feature_s2_gyro_mag = fShot.s2GyroMag,
                    swing_feature_s2_grav_y_mean = fShot.s2GravYMean,
                    swing_feature_s2_delta_x = fShot.s2DeltaX,
                    swing_feature_s2_delta_z = fShot.s2DeltaZ,
                    swing_feature_s3_roll_deg = fShot.s3RollImpactDeg,
                    swing_feature_s3_yaw_deg = fShot.s3YawImpactDeg,
                    swing_feature_s3_delta_x = fShot.s3DeltaX,
                    swing_feature_s3_delta_z = fShot.s3DeltaZ,
                    swing_feature_s3_plane_ratio = fShot.s3PlaneRatio,
                    swing_feature_s3_gyro_y_min = fShot.s3GyroYMin
                ))
            }
        }

        // E. Combine all shots, sort chronologically, and apply NMS (Non-Maximum Suppression) with 5.0s window
        val allCandidates = (confirmedPass1Shots + confirmedPass2Shots).sortedBy { it.timestamp }
        val finalShots = mutableListOf<InningsEvent>()
        
        for (cand in allCandidates) {
            val dupIdx = finalShots.indexOfFirst { Math.abs(it.timestamp - cand.timestamp) < 5000L }
            if (dupIdx != -1) {
                val existing = finalShots[dupIdx]
                val existingSpeed = existing.batSpeed ?: 0f
                val candSpeed = cand.batSpeed ?: 0f
                if (candSpeed > existingSpeed) {
                    finalShots[dupIdx] = cand
                }
            } else {
                finalShots.add(cand)
            }
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
                    val sec = buffer.float
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
                return list.sortedBy { it.sensorNs }
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
                
                // Enforce clock offset constraint (taps must be within 3.0s of each other)
                val diff = polarSeq[4].toDouble() - watchAnchorMs.toDouble()
                if (abs(diff) > 3000.0) continue
                
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

    private fun detectWatchImpactPeaks(samples: List<WatchIMUSample>, threshold: Float): List<Long> {
        if (samples.isEmpty()) return emptyList()
        
        val mags = FloatArray(samples.size) { samples[it].mag }
        val candidatePeaks = mutableListOf<WatchIMUSample>()
        
        // 1. Find local maxima peaks
        for (i in samples.indices) {
            val mag = mags[i]
            val prevMag = if (i > 0) mags[i - 1] else 0f
            val nextMag = if (i < samples.size - 1) mags[i + 1] else 0f
            
            if (mag >= prevMag && mag >= nextMag) {
                // local maximum candidate
                val isStage1 = mag >= threshold
                val isStage2 = mag >= 0.75f && calculateProminence(mags, i) >= 0.5f
                
                if (isStage1 || isStage2) {
                    candidatePeaks.add(samples[i])
                }
            }
        }
        
        // 2. Sort candidate peaks by magnitude descending to prioritize larger spikes
        candidatePeaks.sortByDescending { it.mag }
        
        val peaks = mutableListOf<Long>()
        val minGapMs = 1500L
        
        // 3. Enforce min spacing (distance) constraint
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
        if (peakGyro < 4.0f) return false
        
        // 2. Verify Stance
        val stanceStart = impactSensorNs - 2_500_000_000L
        val stanceEnd = impactSensorNs - 1_000_000_000L
        val stanceRotSamples = watchRot.filter { it.timeNanos in stanceStart..stanceEnd }
        if (stanceRotSamples.size < 5) return false
        
        val meanQx = stanceRotSamples.map { it.qx }.average().toFloat()
        val meanQy = stanceRotSamples.map { it.qy }.average().toFloat()
        val meanQz = stanceRotSamples.map { it.qz }.average().toFloat()
        val meanQw = stanceRotSamples.map { it.qw }.average().toFloat()
        
        var devSum = 0f
        for (s in stanceRotSamples) {
            devSum += (s.qx - meanQx).pow(2) + (s.qy - meanQy).pow(2) + (s.qz - meanQz).pow(2) + (s.qw - meanQw).pow(2)
        }
        val stdDev = sqrt(devSum / stanceRotSamples.size)
        if (stdDev > 0.12f) return false
        
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
