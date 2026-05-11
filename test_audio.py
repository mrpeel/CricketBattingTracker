import pygame
pygame.mixer.init()
try:
    pygame.mixer.music.load('/Users/neilkloot/Code/Batting Sensor Stats/ground_truth/2026_05_02/Pull shots/Pull shots.m4a')
    print("Success loading m4a!")
except Exception as e:
    print(f"Failed: {e}")
