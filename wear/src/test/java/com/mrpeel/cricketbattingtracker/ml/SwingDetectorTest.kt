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
        deltaZ: Float = 0f
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
            detector.processGravity(floatArrayOf(0f, gravY, gravZ), time)
            detector.processAccel(floatArrayOf(0f, gravY, gravZ), time)
            detector.processRotation(floatArrayOf(0f, 0f, 0f, 1f), time)
            time += 20_000_000L
        }

        // 2. Simulate swing initiation (0.2s)
        for (i in 1..10) {
            val progress = i / 10f
            detector.processGyro(floatArrayOf(preGyro, 0f, 0f), time)
            detector.processGravity(floatArrayOf(0f, gravY, gravZ), time)
            detector.processAccel(floatArrayOf(0f, gravY, gravZ), time)
            
            val q = computeRotationQuat(progress, rollImpactDeg, deltaX, deltaZ)
            detector.processRotation(q, time)
            time += 20_000_000L
        }

        // 3. Impact & Peak
        val impactTime = time
        detector.processGyro(floatArrayOf(impactGyro, 0f, 0f), impactTime)
        detector.processAccel(floatArrayOf(if (isHit) shock else 2.0f, 0f, 0f), impactTime)
        detector.processGravity(floatArrayOf(0f, gravY, gravZ), impactTime)
        
        val qImpact = computeRotationQuat(1.0f, rollImpactDeg, deltaX, deltaZ)
        detector.processRotation(qImpact, impactTime)
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
            detector.processGravity(floatArrayOf(0f, gravY, gravZ), time)
            detector.processAccel(floatArrayOf(0f, gravY, gravZ), time)
            
            val q = computeRotationQuat(1.0f, rollImpactDeg, deltaX, deltaZ)
            detector.processRotation(q, time)
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
            impactGyro = 10f, 
            postGyro = 15f,  // keep maxGyro <= 22.12 to stay in GLANCE/FLICK
            shock = 30f, 
            postGyroY = 1.0f,
            rollImpactDeg = 30f, // positive roll for pronation (top hand left)
            deltaX = 0.2f, 
            deltaZ = 0.1f
        )
        assertNotNull("Shot should be detected", shot)
        assertEquals("GLANCE/FLICK", shot?.shotType)
        // With maxGyro = sqrt(15^2 + 1^2) = 15.033f, speedKmh = 15.033 * 0.68 * 3.6 * 1.30 = 47.84 km/h
        assertEquals(47.84f, shot?.speedKmh ?: 0f, 0.1f)
    }

    @Test
    fun testPullShot() {
        val shot = simulateShot(
            preGyro = 10f, 
            impactGyro = 20f, 
            postGyro = 15f, 
            shock = 60f, 
            postGyroY = 5f,
            rollImpactDeg = -30f,
            deltaX = 0.5f
        )
        assertNotNull("Shot should be detected", shot)
        assertEquals("PULL/HOOK", shot?.shotType)
    }

    @Test
    fun testCutPunch() {
        val shot = simulateShot(
            preGyro = 10f, 
            impactGyro = 20f, 
            postGyro = 15f, 
            shock = 60f, 
            postGyroY = 5f,
            rollImpactDeg = -10f,
            deltaX = 0.2f
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

        // 3. Restore quiet stance (1.8s) - 90 samples
        for (i in 0 until 90) {
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

        // 2. Simulate longer failure exceeding tolerance (1.5s) - 75 samples
        for (i in 0 until 75) {
            detector.processGyro(floatArrayOf(5.0f, 0f, 0f), time)
            detector.processGravity(floatArrayOf(0f, gravY, gravZ), time)
            detector.processAccel(floatArrayOf(0f, gravY, gravZ), time)
            detector.processRotation(floatArrayOf(0f, 0f, 0f, 1f), time)
            time += 20_000_000L
        }

        // 3. Restore quiet stance (800ms) - 40 samples (not enough to lock since it reset completely and only has 800ms < 1.2s)
        for (i in 0 until 40) {
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
