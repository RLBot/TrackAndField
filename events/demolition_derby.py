"""
Bot makers:

To support this event type, you must listen on matchcomms for an event shaped like this (see DerbySpecification):
{
  "event_type": "DemolitionDerby",
  "perma_death": true,
  "max_duration": 60.0,
  "starts": [
    {
      "location": {"x": 0.0, "y": -8000.0, "z": 50.0},
      "rotation": {"pitch": 0.0, "yaw": 1.5707963267948966, "roll": 0.0},
      "velocity": {"x": 0.0, "y": 0.0, "z": 0.0},
      "angular_velocity": {"x": 0.0, "y": 0.0, "z": 0.0}
    },
    ...
  ]
}

This event requires the Friendly Fire mutator.
All bots spawn at once at the specified `starts`.
The goal is to demo as many cars as you can, and avoid getting demoed.
If `perma_death` is true, when your bot is demolished, it won't respawn (it actually does but it gets teleported outside the map).
The event ends when there is only one bot alive or `max_duration` has passed.
"""

import math
from dataclasses import dataclass
from pathlib import Path
import random
from typing import List, Dict

from mashumaro import DataClassJSONMixin
from rlbot.utils.game_state_util import GameState, CarState, Physics as DesiredPhysics
from rlbot.utils.structures.game_data_struct import GameTickPacket
from rlbot.utils.structures.game_interface import GameInterface

from competitor import Competitor
from data_types.physics import Physics
from data_types.rotator import Rotator
from data_types.vector3 import Vector3
from event import Event, EventMeta, EventStatus
from event_utils.spawn_helper import ActiveBot, CompletedSpawn, SpawnHelper
from event_utils.time_lord import TimeLord


@dataclass
class DerbySpecification(DataClassJSONMixin):
    """
    This will be saved in the file, and also sent to bots via matchcomms to tell them
    they'll be competing and where each bot starts.
    """
    perma_death: bool
    max_duration: float
    starts: List[Physics]
    event_type: str = "DemolitionDerby"


@dataclass
class EventDocument(DataClassJSONMixin):
    derby_spec: DerbySpecification
    competitor_cfg_files: List[str]
    result_demolitions: Dict[str, int]


@dataclass
class ActiveBotInfo:
    competitor: Competitor
    active_bot: ActiveBot
    packet_index: int
    time_lord: TimeLord
    is_dead: bool = False


