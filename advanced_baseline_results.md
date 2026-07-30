# Advanced 423 Hz Baseline Test Results

**Holdout Session**: `session_2026-07-18_13-44-09` (114 Ground-Truth Physical Shots)  
**Date**: 2026-07-30 10:33

---

## 📊 Advanced Baseline Enhancements Scorecard Table

| Test ID | Enhancement Description | Detection Recall (±0.5s) | Holdout Shot Classification Accuracy | Physical Shots Captured (out of 114) | **Total Ground-Truth Coverage Rate** |
|---|---|:---:|:---:|:---:|:---:|
| **Test 1** | Non-Causal Padding Swap | **47.4%** | **69.41%** | **37** | **32.46%** |
| **Test 2** | Skip-Head Feature Aggregation | **50.0%** | **47.33%** | **27** | **23.68%** |
| **Test 3** | Classification Focal Loss | **92.1%** | **52.02%** | **55** | **48.25%** |
| **Test 4** | Two-Stage Freeze Training | **36.8%** | **50.03%** | **21** | **18.42%** |
| **Test 5 (ALL COMBINED)** | Ultimate Baseline | **98.2%** | **64.84%** | **73** | **64.04%** |

---

## 🏆 Reference Benchmarks Comparison

| Reference Model / Architecture | Detection Recall | Subset Classification Accuracy | Physical Shots Captured (out of 114) | Total Coverage Rate | Notes |
|---|:---:|:---:|:---:|:---:|---|
| **Production Random Forest** | 74.6% (85 shots) | 35.87% | **30 physical shots** | **26.76%** | Severe training overfitting |
| **Original Baseline TCN (Causal)** | 92.1% (105 shots) | 52.40% | **55 physical shots** | **48.25%** | Original baseline reference |
