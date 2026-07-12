package com.mrpeel.cricketbattingtracker.data

import androidx.room.Dao
import androidx.room.Entity
import androidx.room.Insert
import androidx.room.PrimaryKey
import androidx.room.Query
import kotlinx.coroutines.flow.Flow

@Entity(tableName = "innings_events")
data class InningsEvent(
    @PrimaryKey(autoGenerate = true) val id: Int = 0,
    val inningsId: Long, // Grouping factor for a single match/innings
    val timestamp: Long,
    val description: String,
    val batSpeed: Float? = null,
    val impactForce: Float? = null,   // raw peak accel in g (not displayed directly)
    val impactTimeMs: Long? = null,    // reaction time: backlift→contact in ms
    val distanceRun: Float? = null,
    val shotType: String? = null,
    val efficiency: Float? = null,
    val backliftAngle: Float? = null,
    val followThroughAngle: Float? = null,
    val wristRollDeg: Float? = null,    // wrist rotation during follow-through
    val location: String? = null,       // reverse-geocoded street/suburb combo
    val bladeAngle: Float? = null,
    val bladeClass: String? = null,
    val launchAngle: Float? = null,
    val launchClass: String? = null,

    // Bottom hand (Polar Sense) enhancement metrics
    val bottom_hand_gyro_peak: Float? = null,      // Peak gyro magnitude from bottom hand arm
    val bottom_hand_acc_peak: Float? = null,        // Peak accel magnitude from bottom hand arm
    val bottom_hand_gyro_ratio: Float? = null,      // Bottom hand gyro / Watch gyro peak ratio
    val bottom_hand_acc_ratio: Float? = null,       // Bottom hand accel / Watch accel peak ratio
    val bottom_hand_time_lead_ms: Long? = null,     // Lag between top and bottom hand peaks (ms)
    val bottom_hand_sync_score: Float? = null,      // Hand synchronization quality score (0-100)

    // Watch SwingFeatures (stored for future re-classification)
    val swing_feature_s1_gyro_y_std: Float? = null,
    val swing_feature_s1_gyro_z_std: Float? = null,
    val swing_feature_s1_delta_x: Float? = null,
    val swing_feature_s1_delta_z: Float? = null,
    val swing_feature_s2_gyro_mag: Float? = null,
    val swing_feature_s2_grav_y_mean: Float? = null,
    val swing_feature_s2_delta_x: Float? = null,
    val swing_feature_s2_delta_z: Float? = null,
    val swing_feature_s3_roll_deg: Float? = null,
    val swing_feature_s3_yaw_deg: Float? = null,
    val swing_feature_s3_delta_x: Float? = null,
    val swing_feature_s3_delta_z: Float? = null,
    val swing_feature_s3_plane_ratio: Float? = null,
    val swing_feature_s3_gyro_y_min: Float? = null,
    val videoFilePath: String? = null,
)

@Entity(tableName = "heart_rate_events")
data class HeartRateEvent(
    @PrimaryKey(autoGenerate = true) val id: Int = 0,
    val inningsId: Long,
    val timestamp: Long,
    val beatsPerMinute: Long
)

@Dao
interface InningsEventDao {
    @Query("SELECT * FROM innings_events WHERE inningsId = :inningsId ORDER BY timestamp ASC")
    fun getTimelineForInnings(inningsId: Long): Flow<List<InningsEvent>>

    @Query("SELECT * FROM innings_events WHERE inningsId = :inningsId ORDER BY timestamp ASC")
    suspend fun getTimelineForInningsListSync(inningsId: Long): List<InningsEvent>

    @Query("SELECT * FROM innings_events ORDER BY timestamp DESC")
    fun getAllEventsFlow(): Flow<List<InningsEvent>>

    @Insert
    suspend fun insertEvent(event: InningsEvent)

    @Insert
    suspend fun insertHeartRate(hrEvent: HeartRateEvent)

    @Query("SELECT * FROM heart_rate_events WHERE inningsId = :inningsId ORDER BY timestamp ASC")
    suspend fun getHeartRatesForInningsSync(inningsId: Long): List<HeartRateEvent>
    
    @Query("SELECT MAX(inningsId) FROM innings_events")
    suspend fun getLatestInningsId(): Long?

    @Query("SELECT MAX(inningsId) FROM innings_events")
    fun getLatestInningsIdFlow(): Flow<Long?>

    @Query("SELECT DISTINCT inningsId FROM innings_events ORDER BY inningsId DESC")
    suspend fun getAllUniqueInningsIds(): List<Long>

    @Query("SELECT location FROM innings_events WHERE location IS NOT NULL AND location != 'Net Practice' AND location != '' ORDER BY timestamp DESC LIMIT 1")
    suspend fun getLastResolvedLocation(): String?

    // Update bottom hand enhancement metrics for a specific shot event
    @Query("""UPDATE innings_events SET 
        bottom_hand_gyro_peak = :gyroPeak, 
        bottom_hand_acc_peak = :accPeak, 
        bottom_hand_gyro_ratio = :gyroRatio, 
        bottom_hand_acc_ratio = :accRatio, 
        bottom_hand_time_lead_ms = :timeLeadMs, 
        bottom_hand_sync_score = :syncScore 
        WHERE id = :eventId""")
    suspend fun updateBottomHandMetrics(
        eventId: Int, gyroPeak: Float, accPeak: Float,
        gyroRatio: Float, accRatio: Float, timeLeadMs: Long, syncScore: Float
    )
    
    @Query("UPDATE innings_events SET videoFilePath = :videoFilePath WHERE id = :eventId")
    suspend fun updateVideoFilePath(eventId: Int, videoFilePath: String?)
}
