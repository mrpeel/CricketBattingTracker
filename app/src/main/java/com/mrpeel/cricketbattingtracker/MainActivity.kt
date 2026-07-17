package com.mrpeel.cricketbattingtracker

import android.content.Intent
import android.os.Bundle
import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.viewModels
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.mrpeel.cricketbattingtracker.data.AppDatabase
import com.mrpeel.cricketbattingtracker.data.InningsEvent
import com.mrpeel.cricketbattingtracker.data.HeartRateEvent
import com.mrpeel.cricketbattingtracker.services.HealthConnectManager
import java.text.SimpleDateFormat
import java.util.*
import androidx.lifecycle.lifecycleScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import androidx.health.connect.client.PermissionController
import androidx.health.connect.client.permission.HealthPermission
import androidx.health.connect.client.records.ExerciseSessionRecord
import androidx.health.connect.client.records.HeartRateRecord
import androidx.health.connect.client.records.TotalCaloriesBurnedRecord
import androidx.health.connect.client.records.ActiveCaloriesBurnedRecord
import androidx.health.connect.client.HealthConnectClient
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.window.Dialog
import android.content.Context
import androidx.compose.animation.core.*
import androidx.compose.animation.animateColorAsState
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow

class MainActivity : ComponentActivity() {

    private val viewModel: InningsViewModel by viewModels()

    // Location permissions request launcher
    private val requestLocationPermissionLauncher = registerForActivityResult(
        androidx.activity.result.contract.ActivityResultContracts.RequestMultiplePermissions()
    ) { permissions ->
        val fineGranted = permissions[android.Manifest.permission.ACCESS_FINE_LOCATION] ?: false
        val coarseGranted = permissions[android.Manifest.permission.ACCESS_COARSE_LOCATION] ?: false
        if (fineGranted || coarseGranted) {
            android.util.Log.d("MainActivity", "Location permissions granted successfully!")
            triggerForegroundLocationResolution()
        } else {
            android.util.Log.w("MainActivity", "Location permissions were denied.")
        }
    }

    private val requestCameraPermissionLauncher = registerForActivityResult(
        androidx.activity.result.contract.ActivityResultContracts.RequestMultiplePermissions()
    ) { permissions ->
        val cameraGranted = permissions[android.Manifest.permission.CAMERA] ?: false
        val audioGranted  = permissions[android.Manifest.permission.RECORD_AUDIO] ?: false
        if (cameraGranted && audioGranted) {
            android.util.Log.d("MainActivity", "Camera+audio permissions granted — starting video recording")
            com.mrpeel.cricketbattingtracker.services.VideoRecordManager.startRecording(this)
        } else {
            android.util.Log.w("MainActivity", "Camera/audio permission denied for video recording")
            Toast.makeText(this, "Camera and microphone permissions required for video recording", Toast.LENGTH_LONG).show()
        }
    }

