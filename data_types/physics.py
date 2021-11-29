from dataclasses import dataclass

from mashumaro import DataClassJSONMixin

from data_types.rotator import Rotator
from data_types.vector3 import Vector3

from rlbot.utils.game_state_util import Physics as GamestatePhysics


@dataclass
class Physics(DataClassJSONMixin):
    location: Vector3
    rotation: Rotator
    velocity: Vector3
    angular_velocity: Vector3

    def to_gamestate(self):
        return GamestatePhysics(
            location=self.location.to_gamestate(),
            rotation=self.rotation.to_gamestate(),
            velocity=self.velocity.to_gamestate(),
            angular_velocity=self.angular_velocity.to_gamestate())
