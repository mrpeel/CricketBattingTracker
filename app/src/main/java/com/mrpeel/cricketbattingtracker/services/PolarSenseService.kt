package com.mrpeel.cricketbattingtracker.services

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.Service
import android.content.Context
import android.content.Intent
import android.os.IBinder
import android.util.Log
import java.io.BufferedOutputStream
import java.io.File
import java.io.FileOutputStream
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

/**
 * Foreground service for Polar Sense BLE streaming.
 * Writes raw ACC and GYRO data to binary files (.bin) in app-specific storage.
 * Each record is 28 bytes: PhoneMS (Long, 8B) + SensorNS (Long, 8B) + X (Float, 4B) + Y (Float, 4B) + Z (Float, 4B)
 */
class PolarSenseService : Service() {
    companion object {
        private const val TAG = "PolarSenseService"
        private const val CHANNEL_ID = "polar_sense_channel"
        private const val NOTIFICATION_ID = 4001
        const val ACTION_START = "POLAR_START"
        const val ACTION_STOP = "POLAR_STOP"
    }

    private var accStream: BufferedOutputStream? = null
    private var gyroStream: BufferedOutputStream? = null
    private var magStream: BufferedOutputStream? = null
    private var sessionDir: File? = null

    override fun onCreate() {
        super.onCreate()
        createNotificationChannel()
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        when (intent?.action) {
            ACTION_START -> {
                startForegroundWithNotification()
                startBinaryWriting()
                PolarSenseManager.initialize(this)
                PolarSenseManager.connect(this)
            }
            ACTION_STOP -> {
                val shouldDiscard = intent.getBooleanExtra("discard", false)
                if (shouldDiscard) {
                    discardSessionData()
                } else {
                    stopBinaryWriting()
                }
                PolarSenseManager.stopStreaming()
                PolarSenseManager.disconnect()
                stopForeground(STOP_FOREGROUND_REMOVE)
                stopSelf()
            }
            else -> {
                startForegroundWithNotification()
                startBinaryWriting()
                PolarSenseManager.initialize(this)
                PolarSenseManager.connect(this)
            }
        }
        return START_STICKY
    }

    private fun startBinaryWriting() {
        val timestamp = SimpleDateFormat("yyyy-MM-dd_HH-mm-ss", Locale.US).format(Date())
        val dir = File(getExternalFilesDir("polar_sessions"), "polar_session_$timestamp")
        dir.mkdirs()
        sessionDir = dir

        val accFile = File(dir, "PolarAccelerometer.bin")
        accStream = BufferedOutputStream(FileOutputStream(accFile))

        val gyroFile = File(dir, "PolarGyroscope.bin")
        gyroStream = BufferedOutputStream(FileOutputStream(gyroFile))

        val magFile = File(dir, "PolarMagnetometer.bin")
        magStream = BufferedOutputStream(FileOutputStream(magFile))

        // Wire up callbacks from PolarSenseManager
        val buffer = ByteBuffer.allocate(28).order(ByteOrder.LITTLE_ENDIAN)

        PolarSenseManager.onAccSample = { phoneMs, sensorNs, x, y, z ->
            try {
                buffer.clear()
                buffer.putLong(phoneMs)
                buffer.putLong(sensorNs)
                buffer.putFloat(x.toFloat())
                buffer.putFloat(y.toFloat())
                buffer.putFloat(z.toFloat())
                accStream?.write(buffer.array())
            } catch (e: Exception) {
                Log.e(TAG, "ACC write error: ${e.message}")
            }
        }

        PolarSenseManager.onGyroSample = { phoneMs, sensorNs, x, y, z ->
            try {
                buffer.clear()
                buffer.putLong(phoneMs)
                buffer.putLong(sensorNs)
                buffer.putFloat(x)
                buffer.putFloat(y)
                buffer.putFloat(z)
                gyroStream?.write(buffer.array())
            } catch (e: Exception) {
                Log.e(TAG, "GYRO write error: ${e.message}")
            }
        }

        PolarSenseManager.onMagSample = { phoneMs, sensorNs, x, y, z ->
            try {
                buffer.clear()
                buffer.putLong(phoneMs)
                buffer.putLong(sensorNs)
                buffer.putFloat(x)
                buffer.putFloat(y)
                buffer.putFloat(z)
                magStream?.write(buffer.array())
            } catch (e: Exception) {
                Log.e(TAG, "MAG write error: ${e.message}")
            }
        }

        Log.d(TAG, "Binary streams opened: $dir")
    }

    private fun stopBinaryWriting(compress: Boolean = true) {
        PolarSenseManager.onAccSample = null
        PolarSenseManager.onGyroSample = null
        PolarSenseManager.onMagSample = null

        try {
            accStream?.flush()
            accStream?.close()
        } catch (e: Exception) {
            Log.e(TAG, "Error closing ACC stream: ${e.message}")
        }
        accStream = null

        try {
            gyroStream?.flush()
            gyroStream?.close()
        } catch (e: Exception) {
            Log.e(TAG, "Error closing GYRO stream: ${e.message}")
        }
        gyroStream = null

        try {
            magStream?.flush()
            magStream?.close()
        } catch (e: Exception) {
            Log.e(TAG, "Error closing MAG stream: ${e.message}")
        }
        magStream = null

        Log.d(TAG, "Binary streams closed. Session dir: ${sessionDir?.absolutePath}")

        if (compress) {
            sessionDir?.let { dir ->
                if (dir.exists()) {
                    val zipFile = File(dir.parentFile, "${dir.name}.zip")
                    try {
                        zipDirectory(dir, zipFile)
                        dir.deleteRecursively()
                        Log.d(TAG, "Compressed Polar session folder into: ${zipFile.absolutePath}")
                    } catch (e: java.lang.Exception) {
                        Log.e(TAG, "Failed to compress Polar session: ${e.message}")
                    }
                }
            }
        }
    }

    fun discardSessionData() {
        stopBinaryWriting(compress = false)
        sessionDir?.let { dir ->
            if (dir.exists()) {
                dir.deleteRecursively()
                Log.d(TAG, "Discarded Polar session data: ${dir.absolutePath}")
            }
            val zipFile = File(dir.parentFile, "${dir.name}.zip")
            if (zipFile.exists()) {
                zipFile.delete()
            }
        }
        sessionDir = null
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

    private fun startForegroundWithNotification() {
        val notification = Notification.Builder(this, CHANNEL_ID)
            .setContentTitle("Polar Sense Streaming")
            .setContentText("Bottom hand sensor — 52Hz ACC + GYRO (Binary)")
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
        stopBinaryWriting()
        PolarSenseManager.stopStreaming()
        PolarSenseManager.disconnect()
        super.onDestroy()
    }
}
