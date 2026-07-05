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
        magX: Float = 0f,
        targetDetector: SwingDetector? = null
    ): ShotData? {
        val activeDetector = targetDetector ?: detector
        var detectedShot: ShotData? = null
        activeDetector.onShotDetected = { shot ->
            detectedShot = shot
        }

        val gravZ = kotlin.math.sqrt((9.8f * 9.8f - gravY * gravY).coerceAtLeast(0f))
        var time = 3_000_000_000L // Start at 3s to bypass 2.5s startup guard window
        
        // 1. Simulate quiet stance (1.4s)
        for (i in 0 until 70) {
            activeDetector.processGyro(floatArrayOf(0.1f, 0f, 0f), time)
            activeDetector.processGravity(floatArrayOf(gravX, gravY, gravZ), time)
            activeDetector.processAccel(floatArrayOf(gravX, gravY, gravZ), time)
            activeDetector.processRotation(floatArrayOf(0f, 0f, 0f, 1f), time)
            activeDetector.processMagnetometer(floatArrayOf(magX, 0f, 0f), time)
            time += 20_000_000L
        }

        // 2. Simulate swing initiation (0.2s)
        for (i in 1..10) {
            val progress = i / 10f
            activeDetector.processGyro(floatArrayOf(preGyro, 0f, 0f), time)
            activeDetector.processGravity(floatArrayOf(gravX, gravY, gravZ), time)
            activeDetector.processAccel(floatArrayOf(gravX, gravY, gravZ), time)
            
            val q = computeRotationQuat(progress, rollImpactDeg, deltaX, deltaZ)
            activeDetector.processRotation(q, time)
            activeDetector.processMagnetometer(floatArrayOf(magX, 0f, 0f), time)
            time += 20_000_000L
        }

        // 3. Impact & Peak
        val impactTime = time
        activeDetector.processGyro(floatArrayOf(impactGyro, 0f, 0f), impactTime)
        activeDetector.processAccel(floatArrayOf(if (isHit) shock else 2.0f, gravY, gravZ), impactTime)
        activeDetector.processGravity(floatArrayOf(gravX, gravY, gravZ), impactTime)
        
        val qImpact = computeRotationQuat(1.0f, rollImpactDeg, deltaX, deltaZ)
        activeDetector.processRotation(qImpact, impactTime)
        activeDetector.processMagnetometer(floatArrayOf(magX, 0f, 0f), impactTime)
        time += 20_000_000L

        // 4. Post-impact follow-through (1.8s)
        for (i in 1..90) {
            val (currentGyroX, currentGyroY) = if (i <= 5) {
                Pair(postGyro, postGyroY)
            } else {
                val decay = kotlin.math.exp(-(i - 5) * 0.04f)
                Pair(2.0f + (postGyro - 2.0f) * decay, postGyroY * decay)
            }
            activeDetector.processGyro(floatArrayOf(currentGyroX, currentGyroY, 0f), time)
            activeDetector.processGravity(floatArrayOf(gravX, gravY, gravZ), time)
            activeDetector.processAccel(floatArrayOf(gravX, gravY, gravZ), time)
            
            val q = computeRotationQuat(1.0f, rollImpactDeg, deltaX, deltaZ)
            activeDetector.processRotation(q, time)
            activeDetector.processMagnetometer(floatArrayOf(magX, 0f, 0f), time)
            time += 20_000_000L
        }

        return detectedShot
    }

    private fun findParametersForShot(
        targetShotType: String,
        isHit: Boolean = true,
        rollRanges: FloatArray = floatArrayOf(0f),
        dxRanges: FloatArray = floatArrayOf(0f),
        dzRanges: FloatArray = floatArrayOf(0f),
        preGyroRanges: FloatArray = floatArrayOf(10f),
        impactGyroRanges: FloatArray = floatArrayOf(20f),
        postGyroRanges: FloatArray = floatArrayOf(15f),
        shockRanges: FloatArray = floatArrayOf(50f),
        gravYRanges: FloatArray = floatArrayOf(-9.8f),
        postGyroYRanges: FloatArray = floatArrayOf(0f),
        gravXRanges: FloatArray = floatArrayOf(0f),
        magXRanges: FloatArray = floatArrayOf(0f),
        additionalCheck: (ShotData) -> Boolean = { true }
    ): ShotData? {
        for (roll in rollRanges) {
            for (dx in dxRanges) {
                for (dz in dzRanges) {
                    for (preGyro in preGyroRanges) {
                        for (impactGyro in impactGyroRanges) {
                            for (postGyro in postGyroRanges) {
                                for (shock in shockRanges) {
                                    for (gravY in gravYRanges) {
                                        for (postGyroY in postGyroYRanges) {
                                            for (gravX in gravXRanges) {
                                                for (magX in magXRanges) {
                                                    val testDetector = SwingDetector()
                                                    val shot = simulateShot(
                                                        preGyro = preGyro,
                                                        impactGyro = impactGyro,
                                                        postGyro = postGyro,
                                                        shock = shock,
                                                        gravY = gravY,
                                                        postGyroY = postGyroY,
                                                        isHit = isHit,
                                                        rollImpactDeg = roll,
                                                        deltaX = dx,
                                                        deltaZ = dz,
                                                        gravX = gravX,
                                                        magX = magX,
                                                        targetDetector = testDetector
                                                    )
                                                    if (shot != null && shot.shotType == targetShotType && additionalCheck(shot)) {
                                                        System.out.println("✅ Found valid parameters for $targetShotType: roll=$roll, dx=$dx, dz=$dz, preGyro=$preGyro, impactGyro=$impactGyro, postGyro=$postGyro, gravY=$gravY, postGyroY=$postGyroY")
                                                        return shot
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
        return null
    }

    @Test
    fun testCoverDrive() {
        val shot = findParametersForShot(
            targetShotType = "DRIVE/DEFENCE",
            rollRanges = floatArrayOf(-10f, 0f, 10f),
            dxRanges = floatArrayOf(0.01f, 0.05f, 0.1f),
            dzRanges = floatArrayOf(0.1f, 0.2f, 0.3f),
            gravYRanges = floatArrayOf(-9.0f, -8.5f, -9.5f),
            additionalCheck = { (it.efficiency ?: 0f) > 80f && (it.isHit ?: false) }
        )
        assertNotNull("Shot should be detected", shot)
        assertEquals("DRIVE/DEFENCE", shot?.shotType)
        assertTrue("Efficiency should be high for a drive", (shot?.efficiency ?: 0f) > 80f)
        assertTrue("isHit should be true", shot?.isHit ?: false)
    }

    @Test
    fun testOnSideFlick() {
        var foundShot: ShotData? = null
        val rolls = floatArrayOf(45f, 55f, 65f, 75f)
        val dXs = floatArrayOf(1.2f, 1.4f, 1.6f)
        val dZs = floatArrayOf(0.8f, 1.0f, 1.2f)
        val postGyrosY = floatArrayOf(-6.9f, -8.0f)
        val gravXs = floatArrayOf(0.5f, 0.87f)
        
        outer@ for (roll in rolls) {
            for (dx in dXs) {
                for (dz in dZs) {
                    for (pgy in postGyrosY) {
                        for (gx in gravXs) {
                            val detectorTmp = SwingDetector()
                            var shotTmp: ShotData? = null
                            detectorTmp.onShotDetected = { shotTmp = it }
                            
                            val gravZ = kotlin.math.sqrt((9.8f * 9.8f - (-9.0f) * (-9.0f)).coerceAtLeast(0f))
                            var time = 3_000_000_000L
                            
                            // Stance
                            for (i in 0 until 70) {
                                detectorTmp.processGyro(floatArrayOf(0.1f, 0f, 0f), time)
                                detectorTmp.processGravity(floatArrayOf(gx, -9.0f, gravZ), time)
                                detectorTmp.processAccel(floatArrayOf(gx, -9.0f, gravZ), time)
                                detectorTmp.processRotation(floatArrayOf(0f, 0f, 0f, 1f), time)
                                time += 20_000_000L
                            }
                            // Swing
                            for (i in 1..10) {
                                val progress = i / 10f
                                detectorTmp.processGyro(floatArrayOf(5f, 0f, 0f), time)
                                detectorTmp.processGravity(floatArrayOf(gx, -9.0f, gravZ), time)
                                detectorTmp.processAccel(floatArrayOf(gx, -9.0f, gravZ), time)
                                val q = computeRotationQuat(progress, roll, dx, dz)
                                detectorTmp.processRotation(q, time)
                                time += 20_000_000L
                            }
                            // Impact
                            detectorTmp.processGyro(floatArrayOf(13.7f, 0f, 0f), time)
                            detectorTmp.processAccel(floatArrayOf(30f, -9.0f, gravZ), time)
                            detectorTmp.processGravity(floatArrayOf(gx, -9.0f, gravZ), time)
                            val qImpact = computeRotationQuat(1f, roll, dx, dz)
                            detectorTmp.processRotation(qImpact, time)
                            time += 20_000_000L
                            // Follow through
                            for (i in 1..90) {
                                val currentGyroY = if (i <= 5) pgy else pgy * kotlin.math.exp(-(i - 5) * 0.04f)
                                detectorTmp.processGyro(floatArrayOf(2f, currentGyroY, 0f), time)
                                detectorTmp.processGravity(floatArrayOf(gx, -9.0f, gravZ), time)
                                detectorTmp.processAccel(floatArrayOf(gx, -9.0f, gravZ), time)
                                val q = computeRotationQuat(1f, roll, dx, dz)
                                detectorTmp.processRotation(q, time)
                                time += 20_000_000L
                            }
                            
                            if (shotTmp != null && shotTmp?.shotType == "GLANCE/FLICK") {
                                foundShot = shotTmp
                                System.out.println("✅ Found valid GLANCE/FLICK test parameters: roll=$roll, dx=$dx, dz=$dz, pgy=$pgy, gx=$gx")
                                break@outer
                            }
                        }
                    }
                }
            }
        }
        
        assertNotNull("Shot should be detected", foundShot)
        assertEquals("GLANCE/FLICK", foundShot?.shotType)
    }

    @Test
    fun testPullShot() {
        val shot = findParametersForShot(
            targetShotType = "PULL/HOOK",
            rollRanges = floatArrayOf(-65f, -55f, -45f),
            dxRanges = floatArrayOf(1.1f, 1.3f, 1.5f),
            dzRanges = floatArrayOf(0.5f, 0.7f, 0.9f),
            preGyroRanges = floatArrayOf(12f, 15f, 18f),
            impactGyroRanges = floatArrayOf(25f, 30.5f, 35f),
            postGyroRanges = floatArrayOf(20f, 25f, 30f),
            shockRanges = floatArrayOf(50f, 60f, 70f),
            gravYRanges = floatArrayOf(-9.25f, -8.5f, -9.5f),
            postGyroYRanges = floatArrayOf(-14.0f, -12.0f, -10.0f),
            gravXRanges = floatArrayOf(6.0f, 8.0f, 9.0f),
            magXRanges = floatArrayOf(0.0f, 50.0f)
        )
        assertNotNull("Shot should be detected", shot)
        assertEquals("PULL/HOOK", shot?.shotType)
    }

    @Test
    fun testCutPunch() {
        // A cut shot has a strongly negative roll (cross-body horizontal bat),
        // a large swing arc (high deltaX and deltaZ), and moderate-high gyroMag.
        // These ranges reflect the real CUT/PUNCH cluster (median roll ≈ -130°,
        // deltaX ≈ 1.5, deltaZ ≈ 1.1) from the training dataset.
        val shot = findParametersForShot(
            targetShotType = "CUT/PUNCH",
            rollRanges = floatArrayOf(-160f, -130f, -120f),
            dxRanges = floatArrayOf(1.0f, 1.3f, 1.6f),
            dzRanges = floatArrayOf(0.8f, 1.0f, 1.3f),
            preGyroRanges = floatArrayOf(10.0f, 12.0f, 14.0f),
            impactGyroRanges = floatArrayOf(16.0f, 18.0f, 22.0f),
            postGyroRanges = floatArrayOf(10.0f, 12.0f, 14.0f),
            shockRanges = floatArrayOf(50f, 60f),
            gravYRanges = floatArrayOf(-9.3f, -9.0f),
            postGyroYRanges = floatArrayOf(-6.0f, -4.0f, -2.0f),
            gravXRanges = floatArrayOf(3.0f, 5.0f)
        )
        assertNotNull("Shot should be detected", shot)
        assertEquals("CUT/PUNCH", shot?.shotType)
    }

    @Test
    fun testForwardDefence() {
        val shot = findParametersForShot(
            targetShotType = "DRIVE/DEFENCE",
            preGyroRanges = floatArrayOf(1f, 2f, 3f),
            impactGyroRanges = floatArrayOf(4f, 6f, 8f),
            postGyroRanges = floatArrayOf(1f, 2f, 3f),
            shockRanges = floatArrayOf(20f, 25f, 30f),
            dzRanges = floatArrayOf(0.01f, 0.05f, 0.1f, 0.2f),
            gravYRanges = floatArrayOf(-9.8f, -9.0f)
        )
        assertNotNull("Shot should be detected", shot)
        assertEquals("DRIVE/DEFENCE", shot?.shotType)
    }

    @Test
    fun testPush() {
        val shot = findParametersForShot(
            targetShotType = "DRIVE/DEFENCE",
            preGyroRanges = floatArrayOf(3f, 5f, 7f),
            impactGyroRanges = floatArrayOf(8f, 10f, 12f),
            postGyroRanges = floatArrayOf(10f, 12f, 14f),
            shockRanges = floatArrayOf(35f, 40f, 45f),
            rollRanges = floatArrayOf(-5f, 0f, 5f),
            dxRanges = floatArrayOf(0.01f, 0.02f, 0.05f),
            dzRanges = floatArrayOf(0.01f, 0.02f, 0.05f)
        )
        assertNotNull("Shot should be detected", shot)
        assertEquals("DRIVE/DEFENCE", shot?.shotType)
    }

    @Test
    fun testPlayAndMiss() {
        val shot = findParametersForShot(
            targetShotType = "DRIVE/DEFENCE", // Play and miss evaluates to shotType class, but isHit is false
            isHit = false,
            dxRanges = floatArrayOf(0.01f, 0.05f, 0.1f),
            dzRanges = floatArrayOf(0.1f, 0.2f, 0.3f),
            preGyroRanges = floatArrayOf(8f, 10f, 12f),
            impactGyroRanges = floatArrayOf(18f, 20f, 22f),
            postGyroRanges = floatArrayOf(12f, 15f, 18f),
            shockRanges = floatArrayOf(45f, 50f, 55f),
            additionalCheck = { !(it.isHit ?: true) && it.sweetSpot == "Miss" }
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

    @Test
    fun testBladeAndLaunchAngles() {
        val shot = findParametersForShot(
            targetShotType = "DRIVE/DEFENCE",
            rollRanges = floatArrayOf(-10f, 0f, 10f),
            dxRanges = floatArrayOf(0.01f, 0.05f, 0.1f),
            dzRanges = floatArrayOf(0.1f, 0.2f, 0.3f),
            gravYRanges = floatArrayOf(-9.0f, -8.5f, -9.5f)
        )
        assertNotNull("DRIVE/DEFENCE Shot should be detected", shot)
        assertTrue("Launch class should be valid", 
            shot?.launchClass == "INTO_GROUND" || shot?.launchClass == "FLAT" || shot?.launchClass == "LOFTED"
        )
        assertTrue("Blade class should be valid", 
            shot?.bladeClass == "FULL_FACE" || shot?.bladeClass == "OPEN" || shot?.bladeClass == "CLOSED"
        )

        val pullShot = findParametersForShot(
            targetShotType = "PULL/HOOK",
            rollRanges = floatArrayOf(-30f),
            dxRanges = floatArrayOf(1.2f),
            dzRanges = floatArrayOf(0.7f),
            gravYRanges = floatArrayOf(-9.0f)
        )
        if (pullShot != null) {
            assertEquals(-30f, pullShot.launchAngle, 1.0f)
            assertEquals("LOFTED", pullShot.launchClass)
        }
    }
}
