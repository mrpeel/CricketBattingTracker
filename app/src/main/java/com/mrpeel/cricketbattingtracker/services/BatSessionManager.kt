package com.mrpeel.cricketbattingtracker.services

import android.content.Context
import android.util.Log
import com.google.android.gms.tasks.Tasks
import com.google.android.gms.wearable.Wearable
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import org.json.JSONArray
import org.json.JSONObject
import java.io.File

/** Polar Verity Sense mounting location */
enum class PolarMountMode(val value: String, val code: Int) {
    NONE("NONE", 0),
    WRIST("WRIST", 1),
    BAT_HANDLE("BAT_HANDLE", 2);

    companion object {
        fun fromString(s: String?): PolarMountMode {
            return when (s?.uppercase()) {
                "BAT_HANDLE", "BAT", "HANDLE" -> BAT_HANDLE
                "NONE", "NO_POLAR", "NO" -> NONE
                else -> WRIST // Default / historical
            }
        }

        fun fromCode(code: Int): PolarMountMode {
            return when (code) {
                2 -> BAT_HANDLE
                1 -> WRIST
                else -> NONE
            }
        }
    }
}

/** Configurable physical bat profile */
data class BatProfile(
    val batId: Int, // 1, 2, 3
    val name: String,
    val weightGrams: Float,
    val sensorOffsetFromKnobCm: Float = 31.0f,
    val sensorOffsetFromToeCm: Float = 57.0f
)

/** Timestamped bat switch event during a live practice session */
data class BatSwitchEvent(
    val timestampMs: Long,
    val batId: Int
)

/**
 * Singleton manager for Bat Profiles, Polar Mount Mode, and Mid-Session Bat Switching.
 */
object BatSessionManager {
    private const val TAG = "BatSessionManager"
    private const val PREFS_NAME = "pitch_analytix_prefs"
    private const val KEY_MOUNT_MODE = "polar_mount_mode"
    private const val KEY_ACTIVE_BAT_ID = "active_bat_id"
    private const val KEY_BAT_PROFILES = "bat_profiles_json"

    // Default bat profiles
    private val DEFAULT_PROFILES = listOf(
        BatProfile(1, "Game bat", 1425.0f, sensorOffsetFromKnobCm = 31.0f, sensorOffsetFromToeCm = 57.0f),
        BatProfile(2, "Gray Nicholls Giant", 1625.0f, sensorOffsetFromKnobCm = 31.0f, sensorOffsetFromToeCm = 57.0f),
        BatProfile(3, "Eye in bat", 1200.0f, sensorOffsetFromKnobCm = 31.0f, sensorOffsetFromToeCm = 55.0f)
    )

    private val _polarMountMode = MutableStateFlow(PolarMountMode.WRIST)
    val polarMountMode: StateFlow<PolarMountMode> = _polarMountMode.asStateFlow()

    private val _batProfiles = MutableStateFlow(DEFAULT_PROFILES)
    val batProfiles: StateFlow<List<BatProfile>> = _batProfiles.asStateFlow()

    private val _activeBatId = MutableStateFlow(1)
    val activeBatId: StateFlow<Int> = _activeBatId.asStateFlow()

    private val batSwitches = mutableListOf<BatSwitchEvent>()
    private var isSessionActive = false

    private var initialized = false

    /** Initialize state from persistent SharedPreferences */
    fun initialize(context: Context) {
        if (initialized) return
        val prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)

        val mountStr = prefs.getString(KEY_MOUNT_MODE, PolarMountMode.WRIST.value)
        _polarMountMode.value = PolarMountMode.fromString(mountStr)

        val activeId = prefs.getInt(KEY_ACTIVE_BAT_ID, 1)
        _activeBatId.value = activeId.coerceIn(1, 3)

