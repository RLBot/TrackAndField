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
        # Now we set up a json to let Track and Field know we can play waypointrace and are ready to go, then send it.
        json_str = json.dumps({"readyForTrackAndField": True, "supportedEvents": ["WaypointRace"]})
        self.matchcomms.outgoing_broadcast.put_nowait(json_str)
        # If we don't set this variable then python will have a fit
        recieved_message = False
        self.waypoint_target = 0
        while not recieved_message:
            try:
                self.msg = self.matchcomms.incoming_broadcast.get_nowait()  # Try to get all of the data from Track and Field
                recieved_message = True
                print(self.msg)
                print("Got waypoints, starting up now!")  # We have the waypoints now, lets start this thing up!
            except Empty:
                recieved_message = False  # No data yet, let's loop through it again

    def get_output(self, packet: GameTickPacket) -> SimpleControllerState:
        """
        This function will be called by the framework many times per second. This is where you can
        see the motion of the ball, etc. and return controls to drive your car.
        """
        self.boost_pad_tracker.update_boost_status(packet)
        if self.active_sequence is not None and not self.active_sequence.done:
            controls = self.active_sequence.tick(packet)
            if controls is not None:
                return controls
        # info about the car, and turning the waypoint data into something python likes
        my_car = packet.game_cars[self.index]
        car_location = Vec3(my_car.physics.location)
        points = json.loads(self.msg)
        my_car = packet.game_cars[self.index]
        car_velocity = Vec3(my_car.physics.velocity)
        # By default we will go after one of the waypoints, change self.waypoint_target to go after another waypoint
        target_location = Vec3(points["waypoints"][self.waypoint_target]["x"],
                               points["waypoints"][self.waypoint_target]["y"],
                               points["waypoints"][self.waypoint_target]["z"])

        # telling the bot to steer, etc
        self.renderer.draw_line_3d(car_location, target_location, self.renderer.cyan())

        controls = SimpleControllerState()
        controls.steer = steer_toward_target(my_car, target_location)
        controls.throttle = 1.0

        # Return the controls associated with the beginning of the sequence so we can start right away.
        return controls
