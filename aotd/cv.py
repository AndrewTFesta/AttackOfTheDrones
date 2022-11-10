"""
@title

@description

"""
import argparse

import cv2
import numpy as np


# Display barcode and QR code location
def display_qr(im, bbox):
    n = len(bbox)
    for j in range(n):
        cv2.line(im, tuple(bbox[j][0]), tuple(bbox[(j + 1) % n][0]), (255, 0, 0), 3)

    # Display results
    cv2.imshow("Results", im)
    return


def detect_qr(frame):
    qr_decoder = cv2.QRCodeDetector()

    bbox, rect_img = qr_decoder.detect(frame)
    return bbox, rect_img