        val profilesJson = prefs.getString(KEY_BAT_PROFILES, null)
        if (profilesJson != null) {
            try {
                val list = mutableListOf<BatProfile>()
                val arr = JSONArray(profilesJson)
                for (i in 0 until arr.length()) {
                    val obj = arr.getJSONObject(i)
                    list.add(
                        BatProfile(
                            batId = obj.getInt("bat_id"),
                            name = obj.getString("name"),
                            weightGrams = obj.getDouble("weight_grams").toFloat(),
                            sensorOffsetFromKnobCm = obj.optDouble("sensor_offset_from_knob_cm", 31.0).toFloat(),
                            sensorOffsetFromToeCm = obj.optDouble("sensor_offset_from_toe_cm", 57.0).toFloat()
                        )
                    )
                }
                if (list.size == 3) {
                    _batProfiles.value = list
                }
            } catch (e: Exception) {
                Log.e(TAG, "Error parsing saved bat profiles JSON: ${e.message}", e)
            }
        }
        initialized = true
    }

    /** Set and persist Polar Mount Mode (WRIST vs BAT_HANDLE) */
    fun setMountMode(context: Context, mode: PolarMountMode) {
        _polarMountMode.value = mode
        val prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
        prefs.edit().putString(KEY_MOUNT_MODE, mode.value).apply()
        Log.d(TAG, "Updated Polar Mount Mode: $mode")
    }

    /** Update a specific bat profile (1, 2, or 3) and persist */
    fun updateBatProfile(context: Context, profile: BatProfile) {
        val currentList = _batProfiles.value.toMutableList()
        val idx = currentList.indexOfFirst { it.batId == profile.batId }
        if (idx >= 0) {
            currentList[idx] = profile
        } else {
            currentList.add(profile)
        }
        _batProfiles.value = currentList
        saveProfilesToPrefs(context, currentList)
    }

    private fun saveProfilesToPrefs(context: Context, profiles: List<BatProfile>) {
        try {
            val arr = JSONArray()
            for (p in profiles) {
                val obj = JSONObject()
                obj.put("bat_id", p.batId)
                obj.put("name", p.name)
                obj.put("weight_grams", p.weightGrams.toDouble())
                obj.put("sensor_offset_from_knob_cm", p.sensorOffsetFromKnobCm.toDouble())
                obj.put("sensor_offset_from_toe_cm", p.sensorOffsetFromToeCm.toDouble())
                arr.put(obj)
            }
            val prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
            prefs.edit().putString(KEY_BAT_PROFILES, arr.toString()).apply()
        } catch (e: Exception) {
            Log.e(TAG, "Error saving bat profiles to prefs: ${e.message}", e)
        }
    }

    /**
     * Switch the active bat.
     * Can be invoked prior to session start or DURING a running session.
     */
    fun selectBat(context: Context?, batId: Int) {
        val validId = batId.coerceIn(1, 3)
        _activeBatId.value = validId

        context?.let {
            val prefs = it.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
            prefs.edit().putInt(KEY_ACTIVE_BAT_ID, validId).apply()
        }

        if (isSessionActive) {
            val now = System.currentTimeMillis()
            synchronized(batSwitches) {
                batSwitches.add(BatSwitchEvent(now, validId))
            }
            Log.d(TAG, "🏏 MID-SESSION BAT SWITCH: Bat $validId at Ts=$now")

            // Send notification to watch node so TrackerService records it on timeline
            context?.let { ctx ->
                sendBatSwitchToWatch(ctx, validId, now)
            }
        }
    }

    /** Call when a session starts */
    fun onSessionStart(startTimeMs: Long = System.currentTimeMillis()) {
        isSessionActive = true
        synchronized(batSwitches) {
            batSwitches.clear()
            batSwitches.add(BatSwitchEvent(startTimeMs, _activeBatId.value))
        }
        Log.d(TAG, "BatSessionManager session started at $startTimeMs with initial Bat ${_activeBatId.value}")
    }

    /** Call when a session stops */
    fun onSessionEnd(endTimeMs: Long = System.currentTimeMillis()) {
        isSessionActive = false
        Log.d(TAG, "BatSessionManager session ended at $endTimeMs with ${batSwitches.size} switch events")
    }

    /** Get the active bat ID for a specific shot timestamp */
    fun getBatIdAtTime(timestampMs: Long): Int {
        synchronized(batSwitches) {
            if (batSwitches.isEmpty()) return _activeBatId.value
            // Find latest switch event with timestamp <= target
            val applicable = batSwitches.filter { it.timestampMs <= timestampMs }
            return applicable.lastOrNull()?.batId ?: batSwitches.first().batId
        }
    }

    fun getBatProfile(batId: Int): BatProfile {
        return _batProfiles.value.firstOrNull { it.batId == batId }
            ?: DEFAULT_PROFILES.first { it.batId == batId }
    }

    /** Generate standard JSON configuration string for this session */
    fun createSessionConfigJson(startTimeMs: Long, endTimeMs: Long): String {
        val root = JSONObject()
        root.put("polar_mount_mode", _polarMountMode.value.value)
        root.put("initial_bat_id", batSwitches.firstOrNull()?.batId ?: _activeBatId.value)
        root.put("start_time_ms", startTimeMs)
        root.put("end_time_ms", endTimeMs)

        val profilesArr = JSONArray()
        for (p in _batProfiles.value) {
            val pObj = JSONObject()
            pObj.put("bat_id", p.batId)
            pObj.put("name", p.name)
            pObj.put("weight_grams", p.weightGrams.toDouble())
            pObj.put("sensor_offset_from_knob_cm", p.sensorOffsetFromKnobCm.toDouble())
            pObj.put("sensor_offset_from_toe_cm", p.sensorOffsetFromToeCm.toDouble())
            profilesArr.put(pObj)
        }
        root.put("bat_profiles", profilesArr)

        val switchesArr = JSONArray()
        synchronized(batSwitches) {
            for (s in batSwitches) {
                val sObj = JSONObject()
                sObj.put("timestamp_ms", s.timestampMs)
                sObj.put("bat_id", s.batId)
                switchesArr.put(sObj)
            }
        }
        root.put("bat_switches", switchesArr)

        return root.toString(2)
    }

    /** Write session_config.json to target session directory */
    fun writeSessionConfigFile(targetDir: File, startTimeMs: Long, endTimeMs: Long): File? {
        return try {
            if (!targetDir.exists()) targetDir.mkdirs()
            val file = File(targetDir, "session_config.json")
            file.writeText(createSessionConfigJson(startTimeMs, endTimeMs))
            Log.d(TAG, "Saved session_config.json to: ${file.absolutePath}")
            file
        } catch (e: Exception) {
            Log.e(TAG, "Failed to write session_config.json: ${e.message}", e)
            null
        }
    }

    private fun sendBatSwitchToWatch(context: Context, batId: Int, timestampMs: Long) {
        Thread {
            try {
                val nodeClient = Wearable.getNodeClient(context)
                val nodes = Tasks.await(nodeClient.connectedNodes)
                val messageClient = Wearable.getMessageClient(context)
                val payload = "bat_id=$batId,Ts=$timestampMs".toByteArray(Charsets.UTF_8)
                for (node in nodes) {
                    Tasks.await(messageClient.sendMessage(node.id, "/bat_switch", payload))
                    Log.d(TAG, "Sent /bat_switch to watch node ${node.displayName}")
                }
            } catch (e: Exception) {
                Log.w(TAG, "Failed to send /bat_switch to watch: ${e.message}")
            }
        }.start()
    }
}
