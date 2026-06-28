package com.mrpeel.cricketbattingtracker.services

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.Service
import android.content.Intent
import android.media.AudioDeviceInfo
import android.media.AudioManager
import android.os.Handler
import android.os.IBinder
import android.os.Looper
import android.util.Log
import androidx.camera.core.CameraSelector
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.camera.video.FileOutputOptions
import androidx.camera.video.Quality
import androidx.camera.video.QualitySelector
import androidx.camera.video.Recorder
import androidx.camera.video.Recording
import androidx.camera.video.VideoCapture
import androidx.camera.video.VideoRecordEvent
import androidx.core.content.ContextCompat
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleOwner
import androidx.lifecycle.LifecycleRegistry
import java.io.File
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.concurrent.ExecutorService
import java.util.concurrent.Executors

class VideoRecordService : Service(), LifecycleOwner {

    companion object {
        const val TAG = "VideoRecordService"
        const val ACTION_START   = "com.mrpeel.VIDEO_START"
        const val ACTION_STOP    = "com.mrpeel.VIDEO_STOP"
        const val ACTION_DISCARD = "com.mrpeel.VIDEO_DISCARD"
        private const val NOTIF_CHANNEL = "video_record"
        private const val NOTIF_ID = 2002
    }

    // ── Lifecycle (required by ProcessCameraProvider) ──────────────────────────
    private val _lifecycle = LifecycleRegistry(this)
    override val lifecycle: Lifecycle get() = _lifecycle

    private var cameraExecutor: ExecutorService = Executors.newSingleThreadExecutor()
    private var activeRecording: Recording? = null
    private var outputFile: File? = null
    private var startEpoch = 0L
    private val ticker = Handler(Looper.getMainLooper())
    private val tickRunnable = object : Runnable {
        override fun run() {
            val elapsed = (System.currentTimeMillis() - startEpoch) / 1000
            VideoRecordManager.updateElapsedSeconds(elapsed)
            ticker.postDelayed(this, 1_000)
        }
    }

    override fun onCreate() {
        super.onCreate()
        _lifecycle.handleLifecycleEvent(Lifecycle.Event.ON_CREATE)
        _lifecycle.handleLifecycleEvent(Lifecycle.Event.ON_START)
        _lifecycle.handleLifecycleEvent(Lifecycle.Event.ON_RESUME)
        createNotificationChannel()
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        when (intent?.action) {
            ACTION_START   -> startVideoRecording()
            ACTION_STOP    -> stopVideoRecording(discard = false)
            ACTION_DISCARD -> stopVideoRecording(discard = true)
        }
        return START_NOT_STICKY
    }

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onDestroy() {
        _lifecycle.handleLifecycleEvent(Lifecycle.Event.ON_PAUSE)
        _lifecycle.handleLifecycleEvent(Lifecycle.Event.ON_STOP)
        _lifecycle.handleLifecycleEvent(Lifecycle.Event.ON_DESTROY)
        ticker.removeCallbacks(tickRunnable)
        cameraExecutor.shutdown()
        super.onDestroy()
    }

    // ── Recording ──────────────────────────────────────────────────────────────

