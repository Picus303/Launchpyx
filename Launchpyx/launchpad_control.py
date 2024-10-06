import rtmidi
from rtmidi.midiconstants import NOTE_ON


class LaunchpadController:
    def __init__(self):
        self.midiin = rtmidi.MidiIn()
        self.midiout = rtmidi.MidiOut()
        self.led_state = [[0 for _ in range(8)] for _ in range(8)]
        self.buttons_state = [[0 for _ in range(8)] for _ in range(8)]
        self.general_callback = None

    def open_ports(self, input_port_name, output_port_name):
        available_input_ports = self.midiin.get_ports()
        if input_port_name in available_input_ports:
            self.midiin.open_port(available_input_ports.index(input_port_name))
        else:
            print(f"Port d'entrée {input_port_name} non trouvé.")
            exit(1)

        available_output_ports = self.midiout.get_ports()
        if output_port_name in available_output_ports:
            self.midiout.open_port(available_output_ports.index(output_port_name))
        else:
            print(f"Port de sortie {output_port_name} non trouvé.")
            exit(1)

    def send_sysex_message(self, data):
        message = [0xF0] + data + [0xF7]
        self.midiout.send_message(message)

    def enter_programmer_mode(self):
        sysex_programmer_mode = [0x00, 0x20, 0x29, 0x02, 0x0C, 0x0E, 0x01]
        self.send_sysex_message(sysex_programmer_mode)

    def exit_programmer_mode(self):
        sysex_exit_programmer_mode = [0x00, 0x20, 0x29, 0x02, 0x0C, 0x0E, 0x00]
        self.send_sysex_message(sysex_exit_programmer_mode)

    def ij_to_note(self, i, j):
        return int(str(i + 1) + str(j + 1))

    def note_to_ij(self, note):
        note = str(note)
        return int(note[0]) - 1, int(note[1]) - 1

    def set_led_color(self, i, j, color):
        note = self.ij_to_note(i, j)
        self.midiout.send_message([0x90, note, color])
        self.led_state[i][j] = color

    def clear_grid(self):
        for i in range(8):
            for j in range(8):
                self.set_led_color(i, j, 0)

    def close_ports(self):
        self.midiin.close_port()
        self.midiout.close_port()

    def set_callback(self, callback):
        self.general_callback = callback
        self.midiin.set_callback(self.midi_callback)

    def midi_callback(self, message, data=None):
        message_type, note, _ = message[0]

        if message_type == NOTE_ON:
            i, j = self.note_to_ij(note)
            self.buttons_state[i][j] = 1 - self.buttons_state[i][j]

        if self.general_callback:
            self.general_callback(message)