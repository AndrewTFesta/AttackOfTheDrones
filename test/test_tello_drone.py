"""
@title
@description
"""
import argparse
import time

# from aotd.ai_control.gesture_control import GestureControl
from aotd.project_properties import TERMINAL_COLUMNS
from aotd.tello_drone import TelloDrone, FlipDirection


def main(main_args):
    """

    :param main_args:
    :return:
    """
    send_delay = main_args.get('send_delay', 0.1)
    scan_delay = main_args.get('scan_delay', 0.1)
    ###################################
    tello_drone = TelloDrone()
    # gesture_control = GestureControl(display_feed=True)
    # gesture_control.start_process_thread()
    ###################################
    tello_drone.NETWORK_SCAN_DELAY = scan_delay
    tello_drone.SEND_DELAY = send_delay
    while not tello_drone.connect():
        time.sleep(scan_delay)
    time.sleep(1)
    ###################################
    battery = tello_drone.get_battery()
    speed = tello_drone.get_speed()
    time_aloft = tello_drone.get_time()
    height = tello_drone.get_height()
    accel = tello_drone.get_acceleration()
    attitude = tello_drone.get_attitude()
    baro = tello_drone.get_baro()
    temp = tello_drone.get_temp()
    tof = tello_drone.get_tof()

    print('-' * TERMINAL_COLUMNS)
    print(f'Battery:        {battery}')
    print(f'Speed:          {speed}')
    print(f'height:         {height}')
    print(f'attitude:       {attitude}')
    print(f'time aloft:     {time_aloft}')
    print(f'time of flight: {tof}')
    print(f'acceleration:   {accel}')
    print(f'barometer:      {baro}')
    print(f'temperature:    {temp}')
    print('-' * TERMINAL_COLUMNS)
    time.sleep(10)
    tello_drone.control_takeoff()
    time.sleep(5)
    tello_drone.set_rc(0, 0, 0, 50)
    time.sleep(1)
    tello_drone.set_rc(0, 0, 0, -50)
    time.sleep(1)
    tello_drone.set_rc(0, 0, 0, 50)
    time.sleep(1)
    tello_drone.control_flip(FlipDirection.BACK)
    time.sleep(5)
    tello_drone.control_land()
    time.sleep(5)
    tello_drone.cleanup()
    return


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('--send_delay', type=float, default=1,
                        help='')
    parser.add_argument('--scan_delay', type=float, default=1,
                        help='')

    args = parser.parse_args()
    main(vars(args))
