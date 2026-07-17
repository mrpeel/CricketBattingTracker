package com.mrpeel.cricketbattingtracker.services

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.Service
import android.content.Context
import android.content.Intent
import android.os.IBinder
import android.util.Log
import java.io.BufferedWriter
import java.io.File
import java.io.FileWriter
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

/**
 * Foreground service for Polar Sense BLE streaming.
 * Writes raw ACC and GYRO data to CSV files in app-specific storage.
 * Lifecycle is managed by PolarSenseManager; the service just provides
 * the foreground notification and CSV file I/O.
 */
class PolarSenseService : Service() {
    companion object {
        private const val TAG = "PolarSenseService"
        private const val CHANNEL_ID = "polar_sense_channel"
        private const val NOTIFICATION_ID = 4001
        const val ACTION_START = "POLAR_START"
        const val ACTION_STOP = "POLAR_STOP"
    }

    private var accWriter: BufferedWriter? = null
    private var gyroWriter: BufferedWriter? = null
    private var magWriter: BufferedWriter? = null
    private var sessionDir: File? = null

    override fun onCreate() {
        super.onCreate()
        createNotificationChannel()
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        when (intent?.action) {
            ACTION_START -> {
                startForegroundWithNotification()
                startCsvWriting()
                PolarSenseManager.initialize(this)
                PolarSenseManager.connect(this)
            }
            ACTION_STOP -> {
                val shouldDiscard = intent.getBooleanExtra("discard", false)
                if (shouldDiscard) {
                    discardSessionData()
                } else {
                    stopCsvWriting()
                }
                PolarSenseManager.stopStreaming()
                PolarSenseManager.disconnect()
                stopForeground(STOP_FOREGROUND_REMOVE)
                stopSelf()
            }
            else -> {
                // Default: start
                startForegroundWithNotification()
                startCsvWriting()
                PolarSenseManager.initialize(this)
                PolarSenseManager.connect(this)
            }
        }
        return START_STICKY
    }

    private fun startCsvWriting() {
        val timestamp = SimpleDateFormat("yyyy-MM-dd_HH-mm-ss", Locale.US).format(Date())
        val dir = File(getExternalFilesDir("polar_sessions"), "polar_session_$timestamp")
        dir.mkdirs()
        sessionDir = dir

        // ACC CSV — semicolon-delimited for Polar Sensor Logger compatibility
        val accFile = File(dir, "PolarAccelerometer.csv")
        accWriter = BufferedWriter(FileWriter(accFile))
        accWriter?.write("Phone timestamp;sensor timestamp [ns];X [mg];Y [mg];Z [mg]")
        accWriter?.newLine()

        // GYRO CSV — semicolon-delimited
        val gyroFile = File(dir, "PolarGyroscope.csv")
        gyroWriter = BufferedWriter(FileWriter(gyroFile))
        gyroWriter?.write("Phone timestamp;sensor timestamp [ns];X [dps];Y [dps];Z [dps]")
        gyroWriter?.newLine()

        // MAG CSV — semicolon-delimited
        val magFile = File(dir, "PolarMagnetometer.csv")
        magWriter = BufferedWriter(FileWriter(magFile))
        magWriter?.write("Phone timestamp;sensor timestamp [ns];X [uT];Y [uT];Z [uT]")
        magWriter?.newLine()

        // Wire up callbacks from PolarSenseManager
        PolarSenseManager.onAccSample = { phoneMs, sensorNs, x, y, z ->
            try {
                val phoneTs = formatPhoneTimestamp(phoneMs)
                accWriter?.write("$phoneTs;$sensorNs;$x;$y;$z")
                accWriter?.newLine()
            } catch (e: Exception) {
                Log.e(TAG, "ACC write error: ${e.message}")
            }
        }

        PolarSenseManager.onGyroSample = { phoneMs, sensorNs, x, y, z ->
            try {
                val phoneTs = formatPhoneTimestamp(phoneMs)
                gyroWriter?.write("$phoneTs;$sensorNs;${String.format(Locale.US, "%.6f", x)};${String.format(Locale.US, "%.6f", y)};${String.format(Locale.US, "%.6f", z)}")
                gyroWriter?.newLine()
            } catch (e: Exception) {
                Log.e(TAG, "GYRO write error: ${e.message}")
            }
        }

        PolarSenseManager.onMagSample = { phoneMs, sensorNs, x, y, z ->
            try {
                val phoneTs = formatPhoneTimestamp(phoneMs)
                magWriter?.write("$phoneTs;$sensorNs;${String.format(Locale.US, "%.6f", x)};${String.format(Locale.US, "%.6f", y)};${String.format(Locale.US, "%.6f", z)}")
                magWriter?.newLine()
            } catch (e: Exception) {
                Log.e(TAG, "MAG write error: ${e.message}")
            }
        }

        Log.d(TAG, "CSV writers opened: $dir")
    }

    private fun stopCsvWriting() {
        PolarSenseManager.onAccSample = null
        PolarSenseManager.onGyroSample = null
        PolarSenseManager.onMagSample = null

        try {
            accWriter?.flush()
            accWriter?.close()
        } catch (e: Exception) {
            Log.e(TAG, "Error closing ACC writer: ${e.message}")
        }
        accWriter = null

        try {
            gyroWriter?.flush()
            gyroWriter?.close()
        } catch (e: Exception) {
            Log.e(TAG, "Error closing GYRO writer: ${e.message}")
        }
        gyroWriter = null

        try {
            magWriter?.flush()
            magWriter?.close()
        } catch (e: Exception) {
            Log.e(TAG, "Error closing MAG writer: ${e.message}")
        }
        magWriter = null

        Log.d(TAG, "CSV writers closed. Session dir: ${sessionDir?.absolutePath}")
    }

    /** Delete session data files (for DISCARD flow). */
    fun discardSessionData() {
        stopCsvWriting()
        sessionDir?.let { dir ->
            if (dir.exists()) {
                dir.deleteRecursively()
                Log.d(TAG, "Discarded Polar session data: ${dir.absolutePath}")
            }
        }
        sessionDir = null
    }

    private fun formatPhoneTimestamp(epochMs: Long): String {
        return SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss.SSS", Locale.US).format(Date(epochMs))
    }

    private fun startForegroundWithNotification() {
        val notification = Notification.Builder(this, CHANNEL_ID)
            .setContentTitle("Polar Sense Streaming")
            .setContentText("Bottom hand sensor — 52Hz ACC + GYRO")
            .setSmallIcon(android.R.drawable.stat_sys_data_bluetooth)
            .setOngoing(true)
            .build()

        startForeground(NOTIFICATION_ID, notification)
    }

    private fun createNotificationChannel() {
        val channel = NotificationChannel(
            CHANNEL_ID,
            "Polar Sense Streaming",
            NotificationManager.IMPORTANCE_LOW
        ).apply {
            description = "Ongoing notification while streaming data from Polar Sense"
        }
        val manager = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        manager.createNotificationChannel(channel)
    }

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onDestroy() {
        stopCsvWriting()
        PolarSenseManager.stopStreaming()
        PolarSenseManager.disconnect()
        super.onDestroy()
    }
}
