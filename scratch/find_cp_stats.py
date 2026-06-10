import os
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder

BASE_DIR = "/Users/neilkloot/Code/Batting Sensor Stats"
FEATURES_CSV = os.path.join(BASE_DIR, "combined_features.csv")

def main():
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', 1000)
    df = pd.read_csv(FEATURES_CSV)
    df_swings = df[df['normalized_gt'] != 'NON-SWING'].copy()
    cp_df = df_swings[df_swings['normalized_gt'] == 'CUT/PUNCH']
    print("CUT/PUNCH stats:")
    print(cp_df[[
        'gyroMag', 'rollImpactDeg', 'yawImpactDeg', 'deltaX', 'deltaZ', 'planeRatio',
        'gyro_y_min', 'grav_x_max', 'grav_y_min', 'mag_x_max'
    ]].describe().loc[['min', '25%', '50%', '75%', 'max']])

if __name__ == '__main__':
    main()
