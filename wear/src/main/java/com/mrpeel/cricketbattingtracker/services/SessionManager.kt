package com.mrpeel.cricketbattingtracker.services

import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow

object SessionManager {
    private val _isTracking = MutableStateFlow(false)
    val isTracking: StateFlow<Boolean> = _isTracking.asStateFlow()

    private val _shotCount = MutableStateFlow(0)
    val shotCount: StateFlow<Int> = _shotCount.asStateFlow()

    private val _maxSpeed = MutableStateFlow(0f)
    val maxSpeed: StateFlow<Float> = _maxSpeed.asStateFlow()

    private val _avgSpeed = MutableStateFlow(0f)
    val avgSpeed: StateFlow<Float> = _avgSpeed.asStateFlow()

    private val allSpeeds = mutableListOf<Float>()

    fun setTracking(active: Boolean) {
        _isTracking.value = active
        if (active) {
            // Optional: reset stats when a new session starts
            // resetSession()
        }
    }

    fun addShot(speed: Float) {
        val newCount = _shotCount.value + 1
        _shotCount.value = newCount
        
        if (speed > _maxSpeed.value) {
            _maxSpeed.value = speed
        }
        
        allSpeeds.add(speed)
        _avgSpeed.value = allSpeeds.average().toFloat()
    }

    fun resetSession() {
        _shotCount.value = 0
        _maxSpeed.value = 0f
        _avgSpeed.value = 0f
        allSpeeds.clear()
        _isTracking.value = false
    }
}