    private val requestAudioPermissionLauncher = registerForActivityResult(
        androidx.activity.result.contract.ActivityResultContracts.RequestMultiplePermissions()
    ) { permissions ->
        val recordGranted = permissions[android.Manifest.permission.RECORD_AUDIO] ?: false
        val btGranted = if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.S) {
            permissions[android.Manifest.permission.BLUETOOTH_CONNECT] ?: false
        } else {
            true
        }
        if (recordGranted) {
            android.util.Log.d("MainActivity", "Audio recording permission granted successfully!")
            if (!btGranted) {
                android.util.Log.w("MainActivity", "Bluetooth connect permission denied; recording will fallback to built-in mic.")
            }
            com.mrpeel.cricketbattingtracker.services.AudioRecordManager.refreshRecordings(this)
            com.mrpeel.cricketbattingtracker.services.AudioRecordManager.startRecording(this, true)
        } else {
            android.util.Log.w("MainActivity", "Audio recording permission was denied.")
            Toast.makeText(this, "Microphone permission is required to record narration", Toast.LENGTH_LONG).show()
        }
    }

    // Register Health Connect permissions activity launcher contract
    private val requestPermissionActivityContract = PermissionController.createRequestPermissionResultContract()
    private val requestPermissions = registerForActivityResult(requestPermissionActivityContract) { granted ->
        if (granted.containsAll(setOf(
                HealthPermission.getWritePermission(ExerciseSessionRecord::class),
                HealthPermission.getWritePermission(HeartRateRecord::class),
                HealthPermission.getWritePermission(TotalCaloriesBurnedRecord::class),
                HealthPermission.getWritePermission(ActiveCaloriesBurnedRecord::class)
            ))) {
            android.util.Log.d("MainActivity", "Health Connect permissions granted successfully!")
            syncSessionToHealthConnect(null)
        } else {
            android.util.Log.w("MainActivity", "Health Connect permissions were not fully granted.")
        }
    }

    override fun onResume() {
        super.onResume()
        triggerForegroundLocationResolution()
        checkHealthConnectPermissions()
    }

    private fun checkHealthConnectPermissions() {
        if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.M) {
            try {
                if (HealthConnectClient.getSdkStatus(this) == HealthConnectClient.SDK_AVAILABLE) {
                    val healthConnectClient = HealthConnectClient.getOrCreate(this)
                    lifecycleScope.launch {
                        val permissions = setOf(
                            HealthPermission.getWritePermission(ExerciseSessionRecord::class),
                            HealthPermission.getWritePermission(HeartRateRecord::class),
                            HealthPermission.getWritePermission(TotalCaloriesBurnedRecord::class),
                            HealthPermission.getWritePermission(ActiveCaloriesBurnedRecord::class)
                        )
                        val granted = healthConnectClient.permissionController.getGrantedPermissions()
                        if (!granted.containsAll(permissions)) {
                            requestPermissions.launch(permissions)
                        } else {
                            android.util.Log.d("MainActivity", "Health Connect permissions already granted.")
                            syncSessionToHealthConnect(null)
                        }
                    }
                } else {
                    android.util.Log.i("MainActivity", "Health Connect is not available on this device.")
                }
            } catch (e: Exception) {
                android.util.Log.e("MainActivity", "Failed to check Health Connect permissions: ${e.message}")
            }
        }
    }

    fun syncSessionToHealthConnect(inningsId: Long? = null) {
        lifecycleScope.launch(Dispatchers.IO) {
            try {
                val database = AppDatabase.getDatabase(applicationContext)
                val dao = database.inningsEventDao()
                val hcManager = HealthConnectManager(applicationContext)
                
                // Get list of already synced sessions from SharedPreferences
                val prefs = getSharedPreferences("pitch_analytix_prefs", Context.MODE_PRIVATE)
                val syncedIds = prefs.getStringSet("synced_innings_ids", emptySet())?.toMutableSet() ?: mutableSetOf()

                val targetIds = if (inningsId != null) {
                    listOf(inningsId)
                } else {
                    dao.getAllUniqueInningsIds()
                }

                var newlySyncedCount = 0
                for (id in targetIds) {
                    if (inningsId == null && syncedIds.contains(id.toString())) {
                        continue // Skip already synced sessions when doing automatic full sync
                    }

                    val events = dao.getTimelineForInningsListSync(id)
                    if (events.isEmpty()) continue
                    
                    val shotEvents = events.filter { it.batSpeed != null }
                    val maxSpeed = shotEvents.mapNotNull { it.batSpeed }.maxOrNull() ?: 0f
                    val minTime = events.minOfOrNull { it.timestamp } ?: 0L
                    val maxTime = events.maxOfOrNull { it.timestamp } ?: 0L
                    val duration = if (maxTime > minTime) maxTime - minTime else (events.size * 5000L)
                    val endTime = if (maxTime > minTime) maxTime else (minTime + duration)
                    
                    val dbHeartRates = dao.getHeartRatesForInningsSync(id)
                    val realHeartRates = dbHeartRates.map { Pair(it.timestamp, it.beatsPerMinute) }

                    val success = hcManager.writeCricketWorkout(
                        inningsId = id,
                        startTimeMillis = minTime,
                        endTimeMillis = endTime,
                        shotCount = shotEvents.size,
                        maxSpeed = maxSpeed,
                        realHeartRates = realHeartRates
                    )

                    if (success) {
                        syncedIds.add(id.toString())
                        newlySyncedCount++
                    }
                }

                if (newlySyncedCount > 0) {
                    prefs.edit().putStringSet("synced_innings_ids", syncedIds).apply()
                    android.util.Log.d("MainActivity", "Successfully synced $newlySyncedCount new sessions to Health Connect!")
                    withContext(Dispatchers.Main) {
                        Toast.makeText(this@MainActivity, "Synced $newlySyncedCount new session(s) to Health Connect!", Toast.LENGTH_SHORT).show()
                    }
                }
            } catch (e: Exception) {
                android.util.Log.e("MainActivity", "Failed syncing sessions to Health Connect: ${e.message}")
            }
        }
    }

    private fun triggerForegroundLocationResolution() {
        if (androidx.core.content.ContextCompat.checkSelfPermission(this, android.Manifest.permission.ACCESS_COARSE_LOCATION) != android.content.pm.PackageManager.PERMISSION_GRANTED) {
            return
        }
        lifecycleScope.launch(Dispatchers.IO) {
            try {
                val locationManager = getSystemService(Context.LOCATION_SERVICE) as android.location.LocationManager
                val isGpsEnabled = locationManager.isProviderEnabled(android.location.LocationManager.GPS_PROVIDER)
                val isNetworkEnabled = locationManager.isProviderEnabled(android.location.LocationManager.NETWORK_PROVIDER)
                
                var bestLocation: android.location.Location? = null
                
                // Get last known location first
                for (provider in locationManager.getProviders(true)) {
                    val loc = locationManager.getLastKnownLocation(provider) ?: continue
                    if (bestLocation == null || loc.accuracy < bestLocation.accuracy) {
                        bestLocation = loc
                    }
                }
                
                // Resolve and cache immediately if we have a last known
                bestLocation?.let { cacheLocation(it) }
                
                // Request a fresh update for high accuracy
                withContext(Dispatchers.Main) {
                    val listener = object : android.location.LocationListener {
                        override fun onLocationChanged(location: android.location.Location) {
                            locationManager.removeUpdates(this)
                            lifecycleScope.launch(Dispatchers.IO) {
                                cacheLocation(location)
                            }
                        }
                        @Deprecated("Deprecated in parent class")
                        override fun onStatusChanged(provider: String?, status: Int, extras: Bundle?) {}
                        override fun onProviderEnabled(provider: String) {}
                        override fun onProviderDisabled(provider: String) {}
                    }
                    try {
                        if (isGpsEnabled) {
                            locationManager.requestLocationUpdates(android.location.LocationManager.GPS_PROVIDER, 0L, 0f, listener)
                        }
                        if (isNetworkEnabled) {
                            locationManager.requestLocationUpdates(android.location.LocationManager.NETWORK_PROVIDER, 0L, 0f, listener)
                        }
                    } catch (e: Exception) {
                        android.util.Log.e("MainActivity", "Failed requesting location updates: ${e.message}")
                    }
                    Unit
                }
            } catch (e: Exception) {
                android.util.Log.e("MainActivity", "Error resolving location: ${e.message}")
            }
        }
    }

    @Suppress("DEPRECATION")
    private fun cacheLocation(loc: android.location.Location) {
        try {
            val geocoder = android.location.Geocoder(this, Locale.getDefault())
            val addresses = geocoder.getFromLocation(loc.latitude, loc.longitude, 1)
            if (!addresses.isNullOrEmpty()) {
                val address = addresses[0]
                val streetNum = address.subThoroughfare ?: ""
                val streetName = address.thoroughfare ?: ""
                val street = if (streetNum.isNotEmpty() && streetName.isNotEmpty()) {
                    "$streetNum $streetName"
                } else {
                    streetName
                }
                val suburb = address.locality ?: address.subLocality ?: address.adminArea ?: ""
                val resolvedLocation = when {
                    street.isNotEmpty() && suburb.isNotEmpty() -> "$street, $suburb"
                    suburb.isNotEmpty() -> suburb
                    else -> ""
                }
                if (resolvedLocation.isNotEmpty()) {
                    val prefs = getSharedPreferences("pitch_analytix_prefs", Context.MODE_PRIVATE)
                    prefs.edit().putString("cached_resolved_location", resolvedLocation).apply()
                    android.util.Log.d("MainActivity", "Foreground Geocoder resolved and cached location: $resolvedLocation")
                }
            }
        } catch (e: Exception) {
            android.util.Log.e("MainActivity", "Failed geocoding in foreground: ${e.message}")
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        
        val permissionsToRequest = mutableListOf(
            android.Manifest.permission.ACCESS_FINE_LOCATION,
            android.Manifest.permission.ACCESS_COARSE_LOCATION
        )
        if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.S) {
            permissionsToRequest.add(android.Manifest.permission.BLUETOOTH_SCAN)
            permissionsToRequest.add(android.Manifest.permission.BLUETOOTH_CONNECT)
        }
        
        requestLocationPermissionLauncher.launch(permissionsToRequest.toTypedArray())
        
        triggerForegroundLocationResolution()
        checkHealthConnectPermissions()
        com.mrpeel.cricketbattingtracker.services.AudioRecordManager.refreshRecordings(this)

        setContent {
            val timeline by viewModel.currentTimeline.collectAsState()
            val allSessions by viewModel.allSessions.collectAsState()
            val selectedSessionId by viewModel.selectedInningsId.collectAsState()

            val isRecording by com.mrpeel.cricketbattingtracker.services.AudioRecordManager.isRecording.collectAsState()
            val elapsedSeconds by com.mrpeel.cricketbattingtracker.services.AudioRecordManager.elapsedSeconds.collectAsState()
            val maxAmplitude by com.mrpeel.cricketbattingtracker.services.AudioRecordManager.maxAmplitude.collectAsState()
            val recordingsList by com.mrpeel.cricketbattingtracker.services.AudioRecordManager.recordingsList.collectAsState()
            val context = LocalContext.current

            // Tab navigation state: 0=Dashboard, 1=Record, 2=History
            var selectedTab by remember { mutableStateOf(0) }

            // Athlete Profile preference state management
            var showProfileDialog by remember { mutableStateOf(false) }
            val prefs = remember { getSharedPreferences("pitch_analytix_prefs", Context.MODE_PRIVATE) }
            var userName by remember { mutableStateOf(prefs.getString("user_name", "Neil Kloot") ?: "Neil Kloot") }
            var userWeight by remember { mutableStateOf(prefs.getFloat("user_weight", 80.0f)) }
            var userAge by remember { mutableStateOf(prefs.getInt("user_age", 35)) }
            var userGender by remember { mutableStateOf(prefs.getString("user_gender", "Male") ?: "Male") }

            // Compute dynamic uppercase initials from name
            val initials = remember(userName) {
                userName.split(" ")
                    .filter { it.isNotEmpty() }
                    .take(2)
                    .map { it.first().uppercaseChar() }
                    .joinToString("")
                    .let { if (it.isEmpty()) "PA" else it }
            }

            // Tab labels and icons
            val tabSubtitles = listOf("YOUR CAREER", "SESSION CONSOLE", "SESSIONS HISTORY")

            MaterialTheme(
                colorScheme = darkColorScheme(
                    primary = Color(0xFF58FF63),
                    secondary = Color(0xFFBCD2FE),
                    background = Color(0xFF000C1B),
                    surface = Color(0xFF001B3D),
                    onBackground = Color.White,
                    onSurface = Color.White,
                    onPrimary = Color(0xFF000C1B)
                )
            ) {
                Surface(
                    modifier = Modifier.fillMaxSize(),
                    color = MaterialTheme.colorScheme.background
                ) {
                    if (selectedSessionId != null) {
                        // ── DETAIL SCREEN (full-screen, above nav) ──────────────────────
                        val selectedSession = allSessions.find { it.inningsId == selectedSessionId }
                        val startFormatted = selectedSession?.let {
                            SimpleDateFormat("d MMM HH:mm", Locale.getDefault()).format(Date(it.startTimeMillis))
                        } ?: ""
                        val rawLocation = selectedSession?.locationText ?: ""
                        val suburb = if (rawLocation.contains(",")) rawLocation.substringAfter(",").trim() else rawLocation.trim()
                        val subtitleText = if (startFormatted.isNotEmpty()) "$startFormatted • $suburb" else "INNINGS #${selectedSessionId}"

                        var displaySessionTime by remember { mutableStateOf(false) }
                        var highlightedEventId by remember { mutableStateOf<Int?>(null) }
                        var activePlaybackVideoPath by remember { mutableStateOf<String?>(null) }
                        val listState = rememberLazyListState()
                        val coroutineScope = rememberCoroutineScope()
                        
                        val sessionStartTimestamp = remember(timeline) {
                            timeline.minOfOrNull { it.timestamp } ?: 0L
                        }
                        val shotEvents = remember(timeline) {
                            timeline.filter { it.batSpeed != null }
                        }
                        val timelineShots = remember(timeline) {
                            timeline.filter { it.description != "Session Started" && it.description != "Session Ended" }
                        }
                        val reversedTimelineShots = remember(timelineShots) {
                            timelineShots.reversed()
                        }

                        val isProcessing = remember(timeline, selectedSession) {
                            val now = System.currentTimeMillis()
                            val isRecent = selectedSession?.let { now - it.startTimeMillis < 15 * 60_000L } ?: false
                            val hasShots = timeline.any { it.description.contains("Shot:") || it.batSpeed != null }
                            val isProcessed = hasShots || context.getSharedPreferences("pitch_analytix_prefs", Context.MODE_PRIVATE)
                                .getBoolean("processed_innings_$selectedSessionId", false)
                            isRecent && !isProcessed
                        }

                        Column(modifier = Modifier.fillMaxSize()) {
                            TopBar(
                                title = "SESSION DETAILS",
                                subtitle = subtitleText,
                                showBack = true,
                                onBack = { viewModel.selectInnings(null) },
                                initials = initials,
                                onProfileClick = { showProfileDialog = true }
                            )
                            Box(modifier = Modifier.weight(1f)) {
                                if (isProcessing) {
                                    Box(
                                        modifier = Modifier
                                            .fillMaxSize()
                                            .padding(24.dp),
                                        contentAlignment = Alignment.Center
                                    ) {
                                        Column(
                                            horizontalAlignment = Alignment.CenterHorizontally,
                                            verticalArrangement = Arrangement.spacedBy(16.dp)
                                        ) {
                                            CircularProgressIndicator(color = Color(0xFF58FF63))
                                            Text(
                                                text = "Retrieving and processing raw sensor data from watch...",
                                                color = Color.White.copy(alpha = 0.8f),
                                                fontSize = 14.sp,
                                                textAlign = androidx.compose.ui.text.style.TextAlign.Center
                                            )
                                            Text(
                                                text = "This will take about 1-2 minutes. Please keep your watch close.",
                                                color = Color.Gray,
                                                fontSize = 11.sp,
                                                textAlign = androidx.compose.ui.text.style.TextAlign.Center
                                            )
                                        }
                                    }
                                } else {
                                    LazyColumn(
                                        state = listState,
                                        modifier = Modifier.fillMaxSize(),
                                        contentPadding = PaddingValues(bottom = 24.dp)
                                    ) {
                                        // 1. Summary Dashboard Metrics (Grid)
                                        item {
                                            DashboardSummary(
                                                events = timeline,
                                                onNavigateToShot = { targetEvent ->
                                                    val indexInTimeline = reversedTimelineShots.indexOf(targetEvent)
                                                    if (indexInTimeline != -1) {
                                                        highlightedEventId = targetEvent.id
                                                        coroutineScope.launch {
                                                            // Offset: DashboardSummary is item 0, ShotTypeSummary is item 1, Section Header is item 2
                                                            listState.animateScrollToItem(indexInTimeline + 3)
                                                            // Flash highlight for 1.5s
                                                            kotlinx.coroutines.delay(1500)
                                                            if (highlightedEventId == targetEvent.id) {
                                                                highlightedEventId = null
                                                            }
                                                        }
                                                    }
                                                }
                                            )
                                        }

                                        // 2. Shot Type Summary Table
                                        item {
                                            ShotTypeSummary(events = timeline)
                                        }

                                        // 3. Section Header
                                        item {
                                            Spacer(modifier = Modifier.height(16.dp))
                                            Text(
                                                text = "SHOT TIMELINE",
                                                modifier = Modifier.padding(start = 20.dp, bottom = 8.dp),
                                                fontSize = 12.sp,
                                                fontWeight = FontWeight.Black,
                                                color = MaterialTheme.colorScheme.secondary.copy(alpha = 0.6f),
                                                letterSpacing = 2.sp
                                            )
                                        }

                                        // 4. Shot Card Timeline Items
                                        items(reversedTimelineShots) { event ->
                                             val shotIndex = shotEvents.indexOf(event)
                                             val shotNumber = if (shotIndex != -1) shotIndex + 1 else null
                                             TimelineItem(
                                                 event = event,
                                                 shotNumber = shotNumber,
                                                 displaySessionTime = displaySessionTime,
                                                 sessionStartTimestamp = sessionStartTimestamp,
                                                 isHighlighted = event.id == highlightedEventId,
                                                 onTimeToggle = { displaySessionTime = !displaySessionTime },
                                                 onPlayVideo = { path -> activePlaybackVideoPath = path }
                                             )
                                             Spacer(modifier = Modifier.height(10.dp).padding(horizontal = 16.dp))
                                        }
                                    }
                                }

                                if (activePlaybackVideoPath != null) {
                                    VideoPlayerDialog(
                                        videoPath = activePlaybackVideoPath!!,
                                        onDismiss = { activePlaybackVideoPath = null }
                                    )
                                }
                            }
                        }
                    } else {
                        // ── MAIN APP with 3-TAB NAVIGATION ─────────────────────────────
                        Scaffold(
                            containerColor = MaterialTheme.colorScheme.background,
                            bottomBar = {
                                NavigationBar(
                                    containerColor = MaterialTheme.colorScheme.surface,
                                    tonalElevation = 0.dp,
                                    modifier = Modifier.height(64.dp)
                                ) {
                                    // Dashboard tab
                                    NavigationBarItem(
                                        selected = selectedTab == 0,
                                        onClick = { selectedTab = 0 },
                                        icon = {
                                            Icon(
                                                painter = androidx.compose.ui.res.painterResource(id = R.drawable.ic_dashboard),
                                                contentDescription = "Dashboard",
                                                modifier = Modifier.size(if (selectedTab == 0) 24.dp else 20.dp)
                                            )
                                        },
                                        label = {
                                            Text(
                                                "DASHBOARD",
                                                fontSize = 8.sp,
                                                fontWeight = if (selectedTab == 0) FontWeight.Black else FontWeight.Normal,
                                                letterSpacing = 0.5.sp
                                            )
                                        },
                                        colors = NavigationBarItemDefaults.colors(
                                            selectedIconColor = MaterialTheme.colorScheme.primary,
                                            selectedTextColor = MaterialTheme.colorScheme.primary,
                                            unselectedIconColor = Color.Gray,
                                            unselectedTextColor = Color.Gray,
                                            indicatorColor = MaterialTheme.colorScheme.primary.copy(alpha = 0.1f)
                                        )
                                    )
                                    // Record tab — badge pulses when recording
                                    NavigationBarItem(
                                        selected = selectedTab == 1,
                                        onClick = { selectedTab = 1 },
                                        icon = {
                                            Box {
                                                Icon(
                                                    painter = androidx.compose.ui.res.painterResource(id = R.drawable.ic_record),
                                                    contentDescription = "Record",
                                                    modifier = Modifier.size(if (selectedTab == 1) 24.dp else 20.dp)
                                                )
                                                if (isRecording) {
                                                    val infiniteTransition = rememberInfiniteTransition(label = "badge")
                                                    val badgeAlpha by infiniteTransition.animateFloat(
                                                        initialValue = 0.4f,
                                                        targetValue = 1f,
                                                        animationSpec = infiniteRepeatable(
                                                            animation = tween(600, easing = LinearEasing),
                                                            repeatMode = RepeatMode.Reverse
                                                        ),
                                                        label = "badge_alpha"
                                                    )
                                                    Box(
                                                        modifier = Modifier
                                                            .size(8.dp)
                                                            .clip(CircleShape)
                                                            .background(Color(0xFFFF5252).copy(alpha = badgeAlpha))
                                                            .align(Alignment.TopEnd)
                                                    )
                                                }
                                            }
                                        },
                                        label = {
                                            Text(
                                                "RECORD",
                                                fontSize = 8.sp,
                                                fontWeight = if (selectedTab == 1) FontWeight.Black else FontWeight.Normal,
                                                letterSpacing = 0.5.sp,
                                                color = if (isRecording && selectedTab != 1) Color(0xFFFF5252) else Color.Unspecified
                                            )
                                        },
                                        colors = NavigationBarItemDefaults.colors(
                                            selectedIconColor = MaterialTheme.colorScheme.primary,
                                            selectedTextColor = MaterialTheme.colorScheme.primary,
                                            unselectedIconColor = Color.Gray,
                                            unselectedTextColor = Color.Gray,
                                            indicatorColor = MaterialTheme.colorScheme.primary.copy(alpha = 0.1f)
                                        )
                                    )
                                    // History tab
                                    NavigationBarItem(
                                        selected = selectedTab == 2,
                                        onClick = { selectedTab = 2 },
                                        icon = {
                                            Icon(
                                                painter = androidx.compose.ui.res.painterResource(id = R.drawable.ic_history),
                                                contentDescription = "History",
                                                modifier = Modifier.size(if (selectedTab == 2) 24.dp else 20.dp)
                                            )
                                        },
                                        label = {
                                            Text(
                                                "HISTORY",
                                                fontSize = 8.sp,
                                                fontWeight = if (selectedTab == 2) FontWeight.Black else FontWeight.Normal,
                                                letterSpacing = 0.5.sp
                                            )
                                        },
                                        colors = NavigationBarItemDefaults.colors(
                                            selectedIconColor = MaterialTheme.colorScheme.primary,
                                            selectedTextColor = MaterialTheme.colorScheme.primary,
                                            unselectedIconColor = Color.Gray,
                                            unselectedTextColor = Color.Gray,
                                            indicatorColor = MaterialTheme.colorScheme.primary.copy(alpha = 0.1f)
                                        )
                                    )
                                }
                            }
                        ) { paddingValues ->
                            Column(
                                modifier = Modifier
                                    .fillMaxSize()
                                    .padding(paddingValues)
                            ) {
                                TopBar(
                                    title = "PITCH ANALYTIX",
                                    subtitle = tabSubtitles[selectedTab],
                                    showBack = false,
                                    onBack = {},
                                    initials = initials,
                                    onProfileClick = { showProfileDialog = true }
                                )
                                when (selectedTab) {
                                    0 -> DashboardScreen(allSessions)
                                    1 -> RecordScreen(
                                        isRecording = isRecording,
                                        elapsedSeconds = elapsedSeconds,
                                        maxAmplitude = maxAmplitude,
                                        recordingsList = recordingsList,
                                        onRequestPermission = {
                                            val permissions = if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.S) {
                                                arrayOf(android.Manifest.permission.RECORD_AUDIO, android.Manifest.permission.BLUETOOTH_CONNECT)
                                            } else {
                                                arrayOf(android.Manifest.permission.RECORD_AUDIO)
                                            }
                                            requestAudioPermissionLauncher.launch(permissions)
                                        },
                                        onRequestVideoPermission = {
                                            requestCameraPermissionLauncher.launch(
                                                arrayOf(
                                                    android.Manifest.permission.CAMERA,
                                                    android.Manifest.permission.RECORD_AUDIO
                                                )
                                            )
                                        },
                                        context = context
                                    )
                                    2 -> HistoryScreen(allSessions) { session ->
                                        viewModel.selectInnings(session.inningsId)
                                    }
                                }
                            }
                        }
                    }

                    if (showProfileDialog) {
                        ProfileDialog(
                            currentName = userName,
                            currentWeight = userWeight,
                            currentAge = userAge,
                            currentGender = userGender,
                            onDismiss = { showProfileDialog = false },
                            onSave = { name, weight, age, gender ->
                                userName = name
                                userWeight = weight
                                userAge = age
                                userGender = gender
                                prefs.edit().apply {
                                    putString("user_name", name)
                                    putFloat("user_weight", weight)
                                    putInt("user_age", age)
                                    putString("user_gender", gender)
                                    apply()
                                }
                                showProfileDialog = false
                            }
                        )
                    }
                }
            }
        }
    }
}

@Composable
fun TopBar(title: String, subtitle: String, showBack: Boolean, onBack: () -> Unit, initials: String, onProfileClick: () -> Unit) {
    Surface(
        color = MaterialTheme.colorScheme.surface,
        modifier = Modifier
            .fillMaxWidth()
            .height(72.dp)
            .background(MaterialTheme.colorScheme.primary.copy(alpha = 0.1f))
    ) {
        Row(
            modifier = Modifier.fillMaxSize().padding(horizontal = 16.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.SpaceBetween
        ) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                if (showBack) {
                    Box(
                        modifier = Modifier
                            .padding(end = 12.dp)
                            .size(36.dp)
                            .clip(RoundedCornerShape(8.dp))
                            .background(MaterialTheme.colorScheme.primary.copy(alpha = 0.15f))
                            .clickable { onBack() },
                        contentAlignment = Alignment.Center
                    ) {
                        Text("←", color = MaterialTheme.colorScheme.primary, fontWeight = FontWeight.Black, fontSize = 18.sp)
                    }
                }
                Column {
                    Text(
                        title,
                        fontSize = 18.sp,
                        fontWeight = FontWeight.Black,
                        color = MaterialTheme.colorScheme.primary,
                        letterSpacing = 1.sp
                    )
                    Text(
                        subtitle,
                        fontSize = 10.sp,
                        fontWeight = FontWeight.Bold,
                        color = MaterialTheme.colorScheme.secondary.copy(alpha = 0.7f)
                    )
                }
            }
            Box(
                modifier = Modifier
                    .size(40.dp)
                    .clip(CircleShape)
                    .background(MaterialTheme.colorScheme.primary.copy(alpha = 0.2f))
                    .clickable { onProfileClick() },
                contentAlignment = Alignment.Center
            ) {
                Text(initials, color = MaterialTheme.colorScheme.primary, fontWeight = FontWeight.Bold)
            }
        }
    }
}

