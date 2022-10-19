"""
@title
@description
"""
import argparse
import time

from aotd.tello_drone import TelloDrone
from aotd.util.observable import Observer, Observable


class AutoControl(Observer, Observable):

    def __init__(self, observable_list: list):
        Observer.__init__(self, sub_list=observable_list)
        Observable.__init__(self)
        return

    def update(self, source, update_message):
        if isinstance(source, TelloDrone):
            message_type = update_message['type']
            message_value = update_message['value']
            if message_type == 'video':
                # todo
                self.set_changed_message({'timestamp': time.time(), 'type': 'video', 'value': message_value})
        return


def main(main_args):
    send_delay = main_args.get('send_delay', 0.1)
    scan_delay = main_args.get('scan_delay', 0.1)
    ###################################
    tello_drone = TelloDrone()
    tello_drone.NETWORK_SCAN_DELAY = scan_delay
    tello_drone.SEND_DELAY = send_delay
    tello_drone.connect()
    ###################################
    auto_control = AutoControl(observable_list=[tello_drone])
    ###################################
    time.sleep(10)
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
