from rlbot.utils.game_state_util import CarState, Physics, Vector3 as Vector3GS, GameState
from rlbot.utils.structures.game_data_struct import GameTickPacket
from rlbot.utils.structures.game_interface import GameInterface

from data_types.rotator import Rotator
from data_types.vector3 import Vector3


class TimeLord:
    """
    Freezes a car in a particular place during the countdown to an event, then keeps track of elapsed time.
    """

    def __init__(
        self,
        packet_index: int,
        position: Vector3,
        rotation: Rotator,
        game_interface: GameInterface,
        countdown_seconds=3,
    ):
        self.packet_index = packet_index
        self.position = position
        self.rotation = rotation
        self.game_interface = game_interface
        self.countdown_start_time: float = None
        self.event_start_time: float = None
        self.is_bot_released = False
        self.done_animating = False
        self.already_rendered = []
        self.render_group = "countdown"
        self.countdown_seconds = countdown_seconds

    def get_event_elapsed_time(self, packet: GameTickPacket):
        return packet.game_info.seconds_elapsed - self.event_start_time

    def tick(self, packet: GameTickPacket):
        if self.countdown_start_time is None:
            self.countdown_start_time = packet.game_info.seconds_elapsed
            self.event_start_time = self.countdown_start_time + self.countdown_seconds

        countdown_elapsed = packet.game_info.seconds_elapsed - self.countdown_start_time
        event_elapsed = countdown_elapsed - self.countdown_seconds
        if countdown_elapsed < self.countdown_seconds:
            self.render_if_new(str(self.countdown_seconds - int(countdown_elapsed)))
            cars = {self.packet_index: CarState(
                physics=Physics(
                    location=self.position.to_gamestate(),
                    rotation=self.rotation.to_gamestate(),
                    velocity=Vector3GS(0, 0, 0),
                    angular_velocity=Vector3GS(0, 0, 0)
                ),
                boost_amount=100
            )}
            self.game_interface.set_game_state(GameState(cars=cars))
        elif countdown_elapsed < self.countdown_seconds + 1:
            self.is_bot_released = True
            self.render_if_new("GO")
        elif not self.done_animating:
            self.game_interface.renderer.clear_screen(self.render_group)
            self.done_animating = True

        if event_elapsed > 0:
            self.game_interface.renderer.begin_rendering("chronometer")
            self.game_interface.renderer.draw_string_2d(300, 350, 3, 3, f"{event_elapsed:.3f}", self.game_interface.renderer.lime())
            self.game_interface.renderer.end_rendering()

    def cleanup(self):
        self.game_interface.renderer.clear_screen("chronometer")
        self.game_interface.renderer.clear_screen(self.render_group)


    def render_if_new(self, text):
        if text not in self.already_rendered:
            self.render_text(text)

    def render_text(self, text):
        self.game_interface.renderer.begin_rendering(self.render_group)
        self.game_interface.renderer.draw_string_2d(300, 300, 3, 3, text, self.game_interface.renderer.yellow())
        self.game_interface.renderer.end_rendering()
