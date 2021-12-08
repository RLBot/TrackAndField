from queue import Empty
from typing import List

from rlbot.agents.base_agent import BaseAgent
from rlbot.agents.base_agent import SimpleControllerState
from rlbot.utils.structures.game_data_struct import GameTickPacket

from util.boost_pad_tracker import BoostPadTracker
from util.drive import steer_toward_target
from util.sequence import Sequence, ControlStep, Step, StepResult
from util.vec import Vec3


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
        message = {"readyForTrackAndField": True, "supportedEvents": ["WaypointRace"]}
        self.matchcomms.outgoing_broadcast.put_nowait(message)

    def get_output(self, packet: GameTickPacket) -> SimpleControllerState:
        """
        This function will be called by the framework many times per second. This is where you can
        see the motion of the ball, etc. and return controls to drive your car.
        """
        try:
            message = self.matchcomms.incoming_broadcast.get_nowait()  # Try to get all of the data from Track and Field
            if message.get("event_type") == 'WaypointRace':
                print("Got waypoints, starting up now!")  # We have the waypoints now, lets start this thing up!
                waypoints = [Vec3(w['x'], w['y'], w['z']) for w in message["waypoints"]]
                waypoint_tolerance = message["waypoint_tolerance"]
                self.active_sequence = Sequence([
                    RunWaypointRace(waypoints, waypoint_tolerance, self)
                ])
        except Empty:
            pass  # No message, no problem

        self.boost_pad_tracker.update_boost_status(packet)
        if self.active_sequence is not None and not self.active_sequence.done:
            controls = self.active_sequence.tick(packet)
            if controls is not None:
                return controls

        # If we have no track and field tasks, drive forward and back so people know we're excited.
        self.active_sequence = Sequence([
            ControlStep(1, SimpleControllerState(throttle=1)),
            ControlStep(1, SimpleControllerState(throttle=-1))
        ])

        return SimpleControllerState()


class RunWaypointRace(Step):
    def __init__(self, waypoints: List[Vec3], waypoint_tolerance: float, bot: MyBot):
        self.waypoints = waypoints
        self.waypoint_tolerance = waypoint_tolerance
        self.bot = bot
        self.waypoint_index = 0

    def tick(self, packet: GameTickPacket) -> StepResult:

        my_car = packet.game_cars[self.bot.index]
        car_location = Vec3(my_car.physics.location)
        target_location = self.waypoints[self.waypoint_index]
        if car_location.dist(target_location) < self.waypoint_tolerance:
            if self.waypoint_index >= len(self.waypoints) - 1:
                return StepResult(controls=SimpleControllerState(), done=True)
            self.waypoint_index += 1

        controls = SimpleControllerState()
        controls.steer = steer_toward_target(my_car, target_location)
        controls.throttle = 1.0

        self.bot.renderer.draw_line_3d(car_location, target_location, self.bot.renderer.white())

        return StepResult(controls=controls, done=False)
