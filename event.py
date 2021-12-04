import math
from dataclasses import dataclass
from pathlib import Path

from rlbot.matchcomms.client import MatchcommsClient
from rlbot.utils.packetanalysis.valid_packet_detector import ValidPacketDetector
from rlbot.utils.rendering.rendering_manager import RenderingManager
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
from data_types.vector3 import Vector3
from spawn_helper import SpawnHelper


@dataclass
class EventMeta(DataClassJSONMixin):
    event_type: str
    event_doc_path: str


@dataclass
class EventStatus:
    is_complete: bool


# TODO: give events access to matchcomms, provide helpers for:
# - Telling them what to do via matchcomms
# - Rendering basic stuff to show event status
class Event:
    def __init__(self) -> None:
        self.name: str = None
        self.spawn_helper: SpawnHelper = None
        self.game_interface: GameInterface = None
        self.renderer: RenderingManager = None
        self.competitors: List[Competitor] = []
        self.competition_dir: Path = None
        self.event_meta: EventMeta = None

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

    def load_event(self, doc: EventMeta, spawn_helper: SpawnHelper, game_interface: GameInterface) -> None:
        """
        Gets ready to run based on the event data.
        """
        self.spawn_helper = spawn_helper
        self.game_interface = game_interface
        self.renderer = self.game_interface.renderer
        self.event_meta = doc

    def tick_event(self, packet: GameTickPacket) -> EventStatus:
        raise NotImplementedError

    def broadcast_to_bots(self, json_text):
        self.spawn_helper.matchcomms.outgoing_broadcast.put_nowait(json_text)

    def render_sphere(self, center: Vector3, radius: float, color):
        num_pts = 16

        equator = [center + Vector3(
            radius * math.sin(2 * math.pi * i / num_pts),
            radius * math.cos(2 * math.pi * i / num_pts),
            0
        ) for i in range(num_pts + 1)]

        vertical = [center + Vector3(
            radius * math.sin(2 * math.pi * i / num_pts),
            0,
            radius * math.cos(2 * math.pi * i / num_pts)
        ) for i in range(num_pts + 1)]

        self.renderer.draw_polyline_3d(equator, color)
        self.renderer.draw_polyline_3d(vertical, color)
