package com.mrpeel.cricketbattingtracker.data

import android.content.Context
import androidx.room.Database
import androidx.room.Room
import androidx.room.RoomDatabase
import androidx.room.migration.Migration
import androidx.sqlite.db.SupportSQLiteDatabase

@Database(entities = [InningsEvent::class, HeartRateEvent::class], version = 10, exportSchema = false)
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

        fun getDatabase(context: Context): AppDatabase {
            return INSTANCE ?: synchronized(this) {
                val instance = Room.databaseBuilder(
                    context.applicationContext,
                    AppDatabase::class.java,
                    "cricket_tracker_database"
                )
                .addMigrations(MIGRATION_6_7, MIGRATION_7_8, MIGRATION_8_9, MIGRATION_9_10)
                .fallbackToDestructiveMigration()
                .build()
                INSTANCE = instance
                instance
            }
        }
    }
}
