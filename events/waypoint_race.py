from pathlib import Path

from rlbot.matchcomms.client import MatchcommsClient
from rlbot.utils.structures.game_interface import GameInterface

from competitor import Competitor
from event import Event, EventMeta, EventStatus
from typing import List
from rlbot.utils.structures.game_data_struct import GameTickPacket


class WaypointRace(Event):
    def __init__(self) -> None:
        super().__init__()
        self.name = "Waypoint Race"
        self.file: Path = None

    def load_event(self, doc: EventMeta, matchcomms: MatchcommsClient, game_interface: GameInterface) -> None:
        super().load_event(doc, matchcomms, game_interface)
        # TODO: parse locations out of the doc.
        # Parse out and initialize the competitors
        pass

    def init_event(self, competitors: List[Competitor], competition_dir: Path) -> EventMeta:
        super().init_event(competitors, competition_dir)
        self.file = self.competition_dir / 'WaypointRace.json'
        self.file.touch()
        # TODO: Pick random waypoints for the bots to traverse
        return EventMeta(event_type='WaypointRace', event_doc_path=str(self.file))

    def tick_event(self, packet: GameTickPacket) -> EventStatus:
        # TODO: for each competitor, one at a time,
        # Spawn them and tell them what waypoints to race through.
        # Tell them via self.matchcomms.outgoing_broadcast.put_nowait()
        # Measure their time and record it. Move on to the next bot.
        # TODO: figure out a common schema for track and field communications. Similar to TMCP?

        return EventStatus(is_complete=False)
