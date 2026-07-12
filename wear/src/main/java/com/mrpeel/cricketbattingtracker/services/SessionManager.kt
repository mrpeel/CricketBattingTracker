package com.mrpeel.cricketbattingtracker.services

import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow

data class ShotData(
    val speedKmh: Float,
    val isHit: Boolean,
    val peakAccel: Float,
    val sweetSpot: String, // "Excellent", "Good", "Poor", or "N/A"
    val efficiency: Float,
    val impactTimeMs: Long,
    val backliftAngle: Float,
    val followThroughAngle: Float,
    val shotType: String,
    val wristRollDeg: Float = 0f,
    val bladeAngle: Float = 0f,
    val bladeClass: String = "N/A",
    val launchAngle: Float = 0f,
    val launchClass: String = "N/A",
    // SwingFeatures for phone-side storage (future re-classification)
    val s1GyroYStd: Float = 0f,
    val s1GyroZStd: Float = 0f,
    val s1DeltaX: Float = 0f,
    val s1DeltaZ: Float = 0f,
    val s2GyroMag: Float = 0f,
    val s2GravYMean: Float = 0f,
    val s2DeltaX: Float = 0f,
    val s2DeltaZ: Float = 0f,
    val s3RollImpactDeg: Float = 0f,
    val s3YawImpactDeg: Float = 0f,
    val s3DeltaX: Float = 0f,
    val s3DeltaZ: Float = 0f,
    val s3PlaneRatio: Float = 0f,
    val s3GyroYMin: Float = 0f
)

object SessionManager {
    private val _isTracking = MutableStateFlow(false)
    val isTracking: StateFlow<Boolean> = _isTracking.asStateFlow()

    private val _isVideoMode = MutableStateFlow(false)
    val isVideoMode: StateFlow<Boolean> = _isVideoMode.asStateFlow()

    fun setVideoMode(active: Boolean) {
        _isVideoMode.value = active
    }

    private val _isFacingUp = MutableStateFlow(false)
    val isFacingUp: StateFlow<Boolean> = _isFacingUp.asStateFlow()

    fun setFacingUp(active: Boolean) {
        _isFacingUp.value = active
    }

    private val _shotCount = MutableStateFlow(0)
    val shotCount: StateFlow<Int> = _shotCount.asStateFlow()

    private val _maxSpeed = MutableStateFlow(0f)
    val maxSpeed: StateFlow<Float> = _maxSpeed.asStateFlow()

    private val _avgSpeed = MutableStateFlow(0f)
    val avgSpeed: StateFlow<Float> = _avgSpeed.asStateFlow()

    private val _excellentShots = MutableStateFlow(0)
    val excellentShots: StateFlow<Int> = _excellentShots.asStateFlow()

    private val _goodShots = MutableStateFlow(0)
    val goodShots: StateFlow<Int> = _goodShots.asStateFlow()

    private val _poorShots = MutableStateFlow(0)
    val poorShots: StateFlow<Int> = _poorShots.asStateFlow()

    private val _lastShotSpeed = MutableStateFlow(0f)
    val lastShotSpeed: StateFlow<Float> = _lastShotSpeed.asStateFlow()

    private val _lastShotRating = MutableStateFlow("N/A")
    val lastShotRating: StateFlow<String> = _lastShotRating.asStateFlow()

    private val _lastShotEfficiency = MutableStateFlow(0f)
    val lastShotEfficiency: StateFlow<Float> = _lastShotEfficiency.asStateFlow()

    private val _lastShotType = MutableStateFlow("UNKNOWN")
    val lastShotType: StateFlow<String> = _lastShotType.asStateFlow()

    private val _lastImpactTimeMs = MutableStateFlow(0L)
    val lastImpactTimeMs: StateFlow<Long> = _lastImpactTimeMs.asStateFlow()

    private val _lastFollowThroughAngle = MutableStateFlow(0f)
    val lastFollowThroughAngle: StateFlow<Float> = _lastFollowThroughAngle.asStateFlow()

    private val _lastWristRollDeg = MutableStateFlow(0f)
    val lastWristRollDeg: StateFlow<Float> = _lastWristRollDeg.asStateFlow()

    private val allSpeeds = mutableListOf<Float>()

    fun setTracking(active: Boolean) {
        _isTracking.value = active
    }

    fun addShot(shot: ShotData) {
        val newCount = _shotCount.value + 1
        _shotCount.value = newCount
        
        if (shot.speedKmh > _maxSpeed.value) {
            _maxSpeed.value = shot.speedKmh
        }
        
        allSpeeds.add(shot.speedKmh)
        _avgSpeed.value = if (allSpeeds.isNotEmpty()) allSpeeds.average().toFloat() else 0f
        
        if (shot.isHit) {
            when (shot.sweetSpot) {
                "Excellent" -> _excellentShots.value++
                "Good" -> _goodShots.value++
                "Poor" -> _poorShots.value++
            }
        }
        
        _lastShotSpeed.value = shot.speedKmh
        _lastShotRating.value = if (shot.isHit) shot.sweetSpot else "Miss"
        _lastShotEfficiency.value = shot.efficiency
        _lastShotType.value = shot.shotType
        _lastImpactTimeMs.value = shot.impactTimeMs
        _lastFollowThroughAngle.value = shot.followThroughAngle
        _lastWristRollDeg.value = shot.wristRollDeg
    }

    fun resetSession() {
        _shotCount.value = 0
        _maxSpeed.value = 0f
        _avgSpeed.value = 0f
        _excellentShots.value = 0
        _goodShots.value = 0
        _poorShots.value = 0
        _lastShotSpeed.value = 0f
        _lastShotRating.value = "N/A"
        _lastShotEfficiency.value = 0f
        _lastShotType.value = "UNKNOWN"
        _lastImpactTimeMs.value = 0L
        _lastFollowThroughAngle.value = 0f
        _lastWristRollDeg.value = 0f
        allSpeeds.clear()
        _isTracking.value = false
        _isFacingUp.value = false
        _isVideoMode.value = false
    }
}
