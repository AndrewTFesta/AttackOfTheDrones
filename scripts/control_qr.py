import threading
import time

import av
import cv2 as cv2  # for avoidance of pylint error
import numpy
import numpy as np
import pygame

from aotd.cv import detect_qr, dense_optical_flow, vectors_to_commands, poly_area, draw_text
from aotd.tellopy.tello import Tello

MENU = """
SPACE: Takeoff (If on ground)
SPACE: Land (if flying)
WASD:  Control
C:     Connect to drone ssid
"""


def main():
    def video_handler():
        # skip first N frames
        # skip first 300 frames
        frame_skip = 300
        video_running = True

        # positive value is first command, negative is second command
        command_map = [
            (drone.left, drone.right),
            (drone.down, drone.up),
            (drone.backward, drone.forward),
        ]

        command_list = []
        buffer_len = 5
        last_idx = 0
        prev_area = 5000

        np.set_printoptions(precision=2, floatmode='fixed', sign='+')
        control_pos = 50, 50
        manual_pos = 50, 100
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
                if detected:
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
                # print(f'{command=}')
                command_list.append(command)
                agg_commands = np.asarray(command_list[last_idx:])
                curr_command = np.average(agg_commands, axis=0)

                text = f'{curr_command}'
                draw_text(image, text, font, control_pos, font_scale, font_thickness, text_color, text_color_bg)
                draw_text(image, f'{qr_control=}', font, manual_pos, font_scale, font_thickness, text_color, text_color_bg)

                counter = len(agg_commands)
                if counter >= buffer_len:
                    if qr_control:
                        for axis_command, drone_command in zip(curr_command, command_map):
                            drone_command = drone_command[0] if axis_command > 0 else drone_command[1]
                            drone_command(int(axis_command * speed))
                    last_idx = len(command_list)
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
    pygame.init()
    # logo = pygame.image.load('logo32x32.png')
    # pygame.display.set_icon(logo)
    pygame.display.set_caption('minimal program')
    screen = pygame.display.set_mode((240, 180))

    # track if the game is running and if the drone is controlled manually
    running = True
    qr_control = False
    speed = 90

    controls = {
        'w': 'forward',
        's': 'backward',
        'a': 'left',
        'd': 'right',
        'space': 'up',
        'left shift': 'down',
        'q': 'counter_clockwise',
        'e': 'clockwise',
        # arrow keys for fast turns and altitude adjustments
        'left': lambda drone, speed: drone.counter_clockwise(speed),
        'right': lambda drone, speed: drone.clockwise(speed),
        'up': lambda drone, speed: drone.up(speed),
        'down': lambda drone, speed: drone.down(speed),
        'tab': lambda drone, speed: drone.takeoff(),
        'r': lambda drone, speed: drone.land(),
    }

    # set up connection for drone and wait for video to be ready
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
    while running:
        time.sleep(0.01)  # loop with pygame.event.get() is too mush tight w/o some sleep
        # event handling, gets all event from the event queue
        for event in pygame.event.get():
            # WASD for movement
            if event.type == pygame.KEYDOWN:
                print('+' + pygame.key.name(event.key))
                keyname = pygame.key.name(event.key)
                if keyname == 'escape':
                    drone.quit()
                    exit(0)
                elif keyname == 'z':
                    print(f'Toggle manual control: {qr_control=}')
                    qr_control = not qr_control
                elif keyname in controls:
                    key_handler = controls[keyname]
                    if type(key_handler) == str:
                        getattr(drone, key_handler)(speed)
                    else:
                        key_handler(drone, speed)

            elif event.type == pygame.KEYUP:
                print('-' + pygame.key.name(event.key))
                keyname = pygame.key.name(event.key)
                if keyname in controls:
                    key_handler = controls[keyname]
                    if type(key_handler) == str:
                        getattr(drone, key_handler)(0)
                    else:
                        key_handler(drone, 0)
    drone.quit()
    return


if __name__ == '__main__':
    main()
