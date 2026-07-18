package com.mrpeel.cricketbattingtracker.services

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import kotlin.math.sqrt
import android.app.Service
import android.content.Context
import android.content.Intent
import android.hardware.Sensor
import android.hardware.SensorEvent
import android.hardware.SensorEventListener
import android.hardware.SensorManager
import android.os.IBinder
import android.os.PowerManager
import android.util.Log
import androidx.core.app.NotificationCompat
import com.mrpeel.cricketbattingtracker.MainActivity
import com.mrpeel.cricketbattingtracker.ml.SwingDetector
import android.content.pm.ServiceInfo
import android.os.Build
import androidx.wear.ongoing.OngoingActivity
import androidx.wear.ongoing.Status
import java.io.File
import java.io.BufferedWriter
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers

class TrackerService : Service(), SensorEventListener {

    private val TAG = "TrackerService"
    private lateinit var sensorManager: SensorManager
    private var accelSensor: Sensor? = null
    private var gyroSensor: Sensor? = null
    private var gravitySensor: Sensor? = null
    private var rotationSensor: Sensor? = null
    private var gameRotationSensor: Sensor? = null
    private var stepDetectorSensor: Sensor? = null
    private var heartRateSensor: Sensor? = null
    private var magnetometerSensor: Sensor? = null
    
    private var wakeLock: PowerManager.WakeLock? = null
    private lateinit var dataSyncManager: DataSyncManager
    private lateinit var healthServicesManager: HealthServicesManager
    
    // Store timeline data
    private val sessionTimeline = mutableListOf<String>()
    private var shouldDiscard = false

    // Tap sequence detection for Polar Sense alignment
    private data class TapEvent(val wallClockMs: Long, val sensorNanos: Long, val magnitude: Float)
    private val tapBuffer = mutableListOf<TapEvent>()
    private val TAP_THRESHOLD = 25.0f  // m/s² magnitude
    private val TAP_MIN_GAP_MS = 200L
    private val TAP_MAX_GAP_MS = 1500L
    private val TAP_SEQUENCE_MAX_DURATION_MS = 5000L
    private val TAP_SEQUENCE_COOLDOWN_MS = 10000L
    private var lastTapSequenceTimeMs = 0L

    // Background Sensor Handling Thread
    private var sensorThread: android.os.HandlerThread? = null
    private var sensorHandler: android.os.Handler? = null

    // Dynamic Raw Debug Logging for Full Watch Sensor Stack
    private var enableRawLogging = false
    private var sessionStartNanos: Long = 0L
    private var currentSessionDir: File? = null

    private data class SensorConfig(
        val type: Int,
        val fileName: String,
        val header: String
    )

    private val writers = mutableMapOf<Int, BufferedWriter>()

    private val sensorConfigs = listOf(
        SensorConfig(Sensor.TYPE_ACCELEROMETER, "WatchAccelerometer.csv", "time,seconds_elapsed,x,y,z\n"),
        SensorConfig(Sensor.TYPE_GYROSCOPE, "WatchGyroscope.csv", "time,seconds_elapsed,x,y,z\n"),
        SensorConfig(Sensor.TYPE_GRAVITY, "WatchGravity.csv", "time,seconds_elapsed,x,y,z\n"),
        SensorConfig(Sensor.TYPE_GAME_ROTATION_VECTOR, "WatchGameOrientation.csv", "time,seconds_elapsed,qx,qy,qz,qw\n"),
        SensorConfig(Sensor.TYPE_STEP_DETECTOR, "WatchSteps.csv", "time,seconds_elapsed\n"),
        SensorConfig(Sensor.TYPE_HEART_RATE, "WatchHeartRate.csv", "time,seconds_elapsed,bpm\n"),
        SensorConfig(Sensor.TYPE_LINEAR_ACCELERATION, "WatchLinearAcceleration.csv", "time,seconds_elapsed,x,y,z\n"),
        SensorConfig(Sensor.TYPE_MAGNETIC_FIELD, "WatchMagnetometer.csv", "time,seconds_elapsed,x,y,z\n"),
        SensorConfig(Sensor.TYPE_PRESSURE, "WatchBarometer.csv", "time,seconds_elapsed,pressure\n"),
        SensorConfig(Sensor.TYPE_STEP_COUNTER, "WatchStepCounter.csv", "time,seconds_elapsed,steps\n")
    )

