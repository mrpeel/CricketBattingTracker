#!/usr/bin/env python3
"""
pipelines/export_onnx_production.py — Export Retrained Stage 2 Model to ONNX Asset

Exports the newly retrained PyTorch Stage 2 AdvancedTCN model (tcn_ultimate_baseline.pt)
to ONNX format and updates the companion app production asset at:
  app/src/main/assets/models/tcn_ultimate_baseline.onnx
"""

import os
import sys
import shutil
import torch
import torch.nn as nn

ROOT_DIR = "/Users/neilkloot/Code/CricketBattingTracker"
sys.path.append(os.path.join(ROOT_DIR, "pipelines"))
from train_and_evaluate_full_scorecard import AdvancedTCN, NUM_FEATURES, WINDOW_LEN

MODEL_PT_PATH = os.path.join(ROOT_DIR, "pipelines", "tcn_ultimate_baseline.pt")
MODEL_ONNX_PATH = os.path.join(ROOT_DIR, "pipelines", "tcn_ultimate_baseline.onnx")
APP_ASSETS_DIR = os.path.join(ROOT_DIR, "app", "src", "main", "assets", "models")
APP_ONNX_PATH = os.path.join(APP_ASSETS_DIR, "tcn_ultimate_baseline.onnx")

def main():
    print("==========================================================", flush=True)
    print("   EXPORTING RETRAINED STAGE 2 ADVANCED TCN TO ONNX ASSET", flush=True)
    print("==========================================================", flush=True)
    
    if not os.path.exists(MODEL_PT_PATH):
        print(f"❌ Error: Model checkpoint missing at {MODEL_PT_PATH}", flush=True)
        sys.exit(1)
        
    device = torch.device("cpu")
    print(f"Loading PyTorch checkpoint from {MODEL_PT_PATH}...", flush=True)
    model = AdvancedTCN(in_ch=NUM_FEATURES, num_classes=10).to(device)

    model.load_state_dict(torch.load(MODEL_PT_PATH, map_location=device))
    model.eval()
    
    print("Exporting ONNX opset 18 model...", flush=True)
    dummy_input = torch.randn(1, NUM_FEATURES, WINDOW_LEN, device=device)
    torch.onnx.export(
        model,
        dummy_input,
        MODEL_ONNX_PATH,
        export_params=True,
        opset_version=18,
        do_constant_folding=True,
        input_names=['input_imu_stream'],
        output_names=['output_logits'],
        dynamic_axes={
            'input_imu_stream': {0: 'batch_size', 2: 'sequence_length'},
            'output_logits': {0: 'batch_size', 2: 'sequence_length'}
        }
    )
    
    os.makedirs(APP_ASSETS_DIR, exist_ok=True)
    shutil.copy2(MODEL_ONNX_PATH, APP_ONNX_PATH)
    
    print(f"✅ ONNX model exported -> {MODEL_ONNX_PATH}")
    print(f"✅ Production App Asset Updated -> {APP_ONNX_PATH}")
    print("==========================================================\n", flush=True)

if __name__ == "__main__":
    main()
