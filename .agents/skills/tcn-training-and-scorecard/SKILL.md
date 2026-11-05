---
name: tcn-training-and-scorecard
description: >-
  Use this skill when training, tuning, or evaluating the 10-layer
  BatPlaneGeometryThreeFamilyTCN model, running the authoritative multi-tier
  ground-truth scorecard, modifying Stage 1/Stage 2 gates, or exporting the
  production ONNX model (tcn_ultimate_baseline.onnx) to Android assets.
---

# TCN Model Training, Scorecard Evaluation & ONNX Export Runbook

Follow this workflow whenever modifying `pipelines/telemetry_engine.py`, `pipelines/train_and_evaluate_full_scorecard.py`, `pipelines/dataset_splits.json`, or `TcnModelRunner.kt`.

## 1. Strict Reporting & Architecture Rules
1. **Ground-Truth Holdout Only**: NEVER report training accuracy or synthetic cross-validation scores as model performance. Always report the **12-session Stratified Holdout Test Set** (714 physical GT shots) and **Clean Benchmark** metrics from [full_dataset_training_scorecard.md](../../../full_dataset_training_scorecard.md), comparing **before vs. after**.
2. **100% Python ↔ Kotlin Parity**:
   - Any change to Stage 1 stance thresholds (`0.55 / 0.35 / 1.8 rad/s / 200ms / 4.0s`), Stage 2 `head_reject` threshold (`0.35`), Power Drive soft-routing ($\alpha = 0.85$), closed-form sub-head recovery, or mount-aware consistency gates in `pipelines/telemetry_engine.py` MUST be mirrored identically in [TcnModelRunner.kt](../../../app/src/main/java/com/mrpeel/cricketbattingtracker/ml/TcnModelRunner.kt).
3. **Self-Contained ONNX Export**:
   - Always export `tcn_ultimate_baseline.onnx` with `dynamo=False` and `opset_version=18` so weights are embedded in a single file (`~7.1 MB`) without external `.data` files that fail in Android APK assets.

## 2. Commands

### Evaluate Current Model Without Retraining
To run the full multi-tier scorecard across the 12-session Holdout Test Set and Clean Benchmark using the existing checkpoint:
```bash
python3 pipelines/train_and_evaluate_full_scorecard.py --eval-only
```

### Full Retraining + Authoritative Scorecard Evaluation
Trains `BatPlaneGeometryThreeFamilyTCN` using joint 9-class `NLLLoss` + cross-family Power Drive suppression + on-the-fly kinematic augmentation (with automatic cache validation via `candidate_windows_meta.json`), selects the best checkpoint by Validation Macro-F1 across the 9 validation sessions, evaluates the 12-session Holdout Test Set, and exports `tcn_ultimate_baseline.onnx` + `tcn_norm_stats.json` if the Production Quality Gate passes:
```bash
python3 pipelines/train_and_evaluate_full_scorecard.py
```
All terminal output is automatically tee-logged to `pipelines/training_logs/latest.log`.

## 3. Production Quality Gate & Verification
After running training or modifying inference logic:
1. Inspect [full_dataset_training_scorecard.md](../../../full_dataset_training_scorecard.md) and confirm the **Production Quality Gate** passed (`Holdout Precision >= 75%`, `Global Precision >= 70%`, `Holdout F1 >= 50%`, and no regression against the current baseline of ~92.4% Holdout Recall / ~91.7% Holdout Precision / ~84.1% Holdout Classification Accuracy).
2. Run the Android & Wear OS unit test suites to verify Kotlin ONNX runner parity:
   ```bash
   ./gradlew :app:testDebugUnitTest :wear:testDebugUnitTest
   ```
3. Assemble 16 KB page-aligned release APKs if `tcn_ultimate_baseline.onnx` or `tcn_norm_stats.json` was updated:
   ```bash
   ./gradlew :app:assembleRelease :wear:assembleRelease
   ```