    override fun onCreate() {
        super.onCreate()
        Log.d(TAG, "Service Created")
        
        // Initialize background thread for sensor processing & I/O
        sensorThread = android.os.HandlerThread("SensorLoggingThread").apply { start() }
        sensorHandler = android.os.Handler(sensorThread!!.looper)

        dataSyncManager = DataSyncManager(this)
        // Disable HealthServicesManager MeasureClient in favor of standard Android heart rate sensor
        // healthServicesManager = HealthServicesManager(this)
        // healthServicesManager.onHeartRateUpdate = { bpm ->
        //     val hrTime = System.currentTimeMillis()
        //     Log.d(TAG, "Recording real HR sample to timeline: $bpm BPM")
        //     sessionTimeline.add("HR: BPM=$bpm, Ts=$hrTime")
        // }
        // healthServicesManager.startTracking()
        
        sensorManager = getSystemService(Context.SENSOR_SERVICE) as SensorManager
        accelSensor          = sensorManager.getDefaultSensor(Sensor.TYPE_ACCELEROMETER)
        gyroSensor           = sensorManager.getDefaultSensor(Sensor.TYPE_GYROSCOPE)
        gravitySensor        = sensorManager.getDefaultSensor(Sensor.TYPE_GRAVITY)
        rotationSensor       = sensorManager.getDefaultSensor(Sensor.TYPE_ROTATION_VECTOR)
        // GAME_ROTATION_VECTOR: magnetometer-free quaternion — more stable for bat orientation
        // (immune to metal bat springs, chain-link fences, metallic structures on pitch)
        gameRotationSensor   = sensorManager.getDefaultSensor(Sensor.TYPE_GAME_ROTATION_VECTOR)
        // STEP_DETECTOR: fires once per foot-strike step on dedicated DSP hardware
        // We request the wake-up version to prevent Sensor Hub suspension in ambient/screen-off mode.
        stepDetectorSensor   = sensorManager.getDefaultSensor(Sensor.TYPE_STEP_DETECTOR, true)
            ?: sensorManager.getDefaultSensor(Sensor.TYPE_STEP_DETECTOR)
        heartRateSensor      = sensorManager.getDefaultSensor(Sensor.TYPE_HEART_RATE)
        magnetometerSensor   = sensorManager.getDefaultSensor(Sensor.TYPE_MAGNETIC_FIELD)

        if (accelSensor == null)        Log.w(TAG, "Hardware Accelerometer is NOT available!")
        if (heartRateSensor == null)    Log.w(TAG, "Hardware Heart Rate Sensor is NOT available!")
        if (gyroSensor == null)         Log.w(TAG, "Hardware Gyroscope is NOT available!")
        if (gravitySensor == null)      Log.w(TAG, "Hardware Gravity Sensor is NOT available (SwingDetector will estimate gravity from Accelerometer)")
        if (rotationSensor == null)     Log.w(TAG, "Hardware Rotation Vector is NOT available!")
        if (gameRotationSensor == null) Log.w(TAG, "Game Rotation Vector NOT available — bat orientation will use standard Rotation Vector (magnetometer subject to interference)")
        if (stepDetectorSensor == null) Log.w(TAG, "Step Detector NOT available — walking discrimination will fall back to accel cadence heuristic")
        if (magnetometerSensor == null) Log.w(TAG, "Magnetometer NOT available — POWER SHOT override will rely on gyro magnitude only")
        
        // Setup wake lock to keep recording while screen is off
        val powerManager = getSystemService(Context.POWER_SERVICE) as PowerManager
        wakeLock = powerManager.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "CricketTracker::BattingWakeLock")
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        if (intent?.action == "STOP_TRACKING") {
            shouldDiscard = false
            SessionManager.setTracking(false)
            stopSelf()
            return START_NOT_STICKY
        } else if (intent?.action == "DISCARD_TRACKING") {
            shouldDiscard = true
            SessionManager.setTracking(false)
            stopSelf()
            return START_NOT_STICKY
        }

