class GameStats:
    """Хранит статистику игры."""

    def __init__(self, ai_game):
        self.settings = ai_game.settings
        self.reset_stats()
        self.level = 1

    def reset_stats(self):
        """Сбрасывает статистику к начальным значениям."""
        self.ships_left = self.settings.ship_limit
        self.score = 0