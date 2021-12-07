import time

from rlbot.agents.base_agent import BaseAgent, SimpleControllerState
from rlbot.messages.flat.QuickChatSelection import QuickChatSelection
from rlbot.utils.structures.game_data_struct import GameTickPacket
from util.ball_prediction_analysis import find_slice_at_time
from util.boost_pad_tracker import BoostPadTracker
from util.drive import steer_toward_target
from util.sequence import Sequence, ControlStep
from util.vec import Vec3
from queue import Empty
from rlbot.agents.base_agent import SimpleControllerState
from rlbot.utils.structures.game_data_struct import GameTickPacket
from rlbot.matchcomms.common_uses.set_attributes_message import handle_set_attributes_message
from rlbot.matchcomms.client import MatchcommsClient
import json

class MyBot(BaseAgent):
    """
    accepts parameters over matchcomms.
        """

    def __init__(self, name, team, index):
        super().__init__(name, team, index)
        self.active_sequence: Sequence = None
        self.boost_pad_tracker = BoostPadTracker()

    def initialize_agent(self):
        # Set up information about the boost pads now that the game is active and the info is available
        self.boost_pad_tracker.initialize_boosts(self.get_field_info())

    def get_output(self, packet: GameTickPacket) -> SimpleControllerState:
        """
        This function will be called by the framework many times per second. This is where you can
        see the motion of the ball, etc. and return controls to drive your car.
        """


        try:
            global msg
            msg = self.matchcomms.incoming_broadcast.get_nowait()
        except Empty:
            print("No messages received!")
        # This is good to keep at the beginning of get_output. It will allow you to continue
        # any sequences that you may have started during a previous call to get_output.
        self.boost_pad_tracker.update_boost_status(packet)
        if self.active_sequence is not None and not self.active_sequence.done:
            controls = self.active_sequence.tick(packet)
            if controls is not None:
                return controls

        # info about the car, and sending some mandatory messages to let track & field know we are up and running
        my_car = packet.game_cars[self.index]
        car_location = Vec3(my_car.physics.location)
        points = json.loads(msg)
        my_car = packet.game_cars[self.index]
        car_velocity = Vec3(my_car.physics.velocity)
        # By default we will go after one of the waypoints
        target_location = Vec3(points["waypoints"][0]["x"], points["waypoints"][0]["y"], points["waypoints"][0]["z"])

        # telling the bot to steer, etc
        self.renderer.draw_line_3d(car_location, target_location, self.renderer.cyan())

        controls = SimpleControllerState()
        controls.steer = steer_toward_target(my_car, target_location)
        controls.throttle = 1.0

        # Return the controls associated with the beginning of the sequence so we can start right away.
        return controls