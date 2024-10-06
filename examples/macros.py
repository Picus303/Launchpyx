import time
import random
import webbrowser
import numpy as np
import pyaudiowpatch as pyaudio
from obswebsocket import obsws, requests
from rtmidi.midiconstants import NOTE_ON

from Launchpyx import Macro


class OpenLink(Macro):
    """
    A simple macro that opens a specified URL in the default web browser.
    The URL is provided as an argument in the JSON configuration.
    """
    def run(self):
        webbrowser.open(self.url)


class RandomColor(Macro):
    """
    A macro that randomly changes the color of buttons on the Launchpad grid.
    It runs continuously until the stop event is triggered, changing the color
    of a random button on the grid at regular intervals.
    """
    def run(self):
        while not self.stop_event.is_set():
            i = random.randint(0, 7)
            j = random.randint(0, 7)
            color = random.randint(1, 127)
            self.launchpad.set_led_color(i, j, color)
            time.sleep(1 / self.speed)


class Paint(Macro):
    """
    A macro that allows you to "paint" on the Launchpad by toggling the LEDs on or off
    when a button is pressed. The color is set in the configuration.
    """
    def toggle_led(self, note):
        """
        Toggles the LED on or off based on the current state at the note's position.
        """
        i, j = self.launchpad.note_to_ij(note)
        if self.launchpad.led_state[i][j] == 0:
            self.launchpad.set_led_color(i, j, self.color)
        else:
            self.launchpad.set_led_color(i, j, 0)

    def run(self):
        """
        Continuously listens for button presses and toggles the corresponding LED.
        """
        self.launchpad.clear_grid()
        while not self.stop_event.is_set():
            while not self.message_queue.empty():
                message = self.message_queue.get()
                message_type, note, velocity = message[0]
                if message_type == NOTE_ON and velocity > 0:
                    self.toggle_led(note)
            time.sleep(0.1)


class AudioVisualizer(Macro):
    """
    A macro that creates a real-time audio visualizer on the Launchpad.
    It captures audio output and maps frequency ranges to the columns of the Launchpad,
    displaying intensity as LED brightness for each column.
    """
    def __init__(self, manager, launchpad, stop_event, message_queue, actions, args):
        super().__init__(manager, launchpad, stop_event, message_queue, actions, args)

        self.CHUNK_SIZE = 1024
        self.FORMAT = pyaudio.paInt16
        self.RATE = 44100
        self.COLUMN_COUNT = 8
        self.COLOR_SCHEME = [10, 20, 30, 40, 50, 60, 70, 80]  # Color values for each column
        self.AMPLITUDES_REFERENCE = np.array([1750000, 750000, 400000, 320000, 200000, 80000, 30000, 5000])
        self.FREQUENCY_RANGES = [(20, 78), (78, 312), (312, 625), (625, 1250), (1250, 2500), (2500, 5000), (5000, 10000), (10000, 20000)]

    def run(self):
        """
        Captures audio from the system and displays a real-time visual representation on the Launchpad.
        """
        p = pyaudio.PyAudio()
        try:
            wasapi_info = p.get_host_api_info_by_type(pyaudio.paWASAPI)
        except OSError:
            print("WASAPI not available.")
            return

        default_speakers = p.get_device_info_by_index(wasapi_info["defaultOutputDevice"])

        if not default_speakers["isLoopbackDevice"]:
            # Find the loopback device for capturing system audio
            for loopback in p.get_loopback_device_info_generator():
                if default_speakers["name"] in loopback["name"]:
                    default_speakers = loopback
                    break
            else:
                print("Loopback device not found.")
                return

        CHANNELS = default_speakers["maxInputChannels"]
        RATE = int(default_speakers["defaultSampleRate"])
        stream = p.open(format=self.FORMAT,
                        channels=CHANNELS,
                        rate=RATE,
                        frames_per_buffer=self.CHUNK_SIZE,
                        input=True,
                        input_device_index=default_speakers["index"])

        try:
            while not self.stop_event.is_set():
                # Read audio data
                data = stream.read(self.CHUNK_SIZE, exception_on_overflow=False)
                samples = np.frombuffer(data, dtype=np.int16)
                spectrum = np.abs(np.fft.fft(samples)[:self.CHUNK_SIZE // 2])
                freqs = np.fft.fftfreq(len(samples), 1 / RATE)[:self.CHUNK_SIZE // 2]

                # Map frequency bands to Launchpad columns
                for col, (start_freq, end_freq) in enumerate(self.FREQUENCY_RANGES):
                    col_indices = np.where((freqs >= start_freq) & (freqs < end_freq))[0]

                    if col_indices.size > 0:
                        intensity = np.max(spectrum[col_indices]) / self.AMPLITUDES_REFERENCE[col]
                    else:
                        intensity = 0

                    # Display intensity on the Launchpad
                    for row in range(8):
                        if intensity > (row / 8.0):
                            self.launchpad.set_led_color(row, col, self.COLOR_SCHEME[col])
                        else:
                            self.launchpad.set_led_color(row, col, 0)

                time.sleep(0.05)
        finally:
            stream.stop_stream()
            stream.close()
            p.terminate()


class OBSController(Macro):
    """
    A macro to control OBS (Open Broadcaster Software) via its WebSocket interface.
    This macro can connect/disconnect from OBS and switch between scenes.
    """
    def __init__(self, manager, launchpad, stop_event, message_queue, actions, args):
        super().__init__(manager, launchpad, stop_event, message_queue, actions, args)
        self.ws = obsws(self.host, self.port, self.password)
        self.connected = False

    def connect(self):
        """
        Connects to OBS via WebSocket.
        """
        if not self.connected:
            try:
                self.ws.connect()
                self.connected = True
                return True
            except Exception as e:
                print(f"Connection to OBS failed: {e}")
                return False

    def disconnect(self):
        """
        Disconnects from OBS.
        """
        if self.connected:
            self.ws.disconnect()
            self.connected = False

    def toggle_connection(self):
        """
        Toggles the connection to OBS and updates the button color based on the connection status.
        """
        if self.connected:
            self.disconnect()
            self.manager.set_action_color(self.positions['run_connect'], self.disconnected_color)
        else:
            success = self.connect()
            if success:
                self.manager.set_action_color(self.positions['run_connect'], self.connected_color)

    def change_scene(self, scene_name):
        """
        Switches to the specified scene in OBS.
        """
        if self.connected:
            try:
                self.ws.call(requests.SetCurrentProgramScene(sceneName=scene_name))
            except Exception as e:
                print(f"Failed to change scene: {e}")

    def run_connect(self):
        """
        Macro action to toggle the OBS connection when the button is pressed.
        """
        self.toggle_connection()

    def run_scene1(self):
        """
        Macro action to switch to Scene 1.
        """
        self.change_scene(self.scene1)

    def run_scene2(self):
        """
        Macro action to switch to Scene 2.
        """
        self.change_scene(self.scene2)