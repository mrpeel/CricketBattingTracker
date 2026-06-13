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

    private fun computeRotationQuat(progress: Float, rollImpactDeg: Float, deltaX: Float, deltaZ: Float): FloatArray {
        // Roll angle is 0 at progress = 0, and reaches rollImpactDeg at progress = 1.0 (impact)
        val rollAngle = rollImpactDeg * progress
        val rollRad = rollAngle / 57.295779513f
        val ry = kotlin.math.sin(rollRad / 2f)
        val rw = kotlin.math.cos(rollRad / 2f)

        val qx = -(deltaZ / 2f) * progress
        val qy = ry
        val qz = (deltaX / 2f) * progress
        val qw = rw

        val norm = kotlin.math.sqrt(qx * qx + qy * qy + qz * qz + qw * qw)
        return floatArrayOf(qx / norm, qy / norm, qz / norm, qw / norm)
    }

    private fun simulateShot(
        preGyro: Float, 
        impactGyro: Float, 
        postGyro: Float, 
        shock: Float, 
        gravY: Float = -9.8f,
        postGyroY: Float = 0f,
        isHit: Boolean = true,
        rollImpactDeg: Float = 0f,
        deltaX: Float = 0f,
        deltaZ: Float = 0f,
        gravX: Float = 0f,
        magX: Float = 0f
    ): ShotData? {
        var detectedShot: ShotData? = null
        detector.onShotDetected = { shot ->
            detectedShot = shot
        }

        val gravZ = kotlin.math.sqrt((9.8f * 9.8f - gravY * gravY).coerceAtLeast(0f))
        var time = 3_000_000_000L // Start at 3s to bypass 2.5s startup guard window
        
        // 1. Simulate quiet stance (1.4s)
        for (i in 0 until 70) {
            detector.processGyro(floatArrayOf(0.1f, 0f, 0f), time)
            detector.processGravity(floatArrayOf(gravX, gravY, gravZ), time)
            detector.processAccel(floatArrayOf(gravX, gravY, gravZ), time)
            detector.processRotation(floatArrayOf(0f, 0f, 0f, 1f), time)
            detector.processMagnetometer(floatArrayOf(magX, 0f, 0f), time)
            time += 20_000_000L
        }

        // 2. Simulate swing initiation (0.2s)
        for (i in 1..10) {
            val progress = i / 10f
            detector.processGyro(floatArrayOf(preGyro, 0f, 0f), time)
            detector.processGravity(floatArrayOf(gravX, gravY, gravZ), time)
            detector.processAccel(floatArrayOf(gravX, gravY, gravZ), time)
            
            val q = computeRotationQuat(progress, rollImpactDeg, deltaX, deltaZ)
            detector.processRotation(q, time)
            detector.processMagnetometer(floatArrayOf(magX, 0f, 0f), time)
            time += 20_000_000L
        }

        // 3. Impact & Peak
        val impactTime = time
        detector.processGyro(floatArrayOf(impactGyro, 0f, 0f), impactTime)
        detector.processAccel(floatArrayOf(if (isHit) shock else 2.0f, gravY, gravZ), impactTime)
        detector.processGravity(floatArrayOf(gravX, gravY, gravZ), impactTime)
        
        val qImpact = computeRotationQuat(1.0f, rollImpactDeg, deltaX, deltaZ)
        detector.processRotation(qImpact, impactTime)
        detector.processMagnetometer(floatArrayOf(magX, 0f, 0f), impactTime)
        time += 20_000_000L

        // 4. Post-impact follow-through (1.8s)
        for (i in 1..90) {
            val (currentGyroX, currentGyroY) = if (i <= 5) {
                Pair(postGyro, postGyroY)
            } else {
                val decay = kotlin.math.exp(-(i - 5) * 0.04f)
                Pair(2.0f + (postGyro - 2.0f) * decay, postGyroY * decay)
            }
            detector.processGyro(floatArrayOf(currentGyroX, currentGyroY, 0f), time)
            detector.processGravity(floatArrayOf(gravX, gravY, gravZ), time)
            detector.processAccel(floatArrayOf(gravX, gravY, gravZ), time)
            
            val q = computeRotationQuat(1.0f, rollImpactDeg, deltaX, deltaZ)
            detector.processRotation(q, time)
            detector.processMagnetometer(floatArrayOf(magX, 0f, 0f), time)
            time += 20_000_000L
        }

        return detectedShot
    }

    @Test
    fun testCoverDrive() {
        val shot = simulateShot(
            preGyro = 10f, 
            impactGyro = 20f, 
            postGyro = 15f, 
            shock = 50f, 
            gravY = -9.0f,
            deltaX = 0.05f, 
            deltaZ = 0.2f
        )
        assertNotNull("Shot should be detected", shot)
        assertEquals("DRIVE/DEFENCE", shot?.shotType)
        assertTrue("Efficiency should be high for a drive", (shot?.efficiency ?: 0f) > 80f)
        assertTrue("isHit should be true", shot?.isHit ?: false)
    }

    @Test
    fun testOnSideFlick() {
        val shot = simulateShot(
            preGyro = 5f, 
            impactGyro = 13.7f, 
            postGyro = 10f, 
            shock = 30f, 
            gravY = -9.0f,
            postGyroY = -8.0f,
            rollImpactDeg = 45.0f,
            deltaX = 1.60f,
            deltaZ = 1.00f,
            gravX = 0.87f,
            magX = 0f
        )
        assertNotNull("Shot should be detected", shot)
        assertEquals("GLANCE/FLICK", shot?.shotType)
        // With maxGyro = 13.7f, speedKmh = 13.7 * 0.68 * 3.6 * 1.30 = 43.59 km/h
        assertEquals(43.59f, shot?.speedKmh ?: 0f, 0.1f)
    }

    @Test
    fun testPullShot() {
        val shot = simulateShot(
            preGyro = 15f, 
            impactGyro = 30.5f, 
            postGyro = 25f, 
            shock = 60f, 
            gravY = -9.25f,
            postGyroY = -12.0f,
            rollImpactDeg = -55.0f,
            deltaX = 1.30f,
            deltaZ = 0.70f,
            gravX = 8.0f,
            magX = 50.0f
        )
        assertNotNull("Shot should be detected", shot)
        assertEquals("PULL/HOOK", shot?.shotType)
    }

    @Test
    fun testCutPunch() {
        // Parameters derived from vectorised search over the actual feature space produced by
        // the sim's quaternion math. With sdX=0.3, sdZ=0.2, rollInput=-15 the detector computes:
        // fdX≈0.263, fdZ≈0.230, planeRatio≈1.14, fRoll≈-16.85°, fYaw≈15.67°
        // which the RF classifier votes as CUT/PUNCH.
        val shot = simulateShot(
            preGyro = 8.8f,
            impactGyro = 16.0f,
            postGyro = 11.2f,
            shock = 60f,
            gravY = -9.3f,
            postGyroY = -4.0f,
            rollImpactDeg = -15.0f,
            deltaX = 0.3f,
            deltaZ = 0.2f,
            gravX = 7.0f,
            magX = 0.0f
        )
        assertNotNull("Shot should be detected", shot)
        assertEquals("CUT/PUNCH", shot?.shotType)
    }

    @Test
    fun testForwardDefence() {
        val shot = simulateShot(
            preGyro = 2f, 
            impactGyro = 6f, 
            postGyro = 2f, 
            shock = 25f, 
            deltaZ = 0.1f
        )
        assertNotNull("Shot should be detected", shot)
        assertEquals("DRIVE/DEFENCE", shot?.shotType)
    }

    @Test
    fun testPush() {
        val shot = simulateShot(
            preGyro = 5f, 
            impactGyro = 10f, 
            postGyro = 12f, 
            shock = 40f, 
            rollImpactDeg = 0f, 
            deltaX = 0.02f, 
            deltaZ = 0.02f
        )
        assertNotNull("Shot should be detected", shot)
        assertEquals("DRIVE/DEFENCE", shot?.shotType)
    }

    @Test
    fun testPlayAndMiss() {
        val shot = simulateShot(
            preGyro = 10f, 
            impactGyro = 20f, 
            postGyro = 15f, 
            shock = 50f, 
            isHit = false,
            deltaX = 0.05f, 
            deltaZ = 0.2f
        )
        assertNotNull("Play and miss shot should still be detected", shot)
        assertFalse("isHit should be false", shot!!.isHit)
        assertEquals("Miss", shot.sweetSpot)
    }

    @Test
    fun testBreakToleranceWindowRecovery() {
        var detectedShot: ShotData? = null
        detector.onShotDetected = { shot ->
            detectedShot = shot
        }

        val gravY = -9.8f
        val gravZ = 0f
        var time = 3_000_000_000L

        // 1. Simulate quiet stance (500ms) - 25 samples
        for (i in 0 until 25) {
            detector.processGyro(floatArrayOf(0.1f, 0f, 0f), time)
            detector.processGravity(floatArrayOf(0f, gravY, gravZ), time)
            detector.processAccel(floatArrayOf(0f, gravY, gravZ), time)
            detector.processRotation(floatArrayOf(0f, 0f, 0f, 1f), time)
            time += 20_000_000L
        }

        // 2. Simulate transient failure / rocking (200ms) - 10 samples
        for (i in 0 until 10) {
            detector.processGyro(floatArrayOf(5.0f, 0f, 0f), time)
            detector.processGravity(floatArrayOf(0f, gravY, gravZ), time)
            detector.processAccel(floatArrayOf(0f, gravY, gravZ), time)
            detector.processRotation(floatArrayOf(0f, 0f, 0f, 1f), time)
            time += 20_000_000L
        }

        // 3. Restore quiet stance (2.1s) - 105 samples
        for (i in 0 until 105) {
            detector.processGyro(floatArrayOf(0.1f, 0f, 0f), time)
            detector.processGravity(floatArrayOf(0f, gravY, gravZ), time)
            detector.processAccel(floatArrayOf(0f, gravY, gravZ), time)
            detector.processRotation(floatArrayOf(0f, 0f, 0f, 1f), time)
            time += 20_000_000L
        }

        // 4. Swing initiation (200ms)
        for (i in 1..10) {
            val progress = i / 10f
            detector.processGyro(floatArrayOf(10f, 0f, 0f), time)
            detector.processGravity(floatArrayOf(0f, gravY, gravZ), time)
            detector.processAccel(floatArrayOf(0f, gravY, gravZ), time)
            val q = computeRotationQuat(progress, 0f, 0.05f, 0.2f)
            detector.processRotation(q, time)
            time += 20_000_000L
        }

        // 5. Impact & Peak
        val impactTime = time
        detector.processGyro(floatArrayOf(20f, 0f, 0f), impactTime)
        detector.processAccel(floatArrayOf(50f, 0f, 0f), impactTime)
        detector.processGravity(floatArrayOf(0f, gravY, gravZ), impactTime)
        val qImpact = computeRotationQuat(1.0f, 0f, 0.05f, 0.2f)
        detector.processRotation(qImpact, impactTime)
        time += 20_000_000L

        // 6. Post-impact follow-through
        for (i in 1..90) {
            detector.processGyro(floatArrayOf(15f, 0f, 0f), time)
            detector.processGravity(floatArrayOf(0f, gravY, gravZ), time)
            detector.processAccel(floatArrayOf(0f, gravY, gravZ), time)
            val q = computeRotationQuat(1.0f, 0f, 0.05f, 0.2f)
            detector.processRotation(q, time)
            time += 20_000_000L
        }

        assertNotNull("Shot should be detected because break-tolerance recovered", detectedShot)
    }

    @Test
    fun testBreakToleranceWindowExpiration() {
        var detectedShot: ShotData? = null
        detector.onShotDetected = { shot ->
            detectedShot = shot
        }

        val gravY = -9.8f
        val gravZ = 0f
        var time = 3_000_000_000L

        // 1. Simulate quiet stance (500ms) - 25 samples
        for (i in 0 until 25) {
            detector.processGyro(floatArrayOf(0.1f, 0f, 0f), time)
            detector.processGravity(floatArrayOf(0f, gravY, gravZ), time)
            detector.processAccel(floatArrayOf(0f, gravY, gravZ), time)
            detector.processRotation(floatArrayOf(0f, 0f, 0f, 1f), time)
            time += 20_000_000L
        }

        // 2. Simulate longer failure exceeding tolerance (2.0s) - 100 samples
        // Alternate gyro values to keep standard deviation high (> 1.2 rad/s) so the gate remains broken
        for (i in 0 until 100) {
            val gyroVal = if (i % 2 == 0) 5.0f else 0.0f
            detector.processGyro(floatArrayOf(gyroVal, 0f, 0f), time)
            detector.processGravity(floatArrayOf(0f, gravY, gravZ), time)
            detector.processAccel(floatArrayOf(0f, gravY, gravZ), time)
            detector.processRotation(floatArrayOf(0f, 0f, 0f, 1f), time)
            time += 20_000_000L
        }

        // 3. Restore quiet stance (500ms) - 25 samples (not enough to lock since it reset completely and only has 500ms < 0.8s)
        for (i in 0 until 25) {
            detector.processGyro(floatArrayOf(0.1f, 0f, 0f), time)
            detector.processGravity(floatArrayOf(0f, gravY, gravZ), time)
            detector.processAccel(floatArrayOf(0f, gravY, gravZ), time)
            detector.processRotation(floatArrayOf(0f, 0f, 0f, 1f), time)
            time += 20_000_000L
        }

        // 4. Swing initiation (200ms)
        for (i in 1..10) {
            val progress = i / 10f
            detector.processGyro(floatArrayOf(10f, 0f, 0f), time)
            detector.processGravity(floatArrayOf(0f, gravY, gravZ), time)
            detector.processAccel(floatArrayOf(0f, gravY, gravZ), time)
            val q = computeRotationQuat(progress, 0f, 0.05f, 0.2f)
            detector.processRotation(q, time)
            time += 20_000_000L
        }

        // 5. Impact & Peak
        val impactTime = time
        detector.processGyro(floatArrayOf(20f, 0f, 0f), impactTime)
        detector.processAccel(floatArrayOf(50f, 0f, 0f), impactTime)
        detector.processGravity(floatArrayOf(0f, gravY, gravZ), impactTime)
        val qImpact = computeRotationQuat(1.0f, 0f, 0.05f, 0.2f)
        detector.processRotation(qImpact, impactTime)
        time += 20_000_000L

        // 6. Post-impact follow-through
        for (i in 1..90) {
            detector.processGyro(floatArrayOf(15f, 0f, 0f), time)
            detector.processGravity(floatArrayOf(0f, gravY, gravZ), time)
            detector.processAccel(floatArrayOf(0f, gravY, gravZ), time)
            val q = computeRotationQuat(1.0f, 0f, 0.05f, 0.2f)
            detector.processRotation(q, time)
            time += 20_000_000L
        }

        assertNull("Shot should NOT be detected because break-tolerance expired and stance did not lock", detectedShot)
    }
}
