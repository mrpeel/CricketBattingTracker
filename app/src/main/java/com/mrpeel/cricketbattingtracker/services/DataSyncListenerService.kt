package com.mrpeel.cricketbattingtracker.services

import android.util.Log
import com.google.android.gms.wearable.DataEvent
import com.google.android.gms.wearable.DataEventBuffer
import com.google.android.gms.wearable.DataMapItem
import com.google.android.gms.wearable.WearableListenerService
import com.mrpeel.cricketbattingtracker.data.AppDatabase
import com.mrpeel.cricketbattingtracker.data.InningsEvent
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch

class DataSyncListenerService : WearableListenerService() {
    private val TAG = "DataSyncListener"
    
    override fun onDataChanged(dataEvents: DataEventBuffer) {
        val database = AppDatabase.getDatabase(applicationContext)
        val dao = database.inningsEventDao()
        
        for (event in dataEvents) {
            if (event.type == DataEvent.TYPE_CHANGED) {
                val item = event.dataItem
                if (item.uri.path == "/cricket_timeline") {
                    val dataMapItem = DataMapItem.fromDataItem(item)
                    val dataMap = dataMapItem.dataMap
                    
                    val timestamp = dataMap.getLong("timestamp")
                    val eventsList = dataMap.getStringArray("events")
                    
                    Log.d(TAG, "Received timeline sync: \${eventsList?.size} events")
                    
                    CoroutineScope(Dispatchers.IO).launch {
                        val newInningsId = (dao.getLatestInningsId() ?: 0) + 1
                        
                        eventsList?.forEachIndexed { index, eventString ->
                            // Basic parsing since we just passed simple strings from the watch V1
                            // We would map these to proper data structures in a production environment
                            var speed: Float? = null
                            var impact: Float? = null
                            if (eventString.contains("Shot detected")) {
                                // Extract naive floats (e.g. "Shot detected: Ang=12.5, Imp=45.2")
                                try {
                                    val regex = Regex("Ang=([0-9.]+), Imp=([0-9.]+)")
                                    val match = regex.find(eventString)
                                    if (match != null) {
                                        speed = match.groupValues[1].toFloat()
                                        impact = match.groupValues[2].toFloat()
                                    }
                                } catch (e: Exception) {
                                    Log.e(TAG, "Parse error", e)
                                }
                            }
                            
                            val dbEvent = InningsEvent(
                                inningsId = newInningsId,
                                timestamp = timestamp + index, // mock chronological distribution
                                description = eventString.substringBefore(":"),
                                batSpeed = speed,
                                impactForce = impact
                            )
                            dao.insertEvent(dbEvent)
                        }
                    }
                }
            }
        }
    }
}
