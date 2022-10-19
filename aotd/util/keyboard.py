"""
@title
@description

https://pypi.org/project/keyboard/
https://pyautogui.readthedocs.io/en/latest/keyboard.html
https://pythonhosted.org/pynput/keyboard.html
"""
import argparse
import msvcrt


def keypress():
    key_stroke = msvcrt.getch()
    return key_stroke


def main(main_args):
    return


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='')

    args = parser.parse_args()
    main(vars(args))
