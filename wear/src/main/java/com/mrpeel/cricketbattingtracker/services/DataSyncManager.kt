package com.mrpeel.cricketbattingtracker.services

import android.content.Context
import android.util.Log
import com.google.android.gms.tasks.Tasks
import com.google.android.gms.wearable.DataClient
import com.google.android.gms.wearable.PutDataMapRequest
import com.google.android.gms.wearable.Wearable

class DataSyncManager(context: Context) {
    private val TAG = "DataSyncManager"
    private val dataClient: DataClient = Wearable.getDataClient(context)

    // Sync match summary logic to data layer payload
    fun syncTimelineToPhone(timelineEvents: List<String>) {
        Thread {
            try {
                val putDataMapReq = PutDataMapRequest.create("/cricket_timeline")
                val dataMap = putDataMapReq.dataMap
                
                // Needs unique timestamp to force sync event even if duplicate timeline string arrays occur
                dataMap.putLong("timestamp", System.currentTimeMillis())
                dataMap.putStringArray("events", timelineEvents.toTypedArray())
                
                val putDataReq = putDataMapReq.asPutDataRequest()
                putDataReq.setUrgent()
                
                val result = Tasks.await(dataClient.putDataItem(putDataReq))
                Log.d(TAG, "Data sent to phone layer: \${result.uri}")
                
            } catch (e: Exception) {
                Log.e(TAG, "Failed to sync timeline: \${e.message}")
            }
        }.start()
    }
}
