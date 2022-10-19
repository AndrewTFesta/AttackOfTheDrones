"""
@title
@description
"""
import threading

import cv2


class ObservableVideo:

    def __init__(self, video_fname, output):
        self.video_fname = video_fname
        self.video_thread = None
        self.output = output

        self.frame_delay = 30
        self.frame_history = []
        return

    def start_video_thread(self):
        self.video_thread = threading.Thread(target=self.__read_video, daemon=True)
        self.video_thread.start()
        return

    def __read_video(self):
        self.video_capture = cv2.VideoCapture(self.video_fname)
        if not self.video_capture.isOpened():
            raise RuntimeError(f'Could not open video stream')

        fps = round(float(self.video_capture.get(cv2.CAP_PROP_FPS)), 2)
        self.frame_delay = int(1000 / fps)
        print(f'Frames per second: {fps} | Frame delay: {self.frame_delay}')

        # discard first read and make sure all is reading correctly
        read_success, video_frame = self.video_capture.read()
        if not read_success:
            raise RuntimeError(f'Error reading from video stream')

        while self.video_capture.isOpened():
            read_success, video_frame = self.video_capture.read()
            if read_success:
                self.output.add_frame(video_frame)
                self.frame_history.append(video_frame)
            cv2.waitKey(self.frame_delay)
        self.video_capture.release()
        cv2.destroyAllWindows()
        return
