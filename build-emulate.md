# Hybrid Workflow: CLI-Only Cloud Testing

This document details the hybrid workflow used to develop the Cricket Batting Tracker. Because local Android emulators crash the Chromebook environment, all coding and compilation is done locally, while all testing is pushed to the cloud via the command line, entirely bypassing Android Studio.

This setup relies on the **Firebase Free Tier (Spark Plan)**.

## Core Services

1. **Firebase Test Lab (CLI):** Used for automated UI/Layout checks on cloud emulators.
2. **Firebase App Distribution:** Used for physical movement testing (installing the companion apps on your actual hardware).

---

## 0. First-Time Firebase Setup

Before using the commands below, you must create a Firebase project and link it to this codebase. You only need to do this once.

1. **Create the Project:**
   - Go to the [Firebase Console](https://console.firebase.google.com/) and click **Add project**.
   - Name it (e.g., "Cricket Batting Tracker").
   - You can disable Google Analytics for now unless you want crash reports later.
   - Leave it on the default **Spark (Free)** plan.

2. **Register Your Apps:**
   - On the Project Overview page, click the **Android icon** to add an app.
   - Important: You need to register *two* apps (one for the Phone, one for the Watch).
   - **Phone App:** Enter package name `com.mrpeel.cricketbattingtracker` and register. Download the `google-services.json` file and place it in your `app/` directory.
   - **Watch App:** Repeat the process for package `com.mrpeel.cricketbattingtracker.wear` and place its `google-services.json` file in your `wear/` directory.

3. **Install & Authenticate CLIs:**
   - Install the Firebase CLI (for App Distribution): 
     ```bash
     curl -sL https://firebase.tools | bash
     firebase login
     ```
   - Install the Google Cloud CLI (for Test Lab):
     - Follow instructions for Linux/ChromeOS on [Google Cloud Docs](https://cloud.google.com/sdk/docs/install).
     - Authenticate and set your project:
       ```bash
       gcloud auth login
       gcloud config set project your-firebase-project-id
       ```

---

## 1. UI Checks using Firebase Test Lab (CLI)

Instead of interactive streaming which requires Android Studio and has a strict 30 min/month limit, we use Firebase Test Lab to run our compiled APKs on cloud virtual devices and capture logs, screenshots, and videos.

**Free Tier Limits:** 
* Up to **10 test runs per day** on Virtual Devices.
* Up to **5 test runs per day** on Physical Devices.

### Step-by-Step Test Lab:
**Prerequisite:** Ensure you have the `gcloud` (Google Cloud) CLI installed and authenticated with your Firebase project (`gcloud auth login` and `gcloud config set project [YOUR-PROJECT-ID]`).

1. **Build the APK (and Optional Test APK):**
   ```bash
   ./gradlew assembleDebug
   # Or for instrumented tests:
   # ./gradlew assembleDebug assembleDebugAndroidTest
   ```

2. **Run a Robo Test (Automated UI crawling):**
   Robo tests automatically click through your app and return a video and screenshots of the UI.
   ```bash
   gcloud firebase test android run \
     --type robo \
     --app app/build/outputs/apk/debug/app-debug.apk \
     --device model=Pixel3,version=30,locale=en,orientation=portrait
   ```
   *The console will output a web link. Click it to view the video recording of the app running, the logs, and any crashes.*

---

## 2. Movement Testing using Firebase App Distribution

Because motion sensors and swing detection cannot be accurately tested over an emulator, physical testing is required. App Distribution allows us to push APKs to your phone and watch without connecting cables to the Chromebook.

**Free Tier Limit:** App Distribution is completely free (limits allow up to 1000 testers, which is more than enough).

### Step-by-Step App Distribution:

**Prerequisite:** Ensure your Firebase project is setup, and you have authenticated via the Firebase CLI (`firebase login`) or downloaded a service account JSON.

1. **Build the APKs:** 
   Compile both the phone and watch apps locally here in Antigravity.
   ```bash
   ./gradlew assembleDebug
   ```
2. **Push to Firebase:**
   Upload the resulting APKs to Firebase App Distribution using the dedicated Gradle tasks.
   
   *For the companion phone app:*
   ```bash
   ./gradlew app:appDistributionUploadDebug
   ```
   *For the Wear OS app:*
   ```bash
   ./gradlew wear:appDistributionUploadDebug
   ```
   *(Note: You can pass parameters like `--project`, `--app-id`, or `--groups` if they are not hardcoded in the build.gradle.kts)*

3. **Install on Hardware:**
   - Open the **App Tester** application on your physical Android phone (or tap the link in your email).
   - Download the latest Phone app and Wear OS app.
   - Proceed to the field for swing detection / movement tracking test.
