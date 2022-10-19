"""
@title
@description
"""
import argparse
import os
import threading
import time
from datetime import datetime
from queue import Queue

import cv2
import numpy as np

from aotd.video_iterator import ObservableVideo


def unit_vector(vector):
    """
    Returns the unit vector of the vector

    :param vector:
    :return:
    """
    return vector / np.linalg.norm(vector)


def angle_between(v1, v2):
    """
    Returns the angle in radians between vectors 'v1' and 'v2'

    :param v1:
    :param v2:
    :return:
    """
    v1_u = unit_vector(v1)
    v2_u = unit_vector(v2)
    return np.arccos(np.clip(np.dot(v1_u, v2_u), -1.0, 1.0))


class GestureControl:

    def __init__(self, display_feed: bool, DATA_DIR=None):
        """
        todo save processed video feed

        :param display_feed:
        """
        current_time = time.time()
        date_time = datetime.fromtimestamp(time.time())
        time_str = date_time.strftime("%Y-%m-%d-%H-%M-%S")

        # identification information
        self.name = 'gesture_recognition'
        self.id = f'{self.name}_{time_str}_{int(current_time)}'
        self.save_directory = os.path.join(DATA_DIR, 'gesture_recognition', f'{self.id}')
        self.video_fname = os.path.join(self.save_directory, f'{self.id}.avi')
        if not os.path.isdir(self.save_directory):
            os.makedirs(self.save_directory)

        self.__frame_queue = Queue()
        self.running = False
        self.process_thread = None
        self.window_name = 'Gesture Control'
        self.display_feed = display_feed
        self.video_writer = None

        self.history = []
        self.smoothing_factor = 30
        return

    def cleanup(self):
        self.running = False
        self.process_thread.join()
        return

    def add_frame(self, new_frame):
        self.__frame_queue.put(new_frame)
        return

    def get_last_flow(self):
        last_flow = self.history[-1] if len(self.history) > 0 else None
        return last_flow

    def get_smoothed_vector(self):
        """
        todo    fix since history is no longer just the vector or image
                compute smoothed vector based on 'vector' entry in history

        :return:
        """
        if len(self.history) == 0:
            return None
        num_frames = min(self.smoothing_factor, len(self.history))
        last_frame_list = self.history[-1 * num_frames]
        smoothed_vector = np.average(last_frame_list, axis=0)
        return smoothed_vector

    def start_process_thread(self):
        self.process_thread = threading.Thread(target=self.__process_frame_queue, daemon=True)
        self.process_thread.start()
        return

    def __process_frame_queue(self):
        """
        refactor to only compute frame differences

        track the optical flow for these corners
        https://docs.opencv.org/3.0-beta/modules/imgproc/doc/feature_detection.html
        https://docs.opencv.org/3.0-beta/modules/video/doc/motion_analysis_and_object_tracking.html

        :return:
        """
        num_initial = 10
        len_history = 10
        magnitude_threshold = 3
        frame_resize_factor = 0.25
        draw_color = (0, 255, 0)
        text_color = (0, 0, 255)
        text_font = cv2.FONT_HERSHEY_SIMPLEX
        text_scale = 0.45
        text_spacing = 14
        text_thickness = 1
        text_x0 = 0
        text_y0 = text_spacing * 2
        text_dy = text_spacing * 1
        start_arrow = (text_spacing * 1, text_spacing * 1)
        arrow_len = text_spacing * 1

        st_max_corners = 5
        st_quality_level = 0.2
        st_min_dist = 2
        st_blocksize = 7

        lk_win_size = (15, 15)
        lk_max_level = 2
        lk_criteria = (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 10, 0.03)

        shi_tomasi_params = {
            'maxCorners': st_max_corners,
            'qualityLevel': st_quality_level,
            'minDistance': st_min_dist,
            'blockSize': st_blocksize
        }
        lucas_kanade_params = {
            'winSize': lk_win_size,
            'maxLevel': lk_max_level,
            'criteria': lk_criteria
        }

        # use first frame to compute image characteristics
        first_frame = self.__frame_queue.get(block=True)
        frame_width = int(first_frame.shape[1] * frame_resize_factor)
        frame_height = int(first_frame.shape[0] * frame_resize_factor)
        frame_dims = (frame_width, frame_height)

        fps = 15
        codec_str = 'MJPG'
        self.video_writer = cv2.VideoWriter(
            self.video_fname, cv2.VideoWriter_fourcc(*codec_str),
            fps, (frame_width * 2, frame_height * 2)
        )

        prev_frame = cv2.resize(first_frame, frame_dims, interpolation=cv2.INTER_AREA)
        for frame_idx in range(num_initial):
            frame = self.__frame_queue.get(block=True)
            prev_frame = cv2.resize(frame, frame_dims, interpolation=cv2.INTER_AREA)

        prev_gray = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY)
        prev_features = cv2.goodFeaturesToTrack(prev_gray, mask=None, **shi_tomasi_params)
        base_angle = [1, 0]
        self.running = True
        while self.running:
            next_frame = self.__frame_queue.get(block=True)
            next_frame = cv2.resize(next_frame, frame_dims, interpolation=cv2.INTER_AREA)
            next_mask = np.zeros_like(prev_frame)
            total_mask = np.zeros_like(prev_frame)

            next_gray = cv2.cvtColor(next_frame, cv2.COLOR_BGR2GRAY)
            next_features, status, error = cv2.calcOpticalFlowPyrLK(
                prev_gray, next_gray, prev_features, None, **lucas_kanade_params
            )

            good_features_old = prev_features[status == 1]
            good_features_new = next_features[status == 1]
            shape_good_old = good_features_old.shape
            shape_good_new = good_features_new.shape
            num_good_old = shape_good_old[0]
            num_good_new = shape_good_new[0]
            if num_good_old == 0 or num_good_new == 0:
                # todo if hit this point, reinitialize system
                continue

            num_points = min(len(self.history), len_history)
            if num_points > 0:
                recent_feature_list = [
                    each_history['feature']
                    for each_history in self.history[-1 * num_points:]
                ]
                for idx, feature in enumerate(recent_feature_list):
                    feature_x, feature_y = feature.ravel()
                    total_mask = cv2.circle(total_mask, (feature_x, feature_y), 3, draw_color, -1)

            overlay_frame = cv2.add(next_frame, total_mask)
            first_feature_old = good_features_old[0, :]
            first_feature_new = good_features_new[0, :]
            old_x, old_y = first_feature_old.ravel()
            new_x, new_y = first_feature_new.ravel()
            feature_vector = (new_x - old_x, -1 * (new_y - old_y))

            next_mask = cv2.circle(next_mask, (new_x, new_y), 3, draw_color, -1)
            vector_mag = np.linalg.norm(feature_vector)
            x_end, y_end = start_arrow
            vector_unit = feature_vector / np.linalg.norm(feature_vector) if vector_mag != 0 else [0, 0]
            vector_dot = np.dot(vector_unit, base_angle)
            vector_angle = np.arcsin(vector_dot)
            vector_degrees = np.degrees(vector_angle)
            if vector_mag > magnitude_threshold:
                x_end = int(start_arrow[0] + arrow_len * vector_unit[0])
                y_end = int(start_arrow[1] + arrow_len * vector_unit[1])

            self.history.append({
                'raw': next_frame,
                'processed': overlay_frame,
                'feature': first_feature_new,
                'vector': feature_vector,
                'magnitude': vector_mag,
                'angle': vector_angle,
                'exceeds_threshold': vector_mag > magnitude_threshold
            })

            text_list = [
                {'field': f'Magnitude', 'value': f'{vector_mag:0.2f}'},
                {'field': f'Angle', 'value': f'{vector_degrees:0.2f}'},
                {'field': f'Vector', 'value': f'<{feature_vector[0]:0.2f}, {feature_vector[1]:0.2f}>'},
            ]
            cv2.arrowedLine(overlay_frame, start_arrow, (x_end, y_end), text_color, text_thickness)
            for idx, each_line in enumerate(text_list):
                text_field = each_line['field']
                text_val = each_line['value']
                cv2.putText(
                    img=overlay_frame, text=f'{text_field}: {text_val}', org=(text_x0, text_y0 + text_dy * (idx + 1)),
                    fontFace=text_font, fontScale=text_scale, color=text_color, thickness=text_thickness
                )
            prev_gray = next_gray.copy()
            prev_features = good_features_new.reshape(-1, 1, 2)

            top_layer = np.concatenate((next_frame, overlay_frame), axis=1)
            bottom_layer = np.concatenate((next_mask, total_mask), axis=1)
            frame_stack = np.concatenate((top_layer, bottom_layer), axis=0)

            if self.display_feed:
                cv2.imshow(self.window_name, frame_stack)
                self.video_writer.write(frame_stack.astype('uint8'))
                cv2.waitKey(10)
        self.video_writer.release()
        cv2.destroyWindow(self.window_name)
        return


def main(main_args):
    ###################################
    playback_file = main_args.get('playback_file', os.path.join(DATA_DIR, 'video', 'webcam_test_0.mp4'))
    video_length = main_args.get('length', 20)
    ###################################
    gesture_control = GestureControl(display_feed=True)
    observable_video = ObservableVideo(output=gesture_control, video_fname=playback_file)
    gesture_control.start_process_thread()
    ###################################
    observable_video.start_video_thread()
    time.sleep(video_length)
    gesture_control.cleanup()
    return


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('--playback_file', type=str, default=os.path.join(DATA_DIR, 'video', 'webcam_test_0.mp4'),
                        help='')
    parser.add_argument('--length', type=int, default=21,
                        help='')

    args = parser.parse_args()
    main(vars(args))
