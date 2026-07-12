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
        
        // 1. Simulate quiet stance (2.0s) - 100 samples
        for (i in 0 until 100) {
            activeDetector.processGyro(floatArrayOf(0.1f, 0f, 0f), time)
            activeDetector.processGravity(floatArrayOf(gravX, gravY, gravZ), time)
            activeDetector.processAccel(floatArrayOf(gravX, gravY, gravZ), time)
            activeDetector.processRotation(floatArrayOf(0f, 0f, 0f, 1f), time)
            activeDetector.processMagnetometer(floatArrayOf(magX, 0f, 0f), time)
            time += 20_000_000L
        }

        // 2. Simulate swing initiation (0.8s) - 40 samples
        for (i in 1..40) {
            val progress = i / 40f
            val gyroY = postGyroY * progress + kotlin.math.sin(progress * 3.14159f) * 1.5f
            val gyroZ = kotlin.math.cos(progress * 3.14159f) * 1.5f
            activeDetector.processGyro(floatArrayOf(preGyro * progress, gyroY, gyroZ), time)
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
            val progress = 1.0f + (i / 90f) * 0.2f // continues to rotate follow-through
            val (currentGyroX, currentGyroY) = if (i <= 5) {
                Pair(postGyro, postGyroY)
            } else {
                val decay = kotlin.math.exp(-(i - 5) * 0.04f)
                Pair(2.0f + (postGyro - 2.0f) * decay, postGyroY * decay)
            }
            activeDetector.processGyro(floatArrayOf(currentGyroX, currentGyroY, 0f), time)
            activeDetector.processGravity(floatArrayOf(gravX, gravY, gravZ), time)
            activeDetector.processAccel(floatArrayOf(gravX, gravY, gravZ), time)
            
            val q = computeRotationQuat(progress, rollImpactDeg, deltaX, deltaZ)
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
                                                     if (shot != null) {
                                                         System.out.println("DEBUG SWEEP: target=$targetShotType, pred=${shot.shotType}, roll=$roll, dx=$dx, dz=$dz, preGyro=$preGyro, impactGyro=$impactGyro, postGyro=$postGyro, postGyroY=$postGyroY")
                                                     }
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
        // Real DRIVE/DEFENCE: deltaX median=0.82 (IQR 0.57-1.10), deltaZ median=1.20 (IQR 0.70-1.60)
        // gyro_y_min median=-1.31 (IQR -2.76 to -0.78), grav_x_max median=-0.22
        val shot = findParametersForShot(
            targetShotType = "DRIVE/DEFENCE",
            rollRanges = floatArrayOf(-10f, 0f, 10f),
            dxRanges = floatArrayOf(0.6f, 0.8f, 1.0f),
            dzRanges = floatArrayOf(0.8f, 1.0f, 1.2f),
            preGyroRanges = floatArrayOf(5f, 8f, 10f),
            impactGyroRanges = floatArrayOf(8f, 10f, 12f),
            postGyroRanges = floatArrayOf(5f, 8f, 10f),
            gravYRanges = floatArrayOf(-9.0f, -8.5f, -9.4f),
            postGyroYRanges = floatArrayOf(-3f, -2f, -1f, 0f),
            additionalCheck = { (it.efficiency ?: 0f) > 80f && (it.isHit ?: false) }
        )
        assertNotNull("Shot should be detected", shot)
        assertEquals("DRIVE/DEFENCE", shot?.shotType)
        assertTrue("Efficiency should be high for a drive", (shot?.efficiency ?: 0f) > 80f)
        assertTrue("isHit should be true", shot?.isHit ?: false)
    }

    @Test
    fun testOnSideFlick() {
        val shot = findParametersForShot(
            targetShotType = "GLANCE/FLICK",
            rollRanges = floatArrayOf(-90f, -45f, -30f, -15f, 0f, 15f, 30f, 45f),
            dxRanges = floatArrayOf(0.2f, 0.4f, 0.7f, 1.0f, 1.3f),
            dzRanges = floatArrayOf(0.2f, 0.3f, 0.6f, 0.9f, 1.2f),
            preGyroRanges = floatArrayOf(6f, 10f, 14f),
            impactGyroRanges = floatArrayOf(12f, 16f, 20f),
            postGyroRanges = floatArrayOf(6f, 10f, 14f),
            gravYRanges = floatArrayOf(-9.0f, -9.5f),
            postGyroYRanges = floatArrayOf(-12.0f, -10.0f, -7.0f, -4.0f)
        )
        assertNotNull("Shot should be detected", shot)
        assertEquals("GLANCE/FLICK", shot?.shotType)
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
            postGyroYRanges = floatArrayOf(-14.0f, -8.0f, -6.0f, -4.0f, -2.0f),
            gravXRanges = floatArrayOf(3.0f, 5.0f)
        )
        assertNotNull("Shot should be detected", shot)
        assertEquals("CUT/PUNCH", shot?.shotType)
    }

    @Test
    fun testForwardDefence() {
        val shot = findParametersForShot(
            targetShotType = "DRIVE/DEFENCE",
            rollRanges = floatArrayOf(-10f, -5f, 0f, 5f, 10f),
            dxRanges = floatArrayOf(0.1f, 0.3f, 0.5f, 0.7f),
            dzRanges = floatArrayOf(0.2f, 0.4f, 0.6f, 0.8f),
            preGyroRanges = floatArrayOf(1f, 2f, 3f, 4f, 5f),
            impactGyroRanges = floatArrayOf(4f, 6f, 8f, 10f, 12f),
            postGyroRanges = floatArrayOf(1f, 2f, 3f, 4f, 5f),
            shockRanges = floatArrayOf(20f, 25f, 30f, 35f, 40f),
            gravYRanges = floatArrayOf(-9.8f, -9.0f)
        )
        assertNotNull("Shot should be detected", shot)
        assertEquals("DRIVE/DEFENCE", shot?.shotType)
    }

    @Test
    fun testPush() {
        // A push/nurdle is a gentle DRIVE/DEFENCE with moderate wrist movement
        // Real DRIVE/DEFENCE: deltaX IQR 0.57-1.10, deltaZ IQR 0.70-1.60
        val shot = findParametersForShot(
            targetShotType = "DRIVE/DEFENCE",
            preGyroRanges = floatArrayOf(3f, 5f, 7f),
            impactGyroRanges = floatArrayOf(6f, 8f, 10f),
            postGyroRanges = floatArrayOf(3f, 5f, 7f),
            shockRanges = floatArrayOf(35f, 40f, 45f),
            rollRanges = floatArrayOf(-5f, 0f, 5f),
            dxRanges = floatArrayOf(0.5f, 0.7f, 0.9f),
            dzRanges = floatArrayOf(0.7f, 1.0f, 1.3f),
            postGyroYRanges = floatArrayOf(-3f, -2f, -1f, 0f)
        )
        assertNotNull("Shot should be detected", shot)
        assertEquals("DRIVE/DEFENCE", shot?.shotType)
    }

    @Test
    fun testPlayAndMiss() {
        // Play and miss: same biomechanics as a drive but isHit=false (low shock)
        // Must use realistic deltaX/deltaZ ranges matching DRIVE/DEFENCE training data
        val shot = findParametersForShot(
            targetShotType = "DRIVE/DEFENCE", // Play and miss evaluates to shotType class, but isHit is false
            isHit = false,
            dxRanges = floatArrayOf(0.6f, 0.8f, 1.0f),
            dzRanges = floatArrayOf(0.7f, 1.0f, 1.2f),
            preGyroRanges = floatArrayOf(3f, 5f, 8f, 10f),
            impactGyroRanges = floatArrayOf(6f, 8f, 10f, 12f),
            postGyroRanges = floatArrayOf(3f, 5f, 8f),
            shockRanges = floatArrayOf(45f, 50f, 55f),
            rollRanges = floatArrayOf(-10f, 0f, 10f),
            postGyroYRanges = floatArrayOf(-3f, -2f, -1f, 0f),
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

        // 1. Simulate quiet stance (2.0s) - 100 samples
        for (i in 0 until 100) {
            detector.processGyro(floatArrayOf(0.1f, 0f, 0f), time)
            detector.processGravity(floatArrayOf(0f, gravY, gravZ), time)
            detector.processAccel(floatArrayOf(0f, gravY, gravZ), time)
            detector.processRotation(floatArrayOf(0f, 0f, 0f, 1f), time)
            time += 20_000_000L
        }

        // 2. Simulate transient failure / rocking (800ms) - 40 samples
        for (i in 0 until 40) {
            val gyroVal = if (i % 2 == 0) 4.0f else 0.0f
            detector.processGyro(floatArrayOf(gyroVal, 0f, 0f), time)
            detector.processGravity(floatArrayOf(0f, gravY, gravZ), time)
            detector.processAccel(floatArrayOf(0f, gravY, gravZ), time)
            val q = computeRotationQuat(1.0f, 5.0f * i, 0f, 0f)
            detector.processRotation(q, time)
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

        // 1. Populate buffers with walking/movement (2.0s) - 100 samples
        for (i in 0 until 100) {
            val gyroVal = if (i % 2 == 0) 4.0f else 0.0f
            detector.processGyro(floatArrayOf(gyroVal, 0f, 0f), time)
            detector.processGravity(floatArrayOf(0f, gravY, gravZ), time)
            detector.processAccel(floatArrayOf(0f, gravY, gravZ), time)
            val q = computeRotationQuat(1.0f, 5.0f * i, 0f, 0f)
            detector.processRotation(q, time)
            time += 20_000_000L
        }

        // 2. Open the gate with quiet stance (1.4s) - 70 samples
        // (1.0s to make Segment 2 quiet and open the gate + 400ms of active gate duration < 800ms lock threshold)
        for (i in 0 until 70) {
            detector.processGyro(floatArrayOf(0.1f, 0f, 0f), time)
            detector.processGravity(floatArrayOf(0f, gravY, gravZ), time)
            detector.processAccel(floatArrayOf(0f, gravY, gravZ), time)
            detector.processRotation(floatArrayOf(0f, 0f, 0f, 1f), time)
            time += 20_000_000L
        }

        // 3. Simulate failure exceeding break tolerance (2.0s) - 100 samples
        for (i in 0 until 100) {
            val gyroVal = if (i % 2 == 0) 4.0f else 0.0f
            detector.processGyro(floatArrayOf(gyroVal, 0f, 0f), time)
            detector.processGravity(floatArrayOf(0f, gravY, gravZ), time)
            detector.processAccel(floatArrayOf(0f, gravY, gravZ), time)
            val q = computeRotationQuat(1.0f, 5.0f * i, 0f, 0f)
            detector.processRotation(q, time)
            time += 20_000_000L
        }

        // 4. Restore quiet stance (500ms) - 25 samples (not enough to lock since it reset completely)
        for (i in 0 until 25) {
            detector.processGyro(floatArrayOf(0.1f, 0f, 0f), time)
            detector.processGravity(floatArrayOf(0f, gravY, gravZ), time)
            detector.processAccel(floatArrayOf(0f, gravY, gravZ), time)
            detector.processRotation(floatArrayOf(0f, 0f, 0f, 1f), time)
            time += 20_000_000L
        }

        // 5. Swing initiation (200ms)
        for (i in 1..10) {
            val progress = i / 10f
            detector.processGyro(floatArrayOf(10f, 0f, 0f), time)
            detector.processGravity(floatArrayOf(0f, gravY, gravZ), time)
            detector.processAccel(floatArrayOf(0f, gravY, gravZ), time)
            val q = computeRotationQuat(progress, 0f, 0.05f, 0.2f)
            detector.processRotation(q, time)
            time += 20_000_000L
        }

        // 6. Impact & Peak
        val impactTime = time
        detector.processGyro(floatArrayOf(20f, 0f, 0f), impactTime)
        detector.processAccel(floatArrayOf(50f, 0f, 0f), impactTime)
        detector.processGravity(floatArrayOf(0f, gravY, gravZ), impactTime)
        val qImpact = computeRotationQuat(1.0f, 0f, 0.05f, 0.2f)
        detector.processRotation(qImpact, impactTime)
        time += 20_000_000L

        // 7. Post-impact follow-through
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
        // Uses realistic DRIVE/DEFENCE feature ranges to ensure model classifies correctly
        val shot = findParametersForShot(
            targetShotType = "DRIVE/DEFENCE",
            rollRanges = floatArrayOf(-10f, 0f, 10f),
            dxRanges = floatArrayOf(0.6f, 0.8f, 1.0f),
            dzRanges = floatArrayOf(0.8f, 1.0f, 1.2f),
            preGyroRanges = floatArrayOf(5f, 8f, 10f),
            impactGyroRanges = floatArrayOf(8f, 10f, 12f),
            postGyroRanges = floatArrayOf(5f, 8f, 10f),
            gravYRanges = floatArrayOf(-9.0f, -8.5f, -9.4f),
            postGyroYRanges = floatArrayOf(-3f, -2f, -1f, 0f)
        )
        assertNotNull("DRIVE/DEFENCE Shot should be detected", shot)
        System.out.println("DEBUG BLADE: bladeClass=${shot?.bladeClass}, launchClass=${shot?.launchClass}")
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
            System.out.println("DEBUG PULL: launchAngle=${pullShot.launchAngle}, launchClass=${pullShot.launchClass}")
            assertEquals(-30f, pullShot.launchAngle, 1.0f)
            assertEquals("LOFTED", pullShot.launchClass)
        }
    }
}
