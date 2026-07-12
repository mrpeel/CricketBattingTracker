#!/bin/bash
set -e

echo "======================================"
echo "🏏 Cricket Batting Tracker Build Tool"
echo "======================================"

# 1. Build the APKs
echo "🛠️ Building Phone and Watch apps (debug APKs)..."
export JAVA_HOME="$HOME/.jdk/jdk-17"
export PATH="$JAVA_HOME/bin:$PATH"
./gradlew assembleDebug

echo "✅ Build completed successfully!"
echo "To deploy to testing devices, follow the steps in testing_guide.md."
