#!/usr/bin/env bash
# run_poc.sh — End-to-end POC: build unified dataset for all sessions except the
# holdout (session_2026-07-18_13-44-09), train TCN, evaluate on holdout.
#
# Usage: ./pipelines/run_poc.sh
#
# Stages:
#   1. Build unified parquet + sensor_alignment.json for every session (train + holdout)
#   2. Train TCN with automatic session discovery (all parquets EXCEPT holdout)
#   3. Evaluate on the holdout session 2026-07-18_13-44-09
#   4. Print acceptance metrics
#
# Outputs:
#   /Users/neilkloot/Code/Batting Sensor Stats/poc_unified_dataset/*.parquet
#   /Users/neilkloot/Code/Batting Sensor Stats/poc_unified_dataset/*_sensor_alignment.json
#   /Users/neilkloot/Code/Batting Sensor Stats/poc_tcn_output/tcn_model.pt
#   /Users/neilkloot/Code/Batting Sensor Stats/poc_tcn_output/poc_results.json
#   /tmp/poc_tcn_train.log (live training log)

set -e

REPO_ROOT="/Users/neilkloot/Code/CricketBattingTracker"
PIPELINES_DIR="$REPO_ROOT/pipelines"
DATASET_DIR="/Users/neilkloot/Code/Batting Sensor Stats/poc_unified_dataset"
OUTPUT_DIR="/Users/neilkloot/Code/Batting Sensor Stats/poc_tcn_output"

mkdir -p "$DATASET_DIR" "$OUTPUT_DIR"

echo "============================================================"
echo "  Pitch Analytix Pro — TCN POC Pipeline"
echo "  Holdout: session_2026-07-18_13-44-09"
echo "============================================================"
echo

# -------- Stage 1: Build unified dataset ----------
# Clean outputs so re-runs are deterministic
echo "STAGE 1: Building unified-row datasets..."
rm -f "$DATASET_DIR"/*.parquet "$DATASET_DIR"/*_sensor_alignment.json
python3 -u "$PIPELINES_DIR/build_unified_dataset.py" 2>&1 | tee /tmp/poc_build.log
echo
echo "Built $(ls "$DATASET_DIR"/*_unified.parquet | wc -l | tr -d ' ') original parquet files"
echo "Built $(ls "$DATASET_DIR"/*_sensor_alignment.json | wc -l | tr -d ' ') alignment files"
echo

# -------- Stage 1b: Class-Balanced Augmentation ----------
echo "STAGE 1b: Running Class-Balanced 10x Synthetic Augmentation..."
python3 -u "$PIPELINES_DIR/augment_unified_dataset.py" 2>&1 | tee /tmp/poc_aug.log
echo "Total Training Parquet Files: $(ls "$DATASET_DIR"/*.parquet | wc -l | tr -d ' ')"
echo

# -------- Stage 2 + 3: Train + evaluate ----------
echo "STAGE 2+3: Training TCN with Early Stopping (max 40 epochs) and evaluating on holdout..."
python3 -u "$PIPELINES_DIR/train_tcn_poc.py" 2>&1 | tee /tmp/poc_tcn_train.log

echo
echo "============================================================"
echo "  POC Complete"
echo "  Model:    $OUTPUT_DIR/tcn_model.pt"
echo "  Holdout preds: $OUTPUT_DIR/holdout_preds.npy"
echo "  Training log:  /tmp/poc_tcn_train.log"
echo "============================================================"