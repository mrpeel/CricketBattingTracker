package com.mrpeel.cricketbattingtracker.ml

import org.junit.Assert.*
import org.junit.Test
import com.mrpeel.cricketbattingtracker.services.ShotData
import java.io.File
import kotlin.math.abs

class SwingDetectorGroundTruthTest {

    private val baseDir = File("/Users/neilkloot/Code/Batting Sensor Stats")
    val unifiedFile = File(baseDir, "analysis_outputs/unified_labeled_shots.csv")
    val speedFile = File(baseDir, "analysis_outputs/ground_truth_labeled_shots.csv")

    data class SessionConfig(
        val id: String,
        val canonicalName: String,
        val relativePath: String,
        val wristFolder: String,
        val transcriptFile: String,
        val expectWatchData: Boolean
    )

    val sessions = listOf(
        SessionConfig(
            id = "pull_shots",
            canonicalName = "Pull shots",
            relativePath = "2026_05_02/Pull shots",
            wristFolder = "Wrist_pull_shots-2026-05-02_02-15-11",
            transcriptFile = "pull_shots_full_transcript.csv",
            expectWatchData = true
        ),
        SessionConfig(
            id = "cover_drives",
            canonicalName = "Cover drives",
            relativePath = "2026_05_02/Cover drives ",
            wristFolder = "Wrist_cover_drives-2026-05-02_02-40-41",
            transcriptFile = "cover_drives_transcript.csv",
            expectWatchData = true
        ),
        SessionConfig(
            id = "on_drives",
            canonicalName = "On drives and flick shots",
            relativePath = "2026_05_02/On drives and flick shots",
            wristFolder = "Wrist_on_drives_and_flick_shots-2026-05-02_02-30-57",
            transcriptFile = "on_drives_flick_shots_full_transcript.csv",
            expectWatchData = true
        ),
        SessionConfig(
            id = "short_off_side",
            canonicalName = "Short off side",
            relativePath = "2026_05_02/Short off side",
            wristFolder = "Wrist_short_off_side-2026-05-02_02-50-26",
            transcriptFile = "short_offside_full_transcript.csv",
            expectWatchData = false
        ),
        SessionConfig(
            id = "full_toss",
            canonicalName = "full_toss",
            relativePath = "2026_05_10/full_toss",
            wristFolder = "Wrist_-_full_toss-2026-05-10_05-28-06",
            transcriptFile = "full_toss_practice_transcript.csv",
            expectWatchData = true
        ),
        SessionConfig(
            id = "full_length",
            canonicalName = "full_length",
            relativePath = "2026_05_10/full_length",
            wristFolder = "Wrist_-_full_length_middle_stump-2026-05-10_05-37-44",
            transcriptFile = "full_length_middle_stump_transcript.csv",
            expectWatchData = false
        ),
        SessionConfig(
            id = "session_20260530",
            canonicalName = "live_session_20260530",
            relativePath = "live_watch_sessions/session-2026-05-30_15-04-41",
            wristFolder = "",
            transcriptFile = "ground_truth_aligned.csv",
            expectWatchData = true
        ),
        SessionConfig(
            id = "session_20260531_10",
            canonicalName = "live_session_20260531_10",
            relativePath = "live_watch_sessions/session-2026-05-31_10-06-52",
            wristFolder = "",
            transcriptFile = "ground_truth_aligned.csv",
            expectWatchData = true
        ),
        SessionConfig(
            id = "session_20260531_14",
            canonicalName = "live_session_20260531_14",
            relativePath = "live_watch_sessions/session-2026-05-31_14-12-10",
            wristFolder = "",
            transcriptFile = "ground_truth_aligned.csv",
            expectWatchData = true
        ),
        SessionConfig(
            id = "session_20260601",
            canonicalName = "live_session_20260601",
            relativePath = "live_watch_sessions/session-2026-06-01_12-23-38",
            wristFolder = "",
            transcriptFile = "ground_truth_aligned.csv",
            expectWatchData = true
        ),
        SessionConfig(
            id = "session_20260605",
            canonicalName = "live_session_20260605",
            relativePath = "live_watch_sessions/session-2026-06-05_12-29-59",
            wristFolder = "",
            transcriptFile = "ground_truth_aligned.csv",
            expectWatchData = true
        ),
        SessionConfig(
            id = "session_20260607",
            canonicalName = "live_session_20260607",
            relativePath = "live_watch_sessions/session-2026-06-07_14-34-24",
            wristFolder = "",
            transcriptFile = "ground_truth_aligned.csv",
            expectWatchData = true
        )
    )