@Composable
fun DashboardSummary(
    events: List<InningsEvent>,
    onNavigateToShot: (InningsEvent) -> Unit
) {
    val shotEvents = remember(events) { events.filter { it.batSpeed != null } }
    val maxSpeedEvent = remember(shotEvents) { shotEvents.maxByOrNull { it.batSpeed ?: 0f } }
    val maxSpeedShotNumber = remember(shotEvents, maxSpeedEvent) { maxSpeedEvent?.let { shotEvents.indexOf(it) + 1 } }
    val maxSpeedShotType = maxSpeedEvent?.shotType ?: ""

    val maxEffEvent = remember(shotEvents) { shotEvents.maxByOrNull { it.efficiency ?: 0f } }
    val maxEffShotNumber = remember(shotEvents, maxEffEvent) { maxEffEvent?.let { shotEvents.indexOf(it) + 1 } }
    val maxEffShotType = maxEffEvent?.shotType ?: ""

    val maxBatSpeed = maxSpeedEvent?.batSpeed ?: 0f
    val maxEfficiency = maxEffEvent?.efficiency ?: 0f
    val avgBatSpeed = remember(shotEvents) { shotEvents.mapNotNull { it.batSpeed }.average().let { if (it.isNaN()) 0.0 else it } }
    val avgEfficiency = remember(shotEvents) { shotEvents.mapNotNull { it.efficiency }.average().let { if (it.isNaN()) 0.0 else it } }
    val shotCount = shotEvents.size

    val minTime = events.minOfOrNull { it.timestamp } ?: 0L
    val maxTime = events.maxOfOrNull { it.timestamp } ?: 0L
    val durationMs = if (maxTime > minTime) maxTime - minTime else 0L
    val totalSecs = durationMs / 1000
    val mins = totalSecs / 60
    val secs = totalSecs % 60
    
    val durationVal = String.format(java.util.Locale.US, "%d:%02d", mins, secs)

    Column(
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = 16.dp, vertical = 8.dp),
        verticalArrangement = Arrangement.spacedBy(10.dp)
    ) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(10.dp)
        ) {
            SummaryCard(
                title = "MAX SPEED",
                value = "${maxBatSpeed.toInt()} km/h",
                subtext = if (maxSpeedShotNumber != null) "#$maxSpeedShotNumber $maxSpeedShotType" else "N/A",
                onClick = { maxSpeedEvent?.let { onNavigateToShot(it) } },
                modifier = Modifier.weight(1f)
            )
            SummaryCard(
                title = "MAX EFFICIENCY",
                value = "${maxEfficiency.toInt()}%",
                subtext = if (maxEffShotNumber != null) "#$maxEffShotNumber $maxEffShotType" else "N/A",
                onClick = { maxEffEvent?.let { onNavigateToShot(it) } },
                modifier = Modifier.weight(1f)
            )
            SummaryCard(
                title = "AVG BAT SPEED",
                value = "${avgBatSpeed.toInt()} km/h",
                subtext = "Session Average",
                onClick = null,
                modifier = Modifier.weight(1f)
            )
        }
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(10.dp)
        ) {
            SummaryCard(
                title = "AVG EFFICIENCY",
                value = "${avgEfficiency.toInt()}%",
                subtext = "Session Average",
                onClick = null,
                modifier = Modifier.weight(1f)
            )
            SummaryCard(
                title = "SHOTS",
                value = "$shotCount",
                subtext = "Count",
                onClick = null,
                modifier = Modifier.weight(1f)
            )
            SummaryCard(
                title = "DURATION",
                value = durationVal,
                subtext = "MM:SS",
                onClick = null,
                modifier = Modifier.weight(1f)
            )
        }
    }
}

@Composable
fun SummaryCard(
    title: String,
    value: String,
    subtext: String,
    onClick: (() -> Unit)?,
    modifier: Modifier = Modifier
) {
    val clickableModifier = if (onClick != null) {
        Modifier.clickable { onClick() }
    } else {
        Modifier
    }

    Card(
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        modifier = modifier
            .height(98.dp)
            .then(clickableModifier),
        shape = RoundedCornerShape(12.dp),
        border = androidx.compose.foundation.BorderStroke(1.dp, if (onClick != null) MaterialTheme.colorScheme.primary.copy(alpha = 0.3f) else Color.White.copy(alpha = 0.05f))
    ) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(horizontal = 10.dp, vertical = 8.dp),
            verticalArrangement = Arrangement.SpaceBetween
        ) {
            Text(
                text = title,
                fontSize = 8.sp,
                fontWeight = FontWeight.Bold,
                color = Color.Gray,
                letterSpacing = 0.5.sp,
                maxLines = 1
            )
            Text(
                text = value,
                fontSize = 18.sp,
                fontWeight = FontWeight.Black,
                color = if (onClick != null) MaterialTheme.colorScheme.primary else Color.White,
                maxLines = 1
            )
            Row(verticalAlignment = Alignment.CenterVertically) {
                if (onClick != null) {
                    Text(
                        text = "🔗 ",
                        fontSize = 8.sp
                    )
                }
                Text(
                    text = subtext,
                    fontSize = 8.sp,
                    fontWeight = FontWeight.Bold,
                    color = MaterialTheme.colorScheme.secondary,
                    letterSpacing = 0.2.sp,
                    maxLines = 1
                )
            }
        }
    }
}

fun getShotColor(shotType: String?, isHit: Boolean = true): Color {
    if (!isHit) return Color(0xFFFF5252) // Miss is always red
    val name = shotType?.uppercase() ?: return Color.Gray
    return when {
        "SLOG" in name || "POWER SHOT" in name -> Color(0xFFFF2E93) // Magenta
        "POWER DRIVE" in name -> Color(0xFF58FF63) // Neon Green
        "PULL" in name || "HOOK" in name -> Color(0xFFFF9F2E) // Orange
        "SWEEP" in name -> Color(0xFFFFFF96) // Yellow
        "GLANCE" in name || "FLICK" in name -> Color(0xFFFF85A2) // Pink
        "CUT" in name || "PUNCH" in name -> Color(0xFF2EFFF0) // Cyan
        "GUIDE" in name || "GLIDE" in name || "DEFLECTION" in name -> Color(0xFFAF2EFF) // Purple
        "DRIVE" in name || "DEFENCE" in name || "DEFENSE" in name -> Color(0xFFBCD2FE) // Light Blue
        else -> Color.Gray
    }
}

@Composable
fun ShotTypeSummary(events: List<InningsEvent>) {
    val shotEvents = remember(events) { events.filter { it.batSpeed != null && it.shotType != null } }
    if (shotEvents.isEmpty()) return

    val grouped = remember(shotEvents) { shotEvents.groupBy { it.shotType!! } }

    Column(
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = 16.dp, vertical = 12.dp)
    ) {
        Text(
            text = "SHOT TYPES PLAYED",
            fontSize = 14.sp,
            fontWeight = FontWeight.Black,
            color = Color.White,
            letterSpacing = 1.sp,
            modifier = Modifier.padding(bottom = 12.dp)
        )

        grouped.entries.sortedByDescending { it.value.size }.forEach { entry ->
            val rawTypeName = entry.key
            val group = entry.value
            val count = group.size
            
            val maxSpeed = group.mapNotNull { it.batSpeed }.maxOrNull() ?: 0f
            val avgSpeed = group.mapNotNull { it.batSpeed }.average().let { if (it.isNaN()) 0.0 else it }.toFloat()
            
            val maxEff = group.mapNotNull { it.efficiency }.maxOrNull() ?: 0f
            val avgEff = group.mapNotNull { it.efficiency }.average().let { if (it.isNaN()) 0.0 else it }.toFloat()
            
            val avgFace = group.mapNotNull { it.bladeAngle }.average().let { if (it.isNaN()) 0.0 else it }.toFloat()
            val avgFaceDesc = when {
                avgFace < -1.5f -> "Open"
                avgFace > 1.5f -> "Closed"
                else -> "Full face"
            }
            val avgFaceAngleText = "${String.format(java.util.Locale.US, "%.0f", avgFace)}°"

            val avgLaunch = group.mapNotNull { it.launchAngle }.average().let { if (it.isNaN()) 0.0 else it }.toFloat()
            val avgLaunchDesc = when {
                avgLaunch > 1.5f -> "Lofted"
                avgLaunch < -1.5f -> "Ground"
                else -> "Flat"
            }
            val avgLaunchAngleText = "${String.format(java.util.Locale.US, "%.0f", Math.abs(avgLaunch.toDouble()))}°"

            val indicatorColor = getShotColor(rawTypeName, isHit = true)

            Card(
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface.copy(alpha = 0.4f)),
                shape = RoundedCornerShape(12.dp),
                border = BorderStroke(1.dp, Color.White.copy(alpha = 0.05f)),
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(bottom = 10.dp)
            ) {
                Column(modifier = Modifier.padding(horizontal = 12.dp, vertical = 10.dp)) {
                    // Top Row: Indicator, Name and Shots Count
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Box(
                                modifier = Modifier
                                    .size(8.dp)
                                    .clip(CircleShape)
                                    .background(indicatorColor)
                            )
                            Spacer(modifier = Modifier.width(8.dp))
                            Text(
                                text = rawTypeName.uppercase(),
                                fontSize = 13.sp,
                                fontWeight = FontWeight.Bold,
                                color = Color.White
                            )
                        }
                        Text(
                            text = "$count ${if (count == 1) "SHOT" else "SHOTS"}",
                            fontSize = 11.sp,
                            fontWeight = FontWeight.Bold,
                            color = Color(0xFFFFD54F) // Gold/yellow color
                        )
                    }

                    // Bottom Row: 4 Metric Columns
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(top = 8.dp),
                        horizontalArrangement = Arrangement.SpaceBetween
                    ) {
                        // KM/H Column
                        ShotTypeMetricCol(
                            title = "KM/H",
                            largeVal = "${maxSpeed.toInt()}",
                            smallVal = "${avgSpeed.toInt()}",
                            modifier = Modifier.weight(0.9f)
                        )

                        // EFF Column
                        ShotTypeMetricCol(
                            title = "EFF",
                            largeVal = "${maxEff.toInt()}",
                            smallVal = "${avgEff.toInt()}",
                            modifier = Modifier.weight(0.8f)
                        )

                        // FACE Column
                        ShotTypeMetricCol(
                            title = "FACE",
                            largeVal = avgFaceDesc,
                            smallVal = avgFaceAngleText,
                            modifier = Modifier.weight(1.1f)
                        )

                        // LAUNCH Column
                        ShotTypeMetricCol(
                            title = "LAUNCH",
                            largeVal = avgLaunchDesc,
                            smallVal = avgLaunchAngleText,
                            modifier = Modifier.weight(1.2f)
                        )
                    }
                }
            }
        }
    }
}

@Composable
fun ShotTypeMetricCol(
    title: String,
    largeVal: String,
    smallVal: String,
    modifier: Modifier = Modifier
) {
    Column(modifier = modifier) {
        Text(
            text = title,
            fontSize = 8.sp,
            fontWeight = FontWeight.Bold,
            color = Color.Gray,
            letterSpacing = 0.5.sp,
            style = LocalTextStyle.current.copy(
                platformStyle = androidx.compose.ui.text.PlatformTextStyle(
                    includeFontPadding = false
                )
            )
        )
        Row(
            verticalAlignment = Alignment.Bottom,
            modifier = Modifier.offset(y = (-4).dp)
        ) {
            Text(
                text = largeVal,
                fontSize = 11.sp,
                fontWeight = FontWeight.Medium,
                color = Color.White,
                style = LocalTextStyle.current.copy(
                    platformStyle = androidx.compose.ui.text.PlatformTextStyle(
                        includeFontPadding = false
                    )
                )
            )
            Spacer(modifier = Modifier.width(3.dp))
            Text(
                text = smallVal,
                fontSize = 9.sp,
                fontWeight = FontWeight.Normal,
                color = Color.Gray,
                style = LocalTextStyle.current.copy(
                    platformStyle = androidx.compose.ui.text.PlatformTextStyle(
                        includeFontPadding = false
                    )
                )
            )
        }
    }
}

