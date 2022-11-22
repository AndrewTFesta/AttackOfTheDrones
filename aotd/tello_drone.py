"""
@title
@description
"""
import logging
import threading
import time
from datetime import datetime
from pathlib import Path

import av
import cv2
import numpy as np

from aotd import tellopy
from aotd.project_properties import data_dir


class TelloDrone:

    def __init__(self):
        """
        The Tello SDK connects to the aircraft through a Wi-Fi UDP port, allowing users to control the
        drone with text commands

        If no command is received for 15 seconds, the tello will land automatically.
        Long press Tello for 5 seconds while Tello is on, and the indicator light will turn off and then
        flash yellow. When the indicator light shows a flashing yellow light, the Wi-Fi SSID and password
        will be reset to the factory settings, and there is no password by default.
        For Tello use SDK 1.3. For Tello EDU SDK 2.0. Moving from SDK 1.3 to SDK 2.0, most of the SDK looks
        to be backwards compatible. However, this is not universally true. For example, some specific state
        messages changed.

        SDK 1.3 details using specific commands, including `move`, `curve`, `right`, `left`, etc. These commands
        do not work. Likely this is due to a poor quality IMU sensor, or it may require use of the motion pad.
        Instead, the best way to control movement of the drone for most purposes is through use of the `rc`
        control command. That is what is implemented here. The control commands that do seem to work
        are listed below:
            command
            takeoff
            land
            flip
            streamon
            streamoff
            emergency

        Commands can be broken down into three sets:
            Control
                Returns 'ok' if the command was successful
                Returns 'error' or an informational result code if the command failed
            Set
                Sets new sub-parameter values
                Returns 'ok' if the command was successful
                Returns 'error' or an informational result code if the command failed
            Read
                Returns the current value of the sub-parameter
        """
        logging.basicConfig(level=logging.INFO)

        current_time = time.time()
        date_time = datetime.fromtimestamp(time.time())
        time_str = date_time.strftime("%Y-%m-%d-%H-%M-%S")

        # identification information
        self.name = 'Tello'
        self.id = f'{self.name}_{time_str}_{int(current_time)}'

        # drone object used to communicate with tello drone
        self.drone = tellopy.Tello()

        # state
        # self.response_thread = threading.Thread(target=self.__listen_responses, args=(), daemon=True)
        # self.response_thread.start()
        # self.listening_response = False
        # self.received = []

        # Video
        self.video_stream = None
        self.video_thread = threading.Thread(target=self.__listen_video, args=(), daemon=True)
        self.video_running = False

        # save file names
        self.save_directory = Path(data_dir, 'tello', f'{self.id}')
        if not self.save_directory.is_dir():
            self.save_directory.mkdir(parents=True, exist_ok=True)
        self.video_fname = Path(self.save_directory, f'{self.id}.avi')
        return

    def handle_data(self, event, sender, data, **args):
        self.drone = sender
        print(f'{event}: {data}')
        return

    def connect(self):
        # subscribe to data feeds
        self.drone.subscribe(self.drone.EVENT_FLIGHT_DATA, self.handle_data)
        self.drone.subscribe(self.drone.EVENT_LOG, self.handle_data)
        self.drone.subscribe(self.drone.EVENT_LIGHT, self.handle_data)
        self.drone.subscribe(self.drone.EVENT_WIFI, self.handle_data)
        self.drone.subscribe(self.drone.EVENT_CONNECTED, self.handle_data)
        self.drone.subscribe(self.drone.EVENT_DISCONNECTED, self.handle_data)

        self.drone.connect()
        self.drone.wait_for_connection(60.0)

        # todo look into self.drone.toggle_fast_mode()
        # self.drone.set_video_mode(not self.drone.zoom)
        self.video_stream = self.drone.get_video_stream()

        # todo look into self.drone.set_video_mode()
        # todo look into self.drone.set_exposure()
        # todo look into self.drone.set_video_encoder_rate()
        self.video_thread.start()
        return True

    def __listen_video(self):
        self.video_running = True
        try:
            container = av.open(self.video_stream)
            # skip first 300 frames
            frame_skip = 300
            while self.video_running:
                try:
                    for frame in container.decode(video=0):
                        if 0 < frame_skip:
                            frame_skip = frame_skip - 1
                            continue
                        start_time = time.time()
                        image = cv2.cvtColor(np.array(frame.to_image()), cv2.COLOR_RGB2BGR)

                        cv2.imshow('Original', image)
                        cv2.waitKey(1)
                        if frame.time_base < 1.0 / 60:
                            time_base = 1.0 / 60
                        else:
                            time_base = frame.time_base
                        frame_skip = int((time.time() - start_time) / time_base)
                except Exception as ex:
                    print(ex)
        except Exception as ex:
            print(ex)
        return

    def cleanup(self):
        self.listening_response = False
        self.video_running = False
        return

    # takeoff/land
    def control_takeoff(self):
        # todo look into self.drone.manual_takeoff()
        response = self.drone.takeoff()
        return response

    def control_land(self):
        response = self.drone.land()
        return response

    def control_palm_land(self):
        response = self.drone.palm_land()
        return response

    def control_emergency(self):
        response = self.drone.quit()
        return response

    # tricks/flips
    def flip_forward(self):
        response = self.drone.flip_forward()
        return response

    def flip_back(self):
        response = self.drone.flip_back()
        return response

    def flip_right(self):
        response = self.drone.flip_right()
        return response

    def flip_left(self):
        response = self.drone.flip_left()
        return response

    def flip_forwardleft(self):
        response = self.drone.flip_forwardright()
        return response

    def flip_backleft(self):
        response = self.drone.flip_backright()
        return response

    def flip_forwardright(self):
        response = self.drone.flip_forwardright()
        return response

    def flip_backright(self):
        response = self.drone.flip_backright()
        return response

    # direction
    def up(self, val):
        """Up tells the drone to ascend. Pass in an int from 0-100."""
        response = self.drone.up(val)
        return response

    def down(self, val):
        """Down tells the drone to descend. Pass in an int from 0-100."""
        response = self.drone.down(val)
        return response

    def forward(self, val):
        """Forward tells the drone to go forward. Pass in an int from 0-100."""
        response = self.drone.forward(val)
        return response

    def backward(self, val):
        """Backward tells the drone to go in reverse. Pass in an int from 0-100."""
        response = self.drone.backward(val)
        return response

    def right(self, val):
        """Right tells the drone to go right. Pass in an int from 0-100."""
        response = self.drone.right(val)
        return response

    def left(self, val):
        """Left tells the drone to go left. Pass in an int from 0-100."""
        response = self.drone.left(val)
        return response

    def clockwise(self, val):
        """
        Clockwise tells the drone to rotate in a clockwise direction.
        Pass in an int from 0-100.
        """
        response = self.drone.clockwise(val)
        return response

    def counter_clockwise(self, val):
        """
        CounterClockwise tells the drone to rotate in a counter-clockwise direction.
        Pass in an int from 0-100.
        """
        response = self.drone.counter_clockwise(val)
        return response

    # axes/power
    def set_throttle(self, throttle):
        """
        Set_throttle controls the vertical up and down motion of the drone.
        Pass in an int from -1.0 ~ 1.0. (positive value means upward)
        """
        response = self.drone.set_throttle(throttle)
        return response

    def set_yaw(self, yaw):
        """
        Set_yaw controls the left and right rotation of the drone.
        Pass in an int from -1.0 ~ 1.0. (positive value will make the drone turn to the right)
        """
        response = self.drone.set_yaw(yaw)
        return response

    def set_pitch(self, pitch):
        """
        Set_pitch controls the forward and backward tilt of the drone.
        Pass in an int from -1.0 ~ 1.0. (positive value will make the drone move forward)
        """
        response = self.drone.set_pitch(pitch)
        return response

    def set_roll(self, roll):
        """
        Set_roll controls the the side to side tilt of the drone.
        Pass in an int from -1.0 ~ 1.0. (positive value will make the drone move to the right)
        """
        response = self.drone.set_roll(roll)
        return response
