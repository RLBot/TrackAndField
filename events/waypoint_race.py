import math
from dataclasses import dataclass
from pathlib import Path
from random import randint

from mashumaro import DataClassJSONMixin
from rlbot.matchcomms.client import MatchcommsClient
from rlbot.utils.game_state_util import GameState, CarState
from rlbot.utils.structures.game_interface import GameInterface

from competitor import Competitor
from data_types.physics import Physics
from data_types.rotator import Rotator
from data_types.vector3 import Vector3
from event import Event, EventMeta, EventStatus
from typing import List, Dict
from rlbot.utils.structures.game_data_struct import GameTickPacket


@dataclass
class RaceSpecification(DataClassJSONMixin):
    """
    This will be saved in the file, and also sent to bots via matchcomms to tell them
    they'll be racing and where to go.
    """
    waypoints: List[Vector3]
    start: Physics
    event_type: str = "WaypointRace"


@dataclass
class EventDocument(DataClassJSONMixin):
    race_spec: RaceSpecification
    competitor_cfg_files: List[str]
    result_times: Dict[str, float]


def get_random_waypoint() -> Vector3:
    return Vector3(x=randint(-2000, 2000), y=randint(-2000, 2000), z=randint(50, 500))


class WaypointRace(Event):
    def __init__(self) -> None:
        super().__init__()
        self.name = "Waypoint Race"
        self.file: Path = None
        self.event_doc: EventDocument = None
        self.active_competitor: Competitor = None
        self.competitor_has_begun = False

    def load_event(self, doc: EventMeta, matchcomms: MatchcommsClient, game_interface: GameInterface) -> None:
        super().load_event(doc, matchcomms, game_interface)
        doc_text = Path(doc.event_doc_path).read_text()
        self.event_doc = EventDocument.from_json(doc_text)
        self.competitors = [Competitor.from_config_path(p) for p in self.event_doc.competitor_cfg_files]

    def init_event(self, competitors: List[Competitor], competition_dir: Path) -> EventMeta:
        super().init_event(competitors, competition_dir)

        waypoints = [get_random_waypoint() for _ in range(4)]
        start_point = Physics(
            location=Vector3(0, -8000, 50),
            rotation=Rotator(0, math.pi / 2, 0),
            velocity=Vector3(0, 0, 0),
            angular_velocity=Vector3(0, 0, 0))

        race_spec = RaceSpecification(waypoints=waypoints, start=start_point)
        event_doc = EventDocument(
            race_spec=race_spec,
            competitor_cfg_files=[c.bundle.config_path for c in competitors],
            result_times={}
        )

        self.file = self.competition_dir / 'WaypointRace.json'
        self.file.write_text(event_doc.to_json())

        return EventMeta(event_type='WaypointRace', event_doc_path=str(self.file))

    def tick_event(self, packet: GameTickPacket) -> EventStatus:

        if self.active_competitor is not None:
            if not self.competitor_has_begun:
                # TODO: spawn the car into the match
                competitor_in_game_index = 0
                # TODO: start the bot process
                self.matchcomms.outgoing_broadcast.put_nowait(self.event_doc.race_spec.to_json())
                cars = {competitor_in_game_index: CarState(
                    physics=self.event_doc.race_spec.start.to_gamestate(),
                    boost_amount=100
                )}
                self.game_interface.set_game_state(GameState(cars=cars))
            else:
                # TODO: watch the packet and keep track of whether the bot has reached all the waypoints
                pass
        else:
            for competitor in self.competitors:
                if competitor.bundle.config_path not in self.event_doc.result_times:
                    self.active_competitor = competitor

        return EventStatus(is_complete=False)  # TODO: return complete if all bots have finished the event.
