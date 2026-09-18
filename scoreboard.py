import pygame
from pygame.sprite import Group
from pathlib import Path
from utils import resource_path, app_path, get_data_path


class Scoreboard:
    """Отображает счет, рекорд, уровень и оставшиеся корабли."""

    # Настройки отображения
    TEXT_COLOR = (255, 215, 0)
    FONT_SIZE = 48
    SCORE_TOP = 20
    SCORE_RIGHT_OFFSET = 20
    SHIP_SPACING = 10
    FLEET_TOP_OFFSET = FONT_SIZE + 20
    RECORD_FILE = "record.txt"
    RECORD_SOUND = "dop_fails/music/record.mp3"

    def __init__(self, screen, screen_rect, settings, stats, ship_factory):
        self.screen = screen
        self.screen_rect = screen_rect
        self.settings = settings
        self.stats = stats
        self._ship_factory = ship_factory

        self.font = pygame.font.SysFont(None, self.FONT_SIZE)

        # Загрузка рекорда
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

        # Кэши для оптимизации
        self.last_score = -1
        self._last_level = -1
        self._last_ships = -1

        # Группа для кораблей
        self.ships = Group()

        # Изображения и их прямоугольники
        self.score_image = None
        self.record_image = None
        self.level_image = None
        self.score_rect = None
        self.record_rect = None
        self.level_rect = None

    def _load_record(self) -> int:
        """Загружает рекорд из скрытой папки данных."""
        try:
            data_dir = get_data_path()
            path = Path(data_dir) / self.RECORD_FILE
            if not path.exists():
                return 0
            content = path.read_text().strip()
            return int(content) if content and content.isdigit() else 0
        except (FileNotFoundError, ValueError, OSError):
            return 0

    def _save_record(self, score: int) -> None:
        """Сохраняет рекорд в скрытую папку данных."""
        try:
            data_dir = get_data_path()
            path = Path(data_dir) / self.RECORD_FILE
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(str(score))
        except OSError:
            pass


    @staticmethod
    def _format(number: int) -> str:
        """Форматирует число с разделителями тысяч."""
        return f"{number:,}"

    def _render(self, text: str, position: tuple, anchor: str):
        """
        Рендерит текст и возвращает изображение с прямоугольником.
        anchor: topleft, topright, centerx, center
        """
        image = self.font.render(text, True, self.TEXT_COLOR, self.settings.bg_color)
        rect = image.get_rect()

        x, y = position
        anchors = {
            'topleft': (x, y),
            'topright': (x - rect.width, y),
            'centerx': (x - rect.width // 2, y),
            'center': (x - rect.width // 2, y - rect.height // 2),
        }
        rect.x, rect.y = anchors.get(anchor, (x, y))

        return image, rect

    def _update_ships(self):
        """Обновляет отображение оставшихся кораблей."""
        if self.stats.ships_left == self._last_ships:
            return

        self._last_ships = self.stats.ships_left
        self.ships.empty()

        for i in range(self.stats.ships_left):
            ship = self._ship_factory()
            ship.rect.x = self.SHIP_SPACING + i * (ship.rect.width + self.SHIP_SPACING)
            ship.rect.y = 10
            self.ships.add(ship)

    def check_record(self) -> bool:
        """
        Проверяет и обновляет рекорд.
        Возвращает True, если рекорд побит.
        """
        if self.stats.score <= self.record:
            return False

        self.record = self.stats.score
        self._save_record(self.record)

        # Показываем сообщение только если есть существующий рекорд
        if self.has_record and not self.new_record:
            self.new_record = True
            self.rm_cur = False

        self.last_score = -1
        return True

    def reset(self):
        """Сбрасывает состояние для новой игры."""
        self.new_record = False
        self.rm_cur = False
        self.last_score = -1
        self._last_level = -1
        self._last_ships = -1
        self.ships.empty()

        # Перезагружаем рекорд
        self.record = self._load_record()
        self.has_record = self.record > 0

    def draw(self):
        """Отрисовывает все элементы на экране."""
        # Счет
        if self.stats.score != self.last_score:
            self.last_score = self.stats.score
            self.score_image, self.score_rect = self._render(
                self._format(self.stats.score),
                (self.screen_rect.right - self.SCORE_RIGHT_OFFSET, self.SCORE_TOP),
                'topright'
            )

        # Рекорд
        self.record_image, self.record_rect = self._render(
            self._format(self.record),
            (self.screen_rect.centerx, self.SCORE_TOP),
            'centerx'
        )

        # Уровень
        if self.settings.level != self._last_level:
            self._last_level = self.settings.level
            self.level_image, self.level_rect = self._render(
                str(self.settings.level),
                (self.screen_rect.right - self.SCORE_RIGHT_OFFSET, self.SCORE_TOP + 50),
                'topright'
            )

        # Сообщение о новом рекорде
        if self.new_record:
            # Звук воспроизводим только один раз
            if self.record_sound and not self.rm_cur:
                self.rm_cur = True
                try:
                    self.record_sound.play()
                except pygame.error:
                    pass

            msg_image, msg_rect = self._render(
                "NEW RECORD!",
                (self.screen_rect.centerx, self.record_rect.bottom + 10),
                'centerx'
            )
            self.screen.blit(msg_image, msg_rect)

        # Отрисовка
        if self.score_image:
            self.screen.blit(self.score_image, self.score_rect)
        self.screen.blit(self.record_image, self.record_rect)
        if self.level_image:
            self.screen.blit(self.level_image, self.level_rect)

        self._update_ships()
        self.ships.draw(self.screen)