    data class GroundTruthShot(
        val session: String,
        val shotType: String,
        val wristTimestamp: Float, // seconds_elapsed in the session
        val narration: String,
        val batHit: Boolean,
        val batTrueSpeedKmh: Float?
    )

    data class SensorEvent(
        val type: Int, // 1: accel, 2: gyro, 3: gravity
        val timestamp: Long,
        val secondsElapsed: Float,
        val values: FloatArray
    ) : Comparable<SensorEvent> {
        override fun compareTo(other: SensorEvent): Int {
            return this.timestamp.compareTo(other.timestamp)
        }
    }

    data class MatchResult(
        val gtShot: GroundTruthShot,
        val detectedShot: ShotData,
        val timeDiff: Float,
        val speedError: Float?,
        val isTypeMatch: Boolean,
        val isHitMatch: Boolean
    )

    data class SessionResult(
        val config: SessionConfig,
        val gtCount: Int,
        val detectedCount: Int,
        val tp: Int,
        val fp: Int,
        val fn: Int,
        val precision: Float,
        val recall: Float,
        val f1: Float,
        val classificationAccuracy: Float,
        val hitMissAgreement: Float,
        val maeSpeed: Float?,
        val matches: List<MatchResult>
    )

    @Test
    fun testSwingDetectorPerformanceAgainstGroundTruth() {
        val results = mutableListOf<SessionResult>()

        for (config in sessions) {
            println("=== Processing Session: ${config.canonicalName} ===")
            
            // 1. Resolve sensor files
            val sessionDir = if (config.relativePath.startsWith("live_watch_sessions")) {
                File(baseDir, config.relativePath)
            } else {
                File(baseDir, "old_session_data/${config.relativePath}")
            }
            val wristDir = if (config.wristFolder.isEmpty()) sessionDir else File(sessionDir, config.wristFolder)
            
            val accelFile = File(wristDir, "WatchAccelerometer.csv").takeIf { it.exists() } ?: File(wristDir, "Accelerometer.csv")
            val gyroFile = File(wristDir, "WatchGyroscope.csv").takeIf { it.exists() } ?: File(wristDir, "Gyroscope.csv")
            val gravFile = File(wristDir, "WatchGravity.csv").takeIf { it.exists() } ?: File(wristDir, "Gravity.csv")
            val orientFile = File(wristDir, "WatchGameOrientation.csv").takeIf { it.exists() } ?: File(wristDir, "WatchOrientation.csv").takeIf { it.exists() } ?: File(wristDir, "Orientation.csv")

            println("Sensor files: ")
            println("  Accel:  ${accelFile.absolutePath}")
            println("  Gyro:   ${gyroFile.absolutePath}")
            println("  Grav:   ${gravFile.absolutePath}")
            println("  Orient: ${orientFile.absolutePath}")

            // 2. Load ground truth shots for this session
            val transcriptFile = File(sessionDir, config.transcriptFile)
            val gtLoader = GroundTruthLoader(unifiedFile, speedFile, transcriptFile, config.canonicalName)
            val gtShots = gtLoader.load()
            println("Loaded ${gtShots.size} ground truth shots from unified list & transcript.")

            // 3. Load and sort sensor events
            val events = mutableListOf<SensorEvent>()
            events.addAll(SensorCsvReader(accelFile, 1).readEvents())
            events.addAll(SensorCsvReader(gyroFile, 2).readEvents())
            events.addAll(SensorCsvReader(gravFile, 3).readEvents())
            events.addAll(SensorCsvReader(orientFile, 4).readEvents())
            events.sort()
            println("Sorted ${events.size} raw sensor events.")

            // 4. Stream into SwingDetector
            val detector = SwingDetector()
            val detectedShots = mutableListOf<Pair<ShotData, Float>>()
            var currentSecondsElapsed = 0f

            detector.onShotDetected = { shot ->
                detectedShots.add(Pair(shot, currentSecondsElapsed))
            }

            for (event in events) {
                currentSecondsElapsed = event.secondsElapsed
                when (event.type) {
                    1 -> detector.processAccel(event.values, event.timestamp)
                    2 -> detector.processGyro(event.values, event.timestamp)
                    3 -> detector.processGravity(event.values, event.timestamp)
                    4 -> detector.processRotation(event.values, event.timestamp)
                }
            }
            println("Detector identified ${detectedShots.size} shots.")

            // 5. Align and calculate metrics
            val matchedGt = mutableSetOf<Int>()
            val matchedDet = mutableSetOf<Int>()
            val matches = mutableListOf<MatchResult>()

            for (gtIdx in gtShots.indices) {
                val gtShot = gtShots[gtIdx]
                var bestDetIdx = -1
                var bestTimeDiff = Float.MAX_VALUE

                for (detIdx in detectedShots.indices) {
                    if (detIdx in matchedDet) continue
                    val (detShot, detSecondsElapsed) = detectedShots[detIdx]
                    
                    // Estimate impact time by subtracting 0.75s contact window lag
                    val detectedImpactTime = detSecondsElapsed - 0.75f
                    val diff = abs(detectedImpactTime - gtShot.wristTimestamp)

                    if (diff <= 2.0f && diff < bestTimeDiff) {
                        bestTimeDiff = diff
                        bestDetIdx = detIdx
                    }
                }

                if (bestDetIdx != -1) {
                    matchedGt.add(gtIdx)
                    matchedDet.add(bestDetIdx)
                    val (detShot, detSecondsElapsed) = detectedShots[bestDetIdx]

                    val speedError = if (gtShot.batTrueSpeedKmh != null) {
                        abs(detShot.speedKmh - gtShot.batTrueSpeedKmh)
                    } else {
                        null
                    }

                    val typeMatch = shotTypesMatch(gtShot.shotType, detShot.shotType)
                    val hitMatch = (gtShot.batHit == detShot.isHit)

                    matches.add(MatchResult(
                        gtShot = gtShot,
                        detectedShot = detShot,
                        timeDiff = bestTimeDiff,
                        speedError = speedError,
                        isTypeMatch = typeMatch,
                        isHitMatch = hitMatch
                    ))
                }
            }

            val tp = matches.size
            val fn = gtShots.size - tp
            val fp = detectedShots.size - tp

            val precision = if (tp + fp > 0) tp.toFloat() / (tp + fp) else 0f
            val recall = if (tp + fn > 0) tp.toFloat() / (tp + fn) else 0f
            val f1 = if (precision + recall > 0) 2 * (precision * recall) / (precision + recall) else 0f

            val classifiableMatches = matches.filter {
                val gtClean = it.gtShot.shotType.trim().uppercase()
                gtClean != "UNKNOWN" && gtClean != "MISS"
            }
            val classificationAccuracy = if (classifiableMatches.isNotEmpty()) {
                classifiableMatches.count { it.isTypeMatch }.toFloat() / classifiableMatches.size
            } else {
                0f
            }

            val hitMissAgreement = if (tp > 0) {
                matches.count { it.isHitMatch }.toFloat() / tp
            } else {
                0f
            }

            val validSpeedErrors = matches.mapNotNull { it.speedError }
            val maeSpeed = if (validSpeedErrors.isNotEmpty()) {
                validSpeedErrors.average().toFloat()
            } else {
                null
            }

            val result = SessionResult(
                config = config,
                gtCount = gtShots.size,
                detectedCount = detectedShots.size,
                tp = tp,
                fp = fp,
                fn = fn,
                precision = precision,
                recall = recall,
                f1 = f1,
                classificationAccuracy = classificationAccuracy,
                hitMissAgreement = hitMissAgreement,
                maeSpeed = maeSpeed,
                matches = matches
            )
            results.add(result)

            println("Precision: %.2f | Recall: %.2f | F1: %.2f".format(precision, recall, f1))
            println("Classification Accuracy: %.2f | Hit/Miss Agreement: %.2f".format(classificationAccuracy, hitMissAgreement))
            if (maeSpeed != null) {
                println("Speed MAE: %.2f km/h".format(maeSpeed))
            } else {
                println("Speed MAE: N/A")
            }
            println("==========================================\n")
        }

        // 6. Write Markdown Report
        writeScorecardReport(results)
    }

