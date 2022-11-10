"""
@title

@description

"""
import argparse
import time
from pathlib import Path

import cv2
import numpy as np

from aotd.cv import detect_qr, display_qr
from aotd.project_properties import data_dir


def main(main_args):
    test_videos = [
        Path(data_dir, 'videos', 'phone_qr.mp4'),
        Path(data_dir, 'videos', 'drone_qr.mp4')
    ]

    for each_path in test_videos:
        cap = cv2.VideoCapture(str(each_path))

        while not cap.isOpened():
            print('Error opening video stream or file')
            time.sleep(1)
            cap = cv2.VideoCapture(each_path)

        # Read until video is completed
        stopped = False
        while cap.isOpened() and not stopped:
            ret, frame = cap.read()
            if ret:
                qrCodeDetector = cv2.QRCodeDetector()
                points = qrCodeDetector.detect(frame)[1]
                data, bbox, rectifiedImage = qrCodeDetector.detectAndDecode(frame)

                if points is not None:
                    if bbox is None:
                        print('Decoder failed')
                    points = points[0]

                    # get center of all points
                    center = tuple(np.mean(np.array(points), axis=0).astype(int))

                    # draw circle around QR code
                    cv2.circle(frame, center, 50, color=(255, 0, 0), thickness=2)

                    cv2.imshow('frame', frame)

                if cv2.waitKey(1) & 0xFF == ord('q'):
                    stopped = True

        cap.release()
        cv2.destroyAllWindows()
    return


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='')

    args = parser.parse_args()
    main(vars(args))
