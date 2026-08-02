package com.mrpeel.cricketbattingtracker.ui.biomechanics

/**
 * Immutable presentation UI state representing qualitative biomechanical coaching metrics.
 * Decoupled from raw IMU sensors and TCN classification pipeline outputs.
 */
data class BiomechanicalUiState(
    val sequencingTitle: String,
    val sequencingDescription: String,
    val sequencingSliderVal: Float,
    val powerPatternTitle: String,
    val powerPatternDescription: String,
    val powerSliderVal: Float,
    val coachingInsight: String,
    val displaysWarning: Boolean
)
