#!/usr/bin/env python3
"""
augment_unified_dataset.py — Class-Balanced 10x Synthetic Data Augmentation

Generates synthetic variants of training session Parquet files in poc_unified_dataset:
  - 3D Quaternion Rotational Jitter (+-8 deg random 3D axis rotation)
  - Kinematic Force Amplitude Scaling (+-10% watch and polar acc/gyro scaling)
  - Gaussian Sensor Noise Injection (sigma_acc = 0.05 m/s^2, sigma_gyro = 0.02 rad/s)
  - Class-Balanced Variant Allocation (rare shots get 15-20x variants, common shots 5x)
"""
import os
import sys
import glob
import numpy as np
import pandas as pd

DATASET_DIR = "/Users/neilkloot/Code/Batting Sensor Stats/poc_unified_dataset"
HOLDOUT     = "session_2026-07-18_13-44-09"

def random_rotation_quaternion(max_angle_deg=8.0):
    """Generate a random 3D perturbation quaternion with angle in [-max_angle_deg, +max_angle_deg]."""
    angle_rad = np.radians(np.random.uniform(-max_angle_deg, max_angle_deg))
    axis = np.random.normal(size=3)
    norm = np.linalg.norm(axis)
    if norm < 1e-9:
        return np.array([0.0, 0.0, 0.0, 1.0], dtype=np.float32)
    axis = axis / norm
    
    sin_a = np.sin(angle_rad / 2.0)
    cos_a = np.cos(angle_rad / 2.0)
    
    return np.array([axis[0] * sin_a, axis[1] * sin_a, axis[2] * sin_a, cos_a], dtype=np.float32)

def multiply_quats_vectorized(q1, q2_arr):
    """Multiply a single quaternion q1 by an array of quaternions q2_arr [N, 4]."""
    x1, y1, z1, w1 = q1
    x2 = q2_arr[:, 0]; y2 = q2_arr[:, 1]; z2 = q2_arr[:, 2]; w2 = q2_arr[:, 3]
    
    rx = w1*x2 + x1*w2 + y1*z2 - z1*y2
    ry = w1*y2 - x1*z2 + y1*w2 + z1*x2
    rz = w1*z2 + x1*y2 - y1*x2 + z1*w2
    rw = w1*w2 - x1*x2 - y1*y2 - z1*z2
    
    # Normalize
    norms = np.sqrt(rx**2 + ry**2 + rz**2 + rw**2)
    norms = np.where(norms < 1e-9, 1.0, norms)
    return np.column_stack([rx / norms, ry / norms, rz / norms, rw / norms]).astype(np.float32)

def rotate_vectors_quat(q_arr, v_arr):
    """Vectorized quaternion rotation: rotates 3D vectors v_arr by quaternions q_arr."""
    qx = q_arr[:, 0]; qy = q_arr[:, 1]; qz = q_arr[:, 2]; qw = q_arr[:, 3]
    vx = v_arr[:, 0]; vy = v_arr[:, 1]; vz = v_arr[:, 2]
    
    tx = 2.0 * (qy * vz - qz * vy)
    ty = 2.0 * (qz * vx - qx * vz)
    tz = 2.0 * (qx * vy - qy * vx)
    
    rx = vx + qw * tx + (qy * tz - qz * ty)
    ry = vy + qw * ty + (qz * tx - qx * tz)
    rz = vz + qw * tz + (qx * ty - qy * vx)
    
    return np.column_stack([rx, ry, rz]).astype(np.float32)

