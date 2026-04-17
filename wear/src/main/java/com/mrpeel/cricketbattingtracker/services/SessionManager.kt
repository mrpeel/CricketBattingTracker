package com.mrpeel.cricketbattingtracker.services

import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow

data class ShotData(
    val speedKmh: Float,
    val isHit: Boolean,
    val peakAccel: Float,
    val sweetSpot: String // "Excellent", "Good", "Poor", or "N/A"
)

object SessionManager {
    private val _isTracking = MutableStateFlow(false)
    val isTracking: StateFlow<Boolean> = _isTracking.asStateFlow()

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
        allSpeeds.clear()
        _isTracking.value = false
    }
}