    private fun writeScorecardReport(results: List<SessionResult>) {
        val reportFile = File("/Users/neilkloot/.gemini/antigravity/brain/2b0e7b71-5668-46cd-a61d-48994a7fdd70/swing_detector_scorecard.md")
        val sb = StringBuilder()

        sb.append("# SwingDetector Performance Scorecard\n\n")
        sb.append("This document summarizes the chronological performance evaluation of the Kotlin `SwingDetector` state machine against ground truth cricket batting sessions.\n\n")

        sb.append("## Overview Table\n\n")
        sb.append("| Session | Ground Truth (GT) | Detected | True Positives (TP) | False Positives (FP) | False Negatives (FN) | Precision | Recall | F1 Score | Classification Accuracy | Hit/Miss Agreement | Speed MAE (km/h) |\n")
        sb.append("|---|---|---|---|---|---|---|---|---|---|---|---|\n")

        for (r in results) {
            val speedMaeStr = r.maeSpeed?.let { "%.2f".format(it) } ?: "N/A"
            sb.append("| %s | %d | %d | %d | %d | %d | %.2f | %.2f | %.2f | %.2f | %.2f | %s |\n".format(
                r.config.canonicalName, r.gtCount, r.detectedCount, r.tp, r.fp, r.fn, r.precision, r.recall, r.f1, r.classificationAccuracy, r.hitMissAgreement, speedMaeStr
            ))
        }

        sb.append("\n## Detailed Session Logs\n\n")

        for (r in results) {
            sb.append("### Session: ${r.config.canonicalName}\n\n")
            sb.append("- **Active Watch Data**: ${if (r.config.expectWatchData) "Yes" else "No (Stationary phone sensor fallback, expected 0% recall)"}\n")
            sb.append("- **Precision**: %.2f\n".format(r.precision))
            sb.append("- **Recall**: %.2f\n".format(r.recall))
            sb.append("- **F1-Score**: %.2f\n".format(r.f1))
            sb.append("- **Shot Classification Accuracy**: %.2f\n".format(r.classificationAccuracy))
            sb.append("- **Hit/Miss Detection Agreement**: %.2f\n".format(r.hitMissAgreement))
            sb.append("- **Speed MAE**: ${r.maeSpeed?.let { "%.2f km/h".format(it) } ?: "N/A"}\n\n")

            if (r.matches.isNotEmpty()) {
                sb.append("#### Match Breakdown\n\n")
                sb.append("| GT Index | GT Timestamp | GT Shot Type | Detected Shot Type | Match? | GT Hit | Detected Hit | Match? | GT Speed (km/h) | Detected Speed (km/h) | Error (km/h) |\n")
                sb.append("|---|---|---|---|---|---|---|---|---|---|---|\n")
                for (idx in r.matches.indices) {
                    val m = r.matches[idx]
                    val gtSpeedStr = m.gtShot.batTrueSpeedKmh?.let { "%.2f".format(it) } ?: "N/A"
                    val errorStr = m.speedError?.let { "%.2f".format(it) } ?: "N/A"
                    sb.append("| %d | %.2f | %s | %s | %s | %s | %s | %s | %s | %.2f | %s |\n".format(
                        idx + 1,
                        m.gtShot.wristTimestamp,
                        m.gtShot.shotType,
                        m.detectedShot.shotType,
                        if (m.isTypeMatch) "✅" else "❌",
                        if (m.gtShot.batHit) "Hit" else "Miss",
                        if (m.detectedShot.isHit) "Hit" else "Miss",
                        if (m.isHitMatch) "✅" else "❌",
                        gtSpeedStr,
                        m.detectedShot.speedKmh,
                        errorStr
                    ))
                }
            } else {
                sb.append("*No matches detected for this session.*\n")
            }
            sb.append("\n---\n\n")
        }

        reportFile.writeText(sb.toString())
        println("Performance scorecard written to: file://${reportFile.absolutePath}")
    }

