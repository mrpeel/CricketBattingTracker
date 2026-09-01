package com.mrpeel.cricketbattingtracker

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.mrpeel.cricketbattingtracker.data.AppDatabase
import com.mrpeel.cricketbattingtracker.data.InningsEvent
import com.mrpeel.cricketbattingtracker.analytics.BiomechanicsAggregator
import com.mrpeel.cricketbattingtracker.analytics.DiagnosticRulesEngine
import com.mrpeel.cricketbattingtracker.ui.insights.LongitudinalInsightsUiState
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

    // Longitudinal Biomechanical Insights Flow
    val longitudinalInsights: StateFlow<LongitudinalInsightsUiState> = dao.getAllEventsFlow()
        .map { events ->
            val aggregation = BiomechanicsAggregator.aggregate(events)
            val diagnosis = DiagnosticRulesEngine.diagnose(aggregation)
            LongitudinalInsightsUiState(
                aggregation = aggregation,
                diagnosis = diagnosis,
                isLoading = false
            )
        }
        .stateIn(
            scope = viewModelScope,
            started = SharingStarted.WhileSubscribed(5000),
            initialValue = LongitudinalInsightsUiState(
                aggregation = BiomechanicsAggregator.aggregate(emptyList()),
                diagnosis = DiagnosticRulesEngine.diagnose(BiomechanicsAggregator.aggregate(emptyList())),
                isLoading = true
            )
        )

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
            var tempWatchDir: java.io.File? = null
            var tempPolarDir: java.io.File? = null
            try {
                val watchRoot = getApplication<Application>().getExternalFilesDir("watch_sessions")
                val watchItems = watchRoot?.listFiles()?.filter { it.name.startsWith("session_") } ?: emptyList()
                
                val timeline = dao.getTimelineForInningsListSync(inningsId)
                val startEvent = timeline.firstOrNull { it.description == "Session Started" }
                if (startEvent == null) {
                    onResult(false, "Could not find session start timestamp in database")
                    return@launch
                }
                
                val startTimeMs = startEvent.timestamp
                val targetItem = watchItems.minByOrNull { file ->
                    try {
                        val cleanName = file.name.substringBefore(".zip")
                        val dirTimeStr = cleanName.substringAfter("session_")
                        val dirTimeMs = java.text.SimpleDateFormat("yyyy-MM-dd_HH-mm-ss", java.util.Locale.US).parse(dirTimeStr)?.time ?: 0L
                        kotlin.math.abs(dirTimeMs - startTimeMs)
                    } catch (e: Exception) {
                        Long.MAX_VALUE
                    }
                }
                
                if (targetItem == null || !targetItem.exists()) {
                    onResult(false, "No matching watch session found on phone storage.")
                    return@launch
                }
                
                val cleanName = targetItem.name.substringBefore(".zip")
                val dirTimeStr = cleanName.substringAfter("session_")
                val dirTimeMs = try {
                    java.text.SimpleDateFormat("yyyy-MM-dd_HH-mm-ss", java.util.Locale.US).parse(dirTimeStr)?.time ?: 0L
                } catch (e: Exception) { 0L }
                
                if (kotlin.math.abs(dirTimeMs - startTimeMs) > 10 * 60_000L) {
                    onResult(false, "No matching watch session found for this session's time.")
                    return@launch
                }
                
                val polarRoot = getApplication<Application>().getExternalFilesDir("polar_sessions")
                val polarItems = polarRoot?.listFiles()?.filter { it.name.startsWith("polar_session_") } ?: emptyList()
                val targetPolarItem = polarItems.minByOrNull { file ->
                    try {
                        val cleanPolar = file.name.substringBefore(".zip")
                        val polarTimeStr = cleanPolar.substringAfter("polar_session_")
                        val polarTimeMs = java.text.SimpleDateFormat("yyyy-MM-dd_HH-mm-ss", java.util.Locale.US).parse(polarTimeStr)?.time ?: 0L
                        kotlin.math.abs(polarTimeMs - startTimeMs)
                    } catch (e: Exception) {
                        Long.MAX_VALUE
                    }
                }
                
                val matchedPolarItem = targetPolarItem?.takeIf { file ->
                    try {
                        val cleanPolar = file.name.substringBefore(".zip")
                        val polarTimeStr = cleanPolar.substringAfter("polar_session_")
                        val polarTimeMs = java.text.SimpleDateFormat("yyyy-MM-dd_HH-mm-ss", java.util.Locale.US).parse(polarTimeStr)?.time ?: 0L
                        kotlin.math.abs(polarTimeMs - startTimeMs) < 10 * 60_000L
                    } catch (e: Exception) { false }
                }
                
                // Set up temporary directories for zip execution
                val finalWatchDir = if (targetItem.isFile && targetItem.name.endsWith(".zip")) {
                    val tempDir = java.io.File(watchRoot, "temp_retry_watch_${System.currentTimeMillis()}")
                    tempDir.mkdirs()
                    tempWatchDir = tempDir
                    unzip(targetItem, tempDir)
                    tempDir
                } else {
                    targetItem
                }
                
                val finalPolarDir = matchedPolarItem?.let { file ->
                    if (file.isFile && file.name.endsWith(".zip")) {
                        val tempDir = java.io.File(polarRoot, "temp_retry_polar_${System.currentTimeMillis()}")
                        tempDir.mkdirs()
                        tempPolarDir = tempDir
                        unzip(file, tempDir)
                        tempDir
                    } else {
                        file
                    }
                }
                
                val success = if (finalPolarDir != null) {
                    com.mrpeel.cricketbattingtracker.services.PhoneSwingDetector.processSession(
                        inningsId,
                        finalWatchDir,
                        finalPolarDir,
                        getApplication()
                    )
                } else {
                    com.mrpeel.cricketbattingtracker.services.PhoneSwingDetector.processWatchOnlySession(
                        inningsId,
                        finalWatchDir,
                        getApplication()
                    )
                }
                
                if (success) {
                    onResult(true, if (finalPolarDir != null) "Successfully processed dual-sensor session data!" else "Successfully recovered session using Watch-only data!")
                } else {
                    onResult(false, "Processing aborted: Session raw files were empty or invalid.")
                }
                
                // Force timeline re-trigger
                _selectedInningsId.value = inningsId
                
            } catch (e: Exception) {
                onResult(false, "Recovery processing failed: ${e.message}")
            } finally {
                // Clean up any temporary folders
                try {
                    tempWatchDir?.deleteRecursively()
                    tempPolarDir?.deleteRecursively()
                } catch (e: Exception) {}
            }
        }
    }

    private fun unzip(zipFile: java.io.File, targetDirectory: java.io.File) {
        java.util.zip.ZipInputStream(java.io.BufferedInputStream(java.io.FileInputStream(zipFile))).use { zis ->
            var ze: java.util.zip.ZipEntry? = zis.nextEntry
            while (ze != null) {
                val file = java.io.File(targetDirectory, ze.name)
                val dir = if (ze.isDirectory) file else file.parentFile
                if (dir != null && !dir.exists() && !dir.mkdirs()) {
                    throw java.io.IOException("Failed to create directory " + dir.absolutePath)
                }
                if (!ze.isDirectory) {
                    java.io.BufferedOutputStream(java.io.FileOutputStream(file)).use { bos ->
                        zis.copyTo(bos)
                    }
                }
                ze = zis.nextEntry
            }
        }
    }
}
