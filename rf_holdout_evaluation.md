# Production Random Forest Model Holdout Evaluation

**Holdout Session**: `session_2026-07-18_13-44-09`  
**Training Set**: 1139 sessions (3056 ground-truth shots)  
**Evaluation Date**: 2026-07-28 17:51

---

## 1. Raw Peak Detection Audit (Detection Phase)

Evaluated by running raw peak detection (gyroscope magnitude prominence $\ge 5.0\text{ rad/s}$ + backswing load check $\ge 2.0\text{ rad/s}$ & stance stability lock) directly over `WatchGyroscope.bin.gz` and `PolarSense` binary files for `session_2026-07-18_13-44-09`:

| Metric | Value | Notes |
|---|---|---|
| **Session Duration** | **21.57 min** | Total recorded sensor duration |
| **Narrated Ground-Truth Shots** | **114** | Actual physical shots played |
| **Raw Candidate Detections** | **177** | Candidate peak detections from raw sensor stream |
| **True Positives (TP)** | **85** | Detected peaks matching narrated shots (±1.5s) |
| **False Positives (FP)** | **92** | Non-shot movements triggering detection |
| **Missed Shots (FN)** | **29** | Ground-truth shots missed by peak detector |
| **Detection Recall** | **74.6%** | Proportion of ground-truth shots detected |
| **Detection Precision** | **48.0%** | Proportion of detected peaks that were real shots |
| **Detection $F_1$ Score** | **0.584** | Harmonic mean of detection precision & recall |
| **False Alarm Rate** | **4.27 FP/min** | False detections per minute of session |

---

## 2. Holdout Shot Classification Performance (Classification Phase)

Evaluated on `session_2026-07-18_13-44-09` ground-truth shots using the Dual-Hand Random Forest (26 features) trained strictly on all other sessions:

* **Overall Holdout Classification Accuracy**: **35.87%**

### Per-Class Holdout Accuracy

| Shot Class | Ground-Truth Count | Model Accuracy |
|---|---|---|
| **CUT/PUNCH** | 17 | **17.6%** |
| **DEFLECTION/GUIDE** | 18 | **22.2%** |
| **DRIVE/DEFENCE** | 21 | **85.7%** |
| **GLANCE/FLICK** | 9 | **0.0%** |
| **POWER DRIVE** | 1 | **0.0%** |
| **PULL/HOOK** | 14 | **0.0%** |
| **SLOG** | 4 | **0.0%** |
| **SWEEP** | 8 | **100.0%** |
