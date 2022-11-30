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
                if detectedBarcodes:
                    # Traverse through all the detected barcodes in image
                    for barcode in detectedBarcodes:
                        (x, y, w, h) = barcode.rect

                        cv2.circle(img, (int(x + w / 2), int(y + h / 2)), 10, (0, 0, 255), -1)
                        cv2.putText(img, "Target", (int(x + w / 2)-25, int(y + h / 2)-25), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)


                img2 = cv2.cvtColor(numpy.array(video_frame), cv2.COLOR_RGB2HSV)
                lower = numpy.array([78, 126, 54], dtype="uint8")
                upper = numpy.array([88, 255, 255], dtype="uint8")
                mask = cv2.inRange(img2, lower, upper)

                # calculate moments of binary image
                M = cv2.moments(mask)

                try:
                    # calculate x,y coordinate of center
                    cX = int(M["m10"] / M["m00"])
                    cY = int(M["m01"] / M["m00"])

                    # put text and highlight the center
                    cv2.circle(img, (cX, cY), 10, (0, 0, 255), -1)
                    cv2.putText(img, "Target", (cX - 25, cY - 25), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
                except ZeroDivisionError:
                    pass

                cv2.imshow('Original', img)
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
