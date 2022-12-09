"""
@title

@description

"""
import argparse
import time
from pathlib import Path

import cv2
import numpy as np

from aotd.cv import detect_qr, dense_optical_flow, vectors_to_commands, poly_area, draw_text
from aotd.project_properties import data_dir


def main(main_args):
    test_videos = [
        # Path(data_dir, 'videos', 'phone_qr.mp4'),
        Path(data_dir, 'videos', 'drone_qr.mp4')
    ]
    np.set_printoptions(precision=2, floatmode='fixed', sign='+')
    pos = 50, 50
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 1
    font_thickness = 2
    text_color = 255, 255, 255
    text_color_bg = 0, 0, 0

    command_list = [[0, 0, 0]]
    buffer_len = 5
    last_idx = 0
    for each_path in test_videos:
        cap = cv2.VideoCapture(str(each_path))

        while not cap.isOpened():
            print('Error opening video stream or file')
            time.sleep(1)
            cap = cv2.VideoCapture(each_path)

        # Read until video is completed
        stopped = False
        prev_image = None
        ret = False
        while not ret:
            ret, prev_image = cap.read()

        true_info = r'https://www.youtube.com/watch?v=dQw4w9WgXcQ'
        rad = 50
        prev_area = 5000
        while cap.isOpened() and not stopped:
            ret, image = cap.read()
            if ret:
                empty_image = np.zeros_like(image)
                detected, points, info, qr_frame = detect_qr(image)
                if points is not None:
                    # get center of all points
                    # draw circle around QR code
                    points = np.array(points[0])
                    x_points = points[:, 0]
                    y_points = points[:, 1]
                    area = poly_area(x_points, y_points)
                    size_proportion = area / prev_area
                    if size_proportion < 0.5:
                        print(f'{area=} | {size_proportion=}')

                    center = tuple(np.mean(points, axis=0).astype(int))
                    cv2.circle(image, center, rad, color=(255, 0, 0), thickness=2)

                    flow, x_vectors, y_vectors = dense_optical_flow(prev_image, curr_frame=image)

                    prev_image = image
                    prev_area = area

                    command = vectors_to_commands(x_vectors, y_vectors, size_proportion, center, rad)

                    mag, ang = cv2.cartToPolar(flow[..., 0], flow[..., 1])

                    hsv = np.zeros_like(image)
                    hsv[..., 1] = 255
                    hsv[..., 0] = ang * 180 / np.pi / 2
                    hsv[..., 2] = cv2.normalize(mag, None, 0, 255, cv2.NORM_MINMAX)
                    bgr = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)

                    raw_imgs = np.concatenate((prev_image, image), axis=0)
                    optical_image = np.concatenate((empty_image, bgr), axis=0)

                    display_frame = np.concatenate((raw_imgs, optical_image), axis=1)
                else:
                    command = (0, 0, 0)

                    raw_imgs = np.concatenate((prev_image, image), axis=0)
                    both_empty = np.concatenate((empty_image, empty_image), axis=0)

                    display_frame = np.concatenate((raw_imgs, both_empty), axis=1)
                print(f'{command=}')
                command_list.append(command)
                agg_commands = np.asarray(command_list[last_idx:])
                curr_command = np.average(agg_commands, axis=0)

                text = f'{curr_command}'
                draw_text(image, text, font, pos, font_scale, font_thickness, text_color, text_color_bg)

                counter = len(agg_commands)
                if counter >= buffer_len:
                    last_idx = len(command_list)
                    print(f'sending command: {curr_command}')

                # cv2.imshow('frame', image)
                cv2.imshow('frame', display_frame)

            if cv2.waitKey(10) & 0xFF == ord('q'):
                stopped = True

        cap.release()
        cv2.destroyAllWindows()
    return


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='')

    args = parser.parse_args()
    main(vars(args))
