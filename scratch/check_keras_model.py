#!/usr/bin/env python3
import os
os.environ["KERAS_BACKEND"] = "torch"
import keras

model_path = "/Users/neilkloot/Code/Batting Sensor Stats/cricshot10k/Models/Efficientnetv2-s_GRU_128_NEEDS_CROPPED_SEGMENTED_SHOTS.keras"
print(f"Loading Keras model from {model_path}...")
model = keras.models.load_model(model_path)
print("\nModel Loaded Successfully!")
print("Input shape:", model.input_shape)
print("Output shape:", model.output_shape)
print("\nModel Summary:")
model.summary()
