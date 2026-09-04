package com.mrpeel.cricketbattingtracker.ml

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.File

class SwingDetectorRandomForestAlignmentTest {

    @org.junit.Ignore("Legacy Random Forest alignment test superseded by Phone TCN engine")
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
        val fDataProfileIdx = featuresHeader.indexOf("data_profile")
        
        val fS1GyroYStdIdx = featuresHeader.indexOf("s1_gyro_y_std")
        val fS1GyroZStdIdx = featuresHeader.indexOf("s1_gyro_z_std")
        val fS1DeltaXIdx = featuresHeader.indexOf("s1_deltaX")
        val fS1DeltaZIdx = featuresHeader.indexOf("s1_deltaZ")
        
        val fS2GyroMagIdx = featuresHeader.indexOf("s2_gyroMag")
        val fS2GravYMeanIdx = featuresHeader.indexOf("s2_grav_y_mean")
        val fS2DeltaXIdx = featuresHeader.indexOf("s2_deltaX")
        val fS2DeltaZIdx = featuresHeader.indexOf("s2_deltaZ")
        
        val fS3RollIdx = featuresHeader.indexOf("s3_rollImpactDeg")
        val fS3YawIdx = featuresHeader.indexOf("s3_yawImpactDeg")
        val fS3DeltaXIdx = featuresHeader.indexOf("s3_deltaX")
        val fS3DeltaZIdx = featuresHeader.indexOf("s3_deltaZ")
        val fS3RatioIdx = featuresHeader.indexOf("s3_planeRatio")
        val fS3GyroYMinIdx = featuresHeader.indexOf("s3_gyro_y_min")

        assertTrue("Missing critical features/metadata in combined_features.csv header",
            fSessionIdx != -1 && fShotIdx != -1 && fDataProfileIdx != -1 &&
            fS1GyroYStdIdx != -1 && fS1GyroZStdIdx != -1 && fS1DeltaXIdx != -1 && fS1DeltaZIdx != -1 &&
            fS2GyroMagIdx != -1 && fS2GravYMeanIdx != -1 && fS2DeltaXIdx != -1 && fS2DeltaZIdx != -1 &&
            fS3RollIdx != -1 && fS3YawIdx != -1 && fS3DeltaXIdx != -1 && fS3DeltaZIdx != -1 &&
            fS3RatioIdx != -1 && fS3GyroYMinIdx != -1
        )

        var matchedCount = 0
        var mismatchCount = 0

        for (i in 1 until featuresLines.size) {
            val line = featuresLines[i]
            if (line.isBlank()) continue
            val parts = parseCsvLine(line)
            if (parts.size > maxOf(
                    fSessionIdx, fShotIdx,
                    fS1GyroYStdIdx, fS1GyroZStdIdx, fS1DeltaXIdx, fS1DeltaZIdx,
                    fS2GyroMagIdx, fS2GravYMeanIdx, fS2DeltaXIdx, fS2DeltaZIdx,
                    fS3RollIdx, fS3YawIdx, fS3DeltaXIdx, fS3DeltaZIdx, fS3RatioIdx, fS3GyroYMinIdx
                )) {
                val sessionId = parts[fSessionIdx]
                val shotIndex = parts[fShotIdx]
                val dataProfile = parts[fDataProfileIdx]
                
                // Skip Polar sessions since the watch module runs 14-feature watch-only RF
                // whereas Polar sessions are predicted in Python using the 20-feature model.
                if (dataProfile.contains("polar", ignoreCase = true)) {
                    continue
                }
                
                val key = "$sessionId|$shotIndex"
                val expected = expectedPreds[key]
                if (expected == null) {
                    // This shot was skipped or non-swing in alignment
                    continue
                }

                // Construct feature vector
                val f = SwingFeatures(
                    s1_gyro_y_std = parts[fS1GyroYStdIdx].toFloat(),
                    s1_gyro_z_std = parts[fS1GyroZStdIdx].toFloat(),
                    s1_deltaX = parts[fS1DeltaXIdx].toFloat(),
                    s1_deltaZ = parts[fS1DeltaZIdx].toFloat(),
                    s2_gyroMag = parts[fS2GyroMagIdx].toFloat(),
                    s2_grav_y_mean = parts[fS2GravYMeanIdx].toFloat(),
                    s2_deltaX = parts[fS2DeltaXIdx].toFloat(),
                    s2_deltaZ = parts[fS2DeltaZIdx].toFloat(),
                    s3_rollImpactDeg = parts[fS3RollIdx].toFloat(),
                    s3_yawImpactDeg = parts[fS3YawIdx].toFloat(),
                    s3_deltaX = parts[fS3DeltaXIdx].toFloat(),
                    s3_deltaZ = parts[fS3DeltaZIdx].toFloat(),
                    s3_planeRatio = parts[fS3RatioIdx].toFloat(),
                    s3_gyro_y_min = parts[fS3GyroYMinIdx].toFloat()
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
