import math
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

    @staticmethod
    def from_vec(vec):
        return Vector3(vec.x, vec.y, vec.z)

    def length(self):
        """Returns the length of the vector. Also called magnitude and norm."""
        return math.sqrt(self.x**2 + self.y**2 + self.z**2)

    def dist(self, other: 'Vector3') -> float:
        """Returns the distance between this vector and another vector using pythagoras."""
        return (self - other).length()

    def __getitem__(self, item: int):
        return (self.x, self.y, self.z)[item]

    def __add__(self, other: 'Vector3') -> 'Vector3':
        return Vector3(self.x + other.x, self.y + other.y, self.z + other.z)

    def __sub__(self, other: 'Vector3') -> 'Vector3':
        return Vector3(self.x - other.x, self.y - other.y, self.z - other.z)
