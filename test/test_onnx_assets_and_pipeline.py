#!/usr/bin/env python3
"""
test/test_onnx_assets_and_pipeline.py

Automated integrity tests verifying:
1. All ONNX models in app/src/main/assets/models/ are 100% self-contained (no external .data files).
2. ONNX models initialize cleanly in memory from raw byte buffers (matching Android APK asset loading).
3. Stage 1 (facing_up_detector) and Stage 2 (tcn_ultimate_baseline) produce valid outputs matching expected shapes.
4. Normalization statistics JSON exists, is valid, and matches 28 channels.
"""

import os
import json
import unittest
import numpy as np
import onnx
import onnxruntime as ort

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS_MODELS_DIR = os.path.join(ROOT_DIR, "app", "src", "main", "assets", "models")


class TestOnnxAssetsAndPipeline(unittest.TestCase):

    def test_no_external_data_files_in_assets(self):
        """Ensure no .data sidecars exist in the APK asset bundle."""
        for root, _, files in os.walk(ASSETS_MODELS_DIR):
            for f in files:
                self.assertFalse(
                    f.endswith(".data"),
                    f"External data file found: {f}. Android APK asset loading requires self-contained ONNX models!"
                )

    def test_facing_up_detector_in_memory_loading_and_inference(self):
        """Test Stage 1 Facing Up Detector ONNX model from in-memory byte buffer."""
        model_path = os.path.join(ASSETS_MODELS_DIR, "facing_up_detector.onnx")
        self.assertTrue(os.path.exists(model_path), "facing_up_detector.onnx is missing")

        # Verify protobuf has no external data references
        onnx_model = onnx.load(model_path)
        for init in onnx_model.graph.initializer:
            self.assertEqual(
                len(init.external_data), 0,
                f"Initializer {init.name} contains external data reference"
            )

        # In-memory session initialization
        with open(model_path, "rb") as f:
            model_bytes = f.read()

        session = ort.InferenceSession(model_bytes)
        self.assertEqual(session.get_inputs()[0].name, "input_imu_12ch")

        # Run dummy inference
        dummy_input = np.random.randn(1, 12, 423).astype(np.float32)
        outputs = session.run(None, {"input_imu_12ch": dummy_input})
        self.assertEqual(len(outputs), 1)
        self.assertIn(outputs[0].shape, [(1,), (1, 1)])

        # Run batch inference (e.g. batch size 8)
        batch_input = np.random.randn(8, 12, 423).astype(np.float32)
        batch_outputs = session.run(None, {"input_imu_12ch": batch_input})
        self.assertIn(batch_outputs[0].shape, [(8,), (8, 1)])

    def test_tcn_ultimate_baseline_in_memory_loading_and_inference(self):
        """Test Stage 2 TCN Window Baseline ONNX model from in-memory byte buffer."""
        model_path = os.path.join(ASSETS_MODELS_DIR, "tcn_ultimate_baseline.onnx")
        self.assertTrue(os.path.exists(model_path), "tcn_ultimate_baseline.onnx is missing")

        # Verify protobuf has no external data references
        onnx_model = onnx.load(model_path)
        for init in onnx_model.graph.initializer:
            self.assertEqual(
                len(init.external_data), 0,
                f"Initializer {init.name} contains external data reference"
            )

        # In-memory session initialization
        with open(model_path, "rb") as f:
            model_bytes = f.read()

        session = ort.InferenceSession(model_bytes)
        self.assertEqual(session.get_inputs()[0].name, "input_imu_stream")

        # Run dummy inference (1, 28, 2048)
        dummy_input = np.random.randn(1, 28, 2048).astype(np.float32)
        outputs = session.run(None, {"input_imu_stream": dummy_input})
        self.assertEqual(len(outputs), 1)
        self.assertEqual(outputs[0].shape, (1, 10, 2048))

    def test_norm_stats_integrity(self):
        """Verify tcn_norm_stats.json has exactly 28 median and 28 MAD elements."""
        stats_path = os.path.join(ASSETS_MODELS_DIR, "tcn_norm_stats.json")
        self.assertTrue(os.path.exists(stats_path), "tcn_norm_stats.json is missing")

        with open(stats_path, "r") as f:
            stats = json.load(f)

        self.assertIn("median", stats)
        self.assertIn("mad", stats)
        self.assertEqual(len(stats["median"]), 28)
        self.assertEqual(len(stats["mad"]), 28)
        for val in stats["mad"]:
            self.assertGreater(val, 0.0, "MAD scale factor must be strictly positive")


if __name__ == "__main__":
    unittest.main()
