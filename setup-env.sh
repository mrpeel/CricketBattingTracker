#!/bin/bash
set -e

echo "Setting up Google Cloud CLI for Firebase Test Lab..."

# Download and install gcloud
curl -O https://dl.google.com/dl/cloudsdk/channels/rapid/downloads/google-cloud-cli-linux-x86_64.tar.gz
tar -xf google-cloud-cli-linux-x86_64.tar.gz
rm google-cloud-cli-linux-x86_64.tar.gz

echo "Running Google Cloud CLI installer..."
./google-cloud-sdk/install.sh --quiet

echo ""
echo "=========================================================="
echo "✅ Installation complete!"
echo ""
echo "⚠️ IMPORTANT NEXT STEPS:"
echo "1. Run the script again to load gcloud into bash by running:"
echo "   source ~/.bashrc"
echo "   (or close and reopen your terminal)"
echo "2. Log in by running:"
echo "   ~/Code/CricketBattingTracker/google-cloud-sdk/bin/gcloud auth login"
echo "3. Set your project by running (replace <ID> with your project ID):"
echo "   ~/Code/CricketBattingTracker/google-cloud-sdk/bin/gcloud config set project <ID>"
echo "=========================================================="
