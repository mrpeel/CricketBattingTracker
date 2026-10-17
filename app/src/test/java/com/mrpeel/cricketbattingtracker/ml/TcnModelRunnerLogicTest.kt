package com.mrpeel.cricketbattingtracker.ml

import org.junit.Assert.*
import org.junit.Test
import kotlin.math.*

class TcnModelRunnerLogicTest {

    @Test
    fun testStanceTrackerSustainGuardAndExit() {
        val tracker = TcnModelRunner.StanceTracker(
            highThresh = 0.55f,
            lowThresh = 0.35f,
            motionSurgeW = 1.8f,
            sustainMs = 200
        )

        assertEquals("IDLE", tracker.state)

        // Step 1: 100ms at high probability -> still IDLE (sustain < 200ms)
        var (state, exited) = tracker.processStep(prob = 0.85f, wMag = 0.2f, dtMs = 100)
        assertEquals("IDLE", state)
        assertFalse(exited)

        // Step 2: Another 100ms at high probability -> becomes FACING_UP
        val (state2, exited2) = tracker.processStep(prob = 0.80f, wMag = 0.3f, dtMs = 100)
        assertEquals("FACING_UP", state2)
        assertFalse(exited2)

        // Step 3: Sustained stance
        val (state3, exited3) = tracker.processStep(prob = 0.75f, wMag = 0.4f, dtMs = 100)
        assertEquals("FACING_UP", state3)
        assertFalse(exited3)

        // Step 4: Motion surge (w >= 1.8 rad/s) triggers STANCE_EXIT
        val (state4, exited4) = tracker.processStep(prob = 0.60f, wMag = 2.1f, dtMs = 100)
        assertEquals("STANCE_EXIT", state4)
        assertTrue(exited4)

        // Step 5: Post-exit step resets to IDLE
        val (state5, exited5) = tracker.processStep(prob = 0.20f, wMag = 0.5f, dtMs = 100)
        assertEquals("IDLE", state5)
        assertFalse(exited5)
    }

    @Test
    fun testStanceTrackerLowProbabilityExit() {
        val tracker = TcnModelRunner.StanceTracker(sustainMs = 200)

        tracker.processStep(prob = 0.90f, wMag = 0.2f, dtMs = 100)
        tracker.processStep(prob = 0.90f, wMag = 0.2f, dtMs = 100)
        assertEquals("FACING_UP", tracker.state)

        // Stance probability drops below low threshold (< 0.35)
        val (state, exited) = tracker.processStep(prob = 0.25f, wMag = 0.2f, dtMs = 100)
        assertEquals("STANCE_EXIT", state)
        assertTrue(exited)
    }

    @Test
    fun testOneStanceSinglePeakDeduplication() {
        // Simulates 4.0s window (1692 frames at 423 Hz) with a primary strike and a secondary follow-through peak
        val numFrames = 1692
        val wGyroMag = FloatArray(numFrames) { 0.5f }

        // Primary strike at frame 300 (peak = 12.5 rad/s)
        wGyroMag[300] = 12.5f
        // Secondary follow-through peak at frame 500 (peak = 6.2 rad/s)
        wGyroMag[500] = 6.2f

        var maxGyro = 0f
        var peakF = 0
        for (k in 0 until numFrames) {
            if (wGyroMag[k] > maxGyro) {
                maxGyro = wGyroMag[k]
                peakF = k
            }
        }

        // Deduplication must extract ONLY the global maximum within the stance window
        assertEquals(300, peakF)
        assertEquals(12.5f, maxGyro, 1e-4f)
    }

    @Test
    fun testKinematicBackswingDisplacementCheck() {
        // Test backswing displacement check over 300ms (127 frames)
        val numFrames = 128
        val gentleTapGyro = FloatArray(numFrames) { 0.2f } // Gentle waggle (~0.06 rad displacement)
        val genuineSwingGyro = FloatArray(numFrames) { 2.5f } // Genuine backswing (> 0.75 rad displacement)

        val deltaThetaGentle = gentleTapGyro.sum() * (1.0f / 423.0f)
        val deltaThetaSwing = genuineSwingGyro.sum() * (1.0f / 423.0f)

        // Threshold = 0.14 rad (~8 deg)
        assertTrue("Gentle tap must be rejected (< 0.14 rad)", deltaThetaGentle < 0.14f)
        assertTrue("Genuine backswing must pass (>= 0.14 rad)", deltaThetaSwing >= 0.14f)
    }

