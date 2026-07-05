def predict_stance(gyro_std, accel_std, ori_disp, mean_grav_y, step_age):
    if gyro_std <= 1.176236:
        if ori_disp <= 0.281161:
            if gyro_std <= 0.419345:
                if mean_grav_y <= -8.347519:
                    return 1
                else:
                    return 0
            else:
                if gyro_std <= 0.586201:
                    return 1
                else:
                    return 1
        else:
            if gyro_std <= 0.188638:
                if mean_grav_y <= -8.846963:
                    return 0
                else:
                    return 0
            else:
                if ori_disp <= 1.103512:
                    return 0
                else:
                    return 0
    else:
        if ori_disp <= 1.329910:
            if mean_grav_y <= -6.663786:
                if ori_disp <= 0.865127:
                    return 1
                else:
                    return 1
            else:
                if ori_disp <= 0.745373:
                    return 1
                else:
                    return 1
        else:
            if gyro_std <= 1.807490:
                if ori_disp <= 2.972609:
                    return 1
                else:
                    return 0
            else:
                if ori_disp <= 3.014546:
                    return 1
                else:
                    return 1
