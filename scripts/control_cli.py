"""
@title
@description
"""
import argparse
import threading

from auto_drone.drone.tello_drone import TelloDrone


class ControlCli:

    def __init__(self, drone: TelloDrone):
        self.drone = drone
        self.running = False

        self.option_menu = {
            'exit': self.destroy,
        }

        # move_option_list = {f'move {direction.name}': direction.value for direction in MoveDirection}
        # flip_option_list = {f'flip {direction.name}': direction.value for direction in FlipDirection}
        # rotate_option_list = {f'rotate {direction.name}': direction.value for direction in RotateDirection}

        # self.option_menu = dict(self.option_menu, **move_option_list)
        # self.option_menu = dict(self.option_menu, **flip_option_list)
        # self.option_menu = dict(self.option_menu, **rotate_option_list)
        return

    def display_menu(self):
        print(str(self.drone))
        for idx, (option_name, option_func) in enumerate(self.option_menu.items()):
            print(f'{idx}: {" ".join(option_name.lower().split("_"))}')
        return

    def run_menu(self):
        # todo add check for it drone is connected
        self.running = True
        user_prompt = f'Enter the index of a displayed option: '
        user_option = ''
        while self.running:
            self.display_menu()
            # todo add input validation
            user_option = int(input(user_prompt))
            print(user_option)
        return

    def destroy(self):
        self.drone.cleanup()
        return


def main(main_args):
    """

    :param main_args:
    :return:
    """
    send_delay = main_args.get('send_delay', 0.1)
    scan_delay = main_args.get('scan_delay', 0.1)
    ###################################
    tello_drone = TelloDrone()
    tello_drone.NETWORK_SCAN_DELAY = scan_delay
    tello_drone.SEND_DELAY = send_delay
    tello_drone.connect()

    control_cli = ControlCli(drone=tello_drone)
    ###################################
    print(tello_drone)
    # connect call blocks until connected
    connect_thread = threading.Thread(
        target=tello_drone.connect(),
        args=(),
        daemon=True
    )
    connect_thread.start()
    ###################################
    control_cli.run_menu()
    return


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('--timeout', type=float, default=1,
                        help='')

    args = parser.parse_args()
    main(vars(args))