// ── Dashboard Tab ──────────────────────────────────────────────────────────────
@Composable
fun DashboardScreen(allSessions: List<SessionHistoryItem>) {
    val careerMaxSpeed = allSessions.map { it.maxSpeed }.maxOrNull() ?: 0f
    val totalShots = allSessions.sumOf { it.totalShots }
    val sessionCount = allSessions.size
    val bestSession = allSessions.maxByOrNull { it.maxSpeed }
    val lastSession = allSessions.firstOrNull()

    LazyColumn(
        modifier = Modifier.fillMaxSize(),
        contentPadding = PaddingValues(start = 16.dp, end = 16.dp, top = 20.dp, bottom = 24.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        // Hero career best card
        item {
            Card(
                colors = CardDefaults.cardColors(containerColor = Color(0xFF001F4D)),
                shape = RoundedCornerShape(24.dp),
                border = BorderStroke(1.dp, Color(0xFF58FF63).copy(alpha = 0.25f)),
                modifier = Modifier.fillMaxWidth()
            ) {
                Column(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(24.dp),
                    horizontalAlignment = Alignment.CenterHorizontally
                ) {
                    Text(
                        "🏏  CAREER BEST",
                        fontSize = 11.sp,
                        fontWeight = FontWeight.Black,
                        color = Color(0xFFBCD2FE),
                        letterSpacing = 2.sp
                    )
                    Spacer(modifier = Modifier.height(8.dp))
                    Text(
                        "${careerMaxSpeed.toInt()}",
                        fontSize = 72.sp,
                        fontWeight = FontWeight.Black,
                        color = Color(0xFF58FF63),
                        lineHeight = 76.sp
                    )
                    Text(
                        "KM/H BAT SPEED",
                        fontSize = 12.sp,
                        fontWeight = FontWeight.Bold,
                        color = Color(0xFFBCD2FE).copy(alpha = 0.7f),
                        letterSpacing = 1.5.sp
                    )
                }
            }
        }
        // Shots + Sessions side by side
        item {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(12.dp)
            ) {
                // Shots card
                Card(
                    colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
                    shape = RoundedCornerShape(20.dp),
                    border = BorderStroke(1.dp, Color.White.copy(alpha = 0.05f)),
                    modifier = Modifier.weight(1f)
                ) {
                    Column(
                        modifier = Modifier.fillMaxWidth().padding(20.dp),
                        horizontalAlignment = Alignment.Start
                    ) {
                        Text("TOTAL SHOTS", fontSize = 9.sp, fontWeight = FontWeight.Bold, color = Color.Gray, letterSpacing = 1.sp)
                        Spacer(modifier = Modifier.height(6.dp))
                        Text(
                            "$totalShots",
                            fontSize = 44.sp,
                            fontWeight = FontWeight.Black,
                            color = Color(0xFF58FF63)
                        )
                        Text("shots", fontSize = 11.sp, color = Color(0xFFBCD2FE).copy(alpha = 0.7f))
                    }
                }
                // Sessions card
                Card(
                    colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
                    shape = RoundedCornerShape(20.dp),
                    border = BorderStroke(1.dp, Color.White.copy(alpha = 0.05f)),
                    modifier = Modifier.weight(1f)
                ) {
                    Column(
                        modifier = Modifier.fillMaxWidth().padding(20.dp),
                        horizontalAlignment = Alignment.Start
                    ) {
                        Text("SESSIONS", fontSize = 9.sp, fontWeight = FontWeight.Bold, color = Color.Gray, letterSpacing = 1.sp)
                        Spacer(modifier = Modifier.height(6.dp))
                        Text(
                            "$sessionCount",
                            fontSize = 44.sp,
                            fontWeight = FontWeight.Black,
                            color = Color(0xFF58FF63)
                        )
                        Text("tracked", fontSize = 11.sp, color = Color(0xFFBCD2FE).copy(alpha = 0.7f))
                    }
                }
            }
        }
        // Best session quick-view
        if (bestSession != null) {
            item {
                Text(
                    "BEST SESSION",
                    fontSize = 10.sp,
                    fontWeight = FontWeight.Black,
                    color = Color(0xFFBCD2FE).copy(alpha = 0.6f),
                    letterSpacing = 2.sp
                )
            }
            item {
                val bestDate = SimpleDateFormat("d MMM", Locale.getDefault()).format(Date(bestSession.startTimeMillis))
                Card(
                    colors = CardDefaults.cardColors(containerColor = Color(0xFF001B3D)),
                    shape = RoundedCornerShape(16.dp),
                    border = BorderStroke(1.dp, Color(0xFF58FF63).copy(alpha = 0.15f)),
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Row(
                        modifier = Modifier.padding(16.dp),
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.SpaceBetween
                    ) {
                        Column {
                            Text(bestDate, fontSize = 13.sp, fontWeight = FontWeight.Black, color = Color.White)
                            Text(bestSession.locationText.substringAfter(",").trim().ifEmpty { bestSession.locationText }, fontSize = 11.sp, color = Color.Gray)
                        }
                        Row(horizontalArrangement = Arrangement.spacedBy(16.dp)) {
                            Column(horizontalAlignment = Alignment.CenterHorizontally) {
                                Text("${bestSession.maxSpeed.toInt()}", fontSize = 20.sp, fontWeight = FontWeight.Black, color = Color(0xFF58FF63))
                                Text("KM/H", fontSize = 8.sp, color = Color.Gray, letterSpacing = 1.sp)
                            }
                            Column(horizontalAlignment = Alignment.CenterHorizontally) {
                                Text("${bestSession.avgEfficiency.toInt()}%", fontSize = 20.sp, fontWeight = FontWeight.Black, color = Color(0xFF58FF63))
                                Text("EFF", fontSize = 8.sp, color = Color.Gray, letterSpacing = 1.sp)
                            }
                            Column(horizontalAlignment = Alignment.CenterHorizontally) {
                                Text("${bestSession.totalShots}", fontSize = 20.sp, fontWeight = FontWeight.Black, color = Color(0xFF58FF63))
                                Text("SHOTS", fontSize = 8.sp, color = Color.Gray, letterSpacing = 1.sp)
                            }
                        }
                    }
                }
            }
        }
        // Last session quick-view (if different from best)
        if (lastSession != null && lastSession.inningsId != bestSession?.inningsId) {
            item {
                Text(
                    "LAST SESSION",
                    fontSize = 10.sp,
                    fontWeight = FontWeight.Black,
                    color = Color(0xFFBCD2FE).copy(alpha = 0.6f),
                    letterSpacing = 2.sp
                )
            }
            item {
                val lastDate = SimpleDateFormat("d MMM HH:mm", Locale.getDefault()).format(Date(lastSession.startTimeMillis))
                val durationMs = lastSession.endTimeMillis - lastSession.startTimeMillis
                val mins = durationMs / 1000 / 60
                val secs = durationMs / 1000 % 60
                val dur = if (mins > 0) "${mins}m ${secs}s" else "${secs}s"
                Card(
                    colors = CardDefaults.cardColors(containerColor = Color(0xFF001B3D)),
                    shape = RoundedCornerShape(16.dp),
                    border = BorderStroke(1.dp, Color.White.copy(alpha = 0.05f)),
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Row(
                        modifier = Modifier.padding(16.dp),
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.SpaceBetween
                    ) {
                        Column {
                            Text(lastDate, fontSize = 13.sp, fontWeight = FontWeight.Black, color = Color.White)
                            Text(lastSession.locationText.substringAfter(",").trim().ifEmpty { lastSession.locationText }, fontSize = 11.sp, color = Color.Gray)
                            Spacer(modifier = Modifier.height(4.dp))
                            Text("${lastSession.totalShots} shots · ${lastSession.maxSpeed.toInt()} km/h · $dur", fontSize = 11.sp, color = Color(0xFFBCD2FE))
                        }
                    }
                }
            }
        }
        // Empty state
        if (allSessions.isEmpty()) {
            item {
                Card(
                    colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface.copy(alpha = 0.4f)),
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(24.dp),
                    border = BorderStroke(1.dp, Color.White.copy(alpha = 0.05f))
                ) {
                    Column(
                        modifier = Modifier.fillMaxWidth().padding(32.dp),
                        horizontalAlignment = Alignment.CenterHorizontally,
                        verticalArrangement = Arrangement.spacedBy(12.dp)
                    ) {
                        Text("🏏", fontSize = 48.sp)
                        Text("NO SESSIONS YET", fontSize = 14.sp, fontWeight = FontWeight.Black, color = Color.White, letterSpacing = 1.sp)
                        Text(
                            "Head to the Record tab to start your first session. Your stats will appear here.",
                            fontSize = 12.sp, color = Color.Gray,
                            textAlign = androidx.compose.ui.text.style.TextAlign.Center,
                            lineHeight = 18.sp
                        )
                    }
                }
            }
        }
    }
}

// ── Record Tab ─────────────────────────────────────────────────────────────────
@Composable
fun RecordScreen(
    isRecording: Boolean,
    elapsedSeconds: Long,
    maxAmplitude: Float,
    recordingsList: List<java.io.File>,
    onRequestPermission: () -> Unit,
    onRequestVideoPermission: () -> Unit,
    context: android.content.Context
) {
    val prefs = remember { context.getSharedPreferences("pitch_analytix_prefs", Context.MODE_PRIVATE) }
    var audioEnabled by remember { mutableStateOf(prefs.getBoolean("audio_narration_enabled", true)) }
    var polarEnabled by remember { mutableStateOf(prefs.getBoolean("bottom_hand_sensor_enabled", false)) }
    var videoEnabled by remember { mutableStateOf(prefs.getBoolean("record_video_enabled", false)) }

    val polarState by com.mrpeel.cricketbattingtracker.services.PolarSenseManager.connectionState.collectAsState()
    val polarSampleCount by com.mrpeel.cricketbattingtracker.services.PolarSenseManager.sampleCount.collectAsState()
    val polarTaps by com.mrpeel.cricketbattingtracker.services.PolarSenseManager.detectedTapSequences.collectAsState()
    val pairedDevice by com.mrpeel.cricketbattingtracker.services.PolarSenseManager.pairedDeviceId.collectAsState()

    var showPairingScreen by remember { mutableStateOf(false) }
    var showVideoConfigScreen by remember { mutableStateOf(false) }

    if (showPairingScreen) {
        PolarPairingScreen(
            context = context,
            onBack = { showPairingScreen = false }
        )
        return
    }

    if (showVideoConfigScreen) {
        VideoSetupScreen(
            context = context,
            onBack = { showVideoConfigScreen = false }
        )
        return
    }

    val isVideoRecording by com.mrpeel.cricketbattingtracker.services.VideoRecordManager.isRecording.collectAsState()
    val videoElapsed by com.mrpeel.cricketbattingtracker.services.VideoRecordManager.elapsedSeconds.collectAsState()

    // Determine overall active session state
    val sessionActive = isRecording || isVideoRecording

    if (videoEnabled && (sessionActive || isVideoRecording)) {
        VideoRecordScreen(
            isRecording = isVideoRecording,
            elapsedSeconds = videoElapsed,
            onStartClick = {
                val hasCamera = androidx.core.content.ContextCompat.checkSelfPermission(
                    context, android.Manifest.permission.CAMERA
                ) == android.content.pm.PackageManager.PERMISSION_GRANTED
                val hasAudio = androidx.core.content.ContextCompat.checkSelfPermission(
                    context, android.Manifest.permission.RECORD_AUDIO
                ) == android.content.pm.PackageManager.PERMISSION_GRANTED
                if (hasCamera && hasAudio) {
                    com.mrpeel.cricketbattingtracker.services.VideoRecordManager.startRecording(context)
                } else {
                    onRequestVideoPermission()
                }
            },
            onSaveClick = {
                com.mrpeel.cricketbattingtracker.services.VideoRecordManager.stopAndSave(context)
                // Stop other enabled services
                if (isRecording) {
                    com.mrpeel.cricketbattingtracker.services.AudioRecordManager.stopRecording(context)
                }
                if (polarState == com.mrpeel.cricketbattingtracker.services.PolarConnectionState.STREAMING) {
                    val serviceIntent = Intent(context, com.mrpeel.cricketbattingtracker.services.PolarSenseService::class.java).apply {
                        action = com.mrpeel.cricketbattingtracker.services.PolarSenseService.ACTION_STOP
                    }
                    context.startService(serviceIntent)
                }
            },
            onCancelClick = {
                if (isVideoRecording) {
                    com.mrpeel.cricketbattingtracker.services.VideoRecordManager.discard(context)
                }
                if (isRecording) {
                    com.mrpeel.cricketbattingtracker.services.AudioRecordManager.discardRecording(context)
                }
                if (polarState == com.mrpeel.cricketbattingtracker.services.PolarConnectionState.STREAMING) {
                    val serviceIntent = Intent(context, com.mrpeel.cricketbattingtracker.services.PolarSenseService::class.java).apply {
                        action = com.mrpeel.cricketbattingtracker.services.PolarSenseService.ACTION_STOP
                    }
                    context.startService(serviceIntent)
                }
            }
        )
        return
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(top = 8.dp)
            .verticalScroll(rememberScrollState()),
        verticalArrangement = Arrangement.spacedBy(0.dp)
    ) {
        UnifiedConsoleCard(
            sessionActive = sessionActive,
            audioEnabled = audioEnabled,
            onAudioToggle = {
                audioEnabled = it
                prefs.edit().putBoolean("audio_narration_enabled", it).apply()
            },
            polarEnabled = polarEnabled,
            onPolarToggle = {
                if (pairedDevice == null && it) {
                    showPairingScreen = true
                } else {
                    polarEnabled = it
                    prefs.edit().putBoolean("bottom_hand_sensor_enabled", it).apply()
                }
            },
            videoEnabled = videoEnabled,
            onVideoToggle = {
                if (it) {
                    val hasCamera = androidx.core.content.ContextCompat.checkSelfPermission(
                        context, android.Manifest.permission.CAMERA
                    ) == android.content.pm.PackageManager.PERMISSION_GRANTED
                    if (!hasCamera) {
                        onRequestVideoPermission()
                    } else {
                        videoEnabled = true
                        prefs.edit().putBoolean("record_video_enabled", true).apply()
                    }
                } else {
                    videoEnabled = false
                    prefs.edit().putBoolean("record_video_enabled", false).apply()
                }
            },
            polarState = polarState,
            polarSampleCount = polarSampleCount,
            polarTaps = polarTaps.size,
            pairedDevice = pairedDevice,
            onPairingClick = { showPairingScreen = true },
            onVideoConfigClick = {
                val hasCamera = androidx.core.content.ContextCompat.checkSelfPermission(
                    context, android.Manifest.permission.CAMERA
                ) == android.content.pm.PackageManager.PERMISSION_GRANTED
                if (!hasCamera) {
                    onRequestVideoPermission()
                } else {
                    showVideoConfigScreen = true
                }
            },
            elapsedSeconds = if (videoEnabled) videoElapsed else elapsedSeconds,
            maxAmplitude = maxAmplitude,
            recordingsList = recordingsList,
            onRequestPermission = onRequestPermission,
            onRequestVideoPermission = onRequestVideoPermission,
            context = context
        )
    }
}


