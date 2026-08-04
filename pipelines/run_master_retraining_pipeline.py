#!/usr/bin/env python3
"""
pipelines/run_master_retraining_pipeline.py — Master Dataset Recompilation & Retraining Pipeline

Executes full sequential retraining across Stage 1 and Stage 2 models on restored ground truth data:
  1. Recompiles 423 Hz stance dataset (build_facing_up_dataset.py).
  2. Retrains Stage 1 Facing Up Stance TCN model (train_facing_up_detector.py).
  3. Retrains Stage 2 AdvancedTCN Shot Classifier model (train_and_evaluate_full_scorecard.py).
  4. Evaluates Hierarchical Multi-Tier Telemetry Pipeline (run_multitier_pipeline.py).
"""

import os
import sys
import time
import subprocess

ROOT_DIR = "/Users/neilkloot/Code/CricketBattingTracker"
PIPELINES_DIR = os.path.join(ROOT_DIR, "pipelines")

def run_step(step_num, title, script_name):
    print("\n" + "=" * 90, flush=True)
    print(f"  STEP {step_num}: {title.upper()} ({script_name})", flush=True)
    print("=" * 90, flush=True)
    
    script_path = os.path.join(PIPELINES_DIR, script_name)
    t0 = time.time()
    
    res = subprocess.run(["python3", "-u", script_path])
    elapsed = time.time() - t0
    
    if res.returncode == 0:
        print(f"\n✅ Step {step_num} ({title}) completed cleanly in {elapsed:.1f}s.", flush=True)
    else:
        print(f"\n❌ Step {step_num} ({title}) failed with return code {res.returncode}.", flush=True)
        sys.exit(res.returncode)

def main():
    print("==========================================================", flush=True)
    print("   MASTER DATASET RECOMPILATION & RETRAINING PIPELINE", flush=True)
    print("==========================================================", flush=True)
    print(f"Target Holdout Sessions: ['session_2026-07-21_12-43-37', 'session_2026-07-25_15-16-32']", flush=True)
    
    # 1. Dataset Recompilation
    run_step(1, "Continuous 423 Hz Stance Dataset Recompilation", "build_facing_up_dataset.py")
    
    # 2. Stage 1 Stance Detector Retraining
    run_step(2, "Stage 1 Facing Up Stance TCN Retraining", "train_facing_up_detector.py")
    
    # 3. Stage 2 Shot Classifier Retraining
    run_step(3, "Stage 2 AdvancedTCN Shot Classifier Retraining", "train_and_evaluate_full_scorecard.py")
    
    # 4. Multi-Tier Telemetry Pipeline Evaluation
    run_step(4, "Multi-Tier Telemetry Pipeline Evaluation", "run_multitier_pipeline.py")
    
    print("\n" + "=" * 90, flush=True)
    print("🏆 MASTER RETRAINING & EVALUATION COMPLETE", flush=True)
    print("=" * 90 + "\n", flush=True)

if __name__ == "__main__":
    main()
