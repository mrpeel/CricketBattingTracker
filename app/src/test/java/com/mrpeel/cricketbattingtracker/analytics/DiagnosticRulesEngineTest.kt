package com.mrpeel.cricketbattingtracker.analytics

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class DiagnosticRulesEngineTest {

    private fun createProfile(
        shotClass: String,
        timeLeads: List<Float>,
        gyroRatios: List<Float>,
        accRatios: List<Float>,
        faultRate: Float = 0f
    ): ShotClassStatisticalProfile {
        val timeDist = BiomechanicsAggregator.computeDistribution(timeLeads)!!
        val gyroDist = BiomechanicsAggregator.computeDistribution(gyroRatios)!!
        val accDist = BiomechanicsAggregator.computeDistribution(accRatios)!!

        val timingTrait = BiomechanicsAggregator.determineTimingTrait(timeDist.median, timeDist.iqr)
        val angularTrait = BiomechanicsAggregator.determineAngularTrait(gyroDist.median)
        val linearTrait = BiomechanicsAggregator.determineLinearTrait(accDist.median)

        return ShotClassStatisticalProfile(
            shotClass = shotClass,
            sampleCount = timeLeads.size,
            dualSensorSampleCount = timeLeads.size,
            percentageOfRepertoire = 50.0f,
            batSpeedMax = 95.0f,
            batSpeedP80 = 88.0f,
            batSpeedMedian = 82.0f,
            batSpeedMin = 70.0f,
            efficiencyP80 = 85.0f,
            efficiencyMean = 78.0f,
            efficiencyMedian = 80.0f,
            timeLeadDistribution = timeDist,
            gyroRatioDistribution = gyroDist,
            accRatioDistribution = accDist,
            amberFaultRate = faultRate,
            timingTrait = timingTrait,
            angularTrait = angularTrait,
            linearTrait = linearTrait,
            keyTechnicalObservation = "Test observation",
            rawTimeLeads = timeLeads,
            rawGyroRatios = gyroRatios,
            rawAccRatios = accRatios
        )
    }

    @Test
    fun testPullLagFaultTriggersWhenMedianAboveTenOrHighPositivePercentage() {
        // Case 1: Median > +10ms
        val profileMedianHigh = createProfile(
            shotClass = "PULL/HOOK",
            timeLeads = listOf(+12f, +15f, +20f, +18f, +14f),
            gyroRatios = listOf(0.15f, 0.15f, 0.15f, 0.15f, 0.15f),
            accRatios = listOf(1.30f, 1.30f, 1.30f, 1.30f, 1.30f)
        )
        val fault1 = DiagnosticRulesEngine.checkPullLag(profileMedianHigh)
        assertNotNull(fault1)
        assertEquals(DiagnosticFaultCode.FAULT_PULL_LAG, fault1!!.faultCode)
        assertEquals(DiagnosticRulesEngine.DRILL_PULL_TEE_SLAPS.id, fault1.drill.id)
        assertTrue(fault1.quantifiedImpact.contains("+12 to 18 km/h"))

        // Case 2: Median <= +10ms but > 40% positive lag (3 of 5 > 0ms, e.g. +5ms, +8ms, +2ms, -15ms, -20ms)
        val profilePositiveRateHigh = createProfile(
            shotClass = "PULL/HOOK",
            timeLeads = listOf(+5f, +8f, +2f, -15f, -20f), // median = +2ms <= 10ms, but 60% > 0ms
            gyroRatios = listOf(0.15f, 0.15f, 0.15f, 0.15f, 0.15f),
            accRatios = listOf(1.30f, 1.30f, 1.30f, 1.30f, 1.30f)
        )
        val fault2 = DiagnosticRulesEngine.checkPullLag(profilePositiveRateHigh)
        assertNotNull(fault2)
        assertEquals(DiagnosticFaultCode.FAULT_PULL_LAG, fault2!!.faultCode)

        // Case 3: Optimal window (median = -20ms, 0% > 0ms)
        val profileOptimal = createProfile(
            shotClass = "PULL/HOOK",
            timeLeads = listOf(-25f, -20f, -18f, -22f, -15f),
            gyroRatios = listOf(0.15f, 0.15f, 0.15f, 0.15f, 0.15f),
            accRatios = listOf(1.30f, 1.30f, 1.30f, 1.30f, 1.30f)
        )
        assertNull(DiagnosticRulesEngine.checkPullLag(profileOptimal))
    }

    @Test
    fun testPullPowerFaultTriggersWhenMedianAccRatioBelowOne() {
        // Trigger: median accRatio < 1.00
        val profileWeak = createProfile(
            shotClass = "PULL/HOOK",
            timeLeads = listOf(-20f, -18f, -22f, -15f, -20f),
            gyroRatios = listOf(0.15f, 0.15f, 0.15f, 0.15f, 0.15f),
            accRatios = listOf(0.85f, 0.90f, 0.75f, 0.80f, 0.95f) // median = 0.85 < 1.00
        )
        val fault = DiagnosticRulesEngine.checkPullPower(profileWeak)
        assertNotNull(fault)
        assertEquals(DiagnosticFaultCode.FAULT_PULL_POWER, fault!!.faultCode)
        assertEquals(DiagnosticRulesEngine.DRILL_PULL_TEE_SLAPS.id, fault.drill.id)
        assertTrue(fault.quantifiedImpact.contains("+15% exit velocity"))

        // Non-trigger: median accRatio >= 1.00
        val profileStrong = createProfile(
            shotClass = "PULL/HOOK",
            timeLeads = listOf(-20f, -18f, -22f, -15f, -20f),
            gyroRatios = listOf(0.15f, 0.15f, 0.15f, 0.15f, 0.15f),
            accRatios = listOf(1.25f, 1.30f, 1.40f, 1.20f, 1.35f)
        )
        assertNull(DiagnosticRulesEngine.checkPullPower(profileStrong))
    }

    @Test
    fun testDriveTakeoverFaultTriggersWhenGyroRatioHighOrTrippingChokeRate() {
        // Case 1: Median gyroRatio > 0.75
        val profileChokeMedian = createProfile(
            shotClass = "DRIVE/DEFENCE",
            timeLeads = listOf(10f, 12f, 15f, 8f, 14f),
            gyroRatios = listOf(0.80f, 0.82f, 0.85f, 0.78f, 0.90f),
            accRatios = listOf(0.40f, 0.45f, 0.40f, 0.50f, 0.42f)
        )
        val fault1 = DiagnosticRulesEngine.checkDriveTakeover(profileChokeMedian)
        assertNotNull(fault1)
        assertEquals(DiagnosticFaultCode.FAULT_DRIVE_TAKEOVER, fault1!!.faultCode)
        assertEquals(DiagnosticRulesEngine.DRILL_DROP_DRIVES.id, fault1.drill.id)
        assertTrue(fault1.quantifiedImpact.contains("+25%"))

        // Case 2: Median <= 0.75 but > 30% shots with gyroRatio > 0.85 (2 of 5 = 40%)
        val profileChokeSpikes = createProfile(
            shotClass = "DRIVE/DEFENCE",
            timeLeads = listOf(10f, 12f, 15f, 8f, 14f),
            gyroRatios = listOf(0.60f, 0.65f, 0.70f, 0.92f, 0.88f), // median = 0.70, but 40% > 0.85
            accRatios = listOf(0.40f, 0.45f, 0.40f, 0.50f, 0.42f)
        )
        val fault2 = DiagnosticRulesEngine.checkDriveTakeover(profileChokeSpikes)
        assertNotNull(fault2)
        assertEquals(DiagnosticFaultCode.FAULT_DRIVE_TAKEOVER, fault2!!.faultCode)

        // Non-trigger: Top-hand control (median = 0.55, 0% > 0.85)
        val profileTopHand = createProfile(
            shotClass = "DRIVE/DEFENCE",
            timeLeads = listOf(10f, 12f, 15f, 8f, 14f),
            gyroRatios = listOf(0.50f, 0.55f, 0.58f, 0.60f, 0.52f),
            accRatios = listOf(0.40f, 0.45f, 0.40f, 0.50f, 0.42f)
        )
        assertNull(DiagnosticRulesEngine.checkDriveTakeover(profileTopHand))
    }

    @Test
    fun testCutAsyncFaultTriggersWhenTimeLagOrAccRatioFails() {
        // Case 1: Median timeLeadMs > +10ms
        val profileLag = createProfile(
            shotClass = "CUT/PUNCH",
            timeLeads = listOf(15f, 18f, 22f, 12f, 14f),
            gyroRatios = listOf(1.00f, 1.00f, 1.00f, 1.00f, 1.00f),
            accRatios = listOf(1.00f, 1.00f, 1.00f, 1.00f, 1.00f)
        )
        val fault1 = DiagnosticRulesEngine.checkCutAsync(profileLag)
        assertNotNull(fault1)
        assertEquals(DiagnosticFaultCode.FAULT_CUT_ASYNC, fault1!!.faultCode)
        assertEquals(DiagnosticRulesEngine.DRILL_WALL_PUNCH.id, fault1.drill.id)
        assertTrue(fault1.quantifiedImpact.contains("+10 km/h"))

        // Case 2: Median accRatio < 0.75
        val profileWeakPunch = createProfile(
            shotClass = "CUT/PUNCH",
            timeLeads = listOf(0f, 2f, -2f, 1f, 0f),
            gyroRatios = listOf(1.00f, 1.00f, 1.00f, 1.00f, 1.00f),
            accRatios = listOf(0.60f, 0.65f, 0.70f, 0.55f, 0.68f)
        )
        val fault2 = DiagnosticRulesEngine.checkCutAsync(profileWeakPunch)
        assertNotNull(fault2)
        assertEquals(DiagnosticFaultCode.FAULT_CUT_ASYNC, fault2!!.faultCode)

        // Non-trigger: Synchronous 0ms, balanced 1.00x acc
        val profileSynchronous = createProfile(
            shotClass = "CUT/PUNCH",
            timeLeads = listOf(0f, 2f, -1f, 1f, 0f),
            gyroRatios = listOf(1.00f, 1.00f, 1.00f, 1.00f, 1.00f),
            accRatios = listOf(1.00f, 1.05f, 0.95f, 1.00f, 0.98f)
        )
        assertNull(DiagnosticRulesEngine.checkCutAsync(profileSynchronous))
    }

    @Test
    fun testSweepArmsFaultTriggersWhenAccRatioLowOrTimeLagHigh() {
        // Trigger: Median accRatio < 0.80
        val profileArmSweep = createProfile(
            shotClass = "SWEEP",
            timeLeads = listOf(0f, 2f, -2f, 1f, 0f),
            gyroRatios = listOf(1.15f, 1.15f, 1.15f, 1.15f, 1.15f),
            accRatios = listOf(0.65f, 0.70f, 0.72f, 0.60f, 0.68f)
        )
        val fault = DiagnosticRulesEngine.checkSweepArms(profileArmSweep)
        assertNotNull(fault)
        assertEquals(DiagnosticFaultCode.FAULT_SWEEP_ARMS, fault!!.faultCode)
        assertEquals(DiagnosticRulesEngine.DRILL_CORE_SWEEPS.id, fault.drill.id)
        assertTrue(fault.quantifiedImpact.contains("placement torque"))

        // Trigger: Median timeLeadMs > +12ms
        val profileLagSweep = createProfile(
            shotClass = "SWEEP",
            timeLeads = listOf(15f, 18f, 14f, 20f, 16f),
            gyroRatios = listOf(1.15f, 1.15f, 1.15f, 1.15f, 1.15f),
            accRatios = listOf(1.00f, 1.05f, 0.95f, 1.00f, 0.98f)
        )
        val faultLag = DiagnosticRulesEngine.checkSweepArms(profileLagSweep)
        assertNotNull(faultLag)
        assertEquals(DiagnosticFaultCode.FAULT_SWEEP_ARMS, faultLag!!.faultCode)

        // Non-trigger: Torso-linked sweep (acc = 1.05x, lead = 0ms)
        val profileTorsoLinked = createProfile(
            shotClass = "SWEEP",
            timeLeads = listOf(0f, 2f, -1f, 1f, 0f),
            gyroRatios = listOf(1.15f, 1.15f, 1.15f, 1.15f, 1.15f),
            accRatios = listOf(1.05f, 1.10f, 1.00f, 1.02f, 1.08f)
        )
        assertNull(DiagnosticRulesEngine.checkSweepArms(profileTorsoLinked))
    }

    @Test
    fun testFlickEarlyFaultTriggersWhenTimeLeadTooEarlyOrGyroLow() {
        // Trigger: Median timeLeadMs < -20ms (e.g. -25ms)
        val profileEarlyRoll = createProfile(
            shotClass = "GLANCE/FLICK",
            timeLeads = listOf(-25f, -28f, -22f, -30f, -24f),
            gyroRatios = listOf(1.30f, 1.35f, 1.25f, 1.40f, 1.30f),
            accRatios = listOf(1.00f, 1.00f, 1.00f, 1.00f, 1.00f)
        )
        val fault1 = DiagnosticRulesEngine.checkFlickEarly(profileEarlyRoll)
        assertNotNull(fault1)
        assertEquals(DiagnosticFaultCode.FAULT_FLICK_EARLY, fault1!!.faultCode)
        assertEquals(DiagnosticRulesEngine.DRILL_PAD_CLEARANCE.id, fault1.drill.id)
        assertTrue(fault1.quantifiedImpact.contains("Sharpens pad-clearance angle"))

        // Trigger: Median gyroRatio < 1.00
        val profileWeakSnap = createProfile(
            shotClass = "GLANCE/FLICK",
            timeLeads = listOf(-10f, -8f, -12f, -11f, -9f),
            gyroRatios = listOf(0.75f, 0.80f, 0.70f, 0.85f, 0.72f),
            accRatios = listOf(1.00f, 1.00f, 1.00f, 1.00f, 1.00f)
        )
        val fault2 = DiagnosticRulesEngine.checkFlickEarly(profileWeakSnap)
        assertNotNull(fault2)
        assertEquals(DiagnosticFaultCode.FAULT_FLICK_EARLY, fault2!!.faultCode)

        // Non-trigger: Perfect timing (-10ms, gyro = 1.30x)
        val profilePerfect = createProfile(
            shotClass = "GLANCE/FLICK",
            timeLeads = listOf(-10f, -8f, -12f, -11f, -9f),
            gyroRatios = listOf(1.30f, 1.35f, 1.25f, 1.40f, 1.30f),
            accRatios = listOf(1.00f, 1.00f, 1.00f, 1.00f, 1.00f)
        )
        assertNull(DiagnosticRulesEngine.checkFlickEarly(profilePerfect))
    }

    @Test
    fun testDiagnoseRanksFaultsAndAttachesDistinctDrills() {
        val profilePullLag = createProfile(
            shotClass = "PULL/HOOK",
            timeLeads = listOf(+25f, +30f, +22f, +28f, +24f),
            gyroRatios = listOf(0.15f, 0.15f, 0.15f, 0.15f, 0.15f),
            accRatios = listOf(1.30f, 1.30f, 1.30f, 1.30f, 1.30f)
        )

        val profileDriveTakeover = createProfile(
            shotClass = "DRIVE/DEFENCE",
            timeLeads = listOf(10f, 12f, 15f, 8f, 14f),
            gyroRatios = listOf(0.88f, 0.90f, 0.85f, 0.82f, 0.92f),
            accRatios = listOf(0.40f, 0.45f, 0.40f, 0.50f, 0.42f)
        )

        val aggregation = LongitudinalAggregationResult(
            totalShots = 10,
            totalDualSensorShots = 10,
            totalSessionsAnalyzed = 2,
            totalDualSessionsAnalyzed = 2,
            coordinationHealthScore = 40,
            classProfiles = mapOf(
                "PULL/HOOK" to profilePullLag,
                "DRIVE/DEFENCE" to profileDriveTakeover
            ),
            insufficientDataClasses = emptyMap(),
            shotFamilyDistribution = mapOf("PULL/HOOK" to 5, "DRIVE/DEFENCE" to 5),
            validDualSensorEvents = emptyList()
        )

        val diagnosis = DiagnosticRulesEngine.diagnose(aggregation)
        assertEquals(2, diagnosis.allDetectedFaults.size)
        assertEquals(2, diagnosis.topPrimaryFlaws.size)
        assertEquals(2, diagnosis.prescribedDrills.size)

        // Ensure distinct drills list contains both unique drills
        val drillIds = diagnosis.prescribedDrills.map { it.id }.toSet()
        assertTrue(drillIds.contains(DiagnosticRulesEngine.DRILL_PULL_TEE_SLAPS.id))
        assertTrue(drillIds.contains(DiagnosticRulesEngine.DRILL_DROP_DRIVES.id))
    }
}
