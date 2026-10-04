from utils import load_config, save_config


class Settings:
    """Хранит все настройки игры."""

    # ─── Константы баланса ────────────────────────────────────────
    DISTANCE_MAX = 5.0              # предел множителя расстояния во флоте
    POINTS_SOFT_CAP = 1488          # до этого порога очки растут быстро
    POINTS_GROWTH_FAST = 1.5        # множитель очков ниже порога
    POINTS_GROWTH_SLOW = 1.005      # множитель очков выше порога
    BULLETS_MAX = 12                # предел одновременных пуль

    # ─── Фазы сложности (по уровню) ───────────────────────────────
    PHASE_1_END = 30                # до 30 — плавный рост alien_speed
    PHASE_2_END = 60                # до 60 — рост ресурсов игрока

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
        """Инициализирует настройки, которые меняются во время игры.

        Все скорости — в ПИКСЕЛЯХ В СЕКУНДУ (px/sec).
        Значения эквивалентны прежним пикселям за кадр при 240 FPS."""

        self.ship_speed = 600.0
        self.alien_speed = 120.0
        self.bullet_speed = 600.0
        self.bullets_allowed = 4
        self.fleet_direction = 1
        self.alien_points = 10
        self.level = 1

    def increase_speed(self):
        """Увеличивает скорость и сложность игры.

        Логика разбита на фазы:
        - Уровни 1 - 29: плавное ускорение пришельцев.
        - Уровни 30 - 59: игроку больше пуль и скорости,
          пришельцы растут мягче.
        - Уровни 60+: только очки растут (мягко).
        """

        # Расстояние между пришельцами — растёт до предела
        if self.distance_multiplier < self.DISTANCE_MAX:
            self.distance_multiplier += self.distance_increase_rate

        # Очки: быстрый рост до soft-cap, потом мягкий
        if self.alien_points < self.POINTS_SOFT_CAP:
            self.alien_points = int(self.alien_points * self.POINTS_GROWTH_FAST)
        else:
            self.alien_points = int(self.alien_points * self.POINTS_GROWTH_SLOW)

        if self.level < self.PHASE_1_END:
            # Фаза 1: плавный рост скорости пришельцев
            self.alien_speed *= 1.05
        elif self.level < self.PHASE_2_END:
            # Фаза 2: игроку больше ресурсов, пришельцы растут мягче
            self.bullets_allowed = min(
                self.bullets_allowed + 1, self.BULLETS_MAX
            )
            self.bullet_speed += 50
            self.alien_speed *= 1.03
            self.ship_speed += 120

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