package com.mrpeel.cricketbattingtracker.data

import android.content.Context
import androidx.room.Database
import androidx.room.Room
import androidx.room.RoomDatabase
import androidx.room.migration.Migration
import androidx.sqlite.db.SupportSQLiteDatabase

@Database(entities = [InningsEvent::class, HeartRateEvent::class], version = 12, exportSchema = false)
abstract class AppDatabase : RoomDatabase() {
    abstract fun inningsEventDao(): InningsEventDao

    companion object {
        @Volatile
        private var INSTANCE: AppDatabase? = null

        /** Migration 6→7: Add bottom_hand and swing_feature columns to innings_events. */
        private val MIGRATION_6_7 = object : Migration(6, 7) {
            override fun migrate(db: SupportSQLiteDatabase) {
                // Bottom hand (Polar Sense) enhancement metrics
                db.execSQL("ALTER TABLE innings_events ADD COLUMN bottom_hand_gyro_peak REAL")
                db.execSQL("ALTER TABLE innings_events ADD COLUMN bottom_hand_acc_peak REAL")
                db.execSQL("ALTER TABLE innings_events ADD COLUMN bottom_hand_gyro_ratio REAL")
                db.execSQL("ALTER TABLE innings_events ADD COLUMN bottom_hand_acc_ratio REAL")
                db.execSQL("ALTER TABLE innings_events ADD COLUMN bottom_hand_time_lead_ms INTEGER")
                db.execSQL("ALTER TABLE innings_events ADD COLUMN bottom_hand_sync_score REAL")

                // Watch SwingFeatures (stored for future re-classification)
                db.execSQL("ALTER TABLE innings_events ADD COLUMN swing_feature_s1_gyro_y_std REAL")
                db.execSQL("ALTER TABLE innings_events ADD COLUMN swing_feature_s1_gyro_z_std REAL")
                db.execSQL("ALTER TABLE innings_events ADD COLUMN swing_feature_s1_delta_x REAL")
                db.execSQL("ALTER TABLE innings_events ADD COLUMN swing_feature_s1_delta_z REAL")
                db.execSQL("ALTER TABLE innings_events ADD COLUMN swing_feature_s2_gyro_mag REAL")
                db.execSQL("ALTER TABLE innings_events ADD COLUMN swing_feature_s2_grav_y_mean REAL")
                db.execSQL("ALTER TABLE innings_events ADD COLUMN swing_feature_s2_delta_x REAL")
                db.execSQL("ALTER TABLE innings_events ADD COLUMN swing_feature_s2_delta_z REAL")
                db.execSQL("ALTER TABLE innings_events ADD COLUMN swing_feature_s3_roll_deg REAL")
                db.execSQL("ALTER TABLE innings_events ADD COLUMN swing_feature_s3_yaw_deg REAL")
                db.execSQL("ALTER TABLE innings_events ADD COLUMN swing_feature_s3_delta_x REAL")
                db.execSQL("ALTER TABLE innings_events ADD COLUMN swing_feature_s3_delta_z REAL")
                db.execSQL("ALTER TABLE innings_events ADD COLUMN swing_feature_s3_plane_ratio REAL")
                db.execSQL("ALTER TABLE innings_events ADD COLUMN swing_feature_s3_gyro_y_min REAL")
            }
        }

        /** Migration 7→8: Add videoFilePath column to innings_events. */
        private val MIGRATION_7_8 = object : Migration(7, 8) {
            override fun migrate(db: SupportSQLiteDatabase) {
                db.execSQL("ALTER TABLE innings_events ADD COLUMN videoFilePath TEXT")
            }
        }

        /** Migration 8→9: Add bottom_hand_mag_* columns to innings_events. */
        private val MIGRATION_8_9 = object : Migration(8, 9) {
            override fun migrate(db: SupportSQLiteDatabase) {
                db.execSQL("ALTER TABLE innings_events ADD COLUMN bottom_hand_mag_peak REAL")
                db.execSQL("ALTER TABLE innings_events ADD COLUMN bottom_hand_mag_delta REAL")
                db.execSQL("ALTER TABLE innings_events ADD COLUMN bottom_hand_mag_x REAL")
                db.execSQL("ALTER TABLE innings_events ADD COLUMN bottom_hand_mag_y REAL")
                db.execSQL("ALTER TABLE innings_events ADD COLUMN bottom_hand_mag_z REAL")
            }
        }

        /** Migration 9→10: Add polar_mount_mode and bat_id columns to innings_events. */
        private val MIGRATION_9_10 = object : Migration(9, 10) {
            override fun migrate(db: SupportSQLiteDatabase) {
                db.execSQL("ALTER TABLE innings_events ADD COLUMN polar_mount_mode TEXT")
                db.execSQL("ALTER TABLE innings_events ADD COLUMN bat_id INTEGER")
            }
        }

        /** Migration 10→11: Add bat physical spec columns to innings_events. */
        private val MIGRATION_10_11 = object : Migration(10, 11) {
            override fun migrate(db: SupportSQLiteDatabase) {
                db.execSQL("ALTER TABLE innings_events ADD COLUMN bat_name TEXT")
                db.execSQL("ALTER TABLE innings_events ADD COLUMN bat_weight_grams REAL")
                db.execSQL("ALTER TABLE innings_events ADD COLUMN bat_sensor_offset_knob_cm REAL")
                db.execSQL("ALTER TABLE innings_events ADD COLUMN bat_sensor_offset_toe_cm REAL")
            }
        }

        /** Migration 11→12: Add 3D AHRS orientation and kinematic guard columns to innings_events. */
        internal val MIGRATION_11_12 = object : Migration(11, 12) {
            override fun migrate(db: SupportSQLiteDatabase) {
                db.execSQL("ALTER TABLE innings_events ADD COLUMN blade_pitch_deg REAL")
                db.execSQL("ALTER TABLE innings_events ADD COLUMN face_angle_deg REAL")
                db.execSQL("ALTER TABLE innings_events ADD COLUMN swing_yaw_deg REAL")
                db.execSQL("ALTER TABLE innings_events ADD COLUMN relative_wrist_angle_deg REAL")
                db.execSQL("ALTER TABLE innings_events ADD COLUMN azimuth_deviation_deg REAL")
                db.execSQL("ALTER TABLE innings_events ADD COLUMN polar_mount_type TEXT")
                db.execSQL("ALTER TABLE innings_events ADD COLUMN is_kinematically_valid INTEGER")
            }
        }

        internal val REQUIRED_INNINGS_EVENT_COLUMNS = mapOf(
            "blade_pitch_deg" to "REAL",
            "face_angle_deg" to "REAL",
            "swing_yaw_deg" to "REAL",
            "relative_wrist_angle_deg" to "REAL",
            "azimuth_deviation_deg" to "REAL",
            "polar_mount_type" to "TEXT",
            "is_kinematically_valid" to "INTEGER",
            "bat_name" to "TEXT",
            "bat_weight_grams" to "REAL",
            "bat_sensor_offset_knob_cm" to "REAL",
            "bat_sensor_offset_toe_cm" to "REAL",
            "polar_mount_mode" to "TEXT",
            "bat_id" to "INTEGER",
            "videoFilePath" to "TEXT",
            "bottom_hand_mag_peak" to "REAL",
            "bottom_hand_mag_delta" to "REAL",
            "bottom_hand_mag_x" to "REAL",
            "bottom_hand_mag_y" to "REAL",
            "bottom_hand_mag_z" to "REAL",
            "bottom_hand_gyro_peak" to "REAL",
            "bottom_hand_acc_peak" to "REAL",
            "bottom_hand_gyro_ratio" to "REAL",
            "bottom_hand_acc_ratio" to "REAL",
            "bottom_hand_time_lead_ms" to "INTEGER",
            "bottom_hand_sync_score" to "REAL",
            "swing_feature_s1_gyro_y_std" to "REAL",
            "swing_feature_s1_gyro_z_std" to "REAL",
            "swing_feature_s1_delta_x" to "REAL",
            "swing_feature_s1_delta_z" to "REAL",
            "swing_feature_s2_gyro_mag" to "REAL",
            "swing_feature_s2_grav_y_mean" to "REAL",
            "swing_feature_s2_delta_x" to "REAL",
            "swing_feature_s2_delta_z" to "REAL",
            "swing_feature_s3_roll_deg" to "REAL",
            "swing_feature_s3_yaw_deg" to "REAL",
            "swing_feature_s3_delta_x" to "REAL",
            "swing_feature_s3_delta_z" to "REAL",
            "swing_feature_s3_plane_ratio" to "REAL",
            "swing_feature_s3_gyro_y_min" to "REAL",
            "bladeAngle" to "REAL",
            "bladeClass" to "TEXT",
            "launchAngle" to "REAL",
            "launchClass" to "TEXT",
            "distanceRun" to "REAL",
            "shotType" to "TEXT",
            "efficiency" to "REAL",
            "backliftAngle" to "REAL",
            "followThroughAngle" to "REAL",
            "wristRollDeg" to "REAL",
            "location" to "TEXT",
            "batSpeed" to "REAL",
            "impactForce" to "REAL",
            "impactTimeMs" to "INTEGER"
        )

        private fun logWarning(tag: String, msg: String) {
            try {
                android.util.Log.w(tag, msg)
            } catch (_: Throwable) {
                println("[$tag] WARN: $msg")
            }
        }

        private fun logError(tag: String, msg: String, tr: Throwable?) {
            try {
                android.util.Log.e(tag, msg, tr)
            } catch (_: Throwable) {
                println("[$tag] ERROR: $msg ${tr?.message}")
            }
        }

        internal fun ensureSchemaIntegrity(db: SupportSQLiteDatabase) {
            try {
                val cursor = db.query("PRAGMA table_info(innings_events)")
                val existingColumns = mutableSetOf<String>()
                cursor.use {
                    val nameIdx = it.getColumnIndex("name")
                    if (nameIdx >= 0) {
                        while (it.moveToNext()) {
                            existingColumns.add(it.getString(nameIdx))
                        }
                    }
                }

                if (existingColumns.isNotEmpty()) {
                    for ((colName, colType) in REQUIRED_INNINGS_EVENT_COLUMNS) {
                        if (!existingColumns.contains(colName)) {
                            logWarning("AppDatabase", "Auto-repaired missing column $colName ($colType) in innings_events")
                            db.execSQL("ALTER TABLE innings_events ADD COLUMN $colName $colType")
                        }
                    }
                }
            } catch (e: Exception) {
                logError("AppDatabase", "Failed to verify/repair schema integrity: ${e.message}", e)
            }
        }

        fun getDatabase(context: Context): AppDatabase {
            return INSTANCE ?: synchronized(this) {
                val instance = Room.databaseBuilder(
                    context.applicationContext,
                    AppDatabase::class.java,
                    "cricket_tracker_database"
                )
                .addMigrations(MIGRATION_6_7, MIGRATION_7_8, MIGRATION_8_9, MIGRATION_9_10, MIGRATION_10_11, MIGRATION_11_12)
                .addCallback(object : RoomDatabase.Callback() {
                    override fun onOpen(db: SupportSQLiteDatabase) {
                        super.onOpen(db)
                        ensureSchemaIntegrity(db)
                    }
                })
                .fallbackToDestructiveMigration()
                .build()
                INSTANCE = instance
                instance
            }
        }
    }
}