    private fun parseCsvLine(line: String): List<String> {
        val result = mutableListOf<String>()
        val currentToken = StringBuilder()
        var inQuotes = false
        var i = 0
        while (i < line.length) {
            val c = line[i]
            if (c == '"') {
                if (inQuotes && i + 1 < line.length && line[i + 1] == '"') {
                    currentToken.append('"')
                    i += 2
                    continue
                }
                inQuotes = !inQuotes
                i++
            } else if (c == ',' && !inQuotes) {
                result.add(currentToken.toString().trim())
                currentToken.setLength(0)
                i++
            } else {
                currentToken.append(c)
                i++
            }
        }
        result.add(currentToken.toString().trim())
        return result
    }

    private fun shotTypesMatch(gt: String, detected: String): Boolean {
        val gtClean = gt.trim().uppercase()
        val detClean = detected.trim().uppercase()

        return when (detClean) {
            "DRIVE/DEFENCE" -> gtClean.contains("DRIVE") || gtClean.contains("DEFENCE") || gtClean.contains("DEFENSE") || gtClean.contains("PUSH") || gtClean.contains("BLOCK")
            "GLANCE/FLICK" -> gtClean.contains("FLICK") || gtClean.contains("GLANCE") || gtClean.contains("SWEEP")
            "CUT/PUNCH" -> gtClean.contains("CUT") || gtClean.contains("PUNCH")
            "PULL/HOOK" -> gtClean.contains("PULL") || gtClean.contains("HOOK")
            "DEFLECTION/GUIDE" -> gtClean.contains("GUIDE") || gtClean.contains("STEER") || gtClean.contains("GLIDE") || gtClean.contains("LATE CUT") || gtClean.contains("UPPER CUT")
            "POWER SHOT" -> gtClean.contains("POWER") || gtClean.contains("SLOG") || gtClean.contains("LOFT")
            else -> false
        }
    }

