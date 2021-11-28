from dataclasses import dataclass
from pathlib import Path

from rlbot.matchcomms.client import MatchcommsClient
from rlbot.utils.structures.game_data_struct import GameTickPacket
from rlbot.utils.structures.game_interface import GameInterface

from competitor import Competitor
from mashumaro import DataClassJSONMixin
from typing import List


# What should an overall pentathlon script look like?
# Python file that constructs a list of event objects?
# Directory full of event config files?
# I think it should be python file driven
# How do we choose bots for the event? Can the user just drag bots onto teams
# in RLBotGUI, start a fake match with the script active, and the script hooks
# and takes over?

@dataclass
class EventMeta(DataClassJSONMixin):
    event_type: str
    event_doc_path: str


@dataclass
class EventStatus:
    is_complete: bool


# TODO: give events access to matchcomms, provide helpers for:
# - Spawning bots
# - Telling them what to do via matchcomms
# - Rendering basic stuff to show event status
class Event:
    def __init__(self) -> None:
        self.name: str = None
        self.matchcomms: MatchcommsClient = None
        self.game_interface: GameInterface = None
        self.competitors: List[Competitor] = []
        self.competition_dir: Path = None

    def init_event(self, competitors: List[Competitor], competition_dir: Path) -> EventMeta:
        self.competitors = competitors
        self.competition_dir = competition_dir
        """
        This should create a document that persists which bots are in the event,
        and the progress and standings so far. If the program crashes, the
        doc should be adequate for picking up where we left off.

        Anything using random number generation should be done here.
        """
        return None

    def load_event(self, doc: EventMeta, matchcomms: MatchcommsClient, game_interface: GameInterface) -> None:
        """
        Gets ready to run based on the event data.
        """
        self.matchcomms = matchcomms
        self.game_interface = game_interface

    def tick_event(self, packet: GameTickPacket) -> EventStatus:
        raise NotImplementedError
