# Launchpyx

Launchpyx is a Python library that allows you to turn your Launchpad X into a customizable macro pad for automating workflows.

## Installation

You can install Launchpyx via pip:

```bash
pip install launchpyx
```

## Usage

To set up Launchpyx, you need two files:
- A Python file with your macro classes inherited from the library's `Macro` class.
- A configuration file (JSON) that associates actions/buttons with your macros.

Here’s a basic example of how to use Launchpyx to assign a macro to a button on your Launchpad X. In this example, we create a macro that opens a link when you press a button:

**macros.py**
```python
import webbrowser
from launchpyx import Macro

class OpenLink(Macro):
    def run(self):
        webbrowser.open(self.url)
```

**config.json**
```json
{
  "macros": [
    {
      "name": "OpenLink",
      "args": {
        "url": "https://example.com"
      },
      "actions": [
        {
          "name": "run",
          "position": [0, 0],
          "color": 5,
          "blocking": false
        }
      ]
    }
  ]
}
{
  "macros": [
    {
      "name": "OpenLink",
      "args": {
        "url": "https://example.com"
      },
      "actions": [
        {
          "name": "run",
          "position": [0, 0],
          "color": 5,
          "blocking": false
        }
      ]
    }
  ]
}
```

Finally, you can run the program to assign the macro:
```python
from launchpyx import MacroManager
from launchpyx.utils import get_ports

if __name__ == '__main__':
    input_ports, output_ports = get_ports()  # Use this function to get the names of your MIDI ports
    manager = MacroManager('config.json', 'macros.py')
    manager.initialize_launchpad('MIDIIN2 (LPX MIDI) 1', 'MIDIOUT2 (LPX MIDI) 2')
    manager.start()
```

With this, the button at the bottom left of your Launchpad should light up in red and open a link when you press it.

### Information

- By assigning multiple actions/buttons to a single macro, you can manage persistent data and perform more complex tasks.
- The Launchpad X has a unique way of handling colors. You can find the values corresponding to each color on page 12 of the [programmer reference manual](https://fael-downloads-prod.focusrite.com/customer/prod/s3fs-public/downloads/Launchpad%20X%20-%20Programmers%20Reference%20Manual.pdf).
- Actions associated with macros can be either blocking or non-blocking. A blocking action is one that uses the pad while it is being executed (e.g., to display random colors). When a blocking action is executed, the pad is automatically cleared, and the buttons associated with other actions are deactivated.
- You can change the color of the button assigned to an action using `self.manager.set_action_color(self.positions['action_name'], color)` (useful for displaying a status change, for example).
- You can temporarily change the color of any button using `self.launchpad.set_led_color(row, col, color)` (normally, this should only be used inside a blocking action).
- You can dynamically register new actions at runtime using `self.manager.register_action(function, [row, col], color, blocking)`.
- You can also dynamically remove an action using `self.manager.revoke_action([row, col])`.

### Advanced Usage

You can find more advanced examples in the **examples** folder of this repository.

## License

This project is licensed under the MIT License. See the LICENSE file for details.