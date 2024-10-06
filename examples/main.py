from Launchpyx import MacroManager
from Launchpyx.utils import get_ports

if __name__ == '__main__':
    input_ports, output_ports = get_ports()
    print("Available input ports:", input_ports)
    print("Available output ports:", output_ports)

    manager = MacroManager('config.json', "macros.py")
    manager.initialize_launchpad('MIDIIN2 (LPX MIDI) 1', 'MIDIOUT2 (LPX MIDI) 2')
    manager.start()