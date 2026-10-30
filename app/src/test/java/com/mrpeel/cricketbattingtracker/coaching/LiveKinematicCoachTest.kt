package com.mrpeel.cricketbattingtracker.coaching

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class LiveKinematicCoachTest {

    private class FakeCoachingFeedback(
        override var coachingMode: CoachingMode = CoachingMode.STAGE_1_CALIBRATION,
        override var isEnabled: Boolean = true
    ) : LiveCoachingAudioFeedback {
        var lastSpokenCue: String? = null
        var lastPlayedEarcon: LiveShotFault? = null
        var speakCount = 0
        var earconCount = 0

        override fun speak(cue: String) {
            lastSpokenCue = cue
            speakCount++
        }

        override fun playEarcon(fault: LiveShotFault) {
            lastPlayedEarcon = fault
            earconCount++
        }

        fun reset() {
            lastSpokenCue = null
            lastPlayedEarcon = null
            speakCount = 0
            earconCount = 0
        }
    }

    // ─── Shot-Invariant Failure Mode Diagnosis Unit Tests ─────────────────────

    @Test
    fun testDiagnoseEarlyPeakDeceleration() {
        val coach = LiveKinematicCoach()
        val fault = coach.diagnoseShotInvariant(
            ShotInvariantMetrics(
                peakGyroRadS = 20.0f,
                speedKmh = 68.0f,
                velocityRetention = 0.58f,
                accelSlope = -0.28f,
                planeWobbleDeg = 7.5f,
                twistSpikeRatio = 0.20f,
                axialJerkRadS = 1.2f
            )
        )
        assertEquals(LiveShotFault.EARLY_PEAK_DECELERATION, fault)
        assertEquals("Swing through", fault.cue)
    }

    @Test
    fun testDiagnoseStalledReachPush() {
        val coach = LiveKinematicCoach()
        val fault = coach.diagnoseShotInvariant(
            ShotInvariantMetrics(
                peakGyroRadS = 12.5f,
                speedKmh = 42.5f,
                velocityRetention = 0.72f,
                accelSlope = -0.15f,
                planeWobbleDeg = 8.0f,
                twistSpikeRatio = 0.18f,
                axialJerkRadS = 0.9f
            )
        )
        assertEquals(LiveShotFault.STALLED_REACH_PUSH, fault)
        assertEquals("Let it come", fault.cue)
    }

    @Test
    fun testDiagnoseMidSwingPlaneLoop() {
        val coach = LiveKinematicCoach()
        val fault = coach.diagnoseShotInvariant(
            ShotInvariantMetrics(
                peakGyroRadS = 19.0f,
                speedKmh = 64.6f,
                velocityRetention = 0.92f,
                accelSlope = 0.12f,
                planeWobbleDeg = 25.4f,
                twistSpikeRatio = 0.25f,
                axialJerkRadS = 1.5f
            )
        )
        assertEquals(LiveShotFault.MID_SWING_PLANE_LOOP, fault)
        assertEquals("Watch the ball", fault.cue)
    }

    @Test
    fun testDiagnoseOutOfPlaneWipe() {
        val coach = LiveKinematicCoach()
        val fault = coach.diagnoseShotInvariant(
            ShotInvariantMetrics(
                peakGyroRadS = 21.0f,
                speedKmh = 71.4f,
                velocityRetention = 0.90f,
                accelSlope = 0.10f,
                planeWobbleDeg = 18.5f,
                twistSpikeRatio = 0.45f,
                axialJerkRadS = 2.1f
            )
        )
        assertEquals(LiveShotFault.OUT_OF_PLANE_WIPE, fault)
        assertEquals("Head to the ball", fault.cue)
    }

    @Test
    fun testDiagnoseLateWristRescue() {
        val coach = LiveKinematicCoach()
        val fault = coach.diagnoseShotInvariant(
            ShotInvariantMetrics(
                peakGyroRadS = 18.0f,
                speedKmh = 61.2f,
                velocityRetention = 0.88f,
                accelSlope = 0.08f,
                planeWobbleDeg = 14.2f,
                twistSpikeRatio = 0.62f,
                axialJerkRadS = 3.2f
            )
        )
        assertEquals(LiveShotFault.LATE_WRIST_RESCUE, fault)
        assertEquals("Roll smoothly", fault.cue)
    }

    @Test
    fun testDiagnoseImpactFaceTwist() {
        val coach = LiveKinematicCoach()
        val fault = coach.diagnoseShotInvariant(
            ShotInvariantMetrics(
                peakGyroRadS = 22.0f,
                speedKmh = 74.8f,
                velocityRetention = 0.76f,
                accelSlope = -0.05f,
                planeWobbleDeg = 9.5f,
                twistSpikeRatio = 0.35f,
                axialJerkRadS = 6.8f
            )
        )
        assertEquals(LiveShotFault.IMPACT_FACE_TWIST, fault)
        assertEquals("Tighten grip", fault.cue)
    }

    @Test
    fun testDiagnoseOverswingLossOfShape() {
        val coach = LiveKinematicCoach()
        val fault = coach.diagnoseShotInvariant(
            ShotInvariantMetrics(
                peakGyroRadS = 33.5f,
                speedKmh = 113.9f,
                velocityRetention = 0.85f,
                accelSlope = 0.10f,
                planeWobbleDeg = 17.0f,
                twistSpikeRatio = 0.30f,
                axialJerkRadS = 2.0f
            )
        )
        assertEquals(LiveShotFault.OVERSWING_LOSS_OF_SHAPE, fault)
        assertEquals("Hold your shape", fault.cue)
    }

    @Test
    fun testCleanFlickWithHighWristRollIsNotPenalized() {
        val coach = LiveKinematicCoach()
        // A clean Flick / Glance has high steady wrist roll, but stays on a consistent diagonal plane (wobble ~6.5°)
        // and accelerates right into impact (retention = 0.96). Must NEVER trigger a Cut or Wrist fault!
        val fault = coach.diagnoseShotInvariant(
            ShotInvariantMetrics(
                peakGyroRadS = 19.5f,
                speedKmh = 66.3f,
                velocityRetention = 0.96f,
                accelSlope = 0.15f,
                planeWobbleDeg = 6.5f,
                twistSpikeRatio = 0.42f,
                axialJerkRadS = 1.1f
            )
        )
        assertEquals(LiveShotFault.CLEAN_STROKE, fault)
        assertEquals("Solid", fault.cue)
    }

    @Test
    fun testHighSpeedOnPlanePowerShotIsCleanStroke() {
        val coach = LiveKinematicCoach()
        // Fast Pull / Power Drive (>31 rad/s) that remains on-plane (wobble 8.5°) with high retention (0.96)
        val fault = coach.diagnoseShotInvariant(
            ShotInvariantMetrics(
                peakGyroRadS = 34.0f,
                speedKmh = 115.6f,
                velocityRetention = 0.96f,
                accelSlope = 0.22f,
                planeWobbleDeg = 8.5f,
                twistSpikeRatio = 0.25f,
                axialJerkRadS = 1.4f
            )
        )
        assertEquals(LiveShotFault.CLEAN_STROKE, fault)
    }

    // ─── Stream Windowing & Stale Stance Tap Immunity Tests ──────────────────

    @Test
    fun testStalePracticeSwingDoesNotTriggerOnLaterStanceTap() {
        val fakeFeedback = FakeCoachingFeedback(coachingMode = CoachingMode.STAGE_1_CALIBRATION)
        val coach = LiveKinematicCoach(fakeFeedback, syncExecutionForTesting = true)

        var t = 1000L
        // 1. Batter takes a fast practice waggle (no ball impact)
        for (i in 0 until 25) {
            coach.processGyroSample(phoneMs = t, x = 1100f, y = 400f, z = 200f)
            t += 2
        }

        // 2. 3 seconds later, batter is stationary in stance and taps bat on ground (>10g)
        t += 3000L
        for (i in 0 until 25) {
            coach.processGyroSample(phoneMs = t, x = 20f, y = 10f, z = 5f)
            t += 2
        }
        coach.processAccSample(phoneMs = t, x = 12000f, y = 3000f, z = 2000f)

        // Because the [-220ms, 0ms] window before the tap had no active swing, nothing fires!
        assertNull(fakeFeedback.lastPlayedEarcon)
        assertEquals(0, fakeFeedback.earconCount)
    }

    // ─── Three-Stage Audio Modes Unit Tests ────────────────────────────────────

    private fun feedDeceleratingSwingAndImpact(coach: LiveKinematicCoach, startTimeMs: Long): Long {
        var t = startTimeMs
        // Early downswing peak (~22 rad/s = 1260 deg/s), then decelerates to ~10 rad/s (570 deg/s) before contact
        for (i in 0 until 24) {
            val xDeg = if (i < 10) 1260f else 570f
            coach.processGyroSample(phoneMs = t, x = xDeg, y = 80f, z = 40f)
            t += 2
        }
        coach.processAccSample(phoneMs = t, x = 11000f, y = 8000f, z = 2000f)
        return t
    }

    @Test
    fun testStage1CalibrationFiresBothEarconAndVoiceCue() {
        val fakeFeedback = FakeCoachingFeedback(coachingMode = CoachingMode.STAGE_1_CALIBRATION)
        val coach = LiveKinematicCoach(fakeFeedback, syncExecutionForTesting = true)

        feedDeceleratingSwingAndImpact(coach, 1000L)

        // In Stage 1: Both earcon AND TTS cue are played
        assertEquals(LiveShotFault.EARLY_PEAK_DECELERATION, fakeFeedback.lastPlayedEarcon)
        assertEquals("Swing through", fakeFeedback.lastSpokenCue)
        assertEquals(1, fakeFeedback.earconCount)
        assertEquals(1, fakeFeedback.speakCount)
    }

    @Test
    fun testStage2FlowStateFiresEarconOnlyOnFaults() {
        val fakeFeedback = FakeCoachingFeedback(coachingMode = CoachingMode.STAGE_2_FLOW_STATE)
        val coach = LiveKinematicCoach(fakeFeedback, syncExecutionForTesting = true)

        feedDeceleratingSwingAndImpact(coach, 1000L)

        // In Stage 2: Earcon plays, but TTS voice cue is completely silent!
        assertEquals(LiveShotFault.EARLY_PEAK_DECELERATION, fakeFeedback.lastPlayedEarcon)
        assertNull(fakeFeedback.lastSpokenCue)
        assertEquals(1, fakeFeedback.earconCount)
        assertEquals(0, fakeFeedback.speakCount)
    }

    @Test
    fun testStage2FlowStateFiresChimeAndSpeedOnCleanHit() {
        val fakeFeedback = FakeCoachingFeedback(coachingMode = CoachingMode.STAGE_2_FLOW_STATE)
        val coach = LiveKinematicCoach(fakeFeedback, syncExecutionForTesting = true)

        var t = 1000L
        for (i in 0 until 20) {
            // Accelerating smoothly on-plane into contact
            val xDeg = 800f + i * 20f
            coach.processGyroSample(phoneMs = t, x = xDeg, y = 120f, z = 60f)
            t += 2
        }
        coach.processAccSample(phoneMs = t, x = 12000f, y = 8000f, z = 4000f)

        // In Stage 2 on success: Earcon chime plays, followed by speed integer
        assertEquals(LiveShotFault.CLEAN_STROKE, fakeFeedback.lastPlayedEarcon)
        assertTrue(fakeFeedback.lastSpokenCue?.toIntOrNull() != null)
        assertEquals(1, fakeFeedback.earconCount)
        assertEquals(1, fakeFeedback.speakCount)
    }

    @Test
    fun testStage3SilentDiagnosticOnlyTriggersOnRepeatedFault() {
        val fakeFeedback = FakeCoachingFeedback(coachingMode = CoachingMode.STAGE_3_SILENT_DIAGNOSTIC)
        val coach = LiveKinematicCoach(fakeFeedback, syncExecutionForTesting = true)

        // Shot 1: First decelerating swing
        var t = feedDeceleratingSwingAndImpact(coach, 1000L)

        // Shot 1 is a one-off fault -> complete silence!
        assertNull(fakeFeedback.lastPlayedEarcon)
        assertEquals(0, fakeFeedback.earconCount)

        // Shot 2 (after cooldown): Second consecutive decelerating swing
        t += 2500L
        feedDeceleratingSwingAndImpact(coach, t)

        // Shot 2 repeated the same fault -> Earcon triggers! Voice remains silent.
        assertEquals(LiveShotFault.EARLY_PEAK_DECELERATION, fakeFeedback.lastPlayedEarcon)
        assertEquals(1, fakeFeedback.earconCount)
        assertEquals(0, fakeFeedback.speakCount)
    }

    @Test
    fun testImpactCooldownPreventsDuplicateTrigger() {
        val fakeFeedback = FakeCoachingFeedback(coachingMode = CoachingMode.STAGE_1_CALIBRATION)
        val coach = LiveKinematicCoach(fakeFeedback, syncExecutionForTesting = true)

        var t = 1000L
        for (i in 0 until 20) {
            coach.processGyroSample(phoneMs = t, x = 1030f, y = 10f, z = 10f)
            t += 2
        }
        coach.processAccSample(phoneMs = t, x = 12000f, y = 8000f, z = 4000f)
        assertEquals(1, fakeFeedback.earconCount)

        // Another impact 500ms later (within 1800ms cooldown)
        t += 500L
        for (i in 0 until 20) {
            coach.processGyroSample(phoneMs = t, x = 1030f, y = 10f, z = 10f)
            t += 2
        }
        coach.processAccSample(phoneMs = t, x = 12000f, y = 8000f, z = 4000f)

        // Cooldown prevents duplicate trigger
        assertEquals(1, fakeFeedback.earconCount)
    }

    @Test
    fun testStationaryTapDoesNotTriggerImpact() {
        val fakeFeedback = FakeCoachingFeedback(coachingMode = CoachingMode.STAGE_1_CALIBRATION)
        val coach = LiveKinematicCoach(fakeFeedback, syncExecutionForTesting = true)

        var t = 1000L
        // Stance tap: low gyro
        for (i in 0 until 20) {
            coach.processGyroSample(phoneMs = t, x = 28f, y = 5f, z = 5f)
            t += 2
        }
        coach.processAccSample(phoneMs = t, x = 11000f, y = 2000f, z = 1000f)

        assertNull(fakeFeedback.lastPlayedEarcon)
        assertEquals(0, fakeFeedback.earconCount)
    }
}
