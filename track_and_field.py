import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict

from mashumaro import DataClassJSONMixin
from rlbot.agents.base_script import BaseScript
from rlbot.parsing.bot_config_bundle import get_bot_config_bundle
from rlbot_gui.gui import get_team_settings

from competitor import Competitor
from event import Event, EventMeta
from events.waypoint_race import WaypointRace


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
        self.competition_document = doc
        self.events: List[Event] = [self.construct_and_load(d) for d in doc.event_documents]
        self.event_index = 0

    def construct_event(self, event_type: str) -> Event:
        if event_type == 'WaypointRace':
            return WaypointRace()

    def construct_and_load(self, event_doc: EventMeta) -> Event:
        event = self.construct_event(event_doc.event_type)
        event.load_event(event_doc)
        return event

    def run(self):

        while True:
            packet = self.wait_game_tick_packet()

            active_event = self.events[self.event_index]
            event_status = active_event.tick_event(packet)
            if event_status.is_complete:
                self.event_index += 1
                next_event = self.events[self.event_index]
                color = self.renderer.white()
                text = f"Event: {next_event.name}"
                self.game_interface.renderer.begin_rendering("tracknfield")
                self.game_interface.renderer.draw_string_2d(20, 20, 2, 2, text, color)
                self.game_interface.renderer.end_rendering()
                # TODO: go into some kindof pause mode until the user
                # manually advances to the next event with some kind of command.


if __name__ == "__main__":
    competitors: List[Competitor] = load_competitors()

    current_competition_file = Path("./data/current_competition.json")
    if current_competition_file.exists():

        # Load the file
        doc = CompetitionDocument.from_json(current_competition_file.read_text())

        # TODO: Validate that either competitors are empty or they match
        # the expectation of the competition file
    else:

        events = [WaypointRace()]
        time_str = time.strftime("%Y-%m-%dT%H-%M-%S")
        competition_dir = Path(f"./data/{time_str}")
        competition_dir.mkdir(parents=True, exist_ok=True)
        event_docs = [e.init_event(competitors, competition_dir) for e in events]

        doc = CompetitionDocument([c.bundle.config_path for c in competitors], event_docs)
        # Save a current competition file here
        current_competition_file.write_text(doc.to_json())

    # Run the competition
    track_and_field = TrackAndField(doc)
    track_and_field.run()
