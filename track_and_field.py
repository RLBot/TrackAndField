import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict

from mashumaro import DataClassJSONMixin
from rlbot.agents.base_script import BaseScript
from rlbot.matchcomms.client import MatchcommsClient
from rlbot.matchconfig.match_config import MatchConfig
from rlbot.parsing.bot_config_bundle import get_bot_config_bundle
from rlbot.setup_manager import SetupManager
from rlbot_gui.gui import get_team_settings

from competitor import Competitor
from event import Event, EventMeta
from events.waypoint_race import WaypointRace
from spawn_helper import SpawnHelper


def load_competitors() -> List[Competitor]:
    # Loads the bots used in the most recently launched match from RLBotGUI.
    team_settings = get_team_settings()
    blue_settings: List[Dict] = team_settings['blue_team']
    orange_settings: List[Dict] = team_settings['orange_team']
    all_settings = blue_settings + orange_settings
    all_bundles = [get_bot_config_bundle(d["path"]) for d in all_settings if "path" in d]
    return [Competitor(b) for b in all_bundles]


@dataclass
class CompetitionDocument(DataClassJSONMixin):
    competitor_cfg_files: List[str]
    event_documents: List[EventMeta]


# Extending the BaseScript class is purely optional. It's just convenient / abstracts you away from
# some strange classes like GameInterface
class TrackAndField(BaseScript):
    def __init__(self, doc: CompetitionDocument):
        super().__init__("Track and Field")
        self.screen_log: List[str] = []
        self.log_to_screen("Welcome to Track and Field!")
        self.spawn_helper = SpawnHelper(self.game_interface)
        self.competition_document = doc
        self.wait_for_game_stabilization()
        self.events: List[Event] = [self.construct_and_load(d) for d in doc.event_documents]
        self.event_index = 0

    def log_to_screen(self, text: str):
        self.screen_log.append(text)
        self.logger.info(text)
        while len(self.screen_log) > 4:
            self.screen_log = self.screen_log[1:]
        self.renderer.begin_rendering("track_n_field_log")
        self.renderer.draw_string_2d(20, 20, 2, 2, "\n".join(self.screen_log), self.renderer.yellow())
        self.renderer.end_rendering()

    def wait_for_game_stabilization(self):
        """
        Bots will be waiting to see their own spawn_id in the packet. Once they see it once, they'll be ready
        to retire when it disappears / when the car de-spawns. Wait for long enough to make sure they see it.
        """
        for _ in range(20):
            packet = self.get_game_tick_packet()
            if packet.game_info.is_round_active:
                time.sleep(1.5)
                self.log_to_screen("Clearing bots to prepare for track and field.")
                self.spawn_helper.clear_bots()
                self.log_to_screen("Bots cleared, waiting for processes to die...")
                time.sleep(3)
                break
            time.sleep(.5)

    def construct_event(self, event_type: str) -> Event:
        if event_type == 'WaypointRace':
            return WaypointRace()

    def construct_and_load(self, event_doc: EventMeta) -> Event:
        event = self.construct_event(event_doc.event_type)
        event.load_event(event_doc, self.spawn_helper, self.game_interface)
        return event

    def run(self):
        self.log_to_screen(f"Running {len(self.events)} track and field events...")
        active_event: Event = None
        while True:
            packet = self.wait_game_tick_packet()

            if active_event is None:
                if self.event_index >= len(self.events):
                    self.log_to_screen("Finished all Track and Field events!")
                    exit(0)
                active_event = self.events[self.event_index]
                self.log_to_screen(f"Event: {active_event.name}")
                # TODO: go into some kindof pause mode until the user
                # manually advances to the next event with some kind of command.

            event_status = active_event.tick_event(packet)
            if event_status.is_complete:
                self.event_index += 1
                active_event = None


if __name__ == "__main__":
    competitors: List[Competitor] = load_competitors()

    data_dir = Path(__file__).parent / "data"
    current_competition_file = data_dir / "current_competition.json"
    if current_competition_file.exists():

        # Load the file
        print(f"Current competition file already exists at {current_competition_file.absolute()}")
        doc = CompetitionDocument.from_json(current_competition_file.read_text())

        if len(competitors) > 0:
            comp_config_files = [k.bundle.config_path for k in competitors]
            if doc.competitor_cfg_files != comp_config_files:
                raise ValueError(f"Competitors from RLBotGUI ({comp_config_files}) do not match competitors in doc"
                                 f" ({doc.competitor_cfg_files}). If you want to start fresh, remove or rename"
                                 f" {current_competition_file.absolute()}")
    else:

        events = [WaypointRace()]
        time_str = time.strftime("%Y-%m-%dT%H-%M-%S")
        competition_dir = data_dir / time_str
        competition_dir.mkdir(parents=True, exist_ok=True)
        event_docs = [e.init_event(competitors, competition_dir) for e in events]

        doc = CompetitionDocument([c.bundle.config_path for c in competitors], event_docs)
        # Save a current competition file here
        current_competition_file.write_text(doc.to_json())

    # Run the competition
    track_and_field = TrackAndField(doc)
    track_and_field.run()
