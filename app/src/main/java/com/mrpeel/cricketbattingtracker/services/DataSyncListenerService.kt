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
                if (bestLocation == null || loc.accuracy < bestLocation!!.accuracy) {
                    bestLocation = loc
                }
            }
        }
        
        // If we got a highly accurate recent location, return it immediately!
        if (bestLocation != null && bestLocation!!.accuracy < 30f) {
            continuation.resume(bestLocation)
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
            mainHandler.postDelayed(timeoutRunnable, 5000)
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
        try {
            val loc = getCurrentLocationSuspend(applicationContext)
            if (loc != null) {
                val geocoder = Geocoder(applicationContext, Locale.getDefault())
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
                    return when {
                        street.isNotEmpty() && suburb.isNotEmpty() -> "$street, $suburb"
                        suburb.isNotEmpty() -> suburb
                        else -> "Net Practice"
                    }
                }
            }
        } catch (e: Exception) {
            Log.e(TAG, "Failed to retrieve location: ${e.message}")
        }
        return "Net Practice"
    }

    private fun ingestTimeline(timestamp: Long, eventsList: Array<String>) {
        val database = AppDatabase.getDatabase(applicationContext)
        val dao = database.inningsEventDao()
        
        CoroutineScope(Dispatchers.IO).launch {
            val newInningsId = (dao.getLatestInningsId() ?: 0) + 1
            val resolvedLocation = getPhoneLocation()
            var maxSpeed = 0f
            var shotCount = 0
            
            var parsedStartTs = Long.MAX_VALUE
            var parsedEndTs = Long.MIN_VALUE
            val parsedHeartRates = mutableListOf<Pair<Long, Long>>()

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
                    var desc = eventString
                    var shotTimestamp: Long? = null

                    try {
                        val regex = Regex("Type=([^,]+), Spd=([0-9.]+), Hit=(true|false), Acc=([0-9.]+), SS=([A-Za-z/]+), Eff=([0-9.]+), BL=([0-9.-]+), FT=([0-9.-]+)(?:,\\s*ItMs=([0-9]+))?(?:,\\s*Wr=([0-9.-]+))?(?:,\\s*Ts=([0-9]+))?")
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
                        location = resolvedLocation
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
                }
            }

            // Sync the completed session to Health Connect (Samsung Health)
            try {
                val finalStartTime = if (parsedStartTs != Long.MAX_VALUE) parsedStartTs else timestamp
                val finalEndTime = if (parsedEndTs != Long.MIN_VALUE && parsedEndTs > finalStartTime) {
                    parsedEndTs
                } else {
                    finalStartTime + (eventsList.size * 5000L)
                }

                val hcManager = HealthConnectManager(applicationContext)
                val success = hcManager.writeCricketWorkout(
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

            // Pass the downloaded batch asynchronously up to Google Firestore
            // Auto-launch the UI to show the new sync results
            val launchIntent = Intent(applicationContext, com.mrpeel.cricketbattingtracker.MainActivity::class.java)
            launchIntent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            launchIntent.addFlags(Intent.FLAG_ACTIVITY_SINGLE_TOP)
            applicationContext.startActivity(launchIntent)
        }
    }
}
