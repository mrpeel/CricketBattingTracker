# Shot Alignment Pipeline Report

**Generated:** 2026-07-19 12:03:42

**Sessions Processed:** 34  |  **With Polar:** 4  |  **Total Swing Shots:** 1941  |  **Polar Timestamp Refinements:** 134

## 1. Per-Session Alignment Confidence

| Session | Profile | Hz | Swings | Match Rate | MAE (s) | Fallback | Confidence | Polar Refined |
|---|---|---|---|---|---|---|---|---|
| session-2026-05-31_10-06-52 | 50hz_watch | 50 | 6 | 100% | 1.23 | 50% | MEDIUM | — |
| session-2026-05-31_14-12-10 | 50hz_watch | 50 | 47 | 94% | 1.00 | 23% | MEDIUM | — |
| session-2026-06-01_12-23-38 | 50hz_watch | 50 | 68 | 94% | 0.78 | 62% | HIGH | — |
| session-2026-06-05_12-29-59 | 50hz_watch | 50 | 22 | 100% | 1.40 | 9% | MEDIUM | — |
| session-2026-06-07_14-34-24 | 50hz_watch | 50 | 49 | 100% | 1.28 | 20% | MEDIUM | — |
| session-2026-06-08_12-22-26 | 50hz_watch | 50 | 60 | 100% | 7.46 | 20% | LOW | — |
| session-2026-06-09_12-16-49 | 50hz_watch | 50 | 63 | 100% | 1.84 | 38% | LOW | — |
| session-2026-06-11_12-27-53 | 50hz_watch | 50 | 56 | 96% | 1.12 | 29% | MEDIUM | — |
| session-2026-06-12_12-24-37 | 50hz_watch | 50 | 77 | 95% | 1.35 | 17% | MEDIUM | — |
| session-2026-06-13_10-59-04 | 50hz_watch | 50 | 43 | 95% | 1.29 | 26% | MEDIUM | — |
| session-2026-06-14_13-16-12 | 50hz_watch | 50 | 71 | 96% | 1.39 | 7% | MEDIUM | — |
| session-2026-06-15_12-21-37 | 50hz_watch | 50 | 21 | 95% | 1.00 | 5% | MEDIUM | — |
| session-2026-06-16_15-39-33 | 50hz_watch | 50 | 54 | 100% | 0.74 | 94% | HIGH | — |
| session-2026-06-18_12-23-09 | 50hz_watch | 50 | 76 | 89% | 1.26 | 13% | MEDIUM | — |
| session-2026-06-21_13-53-17 | 50hz_watch | 50 | 113 | 94% | 1.28 | 12% | MEDIUM | — |
| session-2026-06-22_12-27-26 | 50hz_watch | 50 | 46 | 93% | 1.01 | 37% | MEDIUM | — |
| session-2026-06-23_12-24-48 | 50hz_watch | 50 | 66 | 91% | 1.15 | 33% | MEDIUM | — |
| session-2026-06-25_12-25-07 | 50hz_watch | 50 | 67 | 97% | 1.18 | 27% | MEDIUM | — |
| session-2026-06-26_12-22-13 | 50hz_watch | 50 | 63 | 98% | 0.96 | 48% | MEDIUM | — |
| session-2026-06-27_14-12-40 | 50hz_watch | 50 | 38 | 84% | 0.76 | 53% | MEDIUM | — |
| session-2026-06-28_11-28-09 | 50hz_watch | 50 | 36 | 92% | 1.03 | 22% | MEDIUM | — |
| session-2026-06-29_12-21-45 | 50hz_watch | 50 | 65 | 100% | 1.30 | 23% | MEDIUM | — |
| session-2026-07-02_12-38-53 | 50hz_watch | 50 | 66 | 97% | 1.30 | 26% | MEDIUM | — |
| session-2026-07-04_12-19-20 | 50hz_watch | 50 | 56 | 100% | 1.15 | 36% | MEDIUM | — |
| session-2026-07-05_16-27-16 | 50hz_watch | 50 | 40 | 95% | 1.23 | 22% | MEDIUM | — |
| session-2026-07-06_12-25-05 | 50hz_watch | 50 | 39 | 90% | 1.31 | 15% | MEDIUM | — |
| session-2026-07-07_15-10-50 | 50hz_watch | 50 | 57 | 95% | 1.10 | 9% | MEDIUM | — |
| session-2026-07-09_12-19-05 | 50hz_watch | 50 | 45 | 96% | 1.25 | 13% | MEDIUM | — |
| session-2026-07-10_12-30-15 | 50hz_watch | 50 | 59 | 98% | 1.46 | 2% | MEDIUM | — |
| session-2026-07-11_12-51-39 | 50hz_watch_polar | 50 | 61 | 100% | 1.61 | 2% | LOW | ✅ 11 |
| session-2026-07-12_11-23-59 | 50hz_watch_polar | 50 | 66 | 98% | 1.43 | 6% | MEDIUM | ✅ 17 |
| session-2026-07-13_12-17-57 | 50hz_watch | 50 | 71 | 99% | 1.05 | 21% | MEDIUM | — |
| session-2026-07-17_12-30-41 | 50hz_watch_polar | 50 | 67 | 94% | 1.08 | 45% | MEDIUM | ✅ 38 |
| session-2026-07-18_13-44-09 | 100hz_watch_polar | 100 | 107 | 98% | 1.08 | 23% | MEDIUM | ✅ 68 |