def augment_session_dataframe(df, k):
    """Apply physical augmentation transformations to a session DataFrame."""
    df_aug = df.copy()
    n_rows = len(df_aug)
    
    # 1. 3D Quaternion Rotational Jitter
    q_jitter = random_rotation_quaternion(max_angle_deg=8.0)
    q_orig = df_aug[['w_rot_qx', 'w_rot_qy', 'w_rot_qz', 'w_rot_qw']].values.astype(np.float32)
    q_new = multiply_quats_vectorized(q_jitter, q_orig)
    
    df_aug['w_rot_qx'] = q_new[:, 0]
    df_aug['w_rot_qy'] = q_new[:, 1]
    df_aug['w_rot_qz'] = q_new[:, 2]
    df_aug['w_rot_qw'] = q_new[:, 3]
    
    # Re-calculate world-frame acceleration and gyroscope vectors using new quaternions
    w_acc_raw = df_aug[['w_acc_x', 'w_acc_y', 'w_acc_z']].values.astype(np.float32)
    w_gyro_raw = df_aug[['w_gyro_x', 'w_gyro_y', 'w_gyro_z']].values.astype(np.float32)
    
    w_acc_world = rotate_vectors_quat(q_new, w_acc_raw)
    w_gyro_world = rotate_vectors_quat(q_new, w_gyro_raw)
    
    # 2. Kinematic Force Amplitude Scaling (+-10%)
    s_watch_acc  = np.random.uniform(0.90, 1.10)
    s_watch_gyro = np.random.uniform(0.90, 1.10)
    s_polar_acc  = np.random.uniform(0.90, 1.10)
    s_polar_gyro = np.random.uniform(0.90, 1.10)
    
    df_aug['w_acc_x'] *= s_watch_acc
    df_aug['w_acc_y'] *= s_watch_acc
    df_aug['w_acc_z'] *= s_watch_acc
    
    df_aug['w_gyro_x'] *= s_watch_gyro
    df_aug['w_gyro_y'] *= s_watch_gyro
    df_aug['w_gyro_z'] *= s_watch_gyro
    
    df_aug['w_acc_world_x'] = w_acc_world[:, 0] * s_watch_acc
    df_aug['w_acc_world_y'] = w_acc_world[:, 1] * s_watch_acc
    df_aug['w_acc_world_z'] = w_acc_world[:, 2] * s_watch_acc
    
    df_aug['w_gyro_world_x'] = w_gyro_world[:, 0] * s_watch_gyro
    df_aug['w_gyro_world_y'] = w_gyro_world[:, 1] * s_watch_gyro
    df_aug['w_gyro_world_z'] = w_gyro_world[:, 2] * s_watch_gyro
    
    df_aug['p_acc_x'] *= s_polar_acc
    df_aug['p_acc_y'] *= s_polar_acc
    df_aug['p_acc_z'] *= s_polar_acc
    
    df_aug['p_gyro_x'] *= s_polar_gyro
    df_aug['p_gyro_y'] *= s_polar_gyro
    df_aug['p_gyro_z'] *= s_polar_gyro
    
    # 3. Sensor Noise Injection
    acc_cols = ['w_acc_x', 'w_acc_y', 'w_acc_z', 'w_acc_world_x', 'w_acc_world_y', 'w_acc_world_z', 'p_acc_x', 'p_acc_y', 'p_acc_z']
    gyro_cols = ['w_gyro_x', 'w_gyro_y', 'w_gyro_z', 'w_gyro_world_x', 'w_gyro_world_y', 'w_gyro_world_z', 'p_gyro_x', 'p_gyro_y', 'p_gyro_z']
    
    for c in acc_cols:
        df_aug[c] += np.random.normal(0, 0.05, size=n_rows).astype(np.float32)
        
    for c in gyro_cols:
        df_aug[c] += np.random.normal(0, 0.02, size=n_rows).astype(np.float32)
        
    return df_aug

def main():
    print("============================================================")
    print("  Class-Balanced 10x Synthetic Data Augmentation Pipeline")
    print("============================================================")
    
    all_files = glob.glob(os.path.join(DATASET_DIR, "*_unified.parquet"))
    # Filter out holdout and previously generated augmented files
    orig_files = [f for f in all_files if (HOLDOUT not in f) and ('_aug_' not in f)]
    
    print(f"Found {len(orig_files)} original training sessions (excluding holdout {HOLDOUT}).\n")
    
    total_aug_created = 0
    for f_path in orig_files:
        base_name = os.path.basename(f_path).replace("_unified.parquet", "")
        df = pd.read_parquet(f_path)
        
        # Check label distribution to set class-balanced variant count
        unique_labels = set(df['label'].unique())
        
        if 'Glance' in unique_labels:
            n_variants = 20  # Rare class: high augmentation
        elif ('Sweep' in unique_labels) or ('Cut' in unique_labels):
            n_variants = 15
        elif ('Flick' in unique_labels) or ('Slog' in unique_labels):
            n_variants = 10
        else:
            n_variants = 5   # Common classes (Defence, Drive, Pull)
            
        print(f"[{base_name}] Labels: {unique_labels - {'no_shot', 'pre_shot'}} -> Allocating {n_variants} synthetic variants")
        
        for k in range(1, n_variants + 1):
            out_path = os.path.join(DATASET_DIR, f"{base_name}_aug_{k}_unified.parquet")
            # Skip if already exists
            if os.path.exists(out_path):
                continue
                
            df_aug = augment_session_dataframe(df, k)
            df_aug.to_parquet(out_path, index=False)
            total_aug_created += 1
            
    print(f"\n✅ Synthetic Data Augmentation Complete! Created {total_aug_created} new augmented session files.")

if __name__ == "__main__":
    main()
