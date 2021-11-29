from dataclasses import dataclass

from rlbot.utils.game_state_util import Vector3 as GamestateVector3

from mashumaro import DataClassJSONMixin


@dataclass
class Vector3(DataClassJSONMixin):
    x: float
    y: float
    z: float

    def to_gamestate(self) -> GamestateVector3:
        return GamestateVector3(x=self.x, y=self.y, z=self.z)
