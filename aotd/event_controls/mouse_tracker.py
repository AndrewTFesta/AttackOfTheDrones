"""
@title
@description
"""
import logging
import os
import threading
import time

from pynput import mouse


class MouseTracker:

    def __init__(self, log_dir: str, log_id=None, callback_list=None):
        self.history = []
        self.callback_list = callback_list if callback_list is not None else []
        self.listen_thread = None
        self.listening = None

        self.mouse_listener = mouse.Listener(on_move=self.on_move, on_click=self.on_click, on_scroll=self.on_scroll)
        start_time = time.time()

        if not os.path.isdir(log_dir):
            os.makedirs(log_dir)

        if log_id:
            self.log_fname = os.path.join(log_dir, f'log_{log_id}_{start_time}.txt')
        else:
            self.log_fname = os.path.join(log_dir, f'log_{start_time}.txt')
        return

    def on_move(self, x, y):
        new_item = {'type': 'move', 'x': x, 'y': y}
        self.history.append(new_item)
        logging.info(new_item)
        return

    def on_click(self, x, y, button, pressed):
        new_item = {'type': 'click', 'x': x, 'y': y, 'button': button, 'pressed': pressed}
        self.history.append(new_item)
        logging.info(new_item)
        return

    def on_scroll(self, x, y, dx, dy):
        new_item = {'type': 'scroll', 'x': x, 'y': y, 'dy': dy, 'dx': dx}
        self.history.append(new_item)
        logging.info(new_item)
        return

    def start_listener(self):
        self.listen_thread = threading.Thread(target=self.__listen, daemon=True)
        self.listen_thread.start()
        return

    def __listen(self):
        self.listening = True
        logging.basicConfig(filename=self.log_fname, level=logging.DEBUG, format='%(asctime)s: %(message)s')
        self.mouse_listener.start()
        while self.listening:
            pass
        return

    def stop_listener(self):
        self.listening = False
        return

    def cleanup(self):
        self.stop_listener()
        self.listen_thread.join()

        self.mouse_listener.stop()
        return
