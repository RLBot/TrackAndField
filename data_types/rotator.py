from dataclasses import dataclass

from mashumaro import DataClassJSONMixin
from rlbot.utils.game_state_util import Rotator as GamestateRotator


@dataclass
class Rotator(DataClassJSONMixin):
    pitch: float
    yaw: float
    roll: float

    def to_gamestate(self):
        return GamestateRotator(pitch=self.pitch, yaw=self.yaw, roll=self.roll)
