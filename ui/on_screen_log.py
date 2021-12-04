import random
from typing import List

from rlbot.utils.rendering.rendering_manager import RenderingManager


class OnScreenLog:
    def __init__(self, renderer: RenderingManager, num_lines: int, screen_x: int, screen_y: int, scale: int, color):
        self.screen_log: List[str] = []
        self.renderer = renderer
        self.num_lines = num_lines
        self.screen_x = screen_x
        self.screen_y = screen_y
        self.scale = scale
        self.color = color
        self.render_group = f"screen_log_{random.randint(0, 99999)}"

    def log(self, text: str):
        self.screen_log.append(text)
        print(f"[Screen Log] {text}")
        while len(self.screen_log) > self.num_lines:
            self.screen_log = self.screen_log[1:]
        self.renderer.begin_rendering(self.render_group)
        self.renderer.draw_string_2d(self.screen_x, self.screen_y, self.scale, self.scale, "\n".join(self.screen_log), self.color)
        self.renderer.end_rendering()
