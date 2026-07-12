package com.mrpeel.cricketbattingtracker.services

import android.content.Context
import android.content.Intent
import android.util.Log
import com.google.android.gms.tasks.Tasks
import com.google.android.gms.wearable.Wearable
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow

object VideoRecordManager {
    private const val TAG = "VideoRecordManager"

    private val _isRecording = MutableStateFlow(false)
    val isRecording: StateFlow<Boolean> = _isRecording.asStateFlow()

    private val _elapsedSeconds = MutableStateFlow(0L)
    val elapsedSeconds: StateFlow<Long> = _elapsedSeconds.asStateFlow()

    // Last saved file path — set by VideoRecordService when recording stops
    var lastSavedFilePath: String? = null

    fun updateRecordingState(recording: Boolean) {
        _isRecording.value = recording
        if (!recording) _elapsedSeconds.value = 0L
    }

    fun updateElapsedSeconds(seconds: Long) {
        _elapsedSeconds.value = seconds
    }

    fun startRecording(context: Context) {
        if (_isRecording.value) return
        val prefs = context.getSharedPreferences("pitch_analytix_prefs", Context.MODE_PRIVATE)
        val cameraFacing = prefs.getString("video_camera_facing", "back") ?: "back"
        val zoomValue = prefs.getFloat("video_zoom_value", 0.0f)
        val targetFps = prefs.getInt("video_target_fps", 120)

        val intent = Intent(context, VideoRecordService::class.java).apply {
            action = VideoRecordService.ACTION_START
            putExtra("CAMERA_FACING", cameraFacing)
            putExtra("ZOOM_VALUE", zoomValue)
            putExtra("TARGET_FPS", targetFps)
        }
        try {
            if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.O) {
                context.startForegroundService(intent)
            } else {
                context.startService(intent)
            }
            sendMessageToWatch(context, "/start_video_session")
        } catch (e: Exception) {
            Log.e(TAG, "Failed to start VideoRecordService: ${e.message}", e)
        }
    }

    fun stopAndSave(context: Context) {
        val intent = Intent(context, VideoRecordService::class.java).apply {
            action = VideoRecordService.ACTION_STOP
        }
        context.startService(intent)
        sendMessageToWatch(context, "/stop_tracking")
    }

    fun discard(context: Context) {
        val intent = Intent(context, VideoRecordService::class.java).apply {
            action = VideoRecordService.ACTION_DISCARD
        }
        context.startService(intent)
        sendMessageToWatch(context, "/stop_tracking")
    }

    private fun sendMessageToWatch(context: Context, path: String) {
        Thread {
            try {
                val nodes = Tasks.await(Wearable.getNodeClient(context).connectedNodes)
                val msgClient = Wearable.getMessageClient(context)
                if (nodes.isEmpty()) {
                    Log.w(TAG, "No connected watch nodes for $path")
                }
                for (node in nodes) {
                    Tasks.await(msgClient.sendMessage(node.id, path, null))
                    Log.d(TAG, "Sent $path to ${node.displayName}")
                }
            } catch (e: Exception) {
                Log.e(TAG, "Failed to send watch message: ${e.message}", e)
            }
        }.start()
    }
}