    class SensorCsvReader(val file: File, val type: Int) {
        fun readEvents(): List<SensorEvent> {
            val lines = file.readLines()
            if (lines.isEmpty()) return emptyList()
            val header = parseCsvLine(lines[0])
            val timeIdx = header.indexOfFirst { it.equals("time", ignoreCase = true) }
            val secondsElapsedIdx = header.indexOfFirst { it.equals("seconds_elapsed", ignoreCase = true) || it.equals("secondsElapsed", ignoreCase = true) }

            if (type == 4) {
                val qxIdx = header.indexOfFirst { it.equals("qx", ignoreCase = true) }
                val qyIdx = header.indexOfFirst { it.equals("qy", ignoreCase = true) }
                val qzIdx = header.indexOfFirst { it.equals("qz", ignoreCase = true) }
                val qwIdx = header.indexOfFirst { it.equals("qw", ignoreCase = true) }

                if (qxIdx == -1 || qyIdx == -1 || qzIdx == -1 || qwIdx == -1) {
                    throw IllegalArgumentException("Missing required orientation columns in ${file.name}: header is $header")
                }

                val events = ArrayList<SensorEvent>(lines.size - 1)
                for (i in 1 until lines.size) {
                    val line = lines[i]
                    if (line.isBlank()) continue
                    val parts = parseCsvLine(line)
                    if (parts.size <= maxOf(timeIdx, secondsElapsedIdx, qxIdx, qyIdx, qzIdx, qwIdx)) continue
                    try {
                        val time = if (timeIdx != -1 && parts[timeIdx].isNotBlank()) {
                            parts[timeIdx].toLong()
                        } else {
                            (parts[secondsElapsedIdx].toDouble() * 1_000_000_000.0).toLong()
                        }
                        val secondsElapsed = if (secondsElapsedIdx != -1) parts[secondsElapsedIdx].toFloat() else 0f
                        val qx = parts[qxIdx].toFloat()
                        val qy = parts[qyIdx].toFloat()
                        val qz = parts[qzIdx].toFloat()
                        val qw = parts[qwIdx].toFloat()
                        events.add(SensorEvent(type, time, secondsElapsed, floatArrayOf(qx, qy, qz, qw)))
                    } catch (e: Exception) {
                        // Ignore malformed rows
                    }
                }
                return events
            } else {
                val xIdx = header.indexOfFirst { it.equals("x", ignoreCase = true) }
                val yIdx = header.indexOfFirst { it.equals("y", ignoreCase = true) }
                val zIdx = header.indexOfFirst { it.equals("z", ignoreCase = true) }

                if (timeIdx == -1 || xIdx == -1 || yIdx == -1 || zIdx == -1) {
                    throw IllegalArgumentException("Missing required columns in ${file.name}: header is $header")
                }

                val events = ArrayList<SensorEvent>(lines.size - 1)
                for (i in 1 until lines.size) {
                    val line = lines[i]
                    if (line.isBlank()) continue
                    val parts = parseCsvLine(line)
                    if (parts.size <= maxOf(timeIdx, secondsElapsedIdx, xIdx, yIdx, zIdx)) continue
                    try {
                        val time = parts[timeIdx].toLong()
                        val secondsElapsed = if (secondsElapsedIdx != -1) parts[secondsElapsedIdx].toFloat() else 0f
                        val x = parts[xIdx].toFloat()
                        val y = parts[yIdx].toFloat()
                        val z = parts[zIdx].toFloat()
                        events.add(SensorEvent(type, time, secondsElapsed, floatArrayOf(x, y, z)))
                    } catch (e: Exception) {
                        // Ignore malformed rows
                    }
                }
                return events
            }
        }

