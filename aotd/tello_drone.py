"""
@title
@description
"""
import logging
import os
import socket
import threading
import time
from datetime import datetime
from enum import Enum

import cv2

from aotd.project_properties import data_dir


class FlipDirection(Enum):
    """

    """
    LEFT = 'l'
    RIGHT = 'r'
    FORWARDS = 'f'
    BACK = 'b'


class TelloDrone:
    # todo more clearly define the function of NETWORK_SCAN_DELAY and SEND_DELAY
    # Network constants
    BASE_SSID = 'TELLO-'
    NETWORK_SCAN_DELAY = 0.5
    NUM_RETRY = 5
    MAX_TIME_OUT = 15

    # Send/receive commands socket
    TELLO_HOST = '192.168.10.1'
    TELLO_PORT = 8889
    LOCAL_HOST = ''
    LOCAL_PORT = 8889
    SEND_DELAY = 0.1
    BUFFER_SIZE = 1024

    # state stream constants
    STATE_PORT = 8890
    STATE_DELAY = 0.1
    NUM_BASELINE_VALS = 10

    # Video
    VIDEO_UDP_URL = f'udp://0.0.0.0:11111'
    FRAME_DELAY = 1

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

        # To send comments
        self.comm_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.comm_socket.bind((self.LOCAL_HOST, self.LOCAL_PORT))

        self.response_thread = threading.Thread(target=self.__listen_responses, args=(), daemon=True)
        self.response_thread.start()
        self.listening_response = False
        self.last_received = None

        # Tello
        self.tello_address = (self.TELLO_HOST, self.TELLO_PORT)

        # Video
        self.video_thread = threading.Thread(target=self.__listen_video, args=(), daemon=True)
        self.video_running = False

        # save file names
        self.save_directory = os.path.join(data_dir, 'tello', f'{self.id}')
        if not os.path.isdir(self.save_directory):
            os.makedirs(self.save_directory)
        self.video_fname = os.path.join(self.save_directory, f'{self.id}.avi')

        while not self.listening_response:
            time.sleep(1)
        return

    def connect(self, max_retries=-1):
        """

        :return:
        """
        # todo add retry attempt to connect
        # todo add delay between scanning
        # todo add check if on correct ssid
        command = 'command'
        self.__send_command(command)
        return True

    def cleanup(self):
        """

        :return:
        """
        self.listening_response = False
        self.video_running = False

        self.comm_socket.close()
        return

    def __send_command(self, command: str):
        """

        :param command:
        :return:
        """
        # todo make into polling queue
        enc_command = command.encode(encoding='utf-8')
        logging.info(f'Sending message: {command}')
        self.comm_socket.sendto(enc_command, self.tello_address)

        start = time.time()
        while not self.last_received:
            now = time.time()
            diff = now - start
            if diff > self.MAX_TIME_OUT:
                return False
        self.last_received = None
        return True

    def __listen_responses(self):
        self.listening_response = True
        logging.info(f'Starting listening thread...')
        while self.listening_response:
            try:
                response_bytes, ip = self.comm_socket.recvfrom(self.BUFFER_SIZE)
                response_str = response_bytes.decode('utf-8')
                logging.info(f'Received from {ip}: {response_str}')
                self.last_received = response_str
            except UnicodeDecodeError as ude:
                logging.warning(f'Error in decoding response: {str(ude)}')
        logging.info(f'Exiting listening thread...')
        return

    def start_video(self, max_retries=0):
        # ensure the drone video stream is in a known state
        self.control_streamoff()
        self.control_streamon()
        time.sleep(1)
        self.video_thread.start()
        return

    def __listen_video(self):
        """
        always on

        :return:
        """
        logging.info(f'Starting video thread...')
        self.video_capture = cv2.VideoCapture(self.VIDEO_UDP_URL, cv2.CAP_FFMPEG)
        # todo make opening stream into loop for XXX tries
        while not self.video_capture.isOpened():
            logging.info(f'Could not open video stream')
            self.video_capture = cv2.VideoCapture(self.VIDEO_UDP_URL, cv2.CAP_FFMPEG)

        logging.info(f'Opened video stream: {self.VIDEO_UDP_URL}')

        # discard first read and make sure all is reading correctly
        read_success, video_frame = self.video_capture.read()
        # todo make reading stream into loop for XXX tries
        while not read_success:
            logging.info(f'Error reading from video stream')
            read_success, video_frame = self.video_capture.read()

        # save capture width and height for later when saving the video
        fps = 30
        frame_width = int(self.video_capture.get(3))
        frame_height = int(self.video_capture.get(4))
        logging.info(
            f'Read frame from video stream\n'
            f'FPS: {fps}\n'
            f'Width: {frame_width}\n'
            f'Height: {frame_height}'
        )

        codec_str = 'MJPG'
        self.video_writer = cv2.VideoWriter(
            self.video_fname, cv2.VideoWriter_fourcc(*codec_str),
            fps, (frame_width, frame_height)
        )

        self.video_running = True
        self.video_start_time = time.time()
        logging.info(f'running video loop')
        while self.video_capture.isOpened() and self.video_running:
            read_success, video_frame = self.video_capture.read()
            logging.debug('received frame')
            if read_success:
                logging.debug(f'read frame success')
                # self.video_writer.write(video_frame.astype('uint8'))
                cv2.imshow('drone video', video_frame)
            cv2.waitKey(self.FRAME_DELAY)
        self.video_end_time = time.time()

        self.video_capture.release()
        self.video_writer.release()
        cv2.destroyAllWindows()
        return

    def control_streamoff(self):
        """
        takeoff

        auto-takeoff

        ok, error

        :return:
        """
        command_str = f'streamoff'
        self.__send_command(command_str)
        return

    def control_streamon(self):
        """
        takeoff

        auto-takeoff

        ok, error

        :return:
        """
        command_str = f'streamon'
        self.__send_command(command_str)
        return

    def control_takeoff(self):
        """
        takeoff

        auto-takeoff

        ok, error

        :return:
        """
        command_str = f'takeoff'
        self.__send_command(command_str)
        return

    def control_land(self):
        """
        lland

        auto-land

        ok, error

        :return:
        """
        command_str = f'land'
        self.__send_command(command_str)
        return

    def control_emergency(self):
        """
        emergency

        immediately stops all motors

        ok, error

        :return:
        """
        command_str = f'emergency'
        response = 'error'
        self.__send_command(command_str)
        return response

    def control_flip(self, direction: FlipDirection):
        """
        flip x

        perform a flip
        l: left
        r: right
        f: forward
        b: back

        ok, error

        :return:
        """
        command_str = f'flip {direction.value}'
        self.__send_command(command_str)
        return

    def set_speed(self, speed_cms):
        """
        speed x

        set speed to x (cm/s)
        x: 10-100

        ok, error

        :param speed_cms:
        :return:
        """
        command_str = f'speed {int(speed_cms)}'
        self.__send_command(command_str)
        return

    def set_rc(self, left_right, forward_back, up_down, yaw):
        """
        Send RC control via four channels.

        left/right (-100~100)
        forward/backward (-100~100)
        up/down (-100~100)
        yaw (-100~100)

        ok, error

        :return:
        """
        command_str = f'rc {left_right} {forward_back} {up_down} {yaw}'
        self.__send_command(command_str)
        return
