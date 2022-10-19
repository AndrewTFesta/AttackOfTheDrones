"""
@title
@description
"""
import os
import threading
import time

import cv2
import dlib
import numpy as np

from auto_drone import DATA_DIR


def shape_to_np(shape, dtype='int'):
    coords = np.zeros((68, 2), dtype=dtype)
    for i in range(0, 68):
        coords[i] = (shape.part(i).x, shape.part(i).y)
    return coords


class EyeTracker:

    FRAME_DELAY = 1

    def __init__(self, log_dir: str, log_id=None, callback_list=None):
        self.history = []
        self.callback_list = callback_list if callback_list is not None else []
        self.listen_thread = None
        self.listening = False

        self.webcam_index = 0
        self.video_capture = cv2.VideoCapture(self.webcam_index)
        self.detector = dlib.get_frontal_face_detector()
        self.predictor = dlib.shape_predictor(
            os.path.join(DATA_DIR, 'eye_tracking', 'shape_predictor_68_face_landmarks.dat')
        )
        self.video_writer = None
        self.video_start_time = None
        self.video_end_time = None
        start_time = time.time()

        if not os.path.isdir(log_dir):
            os.makedirs(log_dir)

        if log_id:
            self.log_fname = os.path.join(log_dir, f'log_{log_id}_{start_time}.txt')
            self.video_fname = os.path.join(log_dir, f'video_{log_id}_{start_time}.avi')
        else:
            self.log_fname = os.path.join(log_dir, f'log_{start_time}.txt')
            self.video_fname = os.path.join(log_dir, f'video_{start_time}.avi')
        return

    def start_listener(self):
        self.listen_thread = threading.Thread(target=self.__listen, daemon=True)
        self.listen_thread.start()
        return

    def __listen(self):
        if not self.video_capture.isOpened():
            print(f'Could not open video stream')
            return

        print(f'Opened video stream: {self.webcam_index}')

        # discard first read and make sure all is reading correctly
        read_success, video_frame = self.video_capture.read()
        if not read_success:
            print(f'Error reading from video stream')
            return

        calibration_frame_count = 120
        calibration_start = time.time()
        for frame_idx in range(0, calibration_frame_count):
            _, _ = self.video_capture.read()
        calibration_end = time.time()

        # save capture width and height for later when saving the video
        fps = int(calibration_frame_count / (calibration_end - calibration_start))
        frame_width = int(self.video_capture.get(3))
        frame_height = int(self.video_capture.get(4))
        print(f'Read frame from video stream\n'
              f'FPS: {fps}\n'
              f'Width: {frame_width}\n'
              f'Height: {frame_height}')

        codec_str = 'MJPG'
        self.video_writer = cv2.VideoWriter(
            self.video_fname, cv2.VideoWriter_fourcc(*codec_str),
            fps, (frame_width, frame_height)
        )

        self.listening = True
        self.video_start_time = time.time()
        while self.listening:
            ret, img = self.video_capture.read()
            if ret:
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                rects = self.detector(gray, 1)

                for (i, rect) in enumerate(rects):
                    shape = self.predictor(gray, rect)
                    shape = shape_to_np(shape)
                    for (x, y) in shape:
                        cv2.circle(img, (x, y), 2, (0, 0, 255), -1)

                self.video_writer.write(img.astype('uint8'))
                cv2.imshow('EyeTracker', img)
                cv2.waitKey(self.FRAME_DELAY)

                self.history.append(img)
                # # todo save to video
                read_time = time.time()
                for each_callback in self.callback_list:
                    if callable(each_callback):
                        each_callback({'timestamp': read_time, 'data': img})
        self.video_end_time = time.time()
        cv2.destroyAllWindows()
        self.video_capture.release()
        return

    def stop_listener(self):
        self.listening = False
        return

    def cleanup(self):
        self.stop_listener()
        self.listen_thread.join()
        return
