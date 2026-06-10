import os
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder

BASE_DIR = "/Users/neilkloot/Code/Batting Sensor Stats"
FEATURES_CSV = os.path.join(BASE_DIR, "combined_features.csv")

def conjugateQuat(q):
    return np.array([-q[0], -q[1], -q[2], q[3]])

def multiplyQuats(q1, q2):
    x1, y1, z1, w1 = q1
    x2, y2, z2, w2 = q2
    return np.array([
        w1*x2 + x1*w2 + y1*z2 - z1*y2,
        w1*y2 - x1*z2 + y1*w2 + z1*x2,
        w1*z2 + x1*y2 - y1*x2 + z1*w2,
        w1*w2 - x1*x2 - y1*y2 - z1*z2
    ])

def rotateVector(q, v):
    qx, qy, qz, qw = q
    vx, vy, vz = v
    tx = 2.0 * (qy*vz - qz*vy)
    ty = 2.0 * (qz*vx - qx*vz)
    tz = 2.0 * (qx*vy - qy*vx)
    return np.array([
        vx + qw*tx + (qy*tz - qz*ty),
        vy + qw*ty + (qz*tx - qx*tz),
        vz + qw*tz + (qx*ty - qy*tx)
    ])

def calcRelativeRoll(q):
    x, y, z, w = q
    return np.arctan2(2.0*(w*y + x*z), 1.0 - 2.0*(y*y + z*z)) * 57.295779513

def computeRotationQuat(progress, rollImpactDeg, deltaX, deltaZ):
    rollAngle = rollImpactDeg * progress
    rollRad = rollAngle / 57.295779513
    ry = np.sin(rollRad / 2.0)
    rw = np.cos(rollRad / 2.0)
    
    qx = -(deltaZ / 2.0) * progress
    qy = ry
    qz = (deltaX / 2.0) * progress
    qw = rw
    
    norm = np.sqrt(qx*qx + qy*qy + qz*qz + qw*qw)
    return np.array([qx / norm, qy / norm, qz / norm, qw / norm])

def simulate_features(rollImpactDeg, deltaX_in, deltaZ_in, gyroMag, postGyroY, gravX, gravY, magX):
    # stance is identity
    qStanceInv = np.array([0.0, 0.0, 0.0, 1.0])
    vLocal = np.array([0.0, -1.0, 0.0])
    
    # We collect all rotation samples during the swing window.
    # Since swingStartForFeats to swingEndForFeats covers stanceExitTime (progress=0), swing initiation (progress from 0.1 to 1.0),
    # impact (progress=1.0), and follow-through (progress=1.0).
    progress_vals = [0.0] * 10 + [i / 10.0 for i in range(1, 11)] + [1.0] * 15
    
    minX = float('inf')
    maxX = float('-inf')
    minZ = float('inf')
    maxZ = float('-inf')
    
    for p in progress_vals:
        qCurr = computeRotationQuat(p, rollImpactDeg, deltaX_in, deltaZ_in)
        qRel = multiplyQuats(qStanceInv, qCurr)
        vRot = rotateVector(qRel, vLocal)
        
        minX = min(minX, vRot[0])
        maxX = max(maxX, vRot[0])
        minZ = min(minZ, vRot[2])
        maxZ = max(maxZ, vRot[2])
        
    deltaX = maxX - minX
    deltaZ = maxZ - minZ
    planeRatio = deltaX / deltaZ if deltaZ > 0.0 else 0.0
    
    # Impact orientation is at progress = 1.0
    qImpact = computeRotationQuat(1.0, rollImpactDeg, deltaX_in, deltaZ_in)
    qRelImpact = multiplyQuats(qStanceInv, qImpact)
    vRotImpact = rotateVector(qRelImpact, vLocal)
    rollVal = calcRelativeRoll(qRelImpact)
    yawVal = np.arctan2(vRotImpact[0], -vRotImpact[1]) * 57.295779513
    
    return {
        'gyroMag': gyroMag,
        'rollImpactDeg': rollVal,
        'yawImpactDeg': yawVal,
        'deltaX': deltaX,
        'deltaZ': deltaZ,
        'planeRatio': planeRatio,
        'gyro_y_min': postGyroY,
        'grav_x_max': gravX,
        'grav_y_min': gravY,
        'mag_x_max': magX
    }

