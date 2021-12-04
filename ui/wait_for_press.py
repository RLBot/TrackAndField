import time

from pynput import keyboard
from rlbot.utils.rendering.rendering_manager import RenderingManager


class KeyWaiter:

    def __init__(self):
        self.desired_key_press: str = None
        self.action_description: str = None
        self.done = False

    def wait_for_press(self, key: str, action_description: str, renderer: RenderingManager):
        self.desired_key_press = key
        self.action_description = action_description
        listener = keyboard.Listener(on_press=self.on_press)
        listener.start()
        while not self.done:
            renderer.begin_rendering("wait_for_press")
            renderer.draw_string_2d(300, 300, 3, 3, f"Press {self.desired_key_press} to {self.action_description}.", renderer.cyan())
            renderer.end_rendering()
            time.sleep(.1)
        renderer.begin_rendering("wait_for_press")
        renderer.end_rendering()
        listener.stop()
        listener.join()

    def on_press(self, key):
        char = None
        try:
            char = key.char
        except AttributeError:
            pass

        if char == self.desired_key_press:
            self.done = True