// ── Video Record Screen ─────────────────────────────────────────────────────────
@Composable
fun VideoRecordScreen(
    isRecording: Boolean,
    elapsedSeconds: Long,
    onStartClick: () -> Unit,
    onSaveClick: () -> Unit,
    onCancelClick: () -> Unit
) {
    val neonGreen = Color(0xFF58FF63)

    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(Color(0xFF000C1B))
    ) {
        if (!isRecording) {
            // ── Phase 1: Camera Preview ──────────────────────────────────────
            Column(modifier = Modifier.fillMaxSize()) {
                // Camera preview fills most of the screen
                Box(
                    modifier = Modifier
                        .fillMaxWidth()
                        .weight(1f)
                ) {
                    androidx.compose.ui.viewinterop.AndroidView(
                        factory = { ctx ->
                            val previewView = androidx.camera.view.PreviewView(ctx).apply {
                                implementationMode = androidx.camera.view.PreviewView.ImplementationMode.PERFORMANCE
                                scaleType = androidx.camera.view.PreviewView.ScaleType.FIT_CENTER
                            }
                            val prefs = ctx.getSharedPreferences("pitch_analytix_prefs", Context.MODE_PRIVATE)
                            val cameraFacing = prefs.getString("video_camera_facing", "back") ?: "back"
                            val zoomValue = prefs.getFloat("video_zoom_value", 0.0f)

                            // Bind camera preview
                            val cameraProviderFuture = androidx.camera.lifecycle.ProcessCameraProvider.getInstance(ctx)
                            val lifecycleOwner = ctx as? androidx.lifecycle.LifecycleOwner
                            cameraProviderFuture.addListener({
                                try {
                                    val cameraProvider = cameraProviderFuture.get()
                                    val preview = androidx.camera.core.Preview.Builder().build().also {
                                        it.setSurfaceProvider(previewView.surfaceProvider)
                                    }
                                    val cameraSelector = if (cameraFacing == "front") {
                                        androidx.camera.core.CameraSelector.DEFAULT_FRONT_CAMERA
                                    } else {
                                        androidx.camera.core.CameraSelector.DEFAULT_BACK_CAMERA
                                    }
                                    cameraProvider.unbindAll()
                                    if (lifecycleOwner != null) {
                                        val camera = cameraProvider.bindToLifecycle(
                                            lifecycleOwner,
                                            cameraSelector,
                                            preview
                                        )
                                        camera.cameraControl.setLinearZoom(zoomValue)
                                    }
                                } catch (e: Exception) {
                                    android.util.Log.e("VideoRecordScreen", "Preview bind failed: ${e.message}")
                                }
                            }, androidx.core.content.ContextCompat.getMainExecutor(ctx))
                            previewView
                        },
                        modifier = Modifier.fillMaxSize()
                    )

                    // Overlay: position guide
                    Box(
                        modifier = Modifier
                            .fillMaxWidth()
                            .align(Alignment.TopCenter)
                            .background(Color.Black.copy(alpha = 0.55f))
                            .padding(horizontal = 16.dp, vertical = 10.dp)
                    ) {
                        Column(horizontalAlignment = Alignment.CenterHorizontally,
                               modifier = Modifier.fillMaxWidth()) {
                            Text(
                                "🎥  VIDEO ANALYSIS MODE",
                                fontSize = 10.sp,
                                fontWeight = FontWeight.Black,
                                color = neonGreen,
                                letterSpacing = 1.5.sp
                            )
                            Text(
                                "Position camera at 45° to batting crease, then tap Start.",
                                fontSize = 11.sp,
                                color = Color.White.copy(alpha = 0.8f),
                                lineHeight = 15.sp,
                                textAlign = androidx.compose.ui.text.style.TextAlign.Center
                            )
                        }
                    }
                }

                // Bottom controls
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(horizontal = 20.dp, vertical = 16.dp),
                    horizontalArrangement = Arrangement.spacedBy(12.dp)
                ) {
                    OutlinedButton(
                        onClick = onCancelClick,
                        modifier = Modifier.weight(1f).height(48.dp),
                        shape = RoundedCornerShape(14.dp),
                        colors = ButtonDefaults.outlinedButtonColors(contentColor = Color.White),
                        border = BorderStroke(1.dp, Color.White.copy(alpha = 0.2f))
                    ) {
                        Text("CANCEL", fontWeight = FontWeight.Bold, fontSize = 12.sp)
                    }
                    Button(
                        onClick = onStartClick,
                        modifier = Modifier.weight(1.5f).height(48.dp),
                        shape = RoundedCornerShape(14.dp),
                        colors = ButtonDefaults.buttonColors(containerColor = neonGreen)
                    ) {
                        Text("START", fontWeight = FontWeight.Black, fontSize = 13.sp,
                             color = Color(0xFF000C1B), letterSpacing = 1.sp)
                    }
                }
            }
        } else {
            // ── Phase 2: Recording Status ────────────────────────────────────
            Column(
                modifier = Modifier.fillMaxSize().padding(24.dp),
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.Center
            ) {
                val infiniteTransition = rememberInfiniteTransition(label = "rec_pulse")
                val pulseAlpha by infiniteTransition.animateFloat(
                    initialValue = 0.3f, targetValue = 1f,
                    animationSpec = infiniteRepeatable(
                        animation = tween(700, easing = LinearEasing),
                        repeatMode = RepeatMode.Reverse
                    ), label = "alpha"
                )
                Row(verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                    Box(modifier = Modifier.size(12.dp).clip(CircleShape)
                        .background(Color(0xFFFF5252).copy(alpha = pulseAlpha)))
                    Text("RECORDING", fontSize = 12.sp, fontWeight = FontWeight.Black,
                         color = Color(0xFFFF5252), letterSpacing = 2.sp)
                }

                Spacer(modifier = Modifier.height(16.dp))

                val mins = elapsedSeconds / 60
                val secs = elapsedSeconds % 60
                Text(
                    String.format(Locale.US, "%02d:%02d", mins, secs),
                    fontSize = 52.sp, fontWeight = FontWeight.Black, color = Color.White,
                    letterSpacing = 2.sp
                )

                Spacer(modifier = Modifier.height(8.dp))
                Text("120fps video + watch sensors active", fontSize = 11.sp, color = Color.Gray)

                Spacer(modifier = Modifier.height(40.dp))

                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(12.dp)
                ) {
                    OutlinedButton(
                        onClick = onCancelClick,
                        modifier = Modifier.weight(1f).height(48.dp),
                        shape = RoundedCornerShape(14.dp),
                        colors = ButtonDefaults.outlinedButtonColors(contentColor = Color.White),
                        border = BorderStroke(1.dp, Color.White.copy(alpha = 0.2f))
                    ) {
                        Text("DISCARD", fontWeight = FontWeight.Bold, fontSize = 11.sp)
                    }
                    Button(
                        onClick = onSaveClick,
                        modifier = Modifier.weight(1.5f).height(48.dp),
                        shape = RoundedCornerShape(14.dp),
                        colors = ButtonDefaults.buttonColors(containerColor = neonGreen)
                    ) {
                        Text("CLOSE & SAVE", fontWeight = FontWeight.Black, fontSize = 11.sp,
                             color = Color(0xFF000C1B), letterSpacing = 0.5.sp)
                    }
                }
            }
        }
    }
}

// ── History Tab ────────────────────────────────────────────────────────────────
@Composable
fun HistoryScreen(allSessions: List<SessionHistoryItem>, onSessionClick: (SessionHistoryItem) -> Unit) {
    if (allSessions.isEmpty()) {
        Box(
            modifier = Modifier.fillMaxSize(),
            contentAlignment = Alignment.Center
        ) {
            Column(
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.spacedBy(12.dp),
                modifier = Modifier.padding(32.dp)
            ) {
                Text("🏏", fontSize = 48.sp)
                Text("NO SESSIONS SYNCED YET", fontSize = 14.sp, fontWeight = FontWeight.Black, color = Color.White, letterSpacing = 1.sp)
                Text(
                    "Sync data from your Wear OS watch to see sessions here.",
                    fontSize = 12.sp, color = Color.Gray,
                    textAlign = androidx.compose.ui.text.style.TextAlign.Center,
                    lineHeight = 18.sp
                )
            }
        }
    } else {
        LazyColumn(
            modifier = Modifier.fillMaxSize().padding(horizontal = 16.dp),
            contentPadding = PaddingValues(top = 12.dp, bottom = 24.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            items(allSessions) { session ->
                SessionHistoryCard(session) { onSessionClick(session) }
            }
        }
    }
}

@Composable
fun SessionHistoryCard(session: SessionHistoryItem, onClick: () -> Unit) {
    val durationMs = session.endTimeMillis - session.startTimeMillis
    val totalSecs = durationMs / 1000
    val mins = totalSecs / 60
    val secs = totalSecs % 60
    val durationText = if (mins > 0) "${mins}m ${secs}s" else "${secs}s"
    val startFormatted = SimpleDateFormat("d MMM HH:mm", Locale.getDefault()).format(Date(session.startTimeMillis))

    Card(
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface.copy(alpha = 0.6f)),
        modifier = Modifier.fillMaxWidth().clickable { onClick() },
        shape = RoundedCornerShape(16.dp),
        border = androidx.compose.foundation.BorderStroke(1.dp, Color.White.copy(alpha = 0.05f))
    ) {
        Row(
            modifier = Modifier.padding(16.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.SpaceBetween
        ) {
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    startFormatted,
                    fontSize = 14.sp,
                    fontWeight = FontWeight.Black,
                    color = Color.White
                )
                Text(
                    session.locationText,
                    fontSize = 11.sp,
                    color = Color.Gray
                )
                Spacer(modifier = Modifier.height(8.dp))
                Row(horizontalArrangement = Arrangement.spacedBy(16.dp)) {
                    Column {
                        Text("SHOTS", fontSize = 8.sp, fontWeight = FontWeight.Bold, color = Color.Gray)
                        Text("${session.totalShots}", fontSize = 12.sp, fontWeight = FontWeight.Black, color = MaterialTheme.colorScheme.primary)
                    }
                    Column {
                        Text("MAX SPEED", fontSize = 8.sp, fontWeight = FontWeight.Bold, color = Color.Gray)
                        Text("${session.maxSpeed.toInt()} km/h", fontSize = 12.sp, fontWeight = FontWeight.Black, color = MaterialTheme.colorScheme.primary)
                    }
                    Column {
                        Text("AVG EFF", fontSize = 8.sp, fontWeight = FontWeight.Bold, color = Color.Gray)
                        Text("${session.avgEfficiency.toInt()}%", fontSize = 12.sp, fontWeight = FontWeight.Black, color = MaterialTheme.colorScheme.primary)
                    }
                    Column {
                        Text("DURATION", fontSize = 8.sp, fontWeight = FontWeight.Bold, color = Color.Gray)
                        Text(durationText, fontSize = 12.sp, fontWeight = FontWeight.Black, color = MaterialTheme.colorScheme.primary)
                    }
                }
            }
            Text("→", fontSize = 18.sp, fontWeight = FontWeight.Black, color = MaterialTheme.colorScheme.primary)
        }
    }
}

@Composable
fun HealthSyncBar(onSync: () -> Unit) {
    Card(
        colors = CardDefaults.cardColors(containerColor = Color(0xFF001F4D)),
        modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 8.dp),
        shape = RoundedCornerShape(12.dp),
        border = androidx.compose.foundation.BorderStroke(1.dp, MaterialTheme.colorScheme.primary.copy(alpha = 0.3f))
    ) {
        Row(
            modifier = Modifier.padding(12.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.SpaceBetween
        ) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Box(
                    modifier = Modifier
                        .size(28.dp)
                        .clip(CircleShape)
                        .background(MaterialTheme.colorScheme.primary.copy(alpha = 0.2f)),
                    contentAlignment = Alignment.Center
                ) {
                    Text("❤️", fontSize = 14.sp)
                }
                Spacer(modifier = Modifier.width(12.dp))
                Column {
                    Text("Samsung Health Sync", fontSize = 12.sp, fontWeight = FontWeight.Black, color = Color.White)
                    Text("Keep workout and vitals linked", fontSize = 10.sp, color = Color.Gray)
                }
            }
            Button(
                onClick = { onSync() },
                colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.primary),
                contentPadding = PaddingValues(horizontal = 12.dp, vertical = 4.dp),
                shape = RoundedCornerShape(8.dp),
                modifier = Modifier.height(28.dp)
            ) {
                Text("Sync Now", fontSize = 10.sp, fontWeight = FontWeight.Black, color = Color(0xFF000C1B))
            }
        }
    }
}

@Composable
fun TimelineItem(
    event: InningsEvent,
    shotNumber: Int?,
    displaySessionTime: Boolean,
    sessionStartTimestamp: Long,
    isHighlighted: Boolean,
    onTimeToggle: () -> Unit,
    onPlayVideo: (String) -> Unit
) {
    val isHit = !event.description.contains("Miss")
    val accentColor = getShotColor(event.shotType, isHit)

    val borderAlpha by animateFloatAsState(
        targetValue = if (isHighlighted) 0.8f else 0.15f,
        animationSpec = if (isHighlighted) {
            repeatable(
                iterations = 3,
                animation = tween(durationMillis = 250, easing = LinearEasing),
                repeatMode = RepeatMode.Reverse
            )
        } else {
            tween(durationMillis = 500)
        },
        label = "borderHighlight"
    )
    val cardBgColor by animateColorAsState(
        targetValue = if (isHighlighted) {
            MaterialTheme.colorScheme.primary.copy(alpha = 0.1f)
        } else {
            MaterialTheme.colorScheme.surface.copy(alpha = 0.4f)
        },
        animationSpec = tween(durationMillis = 500),
        label = "bgHighlight"
    )

    val timeText = if (displaySessionTime) {
        val offsetMs = event.timestamp - sessionStartTimestamp
        val totalSecs = offsetMs / 1000
        val mins = totalSecs / 60
        val secs = totalSecs % 60
        "${mins}m ${secs}s"
    } else {
        SimpleDateFormat("h:mm:ss a", Locale.getDefault()).format(Date(event.timestamp)).lowercase()
    }

    var expanded by remember { mutableStateOf(false) }

    Card(
        colors = CardDefaults.cardColors(containerColor = cardBgColor),
        modifier = Modifier.fillMaxWidth().clickable { expanded = !expanded },
        shape = RoundedCornerShape(12.dp),
        border = androidx.compose.foundation.BorderStroke(1.dp, accentColor.copy(alpha = borderAlpha))
    ) {
        Row(
            modifier = Modifier.fillMaxWidth().height(IntrinsicSize.Max),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Box(
                modifier = Modifier
                    .width(5.dp)
                    .fillMaxHeight()
                    .background(accentColor)
            )

            Column(
                modifier = Modifier
                    .weight(1f)
                    .padding(horizontal = 12.dp, vertical = 8.dp)
            ) {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    val headerText = buildString {
                        if (shotNumber != null) {
                            append("#$shotNumber ")
                        }
                        append(event.shotType?.uppercase() ?: event.description.uppercase())
                    }
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Text(
                            text = headerText,
                            fontWeight = FontWeight.Black,
                            fontSize = 12.sp,
                            color = Color.White,
                            letterSpacing = 0.5.sp
                        )
                        if (event.bottom_hand_sync_score != null) {
                            Spacer(modifier = Modifier.width(6.dp))
                            Text(
                                text = "🧤",
                                fontSize = 12.sp,
                                modifier = Modifier.clickable { expanded = !expanded }
                            )
                        }
                        if (!event.videoFilePath.isNullOrEmpty()) {
                            Spacer(modifier = Modifier.width(8.dp))
                            Text(
                                text = "📹",
                                fontSize = 12.sp,
                                modifier = Modifier.clickable { onPlayVideo(event.videoFilePath) }
                            )
                        }
                    }
                    Text(
                        text = timeText,
                        fontSize = 10.sp,
                        color = MaterialTheme.colorScheme.secondary.copy(alpha = 0.8f),
                        fontWeight = FontWeight.Bold,
                        modifier = Modifier.clickable { onTimeToggle() }
                    )
                }

                if (event.shotType != null) {
                    Text(
                        text = event.description,
                        fontSize = 11.sp,
                        color = Color.White.copy(alpha = 0.6f),
                        modifier = Modifier.padding(bottom = 6.dp)
                    )
                }

                if (event.batSpeed != null) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(16.dp)
                    ) {
                        MetricSmallCompact("SPEED", "${event.batSpeed.toInt()} km/h", modifier = Modifier.weight(0.8f))
                        if (event.efficiency != null) {
                            MetricSmallCompact("EFF", "${event.efficiency.toInt()}%", modifier = Modifier.weight(0.5f))
                        }
                        if (event.impactTimeMs != null) {
                            MetricSmallCompact("REACT", "${event.impactTimeMs} ms", modifier = Modifier.weight(0.8f))
                        }
                        if (event.bladeAngle != null || !event.bladeClass.isNullOrEmpty()) {
                            val cls = event.bladeClass ?: ""
                            val desc = when {
                                cls.uppercase() == "CLOSED" || "CLOSE" in cls.uppercase() -> "Closed"
                                cls.uppercase() == "OPEN" || "OPEN" in cls.uppercase() -> "Open"
                                cls.uppercase() == "SQUARE" || "SQUARE" in cls.uppercase() || "FULL_FACE" in cls.uppercase() || "FULL" in cls.uppercase() -> "Full face"
                                else -> cls
                            }
                            val displayValue = if (event.bladeAngle != null) {
                                val angleText = String.format(java.util.Locale.US, "%.0f", event.bladeAngle)
                                "$desc ($angleText°)"
                            } else {
                                desc
                            }
                            MetricSmallCompact("BLADE", displayValue, modifier = Modifier.weight(1.8f))
                        }
                        if (event.launchAngle != null || !event.launchClass.isNullOrEmpty()) {
                            val cls = event.launchClass ?: ""
                            val desc = when {
                                cls.uppercase() == "INTO_GROUND" || "GROUND" in cls.uppercase() -> "Grounded"
                                cls.uppercase() == "FLAT" || "FLAT" in cls.uppercase() -> "Flat"
                                cls.uppercase() == "LOFTED" || "LOFT" in cls.uppercase() -> "Lofted"
                                cls.uppercase() == "POWER_ZONE" || "POWER" in cls.uppercase() -> "Power Zone"
                                cls.uppercase() == "HIGH_LOFT" || "HIGH" in cls.uppercase() -> "High Loft"
                                else -> cls
                            }
                            val displayValue = if (event.launchAngle != null) {
                                val angleText = String.format(java.util.Locale.US, "%.0f", Math.abs(event.launchAngle.toDouble()))
                                "$desc ($angleText°)"
                            } else {
                                desc
                            }
                            MetricSmallCompact("LAUNCH", displayValue, modifier = Modifier.weight(2.1f))
                        }
                    }
                }

                if (expanded && event.bottom_hand_sync_score != null) {
                    Spacer(modifier = Modifier.height(10.dp))
                    Box(modifier = Modifier.fillMaxWidth().height(1.dp).background(Color.White.copy(alpha = 0.05f)))
                    Spacer(modifier = Modifier.height(8.dp))
                    Text(
                        "🧤 BOTTOM HAND BIO-METRICS",
                        fontSize = 8.sp,
                        fontWeight = FontWeight.Black,
                        color = MaterialTheme.colorScheme.primary,
                        letterSpacing = 1.sp
                    )
                    Spacer(modifier = Modifier.height(8.dp))
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(12.dp)
                    ) {
                        val score = event.bottom_hand_sync_score
                        Column(modifier = Modifier.weight(1f)) {
                            Text("SYNC SCORE", fontSize = 7.sp, color = Color.Gray, fontWeight = FontWeight.Bold)
                            Text("${score.toInt()}/100", fontSize = 14.sp, fontWeight = FontWeight.Black, color = MaterialTheme.colorScheme.primary)
                            Spacer(modifier = Modifier.height(2.dp))
                            LinearProgressIndicator(
                                progress = { score / 100f },
                                modifier = Modifier.fillMaxWidth().height(4.dp).clip(RoundedCornerShape(2.dp)),
                                color = MaterialTheme.colorScheme.primary,
                                trackColor = Color.White.copy(alpha = 0.05f)
                            )
                        }

                        val lead = event.bottom_hand_time_lead_ms ?: 0L
                        val leadText = if (lead > 0) "+${lead}ms" else "${lead}ms"
                        val leadColor = when {
                            kotlin.math.abs(lead) < 60 -> MaterialTheme.colorScheme.primary
                            kotlin.math.abs(lead) < 200 -> Color(0xFFFFD54F)
                            else -> Color(0xFFFF5252)
                        }
                        Column(modifier = Modifier.weight(1f)) {
                            Text("HAND TIMING", fontSize = 7.sp, color = Color.Gray, fontWeight = FontWeight.Bold)
                            Text(leadText, fontSize = 14.sp, fontWeight = FontWeight.Black, color = leadColor)
                            Text(if (lead > 0) "Bottom Hand Leads" else "Top Hand Leads", fontSize = 8.sp, color = Color.Gray)
                        }

                        val gyroRatio = (event.bottom_hand_gyro_ratio ?: 0f) * 100
                        Column(modifier = Modifier.weight(1f)) {
                            Text("GYRO RATIO", fontSize = 7.sp, color = Color.Gray, fontWeight = FontWeight.Bold)
                            Text("${gyroRatio.toInt()}%", fontSize = 14.sp, fontWeight = FontWeight.Black, color = Color.White)
                            Text("of top hand peak", fontSize = 8.sp, color = Color.Gray)
                        }

                        val forceRatio = (event.bottom_hand_acc_ratio ?: 0f) * 100
                        Column(modifier = Modifier.weight(1f)) {
                            Text("FORCE RATIO", fontSize = 7.sp, color = Color.Gray, fontWeight = FontWeight.Bold)
                            Text("${forceRatio.toInt()}%", fontSize = 14.sp, fontWeight = FontWeight.Black, color = Color.White)
                            Text("of top hand peak", fontSize = 8.sp, color = Color.Gray)
                        }
                    }

                    Spacer(modifier = Modifier.height(10.dp))
                    val gyroRatioVal = event.bottom_hand_gyro_ratio ?: 0f
                    val dominanceText = when {
                        gyroRatioVal > 1.15f -> "Bottom Hand Dominant (Power Whip)"
                        gyroRatioVal < 0.85f -> "Top Hand Dominant (Control/Straight)"
                        else -> "Balanced Dual-Hand Contribution"
                    }
                    val wristText = when {
                        gyroRatioVal > 1.25f -> "Whippy / Active Bottom Hand Release"
                        gyroRatioVal < 0.75f -> "Locked / Rigid Wrist Interface"
                        else -> "Controlled Wrist Release"
                    }
                    val lead = event.bottom_hand_time_lead_ms ?: 0L
                    val timingDetail = if (lead > 0) {
                        "Bottom hand leads by ${lead}ms (Early Release)"
                    } else if (lead < 0) {
                        "Top hand leads by ${kotlin.math.abs(lead)}ms (Late Push)"
                    } else {
                        "Synchronous hand release (Perfect Timing)"
                    }

                    Column(
                        modifier = Modifier
                            .fillMaxWidth()
                            .background(Color.White.copy(alpha = 0.03f), RoundedCornerShape(12.dp))
                            .padding(10.dp),
                        verticalArrangement = Arrangement.spacedBy(4.dp)
                    ) {
                        Text("• Contribution: $dominanceText", fontSize = 9.sp, color = Color.White, fontWeight = FontWeight.Medium)
                        Text("• Wrist Action: $wristText", fontSize = 9.sp, color = Color.Gray)
                        Text("• Hand Release: $timingDetail", fontSize = 9.sp, color = Color.Gray)
                    }
                }
            }
        }
    }
}

