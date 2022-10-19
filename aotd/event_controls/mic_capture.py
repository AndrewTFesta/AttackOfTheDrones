"""
@title
@description
"""
import os
import threading
import time
import wave

import pyaudio


class MicCapture:
    CHUNK = 1024
    FORMAT = pyaudio.paInt16
    CHANNELS = 2
    RATE = 44100

    def __init__(self, log_dir: str, log_id=None, callback_list=None):
        """
        ...and when I got one how to process it (do I need to use Fourier Transform like
        it was instructed in the above post)?

        If you want a "tap" then I think you are interested in amplitude more than frequency.
        So Fourier transforms probably aren't useful for your particular goal. You probably
        want to make a running measurement of the short-term (say 10 ms) amplitude of the input,
        and detect when it suddenly increases by a certain delta. You would need to tune the parameters of:

        what is the "short-term" amplitude measurement
        what is the delta increase you look for
        how quickly the delta change must occur
        Although I said you're not interested in frequency, you might want to do some filtering
        first, to filter out especially low and high frequency components. That might help you avoid
        some "false positives". You could do that with an FIR or IIR digital filter; Fourier isn't necessary.

        Yes, what I did was taking audioop.max(data,2) and change its value with the previous one (from the
        previous iteration). This way I can detect if there is a sudden increase.

        :param log_dir:
        :param log_id:
        """
        self.history = []
        self.callback_list = callback_list if callback_list is not None else []
        self.listen_thread = None
        self.listening = False

        self.py_audio = pyaudio.PyAudio()
        self.audio_stream = None
        start_time = time.time()

        if not os.path.isdir(log_dir):
            os.makedirs(log_dir)

        if log_id:
            self.log_fname = os.path.join(log_dir, f'log_{log_id}_{start_time}.wav')
        else:
            self.log_fname = os.path.join(log_dir, f'log_{start_time}.wav')
        return

    def start_listener(self):
        self.audio_stream = self.py_audio.open(
            format=self.FORMAT, channels=self.CHANNELS, rate=self.RATE,
            input=True, frames_per_buffer=self.CHUNK
        )

        self.listen_thread = threading.Thread(target=self.__listen, daemon=True)
        self.listen_thread.start()
        return

    def __listen(self):
        self.listening = True
        while self.listening:
            raw_data = self.audio_stream.read(self.CHUNK)
            self.history.append(raw_data)
            read_time = time.time()
            for each_callback in self.callback_list:
                if callable(each_callback):
                    each_callback({'timestamp': read_time, 'data': raw_data})
        return

    def stop_listener(self):
        self.listening = False
        return

    def cleanup(self):
        self.stop_listener()
        self.listen_thread.join()

        self.audio_stream.stop_stream()
        self.audio_stream.close()
        self.py_audio.terminate()
        self.save_history()
        return

    def save_history(self):
        with wave.open(self.log_fname, 'wb') as wave_file:
            wave_file.setnchannels(self.CHANNELS)
            wave_file.setsampwidth(self.py_audio.get_sample_size(self.FORMAT))
            wave_file.setframerate(self.RATE)
            wave_file.writeframes(b''.join(self.history))
            wave_file.close()
        return
