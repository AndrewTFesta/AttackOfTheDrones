"""
@title
@description
"""
import argparse
from pathlib import Path

from aotd import DATA_DIR


def main(main_args):
    """

    :param main_args:
    :return:
    """
    log_id = main_args.get('log_id', None)
    log_dir = main_args.get('log_dir', Path(DATA_DIR, 'keylogger'))
    run_length = main_args.get('run_length', 10)
    return


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('--send_delay', type=float, default=1,
                        help='')
    parser.add_argument('--scan_delay', type=float, default=1,
                        help='')

    args = parser.parse_args()
    main(vars(args))
