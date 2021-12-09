import queue
import time
from dataclasses import dataclass
from random import randint
from typing import List

from rlbot.matchcomms.client import MatchcommsClient
from rlbot.matchconfig.match_config import EmptyPlayerSlot, PlayerConfig, MatchConfig, MutatorConfig
from rlbot.parsing.bot_config_bundle import BotConfigBundle
from rlbot.setup_manager import SetupManager
from rlbot.utils.structures.game_data_struct import GameTickPacket
from rlbot.utils.structures.game_interface import GameInterface


@dataclass
class ActiveBot:
    name: str
    team: int
    spawn_id: int
    bundle: BotConfigBundle


@dataclass
class CompletedSpawn:
    bot: ActiveBot
    packet_index: int


def player_config_from_active_bot(active_bot: ActiveBot):
    if active_bot is None:
        return EmptyPlayerSlot()
    return create_player_config(active_bot.name, active_bot.team, active_bot.spawn_id, active_bot.bundle.config_path)


def create_player_config(name: str, team: int, spawn_id: int, config_path: str):
    player_config = PlayerConfig()
    player_config.bot = True
    player_config.rlbot_controlled = True
    player_config.bot_skill = 1
    player_config.human_index = 0
    player_config.name = name
    player_config.team = team
    player_config.spawn_id = spawn_id
    player_config.config_path = config_path
    return player_config


def build_match_config(active_bots: List[ActiveBot]):
    match_config = MatchConfig()
    match_config.player_configs = [player_config_from_active_bot(ab) for ab in active_bots]
    match_config.game_mode = 'Soccer'
    match_config.game_map = 'DFHStadium'
    match_config.existing_match_behavior = 'Continue And Spawn'
    match_config.mutators = MutatorConfig()
    match_config.enable_state_setting = True
    return match_config


def index_from_spawn_id(packet: GameTickPacket, spawn_id: int):
    for n in range(0, packet.num_cars):
        packet_spawn_id = packet.game_cars[n].spawn_id
        if spawn_id == packet_spawn_id:
            return n
    return None


class SpawnHelper:

    def __init__(self, game_interface: GameInterface):
        self.active_bots: List[ActiveBot] = []
        self.setup_manager = SetupManager()
        self.setup_manager.game_interface = game_interface
        self.setup_manager.num_participants = 0
        self.setup_manager.launch_bot_processes(MatchConfig())
        self.matchcomms = MatchcommsClient(
            self.setup_manager.matchcomms_server.root_url)  # This must come after launch_bot_processes

    def _make_active_bot(self, bundle: BotConfigBundle, team: int):
        name = bundle.name
        names = set([ab.name for ab in self.active_bots if ab is not None])
        unique_name = name[:31]
        count = 2
        while unique_name in names:
            unique_name = f'{name[:27]} ({count})'  # Truncate at 27 because we can have up to '(10)' appended
            count += 1

        return ActiveBot(unique_name, team, randint(1, 2 ** 31 - 1), bundle)

    def spawn_bots(self, bundles: List[BotConfigBundle]) -> List[CompletedSpawn]:
        new_active_bots = [self._make_active_bot(bundle, 0) for bundle in bundles]
        self.active_bots += new_active_bots
        match_config = build_match_config(self.active_bots)
        self.launch_match(match_config)
        packet = GameTickPacket()
        self.setup_manager.game_interface.update_live_data_packet(packet)
        return [CompletedSpawn(
            bot=active_bot,
            packet_index=index_from_spawn_id(packet, active_bot.spawn_id)
        ) for active_bot in new_active_bots]

    def listen_for_events_supported_by_bot(self, timeout: int = 7) -> List[str]:
        """
        Bots which support Track and Field should please send a message to matchcomms
        when they start up, shaped like this:
        { "readyForTrackAndField": True, "supportedEvents": ["WaypointRace", "etc"] }

        If they don't send it, we'll assume they don't support any. The event itself
        will choose whether such bots can still try to participate.
        """
        supported_events = []
        try:
            for _ in range(10):
                message = self.matchcomms.incoming_broadcast.get(block=True, timeout=timeout)
                if message.get("readyForTrackAndField", False):
                    # The bot claims to be ready.
                    supported_events = message.get("supportedEvents", [])
                    break
        except queue.Empty:
            print(f"Bot never sent a 'ready' message, proceeding anyway.")
        return supported_events

    def clear_bots(self):
        self.active_bots = []
        match_config = build_match_config(self.active_bots)
        self.launch_match(match_config)

    def launch_match(self, match_config: MatchConfig):
        self.setup_manager.load_match_config(match_config)
        self.setup_manager.start_match()
        self.setup_manager.launch_bot_processes(match_config=match_config)
        time.sleep(1)  # Give a chance for the agent metadata to arrive
        num_received = self.setup_manager.try_recieve_agent_metadata()
        print(f"Got {num_received} agent metadata objects.")