        private fun parseCsvLine(line: String): List<String> {
            val result = mutableListOf<String>()
            val currentToken = StringBuilder()
            var inQuotes = false
            var i = 0
            while (i < line.length) {
                val c = line[i]
                if (c == '"') {
                    if (inQuotes && i + 1 < line.length && line[i + 1] == '"') {
                        currentToken.append('"')
                        i += 2
                        continue
                    }
                    inQuotes = !inQuotes
                    i++
                } else if (c == ',' && !inQuotes) {
                    result.add(currentToken.toString().trim())
                    currentToken.setLength(0)
                    i++
                } else {
                    currentToken.append(c)
                    i++
                }
            }
            result.add(currentToken.toString().trim())
            return result
        }
    }

    class GroundTruthLoader(
        val unifiedFile: File,
        val speedFile: File,
        val transcriptFile: File,
        val sessionCanonicalName: String
    ) {
        fun load(): List<GroundTruthShot> {
            val speedMap = parseGroundTruthSpeeds(speedFile)
            val transcriptMap = parseTranscriptHitMap(transcriptFile)

            val speedUsage = mutableMapOf<String, Int>()
            val transcriptUsage = mutableMapOf<String, Int>()

            val shots = mutableListOf<GroundTruthShot>()

            if (sessionCanonicalName.startsWith("live_session_") || sessionCanonicalName == "session_20260529") {
                val lines = transcriptFile.readLines()
                if (lines.isEmpty()) return shots
                val header = parseCsvLine(lines[0])
                val typeIdx = header.indexOfFirst { it.equals("shot_type", ignoreCase = true) }
                val timeIdx = header.indexOfFirst { it.equals("impact_time_seconds", ignoreCase = true) }
                val narrationIdx = header.indexOfFirst { it.equals("narrated_text", ignoreCase = true) }
                
                for (i in 1 until lines.size) {
                    val line = lines[i]
                    if (line.isBlank()) continue
                    val parts = parseCsvLine(line)
                    if (parts.size <= maxOf(typeIdx, timeIdx, narrationIdx)) continue
                    val shotType = parts[typeIdx].trim()
                    val timestamp = parts[timeIdx].toFloatOrNull() ?: 0f
                    val narration = parts[narrationIdx].trim()
                    
                    val isHit = !narration.lowercase().contains("miss")
                    
                    shots.add(GroundTruthShot(
                        session = sessionCanonicalName,
                        shotType = shotType,
                        wristTimestamp = timestamp,
                        narration = narration,
                        batHit = isHit,
                        batTrueSpeedKmh = null
                    ))
                }
                return shots
            }

            val lines = unifiedFile.readLines()
            if (lines.isEmpty()) return shots

            val header = parseCsvLine(lines[0])
            val sessionIdx = header.indexOfFirst { it.equals("session", ignoreCase = true) }
            val shotTypeIdx = header.indexOfFirst { it.equals("shot_type", ignoreCase = true) }
            val timeIdx = header.indexOfFirst { it.equals("wrist_timestamp", ignoreCase = true) }
            val narrationIdx = header.indexOfFirst { it.equals("narration", ignoreCase = true) }

            for (i in 1 until lines.size) {
                val line = lines[i]
                if (line.isBlank()) continue
                val parts = parseCsvLine(line)
                if (parts.size <= maxOf(sessionIdx, shotTypeIdx, timeIdx, narrationIdx)) continue

                val sessionName = parts[sessionIdx].trim()
                if (!sessionName.equals(sessionCanonicalName, ignoreCase = true)) continue

                val shotType = parts[shotTypeIdx].trim()
                val timestamp = parts[timeIdx].toFloatOrNull() ?: 0f
                val narration = parts[narrationIdx].trim()

                // Look up hit status
                val narrationKey = narration.lowercase()
                val hits = transcriptMap[narrationKey]
                val usageIdx = transcriptUsage.getOrDefault(narrationKey, 0)
                val isHit = if (hits != null && usageIdx < hits.size) {
                    transcriptUsage[narrationKey] = usageIdx + 1
                    hits[usageIdx]
                } else {
                    true
                }

                // Look up speed
                val speedKey = "${sessionCanonicalName.lowercase().trim()}|${narration.lowercase()}"
                val speeds = speedMap[speedKey]
                val sUsageIdx = speedUsage.getOrDefault(speedKey, 0)
                val trueSpeed = if (speeds != null && sUsageIdx < speeds.size) {
                    speedUsage[speedKey] = sUsageIdx + 1
                    speeds[sUsageIdx]
                } else {
                    null
                }

                shots.add(GroundTruthShot(
                    session = sessionCanonicalName,
                    shotType = shotType,
                    wristTimestamp = timestamp,
                    narration = narration,
                    batHit = isHit,
                    batTrueSpeedKmh = trueSpeed
                ))
            }
            return shots
        }

        private fun parseCsvLine(line: String): List<String> {
            val result = mutableListOf<String>()
            val currentToken = StringBuilder()
            var inQuotes = false
            var i = 0
            while (i < line.length) {
                val c = line[i]
                if (c == '"') {
                    if (inQuotes && i + 1 < line.length && line[i + 1] == '"') {
                        currentToken.append('"')
                        i += 2
                        continue
                    }
                    inQuotes = !inQuotes
                    i++
                } else if (c == ',' && !inQuotes) {
                    result.add(currentToken.toString().trim())
                    currentToken.setLength(0)
                    i++
                } else {
                    currentToken.append(c)
                    i++
                }
            }
            result.add(currentToken.toString().trim())
            return result
        }

        private fun parseGroundTruthSpeeds(file: File): Map<String, List<Float>> {
            val resultMap = mutableMapOf<String, MutableList<Float>>()
            if (!file.exists()) return resultMap
            val lines = file.readLines()
            if (lines.isEmpty()) return resultMap

            val header = parseCsvLine(lines[0])
            val sessionIdx = header.indexOfFirst { it.equals("shot_category", ignoreCase = true) }
            val narrationIdx = header.indexOfFirst { it.equals("narration", ignoreCase = true) }
            val speedIdx = header.indexOfFirst { it.equals("bat_true_speed_kmh", ignoreCase = true) }

            if (sessionIdx == -1 || narrationIdx == -1 || speedIdx == -1) {
                return resultMap
            }

            for (i in 1 until lines.size) {
                val line = lines[i]
                if (line.isBlank()) continue
                val parts = parseCsvLine(line)
                if (parts.size <= maxOf(sessionIdx, narrationIdx, speedIdx)) continue
                val session = parts[sessionIdx].trim()
                val narration = parts[narrationIdx].trim()
                val speedStr = parts[speedIdx]
                val speed = speedStr.toFloatOrNull() ?: continue

                val key = "${session.lowercase()}|${narration.lowercase()}"
                resultMap.getOrPut(key) { mutableListOf() }.add(speed)
            }
            return resultMap
        }

        private fun parseTranscriptHitMap(file: File): Map<String, List<Boolean>> {
            val resultMap = mutableMapOf<String, MutableList<Boolean>>()
            if (!file.exists()) return resultMap
            val lines = file.readLines()
            if (lines.isEmpty()) return resultMap

            val header = parseCsvLine(lines[0])
            val narrationIdx = header.indexOfFirst { it.equals("Narration", ignoreCase = true) }
            val hitIdx = header.indexOfFirst { it.equals("Bat Hit", ignoreCase = true) }

            if (narrationIdx == -1 || hitIdx == -1) return resultMap

            for (i in 1 until lines.size) {
                val line = lines[i]
                if (line.isBlank()) continue
                val parts = parseCsvLine(line)
                if (parts.size <= maxOf(narrationIdx, hitIdx)) continue
                val narration = parts[narrationIdx].trim()
                val hitStr = parts[hitIdx].trim()
                val hit = hitStr.equals("Yes", ignoreCase = true)

                val key = narration.lowercase()
                resultMap.getOrPut(key) { mutableListOf() }.add(hit)
            }
            return resultMap
        }
    }
}