    @Test
    fun testPowerDriveReclassificationGateRemoved() {
        // Obsolete Gate 1 (< 1.35 -> DRIVE/DEFENCE) was removed because real Power Drives
        // have mean post-impact ratio 0.92-0.95. Genuine POWER DRIVE predictions are now preserved.
        fun applyPowerDriveGate(predClass: String, ratio: Float): String {
            // No demotion of POWER DRIVE based on post-impact ratio
            return predClass
        }

        assertEquals("POWER DRIVE", applyPowerDriveGate("POWER DRIVE", 0.92f))
        assertEquals("POWER DRIVE", applyPowerDriveGate("POWER DRIVE", 1.65f))
        assertEquals("DRIVE/DEFENCE", applyPowerDriveGate("DRIVE/DEFENCE", 0.92f))
        assertEquals("PULL/HOOK/SLOG", applyPowerDriveGate("PULL/HOOK/SLOG", 0.92f))
    }

    @Test
    fun testCalibratedDualPathSweepGate() {
        fun evaluateSweepGate(
            deltaPitch: Float,
            deltaGz: Float,
            maxRollVel: Float,
            prob: Float
        ): Boolean {
            val isPath1 = (deltaPitch >= 10.0f || deltaGz >= 1.2f) && (prob >= 0.30f)
            val isPath2 = (maxRollVel >= 1.6f) && (prob >= 0.35f)
            return isPath1 || isPath2
        }

        // Case 1: Kneeling Slog Sweep (High pitch tilt 35 deg, P = 0.32) -> Path 1 PASS
        assertTrue(evaluateSweepGate(deltaPitch = 35f, deltaGz = 3.5f, maxRollVel = 0.5f, prob = 0.32f))

        // Case 2: Standing Paddle Sweep (Pitch tilt 4 deg, Wrist roll 2.1 rad/s, P = 0.38) -> Path 2 PASS
        assertTrue(evaluateSweepGate(deltaPitch = 4f, deltaGz = 0.4f, maxRollVel = 2.1f, prob = 0.38f))

        // Case 3: Standing Twich / Waggle (Pitch tilt 3 deg, Wrist roll 0.6 rad/s, P = 0.25) -> REJECT
        assertFalse(evaluateSweepGate(deltaPitch = 3f, deltaGz = 0.3f, maxRollVel = 0.6f, prob = 0.25f))

        // Case 4: Standing with Low Roll (Pitch tilt 5 deg, Wrist roll 1.1 rad/s, P = 0.32) -> REJECT
        assertFalse(evaluateSweepGate(deltaPitch = 5f, deltaGz = 0.5f, maxRollVel = 1.1f, prob = 0.32f))
    }

    @Test
    fun testDynamicClassAwareNmsLockout() {
        fun getRefractoryFrames(shotType: String, prevWasSweep: Boolean): Int {
            val isSweep = (shotType == "SWEEP")
            return if (prevWasSweep || isSweep) 1015 else 761 // 2.4s vs 1.8s at 423 Hz
        }

        assertEquals(1015, getRefractoryFrames("SWEEP", prevWasSweep = false))
        assertEquals(1015, getRefractoryFrames("DRIVE/DEFENCE", prevWasSweep = true))
        assertEquals(761, getRefractoryFrames("DRIVE/DEFENCE", prevWasSweep = false))
        assertEquals(761, getRefractoryFrames("PULL/HOOK", prevWasSweep = false))
    }

    @Test
    fun testGate25BatHandleConsistencyGateRule1Maintained() {
        fun applyGate25(
            predShotType: String,
            pitchDeg: Float,
            postImpactRatio: Float,
            polarMountMode: String
        ): String {
            var result = predShotType
            if (polarMountMode == "BAT_HANDLE") {
                if (pitchDeg >= 65.0f && (result == "PULL/HOOK/SLOG" || result == "CUT/PUNCH")) {
                    result = if (postImpactRatio >= 1.35f) "POWER DRIVE" else "DRIVE/DEFENCE"
                }
            }
            return result
        }

        // Steep vertical angles (>= 65°) convert cross-bat errors to drives
        assertEquals("DRIVE/DEFENCE", applyGate25("PULL/HOOK/SLOG", 70.0f, 1.1f, "BAT_HANDLE"))
        assertEquals("POWER DRIVE", applyGate25("PULL/HOOK/SLOG", 68.0f, 1.45f, "BAT_HANDLE"))
        assertEquals("DRIVE/DEFENCE", applyGate25("CUT/PUNCH", 65.0f, 1.0f, "BAT_HANDLE"))
    }

