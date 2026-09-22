from utils import load_config, save_config


class Settings:
    """Хранит все настройки игры."""

    def __init__(self):
        # Загружаем сохранённый цвет фона
        config = load_config()
        r = config.get('bg_r', 10)
        g = config.get('bg_g', 10)
        b = config.get('bg_b', 70)

        # Цвет фона (значения ограничены 0–255)
        self.bg_color = (
            max(0, min(255, r)),
            max(0, min(255, g)),
            max(0, min(255, b)),
        )

        # Статические настройки
        self.screen_width = None
        self.screen_height = None

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

    def set_bg_color(self, color: tuple) -> None:
        """Устанавливает новый цвет фона (0–255 по каждому каналу)."""
        self.bg_color = (
            max(0, min(255, color[0])),
            max(0, min(255, color[1])),
            max(0, min(255, color[2])),
        )

    def save(self) -> None:
        """Сохраняет настройки в config.json."""
        save_config({
            'bg_r': self.bg_color[0],
            'bg_g': self.bg_color[1],
            'bg_b': self.bg_color[2],
        })