def main():
    if not os.path.exists(FEATURES_CSV):
        print(f"ERROR: {FEATURES_CSV} not found")
        return
        
    df = pd.read_csv(FEATURES_CSV)
    df_swings = df[df['normalized_gt'] != 'NON-SWING'].copy()
    
    features = [
        'gyroMag', 'rollImpactDeg', 'yawImpactDeg', 'deltaX', 'deltaZ', 'planeRatio',
        'gyro_y_min', 'grav_x_max', 'grav_y_min', 'mag_x_max'
    ]
    
    X = df_swings[features].fillna(df_swings[features].median())
    y = df_swings['normalized_gt'].values
    
    le = LabelEncoder()
    y_enc = le.fit_transform(y)
    
    rf = RandomForestClassifier(
        n_estimators=200,
        max_depth=8,
        class_weight='balanced_subsample',
        random_state=42,
        n_jobs=-1
    )
    rf.fit(X, y_enc)
    
    # ─── Grid search for GLANCE/FLICK ───
    print("Searching for GLANCE/FLICK parameters...")
    found_gf = []
    
    # Search around values of sample 60:
    # gyroMag=13.7, rollImpactDeg=66.0, deltaX=1.4, deltaZ=1.0, postGyroY=-6.9, gravX=0.87, gravY=-8.68, magX=0.0
    for roll in [45.0, 55.0, 66.0, 75.0]:
        for dx in [1.0, 1.2, 1.4, 1.6]:
            for dz in [0.8, 1.0, 1.2]:
                for gy in [-5.0, -6.9, -8.0]:
                    for gx in [0.5, 0.87, 1.2]:
                        for gy_min in [-8.68, -9.0]:
                            feats = simulate_features(
                                rollImpactDeg=roll,
                                deltaX_in=dx,
                                deltaZ_in=dz,
                                gyroMag=13.7,
                                postGyroY=gy,
                                gravX=gx,
                                gravY=gy_min,
                                magX=0.0
                            )
                            feat_df = pd.DataFrame([feats])[features]
                            pred_idx = rf.predict(feat_df)[0]
                            pred_cls = le.classes_[pred_idx]
                            if pred_cls == "GLANCE/FLICK":
                                found_gf.append((roll, dx, dz, gy, gx, gy_min, feats))
                                
    print(f"Found {len(found_gf)} parameter sets that predict GLANCE/FLICK.")
    if found_gf:
        print("Example GF parameter set:")
        example = found_gf[0]
        print(f"rollImpactDeg={example[0]}, deltaX={example[1]}, deltaZ={example[2]}, postGyroY={example[3]}, gravX={example[4]}, gravY={example[5]}")
        print("Resulting features:")
        for k, v in example[6].items():
            print(f"  {k}: {v:.4f}")
            
    # ─── Grid search for CUT/PUNCH ───
    print("\nSearching for CUT/PUNCH parameters...")
    found_cp = []
    
    # Search around values of CP samples:
    # gyroMag=18.9, rollImpactDeg=-11.0, deltaX=1.45, deltaZ=1.31, postGyroY=-5.7, gravX=5.3, gravY=-9.0, magX=0.0
    for roll in [-80.0, -50.0, -30.0, -11.0, 0.0]:
        for dx in [0.8, 1.1, 1.45, 1.6]:
            for dz in [0.8, 1.1, 1.3, 1.5]:
                for gy in [-5.7, -3.0, -1.0]:
                    for gx in [2.0, 5.3, 7.0]:
                        for gy_min in [-9.0, -9.3]:
                            feats = simulate_features(
                                rollImpactDeg=roll,
                                deltaX_in=dx,
                                deltaZ_in=dz,
                                gyroMag=18.9,
                                postGyroY=gy,
                                gravX=gx,
                                gravY=gy_min,
                                magX=0.0
                            )
                            feat_df = pd.DataFrame([feats])[features]
                            pred_idx = rf.predict(feat_df)[0]
                            pred_cls = le.classes_[pred_idx]
                            if pred_cls == "CUT/PUNCH":
                                found_cp.append((roll, dx, dz, gy, gx, gy_min, feats))
                                
    print(f"Found {len(found_cp)} parameter sets that predict CUT/PUNCH.")
    if found_cp:
        print("Example CP parameter set:")
        example = found_cp[0]
        print(f"rollImpactDeg={example[0]}, deltaX={example[1]}, deltaZ={example[2]}, postGyroY={example[3]}, gravX={example[4]}, gravY={example[5]}")
        print("Resulting features:")
        for k, v in example[6].items():
            print(f"  {k}: {v:.4f}")

if __name__ == '__main__':
    main()
