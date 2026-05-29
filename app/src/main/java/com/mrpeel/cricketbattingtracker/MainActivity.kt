package com.mrpeel.cricketbattingtracker

import android.os.Bundle
import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.viewModels
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
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
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.ui.platform.LocalContext

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
            com.mrpeel.cricketbattingtracker.services.AudioRecordManager.startRecording(this)
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
                    if (bestLocation == null || loc.accuracy < bestLocation!!.accuracy) {
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
        
        requestLocationPermissionLauncher.launch(
            arrayOf(
                android.Manifest.permission.ACCESS_FINE_LOCATION,
                android.Manifest.permission.ACCESS_COARSE_LOCATION
            )
        )
        
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

                        Column(modifier = Modifier.fillMaxSize()) {
                            TopBar(
                                title = "SESSION DETAILS",
                                subtitle = subtitleText,
                                showBack = true,
                                onBack = { viewModel.selectInnings(null) },
                                initials = initials,
                                onProfileClick = { showProfileDialog = true }
                            )
                            DashboardSummary(timeline)
                            Text(
                                "SESSION TIMELINE",
                                modifier = Modifier.padding(horizontal = 16.dp, vertical = 8.dp),
                                fontSize = 12.sp,
                                fontWeight = FontWeight.Black,
                                color = MaterialTheme.colorScheme.secondary.copy(alpha = 0.6f),
                                letterSpacing = 2.sp
                            )
                            TimelineList(timeline)
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
                                            Text(
                                                "📊",
                                                fontSize = if (selectedTab == 0) 22.sp else 18.sp
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
                                                Text(
                                                    if (isRecording) "⏺" else "🎙️",
                                                    fontSize = if (selectedTab == 1) 22.sp else 18.sp
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
                                            Text(
                                                "📋",
                                                fontSize = if (selectedTab == 2) 22.sp else 18.sp
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
fun DashboardSummary(events: List<InningsEvent>) {
    val maxBatSpeed = events.mapNotNull { it.batSpeed }.maxOrNull() ?: 0f
    val avgEfficiency = events.mapNotNull { it.efficiency }.average().let { if (it.isNaN()) 0.0 else it }
    val shotCount = events.count { it.description.contains("Shot") || it.shotType != null }

    val minTime = events.minOfOrNull { it.timestamp } ?: 0L
    val maxTime = events.maxOfOrNull { it.timestamp } ?: 0L
    val durationMs = if (maxTime > minTime) maxTime - minTime else 0L
    val totalSecs = durationMs / 1000
    val mins = totalSecs / 60
    val secs = totalSecs % 60
    
    val durationVal = String.format(java.util.Locale.US, "%d:%02d", mins, secs)
    val durationUnit = "MM:SS"

    Column(
        modifier = Modifier
            .fillMaxWidth()
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            SummaryCard("MAX SPEED", "${maxBatSpeed.toInt()}", "KM/H", Modifier.weight(1f))
            SummaryCard("AVG EFF", "${avgEfficiency.toInt()}", "%", Modifier.weight(1f))
        }
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            SummaryCard("SHOTS", "$shotCount", "COUNT", Modifier.weight(1f))
            SummaryCard("DURATION", durationVal, durationUnit, Modifier.weight(1f))
        }
    }
}

@Composable
fun SummaryCard(title: String, value: String, unit: String, modifier: Modifier = Modifier) {
    Card(
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        modifier = modifier.height(110.dp),
        shape = RoundedCornerShape(16.dp),
        border = androidx.compose.foundation.BorderStroke(1.dp, Color.White.copy(alpha = 0.05f))
    ) {
        Column(
            modifier = Modifier.fillMaxSize().padding(12.dp),
            verticalArrangement = Arrangement.SpaceBetween
        ) {
            Text(title, fontSize = 10.sp, fontWeight = FontWeight.Bold, color = Color.Gray, letterSpacing = 1.sp)
            // Value and unit on separate lines to avoid overflow with 3-digit numbers
            Text(value, fontSize = 32.sp, fontWeight = FontWeight.Black, color = MaterialTheme.colorScheme.primary)
            Text(unit, fontSize = 10.sp, fontWeight = FontWeight.Bold, color = MaterialTheme.colorScheme.secondary, letterSpacing = 0.5.sp)
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
    context: android.content.Context
) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(top = 8.dp)
    ) {
        SessionControlPanel(
            isRecording = isRecording,
            elapsedSeconds = elapsedSeconds,
            maxAmplitude = maxAmplitude,
            recordingsList = recordingsList,
            onRequestPermission = onRequestPermission,
            context = context
        )
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
fun TimelineList(events: List<InningsEvent>) {
    val formatter = SimpleDateFormat("HH:mm:ss", Locale.getDefault())
    val filteredEvents = events.filter { it.description != "Session Started" && it.description != "Session Ended" }
    
    LazyColumn(
        modifier = Modifier.fillMaxSize().padding(horizontal = 16.dp),
        contentPadding = PaddingValues(bottom = 24.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        items(filteredEvents.reversed()) { event ->
            TimelineItem(event, formatter)
        }
    }
}

@Composable
fun TimelineItem(event: InningsEvent, formatter: SimpleDateFormat) {
    val isHit = !event.description.contains("Miss")
    val accentColor = if (isHit) MaterialTheme.colorScheme.primary else Color(0xFFFF5252)

    Card(
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface.copy(alpha = 0.5f)),
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(16.dp),
        border = androidx.compose.foundation.BorderStroke(1.dp, accentColor.copy(alpha = 0.2f))
    ) {
        Row(
            modifier = Modifier.padding(16.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Box(
                modifier = Modifier
                    .width(4.dp)
                    .height(40.dp)
                    .clip(CircleShape)
                    .background(accentColor)
            )
            
            Spacer(modifier = Modifier.width(16.dp))
            
            Column(modifier = Modifier.weight(1f)) {
                Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                    Text(
                        event.shotType?.uppercase() ?: "ACTION",
                        fontWeight = FontWeight.Black,
                        fontSize = 14.sp,
                        color = Color.White,
                        letterSpacing = 0.5.sp
                    )
                    Text(
                        formatter.format(Date(event.timestamp)),
                        fontSize = 11.sp,
                        color = Color.Gray
                    )
                }
                
                Text(
                    event.description,
                    fontSize = 12.sp,
                    color = Color.White.copy(alpha = 0.6f)
                )

                if (event.batSpeed != null) {
                    Spacer(modifier = Modifier.height(8.dp))
                    Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                        MetricSmall("SPEED", "${event.batSpeed.toInt()} km/h")
                        if (event.efficiency != null) {
                            MetricSmall("EFF", "${event.efficiency.toInt()}%")
                        }
                        if (event.impactTimeMs != null) {
                            MetricSmall("REACT", "${event.impactTimeMs} ms")
                        }
                    }
                    if (event.wristRollDeg != null || event.followThroughAngle != null) {
                        Spacer(modifier = Modifier.height(4.dp))
                        Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                            if (event.wristRollDeg != null) {
                                MetricSmall("WRIST", "${String.format("%.0f", event.wristRollDeg)}°")
                            }
                            if (event.followThroughAngle != null) {
                                MetricSmall("FINISH", "${String.format("%.0f", event.followThroughAngle)}°")
                            }
                        }
                    }
                }
            }
        }
    }
}

@Composable
fun MetricSmall(label: String, value: String) {
    Column {
        Text(label, fontSize = 8.sp, fontWeight = FontWeight.Bold, color = Color.Gray)
        Text(value, fontSize = 12.sp, fontWeight = FontWeight.Bold, color = Color(0xFFBCD2FE))
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
fun SessionControlPanel(
    isRecording: Boolean,
    elapsedSeconds: Long,
    maxAmplitude: Float,
    recordingsList: List<java.io.File>,
    onRequestPermission: () -> Unit,
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
                        if (isRecording) "SESSION TRACKING ACTIVE" else "SESSION CONTROLLER",
                        fontSize = 14.sp,
                        fontWeight = FontWeight.Black,
                        color = Color.White
                    )
                }
                
                if (isRecording) {
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
                } else {
                    Box(
                        modifier = Modifier
                            .size(10.dp)
                            .clip(CircleShape)
                            .background(Color.Gray.copy(alpha = 0.5f))
                    )
                }
            }

            if (!isRecording) {
                Text(
                    "Start session tracking to record raw watch telemetry and capture voice annotations. Recording saves automatically for direct sync.",
                    fontSize = 11.sp,
                    color = Color.Gray,
                    lineHeight = 16.sp
                )

                Button(
                    onClick = {
                        val hasAudio = androidx.core.content.ContextCompat.checkSelfPermission(
                            context,
                            android.Manifest.permission.RECORD_AUDIO
                        ) == android.content.pm.PackageManager.PERMISSION_GRANTED
                        val hasBt = if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.S) {
                            androidx.core.content.ContextCompat.checkSelfPermission(
                                context,
                                android.Manifest.permission.BLUETOOTH_CONNECT
                            ) == android.content.pm.PackageManager.PERMISSION_GRANTED
                        } else {
                            true
                        }
                        if (hasAudio && hasBt) {
                            com.mrpeel.cricketbattingtracker.services.AudioRecordManager.startRecording(context)
                        } else {
                            onRequestPermission()
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
                        Text("🎙️", fontSize = 16.sp)
                        Text(
                            "START SESSION & AUDIO RECORD",
                            fontWeight = FontWeight.Black,
                            fontSize = 11.sp,
                            color = Color(0xFF000C1B),
                            letterSpacing = 0.5.sp
                        )
                    }
                }

                if (recordingsList.isNotEmpty()) {
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
                        fontSize = 36.sp,
                        fontWeight = FontWeight.Black,
                        color = MaterialTheme.colorScheme.primary,
                        letterSpacing = 1.sp
                    )

                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(40.dp)
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

                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(12.dp)
                    ) {
                        OutlinedButton(
                            onClick = {
                                com.mrpeel.cricketbattingtracker.services.AudioRecordManager.discardRecording(context)
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
                                com.mrpeel.cricketbattingtracker.services.AudioRecordManager.stopRecording(context)
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