> [!WARNING]
> **Low-confidence sessions requiring manual review:** session-2026-06-08_12-22-26, session-2026-06-09_12-16-49, session-2026-07-11_12-51-39

## 2. 1st Pass Detection — Threshold Sensitivity

Detection rate (%) for each shot quality class at each gyro threshold.
**Non-swing column = false positive rate (lower is better).**
Current threshold highlighted with `→`.

| Threshold (rad/s) | Excellent | Good | Poor | Edge | Miss | Non-Swing (FP) |
|---|---|---|---|---|---|---|
| **0.50** | 0% (0/0) | 98% (1461/1486) | 99% (288/291) | 0% (0/0) | 100% (164/164) | 98% (2051/2094) |
| **0.75** | 0% (0/0) | 98% (1449/1486) | 98% (286/291) | 0% (0/0) | 99% (162/164) | 97% (2032/2094) |
| **1.00** | 0% (0/0) | 97% (1435/1486) | 98% (284/291) | 0% (0/0) | 98% (161/164) | 96% (2010/2094) |
| **1.25** | 0% (0/0) | 96% (1427/1486) | 97% (283/291) | 0% (0/0) | 98% (161/164) | 95% (1988/2094) |
| **1.50** ← | 0% (0/0) | 96% (1420/1486) | 97% (283/291) | 0% (0/0) | 98% (161/164) | 94% (1970/2094) |
| **1.75** | 0% (0/0) | 95% (1413/1486) | 97% (283/291) | 0% (0/0) | 98% (161/164) | 93% (1946/2094) |
| **2.00** | 0% (0/0) | 95% (1412/1486) | 97% (283/291) | 0% (0/0) | 97% (159/164) | 92% (1934/2094) |
| **2.25** | 0% (0/0) | 95% (1407/1486) | 97% (283/291) | 0% (0/0) | 96% (158/164) | 92% (1918/2094) |
| **2.50** | 0% (0/0) | 94% (1401/1486) | 97% (282/291) | 0% (0/0) | 96% (157/164) | 91% (1898/2094) |
| **2.75** | 0% (0/0) | 94% (1393/1486) | 97% (282/291) | 0% (0/0) | 96% (157/164) | 89% (1873/2094) |
| **3.00** | 0% (0/0) | 93% (1378/1486) | 96% (279/291) | 0% (0/0) | 95% (155/164) | 87% (1831/2094) |
| **3.25** | 0% (0/0) | 91% (1354/1486) | 94% (274/291) | 0% (0/0) | 95% (155/164) | 86% (1797/2094) |
| **3.50** | 0% (0/0) | 90% (1338/1486) | 93% (272/291) | 0% (0/0) | 93% (153/164) | 84% (1756/2094) |
| **3.75** | 0% (0/0) | 89% (1318/1486) | 92% (267/291) | 0% (0/0) | 91% (149/164) | 82% (1721/2094) |
| **4.00** | 0% (0/0) | 87% (1300/1486) | 91% (265/291) | 0% (0/0) | 88% (145/164) | 81% (1688/2094) |

**Recommended threshold: `4.00 rad/s`** (selected to maximise good/excellent recall while minimising false positives)

## 3. 2nd Pass Missed Shot Recovery

**Total shots missed at standard threshold (1.5 rad/s):** 77

| Recovery Method | Shots Recovered | Rate |
|---|---|---|
| Lowered threshold (0.75 rad/s) | 33 | 43% |
| Peak prominence detector | 11 | 14% |
| Unrecoverable (no signal at any threshold) | 33 | 43% |

**Total potentially recoverable missed shots: 44/77 (57%)**

## 4. Peak Detection Algorithm Comparison

Results across all sessions (1941 swing shots).

| Algorithm | Detected | Rate | Notes |
|---|---|---|---|
| Threshold + DP (current) | 1864 | 96.0% | `1.5 rad/s` |
| Peak Prominence (scipy) | 1898 | 97.8% | prominence ≥ 0.5 rad/s |
| Envelope RMS Detector | 1809 | 93.2% | 0.1s RMS window, top 20% |

**Recommended algorithm: `scipy peak prominence`**

> [!IMPORTANT]
> A different algorithm outperformed the current system. Consider replacing the peak detection step in `automate_pipeline.py` with the `scipy peak prominence` approach.

## 5. Polar Timestamp Refinement Summary

Impact timestamps refined using 500Hz Polar accelerometer: **134 shots** across 4 Polar sessions.

Polar data at 500Hz provides ±2ms timestamp resolution vs. ±20ms from the 50Hz watch gyro. The updated `ground_truth_aligned.csv` files now contain the best available impact timestamps for all sessions.

## 6. Recommended Actions

1. Update `WATCH_GYRO_THRESHOLD` in `automate_pipeline.py` from `1.5` to `4.00` rad/s
2. Consider replacing threshold-based peak detection with `scipy peak prominence` in `automate_pipeline.py`
3. Manually review low-confidence sessions and consider re-running `automate_pipeline.py`: session-2026-06-08_12-22-26, session-2026-06-09_12-16-49, session-2026-07-11_12-51-39
4. Consider adopting a 2-stage detection threshold: primary=4.00 rad/s, recovery=0.75 rad/s for shots initially missed (potential recovery: 44 shots)
