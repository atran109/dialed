import mediapipe as mp
import numpy as np
from collections import deque
import cv2
import time
import csv
import math

#initialize facemesh
mp_face = mp.solutions.face_mesh.FaceMesh(
    max_num_faces = 1,
    refine_landmarks = True,
    min_detection_confidence = 0.5,
    min_tracking_confidence = 0.5
)

#read a frame convert and run inference
cap = cv2.VideoCapture(0)

csvfile = open("data_raw/gaze_log.csv", "w", newline="")
writer = csv.writer(csvfile)
writer.writerow(["ts","eye_off_center","blink","head_pitch","head_yaw"])

def dist(pt1, pt2):
    return np.linalg.norm(np.array(pt1) - np.array(pt2))

ear_window = deque(maxlen=4)

while cap.isOpened():
    ret, frame = cap.read()
    if not ret: break
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB) #turns bgr to rgb
    result = mp_face.process(rgb)

    #Convert normalised coords to pixels
    h, w = frame.shape[:2]

    if result.multi_face_landmarks:
        lm = result.multi_face_landmarks[0]

        def to_px(idx):
            pt = lm.landmark[idx]
            return int(pt.x * w), int(pt.y * h)

        #gaze feature (to determine if eyes are off center)
        pLx,_ = to_px(473) #left pupil
        pRx,_ = to_px(468) #right pupil
        eye_off_center = abs((pLx + pRx)/2 - w//2) / (w//2)

        #calculating blinking: EAR = (average vertical eyelid distance) / (horizontal eye width)

        l_top1 = to_px(159) # upper inner lid
        l_top2 = to_px(27) # upper outer lid
        l_bot1 = to_px(145) # lower inner lid
        l_bot2 = to_px(23) # lower outer lid
        l_left_corner = to_px(35)
        l_right_corner = to_px(133)

        l_vert = (dist(l_top1, l_bot1) + dist(l_top2, l_bot2)) / 2.0
        l_horiz = dist(l_left_corner, l_right_corner)
        l_ear = l_vert/(l_horiz + 1e-6)

        r_top1 = to_px(386)
        r_top2 = to_px(257)
        r_bot1 = to_px(174)
        r_bot2 = to_px(253)
        r_left_corner = to_px(362)
        r_right_corner = to_px(263)

        r_vert = (dist(r_top1, r_bot1) + dist(r_top2, r_bot2)) / 2.0
        r_horiz = dist(r_left_corner, r_right_corner)
        r_ear = r_vert/(r_horiz + 1e-6)

        ear_mean = (l_ear + r_ear) / 2.0

        #Have a rolling 4 blinks to have smoothing 

        ear_window.append(ear_mean)
        blink_flag = 1 if len(ear_window) == ear_window.maxlen and all(e < 0.18 for e in ear_window) else 0


        #head pitch and yaw
        nose = to_px(1)
        chin = to_px(152)
        dy = chin[1] - nose[1]
        dx = chin[0] - nose[0]
        #up/down nod
        pitch_rad = math.atan2(dy, dx) #radians relative to horizontal
        pitch_deg = math.degrees(pitch_rad) - 90 #negative means head up, positive down
        #left/right turn
        yaw_norm = (l_left_corner[0] + r_right_corner[0]) / 2 - w//2
        yaw_deg = (yaw_norm / (w//2)) * 30 #scale to approx +-30 degrees

        writer.writerow([time.time(), float(eye_off_center), int(blink_flag), float(pitch_deg), float(yaw_deg)])

cap.release()
csvfile.close()