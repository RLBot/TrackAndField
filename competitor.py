from rlbot.parsing.bot_config_bundle import BotConfigBundle, get_bot_config_bundle


class Competitor:
    """
    This is a bot that competes in a track and field event.
    """

    def __init__(self, bundle: BotConfigBundle) -> None:
        self.bundle = bundle

    @staticmethod
    def from_config_path(path: str):
        return Competitor(bundle=get_bot_config_bundle(path))

    def name(self):
        return self.bundle.name

    def __str__(self):
        return self.name()
