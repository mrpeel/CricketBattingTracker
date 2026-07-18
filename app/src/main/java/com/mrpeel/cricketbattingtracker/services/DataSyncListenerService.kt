package com.mrpeel.cricketbattingtracker.services

import android.Manifest
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.location.Geocoder
import android.location.Location
import android.location.LocationManager
import android.location.LocationListener
import android.os.Bundle
import android.util.Log
import androidx.core.content.ContextCompat
import com.google.android.gms.wearable.DataEvent
import com.google.android.gms.wearable.DataEventBuffer
import com.google.android.gms.wearable.DataMapItem
import com.google.android.gms.wearable.WearableListenerService
import com.mrpeel.cricketbattingtracker.data.AppDatabase
import com.mrpeel.cricketbattingtracker.data.HeartRateEvent
import com.mrpeel.cricketbattingtracker.data.InningsEvent
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.suspendCancellableCoroutine
import kotlin.coroutines.resume
import java.util.Locale

class DataSyncListenerService : WearableListenerService() {
    private val TAG = "DataSyncListener"

    override fun onCreate() {
        super.onCreate()
        Log.d(TAG, "DataSyncListenerService onCreate: checking for unprocessed incoming sessions...")
        val sessionsDir = java.io.File(getExternalFilesDir(null), "watch_sessions_incoming")
        val tempZipFile = java.io.File(sessionsDir, "temp_session_raw.zip")
        if (tempZipFile.exists() && tempZipFile.length() > 0) {
            Log.d(TAG, "Found unprocessed session ZIP on service start. Processing...")
            CoroutineScope(Dispatchers.IO).launch {
                try {
                    unzipAndProcessIncomingSession(tempZipFile)
                } catch (e: Exception) {
                    Log.e(TAG, "Error unzipping and processing incoming session on start", e)
                }
            }
        }
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        if (intent?.action == "com.mrpeel.cricketbattingtracker.INJECT_TIMELINE") {
            try {
                // Read the pushed wear OS file directly off disk to avoid ADB shell string collision
                val file = java.io.File("/data/local/tmp/wear_timeline.txt")
                if (file.exists()) {
                    val payload = file.readText().split("\n").filter { it.isNotBlank() }.toTypedArray()
                    Log.d(TAG, "ADB Injection Detected! Processing ${payload.size} events...")
                    ingestTimeline(System.currentTimeMillis(), payload)
                }
            } catch (e: Exception) {
                Log.e(TAG, "Injection read failed", e)
            }
        }
        return super.onStartCommand(intent, flags, startId)
    }

    override fun onDataChanged(dataEvents: DataEventBuffer) {
        for (event in dataEvents) {
            if (event.type == DataEvent.TYPE_CHANGED) {
                val item = event.dataItem
                if (item.uri.path == "/cricket_timeline") {
                    val dataMapItem = DataMapItem.fromDataItem(item)
                    val dataMap = dataMapItem.dataMap
                    
                    val timestamp = dataMap.getLong("timestamp")
                    val eventsList = dataMap.getStringArray("events")
                    
                    val watchToPhoneOffset = System.currentTimeMillis() - timestamp
                    val prefs = getSharedPreferences("pitch_analytix_prefs", Context.MODE_PRIVATE)
                    prefs.edit().putLong("watch_to_phone_offset", watchToPhoneOffset).apply()
                    Log.d(TAG, "Watch-to-Phone clock offset calibrated: ${watchToPhoneOffset}ms")
                    
                    Log.d(TAG, "Received timeline sync: ${eventsList?.size} events")
                    if (eventsList != null) {
                        ingestTimeline(timestamp, eventsList)
                    }
                }
            }
        }
    }

