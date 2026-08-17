#!/usr/bin/env python3
"""
pipelines/export_facing_up_to_onnx.py — Export Stage 1 Facing Up Stance Detector to ONNX Asset

Exports the trained PyTorch FacingUpTCN model (facing_up_tcn_model.pt) to a self-contained
ONNX format with dynamic batch support and updates the companion app asset at:
  app/src/main/assets/models/facing_up_detector.onnx
"""

import os
import sys
import shutil
import torch
import torch.nn as nn

ROOT_DIR = "/Users/neilkloot/Code/CricketBattingTracker"
sys.path.append(os.path.join(ROOT_DIR, "pipelines"))
from train_facing_up_detector import FacingUpTCN

MODEL_PT_PATH = os.path.join(ROOT_DIR, "facing_up_tcn_model.pt")
MODEL_ONNX_PATH = os.path.join(ROOT_DIR, "pipelines", "facing_up_detector.onnx")
APP_ASSETS_DIR = os.path.join(ROOT_DIR, "app", "src", "main", "assets", "models")
APP_ONNX_PATH = os.path.join(APP_ASSETS_DIR, "facing_up_detector.onnx")

def main():
    print("==========================================================", flush=True)
    print("   EXPORTING STAGE 1 FACING UP DETECTOR TO ONNX ASSET", flush=True)
    print("==========================================================", flush=True)

    if not os.path.exists(MODEL_PT_PATH):
        print(f"❌ Error: Model checkpoint missing at {MODEL_PT_PATH}", flush=True)
        sys.exit(1)

    device = torch.device("cpu")
    print(f"Loading PyTorch checkpoint from {MODEL_PT_PATH}...", flush=True)
    model = FacingUpTCN(in_channels=12, num_filters=32).to(device)
    model.load_state_dict(torch.load(MODEL_PT_PATH, map_location=device))
    model.eval()

    print("Exporting ONNX opset 18 model with dynamic batch size...", flush=True)
    dummy_input = torch.randn(1, 12, 423, device=device)
    torch.onnx.export(
        model,
        dummy_input,
        MODEL_ONNX_PATH,
        export_params=True,
        opset_version=18,
        do_constant_folding=True,
        input_names=['input_imu_12ch'],
        output_names=['output_logit'],
        dynamic_axes={
            'input_imu_12ch': {0: 'batch_size'},
            'output_logit': {0: 'batch_size'}
        },
        dynamo=False
    )

    os.makedirs(APP_ASSETS_DIR, exist_ok=True)
    shutil.copy2(MODEL_ONNX_PATH, APP_ONNX_PATH)

    print(f"✅ ONNX model exported -> {MODEL_ONNX_PATH}")
    print(f"✅ Production App Asset Updated -> {APP_ONNX_PATH}")
    print(f"   Size: {os.path.getsize(APP_ONNX_PATH)} bytes")
    print("==========================================================\n", flush=True)

if __name__ == "__main__":
    main()