class DemolitionDerby(Event):
    def __init__(self, max_duration=60, perma_death=True) -> None:
        super().__init__()
        self.max_duration = max_duration
        self.perma_death = perma_death

        self.name = "Demolition Derby"
        self.file: Path = None
        self.event_doc: EventDocument = None
        
        self.derby_started = False
        self.infos: List[ActiveBotInfo] = None

    def load_event(self, doc: EventMeta, spawn_helper: SpawnHelper, game_interface: GameInterface) -> None:
        """
        Loads the derby tracking document from disk and initializes game interface type stuff.
        """
        super().load_event(doc, spawn_helper, game_interface)
        doc_text = Path(doc.event_doc_path).read_text()
        self.event_doc = EventDocument.from_json(doc_text)
        self.competitors = [Competitor.from_config_path(p) for p in self.event_doc.competitor_cfg_files]

    def save_doc(self):
        """
        Writes the derby tracking document to disk.
        """
        json = self.event_doc.to_json()
        path = Path(self.event_meta.event_doc_path)
        path.write_text(json)

    def init_event(self, competitors: List[Competitor], competition_dir: Path) -> EventMeta:
        """
        This should create a document that persists which bots are in the event,
        and the progress and standings so far. If the program crashes, the
        doc should be adequate for picking up where we left off.

        Anything using random number generation should be done here.
        """
        super().init_event(competitors, competition_dir)

        # arrange all bots in a circle
        spawn_angles = [2 * math.pi * i / len(competitors) for i in range(len(competitors))]
        radius = 3000
        spawn_physics = [Physics(
            location=Vector3(math.cos(angle) * radius, math.sin(angle) * radius, 50),
            rotation=Rotator(0, angle + math.pi, 0),
            velocity=Vector3(0, 0, 0),
            angular_velocity=Vector3(0, 0, 0)
        ) for angle in spawn_angles]
        random.shuffle(spawn_physics)  # randomize spawn positions

        derby_spec = DerbySpecification(perma_death=self.perma_death, max_duration=self.max_duration, starts=spawn_physics)
        event_doc = EventDocument(
            derby_spec=derby_spec,
            competitor_cfg_files=[c.bundle.config_path for c in competitors],
            result_demolitions={}
        )

        self.file = self.competition_dir / 'DemolitionDerby.json'
        self.file.write_text(event_doc.to_json())

        return EventMeta(event_type='DemolitionDerby', event_doc_path=str(self.file))

    def start_derby(self):
        derby_spec = self.event_doc.derby_spec
        self.spawn_helper.clear_bots()

        self.on_screen_log.log(f"About to spawn bots for DemolitionDerby.")
        completed_spawns = self.spawn_helper.spawn_bots([competitor.bundle for competitor in self.competitors])

        self.on_screen_log.log("Waiting for bots to get ready")
        # We expect a number of ready messages equal to the number of competitors. Doesn't matter in which order they arrive.
        # Currently we have no way of knowing which bot sent which message, so we don't know who supports this event.
        for i in range(len(self.competitors)):
            self.hide_ball()
            self.spawn_helper.listen_for_events_supported_by_bot(timeout=7)
            self.on_screen_log.log(f"{i+1}/{len(self.competitors)} bots ready")

        self.broadcast_to_bots(derby_spec.to_dict())

        self.game_interface.set_game_state(GameState(cars={spawn.packet_index: CarState(
            physics=start.to_gamestate(),
            boost_amount=0
        ) for spawn, start in zip(completed_spawns, derby_spec.starts)}))

        self.hide_ball()

        self.infos = [ActiveBotInfo(
            competitor=competitor,
            active_bot=spawn.bot,
            packet_index=spawn.packet_index,
            time_lord=TimeLord(
                spawn.packet_index,
                start.location,
                start.rotation,
                self.game_interface,
                countdown_seconds=10,
            ),
        ) for spawn, competitor, start in zip(completed_spawns, self.competitors, derby_spec.starts)]

        self.on_screen_log.log("Starting derby!")
        self.derby_started = True

    def tick_event(self, packet: GameTickPacket) -> EventStatus:
        """
        This is the main logic for running the derby.
        It spawns all the cars and tracks their demolitions.
        """
        if not self.derby_started:
            self.start_derby()
            return EventStatus(is_complete=False)  # exit out of this tick so we can get a fresh packet

        car_states = {}
        for info in self.infos:
            info.time_lord.tick(packet)
            if not info.is_dead and self.perma_death and packet.game_cars[info.packet_index].is_demolished:
                info.is_dead = True
                self.on_screen_log.log(f"{info.competitor.name()} is permanently dead")

            # hide dead bots
            if info.is_dead:
                car_states[info.packet_index] = CarState(DesiredPhysics(
                    location=Vector3(info.packet_index * 100, 0, 3000).to_gamestate()))

        # if only one bot is alive or we ran out of time, end the event
        bots_alive = sum(not info.is_dead for info in self.infos)
        if bots_alive <= 1 or self.infos[0].time_lord.get_event_elapsed_time(packet) > self.max_duration:
            for info in self.infos:
                demos_scored = packet.game_cars[info.packet_index].score_info.demolitions
                self.event_doc.result_demolitions[info.competitor.bundle.config_path] = demos_scored
                info.time_lord.cleanup()
            self.on_screen_log.clear()
            self.save_doc()
            return EventStatus(is_complete=True)

        self.game_interface.set_game_state(GameState(cars=car_states))
        return EventStatus(is_complete=False)

