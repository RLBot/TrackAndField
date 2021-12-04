import math
from dataclasses import dataclass
from pathlib import Path
from random import randint
from typing import List, Dict

from mashumaro import DataClassJSONMixin
from rlbot.utils.game_state_util import GameState, CarState
from rlbot.utils.structures.game_data_struct import GameTickPacket, PlayerInfo
from rlbot.utils.structures.game_interface import GameInterface

from competitor import Competitor
from data_types.physics import Physics
from data_types.rotator import Rotator
from data_types.vector3 import Vector3
from event import Event, EventMeta, EventStatus
from spawn_helper import SpawnHelper


@dataclass
class RaceSpecification(DataClassJSONMixin):
    """
    This will be saved in the file, and also sent to bots via matchcomms to tell them
    they'll be racing and where to go.
    """
    waypoints: List[Vector3]
    waypoint_tolerance: float
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
        self.competitor_start_time: float = 0
        self.competitor_packet_index: int = None
        self.completed_waypoints_indices: List[int] = []

    def load_event(self, doc: EventMeta, spawn_helper: SpawnHelper, game_interface: GameInterface) -> None:
        super().load_event(doc, spawn_helper, game_interface)
        doc_text = Path(doc.event_doc_path).read_text()
        self.event_doc = EventDocument.from_json(doc_text)
        self.competitors = [Competitor.from_config_path(p) for p in self.event_doc.competitor_cfg_files]

    def save_doc(self):
        json = self.event_doc.to_json()
        path = Path(self.event_meta.event_doc_path)
        path.write_text(json)


    def init_event(self, competitors: List[Competitor], competition_dir: Path) -> EventMeta:
        super().init_event(competitors, competition_dir)

        waypoints = [get_random_waypoint() for _ in range(4)]
        start_point = Physics(
            location=Vector3(0, -8000, 50),
            rotation=Rotator(0, math.pi / 2, 0),
            velocity=Vector3(0, 0, 0),
            angular_velocity=Vector3(0, 0, 0))

        race_spec = RaceSpecification(waypoints=waypoints, start=start_point, waypoint_tolerance=100)
        event_doc = EventDocument(
            race_spec=race_spec,
            competitor_cfg_files=[c.bundle.config_path for c in competitors],
            result_times={}
        )

        self.file = self.competition_dir / 'WaypointRace.json'
        self.file.write_text(event_doc.to_json())

        return EventMeta(event_type='WaypointRace', event_doc_path=str(self.file))

    def check_for_human_usurper(self, packet: GameTickPacket):
        for i in range(packet.num_cars):
            car = packet.game_cars[i]
            if len(car.name) and not car.is_bot:
                self.competitor_packet_index = i

    def tick_event(self, packet: GameTickPacket) -> EventStatus:
        race_spec = self.event_doc.race_spec

        self.check_for_human_usurper(packet)

        if self.active_competitor is not None:
            if not self.competitor_has_begun and packet.game_info.is_round_active:
                self.competitor_has_begun = True
                self.competitor_start_time = packet.game_info.seconds_elapsed
                self.spawn_helper.clear_bots()
                print(f"About to spawn {self.active_competitor.bundle.name} for WaypointRace.")
                completed_spawn = self.spawn_helper.spawn_bot(self.active_competitor.bundle)
                self.competitor_packet_index = completed_spawn.packet_index
                self.broadcast_to_bots(race_spec.to_json())
                cars = {self.competitor_packet_index: CarState(
                    physics=race_spec.start.to_gamestate(),
                    boost_amount=100
                )}
                self.game_interface.set_game_state(GameState(cars=cars))
                self.completed_waypoints_indices = []
            else:
                self.renderer.begin_rendering('waypoints')
                competitor_pos = Vector3.from_vec(packet.game_cars[self.competitor_packet_index].physics.location)
                for idx, w in enumerate(race_spec.waypoints):
                    if idx not in self.completed_waypoints_indices:
                        if w.dist(competitor_pos) < race_spec.waypoint_tolerance:
                            self.completed_waypoints_indices.append(idx)
                    color = self.renderer.lime() if idx in self.completed_waypoints_indices else self.renderer.yellow()
                    self.render_sphere(w, race_spec.waypoint_tolerance / 2, color)
                self.render_sphere(competitor_pos, race_spec.waypoint_tolerance / 2, self.renderer.cyan())
                self.renderer.end_rendering()
                waypoints_complete = len(self.completed_waypoints_indices) >= len(race_spec.waypoints)
                if waypoints_complete:
                    race_time = packet.game_info.seconds_elapsed - self.competitor_start_time
                    self.event_doc.result_times[self.active_competitor.bundle.config_path] = race_time
                    self.save_doc()
                    self.active_competitor = None
        else:
            for competitor in self.competitors:
                if competitor.bundle.config_path not in self.event_doc.result_times:
                    self.active_competitor = competitor

        competitors_lacking_times = [c for c in self.competitors if c.bundle.config_path not in self.event_doc.result_times]
        return EventStatus(is_complete=len(competitors_lacking_times) == 0)
