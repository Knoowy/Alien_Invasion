from pathlib import Path

import pygame
from pygame.sprite import Group

from style import (
    FONT_SIZE_LARGE,
    SCORE_LINE_HEIGHT,
    SCORE_RIGHT_OFFSET,
    SCORE_TOP,
    SHIP_SPACING,
    TEXT_COLOR,
)
from utils import get_data_path, load_font, resource_path


class Scoreboard:
    """Отображает счёт, рекорд, уровень и оставшиеся корабли."""

    RECORD_FILE = "record.txt"
    RECORD_SOUND = "dop_fails/music/record.mp3"

    def __init__(self, screen, screen_rect, settings, stats, ship_factory):
        self.screen = screen
        self.screen_rect = screen_rect
        self.settings = settings
        self.stats = stats
        self._ship_factory = ship_factory

        self.font = load_font(FONT_SIZE_LARGE)

        # Рекорд
        self.record = self._load_record()
        self.has_record = self.record > 0

        # Состояние нового рекорда
        self.new_record = False
        self.rm_cur = False

        # Звук рекорда
        try:
            self.record_sound = pygame.mixer.Sound(resource_path(self.RECORD_SOUND))
        except (FileNotFoundError, pygame.error):
            self.record_sound = None

        # Кэши
        self._last_score = -1
        self._last_level = -1
        self._last_record = -1
        self._last_ships = -1
        self._last_bg_color = None

        self.ships = Group()

        self.score_image = None
        self.record_image = None
        self.level_image = None
        self.score_rect = None
        self.record_rect = None
        self.level_rect = None

    def _load_record(self) -> int:
        """Загружает рекорд из скрытой папки данных."""
        try:
            path = Path(get_data_path()) / self.RECORD_FILE
            if not path.exists():
                return 0
            content = path.read_text().strip()
            return int(content) if content and content.isdigit() else 0
        except (FileNotFoundError, ValueError, OSError):
            return 0

    def _save_record(self, score: int) -> None:
        """Сохраняет рекорд в скрытую папку данных."""
        try:
            path = Path(get_data_path()) / self.RECORD_FILE
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(str(score))
        except OSError:
            pass

    @staticmethod
    def _format(number: int) -> str:
        """Форматирует число с разделителями тысяч."""
        return f"{number:,}"

    def _render(self, text: str, position: tuple, anchor: str):
        """Рендерит текст и возвращает изображение с прямоугольником.

        anchor: topleft, topright, centerx, center
        """
        image = self.font.render(text, True, TEXT_COLOR, self.settings.bg_color)
        rect = image.get_rect()

        x, y = position
        anchors = {
            "topleft": (x, y),
            "topright": (x - rect.width, y),
            "centerx": (x - rect.width // 2, y),
            "center": (x - rect.width // 2, y - rect.height // 2),
        }
        rect.x, rect.y = anchors.get(anchor, (x, y))

        return image, rect

    def _invalidate_caches(self):
        """Сбрасывает все кэши — для перерендера."""
        self._last_score = -1
        self._last_level = -1
        self._last_record = -1

    def _update_ships(self):
        """Обновляет отображение оставшихся кораблей."""
        if self.stats.ships_left == self._last_ships:
            return

        self._last_ships = self.stats.ships_left
        self.ships.empty()

        for i in range(self.stats.ships_left):
            ship = self._ship_factory()
            ship.rect.x = SHIP_SPACING + i * (ship.rect.width + SHIP_SPACING)
            ship.rect.y = 10
            self.ships.add(ship)

    def check_record(self) -> bool:
        """Проверяет и обновляет рекорд. True — если рекорд побит."""
        if self.stats.score <= self.record:
            return False

        self.record = self.stats.score
        self._save_record(self.record)

        if self.has_record and not self.new_record:
            self.new_record = True
            self.rm_cur = False

        self._last_score = -1
        self._last_record = -1
        return True

    def reset(self):
        """Сбрасывает состояние для новой игры."""
        self.new_record = False
        self.rm_cur = False
        self._last_ships = -1
        self.ships.empty()
        self._invalidate_caches()

        self.record = self._load_record()
        self.has_record = self.record > 0

    def draw(self):
        """Отрисовывает все элементы на экране."""
        # Смена цвета фона → все кэши невалидны
        if self.settings.bg_color != self._last_bg_color:
            self._last_bg_color = self.settings.bg_color
            self._invalidate_caches()

        # Счёт
        if self.stats.score != self._last_score:
            self._last_score = self.stats.score
            self.score_image, self.score_rect = self._render(
                self._format(self.stats.score),
                (self.screen_rect.right - SCORE_RIGHT_OFFSET, SCORE_TOP),
                "topright",
            )

        # Рекорд
        if self.record != self._last_record:
            self._last_record = self.record
            self.record_image, self.record_rect = self._render(
                self._format(self.record),
                (self.screen_rect.centerx, SCORE_TOP),
                "centerx",
            )

        # Уровень
        if self.settings.level != self._last_level:
            self._last_level = self.settings.level
            self.level_image, self.level_rect = self._render(
                str(self.settings.level),
                (
                    self.screen_rect.right - SCORE_RIGHT_OFFSET,
                    SCORE_TOP + SCORE_LINE_HEIGHT,
                ),
                "topright",
            )

        # Сообщение о новом рекорде
        if self.new_record:
            if self.record_sound and not self.rm_cur:
                self.rm_cur = True
                try:
                    self.record_sound.play()
                except pygame.error:
                    pass

            msg_image, msg_rect = self._render(
                "NEW RECORD!",
                (self.screen_rect.centerx, self.record_rect.bottom + 10),
                "centerx",
            )
            self.screen.blit(msg_image, msg_rect)

        # Отрисовка
        if self.score_image:
            self.screen.blit(self.score_image, self.score_rect)
        if self.record_image:
            self.screen.blit(self.record_image, self.record_rect)
        if self.level_image:
            self.screen.blit(self.level_image, self.level_rect)

        self._update_ships()
        self.ships.draw(self.screen)
