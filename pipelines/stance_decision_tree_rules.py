def predict_stance(gyro_std, accel_std, ori_disp, mean_grav_y, step_age):
    if gyro_std <= 1.176236:
        if ori_disp <= 0.281161:
            if gyro_std <= 0.419345:
                return 0
            else:
                return 1
        else:
            if gyro_std <= 0.188638:
                return 0
            else:
                return 0
    else:
        if ori_disp <= 1.329910:
            if mean_grav_y <= -6.663786:
                return 1
            else:
                return 1
        else:
            if gyro_std <= 1.807490:
                return 0
            else:
                return 1
