import sys
import threading
import traceback
import av
import cv2 as cv2  # for avoidance of pylint error
import numpy
import time
from pyzbar.pyzbar import decode

from aotd.tellopy.tello import Tello


def handler(event, sender, data, **args):
    drone = sender
    if event is drone.EVENT_FLIGHT_DATA:
        # print(data)
        pass
    return


def main():
    def video_handler():
        # skip first 300 frames
        frame_skip = 300
        video_running = True
        detector = cv2.QRCodeDetector()
        while video_running:
            print('video running')
            for frame in container.decode(video=0):
                if 0 < frame_skip:
                    frame_skip = frame_skip - 1
                    continue
                start_time = time.time()
                video_frame = frame.to_image()
                # todo  process frame to find qr code
                #       draw square on frame


                img = cv2.cvtColor(numpy.array(video_frame), cv2.COLOR_RGB2BGR)
                detectedBarcodes = decode(img)

                # If not detected then print the message
                if not detectedBarcodes:
                    print("Barcode Not Detected or your barcode is blank/corrupted!")
                else:

                    # Traverse through all the detected barcodes in image
                    for barcode in detectedBarcodes:
                        (x, y, w, h) = barcode.rect

                        cv2.rectangle(img, (x - 10, y - 10),
                                      (x + w + 10, y + h + 10),
                                      (0, 0, 255), 2)

                        cv2.circle(img, (int(x + w / 2), int(y + h / 2)), radius=5, color=(0, 255, 0), thickness=5)
                        cv2.circle(img, (int(x + w / 2), int(y + h / 2)), radius=2, color=(0, 0, 255), thickness=5)

                # Display the image
                cv2.imshow("Image", img)


                # img = cv2.cvtColor(numpy.array(video_frame), cv2.COLOR_RGB2BGR)
                #
                # img_gray = cv2.cvtColor(numpy.array(video_frame), cv2.COLOR_BGR2GRAY)
                # data, bbox, _ = detector.detectAndDecode(img_gray)
                #
                # if bbox is not None:
                #     top_left = (int(bbox[0][2][0]) - 10, int(bbox[0][2][1]) - 10)
                #     bottom_right = (int(bbox[0][0][0]) + 10, int(bbox[0][0][1]) + 10)
                #     img = cv2.rectangle(img, top_left, bottom_right, (0, 0, 255), 3)
                #     center_x = int((bbox[0][2][0] + bbox[0][0][0]) / 2)
                #     center_y = int((bbox[0][2][1] + bbox[0][0][1]) / 2)
                #     img = cv2.circle(img, (center_x, center_y), radius=5, color=(0, 255, 0), thickness=5)
                #     img = cv2.circle(img, (center_x, center_y), radius=2, color=(0, 0, 255), thickness=5)
                #
                # cv2.imshow("Video", img)

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

    try:
        drone.subscribe(drone.EVENT_FLIGHT_DATA, handler)

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
        time.sleep(100)
        video_running = False
        time.sleep(5)


    except Exception as ex:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        traceback.print_exception(exc_type, exc_value, exc_traceback)
        print(ex)
    finally:
        drone.quit()


if __name__ == '__main__':
    main()