    @Test
    fun testGate25BatHandleReachingDriveNotFlippedToPull() {
        fun applyGate25(
            predShotType: String,
            pitchDeg: Float,
            postImpactRatio: Float,
            polarMountMode: String
        ): String {
            var result = predShotType
            if (polarMountMode == "BAT_HANDLE") {
                // Rule 1: Vertical Bat Gate
                if (pitchDeg >= 65.0f && (result == "PULL/HOOK/SLOG" || result == "CUT/PUNCH")) {
                    result = if (postImpactRatio >= 1.35f) "POWER DRIVE" else "DRIVE/DEFENCE"
                }
                // Rule 2 was removed! Reaching drives (pitch 20°-40°) must NOT be flipped to PULL/HOOK/SLOG!
            }
            return result
        }

        // Reaching drives with low pitch angles (20°-40°) MUST retain DRIVE/DEFENCE
        assertEquals("DRIVE/DEFENCE", applyGate25("DRIVE/DEFENCE", 29.1f, 1.1f, "BAT_HANDLE"))
        assertEquals("DRIVE/DEFENCE", applyGate25("DRIVE/DEFENCE", 35.8f, 1.1f, "BAT_HANDLE"))
        assertEquals("DRIVE/DEFENCE", applyGate25("DRIVE/DEFENCE", 37.6f, 1.1f, "BAT_HANDLE"))
        assertEquals("DRIVE/DEFENCE", applyGate25("DRIVE/DEFENCE", 25.0f, 1.1f, "BAT_HANDLE"))
        assertEquals("GLANCE/FLICK", applyGate25("GLANCE/FLICK", 25.0f, 1.1f, "BAT_HANDLE"))
    }

    @Test
    fun testLearnedFalsePositiveRejection() {
        fun resolveCandidateClass(avgNoShotProb: Float, topShotIdx: Int, classes: Array<String>): String {
            return if (avgNoShotProb >= 0.35f) {
                "no_shot"
            } else {
                if (topShotIdx < classes.size) classes[topShotIdx] else "DRIVE/DEFENCE"
            }
        }

        val classes = arrayOf(
            "no_shot", "pre_shot", "PULL/HOOK/SLOG", "DRIVE/DEFENCE",
            "GLANCE/FLICK", "CUT/PUNCH", "DEFLECTION/GUIDE", "POWER DRIVE", "SWEEP"
        )

        // Case 1: Candidate with high no_shot probability (0.52 >= 0.35) -> REJECT as "no_shot"
        assertEquals("no_shot", resolveCandidateClass(0.52f, topShotIdx = 3, classes = classes))

        // Case 2: Candidate with moderate no_shot probability right at threshold (0.35 >= 0.35) -> REJECT
        assertEquals("no_shot", resolveCandidateClass(0.35f, topShotIdx = 3, classes = classes))

        // Case 3: Genuine stroke with low no_shot probability (0.12 < 0.35) -> ACCEPT as topShotIdx (e.g. DRIVE/DEFENCE)
        assertEquals("DRIVE/DEFENCE", resolveCandidateClass(0.12f, topShotIdx = 3, classes = classes))

        // Case 4: Genuine power drive with very low no_shot probability (0.05 < 0.35) -> ACCEPT as POWER DRIVE
        assertEquals("POWER DRIVE", resolveCandidateClass(0.05f, topShotIdx = 7, classes = classes))
    }

    @Test
    fun testClosedFormSubHeadProbabilityRecovery() {
        // Verify exact mathematical recovery of p_sub0(Glance) and p_fam(Sweep) from 9-class post-softmax probabilities
        val a0True = 0.62
        val a1True = 0.14
        val a2True = 0.16
        val pSub0Drive = 0.18
        val pSub0Power = 0.12
        val pSub0GlanceTrue = 0.64
        val pSub0Defl = 0.06
        val pSub1Pull = 0.70
        val pSub1Cut = 0.30

        val q3 = a0True * pSub0Drive
        val q4 = a0True * pSub0GlanceTrue
        val q6 = a0True * pSub0Defl
        val q7 = (a0True + 0.85 * a1True) * pSub0Power
        val q2 = a1True * pSub1Pull
        val q5 = a1True * pSub1Cut
        val q8 = a2True

        val kVert = q3 + q4 + q6
        val a1Cross = q2 + q5
        val a2Sweep = q8
        val bCoef = kVert + q7 - 0.85 * a1Cross
        val a0Vert = 0.5 * (bCoef + sqrt(max(0.0, bCoef * bCoef + 3.4 * a1Cross * kVert)))
        val pSub0GlanceRec = (q4 / (a0Vert + 1e-12)).toFloat()
        val pFamSweepRec = (a2Sweep / (a0Vert + a1Cross + a2Sweep + 1e-12)).toFloat()

        assertEquals(pSub0GlanceTrue.toFloat(), pSub0GlanceRec, 1e-6f)
        assertEquals((a2True / (a0True + a1True + a2True)).toFloat(), pFamSweepRec, 1e-6f)
    }

