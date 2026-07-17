package com.mrpeel.cricketbattingtracker

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.mrpeel.cricketbattingtracker.data.AppDatabase
import com.mrpeel.cricketbattingtracker.data.InningsEvent
import kotlinx.coroutines.launch
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

    fun deleteInnings(inningsId: Long) {
        viewModelScope.launch {
            dao.deleteTimelineForInningsSync(inningsId)
            selectInnings(null) // Reset selection
        }
    }

    fun markInningsProcessed(inningsId: Long) {
        val prefs = getApplication<Application>().getSharedPreferences("pitch_analytix_prefs", android.content.Context.MODE_PRIVATE)
        prefs.edit().putBoolean("processed_innings_$inningsId", true).apply()
        // Force flow refresh
        _selectedInningsId.value = _selectedInningsId.value
    }

    fun retryLocalProcessing(inningsId: Long, onResult: (Boolean, String) -> Unit) {
        viewModelScope.launch {
            try {
                val watchRoot = getApplication<Application>().getExternalFilesDir("watch_sessions")
                val watchDirs = watchRoot?.listFiles()?.filter { it.isDirectory && it.name.startsWith("session_") }
                
                val timeline = dao.getTimelineForInningsListSync(inningsId)
                val startEvent = timeline.firstOrNull { it.description == "Session Started" }
                if (startEvent == null) {
                    onResult(false, "Could not find session start timestamp in database")
                    return@launch
                }
                
                val startTimeMs = startEvent.timestamp
                val targetDir = watchDirs?.minByOrNull { dir ->
                    try {
                        val dirTimeStr = dir.name.substringAfter("session_")
                        val dirTimeMs = java.text.SimpleDateFormat("yyyy-MM-dd_HH-mm-ss", java.util.Locale.US).parse(dirTimeStr)?.time ?: 0L
                        kotlin.math.abs(dirTimeMs - startTimeMs)
                    } catch (e: Exception) {
                        Long.MAX_VALUE
                    }
                }
                
                if (targetDir == null || !targetDir.exists()) {
                    onResult(false, "No matching watch session folder found on phone storage.")
                    return@launch
                }
                
                val dirTimeStr = targetDir.name.substringAfter("session_")
                val dirTimeMs = try {
                    java.text.SimpleDateFormat("yyyy-MM-dd_HH-mm-ss", java.util.Locale.US).parse(dirTimeStr)?.time ?: 0L
                } catch (e: Exception) { 0L }
                
                if (kotlin.math.abs(dirTimeMs - startTimeMs) > 10 * 60_000L) {
                    onResult(false, "No matching watch session folder found for this session's time.")
                    return@launch
                }
                
                val polarRoot = getApplication<Application>().getExternalFilesDir("polar_sessions")
                val polarSessionDir = polarRoot?.listFiles()
                    ?.filter { it.isDirectory && it.name.startsWith("polar_session_") }
                    ?.minByOrNull { dir ->
                        try {
                            val polarTimeStr = dir.name.substringAfter("polar_session_")
                            val polarTimeMs = java.text.SimpleDateFormat("yyyy-MM-dd_HH-mm-ss", java.util.Locale.US).parse(polarTimeStr)?.time ?: 0L
                            kotlin.math.abs(polarTimeMs - startTimeMs)
                        } catch (e: Exception) {
                            Long.MAX_VALUE
                        }
                    }
                
                val matchedPolarDir = polarSessionDir?.takeIf { dir ->
                    try {
                        val polarTimeStr = dir.name.substringAfter("polar_session_")
                        val polarTimeMs = java.text.SimpleDateFormat("yyyy-MM-dd_HH-mm-ss", java.util.Locale.US).parse(polarTimeStr)?.time ?: 0L
                        kotlin.math.abs(polarTimeMs - startTimeMs) < 10 * 60_000L
                    } catch (e: Exception) { false }
                }
                
                if (matchedPolarDir != null) {
                    com.mrpeel.cricketbattingtracker.services.PhoneSwingDetector.processSession(
                        inningsId,
                        targetDir,
                        matchedPolarDir,
                        getApplication()
                    )
                    onResult(true, "Successfully processed dual-sensor session data!")
                } else {
                    com.mrpeel.cricketbattingtracker.services.PhoneSwingDetector.processWatchOnlySession(
                        inningsId,
                        targetDir,
                        getApplication()
                    )
                    onResult(true, "Successfully recovered session using Watch-only data!")
                }
                
                // Force timeline re-trigger
                _selectedInningsId.value = inningsId
                
            } catch (e: Exception) {
                onResult(false, "Recovery processing failed: ${e.message}")
            }
        }
    }
}
