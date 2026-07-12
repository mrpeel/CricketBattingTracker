#!/usr/bin/env python3
import os
import glob
import random
import cv2
import numpy as np
import mediapipe as mp

videos_root = "/Users/neilkloot/Code/Batting Sensor Stats/cricshot10k/Videos"
model_path = "scratch/pose_landmarker_full.task"

def setup_detector():
    BaseOptions = mp.tasks.BaseOptions
    PoseLandmarker = mp.tasks.vision.PoseLandmarker
    PoseLandmarkerOptions = mp.tasks.vision.PoseLandmarkerOptions
    VisionRunningMode = mp.tasks.vision.RunningMode

    options = PoseLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=model_path),
        running_mode=VisionRunningMode.IMAGE,
        output_segmentation_masks=False
    )
    return PoseLandmarker.create_from_options(options)

def main():
    random.seed(42)
    
    if not os.path.exists(model_path):
        print(f"❌ MediaPipe model not found at {model_path}")
        return
        
    detector = setup_detector()
    
    # Gather all video files
    video_files = glob.glob(os.path.join(videos_root, "**/*.avi"), recursive=True) + \
                  glob.glob(os.path.join(videos_root, "**/*.mp4"), recursive=True)
                  
    if not video_files:
        print("❌ No videos found in dataset.")
        return
        
    print(f"Total videos in dataset: {len(video_files)}")
    sample_size = min(100, len(video_files))
    sampled_videos = random.sample(video_files, sample_size)
    print(f"Sampling {sample_size} videos to test MediaPipe tracking quality...")

    detection_rates = []
    skipped_videos = 0

    for idx, v_path in enumerate(sampled_videos):
        cap = cv2.VideoCapture(v_path)
        if not cap.isOpened():
            skipped_videos += 1
            continue
            
        total_frames = 0
        detected_frames = 0
        
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
                
            total_frames += 1
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
            results = detector.detect(mp_image)
            
            if results.pose_landmarks and len(results.pose_landmarks) > 0:
                landmarks = results.pose_landmarks[0]
                hip_l, hip_r = landmarks[23], landmarks[24]
                # Hips presence threshold
                if hip_l.presence > 0.5 and hip_r.presence > 0.5:
                    detected_frames += 1
                    
        cap.release()
        
        if total_frames > 0:
            rate = (detected_frames / total_frames) * 100.0
            detection_rates.append(rate)
            
        if (idx + 1) % 20 == 0:
            print(f"   Analyzed {idx + 1} / {sample_size} videos...")

    if not detection_rates:
        print("❌ No valid video analysis results.")
        return

    # Calculate statistics
    mean_rate = np.mean(detection_rates)
    median_rate = np.median(detection_rates)
    min_rate = np.min(detection_rates)
    max_rate = np.max(detection_rates)
    failures = sum(1 for r in detection_rates if r < 50.0)

    print("\n============================================================")
    print("📊  MediaPipe Pose Tracking Quality Diagnostics")
    print("============================================================")
    print(f"Total Videos Analyzed         : {len(detection_rates)}")
    print(f"Average Frame Detection Rate  : {mean_rate:.2f}%")
    print(f"Median Frame Detection Rate   : {median_rate:.2f}%")
    print(f"Minimum Frame Detection Rate  : {min_rate:.2f}%")
    print(f"Maximum Frame Detection Rate  : {max_rate:.2f}%")
    print(f"Videos with <50% Tracking Rate: {failures} ({failures/len(detection_rates)*100.0:.1f}%)")
    print("------------------------------------------------------------")
    if mean_rate > 85.0:
        print("🟢  MediaPipe is successfully tracking the player in the majority of frames.")
        print("    The bottleneck lies in classifier boundaries or temporal segment alignment.")
    elif mean_rate > 60.0:
        print("🟡  MediaPipe has moderate tracking rate. Some frames are lost due to blur/occlusion.")
        print("    We may need to interpolate missing landmarks instead of skipping frames.")
    else:
        print("🔴  MediaPipe tracking rate is poor. Many frames are skipped due to low resolution/distance.")
        print("    Bypassing missing pose frames degrades quality. We must apply interpolation or smoothing.")
    print("============================================================")

if __name__ == "__main__":
    main()
