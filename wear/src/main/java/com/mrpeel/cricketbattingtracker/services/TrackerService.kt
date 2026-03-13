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
        
        swingDetector.onShotDetected = { angular, impact ->
            Log.d(TAG, "Shot detected! Angular: $angular, Impact: $impact")
            sessionTimeline.add("Shot detected: Ang=$angular, Imp=$impact")
            // Here we would typically write to local database or queue for DataLayer API
        }
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        if (intent?.action == "STOP_TRACKING") {
            stopSelf()
            return START_NOT_STICKY
        }
        
        startForegroundService()
        wakeLock?.acquire(3 * 60 * 60 * 1000L) // maximum 3 hours
        
        // SENSOR_DELAY_GAME = 50Hz, good for sports mechanics without destroying battery like FASTEST
        sensorManager.registerListener(this, accelSensor, SensorManager.SENSOR_DELAY_GAME)
        sensorManager.registerListener(this, gyroSensor, SensorManager.SENSOR_DELAY_GAME)
        
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

        val notification: Notification = NotificationCompat.Builder(this, channelId)
            .setContentTitle("Cricket Tracking Active")
            .setContentText("Recording batting session...")
            .setContentIntent(pendingIntent)
            .setOngoing(true)
            .build()

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
        // Save timeline data or initiate sync
    }

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onSensorChanged(event: SensorEvent?) {
        if (event == null) return
        
        when (event.sensor.type) {
            Sensor.TYPE_ACCELEROMETER -> swingDetector.processAccel(event)
            Sensor.TYPE_GYROSCOPE -> swingDetector.processGyro(event)
        }
    }

    override fun onAccuracyChanged(sensor: Sensor?, accuracy: Int) {
        // Not used
    }
}
