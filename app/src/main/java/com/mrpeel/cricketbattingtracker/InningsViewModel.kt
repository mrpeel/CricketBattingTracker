package com.mrpeel.cricketbattingtracker

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.mrpeel.cricketbattingtracker.data.AppDatabase
import com.mrpeel.cricketbattingtracker.data.InningsEvent
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.flatMapLatest
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.flow.stateIn
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

data class SessionHistoryItem(
    val inningsId: Long,
    val startTimeMillis: Long,
    val endTimeMillis: Long,
    val dateText: String,
    val totalShots: Int,
    val maxSpeed: Float,
    val avgEfficiency: Float,
    val events: List<InningsEvent>,
    val locationText: String
)

class InningsViewModel(application: Application) : AndroidViewModel(application) {
    private val dao = AppDatabase.getDatabase(application).inningsEventDao()
    
    // Navigation & Selected Session State
    private val _selectedInningsId = MutableStateFlow<Long?>(null)
    val selectedInningsId: StateFlow<Long?> = _selectedInningsId.asStateFlow()
    
    fun selectInnings(id: Long?) {
        _selectedInningsId.value = id
    }

    // Historical Sessions List Flow
    val allSessions: StateFlow<List<SessionHistoryItem>> = dao.getAllEventsFlow()
        .map { events ->
            val formatter = SimpleDateFormat("MMM d, yyyy 'at' HH:mm:ss", Locale.getDefault())
            events.groupBy { it.inningsId }
                .map { (inningsId, sessionEvents) ->
                    val minTime = sessionEvents.minOfOrNull { it.timestamp } ?: 0L
                    val maxTime = sessionEvents.maxOfOrNull { it.timestamp } ?: 0L
                    val shotEvents = sessionEvents.filter { it.batSpeed != null }
                    val maxSpeed = shotEvents.mapNotNull { it.batSpeed }.maxOrNull() ?: 0f
                    val avgEff = shotEvents.mapNotNull { it.efficiency }.average().let { if (it.isNaN()) 0.0 else it }.toFloat()
                    
                    val location = sessionEvents.firstOrNull { !it.location.isNullOrBlank() }?.location ?: "Net Practice"

                    SessionHistoryItem(
                        inningsId = inningsId,
                        startTimeMillis = minTime,
                        endTimeMillis = maxTime,
                        dateText = formatter.format(Date(minTime)),
                        totalShots = shotEvents.size,
                        maxSpeed = maxSpeed,
                        avgEfficiency = avgEff,
                        events = sessionEvents,
                        locationText = location
                    )
                }
                .sortedByDescending { it.startTimeMillis }
        }
        .stateIn(
            scope = viewModelScope,
            started = SharingStarted.WhileSubscribed(5000),
            initialValue = emptyList()
        )

    // Current Session / Details Flow
    @OptIn(kotlinx.coroutines.ExperimentalCoroutinesApi::class)
    val currentTimeline: StateFlow<List<InningsEvent>> = _selectedInningsId
        .flatMapLatest { id ->
            if (id != null) {
                dao.getTimelineForInnings(id)
            } else {
                dao.getLatestInningsIdFlow().flatMapLatest { latestId ->
                    dao.getTimelineForInnings(latestId ?: 0L)
                }
            }
        }
        .stateIn(
            scope = viewModelScope,
            started = SharingStarted.WhileSubscribed(5000),
            initialValue = emptyList()
        )
}