@Composable
fun MetricSmallCompact(label: String, value: String, modifier: Modifier = Modifier) {
    Column(modifier = modifier) {
        Text(
            text = label,
            fontSize = 7.sp,
            fontWeight = FontWeight.Bold,
            color = Color.Gray,
            maxLines = 1,
            style = LocalTextStyle.current.copy(
                platformStyle = androidx.compose.ui.text.PlatformTextStyle(
                    includeFontPadding = false
                )
            )
        )
        Text(
            text = value,
            fontSize = 11.sp,
            fontWeight = FontWeight.Bold,
            color = Color(0xFFBCD2FE),
            maxLines = 1,
            modifier = Modifier.offset(y = (-4).dp),
            style = LocalTextStyle.current.copy(
                platformStyle = androidx.compose.ui.text.PlatformTextStyle(
                    includeFontPadding = false
                )
            )
        )
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ProfileDialog(
    currentName: String,
    currentWeight: Float,
    currentAge: Int,
    currentGender: String,
    onDismiss: () -> Unit,
    onSave: (name: String, weight: Float, age: Int, gender: String) -> Unit
) {
    var name by remember { mutableStateOf(currentName) }
    var weightText by remember { mutableStateOf(currentWeight.toString()) }
    var ageText by remember { mutableStateOf(currentAge.toString()) }
    var gender by remember { mutableStateOf(currentGender) }

    Dialog(onDismissRequest = onDismiss) {
        Card(
            colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
            shape = RoundedCornerShape(24.dp),
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp),
            border = androidx.compose.foundation.BorderStroke(1.dp, Color.White.copy(alpha = 0.1f))
        ) {
            Column(
                modifier = Modifier
                    .padding(24.dp)
                    .fillMaxWidth(),
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.spacedBy(16.dp)
            ) {
                Text(
                    text = "ATHLETE BIO & PROFILE",
                    fontSize = 18.sp,
                    fontWeight = FontWeight.Black,
                    color = MaterialTheme.colorScheme.primary,
                    letterSpacing = 1.sp
                )
                
                Text(
                    text = "Used for physiologically accurate dynamic Keytel energy expenditure tracking in Samsung Health.",
                    fontSize = 11.sp,
                    color = Color.Gray,
                    lineHeight = 16.sp
                )

                OutlinedTextField(
                    value = name,
                    onValueChange = { name = it },
                    label = { Text("Name") },
                    colors = OutlinedTextFieldDefaults.colors(
                        focusedBorderColor = MaterialTheme.colorScheme.primary,
                        focusedLabelColor = MaterialTheme.colorScheme.primary
                    ),
                    modifier = Modifier.fillMaxWidth(),
                    singleLine = true
                )

                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(12.dp)
                ) {
                    OutlinedTextField(
                        value = ageText,
                        onValueChange = { ageText = it },
                        label = { Text("Age (yrs)") },
                        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                        colors = OutlinedTextFieldDefaults.colors(
                            focusedBorderColor = MaterialTheme.colorScheme.primary,
                            focusedLabelColor = MaterialTheme.colorScheme.primary
                        ),
                        modifier = Modifier.weight(1f),
                        singleLine = true
                    )

                    OutlinedTextField(
                        value = weightText,
                        onValueChange = { weightText = it },
                        label = { Text("Weight (kg)") },
                        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal),
                        colors = OutlinedTextFieldDefaults.colors(
                            focusedBorderColor = MaterialTheme.colorScheme.primary,
                            focusedLabelColor = MaterialTheme.colorScheme.primary
                        ),
                        modifier = Modifier.weight(1f),
                        singleLine = true
                    )
                }

                Column(modifier = Modifier.fillMaxWidth()) {
                    Text(
                        text = "GENDER",
                        fontSize = 12.sp,
                        fontWeight = FontWeight.Bold,
                        color = Color.Gray,
                        modifier = Modifier.padding(bottom = 6.dp)
                    )
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(12.dp)
                    ) {
                        listOf("Male", "Female").forEach { option ->
                            val isSelected = gender.equals(option, ignoreCase = true)
                            Button(
                                onClick = { gender = option },
                                colors = ButtonDefaults.buttonColors(
                                    containerColor = if (isSelected) MaterialTheme.colorScheme.primary else Color.White.copy(alpha = 0.05f),
                                    contentColor = if (isSelected) MaterialTheme.colorScheme.onPrimary else Color.White
                                ),
                                modifier = Modifier.weight(1f),
                                shape = RoundedCornerShape(12.dp)
                            ) {
                                Text(option, fontWeight = FontWeight.Bold)
                            }
                        }
                    }
                }

                Spacer(modifier = Modifier.height(8.dp))

                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(12.dp)
                ) {
                    OutlinedButton(
                        onClick = onDismiss,
                        modifier = Modifier.weight(1f),
                        shape = RoundedCornerShape(12.dp),
                        colors = ButtonDefaults.outlinedButtonColors(contentColor = Color.White)
                    ) {
                        Text("CANCEL")
                    }

                    Button(
                        onClick = {
                            val parsedWeight = weightText.toFloatOrNull() ?: currentWeight
                            val parsedAge = ageText.toIntOrNull() ?: currentAge
                            if (name.isNotBlank()) {
                                onSave(name, parsedWeight, parsedAge, gender)
                            }
                        },
                        colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.primary),
                        modifier = Modifier.weight(1f),
                        shape = RoundedCornerShape(12.dp)
                    ) {
                        Text("SAVE", fontWeight = FontWeight.Bold)
                    }
                }
            }
        }
    }
}

