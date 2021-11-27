from pathlib import Path

from competitor import Competitor
from event import Event, EventMeta, EventStatus
from typing import List
from rlbot.utils.structures.game_data_struct import GameTickPacket


class WaypointRace(Event):
    def __init__(self) -> None:
        super().__init__()
        self.name = "Waypoint Race"
        self.file: Path = None
        self.competitors = []

    def load_event(self, doc: EventMeta) -> None:
        return super().load_event(doc)

    def init_event(self, competitors: List[Competitor], competition_dir: Path) -> EventMeta:
        self.competitors = competitors
        self.file = competition_dir / 'WaypointRace.json'
        self.file.touch()
        return EventMeta(event_type='WaypointRace', event_doc_path=str(self.file))

    def tick_event(self, packet: GameTickPacket) -> EventStatus:
        # TODO: for each competitor, one at a time,
        # Spawn them and tell them what waypoints to race through.
        # Measure their time and record it. Move on to the next bot.

        return EventStatus(is_complete=False)
