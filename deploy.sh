#!/bin/bash
set -e

echo "======================================"
echo "🏏 Cricket Batting Tracker Deploy Tool"
echo "======================================"

# 1. Check for gcloud and firebase CLIs
if ! command -v gcloud &> /dev/null; then
    echo "❌ Error: gcloud CLI is not installed."
    echo "Please run ./setup-env.sh to install it first."
    exit 1
fi

if ! command -v firebase &> /dev/null; then
    echo "❌ Error: firebase CLI is not installed."
    echo "Please run 'curl -sL https://firebase.tools | bash' to install."
    exit 1
fi

# 2. Build the APKs
echo "🛠️ Building Phone and Watch apps (debug APKs)..."
./gradlew assembleDebug

# 3. Robo Test (Firebase Test Lab) - Free tier limit 10/day
echo "🤖 Starting Firebase Test Lab Robo Test..."
echo "Running on Pixel 3, API 30..."
gcloud firebase test android run \
    --type robo \
    --app app/build/outputs/apk/debug/app-debug.apk \
    --device model=Pixel3,version=30,locale=en,orientation=portrait

# 4. App Distribution (Physical device testing)
echo "📱 Uploading to Firebase App Distribution..."
./gradlew app:appDistributionUploadDebug
./gradlew wear:appDistributionUploadDebug

echo "✅ Deployment completed successfully!"
echo "Check your phone/watch App Tester for the latest physical builds."
echo "Check the web console link above for the Test Lab video and logs."