@Composable
fun UnifiedConsoleCard(
    sessionActive: Boolean,
    audioEnabled: Boolean,
    onAudioToggle: (Boolean) -> Unit,
    polarEnabled: Boolean,
    onPolarToggle: (Boolean) -> Unit,
    videoEnabled: Boolean,
    onVideoToggle: (Boolean) -> Unit,
    polarState: com.mrpeel.cricketbattingtracker.services.PolarConnectionState,
    polarSampleCount: Long,
    polarTaps: Int,
    pairedDevice: String?,
    onPairingClick: () -> Unit,
    onVideoConfigClick: () -> Unit,
    elapsedSeconds: Long,
    maxAmplitude: Float,
    recordingsList: List<java.io.File>,
    onRequestPermission: () -> Unit,
    onRequestVideoPermission: () -> Unit,
    context: Context
) {
    Card(
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        modifier = Modifier
            .fillMaxWidth()
            .padding(16.dp),
        shape = RoundedCornerShape(24.dp),
        border = BorderStroke(1.dp, Color.White.copy(alpha = 0.05f))
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(20.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            // Header
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Column {
                    Text(
                        "🏏 PITCH ANALYTIX CONSOLE",
                        fontSize = 10.sp,
                        fontWeight = FontWeight.Black,
                        color = MaterialTheme.colorScheme.secondary,
                        letterSpacing = 1.5.sp
                    )
                    Text(
                        if (sessionActive) "TRACKING IN PROGRESS" else "SESSION SETUP",
                        fontSize = 14.sp,
                        fontWeight = FontWeight.Black,
                        color = Color.White
                    )
                }

                if (sessionActive) {
                    val infiniteTransition = rememberInfiniteTransition(label = "pulse")
                    val alpha by infiniteTransition.animateFloat(
                        initialValue = 0.3f,
                        targetValue = 1f,
                        animationSpec = infiniteRepeatable(
                            animation = tween(800, easing = LinearEasing),
                            repeatMode = RepeatMode.Reverse
                        ),
                        label = "alpha"
                    )
                    Box(
                        modifier = Modifier
                            .size(10.dp)
                            .clip(CircleShape)
                            .background(Color(0xFF58FF63).copy(alpha = alpha))
                    )
                }
            }

            if (!sessionActive) {
                // Determine if Bluetooth headphones are connected
                val audioManager = context.getSystemService(Context.AUDIO_SERVICE) as android.media.AudioManager
                val devices = audioManager.getDevices(android.media.AudioManager.GET_DEVICES_OUTPUTS)
                val isBluetoothHeadphonesConnected = devices.any { device ->
                    val type = device.type
                    type == android.media.AudioDeviceInfo.TYPE_BLUETOOTH_A2DP ||
                    type == android.media.AudioDeviceInfo.TYPE_BLUETOOTH_SCO ||
                    type == android.media.AudioDeviceInfo.TYPE_BLE_HEADSET
                }

                // If not connected, force audio narration option off
                val isAudioAvailable = isBluetoothHeadphonesConnected
                val finalAudioEnabled = audioEnabled && isAudioAvailable

                // Toggles for configuring session options
                Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    // Audio toggle
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.SpaceBetween
                    ) {
                        Row(
                            verticalAlignment = Alignment.CenterVertically, 
                            modifier = Modifier.weight(1f)
                        ) {
                            Text(
                                "🎙️", 
                                fontSize = 18.sp, 
                                modifier = Modifier.padding(end = 12.dp),
                                color = if (isAudioAvailable) Color.Unspecified else Color.Gray.copy(alpha = 0.5f)
                            )
                            Column {
                                Text(
                                    "Audio Narration", 
                                    fontSize = 12.sp, 
                                    fontWeight = FontWeight.Bold, 
                                    color = if (isAudioAvailable) Color.White else Color.Gray.copy(alpha = 0.5f)
                                )
                                Text(
                                    if (isAudioAvailable) "Record voice shot observations" else "Requires Bluetooth Headphones", 
                                    fontSize = 10.sp, 
                                    color = if (isAudioAvailable) Color.Gray else Color.Gray.copy(alpha = 0.5f)
                                )
                            }
                        }
                        Switch(
                            checked = finalAudioEnabled,
                            onCheckedChange = { onAudioToggle(it) },
                            enabled = isAudioAvailable,
                            colors = SwitchDefaults.colors(
                                checkedThumbColor = MaterialTheme.colorScheme.primary,
                                disabledCheckedThumbColor = MaterialTheme.colorScheme.primary.copy(alpha = 0.3f),
                                disabledUncheckedThumbColor = Color.Gray.copy(alpha = 0.3f)
                            )
                        )
                    }

                    HorizontalDivider(color = Color.White.copy(alpha = 0.05f))

                    // Polar Sense toggle
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.SpaceBetween
                    ) {
                        Row(verticalAlignment = Alignment.CenterVertically, modifier = Modifier.weight(1f)) {
                            Text("🧤", fontSize = 18.sp, modifier = Modifier.padding(end = 12.dp))
                            Column {
                                Row(verticalAlignment = Alignment.CenterVertically) {
                                    Text("Bottom Hand Sensor", fontSize = 12.sp, fontWeight = FontWeight.Bold, color = Color.White)
                                    Spacer(modifier = Modifier.width(6.dp))
                                    Text(
                                        text = pairedDevice?.let { "PAIRED" } ?: "NOT CONFIG",
                                        fontSize = 8.sp,
                                        fontWeight = FontWeight.Black,
                                        color = if (pairedDevice != null) MaterialTheme.colorScheme.primary else Color(0xFFFF5252),
                                        modifier = Modifier
                                            .background(
                                                if (pairedDevice != null) MaterialTheme.colorScheme.primary.copy(alpha = 0.15f)
                                                else Color(0xFFFF5252).copy(alpha = 0.15f),
                                                shape = RoundedCornerShape(4.dp)
                                            )
                                            .padding(horizontal = 6.dp, vertical = 2.dp)
                                    )
                                }
                                Text(
                                    text = pairedDevice?.let { "Polar Sense ID: $it" } ?: "Pair your sensor first",
                                    fontSize = 10.sp,
                                    color = Color.Gray
                                )
                            }
                        }
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            IconButton(onClick = onPairingClick) {
                                Text("⚙️", fontSize = 16.sp)
                            }
                            Switch(
                                checked = polarEnabled && pairedDevice != null,
                                onCheckedChange = onPolarToggle,
                                enabled = pairedDevice != null,
                                colors = SwitchDefaults.colors(checkedThumbColor = MaterialTheme.colorScheme.primary)
                            )
                        }
                    }

                    HorizontalDivider(color = Color.White.copy(alpha = 0.05f))

                    // Video toggle
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.SpaceBetween
                    ) {
                        Row(verticalAlignment = Alignment.CenterVertically, modifier = Modifier.weight(1f)) {
                            Text("🎥", fontSize = 18.sp, modifier = Modifier.padding(end = 12.dp))
                            Column {
                                Text("Record Session Video", fontSize = 12.sp, fontWeight = FontWeight.Bold, color = Color.White)
                                Text("Record clips linked to watch swings", fontSize = 10.sp, color = Color.Gray)
                            }
                        }
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            IconButton(onClick = onVideoConfigClick) {
                                Text("⚙️", fontSize = 16.sp)
                            }
                            Switch(
                                checked = videoEnabled,
                                onCheckedChange = onVideoToggle,
                                colors = SwitchDefaults.colors(checkedThumbColor = MaterialTheme.colorScheme.primary)
                            )
                        }
                    }
                }

                Spacer(modifier = Modifier.height(8.dp))

                // Start button orchestration
                Button(
                    onClick = {
                        // Start watch session
                        if (videoEnabled) {
                            val hasCamera = androidx.core.content.ContextCompat.checkSelfPermission(
                                context, android.Manifest.permission.CAMERA
                            ) == android.content.pm.PackageManager.PERMISSION_GRANTED
                            val hasAudio = androidx.core.content.ContextCompat.checkSelfPermission(
                                context, android.Manifest.permission.RECORD_AUDIO
                            ) == android.content.pm.PackageManager.PERMISSION_GRANTED
                            if (hasCamera && hasAudio) {
                                com.mrpeel.cricketbattingtracker.services.VideoRecordManager.startRecording(context)
                            } else {
                                onRequestVideoPermission()
                            }
                        } else if (audioEnabled) {
                            val hasAudio = androidx.core.content.ContextCompat.checkSelfPermission(
                                context, android.Manifest.permission.RECORD_AUDIO
                            ) == android.content.pm.PackageManager.PERMISSION_GRANTED
                            val hasBt = if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.S) {
                                androidx.core.content.ContextCompat.checkSelfPermission(
                                    context, android.Manifest.permission.BLUETOOTH_CONNECT
                                ) == android.content.pm.PackageManager.PERMISSION_GRANTED
                            } else {
                                true
                            }
                            if (hasAudio && hasBt) {
                                com.mrpeel.cricketbattingtracker.services.AudioRecordManager.startRecording(context, true)
                            } else {
                                onRequestPermission()
                            }
                        } else {
                            // If only watch/polar tracking (no video, no audio)
                            // AudioRecordManager.startRecording() handles sending the watch start tracking message
                            com.mrpeel.cricketbattingtracker.services.AudioRecordManager.startRecording(context, false)
                        }

                        // Start Polar Sense streaming if enabled
                        if (polarEnabled && pairedDevice != null) {
                            val serviceIntent = Intent(context, com.mrpeel.cricketbattingtracker.services.PolarSenseService::class.java).apply {
                                action = com.mrpeel.cricketbattingtracker.services.PolarSenseService.ACTION_START
                            }
                            context.startService(serviceIntent)
                        }
                    },
                    colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.primary),
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(48.dp),
                    shape = RoundedCornerShape(14.dp)
                ) {
                    Row(
                        horizontalArrangement = Arrangement.spacedBy(8.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text("▶️", fontSize = 14.sp)
                        Text(
                            "START BATTING SESSION",
                            fontWeight = FontWeight.Black,
                            fontSize = 11.sp,
                            color = Color(0xFF000C1B),
                            letterSpacing = 0.5.sp
                        )
                    }
                }

                if (recordingsList.isNotEmpty() && audioEnabled) {
                    Box(modifier = Modifier.fillMaxWidth().height(1.dp).background(Color.White.copy(alpha = 0.05f)))
                    Text(
                        "RECENT NARRATIONS (${recordingsList.size})",
                        fontSize = 9.sp,
                        fontWeight = FontWeight.Bold,
                        color = Color.Gray,
                        letterSpacing = 1.sp
                    )
                    LazyRow(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(8.dp),
                        contentPadding = PaddingValues(bottom = 4.dp)
                    ) {
                        items(recordingsList.take(5)) { file ->
                            RecordingHistoryItem(file, context)
                        }
                    }
                }
            } else {
                // Active session telemetry display
                Column(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalAlignment = Alignment.CenterHorizontally,
                    verticalArrangement = Arrangement.spacedBy(16.dp)
                ) {
                    val minutes = elapsedSeconds / 60
                    val seconds = elapsedSeconds % 60
                    val timerStr = String.format(Locale.US, "%02d:%02d", minutes, seconds)
                    
                    Text(
                        text = timerStr,
                        fontSize = 44.sp,
                        fontWeight = FontWeight.Black,
                        color = MaterialTheme.colorScheme.primary,
                        letterSpacing = 1.sp
                    )

                    // Audio visualizer (only when audio enabled)
                    if (audioEnabled) {
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .height(32.dp)
                                .padding(horizontal = 32.dp),
                            horizontalArrangement = Arrangement.SpaceEvenly,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            val random = remember { java.util.Random(1234) }
                            for (i in 0 until 7) {
                                val factor = 0.4f + 0.6f * random.nextFloat()
                                val heightRatio = (maxAmplitude * factor).coerceIn(0.05f, 1f)
                                Box(
                                    modifier = Modifier
                                        .width(4.dp)
                                        .fillMaxHeight(heightRatio)
                                        .clip(CircleShape)
                                        .background(
                                            if (i == 3) MaterialTheme.colorScheme.primary 
                                            else MaterialTheme.colorScheme.primary.copy(alpha = 0.5f + 0.5f * heightRatio)
                                        )
                                )
                            }
                        }
                    }

                    // Polar Sense status (only if streaming)
                    if (polarEnabled && polarState == com.mrpeel.cricketbattingtracker.services.PolarConnectionState.STREAMING) {
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .background(Color.White.copy(alpha = 0.03f), shape = RoundedCornerShape(12.dp))
                                .padding(horizontal = 16.dp, vertical = 10.dp),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Row(verticalAlignment = Alignment.CenterVertically) {
                                Text("🧤", fontSize = 16.sp, modifier = Modifier.padding(end = 8.dp))
                                Text("Polar Verity Sense", fontSize = 11.sp, fontWeight = FontWeight.Bold, color = Color.White)
                            }
                            Column(horizontalAlignment = Alignment.End) {
                                Text("Live Stream (52Hz)", fontSize = 9.sp, color = MaterialTheme.colorScheme.primary, fontWeight = FontWeight.Bold)
                                Text("Samples: $polarSampleCount  •  Taps: $polarTaps", fontSize = 10.sp, color = Color.Gray)
                            }
                        }
                    }

                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(12.dp)
                    ) {
                        OutlinedButton(
                            onClick = {
                                // Discard all services
                                com.mrpeel.cricketbattingtracker.services.AudioRecordManager.discardRecording(context)
                                if (polarState == com.mrpeel.cricketbattingtracker.services.PolarConnectionState.STREAMING) {
                                    val serviceIntent = Intent(context, com.mrpeel.cricketbattingtracker.services.PolarSenseService::class.java).apply {
                                        action = com.mrpeel.cricketbattingtracker.services.PolarSenseService.ACTION_STOP
                                    }
                                    context.startService(serviceIntent)
                                    // Discard polar files
                                    val serviceClass = com.mrpeel.cricketbattingtracker.services.PolarSenseService()
                                    serviceClass.discardSessionData()
                                }
                                if (videoEnabled) {
                                    com.mrpeel.cricketbattingtracker.services.VideoRecordManager.discard(context)
                                }
                            },
                            modifier = Modifier
                                .weight(1f)
                                .height(44.dp),
                            shape = RoundedCornerShape(12.dp),
                            colors = ButtonDefaults.outlinedButtonColors(contentColor = Color.White),
                            border = BorderStroke(1.dp, Color.White.copy(alpha = 0.15f))
                        ) {
                            Text("DISCARD", fontWeight = FontWeight.Bold, fontSize = 11.sp, letterSpacing = 0.5.sp)
                        }

                        Button(
                            onClick = {
                                // Stop and save all active services
                                com.mrpeel.cricketbattingtracker.services.AudioRecordManager.stopRecording(context)
                                if (polarState == com.mrpeel.cricketbattingtracker.services.PolarConnectionState.STREAMING) {
                                    val serviceIntent = Intent(context, com.mrpeel.cricketbattingtracker.services.PolarSenseService::class.java).apply {
                                        action = com.mrpeel.cricketbattingtracker.services.PolarSenseService.ACTION_STOP
                                    }
                                    context.startService(serviceIntent)
                                }
                                if (videoEnabled) {
                                    com.mrpeel.cricketbattingtracker.services.VideoRecordManager.stopAndSave(context)
                                }
                            },
                            colors = ButtonDefaults.buttonColors(containerColor = Color(0xFFFF5252)),
                            modifier = Modifier
                                .weight(1.5f)
                                .height(44.dp),
                            shape = RoundedCornerShape(12.dp)
                        ) {
                            Row(
                                horizontalArrangement = Arrangement.spacedBy(6.dp),
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                Box(
                                    modifier = Modifier
                                        .size(10.dp)
                                        .clip(RoundedCornerShape(2.dp))
                                        .background(Color.White)
                                )
                                Text("STOP & SAVE", fontWeight = FontWeight.Black, fontSize = 11.sp, color = Color.White, letterSpacing = 0.5.sp)
                            }
                        }
                    }
                }
            }
        }
    }
}

@Composable
fun PolarPairingScreen(
    context: Context,
    onBack: () -> Unit
) {
    LaunchedEffect(Unit) {
        com.mrpeel.cricketbattingtracker.services.PolarSenseManager.initialize(context)
    }

    val pairedDevice by com.mrpeel.cricketbattingtracker.services.PolarSenseManager.pairedDeviceId.collectAsState()
    val scanDevices by com.mrpeel.cricketbattingtracker.services.PolarSenseManager.discoveredDevices.collectAsState()
    val connectionState by com.mrpeel.cricketbattingtracker.services.PolarSenseManager.connectionState.collectAsState()

    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        // Back Bar
        Row(
            modifier = Modifier.fillMaxWidth(),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Box(
                modifier = Modifier
                    .size(36.dp)
                    .clip(RoundedCornerShape(8.dp))
                    .background(MaterialTheme.colorScheme.primary.copy(alpha = 0.15f))
                    .clickable {
                        com.mrpeel.cricketbattingtracker.services.PolarSenseManager.stopScan()
                        onBack()
                    },
                contentAlignment = Alignment.Center
            ) {
                Text("←", color = MaterialTheme.colorScheme.primary, fontWeight = FontWeight.Black, fontSize = 18.sp)
            }
            Spacer(modifier = Modifier.width(12.dp))
            Column {
                Text("POLAR SENSE PAIRING", fontSize = 14.sp, fontWeight = FontWeight.Black, color = Color.White)
                Text("Configure bottom hand arm sensor", fontSize = 10.sp, color = Color.Gray)
            }
        }

        // Active Pairing Status Card
        Card(
            colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
            shape = RoundedCornerShape(16.dp),
            border = BorderStroke(1.dp, Color.White.copy(alpha = 0.05f)),
            modifier = Modifier.fillMaxWidth()
        ) {
            Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
                Text("CURRENT SENSOR STATUS", fontSize = 10.sp, fontWeight = FontWeight.Black, color = MaterialTheme.colorScheme.secondary, letterSpacing = 1.sp)
                
                if (pairedDevice != null) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Column {
                            Text("Paired ID: $pairedDevice", fontSize = 13.sp, fontWeight = FontWeight.Bold, color = Color.White)
                            Text("State: $connectionState", fontSize = 10.sp, color = Color.Gray)
                        }
                        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                            Button(
                                onClick = {
                                    if (connectionState == com.mrpeel.cricketbattingtracker.services.PolarConnectionState.DISCONNECTED) {
                                        com.mrpeel.cricketbattingtracker.services.PolarSenseManager.connect(context)
                                    } else {
                                        com.mrpeel.cricketbattingtracker.services.PolarSenseManager.disconnect()
                                    }
                                },
                                shape = RoundedCornerShape(8.dp),
                                contentPadding = PaddingValues(horizontal = 12.dp, vertical = 6.dp),
                                modifier = Modifier.height(32.dp),
                                colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.primary.copy(alpha = 0.2f), contentColor = MaterialTheme.colorScheme.primary)
                            ) {
                                Text(
                                    text = if (connectionState == com.mrpeel.cricketbattingtracker.services.PolarConnectionState.DISCONNECTED) "Connect" else "Disconnect",
                                    fontSize = 10.sp,
                                    fontWeight = FontWeight.Bold
                                )
                            }
                            Button(
                                onClick = { com.mrpeel.cricketbattingtracker.services.PolarSenseManager.forgetDevice(context) },
                                shape = RoundedCornerShape(8.dp),
                                contentPadding = PaddingValues(horizontal = 12.dp, vertical = 6.dp),
                                modifier = Modifier.height(32.dp),
                                colors = ButtonDefaults.buttonColors(containerColor = Color(0xFFFF5252).copy(alpha = 0.2f), contentColor = Color(0xFFFF5252))
                            ) {
                                Text("Forget", fontSize = 10.sp, fontWeight = FontWeight.Bold)
                            }
                        }
                    }
                } else {
                    Text("No sensor paired. Place Polar Sense in pairing mode and scan below.", fontSize = 12.sp, color = Color.Gray)
                }
            }
        }

        // Discovery / Scanner List
        Card(
            colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
            shape = RoundedCornerShape(16.dp),
            border = BorderStroke(1.dp, Color.White.copy(alpha = 0.05f)),
            modifier = Modifier.fillMaxWidth().weight(1f)
        ) {
            Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text("DISCOVERED SENSORS", fontSize = 10.sp, fontWeight = FontWeight.Black, color = MaterialTheme.colorScheme.secondary, letterSpacing = 1.sp)
                    Button(
                        onClick = {
                            if (connectionState == com.mrpeel.cricketbattingtracker.services.PolarConnectionState.SCANNING) {
                                com.mrpeel.cricketbattingtracker.services.PolarSenseManager.stopScan()
                            } else {
                                com.mrpeel.cricketbattingtracker.services.PolarSenseManager.startScan()
                            }
                        },
                        shape = RoundedCornerShape(8.dp),
                        contentPadding = PaddingValues(horizontal = 12.dp, vertical = 6.dp),
                        modifier = Modifier.height(32.dp)
                    ) {
                        Text(
                            text = if (connectionState == com.mrpeel.cricketbattingtracker.services.PolarConnectionState.SCANNING) "Stop Scan" else "Start Scan",
                            fontSize = 10.sp,
                            fontWeight = FontWeight.Bold,
                            color = Color(0xFF000C1B)
                        )
                    }
                }

                if (scanDevices.isEmpty()) {
                    Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                        Text(
                            text = if (connectionState == com.mrpeel.cricketbattingtracker.services.PolarConnectionState.SCANNING) "Searching for sensors..." else "Scan inactive",
                            fontSize = 11.sp,
                            color = Color.Gray
                        )
                    }
                } else {
                    LazyColumn(
                        modifier = Modifier.fillMaxSize(),
                        verticalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        items(scanDevices) { device ->
                            Row(
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .background(Color.White.copy(alpha = 0.03f), shape = RoundedCornerShape(8.dp))
                                    .clickable {
                                        com.mrpeel.cricketbattingtracker.services.PolarSenseManager.stopScan()
                                        com.mrpeel.cricketbattingtracker.services.PolarSenseManager.pairDevice(context, device.deviceId)
                                    }
                                    .padding(horizontal = 12.dp, vertical = 10.dp),
                                horizontalArrangement = Arrangement.SpaceBetween,
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                Column {
                                    Text(device.name, fontSize = 12.sp, fontWeight = FontWeight.Bold, color = Color.White)
                                    Text("ID: ${device.deviceId}", fontSize = 9.sp, color = Color.Gray)
                                }
                                Text("📶 ${device.rssi} dBm", fontSize = 10.sp, color = MaterialTheme.colorScheme.primary, fontWeight = FontWeight.Bold)
                            }
                        }
                    }
                }
            }
        }
    }
}

