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

    // ─── Repertoire Failure Mode Diagnosis Unit Tests ─────────────────────────

    @Test
    fun testDiagnosePullSkied() {
        val coach = LiveKinematicCoach()
        // Speed 75 km/h, horizontal plane with high roll / attack angle
        val fault = coach.diagnoseShot(
            speedKmh = 75.0f,
            gyroRadS = 16.6f,
            twistDeltaRadS = 5.2f,
            zRotationRate = 3.5f
        )
        assertEquals(LiveShotFault.PULL_SKIED, fault)
        assertEquals("Stay tall", fault.cue)
    }

    @Test
    fun testDiagnoseDriveScoop() {
        val coach = LiveKinematicCoach()
        // Speed 75 km/h, vertical drive where bottom wrist lifts upward (zRate > 3.0)
        val fault = coach.diagnoseShot(
            speedKmh = 75.0f,
            gyroRadS = 16.6f,
            twistDeltaRadS = 3.5f,
            zRotationRate = 3.8f
        )
        assertEquals(LiveShotFault.DRIVE_SCOOP, fault)
        assertEquals("Head to pitch", fault.cue)
    }

    @Test
    fun testDiagnosePunchScoop() {
        val coach = LiveKinematicCoach()
        // Speed 62 km/h, back foot punch hand path drop
        val fault = coach.diagnoseShot(
            speedKmh = 62.0f,
            gyroRadS = 13.8f,
            twistDeltaRadS = 4.5f,
            zRotationRate = 2.6f
        )
        assertEquals(LiveShotFault.PUNCH_SCOOP, fault)
        assertEquals("High hands", fault.cue)
    }

    @Test
    fun testDiagnoseDefenseHardHands() {
        val coach = LiveKinematicCoach()
        // Downswing speed 38 km/h on defense, low twist and low z rate
        val fault = coach.diagnoseShot(
            speedKmh = 38.0f,
            gyroRadS = 8.4f,
            twistDeltaRadS = 1.8f,
            zRotationRate = 0.5f
        )
        assertEquals(LiveShotFault.DEFENSE_HARD_HANDS, fault)
        assertEquals("Behind the knee", fault.cue)
    }

    @Test
    fun testDiagnoseGlidePushed() {
        val coach = LiveKinematicCoach()
        // Speed 42 km/h on deflection, moderate z rotation
        val fault = coach.diagnoseShot(
            speedKmh = 42.0f,
            gyroRadS = 9.3f,
            twistDeltaRadS = 2.0f,
            zRotationRate = 2.0f
        )
        assertEquals(LiveShotFault.GLIDE_PUSHED, fault)
        assertEquals("Give with it", fault.cue)
    }

    @Test
    fun testDiagnoseCutOverHit() {
        val coach = LiveKinematicCoach()
        // Speed 72 km/h, lateral twist delta 5.5 rad/s -> Cut over-hit
        val fault = coach.diagnoseShot(
            speedKmh = 72.0f,
            gyroRadS = 16.0f,
            twistDeltaRadS = 5.5f,
            zRotationRate = 2.2f
        )
        assertEquals(LiveShotFault.CUT_OVERHIT, fault)
        assertEquals("Behind point", fault.cue)
    }

    @Test
    fun testDiagnoseFlickLeadingEdge() {
        val coach = LiveKinematicCoach()
        // Speed 55 km/h, face closing early (zRate < -2.0)
        val fault = coach.diagnoseShot(
            speedKmh = 55.0f,
            gyroRadS = 12.2f,
            twistDeltaRadS = 3.8f,
            zRotationRate = -2.5f
        )
        assertEquals(LiveShotFault.FLICK_LEADING_EDGE, fault)
        assertEquals("Show the face", fault.cue)
    }

    @Test
    fun testDiagnoseDriveSlice() {
        val coach = LiveKinematicCoach()
        // Speed 82 km/h, massive handle jerk / twist delta = 7.2 rad/s -> Sliced drive
        val fault = coach.diagnoseShot(
            speedKmh = 82.0f,
            gyroRadS = 18.2f,
            twistDeltaRadS = 7.2f,
            zRotationRate = 0.8f
        )
        assertEquals(LiveShotFault.DRIVE_SLICE, fault)
        assertEquals("Lead with toe", fault.cue)
    }

    @Test
    fun testDiagnosePullChoked() {
        val coach = LiveKinematicCoach()
        // Speed 45 km/h, checked pull
        val fault = coach.diagnoseShot(
            speedKmh = 45.0f,
            gyroRadS = 10.0f,
            twistDeltaRadS = 2.5f,
            zRotationRate = 2.6f
        )
        assertEquals(LiveShotFault.PULL_CHOKED, fault)
        assertEquals("Clear the hip", fault.cue)
    }

    @Test
    fun testDiagnosePowerDriveOverSwing() {
        val coach = LiveKinematicCoach()
        // Speed 108 km/h -> Over-swung power drive
        val fault = coach.diagnoseShot(
            speedKmh = 108.0f,
            gyroRadS = 24.0f,
            twistDeltaRadS = 3.0f,
            zRotationRate = 0.5f
        )
        assertEquals(LiveShotFault.POWER_DRIVE_OVERSWING, fault)
        assertEquals("Freeze the head", fault.cue)
    }

    @Test
    fun testDiagnoseCleanStroke() {
        val coach = LiveKinematicCoach()
        // Speed 85 km/h, balanced vertical drive, low twist delta = 2.2 rad/s -> Clean stroke
        val fault = coach.diagnoseShot(
            speedKmh = 85.0f,
            gyroRadS = 18.9f,
            twistDeltaRadS = 2.2f,
            zRotationRate = 0.5f
        )
        assertEquals(LiveShotFault.CLEAN_STROKE, fault)
        assertEquals("Solid", fault.cue)
    }

    // ─── Three-Stage Audio Modes Unit Tests ────────────────────────────────────

    @Test
    fun testStage1CalibrationFiresBothEarconAndVoiceCue() {
        val fakeFeedback = FakeCoachingFeedback(coachingMode = CoachingMode.STAGE_1_CALIBRATION)
        val coach = LiveKinematicCoach(fakeFeedback, syncExecutionForTesting = true)

        var t = 1000L
        for (i in 0 until 20) {
            val yDeg = if (i < 10) 50f else 380f
            coach.processGyroSample(phoneMs = t, x = 850f, y = yDeg, z = 140f)
            t += 2
        }
        coach.processAccSample(phoneMs = t, x = 10000f, y = 9000f, z = 2000f)

        // In Stage 1: Both earcon AND TTS cue are played
        assertEquals(LiveShotFault.CUT_OVERHIT, fakeFeedback.lastPlayedEarcon)
        assertEquals("Behind point", fakeFeedback.lastSpokenCue)
        assertEquals(1, fakeFeedback.earconCount)
        assertEquals(1, fakeFeedback.speakCount)
    }

    @Test
    fun testStage2FlowStateFiresEarconOnlyOnFaults() {
        val fakeFeedback = FakeCoachingFeedback(coachingMode = CoachingMode.STAGE_2_FLOW_STATE)
        val coach = LiveKinematicCoach(fakeFeedback, syncExecutionForTesting = true)

        var t = 1000L
        for (i in 0 until 20) {
            val yDeg = if (i < 10) 50f else 380f
            coach.processGyroSample(phoneMs = t, x = 850f, y = yDeg, z = 140f)
            t += 2
        }
        coach.processAccSample(phoneMs = t, x = 10000f, y = 9000f, z = 2000f)

        // In Stage 2: Earcon plays, but TTS voice cue is completely silent!
        assertEquals(LiveShotFault.CUT_OVERHIT, fakeFeedback.lastPlayedEarcon)
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
            coach.processGyroSample(phoneMs = t, x = 1030f, y = 10f, z = 10f)
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

        var t = 1000L
        // Shot 1: First cut overhit
        for (i in 0 until 20) {
            val yDeg = if (i < 10) 50f else 380f
            coach.processGyroSample(phoneMs = t, x = 850f, y = yDeg, z = 140f)
            t += 2
        }
        coach.processAccSample(phoneMs = t, x = 10000f, y = 9000f, z = 2000f)

        // Shot 1 is a one-off fault -> complete silence!
        assertNull(fakeFeedback.lastPlayedEarcon)
        assertEquals(0, fakeFeedback.earconCount)

        // Shot 2 (after cooldown): Second consecutive cut overhit
        t += 2500L
        for (i in 0 until 20) {
            val yDeg = if (i < 10) 50f else 380f
            coach.processGyroSample(phoneMs = t, x = 850f, y = yDeg, z = 140f)
            t += 2
        }
        coach.processAccSample(phoneMs = t, x = 10000f, y = 9000f, z = 2000f)

        // Shot 2 repeated the same fault -> Earcon triggers! Voice remains silent.
        assertEquals(LiveShotFault.CUT_OVERHIT, fakeFeedback.lastPlayedEarcon)
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
