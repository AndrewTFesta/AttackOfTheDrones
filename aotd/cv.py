"""
@title

@description

"""

import cv2 as cv2
import numpy as np


def vectors_to_commands(x_vectors, y_vectors, size_diff, center, rad=50, n_points=100, z_scale=1):
    x_bounds = max(0, center[1] - rad), min(x_vectors.shape[1], center[1] + rad)
    y_bounds = max(0, center[0] - rad), min(x_vectors.shape[1], center[0] + rad)

    # x_vectors = x_vectors[max(0, x_bounds[0]):x_bounds[1], max(0, y_bounds[0]):y_bounds[1]]
    # y_vectors = y_vectors[max(0, x_bounds[0]):x_bounds[1], max(0, y_bounds[0]):y_bounds[1]]

    # x_vectors = x_vectors.flatten()
    # y_vectors = y_vectors.flatten()

    avg_x = np.average(x_vectors)
    avg_y = np.average(y_vectors)

    # calculate z based on how points are moving towards or away from the center
    vector_field = np.stack((x_vectors, y_vectors), axis=-1)

    mid_pts = np.divide(vector_field.shape, 2)

    right_vect = vector_field[-1, int(mid_pts[0]) - 1]
    left_vect = vector_field[0, int(mid_pts[0]) - 1]
    top_vect = vector_field[int(mid_pts[1]) - 1, 0]
    bot_vect = vector_field[int(mid_pts[1]) - 1, -1]

    # rough estimation of flux across a circle around the center of the vectors
    right_dot = np.dot(right_vect, [1, 0])
    left_dot = np.dot(left_vect, [-1, 0])
    top_dot = np.dot(top_vect, [0, 1])
    bottom_dot = np.dot(bot_vect, [0, -1])

    total_dot = right_dot + left_dot + top_dot + bottom_dot
    #

    z_command = 1 - (size_diff * z_scale)
    return avg_x, avg_y, z_command


def detect_qr(frame):
    info, decode_frame = None, None
    qr_detector = cv2.QRCodeDetector()
    detected, points = qr_detector.detect(frame)
    if points is not None:
        info, decode_frame = qr_detector.decode(frame, points)
    return detected, points, info, decode_frame


def poly_area(x, y):
    x_term = np.dot(x, np.roll(y, 1))
    y_term = np.dot(y, np.roll(x, 1))
    return 0.5 * np.abs(x_term - y_term)


def dense_optical_flow(prev_frame, curr_frame, params=None):
    if not params:
        params = [0.5, 3, 15, 3, 5, 1.2, 0]
    # Preprocessing for exact method
    prev_frame = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY)
    curr_frame = cv2.cvtColor(curr_frame, cv2.COLOR_BGR2GRAY)

    # Calculate Optical Flow
    flow = cv2.calcOpticalFlowFarneback(prev_frame, curr_frame, None, *params)
    x_vect, y_vect = flow[..., 0], flow[..., 1]
    return flow, x_vect, y_vect


def draw_text(img, text, font=cv2.FONT_HERSHEY_PLAIN, pos=(0, 0), font_scale=3, font_thickness=2,
              text_color=(0, 255, 0), text_color_bg=(0, 0, 0)):
    x, y = pos
    text_size, _ = cv2.getTextSize(text, font, font_scale, font_thickness)
    text_w, text_h = text_size
    cv2.rectangle(img, (pos[0] - 10, pos[1] - 10), (x + text_w + 20, y + text_h + 20), text_color_bg, -1)
    cv2.putText(img, text, (x, y + text_h + font_scale - 1), font, font_scale, text_color, font_thickness)
    return text_size