        enableRawLogging = true // Force raw logging to always be active in raw-only recording mode
        try {
            val ts = java.text.SimpleDateFormat("yyyy-MM-dd_HH-mm-ss", java.util.Locale.US).format(java.util.Date())
            val sessionDir = File(getExternalFilesDir(null), "sessions/session-$ts")
            sessionDir.mkdirs()
            currentSessionDir = sessionDir

            for (config in sensorConfigs) {
                val sensor = sensorManager.getDefaultSensor(config.type)
                if (sensor != null) {
                    try {
                        val writer = File(sessionDir, config.fileName).bufferedWriter()
                        writer.write(config.header)
                        writers[config.type] = writer
                    } catch (e: Exception) {
                        Log.e(TAG, "Failed to create writer for ${config.fileName}", e)
                    }
                }
            }
            Log.d(TAG, "Raw Logging ENABLED for all supported sensors in: ${sessionDir.absolutePath}")
        } catch (e: Exception) {
            Log.e(TAG, "Failed to prep log writers: ${e.message}")
        }

        if (sessionTimeline.isEmpty()) {
            val startTime = System.currentTimeMillis()
            sessionTimeline.add("SYSTEM_START: Ts=$startTime")
            Log.d(TAG, "Recording system start event: $startTime")
        }

        SessionManager.setTracking(true)
        startForegroundService()
        wakeLock?.acquire(3 * 60 * 60 * 1000L) // maximum 3 hours
        
        // Register sensor listeners on background thread handler at maximum frequency (SENSOR_DELAY_FASTEST)
        val hasGameRotation = sensorConfigs.any { it.type == Sensor.TYPE_GAME_ROTATION_VECTOR && sensorManager.getDefaultSensor(it.type) != null }
        for (config in sensorConfigs) {
            if (config.type == Sensor.TYPE_ROTATION_VECTOR && hasGameRotation) {
                continue // Skip standard rotation vector if game rotation vector is available to avoid double-binding
            }
            
            // Request wake-up version of low-frequency sensors to prevent Sensor Hub suspension in ambient/screen-off mode
            val sensor = if (config.type == Sensor.TYPE_STEP_DETECTOR ||
                             config.type == Sensor.TYPE_STEP_COUNTER ||
                             config.type == Sensor.TYPE_HEART_RATE) {
                sensorManager.getDefaultSensor(config.type, true) ?: sensorManager.getDefaultSensor(config.type)
            } else {
                sensorManager.getDefaultSensor(config.type)
            }
            if (sensor != null) {
                val delay = if (config.type == Sensor.TYPE_STEP_DETECTOR || 
                                 config.type == Sensor.TYPE_HEART_RATE ||
                                 config.type == Sensor.TYPE_STEP_COUNTER) {
                    SensorManager.SENSOR_DELAY_NORMAL
                } else {
                    5000 // 5000 microseconds = 200Hz high-fidelity logging (auto-bounded by hardware max)
                }
                sensorManager.registerListener(this, sensor, delay, 0, sensorHandler)
            }
        }
        
