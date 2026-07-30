# Hybrid TCN-Detection + Conv-LSTM Classification Pipeline Results

**Holdout Session**: `session_2026-07-18_13-44-09`  
**Window Length**: 3.0 seconds (1,269 samples at 423 Hz, [-2.0s to +1.0s])  
**Date**: 2026-07-29 21:34

---

## 📊 End-to-End System Performance Scorecard

| Metric | Value | Notes |
|---|---|---|
| **Ground-Truth Physical Shots** | **114 shots** | Total physical shots played in holdout session |
| **Stage 1 TCN Detection Recall** | **87.7%** | **100 of 114 shots detected** |
| **Stage 2 Conv-LSTM Window Classification Accuracy** | **39.47%** | Accuracy on 3.0s detected candidate swing windows |
| **End-to-End Physical Shots Correctly Captured** | **45 of 114 shots** | **39.47% Total Coverage Rate** |

---

## 🎯 Per-Class Shot Accuracy on Detected Windows (Conv-LSTM Stage 2)

| Shot Class | Detected Shots | Correctly Classified | Classification Accuracy |
|---|---|---|---|
| **Pull** | 20 | 5 | **25.0%** |
| **Defence** | 38 | 20 | **52.6%** |
| **Flick** | 12 | 0 | **0.0%** |
| **Drive** | 12 | 2 | **16.7%** |
| **Glance** | 0 | 0 | N/A |
| **Sweep** | 12 | 8 | **66.7%** |
| **Cut** | 14 | 9 | **64.3%** |
| **Slog** | 6 | 1 | **16.7%** |