    private fun startVideoRecording() {
        startForeground(NOTIF_ID, buildNotification("Starting camera…"))

        val outputDir = getExternalFilesDir("video_sessions") ?: filesDir
        outputDir.mkdirs()
        val timestamp = SimpleDateFormat("yyyyMMdd_HHmmss", Locale.US).format(Date())
        val file = File(outputDir, "video_$timestamp.mp4")
        outputFile = file

        val cameraProviderFuture = ProcessCameraProvider.getInstance(this)
        cameraProviderFuture.addListener({
            try {
                val cameraProvider = cameraProviderFuture.get()

                // Target FPS 120; CameraX will silently fall back to highest supported if unavailable
                val qualitySelector = QualitySelector.fromOrderedList(
                    listOf(Quality.FHD, Quality.HD, Quality.SD)
                )
                val recorder = Recorder.Builder()
                    .setQualitySelector(qualitySelector)
                    .build()
                val videoCapture = VideoCapture.withOutput(recorder)

                // Select audio input: prefer BT SCO mic, fall back to phone mic
                val audioManager = getSystemService(AUDIO_SERVICE) as AudioManager
                val hasBluetooth = audioManager
                    .getDevices(AudioManager.GET_DEVICES_INPUTS)
                    .any { it.type == AudioDeviceInfo.TYPE_BLUETOOTH_SCO }
                if (hasBluetooth) {
                    audioManager.startBluetoothSco()
                    audioManager.isBluetoothScoOn = true
                    Log.d(TAG, "Using Bluetooth SCO microphone")
                } else {
                    Log.d(TAG, "Bluetooth SCO not available — using phone mic")
                }

                cameraProvider.unbindAll()
                cameraProvider.bindToLifecycle(
                    this,
                    CameraSelector.DEFAULT_BACK_CAMERA,
                    videoCapture
                )

                val outputOptions = FileOutputOptions.Builder(file).build()
                activeRecording = videoCapture.output
                    .prepareRecording(this, outputOptions)
                    .withAudioEnabled()
                    .start(ContextCompat.getMainExecutor(this)) { event ->
                        when (event) {
                            is VideoRecordEvent.Start -> {
                                Log.d(TAG, "Video recording started → ${file.name}")
                                startEpoch = System.currentTimeMillis()
                                VideoRecordManager.updateRecordingState(true)
                                ticker.post(tickRunnable)
                                updateNotification("● REC ${file.name}")
                            }
                            is VideoRecordEvent.Finalize -> {
                                if (event.hasError()) {
                                    Log.e(TAG, "Recording error: ${event.error}")
                                } else {
                                    Log.d(TAG, "Video saved: ${file.absolutePath}")
                                    VideoRecordManager.lastSavedFilePath = file.absolutePath
                                }
                                stopSelf()
                            }
                            else -> {}
                        }
                    }
            } catch (e: Exception) {
                Log.e(TAG, "CameraX setup failed: ${e.message}", e)
                VideoRecordManager.updateRecordingState(false)
                stopSelf()
            }
        }, ContextCompat.getMainExecutor(this))
    }

    private fun stopVideoRecording(discard: Boolean) {
        ticker.removeCallbacks(tickRunnable)
        VideoRecordManager.updateRecordingState(false)
        activeRecording?.stop()
        activeRecording = null

        if (discard) {
            // Delete file after stop — the Finalize event fires after stop()
            // so we mark it for deletion; the Finalize listener just calls stopSelf()
            outputFile?.let { f ->
                // Post-delayed to let Finalize complete before we delete
                Handler(Looper.getMainLooper()).postDelayed({
                    if (f.exists()) {
                        f.delete()
                        Log.d(TAG, "Discarded video: ${f.name}")
                    }
                }, 1_500)
            }
        }
    }

    // ── Notification ───────────────────────────────────────────────────────────

    private fun createNotificationChannel() {
        val mgr = getSystemService(NotificationManager::class.java)
        if (mgr.getNotificationChannel(NOTIF_CHANNEL) == null) {
            mgr.createNotificationChannel(
                NotificationChannel(NOTIF_CHANNEL, "Video Recording", NotificationManager.IMPORTANCE_LOW)
            )
        }
    }

    private fun buildNotification(text: String): Notification =
        Notification.Builder(this, NOTIF_CHANNEL)
            .setContentTitle("Pitch Analytix — Video")
            .setContentText(text)
            .setSmallIcon(android.R.drawable.ic_menu_camera)
            .build()

    private fun updateNotification(text: String) {
        val mgr = getSystemService(NotificationManager::class.java)
        mgr.notify(NOTIF_ID, buildNotification(text))
    }
}
