package com.mrpeel.cricketbattingtracker.ml

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.File

class SwingDetectorRandomForestAlignmentTest {

    @Test
    fun testRandomForestParityWithPython() {
        val baseDir = File("/Users/neilkloot/Code/Batting Sensor Stats")
        val featuresFile = File(baseDir, "combined_features.csv")
        val proposedFile = File(baseDir, "proposed_logic_aligned.csv")

        assertTrue("combined_features.csv must exist", featuresFile.exists())
        assertTrue("proposed_logic_aligned.csv must exist", proposedFile.exists())

        // 1. Load expected predictions from proposed_logic_aligned.csv
        // Key: "session_id|shot_index" -> predicted_shot_type
        val expectedPreds = mutableMapOf<String, String>()
        val proposedLines = proposedFile.readLines()
        assertTrue("proposed_logic_aligned.csv must have data", proposedLines.size > 1)
        
        val proposedHeader = parseCsvLine(proposedLines[0])
        val pSessionIdx = proposedHeader.indexOf("session_id")
        val pShotIdx = proposedHeader.indexOf("shot_index")
        val pPredIdx = proposedHeader.indexOf("predicted_shot_type")

        assertTrue("proposed_logic_aligned.csv must contain session_id", pSessionIdx != -1)
        assertTrue("proposed_logic_aligned.csv must contain shot_index", pShotIdx != -1)
        assertTrue("proposed_logic_aligned.csv must contain predicted_shot_type", pPredIdx != -1)

        for (i in 1 until proposedLines.size) {
            val line = proposedLines[i]
            if (line.isBlank()) continue
            val parts = parseCsvLine(line)
            if (parts.size > maxOf(pSessionIdx, pShotIdx, pPredIdx)) {
                val sessionId = parts[pSessionIdx]
                val shotIndex = parts[pShotIdx]
                val predShotType = parts[pPredIdx]
                if (predShotType != "N/A" && predShotType.isNotBlank()) {
                    expectedPreds["$sessionId|$shotIndex"] = predShotType
                }
            }
        }
        
        println("Loaded ${expectedPreds.size} expected predictions from proposed_logic_aligned.csv")

        // 2. Load features from combined_features.csv and run Kotlin prediction
        val featuresLines = featuresFile.readLines()
        assertTrue("combined_features.csv must have data", featuresLines.size > 1)
        
        val featuresHeader = parseCsvLine(featuresLines[0])
        
        // Map feature column indices dynamically
        val fSessionIdx = featuresHeader.indexOf("session_id")
        val fShotIdx = featuresHeader.indexOf("shot_index")
        val fGyroMagIdx = featuresHeader.indexOf("gyroMag")
        val fRollIdx = featuresHeader.indexOf("rollImpactDeg")
        val fYawIdx = featuresHeader.indexOf("yawImpactDeg")
        val fDeltaXIdx = featuresHeader.indexOf("deltaX")
        val fDeltaZIdx = featuresHeader.indexOf("deltaZ")
        val fRatioIdx = featuresHeader.indexOf("planeRatio")
        val fGyroYMinIdx = featuresHeader.indexOf("gyro_y_min")
        val fGravXMaxIdx = featuresHeader.indexOf("grav_x_max")
        val fGravYMinIdx = featuresHeader.indexOf("grav_y_min")
        val fMagXMaxIdx = featuresHeader.indexOf("mag_x_max")

        assertTrue("Missing critical features/metadata in combined_features.csv header",
            fSessionIdx != -1 && fShotIdx != -1 && fGyroMagIdx != -1 && fRollIdx != -1 &&
            fYawIdx != -1 && fDeltaXIdx != -1 && fDeltaZIdx != -1 && fRatioIdx != -1 &&
            fGyroYMinIdx != -1 && fGravXMaxIdx != -1 && fGravYMinIdx != -1 && fMagXMaxIdx != -1
        )

        var matchedCount = 0
        var mismatchCount = 0

        for (i in 1 until featuresLines.size) {
            val line = featuresLines[i]
            if (line.isBlank()) continue
            val parts = parseCsvLine(line)
            if (parts.size > maxOf(fSessionIdx, fShotIdx, fGyroMagIdx, fRollIdx, fYawIdx, fDeltaXIdx, fDeltaZIdx, fRatioIdx, fGyroYMinIdx, fGravXMaxIdx, fGravYMinIdx, fMagXMaxIdx)) {
                val sessionId = parts[fSessionIdx]
                val shotIndex = parts[fShotIdx]
                
                val key = "$sessionId|$shotIndex"
                val expected = expectedPreds[key]
                if (expected == null) {
                    // This shot was skipped or non-swing in alignment
                    continue
                }

                // Construct feature vector
                val f = SwingFeatures(
                    gyroMag = parts[fGyroMagIdx].toFloat(),
                    rollImpactDeg = parts[fRollIdx].toFloat(),
                    yawImpactDeg = parts[fYawIdx].toFloat(),
                    deltaX = parts[fDeltaXIdx].toFloat(),
                    deltaZ = parts[fDeltaZIdx].toFloat(),
                    planeRatio = parts[fRatioIdx].toFloat(),
                    gyro_y_min = parts[fGyroYMinIdx].toFloat(),
                    grav_x_max = parts[fGravXMaxIdx].toFloat(),
                    grav_y_min = parts[fGravYMinIdx].toFloat(),
                    mag_x_max = parts[fMagXMaxIdx].toFloat()
                )

                // Predict in Kotlin
                val actual = GeneratedForest.predict(f)

                if (actual == expected) {
                    matchedCount++
                } else {
                    mismatchCount++
                    System.err.println("❌ MISMATCH on shot $key: expected '$expected' (Python) but got '$actual' (Kotlin)")
                }
            }
        }

        println("Parity alignment test completed: matched=$matchedCount, mismatches=$mismatchCount")
        assertEquals("Kotlin predictions must match Python predictions exactly with 0 mismatches", 0, mismatchCount)
        assertTrue("Must verify at least 200 shots", matchedCount >= 200)
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