@Composable
fun VideoSetupScreen(
    context: Context,
    onBack: () -> Unit
) {
    val prefs = remember { context.getSharedPreferences("pitch_analytix_prefs", Context.MODE_PRIVATE) }
    var cameraFacing by remember { mutableStateOf(prefs.getString("video_camera_facing", "back") ?: "back") }
    var zoomValue by remember { mutableFloatStateOf(prefs.getFloat("video_zoom_value", 0.0f)) }
    var targetFps by remember { mutableIntStateOf(prefs.getInt("video_target_fps", 120)) }

    var cameraControlRef = remember { mutableStateOf<androidx.camera.core.CameraControl?>(null) }
    val lifecycleOwner = androidx.compose.ui.platform.LocalLifecycleOwner.current

    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp)
            .verticalScroll(rememberScrollState()),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        // Back Navigation Bar
        Row(
            modifier = Modifier.fillMaxWidth(),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Box(
                modifier = Modifier
                    .size(36.dp)
                    .clip(RoundedCornerShape(8.dp))
                    .background(MaterialTheme.colorScheme.primary.copy(alpha = 0.15f))
                    .clickable { onBack() },
                contentAlignment = Alignment.Center
            ) {
                Text("←", color = MaterialTheme.colorScheme.primary, fontWeight = FontWeight.Black, fontSize = 18.sp)
            }
            Spacer(modifier = Modifier.width(12.dp))
            Column {
                Text("VIDEO CAPTURE CONFIG", fontSize = 14.sp, fontWeight = FontWeight.Black, color = Color.White)
                Text("Configure frame rate, zoom, and direction", fontSize = 10.sp, color = Color.Gray)
            }
        }

        // Live Preview Card Finder
        Card(
            colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
            shape = RoundedCornerShape(16.dp),
            border = BorderStroke(1.dp, Color.White.copy(alpha = 0.05f)),
            modifier = Modifier
                .fillMaxWidth()
                .height(240.dp)
        ) {
            Box(modifier = Modifier.fillMaxSize()) {
                androidx.compose.ui.viewinterop.AndroidView(
                    factory = { ctx ->
                        val previewView = androidx.camera.view.PreviewView(ctx).apply {
                            implementationMode = androidx.camera.view.PreviewView.ImplementationMode.PERFORMANCE
                            scaleType = androidx.camera.view.PreviewView.ScaleType.FIT_CENTER
                        }
                        val cameraProviderFuture = androidx.camera.lifecycle.ProcessCameraProvider.getInstance(ctx)
                        cameraProviderFuture.addListener({
                            try {
                                val cameraProvider = cameraProviderFuture.get()
                                val preview = androidx.camera.core.Preview.Builder().build().also {
                                    it.setSurfaceProvider(previewView.surfaceProvider)
                                }
                                val cameraSelector = if (cameraFacing == "front") {
                                    androidx.camera.core.CameraSelector.DEFAULT_FRONT_CAMERA
                                } else {
                                    androidx.camera.core.CameraSelector.DEFAULT_BACK_CAMERA
                                }

                                cameraProvider.unbindAll()
                                var camera: androidx.camera.core.Camera?
                                try {
                                    camera = cameraProvider.bindToLifecycle(
                                        lifecycleOwner,
                                        cameraSelector,
                                        preview
                                    )
                                } catch (e: Exception) {
                                    android.util.Log.w("VideoSetupScreen", "Preferred camera bind failed: ${e.message}, falling back to back camera")
                                    // Fallback to back camera if selected one fails
                                    camera = cameraProvider.bindToLifecycle(
                                        lifecycleOwner,
                                        androidx.camera.core.CameraSelector.DEFAULT_BACK_CAMERA,
                                        preview
                                    )
                                }
                                if (camera != null) {
                                    cameraControlRef.value = camera.cameraControl
                                    camera.cameraControl.setLinearZoom(zoomValue)
                                }
                            } catch (e: Exception) {
                                android.util.Log.e("VideoSetupScreen", "Setup Preview bind failed: ${e.message}")
                            }
                        }, androidx.core.content.ContextCompat.getMainExecutor(ctx))
                        previewView
                    },
                    update = { _ ->
                        // Re-apply zoom when slider updates
                        cameraControlRef.value?.setLinearZoom(zoomValue)
                    },
                    modifier = Modifier.fillMaxSize()
                )

                // Aspect ratio guide overlay
                Box(
                    modifier = Modifier
                        .fillMaxSize()
                        .background(Color.Transparent)
                        .then(
                            Modifier.border(
                                width = 1.dp,
                                color = MaterialTheme.colorScheme.primary.copy(alpha = 0.25f),
                                shape = RoundedCornerShape(16.dp)
                            )
                        )
                )
            }
        }

        // Camera facing & frame rate control controls
        Card(
            colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
            shape = RoundedCornerShape(16.dp),
            border = BorderStroke(1.dp, Color.White.copy(alpha = 0.05f)),
            modifier = Modifier.fillMaxWidth()
        ) {
            Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(14.dp)) {
                // Camera Direction selection
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Column {
                        Text("CAMERA DIRECTION", fontSize = 10.sp, fontWeight = FontWeight.Black, color = MaterialTheme.colorScheme.secondary, letterSpacing = 1.sp)
                        Text(if (cameraFacing == "back") "Rear Facing (Recommended)" else "Front Facing (Selfie)", fontSize = 12.sp, color = Color.White)
                    }
                    Button(
                        onClick = {
                            val newFacing = if (cameraFacing == "back") "front" else "back"
                            cameraFacing = newFacing
                            prefs.edit().putString("video_camera_facing", newFacing).apply()
                        },
                        shape = RoundedCornerShape(8.dp),
                        colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.primary.copy(alpha = 0.15f), contentColor = MaterialTheme.colorScheme.primary)
                    ) {
                        Text("🔄 FLIP", fontSize = 10.sp, fontWeight = FontWeight.Bold)
                    }
                }

                HorizontalDivider(color = Color.White.copy(alpha = 0.05f))

                // Linear zoom slider
                Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween
                    ) {
                        Text("ZOOM CONTROL", fontSize = 10.sp, fontWeight = FontWeight.Black, color = MaterialTheme.colorScheme.secondary, letterSpacing = 1.sp)
                        Text(String.format(Locale.US, "%.1fx", 1.0f + zoomValue * 4.0f), fontSize = 11.sp, fontWeight = FontWeight.Bold, color = MaterialTheme.colorScheme.primary)
                    }
                    Slider(
                        value = zoomValue,
                        onValueChange = {
                            zoomValue = it
                            prefs.edit().putFloat("video_zoom_value", it).apply()
                        },
                        valueRange = 0f..1f,
                        colors = SliderDefaults.colors(
                            thumbColor = MaterialTheme.colorScheme.primary,
                            activeTrackColor = MaterialTheme.colorScheme.primary,
                            inactiveTrackColor = Color.White.copy(alpha = 0.1f)
                        )
                    )
                }

                HorizontalDivider(color = Color.White.copy(alpha = 0.05f))

                // Target Capture FPS Selector
                Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
                    Text("TARGET CAPTURE FRAME RATE", fontSize = 10.sp, fontWeight = FontWeight.Black, color = MaterialTheme.colorScheme.secondary, letterSpacing = 1.sp)
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        listOf(120, 60, 30).forEach { fps ->
                            val isSelected = targetFps == fps
                            Button(
                                onClick = {
                                    targetFps = fps
                                    prefs.edit().putInt("video_target_fps", fps).apply()
                                },
                                modifier = Modifier.weight(1f),
                                shape = RoundedCornerShape(8.dp),
                                colors = ButtonDefaults.buttonColors(
                                    containerColor = if (isSelected) MaterialTheme.colorScheme.primary else Color.White.copy(alpha = 0.05f),
                                    contentColor = if (isSelected) Color(0xFF000C1B) else Color.White
                                )
                            ) {
                                Text("${fps} FPS", fontSize = 11.sp, fontWeight = FontWeight.Bold)
                            }
                        }
                    }
                }
            }
        }
    }
}


@Composable
fun RecordingHistoryItem(file: java.io.File, context: Context) {
    val playingFile by com.mrpeel.cricketbattingtracker.services.AudioPlayManager.playingFile.collectAsState()
    val isPlaying = playingFile == file
    
    val timeFormatted = remember(file) {
        val sdf = SimpleDateFormat("HH:mm:ss", Locale.getDefault())
        sdf.format(Date(file.lastModified()))
    }
    
    val sizeFormatted = remember(file) {
        val kb = file.length() / 1024
        "$kb KB"
    }

    Card(
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface.copy(alpha = 0.5f)),
        modifier = Modifier
            .width(130.dp)
            .height(72.dp),
        shape = RoundedCornerShape(12.dp),
        border = BorderStroke(
            width = 1.dp,
            color = if (isPlaying) MaterialTheme.colorScheme.primary else Color.White.copy(alpha = 0.05f)
        )
    ) {
        Row(
            modifier = Modifier
                .fillMaxSize()
                .padding(8.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.SpaceBetween
        ) {
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    timeFormatted,
                    fontSize = 11.sp,
                    fontWeight = FontWeight.Bold,
                    color = Color.White
                )
                Text(
                    sizeFormatted,
                    fontSize = 9.sp,
                    color = Color.Gray
                )
            }
            
            Row(horizontalArrangement = Arrangement.spacedBy(4.dp), verticalAlignment = Alignment.CenterVertically) {
                Box(
                    modifier = Modifier
                        .size(24.dp)
                        .clip(CircleShape)
                        .background(
                            if (isPlaying) MaterialTheme.colorScheme.primary.copy(alpha = 0.2f)
                            else Color.White.copy(alpha = 0.05f)
                        )
                        .clickable {
                            if (isPlaying) {
                                com.mrpeel.cricketbattingtracker.services.AudioPlayManager.stopPlaying()
                            } else {
                                com.mrpeel.cricketbattingtracker.services.AudioPlayManager.playFile(context, file)
                            }
                        },
                    contentAlignment = Alignment.Center
                ) {
                    Text(
                        if (isPlaying) "⏹️" else "▶️",
                        fontSize = 10.sp,
                        color = if (isPlaying) MaterialTheme.colorScheme.primary else Color.White
                    )
                }

                Box(
                    modifier = Modifier
                        .size(24.dp)
                        .clip(CircleShape)
                        .background(Color.White.copy(alpha = 0.05f))
                        .clickable {
                            if (isPlaying) {
                                com.mrpeel.cricketbattingtracker.services.AudioPlayManager.stopPlaying()
                            }
                            com.mrpeel.cricketbattingtracker.services.AudioRecordManager.deleteRecording(file, context)
                        },
                    contentAlignment = Alignment.Center
                ) {
                    Text(
                        "🗑️",
                        fontSize = 10.sp
                    )
                }
            }
        }
    }
}

@Composable
fun VideoPlayerDialog(videoPath: String, onDismiss: () -> Unit) {
    Dialog(
        onDismissRequest = onDismiss,
        properties = androidx.compose.ui.window.DialogProperties(usePlatformDefaultWidth = false)
    ) {
        Card(
            colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
            shape = RoundedCornerShape(16.dp),
            border = BorderStroke(1.dp, Color.White.copy(alpha = 0.1f)),
            modifier = Modifier
                .fillMaxWidth(0.95f)
                .fillMaxHeight(0.65f)
                .padding(8.dp)
        ) {
            Column(
                modifier = Modifier.fillMaxSize().padding(12.dp),
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.Center
            ) {
                Row(
                    modifier = Modifier.fillMaxWidth().padding(bottom = 8.dp),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(
                        text = "SHOT PLAYBACK",
                        fontSize = 12.sp,
                        fontWeight = FontWeight.Black,
                        color = MaterialTheme.colorScheme.primary,
                        letterSpacing = 1.sp
                    )
                    IconButton(
                        onClick = onDismiss,
                        modifier = Modifier.size(24.dp)
                    ) {
                        Text("✕", color = Color.White, fontSize = 14.sp, fontWeight = FontWeight.Bold)
                    }
                }
                
                Box(
                    modifier = Modifier
                        .weight(1f)
                        .fillMaxWidth()
                        .clip(RoundedCornerShape(8.dp))
                        .background(Color.Black),
                    contentAlignment = Alignment.Center
                ) {
                    androidx.compose.ui.viewinterop.AndroidView(
                        modifier = Modifier.fillMaxSize(),
                        factory = { ctx ->
                            android.widget.VideoView(ctx).apply {
                                setVideoPath(videoPath)
                                val mc = android.widget.MediaController(ctx)
                                mc.setAnchorView(this)
                                setMediaController(mc)
                                start()
                            }
                        },
                        update = { view ->
                            view.setVideoPath(videoPath)
                            view.start()
                        }
                    )
                }
            }
        }
    }
}

