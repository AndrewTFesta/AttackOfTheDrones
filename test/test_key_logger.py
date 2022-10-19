"""
@title
@description
"""
import argparse
import os
import time


def main(main_args):
    log_id = main_args.get('log_id', None)
    log_dir = main_args.get('log_dir', os.path.join(DATA_DIR, 'keylogger'))
    run_length = main_args.get('run_length', 10)
    #####################################################################
    key_logger = KeyLogger(log_dir=log_dir, log_id=log_id)
    print('starting listener')
    key_logger.start_listener()
    time.sleep(run_length)
    print('stopping listener')
    key_logger.cleanup()
    return


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='')

    args = parser.parse_args()
    main(vars(args))