        Log.d(TAG, "Service Started, tracking sensors at max frequency")
        return START_STICKY
    }

    private fun startForegroundService() {
        val channelId = "CRICKET_TRACKING_CHANNEL"
        
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                channelId,
                "Cricket Batting Tracker",
                NotificationManager.IMPORTANCE_LOW
            )
            val manager = getSystemService(NotificationManager::class.java)
            manager.createNotificationChannel(channel)
        }

        val notificationIntent = Intent(this, MainActivity::class.java)
        val pendingIntent = PendingIntent.getActivity(
            this,
            0,
            notificationIntent,
            PendingIntent.FLAG_IMMUTABLE
        )
        val builder = NotificationCompat.Builder(this, channelId)
            .setSmallIcon(android.R.drawable.star_on)
            .setContentTitle("Cricket Tracking Active")
            .setContentText("Recording batting session...")
            .setContentIntent(pendingIntent)
            .setCategory(NotificationCompat.CATEGORY_WORKOUT)
            .setOngoing(true)

        val ongoingActivityStatus = Status.Builder()
            .addTemplate("Tracking Swings")
            .build()

        val ongoingActivity = OngoingActivity.Builder(applicationContext, 1, builder)
            .setAnimatedIcon(android.R.drawable.star_on)
            .setStaticIcon(android.R.drawable.star_on)
            .setTouchIntent(pendingIntent)
            .setStatus(ongoingActivityStatus)
            .build()
            
        ongoingActivity.apply(applicationContext)
        val notification = builder.build()

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            startForeground(1, notification, ServiceInfo.FOREGROUND_SERVICE_TYPE_HEALTH)
        } else {
            startForeground(1, notification)
        }
    }

    override fun onDestroy() {
        super.onDestroy()
        Log.d(TAG, "Service Destroyed")
        sensorManager.unregisterListener(this)
        
        // Safely shutdown background handler thread
        sensorThread?.quitSafely()
        
        if (::healthServicesManager.isInitialized) {
            healthServicesManager.stopTracking()
        }
        
        if (!shouldDiscard) {
            val endTime = System.currentTimeMillis()
            sessionTimeline.add("SYSTEM_END: Ts=$endTime")
            Log.d(TAG, "Recording system end event: $endTime")
            dataSyncManager.syncTimelineToPhone(sessionTimeline)
            // Expose timeline to ADB for headless integration testing
            try {
                val timelineFile = File(getExternalFilesDir(null), "latest_timeline.txt")
                timelineFile.writeText(sessionTimeline.joinToString("\n"))
            } catch (e: Exception) {}
            
            // Also write latest_timeline.txt into the session directory so it is part of the ZIP
            try {
                currentSessionDir?.let { sDir ->
                    val timelineFile = File(sDir, "latest_timeline.txt")
                    timelineFile.writeText(sessionTimeline.joinToString("\n"))
                }
            } catch (e: Exception) {
                Log.e(TAG, "Failed to write timeline to session directory: ${e.message}")
            }
        } else {
            Log.d(TAG, "Session discarded, skipping sync and timeline write.")
            try {
                val timelineFile = File(getExternalFilesDir(null), "latest_timeline.txt")
                if (timelineFile.exists()) {
                    timelineFile.delete()
                }
            } catch (e: Exception) {}
        }

        wakeLock?.let {
            if (it.isHeld) {
                it.release()
            }
        }
        
        // Clean up and close all dynamic log writers
        for ((type, writer) in writers) {
            try {
                writer.flush()
                writer.close()
                Log.d(TAG, "Closed raw log writer for sensor type $type")
            } catch (e: Exception) {
                Log.e(TAG, "Failed to close raw log writer for sensor type $type", e)
            }
        }
        writers.clear()

        // Zip and transfer to phone over GMS ChannelClient
        if (!shouldDiscard) {
            val sDir = currentSessionDir
            if (sDir != null && sDir.exists()) {
                val parentDir = sDir.parentFile ?: getExternalFilesDir(null)!!
                val zipFile = File(parentDir, "${sDir.name}_raw.zip")
                Thread {
                    try {
                        Log.d(TAG, "Zipping session folder: ${sDir.absolutePath}")
                        zipDirectory(sDir, zipFile)
                        Log.d(TAG, "Zip file created at: ${zipFile.absolutePath} (${zipFile.length()} bytes)")
                        syncRawDataToPhone(zipFile)
                    } catch (e: Exception) {
                        Log.e(TAG, "Zipping and syncing failed: ${e.message}", e)
                    }
                }.start()
            }
        }
    }

    private fun zipDirectory(sourceDir: File, zipFile: File) {
        java.util.zip.ZipOutputStream(java.io.BufferedOutputStream(java.io.FileOutputStream(zipFile))).use { zos ->
            sourceDir.walkTopDown().forEach { file ->
                if (file.isFile) {
                    val entryName = sourceDir.toURI().relativize(file.toURI()).path
                    zos.putNextEntry(java.util.zip.ZipEntry(entryName))
                    file.inputStream().use { input ->
                        input.copyTo(zos)
                    }
                    zos.closeEntry()
                }
            }
        }
    }

    private fun syncRawDataToPhone(zipFile: File) {
        val nodeClient = com.google.android.gms.wearable.Wearable.getNodeClient(this)
        val channelClient = com.google.android.gms.wearable.Wearable.getChannelClient(this)
        
        try {
            val nodes = com.google.android.gms.tasks.Tasks.await(nodeClient.connectedNodes)
            val phoneNode = nodes.firstOrNull()
            if (phoneNode == null) {
                Log.e(TAG, "No phone node connected to sync raw data!")
                return
            }
            
            Log.d(TAG, "Opening Channel to phone (${phoneNode.displayName}) under path /raw_session_data")
            val channel = com.google.android.gms.tasks.Tasks.await(channelClient.openChannel(phoneNode.id, "/raw_session_data"))
            
            Log.d(TAG, "Sending zip file ${zipFile.name} (${zipFile.length()} bytes)...")
            com.google.android.gms.tasks.Tasks.await(channelClient.sendFile(channel, android.net.Uri.fromFile(zipFile)))
            Log.d(TAG, "✅ Zipped raw data sent successfully to phone!")
            
            // Clean up the temporary zip file after successful send
            if (zipFile.exists()) {
                zipFile.delete()
            }
        } catch (e: Exception) {
            Log.e(TAG, "Error syncing raw session zip to phone: ${e.message}", e)
        }
    }

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onSensorChanged(event: SensorEvent?) {
        if (event == null) return
        
        val type = event.sensor.type
        val ts = event.timestamp
        val vals = event.values

        // Standard real-time sensor processing for state machine (passive logging mode)
        when (type) {
            Sensor.TYPE_ACCELEROMETER -> {
                // Tap sequence detection for Polar Sense alignment
                val accelMag = sqrt(vals[0] * vals[0] + vals[1] * vals[1] + vals[2] * vals[2])
                if (accelMag > TAP_THRESHOLD * 0.7f) {
                    tapBuffer.add(TapEvent(System.currentTimeMillis(), event.timestamp, accelMag))
                }
                // Prune tapBuffer entries older than 10 seconds
                val cutoffMs = System.currentTimeMillis() - 10_000L
                tapBuffer.removeAll { it.wallClockMs < cutoffMs }
                checkForTapSequence()
            }
            Sensor.TYPE_STEP_DETECTOR -> {
                val stepTime = System.currentTimeMillis()
                sessionTimeline.add("Step: Ts=$stepTime")
                Log.v(TAG, "Step detected at ${ts / 1_000_000_000.0f}s")
            }
            Sensor.TYPE_HEART_RATE -> {
                val bpm = vals[0].toInt()
                if (bpm > 0) {
                    val hrTime = System.currentTimeMillis()
                    Log.d(TAG, "Recording standard HR sample to timeline: $bpm BPM")
                    sessionTimeline.add("HR: BPM=$bpm, Ts=$hrTime")
                }
            }
        }

        // Dynamic background thread logging for full watch sensor stack
        if (enableRawLogging) {
            val writer = writers[type]
            if (writer != null) {
                try {
                    if (sessionStartNanos == 0L) sessionStartNanos = ts
                    val elapsedSecs = (ts - sessionStartNanos) / 1_000_000_000.0
                    
                    val csvLine = when (type) {
                        Sensor.TYPE_ROTATION_VECTOR,
                        Sensor.TYPE_GAME_ROTATION_VECTOR,
                        Sensor.TYPE_GEOMAGNETIC_ROTATION_VECTOR -> {
                            val qw = if (vals.size > 3) vals[3]
                                     else kotlin.math.sqrt(kotlin.math.max(0.0f, 1.0f - vals[0]*vals[0] - vals[1]*vals[1] - vals[2]*vals[2]))
                            String.format(java.util.Locale.US, "%d,%.6f,%.6f,%.6f,%.6f,%.6f\n", ts, elapsedSecs, vals[0], vals[1], vals[2], qw)
                        }
                        Sensor.TYPE_MAGNETIC_FIELD_UNCALIBRATED,
                        Sensor.TYPE_GYROSCOPE_UNCALIBRATED,
                        Sensor.TYPE_ACCELEROMETER_UNCALIBRATED -> {
                            val x = vals.getOrNull(0) ?: 0f
                            val y = vals.getOrNull(1) ?: 0f
                            val z = vals.getOrNull(2) ?: 0f
                            val bx = vals.getOrNull(3) ?: 0f
                            val by = vals.getOrNull(4) ?: 0f
                            val bz = vals.getOrNull(5) ?: 0f
                            String.format(java.util.Locale.US, "%d,%.6f,%.6f,%.6f,%.6f,%.6f,%.6f,%.6f\n", ts, elapsedSecs, x, y, z, bx, by, bz)
                        }
                        Sensor.TYPE_HEART_RATE,
                        Sensor.TYPE_PRESSURE,
                        Sensor.TYPE_STEP_COUNTER -> {
                            String.format(java.util.Locale.US, "%d,%.6f,%.6f\n", ts, elapsedSecs, vals[0])
                        }
                        Sensor.TYPE_STEP_DETECTOR -> {
                            String.format(java.util.Locale.US, "%d,%.6f\n", ts, elapsedSecs)
                        }
                        else -> {
                            String.format(java.util.Locale.US, "%d,%.6f,%.6f,%.6f,%.6f\n", ts, elapsedSecs, vals[0], vals[1], vals[2])
                        }
                    }
                    writer.write(csvLine)
                } catch (e: Exception) {
                    // Fail silently to prevent exception looping under high frequency events
                }
            }
        }
    }

    override fun onAccuracyChanged(sensor: Sensor?, accuracy: Int) {
        // Not used
    }

    /**
     * Detects a sequence of 5 deliberate taps on the watch/bat for Polar Sense alignment.
     * Finds peaks (local maxima) in the tap buffer, deduplicates within TAP_MIN_GAP_MS,
     * and checks for 5 consecutive peaks with inter-peak gaps in [TAP_MIN_GAP_MS, TAP_MAX_GAP_MS]
     * and total duration ≤ TAP_SEQUENCE_MAX_DURATION_MS.
     */
    private fun checkForTapSequence() {
        if (tapBuffer.size < 5) return

        val now = System.currentTimeMillis()
        if (now - lastTapSequenceTimeMs < TAP_SEQUENCE_COOLDOWN_MS) return

        // Find peaks: local maxima within ±150ms window, magnitude ≥ TAP_THRESHOLD
        val peaks = mutableListOf<TapEvent>()
        for (i in tapBuffer.indices) {
            val event = tapBuffer[i]
            if (event.magnitude < TAP_THRESHOLD) continue

            var isLocalMax = true
            for (j in tapBuffer.indices) {
                if (i == j) continue
                val other = tapBuffer[j]
                if (kotlin.math.abs(event.wallClockMs - other.wallClockMs) <= 150L) {
                    if (other.magnitude > event.magnitude) {
                        isLocalMax = false
                        break
                    }
                }
            }
            if (isLocalMax) peaks.add(event)
        }

        // Deduplicate peaks within TAP_MIN_GAP_MS
        val dedupedPeaks = mutableListOf<TapEvent>()
        for (peak in peaks.sortedBy { it.wallClockMs }) {
            if (dedupedPeaks.isEmpty() || peak.wallClockMs - dedupedPeaks.last().wallClockMs >= TAP_MIN_GAP_MS) {
                dedupedPeaks.add(peak)
            }
        }

        if (dedupedPeaks.size < 5) return

        // Check for 5 consecutive peaks with valid inter-peak gaps
        for (i in 0..dedupedPeaks.size - 5) {
            val window = dedupedPeaks.subList(i, i + 5)
            val totalDuration = window.last().wallClockMs - window.first().wallClockMs
            if (totalDuration > TAP_SEQUENCE_MAX_DURATION_MS) continue

            var validGaps = true
            for (j in 0 until 4) {
                val gap = window[j + 1].wallClockMs - window[j].wallClockMs
                if (gap < TAP_MIN_GAP_MS || gap > TAP_MAX_GAP_MS) {
                    validGaps = false
                    break
                }
            }

            if (validGaps) {
                lastTapSequenceTimeMs = now
                val entry = "TAP_SEQ: Ts=$now, T1=${window[0].sensorNanos},T2=${window[1].sensorNanos},T3=${window[2].sensorNanos},T4=${window[3].sensorNanos},T5=${window[4].sensorNanos}"
                sessionTimeline.add(entry)
                Log.d(TAG, "🔔 Tap sequence detected: $entry")
                tapBuffer.clear()
                return
            }
        }
    }
}
