# Cricket Batting Tracker - V1 Release

I have completed the end-to-end V1 foundation for your Galaxy Watch 7 Cricket Tracker! 

The codebase is located in `~/Code/CricketBattingTracker` and can be opened directly in **Android Studio**.

## What Was Built

### 1. Wear OS (`:wear` module)
* **Foreground Tracking**: Built `TrackerService` which operates even while the watch face is off. It holds a partial wake lock to guarantee we get continuous IMU (Inertial Measurement Unit) data through your entire innings.
* **Health Services API Integration**: Implemented `HealthServicesManager` which ties directly into the standard Samsung/Google Health Wear OS Exercise client. It starts a "Cricket" workout session to track your distances run and calories reliably via GPS and pedometers.
* **Kinematics Engine**: Built a heuristic `SwingDetector` that monitors the 50Hz Accel/Gyro data from your top (left) hand. It identifies high rotational velocity (swings) combined with sharp acceleration spikes (impacts), generating a kinematic view of your shots.
* **Data Layer Hub**: The watch batches all recorded timeline strings (shots, distances) and securely pushes them to your phone automatically when connected via Bluetooth using `DataSyncManager`.

### 2. Mobile Companion App (`:app` module)
* **Room Database**: Structured a fast on-device SQLite database using Room to permanently store your past innings.
* **Wearable Sync Listener**: Created `DataSyncListenerService` which listens silently in the background for new timeline data pushed by the watch after your match.
* **Review Dashboard UI**: Built a beautiful dark-mode Jetpack Compose user interface containing an Innings summary dashboard (Total Distance, Max Bat Speed) and a chronological ordered list of the ball-by-ball actions you took on the field.

## Validation & Next Steps

Because tracking biomechanics is highly sensitive to the individual user and device hardware, the logic inside `SwingDetector` (specifically the kinematic thresholds and the difference between a forward defense and a pull block) will need tuning in the nets. 

### How to test:
1. Open `~/Code/CricketBattingTracker` in Android Studio.
2. Build and Deploy the `:wear` module to your Galaxy Watch 7.
3. Build and Deploy the `:app` module to your Samsung Phone.
4. Put the watch on your left hand under a sweatband, head to the nets, and hit START. 
5. See how accurately the baseline math detects the impact peaks! All the raw data generated can now be exported to train your custom ML shot-type classifier for V2.
