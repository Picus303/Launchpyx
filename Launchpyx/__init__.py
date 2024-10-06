import sys
import time
import json
import threading
import importlib.util
from queue import Queue
from rtmidi.midiconstants import NOTE_ON

from launchpad_control import LaunchpadController


class Macro:
    def __init__(self, manager, launchpad, stop_event, message_queue, actions, args):
        self.manager = manager
        self.launchpad = launchpad
        self.stop_event = stop_event
        self.message_queue = message_queue
        self.actions = actions
        self.args = args

        for action in actions:
            action_fct = getattr(self, action['name'])
            manager.register_action(action_fct, action['position'], action['color'], action['blocking'])

        self.positions = {action['name']: action['position'] for action in actions}
        self.colors = {action['name']: action['color'] for action in actions}

        self.register_args(args)

    def register_args(self, args):
        for arg, value in args.items():
            setattr(self, arg, value)


class MacroManager:
    def __init__(self, config_file, macros_files):
        self.startup_done = False

        self.load_config(config_file)
        self.launchpad = LaunchpadController()

        self.message_queue = Queue()
        self.blocking_macro_thread = None
        self.blocking_macro_active = False
        self.stop_event = threading.Event()

        self.load_macros(macros_files)

        self.actions = {}
        self.create_macros()

    def load_config(self, config_file):
        with open(config_file, 'r') as f:
            self.config = json.load(f)
    
    def load_macros(self, macros_files):
        if not isinstance(macros_files, list):
            macros_files = [macros_files]
        
        for macros_file in macros_files:
            module_name = macros_file.split('/')[-1].split('.')[0]

            spec = importlib.util.spec_from_file_location(module_name, macros_file)
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)

            globals().update({name: getattr(module, name) for name in dir(module) if not name.startswith('_')})

    def create_macros(self):
        for macro in self.config['macros']:
            macro_class = globals().get(macro['name'])
            if macro_class:
                macro_class(self, self.launchpad, self.stop_event, self.message_queue, macro['actions'], macro['args'])
            else:
                print(f"Macro {macro['name']} not found")

    def register_action(self, action_fct, position, color, blocking):
        self.actions[tuple(position)] = {'action': action_fct, 'color': color, 'blocking': blocking}
        if self.startup_done and not self.blocking_macro_active:
            self.launchpad.clear_grid()
            self.display_macro_buttons()

    def revoke_action(self, position):
        self.actions.pop(position, None)
        if not self.blocking_macro_active:
            self.launchpad.set_led_color(*position, 0)

    def initialize_launchpad(self, input_port_name, output_port_name):
        self.launchpad.open_ports(input_port_name, output_port_name)
        self.launchpad.enter_programmer_mode()
        self.launchpad.clear_grid()
        self.display_macro_buttons()

    def display_macro_buttons(self):
        self.launchpad.clear_grid()
        for position, action in self.actions.items():
            self.launchpad.set_led_color(*position, action['color'])
    
    def set_action_color(self, position, color):
        self.actions[tuple(position)]['color'] = color
        if not self.blocking_macro_active:
            self.launchpad.set_led_color(*position, color)

    def start(self):
        self.launchpad.set_callback(self.midi_callback)
        self.startup_done = True
        try:
            while True:
                time.sleep(0.1)
        except KeyboardInterrupt:
            self.stop_all()
        finally:
            self.launchpad.clear_grid()
            self.launchpad.exit_programmer_mode()
            self.launchpad.close_ports()

    def midi_callback(self, message, data=None):
        message_type, note, velocity = message[0]
        if self.blocking_macro_active:
            self.message_queue.put(message)
            self.check_exit_condition()
        else:
            if message_type == NOTE_ON and velocity > 0:
                i, j = self.launchpad.note_to_ij(note)
                action = self.actions.get((i, j))
                if action:
                    self.launch_action(action['action'], action['blocking'])

    def launch_action(self, action_fct, blocking):
        if self.blocking_macro_active:
            return

        if blocking:
            self.blocking_macro_active = True
            self.clear_macro_buttons()
            self.stop_event.clear()
            self.message_queue.queue.clear()
            self.blocking_macro_thread = threading.Thread(target=self.blocking_action_wrapper, args=(action_fct,))
            self.blocking_macro_thread.start()
        else:
            threading.Thread(target=action_fct).start()
    
    def blocking_action_wrapper(self, action_fct):
        action_fct()
        self.exit_blocking_action()
    
    def exit_blocking_action(self):
        self.blocking_macro_active = False
        self.display_macro_buttons()
        self.stop_event.set()

    def clear_macro_buttons(self):
        self.launchpad.clear_grid()

    def check_exit_condition(self):
        pressed_buttons = sum([sum(row) for row in self.launchpad.buttons_state])
        if pressed_buttons >= 3:
            self.stop_event.set()
            self.blocking_macro_thread.join()
            self.exit_blocking_action()

    def stop_all(self):
        self.stop_event.set()
        if self.blocking_macro_thread:
            self.blocking_macro_thread.join()