package com.mrpeel.cricketbattingtracker.services

import android.content.Intent
import android.util.Log
import com.google.android.gms.wearable.MessageEvent
import com.google.android.gms.wearable.WearableListenerService

class MessageReceiverService : WearableListenerService() {
    private val TAG = "MessageReceiverService"

    override fun onMessageReceived(messageEvent: MessageEvent) {
        Log.d(TAG, "onMessageReceived: path=${messageEvent.path}")
        val action = messageEvent.path
        if (action == "/start_tracking") {
            val intent = Intent(this, TrackerService::class.java).apply {
                putExtra("ENABLE_RAW_LOGGING", true)
            }
            try {
                if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.O) {
                    startForegroundService(intent)
                } else {
                    startService(intent)
                }
            } catch (e: Exception) {
                Log.e(TAG, "Failed to start TrackerService from message receiver", e)
            }
        } else if (action == "/start_video_session") {
            // Video analysis session — raw logging on, SwingDetector passive
            SessionManager.setVideoMode(true)
            val intent = Intent(this, TrackerService::class.java).apply {
                putExtra("ENABLE_RAW_LOGGING", true)
                putExtra("VIDEO_MODE", true)
            }
            try {
                if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.O) {
                    startForegroundService(intent)
                } else {
                    startService(intent)
                }
            } catch (e: Exception) {
                Log.e(TAG, "Failed to start TrackerService (video mode) from message receiver", e)
            }
        } else if (action == "/stop_tracking") {
            val intent = Intent(this, TrackerService::class.java).apply {
                this.action = "STOP_TRACKING"
            }
            try {
                startService(intent)
            } catch (e: Exception) {
                Log.e(TAG, "Failed to stop TrackerService from message receiver", e)
            }
        }
    }
}
