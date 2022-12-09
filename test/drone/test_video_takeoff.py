import sys
import threading
import traceback
import av
import cv2 as cv2  # for avoidance of pylint error
import numpy
import time

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
                image = cv2.cvtColor(numpy.array(video_frame), cv2.COLOR_RGB2BGR)
                # todo  process frame to find qr code
                #       draw square on frame

                cv2.imshow('Original', image)
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
        time.sleep(10)
        drone.takeoff()
        time.sleep(5)
        drone.down(50)
        time.sleep(5)
        drone.land()
        time.sleep(20)
        video_running = False
        time.sleep(5)


    except Exception as ex:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        traceback.print_exception(exc_type, exc_value, exc_traceback)
        print(ex)
    finally:
        drone.quit()
    return


if __name__ == '__main__':
    main()
