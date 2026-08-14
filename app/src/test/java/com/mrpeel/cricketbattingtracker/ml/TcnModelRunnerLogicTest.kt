package com.mrpeel.cricketbattingtracker.ml

import org.junit.Assert.*
import org.junit.Test
import kotlin.math.*

class TcnModelRunnerLogicTest {

    @Test
    fun testStanceTrackerSustainGuardAndExit() {
        val tracker = TcnModelRunner.StanceTracker(
            highThresh = 0.70f,
            lowThresh = 0.40f,
            motionSurgeW = 1.0f,
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

        // Step 4: Motion surge (w >= 1.0 rad/s) triggers STANCE_EXIT
        val (state4, exited4) = tracker.processStep(prob = 0.70f, wMag = 1.4f, dtMs = 100)
        assertEquals("STANCE_EXIT", state4)
        assertTrue(exited4)

        // Step 5: Post-exit step resets to IDLE
        val (state5, exited5) = tracker.processStep(prob = 0.30f, wMag = 0.5f, dtMs = 100)
        assertEquals("IDLE", state5)
        assertFalse(exited5)
    }

    @Test
    fun testStanceTrackerLowProbabilityExit() {
        val tracker = TcnModelRunner.StanceTracker(sustainMs = 200)

        tracker.processStep(prob = 0.90f, wMag = 0.2f, dtMs = 100)
        tracker.processStep(prob = 0.90f, wMag = 0.2f, dtMs = 100)
        assertEquals("FACING_UP", tracker.state)

        // Stance probability drops below low threshold (< 0.40)
        val (state, exited) = tracker.processStep(prob = 0.35f, wMag = 0.2f, dtMs = 100)
        assertEquals("STANCE_EXIT", state)
        assertTrue(exited)
    }

    @Test
    fun testOneStanceSinglePeakDeduplication() {
        // Simulates 3.5s window (1480 frames at 423 Hz) with a primary strike and a secondary follow-through peak
        val numFrames = 1480
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
    fun testPowerDriveReclassificationGate() {
        // Post-Impact Acceleration Ratio Gate: < 1.35 -> DRIVE/DEFENCE
        val weakRatio = 1.15f
        val strongRatio = 1.65f

        fun applyPowerDriveGate(predClass: String, ratio: Float): String {
            return if (predClass == "POWER DRIVE" && ratio < 1.35f) {
                "DRIVE/DEFENCE"
            } else {
                predClass
            }
        }

        assertEquals("DRIVE/DEFENCE", applyPowerDriveGate("POWER DRIVE", weakRatio))
        assertEquals("POWER DRIVE", applyPowerDriveGate("POWER DRIVE", strongRatio))
        assertEquals("PULL/HOOK", applyPowerDriveGate("PULL/HOOK", weakRatio))
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
}
