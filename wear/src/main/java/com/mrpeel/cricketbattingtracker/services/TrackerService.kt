package com.mrpeel.cricketbattingtracker.services

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
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
    
    private var wakeLock: PowerManager.WakeLock? = null
    private val swingDetector = SwingDetector()
    private lateinit var dataSyncManager: DataSyncManager
    private lateinit var healthServicesManager: HealthServicesManager
    
    // Store timeline data
    private val sessionTimeline = mutableListOf<String>()
    private var shouldDiscard = false

    // Background Sensor Handling Thread
    private var sensorThread: android.os.HandlerThread? = null
    private var sensorHandler: android.os.Handler? = null

    // Dynamic Raw Debug Logging for Full Watch Sensor Stack
    private var enableRawLogging = false
    private var sessionStartNanos: Long = 0L

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
        SensorConfig(Sensor.TYPE_ROTATION_VECTOR, "WatchOrientation.csv", "time,seconds_elapsed,qx,qy,qz,qw\n"),
        SensorConfig(Sensor.TYPE_GAME_ROTATION_VECTOR, "WatchGameOrientation.csv", "time,seconds_elapsed,qx,qy,qz,qw\n"),
        SensorConfig(Sensor.TYPE_STEP_DETECTOR, "WatchSteps.csv", "time,seconds_elapsed\n"),
        SensorConfig(Sensor.TYPE_HEART_RATE, "WatchHeartRate.csv", "time,seconds_elapsed,bpm\n"),
        SensorConfig(Sensor.TYPE_LINEAR_ACCELERATION, "WatchLinearAcceleration.csv", "time,seconds_elapsed,x,y,z\n"),
        SensorConfig(Sensor.TYPE_MAGNETIC_FIELD, "WatchMagnetometer.csv", "time,seconds_elapsed,x,y,z\n"),
        SensorConfig(Sensor.TYPE_MAGNETIC_FIELD_UNCALIBRATED, "WatchMagnetometerUncalibrated.csv", "time,seconds_elapsed,x,y,z,bias_x,bias_y,bias_z\n"),
        SensorConfig(Sensor.TYPE_GYROSCOPE_UNCALIBRATED, "WatchGyroscopeUncalibrated.csv", "time,seconds_elapsed,x,y,z,bias_x,bias_y,bias_z\n"),
        SensorConfig(Sensor.TYPE_ACCELEROMETER_UNCALIBRATED, "WatchAccelerometerUncalibrated.csv", "time,seconds_elapsed,x,y,z,bias_x,bias_y,bias_z\n"),
        SensorConfig(Sensor.TYPE_PRESSURE, "WatchBarometer.csv", "time,seconds_elapsed,pressure\n"),
        SensorConfig(Sensor.TYPE_GEOMAGNETIC_ROTATION_VECTOR, "WatchGeomagneticOrientation.csv", "time,seconds_elapsed,qx,qy,qz,qw\n"),
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
        // Used to definitively detect walking and suppress false facing-up detection
        stepDetectorSensor   = sensorManager.getDefaultSensor(Sensor.TYPE_STEP_DETECTOR)
        heartRateSensor      = sensorManager.getDefaultSensor(Sensor.TYPE_HEART_RATE)

        if (accelSensor == null)        Log.w(TAG, "Hardware Accelerometer is NOT available!")
        if (heartRateSensor == null)    Log.w(TAG, "Hardware Heart Rate Sensor is NOT available!")
        if (gyroSensor == null)         Log.w(TAG, "Hardware Gyroscope is NOT available!")
        if (gravitySensor == null)      Log.w(TAG, "Hardware Gravity Sensor is NOT available (SwingDetector will estimate gravity from Accelerometer)")
        if (rotationSensor == null)     Log.w(TAG, "Hardware Rotation Vector is NOT available!")
        if (gameRotationSensor == null) Log.w(TAG, "Game Rotation Vector NOT available — bat orientation will use standard Rotation Vector (magnetometer subject to interference)")
        if (stepDetectorSensor == null) Log.w(TAG, "Step Detector NOT available — walking discrimination will fall back to accel cadence heuristic")
        
        // Setup wake lock to keep recording while screen is off
        val powerManager = getSystemService(Context.POWER_SERVICE) as PowerManager
        wakeLock = powerManager.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "CricketTracker::BattingWakeLock")
        
        swingDetector.onShotDetected = { shot ->
            val shotTime = System.currentTimeMillis()
            Log.d(TAG, "Shot detected! ${shot.shotType}, Speed: ${shot.speedKmh}, Hit: ${shot.isHit}, SS: ${shot.sweetSpot}")
            sessionTimeline.add("Shot: Type=${shot.shotType}, Spd=${shot.speedKmh}, Hit=${shot.isHit}, Acc=${shot.peakAccel}, SS=${shot.sweetSpot}, Eff=${shot.efficiency}, BL=${shot.backliftAngle}, FT=${shot.followThroughAngle}, ItMs=${shot.impactTimeMs}, Wr=${shot.wristRollDeg}, Ts=$shotTime")
            SessionManager.addShot(shot)
        }
        
        swingDetector.onFacingUpChanged = { isFacingUp ->
            SessionManager.setFacingUp(isFacingUp)
        }
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
           enableRawLogging = intent?.getBooleanExtra("ENABLE_RAW_LOGGING", false) ?: false
        if (enableRawLogging) {
            try {
                val ts = java.text.SimpleDateFormat("yyyy-MM-dd_HH-mm-ss", java.util.Locale.US).format(java.util.Date())
                val sessionDir = File(getExternalFilesDir(null), "sessions/session-$ts")
                sessionDir.mkdirs()

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
        }
        if (sessionTimeline.isEmpty()) {
            val startTime = System.currentTimeMillis()
            sessionTimeline.add("SYSTEM_START: Ts=$startTime")
            Log.d(TAG, "Recording system start event: $startTime")
        }

        SessionManager.setTracking(true)
        startForegroundService()
        wakeLock?.acquire(3 * 60 * 60 * 1000L) // maximum 3 hours
        
        // Register sensor listeners on background thread handler
        if (enableRawLogging) {
            // Register ALL supported configurations for full stack diagnostics
            for (config in sensorConfigs) {
                val sensor = sensorManager.getDefaultSensor(config.type)
                if (sensor != null) {
                    val delay = if (config.type == Sensor.TYPE_STEP_DETECTOR || 
                                     config.type == Sensor.TYPE_HEART_RATE ||
                                     config.type == Sensor.TYPE_STEP_COUNTER) {
                        SensorManager.SENSOR_DELAY_NORMAL
                    } else {
                        SensorManager.SENSOR_DELAY_GAME
                    }
                    sensorManager.registerListener(this, sensor, delay, 0, sensorHandler)
                }
            }
        } else {
            // Register ONLY the subset required for real-time SwingDetector to save battery
            accelSensor?.let        { sensorManager.registerListener(this, it, SensorManager.SENSOR_DELAY_GAME, 0, sensorHandler) }
            gyroSensor?.let         { sensorManager.registerListener(this, it, SensorManager.SENSOR_DELAY_GAME, 0, sensorHandler) }
            gravitySensor?.let      { sensorManager.registerListener(this, it, SensorManager.SENSOR_DELAY_GAME, 0, sensorHandler) }
            rotationSensor?.let     { sensorManager.registerListener(this, it, SensorManager.SENSOR_DELAY_GAME, 0, sensorHandler) }
            gameRotationSensor?.let { sensorManager.registerListener(this, it, SensorManager.SENSOR_DELAY_GAME, 0, sensorHandler) }
            stepDetectorSensor?.let { sensorManager.registerListener(this, it, SensorManager.SENSOR_DELAY_NORMAL, 0, sensorHandler) }
            heartRateSensor?.let    { sensorManager.registerListener(this, it, SensorManager.SENSOR_DELAY_NORMAL, 0, sensorHandler) }
        }
        
        Log.d(TAG, "Service Started, tracking sensors")
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
    }

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onSensorChanged(event: SensorEvent?) {
        if (event == null) return
        
        val type = event.sensor.type
        val ts = event.timestamp
        val vals = event.values

        // Standard real-time sensor processing for state machine
        when (type) {
            Sensor.TYPE_ACCELEROMETER -> swingDetector.processAccel(vals, ts)
            Sensor.TYPE_GYROSCOPE     -> swingDetector.processGyro(vals, ts)
            Sensor.TYPE_GRAVITY       -> swingDetector.processGravity(vals, ts)
            Sensor.TYPE_GAME_ROTATION_VECTOR -> swingDetector.processRotation(vals, ts)
            Sensor.TYPE_STEP_DETECTOR -> {
                swingDetector.processStep(ts)
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
}
