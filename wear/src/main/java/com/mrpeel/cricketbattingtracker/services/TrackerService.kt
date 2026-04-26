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
    
    private var wakeLock: PowerManager.WakeLock? = null
    private val swingDetector = SwingDetector()
    private lateinit var dataSyncManager: DataSyncManager
    private lateinit var healthServicesManager: HealthServicesManager
    
    // Store timeline data
    private val sessionTimeline = mutableListOf<String>()

    // Hybrid Raw Debug Logging
    private var enableRawLogging = false
    private var accWriter: BufferedWriter? = null
    private var gyroWriter: BufferedWriter? = null
    private var sessionStartNanos: Long = 0L

    override fun onCreate() {
        super.onCreate()
        Log.d(TAG, "Service Created")
        
        dataSyncManager = DataSyncManager(this)
        healthServicesManager = HealthServicesManager(this)
        healthServicesManager.startTracking()
        sensorManager = getSystemService(Context.SENSOR_SERVICE) as SensorManager
        accelSensor = sensorManager.getDefaultSensor(Sensor.TYPE_ACCELEROMETER)
        gyroSensor = sensorManager.getDefaultSensor(Sensor.TYPE_GYROSCOPE)
        
        // Setup wake lock to keep recording while screen is off
        val powerManager = getSystemService(Context.POWER_SERVICE) as PowerManager
        wakeLock = powerManager.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "CricketTracker::BattingWakeLock")
        
        swingDetector.onShotDetected = { shot ->
            Log.d(TAG, "Shot detected! Speed: ${shot.speedKmh}, Hit: ${shot.isHit}, SS: ${shot.sweetSpot}")
            sessionTimeline.add("Shot: Spd=${shot.speedKmh}, Hit=${shot.isHit}, Acc=${shot.peakAccel}, SS=${shot.sweetSpot}")
            SessionManager.addShot(shot)
        }
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        if (intent?.action == "STOP_TRACKING") {
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
                accWriter?.write("seconds_elapsed,x,y,z\n")
                
                gyroWriter = File(sessionDir, "WatchGyroscope.csv").bufferedWriter()
                gyroWriter?.write("seconds_elapsed,x,y,z\n")
                
                Log.d(TAG, "Raw Logging ENABLED to \${sessionDir.absolutePath}")
            } catch (e: Exception) {
                Log.e(TAG, "Failed to prep log writers: \${e.message}")
            }
        }
        
        SessionManager.setTracking(true)
        startForegroundService()
        wakeLock?.acquire(3 * 60 * 60 * 1000L) // maximum 3 hours
        
        // SENSOR_DELAY_GAME = 50Hz, explicit 0 latency out of caution against Wear OS suspending listeners
        sensorManager.registerListener(this, accelSensor, SensorManager.SENSOR_DELAY_GAME, 0)
        sensorManager.registerListener(this, gyroSensor, SensorManager.SENSOR_DELAY_GAME, 0)
        
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
        healthServicesManager.stopTracking()
        dataSyncManager.syncTimelineToPhone(sessionTimeline)
        wakeLock?.let {
            if (it.isHeld) {
                it.release()
            }
        }
        if (enableRawLogging) {
            try {
                accWriter?.close()
                gyroWriter?.close()
            } catch (e: Exception) {}
        }
        
        // Expose timeline to ADB for headless integration testing
        try {
            val timelineFile = File(getExternalFilesDir(null), "latest_timeline.txt")
            timelineFile.writeText(sessionTimeline.joinToString("\n"))
        } catch (e: Exception) {}
    }

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onSensorChanged(event: SensorEvent?) {
        if (event == null) return
        
        val type = event.sensor.type
        val ts = event.timestamp
        val vals = event.values

        when (type) {
            Sensor.TYPE_ACCELEROMETER -> swingDetector.processAccel(vals, ts)
            Sensor.TYPE_GYROSCOPE -> swingDetector.processGyro(vals, ts)
        }

        if (enableRawLogging) {
            if (sessionStartNanos == 0L) sessionStartNanos = ts
            val elapsedSecs = (ts - sessionStartNanos) / 1_000_000_000.0
            val line = String.format(java.util.Locale.US, "%.6f,%.6f,%.6f,%.6f\n", elapsedSecs, vals[0], vals[1], vals[2])
            
            try {
                if (type == Sensor.TYPE_ACCELEROMETER) accWriter?.write(line)
                else if (type == Sensor.TYPE_GYROSCOPE) gyroWriter?.write(line)
            } catch (e: Exception) {}
        }
    }

    override fun onAccuracyChanged(sensor: Sensor?, accuracy: Int) {
        // Not used
    }
}