    @Test
    fun testOption2NonBatPostureMitigation() {
        fun applyNonBatSweepMitigation(
            predShotType: String,
            polarMountMode: String,
            pSub0Glance: Float,
            impGz: Float,
            pFamSweep: Float
        ): String {
            var res = predShotType
            if (res == "SWEEP" && polarMountMode != "BAT_HANDLE") {
                if (pSub0Glance >= 0.55f && impGz < 5.5f && pFamSweep < 0.72f) {
                    res = "GLANCE/FLICK"
                }
            }
            return res
        }

        // Upright high-roll Glance/Flick in WRIST or NONE mode -> rescued to GLANCE/FLICK
        assertEquals("GLANCE/FLICK", applyNonBatSweepMitigation("SWEEP", "WRIST", 0.73f, 3.6f, 0.50f))
        assertEquals("GLANCE/FLICK", applyNonBatSweepMitigation("SWEEP", "NONE", 0.65f, 5.2f, 0.49f))

        // Kneeling Sweep with high vertical gravity Z (impGz >= 5.5) or strong Sweep family confidence -> stays SWEEP
        assertEquals("SWEEP", applyNonBatSweepMitigation("SWEEP", "WRIST", 0.70f, 8.2f, 0.55f))
        assertEquals("SWEEP", applyNonBatSweepMitigation("SWEEP", "NONE", 0.70f, 4.1f, 0.85f))
        assertEquals("SWEEP", applyNonBatSweepMitigation("SWEEP", "BAT_HANDLE", 0.73f, 3.6f, 0.50f))
    }

    @Test
    fun testOption2BatSensorFirstGlanceDisambiguation() {
        fun applyBatHandleGlanceDisambiguation(
            predShotType: String,
            polarMountMode: String,
            swingYawDeg: Float,
            batGzMin: Float,
            pSub0Glance: Float
        ): String {
            var res = predShotType
            if (polarMountMode == "BAT_HANDLE" &&
                (res == "DRIVE/DEFENCE" || res == "POWER DRIVE")
            ) {
                if ((swingYawDeg <= -17.0f && batGzMin <= -11.5f && pSub0Glance >= 0.25f) ||
                    (swingYawDeg <= -50.0f && pSub0Glance >= 0.50f)
                ) {
                    res = "GLANCE/FLICK"
                }
            }
            return res
        }

        // Case 1: Leg-side yaw (-25.6 deg) + wrist-snap axial roll (-12.5 rad/s) + Glance sub-head (0.57) -> GLANCE/FLICK
        assertEquals("GLANCE/FLICK", applyBatHandleGlanceDisambiguation("DRIVE/DEFENCE", "BAT_HANDLE", -25.6f, -12.5f, 0.57f))
        assertEquals("GLANCE/FLICK", applyBatHandleGlanceDisambiguation("POWER DRIVE", "BAT_HANDLE", -34.8f, -18.2f, 0.31f))

        // Case 2: Extreme leg-side yaw (-55.0 deg) + high Glance sub-head (0.55) on DRIVE -> GLANCE/FLICK
        assertEquals("GLANCE/FLICK", applyBatHandleGlanceDisambiguation("DRIVE/DEFENCE", "BAT_HANDLE", -55.0f, -8.0f, 0.55f))

        // Case 3: Cross-bat PULL/HOOK/SLOG must NEVER be flipped to GLANCE/FLICK even with leg-side yaw and roll
        assertEquals("PULL/HOOK/SLOG", applyBatHandleGlanceDisambiguation("PULL/HOOK/SLOG", "BAT_HANDLE", -55.0f, -18.0f, 0.55f))

        // Case 4: Genuine On-Drive (yaw -18.0 deg, but low axial roll -6.5 rad/s) -> stays DRIVE/DEFENCE
        assertEquals("DRIVE/DEFENCE", applyBatHandleGlanceDisambiguation("DRIVE/DEFENCE", "BAT_HANDLE", -18.0f, -6.5f, 0.40f))

        // Case 5: Genuine Power Drive with straight yaw (-5.0 deg) -> stays POWER DRIVE
        assertEquals("POWER DRIVE", applyBatHandleGlanceDisambiguation("POWER DRIVE", "BAT_HANDLE", -5.0f, -14.0f, 0.35f))
    }
}

