package com.mrpeel.cricketbattingtracker.analytics

import com.mrpeel.cricketbattingtracker.data.InningsEvent
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class BiomechanicsAggregatorTest {

    private fun createDualShot(
        inningsId: Long = 101L,
        shotType: String = "Pull shot",
        timeLeadMs: Long = -18L,
        gyroRatio: Float = 0.15f,
        accRatio: Float = 1.35f
    ): InningsEvent {
        return InningsEvent(
            inningsId = inningsId,
            timestamp = 1750000000000L,
            description = "Shot: $shotType",
            batSpeed = 85.0f,
            shotType = shotType,
            bottom_hand_gyro_ratio = gyroRatio,
            bottom_hand_acc_ratio = accRatio,
            bottom_hand_time_lead_ms = timeLeadMs
        )
    }

    @Test
    fun testComputePercentileAndDistributionCalculations() {
        val oddList = listOf(10f, 20f, 30f, 40f, 50f)
        val distOdd = BiomechanicsAggregator.computeDistribution(oddList)

        assertNotNull(distOdd)
        assertEquals(5, distOdd!!.count)
        assertEquals(30f, distOdd.median, 0.001f)
        assertEquals(20f, distOdd.p25, 0.001f)
        assertEquals(40f, distOdd.p75, 0.001f)
        assertEquals(20f, distOdd.iqr, 0.001f)
        assertEquals(30f, distOdd.mean, 0.001f)
        assertEquals(10f, distOdd.min, 0.001f)
        assertEquals(50f, distOdd.max, 0.001f)

        val singleList = listOf(42f)
        val distSingle = BiomechanicsAggregator.computeDistribution(singleList)
        assertNotNull(distSingle)
        assertEquals(1, distSingle!!.count)
        assertEquals(42f, distSingle.median, 0.001f)
        assertEquals(42f, distSingle.p25, 0.001f)
        assertEquals(42f, distSingle.p75, 0.001f)
        assertEquals(0f, distSingle.iqr, 0.001f)
        assertEquals(42f, distSingle.mean, 0.001f)
        assertEquals(0f, distSingle.stdDev, 0.001f)

        val emptyList = emptyList<Float>()
        assertNull(BiomechanicsAggregator.computeDistribution(emptyList))
    }

    @Test
    fun testSingleHandAndZeroedSessionsIgnored() {
        val watchOnlyNull = InningsEvent(
            inningsId = 100L,
            timestamp = 1750000000000L,
            description = "Watch only shot",
            batSpeed = 70f,
            shotType = "Cover drive",
            bottom_hand_gyro_ratio = null,
            bottom_hand_acc_ratio = null,
            bottom_hand_time_lead_ms = null
        )

        val watchOnlyZeros = InningsEvent(
            inningsId = 100L,
            timestamp = 1750000000000L,
            description = "Watch only zeroed",
            batSpeed = 70f,
            shotType = "Cover drive",
            bottom_hand_gyro_ratio = 0f,
            bottom_hand_acc_ratio = 0f,
            bottom_hand_time_lead_ms = 0L
        )

        val validDual = createDualShot(inningsId = 101L)

        assertFalse(BiomechanicsAggregator.hasDualSensor(watchOnlyNull))
        assertFalse(BiomechanicsAggregator.hasDualSensor(watchOnlyZeros))
        assertTrue(BiomechanicsAggregator.hasDualSensor(validDual))

        val result = BiomechanicsAggregator.aggregate(listOf(watchOnlyNull, watchOnlyZeros, validDual))
        assertEquals(3, result.totalShots)
        assertEquals(1, result.totalDualSensorShots)
        assertEquals(2, result.totalSessionsAnalyzed)
        assertEquals(1, result.totalDualSessionsAnalyzed)
        assertEquals(1, result.validDualSensorEvents.size)
    }

    @Test
    fun testMinFiveShotsThresholdPerClass() {
        val fourShots = (1..4).map { createDualShot(shotType = "Pull shot") }
        val resultFour = BiomechanicsAggregator.aggregate(fourShots)

        assertEquals(4, resultFour.totalDualSensorShots)
        assertTrue(resultFour.classProfiles.isEmpty())
        assertEquals(4, resultFour.insufficientDataClasses["PULL/HOOK"])

        val fiveShots = (1..5).map { createDualShot(shotType = "Pull shot") }
        val resultFive = BiomechanicsAggregator.aggregate(fiveShots)

        assertEquals(5, resultFive.totalDualSensorShots)
        assertEquals(1, resultFive.classProfiles.size)
        assertNotNull(resultFive.classProfiles["PULL/HOOK"])
        assertEquals(5, resultFive.classProfiles["PULL/HOOK"]!!.sampleCount)
        assertFalse(resultFive.insufficientDataClasses.containsKey("PULL/HOOK"))
    }

    @Test
    fun testCanonicalTaxonomyNormalizationAndDistribution() {
        val events = listOf(
            createDualShot(shotType = "Pull shot"),
            createDualShot(shotType = "Hook"),
            createDualShot(shotType = "PULL/HOOK"),
            createDualShot(shotType = "Cover drive"),
            createDualShot(shotType = "Forward defense"),
            createDualShot(shotType = "Straight drive"),
            createDualShot(shotType = "DRIVE/DEFENCE"),
            createDualShot(shotType = "Square cut"),
            createDualShot(shotType = "Punch"),
            createDualShot(shotType = "Sweep")
        )

        val result = BiomechanicsAggregator.aggregate(events)
        assertEquals(10, result.totalDualSensorShots)
        assertEquals(3, result.shotFamilyDistribution["PULL/HOOK"])
        assertEquals(4, result.shotFamilyDistribution["DRIVE/DEFENCE"])
        assertEquals(2, result.shotFamilyDistribution["CUT/PUNCH"])
        assertEquals(1, result.shotFamilyDistribution["SWEEP"])
        assertEquals(0, result.shotFamilyDistribution["SLOG"])
    }

    @Test
    fun testCoordinationHealthScoreComputation() {
        // Create 10 optimal pull shots
        val optimalPulls = (1..10).map {
            createDualShot(
                shotType = "Pull shot",
                timeLeadMs = -20L,
                gyroRatio = 0.15f,
                accRatio = 1.30f
            )
        }
        val resultOptimal = BiomechanicsAggregator.aggregate(optimalPulls)
        assertEquals(100, resultOptimal.coordinationHealthScore)
        assertEquals(0.0f, resultOptimal.classProfiles["PULL/HOOK"]!!.amberFaultRate, 0.01f)

        // Create 6 optimal pulls + 4 dragged pulls (tripping warning)
        val draggedPulls = (1..4).map {
            createDualShot(
                shotType = "Pull shot",
                timeLeadMs = +50L,
                gyroRatio = 0.20f,
                accRatio = 1.00f
            )
        }
        val mixedList = (1..6).map { optimalPulls[0] } + draggedPulls
        val resultMixed = BiomechanicsAggregator.aggregate(mixedList)
        assertEquals(60, resultMixed.coordinationHealthScore)
        assertEquals(40.0f, resultMixed.classProfiles["PULL/HOOK"]!!.amberFaultRate, 0.01f)

        // Empty list defaults to 100
        val resultEmpty = BiomechanicsAggregator.aggregate(emptyList())
        assertEquals(100, resultEmpty.coordinationHealthScore)
    }

    @Test
    fun testSpeedEfficiencyMetricsAndTraits() {
        val shots = listOf(
            InningsEvent(
                inningsId = 1L, timestamp = 1000L, description = "Drive 1",
                batSpeed = 80.0f, efficiency = 75.0f, shotType = "Cover drive",
                bottom_hand_gyro_ratio = 0.55f, bottom_hand_acc_ratio = 0.45f, bottom_hand_time_lead_ms = 10L
            ),
            InningsEvent(
                inningsId = 1L, timestamp = 2000L, description = "Drive 2",
                batSpeed = 85.0f, efficiency = 80.0f, shotType = "Cover drive",
                bottom_hand_gyro_ratio = 0.60f, bottom_hand_acc_ratio = 0.50f, bottom_hand_time_lead_ms = 12L
            ),
            InningsEvent(
                inningsId = 1L, timestamp = 3000L, description = "Drive 3",
                batSpeed = 90.0f, efficiency = 85.0f, shotType = "Cover drive",
                bottom_hand_gyro_ratio = 0.50f, bottom_hand_acc_ratio = 0.40f, bottom_hand_time_lead_ms = 8L
            ),
            InningsEvent(
                inningsId = 1L, timestamp = 4000L, description = "Drive 4",
                batSpeed = 95.0f, efficiency = 88.0f, shotType = "Cover drive",
                bottom_hand_gyro_ratio = 0.65f, bottom_hand_acc_ratio = 0.55f, bottom_hand_time_lead_ms = 15L
            ),
            InningsEvent(
                inningsId = 1L, timestamp = 5000L, description = "Drive 5",
                batSpeed = 100.0f, efficiency = 92.0f, shotType = "Cover drive",
                bottom_hand_gyro_ratio = 0.58f, bottom_hand_acc_ratio = 0.48f, bottom_hand_time_lead_ms = 11L
            )
        )

        val result = BiomechanicsAggregator.aggregate(shots)
        val profile = result.classProfiles["DRIVE/DEFENCE"]
        assertNotNull(profile)

        // Speed checks
        assertEquals(100.0f, profile!!.batSpeedMax, 0.01f)
        assertEquals(80.0f, profile.batSpeedMin, 0.01f)
        assertEquals(90.0f, profile.batSpeedMedian, 0.01f)
        assertEquals(96.0f, profile.batSpeedP80, 0.5f)

        // Efficiency checks
        assertEquals(92.0f, profile.efficiencyP80, 5.0f)
        assertEquals(84.0f, profile.efficiencyMean, 0.1f)

        // Traits & observations
        assertTrue(profile.angularTrait.contains("Top-Hand Controlled Steer"))
        assertTrue(profile.timingTrait.contains("Synchronous Two-Hand Lock") || profile.timingTrait.contains("Controlled Trailing Hand"))
        assertTrue(profile.keyTechnicalObservation.contains("Top-hand dominant steering"))
        assertEquals(100.0f, profile.percentageOfRepertoire, 0.01f)
    }
}