    private suspend fun getCurrentLocationSuspend(context: Context): Location? = suspendCancellableCoroutine { continuation ->
        val locationManager = context.getSystemService(Context.LOCATION_SERVICE) as LocationManager
        if (ContextCompat.checkSelfPermission(context, Manifest.permission.ACCESS_COARSE_LOCATION) != PackageManager.PERMISSION_GRANTED) {
            continuation.resume(null)
            return@suspendCancellableCoroutine
        }

        // 1. Try to get a recent and accurate last known location first (less than 5 minutes old)
        val now = System.currentTimeMillis()
        var bestLocation: Location? = null
        for (provider in locationManager.getProviders(true)) {
            val loc = locationManager.getLastKnownLocation(provider) ?: continue
            // If the location is recent (within 5 minutes)
            if (now - loc.time < 5 * 60 * 1000L) {
                val currentBest = bestLocation
                if (currentBest == null || loc.accuracy < currentBest.accuracy) {
                    bestLocation = loc
                }
            }
        }
        
        // If we got a highly accurate recent location, return it immediately!
        val finalBest = bestLocation
        if (finalBest != null && finalBest.accuracy < 30f) {
            continuation.resume(finalBest)
            return@suspendCancellableCoroutine
        }

        val isGpsEnabled = locationManager.isProviderEnabled(LocationManager.GPS_PROVIDER)
        val isNetworkEnabled = locationManager.isProviderEnabled(LocationManager.NETWORK_PROVIDER)

        if (!isGpsEnabled && !isNetworkEnabled) {
            // Fallback to absolute best last known regardless of time
            var fallback: Location? = null
            for (provider in locationManager.getProviders(true)) {
                val loc = locationManager.getLastKnownLocation(provider) ?: continue
                val currentFallback = fallback
                if (currentFallback == null || loc.accuracy < currentFallback.accuracy) {
                    fallback = loc
                }
            }
            continuation.resume(fallback ?: bestLocation)
            return@suspendCancellableCoroutine
        }

        val listener = object : LocationListener {
            override fun onLocationChanged(location: Location) {
                locationManager.removeUpdates(this)
                if (continuation.isActive) {
                    continuation.resume(location)
                }
            }
            @Deprecated("Deprecated in Android 29")
            override fun onStatusChanged(provider: String?, status: Int, extras: Bundle?) {}
            override fun onProviderEnabled(provider: String) {}
            override fun onProviderDisabled(provider: String) {}
        }

        val mainHandler = android.os.Handler(android.os.Looper.getMainLooper())
        val timeoutRunnable = Runnable {
            locationManager.removeUpdates(listener)
            if (continuation.isActive) {
                var fallback: Location? = null
                for (p in locationManager.getProviders(true)) {
                    val loc = locationManager.getLastKnownLocation(p) ?: continue
                    val currentFallback = fallback
                    if (currentFallback == null || loc.accuracy < currentFallback.accuracy) {
                        fallback = loc
                    }
                }
                continuation.resume(fallback ?: bestLocation)
            }
        }

        try {
            // Request updates from both providers for maximum reliability
            if (isGpsEnabled) {
                locationManager.requestLocationUpdates(LocationManager.GPS_PROVIDER, 0L, 0f, listener, android.os.Looper.getMainLooper())
            }
            if (isNetworkEnabled) {
                locationManager.requestLocationUpdates(LocationManager.NETWORK_PROVIDER, 0L, 0f, listener, android.os.Looper.getMainLooper())
            }
            mainHandler.postDelayed(timeoutRunnable, 12000)
        } catch (e: Exception) {
            Log.e(TAG, "Failed requesting location updates: ${e.message}")
            locationManager.removeUpdates(listener)
            mainHandler.removeCallbacks(timeoutRunnable)
            if (continuation.isActive) {
                continuation.resume(bestLocation)
            }
        }

        continuation.invokeOnCancellation {
            locationManager.removeUpdates(listener)
            mainHandler.removeCallbacks(timeoutRunnable)
        }
    }

