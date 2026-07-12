#!/usr/bin/env python3
import os
import zipfile
import shutil
import keras
from keras import layers

keras_file = "/Users/neilkloot/Code/Batting Sensor Stats/cricshot10k/Models/Efficientnetv2-s_GRU_128_NEEDS_CROPPED_SEGMENTED_SHOTS.keras"
weights_temp = "scratch/model.weights.h5"

print("Extracting weights file from model zip...")
with zipfile.ZipFile(keras_file, 'r') as zip_ref:
    zip_ref.extract("model.weights.h5", "scratch")

print("Rebuilding model architecture...")
# Build base model
base_model = keras.applications.EfficientNetV2S(
    include_top=False,
    weights=None,
    input_shape=(224, 224, 3)
)
base_model._name = "efficientnetv2-s"

# Build sequential wrapper
model = keras.Sequential([
    layers.Input(shape=(15, 224, 224, 3)),
    layers.TimeDistributed(base_model, name="time_distributed_8"),
    layers.TimeDistributed(layers.Flatten(), name="time_distributed_9"),
    layers.GRU(128, return_sequences=False, name="gru_4"),
    layers.BatchNormalization(name="batch_normalization_4"),
    layers.Dense(1024, activation="relu", name="dense_8"),
    layers.Dense(15, activation="softmax", name="dense_9")
])

print("Loading weights...")
try:
    model.load_weights(weights_temp)
    print("\n✅ Success! Weights loaded successfully!")
    print("Input shape:", model.input_shape)
    print("Output shape:", model.output_shape)
except Exception as e:
    print("\n❌ Failed to load weights:", e)

# Clean up extracted weights
if os.path.exists(weights_temp):
    os.remove(weights_temp)
