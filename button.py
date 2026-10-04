import pygame
import time
from utils import load_font
from style import FONT_SIZE_LARGE


class Button:
    """Кнопка c постоянно бегающим бликом."""

    TEXT_COLOR = (255, 255, 255)

    # Подложка — чёрная полупрозрачная
    BG_ALPHA = 40
    BG_ALPHA_HOVER = 70

    # Рамка
    BORDER_ALPHA = 90
    BORDER_ALPHA_HOVER = 200

    # Блик
    SHINE_DURATION = 1
    SHINE_PAUSE = 1.2         
    SHINE_WIDTH = 60
    SHINE_PEAK_ALPHA = 100

    def __init__(self, ai_game, msg):
        self.screen = ai_game.screen
        self.screen_rect = self.screen.get_rect()

        self.width, self.height = 220, 60

        self.font = load_font(FONT_SIZE_LARGE)

        self.rect = pygame.Rect(0, 0, self.width, self.height)
        self.rect.center = self.screen_rect.center

        self.hovered = False

        self.start_time = time.time()

        self.msg_image = self.font.render(msg, True, self.TEXT_COLOR)
        self.msg_rect = self.msg_image.get_rect(center=self.rect.center)

        self._shine = self._build_shine()

    def _build_shine(self):
        """Плавный блик c затуханием к краям."""
        shine = pygame.Surface((self.SHINE_WIDTH, self.height), pygame.SRCALPHA)
        half = self.SHINE_WIDTH / 2

        for x in range(self.SHINE_WIDTH):
            dist = abs(x - half) / half
            alpha = int(self.SHINE_PEAK_ALPHA * (1 - dist) ** 2)
            pygame.draw.line(
                shine, (255, 255, 255, alpha),
                (x, 0), (x, self.height),
            )

        return shine

    def _get_shine_x(self):
        """Возвращает X-позицию блика. None — если сейчас пауза."""
        cycle = self.SHINE_DURATION + self.SHINE_PAUSE
        elapsed = (time.time() - self.start_time) % cycle

        # Если в паузе — блик не рисуем
        if elapsed >= self.SHINE_DURATION:
            return None

        progress = elapsed / self.SHINE_DURATION
        return int(-self.SHINE_WIDTH + (self.width + self.SHINE_WIDTH) * progress)

    def draw_button(self):
        self.hovered = self.rect.collidepoint(pygame.mouse.get_pos())
        rect = self.rect

        # 1. Тень — тонкая и мягкая
        for i in range(6, 0, -1):
            shadow = pygame.Surface(
                (rect.width + i * 2, rect.height + i * 2),
                pygame.SRCALPHA,
            )
            pygame.draw.rect(shadow, (0, 0, 0, 6), shadow.get_rect())
            self.screen.blit(shadow, (rect.x - i, rect.y - i + 3))

        # 2. Чёрная полупрозрачная подложка
        alpha = self.BG_ALPHA_HOVER if self.hovered else self.BG_ALPHA
        bg = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(bg, (0, 0, 0, alpha), bg.get_rect())
        self.screen.blit(bg, rect.topleft)

        # 3. Блик — бегает постоянно с паузами
        x_pos = self._get_shine_x()
        if x_pos is not None:
            shine_layer = pygame.Surface(rect.size, pygame.SRCALPHA)
            shine_layer.blit(self._shine, (x_pos, 0))

            # Обрезаем блик по границам кнопки
            mask = pygame.Surface(rect.size, pygame.SRCALPHA)
            pygame.draw.rect(mask, (255, 255, 255, 255), mask.get_rect())
            shine_layer.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)

            self.screen.blit(shine_layer, rect.topleft)

        # 4. Рамка — ярче при hover
        border_alpha = self.BORDER_ALPHA_HOVER if self.hovered else self.BORDER_ALPHA
        border = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(
            border, (255, 255, 255, border_alpha),
            border.get_rect(), 1,
        )
        self.screen.blit(border, rect.topleft)

        # 5. Текст
        self.screen.blit(self.msg_image, self.msg_rect)