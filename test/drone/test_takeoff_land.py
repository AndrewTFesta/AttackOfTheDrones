"""
@title
@description
"""
import argparse
import time

from aotd.tello_drone import TelloDrone


def main(main_args):
    """

    :param main_args:
    :return:
    """
    send_delay = main_args.get('send_delay', 0.1)
    scan_delay = main_args.get('scan_delay', 0.1)
    ###################################
    tello_drone = TelloDrone()
    ###################################
    tello_drone.NETWORK_SCAN_DELAY = scan_delay
    tello_drone.SEND_DELAY = send_delay
    tello_drone.connect()

    tello_drone.control_takeoff()
    time.sleep(2)
    tello_drone.control_land()
    time.sleep(2)
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
