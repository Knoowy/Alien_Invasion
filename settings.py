"""Настройки игры Alien Invasion.

Единственная точка правды о сложности — self.level.
Все динамические параметры (скорости, очки, HP босса и т.д.)
пересчитываются из уровня через set_level().

Примеры использования:

    settings.set_level(1)      # новая игра
    settings.set_level(100)    # тест на 100-м уровне
    settings.increase_level()  # игрок перешёл на следующий уровень
    settings.reset()           # вернуть всё на стартовый уровень
"""

from utils import load_config, save_config


# LAST  COMMIT AI NOT CHECK
class Settings:
    """Все параметры игры; динамические — вычисляются из уровня."""

    # ═══════════════════════════════════════════════════════════════
    # 1. КОНСТАНТЫ БАЛАНСА
    # ═══════════════════════════════════════════════════════════════

    # ─── Уровень, с которого начинается новая игра ─────────────
    STARTING_LEVEL = 1

    # ─── Фазы сложности ────────────────────────────────────────
    # Скорость пришельцев: быстро растёт до ур. 29, умеренно до 59,
    # после 59 — замирает (дальше растут только очки и HP босса).
    PHASE_1_END = 30
    PHASE_2_END = 60

    # ─── Базовые значения (уровень 1) ──────────────────────────
    BASE_ALIEN_SPEED = 120.0
    BASE_BULLET_SPEED = 600.0
    BASE_SHIP_SPEED = 600.0
    BASE_BULLETS_ALLOWED = 4
    BASE_ALIEN_POINTS = 10
    BASE_DISTANCE_MULTIPLIER = 1.0

    # ─── Скорости: коэффициенты роста ──────────────────────────
    ALIEN_SPEED_GROWTH_P1 = 1.05  # ×1.05 за уровень в фазе 1
    ALIEN_SPEED_GROWTH_P2 = 1.03  # ×1.03 за уровень в фазе 2
    BULLET_SPEED_GROWTH_P2 = 50.0  # +50 за уровень в фазе 2
    SHIP_SPEED_GROWTH_P2 = 100.0  # +100 за уровень в фазе 2

    # ─── Очки ──────────────────────────────────────────────────
    POINTS_SOFT_CAP = 1488  # порог перехода на медленный рост
    POINTS_GROWTH_FAST = 1.5  # ×1.5 до капа
    POINTS_GROWTH_SLOW = 1.005  # ×1.005 после капа

    # ─── Флот ──────────────────────────────────────────────────
    DISTANCE_MAX = 5.0
    DISTANCE_INCREASE_RATE = 0.05  # +0.1 за уровень
    BULLETS_MAX = 12

    # ─── Босс: базовые характеристики ──────────────────────────
    BOSS_LEVEL_INTERVAL = 5
    BOSS_HP_BASE = 10
    BOSS_HP_PER_LEVEL = 1
    BOSS_HIT_POINTS = 50
    BOSS_KILL_POINTS = 1000
    BOSS_KILL_POINTS_PER_LEVEL = 100
    BOSS_SPAWN_DURATION = 2.5

    # ─── Босс: скорость движения ───────────────────────────────
    BOSS_MOVE_SPEED_BASE = 0.2  # на 1-м уровне
    BOSS_MOVE_SPEED_MAX = 0.5  # на 60-м уровне (дальше не растёт)

    # ─── Босс: базовые интервалы атак (на ур. 1) ───────────────
    # К 60-му уровню все интервалы сокращаются ровно в 2 раза.
    BOSS_SHOOT_P1 = 1.6
    BOSS_SHOOT_P2 = 1.2
    BOSS_SHOOT_P3 = 0.9
    BOSS_BEAM_COOLDOWN_P1 = 6.0
    BOSS_BEAM_COOLDOWN_P2 = 4.5
    BOSS_BEAM_COOLDOWN_P3 = 3.5
    BOSS_BOMBING_COOLDOWN_P2 = 9.0
    BOSS_BOMBING_COOLDOWN_P3 = 6.5

    # ─── Босс: параметры атак, НЕ зависящие от уровня ──────────
    BOSS_BULLET_SPEED = 600.0
    BOSS_BEAM_TELEGRAPH = 0.8
    BOSS_BEAM_DURATION = 0.2
    BOSS_BEAM_WIDTH = 24
    BOSS_BOMBING_TELEGRAPH = 1.5
    BOSS_BOMBING_RADIUS = 60
    BOSS_BOMBING_COUNT = 5

    # ═══════════════════════════════════════════════════════════════
    # 2. ИНИЦИАЛИЗАЦИЯ
    # ═══════════════════════════════════════════════════════════════

    def __init__(self):
        # ─── Цвет фона (из config.json) ────────────────────────
        config = load_config()
        self.bg_color = (
            max(0, min(255, config.get("bg_r", 10))),
            max(0, min(255, config.get("bg_g", 10))),
            max(0, min(255, config.get("bg_b", 70))),
        )

        # ─── Статические настройки (не зависят от уровня) ──────
        self.screen_width = None
        self.screen_height = None
        self.ship_limit = 3
        self.bullet_width = 3
        self.bullet_height = 20
        self.bullet_color = (220, 200, 200)
        self.fleet_drop_speed = 10

        # ─── Динамические (заполнятся в set_level) ─────────────
        self.set_level(self.STARTING_LEVEL)

    # ═══════════════════════════════════════════════════════════════
    # 3. ПУБЛИЧНЫЙ API
    # ═══════════════════════════════════════════════════════════════

    def set_level(self, level: int) -> None:
        self.level = max(1, int(level))
        self._recalculate()

    def increase_level(self) -> None:
        self.set_level(self.level + 1)

    def reset(self) -> None:
        """Сбрасывает игру на стартовый уровень (для новой игры)."""
        self.set_level(self.STARTING_LEVEL)

    def set_bg_color(self, color: tuple) -> None:
        """Устанавливает цвет фона (0–255 по каждому каналу)."""
        self.bg_color = tuple(max(0, min(255, c)) for c in color[:3])

    def save(self) -> None:
        """Сохраняет настройки в config.json."""
        save_config(
            {
                "bg_r": self.bg_color[0],
                "bg_g": self.bg_color[1],
                "bg_b": self.bg_color[2],
            }
        )

    # ═══════════════════════════════════════════════════════════════
    # 4. ГЛАВНЫЙ ПЕРЕСЧЁТ — единственное место, где меняются параметры
    # ═══════════════════════════════════════════════════════════════

    def _recalculate(self) -> None:
        """Пересчитывает все динамические параметры из self.level."""

        # ─── Игрок и враги ─────────────────────────────────────
        self.alien_speed = self._calc_alien_speed(self.level)
        self.alien_points = self._calc_alien_points(self.level)
        self.bullets_allowed = self._calc_bullets_allowed(self.level)
        self.bullet_speed = self._calc_bullet_speed(self.level)
        self.ship_speed = self._calc_ship_speed(self.level)
        self.distance_multiplier = self._calc_distance_multiplier(self.level)
        self.fleet_direction = 1

        # ─── Босс ──────────────────────────────────────────────
        self._recalc_boss(self.level)

    # ─── Формулы: игрок и враги ────────────────────────────────

    def _calc_alien_speed(self, level: int) -> float:
        """Скорость пришельцев.

        Экспоненциальный рост в двух фазах, потом — заморозка.
        Ур. 1: 120 → Ур. 30: ~487 → Ур. 60: ~1182 → Ур. 60+: без изменений.
        """
        # Сколько шагов сделано в каждой фазе
        steps_p1 = min(level - 1, self.PHASE_1_END - 1)
        steps_p2 = max(0, min(level - 1, self.PHASE_2_END - 1) - (self.PHASE_1_END - 1))
        return (
            self.BASE_ALIEN_SPEED
            * (self.ALIEN_SPEED_GROWTH_P1**steps_p1)
            * (self.ALIEN_SPEED_GROWTH_P2**steps_p2)
        )

    def _calc_alien_points(self, level: int) -> int:
        """Очки за пришельца.

        Быстрый рост ×1.5, пока не упрёмся в POINTS_SOFT_CAP,
        затем медленный ×1.005 — чтобы на 100-м уровне очки
        не улетели в космос. Шаг в цикле, потому что int()
        на каждом шаге даёт точное совпадение со старой логикой.
        """
        points = self.BASE_ALIEN_POINTS
        for _ in range(level - 1):
            growth = (
                self.POINTS_GROWTH_FAST
                if points < self.POINTS_SOFT_CAP
                else self.POINTS_GROWTH_SLOW
            )
            points = int(points * growth)
        return points

    def _calc_bullets_allowed(self, level: int) -> int:
        """Максимум пуль на экране: 4 на фазе 1, растёт на фазе 2, кап — 12."""
        extra = max(0, level - self.PHASE_1_END)
        return min(self.BASE_BULLETS_ALLOWED + extra, self.BULLETS_MAX)

    def _calc_bullet_speed(self, level: int) -> float:
        """Скорость пуль игрока: линейный рост только в фазе 2."""
        return (
            self.BASE_BULLET_SPEED
            + self._phase2_steps(level) * self.BULLET_SPEED_GROWTH_P2
        )

    def _calc_ship_speed(self, level: int) -> float:
        """Скорость корабля игрока: линейный рост только в фазе 2."""
        return (
            self.BASE_SHIP_SPEED + self._phase2_steps(level) * self.SHIP_SPEED_GROWTH_P2
        )

    def _calc_distance_multiplier(self, level: int) -> float:
        """Плотность флота: линейный рост, кап — DISTANCE_MAX (5.0)."""
        return min(
            self.BASE_DISTANCE_MULTIPLIER + (level - 1) * self.DISTANCE_INCREASE_RATE,
            self.DISTANCE_MAX,
        )

    def _phase2_steps(self, level: int) -> int:
        """Сколько шагов роста фазы 2 пришлось на этот уровень (0 .. 30)."""
        return max(0, min(level, self.PHASE_2_END) - self.PHASE_1_END)

    # ─── Формулы: босс ─────────────────────────────────────────

    def _recalc_boss(self, level: int) -> None:
        """Пересчитывает все параметры босса из уровня.

        HP        — линейно.
        Скорость  — от BASE к MAX к 60-му уровню.
        Интервалы — сокращаются в 2 раза к 60-му уровню.
        """
        # ─── Прогресс сложности 0.0 .. 1.0 ─────────────────────
        capped_level = min(level, self.PHASE_2_END)
        progress = (capped_level - 1) / (self.PHASE_2_END - 1)

        # ─── HP ────────────────────────────────────────────────
        self.boss_hp = self.BOSS_HP_BASE + level * self.BOSS_HP_PER_LEVEL

        # ─── Скорость движения ─────────────────────────────────
        self.boss_move_speed = (
            self.BOSS_MOVE_SPEED_BASE
            + (self.BOSS_MOVE_SPEED_MAX - self.BOSS_MOVE_SPEED_BASE) * progress
        )

        # ─── Интервалы атак (1.0 на ур.1 → 0.5 на ур.60+) ──────
        mult = 1.0 - progress * 0.5

        # Хранятся как словари {фаза: значение} — удобно читать в Boss
        self.boss_shoot_intervals = {
            1: self.BOSS_SHOOT_P1 * mult,
            2: self.BOSS_SHOOT_P2 * mult,
            3: self.BOSS_SHOOT_P3 * mult,
        }
        self.boss_beam_cooldowns = {
            1: self.BOSS_BEAM_COOLDOWN_P1 * mult,
            2: self.BOSS_BEAM_COOLDOWN_P2 * mult,
            3: self.BOSS_BEAM_COOLDOWN_P3 * mult,
        }
        self.boss_bombing_cooldowns = {
            1: self.BOSS_BOMBING_COOLDOWN_P2 * mult,  # P1 не бомбит
            2: self.BOSS_BOMBING_COOLDOWN_P2 * mult,
            3: self.BOSS_BOMBING_COOLDOWN_P3 * mult,
        }
