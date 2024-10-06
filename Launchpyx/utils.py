import rtmidi

def get_ports():
    midiout = rtmidi.MidiOut()
    midiin = rtmidi.MidiIn()

    available_input_ports = midiin.get_ports()
    available_output_ports = midiout.get_ports()

    return available_input_ports, available_output_ports