#!/usr/bin/env python3
"""
pipelines/run_multitier_pipeline.py — Multi-Tier Telemetry Pipeline CLI

Executes the authoritative Multi-Tier evaluation scorecard across all physical sessions
using the unified telemetry engine (pipelines/telemetry_engine.py).
"""

import os
import sys

ROOT_DIR = "/Users/neilkloot/Code/CricketBattingTracker"
PIPELINES_DIR = os.path.join(ROOT_DIR, "pipelines")
if PIPELINES_DIR not in sys.path:
    sys.path.append(PIPELINES_DIR)

from telemetry_engine import (
    ROOT_DIR, BASE_DIR, DATASET_DIR, SESSIONS_DIR, STAGE1_MODEL_PATH, STAGE2_MODEL_PATH,
    STATS_PATH, APP_ASSETS_DIR, REPORT_OUT, HOLDOUT_SESSIONS, STAGE1_CHANNELS, FEATURES,
    CLASSES, SHOT_CLASSES, SOFT_TOUCH_CLASSES, normalise_shot_type,
    FacingUpTCN, StanceTracker, AdvancedTCNBlock, AdvancedTCN, Stage2TCNClassifier,
    estimate_session_clock_offset, load_parquet_session, predict_candidate_batch_unleaked,
    run_session_multitier, format_class_table, evaluate_multitier_scorecard
)

# Backward-compatible alias
UNIFIED_PARQUET_DIR = DATASET_DIR
DATASET_PATH = os.path.join(ROOT_DIR, "facing_up_sessions_423hz.pkl")


def main():
    metrics = evaluate_multitier_scorecard(verbose=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
