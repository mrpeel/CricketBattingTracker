package com.mrpeel.cricketbattingtracker.ml

import org.junit.Assert.*
import org.junit.Before
import org.junit.Test
import com.mrpeel.cricketbattingtracker.services.ShotData

class SwingDetectorTest {

    private lateinit var detector: SwingDetector

    @Before
    fun setUp() {
        detector = SwingDetector()
    }

    private fun simulateShot(
        preGyro: Float, 
        impactGyro: Float, 
        postGyro: Float, 
        shock: Float, 
        gravY: Float = 9.8f,
        postGyroY: Float = 0f
    ): ShotData? {
        var detectedShot: ShotData? = null
        detector.onShotDetected = { shot ->
            detectedShot = shot
        }

        var time = 1_000_000_000L // Start at 1s
        
        // Fill pre-window (0.6s)
        for (i in 0 until 30) {
            detector.processGyro(floatArrayOf(preGyro, 0f, 0f), time)
            detector.processGravity(floatArrayOf(0f, gravY, 0f), time)
            detector.processAccel(floatArrayOf(0f, 0f, 9.8f), time)
            time += 20_000_000L // 20ms = 50Hz
        }

        // Impact
        val impactTime = time
        detector.processGyro(floatArrayOf(impactGyro, 0f, 0f), impactTime)
        detector.processAccel(floatArrayOf(shock, 0f, 0f), impactTime)
        detector.processGravity(floatArrayOf(0f, gravY, 0f), impactTime)

        // Fill post-window (0.6s)
        for (i in 0 until 30) {
            time += 20_000_000L
            detector.processGyro(floatArrayOf(postGyro, postGyroY, 0f), time)
            detector.processGravity(floatArrayOf(0f, gravY, 0f), time)
            detector.processAccel(floatArrayOf(0f, 0f, 9.8f), time)
        }

        return detectedShot
    }

    @Test
    fun testCoverDrive() {
        // High impact gyro, low snap ratio, vertical bat (gravY ~ 9.8)
        val shot = simulateShot(preGyro = 10f, impactGyro = 20f, postGyro = 15f, shock = 50f, gravY = 9.0f)
        assertNotNull(shot)
        assertEquals("COVER DRIVE", shot?.shotType)
        assertTrue("Efficiency should be high for a drive", (shot?.efficiency ?: 0f) > 80f)
    }

    @Test
    fun testOnSideFlick() {
        // High post-gyro relative to pre-gyro (snap ratio)
        val shot = simulateShot(preGyro = 5f, impactGyro = 10f, postGyro = 25f, shock = 30f)
        assertNotNull(shot)
        assertEquals("ON-SIDE FLICK", shot?.shotType)
        assertTrue("Speed should be corrected downward for flick", (shot?.speedKmh ?: 100f) < 40f)
    }

    @Test
    fun testPullShot() {
        // High wrist roll (Gyro Y)
        val shot = simulateShot(preGyro = 10f, impactGyro = 20f, postGyro = 20f, shock = 60f, postGyroY = 10f) // 10 rad/s roll
        assertNotNull(shot)
        assertEquals("PULL SHOT", shot?.shotType)
    }

    @Test
    fun testForwardDefence() {
        // Low gyro magnitude overall
        val shot = simulateShot(preGyro = 2f, impactGyro = 3f, postGyro = 2f, shock = 10f)
        assertNotNull(shot)
        assertEquals("DEFENCE", shot?.shotType)
    }

    @Test
    fun testSweepShot() {
        // Horizontal bat (gravY is low, gravX or Z is high)
        // In our simple calc_angle, angle = acos(y/mag). If y=0, angle=90.
        val shot = simulateShot(preGyro = 10f, impactGyro = 15f, postGyro = 15f, shock = 40f, gravY = 0f)
        assertNotNull(shot)
        assertEquals("SWEEP", shot?.shotType)
    }
}
