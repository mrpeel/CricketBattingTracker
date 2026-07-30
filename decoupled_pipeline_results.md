# Decoupled 2-Model Pipeline Results

**Holdout Session**: `session_2026-07-18_13-44-09`  
**Window Length**: 1.8 seconds (761 samples at 423 Hz)  
**Date**: 2026-07-29 06:20

---

## 📊 End-to-End System Performance Scorecard

| Metric | Value | Notes |
|---|---|---|
| **Ground-Truth Physical Shots** | **114 shots** | Total physical shots played in session |
| **Model 1 Detection Recall** | **86.0%** | **98 of 114 shots detected** |
| **Model 2 Window Classification Accuracy** | **48.15%** | Accuracy on detected shot candidate windows |
| **End-to-End Correct Shots Captured** | **52 of 114 shots** | **45.61% Total Coverage** |

---

## 🎯 Per-Class Shot Accuracy on Detected Windows

| Shot Class | Detected Shots | Correctly Classified | Accuracy |
|---|---|---|---|
| **Pull** | 19 | 7 | **36.8%** |
| **Defence** | 36 | 28 | **77.8%** |
| **Flick** | 11 | 1 | **9.1%** |
| **Drive** | 12 | 4 | **33.3%** |
| **Glance** | 0 | 0 | N/A |
| **Sweep** | 12 | 5 | **41.7%** |
| **Cut** | 12 | 7 | **58.3%** |
| **Slog** | 6 | 0 | **0.0%** |
