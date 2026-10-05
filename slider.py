import pygame

from style import FONT_SIZE_SLIDER
from utils import load_font


class Slider:
    """Ползунок для настройки значения (от min_val до max_val)."""

    def __init__(self, x, y, width, min_val, max_val, initial_value, label, color):
        self.rect = pygame.Rect(x, y, width, 8)
        self.min_val = min_val
        self.max_val = max_val
        self.value = initial_value
        self.label = label
        self.color = color
        self.dragging = False
        self.handle_radius = 12
        # Отдельный шрифт для подписи (меньше основного)
        self.label_font = load_font(FONT_SIZE_SLIDER)

    def handle_event(self, event) -> bool:
        """Обрабатывает события мыши. True — если значение изменилось."""
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._handle_rect().collidepoint(event.pos) or self.rect.inflate(
                0, 20
            ).collidepoint(event.pos):
                self.dragging = True
                self._update_from_pos(event.pos[0])
                return True

        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self.dragging:
                self.dragging = False
                return True

        elif event.type == pygame.MOUSEMOTION and self.dragging:
            self._update_from_pos(event.pos[0])
            return True

        return False

    def _update_from_pos(self, mouse_x):
        rel_x = mouse_x - self.rect.x
        rel_x = max(0, min(rel_x, self.rect.width))
        ratio = rel_x / self.rect.width
        self.value = int(self.min_val + ratio * (self.max_val - self.min_val))

    def _handle_x(self) -> int:
        ratio = (self.value - self.min_val) / (self.max_val - self.min_val)
        return self.rect.x + int(ratio * self.rect.width)

    def _handle_rect(self) -> pygame.Rect:
        hx = self._handle_x()
        return pygame.Rect(
            hx - self.handle_radius,
            self.rect.centery - self.handle_radius,
            self.handle_radius * 2,
            self.handle_radius * 2,
        )

    def draw(self, screen):
        """Рисует ползунок."""
        rgb_color = (255, 255, 255)
        # Буква "R" — на фиксированной позиции, не двигается
        letter_surf = self.label_font.render(self.label, True, rgb_color)
        letter_rect = letter_surf.get_rect()
        letter_rect.left = self.rect.x - 80  # фиксированный отступ
        letter_rect.centery = self.rect.centery
        screen.blit(letter_surf, letter_rect)

        # Число — прижато правым краем, растёт влево
        value_surf = self.label_font.render(str(self.value), True, rgb_color)
        value_rect = value_surf.get_rect()
        value_rect.right = self.rect.x - 20  # ← фиксируем ПРАВЫЙ край
        value_rect.centery = self.rect.centery
        screen.blit(value_surf, value_rect)

        # Дорожка
        pygame.draw.rect(screen, (50, 50, 60), self.rect, border_radius=4)

        # Заполненная часть
        filled_width = self._handle_x() - self.rect.x
        if filled_width > 0:
            filled = pygame.Rect(
                self.rect.x, self.rect.y, filled_width, self.rect.height
            )
            pygame.draw.rect(screen, self.color, filled, border_radius=4)

        # Ручка
        hx = self._handle_x()
        pygame.draw.circle(
            screen, (240, 240, 240), (hx, self.rect.centery), self.handle_radius
        )
        pygame.draw.circle(
            screen, (30, 30, 30), (hx, self.rect.centery), self.handle_radius, 2
        )
