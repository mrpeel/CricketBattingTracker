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

    // Hybrid Raw Debug Logging
    private var enableRawLogging = false
    private var accWriter: BufferedWriter? = null
    private var gyroWriter: BufferedWriter? = null
    private var gravityWriter: BufferedWriter? = null
    private var rotationWriter: BufferedWriter? = null
    private var gameRotationWriter: BufferedWriter? = null
    private var stepWriter: BufferedWriter? = null
    private var sessionStartNanos: Long = 0L

    override fun onCreate() {
        super.onCreate()
        Log.d(TAG, "Service Created")
        
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

                accWriter = File(sessionDir, "WatchAccelerometer.csv").bufferedWriter()
                accWriter?.write("time,seconds_elapsed,x,y,z\n")

                gyroWriter = File(sessionDir, "WatchGyroscope.csv").bufferedWriter()
                gyroWriter?.write("time,seconds_elapsed,x,y,z\n")

                gravityWriter = File(sessionDir, "WatchGravity.csv").bufferedWriter()
                gravityWriter?.write("time,seconds_elapsed,x,y,z\n")

                // Standard Rotation Vector (with magnetometer) — kept for long-term reference
                rotationWriter = File(sessionDir, "WatchOrientation.csv").bufferedWriter()
                rotationWriter?.write("time,seconds_elapsed,qx,qy,qz,qw\n")

                // Game Rotation Vector (no magnetometer) — preferred for short-term bat orientation
                gameRotationWriter = File(sessionDir, "WatchGameOrientation.csv").bufferedWriter()
                gameRotationWriter?.write("time,seconds_elapsed,qx,qy,qz,qw\n")

                // Step events (timestamp only)
                stepWriter = File(sessionDir, "WatchSteps.csv").bufferedWriter()
                stepWriter?.write("time,seconds_elapsed\n")

                Log.d(TAG, "Raw Logging ENABLED to \${sessionDir.absolutePath}")
            } catch (e: Exception) {
                Log.e(TAG, "Failed to prep log writers: \${e.message}")
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
        
        // SENSOR_DELAY_GAME = 50Hz, explicit 0 latency out of caution against Wear OS suspending listeners
        accelSensor?.let        { sensorManager.registerListener(this, it, SensorManager.SENSOR_DELAY_GAME, 0) }
        gyroSensor?.let         { sensorManager.registerListener(this, it, SensorManager.SENSOR_DELAY_GAME, 0) }
        gravitySensor?.let      { sensorManager.registerListener(this, it, SensorManager.SENSOR_DELAY_GAME, 0) }
        rotationSensor?.let     { sensorManager.registerListener(this, it, SensorManager.SENSOR_DELAY_GAME, 0) }
        // Game Rotation Vector: no magnetometer — preferred for bat orientation (immunity to field distortion)
        gameRotationSensor?.let { sensorManager.registerListener(this, it, SensorManager.SENSOR_DELAY_GAME, 0) }
        // Step Detector: fires per foot-strike on hardware DSP (near-zero power)
        // SENSOR_DELAY_NORMAL is correct — the sensor fires on events, not on a poll interval
        stepDetectorSensor?.let { sensorManager.registerListener(this, it, SensorManager.SENSOR_DELAY_NORMAL, 0) }
        heartRateSensor?.let    { sensorManager.registerListener(this, it, SensorManager.SENSOR_DELAY_NORMAL, 0) }
        
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
        if (enableRawLogging) {
            try {
                accWriter?.close()
                gyroWriter?.close()
                gravityWriter?.close()
                rotationWriter?.close()
                gameRotationWriter?.close()
                stepWriter?.close()
            } catch (e: Exception) {}
        }
    }

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onSensorChanged(event: SensorEvent?) {
        if (event == null) return
        
        val type = event.sensor.type
        val ts = event.timestamp
        val vals = event.values

        when (type) {
            Sensor.TYPE_ACCELEROMETER -> swingDetector.processAccel(vals, ts)
            Sensor.TYPE_GYROSCOPE     -> swingDetector.processGyro(vals, ts)
            Sensor.TYPE_GRAVITY       -> swingDetector.processGravity(vals, ts)
            // ROTATION_VECTOR kept for reference only — SwingDetector uses GAME_ROTATION_VECTOR
            Sensor.TYPE_ROTATION_VECTOR      -> { /* logged below; not fed to SwingDetector */ }
            // GAME_ROTATION_VECTOR: no magnetometer — primary source for bat orientation in SwingDetector
            Sensor.TYPE_GAME_ROTATION_VECTOR -> swingDetector.processRotation(vals, ts)
            // STEP_DETECTOR: single event per foot-strike; used to detect walking and break facing-up gate
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

        if (enableRawLogging) {
            if (sessionStartNanos == 0L) sessionStartNanos = ts
            val elapsedSecs = (ts - sessionStartNanos) / 1_000_000_000.0

            fun quatW(v: FloatArray): Float =
                if (v.size > 3) v[3]
                else kotlin.math.sqrt(kotlin.math.max(0.0f, 1.0f - v[0]*v[0] - v[1]*v[1] - v[2]*v[2]))

            try {
                when (type) {
                    Sensor.TYPE_ACCELEROMETER ->
                        accWriter?.write(String.format(java.util.Locale.US, "%d,%.6f,%.6f,%.6f,%.6f\n", ts, elapsedSecs, vals[0], vals[1], vals[2]))
                    Sensor.TYPE_GYROSCOPE ->
                        gyroWriter?.write(String.format(java.util.Locale.US, "%d,%.6f,%.6f,%.6f,%.6f\n", ts, elapsedSecs, vals[0], vals[1], vals[2]))
                    Sensor.TYPE_GRAVITY ->
                        gravityWriter?.write(String.format(java.util.Locale.US, "%d,%.6f,%.6f,%.6f,%.6f\n", ts, elapsedSecs, vals[0], vals[1], vals[2]))
                    Sensor.TYPE_ROTATION_VECTOR ->
                        rotationWriter?.write(String.format(java.util.Locale.US, "%d,%.6f,%.6f,%.6f,%.6f,%.6f\n", ts, elapsedSecs, vals[0], vals[1], vals[2], quatW(vals)))
                    Sensor.TYPE_GAME_ROTATION_VECTOR ->
                        gameRotationWriter?.write(String.format(java.util.Locale.US, "%d,%.6f,%.6f,%.6f,%.6f,%.6f\n", ts, elapsedSecs, vals[0], vals[1], vals[2], quatW(vals)))
                    Sensor.TYPE_STEP_DETECTOR ->
                        stepWriter?.write(String.format(java.util.Locale.US, "%d,%.6f\n", ts, elapsedSecs))
                }
            } catch (e: Exception) {}
        }
    }

    override fun onAccuracyChanged(sensor: Sensor?, accuracy: Int) {
        // Not used
    }
}
