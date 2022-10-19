"""
@title
@description
"""
import json
import math
import os
import queue
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

    # Send/receive commands socket
    CLIENT_HOST = '192.168.10.1'
    CLIENT_PORT = 8889
    SEND_DELAY = 0.1

    # receive constants
    BUFFER_SIZE = 1024
    ANY_HOST = '0.0.0.0'

    # state stream constants
    STATE_PORT = 8890
    STATE_DELAY = 0.1
    NUM_BASELINE_VALS = 10

    # video stream constants
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
        to be backwards compatible. However, this is not universally true. For example, some of the
        specific state messages changed.

        SDK 1.3 details using specific commands, including `move`, `curve`, `right`, `left`, etc. These commands
        do not work. Likely this is due to a poor quality IMU sensor or it may require use of the motion pad.
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
        current_time = time.time()
        date_time = datetime.fromtimestamp(time.time())
        time_str = date_time.strftime("%Y-%m-%d-%H-%M-%S")

        # identification information
        self.name = 'Tello'
        self.id = f'{self.name}_{time_str}_{int(current_time)}'
        self.event_log = []
        self.save_directory = os.path.join(data_dir, 'tello', f'{self.id}')
        if not os.path.isdir(self.save_directory):
            os.makedirs(self.save_directory)

        # To send comments
        self.tello_address = (self.CLIENT_HOST, self.CLIENT_PORT)
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.client_socket.bind((self.ANY_HOST, self.CLIENT_PORT))

        # receive state messages
        self.state_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.state_socket.bind((self.ANY_HOST, self.STATE_PORT))

        # send and receive message logging
        self.send_queue = queue.Queue()
        self.send_history = []
        self.receive_history = []
        self.outstanding_receive_count = 0
        self.message_lock = threading.Lock()

        # state information
        self.state_history = []
        self.state_lock = threading.Lock()

        # video stream
        self.frame_history = []
        self.video_lock = threading.Lock()
        self.video_start_time = -1
        self.video_end_time = -1
        self.video_capture = None
        self.video_writer = None

        # drone status
        self.sdk_mode = False
        self.is_flying = False

        # save file names
        self.video_fname = os.path.join(self.save_directory, f'{self.id}.avi')
        self.state_history_fname = os.path.join(self.save_directory, f'states_{self.id}.json')
        self.message_history_fname = os.path.join(self.save_directory, f'messages_{self.id}.json')
        self.metadata_fname = os.path.join(self.save_directory, f'metadata_{self.id}.json')
        self.event_log_fname = os.path.join(self.save_directory, f'event_log_{self.id}.json')

        # thread info
        self.__thread_dict = {
            'video': {'thread': threading.Thread(target=self.__listen_video, args=(), daemon=True), 'running': False},
            'state': {'thread': threading.Thread(target=self.__listen_state, args=(), daemon=True), 'running': False}
        }
        return

    def connect(self):
        """

        :return:
        """
        self.event_log.append({'timestamp': time.time(), 'type': 'status',
                               'value': f'Attempting initialization of SDK mode...'})
        response_str = 'error'
        try:
            response = self.control_command()
            response_str = response['response']
            if response_str == 'ok':
                self.sdk_mode = True
                self.event_log.append(
                    {'timestamp': time.time(), 'type': 'status', 'value': f'SDK mode enabled...'}
                )
                # ensure the drone video stream is in a known state
                self.control_streamoff()
                while not self.control_streamon():
                    self.event_log.append({'timestamp': time.time(), 'type': 'status',
                                           'value': f'Could not open turn on drone video stream'})
                self.__start_threads()
        except UnicodeDecodeError:
            pass
        return response_str == 'ok'

    def cleanup(self):
        """

        :return:
        """
        self.control_streamoff()
        for thread_name, thread_entry in self.__thread_dict.items():
            thread_entry['running'] = False
            each_thread = thread_entry['thread']
            if each_thread.ident:
                each_thread.join()

        delta_video_time = max(self.video_end_time - self.video_start_time, 1)
        meta_data = {
            'id': self.id,
            'num_messages': len(self.send_history),
            'num_states': len(self.state_history),
            'num_frames': len(self.frame_history),
            'video_start_time': self.video_start_time,
            'video_end_time': self.video_start_time,
            'video_fps': len(self.frame_history) / delta_video_time
        }
        with open(self.metadata_fname, 'w+') as save_file:
            json.dump(fp=save_file, obj=meta_data, indent=2)

        with open(self.event_log_fname, 'w+') as save_file:
            json.dump(fp=save_file, obj=self.event_log, indent=2)

        with self.message_lock:
            with open(self.message_history_fname, 'w+') as save_file:
                json.dump(fp=save_file, obj=self.send_history, indent=2)

        with self.state_lock:
            with open(self.state_history_fname, 'w+') as save_file:
                json.dump(fp=save_file, obj=self.state_history, indent=2)
        return

    def __start_threads(self):
        for thread_name, thread_entry in self.__thread_dict.items():
            each_thread = thread_entry['thread']
            each_thread.start()
        return

    def __send_command(self, command: str, wait_response: bool, receive_timeout: float = 4):
        """

        :param command:
        :param wait_response:
        :param receive_timeout:
        :return:
        """
        enc_command = command.encode(encoding='utf-8')
        initial_time = time.time()
        self.event_log.append(
            {'timestamp': initial_time, 'type': 'send', 'value': f'Sending message: {command}'}
        )
        self.client_socket.sendto(enc_command, self.tello_address)

        response_time = None
        response_message = None
        if wait_response:
            while self.outstanding_receive_count > 0:
                # todo  back-correlate messages that didn't receive a response
                #       assume packets are not received out of order
                _ = self.__receive_response(receive_timeout)
                self.outstanding_receive_count -= 1
            response_info = self.__receive_response(receive_timeout)
            response_message = response_info['response']
            response_time = response_info['receive_time']
        else:
            self.outstanding_receive_count += 1
        send_info = {
            'timestamp': initial_time, 'command': command, 'response_time': response_time, 'response': response_message
        }
        with self.message_lock:
            self.send_history.append(send_info)
        return send_info

    def __receive_response(self, receive_timeout: float):
        initial_time = time.time()
        response_str = None
        receive_time = None
        try:
            self.client_socket.settimeout(receive_timeout)
            response = self.client_socket.recvfrom(self.BUFFER_SIZE)
            receive_time = time.time()
            if isinstance(response, Exception):
                response_str = str(response)
            else:
                (response_bytes, _) = response
                response_str = response_bytes.decode('utf-8')
                self.event_log.append({'timestamp': time.time(), 'type': 'receive', 'value': f'{response_str}'})
        except UnicodeDecodeError:
            pass
        except socket.timeout:
            pass

        receive_message = {'timestamp': initial_time, 'response': response_str, 'receive_time': receive_time}
        with self.message_lock:
            self.receive_history.append(receive_message)
        return receive_message

    def __listen_state(self):
        """

        :return:
        """
        state_thread = self.__thread_dict['state']
        state_thread['running'] = True
        while state_thread['running']:
            try:
                state_bytes, _ = self.state_socket.recvfrom(self.BUFFER_SIZE)
                initial_time = time.time()
                state_str = state_bytes.decode('utf-8').strip()
                state_val_list = state_str.split(';')
                state_dict = {
                    state_entry.split(':')[0]: state_entry.split(':')[1]
                    for state_entry in state_val_list
                    if len(state_entry) > 0
                }
                state_dict['timestamp'] = initial_time
                with self.state_lock:
                    self.state_history.append(state_dict)
                self.event_log.append({'timestamp': time.time(), 'type': 'state', 'value': state_dict})
            except Exception as e:
                self.event_log.append({'timestamp': time.time(), 'type': 'status', 'value': f'{str(e)}'})
            time.sleep(self.STATE_DELAY)
        return

    def __listen_video(self):
        """
        always on

        :return:
        """
        self.video_capture = cv2.VideoCapture(self.VIDEO_UDP_URL, cv2.CAP_FFMPEG)
        if not self.video_capture.isOpened():
            self.event_log.append({'timestamp': time.time(), 'type': 'status',
                                   'value': f'Could not open video stream'})
            return

        self.event_log.append({'timestamp': time.time(), 'type': 'status',
                               'value': f'Opened video stream: {self.VIDEO_UDP_URL}'})

        # discard first read and make sure all is reading correctly
        read_success, video_frame = self.video_capture.read()
        if not read_success:
            self.event_log.append({'timestamp': time.time(), 'type': 'status',
                                   'value': f'Error reading from video stream'})
            return
        # save capture width and height for later when saving the video
        fps = 30
        frame_width = int(self.video_capture.get(3))
        frame_height = int(self.video_capture.get(4))
        self.event_log.append({'timestamp': time.time(), 'type': 'status',
                               'value': f'Read frame from video stream\n'
                                        f'FPS: {fps}\n'
                                        f'Width: {frame_width}\n'
                                        f'Height: {frame_height}'})

        codec_str = 'MJPG'
        self.video_writer = cv2.VideoWriter(
            self.video_fname, cv2.VideoWriter_fourcc(*codec_str),
            fps, (frame_width, frame_height)
        )

        video_thread = self.__thread_dict['video']
        video_thread['running'] = True
        self.video_start_time = time.time()
        print(f'running video loop')
        while self.video_capture.isOpened() and video_thread['running']:
            read_success, video_frame = self.video_capture.read()
            print('received frame')
            if read_success:
                print(f'read frame success')
                self.frame_history.append(video_frame)
                self.video_writer.write(video_frame.astype('uint8'))
            cv2.waitKey(self.FRAME_DELAY)
        self.video_end_time = time.time()

        self.video_capture.release()
        self.video_writer.release()
        cv2.destroyAllWindows()
        return

    def get_last_state(self):
        """
        Gets the latest state information from the stream to port 8890.

        pitch:  %d:     attitude pitch, degrees
        roll:   %d:     attitude roll, degrees
        yaw:    %d:     attitude yaw, degrees
        vgx:    %d:     speed x
        vgy:    %d:     speed y
        vgz:    %d:     speed z
        templ:  %d:     lowest temperature, degrees celsius
        temph:  %d:     highest temperature, degrees celsius
        tof:    %d:     distance from point of takeoff, centimeters
        h:      %d:     height from ground, centimeters
        bat:    %d:     current battery level, percentage
        baro:   %0.2f:  pressure measurement, cm
        time:   %d:     time motors have been on, seconds
        agx:    %0.2f:  acceleration x
        agy:    %0.2f:  acceleration y
        agz:    %0.2f:  acceleration z

        :return:
        """
        last_state = self.state_history[-1] if len(self.state_history) > 0 else None
        return last_state

    def get_last_frame(self):
        """
        Gets the latest video frame from the stream to port 11111.

        :return:
        """
        last_frame = self.frame_history[-1] if len(self.frame_history) > 0 else None
        return last_frame

    def control_command(self):
        """
        todo ???

        ok, error

        :return:
        """
        command_str = f'command'
        response = self.__send_command(command_str, wait_response=True)
        return response

    def control_streamon(self):
        """
        streamon

        sets the video stream on

        ok, error

        :return:
        """
        command_str = f'streamon'
        response = 'error'
        if self.sdk_mode:
            response = self.__send_command(command_str, wait_response=True)
        return response

    def control_streamoff(self):
        """
        streamoff

        sets the video stream off

        ok, error

        :return:
        """
        command_str = f'streamoff'
        response = 'error'
        if self.sdk_mode:
            response = self.__send_command(command_str, wait_response=True)
        return response

    def control_takeoff(self):
        """
        takeoff

        auto-takeoff

        ok, error

        :return:
        """
        command_str = f'takeoff'
        if self.sdk_mode:
            self.__send_command(command_str, wait_response=False)
        return

    def control_land(self):
        """
        lland

        auto-land

        ok, error

        :return:
        """
        command_str = f'land'
        if self.sdk_mode:
            print('land')
            self.__send_command(command_str, wait_response=False)
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
        if self.sdk_mode:
            response = self.__send_command(command_str, wait_response=False)
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
        if self.sdk_mode:
            self.__send_command(command_str, wait_response=False)
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
        if self.sdk_mode:
            self.__send_command(command_str, wait_response=False)
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
        if self.sdk_mode:
            self.__send_command(command_str, wait_response=False)
        return

    def get_speed(self):
        """
        speed?

        get current speed (cm/s)

        x: 1-100

        :return:
        """
        if not self.sdk_mode:
            return None
        last_state = self.get_last_state()
        if not last_state:
            return None

        vgx = float(last_state['vgx'])
        vgy = float(last_state['vgy'])
        vgz = float(last_state['vgz'])

        radicand = (vgx ** 2) + (vgy ** 2) + (vgz ** 2)
        total = math.sqrt(radicand)
        value = {
            'vgx': vgx,
            'vgy': vgy,
            'vgz': vgz,
            'total': total
        }
        return value

    def get_battery(self):
        """
        battery?

        get current battery percentage

        x: 0-100

        :return:
        """
        if not self.sdk_mode:
            return None
        last_state = self.get_last_state()
        value = float(last_state['bat']) if last_state else None
        return value

    def get_time(self):
        """
        time?

        get current fly time (s)

        time
        :return:
        """
        if not self.sdk_mode:
            return None
        last_state = self.get_last_state()
        value = float(last_state['time']) if last_state else None
        return value

    def get_height(self):
        """

        height?

        get height (cm)

        x: 0-3000

        :return:
        """
        if not self.sdk_mode:
            return None
        last_state = self.get_last_state()
        value = float(last_state['h']) if last_state else None
        return value

    def get_temp(self):
        """
        temp?

        get temperature (C)

        x: 0-90

        :return:
        """
        if not self.sdk_mode:
            return None
        last_state = self.get_last_state()
        if not last_state:
            return None

        temp_low = float(last_state['templ'])
        temp_high = float(last_state['temph'])
        value = {
            'templ': temp_low,
            'temph': temp_high,
            'range': temp_high - temp_low
        }
        return value

    def get_attitude(self):
        """
        attitude?

        get IMU attitude data

        pitch roll yaw

        :return:
        """
        if not self.sdk_mode:
            return None
        last_state = self.get_last_state()
        if not last_state:
            return None

        pitch = float(last_state['pitch'])
        roll = float(last_state['roll'])
        yaw = float(last_state['yaw'])
        value = {
            'pitch': pitch,
            'roll': roll,
            'yaw': yaw
        }
        return value

    def get_baro(self):
        """
        baro?

        get barometer value (m)

        x

        :return:
        """
        if not self.sdk_mode:
            return None
        last_state = self.get_last_state()
        value = float(last_state['baro']) if last_state else None
        return value

    def get_acceleration(self):
        """
        acceleration?

        get IMU angular acceleration data (0.001g)

        x y z

        :return:
        """
        if not self.sdk_mode:
            return None
        last_state = self.get_last_state()
        if not last_state:
            return None

        agx = float(last_state['agx'])
        agy = float(last_state['agy'])
        agz = float(last_state['agz'])

        radicand = (agx ** 2) + (agy ** 2) + (agz ** 2)
        total = math.sqrt(radicand)
        value = {
            'agx': agx,
            'agy': agy,
            'agz': agz,
            'total': total
        }
        return value

    def get_tof(self):
        """
        tof?

        get distance value from point of takeoff (cm)

        x: 30-1000

        :return:
        """
        if not self.sdk_mode:
            return None
        last_state = self.get_last_state()
        value = float(last_state['tof']) if last_state else None
        return value
