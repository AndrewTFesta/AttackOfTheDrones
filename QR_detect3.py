import cv2
from pyzbar import pyzbar


def read_barcodes(frame):
    QRcodes = pyzbar.decode(frame)
    for QRcode in QRcodes:
        x, y, w, h = QRcode.rect
        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
        cv2.circle(frame, (int(x + w / 2), int(y + h / 2)), radius=2, color=(0, 0, 255), thickness=5)

    return frame


def main():
    camera = cv2.VideoCapture('media/test_vid2.mp4')
    ret, frame = camera.read()
    while ret:
        ret, frame = camera.read()
        frame = cv2.flip(frame, -1)
        frame = cv2.resize(frame, (480, 750))
        frame = read_barcodes(frame)
        cv2.imshow('Barcode/QR code reader', frame)
        if cv2.waitKey(1) & 0xFF == 27:
            break
    camera.release()
    cv2.destroyAllWindows()


# 4
if __name__ == '__main__':
    main()