    private suspend fun getPhoneLocation(): String {
        val db = AppDatabase.getDatabase(applicationContext)
        
        // Redundancy Layer 1: Try real-time GPS/Network location and Geocoder
        try {
            val loc = getCurrentLocationSuspend(applicationContext)
            if (loc != null) {
                val geocoder = Geocoder(applicationContext, Locale.getDefault())
                var addresses: List<android.location.Address>? = null
                if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.TIRAMISU) {
                    val lat = loc.latitude
                    val lon = loc.longitude
                    val comp = kotlinx.coroutines.CompletableDeferred<List<android.location.Address>?>()
                    geocoder.getFromLocation(lat, lon, 1, object : Geocoder.GeocodeListener {
                        override fun onGeocode(list: List<android.location.Address>) {
                            comp.complete(list)
                        }
                        override fun onError(errorMessage: String?) {
                            comp.complete(null)
                        }
                    })
                    addresses = comp.await()
                } else {
                    var attempt = 0
                    while (attempt < 3 && addresses == null) {
                        try {
                            @Suppress("DEPRECATION")
                            addresses = geocoder.getFromLocation(loc.latitude, loc.longitude, 1)
                        } catch (e: Exception) {
                            attempt++
                            if (attempt >= 3) throw e
                            kotlinx.coroutines.delay(500)
                        }
                    }
                }
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
                    val resolved = when {
                        street.isNotEmpty() && suburb.isNotEmpty() -> "$street, $suburb"
                        suburb.isNotEmpty() -> suburb
                        else -> ""
                    }
                    if (resolved.isNotEmpty()) {
                        return resolved
                    }
                }
            }
        } catch (e: Exception) {
            Log.e(TAG, "Failed to retrieve real-time location: ${e.message}")
        }

        // Redundancy Layer 2: Read cached location from SharedPreferences (populated by MainActivity in the foreground)
        try {
            val prefs = getSharedPreferences("pitch_analytix_prefs", Context.MODE_PRIVATE)
            val cachedLoc = prefs.getString("cached_resolved_location", null)
            if (!cachedLoc.isNullOrBlank()) {
                Log.d(TAG, "Found highly accurate cached foreground location: $cachedLoc")
                return cachedLoc
            }
        } catch (e: Exception) {
            Log.e(TAG, "Failed reading cached location from preferences: ${e.message}")
        }

        // Redundancy Layer 3: Fallback to the last successfully resolved location from database
        val lastDbLoc = db.inningsEventDao().getLastResolvedLocation()
        if (!lastDbLoc.isNullOrBlank()) {
            Log.d(TAG, "Fallback to last known database resolved location: $lastDbLoc")
            return lastDbLoc
        }

        // Final Default Fallback
        return "Net Practice"
    }

    /** Extract a float value for a key like "F1=" from an event string. */
    private fun extractFloat(event: String, key: String): Float? {
        val prefix = "$key="
        val startIdx = event.indexOf(prefix)
        if (startIdx < 0) return null
        val valueStart = startIdx + prefix.length
        val endIdx = event.indexOf(',', valueStart).let { if (it < 0) event.length else it }
        return event.substring(valueStart, endIdx).trim().toFloatOrNull()
    }

    private fun ingestTimeline(timestamp: Long, eventsList: Array<String>) {
        val database = AppDatabase.getDatabase(applicationContext)
        val dao = database.inningsEventDao()
        
        CoroutineScope(Dispatchers.IO).launch {
            var systemStartTs: Long? = null
            eventsList.forEach { eventString ->
                if (eventString.startsWith("SYSTEM_START:")) {
                    try {
                        val regex = Regex("Ts=(\\d+)")
                        val match = regex.find(eventString)
                        if (match != null) {
                            systemStartTs = match.groupValues[1].toLong()
                        }
                    } catch (e: Exception) {}
                }
            }

            val newInningsId = systemStartTs?.let { dao.findInningsIdNearTime(it) }
                ?: ((dao.getLatestInningsId() ?: 0) + 1)

            val resolvedLocation = getPhoneLocation()
            var maxSpeed = 0f
            var shotCount = 0
            
            var parsedStartTs = Long.MAX_VALUE
            var parsedEndTs = Long.MIN_VALUE
            val parsedHeartRates = mutableListOf<Pair<Long, Long>>()
            // systemStartTs resolved above
            var systemEndTs: Long? = null
            
            // Collect TAP_SEQ events for Polar Sense alignment
            val watchTapSequences = mutableListOf<Pair<Long, List<Long>>>()

            eventsList.forEachIndexed { index, eventString ->
                if (eventString.startsWith("Shot:")) {
                    var speed: Float? = null
                    var impact: Float? = null
                    var impactTimeMs: Long? = null
                    var shotType: String? = null
                    var efficiency: Float? = null
                    var blAngle: Float? = null
                    var ftAngle: Float? = null
                    var wristRollDeg: Float? = null
                    var bladeAngle: Float? = null
                    var bladeClass: String? = null
                    var launchAngle: Float? = null
                    var launchClass: String? = null
                    var desc = eventString
                    var shotTimestamp: Long? = null

                    try {
                        val regex = Regex("Type=([^,]+), Spd=([0-9.]+), Hit=(true|false), Acc=([0-9.]+), SS=([A-Za-z/]+), Eff=([0-9.]+), BL=([0-9.-]+), FT=([0-9.-]+)(?:,\\s*ItMs=([0-9]+))?(?:,\\s*Wr=([0-9.-]+))?(?:,\\s*Ts=([0-9]+))?(?:,\\s*Bd=([0-9.-]+))?(?:,\\s*BdCl=([A-Za-z_/]+))?(?:,\\s*Lch=([0-9.-]+))?(?:,\\s*LchCl=([A-Za-z_/]+))?")
                        val match = regex.find(eventString)
                        if (match != null) {
                            shotType = match.groupValues[1]
                            speed = match.groupValues[2].toFloat()
                            val isHit = match.groupValues[3].toBoolean()
                            impact = match.groupValues[4].toFloat()
                            val sweetSpot = match.groupValues[5]
                            efficiency = match.groupValues[6].toFloat()
                            blAngle = match.groupValues[7].toFloat()
                            ftAngle = match.groupValues[8].toFloat()
                            impactTimeMs = match.groupValues[9].toLongOrNull()
                            wristRollDeg = match.groupValues[10].toFloatOrNull()
                            shotTimestamp = match.groupValues.getOrNull(11)?.toLongOrNull()
                            bladeAngle = match.groupValues.getOrNull(12)?.toFloatOrNull()
                            bladeClass = match.groupValues.getOrNull(13)?.takeIf { it.isNotBlank() && it != "null" }
                            launchAngle = match.groupValues.getOrNull(14)?.toFloatOrNull()
                            launchClass = match.groupValues.getOrNull(15)?.takeIf { it.isNotBlank() && it != "null" }
                            desc = if (isHit) "$shotType ($sweetSpot)" else "Play and Miss"
                            
                            shotCount++
                            if (speed > maxSpeed) {
                                maxSpeed = speed
                            }

                            shotTimestamp?.let { ts ->
                                if (ts < parsedStartTs) parsedStartTs = ts
                                if (ts > parsedEndTs) parsedEndTs = ts
                            }
                        }
                    } catch (e: Exception) {
                        Log.e(TAG, "Parse error: $eventString", e)
                    }

                    // Parse SwingFeatures F1-F14 (appended by watch in expanded format)
                    val f1 = extractFloat(eventString, "F1")
                    val f2 = extractFloat(eventString, "F2")
                    val f3 = extractFloat(eventString, "F3")
                    val f4 = extractFloat(eventString, "F4")
                    val f5 = extractFloat(eventString, "F5")
                    val f6 = extractFloat(eventString, "F6")
                    val f7 = extractFloat(eventString, "F7")
                    val f8 = extractFloat(eventString, "F8")
                    val f9 = extractFloat(eventString, "F9")
                    val f10 = extractFloat(eventString, "F10")
                    val f11 = extractFloat(eventString, "F11")
                    val f12 = extractFloat(eventString, "F12")
                    val f13 = extractFloat(eventString, "F13")
                    val f14 = extractFloat(eventString, "F14")

                    val dbEvent = InningsEvent(
                        inningsId = newInningsId,
                        timestamp = shotTimestamp ?: (timestamp + index * 5000L),
                        description = desc,
                        batSpeed = speed,
                        impactForce = impact,
                        impactTimeMs = impactTimeMs,
                        shotType = shotType,
                        efficiency = efficiency,
                        backliftAngle = blAngle,
                        followThroughAngle = ftAngle,
                        wristRollDeg = wristRollDeg,
                        location = resolvedLocation,
                        bladeAngle = bladeAngle,
                        bladeClass = bladeClass,
                        launchAngle = launchAngle,
                        launchClass = launchClass,
                        swing_feature_s1_gyro_y_std = f1,
                        swing_feature_s1_gyro_z_std = f2,
                        swing_feature_s1_delta_x = f3,
                        swing_feature_s1_delta_z = f4,
                        swing_feature_s2_gyro_mag = f5,
                        swing_feature_s2_grav_y_mean = f6,
                        swing_feature_s2_delta_x = f7,
                        swing_feature_s2_delta_z = f8,
                        swing_feature_s3_roll_deg = f9,
                        swing_feature_s3_yaw_deg = f10,
                        swing_feature_s3_delta_x = f11,
                        swing_feature_s3_delta_z = f12,
                        swing_feature_s3_plane_ratio = f13,
                        swing_feature_s3_gyro_y_min = f14
                    )
                    dao.insertEvent(dbEvent)
                } else if (eventString.startsWith("HR:")) {
                    try {
                        val regex = Regex("BPM=(\\d+), Ts=(\\d+)")
                        val match = regex.find(eventString)
                        if (match != null) {
                            val bpm = match.groupValues[1].toLong()
                            val ts = match.groupValues[2].toLong()
                            parsedHeartRates.add(Pair(ts, bpm))
                            if (ts < parsedStartTs) parsedStartTs = ts
                            if (ts > parsedEndTs) parsedEndTs = ts

                            val hrEvent = HeartRateEvent(
                                inningsId = newInningsId,
                                timestamp = ts,
                                beatsPerMinute = bpm
                            )
                            dao.insertHeartRate(hrEvent)
                        }
                    } catch (e: Exception) {
                        Log.e(TAG, "Failed to parse HR event: $eventString", e)
                    }
                } else if (eventString.startsWith("SYSTEM_START:")) {
                    try {
                        val regex = Regex("Ts=(\\d+)")
                        val match = regex.find(eventString)
                        if (match != null) {
                            val ts = match.groupValues[1].toLong()
                            systemStartTs = ts
                            
                            val startEvent = InningsEvent(
                                inningsId = newInningsId,
                                timestamp = ts,
                                description = "Session Started",
                                location = resolvedLocation
                            )
                            dao.insertEvent(startEvent)
                        }
                    } catch (e: Exception) {
                        Log.e(TAG, "Failed to parse SYSTEM_START: $eventString", e)
                    }
                } else if (eventString.startsWith("TAP_SEQ:")) {
                    // Parse tap sequence for Polar Sense alignment
                    // Format: TAP_SEQ: Ts={wallClockMs}, T1={ns1},T2={ns2},T3={ns3},T4={ns4},T5={ns5}
                    try {
                        val tsMatch = Regex("Ts=(\\d+)").find(eventString)
                        val wallClockMs = tsMatch?.groupValues?.get(1)?.toLongOrNull() ?: 0L
                        
                        val tapNanos = mutableListOf<Long>()
                        for (i in 1..5) {
                            val tMatch = Regex("T$i=(\\d+)").find(eventString)
                            tMatch?.groupValues?.get(1)?.toLongOrNull()?.let { tapNanos.add(it) }
                        }
                        
                        if (tapNanos.size == 5 && wallClockMs > 0) {
                            watchTapSequences.add(Pair(wallClockMs, tapNanos))
                            Log.d(TAG, "Parsed TAP_SEQ at $wallClockMs with 5 taps")
                        }
                    } catch (e: Exception) {
                        Log.e(TAG, "Failed to parse TAP_SEQ: $eventString", e)
                    }
                } else if (eventString.startsWith("SYSTEM_END:")) {
                    try {
                        val regex = Regex("Ts=(\\d+)")
                        val match = regex.find(eventString)
                        if (match != null) {
                            val ts = match.groupValues[1].toLong()
                            systemEndTs = ts
                            
                            val endEvent = InningsEvent(
                                inningsId = newInningsId,
                                timestamp = ts,
                                description = "Session Ended",
                                location = resolvedLocation
                            )
                            dao.insertEvent(endEvent)
                        }
                    } catch (e: Exception) {
                        Log.e(TAG, "Failed to parse SYSTEM_END: $eventString", e)
                    }
                }
            }

            // Sync the completed session to Health Connect (Samsung Health)
            try {
                val finalStartTime = systemStartTs ?: (if (parsedStartTs != Long.MAX_VALUE) parsedStartTs else timestamp)
                val finalEndTime = systemEndTs ?: (if (parsedEndTs != Long.MIN_VALUE && parsedEndTs > finalStartTime) {
                    parsedEndTs
                } else {
                    finalStartTime + (eventsList.size * 5000L)
                })

                val hcManager = HealthConnectManager(applicationContext)
                val success = hcManager.writeCricketWorkout(
                    inningsId = newInningsId,
                    startTimeMillis = finalStartTime,
                    endTimeMillis = finalEndTime,
                    shotCount = shotCount,
                    maxSpeed = maxSpeed,
                    realHeartRates = parsedHeartRates
                )
                if (success) {
                    val prefs = applicationContext.getSharedPreferences("pitch_analytix_prefs", android.content.Context.MODE_PRIVATE)
                    val syncedIds = prefs.getStringSet("synced_innings_ids", emptySet())?.toMutableSet() ?: mutableSetOf()
                    syncedIds.add(newInningsId.toString())
                    prefs.edit().putStringSet("synced_innings_ids", syncedIds).apply()
                    Log.d(TAG, "Background sync to Health Connect succeeded for session $newInningsId!")
                } else {
                    Log.w(TAG, "Background sync to Health Connect skipped or failed for session $newInningsId.")
                }
            } catch (e: Exception) {
                Log.e(TAG, "Failed syncing to Health Connect: ${e.message}")
            }

            // Expose the temporary watch tap sequence data to shared preferences or log
            try {
                if (watchTapSequences.isNotEmpty()) {
                    Log.d(TAG, "Saved ${watchTapSequences.size} watch tap sequences for raw alignment matching")
                }
            } catch (e: Exception) {}

            Log.d(TAG, "Watch timeline sync completed for innings $newInningsId. Awaiting raw ZIP data...")
        }
    }

    override fun onChannelOpened(channel: com.google.android.gms.wearable.ChannelClient.Channel) {
        Log.d(TAG, "onChannelOpened: path=${channel.path}")
        if (channel.path == "/raw_session_data") {
            val sessionsDir = java.io.File(getExternalFilesDir(null), "watch_sessions_incoming")
            sessionsDir.mkdirs()
            val tempZipFile = java.io.File(sessionsDir, "temp_session_raw.zip")
            
            val channelClient = com.google.android.gms.wearable.Wearable.getChannelClient(this)
            channelClient.receiveFile(channel, android.net.Uri.fromFile(tempZipFile), false)
                .addOnSuccessListener {
                    Log.d(TAG, "Successfully started receiving raw session ZIP file")
                }
                .addOnFailureListener { e ->
                    Log.e(TAG, "Failed to initiate receiveFile: ${e.message}")
                }
        }
    }

    override fun onInputClosed(channel: com.google.android.gms.wearable.ChannelClient.Channel, closeReason: Int, appSpecificErrorCode: Int) {
        Log.d(TAG, "onInputClosed: path=${channel.path}, reason=$closeReason")
        if (channel.path == "/raw_session_data" && closeReason == com.google.android.gms.wearable.ChannelClient.ChannelCallback.CLOSE_REASON_NORMAL) {
            val sessionsDir = java.io.File(getExternalFilesDir(null), "watch_sessions_incoming")
            val tempZipFile = java.io.File(sessionsDir, "temp_session_raw.zip")
            if (tempZipFile.exists()) {
                Log.d(TAG, "Raw session ZIP received fully. Length: ${tempZipFile.length()} bytes")
                CoroutineScope(Dispatchers.IO).launch {
                    try {
                        unzipAndProcessIncomingSession(tempZipFile)
                    } catch (e: Exception) {
                        Log.e(TAG, "Error unzipping and processing incoming session", e)
                    }
                }
            }
        }
    }

    private suspend fun unzipAndProcessIncomingSession(zipFile: java.io.File) {
        val database = AppDatabase.getDatabase(applicationContext)
        val dao = database.inningsEventDao()
        
        val timestamp = java.text.SimpleDateFormat("yyyy-MM-dd_HH-mm-ss", java.util.Locale.US).format(java.util.Date())
        
        // 1. Copy the incoming zip to permanent compressed zip file
        val permanentZipFile = java.io.File(getExternalFilesDir("watch_sessions"), "session_$timestamp.zip")
        try {
            zipFile.copyTo(permanentZipFile, overwrite = true)
            Log.d(TAG, "Saved permanent compressed session zip to: ${permanentZipFile.absolutePath}")
        } catch (e: Exception) {
            Log.e(TAG, "Failed to save permanent zip file: ${e.message}")
        }
        
        // 2. Unzip to temporary folder for processing
        val watchSessionsDir = java.io.File(getExternalFilesDir("watch_sessions"), "temp_processing_$timestamp")
        watchSessionsDir.mkdirs()
        
        Log.d(TAG, "Unzipping watch logs for processing to: ${watchSessionsDir.absolutePath}")
        unzip(zipFile, watchSessionsDir)
        
        // Clean up temporary ZIP file
        if (zipFile.exists()) {
            zipFile.delete()
        }

        // Resolve innings ID by matching watch session timestamp with timeline
        var sessionStartMs: Long? = null
        val timelineFile = java.io.File(watchSessionsDir, "latest_timeline.txt")
        if (timelineFile.exists()) {
            try {
                timelineFile.forEachLine { line ->
                    if (line.startsWith("SYSTEM_START:")) {
                        val regex = Regex("Ts=(\\d+)")
                        val match = regex.find(line)
                        if (match != null) {
                            sessionStartMs = match.groupValues[1].toLong()
                        }
                    }
                }
            } catch (e: Exception) {
                Log.e(TAG, "Failed parsing latest_timeline.txt for start time", e)
            }
        }
        
        if (sessionStartMs == null) {
            val accFile = java.io.File(watchSessionsDir, "WatchAccelerometer.csv")
            if (accFile.exists()) {
                try {
                    accFile.useLines { lines ->
                        val firstSample = lines.drop(1).firstOrNull()
                        if (firstSample != null) {
                            val parts = firstSample.split(",")
                            if (parts.isNotEmpty()) {
                                val timeNanos = parts[0].toLongOrNull()
                                if (timeNanos != null) {
                                    sessionStartMs = timeNanos / 1_000_000L
                                }
                            }
                        }
                    }
                } catch (e: Exception) {}
            }
        }

        val resolvedStartMs = sessionStartMs ?: System.currentTimeMillis()
        val newInningsId = dao.findInningsIdNearTime(resolvedStartMs)
            ?: ((dao.getLatestInningsId() ?: 0) + 1)

        Log.d(TAG, "Resolved inningsId $newInningsId for session starting at $resolvedStartMs")

        // Find the latest Polar session directory on the phone
        val polarRoot = getExternalFilesDir("polar_sessions")
        val polarSessionDir = polarRoot?.listFiles()
            ?.filter { it.isDirectory && it.name.startsWith("polar_session_") }
            ?.maxByOrNull { it.name }

        if (polarSessionDir == null) {
            Log.d(TAG, "No Polar session directory found on phone — falling back to watch-only batch processing.")
            try {
                PhoneSwingDetector.processWatchOnlySession(newInningsId, watchSessionsDir, applicationContext)
            } catch (e: Exception) {
                Log.e(TAG, "Phone watch-only swing detection batch processing failed", e)
            }
        } else {
            Log.d(TAG, "Found Polar session directory: ${polarSessionDir.absolutePath}")
            try {
                PhoneSwingDetector.processSession(newInningsId, watchSessionsDir, polarSessionDir, applicationContext)
            } catch (e: Exception) {
                Log.e(TAG, "Phone swing detection batch processing failed", e)
            }
        }

        // Run video clipping for the completed session
        try {
            VideoClippingEngine.clipSessionShots(newInningsId, applicationContext)
        } catch (e: Exception) {
            Log.e(TAG, "Video clipping failed: ${e.message}", e)
        }

        // Clean up the temporary watch uncompressed directory
        if (watchSessionsDir.exists()) {
            try {
                watchSessionsDir.deleteRecursively()
                Log.d(TAG, "Deleted temp watch sessions directory: ${watchSessionsDir.absolutePath}")
            } catch (e: Exception) {
                Log.e(TAG, "Failed to delete temp watch directory", e)
            }
        }

        // Auto-launch the UI to show the new sync results
        val launchIntent = Intent(applicationContext, com.mrpeel.cricketbattingtracker.MainActivity::class.java)
        launchIntent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        launchIntent.addFlags(Intent.FLAG_ACTIVITY_SINGLE_TOP)
        applicationContext.startActivity(launchIntent)
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
