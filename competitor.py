from rlbot.parsing.bot_config_bundle import BotConfigBundle


class Competitor:
    """
    This is a bot that competes in a track and field event.
    """

    def __init__(self, bundle: BotConfigBundle) -> None:
        self.bundle = bundle
