package com.mrpeel.cricketbattingtracker.ui.biomechanics

import android.view.View
import android.widget.ProgressBar
import android.widget.TextView
import androidx.core.content.ContextCompat
import com.mrpeel.cricketbattingtracker.R

/**
 * View binder hook demonstrating traditional Android View / View Binding / ViewHolder logic
 * for binding [BiomechanicalUiState] to layout elements and toggling warning color resources.
 */
class BiomechanicalViewBinder(private val rootView: View) {

    private val cardContainer: View? = rootView.findViewById(R.id.cardContainer)
    private val tvSequencingTitle: TextView? = rootView.findViewById(R.id.tvSequencingTitle)
    private val tvSequencingDescription: TextView? = rootView.findViewById(R.id.tvSequencingDescription)
    private val progressSequencing: ProgressBar? = rootView.findViewById(R.id.progressSequencing)

    private val tvPowerTitle: TextView? = rootView.findViewById(R.id.tvPowerTitle)
    private val tvPowerDescription: TextView? = rootView.findViewById(R.id.tvPowerDescription)
    private val progressPower: ProgressBar? = rootView.findViewById(R.id.progressPower)

    private val tvCoachingInsight: TextView? = rootView.findViewById(R.id.tvCoachingInsight)

    /**
     * Ingest raw TCN pipeline outputs, evaluate via [BiomechanicalUiMapper], and bind results to UI elements.
     */
    fun bind(
        shotClass: String?,
        timeLeadMs: Float?,
        gyroRatio: Float?,
        accRatio: Float?
    ) {
        val state = BiomechanicalUiMapper.mapToUiState(shotClass, timeLeadMs, gyroRatio, accRatio)
        bindState(state)
    }

    /**
     * Bind a pre-computed [BiomechanicalUiState] directly to UI elements.
     */
    fun bindState(state: BiomechanicalUiState) {
        val context = rootView.context
        val statusColorRes = if (state.displaysWarning) R.color.ui_warning_amber else R.color.ui_optimal_green
        val colorInt = ContextCompat.getColor(context, statusColorRes)

        // Bind Sequencing UI
        tvSequencingTitle?.text = state.sequencingTitle
        tvSequencingTitle?.setTextColor(colorInt)
        tvSequencingDescription?.text = state.sequencingDescription
        progressSequencing?.progress = (state.sequencingSliderVal * 100f).toInt().coerceIn(0, 100)

        // Bind Power Pattern UI
        tvPowerTitle?.text = state.powerPatternTitle
        tvPowerTitle?.setTextColor(colorInt)
        tvPowerDescription?.text = state.powerPatternDescription
        progressPower?.progress = (state.powerSliderVal * 100f).toInt().coerceIn(0, 100)

        // Bind Coaching Insight
        tvCoachingInsight?.text = state.coachingInsight

        // Apply conditional styling for amber warning state
        cardContainer?.let { container ->
            if (state.displaysWarning) {
                container.alpha = 0.95f
            } else {
                container.alpha = 1.0f
            }
        }
    }
}
