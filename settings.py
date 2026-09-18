class Settings:
    """Хранит все настройки игры."""

    def __init__(self):
        # Статические настройки
        self.screen_width = None
        self.screen_height = None
        self.bg_color = (10, 10, 70)

        self.ship_limit = 3
        self.bullet_width = 3
        self.bullet_height = 20
        self.bullet_color = (220, 200, 200)

        self.fleet_drop_speed = 10
        self.distance_multiplier = 1.0
        self.distance_increase_rate = 0.1

        self.initialize_dynamic_settings()

    def initialize_dynamic_settings(self):
        """Инициализирует настройки, которые меняются во время игры."""
        self.ship_speed = 2.5
        self.alien_speed = 0.5
        self.bullet_speed = 2.5
        self.bullets_allowed = 4
        self.fleet_direction = 1
        self.alien_points = 10
        self.level = 1

    def increase_speed(self):
        """Увеличивает скорость и сложность игры."""
        if self.distance_multiplier < 5:
            self.distance_multiplier += self.distance_increase_rate

        if self.alien_points < 1488:
            self.alien_points = int(self.alien_points * 1.5)
        else:
            self.alien_points = int(self.alien_points * 1.005)

        if self.level < 30:
            self.alien_speed *= 1.05
        elif self.level < 60:
            self.bullets_allowed += 1
            self.bullet_speed += 0.2
            self.alien_speed += 1.0
            self.ship_speed += 0.5