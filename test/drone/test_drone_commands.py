import sys
import threading
import traceback
import av
import cv2 as cv2  # for avoidance of pylint error
import numpy
import time

import numpy as np

from aotd.cv import detect_qr, vectors_to_commands, dense_optical_flow, poly_area, draw_text
from aotd.tellopy import logger
from aotd.tellopy.tello import Tello


def handler(event, sender, data, **args):
    drone = sender
    if event is drone.EVENT_FLIGHT_DATA:
        # print(data)
        pass
    return


def main():
    def video_handler():
        # skip first N frames
        # skip first 300 frames
        frame_skip = 300
        video_running = True

        command_map = [
            (drone.up, drone.down),
            (drone.right, drone.left),
            (drone.forward, drone.backward),
        ]

        command_list = []
        buffer_len = 5
        last_idx = 0
        prev_area = 5000

        np.set_printoptions(precision=2, floatmode='fixed', sign='+')
        pos = 50, 50
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 1
        font_thickness = 2
        text_color = 255, 255, 255
        text_color_bg = 0, 0, 0

        rad = 50
        true_info = r'https://www.youtube.com/watch?v=dQw4w9WgXcQ'
        while video_running:
            print('video running')
            for frame in container.decode(video=0):
                if 0 < frame_skip:
                    frame_skip = frame_skip - 1
                    prev_image = frame.to_image()
                    prev_image = cv2.cvtColor(numpy.array(prev_image), cv2.COLOR_RGB2BGR)
                    continue
                start_time = time.time()

                video_frame = frame.to_image()
                image = cv2.cvtColor(numpy.array(video_frame), cv2.COLOR_RGB2BGR)

                detected, points, info, qr_frame = detect_qr(image)
                if detected and info == true_info:
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
                else:
                    command = (0, 0, 0)
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
                cv2.imshow('Original', image)
                cv2.waitKey(1)

                if frame.time_base < 1.0 / 60:
                    time_base = 1.0 / 60
                else:
                    time_base = frame.time_base
                frame_skip = int((time.time() - start_time) / time_base)
        cv2.destroyAllWindows()
        print(f'video exiting')
        return

    video_thread = threading.Thread(target=video_handler, daemon=True)
    drone = Tello()
    drone.set_loglevel(logger.LOG_WARN)

    try:
        drone.connect()
        drone.wait_for_connection(60.0)

        retry = 3
        container = None
        while container is None and 0 < retry:
            retry -= 1
            try:
                container = av.open(drone.get_video_stream())
            except av.AVError as ave:
                print(ave)
                print('retry...')

        video_thread.start()
        stop = input()
        video_running = False
        time.sleep(5)
    except Exception as ex:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        traceback.print_exception(exc_type, exc_value, exc_traceback)
        print(ex)
    finally:
        drone.quit()
    return


if __name__ == '__main__':
    main()
