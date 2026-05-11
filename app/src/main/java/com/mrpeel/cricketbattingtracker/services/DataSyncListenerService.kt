package com.mrpeel.cricketbattingtracker.services

import android.content.Intent
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

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        if (intent?.action == "com.mrpeel.cricketbattingtracker.INJECT_TIMELINE") {
            try {
                // Read the pushed wear OS file directly off disk to avoid ADB shell string collision
                val file = java.io.File("/data/local/tmp/wear_timeline.txt")
                if (file.exists()) {
                    val payload = file.readText().split("\n").filter { it.isNotBlank() }.toTypedArray()
                    Log.d(TAG, "ADB Injection Detected! Processing \${payload.size} events...")
                    ingestTimeline(System.currentTimeMillis(), payload)
                }
            } catch (e: Exception) {
                Log.e(TAG, "Injection read failed", e)
            }
        }
        return super.onStartCommand(intent, flags, startId)
    }

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
                    if (eventsList != null) {
                        ingestTimeline(timestamp, eventsList)
                    }
                }
            }
        }
    }

    private fun ingestTimeline(timestamp: Long, eventsList: Array<String>) {
        val database = AppDatabase.getDatabase(applicationContext)
        val dao = database.inningsEventDao()
        
        CoroutineScope(Dispatchers.IO).launch {
            val newInningsId = (dao.getLatestInningsId() ?: 0) + 1
            
            eventsList.forEachIndexed { index, eventString ->
                var speed: Float? = null
                var impact: Float? = null
                var impactTimeMs: Long? = null
                var shotType: String? = null
                var efficiency: Float? = null
                var blAngle: Float? = null
                var ftAngle: Float? = null
                var wristRollDeg: Float? = null
                var desc = eventString

                if (eventString.startsWith("Shot:")) {
                    try {
                        val regex = Regex("Type=([^,]+), Spd=([0-9.]+), Hit=(true|false), Acc=([0-9.]+), SS=([A-Za-z/]+), Eff=([0-9.]+), BL=([0-9.-]+), FT=([0-9.-]+)(?:, ItMs=([0-9]+))?(?:, Wr=([0-9.-]+))?")
                        val match = regex.find(eventString)
                        if (match != null) {
                            shotType = match.groupValues[1]
                            speed = match.groupValues[2].toFloat()
                            val isHit = match.groupValues[3].toBoolean()
                            impact = match.groupValues[4].toFloat()
                            val sweetSpot = match.groupValues[5]
                            efficiency = match.groupValues[6].toFloat()
                            blAngle = match.groupValues[7].toFloat()
                            ftAngle = match.groupValues[8].toFloat()
                            impactTimeMs = match.groupValues[9].toLongOrNull()
                            wristRollDeg = match.groupValues[10].toFloatOrNull()
                            desc = if (isHit) "$shotType ($sweetSpot)" else "Play and Miss"
                        }
                    } catch (e: Exception) {
                        Log.e(TAG, "Parse error: $eventString", e)
                    }
                }
                
                val dbEvent = InningsEvent(
                    inningsId = newInningsId,
                    timestamp = timestamp + index,
                    description = desc,
                    batSpeed = speed,
                    impactForce = impact,
                    impactTimeMs = impactTimeMs,
                    shotType = shotType,
                    efficiency = efficiency,
                    backliftAngle = blAngle,
                    followThroughAngle = ftAngle,
                    wristRollDeg = wristRollDeg
                )
                dao.insertEvent(dbEvent)
            }

            // Pass the downloaded batch asynchronously up to Google Firestore
            // Auto-launch the UI to show the new sync results
            val launchIntent = Intent(applicationContext, com.mrpeel.cricketbattingtracker.MainActivity::class.java)
            launchIntent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            launchIntent.addFlags(Intent.FLAG_ACTIVITY_SINGLE_TOP)
            applicationContext.startActivity(launchIntent)
        }
    }
}
