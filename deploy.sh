#!/bin/bash
set -e

echo "======================================"
echo "🏏 Cricket Batting Tracker Build Tool"
echo "======================================"

# 1. Build the APKs
echo "🛠️ Building Phone and Watch apps (debug APKs)..."
./gradlew assembleDebug

echo "✅ Build completed successfully!"
echo "To deploy to testing devices, follow the steps in testing_guide.md."
